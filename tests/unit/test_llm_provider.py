"""The LLM provider's status: which URLs are local, the monitor that checks an Ollama server
and pulls its model or a Claude key, the consent a remote host needs, and the context the
server really gives."""

import json
import logging
import sqlite3
import time
from contextlib import closing

import httpx
import pytest

from api_helpers import make_settings
from fake_llm import FakeLlm
from fione import db
from fione.assistant import provider, store
from fione.assistant.provider import (
    OLLAMA_DEFAULT_CONTEXT,
    LlmMonitor,
    LlmStatus,
    is_local_url,
    native_root,
)
from fione.auth import service as auth
from fione.auth.roles import Role


@pytest.fixture
def fake_llm():
    started = []

    def factory(*args, **kwargs):
        fake = FakeLlm(*args, **kwargs).start()
        started.append(fake)
        return fake

    yield factory
    for fake in started:
        fake.stop()


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "fione.db"
    with closing(db.connect(path)) as conn:
        db.migrate(conn)
    return path


@pytest.fixture
def monitors(tmp_path, db_path):
    made = []

    def factory(url, provider="ollama", recheck_secs=0.05, http=None, **settings):
        values = {"llm_base_url": url, "llm_provider": provider, **settings}
        monitor = LlmMonitor(
            make_settings(tmp_path, **values), db_path, http=http, recheck_secs=recheck_secs
        )
        made.append(monitor)
        return monitor

    yield factory
    for monitor in made:
        monitor.stop()


def consent(db_path, url, provider="claude"):
    with closing(db.connect(db_path)) as conn:
        admin = auth.create_user(conn, "consenter", "password-123", Role.ADMIN)
        store.record_consent(conn, admin, provider=provider, model="m", base_url=url)


def wait_for(monitor, state, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        status = monitor.snapshot()
        if status.state == state:
            return status
        time.sleep(0.01)
    raise AssertionError(f"still {monitor.snapshot()} after {timeout} s, wanted {state}")


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:11434/v1",
        "http://127.0.0.1/v1",
        "http://[::1]:1/v1",
        "http://ollama:11434/v1",
        "http://fake-llm:8000/v1",
        "http://host.docker.internal:11434/v1",
        "http://LocalHost./v1",
        "http://ollama.localhost/v1",
        "http://127.1.2.3/v1",
    ],
)
def test_is_local_url(url):
    assert is_local_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "http://192.168.1.5/v1",
        "http://10.0.0.2/v1",
        "https://api.example.com/v1",
        "http://localhost.example.com/v1",
        "http://3232235781/v1",  # 192.168.1.5 written as one number
        "http://0xc0a80105/v1",
        "http://[2001:db8::1]/v1",
        "http://host.docker.internal.example.com/v1",
        "",
        "not a url",
    ],
)
def test_is_remote_url(url):
    assert is_local_url(url) is False


def test_native_root():
    assert native_root("http://h:11434/v1") == "http://h:11434"
    assert native_root("http://h:11434/v1/") == "http://h:11434"
    assert native_root("http://h/proxy/v1") == "http://h/proxy"
    assert native_root("http://h:11434") == "http://h:11434"


def test_claude_is_ready_when_the_key_is_accepted(fake_llm, monitors, db_path):
    fake = fake_llm(api_key="sk-test-0123456789")
    consent(db_path, fake.origin)
    monitor = monitors(fake.origin, "claude", llm_api_key="sk-test-0123456789", llm_model="m")
    assert monitor.snapshot().state == "checking"
    monitor.start()
    status = wait_for(monitor, "ready")
    assert (status.model, status.local, status.error_code) == ("m", False, None)
    assert status.host == f"127.0.0.1:{fake.port}"
    assert fake.paths[0] == "GET /v1/models/m"  # no tokens: nothing is asked of the model
    assert "POST /v1/messages" not in fake.paths
    assert monitor.pull_now() is False
    assert monitor.effective_context() == 200000  # the claude default, never probed
    assert "GET /api/ps" not in fake.paths


def test_claude_401_is_unauthorized(fake_llm, monitors, db_path):
    fake = fake_llm(api_key="sk-right-0123456789")
    consent(db_path, fake.origin)
    monitor = monitors(fake.origin, "claude", llm_api_key="sk-wrong-0123456789")
    monitor.start()
    status = wait_for(monitor, "error")
    assert status.error_code == "unauthorized"
    assert "sk-wrong-0123456789" not in repr(status)
    assert monitor._thread.is_alive()


def test_claude_model_the_key_cannot_use_is_model_not_found(fake_llm, monitors, db_path):
    fake = fake_llm(api_key="sk-test-0123456789")
    fake.claude_models = ["claude-other"]
    consent(db_path, fake.origin)
    monitor = monitors(fake.origin, "claude", llm_api_key="sk-test-0123456789", llm_model="a/b?c")
    monitor.start()
    assert wait_for(monitor, "error").error_code == "model_not_found"
    assert fake.paths[0] == "GET /v1/models/a%2Fb%3Fc"
    fake.claude_models.append("a/b?c")
    wait_for(monitor, "ready")


def test_claude_404_from_a_gateway_is_probe_failed(fake_llm, monitors, db_path):
    # The fake has no route under /gateway: a 404 whose body is not Anthropic's.
    fake = fake_llm(api_key="sk-test-0123456789")
    consent(db_path, fake.origin)
    monitor = monitors(f"{fake.origin}/gateway", "claude", llm_api_key="sk-test-0123456789")
    monitor.start()
    assert wait_for(monitor, "error").error_code == "probe_failed"


@pytest.mark.parametrize("kind", ["rate_limit_error", "overloaded_error"])
def test_claude_rate_limit_or_overload_on_the_probe_is_probe_failed(
    fake_llm, monitors, db_path, kind
):
    # as any other error status of the probe: the System page says the server answered
    # with an error, and the assistant waits for the next check
    fake = fake_llm(api_key="sk-test-0123456789")
    fake.claude_model_error = kind
    consent(db_path, fake.origin)
    monitor = monitors(fake.origin, "claude", llm_api_key="sk-test-0123456789")
    monitor.start()
    assert wait_for(monitor, "error").error_code == "probe_failed"


def test_ollama_404_is_not_model_not_found(fake_llm, monitors):
    fake = fake_llm()
    monitor = monitors(f"{fake.origin}/wrong/v1")
    monitor.start()
    assert wait_for(monitor, "error").error_code == "probe_failed"


def test_claude_unreachable(fake_llm, monitors, db_path):
    fake = fake_llm()
    fake.stop()
    consent(db_path, fake.origin)
    monitor = monitors(fake.origin, "claude", llm_api_key="sk-test-0123456789")
    monitor.start()
    assert wait_for(monitor, "unreachable").error_code is None


def test_claude_rechecks_the_key_and_recovers(fake_llm, monitors, db_path):
    fake = fake_llm(api_key="sk-right-0123456789")
    consent(db_path, fake.origin)
    monitor = monitors(fake.origin, "claude", llm_api_key="sk-wrong-0123456789")
    monitor.start()
    wait_for(monitor, "error")
    fake.api_key = "sk-wrong-0123456789"  # the key is fixed on the server's side
    wait_for(monitor, "ready")


@pytest.mark.parametrize("url", ["http://gateway:8080", "http://localhost:8080"])
def test_claude_on_a_local_address_needs_consent(monitors, db_path, url):
    monitor = monitors(url, "claude", llm_api_key="sk-test-0123456789")
    status = monitor.snapshot()
    assert (status.state, status.local) == ("consent_required", False)
    consent(db_path, url)
    assert monitor.snapshot().state == "checking"


def test_a_present_model_is_ready(fake_llm, monitors):
    monitor = monitors(fake_llm().url)
    assert monitor.snapshot().state == "checking"
    monitor.start()
    status = wait_for(monitor, "ready")
    assert (status.model, status.error_code) == ("gemma4:12b-mlx", None)


def test_an_untagged_model_matches_latest(fake_llm, monitors):
    monitor = monitors(fake_llm(models=["tiny:latest"]).url, llm_model="tiny")
    monitor.start()
    wait_for(monitor, "ready")
    other = monitors(fake_llm(models=["tiny:1b"]).url, llm_model="tiny", llm_auto_pull=False)
    other.start()
    wait_for(other, "missing")


def test_missing_model_is_pulled_with_progress(fake_llm, monitors):
    fake = fake_llm(models=[], pull_steps=3, pull_delay=0.2)
    monitor = monitors(fake.url, llm_auto_pull=True)
    seen = []
    monitor.start()
    end = time.monotonic() + 10
    while monitor.snapshot().state != "ready" and time.monotonic() < end:
        seen.append(monitor.snapshot())
        time.sleep(0.02)
    assert monitor.snapshot().state == "ready"
    assert {s.state for s in seen} <= {"checking", "missing", "pulling"}
    assert "pulling" in {s.state for s in seen}
    assert any(s.completed and s.total and 0 < s.completed < s.total for s in seen)
    assert "POST /api/pull" in fake.paths
    assert fake.models == ["gemma4:12b-mlx"]


def test_no_auto_pull_leaves_missing(fake_llm, monitors):
    fake = fake_llm(models=[])
    monitor = monitors(fake.url)  # the default: an administrator pulls on the system page
    monitor.start()
    wait_for(monitor, "missing")
    time.sleep(0.3)
    assert monitor.snapshot().state == "missing"
    assert "POST /api/pull" not in fake.paths


def test_unreachable_then_recovers(fake_llm, monitors):
    gone = fake_llm()
    port = gone.port
    gone.stop()
    monitor = monitors(f"http://127.0.0.1:{port}/v1")
    monitor.start()
    wait_for(monitor, "unreachable")
    fake_llm(port=port)
    wait_for(monitor, "ready")


def test_pull_error_in_the_log_hides_the_key(fake_llm, monitors, caplog):
    key = "sk-test-0123456789"
    fake = fake_llm(models=[], pull_error="x" * 180 + key)
    monitor = monitors(fake.url, llm_auto_pull=True, llm_api_key=key)
    with caplog.at_level(logging.WARNING, logger="fione.assistant"):
        monitor.start()
        wait_for(monitor, "error")
    assert key[:6] not in caplog.text and "***" in caplog.text


def test_pull_error_is_a_code_not_text(fake_llm, monitors, caplog):
    fake = fake_llm(models=[], pull_error="pull model manifest: file does not exist\nSECRET-DETAIL")
    monitor = monitors(fake.url, llm_auto_pull=True)
    with caplog.at_level(logging.INFO, logger="fione.assistant"):
        monitor.start()
        status = wait_for(monitor, "error")
    assert status.error_code == "pull_failed"
    assert "SECRET-DETAIL" not in repr(status)
    assert "file does not exist" in caplog.text and "\n" not in caplog.records[-1].getMessage()
    time.sleep(0.3)  # a failed pull is not retried on its own
    assert monitor.snapshot().state == "error"
    assert fake.paths.count("POST /api/pull") == 1
    fake.pull_error = None
    assert monitor.pull_now() is True  # the administrator asks again
    wait_for(monitor, "ready")


def test_pull_now_is_single_flight(fake_llm, monitors):
    fake = fake_llm(models=[], pull_steps=3, pull_delay=0.3)
    monitor = monitors(fake.url, llm_auto_pull=False)
    monitor.start()
    wait_for(monitor, "missing")
    assert monitor.pull_now() is True
    assert monitor.pull_now() is False
    wait_for(monitor, "pulling")
    assert monitor.pull_now() is False
    wait_for(monitor, "ready")
    assert fake.paths.count("POST /api/pull") == 1


def test_the_api_key_is_sent_but_never_logged(fake_llm, monitors, caplog):
    fake = fake_llm(models=[])
    monitor = monitors(fake.url, llm_api_key="sk-secret-key-123", llm_auto_pull=True)
    with caplog.at_level(logging.DEBUG):
        monitor.start()
        wait_for(monitor, "ready")
    assert "sk-secret-key-123" not in caplog.text
    assert "sk-secret-key-123" not in repr(monitor.snapshot())


def test_effective_context(fake_llm, monitors):
    monitor = monitors(fake_llm().url)
    assert monitor.effective_context() == OLLAMA_DEFAULT_CONTEXT == 4096
    assert monitor.snapshot().server_context is None

    from fione.assistant.client import OllamaClient

    fake = fake_llm(context_length=8192)
    monitor = monitors(fake.url)
    monitor.refresh_context()  # nothing loaded yet: unchanged
    assert monitor.effective_context() == 4096
    deadline = time.monotonic() + 5
    OllamaClient(fake.url, "gemma4:12b-mlx").complete(
        [{"role": "user", "content": "hi"}], [], deadline=deadline
    )
    monitor.refresh_context()
    assert monitor.effective_context() == 8192
    assert monitor.snapshot().server_context == 8192

    big = fake_llm(context_length=32768)
    monitor = monitors(big.url)
    OllamaClient(big.url, "gemma4:12b-mlx").complete(
        [{"role": "user", "content": "hi"}], [], deadline=deadline
    )
    monitor.refresh_context()
    assert monitor.effective_context() == 16384  # the setting is the smaller one

    big.stop()
    monitor.refresh_context()  # a failure keeps the old value
    assert monitor.snapshot().server_context == 32768


REMOTE = "https://llm.example.com/v1"


def an_ollama_that_has_the_model():
    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma4:12b-mlx"}]})
        return httpx.Response(200, json={"models": []})

    return httpx.Client(transport=httpx.MockTransport(answer))


def test_remote_host_without_consent_is_consent_required(monitors):
    monitor = monitors(REMOTE)
    status = monitor.snapshot()
    assert status.state == "consent_required"
    assert (status.local, status.host, status.model) == (False, "llm.example.com", "gemma4:12b-mlx")


def test_consent_makes_it_ready_without_restart(monitors, db_path):
    monitor = monitors(REMOTE, http=an_ollama_that_has_the_model())
    monitor.start()
    end = time.monotonic() + 10
    while monitor._current().state != "ready" and time.monotonic() < end:
        time.sleep(0.01)
    assert monitor._current().state == "ready"  # the server answers, but nobody has consented
    assert monitor.snapshot().state == "consent_required"
    with closing(db.connect(db_path)) as conn:
        admin = auth.create_user(conn, "boss", "password-123", Role.ADMIN)
        store.record_consent(conn, admin, provider="ollama", model="m", base_url=REMOTE)
    wait_for(monitor, "ready")


def test_consent_required_hides_what_the_last_check_found(monitors):
    monitor = monitors(REMOTE)
    monitor._update(state="error", error_code="probe_failed", completed=1, total=2)
    status = monitor.snapshot()
    assert (status.state, status.error_code, status.completed, status.total) == (
        "consent_required", None, None, None
    )  # fmt: skip


def test_a_locked_database_counts_as_no_consent(monitors, db_path, monkeypatch, caplog):
    consent(db_path, REMOTE, "ollama")
    monitor = monitors(REMOTE)
    monitor._update(state="ready")

    def locked(conn, base_url, *, provider):
        raise sqlite3.OperationalError("database is locked")

    with monkeypatch.context() as patched:
        patched.setattr(provider, "has_consent", locked)
        with caplog.at_level(logging.WARNING, logger="fione.assistant"):
            assert monitor.snapshot().state == "consent_required"
        assert "consent" in caplog.text
    assert monitor.snapshot().state == "ready"  # once the database can be read again


def test_a_found_consent_is_not_read_again(monitors, db_path, monkeypatch):
    monitor = monitors(REMOTE)
    monitor._update(state="ready")
    assert monitor.snapshot().state == "consent_required"
    consent(db_path, REMOTE, "ollama")
    assert monitor.snapshot().state == "ready"

    def unread(conn, base_url, *, provider):
        raise AssertionError("the consent was read again")

    monkeypatch.setattr(provider, "has_consent", unread)
    assert monitor.snapshot().state == "ready"


def test_a_broken_database_counts_as_no_consent(monitors, db_path, monkeypatch, caplog):
    monitor = monitors(REMOTE)
    monitor._update(state="ready")

    def broken(conn, base_url, *, provider):
        raise sqlite3.DatabaseError("file is not a database")

    monkeypatch.setattr(provider, "has_consent", broken)
    with caplog.at_level(logging.WARNING, logger="fione.assistant"):
        assert monitor.snapshot().state == "consent_required"
    assert "the consent for llm.example.com could not be read" in caplog.text


def test_consent_covers_the_host_not_another(monitors, db_path):
    with closing(db.connect(db_path)) as conn:
        admin = auth.create_user(conn, "boss", "password-123", Role.ADMIN)
        store.record_consent(conn, admin, provider="ollama", model="m", base_url=REMOTE)
    assert monitors("https://llm.example.com:8443/v1").snapshot().state == "consent_required"


def test_local_host_never_needs_consent(fake_llm, tmp_path):
    never = tmp_path / "unused" / "fione.db"  # a read of it would create the file
    settings = make_settings(tmp_path, llm_base_url=fake_llm().url, llm_provider="ollama")
    monitor = LlmMonitor(settings, never, recheck_secs=0.05)
    try:
        monitor.start()
        wait_for(monitor, "ready")
        assert monitor.snapshot().state == "ready"
    finally:
        monitor.stop()
    assert not never.exists()


def test_snapshot_is_frozen_and_complete():
    status = LlmStatus("checking", None, False, None, None, None, None, None)
    with pytest.raises(AttributeError):
        status.state = "ready"


def test_the_app_starts_the_monitor_and_stops_it_on_exit(fake_llm, tmp_path):
    from fastapi.testclient import TestClient

    from fione.api.app import create_app

    fake = fake_llm()
    settings = make_settings(tmp_path / "on", llm_base_url=fake.url, llm_provider="ollama")
    with TestClient(create_app(settings)) as client:
        monitor = client.app.state.llm_monitor
        wait_for(monitor, "ready")
        thread = monitor._thread
        assert thread.is_alive()
    assert not thread.is_alive()


WRONG_SHAPES = [
    b"[]",
    b"null",
    b'"models"',
    b'{"models": null}',
    b'{"models": 5}',
    b'{"models": {"name": "gemma4:12b-mlx"}}',
    b"not json",
    b'{"models": [',
    b"[" * 200_000,
    b"\xff\xfe",
    b"",
]


@pytest.mark.parametrize("body", WRONG_SHAPES, ids=range(len(WRONG_SHAPES)))
def test_a_wrong_answer_is_an_error_code_and_the_thread_lives_on(fake_llm, monitors, body):
    fake = fake_llm()
    fake.raw_replies["/api/tags"] = body
    monitor = monitors(fake.url)
    monitor.start()
    status = wait_for(monitor, "error")
    assert status.error_code == "probe_failed"
    assert monitor._thread.is_alive()
    del fake.raw_replies["/api/tags"]  # the server is fixed: the monitor recovers by itself
    wait_for(monitor, "ready")


def test_junk_entries_in_the_model_list_are_skipped(fake_llm, monitors):
    fake = fake_llm()
    fake.raw_replies["/api/tags"] = json.dumps({"models": [1, "x", None, {"name": 5}]}).encode()
    monitor = monitors(fake.url, llm_auto_pull=False)
    monitor.start()
    wait_for(monitor, "missing")
    assert monitor._thread.is_alive()


@pytest.mark.parametrize(
    "body",
    [
        *WRONG_SHAPES,
        b'{"models": [1, null, "x"]}',
        b'{"models": [{"name": "gemma4:12b-mlx", "context_length": "big"}]}',
        b'{"models": [{"name": "gemma4:12b-mlx", "context_length": true}]}',
        b'{"models": [{"name": "gemma4:12b-mlx", "context_length": -1}]}',
        b'{"models": [{"name": "gemma4:12b-mlx", "context_length": 1.5}]}',
        b'{"models": [{"name": "other:1b", "context_length": 99999}]}',
    ],
)
def test_refresh_context_ignores_a_wrong_answer(fake_llm, monitors, body):
    fake = fake_llm()
    fake.raw_replies["/api/ps"] = body
    monitor = monitors(fake.url)
    monitor.refresh_context()  # never raises
    assert monitor.snapshot().server_context is None
    assert monitor.effective_context() == OLLAMA_DEFAULT_CONTEXT


def test_loading_the_model_reads_a_bounded_answer(fake_llm, monitors, monkeypatch):
    monkeypatch.setattr(provider, "MAX_LOAD_ANSWER_BYTES", 1000)
    fake = fake_llm(context_length=8192)
    monitor = monitors(fake.url)
    assert monitor.load_model() is True
    monitor.refresh_context()
    assert monitor.snapshot().server_context == 8192
    fake.generate_padding = 5000
    assert monitor.load_model() is False
    claude = monitors(fake_llm().url, "claude", llm_api_key="sk-test-0123456789")
    assert claude.load_model() is False


def test_an_oversized_answer_is_refused(fake_llm, monitors, monkeypatch):
    monkeypatch.setattr(provider, "MAX_BODY_BYTES", 1000)
    fake = fake_llm()
    pad = "x" * 5000
    fake.raw_replies["/api/tags"] = json.dumps({"models": [], "pad": pad}).encode()
    fake.raw_replies["/api/ps"] = json.dumps(
        {"models": [{"name": "gemma4:12b-mlx", "context_length": 8192}], "pad": pad}
    ).encode()
    monitor = monitors(fake.url)
    monitor.refresh_context()
    assert monitor.snapshot().server_context is None
    monitor.start()
    assert wait_for(monitor, "error").error_code == "probe_failed"


def test_a_pull_line_that_never_ends_is_a_failed_pull(fake_llm, monitors, monkeypatch, caplog):
    monkeypatch.setattr(provider, "MAX_PULL_LINE_BYTES", 1000)
    fake = fake_llm(models=[], pull_garbage=200_000)
    monitor = monitors(fake.url, llm_auto_pull=True)
    with caplog.at_level(logging.WARNING, logger="fione.assistant"):
        monitor.start()
        status = wait_for(monitor, "error")
    assert status.error_code == "pull_failed"
    assert "Traceback" not in caplog.text and not [r for r in caplog.records if r.exc_info]


def test_a_failed_pull_stays_shown_through_an_outage(fake_llm, monitors):
    fake = fake_llm(models=[], pull_error="boom")
    port = fake.port
    monitor = monitors(fake.url, llm_auto_pull=True)
    monitor.start()
    wait_for(monitor, "error")
    fake.stop()
    wait_for(monitor, "unreachable")
    restarted = fake_llm(models=[], port=port)
    status = wait_for(monitor, "error")  # not stuck at unreachable, and the reason is back
    assert status.error_code == "pull_failed"
    assert "POST /api/pull" not in restarted.paths  # and still no pull of its own accord


def test_the_model_appearing_clears_a_failed_pull(fake_llm, monitors):
    fake = fake_llm(models=[], pull_error="boom")
    monitor = monitors(fake.url, llm_auto_pull=True)
    monitor.start()
    wait_for(monitor, "error")
    fake.add_model("gemma4:12b-mlx")
    status = wait_for(monitor, "ready")
    assert status.error_code is None


def test_a_check_leaves_a_running_pull_alone(fake_llm, monitors):
    fake = fake_llm(models=[], pull_steps=3, pull_delay=0.4)
    monitor = monitors(fake.url, llm_auto_pull=False)
    monitor.start()
    wait_for(monitor, "missing")
    assert monitor.pull_now() is True
    wait_for(monitor, "pulling")
    for _ in range(3):
        monitor._check()  # what the thread does every recheck
        assert monitor.snapshot().state == "pulling"
    wait_for(monitor, "ready")


@pytest.mark.parametrize("by", ["monitor", "pull_now"])
def test_stopping_during_a_pull_is_quiet(fake_llm, monitors, caplog, by):
    fake = fake_llm(models=[], pull_steps=5, pull_delay=0.4)
    monitor = monitors(fake.url, llm_auto_pull=by == "monitor")
    with caplog.at_level(logging.DEBUG, logger="fione.assistant"):
        monitor.start()
        if by == "pull_now":
            wait_for(monitor, "missing")
            assert monitor.pull_now()
        wait_for(monitor, "pulling")
        monitor.stop()
        time.sleep(1.0)
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING or r.exc_info]


def test_an_unexpected_pull_error_is_logged_unless_the_monitor_is_stopping(
    fake_llm, monitors, caplog, monkeypatch
):
    for stopping in (False, True):
        caplog.clear()
        monitor = monitors(fake_llm(models=[], pull_steps=1).url)

        def boom(line, monitor=monitor, stopping=stopping):
            if stopping:
                monitor._stop.set()  # a shutdown closes the client under the pull
            raise RuntimeError("client closed")

        monkeypatch.setattr(monitor, "_pull_line", boom)
        assert monitor._begin_pull(forced=True)
        with caplog.at_level(logging.INFO, logger="fione.assistant"):
            monitor._pull()
        assert bool([r for r in caplog.records if r.exc_info]) is (not stopping)
        assert monitor.snapshot().error_code == "pull_failed" and not monitor._pulling


def test_lines_refuses_a_line_that_never_ends(monkeypatch):
    monkeypatch.setattr(provider, "MAX_PULL_LINE_BYTES", 1000)
    endless = httpx.Response(200, content=iter([b"x" * 600] * 5))  # no newline in 3000 bytes
    with pytest.raises(ValueError, match="too long"):
        list(provider._lines(endless))
    fine = httpx.Response(200, content=iter([b'{"a":1}\n{"b"', b":2}\n", b"last"]))
    assert list(provider._lines(fine)) == ['{"a":1}', '{"b":2}', "last"]


def test_a_failed_pull_is_tried_again_when_the_model_goes_missing_again(
    fake_llm, monitors, monkeypatch
):
    monkeypatch.setattr(provider, "READY_RECHECK_SECS", 0.05)
    fake = fake_llm(models=[], pull_error="boom")
    monitor = monitors(fake.url, llm_auto_pull=True)
    monitor.start()
    wait_for(monitor, "error")  # the first pull failed: no more of its own accord
    fake.add_model("gemma4:12b-mlx")
    wait_for(monitor, "ready")
    pulls = fake.paths.count("POST /api/pull")
    fake.models.clear()  # the model is removed from the server
    deadline = time.monotonic() + 10
    while fake.paths.count("POST /api/pull") == pulls and time.monotonic() < deadline:
        time.sleep(0.02)
    assert fake.paths.count("POST /api/pull") == pulls + 1  # a new automatic pull


def test_the_thread_outlives_an_unexpected_error_and_logs_it_unless_stopping(
    fake_llm, monitors, caplog, monkeypatch
):
    monitor = monitors(fake_llm().url, recheck_secs=0.05)
    calls = []

    def boom():
        calls.append(1)
        raise RuntimeError("bug")

    monkeypatch.setattr(monitor, "_check", boom)
    with caplog.at_level(logging.INFO, logger="fione.assistant"):
        monitor.start()
        deadline = time.monotonic() + 10
        while len(calls) < 3 and time.monotonic() < deadline:  # it keeps looking
            time.sleep(0.02)
        status = monitor.snapshot()
    assert len(calls) >= 3 and (status.state, status.error_code) == ("error", "probe_failed")
    assert [r for r in caplog.records if r.exc_info]
    monitor.stop()  # joins the thread: nothing of it is left to log after this
    caplog.clear()
    monitor._run()  # a run that is stopping logs nothing, even when its check fails
    assert not caplog.records


@pytest.mark.parametrize("stopping", [False, True])
def test_a_transport_error_during_a_pull_is_stopped_or_unreachable(fake_llm, monitors, stopping):
    monitor = monitors(fake_llm(models=[]).url)

    def refuse(*args, **kwargs):
        raise httpx.ConnectError("closed")

    monkeypatched = monitor._http
    monkeypatched.stream = refuse
    if stopping:
        monitor._stop.set()
    assert monitor._begin_pull(forced=True)
    monitor._pull()
    status = monitor.snapshot()
    assert not monitor._pulling and monitor._pull_blocked is False  # never a failed pull
    assert status.state == ("unreachable" if not stopping else status.state)
    assert status.error_code is None
