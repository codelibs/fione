import base64
import binascii
import hashlib
import hmac
import secrets

MIN_PASSWORD_LENGTH = 8

_N = 2**15
_R = 8
_P = 1
_KEY_LEN = 32
_SALT_LEN = 16
_SCHEME = "scrypt"


def _maxmem(n: int, r: int, p: int) -> int:
    # OpenSSL needs more than 128*r*(n+p+1) bytes; double it for headroom.
    return 2 * 128 * r * (n + p + 1)


def _derive(password: str, salt: bytes, n: int, r: int, p: int, key_len: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=key_len, maxmem=_maxmem(n, r, p)
    )


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    """Return ``scrypt$n$r$p$salt$key`` (base64 salt/key) with a fresh random salt."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    salt = secrets.token_bytes(_SALT_LEN)
    key = _derive(password, salt, _N, _R, _P, _KEY_LEN)
    return f"{_SCHEME}${_N}${_R}${_P}${_b64(salt)}${_b64(key)}"


def verify_password(password: str, hashed: str) -> bool:
    """Check ``password`` against ``hashed``; a malformed hash is simply a mismatch."""
    try:
        scheme, n, r, p, salt, key = hashed.split("$")
        if scheme != _SCHEME:
            return False
        n_, r_, p_ = int(n), int(r), int(p)
        salt_b = base64.b64decode(salt, validate=True)
        key_b = base64.b64decode(key, validate=True)
        actual = _derive(password, salt_b, n_, r_, p_, len(key_b))
    except (ValueError, binascii.Error):
        return False
    return hmac.compare_digest(actual, key_b)
