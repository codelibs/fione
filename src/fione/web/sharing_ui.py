"""Project sharing: the members of a project and their access, for the project's owner and
administrators (the API's ``owner`` access: 404 without read access, 403 for other readers).

Adding a member and changing one's access are the same call (``share_project``, as
``POST /api/v1/projects/{id}/share``); removing is ``unshare_project``. The page tells an
unknown username apart from a refusal exactly as the API does, and no more. The owner is
not a member: there is no owner role to give or take away here.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from fione.api.deps import Conn
from fione.auth import service as auth_service
from fione.auth.roles import ProjectAccess
from fione.projects import service as projects
from fione.projects.service import ShareError
from fione.web.access import Ctx, SmallForm, action, field, page, same_site
from fione.web.views import render

router = APIRouter(include_in_schema=False)

ACCESS = (ProjectAccess.EDITOR.value, ProjectAccess.VIEWER.value)
MAX_USERNAME = 64  # as the API's username
DONE = ("saved", "removed")


def _view(
    request: Request,
    conn,
    ctx: Ctx,
    *,
    status: int = 200,
    error: str | None = None,
    error_params: dict | None = None,
    new: dict | None = None,
) -> Response:
    owner = auth_service.get_user(conn, ctx.project.owner_id)
    done = request.query_params.get("done")
    return render(
        request,
        "members.html",
        ctx.auth,
        status=status,
        ctx=ctx,
        owner=owner.username if owner else None,
        members=projects.list_members(conn, ctx.project.id),
        access_levels=ACCESS,
        error=error,
        error_params=error_params or {},
        new=new or {"username": "", "access": ProjectAccess.VIEWER.value},
        done=done if done in DONE and status == 200 else None,
    )


@router.get("/projects/{pid}/members")
def members(request: Request, conn: Conn, pid: str) -> Response:
    return _view(request, conn, page(request, conn, pid, "owner"))


def _posted(request: Request, conn, pid: str, form) -> Ctx:
    same_site(request)
    return action(request, conn, pid, field(form, "csrf_token"), "owner")


@router.post("/projects/{pid}/members")
def share(request: Request, conn: Conn, pid: str, form: SmallForm) -> Response:
    """Add a member, or change a member's access (the same call)."""
    ctx = _posted(request, conn, pid, form)
    username, access = field(form, "username").strip(), field(form, "access")
    new = {"username": username[:200], "access": access if access in ACCESS else ACCESS[1]}
    if not 1 <= len(username) <= MAX_USERNAME:
        return _view(request, conn, ctx, status=422, error="members.error.username", new=new)
    if access not in ACCESS:
        return _view(request, conn, ctx, status=422, error="members.error.access", new=new)
    try:
        projects.share_project(conn, ctx.auth.user, ctx.project.id, username, ProjectAccess(access))
    except ShareError as e:
        params = {"username": username}
        error = f"members.error.{e.code}"
        return _view(request, conn, ctx, status=422, error=error, error_params=params, new=new)
    return RedirectResponse(f"/projects/{ctx.project.id}/members?done=saved", 303)


@router.post("/projects/{pid}/members/remove")
def unshare(request: Request, conn: Conn, pid: str, form: SmallForm) -> Response:
    ctx = _posted(request, conn, pid, form)
    username = field(form, "username")
    if not projects.unshare_project(conn, ctx.auth.user, ctx.project.id, username):
        params = {"username": username[:200]}
        error = "members.error.not_member"
        return _view(request, conn, ctx, status=404, error=error, error_params=params)
    return RedirectResponse(f"/projects/{ctx.project.id}/members?done=removed", 303)
