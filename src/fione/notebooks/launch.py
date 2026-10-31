"""Launch tokens: how Fione signs a user into their notebook container.

Each start gets a fresh nonce, and the container's key is derived from the install secret, the
user id and that nonce (HMAC is one-way: the key reveals nothing about the secret, and no key
is stored). A launch token is ``v1.<b64url(json claims)>.<b64url(HMAC-SHA256(key, "v1." +
payload))>``, good for one sign-in within ``LAUNCH_TOKEN_TTL_SECS``; the container checks it
with ``fione_notebook.auth.verify_launch_token``.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

from fione.auth.roles import User

LAUNCH_TOKEN_TTL_SECS = 60
LAUNCH_PARAM = "launch"  # fione_notebook.auth.LAUNCH_PARAM (that package needs Jupyter)
_VERSION = "v1"
_KEY_LABEL = "fione-notebook-launch-v1"


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def launch_key(secret: bytes, user_id: int, nonce: str) -> bytes:
    """The 32-byte key of one container: ``user_id``'s, started with ``nonce``."""
    message = f"{_KEY_LABEL}:{user_id}:{nonce}".encode()
    return hmac.new(secret, message, hashlib.sha256).digest()


def sign_launch_token(key: bytes, *, user: User, now: float | None = None) -> str:
    now = time.time() if now is None else now
    claims = {
        "sub": str(user.id),
        "name": user.username,
        "role": user.role.value,
        "exp": int(now) + LAUNCH_TOKEN_TTL_SECS,
        "jti": secrets.token_urlsafe(16),
    }
    payload = _b64encode(json.dumps(claims, separators=(",", ":")).encode())
    signature = hmac.new(key, f"{_VERSION}.{payload}".encode(), hashlib.sha256).digest()
    return f"{_VERSION}.{payload}.{_b64encode(signature)}"
