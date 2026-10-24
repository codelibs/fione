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

# Docker's tag grammar, and a conservative image name: lowercase path components, optional
# registry host:port. Both end up in a command people paste into a shell.
IMAGE_TAG = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}")
IMAGE_NAME = re.compile(r"[a-z0-9]+([._-][a-z0-9]+)*(:[0-9]+)?(/[a-z0-9]+([._-][a-z0-9]+)*)*")
MAX_SLUG = 80
_SHOWN_CHARS = 50

CHUNK = 1 << 20
# The zip's members, in order; the run command mounts the unzipped ``model`` directory.
_MEMBERS = ((MANIFEST_FILE, zipfile.ZIP_DEFLATED), (MODEL_FILE, zipfile.ZIP_STORED))
BUNDLE_FILES = tuple(f"model/{name}" for name, _ in _MEMBERS)
CONTAINER_PORT = 8080
HOST_PORT = 8081


class BundleError(ValueError):
    """The bundle cannot be made safely; the message says which part is wrong."""


@dataclass(frozen=True)
class Bundle:
    filename: str
    run_command: str
    example_curl: str
    open: Callable[[], Iterator[bytes]]  # the zip, in chunks; see ``make_serving_bundle``


def _filename(record: ModelRecord) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", record.name)[:MAX_SLUG].strip("-")
    return f"fione-serving-{slug or 'model'}-{record.id}.zip"


def _check_image(image: str, tag: str) -> None:
    if not IMAGE_NAME.fullmatch(image):
        raise BundleError(f"the serving image name is not a valid image name: {_shown(image)}")
    if not IMAGE_TAG.fullmatch(tag):
        raise BundleError(
            f"the image tag in the model's manifest is not a valid tag: {_shown(tag)}"
        )


def _shown(text: str) -> str:
    text = repr(text)
    return text if len(text) <= _SHOWN_CHARS else text[: _SHOWN_CHARS - 3] + "..."


def example_curl(columns: Sequence[str]) -> str:
    """A ``curl`` call to ``/invocations`` with one instance of ``"?"`` placeholders."""
    body = json.dumps(
        {"instances": [{c: "?" for c in columns}]}, ensure_ascii=False, separators=(",", ":")
    )
    return (
        f"curl -s -X POST localhost:{HOST_PORT}/invocations"
        f" -H 'Content-Type: application/json' -d {shlex.quote(body)}"
    )


def _write_zip(storage: Storage, record: ModelRecord, out) -> None:
    with zipfile.ZipFile(out, "w") as zf:
        for name, kind in _MEMBERS:
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

    ``BundleError`` if the manifest's image tag or ``settings.serving_image`` is not a valid
    Docker tag or image name (a foreign model's manifest can hold any text).
    ``ModelNotFound`` if the manifest is missing or unreadable here, or if a file is missing
    from storage when ``open()`` is read (from its first chunk). The zip is built in a temp
    file at the first chunk and removed when the stream ends, fails or is closed early. The
    command mounts the unzipped ``model`` directory into the image tagged as the manifest says.
    """
    try:
        manifest = read_manifest(storage, record.storage_prefix)
    except UntrustedArtifactError as e:
        raise ModelNotFound(f"model {record.id}: {e}") from e

    _check_image(settings.serving_image, manifest.image_tag)
    image = shlex.quote(f"{settings.serving_image}:{manifest.image_tag}")

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
            f'docker run --rm -p {HOST_PORT}:{CONTAINER_PORT} -v "$PWD/model:/model:ro" {image}'
        ),
        example_curl=example_curl(manifest.columns),
        open=stream,
    )
