"""The fake LLM's command line and address, which the e2e stack runs inside a container."""

import urllib.request

from fake_llm import DEFAULT_MODEL, FakeLlm, from_args


def test_defaults_bind_to_loopback_with_the_model():
    fake = from_args([])
    assert (fake.host, fake.port, fake.pull_delay, fake.policy) == ("127.0.0.1", 0, 0.0, "script")
    assert fake.models == [DEFAULT_MODEL]


def test_options_are_read():
    fake = from_args(
        [
            "--host",
            "0.0.0.0",
            "--port",
            "11434",
            "--policy",
            "e2e",
            "--missing",
            "--pull-delay",
            "0.2",
        ]
    )
    assert (fake.host, fake.port, fake.policy, fake.pull_delay) == ("0.0.0.0", 11434, "e2e", 0.2)
    assert fake.models == []


def test_all_interfaces_are_reached_on_loopback():
    fake = FakeLlm(host="0.0.0.0", port=0).start()
    try:
        assert fake.url == f"http://127.0.0.1:{fake.port}/v1"
        with urllib.request.urlopen(f"http://127.0.0.1:{fake.port}/api/version", timeout=5) as r:
            assert r.status == 200
    finally:
        fake.stop()
