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
    """Counts failed password checks per key (client address, lowercased username) in a
    sliding window; a key with ``max_failures`` failures in the window is locked out until
    the oldest one leaves it. A success clears the key.

    In memory, per process. At most ``max_keys`` keys are kept: past that, expired keys are
    dropped, then the least recently failed ones.
    """

    def __init__(
        self,
        max_failures: int,
        window_secs: float,
        *,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._max = max_failures
        self._window = window_secs
        self._max_keys = max_keys
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: dict[tuple[str, str], list[float]] = {}

    def _live(self, key: tuple[str, str], now: float) -> list[float]:
        times = [t for t in self._failures.get(key, ()) if t > now - self._window]
        if times:
            self._failures[key] = times
        else:
            self._failures.pop(key, None)
        return times

    def retry_after(self, key: tuple[str, str]) -> int | None:
        """Seconds until the key may try again, or None if it may now."""
        with self._lock:
            now = self._clock()
            times = self._live(key, now)
            if len(times) < self._max:
                return None
            return max(1, math.ceil(times[-self._max] + self._window - now))

    def failure(self, key: tuple[str, str]) -> None:
        with self._lock:
            now = self._clock()
            times = self._live(key, now)
            self._failures.pop(key, None)  # re-insert last: dict order is failure recency
            self._failures[key] = [*times, now]
            if len(self._failures) > self._max_keys:
                for other in list(self._failures):
                    self._live(other, now)
                while len(self._failures) > self._max_keys:
                    del self._failures[next(iter(self._failures))]

    def success(self, key: tuple[str, str]) -> None:
        with self._lock:
            self._failures.pop(key, None)


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
