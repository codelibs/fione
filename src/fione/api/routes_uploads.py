"""The one-time upload URL an MCP client gets from ``create_upload_url``.

``PUT /uploads/{token}`` takes the raw CSV as the body and ingests it as the dataset the token
was made for, as the token's user. It needs no ``Authorization`` header or cookie: the token is
the credential. Whatever the reason a token is not used (unknown, used, expired, MCP or its
write switch off, the user no longer allowed to write) the answer is the same 404.
"""

import tempfile
from typing import BinaryIO

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from fione.api.deps import Conn
from fione.api.downloads import tmp_dir
from fione.api.errors import ApiError, not_found
from fione.api.routes_datasets import ingest_upload
from fione.api.schemas import dataset_out
from fione.auth import service as auth_service
from fione.auth.roles import can_access_project
from fione.projects import upload_tokens
from fione.projects.upload_tokens import UploadToken

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _refused() -> ApiError:
    return not_found("upload not found")


def _claim(conn, token: str) -> UploadToken | None:
    """The claimed token, if its user may still write to the project."""
    claimed = upload_tokens.claim(conn, token)
    if claimed is None:
        return None
    user = auth_service.get_user(conn, claimed.user_id)
    if user is None or not can_access_project(conn, user, claimed.project_id, "write"):
        upload_tokens.release(conn, claimed.id)
        return None
    return claimed


async def _spool(request: Request, file: BinaryIO, limit: int) -> None:
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise ApiError(413, "too_large", f"the file exceeds {limit} bytes")
        file.write(chunk)
    file.seek(0)


@router.put("/{token}", status_code=201)
async def put_upload(token: str, request: Request, conn: Conn) -> dict:
    """Ingest the request body (a CSV) as the token's dataset and answer the dataset, as the
    REST upload does. The token is consumed only by a successful ingest."""
    settings = request.app.state.settings
    if not (settings.mcp_enabled and settings.mcp_write_enabled):
        raise _refused()
    claimed = await run_in_threadpool(_claim, conn, token)
    if claimed is None:
        raise _refused()
    try:
        with tempfile.TemporaryFile(dir=tmp_dir(settings)) as body:
            await _spool(request, body, settings.max_upload_bytes)
            dataset = await ingest_upload(
                request, conn, claimed.project_id, claimed.name, claimed.type, UploadFile(body)
            )
    except BaseException:  # a failed or abandoned upload gives the token back
        upload_tokens.release(conn, claimed.id)
        raise
    await run_in_threadpool(upload_tokens.finish, conn, claimed.id)
    return dataset_out(dataset, schema=True)
