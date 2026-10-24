import io
import os
import signal
import sqlite3
import subprocess
import sys
import time

import pytest
from sklearn.datasets import load_iris

from fione import db
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.config import Settings, load_secret
from fione.engine.families import XGBoost
from fione.jobs import automl_handler, store, worker
from fione.jobs.runner import JobRunner
from fione.jobs.store import JobStatus
from fione.models import service as models
from fione.projects import service as projects
from fione.projects.ingest import ingest_csv
from fione.projects.service import DatasetType
from fione.storage import open_storage

TERMINAL = {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED}
CONFIG = {"target": "species", "max_runtime_secs": 20, "max_models": 4, "nfolds": 3}


def iris_frame():
    df = load_iris(as_frame=True).frame
    df["species"] = df.pop("target").map({0: "setosa", 1: "versicolor", 2: "virginica"})
    return df


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
    # The built-in handlers must be there without any extra handler modules.
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
    return projects.create_project(conn, owner, "iris")


def add_dataset(conn, storage, project, df, name="iris"):
    data = df.to_csv(index=False).encode()
    return ingest_csv(storage, conn, project.id, name, DatasetType.TRAIN, io.BytesIO(data))


@pytest.fixture
def dataset(conn, storage, project):
    return add_dataset(conn, storage, project, iris_frame())


@pytest.fixture
def runner(settings, db_path):
    made = JobRunner(settings, db_path, poll_secs=0.05)
    made.start()
    yield made
    made.shutdown(kill_running=True)


def wait_done(conn, job_id):
    return wait_for(lambda: (j := store.get_job(conn, job_id)).status in TERMINAL and j)


def event_types(conn, job_id):
    return [e.type for _, e in store.events_since(conn, job_id)]


def model_count(conn):
    return conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]


# --- through the runner and a worker subprocess ---------------------------------


def test_a_training_job_runs_end_to_end(conn, runner, owner, project, dataset, storage, settings):
    job = models.submit_training(conn, owner, project.id, dataset.id, CONFIG)
    done = wait_done(conn, job.id)
    assert done.status is JobStatus.DONE, done.message

    assert set(done.result) == {"model_id", "stop_reason", "best_model", "metrics", "elapsed"}
    record = models.get_model(conn, done.result["model_id"])
    assert (record.project_id, record.dataset_id, record.job_id) == (project.id, dataset.id, job.id)
    assert record.name.startswith("species model ")
    assert record.storage_prefix.startswith(f"projects/{project.id}/models/")
    assert storage.list(record.storage_prefix)
    assert done.result["stop_reason"] == record.stop_reason
    assert done.result["best_model"] == record.best_model
    assert done.result["metrics"] == record.metrics and done.result["elapsed"] > 0
    assert record.task == "classification" and record.target == "species"
    assert any(row["model"] == "Ensemble" for row in record.leaderboard)
    assert sum(record.importance.values()) == pytest.approx(1.0)
    assert record.trials and record.config["max_models"] == 4

    trained = models.load_trained(storage, record, load_secret(settings))
    frame = iris_frame()
    predicted = trained.predict(frame.drop(columns=["species"]))
    assert (predicted.to_numpy() == frame["species"].to_numpy()).mean() > 0.9

    types = event_types(conn, job.id)
    assert types[0] == "started" and types[-1] == "finished"
    assert "trial" in types and types.index("stopped") < types.index("ensemble")


def test_missing_target_values_fail_the_job_with_a_plain_message(
    conn, runner, owner, project, storage
):
    df = iris_frame()
    df.loc[:4, "species"] = None
    dataset = add_dataset(conn, storage, project, df, "gaps")
    job = models.submit_training(conn, owner, project.id, dataset.id, CONFIG)
    done = wait_done(conn, job.id)
    assert done.status is JobStatus.FAILED
    assert done.message.startswith("target has missing values")
    assert "Error" not in done.message and "Traceback" not in done.message
    assert model_count(conn) == 0 and storage.list(f"projects/{project.id}/models/") == []


def test_cancelling_mid_run_leaves_no_model_and_no_objects(
    conn, runner, owner, project, dataset, storage
):
    config = {**CONFIG, "max_runtime_secs": 120, "max_models": None}
    job = models.submit_training(conn, owner, project.id, dataset.id, config)

    def first_trial():
        return "trial" in event_types(conn, job.id)

    wait_for(first_trial)
    assert runner.cancel(job.id)
    assert store.get_job(conn, job.id).status is JobStatus.CANCELLED
    assert model_count(conn) == 0
    assert storage.list(f"projects/{project.id}/models/") == []


def test_builtin_handlers_are_registered_without_extra_modules():
    env = {k: v for k, v in os.environ.items() if k != "FIONE_JOB_HANDLER_MODULES"}
    code = (
        "from fione.jobs import worker; worker._import_handler_modules();"
        "from fione.jobs.handlers import HANDLERS; print(sorted(HANDLERS))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    )
    assert "'automl'" in out.stdout


# --- the handler run in this process, so failures can be injected -------------------


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


@pytest.fixture
def quick_job(conn, owner, project, dataset):
    config = {**CONFIG, "max_runtime_secs": 15, "max_models": 3}
    return models.submit_training(conn, owner, project.id, dataset.id, config, name="quick")


def test_a_failing_save_leaves_nothing_behind(conn, run_job, quick_job, storage, monkeypatch):
    def fail(model, storage, prefix, secret, *, image_tag):
        storage.put(prefix + "model.joblib", b"partial")
        raise OSError("disk full")

    monkeypatch.setattr(automl_handler, "save_model", fail)
    done = run_job(quick_job)
    assert done.status is JobStatus.FAILED and "disk full" in done.message
    assert model_count(conn) == 0


def test_a_failing_insert_removes_the_saved_objects(
    conn, run_job, quick_job, storage, project, monkeypatch
):
    def fail(conn, **kwargs):
        raise sqlite3.IntegrityError("no such project")

    monkeypatch.setattr(models, "add_model", fail)
    done = run_job(quick_job)
    assert done.status is JobStatus.FAILED and "no such project" in done.message
    assert model_count(conn) == 0
    assert storage.list(f"projects/{project.id}/models/") == []


def test_a_degraded_run_still_records_the_model(
    conn, run_job, owner, project, dataset, monkeypatch
):
    def boom(self, *args, **kwargs):
        raise ValueError("library failure")

    monkeypatch.setattr(XGBoost, "_fit", boom)
    config = {**CONFIG, "max_models": None, "stopping_rounds": 1, "stopping_tolerance": 0.5}
    job = models.submit_training(conn, owner, project.id, dataset.id, config, name="quick")
    done = run_job(job)
    assert done.status is JobStatus.DONE, done.message
    assert done.result["stop_reason"] == "error" and done.result["degraded"] is True
    record = models.get_model(conn, done.result["model_id"])
    assert record.name == "quick" and "XGBoost" not in {r["family"] for r in record.leaderboard}
    notices = [e for _, e in store.events_since(conn, job.id) if e.type == "notice"]
    assert any(e.data.get("kind") == "family_error" for e in notices)


def test_a_job_abort_during_training_passes_through_the_handler(
    conn, run_job, quick_job, storage, project, monkeypatch
):
    def fail(conn, job_id, event):
        raise sqlite3.DatabaseError("disk I/O error")

    monkeypatch.setattr(store, "append_event", fail)
    done = run_job(quick_job)
    assert done.status is JobStatus.FAILED
    assert done.message.startswith("could not record progress")
    assert model_count(conn) == 0
    assert storage.list(f"projects/{project.id}/models/") == []


def test_a_deleted_dataset_is_a_plain_failure(conn, run_job, quick_job, dataset, storage):
    projects.delete_dataset(conn, storage, dataset.id)
    done = run_job(quick_job)
    assert done.status is JobStatus.FAILED and done.message == "the dataset no longer exists"
    assert model_count(conn) == 0


def test_a_dataset_that_was_replaced_by_one_of_another_project_is_refused(
    conn, run_job, owner, project, storage
):
    other = projects.create_project(conn, owner, "other")
    foreign = add_dataset(conn, storage, other, iris_frame())
    job = store.enqueue(
        conn, "automl", project.id, owner.id, {"dataset_id": foreign.id, "config": CONFIG}
    )
    done = run_job(job)
    assert done.status is JobStatus.FAILED and done.message == "the dataset no longer exists"
