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


def test_an_unreachable_start_frees_the_slot_it_may_have_taken(conn, settings, editor):
    launcher = FakeLauncher()
    ensure = launcher.ensure

    def lost_answer(uid, body):
        ensure(uid, body)  # the container started, but the answer timed out
        raise LauncherError("unreachable")

    launcher.ensure = lost_answer
    with pytest.raises(LauncherError):
        service.start(conn, launcher, settings, KEY_SECRET, editor)
    assert launcher.calls[-1] == ("stop", editor.id) and editor.id not in launcher.states
    launcher.stop = lambda uid: (_ for _ in ()).throw(LauncherError("unreachable"))
    with pytest.raises(LauncherError) as raised:  # the start's error, not the stop's
        service.start(conn, launcher, settings, KEY_SECRET, editor)
    assert raised.value.code == "unreachable" and _session(conn, editor.id) is None


def test_start_checks_the_permission_again(conn, settings, editor):
    auth_service.set_notebook_permission(conn, editor.id, NotebookPermission.NONE)
    launcher = FakeLauncher()
    with pytest.raises(service.NotebookNotAllowed):
        service.start(conn, launcher, settings, KEY_SECRET, editor)
    assert launcher.bodies() == [] and _session(conn, editor.id) is None
    assert auth_service.list_tokens(conn, editor.id) == []


def test_a_stop_waits_for_a_start_in_progress(tmp_path, settings, editor):
    """The start holds the user's lock until its launcher call returns; a stop sent meanwhile
    runs after it, so it finds the session and ends it."""
    entered, release = threading.Event(), threading.Event()
    launcher = FakeLauncher()
    ensure = launcher.ensure

    def slow_ensure(uid, body):
        entered.set()
        assert release.wait(10)
        return ensure(uid, body)

    launcher.ensure = slow_ensure
    path = tmp_path / "fione.db"

    def run(action):
        with closing(db.connect(path)) as c:
            action(c)

    starter = threading.Thread(
        target=run, args=(lambda c: service.start(c, launcher, settings, KEY_SECRET, editor),)
    )
    stopper = threading.Thread(target=run, args=(lambda c: service.stop(c, launcher, editor.id),))
    starter.start()
    assert entered.wait(10)
    stopper.start()
    stopper.join(0.3)
    assert stopper.is_alive()  # waiting on the lock
    release.set()
    starter.join(10)
    stopper.join(10)
    assert [c[0] for c in launcher.calls] == ["status", "ensure", "stop"]
    with closing(db.connect(path)) as c:
        assert _session(c, editor.id) is None
        assert not _valid(c, launcher.bodies()[0]["token"])


def test_purge_removes_the_notebook_and_ends_the_session(conn, settings, editor):
    launcher = FakeLauncher()
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    token = launcher.bodies()[0]["token"]
    service.purge(conn, launcher, editor.id)
    assert launcher.calls[-1] == ("purge", editor.id)
    assert _session(conn, editor.id) is None and not _valid(conn, token)


def test_state_ends_a_session_whose_container_is_gone(conn, settings, editor):
    launcher = FakeLauncher()
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    token = launcher.bodies()[0]["token"]
    assert service.state(conn, launcher, editor) == "starting"
    del launcher.states[editor.id]  # culled
    assert service.state(conn, launcher, editor) == "absent"
    assert _session(conn, editor.id) is None and not _valid(conn, token)


def test_a_container_without_a_session_is_stopped_and_absent(conn, editor):
    # Nobody can sign in to it, and it may be one a revocation could not stop.
    launcher = FakeLauncher()
    launcher.states[editor.id] = "running"
    assert service.state(conn, launcher, editor) == "absent"
    assert launcher.calls == [("status", editor.id), ("stop", editor.id)]
    assert editor.id not in launcher.states and _pending(conn) == {}


def test_a_failed_stop_of_a_container_without_a_session_is_pending(conn, editor):
    launcher = FakeLauncher()
    launcher.states[editor.id] = "running"
    launcher.stop = _failing(launcher, "stop")
    with pytest.raises(LauncherError):
        service.state(conn, launcher, editor)
    assert _pending(conn) == {editor.id: 0}


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
    assert _pending(conn) == {editor.id: 0}


# --- pending stops ------------------------------------------------------------------------


def _pending(conn) -> dict[int, int]:
    rows = conn.execute("SELECT user_id, purge FROM notebook_pending_stops").fetchall()
    return {row["user_id"]: row["purge"] for row in rows}


def _failing(launcher, method):
    """``launcher.<method>`` that records the call, then fails."""

    def fail(uid):
        launcher.calls.append((method, uid))
        raise LauncherError("unreachable")

    return fail


@pytest.mark.parametrize("action,purge", [(service.stop, 0), (service.purge, 1)])
def test_a_failed_stop_or_purge_is_pending_and_retried(conn, settings, editor, action, purge):
    launcher = FakeLauncher()
    service.start(conn, launcher, settings, KEY_SECRET, editor)
    launcher.fail = LauncherError("unreachable")
    assert service.quietly(action, conn, launcher, editor.id) is False
    assert _pending(conn) == {editor.id: purge}
    service.retry_pending(conn, launcher)  # still failing: kept
    assert _pending(conn) == {editor.id: purge}
    launcher.fail = None
    launcher.calls.clear()
    service.retry_pending(conn, launcher)
    assert launcher.calls == [("purge" if purge else "stop", editor.id)]
    assert _pending(conn) == {} and editor.id not in launcher.states


@pytest.mark.parametrize("first,second", [("stop", "purge"), ("purge", "stop")])
def test_a_pending_purge_is_never_downgraded(conn, editor, first, second):
    launcher = FakeLauncher()
    launcher.fail = LauncherError("unreachable")
    for name in (first, second):
        assert not service.quietly(getattr(service, name), conn, launcher, editor.id)
    assert _pending(conn) == {editor.id: 1}
    launcher.fail = None
    launcher.calls.clear()
    service._remove_locked(conn, launcher, editor.id, purge=False)  # a stop does the purge
    assert launcher.calls == [("purge", editor.id)] and _pending(conn) == {}


def test_every_service_call_retries_pending_stops_first(conn, settings, editor):
    other = auth_service.create_user(conn, "other", "password-123", Role.EDITOR)
    down = FakeLauncher()
    down.fail = LauncherError("unreachable")
    launcher = FakeLauncher()
    for call in (
        lambda: service.state(conn, launcher, editor),
        lambda: service.start(conn, launcher, settings, KEY_SECRET, editor),
        lambda: service.stop(conn, launcher, editor.id),
        lambda: service.purge(conn, launcher, editor.id),
    ):
        assert not service.quietly(service.purge, conn, down, other.id)
        assert _pending(conn) == {other.id: 1}
        launcher.calls.clear()
        call()
        assert launcher.calls[0] == ("purge", other.id) and _pending(conn) == {}


def test_retrying_stops_at_the_first_failure(conn, editor, caplog):
    other = auth_service.create_user(conn, "other", "password-123", Role.EDITOR)
    launcher = FakeLauncher()
    launcher.fail = LauncherError("unreachable", "the launcher answered 500")
    for uid in (editor.id, other.id):
        service.quietly(service.stop, conn, launcher, uid)
    launcher.calls.clear()
    with caplog.at_level(logging.WARNING, logger="fione.notebooks.service"):
        service.retry_pending(conn, launcher)
    assert len(launcher.calls) == 1 and _pending(conn) == {editor.id: 0, other.id: 0}
    assert "unreachable" in caplog.text and "500" not in caplog.text


def test_a_row_that_keeps_failing_does_not_block_the_others(conn, editor):
    other = auth_service.create_user(conn, "other", "password-123", Role.EDITOR)
    launcher = FakeLauncher()
    launcher.fail = LauncherError("unreachable")
    for uid in (editor.id, other.id):
        service.quietly(service.stop, conn, launcher, uid)
    conn.execute("UPDATE notebook_pending_stops SET since = '2000-01-01 00:00:00'")
    conn.execute(  # the editor's row is the oldest, and it fails for its own reason
        "UPDATE notebook_pending_stops SET since = '1999-01-01 00:00:00' WHERE user_id = ?",
        (editor.id,),
    )
    launcher.fail = None
    stop = launcher.stop

    def stuck_for_editor(uid):
        if uid == editor.id:
            launcher.calls.append(("stop", uid))
            raise LauncherError("unreachable")
        stop(uid)

    launcher.stop = stuck_for_editor
    launcher.calls.clear()
    service.retry_pending(conn, launcher)  # fails on the editor's row: it goes to the back
    assert _pending(conn) == {editor.id: 0, other.id: 0}
    service.retry_pending(conn, launcher)
    assert _pending(conn) == {editor.id: 0}
    assert launcher.calls == [("stop", editor.id), ("stop", other.id), ("stop", editor.id)]


def test_a_start_is_refused_while_a_stop_is_pending(conn, settings, editor):
    # User ids are reused: a pending purge must not remove a new notebook's files later.
    launcher = FakeLauncher()
    launcher.fail = LauncherError("unreachable")
    service.quietly(service.purge, conn, launcher, editor.id)
    launcher.purge = _failing(launcher, "purge")
    launcher.fail = None
    with pytest.raises(LauncherError) as raised:
        service.start(conn, launcher, settings, KEY_SECRET, editor)
    assert raised.value.code == "unreachable" and launcher.bodies() == []
    assert _session(conn, editor.id) is None and _pending(conn) == {editor.id: 1}


def test_a_lost_start_answer_whose_stop_fails_leaves_the_stop_pending(conn, settings, editor):
    launcher = FakeLauncher()
    ensure = launcher.ensure

    def lost_answer(uid, body):
        ensure(uid, body)
        raise LauncherError("unreachable")

    launcher.ensure = lost_answer
    launcher.stop = _failing(launcher, "stop")
    with pytest.raises(LauncherError):
        service.start(conn, launcher, settings, KEY_SECRET, editor)
    assert _pending(conn) == {editor.id: 0}


def test_the_retrier_retries_in_its_own_thread_until_stopped(tmp_path, conn, editor):
    launcher = FakeLauncher()
    launcher.fail = LauncherError("unreachable")
    service.quietly(service.stop, conn, launcher, editor.id)
    launcher.fail = None
    retrier = service.PendingStopRetrier(tmp_path / "fione.db", launcher, interval=0.05)
    retrier.start()
    try:
        deadline = time.monotonic() + 10
        while _pending(conn):
            assert time.monotonic() < deadline, "the pending stop was not retried"
            time.sleep(0.02)
    finally:
        retrier.stop()
    assert ("stop", editor.id) in launcher.calls
    calls = len(launcher.calls)
    service.quietly(service.stop, conn, _down(), editor.id)
    time.sleep(0.2)
    assert len(launcher.calls) == calls and _pending(conn) == {editor.id: 0}  # stopped


def _down() -> FakeLauncher:
    launcher = FakeLauncher()
    launcher.fail = LauncherError("unreachable")
    return launcher


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
    assert f"{PROJECT}-nb-home-{editor.id}" in docker.volumes
    client.purge(editor.id)
    assert f"{PROJECT}-nb-home-{editor.id}" not in docker.volumes


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


def test_purge_asks_the_launcher_to_remove_the_files(stub):
    stub.answer = (204, {}, b"")
    assert HttpLauncher(stub.url, SECRET).purge(7) is None
    assert stub.seen[0][:2] == ("DELETE", "/notebooks/7?purge=1")


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
