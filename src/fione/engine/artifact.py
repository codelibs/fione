"""The model artifact: ``model.joblib`` plus a signed ``manifest.json`` under one storage prefix.

A model file is a pickle, and unpickling untrusted bytes runs arbitrary code. The trust
boundary is therefore the manifest: it carries the sha256 of every file and an HMAC-SHA256,
keyed by the server secret, over the rest of the manifest (so over those hashes too).
``load_model`` checks the HMAC, then the hash, and only then unpickles; every failure raises
``UntrustedArtifactError`` before ``joblib.load`` is reached.

The HMAC covers the canonical JSON (sorted keys, no whitespace, UTF-8) of the manifest
without its ``hmac`` field. ``Manifest.from_json`` rejects unknown fields, so no field can be
added to a signed manifest without being covered.
"""

import hashlib
import hmac
import io
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import joblib

from fione.engine.model import TrainedModel
from fione.storage.base import Storage
from fione.version import __version__

FORMAT_VERSION = 1
MODEL_FILE = "model.joblib"
MANIFEST_FILE = "manifest.json"

_CHUNK = 1 << 20
_DTYPES = {"int": int, "float": float, "bool": bool, "str": str}
_UNSUPPORTED = "unsupported artifact format"


class UntrustedArtifactError(Exception):
    """The artifact is missing, corrupt, tampered with or signed with another secret."""


@dataclass
class Manifest:
    format_version: int
    fione_version: str
    image_tag: str
    files: dict[str, str]  # file name -> sha256 hex
    hmac: str  # hex
    task: str
    classes: list | None  # JSON-native labels; None for regression
    classes_dtype: str | None  # "int", "float", "bool" or "str"; None for regression
    columns: list[str]
    target: str
    created_at: str  # UTC, ISO 8601

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2)

    @classmethod
    def from_json(cls, text: str | bytes) -> "Manifest":
        """Parse and schema-check a manifest; raise ``UntrustedArtifactError`` if it is not one."""
        try:
            raw = json.loads(text)
        except ValueError as e:  # includes JSONDecodeError and UnicodeDecodeError
            raise UntrustedArtifactError("manifest is not valid JSON") from e
        if not isinstance(raw, dict):
            raise UntrustedArtifactError("manifest is not a JSON object")
        version = raw.get("format_version")
        if isinstance(version, int) and not isinstance(version, bool) and version != FORMAT_VERSION:
            raise UntrustedArtifactError(_UNSUPPORTED)
        _check_schema(raw)
        return cls(**raw)


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _check_schema(raw: dict) -> None:
    classes, dtype = raw.get("classes"), raw.get("classes_dtype")
    files = raw.get("files")
    version = raw.get("format_version")
    valid = (
        set(raw) == {f.name for f in Manifest.__dataclass_fields__.values()}
        and isinstance(version, int)
        and not isinstance(version, bool)
        and all(isinstance(raw[k], str) for k in ("fione_version", "image_tag", "hmac"))
        and all(isinstance(raw[k], str) for k in ("task", "target", "created_at"))
        and isinstance(files, dict)
        and all(isinstance(k, str) and isinstance(v, str) for k, v in files.items())
        and _is_str_list(raw["columns"])
        and (
            (classes is None and dtype is None)
            or (isinstance(classes, list) and dtype in _DTYPES and _classes_match(classes, dtype))
        )
    )
    if not valid:
        raise UntrustedArtifactError("manifest does not match the expected schema")


def _classes_match(classes: list, dtype: str) -> bool:
    kind = _DTYPES[dtype]
    if kind is float:  # JSON has no separate int type for whole floats
        return all(isinstance(c, int | float) and not isinstance(c, bool) for c in classes)
    return all(type(c) is kind for c in classes)


def _classes_to_json(classes: list | None) -> tuple[list | None, str | None]:
    if classes is None:
        return None, None
    plain = [c.item() if hasattr(c, "item") else c for c in classes]
    for name, kind in _DTYPES.items():
        if name != "str" and all(type(c) is kind for c in plain):
            return plain, name
    if all(isinstance(c, int | float) and not isinstance(c, bool) for c in plain):
        return [float(c) for c in plain], "float"
    return [str(c) for c in plain], "str"


def _sign(raw: dict, secret: bytes) -> str:
    body = {k: v for k, v in raw.items() if k != "hmac"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_manifest_hmac(manifest: Manifest, secret: bytes) -> bool:
    return hmac.compare_digest(_sign(asdict(manifest), secret), manifest.hmac)


def _sha256_of(fileobj) -> str:
    digest = hashlib.sha256()
    while chunk := fileobj.read(_CHUNK):
        digest.update(chunk)
    return digest.hexdigest()


def save_model(
    model: TrainedModel, storage: Storage, prefix: str, secret: bytes, *, image_tag: str
) -> Manifest:
    """Write ``model.joblib`` and then the signed ``manifest.json`` under ``prefix``.

    The model is dumped with zlib level 1: on an Adult model (2.7 MB raw) that is 2.5x smaller
    for about 10 ms more to dump and load; higher levels gain little more (level 6: 2.9x, 70 ms).
    On any failure the objects written so far are deleted and the error is re-raised.
    """
    if not prefix.endswith("/"):
        raise ValueError(f"prefix must end with '/': {prefix!r}")
    classes, dtype = _classes_to_json(model.classes_)
    fd, tmp_path = tempfile.mkstemp(prefix="fione-model-", suffix=".joblib")
    written: list[str] = []
    try:
        with os.fdopen(fd, "wb") as out:
            joblib.dump(model, out, compress=1)
        with open(tmp_path, "rb") as f:
            digest = _sha256_of(f)
        manifest = Manifest(
            format_version=FORMAT_VERSION,
            fione_version=__version__,
            image_tag=image_tag,
            files={MODEL_FILE: digest},
            hmac="",
            task=model.task,
            classes=classes,
            classes_dtype=dtype,
            columns=list(model.columns),
            target=model.target,
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        manifest.hmac = _sign(asdict(manifest), secret)
        written.append(prefix + MODEL_FILE)
        with open(tmp_path, "rb") as f:
            storage.put(prefix + MODEL_FILE, f)
        written.append(prefix + MANIFEST_FILE)
        storage.put(prefix + MANIFEST_FILE, manifest.to_json().encode("utf-8"))
        return manifest
    except BaseException:
        for key in written:
            storage.delete(key)
        raise
    finally:
        os.unlink(tmp_path)


def read_manifest(storage: Storage, prefix: str) -> Manifest:
    """Parse the manifest under ``prefix``. This verifies nothing: see ``load_model``."""
    try:
        text = storage.get(prefix + MANIFEST_FILE)
    except KeyError as e:
        raise UntrustedArtifactError("manifest is missing") from e
    return Manifest.from_json(text)


def _read_verified(storage: Storage, prefix: str, manifest: Manifest, names: list[str]) -> dict:
    """Read each named file once and check it against the manifest; return the bytes by name."""
    contents = {}
    for name in names:
        expected = manifest.files.get(name)
        if expected is None:
            raise UntrustedArtifactError(f"{name} is not part of the artifact")
        try:
            data = storage.get(prefix + name)
        except (KeyError, ValueError) as e:
            raise UntrustedArtifactError(f"{name} is missing") from e
        if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), expected):
            raise UntrustedArtifactError(f"{name} does not match its recorded hash")
        contents[name] = data
    return contents


def _unpickle(data: bytes) -> TrainedModel:
    # The bytes that were hashed are the bytes that are loaded, so the file cannot change
    # between the check and the use.
    return joblib.load(io.BytesIO(data))


def load_model(storage: Storage, prefix: str, secret: bytes) -> TrainedModel:
    """Load a model after verifying the manifest's HMAC and the model file's sha256.

    Nothing is unpickled unless both checks pass; otherwise ``UntrustedArtifactError``.
    """
    manifest = read_manifest(storage, prefix)
    if not verify_manifest_hmac(manifest, secret):
        raise UntrustedArtifactError("manifest signature does not match")
    data = _read_verified(storage, prefix, manifest, [MODEL_FILE])[MODEL_FILE]
    return _unpickle(data)


def load_model_unverified_hash_only(storage: Storage, prefix: str) -> TrainedModel:
    """Load a model after checking only the sha256 of every file the manifest lists.

    For the serving image, which has no secret and so cannot check the HMAC. This guards
    against corruption and accidental mix-ups, not against an attacker: whoever can write
    the artifact can write a matching manifest, and unpickling it runs their code. The
    operator is trusted to deploy only artifacts they trained themselves (integrity, not
    authenticity). Use ``load_model`` wherever the secret is available.
    """
    manifest = read_manifest(storage, prefix)
    data = _read_verified(storage, prefix, manifest, sorted({MODEL_FILE, *manifest.files}))
    return _unpickle(data[MODEL_FILE])
