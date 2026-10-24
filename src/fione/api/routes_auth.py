"""Login, logout, the current user, password change and first-admin setup.

Password checks are throttled per (client address, lowercased username), whether or not the
user exists, and every scrypt computation holds a ``password_work`` slot.
"""

import logging

from fastapi import APIRouter, Depends, Request, Response

from fione.api.deps import AuthDep, Conn, browser_safe_json, client_ip
from fione.api.errors import ApiError, service_errors
from fione.api.schemas import FirstAdminIn, LoginIn, PasswordChangeIn, user_out
from fione.api.security import (
    SESSION_COOKIE,
    discard_setup_token,
    password_work,
    read_setup_token,
    tokens_equal,
)
from fione.auth import service as auth_service
from fione.auth.roles import User

router = APIRouter(prefix="/auth", tags=["auth"])
setup_log = logging.getLogger("fione.setup")

# Usernames cannot contain "#", so this throttle key never collides with a user's.
_SETUP_THROTTLE_USER = "#first-admin"


def _throttle_key(request: Request, username: str) -> tuple[str, str]:
    return client_ip(request), username.lower()


def _check_throttle(request: Request, key: tuple[str, str]) -> None:
    retry = request.app.state.throttle.retry_after(key)
    if retry is not None:
        message = "too many failed attempts; try again later"
        raise ApiError(429, "throttled", message, {"Retry-After": str(retry)})


def _start_session(request: Request, response: Response, conn, user: User) -> dict:
    found = auth_service.user_for_session(conn, user.id)
    if found is None:
        raise ApiError(401, "unauthorized", "the user no longer exists")
    settings = request.app.state.settings
    value, session = request.app.state.signer.issue(user.id, found[1])
    response.set_cookie(
        SESSION_COOKIE,
        value,
        max_age=settings.session_max_age_secs,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return {"user": user_out(found[0]), "csrf_token": session.csrf}


@router.post("/login", dependencies=[Depends(browser_safe_json)])
def login(body: LoginIn, request: Request, response: Response, conn: Conn) -> dict:
    key = _throttle_key(request, body.username)
    _check_throttle(request, key)
    with password_work():
        user = auth_service.authenticate(conn, body.username, body.password)
    throttle = request.app.state.throttle
    if user is None:
        throttle.failure(key)
        raise ApiError(401, "invalid_credentials", "invalid username or password")
    throttle.success(key)
    return _start_session(request, response, conn, user)


@router.post("/logout", status_code=204)
def logout(auth: AuthDep, response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me")
def me(auth: AuthDep) -> dict:
    """The current user and, for cookie sessions, the CSRF token unsafe requests must send."""
    return {
        "user": user_out(auth.user),
        "csrf_token": auth.session.csrf if auth.session else None,
    }


@router.get("/status")
def status(conn: Conn) -> dict:
    return {"needs_first_admin": auth_service.needs_first_admin(conn)}


@router.post("/first-admin", dependencies=[Depends(browser_safe_json)])
def first_admin(body: FirstAdminIn, request: Request, response: Response, conn: Conn) -> dict:
    """Create the first admin with the setup token printed to the server log at startup."""
    key = (client_ip(request), _SETUP_THROTTLE_USER)
    _check_throttle(request, key)
    already = ApiError(409, "already_set_up", "an administrator already exists")
    if not auth_service.needs_first_admin(conn):
        raise already
    settings = request.app.state.settings
    expected = read_setup_token(settings)
    if expected is None or not tokens_equal(expected, body.setup_token):
        request.app.state.throttle.failure(key)
        raise ApiError(403, "invalid_setup_token", "invalid setup token")
    try:
        with password_work(), service_errors():
            user = auth_service.create_first_admin(conn, body.username, body.password)
    except auth_service.AlreadySetUp:
        raise already from None
    request.app.state.throttle.success(key)
    discard_setup_token(settings)
    setup_log.warning("The first administrator %r was created.", user.username)
    return _start_session(request, response, conn, user)


@router.post("/password")
def change_password(
    body: PasswordChangeIn, auth: AuthDep, request: Request, response: Response, conn: Conn
) -> dict:
    """Change one's own password. Every existing session of the user ends; a cookie session
    gets a new cookie (and CSRF token) in the response."""
    key = _throttle_key(request, auth.user.username)
    _check_throttle(request, key)
    throttle = request.app.state.throttle
    with password_work():
        if auth_service.authenticate(conn, auth.user.username, body.current_password) is None:
            throttle.failure(key)
            raise ApiError(403, "invalid_credentials", "the current password is wrong")
        with service_errors():
            auth_service.set_password(conn, auth.user.id, body.new_password)
    throttle.success(key)
    if auth.via == "cookie":
        return _start_session(request, response, conn, auth.user)
    return {"user": user_out(auth.user), "csrf_token": None}
