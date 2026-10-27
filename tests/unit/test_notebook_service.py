"""Notebook sessions, launch tokens and the launcher client. The client is tried against the
real launcher server (on a fake Docker), so the start body is the one it accepts."""

import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from api_helpers import NOTEBOOK_SETTINGS, FakeLauncher, make_settings
from fione import db
from fione.auth import service as auth_service
from fione.auth.roles import NotebookPermission, Role
from fione.auth.tokens import TokenScope
from fione.notebooks import service
from fione.notebooks.launch import (
    LAUNCH_TOKEN_TTL_SECS,
    launch_key,
    sign_launch_token,
)
from fione.notebooks.launcher import HttpLauncher, LauncherError
from fione_launcher.server import Launcher, make_server
from launcher_helpers import NETWORK, PROJECT, SECRET, FakeDocker, labels, make_config

KEY_SECRET = b"k" * 32


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path / "data", **NOTEBOOK_SETTINGS)


@pytest.fixture
def conn(tmp_path):
    with closing(db.connect(tmp_path / "fione.db")) as c:
        db.migrate(c)
        yield c


@pytest.fixture
def editor(conn):
    user = auth_service.create_user(conn, "ed", "password-123", Role.EDITOR)
    auth_service.set_notebook_permission(conn, user.id, NotebookPermission.RUN)
    return user


def _session(conn, user_id):
    return conn.execute("SELECT * FROM notebook_sessions WHERE user_id = ?", (user_id,)).fetchone()


def _valid(conn, token: str) -> bool:
    return auth_service.token_identity(conn, token) is not None


def _claims(token: str) -> dict:
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


# --- launch tokens ------------------------------------------------------------------------


def test_launch_key_is_derived_per_secret_user_and_nonce():
    key = launch_key(KEY_SECRET, 7, "n1")
    expected = hmac.new(KEY_SECRET, b"fione-notebook-launch-v1:7:n1", hashlib.sha256).digest()
    assert key == expected and len(key) == 32
    others = {launch_key(KEY_SECRET, 8, "n1"), launch_key(KEY_SECRET, 7, "n2")}
    others.add(launch_key(b"j" * 32, 7, "n1"))
    assert key not in others and len(others) == 3


def test_launch_token_claims_and_signature(editor):
    key = launch_key(KEY_SECRET, editor.id, "n")
    token = sign_launch_token(key, user=editor, now=1000.5)
    version, payload, signature = token.split(".")
    assert version == "v1" and "=" not in payload + signature
    mac = hmac.new(key, f"v1.{payload}".encode(), hashlib.sha256).digest()
    assert base64.urlsafe_b64encode(mac).rstrip(b"=").decode() == signature
    claims = _claims(token)
    assert {k: claims[k] for k in ("sub", "name", "role", "exp")} == {
        "sub": str(editor.id),
        "name": "ed",
        "role": "editor",
        "exp": 1000 + LAUNCH_TOKEN_TTL_SECS,
    }
    assert len(claims["jti"]) >= 16
    assert _claims(sign_launch_token(key, user=editor))["jti"] != claims["jti"]


# --- sessions -----------------------------------------------------------------------------


def test_start_makes_a_session_a_notebook_token_and_the_container(conn, settings, editor):
    launcher = FakeLauncher()
    before = int(time.time())
    assert service.start(conn, launcher, settings, KEY_SECRET, editor) == "starting"
    (body,) = launcher.bodies()
    assert set(body) == {"launch_key", "cookie_secret", "token", "fione_origin", "expires_at"}
    row = _session(conn, editor.id)
    assert body["launch_key"] == launch_key(KEY_SECRET, editor.id, row["nonce"]).hex()
    assert len(bytes.fromhex(body["cookie_secret"])) == 32
    assert body["fione_origin"] == "http://127.0.0.1:8080"
    assert before + 43200 <= body["expires_at"] <= int(time.time()) + 43200
    user, record = auth_service.token_identity(conn, body["token"])
    assert user.id == editor.id and record.scope == TokenScope.NOTEBOOK
    assert record.id == row["token_id"] and record.expires_at == row["expires_at"]
    assert time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(body["expires_at"])) == row["expires_at"]


def test_start_twice_keeps_the_running_session(conn, settings, editor):
    launcher = FakeLauncher()
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    launcher.states[editor.id] = "running"
    assert service.start(conn, launcher, settings, KEY_SECRET, editor) == "running"
    assert len(launcher.bodies()) == 1
    assert _valid(conn, launcher.bodies()[0]["token"])


def test_start_replaces_a_container_without_a_session(conn, settings, editor):
    launcher = FakeLauncher()
    launcher.states[editor.id] = "running"  # left from a failed start
    assert service.start(conn, launcher, settings, KEY_SECRET, editor) == "starting"
    assert [c[0] for c in launcher.calls] == ["status", "ensure", "stop", "ensure"]
    first, second = launcher.bodies()
    assert first == second and _valid(conn, second["token"])


def test_a_new_start_revokes_the_ended_sessions_token(conn, settings, editor):
    launcher = FakeLauncher()
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    # The session expired, its container still runs: the start replaces both.
    conn.execute("UPDATE notebook_sessions SET expires_at = '2000-01-01 00:00:00'")
    launcher.states[editor.id] = "running"
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    old, new = launcher.bodies()[0], launcher.bodies()[-1]
    assert not _valid(conn, old["token"]) and _valid(conn, new["token"])
    assert old["launch_key"] != new["launch_key"]


@pytest.mark.parametrize("code", ["limit", "image_missing", "unreachable", "refused", "exists"])
def test_a_failed_start_ends_the_session(conn, settings, editor, code):
    launcher = FakeLauncher()
    if code == "exists":
        launcher.states[editor.id] = "starting"  # and stays: the retry fails too
        launcher.stop = lambda uid: launcher.calls.append(("stop", uid))
    else:
        ensure = launcher.ensure

        def failing(uid, body):
            ensure(uid, body)
            raise LauncherError(code)

        launcher.ensure = failing
    with pytest.raises(LauncherError) as raised:
        service.start(conn, launcher, settings, KEY_SECRET, editor)
    assert raised.value.code == code
    assert _session(conn, editor.id) is None
    assert not _valid(conn, launcher.bodies()[-1]["token"])


def test_state_ends_a_session_whose_container_is_gone(conn, settings, editor):
    launcher = FakeLauncher()
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    token = launcher.bodies()[0]["token"]
    assert service.state(conn, launcher, editor) == "starting"
    del launcher.states[editor.id]  # culled
    assert service.state(conn, launcher, editor) == "absent"
    assert _session(conn, editor.id) is None and not _valid(conn, token)


def test_a_container_without_a_session_is_absent(conn, editor):
    launcher = FakeLauncher()
    launcher.states[editor.id] = "running"
    assert service.state(conn, launcher, editor) == "absent"


def test_state_raises_launcher_errors(conn, editor):
    launcher = FakeLauncher()
    launcher.fail = LauncherError("unreachable")
    with pytest.raises(LauncherError):
        service.state(conn, launcher, editor)


def test_stop_revokes_the_token_even_when_the_launcher_fails(conn, settings, editor):
    launcher = FakeLauncher()
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    token = launcher.bodies()[0]["token"]
    launcher.fail = LauncherError("unreachable")
    with pytest.raises(LauncherError):
        service.stop(conn, launcher, editor.id)
    assert _session(conn, editor.id) is None and not _valid(conn, token)


def test_stop_unless_allowed(conn, settings, editor):
    launcher = FakeLauncher()
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    service.stop_unless_allowed(conn, launcher, editor.id)
    assert ("stop", editor.id) not in launcher.calls
    auth_service.set_notebook_permission(conn, editor.id, NotebookPermission.NONE)
    service.stop_unless_allowed(conn, launcher, editor.id)
    assert ("stop", editor.id) in launcher.calls
    assert not _valid(conn, launcher.bodies()[0]["token"])


def test_quietly_logs_the_code_and_does_nothing_when_disabled(conn, settings, editor, caplog):
    launcher = FakeLauncher()
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    token = launcher.bodies()[0]["token"]
    launcher.fail = LauncherError("unreachable", "the launcher answered 500")
    with caplog.at_level(logging.WARNING, logger="fione.notebooks.service"):
        service.quietly(service.stop, conn, launcher, editor.id)
    assert "unreachable" in caplog.text and not _valid(conn, token)
    service.quietly(service.stop, conn, None, editor.id)  # notebooks off: nothing to call


def test_launch_url_needs_a_live_session(conn, settings, editor):
    launcher = FakeLauncher()
    with pytest.raises(service.NotebookNotRunning):
        service.launch_url(conn, settings, KEY_SECRET, editor)
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    url = service.launch_url(conn, settings, KEY_SECRET, editor)
    prefix = f"http://127.0.0.1:8888/user/{editor.id}/login?launch=v1."
    assert url.startswith(prefix)
    assert url.endswith(f"&next=/user/{editor.id}/lab")
    conn.execute("UPDATE notebook_sessions SET expires_at = '2000-01-01 00:00:00'")
    with pytest.raises(service.NotebookNotRunning):
        service.launch_url(conn, settings, KEY_SECRET, editor)


def test_deleting_the_user_deletes_the_session(conn, settings, editor):
    service.start(conn, FakeLauncher(), settings, KEY_SECRET, editor)
    auth_service.delete_user(conn, editor.id)
    assert conn.execute("SELECT COUNT(*) FROM notebook_sessions").fetchone()[0] == 0


# --- the launcher client ------------------------------------------------------------------


@pytest.fixture
def docker():
    return FakeDocker()


@pytest.fixture
def launcher_url(docker):
    launcher = Launcher(make_config(), docker, project=PROJECT, network=NETWORK)
    server = make_server(launcher, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


def test_the_launcher_accepts_the_start_body(conn, settings, editor, docker, launcher_url):
    client = HttpLauncher(launcher_url, SECRET)
    assert service.start(conn, client, settings, KEY_SECRET, editor) == "starting"
    (create,) = [c for c in docker.calls if c[0] == "create"]
    env = create[2]["Env"]
    nonce = _session(conn, editor.id)["nonce"]
    assert f"FIONE_NB_KEY={launch_key(KEY_SECRET, editor.id, nonce).hex()}" in env
    assert f"FIONE_NB_OWNER={editor.id}" in env
    assert client.status(editor.id) == "starting"
    client.stop(editor.id)
    assert client.status(editor.id) == "absent"


def test_launcher_error_codes(docker, launcher_url):
    body = {
        "launch_key": "a" * 64,
        "cookie_secret": "b" * 64,
        "token": "fione_" + "T" * 40,
        "fione_origin": "http://127.0.0.1:8080",
        "expires_at": int(time.time()) + 3600,
    }
    client = HttpLauncher(launcher_url, SECRET)

    def code(call) -> str:
        with pytest.raises(LauncherError) as raised:
            call()
        return raised.value.code

    assert code(lambda: HttpLauncher(launcher_url, "w" * 40).status(7)) == "refused"  # 401
    assert code(lambda: client.ensure(7, body | {"fione_origin": "x"})) == "refused"  # 422
    client.ensure(7, body)
    assert code(lambda: client.ensure(7, body)) == "exists"
    for uid in ("1", "2", "3"):  # four running: the limit
        docker.add(f"{PROJECT}-nb-{uid}", labels(PROJECT, uid))
    assert code(lambda: client.ensure(8, body)) == "limit"
    client.stop(7)
    docker.images.clear()
    assert code(lambda: client.ensure(8, body)) == "image_missing"

    def broken(name, body):
        raise OSError("socket gone")

    docker.create = broken
    assert code(lambda: client.ensure(9, body)) == "unreachable"  # 500


class _Stub(BaseHTTPRequestHandler):
    """Answers every request with the server's ``answer`` (status, headers, body)."""

    def _answer(self):
        self.server.seen.append((self.command, self.path, dict(self.headers)))
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        status, headers, body = self.server.answer
        if self.server.delay:
            time.sleep(self.server.delay)
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_PUT = do_DELETE = _answer

    def log_message(self, format, *args):  # noqa: A002
        pass


@pytest.fixture
def stub():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
    server.daemon_threads = True
    server.seen, server.answer, server.delay = [], (200, {}, b"{}"), 0
    thread = threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True)
    thread.start()
    server.url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


@pytest.mark.parametrize(
    "answer,code",
    [
        ((409, {}, b'{"error": "limit"}'), "limit"),
        ((409, {}, b'{"error": "other"}'), "refused"),
        ((503, {}, b'{"error": "image_missing"}'), "image_missing"),
        ((503, {}, b'{"error": "closing"}'), "unreachable"),
        ((502, {}, b"<html>bad gateway</html>"), "unreachable"),
        ((422, {}, b'{"error": "invalid", "detail": "SECRET-TEXT"}'), "refused"),
        ((404, {}, b"SECRET-TEXT"), "refused"),
        ((200, {}, b'{"state": "SECRET-TEXT"}'), "unreachable"),
        ((200, {}, b"SECRET-TEXT"), "unreachable"),
        ((200, {}, b"[]"), "unreachable"),
    ],
)
def test_launcher_answers_map_to_codes_without_their_text(stub, answer, code):
    stub.answer = answer
    with pytest.raises(LauncherError) as raised:
        HttpLauncher(stub.url, SECRET).status(7)
    assert raised.value.code == code
    assert "SECRET-TEXT" not in str(raised.value) and raised.value.__cause__ is None


def test_launcher_requests_carry_the_secret_and_json(stub):
    stub.answer = (200, {}, b'{"state": "starting"}')
    assert HttpLauncher(stub.url + "/", SECRET).ensure(7, {"a": 1}) == "starting"
    method, path, headers = stub.seen[0]
    assert (method, path) == ("PUT", "/notebooks/7")
    assert headers["X-Fione-Launcher-Secret"] == SECRET
    assert headers["Content-Type"] == "application/json"


def test_launcher_redirects_are_not_followed(stub):
    stub.answer = (302, {"Location": stub.url + "/elsewhere"}, b"")
    with pytest.raises(LauncherError) as raised:
        HttpLauncher(stub.url, SECRET).status(7)
    assert raised.value.code == "refused"
    assert [path for _, path, _ in stub.seen] == ["/notebooks/7"]


def test_launcher_ignores_proxies_from_the_environment(stub, monkeypatch):
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    stub.answer = (200, {}, b'{"state": "running"}')
    assert HttpLauncher(stub.url, SECRET).status(7) == "running"


def test_launcher_unreachable_and_timeout(stub):
    with ThreadingHTTPServer(("127.0.0.1", 0), _Stub) as closed:
        port = closed.server_address[1]
    with pytest.raises(LauncherError) as raised:
        HttpLauncher(f"http://127.0.0.1:{port}", SECRET).status(7)
    assert raised.value.code == "unreachable"
    stub.delay = 1.0
    with pytest.raises(LauncherError) as raised:
        HttpLauncher(stub.url, SECRET, timeout=0.2).status(7)
    assert raised.value.code == "unreachable"
