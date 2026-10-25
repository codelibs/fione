import io
import json
import signal
import sqlite3
import time
from types import SimpleNamespace

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import xgboost as xgb
from catboost import CatBoostClassifier
from predict_models import classifier, regressor, training_frame
from sklearn.ensemble import ExtraTreesClassifier

from fione import db
from fione.auth import service as auth
from fione.auth.roles import ProjectAccess, Role
from fione.config import Settings, load_secret
from fione.engine import explain
from fione.engine.artifact import save_model
from fione.engine.explain import Contributions, PartialDependence
from fione.engine.families import CatBoost, ExtraTrees, LightGBM, XGBoost
from fione.jobs import automl_handler, explain_handler, store, worker
from fione.jobs.runner import TRAINING_KINDS
from fione.jobs.store import JobStatus
from fione.models import explanations
from fione.models import service as models
from fione.models.service import ModelNotFound
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.ingest import ingest_csv
from fione.projects.service import DatasetNotFound, DatasetType
from fione.storage import open_storage

NO_TRAINING_DATA = (
    "the training data is no longer available; choose a dataset that has the model's columns"
)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.delenv("FIONE_JOB_HANDLER_MODULES", raising=False)
    return Settings(data_dir=tmp_path / "data")


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "fione.db")
    db.migrate(c)
    yield c
    c.close()


@pytest.fixture
def storage(settings):
    return open_storage(settings)


@pytest.fixture
def owner(conn):
    return auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR)


@pytest.fixture
def project(conn, owner):
    return projects.create_project(conn, owner, "demo")


def add_dataset(conn, storage, project, df, name="train", type=DatasetType.TRAIN):
    data = df.to_csv(index=False).encode()
    return ingest_csv(storage, conn, project.id, name, type, io.BytesIO(data))


def add_model(conn, storage, settings, project, model, dataset_id, prefix="abc123"):
    prefix = f"projects/{project.id}/models/{prefix}/"
    save_model(model, storage, prefix, load_secret(settings), image_tag="test")
    return models.add_model(
        conn,
        project_id=project.id,
        dataset_id=dataset_id,
        job_id=None,
        name="m",
        model=model,
        storage_prefix=prefix,
    )


@pytest.fixture
def dataset(conn, storage, project):
    return add_dataset(conn, storage, project, training_frame().drop(columns=["value"]))


@pytest.fixture
def record(conn, storage, settings, project, dataset):
    return add_model(conn, storage, settings, project, classifier(), dataset.id)


@pytest.fixture
def run_job(conn, settings):
    """Run a queued job through the worker's own ``_run`` in this process."""
    before = signal.getsignal(signal.SIGTERM)

    def run(job, run_settings=None):
        assert store.claim_job(conn, job.id, "token")
        worker._run(conn, store.get_job(conn, job.id), run_settings or settings)
        return store.get_job(conn, job.id)

    yield run
    signal.signal(signal.SIGTERM, before)


def submit(conn, owner, project, record, dataset_id=None):
    return explanations.submit_explain(conn, owner, project.id, record.id, dataset_id)


def explain_jobs(conn):
    return conn.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'explain'").fetchone()[0]


def notices(conn, job_id):
    return [e for _, e in store.events_since(conn, job_id) if e.type == "notice"]


# --- the job ------------------------------------------------------------------------


def test_explain_stores_importance_and_top_pd(conn, run_job, owner, project, record, dataset):
    job = submit(conn, owner, project, record)
    assert job.payload == {"model_id": record.id, "dataset_id": None}
    done = run_job(job)
    assert done.status is JobStatus.DONE, done.message
    assert set(done.result) == {"model_id", "dataset_id", "n_rows", "elapsed"}
    assert (done.result["model_id"], done.result["dataset_id"]) == (record.id, dataset.id)

    saved = explanations.get_explanation(conn, record.id)
    assert (saved.model_id, saved.job_id, saved.dataset_id) == (record.id, job.id, dataset.id)
    payload = saved.payload
    assert set(payload) == {
        "version",
        "n_rows",
        "outputs",
        "importance",
        "partial_dependence",
        "elapsed",
    }
    assert payload["version"] == 1 and payload["n_rows"] == 300
    assert payload["outputs"] == list(classifier().classes_)
    importance = payload["importance"]
    assert [row["column"] for row in importance] != [] and {r["column"] for r in importance} == {
        "x",
        "幅",
        "color",
    }
    shares = [row["share"] for row in importance]
    assert sum(shares) == pytest.approx(1.0, abs=1e-5)
    assert shares == sorted(shares, reverse=True)
    assert [row["mean_abs"] for row in importance] == sorted(
        [row["mean_abs"] for row in importance], reverse=True
    )

    curves = payload["partial_dependence"]
    assert [c["column"] for c in curves] == [row["column"] for row in importance]  # min(10, 3)
    for curve in curves:
        assert set(curve) == {
            "column",
            "kind",
            "grid",
            "outputs",
            "average",
            "ice_output",
            "ice",
            "n_rows",
        }
        assert curve["outputs"] == payload["outputs"] and curve["n_rows"] == 300
        assert len(curve["average"]) == len(curve["grid"])
        assert all(len(point) == 3 for point in curve["average"])
        assert len(curve["ice"]) == explain.ICE_ROWS
        assert curve["ice_output"] in range(3)
    assert {c["column"]: c["kind"] for c in curves}["color"] == "category"
    # strict JSON within the cap
    text = json.dumps(payload, allow_nan=False, ensure_ascii=False)
    assert len(text.encode()) <= explanations.MAX_EXPLANATION_BYTES

    types = [e.type for _, e in store.events_since(conn, job.id)]
    assert types[0] == "started" and types[-1] == "finished"
    done_counts = [e.data["columns_done"] for e in notices(conn, job.id)]
    assert done_counts == [1, 2, 3]


def test_pd_keeps_only_the_top_columns_in_importance_order(
    conn, run_job, owner, project, record, monkeypatch
):
    monkeypatch.setattr(explain_handler, "PD_COLUMNS", 2)
    done = run_job(submit(conn, owner, project, record))
    assert done.status is JobStatus.DONE, done.message
    payload = explanations.get_explanation(conn, record.id).payload
    order = [row["column"] for row in payload["importance"]]
    assert [c["column"] for c in payload["partial_dependence"]] == order[:2]


def test_a_regression_model_is_explained_in_target_units(
    conn, run_job, owner, project, storage, settings
):
    data = add_dataset(conn, storage, project, training_frame().drop(columns=["判定"]), "reg")
    record = add_model(conn, storage, settings, project, regressor(), data.id, "reg")
    done = run_job(submit(conn, owner, project, record))
    assert done.status is JobStatus.DONE, done.message
    payload = explanations.get_explanation(conn, record.id).payload
    assert payload["outputs"] == ["value"]
    assert all(len(point) == 1 for c in payload["partial_dependence"] for point in c["average"])


def test_an_explicit_dataset_without_the_target_is_explained(
    conn, run_job, owner, project, record, storage
):
    other = add_dataset(conn, storage, project, training_frame(50, 3).drop(columns=["判定"]), "o")
    done = run_job(submit(conn, owner, project, record, other.id))
    assert done.status is JobStatus.DONE, done.message
    saved = explanations.get_explanation(conn, record.id)
    assert saved.dataset_id == other.id and saved.payload["n_rows"] == 50


def test_deleted_training_dataset_fails_clearly(
    conn, run_job, owner, project, record, dataset, storage
):
    job = submit(conn, owner, project, record)
    projects.delete_dataset(conn, storage, dataset.id)
    done = run_job(job)
    assert done.status is JobStatus.FAILED and done.message == NO_TRAINING_DATA
    assert explanations.get_explanation(conn, record.id) is None


def test_training_data_missing_from_storage_fails_clearly(
    conn, run_job, owner, project, record, dataset, storage
):
    job = submit(conn, owner, project, record)
    storage.delete(dataset.key)
    done = run_job(job)
    assert done.status is JobStatus.FAILED and done.message == NO_TRAINING_DATA


def test_other_dataset_without_the_columns_is_refused(
    conn, run_job, owner, project, record, storage
):
    bad = add_dataset(conn, storage, project, training_frame().drop(columns=["color"]), "bad")
    with pytest.raises(ValueError, match=r"the dataset lacks the model's columns: \['color'\]"):
        submit(conn, owner, project, record, bad.id)
    assert explain_jobs(conn) == 0
    payload = {"model_id": record.id, "dataset_id": bad.id}
    done = run_job(store.enqueue(conn, "explain", project.id, owner.id, payload))
    assert done.status is JobStatus.FAILED
    assert done.message == "the dataset lacks the model's columns: ['color']"


def test_text_in_a_numeric_column_fails_plainly(conn, run_job, owner, project, record, storage):
    frame = training_frame().astype({"x": object}).assign(x="abc")
    bad = add_dataset(conn, storage, project, frame, "bad")
    done = run_job(submit(conn, owner, project, record, bad.id))
    assert done.status is JobStatus.FAILED
    assert "'x'" in done.message and "'abc'" in done.message and "Error" not in done.message


def test_dataset_of_another_project_is_refused(
    conn, run_job, owner, project, record, storage, settings
):
    other = projects.create_project(conn, owner, "other")
    foreign = add_dataset(conn, storage, other, training_frame())
    with pytest.raises(DatasetNotFound):
        submit(conn, owner, project, record, foreign.id)
    with pytest.raises(DatasetNotFound):
        submit(conn, owner, project, record, 9999)
    assert explain_jobs(conn) == 0
    payload = {"model_id": record.id, "dataset_id": foreign.id}
    done = run_job(store.enqueue(conn, "explain", project.id, owner.id, payload))
    assert done.status is JobStatus.FAILED and done.message == "the dataset no longer exists"

    foreign_model = add_model(conn, storage, settings, other, classifier(), foreign.id, "f")
    with pytest.raises(ModelNotFound):
        submit(conn, owner, project, foreign_model)
    payload = {"model_id": foreign_model.id, "dataset_id": None}
    done = run_job(store.enqueue(conn, "explain", project.id, owner.id, payload))
    assert done.status is JobStatus.FAILED and done.message == "the model no longer exists"


def test_an_imported_model_needs_an_explicit_dataset(
    conn, run_job, owner, project, storage, settings, dataset
):
    imported = add_model(conn, storage, settings, project, classifier(), None, "imp")
    with pytest.raises(ValueError, match="training data is no longer available"):
        submit(conn, owner, project, imported)
    assert explain_jobs(conn) == 0
    done = run_job(submit(conn, owner, project, imported, dataset.id))
    assert done.status is JobStatus.DONE, done.message


def test_an_untrusted_import_is_explained_by_the_job(
    conn, run_job, owner, project, storage, settings, dataset
):
    imported = add_model(conn, storage, settings, project, classifier(), None, "imp")
    conn.execute("UPDATE models SET trusted = 0 WHERE id = ?", (imported.id,))
    done = run_job(submit(conn, owner, project, imported, dataset.id))
    assert done.status is JobStatus.DONE, done.message


def test_deleted_model_files_are_not_called_tampering(
    conn, run_job, owner, project, record, storage
):
    job = submit(conn, owner, project, record)
    storage.delete_prefix(record.storage_prefix)  # delete_model removes them before the row
    done = run_job(job)
    assert done.status is JobStatus.FAILED and done.message == "the model no longer exists"


def test_a_tampered_model_fails_verification(conn, run_job, owner, project, record, storage):
    key = next(k for k in storage.list(record.storage_prefix) if k.endswith(".joblib"))
    storage.put(key, b"not a model")
    done = run_job(submit(conn, owner, project, record))
    assert done.status is JobStatus.FAILED
    assert done.message == "the model file failed verification"


def test_rerun_replaces_the_explanation(conn, run_job, owner, project, record):
    first = run_job(submit(conn, owner, project, record))
    second = run_job(submit(conn, owner, project, record))
    assert first.status is second.status is JobStatus.DONE
    rows = conn.execute("SELECT job_id FROM model_explanations").fetchall()
    assert [r["job_id"] for r in rows] == [second.id]
    assert explanations.latest_explain_job(conn, record.id).id == second.id


def test_cancel_keeps_the_previous_explanation(conn, run_job, owner, project, record, monkeypatch):
    first = run_job(submit(conn, owner, project, record))
    before = explanations.get_explanation(conn, record.id)
    job = submit(conn, owner, project, record)
    real = explain.partial_dependence

    def cancel_after_first(*args, **kwargs):
        result = real(*args, **kwargs)
        store.request_cancel(conn, job.id)
        time.sleep(worker.STOP_CHECK_SECS + 0.2)  # the stop flag is cached for 0.5 s
        return result

    monkeypatch.setattr(explain, "partial_dependence", cancel_after_first)
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    assert len(notices(conn, job.id)) == 1  # stopped before the second column
    assert explanations.get_explanation(conn, record.id) == before
    assert before.job_id == first.id


def test_a_cancel_after_the_save_never_clobbers_a_newer_explanation(
    conn, run_job, owner, project, record, monkeypatch
):
    run_job(submit(conn, owner, project, record))
    a = submit(conn, owner, project, record)
    b = store.enqueue(conn, "explain", project.id, owner.id, {"model_id": record.id})
    real = explanations.save_explanation

    def save_then_newer_then_cancel(conn_, model_id, job_id, dataset_id, payload):
        real(conn_, model_id, job_id, dataset_id, payload)
        if job_id == a.id:  # B stores a newer row, then A is cancelled
            real(conn_, model_id, b.id, dataset_id, {**payload, "elapsed": 0.0})
            store.request_cancel(conn, a.id)

    monkeypatch.setattr(explanations, "save_explanation", save_then_newer_then_cancel)
    assert run_job(a).status is JobStatus.CANCELLED
    assert explanations.get_explanation(conn, record.id).job_id == b.id


def test_a_cancel_just_before_the_save_stores_nothing(
    conn, run_job, owner, project, record, monkeypatch
):
    job = submit(conn, owner, project, record)
    real = explain_handler.build_explanation

    def build_then_cancel(*args, **kwargs):
        payload = real(*args, **kwargs)
        store.request_cancel(conn, job.id)  # seen by the forced check, no wait needed
        return payload

    monkeypatch.setattr(explain_handler, "build_explanation", build_then_cancel)
    assert run_job(job).status is JobStatus.CANCELLED
    assert explanations.get_explanation(conn, record.id) is None
    assert not conn.in_transaction


def test_a_model_deleted_while_explaining_fails_plainly(
    conn, run_job, owner, project, record, storage, monkeypatch
):
    job = submit(conn, owner, project, record)
    real = explain_handler.build_explanation

    def build_then_delete(*args, **kwargs):
        payload = real(*args, **kwargs)
        conn.execute("DELETE FROM models WHERE id = ?", (record.id,))
        return payload

    monkeypatch.setattr(explain_handler, "build_explanation", build_then_delete)
    done = run_job(job)
    assert done.status is JobStatus.FAILED and done.message == "the model no longer exists"


def test_deleting_the_model_deletes_its_explanation(conn, run_job, owner, project, record, storage):
    assert run_job(submit(conn, owner, project, record)).status is JobStatus.DONE
    models.delete_model(conn, storage, record.id)
    assert conn.execute("SELECT COUNT(*) FROM model_explanations").fetchone()[0] == 0


def test_deleting_the_dataset_keeps_the_explanation(
    conn, run_job, owner, project, record, dataset, storage
):
    assert run_job(submit(conn, owner, project, record)).status is JobStatus.DONE
    projects.delete_dataset(conn, storage, dataset.id)
    saved = explanations.get_explanation(conn, record.id)
    assert saved is not None and saved.dataset_id is None


def test_a_column_without_values_is_skipped(conn, run_job, owner, project, record, storage):
    frame = training_frame().drop(columns=["value"]).assign(color=None)
    gaps = add_dataset(conn, storage, project, frame, "gaps")
    done = run_job(submit(conn, owner, project, record, gaps.id))
    assert done.status is JobStatus.DONE, done.message
    curves = explanations.get_explanation(conn, record.id).payload["partial_dependence"]
    assert "color" not in [c["column"] for c in curves] and len(curves) == 2


def test_the_payload_is_trimmed_to_the_cap(conn, run_job, owner, project, record, monkeypatch):
    monkeypatch.setattr(explanations, "MAX_EXPLANATION_BYTES", 6_000)
    done = run_job(submit(conn, owner, project, record))
    assert done.status is JobStatus.DONE, done.message
    row = conn.execute("SELECT payload_json FROM model_explanations").fetchone()
    assert len(row["payload_json"].encode()) <= 6_000
    payload = json.loads(row["payload_json"])
    assert len(payload["importance"]) == 3  # the ICE curves went, not the importance
    assert payload["partial_dependence"] and all(
        c["ice"] == [] for c in payload["partial_dependence"]
    )


def test_a_payload_that_cannot_fit_fails_plainly(
    conn, run_job, owner, project, record, monkeypatch
):
    monkeypatch.setattr(explanations, "MAX_EXPLANATION_BYTES", 10)
    done = run_job(submit(conn, owner, project, record))
    assert done.status is JobStatus.FAILED
    assert done.message.startswith("the explanation is too large to store: ")
    assert explanations.get_explanation(conn, record.id) is None


def test_explain_is_a_registered_short_job():
    assert "explain" not in TRAINING_KINDS
    from fione.jobs.handlers import HANDLERS

    assert "explain" in HANDLERS


def test_threads_are_capped_never_raised_and_predictions_unchanged():
    X = training_frame(60, 5)[["x", "幅"]]
    y = (X["x"] > 0).astype(int)
    catboost = CatBoostClassifier(iterations=3, verbose=0, allow_writing_files=False)
    fitted = [
        (LightGBM("classification", 2), lgb.LGBMClassifier(n_estimators=3, n_jobs=8, verbose=-1)),
        (LightGBM("classification", 2), lgb.LGBMClassifier(n_estimators=3, n_jobs=-1, verbose=-1)),
        (XGBoost("classification", 2), xgb.XGBClassifier(n_estimators=3, n_jobs=8)),
        (XGBoost("classification", 2), xgb.XGBClassifier(n_estimators=3, n_jobs=None)),
        (ExtraTrees("classification", 2), ExtraTreesClassifier(n_estimators=3, n_jobs=1)),
        (CatBoost("classification", 2, n_jobs=8), catboost),
        (CatBoost("classification", 2, n_jobs=1), catboost),
    ]
    for _, one in fitted:
        one.fit(X, y)
    expected = [spec.predict(one, X) for spec, one in fitted]
    model = SimpleNamespace(members=[SimpleNamespace(spec=s, models=[m]) for s, m in fitted])
    explain.cap_threads(model, 2)
    threads = [one.get_params()["n_jobs"] for _, one in fitted[:5]]
    threads += [spec.n_jobs for spec, _ in fitted[5:]]
    assert threads == [2, 2, 2, 2, 1, 2, 1]  # one thread stays one
    for (spec, one), before in zip(fitted, expected, strict=True):
        np.testing.assert_array_equal(spec.predict(one, X), before)


def test_catboost_predicts_on_its_spec_threads():
    calls = []

    class Model:
        def predict_proba(self, X, **options):
            calls.append(options)
            return np.full((len(X), 2), 0.5)

        def predict(self, X, **options):
            calls.append(options)
            return np.zeros(len(X))

    X = pd.DataFrame({"a": [1.0, 2.0]})
    CatBoost("classification", 2, n_jobs=3).predict(Model(), X)
    CatBoost("regression", 0, n_jobs=2).predict(Model(), X)
    LightGBM("classification", 2, n_jobs=3).predict(Model(), X)
    assert calls == [{"thread_count": 3}, {"thread_count": 2}, {}]


def test_the_contribution_rows_shrink_for_wide_multiclass(
    conn, run_job, owner, project, record, monkeypatch
):
    cells = len(classifier().classes_) * len(classifier().prep.sources)
    monkeypatch.setattr(explain, "CELLS", cells * 40)
    done = run_job(submit(conn, owner, project, record))
    assert done.status is JobStatus.DONE, done.message
    assert explanations.get_explanation(conn, record.id).payload["n_rows"] == 40


# --- the pieces, on synthetic data ----------------------------------------------------


def test_fit_to_cap_trims_the_importance_tail_then_ice_then_curves(monkeypatch):
    monkeypatch.setattr(explain_handler, "IMPORTANCE_FLOOR", 100)
    curve = {"column": "c", "ice": [[0.5] * 20] * 50, "average": [[0.1]] * 20, "grid": [1] * 20}
    importance = [{"column": f"col{i:05d}", "mean_abs": 0.1, "share": 0.1} for i in range(500)]

    def variant(n_importance, n_ice, n_curves):
        curves = [
            dict(curve, column=f"c{i}", ice=curve["ice"] if i < n_ice else [])
            for i in range(n_curves)
        ]
        return {"importance": importance[:n_importance], "partial_dependence": curves}

    def size(value):
        return len(json.dumps(value, ensure_ascii=False).encode())

    payload = variant(500, 3, 3)
    assert explain_handler._fit_to_cap(payload, size(payload)) == payload
    # each state is the first, in trimming order, to fit within its own size
    for state in [(250, 3, 3), (100, 3, 3), (100, 1, 3), (100, 0, 3), (100, 0, 1), (50, 0, 0)]:
        expected = variant(*state)
        assert explain_handler._fit_to_cap(payload, size(expected)) == expected, state
    assert payload == variant(500, 3, 3)  # unchanged
    with pytest.raises(ValueError, match="too large"):
        explain_handler._fit_to_cap(payload, 10)


def contributions_of(mean_probabilities):
    k = len(mean_probabilities)
    prediction = np.tile(mean_probabilities, (4, 1))
    return Contributions(["a"], list(range(k)), np.zeros((4, k, 1)), prediction.copy(), prediction)


def test_more_than_20_outputs_keep_the_most_probable():
    probabilities = np.linspace(0.01, 0.05, 25)  # the last 20 are the most probable
    assert explain_handler._kept_outputs(contributions_of(probabilities)) == list(range(5, 25))
    assert explain_handler._kept_outputs(contributions_of(np.full(3, 1 / 3))) == [0, 1, 2]


def test_the_ice_output_is_one_of_the_kept_outputs(monkeypatch):
    k, grid = 25, [0, 1]
    average = np.zeros((2, k))
    average[1, 2] = 0.9  # varies most, but is not kept
    average[1, 7] = 0.5  # varies most among the kept
    calls = []

    def fake(model, background, column, *, class_index=None):
        calls.append(class_index)
        ice_output = 2 if class_index is None else class_index
        ice = np.full((3, 2), float(ice_output))
        return PartialDependence(
            column, "numeric", grid, list(range(k)), average, ice, ice_output, 3
        )

    monkeypatch.setattr(explain, "partial_dependence", fake)
    kept = list(range(5, 25))
    entry = explain_handler._curve(None, pd.DataFrame(), "a", kept)
    assert calls == [None, 7]
    assert entry["outputs"] == kept and entry["outputs"][entry["ice_output"]] == 7
    assert entry["ice"] == [[7.0, 7.0]] * 3
    assert len(entry["average"][0]) == 20 and entry["average"][1][2] == 0.5


def test_importance_rows_are_stratified_by_the_target():
    frame = pd.DataFrame({"y": ["a"] * 9_000 + ["b"] * 900 + ["c"] * 100, "x": range(10_000)})
    rows = explain_handler._importance_rows(frame, "y", classify=True, limit=1_000)
    assert len(rows) == 1_000 and list(rows) == sorted(set(rows))
    counts = frame["y"].iloc[rows].value_counts()
    assert abs(counts["a"] - 900) <= 1 and abs(counts["b"] - 90) <= 1 and abs(counts["c"] - 10) <= 1
    assert list(explain_handler._importance_rows(frame, "y", True, 1_000)) == list(rows)
    plain = explain_handler._importance_rows(frame, "y", classify=False, limit=1_000)
    assert len(plain) == 1_000 and frame["x"].iloc[plain].max() > 9_000
    assert list(explain_handler._importance_rows(frame.head(10), "y", True, 1_000)) == list(
        range(10)
    )


def test_read_dataset_spread_is_not_head_biased(conn, storage, project, tmp_path):
    n = 200_000
    table = pa.table({"row": np.arange(n), "target": np.sort(np.random.default_rng(0).random(n))})
    path = tmp_path / "sorted.parquet"
    pq.write_table(table, path, row_group_size=50_000)
    dataset_id = projects.reserve_dataset_id(conn)
    key = f"projects/{project.id}/datasets/{dataset_id}/data.parquet"
    with path.open("rb") as f:
        storage.put(key, f)
    schema = [("row", "int64"), ("target", "double")]
    dataset = projects.add_dataset(
        conn, project.id, "sorted", DatasetType.TRAIN, n, 2, schema, key, dataset_id
    )
    assert pq.ParquetFile(path).metadata.num_row_groups == 4

    sample = ingest.read_dataset_spread(storage, dataset, 1_000)
    assert len(sample) == 1_000 and list(sample.columns) == ["row", "target"]
    assert set(sample["row"] // 50_000) == {0, 1, 2, 3}
    assert sample["row"].is_monotonic_increasing and list(sample.index) == list(range(1_000))
    again = ingest.read_dataset_spread(storage, dataset, 1_000)
    pd.testing.assert_frame_equal(sample, again)
    other = ingest.read_dataset_spread(storage, dataset, 1_000, seed=1)
    assert not sample["row"].equals(other["row"])

    two = ingest.read_dataset_spread(storage, dataset, 1_000, ["row"], max_groups=2)
    assert list(two.columns) == ["row"] and set(two["row"] // 50_000) == {0, 3}
    everything = ingest.read_dataset_spread(storage, dataset, n + 1)
    assert len(everything) == n


def test_read_dataset_spread_per_group_reads_only_the_heads(
    conn, storage, project, tmp_path, monkeypatch
):
    n = 200_000
    table = pa.table({"row": np.arange(n), "target": np.random.default_rng(0).random(n)})
    path = tmp_path / "groups.parquet"
    pq.write_table(table, path, row_group_size=50_000)
    dataset_id = projects.reserve_dataset_id(conn)
    key = f"projects/{project.id}/datasets/{dataset_id}/data.parquet"
    with path.open("rb") as f:
        storage.put(key, f)
    schema = [("row", "int64"), ("target", "double")]
    dataset = projects.add_dataset(
        conn, project.id, "groups", DatasetType.TRAIN, n, 2, schema, key, dataset_id
    )
    whole = ingest.read_dataset_spread(storage, dataset, 300)

    def refuse(*args, **kwargs):
        raise AssertionError("whole row groups were read")

    monkeypatch.setattr(pq.ParquetFile, "read_row_groups", refuse)
    heads = ingest.read_dataset_spread(storage, dataset, 300, per_group=300)
    few = ingest.read_dataset_spread(storage, dataset, 300, ["row"], per_group=50)
    assert len(heads) == 300 and heads.dtypes.equals(whole.dtypes)
    assert set(heads["row"] // 50_000) == {0, 1, 2, 3} and (heads["row"] % 50_000 < 300).all()
    assert heads["row"].is_monotonic_increasing and list(heads.index) == list(range(300))
    assert len(few) == 200 and list(few.columns) == ["row"]  # four heads of 50


# --- submit_explain and the service ----------------------------------------------------


def test_a_viewer_cannot_submit(conn, owner, project, record):
    viewer = auth.create_user(conn, "viewer", "pw-viewer-1", Role.VIEWER)
    projects.share_project(conn, owner, project.id, "viewer", ProjectAccess.VIEWER)
    with pytest.raises(PermissionError):
        submit(conn, viewer, project, record)
    assert explain_jobs(conn) == 0


def test_model_columns_are_the_importance_keys(record):
    assert sorted(explanations.model_columns(record)) == sorted(classifier().columns)


def test_latest_explain_job_is_per_model(conn, owner, project, record, storage, settings, dataset):
    assert explanations.latest_explain_job(conn, record.id) is None
    other = add_model(conn, storage, settings, project, classifier(), dataset.id, "two")
    first = submit(conn, owner, project, record)
    submit(conn, owner, project, other)
    second = store.enqueue(conn, "explain", project.id, owner.id, {"model_id": record.id})
    assert explanations.latest_explain_job(conn, record.id).id == second.id != first.id


def test_a_second_submit_returns_the_active_job(conn, run_job, owner, project, record, storage):
    first = submit(conn, owner, project, record)
    assert submit(conn, owner, project, record).id == first.id  # queued
    assert run_job(first).status is JobStatus.DONE
    again = submit(conn, owner, project, record)
    assert again.id != first.id  # a finished job is not reused
    assert store.claim_job(conn, again.id, "token")
    assert submit(conn, owner, project, record).id == again.id  # running
    other = add_dataset(conn, storage, project, training_frame(50, 3), "other")
    assert submit(conn, owner, project, record, other.id).id != again.id  # another dataset
    assert explain_jobs(conn) == 3


def test_a_stored_payload_is_checked_when_read(conn, record):
    assert explanations.get_explanation(conn, record.id) is None
    explanations.save_explanation(conn, record.id, None, None, {"version": 1, "importance": []})
    assert explanations.get_explanation(conn, record.id).payload["importance"] == []
    for text in ("not json", "[]", '{"version": 2}', '{"version": true}'):
        conn.execute("UPDATE model_explanations SET payload_json = ?", (text,))
        assert explanations.get_explanation(conn, record.id) is None


def test_save_refuses_a_payload_over_the_cap_or_not_strict_json(conn, record, monkeypatch):
    with pytest.raises(ValueError):
        explanations.save_explanation(
            conn, record.id, None, None, {"version": 1, "x": float("nan")}
        )
    monkeypatch.setattr(explanations, "MAX_EXPLANATION_BYTES", 100)
    with pytest.raises(ValueError, match="too large"):
        explanations.save_explanation(conn, record.id, None, None, {"version": 1, "x": "y" * 200})
    assert explanations.get_explanation(conn, record.id) is None


# --- after training ----------------------------------------------------------------------


class FakeAutoML:
    """Returns the cached classifier at once, so these tests train nothing."""

    def __init__(self, config, emit, should_stop):
        pass

    def fit(self, frame):
        return classifier()


@pytest.fixture
def training_job(conn, storage, owner, project, dataset, monkeypatch):
    monkeypatch.setattr(automl_handler, "AutoML", FakeAutoML)
    config = {"target": "判定", "max_runtime_secs": 10, "nfolds": 3}
    return models.submit_training(conn, storage, owner, project.id, dataset.id, config)


def test_automl_enqueues_explain_when_enabled(conn, run_job, training_job, settings):
    enabled = settings.model_copy(update={"explain_after_training": True})
    done = run_job(training_job, enabled)
    assert done.status is JobStatus.DONE, done.message
    queued = store.get_job(conn, done.result["explain_job_id"])
    assert (queued.kind, queued.status, queued.project_id) == (
        "explain",
        JobStatus.QUEUED,
        training_job.project_id,
    )
    assert queued.owner_id == training_job.owner_id
    assert queued.payload == {"model_id": done.result["model_id"], "dataset_id": None}
    assert run_job(queued).status is JobStatus.DONE


def test_automl_enqueues_no_explain_when_disabled(conn, run_job, training_job, settings):
    assert Settings.model_fields["explain_after_training"].default is True  # in production
    assert Settings().explain_after_training is False  # the tests' default
    assert Settings(explain_after_training=True).explain_after_training is True
    done = run_job(training_job)
    assert done.status is JobStatus.DONE, done.message
    assert done.result["explain_job_id"] is None and explain_jobs(conn) == 0


def test_a_failing_enqueue_never_fails_the_training(
    conn, run_job, training_job, settings, monkeypatch, caplog
):
    def fail(conn, kind, *args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(store, "enqueue", fail)
    enabled = settings.model_copy(update={"explain_after_training": True})
    done = run_job(training_job, enabled)
    assert done.status is JobStatus.DONE, done.message
    assert done.result["explain_job_id"] is None and models.get_model(conn, done.result["model_id"])
    assert "could not queue" in caplog.text


def test_cancel_during_save_enqueues_no_explain_job(
    conn, run_job, training_job, settings, monkeypatch
):
    real_save = automl_handler.save_model

    def save_then_cancel(*args, **kwargs):
        manifest = real_save(*args, **kwargs)
        store.request_cancel(conn, training_job.id)
        return manifest

    monkeypatch.setattr(automl_handler, "save_model", save_then_cancel)
    enabled = settings.model_copy(update={"explain_after_training": True})
    assert run_job(training_job, enabled).status is JobStatus.CANCELLED
    assert conn.execute("SELECT COUNT(*) FROM models").fetchone()[0] == 0
    assert explain_jobs(conn) == 0
