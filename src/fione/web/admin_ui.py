"""Administration: the users and the system status, for administrators only (403 for anyone
else, as the API's admin dependency), with the API's services and rules.

Users: create, change the role, set a new password (which ends that user's sessions) and
delete; the service refuses the last admin and one's own role or account, and the reason is
shown on the page. System: what ``/api/v1/system/status`` reports plus failed jobs of the
last day, the workers and the uptime; never a secret, a path, a URL or the environment.
"""

import logging
import math
import time

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from fione import i18n
from fione.api.deps import Auth, Conn
from fione.api.routes_system import system_status
from fione.api.schemas import MAX_PASSWORD_LENGTH
from fione.api.security import password_work
from fione.auth import service as auth_service
from fione.auth.passwords import MIN_PASSWORD_LENGTH
from fione.auth.roles import Role
from fione.auth.service import UserConflict, UsernameError, UserNotFound
from fione.web.access import SmallForm, admin_only, field, form_auth, parse_id, signed_in
from fione.web.easyml import STOP_POLLING
from fione.web.views import UiError, language, render

router = APIRouter(include_in_schema=False)
log = logging.getLogger(__name__)

USERS_PER_PAGE = 50
MAX_USERNAME = 64  # as the API's username
DONE = ("created", "role", "password", "deleted")
POLL_SECS = 10
DAY_SECS = 24 * 3600


def _admin(request: Request, conn) -> Auth:
    return admin_only(signed_in(request, conn))


def _post_admin(request: Request, conn, form) -> Auth:
    return admin_only(form_auth(request, conn, form))


def _page_number(value: str | None, pages: int) -> int:
    if value is None or not value.isascii() or not value.isdigit() or len(value) > 12:
        return 1
    return min(pages, max(1, int(value)))


def _users_view(
    request: Request,
    conn,
    auth: Auth,
    *,
    page: str | None = None,
    status: int = 200,
    problem: dict | None = None,
    errors: dict | None = None,
    new: dict | None = None,
) -> Response:
    total = auth_service.count_users(conn)
    pages = max(1, math.ceil(total / USERS_PER_PAGE))
    number = _page_number(page or request.query_params.get("page"), pages)
    rows = auth_service.page_users(conn, limit=USERS_PER_PAGE, offset=(number - 1) * USERS_PER_PAGE)
    done = request.query_params.get("done")
    return render(
        request,
        "admin_users.html",
        auth,
        status=status,
        nav="users",
        rows=rows,
        total=total,
        page_number=number,
        pages=pages,
        roles=[r.value for r in Role],
        problem=problem,
        errors=errors or {},
        new=new or {"username": "", "role": Role.EDITOR.value},
        done=done if done in DONE and status == 200 else None,
        min_password=MIN_PASSWORD_LENGTH,
        max_password=MAX_PASSWORD_LENGTH,
        here="/admin/users",
    )


@router.get("/admin/users")
def users(request: Request, conn: Conn) -> Response:
    return _users_view(request, conn, _admin(request, conn))


def _password_ok(password: str) -> bool:
    return MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH


@router.post("/admin/users")
def create_user(request: Request, conn: Conn, form: SmallForm) -> Response:
    auth = _post_admin(request, conn, form)
    username, password, role = field(form, "username"), field(form, "password"), field(form, "role")
    roles = {r.value for r in Role}
    new = {"username": username[:200], "role": role if role in roles else Role.EDITOR.value}
    errors = {}
    if not 1 <= len(username) <= MAX_USERNAME:
        errors["username"] = "users.error.username"
    if not _password_ok(password):
        errors["password"] = "users.error.password"
    if role not in roles:
        errors["role"] = "users.error.role"
    if not errors:
        try:
            with password_work():
                auth_service.create_user(conn, username, password, Role(role))
        except UsernameError as e:
            errors["username"] = f"users.error.username_{e.code}"
    if errors:
        return _users_view(request, conn, auth, status=422, errors=errors, new=new)
    pages = max(1, math.ceil(auth_service.count_users(conn) / USERS_PER_PAGE))
    return RedirectResponse(f"/admin/users?done=created&page={pages}", 303)


def _target(conn, uid: str):
    user = auth_service.get_user(conn, parse_id(uid))
    if user is None:
        raise UiError(404, "error.not_found")
    return user


def _refused(request, conn, auth, form, user, key: str, status=409, **params) -> Response:
    """The users page again, saying why nothing was changed for ``user``."""
    problem = {"username": user.username, "key": key, "params": params}
    page = field(form, "page")
    return _users_view(request, conn, auth, page=page, status=status, problem=problem)


def _back(form, done: str) -> RedirectResponse:
    page = field(form, "page")
    page = page if page.isascii() and page.isdigit() and len(page) <= 12 else "1"
    return RedirectResponse(f"/admin/users?done={done}&page={page}", 303)


@router.post("/admin/users/{uid}/role")
def change_role(request: Request, conn: Conn, uid: str, form: SmallForm) -> Response:
    auth = _post_admin(request, conn, form)
    user = _target(conn, uid)
    role = field(form, "role")
    if role not in {r.value for r in Role}:
        return _refused(request, conn, auth, form, user, "users.error.role", 422)
    try:
        auth_service.set_role(conn, user.id, Role(role), actor_id=auth.user.id)
    except UserNotFound:
        raise UiError(404, "error.not_found") from None
    except UserConflict as e:
        return _refused(request, conn, auth, form, user, f"users.refused.{e.code}", n=e.count)
    return _back(form, "role")


@router.post("/admin/users/{uid}/password")
def reset_password(request: Request, conn: Conn, uid: str, form: SmallForm) -> Response:
    """Set a new password, which ends the user's sessions. Like the API, no current password
    is asked for, so there is no throttle; the hashing holds a ``password_work`` slot."""
    auth = _post_admin(request, conn, form)
    user = _target(conn, uid)
    password = field(form, "password")
    if not _password_ok(password):
        key, n = "users.error.password", MIN_PASSWORD_LENGTH
        return _refused(request, conn, auth, form, user, key, 422, n=n)
    try:
        with password_work():
            auth_service.set_password(conn, user.id, password)
    except UserNotFound:
        raise UiError(404, "error.not_found") from None
    return _back(form, "password")


@router.post("/admin/users/{uid}/delete")
def delete_user(request: Request, conn: Conn, uid: str, form: SmallForm) -> Response:
    auth = _post_admin(request, conn, form)
    user = _target(conn, uid)
    try:
        auth_service.delete_user(conn, user.id, actor_id=auth.user.id)
    except UserNotFound:
        raise UiError(404, "error.not_found") from None
    except UserConflict as e:
        return _refused(request, conn, auth, form, user, f"users.refused.{e.code}", n=e.count)
    return _back(form, "deleted")


# --- system status ------------------------------------------------------------------------


def _uptime(seconds: float) -> tuple[str, dict]:
    """The uptime's message key and values: its two largest units."""
    minutes = int(seconds // 60)
    d, h, m = minutes // 1440, minutes // 60 % 24, minutes % 60
    if d:
        return "system.uptime_days", {"d": d, "h": h}
    return ("system.uptime_hours", {"h": h, "m": m}) if h else ("system.uptime_minutes", {"m": m})


def _system_context(request: Request, conn) -> dict:
    state = request.app.state
    settings = state.settings
    status = system_status(request, conn)
    failed = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE status = 'failed' AND finished_at >= ?",
        (time.time() - DAY_SECS,),
    ).fetchone()[0]
    return {
        "info": status,
        "failed_day": failed,
        "workers": state.runner.worker_count() if state.runner is not None else 0,
        "train_limit": settings.max_concurrent_train_jobs,
        "short_limit": settings.max_concurrent_short_jobs,
        "uptime": _uptime(time.monotonic() - state.started_at),
        "checked": time.time(),
        "poll_secs": POLL_SECS,
    }


@router.get("/admin/system")
def system(request: Request, conn: Conn) -> Response:
    """The status page; HTMX polls it every 10 s for the status card. If the card can no
    longer be shown (signed out elsewhere: sent to the login page; no longer an admin; an
    error), the answer is 286 with a final card, and polling stops."""
    polling = bool(request.headers.get("hx-request"))
    try:
        auth = _admin(request, conn)
        context = _system_context(request, conn)
    except UiError as e:
        if not polling or e.status == 401:
            raise
        return _status_gone(request, e.key)
    except Exception:
        if not polling:
            raise
        log.exception("the system status could not be shown")
        return _status_gone(request, "error.generic")
    template = "_system_status.html" if polling else "admin_system.html"
    return render(request, template, auth, nav="system", here="/admin/system", **context)


def _status_gone(request: Request, key: str) -> Response:
    return render(
        request,
        "_system_gone.html",
        status=STOP_POLLING,
        message=i18n.t(key, language(request)),
    )
