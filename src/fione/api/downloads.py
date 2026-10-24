"""File downloads: safe ``Content-Disposition`` headers, streams that fail before their headers
are sent, and the temp directory under ``data_dir`` for files built on the way out."""

import itertools
import re
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote

from fastapi.responses import StreamingResponse

from fione.config import Settings


def _ascii_filename(name: str, fallback: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return safe or fallback


def content_disposition(name: str, extension: str = ".csv", fallback: str = "dataset") -> str:
    """``attachment`` with an ASCII-only ``filename`` and the exact name as RFC 5987
    ``filename*``; neither can carry quotes, CR/LF or other header syntax."""
    filename = name if name.lower().endswith(extension) else f"{name}{extension}"
    ascii_name = _ascii_filename(filename[: -len(extension)], fallback) + extension
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename, safe='')}"


def attachment(chunks: Iterator[bytes], media_type: str, disposition: str) -> StreamingResponse:
    """Stream ``chunks`` as a download. The first chunk is pulled here, before any header is
    sent, so a failure building the file is an error response, not a cut 200."""
    first = next(chunks, b"")
    return StreamingResponse(
        itertools.chain([first], chunks),
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )


def tmp_dir(settings: Settings) -> Path:
    """``<data_dir>/tmp``: temp files of downloads and imports stay on the data volume."""
    path = settings.data_dir / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return path
