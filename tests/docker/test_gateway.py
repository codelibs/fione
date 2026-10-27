"""The notebook gateway (docker/notebook-gateway.conf in the pinned nginx image of
docker/compose.yaml) against two stand-in upstreams: an echo server with the alias `fione` on
the `gateway` network and one with the alias `nb-7` on the internal `notebooks` network. Each
echo prints, and answers with, the request line and headers it received.

The relay (:8081) is not published, so its requests come from inside the `nb-7` container,
as a notebook's would. Requests are sent with http.client, which sends a path as it is (httpx
would resolve dot segments first, and the deny cases would test nothing).

Everything this module creates is labelled with its own project name and removed by it."""

import http.client
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.docker

ROOT = Path(__file__).resolve().parents[2]
PROJECT = f"fione-l9-{os.getpid()}"
LABEL = f"fione.test={PROJECT}"
GATEWAY = f"{PROJECT}-gateway"
FIONE = f"{PROJECT}-fione"
NB7 = f"{PROJECT}-nb7"
NET_GATEWAY = f"{PROJECT}-gateway"
NET_NOTEBOOKS = f"{PROJECT}-notebooks"
ECHO_IMAGE = "python:3.12.15-slim-trixie"
NGINX_IMAGE = yaml.safe_load((ROOT / "docker" / "compose.yaml").read_text())["services"][
    "notebook-gateway"
]["image"]

ECHO = """\
import http.server, json, sys

class Echo(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def handle_one(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        seen = json.dumps({"line": self.requestline, "headers": list(self.headers.items())})
        print(seen, flush=True)
        body = seen.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = handle_one

    def log_message(self, *args):
        pass

http.server.ThreadingHTTPServer(("", int(sys.argv[1])), Echo).serve_forever()
"""

# Runs in the nb-7 container: sends [method, path, headers] requests to the relay as they
# are and prints [[status, body], ...].
CLIENT = """\
import http.client, json, sys

out = []
for method, path, headers in json.loads(sys.argv[2]):
    conn = http.client.HTTPConnection(sys.argv[1], 8081, timeout=30)
    conn.request(method, path, headers=headers)
    response = conn.getresponse()
    out.append([response.status, response.read().decode("utf-8", "replace")])
    conn.close()
print(json.dumps(out))
"""


def _docker(*args: str, check: bool = True, timeout: float = 300) -> str:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check, timeout=timeout
    ).stdout


def _remove_all() -> None:
    """Remove what carries this module's label, and nothing else."""
    for container in _docker("ps", "-aq", "--filter", f"label={LABEL}", check=False).split():
        _docker("rm", "-f", container, check=False)
    for network in _docker("network", "ls", "-q", "--filter", f"label={LABEL}").split():
        _docker("network", "rm", network, check=False)


def _echo(name: str, network: str, alias: str, port: int) -> None:
    _docker(
        "run", "-d", "--name", name, "--label", LABEL, "--network", network,
        "--network-alias", alias, ECHO_IMAGE, "python", "-u", "-c", ECHO, str(port),
    )  # fmt: skip


@pytest.fixture(scope="module")
def gateway():
    try:
        _docker("network", "create", "--label", LABEL, NET_GATEWAY)
        _docker("network", "create", "--internal", "--label", LABEL, NET_NOTEBOOKS)
        _echo(FIONE, NET_GATEWAY, "fione", 8080)
        _echo(NB7, NET_NOTEBOOKS, "nb-7", 8888)
        conf = ROOT / "docker" / "notebook-gateway.conf"
        _docker(
            "create", "--name", GATEWAY, "--label", LABEL, "--network", NET_GATEWAY,
            "-p", "127.0.0.1::8080", "--read-only", "--tmpfs", "/tmp", "--cap-drop", "ALL",
            "-v", f"{conf}:/etc/nginx/conf.d/default.conf:ro", NGINX_IMAGE,
        )  # fmt: skip
        _docker("network", "connect", NET_NOTEBOOKS, GATEWAY)
        _docker("start", GATEWAY)
        port = int(_docker("port", GATEWAY, "8080").split()[0].rsplit(":", 1)[1])
        _wait_ready(port)
        yield port
    finally:
        _remove_all()


def _wait_ready(port: int) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if _public(port, "GET", "/user/7/")[0] == 200 and _relay("GET", "/")[0] == 404:
                return
        except (OSError, subprocess.CalledProcessError):
            pass
        time.sleep(0.5)
    raise AssertionError(_docker("logs", GATEWAY, check=False))


def _public(port: int, method: str, path: str, headers: dict | None = None):
    """(status, body) of a request to the public server, sent from the host."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        conn.request(method, path, headers=headers or {})
        response = conn.getresponse()
        return response.status, response.read().decode("utf-8", "replace")
    finally:
        conn.close()


def _relays(requests: list) -> list:
    """[(status, body)] of requests to the relay, sent from the nb-7 container."""
    out = _docker("exec", NB7, "python", "-c", CLIENT, GATEWAY, json.dumps(requests))
    return json.loads(out)


def _relay(method: str, path: str, headers: dict | None = None):
    return _relays([[method, path, headers or {}]])[0]


def _probe() -> str:
    return uuid.uuid4().hex


def _seen_by(container: str, probe: str) -> list[dict]:
    """The requests ``container``'s echo received that carry the header X-Probe: ``probe``."""
    seen = [json.loads(line) for line in _docker("logs", container).splitlines() if line]
    return [s for s in seen if ["X-Probe", probe] in s["headers"]]


def _headers(seen: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for name, value in seen["headers"]:
        out.setdefault(name.lower(), []).append(value)
    return out


BEARER = {"Authorization": "Bearer fione_test"}


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/tokens",
        "/api/v1/tokens/",
        "/api/v1/%74okens",
        "/API/V1/TOKENS",
        "/api/v1//users",
        "/api/v1/./auth/login",
        "/api/v1/projects/..%2F..%2Ftokens",
        "/api/v1/projects/%2e%2e/%2e%2e/users",
        # Dot segments that nginx resolves to /api/v1/: the raw path would reach Fione.
        "/api/v1/tokens/..",
        "/api/v1/users/%2e%2e",
        "/api/v1/%74okens/%2E%2E",
        "/api/v1/users%2F..",
    ],
)
def test_relay_denies(gateway, path):
    probe = _probe()
    status, _ = _relay("GET", path, {**BEARER, "X-Probe": probe})
    assert status in (403, 404)
    assert _seen_by(FIONE, probe) == []


def test_relay_requires_bearer(gateway):
    probes = [_probe() for _ in range(3)]
    results = _relays(
        [
            ["GET", "/api/v1/projects", {"X-Probe": probes[0]}],
            ["GET", "/api/v1/projects", {"Authorization": "Basic eDp5", "X-Probe": probes[1]}],
            ["GET", "/api/v1/projects", {"Authorization": "Bearer x", "X-Probe": probes[2]}],
        ]
    )
    assert [status for status, _ in results] == [401, 401, 200]
    assert _seen_by(FIONE, probes[0]) == [] and _seen_by(FIONE, probes[1]) == []
    (seen,) = _seen_by(FIONE, probes[2])
    assert seen["line"].startswith("GET /api/v1/projects HTTP/")
    assert _headers(seen)["authorization"] == ["Bearer x"]


def test_relay_passes_encoded_segments_as_sent(gateway):
    probe = _probe()
    path = "/api/v1/projects/1/datasets/2/columns/a%2Fb?x=%2E%2E"
    status, _ = _relay("GET", path, {**BEARER, "X-Probe": probe})
    assert status == 200
    (seen,) = _seen_by(FIONE, probe)
    assert seen["line"].startswith(f"GET {path} HTTP/")


def test_relay_overwrites_forwarding_headers(gateway):
    probe = _probe()
    headers = {
        **BEARER,
        "X-Probe": probe,
        "X-Forwarded-For": "1.2.3.4",
        "X-Forwarded-Host": "evil",
        "X-Forwarded-Proto": "https",
        "Cookie": "fione_session=S; a=1",
    }
    status, _ = _relay("GET", "/api/v1/projects", headers)
    assert status == 200
    (seen,) = _seen_by(FIONE, probe)
    received = _headers(seen)
    address = _docker(
        "inspect",
        "-f",
        f'{{{{(index .NetworkSettings.Networks "{NET_NOTEBOOKS}").IPAddress}}}}',
        NB7,
    ).strip()
    assert address and received["x-forwarded-for"] == [address]
    assert "x-forwarded-host" not in received
    assert "x-forwarded-proto" not in received
    assert "cookie" not in received


def test_relay_serves_nothing_else(gateway):
    results = _relays([["GET", path, BEARER] for path in ("/", "/login", "/api/docs")])
    assert [status for status, _ in results] == [404, 404, 404]


@pytest.mark.parametrize(
    ("cookie", "expected"),
    [
        ("a=1; fione_session=S; b=2", ["a=1; b=2"]),
        ("fione_session=S; a=1", ["a=1"]),
        ("a=1;fione_session=S", ["a=1"]),
        ("fione_session=S", None),
        ("my_fione_session=keep; a=1", ["my_fione_session=keep; a=1"]),
        # A second one (a planted duplicate with a narrower path): no cookies at all.
        ("a=1; fione_session=X; b=2; fione_session=S", None),
    ],
)
def test_public_strips_fione_session(gateway, cookie, expected):
    probe = _probe()
    status, _ = _public(gateway, "GET", "/user/7/lab", {"Cookie": cookie, "X-Probe": probe})
    assert status == 200
    (seen,) = _seen_by(NB7, probe)
    assert _headers(seen).get("cookie") == expected


def test_public_passes_the_browser_headers_unchanged(gateway):
    # Jupyter's sign-in requires Sec-Fetch-Site (same-site from Fione's page) and compares
    # Origin with Host.
    probe = _probe()
    headers = {
        "Host": "127.0.0.1:18888",
        "Origin": "http://127.0.0.1:18080",
        "Sec-Fetch-Site": "same-site",
        "X-Probe": probe,
    }
    status, _ = _public(gateway, "GET", "/user/7/login?launch=v1.x", headers)
    assert status == 200
    (seen,) = _seen_by(NB7, probe)
    received = _headers(seen)
    assert seen["line"] == "GET /user/7/login?launch=v1.x HTTP/1.1"
    assert received["host"] == ["127.0.0.1:18888"]
    assert received["origin"] == ["http://127.0.0.1:18080"]
    assert received["sec-fetch-site"] == ["same-site"]


@pytest.mark.parametrize(
    "path", ["/user/abc/", "/user/7x/", "/user/../", "/user/", "/user/7", "/", "/user/-1/"]
)
def test_public_only_proxies_digit_uids(gateway, path):
    probe = _probe()
    assert _public(gateway, "GET", path, {"X-Probe": probe})[0] == 404
    assert _seen_by(NB7, probe) == []


@pytest.mark.parametrize(
    "path", ["/user/7/lab/api/settings/x", "/user/7/lab/api/workspaces/default"]
)
def test_settings_and_workspaces_writes_are_refused(gateway, path):
    for method in ("PUT", "PATCH", "DELETE", "POST"):
        probe = _probe()
        assert _public(gateway, method, path, {"X-Probe": probe})[0] == 403, method
        assert _seen_by(NB7, probe) == []
    probe = _probe()
    assert _public(gateway, "GET", path, {"X-Probe": probe})[0] == 200
    assert len(_seen_by(NB7, probe)) == 1


@pytest.mark.parametrize(
    ("path", "status"),
    [
        ("/user/7/lab/api/%73ettings/x", 403),
        ("/user/7/lab/api/settings", 403),
        ("/user/7/lab/api/workspaces/", 403),
        # Out of the settings location after normalization, but Jupyter would see the raw path.
        ("/user/7/lab/api/settings/../../x", 404),
        ("/user/7/lab/api/settings/%2e%2e/%2E%2E/x", 404),
    ],
)
def test_settings_writes_cannot_be_disguised(gateway, path, status):
    probe = _probe()
    assert _public(gateway, "PUT", path, {"X-Probe": probe})[0] == status
    assert _seen_by(NB7, probe) == []


def test_websocket_upgrade_passes(gateway):
    probe = _probe()
    headers = {
        "Upgrade": "websocket",
        "Connection": "Upgrade",
        "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
        "Sec-WebSocket-Version": "13",
        "X-Probe": probe,
    }
    _public(gateway, "GET", "/user/7/api/kernels/k/channels", headers)
    (seen,) = _seen_by(NB7, probe)
    received = _headers(seen)
    assert received["upgrade"] == ["websocket"]
    assert received["connection"] == ["upgrade"]
    assert seen["line"].endswith("HTTP/1.1")


def test_logs_have_no_query_strings(gateway):
    # nb-7 answers; nb-8 does not exist, so nginx fails (502) and logs an error.
    assert _public(gateway, "GET", "/user/7/login?launch=SECRETVALUE")[0] == 200
    assert _public(gateway, "GET", "/user/8/login?launch=SECRETVALUE")[0] == 502
    assert _relay("GET", "/api/v1/projects?q=SECRETVALUE", BEARER)[0] == 200
    # The control: elsewhere such an error is logged with the request line.
    assert _public(gateway, "GET", "/user/8/lab?q=CONTROLVALUE")[0] == 502
    logs = subprocess.run(["docker", "logs", GATEWAY], capture_output=True, text=True, check=True)
    text = logs.stdout + logs.stderr
    assert "CONTROLVALUE" in text
    assert "SECRETVALUE" not in text
    assert '"GET /user/8/login" 502' in text
