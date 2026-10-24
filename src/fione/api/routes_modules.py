"""Python modules: the list (built-in and uploaded) for everyone signed in; upload and delete
for admins. Uploaded modules run in job workers, unsandboxed."""

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from fione.api.deps import AdminUser, Conn, CurrentUser
from fione.api.errors import ApiError, not_found, service_errors
from fione.api.schemas import module_out
from fione.modules import service
from fione.modules.service import MAX_SOURCE_BYTES, ModuleNotFound

router = APIRouter(prefix="/modules", tags=["modules"])

UPLOAD_WARNING = (
    "Uploaded modules are NOT sandboxed: they run in job workers with the application's"
    " privileges and can read its secret key, environment and data. Upload only code you"
    " trust; uploading is admin-only."
)

_UPLOAD_SCHEMA = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["id", "file"],
                    "properties": {
                        "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,39}$"},
                        "file": {"type": "string", "format": "binary"},
                    },
                }
            }
        },
    }
}


@router.get("")
def list_modules(user: CurrentUser, conn: Conn) -> list[dict]:
    return [module_out(m) for m in service.list_modules(conn)]


@router.post("", status_code=201, openapi_extra=_UPLOAD_SCHEMA)
async def upload_module(admin: AdminUser, request: Request, conn: Conn) -> dict:
    """Upload a module (multipart ``id`` and ``file``, a UTF-8 ``.py`` of at most 256 KB that
    defines ``MODULE`` and ``run(df, params, ctx)``). Its metadata is read in a separate,
    short-lived process; the API process never imports it. The response carries ``warning``."""
    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        raise ApiError(415, "unsupported_media_type", "Content-Type must be multipart/form-data")
    form = await request.form(max_files=1, max_fields=1)
    try:
        module_id = form.get("id")
        if not isinstance(module_id, str):
            raise ApiError(422, "invalid", "id: a text field is required")
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise ApiError(422, "invalid", "file: a file field is required")
        source = await upload.read(MAX_SOURCE_BYTES + 1)  # the service refuses anything longer

        def run():
            with service_errors():
                return service.upload_module(
                    conn, request.app.state.storage, admin, module_id.strip(), source
                )

        info = await run_in_threadpool(run)
    finally:
        await form.close()
    return {**module_out(info), "warning": UPLOAD_WARNING}


@router.delete("/{module_id}", status_code=204)
def delete_module(module_id: str, admin: AdminUser, conn: Conn, request: Request) -> None:
    """Delete an uploaded module (built-in ones cannot be deleted: 422)."""
    try:
        with service_errors():
            service.delete_module(conn, request.app.state.storage, admin, module_id)
    except ModuleNotFound:
        raise not_found("module not found") from None
