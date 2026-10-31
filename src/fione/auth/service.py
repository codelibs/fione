import re
import sqlite3
from dataclasses import dataclass
from functools import cache

from fione import db
from fione.auth.passwords import hash_password, verify_password
from fione.auth.roles import Role, User
from fione.auth.tokens import hash_token, new_token

_USERNAME_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")


class UserNotFound(KeyError):
    pass


class UserConflict(Exception):
    """The change would break an invariant (the last admin, one's own account, owned data);
    the message is for the user, ``code`` (and ``count``) name it for a translated one."""

    def __init__(self, message: str, code: str = "conflict", count: int | None = None):
        super().__init__(message)
        self.code = code
        self.count = count


class AlreadySetUp(UserConflict):
    pass


class UsernameError(ValueError):
    """A username that cannot be used: ``code`` is ``invalid`` or ``taken``."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ApiToken:
    """A token's metadata; the plaintext is only ever returned once, by ``create_token``."""

    id: int
    user_id: int
    name: str
    created_at: str
    revoked: bool


@cache
def _dummy_hash() -> str:
    """Valid hash of a throwaway password, so unknown usernames cost a real verify."""
    return hash_password("dummy-password-for-timing")


def warm_up() -> None:
    """Compute the dummy hash now, so the first unknown-user login costs one hash like others."""
    _dummy_hash()


def _user(row: sqlite3.Row) -> User:
    return User(id=row["id"], username=row["username"], role=Role(row["role"]))


def create_user(conn: sqlite3.Connection, username: str, password: str, role: Role) -> User:
    _check_username(username)
    role = Role(role)
    return _insert_user(conn, username, hash_password(password), role)


def create_first_admin(conn: sqlite3.Connection, username: str, password: str) -> User:
    """Create the first admin; ``AlreadySetUp`` once any admin exists, even under a race."""
    _check_username(username)
    password_hash = hash_password(password)  # slow: before the write lock is taken
    with db.immediate(conn):
        if not needs_first_admin(conn):
            raise AlreadySetUp("an administrator already exists")
        return _insert_user(conn, username, password_hash, Role.ADMIN)


def _check_username(username: str) -> None:
    if not _USERNAME_RE.fullmatch(username):
        raise UsernameError("username must match [A-Za-z0-9._-]{1,64}", "invalid")


def _insert_user(conn: sqlite3.Connection, username: str, password_hash: str, role: Role) -> User:
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role.value),
        )
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e):
            raise UsernameError("username already exists", "taken") from e
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


def get_user(conn: sqlite3.Connection, user_id: int) -> User | None:
    row = conn.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user(row) if row else None


def list_users(conn: sqlite3.Connection) -> list[User]:
    return [_user(r) for r in conn.execute("SELECT id, username, role FROM users ORDER BY id")]


def page_users(conn: sqlite3.Connection, *, limit: int, offset: int = 0) -> list[tuple[User, str]]:
    """One page of the users by id, each with its creation time (UTC)."""
    rows = conn.execute(
        "SELECT id, username, role, created_at FROM users ORDER BY id LIMIT ? OFFSET ?",
        (limit, offset),
    )
    return [(_user(r), r["created_at"]) for r in rows]


def count_users(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def user_for_session(conn: sqlite3.Connection, user_id: int) -> tuple[User, str] | None:
    """The user and their current password hash, which sessions are bound to: a new password
    or a new user that reuses a deleted user's id must not inherit old sessions."""
    row = conn.execute(
        "SELECT id, username, role, password_hash FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return (_user(row), row["password_hash"]) if row else None


def set_password(conn: sqlite3.Connection, user_id: int, password: str) -> None:
    cur = conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), user_id)
    )
    if cur.rowcount == 0:
        raise UserNotFound(user_id)


def _check_not_last_admin(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    if row["role"] != Role.ADMIN.value:
        return
    admins = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = ?", (Role.ADMIN.value,)
    ).fetchone()[0]
    if admins <= 1:
        raise UserConflict("the last admin cannot be removed or demoted", "last_admin")


def _locked_user(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise UserNotFound(user_id)
    return row


def set_role(
    conn: sqlite3.Connection, user_id: int, role: Role, *, actor_id: int | None = None
) -> User:
    """Change the role; refused (``UserConflict``) for the last admin and, when the admin
    ``actor_id`` is the user, for giving up one's own admin role."""
    role = Role(role)
    with db.immediate(conn):
        row = _locked_user(conn, user_id)
        if role != Role.ADMIN:
            _check_not_last_admin(conn, row)
            if user_id == actor_id:
                raise UserConflict("you cannot remove your own admin role", "self_role")
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role.value, user_id))
    user = get_user(conn, user_id)
    assert user is not None
    return user


def delete_user(conn: sqlite3.Connection, user_id: int, *, actor_id: int | None = None) -> None:
    """Delete a user with their tokens and memberships; refused (``UserConflict``) for the
    last admin, for oneself (the admin ``actor_id``) and for owners of projects or jobs,
    which must be deleted first."""
    with db.immediate(conn):
        row = _locked_user(conn, user_id)
        _check_not_last_admin(conn, row)
        if user_id == actor_id:
            raise UserConflict("you cannot delete your own account", "self_delete")
        projects = conn.execute(
            "SELECT COUNT(*) FROM projects WHERE owner_id = ?", (user_id,)
        ).fetchone()[0]
        if projects:
            message = f"the user owns {projects} project(s); delete them first"
            raise UserConflict(message, "owns_projects", projects)
        jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE owner_id = ?", (user_id,)).fetchone()
        if jobs[0]:
            message = f"the user owns {jobs[0]} job(s); delete them first"
            raise UserConflict(message, "owns_jobs", jobs[0])
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def _api_token(row: sqlite3.Row) -> ApiToken:
    return ApiToken(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        created_at=row["created_at"],
        revoked=row["revoked_at"] is not None,
    )


_TOKEN_COLUMNS = "id, user_id, name, created_at, revoked_at"


def create_token(conn: sqlite3.Connection, user_id: int, name: str) -> tuple[ApiToken, str]:
    """Create an API token: its record and its plaintext; only the sha256 is stored."""
    token = new_token()
    cur = conn.execute(
        "INSERT INTO api_tokens (user_id, name, token_sha256) VALUES (?, ?, ?)",
        (user_id, name, hash_token(token)),
    )
    record = get_token(conn, cur.lastrowid)
    assert record is not None
    return record, token


def issue_token(conn: sqlite3.Connection, user_id: int, name: str) -> str:
    """Create an API token and return its plaintext; only the sha256 is stored."""
    return create_token(conn, user_id, name)[1]


def get_token(conn: sqlite3.Connection, token_id: int) -> ApiToken | None:
    row = conn.execute(
        f"SELECT {_TOKEN_COLUMNS} FROM api_tokens WHERE id = ?", (token_id,)
    ).fetchone()
    return _api_token(row) if row else None


def list_tokens(conn: sqlite3.Connection, user_id: int) -> list[ApiToken]:
    rows = conn.execute(
        f"SELECT {_TOKEN_COLUMNS} FROM api_tokens WHERE user_id = ? ORDER BY id", (user_id,)
    )
    return [_api_token(r) for r in rows]


def page_tokens(
    conn: sqlite3.Connection, user_id: int, *, limit: int, offset: int = 0
) -> list[ApiToken]:
    """One page of the user's tokens, newest first."""
    rows = conn.execute(
        f"SELECT {_TOKEN_COLUMNS} FROM api_tokens WHERE user_id = ?"
        " ORDER BY id DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset),
    )
    return [_api_token(r) for r in rows]


def count_tokens(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) FROM api_tokens WHERE user_id = ?", (user_id,))
    return row.fetchone()[0]


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
