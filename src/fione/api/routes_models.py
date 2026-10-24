"""Trained models: listing, details, export and import, the serving bundle, and the zips of
whole-project exports.

A model id is resolved first and then authorized on the model's own project (404 without
read access). Downloads are built before their headers are sent, so a failure is a JSON
error, never a cut 200; their temp files live under ``<data_dir>/tmp``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from fione.api.deps import (
    UPLOAD_SLACK_BYTES,
    AdminUser,
    Conn,
    CurrentUser,
    ProjectContext,
    authorize,
    project_access,
)
from fione.api.downloads import attachment, content_disposition, tmp_dir
from fione.api.errors import ApiError, not_found, service_errors
from fione.api.routes_jobs import EXPORT_KIND, export_key
from fione.api.schemas import IdPath, model_out
from fione.auth.roles import User
from fione.config import load_secret
from fione.engine.artifact import UntrustedArtifactError
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.models import service
from fione.models.bundle import BUNDLE_FILES, Bundle, BundleError, make_serving_bundle
from fione.models.service import ModelRecord
from fione.models.transfer import MAX_ARCHIVE_BYTES, export_model, import_model
from fione.projects.service import require_project

router = APIRouter(tags=["models"])

Reader = Annotated[ProjectContext, Depends(project_access("read"))]

ZIP = "application/zip"
CHUNK = 1 << 20

_IMPORT_SCHEMA = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {
                        "file": {"type": "string", "format": "binary"},
                        "trust_foreign": {"type": "boolean", "default": False},
                    },
                }
            }
        },
    }
}


def _model(conn, user: User, model_id: int, need) -> ModelRecord:
    record = service.get_model(conn, model_id)  # ModelNotFound -> 404
    authorize(conn, user, record.project_id, need, "model not found")
    return record


@router.get("/projects/{project_id}/models")
def list_models(ctx: Reader, conn: Conn) -> list[dict]:
    return [model_out(m) for m in service.list_models(conn, ctx.project.id)]


@router.get("/models/{model_id}")
def get_model(model_id: IdPath, user: CurrentUser, conn: Conn) -> dict:
    """The model with its metrics, ``stop_reason`` (``degraded`` when training hit an error),
    config, leaderboard, trials and variable importance."""
    return model_out(_model(conn, user, model_id, "read"), detail=True)


@router.get("/models/{model_id}/export")
def export(model_id: IdPath, user: CurrentUser, conn: Conn, request: Request):
    """The model as a zip that ``POST /projects/{project_id}/models/import`` takes."""
    return export_response(request, _model(conn, user, model_id, "read"))


def export_response(request: Request, record: ModelRecord):
    """The model's export zip as a download (the caller has checked read access). Built
    before the headers are sent: a missing file raises ``ModelNotFound``."""
    chunks = export_model(
        request.app.state.storage, record, tmp_dir=tmp_dir(request.app.state.settings)
    )
    return attachment(chunks, ZIP, content_disposition(record.name, ".zip", "model"))


def _bundle(conn, user: User, model_id: int, request: Request) -> Bundle:
    """The model's serving bundle (its zip is built only when ``open()`` is read); a 409 when
    the model's manifest or the configured serving image cannot be used safely."""
    try:
        return serving_bundle_of(request, _model(conn, user, model_id, "read"))
    except BundleError as e:
        raise ApiError(409, "conflict", str(e)) from e


def serving_bundle_of(request: Request, record: ModelRecord) -> Bundle:
    """The serving bundle of a model the caller may read (``BundleError`` if unsafe)."""
    settings = request.app.state.settings
    return make_serving_bundle(
        request.app.state.storage, record, settings, tmp_dir=tmp_dir(settings)
    )


@router.get("/models/{model_id}/serving")
def serving_bundle(model_id: IdPath, user: CurrentUser, conn: Conn, request: Request):
    """The serving bundle: a zip with ``model/manifest.json`` and ``model/model.joblib``.
    ``/serving/info`` gives the command that serves it."""
    bundle = _bundle(conn, user, model_id, request)
    disposition = content_disposition(bundle.filename, ".zip", "model")
    return attachment(bundle.open(), ZIP, disposition)


@router.get("/models/{model_id}/serving/info")
def serving_info(model_id: IdPath, user: CurrentUser, conn: Conn, request: Request) -> dict:
    """How to serve the bundle: the ``docker run`` command (run where the zip was unzipped),
    an example ``curl`` call, and the files in the zip. Nothing is built."""
    bundle = _bundle(conn, user, model_id, request)
    return {
        "filename": bundle.filename,
        "run_command": bundle.run_command,
        "example_curl": bundle.example_curl,
        "files": list(BUNDLE_FILES),
    }


@router.delete("/models/{model_id}", status_code=204)
def delete_model(model_id: IdPath, user: CurrentUser, conn: Conn, request: Request) -> None:
    record = _model(conn, user, model_id, "write")
    service.delete_model(conn, request.app.state.storage, record.id)


def _trust_foreign(form) -> bool:
    value = form.get("trust_foreign")
    if value is None:
        return False
    if not isinstance(value, str) or value.strip().lower() not in ("true", "false"):
        raise ApiError(422, "invalid", "trust_foreign must be true or false")
    return value.strip().lower() == "true"


def _too_large() -> ApiError:
    return ApiError(413, "too_large", f"a model export may be at most {MAX_ARCHIVE_BYTES} bytes")


@router.post("/projects/{project_id}/models/import", status_code=201, openapi_extra=_IMPORT_SCHEMA)
async def import_(project_id: str, admin: AdminUser, request: Request, conn: Conn) -> dict:
    """Import a model export zip (multipart ``file``). Admin only: the file holds a pickle.

    A model signed by another install is refused unless ``trust_foreign`` is true; it is
    then stored with ``trusted`` false. The form is parsed only after authorization.
    """
    require_project(conn, project_id)  # ProjectNotFound -> 404
    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        raise ApiError(415, "unsupported_media_type", "Content-Type must be multipart/form-data")
    if too_large_for_import(request):
        raise _too_large()
    form = await request.form(max_files=1, max_fields=1)
    try:
        trust_foreign = _trust_foreign(form)
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise ApiError(422, "invalid", "file: a file field is required")
        if upload.size is not None and upload.size > MAX_ARCHIVE_BYTES:
            raise _too_large()

        def run() -> ModelRecord:
            try:
                with service_errors():  # ModelImportError is a ValueError with a plain reason
                    return import_upload(request, conn, admin, project_id, upload, trust_foreign)
            except UntrustedArtifactError as e:
                raise ApiError(422, "untrusted", f"the model file failed verification: {e}") from e

        record = await run_in_threadpool(run)
    finally:
        await form.close()
    return model_out(record, detail=True)


def too_large_for_import(request: Request) -> bool:
    """Whether the declared body is over the archive cap (checked before the form is read)."""
    declared = request.headers.get("content-length", "")
    return declared.isdigit() and int(declared) > MAX_ARCHIVE_BYTES + UPLOAD_SLACK_BYTES


def import_upload(
    request: Request, conn, admin: User, project_id: str, upload: UploadFile, trust_foreign: bool
) -> ModelRecord:
    """Import an uploaded export zip (admin checked by the caller and by the service):
    ``ModelImportError`` (a ``ValueError``) or ``UntrustedArtifactError`` if refused."""
    settings = request.app.state.settings
    return import_model(
        request.app.state.storage,
        conn,
        admin,
        project_id,
        upload.file,
        load_secret(settings),
        trust_foreign=trust_foreign,
        tmp_dir=tmp_dir(settings),
        max_bytes=MAX_ARCHIVE_BYTES,
    )


@router.get("/projects/{project_id}/exports/{job_id}")
def download_export(job_id: IdPath, ctx: Reader, conn: Conn, request: Request):
    """The zip of a finished export job of this project (``POST .../jobs/export``)."""
    try:
        job = store.get_job(conn, job_id)
    except KeyError:
        raise not_found("export not found") from None
    if job.project_id != ctx.project.id or job.kind != EXPORT_KIND:
        raise not_found("export not found")
    if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise ApiError(409, "conflict", "the export has not finished")
    if job.status is not JobStatus.DONE:
        raise not_found("the export did not complete")
    # Only the latest export is kept (jobs/export_handler.py removes the older zips).
    newer = store.list_jobs(conn, ctx.project.id, status=JobStatus.DONE)
    if any(j.kind == EXPORT_KIND and j.id > job.id for j in newer):
        raise not_found("this export was superseded by a newer one")
    try:
        source = request.app.state.storage.open_read(export_key(ctx.project.id, job.id))
    except KeyError:
        raise not_found("export not found") from None

    def chunks():
        with source:
            while chunk := source.read(CHUNK):
                yield chunk

    name = f"fione-export-{ctx.project.name}-{job.id}"
    return attachment(chunks(), ZIP, content_disposition(name, ".zip", "fione-export"))
