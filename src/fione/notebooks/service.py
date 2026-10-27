"""Notebook sessions: a user's running container, as Fione knows it.

A start makes a nonce (the container's key is derived from it), a ``notebook`` token for the
SDK inside the container and a ``notebook_sessions`` row, then asks the launcher for the
container. The session ends (its token revoked, its row deleted) when the user stops it, when
the launcher reports the container gone (culled or expired), when a start fails, and when the
user loses the permission, has their password reset or is deleted (then their notebook files
are removed too).

A user's starts, state checks and stops take turns (one process serves Fione), so a status
check cannot end a session that a start has just made.
"""

import contextlib
import logging
import secrets
import sqlite3
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime

from fione import db
from fione.auth import service as auth_service
from fione.auth.roles import User
from fione.auth.tokens import TokenScope
from fione.config import Settings
from fione.notebooks.launch import LAUNCH_PARAM, launch_key, sign_launch_token
from fione.notebooks.launcher import Launcher, LauncherError, NotebookState

log = logging.getLogger(__name__)

TOKEN_NAME = "notebook"
_EXPIRY_FORMAT = "%Y-%m-%d %H:%M:%S"  # as auth_service.expiry_after writes it
_locks: dict[int, threading.Lock] = {}
_locks_guard = threading.Lock()


class NotebookNotRunning(Exception):
    """The user has no live notebook session to sign in to."""


class NotebookNotAllowed(Exception):
    """The user may not use notebooks (any more)."""


def _user_lock(user_id: int) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(user_id, threading.Lock())


def _live_session(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT nonce FROM notebook_sessions WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP",
        (user_id,),
    ).fetchone()


def _end_locked(conn: sqlite3.Connection, user_id: int) -> None:
    row = conn.execute(
        "SELECT token_id FROM notebook_sessions WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is not None:
        auth_service.revoke_token(conn, row["token_id"])
        conn.execute("DELETE FROM notebook_sessions WHERE user_id = ?", (user_id,))


def _end(conn: sqlite3.Connection, user_id: int) -> None:
    """Revoke the session's token and delete its row, if there is one."""
    with db.immediate(conn):
        _end_locked(conn, user_id)


def state(conn: sqlite3.Connection, launcher: Launcher, user: User) -> NotebookState:
    """The container's state; a session whose container is gone ends here. A container without
    a live session is ``absent`` too: nobody can sign in to it, and a start replaces it."""
    with _user_lock(user.id):
        current = launcher.status(user.id)
        if current == "absent":
            _end(conn, user.id)
        elif _live_session(conn, user.id) is None:
            return "absent"
        return current


def start(
    conn: sqlite3.Connection, launcher: Launcher, settings: Settings, secret: bytes, user: User
) -> NotebookState:
    """Start the user's notebook unless it is starting or running with a live session. A
    container left without one (an earlier failed start) is replaced. On any failure the new
    session ends before the error is raised.

    The permission is checked again with the session's write (``NotebookNotAllowed``): a
    revocation committed before it is seen here, and one committed after it finds the session
    and ends it."""
    with _user_lock(user.id):
        current = launcher.status(user.id)
        if current != "absent" and _live_session(conn, user.id) is not None:
            return current
        expires = int(time.time()) + settings.notebook_max_lifetime_secs
        nonce = secrets.token_urlsafe(16)
        with db.immediate(conn):
            current_user = auth_service.get_user(conn, user.id)
            if current_user is None or not auth_service.can_use_notebook(conn, current_user):
                raise NotebookNotAllowed(user.id)
            _end_locked(conn, user.id)
            record, token = auth_service.create_token(
                conn,
                user.id,
                TOKEN_NAME,
                scope=TokenScope.NOTEBOOK,
                expires_at=datetime.fromtimestamp(expires, UTC).strftime(_EXPIRY_FORMAT),
            )
            conn.execute(
                "INSERT INTO notebook_sessions (user_id, nonce, token_id, expires_at)"
                " VALUES (?, ?, ?, ?)",
                (user.id, nonce, record.id, record.expires_at),
            )
        body = {
            "launch_key": launch_key(secret, user.id, nonce).hex(),
            "cookie_secret": secrets.token_hex(32),  # fresh per start, kept nowhere
            "token": token,
            "fione_origin": settings.public_url,
            "expires_at": expires,
        }
        try:
            try:
                return launcher.ensure(user.id, body)
            except LauncherError as e:
                if e.code != "exists":
                    raise
            launcher.stop(user.id)  # a container without a session: replace it, once
            return launcher.ensure(user.id, body)
        except BaseException as e:
            _end(conn, user.id)
            if isinstance(e, LauncherError) and e.code == "unreachable":
                # It may have started the container before the answer was lost: free the slot.
                with contextlib.suppress(LauncherError):
                    launcher.stop(user.id)
            raise


def stop(conn: sqlite3.Connection, launcher: Launcher, user_id: int) -> None:
    """Remove the container and end the session; the token is revoked even when the launcher
    fails (its error is raised after)."""
    with _user_lock(user_id):
        try:
            launcher.stop(user_id)
        finally:
            _end(conn, user_id)


def purge(conn: sqlite3.Connection, launcher: Launcher, user_id: int) -> None:
    """``stop``, and the user's notebook files are removed: after the user is deleted, so a
    later user given the same id starts empty."""
    with _user_lock(user_id):
        try:
            launcher.purge(user_id)
        finally:
            _end(conn, user_id)


def stop_unless_allowed(conn: sqlite3.Connection, launcher: Launcher, user_id: int) -> None:
    """``stop``, unless the user (read fresh) may still use notebooks."""
    user = auth_service.get_user(conn, user_id)
    if user is None or not auth_service.can_use_notebook(conn, user):
        stop(conn, launcher, user_id)


def quietly(
    action: Callable[[sqlite3.Connection, Launcher, int], None],
    conn: sqlite3.Connection,
    launcher: Launcher | None,
    user_id: int,
) -> None:
    """``stop``, ``stop_unless_allowed`` or ``purge`` for a change to a user's account (nothing
    when notebooks are off). A launcher error is logged by its code and never fails the change;
    the token is revoked either way."""
    if launcher is None:
        return
    try:
        action(conn, launcher, user_id)
    except LauncherError as e:
        log.warning("the notebook of user %s could not be stopped: %s", user_id, e.code)


def launch_url(conn: sqlite3.Connection, settings: Settings, secret: bytes, user: User) -> str:
    """The URL that signs the user into their container (a new launch token each time);
    ``NotebookNotRunning`` without a live session."""
    row = _live_session(conn, user.id)
    if row is None:
        raise NotebookNotRunning(user.id)
    token = sign_launch_token(launch_key(secret, user.id, row["nonce"]), user=user)
    base = f"{settings.notebook_url}/user/{user.id}"
    return f"{base}/login?{LAUNCH_PARAM}={token}&next=/user/{user.id}/lab"
