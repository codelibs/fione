"""User management (admin only) and API tokens (one's own; admins may manage anyone's)."""

from fastapi import APIRouter, Query

from fione.api.deps import AdminUser, Conn, CurrentUser
from fione.api.errors import ApiError, not_found, service_errors
from fione.api.schemas import IdPath, TokenIn, UserIn, UserPatch, token_out, user_out
from fione.api.security import password_work
from fione.auth import service as auth_service
from fione.auth.roles import Role

router = APIRouter(tags=["users"])


@router.get("/users")
def list_users(admin: AdminUser, conn: Conn) -> list[dict]:
    return [user_out(u) for u in auth_service.list_users(conn)]


@router.post("/users", status_code=201)
def create_user(body: UserIn, admin: AdminUser, conn: Conn) -> dict:
    with password_work(), service_errors():
        user = auth_service.create_user(conn, body.username, body.password, body.role)
    return user_out(user)


@router.patch("/users/{user_id}")
def update_user(user_id: IdPath, body: UserPatch, admin: AdminUser, conn: Conn) -> dict:
    """Change the role and/or reset the password (which ends the user's sessions); one's own
    admin role cannot be given up (409)."""
    if body.role is None and body.password is None:
        raise ApiError(422, "invalid", "nothing to change: give role and/or password")
    if auth_service.get_user(conn, user_id) is None:
        raise not_found("user not found")
    if body.role is not None:
        auth_service.set_role(conn, user_id, body.role, actor_id=admin.id)
    if body.password is not None:
        with password_work(), service_errors():
            auth_service.set_password(conn, user_id, body.password)
    user = auth_service.get_user(conn, user_id)
    if user is None:
        raise not_found("user not found")
    return user_out(user)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: IdPath, admin: AdminUser, conn: Conn) -> None:
    """Refused (409) for the last admin, oneself and owners of projects or jobs."""
    auth_service.delete_user(conn, user_id, actor_id=admin.id)


@router.post("/tokens", status_code=201)
def create_token(body: TokenIn, user: CurrentUser, conn: Conn) -> dict:
    """A new API token for the caller; the plaintext ``token`` is shown only here."""
    record, token = auth_service.create_token(conn, user.id, body.name)
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
