"""User management (admin only) and API tokens (one's own; admins may manage anyone's)."""

from fastapi import APIRouter, Query, Request

from fione.api.deps import AdminUser, AuthDep, Conn, CurrentUser
from fione.api.errors import ApiError, not_found, service_errors
from fione.api.schemas import IdPath, TokenIn, UserIn, UserPatch, token_out, user_out
from fione.api.security import password_work
from fione.auth import service as auth_service
from fione.auth.roles import NotebookPermission, Role
from fione.notebooks import service as notebooks

router = APIRouter(tags=["users"])


@router.get("/users")
def list_users(admin: AdminUser, conn: Conn) -> list[dict]:
    permissions = auth_service.notebook_permissions(conn)
    # a user created since the permissions were read is shown with the default
    return [
        user_out(u, notebook=permissions.get(u.id, NotebookPermission.NONE))
        for u in auth_service.list_users(conn)
    ]


@router.post("/users", status_code=201)
def create_user(body: UserIn, admin: AdminUser, conn: Conn) -> dict:
    with password_work(), service_errors():
        user = auth_service.create_user(conn, body.username, body.password, body.role)
    return user_out(user, notebook=auth_service.get_notebook_permission(conn, user.id))


@router.patch("/users/{user_id}")
def update_user(
    user_id: IdPath, body: UserPatch, admin: AdminUser, conn: Conn, request: Request
) -> dict:
    """Change the role, the notebook permission and/or reset the password (which ends the
    user's sessions); one's own admin role cannot be given up (409). The notebook of a user who
    may no longer use notebooks, or has a new password, is stopped."""
    if body.role is None and body.password is None and body.notebook is None:
        raise ApiError(422, "invalid", "nothing to change: give role, password and/or notebook")
    if auth_service.get_user(conn, user_id) is None:
        raise not_found("user not found")
    if body.role is not None:
        auth_service.set_role(conn, user_id, body.role, actor_id=admin.id)
    if body.password is not None:
        with password_work(), service_errors():
            auth_service.set_password(conn, user_id, body.password)
    if body.notebook is not None:
        auth_service.set_notebook_permission(conn, user_id, NotebookPermission(body.notebook))
    # A new password ends the notebook too (its sign-in and token), as it ends sessions.
    action = notebooks.stop if body.password is not None else notebooks.stop_unless_allowed
    notebooks.quietly(action, conn, request.app.state.notebook_launcher, user_id)
    user = auth_service.get_user(conn, user_id)
    if user is None:
        raise not_found("user not found")
    return user_out(user, notebook=auth_service.get_notebook_permission(conn, user_id))


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: IdPath, admin: AdminUser, conn: Conn, request: Request) -> None:
    """Refused (409) for the last admin, oneself and owners of projects or jobs. Once deleted,
    the user's notebook and its files are removed (the token went with the user)."""
    auth_service.delete_user(conn, user_id, actor_id=admin.id)
    notebooks.quietly(notebooks.purge, conn, request.app.state.notebook_launcher, user_id)


@router.post("/tokens", status_code=201)
def create_token(body: TokenIn, auth: AuthDep, conn: Conn) -> dict:
    """A new API token for the caller; the plaintext ``token`` is shown only here. One made
    with a token has that token's scope and expiry, so a token cannot mint a longer-lived one."""
    kept = {"scope": auth.scope, "expires_at": auth.token.expires_at} if auth.token else {}
    record, token = auth_service.create_token(conn, auth.user.id, body.name, **kept)
    return {**token_out(record), "token": token}


@router.get("/tokens")
def list_tokens(
    user: CurrentUser, conn: Conn, user_id: int | None = Query(None, ge=1, le=2**63 - 1)
) -> list[dict]:
    """The caller's tokens (admins may pass ``user_id``); never the token or its hash."""
    owner = user.id if user_id is None else user_id
    if owner != user.id and user.role != Role.ADMIN:
        raise ApiError(403, "forbidden", "admin role required to list other users' tokens")
    return [token_out(t) for t in auth_service.list_tokens(conn, owner)]


@router.delete("/tokens/{token_id}", status_code=204)
def revoke_token(token_id: IdPath, user: CurrentUser, conn: Conn) -> None:
    record = auth_service.get_token(conn, token_id)
    if record is None or (record.user_id != user.id and user.role != Role.ADMIN):
        raise not_found("token not found")
    auth_service.revoke_token(conn, token_id)
