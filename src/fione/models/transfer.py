"""Moving a trained model between installs: export it as a zip, import such a zip (spec 5.3).

An export zip holds ``manifest.json`` and ``model.joblib`` (the artifact as stored) and
``record.json`` (the row's metadata). Importing means accepting a pickle from outside, so:

* only an admin may do it;
* the zip is handled strictly: three exact member names, per-member size caps enforced while
  reading (never from the header), a compression-ratio limit, no encryption, and a bound on the
  central directory read before the zip is even opened;
* nothing is ever unpickled: the artifact is verified by ``verify_artifact`` (manifest schema,
  HMAC, streamed sha256) and loaded only later, by ``load_model``, which verifies again;
* a model signed by another install (or by an unknown party) is refused unless the admin
  vouches for the file with ``trust_foreign``. Its integrity is still checked, the manifest is
  re-signed under this install's secret so it loads normally, and the row is flagged
  ``trusted=0``.

``record.json`` also carries ``trusted`` (a required bool): the stored flag is that value and
the signature check ANDed, so an export of an unverified model never comes back as trusted
and a record cannot vouch for a file whose signature fails. The record's key set is exact, so
exports made before ``trusted`` was added are refused (v2 was unreleased).

Everything written for a failed import (objects and row) is deleted again.
"""

import io
import json
import logging
import os
import shutil
import sqlite3
import struct
import tempfile
import uuid
import zipfile
import zlib
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO

from fione.auth.roles import User, can_access_project, require_admin
from fione.engine.artifact import (
    MANIFEST_FILE,
    MODEL_FILE,
    Manifest,
    resign_manifest,
    verify_artifact,
    verify_manifest_hmac,
)
from fione.engine.config import TrainConfig
from fione.jobs import store
from fione.jobs.store import Job
from fione.models import service
from fione.models.service import ModelNotFound, ModelRecord
from fione.projects import service as projects
from fione.storage import Storage

log = logging.getLogger(__name__)

RECORD_FILE = "record.json"
MEMBERS = (MANIFEST_FILE, MODEL_FILE, RECORD_FILE)
RECORD_FIELDS = (
    "name",
    "task",
    "target",
    "best_model",
    "stop_reason",
    "config",
    "leaderboard",
    "trials",
    "metrics",
    "importance",
    "trusted",
)
STOP_REASONS = frozenset({"time", "max_models", "no_improvement", "cancelled", "error"})
IMPORTED_SUFFIX = " (imported)"
MAX_NAME_CHARS = 200

CHUNK = 1 << 20
READ_CHUNK = 1 << 16  # small enough that a bomb is caught early by the ratio check
MANIFEST_CAP = 64 * 1024
RECORD_CAP = 4 * (1 << 20)
MAX_ARCHIVE_BYTES = 512 * (1 << 20)
MAX_RATIO = 200  # uncompressed : compressed, for deflated members
MAX_DIRECTORY_ENTRIES = 16
MAX_DIRECTORY_BYTES = 64 * 1024

_ZIP_ERRORS = (
    zipfile.BadZipFile,
    zipfile.LargeZipFile,
    EOFError,
    zlib.error,
    NotImplementedError,
    RuntimeError,
    OSError,  # a crafted directory can make zipfile seek to a bad offset
    UnicodeDecodeError,  # a name flagged UTF-8 that is not
)


class ModelImportError(ValueError):
    """The file is not an acceptable model export; the message says why, in plain words."""


# --- export -----------------------------------------------------------------------------------


def _info(name: str, compress_type: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = compress_type
    return info


def _record_json(record: ModelRecord) -> bytes:
    body = {field: getattr(record, field) for field in RECORD_FIELDS}
    body["trusted"] = bool(record.trusted)
    return json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")


def _write_export(storage: Storage, record: ModelRecord, out: BinaryIO) -> None:
    with zipfile.ZipFile(out, "w") as zf:
        for name, kind in ((MANIFEST_FILE, zipfile.ZIP_DEFLATED), (MODEL_FILE, zipfile.ZIP_STORED)):
            try:
                source = storage.open_read(record.storage_prefix + name)
            except KeyError as e:
                raise ModelNotFound(f"model {record.id}: {name} is missing from storage") from e
            with source, zf.open(_info(name, kind), "w", force_zip64=name == MODEL_FILE) as dest:
                shutil.copyfileobj(source, dest, CHUNK)
        zf.writestr(_info(RECORD_FILE, zipfile.ZIP_DEFLATED), _record_json(record))


def export_model(
    storage: Storage, record: ModelRecord, *, tmp_dir: Path | None = None
) -> Iterator[bytes]:
    """The model as a zip, in 1 MiB chunks.

    The zip is built in a temp file when the first chunk is asked for (so a generator that is
    never started makes nothing, and a missing object raises ``ModelNotFound`` from that first
    read) and the file is removed when the generator ends, fails or is closed early.
    """
    fd, path = tempfile.mkstemp(prefix="fione-export-", suffix=".zip", dir=tmp_dir)
    try:
        with os.fdopen(fd, "wb") as out:
            _write_export(storage, record, out)
        with open(path, "rb") as f:
            while chunk := f.read(CHUNK):
                yield chunk
    finally:
        os.unlink(path)


# --- import: the zip --------------------------------------------------------------------------


def _spool(stream: BinaryIO, path: Path, max_bytes: int) -> None:
    """Copy ``stream`` to ``path``, giving up as soon as it is longer than ``max_bytes``."""
    total = 0
    with open(path, "wb") as out:
        while chunk := stream.read(CHUNK):
            total += len(chunk)
            if total > max_bytes:
                raise ModelImportError("file too large")
            out.write(chunk)


def _check_directory(path: Path) -> None:
    """Bound the central directory before ``zipfile`` parses it (it reads every entry)."""
    size = path.stat().st_size
    with open(path, "rb") as f:
        f.seek(max(0, size - (0xFFFF + 22 + 20)))
        tail = f.read()
    at = tail.rfind(b"PK\x05\x06")
    if at < 0 or len(tail) - at < 22:
        raise ModelImportError("this is not a model export file")
    if at >= 20 and tail[at - 20 : at - 16] == b"PK\x06\x07":
        # Python follows a zip64 locator and replaces the counts below with the zip64 ones,
        # which this check cannot bound cheaply. Exports under 4 GiB never have one.
        raise ModelImportError("zip64 archives are not supported")
    entries, directory_bytes = struct.unpack_from("<HI", tail, at + 10)
    if entries > MAX_DIRECTORY_ENTRIES or directory_bytes > MAX_DIRECTORY_BYTES:
        raise ModelImportError("the file has too many entries")


def _members(zf: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = zf.infolist()
    names = [i.filename for i in infos]
    if len(set(names)) != len(names):
        raise ModelImportError("the file has the same entry twice")
    for info in infos:
        if info.filename not in MEMBERS:  # also rules out '/', '\', '..' and absolute names
            raise ModelImportError(f"unexpected entry in the file: {info.filename[:40]!r}")
        if info.flag_bits & 0x1:
            raise ModelImportError("encrypted entries are not supported")
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise ModelImportError("unsupported compression in the file")
    for name in MEMBERS:
        if name not in names:
            raise ModelImportError(f"the file has no {name}")
    return {i.filename: i for i in infos}


def _member_chunks(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> Iterator[bytes]:
    """The member's bytes; only errors from reading the zip become ``ModelImportError``."""
    try:
        with zf.open(info) as source:
            while chunk := source.read(READ_CHUNK):
                yield chunk
    except _ZIP_ERRORS as e:
        raise ModelImportError(f"{info.filename} is damaged") from e


def _copy_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo, out: BinaryIO, cap: int) -> None:
    """Copy one member, enforcing ``cap`` and the ratio limit on what is actually read.

    Reads to the end of the member, which is when ``zipfile`` checks its CRC. A failure to
    write to ``out`` (a full disk) is not the file's fault and surfaces as itself.
    """
    if info.file_size > cap:
        raise ModelImportError(f"{info.filename} is too large")
    total = 0
    for chunk in _member_chunks(zf, info):
        total += len(chunk)
        if total > cap:
            raise ModelImportError(f"{info.filename} is too large")
        if info.compress_type == zipfile.ZIP_DEFLATED and total > MAX_RATIO * max(
            info.compress_size, 1
        ):
            raise ModelImportError(f"{info.filename} has a suspicious compression ratio")
        out.write(chunk)


def _read_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo, cap: int) -> bytes:
    out = io.BytesIO()
    _copy_member(zf, info, out, cap)
    return out.getvalue()


# --- import: record.json ----------------------------------------------------------------------


def _bad_record(what: str) -> ModelImportError:
    return ModelImportError(f"{RECORD_FILE} is not valid: {what}")


def _reject_constant(name: str):
    raise ValueError(f"{name} is not allowed")


def _is_number(value) -> bool:
    return value is None or (isinstance(value, int | float) and not isinstance(value, bool))


def _parse_record(raw: bytes, manifest: Manifest) -> dict:
    """The row's fields from ``record.json``, strictly checked; ``ModelImportError`` if not."""
    try:
        record = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except (ValueError, RecursionError) as e:
        raise _bad_record("it is not strict JSON") from e
    if not isinstance(record, dict) or set(record) != set(RECORD_FIELDS):
        raise _bad_record("unexpected fields")
    for field in ("name", "task", "target", "best_model", "stop_reason"):
        if not isinstance(record[field], str):
            raise _bad_record(f"{field} must be text")
    if len(record["name"]) > MAX_NAME_CHARS or len(record["best_model"]) > MAX_NAME_CHARS:
        raise _bad_record("a name is too long")
    if record["task"] != manifest.task or record["target"] != manifest.target:
        raise _bad_record("it does not match the manifest")
    if record["stop_reason"] not in STOP_REASONS:
        raise _bad_record("unknown stop_reason")
    if not isinstance(record["trusted"], bool):
        raise _bad_record("trusted must be true or false")
    if not isinstance(record["config"], dict):
        raise _bad_record("config must be an object")
    try:
        record["config"] = TrainConfig.from_dict(record["config"]).to_dict()
    except (ValueError, TypeError) as e:  # ConfigError is a ValueError
        raise _bad_record(f"config: {e}") from e
    if record["config"]["target"] != manifest.target:
        raise _bad_record("config does not match the manifest")
    for field in ("leaderboard", "trials"):
        rows = record[field]
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise _bad_record(f"{field} must be a list of objects")
    for field in ("metrics", "importance"):
        values = record[field]
        if not isinstance(values, dict) or not all(_is_number(v) for v in values.values()):
            raise _bad_record(f"{field} must map names to numbers")
    try:  # the database stores UTF-8 JSON: a lone surrogate or absurd nesting must fail here
        json.dumps(record, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, RecursionError) as e:
        raise _bad_record("it holds text that cannot be stored") from e
    return record


# --- import -----------------------------------------------------------------------------------


def import_model(
    storage: Storage,
    conn: sqlite3.Connection,
    admin: User,
    project_id: str,
    zip_stream: BinaryIO,
    secret: bytes,
    *,
    trust_foreign: bool = False,
    tmp_dir: Path | None = None,
    max_bytes: int = MAX_ARCHIVE_BYTES,
) -> ModelRecord:
    """Add the exported model in ``zip_stream`` to the project. Admin only; never unpickles.

    By default the manifest must carry a valid HMAC for ``secret`` (``UntrustedArtifactError``
    otherwise). With ``trust_foreign`` a foreign signature is accepted on the admin's word: the
    file's sha256 is still checked, the manifest is re-signed with ``secret`` and the row gets
    ``trusted=0`` (a valid signature still gives ``trusted=1``). ``ModelImportError`` (a
    ``ValueError``) reports a file that is not an acceptable export. A failed import leaves no
    row and no object behind.
    """
    require_admin(admin)
    projects.require_project(conn, project_id)
    with tempfile.TemporaryDirectory(prefix="fione-import-", dir=tmp_dir) as work:
        archive = Path(work) / "upload.zip"
        _spool(zip_stream, archive, max_bytes)
        _check_directory(archive)
        model_path = Path(work) / MODEL_FILE
        try:
            zf = zipfile.ZipFile(archive)
        except _ZIP_ERRORS as e:
            raise ModelImportError("this is not a model export file") from e
        with zf:
            members = _members(zf)
            manifest_bytes = _read_member(zf, members[MANIFEST_FILE], MANIFEST_CAP)
            record_bytes = _read_member(zf, members[RECORD_FILE], RECORD_CAP)
            manifest = Manifest.from_json(manifest_bytes)
            if set(manifest.files) != {MODEL_FILE}:
                raise ModelImportError("the manifest lists files other than the model")
            fields = _parse_record(record_bytes, manifest)
            with open(model_path, "wb") as out:
                _copy_member(zf, members[MODEL_FILE], out, max_bytes)
        return _store(
            storage, conn, project_id, model_path, manifest_bytes, fields, secret, trust_foreign
        )


def _store(
    storage, conn, project_id, model_path, manifest_bytes, fields, secret, trust_foreign
) -> ModelRecord:
    prefix = f"projects/{project_id}/models/{uuid.uuid4().hex}/"
    try:
        with open(model_path, "rb") as f:
            storage.put(prefix + MODEL_FILE, f)
        storage.put(prefix + MANIFEST_FILE, manifest_bytes)  # last: the artifact is complete
        manifest = verify_artifact(storage, prefix, secret, require_hmac=not trust_foreign)
        signed_here = verify_manifest_hmac(manifest, secret)
        if not signed_here:  # only reachable with trust_foreign
            storage.put(
                prefix + MANIFEST_FILE, resign_manifest(manifest, secret).to_json().encode()
            )
        return service.insert_model(
            conn,
            project_id=project_id,
            dataset_id=None,
            job_id=None,
            name=fields["name"][: MAX_NAME_CHARS - len(IMPORTED_SUFFIX)] + IMPORTED_SUFFIX,
            task=fields["task"],
            target=fields["target"],
            best_model=fields["best_model"],
            stop_reason=fields["stop_reason"],
            storage_prefix=prefix,
            # The signature governs; the record can only lower trust, never raise it.
            trusted=signed_here and fields["trusted"],
            config=fields["config"],
            leaderboard=fields["leaderboard"],
            trials=fields["trials"],
            metrics=fields["metrics"],
            importance=fields["importance"],
        )
    except BaseException:
        # Never mask the original error (a JobAbort must stay a JobAbort).
        try:  # the row too: an interrupt right after the INSERT can leave one behind
            conn.execute("DELETE FROM models WHERE storage_prefix = ?", (prefix,))
        except Exception:
            log.exception("could not remove the model row for %s", prefix)
        try:
            storage.delete_prefix(prefix)
        except Exception:
            log.exception("could not remove the objects under %s", prefix)
        raise


# --- export of a whole project ----------------------------------------------------------------


def submit_export_all(conn: sqlite3.Connection, user: User, project_id: str) -> Job:
    """Queue an ``export_models`` job; read access to the project is enough."""
    projects.require_project(conn, project_id)
    if not can_access_project(conn, user, project_id, "read"):
        raise PermissionError("access to the project is required")
    return store.enqueue(conn, "export_models", project_id, user.id, {})
