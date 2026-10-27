"""The notebook launcher image (docker/Dockerfile.launcher) against a real Docker daemon: in a
throwaway Compose project with an internal `notebooks` network, it starts containers with the
fixed spec and no egress, stops them keeping the volume, and removes them all on SIGTERM.

Everything this module creates carries its own project name and is removed by that name."""

import json
import os
import secrets
import subprocess
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.docker

ROOT = Path(__file__).resolve().parents[2]
PROJECT = f"fione-l7-{os.getpid()}"
LAUNCHER_IMAGE = f"{PROJECT}-launcher:test"
NOTEBOOK_IMAGE = f"{PROJECT}-notebook:test"
SECRET = secrets.token_hex(32)
# A stand-in for the notebook image: it only sleeps, and is healthy at once.
NOTEBOOK_DOCKERFILE = """\
FROM python:3.12.15-slim-trixie
HEALTHCHECK --interval=1s --timeout=3s --retries=1 CMD ["true"]
CMD ["sleep", "300"]
"""
COMPOSE = f"""\
name: {PROJECT}
services:
  launcher:
    image: {LAUNCHER_IMAGE}
    environment:
      FIONE_LAUNCHER_SECRET: {SECRET}
      FIONE_NOTEBOOK_IMAGE: {NOTEBOOK_IMAGE}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks: [launcher]
    ports: ["127.0.0.1::8000"]  # for this test only: the real launcher publishes nothing
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    read_only: true
  # Keeps the `notebooks` network in the project, as the gateway does in the real stack.
  peer:
    image: {NOTEBOOK_IMAGE}
    command: ["sleep", "infinity"]
    init: true
    networks: [notebooks]
networks:
  launcher: {{}}
  notebooks:
    internal: true
"""


def _docker(*args: str, check: bool = True, timeout: float = 120) -> str:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check, timeout=timeout
    ).stdout


def _ids(kind: str, label: str) -> list[str]:
    command = ["ps", "-aq"] if kind == "container" else [kind, "ls", "-q"]
    return _docker(*command, "--filter", f"label={label}", check=False).split()


def _remove_project(compose_file: Path) -> None:
    """Remove what carries this module's project name, and nothing else."""
    for container in _ids("container", f"fione.project={PROJECT}"):
        _docker("rm", "-f", container, check=False)
    if compose_file.exists():
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down", "-v", "--remove-orphans"],
            capture_output=True,
            timeout=120,
        )
    for container in _ids("container", f"com.docker.compose.project={PROJECT}"):
        _docker("rm", "-f", container, check=False)
    for volume in _ids("volume", f"fione.project={PROJECT}"):
        _docker("volume", "rm", volume, check=False)
    for network in _ids("network", f"com.docker.compose.project={PROJECT}"):
        _docker("network", "rm", network, check=False)


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    compose_file = tmp_path_factory.mktemp("launcher") / "compose.yaml"
    try:
        build = subprocess.run(
            ["docker", "build", "-f", "docker/Dockerfile.launcher", "-t", LAUNCHER_IMAGE, "."],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=1200,
        )
        assert build.returncode == 0, build.stderr[-5000:]
        build = subprocess.run(
            ["docker", "build", "-t", NOTEBOOK_IMAGE, "-"],
            input=NOTEBOOK_DOCKERFILE,
            capture_output=True,
            text=True,
            timeout=1200,
        )
        assert build.returncode == 0, build.stderr[-5000:]
        compose_file.write_text(COMPOSE)
        up = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d", "--wait"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert up.returncode == 0, up.stderr[-5000:]
        port = _docker("compose", "-f", str(compose_file), "port", "launcher", "8000")
        url = f"http://127.0.0.1:{port.strip().rsplit(':', 1)[1]}"
        yield (
            compose_file,
            httpx.Client(base_url=url, timeout=60, headers={"X-Fione-Launcher-Secret": SECRET}),
        )
    finally:
        _remove_project(compose_file)
        _docker("image", "rm", LAUNCHER_IMAGE, NOTEBOOK_IMAGE, check=False)


@pytest.fixture
def api(stack):
    return stack[1]


def _start_body() -> dict:
    return {
        "launch_key": secrets.token_hex(32),
        "cookie_secret": secrets.token_hex(32),
        "token": "fione_" + secrets.token_urlsafe(30),
        "fione_origin": "http://127.0.0.1:8080",
        "expires_at": int(time.time()) + 3600,
    }


def _wait(condition, timeout: float, what: str):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = condition()
        if value:
            return value
        time.sleep(0.5)
    raise AssertionError(f"timed out waiting for {what}")


def _inspect(name: str) -> dict | None:
    out = _docker("inspect", name, check=False)
    data = json.loads(out) if out.strip() else []
    return data[0] if data else None


def _start(api: httpx.Client, uid: str) -> None:
    r = api.put(f"/notebooks/{uid}", json=_start_body())
    assert r.status_code == 200 and r.json() == {"state": "starting"}, r.text


def test_started_container_has_the_spec(api):
    uid = "7"
    name = f"{PROJECT}-nb-{uid}"
    _start(api, uid)
    try:
        _wait(lambda: api.get(f"/notebooks/{uid}").json()["state"] == "running", 60, "running")
        info = _inspect(name)
        host = info["HostConfig"]
        assert host["NanoCpus"] == 2_000_000_000
        assert host["Memory"] == host["MemorySwap"] == 4294967296
        assert host["PidsLimit"] == 512
        assert host["CapDrop"] == ["ALL"]
        assert host["SecurityOpt"] == ["no-new-privileges:true"]
        assert host["AutoRemove"] is True and host["Init"] is True
        assert host["Privileged"] is False and not host["Binds"] and not host["PortBindings"]
        assert info["Config"]["User"] == "1000:1000"
        assert info["Config"]["Image"] == NOTEBOOK_IMAGE
        labels = info["Config"]["Labels"]
        assert labels["fione.notebook"] == "1"
        assert labels["fione.project"] == PROJECT
        assert labels["fione.uid"] == uid
        assert int(labels["fione.expires"]) > time.time()
        networks = info["NetworkSettings"]["Networks"]
        assert list(networks) == [f"{PROJECT}_notebooks"]
        assert f"nb-{uid}" in networks[f"{PROJECT}_notebooks"]["Aliases"]
        mounts = [(m["Type"], m["Name"], m["Destination"]) for m in info["Mounts"]]
        assert mounts == [("volume", f"{PROJECT}-nb-home-{uid}", "/home/nb/work")]
        volume = json.loads(_docker("volume", "inspect", f"{PROJECT}-nb-home-{uid}"))[0]
        assert volume["Labels"] == {"fione.project": PROJECT, "fione.uid": uid}
    finally:
        api.delete(f"/notebooks/{uid}")


def test_no_egress(api):
    uid = "8"
    name = f"{PROJECT}-nb-{uid}"
    _start(api, uid)
    script = """
import socket
for host in ("pypi.org", "1.1.1.1"):
    try:
        socket.create_connection((host, 443), timeout=5).close()
        print("connected:", host)
    except OSError:
        pass
try:
    socket.getaddrinfo("host.docker.internal", 443)
    print("resolved: host.docker.internal")
except OSError:
    pass
print("done")
"""
    try:
        out = _docker("exec", name, "python", "-c", script, timeout=60)
        assert out.strip() == "done", out
    finally:
        api.delete(f"/notebooks/{uid}")


def test_stop_removes_container_and_keeps_volume(api):
    uid = "9"
    name = f"{PROJECT}-nb-{uid}"
    _start(api, uid)
    assert _inspect(name) is not None
    assert api.delete(f"/notebooks/{uid}").status_code == 204
    _wait(lambda: _inspect(name) is None, 30, "the container to go")
    assert api.get(f"/notebooks/{uid}").json() == {"state": "absent"}
    assert api.delete(f"/notebooks/{uid}").status_code == 204
    _docker("volume", "inspect", f"{PROJECT}-nb-home-{uid}")


def test_sigterm_removes_all(stack, api):
    """Last in this module: it stops the launcher."""
    compose_file = stack[0]
    for uid in ("10", "11"):
        _start(api, uid)
    assert len(_ids("container", f"fione.project={PROJECT}")) == 2
    _docker("compose", "-f", str(compose_file), "stop", "launcher", timeout=60)
    assert _ids("container", f"fione.project={PROJECT}") == []
    launcher = _docker("compose", "-f", str(compose_file), "ps", "-aq", "launcher").strip()
    assert _docker("inspect", "-f", "{{.State.ExitCode}}", launcher).strip() == "0"
