"""Security primitives behind the API: signed sessions, login throttle, setup token."""

import stat
import threading
import time

import pytest

from fione.api import security
from fione.api.security import LoginThrottle, SessionSigner
from fione.config import Settings

SECRET = b"s" * 32


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


# --- sessions -----------------------------------------------------------------


def test_session_key_is_derived_not_the_secret():
    key = security.session_key(SECRET)
    assert key != SECRET and len(key) == 32
    assert security.session_key(b"t" * 32) != key


def test_session_round_trip_carries_only_id_time_and_csrf():
    clock = Clock()
    signer = SessionSigner(SECRET, max_age_secs=60, clock=clock)
    value, session = signer.issue(7, binding="hash-a")
    assert (session.user_id, session.issued_at) == (7, 1000)
    assert len(session.csrf) >= 32
    assert signer.unverified_user_id(value) == 7
    assert signer.verify(value, "hash-a") == session
    assert "hash-a" not in value and "editor" not in value and "admin" not in value


def test_session_rejects_other_binding_tampering_and_other_keys():
    signer = SessionSigner(SECRET, max_age_secs=60)
    value, _ = signer.issue(7, binding="hash-a")
    assert signer.verify(value, "hash-b") is None
    version, payload, sig = value.split(".")
    forged = security._b64e(b'{"u":1,"t":%d,"c":"x"}' % int(time.time()))
    assert signer.verify(f"{version}.{forged}.{sig}", "hash-a") is None
    flipped = sig[:-2] + ("A" if sig[-2] != "A" else "B") + sig[-1]
    assert signer.verify(f"{version}.{payload}.{flipped}", "hash-a") is None
    assert SessionSigner(b"t" * 32, max_age_secs=60).verify(value, "hash-a") is None


def _claim(user_id) -> str:
    payload = security._b64e(b'{"u":%d,"t":%d,"c":"x"}' % (user_id, int(time.time())))
    return f"v1.{payload}.AAAA"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "x",
        "v1..",
        "v1.e30.",
        "v2.e30.AAAA",
        "v1.!!!.AAAA",
        "v1." + "A" * 5000 + ".A",
        # Fixed ids: the claims carry the time, and pytest-xdist needs every worker to
        # collect the same test ids.
        pytest.param(_claim(0), id="claim-0"),
        pytest.param(_claim(-1), id="claim-minus-1"),
        pytest.param(_claim(2**63), id="claim-2**63"),
        pytest.param(_claim(2**64), id="claim-2**64"),
    ],
)
def test_session_rejects_garbage(value):
    signer = SessionSigner(SECRET, max_age_secs=60)
    assert signer.unverified_user_id(value) is None
    assert signer.verify(value, "hash-a") is None


def test_session_expires_on_the_server_side():
    clock = Clock()
    signer = SessionSigner(SECRET, max_age_secs=60, clock=clock)
    value, _ = signer.issue(7, binding="h")
    clock.now += 60
    assert signer.verify(value, "h") is not None
    clock.now += 1
    assert signer.verify(value, "h") is None
    clock.now = 900  # issued in the future
    assert signer.verify(value, "h") is None


# --- login throttle -----------------------------------------------------------


def test_throttle_blocks_after_max_failures_within_window():
    clock = Clock()
    t = LoginThrottle(max_failures=3, window_secs=100, clock=clock)
    key = ("1.2.3.4", "alice")
    for _ in range(3):
        assert t.attempt(key) is None  # each attempt counts as a failure until success()
        clock.now += 10
    assert t.attempt(key) == 70  # now 1030; the first failure leaves the window at 1100
    assert t.attempt(key) == 70  # refused attempts are not counted
    assert t.attempt(("1.2.3.4", "bob")) is None
    assert t.attempt(("5.6.7.8", "alice")) is None
    clock.now = 1100
    assert t.attempt(key) is None


def test_throttle_success_clears_the_key():
    t = LoginThrottle(max_failures=2, window_secs=100, clock=Clock())
    key = ("ip", "alice")
    assert t.attempt(key) is None
    t.success(key)
    assert t.attempt(key) is None
    t.success(key)
    assert t.attempt(key) is None
    assert t.attempt(key) is None
    assert t.attempt(key) is not None


def test_concurrent_attempts_cannot_exceed_the_limit():
    t = LoginThrottle(max_failures=5, window_secs=100)
    key = ("ip", "alice")
    allowed = []
    barrier = threading.Barrier(30)

    def go():
        barrier.wait()
        allowed.append(t.attempt(key) is None)

    threads = [threading.Thread(target=go) for _ in range(30)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert allowed.count(True) == 5


def test_per_address_cap_bounds_username_spraying():
    t = LoginThrottle(max_failures=5, window_secs=100, max_failures_per_ip=4, clock=Clock())
    for i in range(4):
        assert t.attempt(("1.2.3.4", f"user{i}")) is None
    assert t.attempt(("1.2.3.4", "fresh")) is not None
    assert t.attempt(("5.6.7.8", "fresh")) is None
    t.success(("1.2.3.4", "user3"))  # a success gives back only its own attempt
    assert t.attempt(("1.2.3.4", "fresh")) is None
    assert t.attempt(("1.2.3.4", "fresh2")) is not None


def test_a_locked_key_is_never_evicted():
    clock = Clock()
    t = LoginThrottle(max_failures=5, window_secs=900, max_keys=100, clock=clock)
    locked = ("1.2.3.4", "alice")
    for _ in range(5):
        t.attempt(locked)
    for i in range(300):
        t.attempt((f"10.0.{i // 250}.{i % 250}", f"junk{i}"))
    assert t.attempt(locked) is not None


def test_expired_entries_are_pruned():
    clock = Clock()
    t = LoginThrottle(max_failures=2, window_secs=100, max_keys=10, clock=clock)
    for i in range(50):
        t.attempt((f"old{i}", "u"))
    clock.now += 101
    for i in range(60):
        t.attempt((f"new{i}", "u"))
    assert all(ip.startswith("new") for ip, _ in t._failures)
    assert all(ip.startswith("new") for ip in t._by_ip)


def test_password_work_caps_concurrency():
    active = peak = 0
    lock = threading.Lock()

    def work():
        nonlocal active, peak
        with security.password_work():
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.02)
            with lock:
                active -= 1

    threads = [threading.Thread(target=work) for _ in range(12)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert peak == security.PASSWORD_SLOTS == 4


# --- origin and client address -------------------------------------------------


@pytest.mark.parametrize(
    ("origin", "host", "ok"),
    [
        (None, "fione.example", True),
        ("https://fione.example", "fione.example", True),
        ("http://FIONE.example:8080", "fione.example:8080", True),
        ("https://evil.example", "fione.example", False),
        ("null", "fione.example", False),
        ("https://fione.example", None, False),
        ("garbage", "fione.example", False),
    ],
)
def test_origin_matches(origin, host, ok):
    assert security.origin_matches(origin, host) is ok


# --- setup token ----------------------------------------------------------------


def test_setup_token_generated_once_private(tmp_path):
    settings = Settings(data_dir=tmp_path, setup_token=None)
    token, generated = security.ensure_setup_token(settings)
    assert generated is True and len(token) >= 43
    path = tmp_path / security.SETUP_TOKEN_FILE
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert security.ensure_setup_token(settings) == (token, True)
    assert security.read_setup_token(settings) == token
    security.discard_setup_token(settings)
    assert not path.exists()
    assert security.read_setup_token(settings) is None
    security.discard_setup_token(settings)  # idempotent


def test_setup_token_from_settings_writes_no_file(tmp_path):
    settings = Settings(data_dir=tmp_path, setup_token="from-env-token-0123")
    assert security.ensure_setup_token(settings) == ("from-env-token-0123", False)
    assert security.read_setup_token(settings) == "from-env-token-0123"
    assert not (tmp_path / security.SETUP_TOKEN_FILE).exists()


def test_tokens_equal_is_constant_time_compare():
    assert security.tokens_equal("abc", "abc")
    assert not security.tokens_equal("abc", "abd")
    assert not security.tokens_equal("abc", None)
    assert not security.tokens_equal("", "")
    assert not security.tokens_equal("é", "e")
