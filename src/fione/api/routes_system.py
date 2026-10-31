from urllib.parse import urlparse

from fastapi import APIRouter, Request

from fione.api.deps import Conn, CurrentUser
from fione.api.schemas import user_out
from fione.assistant import store as assistant_store
from fione.auth.roles import Role
from fione.jobs.store import JobStatus
from fione.version import __version__

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    """Liveness, unauthenticated: the status and version only."""
    return {"status": "ok", "version": __version__}


@router.get("/system/status")
def status(user: CurrentUser, conn: Conn, request: Request) -> dict:
    """Version, storage kind, job runner and queue, for anyone signed in. No secrets, paths,
    URLs or credentials: the storage is named by its kind only."""
    return {
        **system_status(request, conn, admin=user.role == Role.ADMIN),
        "user": user_out(user),
        "is_admin": user.role == Role.ADMIN,
    }


def system_status(request: Request, conn, *, admin: bool = False) -> dict:
    """The status every signed-in user may see (also the web UI's system page); ``admin``
    adds the LLM server's host and progress. Never the base URL's path, a key or an error's
    text."""
    settings = request.app.state.settings
    counts = dict(conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall())
    scheme = urlparse(settings.storage_url).scheme
    return {
        "version": __version__,
        "image_tag": settings.image_tag,
        "storage": {"file": "local", "s3": "s3"}.get(scheme, "unknown"),
        "runner": "running" if request.app.state.runner is not None else "stopped",
        "jobs": {s.value: counts.get(s.value, 0) for s in (JobStatus.QUEUED, JobStatus.RUNNING)},
        "llm": _llm_status(request, conn, admin),
    }


def _llm_status(request: Request, conn, admin: bool) -> dict:
    settings = request.app.state.settings
    snapshot = request.app.state.llm_monitor.snapshot()
    info = {
        "configured": settings.llm_base_url is not None,
        "state": snapshot.state,
        "model": snapshot.model,
        "local": snapshot.local,
    }
    if admin:
        info |= {
            "host": snapshot.host,
            "completed": snapshot.completed,
            "total": snapshot.total,
            "samples_allowed": settings.llm_base_url is not None
            and assistant_store.samples_allowed(conn, settings.llm_base_url),
        }
    return info
