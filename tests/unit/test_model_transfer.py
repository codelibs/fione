import dataclasses
import errno
import io
import json
import os
import pickle
import sqlite3
import struct
import warnings
import zipfile
from types import SimpleNamespace

import joblib
import pandas as pd
import pytest
from predict_models import classifier, features, regressor

from fione import db
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.config import Settings, load_secret
from fione.engine.artifact import (
    MODEL_FILE,
    UntrustedArtifactError,
    _sign,
    read_manifest,
    save_model,
    verify_artifact,
)
from fione.models import service as models
from fione.models import transfer
from fione.models.transfer import ModelImportError, export_model, import_model
from fione.predict import batch_predict
from fione.projects import service as projects
from fione.projects.service import ProjectNotFound
from fione.storage import open_storage

MIB = 1 << 20
FOREIGN_SECRET = b"f" * 32
COPIED = ("task", "target", "best_model", "stop_reason", "config", "leaderboard", "trials")


def make_env(base, secret=None, *, role=Role.ADMIN):
    """A fresh instance: database, storage, an admin and a project."""
    base.mkdir(parents=True, exist_ok=True)
    settings = Settings(data_dir=base / "data")
    conn = db.connect(base / "fione.db")
    db.migrate(conn)
    tmp = base / "tmp"
    tmp.mkdir()
    admin = auth.create_user(conn, "admin", "pw-admin-1", role)
    return SimpleNamespace(
        conn=conn,
        storage=open_storage(settings),
        admin=admin,
        project=projects.create_project(conn, admin, "demo"),
        secret=secret or load_secret(settings),
        tmp=tmp,
    )


def add_model(env, model, name="m", prefix=None, secret=None):
    prefix = prefix or f"projects/{env.project.id}/models/abc123/"
    save_model(model, env.storage, prefix, secret or env.secret, image_tag="test")
    return models.add_model(
        env.conn,
        project_id=env.project.id,
        dataset_id=None,
        job_id=None,
        name=name,
        model=model,
        storage_prefix=prefix,
    )


def exported(env, record) -> bytes:
    return b"".join(export_model(env.storage, record, tmp_dir=env.tmp))


def parts(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return {i.filename: zf.read(i) for i in zf.infolist()}


def build_zip(members, compression=zipfile.ZIP_STORED) -> bytes:
    buf = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # zipfile warns about duplicate names
        with zipfile.ZipFile(buf, "w", compression) as zf:
            for name, content in members:
                zf.writestr(name, content)
    return buf.getvalue()


def rebuilt(src: dict[str, bytes], **changes) -> bytes:
    """The valid members with some replaced (by name: manifest, model, record) or dropped (None)."""
    names = {"manifest": "manifest.json", "model": "model.joblib", "record": "record.json"}
    merged = dict(src)
    for key, value in changes.items():
        if value is None:
            merged.pop(names[key], None)
        else:
            merged[names[key]] = value
    return build_zip(list(merged.items()))


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    env = make_env(tmp_path_factory.mktemp("source"))
    record = add_model(env, classifier(), name="日本語モデル")
    data = exported(env, record)
    return SimpleNamespace(
        env=env, record=record, zip=data, parts=parts(data), secret=env.secret, model=classifier()
    )


@pytest.fixture
def dest(tmp_path, source):
    env = make_env(tmp_path / "dest", source.secret)
    yield env
    env.conn.close()


def do_import(dest, data, **kw):
    return import_model(
        dest.storage,
        dest.conn,
        kw.pop("admin", dest.admin),
        kw.pop("project_id", dest.project.id),
        io.BytesIO(data),
        kw.pop("secret", dest.secret),
        tmp_dir=dest.tmp,
        **kw,
    )


def assert_nothing_left(dest):
    assert dest.conn.execute("SELECT COUNT(*) FROM models").fetchone()[0] == 0
    assert dest.storage.list("") == []
    assert list(dest.tmp.iterdir()) == []


@pytest.fixture
def unpickles(monkeypatch):
    """Names of the unpickling calls made, so a test can show the import made none."""
    calls = []

    def spying(name, real):
        def spy(*args, **kwargs):
            calls.append(name)
            return real(*args, **kwargs)

        return spy

    monkeypatch.setattr(joblib, "load", spying("joblib.load", joblib.load))
    monkeypatch.setattr(pickle, "load", spying("pickle.load", pickle.load))
    monkeypatch.setattr(pickle, "loads", spying("pickle.loads", pickle.loads))
    return calls


# --- permissions ------------------------------------------------------------------------------


class Untouchable(io.RawIOBase):
    def read(self, n=-1):
        raise AssertionError("the stream was read")


@pytest.mark.parametrize("role", [Role.EDITOR, Role.VIEWER])
def test_only_an_admin_can_import(dest, role):
    user = auth.create_user(dest.conn, "someone", "pw-someone-1", role)
    with pytest.raises(PermissionError):
        import_model(dest.storage, dest.conn, user, dest.project.id, Untouchable(), dest.secret)
    assert_nothing_left(dest)


def test_the_permission_check_comes_before_the_project_check(dest):
    user = auth.create_user(dest.conn, "ed", "pw-editor-1", Role.EDITOR)
    with pytest.raises(PermissionError):
        import_model(dest.storage, dest.conn, user, "nope", Untouchable(), dest.secret)


def test_a_missing_project_is_refused(dest, source):
    with pytest.raises(ProjectNotFound):
        do_import(dest, source.zip, project_id="nope")
    assert_nothing_left(dest)


# --- the round trip ---------------------------------------------------------------------------


def test_an_exported_model_imports_into_a_fresh_instance(dest, source, unpickles):
    rec = do_import(dest, source.zip)
    assert unpickles == []  # the import never unpickles
    assert rec.name == "日本語モデル (imported)"
    assert (rec.project_id, rec.dataset_id, rec.job_id, rec.trusted) == (
        dest.project.id,
        None,
        None,
        1,
    )
    for field in COPIED:
        assert getattr(rec, field) == getattr(source.record, field), field
    assert rec.metrics == source.record.metrics and rec.importance == source.record.importance
    assert rec.target == "判定" and set(rec.importance) == {"幅", "x", "color"}
    assert models.get_model(dest.conn, rec.id) == rec

    prefix = rec.storage_prefix
    assert prefix.startswith(f"projects/{dest.project.id}/models/") and prefix.endswith("/")
    assert dest.storage.list("") == [prefix + "manifest.json", prefix + "model.joblib"]
    assert dest.conn.execute("SELECT COUNT(*) FROM models").fetchone()[0] == 1
    assert list(dest.tmp.iterdir()) == []

    loaded = models.load_trained(dest.storage, rec, dest.secret)
    assert unpickles.count("joblib.load") == 1  # the spy does see a real load
    frame = features(25)
    pd.testing.assert_frame_equal(batch_predict(loaded, frame), batch_predict(source.model, frame))


def test_a_regression_model_round_trips(tmp_path, dest):
    env = make_env(tmp_path / "reg")
    record = add_model(env, regressor(), name="reg")
    rec = do_import(dest, exported(env, record), secret=env.secret)
    assert rec.task == "regression" and rec.trusted == 1
    assert rec.metrics == record.metrics
    assert rec.diagnostics["task"] == "regression" and rec.diagnostics == record.diagnostics


@pytest.mark.parametrize(
    ("secret", "trusted"), [(None, 1), (FOREIGN_SECRET, 0)], ids=["signed", "trust-foreign"]
)
def test_export_import_keeps_diagnostics(dest, source, secret, trusted):
    assert source.record.diagnostics["task"] == "classification"
    assert json.loads(source.parts["record.json"])["diagnostics"] == source.record.diagnostics
    rec = do_import(dest, source.zip, secret=secret or dest.secret, trust_foreign=True)
    assert rec.trusted == trusted
    assert rec.diagnostics == source.record.diagnostics
    assert models.get_model(dest.conn, rec.id).diagnostics == source.record.diagnostics


def test_import_of_export_without_diagnostics(dest, source):
    """A Phase 1 export has no ``diagnostics`` key; it imports, and exports again without one."""
    rec = do_import(dest, rebuilt(source.parts, record=without(source, "diagnostics")))
    assert rec.diagnostics is None and rec.trusted == 1
    body = json.loads(parts(exported(dest, rec))["record.json"])
    assert set(body) == set(transfer.RECORD_FIELDS)


def test_importing_twice_makes_two_independent_models(dest, source):
    first, second = do_import(dest, source.zip), do_import(dest, source.zip)
    assert first.storage_prefix != second.storage_prefix and first.id != second.id


def test_null_metrics_and_importance_survive_a_round_trip(dest, source):
    record = json.loads(source.parts["record.json"])
    record["metrics"] = {"logloss": None, "accuracy": 0.9}
    record["importance"] = {"x": None}
    rec = do_import(dest, rebuilt(source.parts, record=json.dumps(record).encode()))
    assert rec.metrics == record["metrics"] and rec.importance == {"x": None}


# --- tampering and trust ----------------------------------------------------------------------


def test_a_changed_model_file_is_refused_and_nothing_is_left(dest, source, unpickles):
    tampered = bytearray(source.parts["model.joblib"])
    tampered[len(tampered) // 2] ^= 0xFF  # a valid zip again: only the sha256 can notice
    with pytest.raises(UntrustedArtifactError):
        do_import(dest, rebuilt(source.parts, model=bytes(tampered)))
    assert_nothing_left(dest)
    assert unpickles == []


def test_a_changed_manifest_is_refused_and_nothing_is_left(dest, source):
    manifest = json.loads(source.parts["manifest.json"])
    manifest["fione_version"] = "9.9.9"  # the signature no longer matches
    with pytest.raises(UntrustedArtifactError):
        do_import(dest, rebuilt(source.parts, manifest=json.dumps(manifest).encode()))
    assert_nothing_left(dest)


def test_a_manifest_that_is_not_one_is_refused(dest, source):
    for bad in (b"{", b"[]", b"{}", b"\xff\xfe"):
        with pytest.raises(UntrustedArtifactError):
            do_import(dest, rebuilt(source.parts, manifest=bad))
    assert_nothing_left(dest)


def test_a_model_signed_with_another_secret_is_refused_by_default(dest, source):
    with pytest.raises(UntrustedArtifactError):
        do_import(dest, source.zip, secret=FOREIGN_SECRET)
    assert_nothing_left(dest)


def test_trust_foreign_imports_resigns_and_flags_the_model(dest, source, unpickles):
    rec = do_import(dest, source.zip, secret=FOREIGN_SECRET, trust_foreign=True)
    assert unpickles == []  # still no unpickling at import
    assert rec.trusted == 0
    manifest = verify_artifact(dest.storage, rec.storage_prefix, FOREIGN_SECRET)
    original = json.loads(source.parts["manifest.json"])
    assert manifest.created_at == original["created_at"]
    assert manifest.files == original["files"] and manifest.columns == original["columns"]
    assert manifest.hmac != original["hmac"]
    loaded = models.load_trained(dest.storage, rec, FOREIGN_SECRET)
    frame = features(10)
    pd.testing.assert_frame_equal(batch_predict(loaded, frame), batch_predict(source.model, frame))
    with pytest.raises(UntrustedArtifactError):  # signed for the importing install only
        verify_artifact(dest.storage, rec.storage_prefix, source.secret)


def test_trust_foreign_with_a_valid_signature_stays_trusted(dest, source):
    rec = do_import(dest, source.zip, trust_foreign=True)
    assert rec.trusted == 1
    assert (
        read_manifest(dest.storage, rec.storage_prefix).hmac
        == json.loads(source.parts["manifest.json"])["hmac"]
    )  # nothing to re-sign


def test_trust_foreign_still_checks_the_file_hash(dest, source):
    tampered = bytearray(source.parts["model.joblib"])
    tampered[10] ^= 0xFF
    with pytest.raises(UntrustedArtifactError):
        do_import(
            dest,
            rebuilt(source.parts, model=bytes(tampered)),
            secret=FOREIGN_SECRET,
            trust_foreign=True,
        )
    assert_nothing_left(dest)


def test_trust_foreign_still_rejects_a_manifest_that_is_not_one(dest, source):
    with pytest.raises(UntrustedArtifactError):
        do_import(dest, rebuilt(source.parts, manifest=b"{}"), trust_foreign=True)
    assert_nothing_left(dest)


def test_a_manifest_listing_other_files_is_refused(dest, source):
    manifest = json.loads(source.parts["manifest.json"])
    manifest["files"]["extra.bin"] = manifest["files"][MODEL_FILE]
    manifest["hmac"] = _sign(manifest, dest.secret)  # validly signed, still not acceptable
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, manifest=json.dumps(manifest).encode()))
    assert_nothing_left(dest)


# --- hostile zips -----------------------------------------------------------------------------


def valid_members(source):
    return list(source.parts.items())


@pytest.mark.parametrize(
    "name",
    ["../x", "/abs", "a\\b", "unknown.txt", "sub/model.joblib", "..", "dir/", "Model.joblib"],
)
def test_a_member_with_a_bad_name_is_refused(dest, source, name):
    with pytest.raises(ModelImportError):
        do_import(dest, build_zip([*valid_members(source), (name, b"x")]))
    assert_nothing_left(dest)


def test_a_duplicate_member_is_refused(dest, source):
    with pytest.raises(ModelImportError):
        do_import(dest, build_zip([*valid_members(source), ("manifest.json", b"{}")]))
    assert_nothing_left(dest)


@pytest.mark.parametrize("missing", ["manifest", "model", "record"])
def test_a_missing_member_is_refused(dest, source, missing):
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, **{missing: None}))
    assert_nothing_left(dest)


def test_an_encrypted_member_is_refused(dest, source):
    data = bytearray(source.zip)
    start = 0
    while (at := data.find(b"PK\x01\x02", start)) != -1:  # set the encryption bit in the directory
        flags = struct.unpack_from("<H", data, at + 8)[0] | 1
        struct.pack_into("<H", data, at + 8, flags)
        start = at + 4
    with pytest.raises(ModelImportError):
        do_import(dest, bytes(data))
    assert_nothing_left(dest)


def test_a_compression_method_other_than_stored_or_deflate_is_refused(dest, source):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_BZIP2) as zf:
        for name, content in source.parts.items():
            zf.writestr(name, content)
    with pytest.raises(ModelImportError):
        do_import(dest, buf.getvalue())
    assert_nothing_left(dest)


def test_a_deflate_bomb_is_refused_before_it_is_read_in_full(dest, source, monkeypatch):
    zeros = b"\0" * (5 * MIB)
    members = [(n, source.parts[n]) for n in ("manifest.json", "record.json")]
    data = build_zip([*members, ("model.joblib", zeros)], zipfile.ZIP_DEFLATED)
    assert len(data) < 20_000
    read = []
    real = zipfile.ZipExtFile.read

    def counting(self, n=-1):
        chunk = real(self, n)
        read.append(len(chunk))
        return chunk

    monkeypatch.setattr(zipfile.ZipExtFile, "read", counting)
    with pytest.raises(ModelImportError, match="compression"):
        do_import(dest, data)
    assert sum(read) < 5 * MIB
    assert_nothing_left(dest)


def test_a_member_declared_larger_than_its_cap_is_refused(dest, source):
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, record=b" " * (5 * MIB)))
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, manifest=b" " * (65 * 1024)))
    assert_nothing_left(dest)


def test_a_model_larger_than_the_limit_is_refused(dest, source):
    with pytest.raises(ModelImportError):
        do_import(dest, source.zip, max_bytes=len(source.parts["model.joblib"]) - 1)
    assert_nothing_left(dest)


def test_a_member_whose_header_lies_about_its_size_is_refused(dest, source):
    data = bytearray(source.zip)
    at = data.find(b"PK\x01\x02")  # the first directory entry
    struct.pack_into("<I", data, at + 24, 3)  # claims 3 bytes of uncompressed data
    with pytest.raises(ModelImportError):
        do_import(dest, bytes(data))
    assert_nothing_left(dest)


def test_a_file_larger_than_the_limit_is_refused_while_it_is_read(dest):
    class Endless:
        read_bytes = 0

        def read(self, n=-1):
            self.read_bytes += n
            return b"x" * n

    stream = Endless()
    with pytest.raises(ModelImportError, match="file too large"):
        import_model(
            dest.storage, dest.conn, dest.admin, dest.project.id, stream, dest.secret, max_bytes=MIB
        )
    assert stream.read_bytes <= 2 * MIB + (1 << 20)  # it stopped soon after the limit


@pytest.mark.parametrize("damage", ["not a zip", "truncated", "crc"])
def test_a_broken_zip_is_refused(dest, source, damage):
    data = source.zip
    if damage == "not a zip":
        data = b"this is not a zip file"
    elif damage == "truncated":
        data = data[: len(data) - 40]
    else:
        flipped = bytearray(data)
        flipped[data.index(source.parts["model.joblib"][:64]) + 20] ^= 0xFF
        data = bytes(flipped)
    with pytest.raises(ModelImportError):
        do_import(dest, data)
    assert_nothing_left(dest)


def test_an_empty_stream_is_refused(dest):
    with pytest.raises(ModelImportError):
        do_import(dest, b"")


def test_model_import_error_is_a_value_error():
    assert issubclass(ModelImportError, ValueError)


# --- hostile record.json ----------------------------------------------------------------------


def record_with(source, **changes):
    record = json.loads(source.parts["record.json"])
    record.update(changes)
    return json.dumps(record).encode()


def without(source, key):
    record = json.loads(source.parts["record.json"])
    del record[key]
    return json.dumps(record).encode()


@pytest.mark.parametrize(
    "changes",
    [
        {"name": 5},
        {"name": "x" * 10_000},
        {"name": "x" * 201},
        {"name": "\ud800"},
        {"task": "regression"},
        {"target": "other"},
        {"task": 1},
        {"best_model": 3},
        {"stop_reason": "bogus"},
        {"stop_reason": None},
        {"config": []},
        {"config": {"target": "判定", "unknown_option": 1}},
        {"config": {"target": "判定", "nfolds": "many"}},
        {"leaderboard": {"model": "x"}},
        {"leaderboard": ["x"]},
        {"trials": "none"},
        {"trials": [[]]},
        {"metrics": []},
        {"metrics": {"logloss": "bad"}},
        {"metrics": {"logloss": True}},
        {"importance": {"x": [1]}},
        {"importance": ["x"]},
        {"surprise": 1},
    ],
)
def test_a_hostile_record_is_refused_and_nothing_is_left(dest, source, changes):
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, record=record_with(source, **changes)))
    assert_nothing_left(dest)


@pytest.mark.parametrize("key", ["name", "config", "leaderboard", "importance"])
def test_a_record_missing_a_field_is_refused(dest, source, key):
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, record=without(source, key)))
    assert_nothing_left(dest)


@pytest.mark.parametrize(
    "text",
    [b"", b"[]", b"null", b"not json", b'{"name": NaN}', b"[" * 200_000, b"\xff\xfe"],
)
def test_a_record_that_is_not_strict_json_is_refused(dest, source, text):
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, record=text))
    assert_nothing_left(dest)


def test_a_non_finite_number_in_the_record_is_refused(dest, source):
    text = (
        source.parts["record.json"].decode().replace('"metrics": {', '"metrics": {"bad": NaN, ', 1)
    )
    assert "NaN" in text
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, record=text.encode()))
    assert_nothing_left(dest)


@pytest.mark.parametrize(
    "diagnostics",
    [
        [],
        "x",
        None,
        {"version": 2, "task": "classification"},
        {"version": True, "task": "classification"},
        {"version": 1.0, "task": "classification"},
        {"task": "classification"},
        {"version": 1, "task": "regression"},
        {"version": 1},
        {"version": 1, "task": "classification", "labels": ["\ud800"]},
        {"version": 1, "task": "classification", "pad": "a" * models.MAX_DIAGNOSTICS_BYTES},
    ],
    ids=[
        "list",
        "text",
        "null",
        "version-2",
        "version-true",
        "version-float",
        "no-version",
        "other-task",
        "no-task",
        "surrogate",
        "too-large",
    ],
)
def test_import_rejects_bad_diagnostics(dest, source, diagnostics):
    with pytest.raises(ModelImportError, match="diagnostics"):
        do_import(dest, rebuilt(source.parts, record=record_with(source, diagnostics=diagnostics)))
    assert_nothing_left(dest)


def test_a_failing_insert_removes_the_objects(dest, source, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("database is gone")

    monkeypatch.setattr(models, "insert_model", fail)
    with pytest.raises(RuntimeError, match="database is gone"):
        do_import(dest, source.zip)
    assert_nothing_left(dest)


def test_a_failing_cleanup_does_not_mask_the_original_error(dest, source, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("database is gone")

    def fail_cleanup(prefix):
        raise OSError("storage down")

    monkeypatch.setattr(models, "insert_model", fail)
    monkeypatch.setattr(dest.storage, "delete_prefix", fail_cleanup)
    with pytest.raises(RuntimeError, match="database is gone"):
        do_import(dest, source.zip)


def test_a_base_exception_during_the_import_cleans_up_too(dest, source, monkeypatch):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(transfer, "verify_artifact", interrupt)
    with pytest.raises(KeyboardInterrupt):
        do_import(dest, source.zip)
    assert_nothing_left(dest)


def test_the_secret_never_appears_in_an_error(dest, source):
    with pytest.raises(UntrustedArtifactError) as info:
        do_import(dest, source.zip, secret=FOREIGN_SECRET)
    assert FOREIGN_SECRET.decode() not in str(info.value)
    assert dest.secret.hex() not in str(info.value)


# --- export -----------------------------------------------------------------------------------


def test_the_export_is_a_zip_of_manifest_model_and_record(source):
    with zipfile.ZipFile(io.BytesIO(source.zip)) as zf:
        kinds = {i.filename: i.compress_type for i in zf.infolist()}
    assert kinds == {
        "manifest.json": zipfile.ZIP_DEFLATED,
        "model.joblib": zipfile.ZIP_STORED,
        "record.json": zipfile.ZIP_DEFLATED,
    }
    env, record = source.env, source.record
    assert source.parts["manifest.json"] == env.storage.get(record.storage_prefix + "manifest.json")
    assert source.parts["model.joblib"] == env.storage.get(record.storage_prefix + MODEL_FILE)
    body = json.loads(source.parts["record.json"])
    assert set(body) == {"name", *COPIED, "metrics", "importance", "trusted", "diagnostics"}
    assert body["trusted"] is True
    assert body["name"] == "日本語モデル" and body["leaderboard"] == record.leaderboard
    assert "日本語モデル".encode() in source.parts["record.json"]  # not \u-escaped


def fake_record(env, record, prefix, size):
    env.storage.put(prefix + "manifest.json", b"{}")
    env.storage.put(prefix + MODEL_FILE, os.urandom(size))
    return dataclasses.replace(record, storage_prefix=prefix)


def test_the_export_is_yielded_in_one_mebibyte_chunks(source, tmp_path):
    record = fake_record(source.env, source.record, "projects/x/models/big/", 2 * MIB + 5000)
    chunks = list(export_model(source.env.storage, record, tmp_dir=tmp_path))
    assert len(chunks) == 3 and all(len(c) == MIB for c in chunks[:2]) and 0 < len(chunks[2]) <= MIB
    assert len(parts(b"".join(chunks))["model.joblib"]) == 2 * MIB + 5000
    assert list(tmp_path.iterdir()) == []


def test_the_temp_file_exists_only_while_the_export_is_read(source, tmp_path):
    record = fake_record(source.env, source.record, "projects/x/models/temp/", 2 * MIB)
    chunks = export_model(source.env.storage, record, tmp_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []  # nothing is made before the first read
    next(chunks)
    assert len(list(tmp_path.iterdir())) == 1
    chunks.close()  # the consumer gave up
    assert list(tmp_path.iterdir()) == []


def test_a_consumer_that_fails_mid_read_leaves_no_temp_file(source, tmp_path):
    record = fake_record(source.env, source.record, "projects/x/models/fail/", 2 * MIB)
    with pytest.raises(RuntimeError):
        for _ in export_model(source.env.storage, record, tmp_dir=tmp_path):
            raise RuntimeError("client went away")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("missing", ["manifest.json", MODEL_FILE])
def test_an_export_of_a_model_with_missing_objects_fails_readably(source, tmp_path, missing):
    prefix = "projects/x/models/partial/"
    record = fake_record(source.env, source.record, prefix, 100)
    source.env.storage.delete(prefix + missing)
    with pytest.raises(models.ModelNotFound, match=str(record.id)):
        b"".join(export_model(source.env.storage, record, tmp_dir=tmp_path))
    assert list(tmp_path.iterdir()) == []


def test_the_export_does_not_need_the_secret_or_unpickle(source, tmp_path, unpickles):
    b"".join(export_model(source.env.storage, source.record, tmp_dir=tmp_path))
    assert unpickles == []


def test_japanese_column_names_survive_the_round_trip(dest, source):
    rec = do_import(dest, source.zip)
    assert models.load_trained(dest.storage, rec, dest.secret).columns == source.model.columns
    assert "幅" in source.model.columns


# --- zip64 directories ------------------------------------------------------------------------


def zip64_directory_zip(entries: int) -> bytes:
    """A classic EOCD claiming 3 entries over a zip64 record that really holds ``entries``."""
    entry = struct.pack(
        "<4s4B4HL2L5H2L", b"PK\x01\x02", 20, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    )
    directory = entry * entries
    zip64 = struct.pack(
        "<4sQ2H2L2Q2Q", b"PK\x06\x06", 44, 45, 45, 0, 0, entries, entries, len(directory), 0
    )
    locator = struct.pack("<4sLQL", b"PK\x06\x07", 0, len(directory), 1)
    eocd = struct.pack("<4s4H2LH", b"PK\x05\x06", 0, 0, 3, 3, 100, 0, 0)
    return directory + zip64 + locator + eocd


def test_a_normal_export_has_no_zip64_locator(source):
    at = source.zip.rfind(b"PK\x05\x06")
    assert source.zip[at - 20 : at - 16] != b"PK\x06\x07"


def test_a_zip64_directory_is_refused_before_zipfile_parses_it(dest, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("zipfile was asked to parse the archive")

    monkeypatch.setattr(zipfile, "ZipFile", forbidden)
    with pytest.raises(ModelImportError, match="zip64"):
        do_import(dest, zip64_directory_zip(50))
    assert_nothing_left(dest)


# --- the trusted flag travels with the record -------------------------------------------------


def set_trusted(env, record, flag):
    env.conn.execute("UPDATE models SET trusted = ? WHERE id = ?", (int(flag), record.id))
    return models.get_model(env.conn, record.id)


def test_the_record_carries_trusted_as_a_bool(tmp_path):
    env = make_env(tmp_path / "t")
    record = add_model(env, classifier())
    flags = []
    for flag in (False, True):
        data = exported(env, set_trusted(env, record, flag))
        flags.append(json.loads(parts(data)["record.json"])["trusted"])
    assert flags == [False, True]


def test_an_untrusted_model_stays_untrusted_through_an_export_and_import(tmp_path, dest, source):
    first = do_import(dest, source.zip, secret=FOREIGN_SECRET, trust_foreign=True)
    assert first.trusted == 0
    again = do_import(dest, exported(dest, first), secret=FOREIGN_SECRET)  # signed locally now
    assert again.trusted == 0
    verify_artifact(dest.storage, again.storage_prefix, FOREIGN_SECRET)


def test_a_trusted_model_stays_trusted(dest, source):
    assert do_import(dest, source.zip).trusted == 1


def test_a_record_saying_untrusted_wins_over_a_valid_signature(dest, source):
    data = rebuilt(source.parts, record=record_with(source, trusted=False))
    rec = do_import(dest, data)
    assert rec.trusted == 0
    assert (
        read_manifest(dest.storage, rec.storage_prefix).hmac
        == json.loads(source.parts["manifest.json"])["hmac"]
    )


def test_a_record_claiming_trusted_does_not_override_the_signature(dest, source):
    rec = do_import(dest, source.zip, secret=FOREIGN_SECRET, trust_foreign=True)
    assert json.loads(source.parts["record.json"])["trusted"] is True
    assert rec.trusted == 0
    with pytest.raises(UntrustedArtifactError):
        do_import(dest, source.zip, secret=FOREIGN_SECRET)


@pytest.mark.parametrize("value", [1, 0, "true", None, [True]])
def test_trusted_must_be_a_bool(dest, source, value):
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, record=record_with(source, trusted=value)))
    assert_nothing_left(dest)


def test_a_record_without_trusted_is_refused(dest, source):
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, record=without(source, "trusted")))
    assert_nothing_left(dest)


# --- the minor fixes --------------------------------------------------------------------------


def test_names_that_are_not_utf8_are_refused(dest, source):
    central = bytearray(source.zip)
    at = central.find(b"PK\x01\x02")
    struct.pack_into("<H", central, at + 8, struct.unpack_from("<H", central, at + 8)[0] | 0x800)
    central[at + 46] = 0xFF
    with pytest.raises(ModelImportError):
        do_import(dest, bytes(central))
    local = bytearray(source.zip)  # only the local header is bad: found when the member is opened
    struct.pack_into("<H", local, 6, struct.unpack_from("<H", local, 6)[0] | 0x800)
    local[30] = 0xFF
    with pytest.raises(ModelImportError):
        do_import(dest, bytes(local))
    assert_nothing_left(dest)


def test_a_disk_error_while_copying_a_member_is_not_reported_as_damage(source):
    class Full:
        def write(self, chunk):
            raise OSError(errno.ENOSPC, "No space left on device")

    with zipfile.ZipFile(io.BytesIO(source.zip)) as zf:
        with pytest.raises(OSError) as info:
            transfer._copy_member(zf, zf.getinfo("model.joblib"), Full(), 512 * MIB)
    assert not isinstance(info.value, ModelImportError)


def test_a_storage_error_surfaces_as_itself_and_cleans_up(dest, source, monkeypatch):
    def full(key, data):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(dest.storage, "put", full)
    with pytest.raises(OSError, match="No space"):
        do_import(dest, source.zip)
    assert_nothing_left(dest)


def test_an_interrupt_after_the_insert_leaves_no_row(dest, source, monkeypatch):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(models, "get_model", interrupt)  # runs right after the INSERT
    with pytest.raises(KeyboardInterrupt):
        do_import(dest, source.zip)
    assert_nothing_left(dest)


def test_a_failing_row_cleanup_does_not_mask_the_original_error(dest, source, monkeypatch):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    class Broken:
        def __init__(self, real):
            self.real = real

        def execute(self, sql, *args):
            if sql.startswith("DELETE"):
                raise sqlite3.OperationalError("locked")
            return self.real.execute(sql, *args)

    monkeypatch.setattr(models, "get_model", interrupt)
    with pytest.raises(KeyboardInterrupt):
        import_model(
            dest.storage,
            Broken(dest.conn),
            dest.admin,
            dest.project.id,
            io.BytesIO(source.zip),
            dest.secret,
            tmp_dir=dest.tmp,
        )


def test_a_config_for_another_target_is_refused(dest, source):
    config = {**json.loads(source.parts["record.json"])["config"], "target": "other"}
    with pytest.raises(ModelImportError):
        do_import(dest, rebuilt(source.parts, record=record_with(source, config=config)))
    assert_nothing_left(dest)


def test_imported_names_never_exceed_the_cap_and_round_trip(tmp_path, dest):
    env = make_env(tmp_path / "long")
    record = add_model(env, classifier(), name="あ" * 200)
    first = do_import(dest, exported(env, record), secret=env.secret)
    assert len(first.name) == 200 and first.name.endswith("(imported)")
    second = do_import(dest, exported(dest, first), secret=env.secret)
    assert len(second.name) == 200 and second.name.endswith("(imported)")


def test_an_already_imported_name_is_imported_again(dest, source):
    first = do_import(dest, source.zip)
    second = do_import(dest, exported(dest, first))
    assert second.name == "日本語モデル (imported) (imported)"
