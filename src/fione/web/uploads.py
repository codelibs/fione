"""Multipart uploads of the web UI, spooled to ``<data_dir>/tmp`` instead of the system temp dir.

Starlette's parser keeps each file in a ``SpooledTemporaryFile`` (in memory up to
``spool_max_size``, then a temp file). Here that spool rolls over into the data volume, so a
large CSV takes neither memory nor system temp space. Fields keep Starlette's own limits.
"""

from pathlib import Path
from tempfile import SpooledTemporaryFile

from fastapi import Request
from starlette.datastructures import FormData
from starlette.formparsers import MultiPartException, MultiPartParser


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
