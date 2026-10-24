"""CSV uploads of the web UI: checks, multipart parsing and ingest.

Starlette's parser keeps each file in a ``SpooledTemporaryFile`` (in memory up to
``spool_max_size``, then a temp file). Here that spool rolls over into ``<data_dir>/tmp``, so a
large CSV takes neither memory nor system temp space. Fields keep Starlette's own limits.
An upload is checked for the session, write access and ``Origin`` before its body is read,
and for the CSRF token right after the form is parsed.
"""

from pathlib import Path, PurePosixPath, PureWindowsPath
from tempfile import SpooledTemporaryFile

from fastapi import Request
from starlette.datastructures import FormData, UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from fione.api.deps import cookie_auth, request_host
from fione.api.downloads import tmp_dir
from fione.api.errors import ApiError
from fione.api.routes_datasets import ingest_upload
from fione.api.security import origin_matches, tokens_equal
from fione.modules.registry import redact
from fione.projects.ingest import IngestError
from fione.projects.service import Dataset, DatasetType
from fione.web.access import Ctx, context
from fione.web.views import UiError

MAX_NAME_LEN = 100
# The start of an ingest error -> the key of its plain-language message.
INGEST_ERRORS = (
    ("could not detect the text encoding", "upload.error.encoding"),
    ("empty file", "upload.error.empty"),
    ("no data rows", "upload.error.no_rows"),
    ("could not parse the CSV", "upload.error.parse"),
)


class UploadFormError(ValueError):
    """The request is not a well-formed multipart form."""


class _DataDirParser(MultiPartParser):
    def __init__(self, *args, directory: Path, **kwargs):
        super().__init__(*args, **kwargs)
        self.directory = directory

    def on_headers_finished(self) -> None:
        super().on_headers_finished()
        upload = self._current_part.file
        if upload is not None:  # a file part: nothing has been written to its spool yet
            upload.file.close()
            upload.file = SpooledTemporaryFile(max_size=self.spool_max_size, dir=self.directory)
            self._files_to_close_on_error[-1] = upload.file


async def read_form(request: Request, directory: Path, *, max_fields: int) -> FormData:
    """The multipart form of ``request`` with at most one file; close it after use."""
    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        raise UploadFormError("not a multipart form")
    parser = _DataDirParser(
        request.headers,
        request.stream(),
        max_files=1,
        max_fields=max_fields,
        directory=directory,
    )
    try:
        return await parser.parse()
    except MultiPartException as e:
        raise UploadFormError(str(e)) from e


class UploadProblem(Exception):
    """An upload that cannot be used: shown on the upload form as ``key`` (and ``detail``)."""

    def __init__(self, status: int, key: str, detail: str | None = None, **vars):
        super().__init__(key)
        self.status, self.key, self.detail, self.vars = status, key, detail, vars


async def upload_context(request: Request, conn, pid: str) -> Ctx:
    """Everything an upload is checked for before its body is read."""
    auth = cookie_auth(request, conn)
    if auth is None:
        raise UiError(401, "error.session")
    ctx = context(conn, auth, pid, "write")
    if not origin_matches(request.headers.get("origin"), request_host(request)):
        raise UiError(403, "error.forbidden")
    return ctx


def dataset_name(filename: str) -> str:
    """The dataset name for an uploaded file: its base name without ``.csv``."""
    base = PureWindowsPath(PurePosixPath(filename).name).name.strip()
    if base.lower().endswith(".csv"):
        base = base[:-4].strip()
    return base[:MAX_NAME_LEN] or "data"


def _ingest_problem(error: IngestError) -> UploadProblem:
    text = redact(str(error))
    for start, key in INGEST_ERRORS:
        if text.startswith(start):
            return UploadProblem(422, key, text if key == "upload.error.parse" else None)
    if "not valid UTF-8" in text:
        return UploadProblem(422, "upload.error.encoding")
    return UploadProblem(422, "upload.error.invalid", text)


async def receive_csv(request: Request, conn, ctx: Ctx, type_: DatasetType | None) -> Dataset:
    """Read the posted form (``csrf_token``, one ``file`` and, when ``type_`` is None, the
    dataset ``kind``) and ingest the CSV."""
    settings = request.app.state.settings
    try:
        form = await read_form(request, tmp_dir(settings), max_fields=1 if type_ else 2)
    except UploadFormError:
        raise UploadProblem(400, "upload.error.form") from None
    try:
        token = form.get("csrf_token")
        if not tokens_equal(ctx.auth.session.csrf, token if isinstance(token, str) else None):
            raise UiError(403, "error.csrf")
        if type_ is None:
            kind = form.get("kind")
            if kind not in {t.value for t in DatasetType}:
                raise UploadProblem(422, "datasets.error.kind")
            type_ = DatasetType(kind)
        upload = form.get("file")
        if not isinstance(upload, UploadFile) or not upload.filename:
            raise UploadProblem(422, "upload.error.missing")
        try:
            return await ingest_upload(
                request, conn, ctx.project.id, dataset_name(upload.filename), type_, upload
            )
        except ApiError as e:  # 413: over max_upload_bytes
            raise UploadProblem(e.status, "upload.error.too_large") from e
        except IngestError as e:
            raise _ingest_problem(e) from e
    finally:
        await form.close()


def size_text(n: int) -> str:
    for unit, scale in (("GB", 2**30), ("MB", 2**20), ("KB", 2**10)):
        if n >= scale:
            return f"{n / scale:.1f}".removesuffix(".0") + f" {unit}"
    return f"{n} B"
