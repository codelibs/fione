"""Every error leaves the API as ``{"error": "<message>", "code": "<slug>"}``.

Only exceptions whose messages are written for users are shown: ``ApiError``, the domain
errors registered below, and ``ValueError``/``PermissionError`` raised by a service inside
``service_errors()``. Anything else is a 500 with a fixed body; its traceback is only logged.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import pyarrow as pa
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from fione.auth.service import UserConflict, UserNotFound
from fione.engine.config import ConfigError
from fione.models.service import ModelNotFound
from fione.projects.ingest import IngestError
from fione.projects.service import DatasetNotFound, ProjectNotFound

log = logging.getLogger("fione.api")

_HTTP_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "too_large",
    415: "unsupported_media_type",
    422: "invalid",
    429: "throttled",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers


def error_response(
    status: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse({"error": message, "code": code}, status_code=status, headers=headers)


def not_found(what: str = "not found") -> ApiError:
    return ApiError(404, "not_found", what)


@contextmanager
def service_errors() -> Iterator[None]:
    """Show a service's ``ValueError`` (422) and ``PermissionError`` (403) messages.

    Only for calls whose messages are meant for users: Arrow errors (which are ValueErrors)
    and OS permission errors (which carry paths) stay internal.
    """
    try:
        yield
    except PermissionError as e:
        if e.errno is not None:
            raise
        raise ApiError(403, "forbidden", str(e)) from e
    except ValueError as e:
        if isinstance(e, pa.ArrowException | UnicodeError):
            raise
        raise ApiError(422, "invalid", str(e)) from e


def _validation_message(exc: RequestValidationError) -> str:
    # loc and msg only: the offending input (a password, say) is never echoed.
    parts = []
    for error in exc.errors():
        loc = [str(p) for p in error.get("loc", ()) if p not in ("body", "query", "path")]
        parts.append(f"{'.'.join(loc) or 'request'}: {error.get('msg', 'invalid')}")
    return "; ".join(parts) or "invalid request"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message, exc.headers)

    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "request failed"
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, message, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(422, "invalid", _validation_message(exc))

    @app.exception_handler(ProjectNotFound)
    async def _no_project(request: Request, exc: ProjectNotFound) -> JSONResponse:
        return error_response(404, "not_found", "project not found")

    @app.exception_handler(DatasetNotFound)
    async def _no_dataset(request: Request, exc: DatasetNotFound) -> JSONResponse:
        return error_response(404, "not_found", "dataset not found")

    @app.exception_handler(ModelNotFound)
    async def _no_model(request: Request, exc: ModelNotFound) -> JSONResponse:
        return error_response(404, "not_found", "model not found")

    @app.exception_handler(UserNotFound)
    async def _no_user(request: Request, exc: UserNotFound) -> JSONResponse:
        return error_response(404, "not_found", "user not found")

    @app.exception_handler(UserConflict)
    async def _conflict(request: Request, exc: UserConflict) -> JSONResponse:
        return error_response(409, "conflict", str(exc))

    @app.exception_handler(IngestError)
    async def _ingest(request: Request, exc: IngestError) -> JSONResponse:
        return error_response(422, "invalid_csv", str(exc))

    @app.exception_handler(ConfigError)
    async def _config(request: Request, exc: ConfigError) -> JSONResponse:
        return error_response(422, "invalid", str(exc))

    @app.exception_handler(Exception)
    async def _internal(request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return error_response(500, "internal", "internal error")
