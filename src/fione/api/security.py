"""Security primitives of the API: signed session cookies, the login throttle, the bound on
concurrent password hashing, the first-admin setup token and the Origin check.

Session cookie: ``v1.<payload>.<signature>``, base64url. The payload holds only the user id,
the issue time and the session's CSRF token; the role is never in it (it is reloaded from the
database on every request). The signature is HMAC-SHA256 under a key derived from the install
secret (never the secret itself) over the payload and a digest of the user's current password
hash, so a password change ends every session, and a new user that reuses a deleted user's id
(SQLite reuses the highest rowid) cannot inherit that user's sessions.
"""

import base64
import binascii
import hashlib
import hmac
import json
import math
import secrets
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlsplit

from fione.config import Settings, create_private_file

SESSION_COOKIE = "fione_session"
_SESSION_VERSION = "v1"
_SESSION_KEY_LABEL = b"fione-session-v1"
_MAX_COOKIE_LEN = 512
_CLOCK_SKEW_SECS = 60
_MAX_ROWID = 2**63 - 1

PASSWORD_SLOTS = 4
SETUP_TOKEN_FILE = "setup-token"


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def session_key(secret: bytes) -> bytes:
    return hmac.new(secret, _SESSION_KEY_LABEL, hashlib.sha256).digest()


def tokens_equal(expected: str, given: str | None) -> bool:
    """Constant-time comparison; an empty expected token never matches."""
    if not expected or given is None:
        return False
    return hmac.compare_digest(expected.encode("utf-8"), given.encode("utf-8"))


@dataclass(frozen=True)
class Session:
    user_id: int
    issued_at: int
    csrf: str


class SessionSigner:
    def __init__(self, secret: bytes, max_age_secs: int, *, clock: Callable[[], float] = time.time):
        self._key = session_key(secret)
        self._max_age = max_age_secs
        self._clock = clock

    def _sign(self, payload: str, binding: str) -> str:
        bound = hashlib.sha256(binding.encode("utf-8")).digest()
        message = f"{_SESSION_VERSION}.{payload}".encode("ascii") + b"\x00" + bound
        return _b64e(hmac.new(self._key, message, hashlib.sha256).digest())

    def issue(self, user_id: int, binding: str) -> tuple[str, Session]:
        """A new session for ``user_id`` bound to ``binding`` (the password hash): the cookie
        value and the session it carries."""
        session = Session(user_id, int(self._clock()), secrets.token_urlsafe(32))
        body = json.dumps(
            {"u": session.user_id, "t": session.issued_at, "c": session.csrf},
            separators=(",", ":"),
        )
        payload = _b64e(body.encode("ascii"))
        return f"{_SESSION_VERSION}.{payload}.{self._sign(payload, binding)}", session

    @staticmethod
    def _parse(value: str) -> tuple[str, str, Session] | None:
        if len(value) > _MAX_COOKIE_LEN:
            return None
        parts = value.split(".")
        if len(parts) != 3 or parts[0] != _SESSION_VERSION:
            return None
        payload, signature = parts[1], parts[2]
        try:
            data = json.loads(_b64d(payload))
            session = Session(int(data["u"]), int(data["t"]), str(data["c"]))
        except (ValueError, TypeError, KeyError, binascii.Error):
            return None
        if type(data["u"]) is not int or type(data["t"]) is not int:
            return None
        if not 1 <= session.user_id <= _MAX_ROWID:  # never reaches SQLite out of range
            return None
        return payload, signature, session

    def unverified_user_id(self, value: str) -> int | None:
        """The user id the cookie claims, to look up its binding; not yet trustworthy."""
        parsed = self._parse(value)
        return None if parsed is None else parsed[2].user_id

    def verify(self, value: str, binding: str) -> Session | None:
        """The session if the signature matches ``binding`` and it has not expired."""
        parsed = self._parse(value)
        if parsed is None:
            return None
        payload, signature, session = parsed
        if not hmac.compare_digest(signature, self._sign(payload, binding)):
            return None
        age = self._clock() - session.issued_at
        if age > self._max_age or age < -_CLOCK_SKEW_SECS:
            return None
        return session


class LoginThrottle:
    """Limits password checks per key (client address, lowercased username) and per client
    address, in a sliding window.

    ``attempt`` checks and counts in one step under the lock: every allowed attempt is
    recorded as a failure up front, and ``success`` takes it back (and clears the key), so
    concurrent requests can never run more than ``max_failures`` checks for a key, nor more
    than ``max_failures_per_ip`` for an address. A refused attempt is not counted.

    In memory, per process. Live entries are never evicted, so a lockout cannot be undone
    by flooding with junk keys; expired ones are pruned once more than ``max_keys`` keys are
    held. For the login throttle, memory stays bounded because every allowed attempt then
    costs a password hash (``password_work``), over a window of fixed length. The
    first-admin throttle has no such cost per attempt: before setup, many source addresses
    can grow it at request rate (small entries, and only until the first admin exists).
    """

    def __init__(
        self,
        max_failures: int,
        window_secs: float,
        *,
        max_failures_per_ip: int = 50,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._max = max_failures
        self._max_per_ip = max_failures_per_ip
        self._window = window_secs
        self._max_keys = max_keys
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: dict[tuple[str, str], list[float]] = {}
        self._by_ip: dict[str, list[float]] = {}
        self._prune_at = max_keys

    @staticmethod
    def _live(table: dict, key, cutoff: float) -> list[float]:
        times = [t for t in table.get(key, ()) if t > cutoff]
        if times:
            table[key] = times
        else:
            table.pop(key, None)
        return times

    def _retry(self, times: list[float], limit: int, now: float) -> int | None:
        if len(times) < limit:
            return None
        return max(1, math.ceil(times[-limit] + self._window - now))

    def _prune(self, cutoff: float) -> None:
        for table in (self._failures, self._by_ip):
            for key in list(table):
                self._live(table, key, cutoff)
        # Amortized: the next full pass waits until the tables have grown again.
        self._prune_at = max(self._max_keys, 2 * len(self._failures), 2 * len(self._by_ip))

    def attempt(self, key: tuple[str, str]) -> int | None:
        """None if the password check may run (it is counted as a failure until
        ``success``), else the seconds until the key or its address may try again."""
        with self._lock:
            now = self._clock()
            cutoff = now - self._window
            times = self._live(self._failures, key, cutoff)
            ip_times = self._live(self._by_ip, key[0], cutoff)
            retry = self._retry(times, self._max, now)
            if retry is None:
                retry = self._retry(ip_times, self._max_per_ip, now)
            if retry is not None:
                return retry
            self._failures[key] = [*times, now]
            self._by_ip[key[0]] = [*ip_times, now]
            if max(len(self._failures), len(self._by_ip)) > self._prune_at:
                self._prune(cutoff)
            return None

    def success(self, key: tuple[str, str]) -> None:
        """The check passed: clear the key, and give its address back this attempt."""
        with self._lock:
            times = self._failures.pop(key, None)
            ip_times = self._by_ip.get(key[0])
            if times and ip_times and times[-1] in ip_times:
                ip_times.remove(times[-1])
                if not ip_times:
                    del self._by_ip[key[0]]


_password_slots = threading.BoundedSemaphore(PASSWORD_SLOTS)


@contextmanager
def password_work() -> Iterator[None]:
    """Hold one of the process-wide slots for scrypt work (32 MiB each); waiters queue."""
    with _password_slots:
        yield


def origin_matches(origin: str | None, host: str | None) -> bool:
    """True when there is no ``Origin`` (not a cross-site browser request) or it names
    ``host``; ``Origin: null`` (sandboxed or privacy-sensitive contexts) never matches."""
    if origin is None:
        return True
    if not host:
        return False
    try:
        parts = urlsplit(origin)
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return False
    return parts.netloc.lower() == host.lower()


def _setup_token_path(settings: Settings):
    return settings.data_dir / SETUP_TOKEN_FILE


def ensure_setup_token(settings: Settings) -> tuple[str, bool]:
    """The first-admin setup token and whether Fione generated it (else it is configured).

    A generated token is a random 32-byte urlsafe string written once to
    ``<data_dir>/setup-token`` (mode 0600, published atomically).
    """
    if settings.setup_token:
        return settings.setup_token, False
    path = _setup_token_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        create_private_file(path, secrets.token_urlsafe(32).encode("ascii"))
    return path.read_text(encoding="ascii").strip(), True


def read_setup_token(settings: Settings) -> str | None:
    if settings.setup_token:
        return settings.setup_token
    try:
        return _setup_token_path(settings).read_text(encoding="ascii").strip() or None
    except (OSError, UnicodeDecodeError):
        return None


def discard_setup_token(settings: Settings) -> None:
    _setup_token_path(settings).unlink(missing_ok=True)
