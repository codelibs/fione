import re
import sqlite3
from functools import cache

from fione.auth.passwords import hash_password, verify_password
from fione.auth.roles import Role, User
from fione.auth.tokens import hash_token, new_token

_USERNAME_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")


@cache
def _dummy_hash() -> str:
    """Valid hash of a throwaway password, so unknown usernames cost a real verify."""
    return hash_password("dummy-password-for-timing")


def _user(row: sqlite3.Row) -> User:
    return User(id=row["id"], username=row["username"], role=Role(row["role"]))


def create_user(conn: sqlite3.Connection, username: str, password: str, role: Role) -> User:
    if not _USERNAME_RE.fullmatch(username):
        raise ValueError("username must match [A-Za-z0-9._-]{1,64}")
    role = Role(role)
    password_hash = hash_password(password)
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role.value),
        )
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e):
            raise ValueError("username already exists") from e
        raise
    assert cur.lastrowid is not None
    return User(id=cur.lastrowid, username=username, role=role)


def authenticate(conn: sqlite3.Connection, username: str, password: str) -> User | None:
    """Return the user for valid credentials, else None; unknown users cost the same hash."""
    row = conn.execute(
        "SELECT id, username, role, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        verify_password(password, _dummy_hash())
        return None
    return _user(row) if verify_password(password, row["password_hash"]) else None


def needs_first_admin(conn: sqlite3.Connection) -> bool:
    return (
        conn.execute("SELECT 1 FROM users WHERE role = ? LIMIT 1", (Role.ADMIN.value,)).fetchone()
        is None
    )


def issue_token(conn: sqlite3.Connection, user_id: int, name: str) -> str:
    """Create an API token and return its plaintext; only the sha256 is stored."""
    token = new_token()
    conn.execute(
        "INSERT INTO api_tokens (user_id, name, token_sha256) VALUES (?, ?, ?)",
        (user_id, name, hash_token(token)),
    )
    return token


def user_from_token(conn: sqlite3.Connection, token: str) -> User | None:
    row = conn.execute(
        "SELECT u.id, u.username, u.role FROM api_tokens t JOIN users u ON u.id = t.user_id"
        " WHERE t.token_sha256 = ? AND t.revoked_at IS NULL",
        (hash_token(token),),
    ).fetchone()
    return _user(row) if row else None


def revoke_token(conn: sqlite3.Connection, token_id: int) -> None:
    conn.execute(
        "UPDATE api_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE id = ? AND revoked_at IS NULL",
        (token_id,),
    )
