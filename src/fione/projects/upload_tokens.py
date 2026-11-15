"""One-time upload tokens: a capability to PUT one CSV into one project, made by an
authenticated MCP client.

The raw token (128 bits) is shown once and only its SHA-256 is stored. A token is valid for
``ttl_secs``, is claimed atomically by the one request that uses it, and is consumed only when
that request ingests the file: a failed ingest releases the claim and the token stays usable
until it expires.
"""

import hashlib
import secrets
import sqlite3
import time
from dataclasses import dataclass

from fione.projects.service import DatasetType

TTL_SECS = 15 * 60


@dataclass(frozen=True)
class UploadToken:
    id: int
    user_id: int
    project_id: str
    name: str
    type: DatasetType


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create(
    conn: sqlite3.Connection,
    user_id: int,
    project_id: str,
    name: str,
    type: DatasetType,
    *,
    ttl_secs: float = TTL_SECS,
    now: float | None = None,
) -> str:
    """Store a token for the user, project, dataset name and type; returns the raw token."""
    now = time.time() if now is None else now
    # tokens that can no longer be used are of no further interest
    conn.execute("DELETE FROM upload_tokens WHERE expires_at <= ? OR used_at IS NOT NULL", (now,))
    token = secrets.token_urlsafe(16)
    conn.execute(
        "INSERT INTO upload_tokens (token_sha256, user_id, project_id, name, type, expires_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (_digest(token), user_id, project_id, name, DatasetType(type).value, now + ttl_secs),
    )
    return token


def claim(conn: sqlite3.Connection, token: str, *, now: float | None = None) -> UploadToken | None:
    """Claim a token that is unused, unclaimed and unexpired and return its record; a second
    caller, and any other token, gets None."""
    now = time.time() if now is None else now
    digest = _digest(token)
    cur = conn.execute(
        "UPDATE upload_tokens SET claimed_at = ?"
        " WHERE token_sha256 = ? AND used_at IS NULL AND claimed_at IS NULL AND expires_at > ?",
        (now, digest, now),
    )
    if cur.rowcount != 1:
        return None
    row = conn.execute(
        "SELECT id, user_id, project_id, name, type FROM upload_tokens WHERE token_sha256 = ?",
        (digest,),
    ).fetchone()
    return UploadToken(
        row["id"], row["user_id"], row["project_id"], row["name"], DatasetType(row["type"])
    )


def release(conn: sqlite3.Connection, token_id: int) -> None:
    """Give a claimed token back, after an upload that did not produce a dataset."""
    conn.execute(
        "UPDATE upload_tokens SET claimed_at = NULL WHERE id = ? AND used_at IS NULL", (token_id,)
    )


def finish(conn: sqlite3.Connection, token_id: int, *, now: float | None = None) -> None:
    """Consume the token: its upload became a dataset."""
    now = time.time() if now is None else now
    conn.execute("UPDATE upload_tokens SET used_at = ? WHERE id = ?", (now, token_id))
