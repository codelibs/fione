"""The launcher's HTTP API against a fake Docker: the shared secret, validation before any
Docker call, the start conflicts and the states, and logs without secrets."""

import http.client
import json
import logging
import socket
import threading
import time

import pytest

from fione_launcher.docker import DockerError
from fione_launcher.server import SECRET_HEADER
from fione_launcher.spec import StartRequest
from launcher_helpers import IMAGE, PROJECT, SECRET, labels, make_config, start_request

UID = "7"
NAME = f"{PROJECT}-nb-{UID}"


def test_health_needs_no_secret(api):
    assert api.call("GET", "/health", secret=None) == (200, {})


@pytest.mark.parametrize("secret", [None, "", "s" * 39, "t" * 40, "s" * 41, "ß" * 40])
@pytest.mark.parametrize("method", ["PUT", "GET", "DELETE"])
def test_secret_required(api, docker, method, secret):
    body = start_request() if method == "PUT" else None
    assert api.call(method, f"/notebooks/{UID}", body, secret=secret) == (
        401,
        {"error": "unauthorized"},
    )
    assert api.call("GET", "/elsewhere", secret=secret)[0] == 401
    assert docker.calls == []


def test_unknown_route_is_404(api):
    assert api.call("GET", "/notebooks") == (404, {"error": "not_found"})
    assert api.call("POST", f"/notebooks/{UID}") == (405, {"error": "method_not_allowed"})
    assert api.call("PATCH", f"/notebooks/{UID}", secret=None) == (401, {"error": "unauthorized"})


def _invalid_cases():
    now = int(time.time())
    valid = start_request()
    cases = {
        "uid-0": ("0", valid),
        "uid-letter": ("1a", valid),
        "uid-traversal": ("../1", valid),
        "uid-encoded-traversal": ("..%2F1", valid),
        "uid-query": ("1?x=1", valid),
        "uid-19-digits": ("1" * 19, valid),
        "key-63-hex": (UID, start_request(launch_key="a" * 63)),
        "key-uppercase": (UID, start_request(launch_key="A" * 64)),
        "cookie-secret-63-hex": (UID, start_request(cookie_secret="b" * 63)),
        "token-newline": (UID, start_request(token="fione_" + "T" * 30 + "\n")),
        "token-inner-newline": (UID, start_request(token="fione_" + "T" * 15 + "\nX=" + "T" * 15)),
        "token-short": (UID, start_request(token="fione_" + "T" * 19)),
        "origin-path": (UID, start_request(fione_origin="http://127.0.0.1:8080/x")),
        "origin-newline": (UID, start_request(fione_origin="http://127.0.0.1:8080\n")),
        "origin-empty-label": (UID, start_request(fione_origin="http://a..b")),
        "origin-dots": (UID, start_request(fione_origin="http://..")),
        "origin-leading-hyphen": (UID, start_request(fione_origin="http://-x:8080")),
        "origin-trailing-hyphen": (UID, start_request(fione_origin="http://x-")),
        "origin-ipv6": (UID, start_request(fione_origin="http://[::1]:8080")),
        "expires-past": (UID, start_request(expires_at=now - 1)),
        "expires-8-days": (UID, start_request(expires_at=now + 8 * 86400)),
        "extra-image": (UID, {**valid, "image": "evil:latest"}),
        "extra-uid": (UID, {**valid, "uid": UID}),
        "missing-token": (UID, start_request(token=None)),
    }
    return [pytest.param(uid, body, id=name) for name, (uid, body) in cases.items()]


@pytest.mark.parametrize(("uid", "body"), _invalid_cases())
def test_invalid_requests_never_reach_docker(api, docker, uid, body):
    assert api.call("PUT", f"/notebooks/{uid}", body) == (422, {"error": "invalid"})
    assert docker.calls == []


@pytest.mark.parametrize(
    "raw",
    [b"", b"not json", b"[]", b"{" + b" " * 9000 + b"}"],
    ids=["empty", "not-json", "array", "too-large"],
)
def test_malformed_bodies_never_reach_docker(api, docker, raw):
    assert api.call("PUT", f"/notebooks/{UID}", raw=raw) == (422, {"error": "invalid"})
    assert docker.calls == []


def test_non_ascii_content_length_is_refused(api, docker):
    conn = http.client.HTTPConnection("127.0.0.1", api.port, timeout=10)
    try:
        conn.putrequest("PUT", f"/notebooks/{UID}")
        conn.putheader("X-Fione-Launcher-Secret", SECRET)
        conn.putheader("Content-Length", "\u00b2")
        conn.endheaders()
        response = conn.getresponse()
        assert (response.status, json.loads(response.read())) == (422, {"error": "invalid"})
    finally:
        conn.close()
    assert docker.calls == []


def test_duplicate_keys_are_refused(api, docker):
    valid = start_request()
    raw = json.dumps(valid)[:-1] + ', "token": "fione_' + "U" * 40 + '"}'
    assert api.call("PUT", f"/notebooks/{UID}", raw=raw.encode()) == (422, {"error": "invalid"})
    assert docker.calls == []


@pytest.mark.parametrize("uid", ["7", "../1"])
def test_get_and_delete_validate_the_uid(api, docker, uid):
    if uid == "7":
        assert api.call("GET", f"/notebooks/{uid}") == (200, {"state": "absent"})
        assert api.call("DELETE", f"/notebooks/{uid}") == (204, None)
        assert ("inspect", NAME) in docker.calls
    else:
        assert api.call("GET", f"/notebooks/{uid}") == (422, {"error": "invalid"})
        assert api.call("DELETE", f"/notebooks/{uid}") == (422, {"error": "invalid"})
        assert docker.calls == []


def test_put_starts_a_container(api, docker):
    assert api.call("PUT", f"/notebooks/{UID}", start_request()) == (200, {"state": "starting"})
    created = [c for c in docker.calls if c[0] == "create"]
    assert len(created) == 1 and created[0][1] == NAME
    assert created[0][2]["Image"] == IMAGE
    assert docker.volumes == {
        f"{PROJECT}-nb-home-{UID}": {"fione.project": PROJECT, "fione.uid": UID}
    }
    assert ("start", docker.containers[NAME]["Id"]) in docker.calls


def test_put_twice_is_409_exists(api, docker):
    assert api.call("PUT", f"/notebooks/{UID}", start_request())[0] == 200
    assert api.call("PUT", f"/notebooks/{UID}", start_request()) == (409, {"error": "exists"})
    assert len([c for c in docker.calls if c[0] == "create"]) == 1


def test_limit_is_409(api, docker):
    for uid in ("1", "2", "3", "4"):
        docker.add(f"{PROJECT}-nb-{uid}", labels(PROJECT, uid))
    docker.add("q-nb-5", labels("q", "5"))  # another project's: not counted
    assert api.call("PUT", f"/notebooks/{UID}", start_request()) == (409, {"error": "limit"})
    assert not [c for c in docker.calls if c[0] in ("create", "create_volume")]
    # A user already running gets `exists`, not `limit`.
    assert api.call("PUT", "/notebooks/1", start_request()) == (409, {"error": "exists"})
    docker.containers.pop(f"{PROJECT}-nb-4")
    assert api.call("PUT", f"/notebooks/{UID}", start_request())[0] == 200


def test_missing_image_is_503(api, docker):
    docker.images.clear()
    assert api.call("PUT", f"/notebooks/{UID}", start_request()) == (
        503,
        {"error": "image_missing"},
    )
    assert NAME not in docker.containers


def test_docker_failure_is_500_without_details(api, docker):
    def broken(name, body):
        raise OSError("socket gone")

    docker.create = broken
    assert api.call("PUT", f"/notebooks/{UID}", start_request()) == (500, {"error": "internal"})


def test_start_failure_removes_the_container(api, docker):
    def broken(container_id):
        raise OSError("start failed")

    docker.start = broken
    assert api.call("PUT", f"/notebooks/{UID}", start_request())[0] == 500
    assert NAME not in docker.containers


def test_start_failure_reports_the_start_error_when_removal_fails(launcher, docker, caplog):
    def broken_start(container_id):
        raise OSError("start failed")

    def broken_remove(container_id):
        raise TimeoutError("remove failed")

    docker.start = broken_start
    docker.remove = broken_remove
    req = StartRequest.parse(start_request(), now=time.time())
    with pytest.raises(OSError, match="start failed"):
        launcher.ensure(UID, req)
    assert "removing a notebook container failed: TimeoutError" in caplog.text


def test_a_404_other_than_a_missing_image_is_500(api, docker, caplog):
    def broken(name, body):
        raise DockerError(404, "POST /containers/create: 404", "network p_notebooks not found")

    docker.create = broken
    assert api.call("PUT", f"/notebooks/{UID}", start_request()) == (500, {"error": "internal"})
    assert "POST /containers/create: 404" in caplog.text
    assert "network p_notebooks not found" not in caplog.text


def test_concurrent_starts_respect_the_limit(api, launcher, docker):
    launcher.cfg = make_config(FIONE_NOTEBOOK_MAX_RUNNING="1")
    create = docker.create

    def slow_create(name, body):
        time.sleep(0.2)
        return create(name, body)

    docker.create = slow_create
    results = []

    def put(uid):
        results.append(api.call("PUT", f"/notebooks/{uid}", start_request()))

    threads = [threading.Thread(target=put, args=(uid,)) for uid in ("1", "2", "3")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    assert sorted(results, key=lambda r: r[0]) == [
        (200, {"state": "starting"}),
        (409, {"error": "limit"}),
        (409, {"error": "limit"}),
    ]
    assert len(docker.containers) == 1


def test_short_body_is_422(api, docker):
    raw = json.dumps(start_request()).encode()
    with socket.create_connection(("127.0.0.1", api.port), timeout=10) as sock:
        head = (
            f"PUT /notebooks/{UID} HTTP/1.1\r\nHost: x\r\n{SECRET_HEADER}: {SECRET}\r\n"
            f"Content-Length: {len(raw) + 10}\r\n\r\n"
        )
        sock.sendall(head.encode() + raw)
        sock.shutdown(socket.SHUT_WR)  # fewer bytes than announced, then the end
        response = b""
        while chunk := sock.recv(4096):
            response += chunk
    status_line, _, rest = response.partition(b"\r\n")
    assert status_line.split()[1] == b"422", response
    assert json.loads(rest.split(b"\r\n\r\n", 1)[1]) == {"error": "invalid"}
    assert docker.calls == []


def test_state_follows_health(api, docker):
    assert api.call("GET", f"/notebooks/{UID}") == (200, {"state": "absent"})
    docker.add(NAME, labels(PROJECT, UID), health="starting")
    assert api.call("GET", f"/notebooks/{UID}") == (200, {"state": "starting"})
    docker.containers[NAME]["State"]["Health"]["Status"] = "healthy"
    assert api.call("GET", f"/notebooks/{UID}") == (200, {"state": "running"})
    docker.containers[NAME]["State"]["Health"]["Status"] = "unhealthy"
    assert api.call("GET", f"/notebooks/{UID}") == (200, {"state": "starting"})
    docker.containers[NAME]["State"] = {"Status": "created"}
    assert api.call("GET", f"/notebooks/{UID}") == (200, {"state": "starting"})
    docker.containers[NAME]["State"] = {"Status": "exited"}
    assert api.call("GET", f"/notebooks/{UID}") == (200, {"state": "absent"})


def test_a_container_without_our_labels_is_not_ours(api, docker):
    docker.add(NAME, {"fione.notebook": "1", "fione.project": "other", "fione.uid": UID})
    assert api.call("GET", f"/notebooks/{UID}") == (200, {"state": "absent"})
    assert api.call("DELETE", f"/notebooks/{UID}") == (204, None)
    assert NAME in docker.containers


def test_delete_is_idempotent_and_keeps_the_volume(api, docker):
    assert api.call("PUT", f"/notebooks/{UID}", start_request())[0] == 200
    assert api.call("DELETE", f"/notebooks/{UID}") == (204, None)
    assert NAME not in docker.containers
    assert f"{PROJECT}-nb-home-{UID}" in docker.volumes
    assert api.call("DELETE", f"/notebooks/{UID}") == (204, None)
    assert api.call("GET", f"/notebooks/{UID}") == (200, {"state": "absent"})


VOLUME = f"{PROJECT}-nb-home-{UID}"


def test_purge_removes_the_container_and_the_volume(api, docker):
    assert api.call("PUT", f"/notebooks/{UID}", start_request())[0] == 200
    assert api.call("DELETE", f"/notebooks/{UID}?purge=1") == (204, None)
    assert NAME not in docker.containers and VOLUME not in docker.volumes
    removed = [c[0] for c in docker.calls if c[0] in ("remove", "remove_volume")]
    assert removed == ["remove", "remove_volume"]  # the container first
    assert api.call("DELETE", f"/notebooks/{UID}?purge=1") == (204, None)  # idempotent


def test_purge_leaves_a_volume_that_is_not_ours(api, docker):
    docker.volumes[VOLUME] = {"fione.project": PROJECT, "fione.uid": "8"}
    docker.volumes[f"{PROJECT}-nb-home-9"] = {"fione.project": "other", "fione.uid": "9"}
    assert api.call("DELETE", f"/notebooks/{UID}?purge=1") == (204, None)
    assert api.call("DELETE", "/notebooks/9?purge=1") == (204, None)
    assert VOLUME in docker.volumes and f"{PROJECT}-nb-home-9" in docker.volumes
    assert not [c for c in docker.calls if c[0] == "remove_volume"]


def test_purge_retries_a_volume_in_use(api, launcher, docker, monkeypatch):
    monkeypatch.setattr("fione_launcher.server._PURGE_WAIT", 0)
    docker.volumes[VOLUME] = {"fione.project": PROJECT, "fione.uid": UID}
    remove = docker.remove_volume
    answers = [DockerError(409, "DELETE /volumes: 409"), None]

    def busy_once(name):
        answer = answers.pop(0)
        if answer is not None:
            docker.calls.append(("remove_volume", name))
            raise answer
        remove(name)

    docker.remove_volume = busy_once
    assert api.call("DELETE", f"/notebooks/{UID}?purge=1") == (204, None)
    assert VOLUME not in docker.volumes


@pytest.mark.parametrize(
    "method,query",
    [
        ("DELETE", "purge=0"),
        ("DELETE", "purge=1&x=1"),
        ("DELETE", "purge"),
        ("DELETE", ""),
        ("DELETE", "PURGE=1"),
        ("GET", "purge=1"),
        ("PUT", "purge=1"),
    ],
)
def test_any_other_query_is_422(api, docker, method, query):
    docker.volumes[VOLUME] = {"fione.project": PROJECT, "fione.uid": UID}
    body = start_request() if method == "PUT" else None
    assert api.call(method, f"/notebooks/{UID}?{query}", body) == (422, {"error": "invalid"})
    assert docker.calls == [] and VOLUME in docker.volumes


def test_closed_launcher_refuses_to_start(api, launcher, docker):
    launcher.close()
    assert api.call("PUT", f"/notebooks/{UID}", start_request()) == (503, {"error": "closing"})
    assert not [c for c in docker.calls if c[0] == "create"]


def test_logs_hold_no_secrets(api, docker, caplog, capfd):
    caplog.set_level(logging.DEBUG)
    body = start_request(launch_key="c" * 64, cookie_secret="d" * 64, token="fione_" + "Z" * 40)
    assert api.call("PUT", f"/notebooks/{UID}", body)[0] == 200
    assert api.call("GET", f"/notebooks/{UID}")[0] == 200
    assert api.call("DELETE", f"/notebooks/{UID}")[0] == 204
    assert api.call("PUT", f"/notebooks/{UID}", {**body, "image": "x"})[0] == 422
    assert api.call("GET", f"/notebooks/{UID}", secret="w" * 40)[0] == 401
    out = capfd.readouterr()
    logged = caplog.text + out.out + out.err
    assert "PUT /notebooks/7" in caplog.text  # the access log is there
    for secret in ("c" * 64, "d" * 64, "Z" * 40, "s" * 40, "w" * 40):
        assert secret not in logged
