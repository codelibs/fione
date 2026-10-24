import dataclasses
import hashlib
import hmac
import json
import tempfile

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

from fione.engine.artifact import (
    Manifest,
    UntrustedArtifactError,
    load_model,
    load_model_unverified_hash_only,
    read_manifest,
    resign_manifest,
    save_model,
    verify_artifact,
    verify_manifest_hmac,
)
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.storage import LocalStorage
from fione.version import __version__

SECRET = bytes(range(32))
OTHER_SECRET = bytes(range(1, 33))
PREFIX = "models/7/"
MODEL_KEY = PREFIX + "model.joblib"
MANIFEST_KEY = PREFIX + "manifest.json"


@pytest.fixture(scope="module")
def iris():
    df = load_iris(as_frame=True).frame
    df["target"] = df["target"].map({0: "setosa", 1: "versicolor", 2: "virginica"})
    train, test = train_test_split(df, test_size=0.3, stratify=df["target"], random_state=0)
    config = TrainConfig(target="target", max_runtime_secs=15, max_models=3, seed=0)
    return AutoML(config).fit(train), test


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "store")


@pytest.fixture
def saved(iris, storage):
    model, test = iris
    manifest = save_model(model, storage, PREFIX, SECRET, image_tag="fione:test")
    return model, test, manifest


@pytest.fixture
def load_spy(monkeypatch):
    def spy(*args, **kwargs):
        pytest.fail("joblib.load was called on an artifact that is not trusted")

    monkeypatch.setattr(joblib, "load", spy)


def _flip_byte(storage, key, offset=-1):
    path = storage.root / key
    data = bytearray(path.read_bytes())
    data[offset] ^= 0x01
    path.write_bytes(bytes(data))


def _edit_manifest(storage, **changes):
    raw = json.loads(storage.get(MANIFEST_KEY))
    raw.update(changes)
    storage.put(MANIFEST_KEY, json.dumps(raw).encode())


def _canonical(raw: dict) -> bytes:
    body = {k: v for k, v in raw.items() if k != "hmac"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


# --- round trip ---------------------------------------------------------------------


def test_round_trip_predictions_are_equal(saved, storage):
    model, test, _ = saved
    loaded = load_model(storage, PREFIX, SECRET)
    pd.testing.assert_series_equal(loaded.predict(test), model.predict(test))
    pd.testing.assert_frame_equal(loaded.predict_proba(test), model.predict_proba(test))
    assert all(member.weight > 0 for member in loaded.members)


def test_manifest_describes_the_model(saved, storage):
    model, _, manifest = saved
    assert manifest.format_version == 1
    assert manifest.fione_version == __version__
    assert manifest.image_tag == "fione:test"
    assert manifest.task == model.task and manifest.target == model.target
    assert manifest.columns == model.columns
    assert manifest.classes == model.classes_ and manifest.classes_dtype == "str"
    assert manifest.created_at.endswith("+00:00")
    assert read_manifest(storage, PREFIX) == manifest
    assert sorted(storage.list(PREFIX)) == [MANIFEST_KEY, MODEL_KEY]


def test_manifest_lists_only_the_model_file_with_its_sha256(saved, storage):
    _, _, manifest = saved
    assert list(manifest.files) == ["model.joblib"]
    assert manifest.files["model.joblib"] == hashlib.sha256(storage.get(MODEL_KEY)).hexdigest()


def test_hmac_is_sha256_over_the_canonical_json_without_the_hmac_field(saved, storage):
    _, _, manifest = saved
    raw = json.loads(storage.get(MANIFEST_KEY))
    assert raw["hmac"] == manifest.hmac
    expected = hmac.new(SECRET, _canonical(raw), hashlib.sha256).hexdigest()
    assert manifest.hmac == expected
    assert verify_manifest_hmac(manifest, SECRET)
    assert not verify_manifest_hmac(manifest, OTHER_SECRET)


def test_the_secret_is_not_stored_anywhere(saved, storage):
    for key in storage.list(PREFIX):
        assert SECRET not in storage.get(key)


def test_a_file_outside_the_manifest_is_ignored(saved, storage):
    model, test, _ = saved
    storage.put(PREFIX + "extra.joblib", b"not part of the artifact")
    loaded = load_model(storage, PREFIX, SECRET)
    pd.testing.assert_series_equal(loaded.predict(test), model.predict(test))
    assert storage.get(PREFIX + "extra.joblib") == b"not part of the artifact"


@pytest.mark.parametrize(
    ("classes", "dtype"),
    [([0, 1, 2], "int"), ([False, True], "bool"), ([0.5, 1.5], "float"), (["a", "b"], "str")],
)
def test_class_labels_keep_their_type(iris, storage, classes, dtype):
    model, _ = iris
    model = dataclasses.replace(model, classes_=list(classes))
    manifest = save_model(model, storage, PREFIX, SECRET, image_tag="t")
    assert manifest.classes_dtype == dtype
    again = read_manifest(storage, PREFIX)
    assert again.classes == classes
    assert [type(c) for c in again.classes] == [type(c) for c in classes]


def test_numpy_class_labels_become_plain_json_values(iris, storage):
    model, _ = iris
    model = dataclasses.replace(model, classes_=list(np.array([3, 5, 8])))
    save_model(model, storage, PREFIX, SECRET, image_tag="t")
    classes = read_manifest(storage, PREFIX).classes
    assert classes == [3, 5, 8] and all(type(c) is int for c in classes)


def test_regression_manifest_has_no_classes(iris, storage):
    model, _ = iris
    model = dataclasses.replace(model, task="regression", classes_=None)
    manifest = save_model(model, storage, PREFIX, SECRET, image_tag="t")
    assert manifest.classes is None and manifest.classes_dtype is None
    assert read_manifest(storage, PREFIX).classes is None


def test_manifest_json_round_trip(saved):
    _, _, manifest = saved
    assert Manifest.from_json(manifest.to_json()) == manifest


# --- save ---------------------------------------------------------------------------


def test_prefix_must_end_with_a_slash(iris, storage):
    model, _ = iris
    with pytest.raises(ValueError, match="end with"):
        save_model(model, storage, "models/7", SECRET, image_tag="t")
    assert storage.list("") == []


def test_manifest_is_written_last(iris, storage):
    model, _ = iris
    calls = []
    put = storage.put

    def recording_put(key, data):
        calls.append(key)
        put(key, data)

    storage.put = recording_put
    save_model(model, storage, PREFIX, SECRET, image_tag="t")
    assert calls == [MODEL_KEY, MANIFEST_KEY]


@pytest.mark.parametrize("failing_call", [1, 2])
def test_a_failed_upload_leaves_nothing_behind(iris, storage, failing_call):
    model, _ = iris
    put = storage.put
    count = 0

    def flaky_put(key, data):
        nonlocal count
        count += 1
        if count == failing_call:
            raise OSError("disk full")
        put(key, data)

    storage.put = flaky_put
    with pytest.raises(OSError, match="disk full"):
        save_model(model, storage, PREFIX, SECRET, image_tag="t")
    assert storage.list(PREFIX) == []


def test_a_failed_save_keeps_other_objects_under_the_prefix(iris, storage):
    model, _ = iris
    storage.put(PREFIX + "keep.txt", b"x")

    def failing_put(key, data):
        raise OSError("boom")

    storage.put, put = failing_put, storage.put
    with pytest.raises(OSError):
        save_model(model, storage, PREFIX, SECRET, image_tag="t")
    storage.put = put
    assert storage.list(PREFIX) == [PREFIX + "keep.txt"]


def test_the_temporary_dump_is_removed(iris, storage, tmp_path, monkeypatch):
    model, _ = iris
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    save_model(model, storage, PREFIX, SECRET, image_tag="t")
    assert list(scratch.iterdir()) == []


# --- load: nothing is unpickled before the artifact is trusted ----------------------------


def test_a_flipped_model_byte_is_rejected_without_unpickling(saved, storage, load_spy):
    _flip_byte(storage, MODEL_KEY)
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


def test_a_flipped_first_model_byte_is_rejected(saved, storage, load_spy):
    _flip_byte(storage, MODEL_KEY, 0)
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


def test_a_truncated_model_is_rejected(saved, storage, load_spy):
    path = storage.root / MODEL_KEY
    path.write_bytes(path.read_bytes()[:-10])
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


def test_a_missing_model_is_rejected(saved, storage, load_spy):
    storage.delete(MODEL_KEY)
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


def test_a_missing_manifest_is_rejected(saved, storage, load_spy):
    storage.delete(MANIFEST_KEY)
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


def test_the_wrong_secret_is_rejected(saved, storage, load_spy):
    with pytest.raises(UntrustedArtifactError) as info:
        load_model(storage, PREFIX, OTHER_SECRET)
    assert SECRET.hex() not in str(info.value) and OTHER_SECRET.hex() not in str(info.value)


@pytest.mark.parametrize(
    "changes",
    [
        {"image_tag": "evil:latest"},
        {"columns": ["a", "b"]},
        {"classes": ["x", "y", "z"]},
        {"classes_dtype": "int"},
        {"task": "regression"},
        {"target": "other"},
        {"fione_version": "9.9.9"},
        {"created_at": "2000-01-01T00:00:00+00:00"},
        {"files": {"model.joblib": "0" * 64}},
        {"hmac": "0" * 64},
    ],
    ids=lambda changes: next(iter(changes)),
)
def test_an_edited_manifest_is_rejected(saved, storage, load_spy, changes):
    _edit_manifest(storage, **changes)
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


def test_a_flipped_manifest_byte_is_rejected(saved, storage, load_spy):
    _flip_byte(storage, MANIFEST_KEY, 40)
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


def test_a_manifest_re_signed_with_another_secret_is_rejected(saved, storage, load_spy):
    raw = json.loads(storage.get(MANIFEST_KEY))
    raw["image_tag"] = "evil:latest"
    raw["hmac"] = hmac.new(OTHER_SECRET, _canonical(raw), hashlib.sha256).hexdigest()
    storage.put(MANIFEST_KEY, json.dumps(raw).encode())
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


def test_a_replaced_model_with_a_matching_hash_still_needs_a_valid_signature(
    saved, storage, load_spy
):
    payload = b"malicious pickle"
    storage.put(MODEL_KEY, payload)
    _edit_manifest(storage, files={"model.joblib": hashlib.sha256(payload).hexdigest()})
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


@pytest.mark.parametrize(
    "content",
    [b"", b"not json", b"[]", b"null", b'{"format_version": 1}', b"\xff\xfe", b'{"a": '],
    ids=["empty", "text", "list", "null", "missing-fields", "bad-utf8", "truncated"],
)
def test_a_corrupt_manifest_is_an_untrusted_artifact_error(saved, storage, load_spy, content):
    storage.put(MANIFEST_KEY, content)
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)
    with pytest.raises(UntrustedArtifactError):
        read_manifest(storage, PREFIX)
    with pytest.raises(UntrustedArtifactError):
        load_model_unverified_hash_only(storage, PREFIX)


@pytest.mark.parametrize(
    "changes",
    [
        {"files": []},
        {"files": {"model.joblib": 5}},
        {"columns": "abc"},
        {"columns": [1, 2]},
        {"classes": {"a": 1}},
        {"classes_dtype": "complex"},
        {"format_version": "1"},
        {"format_version": True},
        {"task": 3},
        {"unexpected": 1},
    ],
    ids=lambda changes: next(iter(changes)) + "-" + repr(next(iter(changes.values())))[:12],
)
def test_a_manifest_with_the_wrong_schema_is_rejected(saved, storage, load_spy, changes):
    _edit_manifest(storage, **changes)
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


def test_an_unsupported_format_version_is_rejected(saved, storage, load_spy):
    _edit_manifest(storage, format_version=2)
    with pytest.raises(UntrustedArtifactError, match="unsupported artifact format"):
        load_model(storage, PREFIX, SECRET)
    with pytest.raises(UntrustedArtifactError, match="unsupported artifact format"):
        load_model_unverified_hash_only(storage, PREFIX)


# --- serving: hash only -------------------------------------------------------------------


def test_hash_only_load_accepts_a_valid_artifact(saved, storage):
    model, test, _ = saved
    loaded = load_model_unverified_hash_only(storage, PREFIX)
    pd.testing.assert_series_equal(loaded.predict(test), model.predict(test))


def test_hash_only_load_rejects_a_tampered_byte(saved, storage, load_spy):
    _flip_byte(storage, MODEL_KEY)
    with pytest.raises(UntrustedArtifactError):
        load_model_unverified_hash_only(storage, PREFIX)


def test_hash_only_load_rejects_a_missing_or_truncated_model(saved, storage, load_spy):
    path = storage.root / MODEL_KEY
    path.write_bytes(path.read_bytes()[:-10])
    with pytest.raises(UntrustedArtifactError):
        load_model_unverified_hash_only(storage, PREFIX)
    storage.delete(MODEL_KEY)
    with pytest.raises(UntrustedArtifactError):
        load_model_unverified_hash_only(storage, PREFIX)


def test_hash_only_load_cannot_tell_who_signed_the_manifest(saved, storage):
    # Integrity, not authenticity: whoever can write both files passes this check.
    model, test, _ = saved
    raw = json.loads(storage.get(MANIFEST_KEY))
    raw["hmac"] = "0" * 64
    storage.put(MANIFEST_KEY, json.dumps(raw).encode())
    loaded = load_model_unverified_hash_only(storage, PREFIX)
    pd.testing.assert_series_equal(loaded.predict(test), model.predict(test))
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)


# --- the secret must be a real key ----------------------------------------------------------


@pytest.mark.parametrize(
    "secret", [b"", b"short", bytes(16), bytes(31), "x" * 32, None, 12345], ids=repr
)
def test_a_weak_or_mistyped_secret_is_rejected_everywhere(iris, saved, storage, load_spy, secret):
    model, _ = iris
    manifest = read_manifest(storage, PREFIX)
    with pytest.raises(ValueError, match="at least 32 bytes"):
        save_model(model, storage, "other/", secret, image_tag="t")
    assert storage.list("other/") == []
    with pytest.raises(ValueError, match="at least 32 bytes"):
        verify_manifest_hmac(manifest, secret)
    with pytest.raises(ValueError, match="at least 32 bytes"):
        load_model(storage, PREFIX, secret)


def test_a_32_byte_secret_is_accepted(iris, storage):
    model, _ = iris
    manifest = save_model(model, storage, PREFIX, bytes(32), image_tag="t")
    assert verify_manifest_hmac(manifest, bytes(32))


# --- hostile manifests never surface a raw exception ----------------------------------------

HOSTILE_MANIFESTS = {
    "non-ascii-hmac": lambda s: _edit_manifest(s, hmac="é" * 64),
    "non-ascii-file-hash": lambda s: _edit_manifest(s, files={"model.joblib": "é" * 64}),
    "lone-surrogate-image-tag": lambda s: _edit_manifest(s, image_tag="\ud800"),
    "lone-surrogate-column": lambda s: _edit_manifest(s, columns=["\udfff"]),
    "lone-surrogate-file-name": lambda s: _edit_manifest(
        s, files={"\ud800": "0" * 64, "model.joblib": "0" * 64}
    ),
    "deep-nesting": lambda s: s.put(MANIFEST_KEY, b"[" * 100_000),
    "empty-file-name": lambda s: _edit_manifest(s, files={"": "0" * 64}),
    "short-hmac": lambda s: _edit_manifest(s, hmac="ab"),
    "upper-case-hmac": lambda s: _edit_manifest(s, hmac="A" * 64),
    "trailing-newline-hash": lambda s: _edit_manifest(s, files={"model.joblib": "0" * 64 + "\n"}),
}


@pytest.mark.parametrize("hostile", HOSTILE_MANIFESTS.values(), ids=HOSTILE_MANIFESTS.keys())
def test_a_hostile_manifest_is_an_untrusted_artifact_error(saved, storage, load_spy, hostile):
    hostile(storage)
    with pytest.raises(UntrustedArtifactError):
        load_model(storage, PREFIX, SECRET)
    with pytest.raises(UntrustedArtifactError):
        load_model_unverified_hash_only(storage, PREFIX)
    with pytest.raises(UntrustedArtifactError):
        read_manifest(storage, PREFIX)


# --- verification order ---------------------------------------------------------------------


class _RecordingStorage:
    def __init__(self, inner):
        self.inner = inner
        self.reads = []

    def get(self, key):
        self.reads.append(key)
        return self.inner.get(key)

    def open_read(self, key):
        self.reads.append(key)
        return self.inner.open_read(key)


def test_the_model_file_is_not_read_before_the_signature_checks_out(saved, storage, load_spy):
    spy = _RecordingStorage(storage)
    with pytest.raises(UntrustedArtifactError):
        load_model(spy, PREFIX, OTHER_SECRET)
    assert spy.reads == [MANIFEST_KEY]


def test_a_good_signature_with_a_wrong_model_hash_is_not_unpickled(saved, storage, load_spy):
    _flip_byte(storage, MODEL_KEY)
    spy = _RecordingStorage(storage)
    with pytest.raises(UntrustedArtifactError):
        load_model(spy, PREFIX, SECRET)
    assert spy.reads == [MANIFEST_KEY, MODEL_KEY]  # the hash check was reached, then it stopped


# --- verify_artifact and resign_manifest: checks that never unpickle ----------------------


def test_verify_artifact_accepts_a_valid_artifact_without_unpickling(saved, storage, load_spy):
    model, test, manifest = saved
    assert verify_artifact(storage, PREFIX, SECRET) == manifest


def test_verify_artifact_needs_the_signature_unless_told_not_to(saved, storage, load_spy):
    with pytest.raises(UntrustedArtifactError):
        verify_artifact(storage, PREFIX, OTHER_SECRET)
    assert verify_artifact(storage, PREFIX, OTHER_SECRET, require_hmac=False).files


def test_verify_artifact_always_checks_the_file_hashes(saved, storage, load_spy):
    _flip_byte(storage, MODEL_KEY)
    for require_hmac in (True, False):
        with pytest.raises(UntrustedArtifactError):
            verify_artifact(storage, PREFIX, SECRET, require_hmac=require_hmac)


def test_verify_artifact_rejects_missing_files_and_manifests(saved, storage, load_spy):
    storage.delete(MODEL_KEY)
    with pytest.raises(UntrustedArtifactError):
        verify_artifact(storage, PREFIX, SECRET, require_hmac=False)
    storage.delete(MANIFEST_KEY)
    with pytest.raises(UntrustedArtifactError):
        verify_artifact(storage, PREFIX, SECRET, require_hmac=False)


def test_resign_manifest_changes_only_the_signature(saved):
    _, _, manifest = saved
    signed = resign_manifest(manifest, OTHER_SECRET)
    assert verify_manifest_hmac(signed, OTHER_SECRET) and not verify_manifest_hmac(signed, SECRET)
    assert dataclasses.replace(signed, hmac=manifest.hmac) == manifest
