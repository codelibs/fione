import datetime
import io
import os
import signal
import sqlite3
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest
from predict_models import classifier, features, regressor

from fione import db
from fione.auth import service as auth
from fione.auth.roles import ProjectAccess, Role
from fione.config import Settings, load_secret
from fione.engine import explain
from fione.engine.artifact import save_model
from fione.jobs import batch_predict_handler, store, worker
from fione.jobs.runner import TRAINING_KINDS, JobRunner
from fione.jobs.store import JobStatus
from fione.models import service as models
from fione.models.service import ModelNotFound
from fione.predict import PredictInputError, batch, batch_predict
from fione.projects import ingest, service
from fione.projects import service as projects
from fione.projects.ingest import ingest_csv, read_dataset
from fione.projects.service import DatasetNotFound, DatasetType, ProjectNotFound
from fione.storage import LocalStorage, open_storage

TERMINAL = {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED}


def wait_for(predicate, timeout=90.0, interval=0.05):
    deadline = time.monotonic() + timeout
    while True:
        value = predicate()
        if value:
            return value
        if time.monotonic() > deadline:
            raise AssertionError("condition not met in time")
        time.sleep(interval)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.delenv("FIONE_JOB_HANDLER_MODULES", raising=False)
    return Settings(data_dir=tmp_path / "data")


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "fione.db"


@pytest.fixture
def conn(db_path):
    c = db.connect(db_path)
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


def add_model(conn, storage, settings, project, model):
    prefix = f"projects/{project.id}/models/abc123/"
    save_model(model, storage, prefix, load_secret(settings), image_tag="test")
    return models.add_model(
        conn,
        project_id=project.id,
        dataset_id=None,
        job_id=None,
        name="m",
        model=model,
        storage_prefix=prefix,
    )


def add_dataset(conn, storage, project, df, name="new data", type=DatasetType.TEST):
    return ingest_csv(
        storage, conn, project.id, name, type, io.BytesIO(df.to_csv(index=False).encode())
    )


@pytest.fixture
def record(conn, storage, settings, project):
    return add_model(conn, storage, settings, project, classifier())


@pytest.fixture
def frame():
    return features(40)


@pytest.fixture
def dataset(conn, storage, project, frame):
    return add_dataset(conn, storage, project, frame)


@pytest.fixture
def runner(settings, db_path):
    made = JobRunner(settings, db_path, poll_secs=0.05)
    made.start()
    yield made
    made.shutdown(kill_running=True)


@pytest.fixture
def run_job(conn, settings):
    """Run a queued job through the worker's own ``_run`` in this process."""
    before = signal.getsignal(signal.SIGTERM)

    def run(job):
        assert store.claim_job(conn, job.id, "token")
        worker._run(conn, store.get_job(conn, job.id), settings)
        return store.get_job(conn, job.id)

    yield run
    signal.signal(signal.SIGTERM, before)


def wait_done(conn, job_id):
    return wait_for(lambda: (j := store.get_job(conn, job_id)).status in TERMINAL and j)


def event_types(conn, job_id):
    return [e.type for _, e in store.events_since(conn, job_id)]


def predict_datasets(conn, project):
    return [d for d in projects.list_datasets(conn, project.id) if d.type is DatasetType.PREDICT]


def dataset_objects(storage, project):
    return storage.list(f"projects/{project.id}/datasets/")


def submit(conn, owner, project, record, dataset, **kw):
    return models.submit_batch_predict(conn, owner, project.id, record.id, dataset.id, **kw)


# --- through the runner and a worker subprocess ---------------------------------


def test_a_prediction_job_runs_end_to_end(
    conn, runner, owner, project, record, dataset, storage, settings
):
    job = submit(conn, owner, project, record, dataset)
    done = wait_done(conn, job.id)
    assert done.status is JobStatus.DONE, done.message

    assert set(done.result) == {"dataset_id", "n_rows", "elapsed"}
    out = projects.get_dataset(conn, done.result["dataset_id"])
    assert (out.name, out.type, out.project_id) == (
        "predict_new data",
        DatasetType.PREDICT,
        project.id,
    )
    assert out.n_rows == done.result["n_rows"] == dataset.n_rows == 40
    assert done.result["elapsed"] > 0

    model = models.load_trained(storage, record, load_secret(settings))
    expected = batch_predict(model, read_dataset(storage, dataset))
    pd.testing.assert_frame_equal(read_dataset(storage, out), expected)
    assert out.schema[0][0] == "predict" and [n for n, _ in out.schema][1:4] == [
        "p_悪",
        "p_普通",
        "p_良",
    ]

    types = event_types(conn, job.id)
    assert types[0] == "started" and types[-1] == "finished"
    assert "notice" in types


def test_included_columns_and_the_name_are_honoured(
    conn, runner, owner, project, record, dataset, storage
):
    job = submit(conn, owner, project, record, dataset, include_columns=["color"], name="results")
    done = wait_done(conn, job.id)
    assert done.status is JobStatus.DONE, done.message
    out = projects.get_dataset(conn, done.result["dataset_id"])
    assert out.name == "results"
    assert [n for n, _ in out.schema] == ["predict", "p_悪", "p_普通", "p_良", "color"]


def test_a_dataset_missing_model_columns_fails_the_job_in_plain_words(
    conn, runner, owner, project, record, storage, frame
):
    bad = add_dataset(conn, storage, project, frame.drop(columns=["x", "color"]), "bad")
    done = wait_done(conn, submit(conn, owner, project, record, bad).id)
    assert done.status is JobStatus.FAILED
    assert done.message == "missing columns: ['x', 'color']"
    assert predict_datasets(conn, project) == []
    assert len(dataset_objects(storage, project)) == 1  # only the input


def test_text_in_a_numeric_column_fails_the_job_in_plain_words(
    conn, runner, owner, project, record, storage, frame
):
    bad = add_dataset(conn, storage, project, frame.astype({"x": object}).assign(x="abc"), "bad")
    done = wait_done(conn, submit(conn, owner, project, record, bad).id)
    assert done.status is JobStatus.FAILED
    assert "'x'" in done.message and "'abc'" in done.message
    assert "Error" not in done.message and predict_datasets(conn, project) == []


def test_a_regression_model_gives_only_a_predict_column(
    conn, runner, owner, project, storage, settings, dataset
):
    record = add_model(conn, storage, settings, project, regressor())
    done = wait_done(conn, submit(conn, owner, project, record, dataset, include_columns=[]).id)
    assert done.status is JobStatus.DONE, done.message
    out = read_dataset(storage, projects.get_dataset(conn, done.result["dataset_id"]))
    assert list(out.columns) == ["predict"] and len(out) == 40


def test_deleting_the_project_removes_the_predictions(
    conn, runner, owner, project, record, dataset, storage
):
    done = wait_done(conn, submit(conn, owner, project, record, dataset).id)
    assert done.status is JobStatus.DONE
    projects.delete_project(conn, storage, owner, project.id)
    assert conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == 0
    assert storage.list("") == []


def test_the_handler_is_registered_without_extra_modules():
    env = {k: v for k, v in os.environ.items() if k != "FIONE_JOB_HANDLER_MODULES"}
    code = (
        "from fione.jobs import worker; worker._import_handler_modules();"
        "from fione.jobs.handlers import HANDLERS; print(sorted(HANDLERS))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    )
    assert "'batch_predict'" in out.stdout


def test_prediction_is_a_short_job():
    assert "batch_predict" not in TRAINING_KINDS


# --- the handler run in this process, so failures can be injected -------------------


@pytest.fixture
def job(conn, owner, project, record, dataset):
    return submit(conn, owner, project, record, dataset)


def test_a_prediction_dataset_can_itself_be_predicted_on(
    conn, run_job, owner, project, record, storage, frame
):
    source = add_dataset(conn, storage, project, frame, "old", DatasetType.PREDICT)
    done = run_job(submit(conn, owner, project, record, source))
    assert done.status is JobStatus.DONE, done.message
    assert projects.get_dataset(conn, done.result["dataset_id"]).name == "predict_old"


def test_progress_is_reported_per_chunk(conn, run_job, job, monkeypatch):
    monkeypatch.setattr(batch_predict_handler, "CHUNK_ROWS", 16)
    done = run_job(job)
    assert done.status is JobStatus.DONE, done.message
    notices = [e for _, e in store.events_since(conn, job.id) if e.type == "notice"]
    assert [e.data["rows_done"] for e in notices] == [16, 32, 40]
    assert all(e.data["rows_total"] == 40 and e.data["message"] for e in notices)
    finished = [e for _, e in store.events_since(conn, job.id) if e.type == "finished"]
    assert finished[0].data["n_rows"] == 40


def test_an_input_column_empty_in_the_first_chunk_keeps_its_type(
    conn, run_job, owner, project, record, storage, frame, monkeypatch
):
    monkeypatch.setattr(batch_predict_handler, "CHUNK_ROWS", 8)
    flag = [None] * 8 + [True, False] * 16  # booleans with gaps are read as objects
    source = add_dataset(conn, storage, project, frame.assign(flag=flag), "flagged")
    assert dict(source.schema)["flag"] == "bool"
    done = run_job(submit(conn, owner, project, record, source))
    assert done.status is JobStatus.DONE, done.message
    out = projects.get_dataset(conn, done.result["dataset_id"])
    assert dict(out.schema)["flag"] == "bool"
    assert read_dataset(storage, out)["flag"].tolist()[8:] == [True, False] * 16


def exact_columns():
    """Columns that must come out of a prediction exactly as they went in."""
    n = 40
    ids = pd.array([2**60 + 1, 2**60 + 2, None] * 13 + [7], dtype="Int64")
    return {
        "id": ids,
        "count": pd.array(range(n), dtype="int64"),
        "flag": pd.array([True, None, False, True] * 10, dtype="boolean"),
        "when": [datetime.date(2024, 1, 1 + i % 28) if i % 5 else None for i in range(n)],
        "memo": ["メモ", None, "x", ""] * 10,
    }


def exact_source(conn, storage, project, frame):
    return ingest.ingest_batches(
        storage,
        conn,
        project.id,
        "exact",
        DatasetType.TEST,
        [frame.assign(**exact_columns())],
    )


def stored_table(storage, dataset):
    with storage.open_read(dataset.key) as f:
        return pq.read_table(f)


def assert_inputs_unchanged(storage, source, out):
    names = [n for n in stored_table(storage, source).column_names]
    assert [(n, t) for n, t in out.schema if n in names] == [
        (n, t) for n, t in source.schema if n in names
    ]
    assert stored_table(storage, out).select(names).equals(stored_table(storage, source))


def test_integer_ids_with_gaps_come_out_exactly_as_they_went_in(
    conn, run_job, owner, project, record, storage, frame, monkeypatch
):
    monkeypatch.setattr(batch_predict_handler, "CHUNK_ROWS", 16)
    source = exact_source(conn, storage, project, frame)
    assert dict(source.schema)["id"] == "int64"
    done = run_job(submit(conn, owner, project, record, source))
    assert done.status is JobStatus.DONE, done.message
    out = projects.get_dataset(conn, done.result["dataset_id"])
    assert dict(out.schema)["id"] == "int64" and dict(out.schema)["count"] == "int64"
    ids = stored_table(storage, out).column("id").to_pylist()
    assert ids[:3] == [2**60 + 1, 2**60 + 2, None]
    assert_inputs_unchanged(storage, source, out)


def test_other_input_types_come_out_unchanged_through_the_runner(
    conn, runner, owner, project, record, storage, frame
):
    source = exact_source(conn, storage, project, frame)
    done = wait_done(conn, submit(conn, owner, project, record, source).id)
    assert done.status is JobStatus.DONE, done.message
    out = projects.get_dataset(conn, done.result["dataset_id"])
    assert {n: t for n, t in out.schema}["flag"] == "bool"
    assert {n: t for n, t in out.schema}["when"] == "date32[day]"
    assert_inputs_unchanged(storage, source, out)


def test_a_deleted_dataset_is_a_plain_failure(conn, run_job, job, dataset, storage):
    projects.delete_dataset(conn, storage, dataset.id)
    done = run_job(job)
    assert done.status is JobStatus.FAILED and done.message == "the dataset no longer exists"


def test_a_deleted_model_is_a_plain_failure(conn, run_job, job, record, storage):
    models.delete_model(conn, storage, record.id)
    done = run_job(job)
    assert done.status is JobStatus.FAILED and done.message == "the model no longer exists"
    assert predict_datasets(conn, projects.require_project(conn, job.project_id)) == []


def test_a_model_or_dataset_of_another_project_is_refused(
    conn, run_job, owner, project, record, dataset, storage, settings, frame
):
    other = projects.create_project(conn, owner, "other")
    foreign_data = add_dataset(conn, storage, other, frame)
    foreign_model = add_model(conn, storage, settings, other, classifier())
    payload = {"model_id": record.id, "dataset_id": foreign_data.id, "include_columns": None}
    done = run_job(store.enqueue(conn, "batch_predict", project.id, owner.id, payload))
    assert done.status is JobStatus.FAILED and done.message == "the dataset no longer exists"
    payload = {"model_id": foreign_model.id, "dataset_id": dataset.id, "include_columns": None}
    done = run_job(store.enqueue(conn, "batch_predict", project.id, owner.id, payload))
    assert done.status is JobStatus.FAILED and done.message == "the model no longer exists"


def test_a_tampered_model_is_refused_with_a_plain_message(conn, run_job, job, record, storage):
    key = next(k for k in storage.list(record.storage_prefix) if k.endswith(".joblib"))
    storage.put(key, b"not a model")
    done = run_job(job)
    assert done.status is JobStatus.FAILED
    assert done.message == "the model file failed verification"


def test_unknown_included_columns_in_a_payload_fail_plainly(
    conn, run_job, owner, project, record, dataset
):
    payload = {"model_id": record.id, "dataset_id": dataset.id, "include_columns": ["nope"]}
    done = run_job(store.enqueue(conn, "batch_predict", project.id, owner.id, payload))
    assert done.status is JobStatus.FAILED
    assert done.message == "unknown columns in include_columns: ['nope']"


def test_a_failing_insert_removes_the_stored_object(
    conn, run_job, job, project, storage, monkeypatch
):
    def fail(*args, **kwargs):
        raise sqlite3.IntegrityError("no such project")

    monkeypatch.setattr(service, "add_dataset", fail)
    done = run_job(job)
    assert done.status is JobStatus.FAILED and "no such project" in done.message
    assert predict_datasets(conn, project) == []
    assert len(dataset_objects(storage, project)) == 1


def test_a_failing_cleanup_does_not_mask_the_original_error(conn, run_job, job, monkeypatch):
    def fail_insert(*args, **kwargs):
        raise sqlite3.IntegrityError("no such project")

    def fail_cleanup(self, key):
        raise OSError("storage down")

    monkeypatch.setattr(service, "add_dataset", fail_insert)
    monkeypatch.setattr(LocalStorage, "delete", fail_cleanup)
    done = run_job(job)
    assert done.status is JobStatus.FAILED
    assert done.message == "IntegrityError: no such project"


def test_a_job_abort_while_reporting_progress_passes_through_the_handler(
    conn, run_job, job, project, storage, monkeypatch
):
    def fail(conn, job_id, event):
        raise sqlite3.DatabaseError("disk I/O error")

    monkeypatch.setattr(store, "append_event", fail)
    done = run_job(job)
    assert done.status is JobStatus.FAILED
    assert done.message.startswith("could not record progress")
    assert predict_datasets(conn, project) == []
    assert len(dataset_objects(storage, project)) == 1


def test_a_job_abort_after_the_dataset_is_recorded_takes_it_back_out(
    conn, run_job, job, project, storage, monkeypatch
):
    real = store.append_event

    def fail_on_finish(conn, job_id, event):
        if event.type == "finished":
            raise sqlite3.DatabaseError("disk I/O error")
        real(conn, job_id, event)

    monkeypatch.setattr(store, "append_event", fail_on_finish)
    done = run_job(job)
    assert done.status is JobStatus.FAILED
    assert done.message.startswith("could not record progress")
    assert predict_datasets(conn, project) == []
    assert len(dataset_objects(storage, project)) == 1


def test_cancelling_between_chunks_stops_the_run_and_leaves_nothing(
    conn, run_job, job, project, storage, monkeypatch
):
    monkeypatch.setattr(batch_predict_handler, "CHUNK_ROWS", 8)
    real = batch_predict_handler.predict_chunks

    def cancel_after_first(*args, **kwargs):
        for number, chunk in enumerate(real(*args, **kwargs)):
            yield chunk
            if number == 0:
                store.request_cancel(conn, job.id)
                time.sleep(worker.STOP_CHECK_SECS + 0.2)  # the stop flag is cached for 0.5 s

    monkeypatch.setattr(batch_predict_handler, "predict_chunks", cancel_after_first)
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    notices = [e for _, e in store.events_since(conn, job.id) if e.type == "notice"]
    assert len(notices) == 2  # the chunk being made at the cancel, then stopped before the 5th
    assert predict_datasets(conn, project) == []
    assert len(dataset_objects(storage, project)) == 1


def test_a_cancel_that_arrives_during_the_last_chunk_is_caught_before_saving(
    conn, run_job, job, project, storage, monkeypatch
):
    real = batch_predict_handler.predict_chunks

    def cancel_during_last(*args, **kwargs):
        yield from real(*args, **kwargs)
        store.request_cancel(conn, job.id)

    monkeypatch.setattr(batch_predict_handler, "predict_chunks", cancel_during_last)
    recorded = []
    real_add = service.add_dataset
    monkeypatch.setattr(
        service, "add_dataset", lambda *a, **k: recorded.append(a) or real_add(*a, **k)
    )
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    assert recorded == []  # caught before anything was stored, not undone afterwards
    assert predict_datasets(conn, project) == []
    assert len(dataset_objects(storage, project)) == 1


def test_a_cancel_that_arrives_while_saving_takes_the_dataset_back_out(
    conn, run_job, job, project, storage, monkeypatch
):
    real = ingest.ingest_batches

    def ingest_then_cancel(*args, **kwargs):
        result = real(*args, **kwargs)
        store.request_cancel(conn, job.id)
        return result

    monkeypatch.setattr(ingest, "ingest_batches", ingest_then_cancel)
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    assert predict_datasets(conn, project) == []
    assert len(dataset_objects(storage, project)) == 1


# --- submit_batch_predict --------------------------------------------------------------


def job_count(conn):
    return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]


def test_submit_enqueues_a_batch_predict_job(conn, owner, project, record, dataset):
    job = submit(conn, owner, project, record, dataset, include_columns=["x"], name="n")
    assert (job.kind, job.project_id, job.status) == ("batch_predict", project.id, JobStatus.QUEUED)
    assert job.payload == {
        "model_id": record.id,
        "dataset_id": dataset.id,
        "include_columns": ["x"],
        "name": "n",
        "include_contributions": False,
    }
    plain = submit(conn, owner, project, record, dataset)
    assert plain.payload["include_columns"] is None and plain.payload["name"] is None
    assert plain.payload["include_contributions"] is False
    wanted = submit(conn, owner, project, record, dataset, include_contributions=True)
    assert wanted.payload["include_contributions"] is True


def test_an_editor_member_can_submit(conn, owner, project, record, dataset):
    editor = auth.create_user(conn, "editor", "pw-editor-1", Role.EDITOR)
    projects.share_project(conn, owner, project.id, "editor", ProjectAccess.EDITOR)
    assert submit(conn, editor, project, record, dataset).kind == "batch_predict"


def test_a_viewer_cannot_submit(conn, owner, project, record, dataset):
    viewer = auth.create_user(conn, "viewer", "pw-viewer-1", Role.VIEWER)
    projects.share_project(conn, owner, project.id, "viewer", ProjectAccess.VIEWER)
    with pytest.raises(PermissionError):
        submit(conn, viewer, project, record, dataset)
    assert job_count(conn) == 0


def test_a_non_member_cannot_submit(conn, project, record, dataset):
    stranger = auth.create_user(conn, "stranger", "pw-stranger-1", Role.EDITOR)
    with pytest.raises(PermissionError):
        submit(conn, stranger, project, record, dataset)
    assert job_count(conn) == 0


def test_an_admin_asking_about_a_missing_project_gets_project_not_found(conn, record, dataset):
    admin = auth.create_user(conn, "admin", "pw-admin-1", Role.ADMIN)
    with pytest.raises(ProjectNotFound):
        models.submit_batch_predict(conn, admin, "nope", record.id, dataset.id)


def test_a_model_of_another_project_is_not_found(
    conn, storage, settings, owner, project, record, dataset
):
    other = projects.create_project(conn, owner, "other")
    foreign = add_model(conn, storage, settings, other, classifier())
    with pytest.raises(ModelNotFound):
        models.submit_batch_predict(conn, owner, project.id, foreign.id, dataset.id)
    with pytest.raises(ModelNotFound):
        models.submit_batch_predict(conn, owner, project.id, 9999, dataset.id)
    assert job_count(conn) == 0


def test_a_dataset_of_another_project_is_not_found(conn, storage, owner, project, record, frame):
    other = projects.create_project(conn, owner, "other")
    foreign = add_dataset(conn, storage, other, frame)
    with pytest.raises(DatasetNotFound):
        models.submit_batch_predict(conn, owner, project.id, record.id, foreign.id)
    with pytest.raises(DatasetNotFound):
        models.submit_batch_predict(conn, owner, project.id, record.id, 9999)
    assert job_count(conn) == 0


def test_unknown_include_columns_are_refused_before_queueing(conn, owner, project, record, dataset):
    with pytest.raises(PredictInputError) as e:
        submit(conn, owner, project, record, dataset, include_columns=["x", "nope"])
    assert isinstance(e.value, ValueError)
    assert str(e.value) == "unknown columns in include_columns: ['nope']"
    assert job_count(conn) == 0


# --- contributions ------------------------------------------------------------------------


def stored(storage, conn, done) -> pd.DataFrame:
    return read_dataset(storage, projects.get_dataset(conn, done.result["dataset_id"]))


def exported(storage, conn, done) -> bytes:
    return b"".join(
        ingest.export_csv(storage, projects.get_dataset(conn, done.result["dataset_id"]))
    )


def test_payload_without_the_key_still_runs(
    conn, run_job, owner, project, record, dataset, storage, settings
):
    phase1 = {"model_id": record.id, "dataset_id": dataset.id, "include_columns": None}
    old = run_job(store.enqueue(conn, "batch_predict", project.id, owner.id, phase1))
    assert old.status is JobStatus.DONE, old.message
    off = run_job(submit(conn, owner, project, record, dataset, include_contributions=False))
    assert off.status is JobStatus.DONE, off.message
    # the default output is Phase 1's, byte for byte: the same CSV, no contribution columns
    assert exported(storage, conn, old) == exported(storage, conn, off)
    header = exported(storage, conn, off).decode().splitlines()[0]
    assert header == '"predict","p_悪","p_普通","p_良","x","幅","color"'
    model = models.load_trained(storage, record, load_secret(settings))
    pd.testing.assert_frame_equal(
        stored(storage, conn, off), batch_predict(model, read_dataset(storage, dataset))
    )


@pytest.mark.parametrize("kind", ["multiclass", "regression"])
def test_contributions_are_stored_and_add_up(
    kind, conn, run_job, owner, project, storage, settings, frame, monkeypatch
):
    model = classifier() if kind == "multiclass" else regressor()
    record = add_model(conn, storage, settings, project, model)
    # a renamed input empty in the first chunk still takes its source's type
    monkeypatch.setattr(batch, "CONTRIBUTION_CHUNK_ROWS", 8)
    gappy = frame.astype({"x": object}).assign(contrib_x=[None] * 8 + [True, False] * 16)
    gappy.loc[[1, 5], "x"] = None
    source = add_dataset(conn, storage, project, gappy, "gappy")
    fallbacks = []
    real = ingest.ingest_batches
    monkeypatch.setattr(
        ingest,
        "ingest_batches",
        lambda *a, **k: fallbacks.append(k["fallback_types"]) or real(*a, **k),
    )
    done = run_job(submit(conn, owner, project, record, source, include_contributions=True))
    assert done.status is JobStatus.DONE, done.message
    out = stored(storage, conn, done)
    contrib = batch.contribution_columns(model)
    assert list(fallbacks[0]) == ["x", "幅", "color", "input_contrib_x"]
    predictions = ["predict"] + ([] if kind == "regression" else ["p_悪", "p_普通", "p_良"])
    assert list(out.columns) == [*predictions, *contrib, "x", "幅", "color", "input_contrib_x"]
    total = out[contrib].sum(axis=1).to_numpy()
    if kind == "regression":
        explained = out["predict"].to_numpy()
    else:
        explained = np.array([out.at[i, f"p_{label}"] for i, label in enumerate(out["predict"])])
    np.testing.assert_allclose(total, explained, atol=1e-5)
    assert dict(projects.get_dataset(conn, done.result["dataset_id"]).schema)[
        "input_contrib_x"
    ] == ("bool")
    assert out["input_contrib_x"].tolist()[8:] == [True, False] * 16


def test_contributions_report_progress_per_smaller_chunk(
    conn, run_job, owner, project, record, dataset, monkeypatch
):
    monkeypatch.setattr(batch, "CONTRIBUTION_CHUNK_ROWS", 15)
    done = run_job(submit(conn, owner, project, record, dataset, include_contributions=True))
    assert done.status is JobStatus.DONE, done.message
    notices = [e for _, e in store.events_since(conn, done.id) if e.type == "notice"]
    assert [e.data["rows_done"] for e in notices] == [15, 30, 40]


def test_cancelling_between_contribution_chunks_leaves_nothing(
    conn, run_job, owner, project, record, dataset, storage, monkeypatch
):
    monkeypatch.setattr(batch, "CONTRIBUTION_CHUNK_ROWS", 8)
    job = submit(conn, owner, project, record, dataset, include_contributions=True)
    real = batch_predict_handler.predict_chunks

    def cancel_after_first(*args, **kwargs):
        for number, chunk in enumerate(real(*args, **kwargs)):
            yield chunk
            if number == 0:
                store.request_cancel(conn, job.id)
                time.sleep(worker.STOP_CHECK_SECS + 0.2)

    monkeypatch.setattr(batch_predict_handler, "predict_chunks", cancel_after_first)
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    notices = [e for _, e in store.events_since(conn, job.id) if e.type == "notice"]
    assert len(notices) == 2
    assert predict_datasets(conn, project) == []
    assert len(dataset_objects(storage, project)) == 1


def test_only_a_contributions_run_caps_the_threads(
    conn, run_job, owner, project, record, dataset, monkeypatch
):
    capped = []
    real = explain.cap_threads
    monkeypatch.setattr(explain, "cap_threads", lambda model: capped.append(model) or real(model))
    assert run_job(submit(conn, owner, project, record, dataset)).status is JobStatus.DONE
    assert capped == []
    done = run_job(submit(conn, owner, project, record, dataset, include_contributions=True))
    assert done.status is JobStatus.DONE, done.message
    assert len(capped) == 1


def test_more_than_100k_rows_is_refused_at_submit(
    conn, owner, project, record, dataset, monkeypatch
):
    assert dataset.n_rows == 40
    monkeypatch.setattr(batch, "MAX_CONTRIBUTION_ROWS", 39)
    with pytest.raises(PredictInputError) as e:
        submit(conn, owner, project, record, dataset, include_contributions=True)
    assert str(e.value) == "contributions are limited to 39 rows"
    assert job_count(conn) == 0
    assert submit(conn, owner, project, record, dataset).kind == "batch_predict"
    monkeypatch.setattr(batch, "MAX_CONTRIBUTION_ROWS", 40)
    assert submit(conn, owner, project, record, dataset, include_contributions=True)


def test_the_job_checks_the_row_cap_again_before_reading(
    conn, run_job, owner, project, record, dataset, monkeypatch
):
    job = submit(conn, owner, project, record, dataset, include_contributions=True)
    monkeypatch.setattr(batch, "MAX_CONTRIBUTION_ROWS", 39)
    reads = []
    monkeypatch.setattr(ingest, "read_dataset", lambda *a, **k: reads.append(a))
    done = run_job(job)
    assert done.status is JobStatus.FAILED
    assert done.message == "contributions are limited to 39 rows"
    assert reads == [] and predict_datasets(conn, project) == []


def test_a_model_too_wide_to_explain_fails_the_job_plainly(
    conn, run_job, owner, project, record, dataset, monkeypatch
):
    monkeypatch.setattr(explain, "CELLS", 1)
    done = run_job(submit(conn, owner, project, record, dataset, include_contributions=True))
    assert done.status is JobStatus.FAILED
    assert "too wide" in done.message
    assert predict_datasets(conn, project) == []
