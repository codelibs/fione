from urllib.parse import urlparse

from fastapi import APIRouter, Request

from fione.api.deps import Conn, CurrentUser
from fione.api.schemas import user_out
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
    settings = request.app.state.settings
    counts = dict(conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall())
    scheme = urlparse(settings.storage_url).scheme
    return {
        "version": __version__,
        "image_tag": settings.image_tag,
        "storage": {"file": "local", "s3": "s3"}.get(scheme, "unknown"),
        "runner": "running" if request.app.state.runner is not None else "stopped",
        "jobs": {s.value: counts.get(s.value, 0) for s in (JobStatus.QUEUED, JobStatus.RUNNING)},
        "ollama": {"configured": False},  # Phase 1 has no LLM connection
        "user": user_out(user),
        "is_admin": user.role == Role.ADMIN,
    }
