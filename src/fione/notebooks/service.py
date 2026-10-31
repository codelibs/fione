"""Notebook sessions: a user's running container, as Fione knows it.

A start makes a nonce (the container's key is derived from it), a ``notebook`` token for the
SDK inside the container and a ``notebook_sessions`` row, then asks the launcher for the
container. The session ends (its token revoked, its row deleted) when the user stops it, when
the launcher reports the container gone (culled or expired), when a start fails, and when the
user loses the permission or the admin role, gets a new password or is deleted (then their
notebook files are removed too).

A stop or purge the launcher fails is pending (``notebook_pending_stops``): the session has
ended anyway, a start for that user is refused until it is done, and it is retried at the
start of every later call here and every minute (``PendingStopRetrier``). A container that
runs without a live session is stopped when its state is read.

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
from pathlib import Path

from fione import db
from fione.auth import service as auth_service
from fione.auth.roles import User
from fione.auth.tokens import TokenScope
from fione.config import Settings
from fione.notebooks.launch import LAUNCH_PARAM, launch_key, sign_launch_token
from fione.notebooks.launcher import Launcher, LauncherError, NotebookState

log = logging.getLogger(__name__)

TOKEN_NAME = "notebook"
RETRY_SECS = 60.0  # how often PendingStopRetrier retries pending stops
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


def _pending(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT purge FROM notebook_pending_stops WHERE user_id = ?", (user_id,)
    ).fetchone()


def _remove_locked(conn: sqlite3.Connection, launcher: Launcher, user_id: int, purge: bool) -> None:
    """Remove the container (``purge``: and the files) under the user's lock. A pending purge
    makes it a purge too; success clears what was pending, a failure is recorded as pending
    (a purge is never downgraded) and raised."""
    pending = _pending(conn, user_id)
    purge = purge or (pending is not None and bool(pending["purge"]))
    try:
        (launcher.purge if purge else launcher.stop)(user_id)
    except LauncherError:
        conn.execute(
            "INSERT INTO notebook_pending_stops (user_id, purge) VALUES (?, ?)"
            " ON CONFLICT (user_id) DO UPDATE SET purge = MAX(purge, excluded.purge),"
            " since = CURRENT_TIMESTAMP",  # to the back: one stuck row never blocks the rest
            (user_id, int(purge)),
        )
        raise
    conn.execute("DELETE FROM notebook_pending_stops WHERE user_id = ?", (user_id,))


def retry_pending(conn: sqlite3.Connection, launcher: Launcher) -> None:
    """Retry the pending stops and purges, oldest first, until one fails again (the launcher
    is likely still failing; that is logged by its code). A failed row goes to the back, so
    one that keeps failing for its own reason does not hold up the others for more than one
    pass. Never raises a launcher error."""
    rows = conn.execute(
        "SELECT user_id FROM notebook_pending_stops ORDER BY since, user_id"
    ).fetchall()
    for row in rows:
        user_id = row["user_id"]
        with _user_lock(user_id):
            if _pending(conn, user_id) is None:  # done meanwhile
                continue
            try:
                _remove_locked(conn, launcher, user_id, purge=False)
            except LauncherError as e:
                log.warning("a pending notebook stop failed again: %s", e.code)
                return


def state(conn: sqlite3.Connection, launcher: Launcher, user: User) -> NotebookState:
    """The container's state; a session whose container is gone ends here. A container without
    a live session is stopped and ``absent``: nobody can sign in to it, and it may be one that
    a revocation could not stop."""
    retry_pending(conn, launcher)
    with _user_lock(user.id):
        current = launcher.status(user.id)
        if current == "absent":
            _end(conn, user.id)
        elif _live_session(conn, user.id) is None:
            _remove_locked(conn, launcher, user.id, purge=False)
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
    and ends it. While a stop of the user's notebook is still pending, the start fails
    (``unreachable``): user ids are reused, and a pending purge must not remove a new
    notebook's files."""
    retry_pending(conn, launcher)
    with _user_lock(user.id):
        if _pending(conn, user.id) is not None:
            raise LauncherError("unreachable", "an earlier stop of this notebook is pending")
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
                # It may have started the container before the answer was lost: free the slot
                # (or leave the stop pending).
                with contextlib.suppress(LauncherError):
                    _remove_locked(conn, launcher, user.id, purge=False)
            raise


def stop(conn: sqlite3.Connection, launcher: Launcher, user_id: int) -> None:
    """Remove the container and end the session; the token is revoked even when the launcher
    fails (the stop is then pending, and the error is raised after)."""
    retry_pending(conn, launcher)
    with _user_lock(user_id):
        try:
            _remove_locked(conn, launcher, user_id, purge=False)
        finally:
            _end(conn, user_id)


def purge(conn: sqlite3.Connection, launcher: Launcher, user_id: int) -> None:
    """``stop``, and the user's notebook files are removed: after the user is deleted, so a
    later user given the same id starts empty."""
    retry_pending(conn, launcher)
    with _user_lock(user_id):
        try:
            _remove_locked(conn, launcher, user_id, purge=True)
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
) -> bool:
    """``stop``, ``stop_unless_allowed`` or ``purge`` for a change to a user's account (nothing
    when notebooks are off). A launcher error is logged by its code and never fails the change;
    the token is revoked either way. False when the stop could not be confirmed: it is pending
    and retried."""
    if launcher is None:
        return True
    try:
        action(conn, launcher, user_id)
    except LauncherError as e:
        log.warning("the notebook of user %s could not be stopped: %s", user_id, e.code)
        return False
    return True


def launch_url(conn: sqlite3.Connection, settings: Settings, secret: bytes, user: User) -> str:
    """The URL that signs the user into their container (a new launch token each time);
    ``NotebookNotRunning`` without a live session."""
    row = _live_session(conn, user.id)
    if row is None:
        raise NotebookNotRunning(user.id)
    token = sign_launch_token(launch_key(secret, user.id, row["nonce"]), user=user)
    base = f"{settings.notebook_url}/user/{user.id}"
    return f"{base}/login?{LAUNCH_PARAM}={token}&next=/user/{user.id}/lab"


class PendingStopRetrier:
    """Retries pending stops every ``interval`` seconds in a thread of its own, with its own
    database connection, from Fione's lifespan (when notebooks are on)."""

    def __init__(self, db_path: Path, launcher: Launcher, interval: float = RETRY_SECS):
        self._db_path = db_path
        self._launcher = launcher
        self._interval = interval
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("pending stop retrier already started")
        self._stopping.clear()
        self._thread = threading.Thread(target=self._loop, name="fione-notebook-stops", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stopping.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _loop(self) -> None:
        while not self._stopping.wait(self._interval):
            try:
                with contextlib.closing(db.connect(self._db_path)) as conn:
                    retry_pending(conn, self._launcher)
            except Exception as e:  # the next round tries again
                log.warning("retrying pending notebook stops failed: %s", type(e).__name__)
