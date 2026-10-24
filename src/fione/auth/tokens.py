import hashlib
import secrets

TOKEN_PREFIX = "fione_"


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hex sha256 of the token: the only form that is ever stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
