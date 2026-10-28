"""The LLM provider's status: which URLs are local, the monitor that checks an Ollama server
and pulls its model, and the context the server really gives."""

import logging
import time

import pytest

from api_helpers import make_settings
from fake_llm import FakeLlm
from fione.assistant.provider import (
    OLLAMA_DEFAULT_CONTEXT,
    LlmMonitor,
    LlmStatus,
    is_local_url,
    native_root,
)


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
def monitors(tmp_path):
    made = []

    def factory(url, provider="ollama", recheck_secs=0.05, **settings):
        values = {"llm_base_url": url, "llm_provider": provider, **settings}
        monitor = LlmMonitor(make_settings(tmp_path, **values), recheck_secs=recheck_secs)
        made.append(monitor)
        return monitor

    yield factory
    for monitor in made:
        monitor.stop()


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


def test_the_monitor_is_off_without_a_base_url(tmp_path):
    monitor = LlmMonitor(make_settings(tmp_path))
    monitor.start()
    status = monitor.snapshot()
    assert (status.state, status.model, status.host) == ("off", None, None)
    assert monitor.pull_now() is False
    monitor.stop()


def test_openai_provider_is_ready_without_probing(fake_llm, monitors):
    fake = fake_llm()
    monitor = monitors(fake.url, "openai", llm_model="m")
    monitor.start()
    status = monitor.snapshot()
    assert (status.state, status.model, status.local) == ("ready", "m", True)
    assert status.host == f"127.0.0.1:{fake.port}"
    assert monitor.pull_now() is False
    monitor.refresh_context()
    time.sleep(0.2)
    assert fake.requests == [] and fake.paths == []
    assert monitor.effective_context() == 16384


def test_a_present_model_is_ready(fake_llm, monitors):
    monitor = monitors(fake_llm().url)
    assert monitor.snapshot().state == "checking"
    monitor.start()
    status = wait_for(monitor, "ready")
    assert (status.model, status.error_code) == ("gemma4:12b", None)


def test_an_untagged_model_matches_latest(fake_llm, monitors):
    monitor = monitors(fake_llm(models=["tiny:latest"]).url, llm_model="tiny")
    monitor.start()
    wait_for(monitor, "ready")
    other = monitors(fake_llm(models=["tiny:1b"]).url, llm_model="tiny", llm_auto_pull=False)
    other.start()
    wait_for(other, "missing")


def test_missing_model_is_pulled_with_progress(fake_llm, monitors):
    fake = fake_llm(models=[], pull_steps=3, pull_delay=0.2)
    monitor = monitors(fake.url)
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
    assert fake.models == ["gemma4:12b"]


def test_no_auto_pull_leaves_missing(fake_llm, monitors):
    fake = fake_llm(models=[])
    monitor = monitors(fake.url, llm_auto_pull=False)
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


def test_pull_error_is_a_code_not_text(fake_llm, monitors, caplog):
    fake = fake_llm(models=[], pull_error="pull model manifest: file does not exist\nSECRET-DETAIL")
    monitor = monitors(fake.url)
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
    monitor = monitors(fake.url, llm_api_key="sk-secret-key-123")
    with caplog.at_level(logging.DEBUG):
        monitor.start()
        wait_for(monitor, "ready")
    assert "sk-secret-key-123" not in caplog.text
    assert "sk-secret-key-123" not in repr(monitor.snapshot())


def test_effective_context(fake_llm, monitors):
    monitor = monitors(fake_llm().url)
    assert monitor.effective_context() == OLLAMA_DEFAULT_CONTEXT == 4096
    assert monitor.snapshot().server_context is None

    from fione.assistant.client import ChatClient

    fake = fake_llm(context_length=8192)
    monitor = monitors(fake.url)
    monitor.refresh_context()  # nothing loaded yet: unchanged
    assert monitor.effective_context() == 4096
    deadline = time.monotonic() + 5
    ChatClient(fake.url, "gemma4:12b").complete(
        [{"role": "user", "content": "hi"}], [], deadline=deadline
    )
    monitor.refresh_context()
    assert monitor.effective_context() == 8192
    assert monitor.snapshot().server_context == 8192

    big = fake_llm(context_length=32768)
    monitor = monitors(big.url)
    ChatClient(big.url, "gemma4:12b").complete(
        [{"role": "user", "content": "hi"}], [], deadline=deadline
    )
    monitor.refresh_context()
    assert monitor.effective_context() == 16384  # the setting is the smaller one

    big.stop()
    monitor.refresh_context()  # a failure keeps the old value
    assert monitor.snapshot().server_context == 32768


def test_snapshot_is_frozen_and_complete():
    status = LlmStatus("off", None, False, None, None, None, None, None)
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

    with TestClient(create_app(make_settings(tmp_path / "off"))) as client:
        assert client.app.state.llm_monitor.snapshot().state == "off"
        assert client.app.state.llm_monitor._thread is None
