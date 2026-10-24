"""Request-scoped dependencies: the database connection, authentication and authorization.

Authentication picks one mechanism per request. With an ``Authorization: Bearer`` header the
request is a bearer-token request and nothing else is considered; otherwise (no header, or
another scheme, which is ignored) the session cookie is used. Both reload the user from the
database, so role changes and deletions apply at once. Cookie-authenticated unsafe requests
must echo the session's CSRF token in ``X-CSRF-Token``.
"""

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Request

from fione import db
from fione.api.errors import ApiError, not_found
from fione.api.security import SESSION_COOKIE, Session, origin_matches, tokens_equal
from fione.auth import service as auth_service
from fione.auth.roles import ProjectAccess, Role, User
from fione.auth.roles import project_access as membership
from fione.projects.service import Project, ProjectNotFound, require_project

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    # Used by one request at a time, but FastAPI may run this dependency and the endpoint
    # in different threadpool threads, hence check_same_thread=False.
    conn = db.connect(request.app.state.db_path, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


@dataclass(frozen=True)
class Auth:
    user: User
    via: Literal["cookie", "bearer"]
    session: Session | None


def _unauthorized(message: str) -> ApiError:
    return ApiError(401, "unauthorized", message, {"WWW-Authenticate": "Bearer"})


def get_auth(request: Request, conn: Conn) -> Auth:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer":
        user = auth_service.user_from_token(conn, token.strip()) if token.strip() else None
        if user is None:
            raise _unauthorized("invalid or revoked API token")
        return Auth(user, "bearer", None)
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise _unauthorized("authentication required")
    signer = request.app.state.signer
    user_id = signer.unverified_user_id(cookie)
    found = None if user_id is None else auth_service.user_for_session(conn, user_id)
    session = None if found is None else signer.verify(cookie, found[1])
    if found is None or session is None:
        raise _unauthorized("session expired or invalid; log in again")
    if request.method in UNSAFE_METHODS and not tokens_equal(
        session.csrf, request.headers.get("x-csrf-token")
    ):
        raise ApiError(403, "csrf", "missing or wrong X-CSRF-Token header")
    return Auth(found[0], "cookie", session)


AuthDep = Annotated[Auth, Depends(get_auth)]


def current_user(auth: AuthDep) -> User:
    return auth.user


CurrentUser = Annotated[User, Depends(current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != Role.ADMIN:
        raise ApiError(403, "forbidden", "admin role required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def effective_access(conn: sqlite3.Connection, user: User, project_id: str) -> ProjectAccess | None:
    """What the user may do in the project: ``owner`` (share, delete), ``editor`` (write),
    ``viewer`` (read), or None. Admins act as owners of every project; a global viewer is
    capped at ``viewer`` even as owner or editor member."""
    if user.role == Role.ADMIN:
        return ProjectAccess.OWNER
    access = membership(conn, user, project_id)
    if access is not None and user.role == Role.VIEWER:
        return ProjectAccess.VIEWER
    return access


@dataclass(frozen=True)
class ProjectContext:
    project: Project
    user: User
    access: ProjectAccess


_SUFFICIENT = {
    "read": {ProjectAccess.OWNER, ProjectAccess.EDITOR, ProjectAccess.VIEWER},
    "write": {ProjectAccess.OWNER, ProjectAccess.EDITOR},
    "owner": {ProjectAccess.OWNER},
}


def project_access(need: Literal["read", "write", "owner"]):
    """Dependency for routes under ``/projects/{project_id}``: 404 without read access (also
    for a missing project, even for admins), 403 with read access but not ``need``."""
    allowed = _SUFFICIENT[need]

    def dependency(project_id: str, conn: Conn, user: CurrentUser) -> ProjectContext:
        try:
            project = require_project(conn, project_id)
        except ProjectNotFound:
            raise not_found("project not found") from None
        access = effective_access(conn, user, project_id)
        if access is None:
            raise not_found("project not found")
        if access not in allowed:
            raise ApiError(403, "forbidden", f"{need} access to the project required")
        return ProjectContext(project, user, access)

    return dependency


def _forwarded(request: Request, name: str) -> str | None:
    """The value the nearest proxy added: the last of a comma-separated header."""
    values = [v.strip() for v in request.headers.get(name, "").split(",") if v.strip()]
    return values[-1] if values else None


def client_ip(request: Request) -> str:
    if request.app.state.settings.trust_proxy:
        forwarded = _forwarded(request, "x-forwarded-for")
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def request_host(request: Request) -> str | None:
    if request.app.state.settings.trust_proxy:
        forwarded = _forwarded(request, "x-forwarded-host")
        if forwarded:
            return forwarded
    return request.headers.get("host")


def browser_safe_json(request: Request) -> None:
    """For unauthenticated POSTs (login, first admin), which carry no CSRF token: only JSON
    bodies (a cross-site form or ``text/plain`` post cannot send one without a CORS
    preflight) and no foreign ``Origin``."""
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "application/json":
        raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json")
    if not origin_matches(request.headers.get("origin"), request_host(request)):
        raise ApiError(403, "cross_origin", "cross-origin request refused")
