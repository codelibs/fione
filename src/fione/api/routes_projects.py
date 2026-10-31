"""Projects and their sharing."""

import logging
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from fione.api.deps import Conn, CurrentUser, ProjectContext, project_access
from fione.api.errors import not_found, service_errors
from fione.api.schemas import ProjectIn, ShareIn, members_out, project_out
from fione.auth import service as auth_service
from fione.auth.roles import ProjectAccess
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.projects import service

router = APIRouter(prefix="/projects", tags=["projects"])
log = logging.getLogger(__name__)

# How long deleting a project waits for its jobs to stop (a running worker gets the
# runner's cancel grace, then is killed).
CANCEL_WAIT_SECS = 15.0
MAX_CANCEL_THREADS = 8

Reader = Annotated[ProjectContext, Depends(project_access("read"))]
Owner = Annotated[ProjectContext, Depends(project_access("owner"))]


@router.get("")
def list_projects(user: CurrentUser, conn: Conn) -> list[dict]:
    return [project_out(p) for p in service.list_projects(conn, user)]


@router.post("", status_code=201)
def create_project(body: ProjectIn, user: CurrentUser, conn: Conn) -> dict:
    with service_errors():
        project = service.create_project(conn, user, body.name)
    return project_out(project)


@router.get("/{project_id}")
def get_project(ctx: Reader, conn: Conn) -> dict:
    """The project with its owner, members and the caller's effective ``access``
    (``owner`` for admins)."""
    owner = auth_service.get_user(conn, ctx.project.owner_id)
    return {
        **project_out(ctx.project),
        "owner": owner.username if owner else None,
        "access": ctx.access.value,
        "members": members_out(service.list_members(conn, ctx.project.id)),
    }


def _stop_jobs(request: Request, conn, project_id: str) -> None:
    """Cancel the project's queued and running jobs before it is deleted, so no worker keeps
    writing objects for a deleted project; waits up to ``CANCEL_WAIT_SECS`` in all."""
    active = [
        job.id
        for job in store.list_jobs(conn, project_id)
        if job.status in (JobStatus.QUEUED, JobStatus.RUNNING)
    ]
    if not active:
        return
    runner = request.app.state.runner
    if runner is None:
        for job_id in active:
            if not store.cancel_queued(conn, job_id):
                store.request_cancel(conn, job_id)
        return
    pool = ThreadPoolExecutor(
        max_workers=min(len(active), MAX_CANCEL_THREADS), thread_name_prefix="fione-cancel"
    )
    try:
        futures = [pool.submit(runner.cancel, job_id) for job_id in active]
        done, pending = wait(futures, timeout=CANCEL_WAIT_SECS)
    finally:
        pool.shutdown(wait=False)
    for future in done:
        if (error := future.exception()) is not None:
            log.error("cancelling a job of project %s failed", project_id, exc_info=error)
    if pending:
        log.warning(
            "%d job(s) of project %s did not stop within %.0f s; deleting anyway",
            len(pending),
            project_id,
            CANCEL_WAIT_SECS,
        )


@router.delete("/{project_id}", status_code=204)
def delete_project(ctx: Owner, request: Request, conn: Conn) -> None:
    """Cancel the project's jobs, then delete it with its datasets, models, jobs and logs."""
    delete_project_and_jobs(request, conn, ctx.user, ctx.project.id)


def delete_project_and_jobs(request: Request, conn, user, project_id: str) -> None:
    """Stop the project's jobs, delete the project with its objects, then its job logs (the
    API's and the web UI's project delete)."""
    _stop_jobs(request, conn, project_id)
    job_ids = [job.id for job in store.list_jobs(conn, project_id)]
    with service_errors():
        service.delete_project(conn, request.app.state.storage, user, project_id)
    logs = request.app.state.settings.data_dir / "jobs"
    for job_id in job_ids:
        (logs / f"{job_id}.log").unlink(missing_ok=True)


@router.post("/{project_id}/share", status_code=204)
def share_project(body: ShareIn, ctx: Owner, conn: Conn) -> None:
    with service_errors():
        service.share_project(
            conn, ctx.user, ctx.project.id, body.username, ProjectAccess(body.access)
        )


@router.delete("/{project_id}/share/{username}", status_code=204)
def unshare_project(username: str, ctx: Owner, conn: Conn) -> None:
    with service_errors():
        removed = service.unshare_project(conn, ctx.user, ctx.project.id, username)
    if not removed:
        raise not_found("not a member of the project")
