"""The launcher's start-up (its Compose project and network), the removal of its notebooks at
start and stop, and the reaper of expired containers."""

import threading
import time

import pytest

from fione_launcher.docker import DockerAPI
from fione_launcher.server import Launcher, run_reaper
from launcher_helpers import NETWORK, PROJECT, FakeDocker, labels, make_config


def test_start_up_finds_the_project_and_the_network():
    docker = FakeDocker()
    launcher = Launcher.start_up(make_config(), docker)
    assert (launcher.project, launcher.network) == (PROJECT, NETWORK)
    assert ("find_network", PROJECT, "notebooks") in docker.calls


def test_start_up_removes_this_projects_notebooks():
    docker = FakeDocker()
    docker.add("p-nb-1", labels(PROJECT, "1"))
    docker.add("p-unrelated", {"com.docker.compose.project": PROJECT})
    Launcher.start_up(make_config(), docker)
    assert docker.names() == {"p-unrelated"}


def test_start_up_without_a_compose_project_exits():
    docker = FakeDocker()
    docker.self_labels = {}
    with pytest.raises(SystemExit) as raised:
        Launcher.start_up(make_config(), docker)
    assert "com.docker.compose.project" in str(raised.value.code)


@pytest.mark.parametrize("change", ["missing", "other-project", "not-internal", "two"])
def test_start_up_without_the_notebooks_network_exits(change):
    docker = FakeDocker()
    network = docker.networks[0]
    if change == "missing":
        docker.networks = []
    elif change == "other-project":
        network["Labels"]["com.docker.compose.project"] = "q"
    elif change == "not-internal":
        network["Internal"] = False
    else:
        docker.networks.append(dict(network, Name="p_notebooks2"))
    with pytest.raises(SystemExit) as raised:
        Launcher.start_up(make_config(), docker)
    assert "notebooks" in str(raised.value.code)
    assert not [c for c in docker.calls if c[0] == "remove"]


def test_reconcile_removes_only_this_projects_notebooks():
    docker = FakeDocker()
    for uid in ("1", "2"):
        docker.add(f"a-nb-{uid}", labels("a", uid))
        docker.add(f"b-nb-{uid}", labels("b", uid))
    docker.add("a-other", {"fione.project": "a"})  # not a notebook
    launcher = Launcher(make_config(), docker, project="a", network="a_notebooks")
    launcher.remove_all()
    assert docker.names() == {"b-nb-1", "b-nb-2", "a-other"}


def test_close_removes_all(launcher, docker):
    docker.add("p-nb-1", labels(PROJECT, "1"))
    launcher.close()
    assert docker.names() == set()


def test_reaper_removes_expired():
    now = 1_800_000_000
    docker = FakeDocker()
    docker.add("p-nb-1", labels(PROJECT, "1", expires=now - 1))
    docker.add("p-nb-2", labels(PROJECT, "2", expires=now))
    docker.add("p-nb-3", labels(PROJECT, "3", expires=now + 1))
    docker.add("p-nb-4", labels(PROJECT, "4", expires="soon"))  # unreadable: removed
    docker.add("p-nb-6", labels(PROJECT, "6", expires="\u00b2"))  # not an ASCII digit: removed
    docker.add("q-nb-5", labels("q", "5", expires=now - 1))  # another project's: kept
    launcher = Launcher(make_config(), docker, project=PROJECT, network=NETWORK)
    launcher.reap(now)
    assert docker.names() == {"p-nb-3", "q-nb-5"}


def test_reaper_thread_runs_until_stopped():
    docker = FakeDocker()
    docker.add("p-nb-1", labels(PROJECT, "1", expires=int(time.time()) - 1))
    launcher = Launcher(make_config(), docker, project=PROJECT, network=NETWORK)
    stop = threading.Event()
    thread = threading.Thread(target=run_reaper, args=(launcher, stop, 0.01), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while docker.names() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert docker.names() == set()
    stop.set()
    thread.join(5)
    assert not thread.is_alive()


def test_reaper_survives_a_docker_error():
    docker = FakeDocker()
    failures = []

    def broken(project):
        failures.append(project)
        raise OSError("socket gone")

    docker.list_notebooks = broken
    launcher = Launcher(make_config(), docker, project=PROJECT, network=NETWORK)
    stop = threading.Event()
    thread = threading.Thread(target=run_reaper, args=(launcher, stop, 0.01), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while len(failures) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    stop.set()
    thread.join(5)
    assert len(failures) >= 2


def test_fake_docker_has_the_same_methods():
    public = {name for name in vars(DockerAPI) if not name.startswith("_")}
    assert public <= set(dir(FakeDocker))


def test_remove_all_goes_on_after_a_failed_removal(caplog):
    docker = FakeDocker()
    for uid in ("1", "2", "3"):
        docker.add(f"p-nb-{uid}", labels(PROJECT, uid))
    remove = docker.remove
    failing = docker.containers["p-nb-1"]["Id"]

    def flaky(container_id):
        if container_id == failing:
            raise TimeoutError("remove failed")
        remove(container_id)

    docker.remove = flaky
    launcher = Launcher(make_config(), docker, project=PROJECT, network=NETWORK)
    launcher.close()
    assert docker.names() == {"p-nb-1"}
    assert "removing a notebook container failed: TimeoutError" in caplog.text
    docker.add("p-nb-4", labels(PROJECT, "4", expires=1))
    launcher.reap(1_800_000_000)
    assert docker.names() == {"p-nb-1"}


def test_listed_containers_of_other_projects_are_never_removed():
    """Even when Docker's answer holds containers the label filter should have left out."""
    docker = FakeDocker()
    docker.add("p-nb-1", labels(PROJECT, "1", expires=1))
    docker.add("q-nb-1", labels("q", "1", expires=1))
    docker.add("p-other", {"fione.project": PROJECT, "fione.expires": "1"})

    def unfiltered(project):
        docker.calls.append(("list_notebooks", project))
        return [{"Id": c["Id"], "Labels": c["Labels"]} for c in docker.containers.values()]

    docker.list_notebooks = unfiltered
    launcher = Launcher(make_config(), docker, project=PROJECT, network=NETWORK)
    launcher.reap(1_800_000_000)
    assert docker.names() == {"q-nb-1", "p-other"}
    docker.add("p-nb-2", labels(PROJECT, "2"))
    launcher.remove_all()
    assert docker.names() == {"q-nb-1", "p-other"}
