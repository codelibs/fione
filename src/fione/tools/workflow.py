"""The MCP workflow tools: follow and cancel jobs, as the token's user with the access the REST
job routes ask for (read to look, write to cancel). Like the other action tools, they are for
MCP clients only and only when ``FIONE_MCP_WRITE_ENABLED`` is set; the chat never lists them."""

import time
from typing import Literal

from fione.auth.roles import Role, can_access_project
from fione.engine.events import jsonable
from fione.jobs import store
from fione.jobs.store import TERMINAL, Job, JobStatus
from fione.projects import service as projects
from fione.tools.actions import _ID, _PROJECT, _schema, _writable
from fione.tools.registry import Tool, ToolContext, ToolError, clean_text, register_action

_MESSAGE_CHARS = 200
MAX_WAIT_SECS = 15
_POLL_SECS = 0.5
_LISTED = 50  # jobs of one list_jobs call, the newest


def _readable(ctx: ToolContext, project_id: str | None) -> None:
    """``PermissionError`` (or ``KeyError``, for a missing project) unless the user may read
    the project; a job without a project is for admins only."""
    if project_id is None:
        if ctx.user.role != Role.ADMIN:
            raise PermissionError("admin only")
        return
    projects.require_project(ctx.conn, project_id)
    if not can_access_project(ctx.conn, ctx.user, project_id, "read"):
        raise PermissionError("no read access")


def _job(ctx: ToolContext, job_id: int, need: Literal["read", "write"]) -> Job:
    """The job, resolved first and then authorized on its own project, as ``routes_jobs._job``
    does: a missing job and one the user may not read are the same refusal."""
    job = store.get_job(ctx.conn, job_id)
    if need == "write" and job.project_id is not None:
        _writable(ctx, job.project_id)
    else:
        _readable(ctx, job.project_id)
    return job


def _describe(ctx: ToolContext, job: Job) -> dict:
    """What a client needs to follow a job. The failure message can quote the user's data (a
    class label, a cell), so it is shown only where cell values may be."""
    result = None
    if job.result is not None:
        result = jsonable({k: v for k, v in job.result.items() if k != "key"})
    described = {
        "job_id": job.id,
        "kind": clean_text(job.kind),
        "status": job.status.value,
        "project_id": job.project_id,
        "message": clean_text(job.message, _MESSAGE_CHARS)
        if job.message and ctx.allow_samples
        else None,
        "result": result,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }
    if job.message and not ctx.allow_samples:
        described["message_hidden"] = True
    return described


def _get_job(ctx: ToolContext, args: dict) -> dict:
    return _describe(ctx, _job(ctx, args["job_id"], "read"))


def _wait_for_job(ctx: ToolContext, args: dict) -> dict:
    job = _job(ctx, args["job_id"], "read")
    timeout = args["timeout_secs"]
    start = time.monotonic()
    while job.status not in TERMINAL:
        left = timeout - (time.monotonic() - start)
        if left <= 0:
            break
        time.sleep(min(_POLL_SECS, left))
        job = store.get_job(ctx.conn, job.id)
    return {
        **_describe(ctx, job),
        "waited_secs": round(time.monotonic() - start, 1),
        "done": job.status in TERMINAL,
    }


def _list_jobs(ctx: ToolContext, args: dict) -> dict:
    status = JobStatus(args["status"]) if "status" in args else None
    if "project_id" in args:
        _readable(ctx, args["project_id"])
        ids = [args["project_id"]]
    else:
        ids = [p.id for p in projects.list_projects(ctx.conn, ctx.user)]
    found = [
        job for pid in ids for job in store.list_jobs(ctx.conn, pid, status=status, limit=_LISTED)
    ]
    found.sort(key=lambda j: (j.created_at, j.id), reverse=True)
    return {
        "jobs": [
            {
                "job_id": job.id,
                "kind": clean_text(job.kind),
                "status": job.status.value,
                "project_id": job.project_id,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "finished_at": job.finished_at,
            }
            for job in found[:_LISTED]
        ]
    }


def _cancel_job(ctx: ToolContext, args: dict) -> dict:
    job = _job(ctx, args["job_id"], "write")
    if job.status in TERMINAL:
        raise ToolError("the job has already finished")
    if ctx.cancel is None:
        raise ToolError("cancelling is not available")
    return _describe(ctx, ctx.cancel(job))


for _tool in (
    Tool(
        "get_job",
        "The status of a job (queued, running, done, failed, cancelled) and, once it has "
        "finished, its result (training: model_id; batch prediction: dataset_id).",
        _schema({"job_id": _ID}, ["job_id"]),
        True,
        _get_job,
    ),
    Tool(
        "wait_for_job",
        f"As get_job, but waits up to timeout_secs (at most {MAX_WAIT_SECS}) for the job to "
        "finish; `done` says whether it has. Call it again while it is false.",
        _schema(
            {
                "job_id": _ID,
                "timeout_secs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_WAIT_SECS,
                    "default": 10,
                },
            },
            ["job_id"],
        ),
        True,
        _wait_for_job,
    ),
    Tool(
        "list_jobs",
        f"The newest jobs (at most {_LISTED}), newest first, of one project or of every project "
        "you can read; optionally only those with one status.",
        _schema(
            {
                "project_id": _PROJECT,
                "status": {"type": "string", "enum": [s.value for s in JobStatus]},
            },
            [],
        ),
        True,
        _list_jobs,
    ),
    Tool(
        "cancel_job",
        "Cancel a queued or running job of a project you may change; a finished job cannot be "
        "cancelled.",
        _schema({"job_id": _ID}, ["job_id"]),
        False,
        _cancel_job,
    ),
):
    register_action(_tool)
