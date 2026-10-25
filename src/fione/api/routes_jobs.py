"""Jobs: submitting training, prediction, explanation, module and export jobs; following,
cancelling and deleting them.

A job id is resolved first and then authorized on the job's own project: without read access
it is a 404, as for a missing job. Non-admins see error messages but not tracebacks.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from fione import db
from fione.api.deps import Conn, CurrentUser, ProjectContext, authorize, project_access
from fione.api.errors import ApiError, not_found, service_errors
from fione.api.schemas import (
    MAX_ID,
    AutomlIn,
    BatchPredictIn,
    ExplainJobIn,
    IdPath,
    ModuleJobIn,
    event_out,
    job_out,
)
from fione.auth.roles import Role, User
from fione.jobs import store
from fione.jobs.store import TERMINAL, Job, JobStatus
from fione.models import explanations
from fione.models import service as models
from fione.models.transfer import submit_export_all
from fione.modules import service as modules
from fione.projects import service as projects

router = APIRouter(tags=["jobs"])

Reader = Annotated[ProjectContext, Depends(project_access("read"))]
Writer = Annotated[ProjectContext, Depends(project_access("write"))]

EXPORT_KIND = "export_models"


def export_key(project_id: str, job_id: int) -> str:
    """Where an ``export_models`` job stores its zip (see ``jobs/export_handler.py``)."""
    return f"projects/{project_id}/exports/{job_id}.zip"


def _admin(user: User) -> bool:
    return user.role == Role.ADMIN


def _job(conn, user: User, job_id: int, need) -> Job:
    try:
        job = store.get_job(conn, job_id)
    except KeyError:
        raise not_found("job not found") from None
    authorize(conn, user, job.project_id, need, "job not found")
    return job


@router.post("/projects/{project_id}/jobs/automl", status_code=201)
def submit_automl(body: AutomlIn, ctx: Writer, conn: Conn, request: Request) -> dict:
    """Queue AutoML training on a train dataset; an invalid config, or a target column the
    engine would refuse (gaps, one value, too few rows...), is a 422 and nothing is queued."""
    with service_errors():
        job = models.submit_training(
            conn,
            request.app.state.storage,
            ctx.user,
            ctx.project.id,
            body.dataset_id,
            body.config,
            name=body.name,
        )
    return job_out(job, admin=_admin(ctx.user))


@router.post("/projects/{project_id}/jobs/batch-predict", status_code=201)
def submit_batch_predict(body: BatchPredictIn, ctx: Writer, conn: Conn) -> dict:
    """Queue a prediction of a dataset (any type) by a model of the same project."""
    with service_errors():
        job = models.submit_batch_predict(
            conn,
            ctx.user,
            ctx.project.id,
            body.model_id,
            body.dataset_id,
            include_columns=body.include_columns,
            name=body.name,
        )
    return job_out(job, admin=_admin(ctx.user))


@router.post("/projects/{project_id}/jobs/explain", status_code=201)
def submit_explain(body: ExplainJobIn, ctx: Writer, conn: Conn) -> dict:
    """Queue the explain job of a model of the project, on ``dataset_id`` or its training
    data; while one for the same dataset is queued or running, that job is returned. It also
    explains imports this install did not sign, which the synchronous routes refuse."""
    with service_errors():
        job = explanations.submit_explain(
            conn, ctx.user, ctx.project.id, body.model_id, body.dataset_id
        )
    return job_out(job, admin=_admin(ctx.user))


@router.post("/projects/{project_id}/jobs/module", status_code=201)
def submit_module(body: ModuleJobIn, ctx: Writer, conn: Conn) -> dict:
    """Queue a module (built-in or uploaded) over a dataset; ``params`` follow the module's
    parameter schema (``GET /modules``)."""
    try:
        with service_errors():
            job = modules.submit_module(
                conn,
                ctx.user,
                ctx.project.id,
                body.module_id,
                body.dataset_id,
                body.params,
                name=body.name,
            )
    except OverflowError:  # an id parameter beyond SQLite's integers
        raise ApiError(422, "invalid", "a parameter is out of range") from None
    return job_out(job, admin=_admin(ctx.user))


def _active_jobs(conn, project_id: str) -> list[Job]:
    return [
        job
        for status in (JobStatus.QUEUED, JobStatus.RUNNING)
        for job in store.list_jobs(conn, project_id, status=status)
    ]


@router.post("/projects/{project_id}/jobs/export", status_code=201)
def submit_export(ctx: Reader, conn: Conn) -> dict:
    """Queue an export of every model of the project into one zip. Download the result from
    ``GET /projects/{project_id}/exports/{job_id}``."""
    # The one job a reader may submit (every other submission needs write): it yields no
    # more than the per-model exports, which read access can already download. One export
    # at a time per project, so readers cannot flood the queue.
    with service_errors():
        job = start_export(conn, ctx.user, ctx.project.id)
    if job is None:
        message = "an export of this project is already queued or running"
        raise ApiError(409, "conflict", message)
    return job_out(job, admin=_admin(ctx.user))


def start_export(conn, user: User, project_id: str) -> Job | None:
    """Queue an ``export_models`` job (read access is enough), or None while one of the
    project is already queued or running."""
    with db.immediate(conn):
        if any(j.kind == EXPORT_KIND for j in _active_jobs(conn, project_id)):
            return None
        return submit_export_all(conn, user, project_id)


@router.get("/jobs")
def list_jobs(
    user: CurrentUser,
    conn: Conn,
    project_id: str | None = Query(None, max_length=100),
    status: JobStatus | None = None,
    limit: int = Query(200, ge=1, le=1000),
) -> list[dict]:
    """The newest ``limit`` jobs, newest first: of ``project_id``, or of every project the
    caller can read."""
    if project_id is not None:
        projects.require_project(conn, project_id)
        authorize(conn, user, project_id, "read", "project not found")
        ids = [project_id]
    else:
        ids = [p.id for p in projects.list_projects(conn, user)]
    jobs = [job for pid in ids for job in store.list_jobs(conn, pid, status=status, limit=limit)]
    jobs.sort(key=lambda j: (j.created_at, j.id), reverse=True)
    return [job_out(job, admin=_admin(user)) for job in jobs[:limit]]


@router.get("/jobs/{job_id}")
def get_job(job_id: IdPath, user: CurrentUser, conn: Conn) -> dict:
    return job_out(_job(conn, user, job_id, "read"), admin=_admin(user))


@router.get("/jobs/{job_id}/events")
def job_events(
    job_id: IdPath,
    user: CurrentUser,
    conn: Conn,
    after: int = Query(0, ge=0, le=MAX_ID),
    limit: int = Query(500, ge=1, le=1000),
) -> dict:
    """At most ``limit`` events after the event id ``after``, oldest first; pass ``last_id``
    back as ``after`` for the next page (an empty page: nothing newer yet)."""
    job = _job(conn, user, job_id, "read")
    events = store.events_since(conn, job.id, after, limit=limit)
    return {
        "events": [event_out(i, e, admin=_admin(user)) for i, e in events],
        "last_id": events[-1][0] if events else after,
        "status": job.status.value,
    }


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: IdPath, user: CurrentUser, conn: Conn, request: Request) -> dict:
    """Cancel a queued or running job (a running worker gets the runner's grace period, up to
    10 s, before it is killed). A finished job is a 409."""
    job = _job(conn, user, job_id, "write")
    if job.status in TERMINAL:
        raise ApiError(409, "conflict", "the job has already finished")
    return job_out(cancel(request, conn, job), admin=_admin(user))


def cancel(request: Request, conn, job: Job) -> Job:
    """Cancel an unfinished job (the caller has checked write access); returns it as it is now.
    Without a runner in this process, a running job is asked to stop."""
    runner = request.app.state.runner
    if runner is not None:
        runner.cancel(job.id)
    elif not store.cancel_queued(conn, job.id):
        store.request_cancel(conn, job.id)
    return store.get_job(conn, job.id)


def remove_job_files(request: Request, job: Job) -> None:
    """A deleted job's log file and, for an export, its zip."""
    (request.app.state.settings.data_dir / "jobs" / f"{job.id}.log").unlink(missing_ok=True)
    if job.kind == EXPORT_KIND and job.project_id:
        request.app.state.storage.delete(export_key(job.project_id, job.id))


def delete_finished_job(request: Request, conn, job: Job) -> None:
    """Delete a finished job with its events, log and export zip (the caller has checked
    write access); ``KeyError`` if it is gone, ``ValueError`` if it has not finished."""
    store.delete_job(conn, job.id)
    remove_job_files(request, job)


def delete_finished_jobs_of(request: Request, conn, project_id: str) -> int:
    """Delete every finished job of the project (as ``delete_finished_job``); queued and
    running ones stay. Returns how many were deleted."""
    deleted = 0
    for job in store.list_jobs(conn, project_id):
        if job.status not in TERMINAL:
            continue
        try:
            delete_finished_job(request, conn, job)
        except (KeyError, ValueError):
            continue  # deleted or restarted meanwhile
        deleted += 1
    return deleted


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: IdPath, user: CurrentUser, conn: Conn, request: Request) -> None:
    """Delete a finished job with its events, log and export zip; otherwise a 409."""
    job = _job(conn, user, job_id, "write")
    try:
        delete_finished_job(request, conn, job)
    except KeyError:
        raise not_found("job not found") from None
    except ValueError:
        raise ApiError(409, "conflict", "only a finished job can be deleted") from None


@router.delete("/jobs")
def delete_finished_jobs(ctx: Writer, conn: Conn, request: Request) -> dict:
    """Delete every finished job of ``project_id`` (a required query parameter) with their
    logs and export zips; queued and running jobs stay."""
    return {"deleted": delete_finished_jobs_of(request, conn, ctx.project.id)}
