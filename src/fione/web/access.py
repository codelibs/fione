"""Resolving and authorizing what a project page works on, with the API's rules.

Every id in a path is resolved and must belong to the path's project (404 otherwise, as for a
project the user cannot read); writes need write access (403 for a viewer). Pages send
anonymous visitors to the login page; form posts check the session's CSRF token first.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from starlette.datastructures import FormData
from starlette.exceptions import HTTPException as StarletteHTTPException

from fione.api.deps import Auth, authorize, cookie_auth, request_host
from fione.api.errors import ApiError
from fione.api.schemas import MAX_ID
from fione.api.security import origin_matches
from fione.auth.roles import ProjectAccess, Role
from fione.jobs import store
from fione.jobs.store import Job
from fione.models import service as models
from fione.models.service import ModelNotFound, ModelRecord
from fione.projects import service as projects
from fione.projects.service import Dataset, DatasetNotFound, Project, ProjectNotFound
from fione.web.views import UiError, action_auth

WRITE = (ProjectAccess.OWNER, ProjectAccess.EDITOR)
SMALL_FORM_FIELDS = 16  # the account, user and sharing forms have a handful each


@dataclass(frozen=True)
class Ctx:
    auth: Auth
    project: Project
    access: ProjectAccess

    @property
    def can_write(self) -> bool:
        return self.access in WRITE

    @property
    def admin(self) -> bool:
        return self.auth.user.role == Role.ADMIN


def context(conn, auth: Auth, pid: str, need) -> Ctx:
    """The path project with the API's rules: 404 without read access, 403 without ``need``."""
    try:
        project = projects.require_project(conn, pid)
        access = authorize(conn, auth.user, pid, need, "project not found")
    except ProjectNotFound:
        raise UiError(404, "error.not_found") from None
    except ApiError as e:
        raise UiError(e.status, "error.not_found" if e.status == 404 else "error.forbidden") from e
    return Ctx(auth, project, access)


def page(request: Request, conn, pid: str, need="read") -> Ctx:
    """A page view: anonymous visitors are sent to the login page (HTMX: told to go there)."""
    auth = cookie_auth(request, conn)
    if auth is None:
        raise UiError(401, "error.session")
    return context(conn, auth, pid, need)


def action(request: Request, conn, pid: str, token: str, need="write") -> Ctx:
    """A form post: the session and its CSRF token first, then access to the project."""
    return context(conn, action_auth(request, conn, token), pid, need)


def parse_id(text) -> int:
    if not isinstance(text, str) or not text.isascii() or not text.isdigit():
        raise UiError(404, "error.not_found")
    value = int(text)
    if not 1 <= value <= MAX_ID:
        raise UiError(404, "error.not_found")
    return value


def dataset_in(conn, ctx: Ctx, did) -> Dataset:
    try:
        dataset = projects.get_dataset(conn, parse_id(did))
    except DatasetNotFound:
        raise UiError(404, "error.not_found") from None
    if dataset.project_id != ctx.project.id:
        raise UiError(404, "error.not_found")
    return dataset


def model_in(conn, ctx: Ctx, mid) -> ModelRecord:
    try:
        record = models.get_model(conn, parse_id(mid))
    except ModelNotFound:
        raise UiError(404, "error.not_found") from None
    if record.project_id != ctx.project.id:
        raise UiError(404, "error.not_found")
    return record


def job_in(conn, ctx: Ctx, jid) -> Job:
    try:
        job = store.get_job(conn, parse_id(jid))
    except KeyError:
        raise UiError(404, "error.not_found") from None
    if job.project_id != ctx.project.id:
        raise UiError(404, "error.not_found")
    return job


def signed_in(request: Request, conn) -> Auth:
    """A page view outside a project: anonymous visitors are sent to the login page."""
    auth = cookie_auth(request, conn)
    if auth is None:
        raise UiError(401, "error.session")
    return auth


def admin_only(auth: Auth) -> Auth:
    """Administrators only (403 for everyone else), as the API's admin dependency."""
    if auth.user.role != Role.ADMIN:
        raise UiError(403, "error.admin_only")
    return auth


def same_site(request: Request) -> None:
    """Refuse a form posted from another site (a foreign ``Origin``)."""
    if not origin_matches(request.headers.get("origin"), request_host(request)):
        raise UiError(403, "error.forbidden")


async def _small_form(request: Request) -> FormData:
    try:
        return await request.form(max_fields=SMALL_FORM_FIELDS, max_files=0)
    except StarletteHTTPException as e:
        if e.status_code != 400:
            raise
        raise UiError(400, "error.form") from None


SmallForm = Annotated[FormData, Depends(_small_form)]


def field(form: FormData, name: str) -> str:
    value = form.get(name)
    return value if isinstance(value, str) else ""


def form_auth(request: Request, conn, form: FormData) -> Auth:
    """A form post outside a project: same site, then the session and its CSRF token."""
    same_site(request)
    return action_auth(request, conn, field(form, "csrf_token"))
