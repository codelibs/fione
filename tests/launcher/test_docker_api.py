"""The real ``DockerAPI`` helpers with canned Docker answers (no socket): the label filters that
keep the launcher to its own project, the internal-network check, the encoding of ids, and
which statuses are errors."""

import json
import logging
from urllib.parse import parse_qs, urlsplit

import pytest

from fione_launcher.docker import DockerAPI, DockerError


class CannedDocker(DockerAPI):
    """``DockerAPI`` whose ``request`` answers from ``answers`` and records each call."""

    def __init__(self, *answers: tuple[int, object]):
        super().__init__("/nonexistent.sock")
        self.answers = list(answers)
        self.sent: list[tuple[str, str, dict | None]] = []

    def request(self, method, path, body=None):
        self.sent.append((method, path, body))
        return self.answers.pop(0)


def _query(path: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(path).query)


def _network(name: str, internal: bool = True) -> dict:
    return {"Name": name, "Internal": internal}


def test_find_network_filters_on_both_compose_labels():
    docker = CannedDocker((200, [_network("p_notebooks")]))
    assert docker.find_network("p", "notebooks") == "p_notebooks"
    [(method, path, body)] = docker.sent
    assert (method, urlsplit(path).path, body) == ("GET", "/networks", None)
    assert json.loads(_query(path)["filters"][0]) == {
        "label": ["com.docker.compose.project=p", "com.docker.compose.network=notebooks"]
    }


@pytest.mark.parametrize(
    "networks",
    [
        [],
        [_network("p_notebooks"), _network("p_notebooks2")],
        [_network("p_notebooks", internal=False)],
        [{"Name": "p_notebooks"}],
    ],
    ids=["none", "two", "not-internal", "internal-unknown"],
)
def test_find_network_fails_closed(networks):
    with pytest.raises(LookupError):
        CannedDocker((200, networks)).find_network("p", "notebooks")


def test_list_notebooks_filters_on_this_project_and_lists_all_states():
    containers = [{"Id": "abc", "Labels": {}}]
    docker = CannedDocker((200, containers))
    assert docker.list_notebooks("p") == containers
    [(method, path, _)] = docker.sent
    assert (method, urlsplit(path).path) == ("GET", "/containers/json")
    query = _query(path)
    assert query["all"] == ["true"]
    assert json.loads(query["filters"][0]) == {"label": ["fione.notebook=1", "fione.project=p"]}


def test_ids_and_names_are_percent_encoded():
    docker = CannedDocker((404, None), (204, None), (204, None))
    assert docker.inspect("a/../b") is None
    docker.start("a/../b")
    docker.remove("a/../b?x=1")
    assert [path for _, path, _ in docker.sent] == [
        "/containers/a%2F..%2Fb/json",
        "/containers/a%2F..%2Fb/start",
        "/containers/a%2F..%2Fb%3Fx%3D1?force=true",
    ]


def test_inspect_error_other_than_404_raises():
    with pytest.raises(DockerError) as raised:
        CannedDocker((500, {"message": "boom"})).inspect("p-nb-7")
    assert raised.value.status == 500


def test_create_sends_the_body_and_returns_the_id():
    docker = CannedDocker((201, {"Id": "abc", "Warnings": []}))
    assert docker.create("p-nb-7", {"Image": "x"}) == "abc"
    [(method, path, body)] = docker.sent
    assert method == "POST" and body == {"Image": "x"}
    assert urlsplit(path).path == "/containers/create" and _query(path) == {"name": ["p-nb-7"]}


def test_create_logs_only_the_number_of_warnings(caplog):
    caplog.set_level(logging.DEBUG)
    warning = "Your kernel does not support swap limit capabilities"
    docker = CannedDocker((201, {"Id": "abc", "Warnings": [warning]}))
    assert docker.create("p-nb-7", {"Image": "x"}) == "abc"
    assert "Docker created p-nb-7 with 1 warning(s)" in caplog.text
    assert warning not in caplog.text


def test_create_of_a_missing_image_is_a_404_with_docker_s_message():
    docker = CannedDocker((404, {"message": "No such image: nb:1"}))
    with pytest.raises(DockerError) as raised:
        docker.create("p-nb-7", {"Image": "nb:1"})
    assert raised.value.status == 404
    assert raised.value.detail == "No such image: nb:1"
    assert str(raised.value) == "POST /containers/create: 404"  # what logs show
    assert [method for method, _, _ in docker.sent] == ["POST"]  # never a pull


@pytest.mark.parametrize("status", [204, 404, 409])
def test_remove_accepts_gone_and_being_removed(status):
    CannedDocker((status, None)).remove("abc")


def test_remove_raises_on_a_server_error():
    with pytest.raises(DockerError):
        CannedDocker((500, None)).remove("abc")


def test_create_volume_keeps_an_existing_one():
    docker = CannedDocker((201, {}), (200, {}))
    docker.create_volume("p-nb-home-7", {"fione.project": "p"})
    docker.create_volume("p-nb-home-7", {"fione.project": "p"})
    assert docker.sent[0] == (
        "POST",
        "/volumes/create",
        {"Name": "p-nb-home-7", "Labels": {"fione.project": "p"}},
    )


def test_inspect_volume():
    docker = CannedDocker((200, {"Name": "p-nb-home-7", "Labels": {}}), (404, None))
    assert docker.inspect_volume("p-nb-home-7")["Name"] == "p-nb-home-7"
    assert docker.inspect_volume("a/b") is None
    assert [path for _, path, _ in docker.sent] == ["/volumes/p-nb-home-7", "/volumes/a%2Fb"]
    with pytest.raises(DockerError):
        CannedDocker((500, None)).inspect_volume("v")


@pytest.mark.parametrize("status", [204, 404])
def test_remove_volume_accepts_gone(status):
    docker = CannedDocker((status, None))
    docker.remove_volume("p-nb-home-7")
    assert docker.sent == [("DELETE", "/volumes/p-nb-home-7", None)]


@pytest.mark.parametrize("status", [409, 500])
def test_remove_volume_raises_on_in_use_and_errors(status):
    with pytest.raises(DockerError) as raised:
        CannedDocker((status, {"message": "volume is in use"})).remove_volume("v")
    assert raised.value.status == status
