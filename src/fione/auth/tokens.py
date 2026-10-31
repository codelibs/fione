import hashlib
import secrets
from enum import StrEnum

TOKEN_PREFIX = "fione_"


class TokenScope(StrEnum):
    """What a token may be used for: ``notebook`` tokens are refused on routes that change
    accounts, credentials or the host (see ``NOTEBOOK_SCOPE_ROUTES``)."""

    FULL = "full"
    NOTEBOOK = "notebook"


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hex sha256 of the token: the only form that is ever stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
