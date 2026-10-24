"""The serving bundle: a zip with the model files, and the ``docker run`` command that serves it."""

import json
import os
import re
import shlex
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from fione.config import Settings
from fione.engine.artifact import MANIFEST_FILE, MODEL_FILE, UntrustedArtifactError, read_manifest
from fione.models.service import ModelNotFound, ModelRecord
from fione.storage import Storage

CHUNK = 1 << 20
CONTAINER_PORT = 8080
HOST_PORT = 8081


@dataclass(frozen=True)
class Bundle:
    filename: str
    run_command: str
    example_curl: str
    open: Callable[[], Iterator[bytes]]  # the zip, in chunks; see ``make_serving_bundle``


def _filename(record: ModelRecord) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", record.name).strip("-")
    return f"fione-serving-{slug or 'model'}-{record.id}.zip"


def example_curl(columns: Sequence[str]) -> str:
    """A ``curl`` call to ``/invocations`` with one instance of ``"?"`` placeholders."""
    body = json.dumps({"instances": [{c: "?" for c in columns}]}, ensure_ascii=False)
    return (
        f"curl -s -X POST localhost:{HOST_PORT}/invocations"
        f" -H 'Content-Type: application/json' -d {shlex.quote(body)}"
    )


def _write_zip(storage: Storage, record: ModelRecord, out) -> None:
    with zipfile.ZipFile(out, "w") as zf:
        for name, kind in ((MANIFEST_FILE, zipfile.ZIP_DEFLATED), (MODEL_FILE, zipfile.ZIP_STORED)):
            try:
                source = storage.open_read(record.storage_prefix + name)
            except KeyError as e:
                raise ModelNotFound(f"model {record.id}: {name} is missing from storage") from e
            info = zipfile.ZipInfo(f"model/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = kind
            with source, zf.open(info, "w", force_zip64=name == MODEL_FILE) as dest:
                shutil.copyfileobj(source, dest, CHUNK)


def make_serving_bundle(
    storage: Storage, record: ModelRecord, settings: Settings, *, tmp_dir: Path | None = None
) -> Bundle:
    """The bundle for ``record``: ``model/manifest.json`` and ``model/model.joblib`` as stored.

    ``ModelNotFound`` if the manifest is missing or unreadable here, or if a file is missing
    from storage when ``open()`` is read (from its first chunk). The zip is built in a temp
    file at the first chunk and removed when the stream ends, fails or is closed early. The
    command mounts the unzipped ``model`` directory into the image tagged as the manifest says.
    """
    try:
        manifest = read_manifest(storage, record.storage_prefix)
    except UntrustedArtifactError as e:
        raise ModelNotFound(f"model {record.id}: {e}") from e

    def stream() -> Iterator[bytes]:
        fd, path = tempfile.mkstemp(prefix="fione-serving-", suffix=".zip", dir=tmp_dir)
        try:
            with os.fdopen(fd, "wb") as out:
                _write_zip(storage, record, out)
            with open(path, "rb") as f:
                while chunk := f.read(CHUNK):
                    yield chunk
        finally:
            os.unlink(path)

    return Bundle(
        filename=_filename(record),
        run_command=(
            f'docker run --rm -p {HOST_PORT}:{CONTAINER_PORT} -v "$PWD/model:/model:ro" '
            f"{settings.serving_image}:{manifest.image_tag}"
        ),
        example_curl=example_curl(manifest.columns),
        open=stream,
    )
