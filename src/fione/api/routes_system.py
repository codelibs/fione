from fastapi import APIRouter

from fione.version import __version__

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    """Liveness, unauthenticated: the status and version only."""
    return {"status": "ok", "version": __version__}
