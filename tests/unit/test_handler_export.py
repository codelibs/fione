import io
import os
import signal
import sqlite3
import subprocess
import sys
import time
import zipfile

import pandas as pd
import pytest
from predict_models import classifier, features, regressor

from fione import db
from fione.auth import service as auth
from fione.auth.roles import ProjectAccess, Role
from fione.config import Settings, load_secret
from fione.engine.artifact import save_model
from fione.jobs import export_handler, store, worker
from fione.jobs.runner import TRAINING_KINDS, JobRunner
from fione.jobs.store import JobStatus
from fione.models import service as models
from fione.models.transfer import import_model, submit_export_all
from fione.predict import batch_predict
from fione.projects import service as projects
from fione.projects.service import ProjectNotFound
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
def admin(conn):
    return auth.create_user(conn, "admin", "pw-admin-1", Role.ADMIN)


@pytest.fixture
def owner(conn):
    return auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR)


@pytest.fixture
def project(conn, owner):
    return projects.create_project(conn, owner, "demo")


def add_model(conn, storage, settings, project, model, name, token):
    prefix = f"projects/{project.id}/models/{token}/"
    save_model(model, storage, prefix, load_secret(settings), image_tag="test")
    return models.add_model(
        conn,
        project_id=project.id,
        dataset_id=None,
        job_id=None,
        name=name,
        model=model,
        storage_prefix=prefix,
    )


@pytest.fixture
def records(conn, storage, settings, project):
    return [
        add_model(conn, storage, settings, project, classifier(), "モデル1", "aaa"),
        add_model(conn, storage, settings, project, regressor(), "second", "bbb"),
        add_model(conn, storage, settings, project, classifier(), "third", "ccc"),
    ]


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


def exports(storage, project):
    return storage.list(f"projects/{project.id}/exports/")


@pytest.fixture
def job(conn, owner, project, records):
    return submit_export_all(conn, owner, project.id)


def outer_members(storage, key):
    with storage.open_read(key) as f, zipfile.ZipFile(f) as zf:
        assert all(i.compress_type == zipfile.ZIP_STORED for i in zf.infolist())
        return {i.filename: zf.read(i) for i in zf.infolist()}


# --- through the runner and a worker subprocess -----------------------------------------------


def test_an_export_job_runs_end_to_end(
    conn, runner, owner, admin, project, records, storage, settings
):
    job = submit_export_all(conn, owner, project.id)
    done = wait_done(conn, job.id)
    assert done.status is JobStatus.DONE, done.message

    key = f"projects/{project.id}/exports/{job.id}.zip"
    assert set(done.result) == {"key", "n_models", "bytes"}
    assert done.result["key"] == key and done.result["n_models"] == 3
    assert done.result["bytes"] == storage.size(key)
    assert exports(storage, project) == [key]

    inner = outer_members(storage, key)
    assert sorted(inner) == sorted(f"model-{r.id}.zip" for r in records)

    types = [e.type for _, e in store.events_since(conn, job.id)]
    assert types[-1] == "finished" and "notice" in types

    other = projects.create_project(conn, owner, "target")
    secret = load_secret(settings)
    for record in records:
        imported = import_model(
            storage, conn, admin, other.id, io.BytesIO(inner[f"model-{record.id}.zip"]), secret
        )
        assert imported.trusted == 1 and imported.name == f"{record.name} (imported)"
        assert imported.task == record.task and imported.leaderboard == record.leaderboard
    frame = features(10)
    first = models.load_trained(storage, models.list_models(conn, other.id)[-1], secret)
    pd.testing.assert_frame_equal(batch_predict(first, frame), batch_predict(classifier(), frame))


def test_the_handler_is_registered_without_extra_modules():
    env = {k: v for k, v in os.environ.items() if k != "FIONE_JOB_HANDLER_MODULES"}
    code = (
        "from fione.jobs import worker; worker._import_handler_modules();"
        "from fione.jobs.handlers import HANDLERS; print(sorted(HANDLERS))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    )
    assert "'export_models'" in out.stdout


def test_exporting_is_a_short_job():
    assert "export_models" not in TRAINING_KINDS


# --- the handler run in this process, so failures can be injected -----------------------------


def test_a_project_without_models_fails_in_plain_words(conn, run_job, owner, project, storage):
    done = run_job(submit_export_all(conn, owner, project.id))
    assert done.status is JobStatus.FAILED and done.message == "this project has no models"
    assert exports(storage, project) == []


def test_only_the_projects_own_models_are_exported(
    conn, run_job, owner, project, records, storage, settings
):
    other = projects.create_project(conn, owner, "other")
    add_model(conn, storage, settings, other, classifier(), "foreign", "ddd")
    done = run_job(submit_export_all(conn, owner, project.id))
    assert done.status is JobStatus.DONE and done.result["n_models"] == 3
    assert exports(storage, other) == []


def test_a_model_with_missing_objects_fails_naming_it(
    conn, run_job, job, project, records, storage
):
    storage.delete(records[1].storage_prefix + "model.joblib")
    done = run_job(job)
    assert done.status is JobStatus.FAILED
    assert str(records[1].id) in done.message and "Error" not in done.message
    assert exports(storage, project) == []


def test_cancelling_between_models_leaves_no_export(
    conn, run_job, job, project, storage, monkeypatch
):
    real = export_handler.export_model
    seen = []

    def cancel_after_first(*args, **kwargs):
        seen.append(1)
        yield from real(*args, **kwargs)
        if len(seen) == 1:
            store.request_cancel(conn, job.id)
            time.sleep(worker.STOP_CHECK_SECS + 0.2)  # the stop flag is cached for 0.5 s

    monkeypatch.setattr(export_handler, "export_model", cancel_after_first)
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    assert len(seen) == 1  # the second model was never started
    assert exports(storage, project) == []


def test_a_cancel_that_arrives_during_the_last_model_is_caught_before_storing(
    conn, run_job, job, project, storage, monkeypatch
):
    real = export_handler.export_model
    left = [3]

    def cancel_during_last(*args, **kwargs):
        yield from real(*args, **kwargs)
        left[0] -= 1
        if left[0] == 0:
            store.request_cancel(conn, job.id)

    monkeypatch.setattr(export_handler, "export_model", cancel_during_last)
    stored = []
    real_put = LocalStorage.put
    monkeypatch.setattr(
        LocalStorage, "put", lambda self, *a: stored.append(a[0]) or real_put(self, *a)
    )
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    assert stored == []  # caught before anything was written
    assert exports(storage, project) == []


def test_a_cancel_that_arrives_while_storing_removes_the_export(
    conn, run_job, job, project, storage, monkeypatch
):
    real_put = LocalStorage.put

    def put_then_cancel(self, key, data):
        real_put(self, key, data)
        if "/exports/" in key:
            store.request_cancel(conn, job.id)

    monkeypatch.setattr(LocalStorage, "put", put_then_cancel)
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    assert exports(storage, project) == []


def test_a_job_abort_after_the_export_is_stored_takes_it_back_out(
    conn, run_job, job, project, storage, monkeypatch
):
    real = store.append_event

    def fail_on_finish(conn, job_id, event):
        if event.type == "finished":
            raise sqlite3.DatabaseError("disk I/O error")
        real(conn, job_id, event)

    monkeypatch.setattr(store, "append_event", fail_on_finish)
    done = run_job(job)
    assert done.status is JobStatus.FAILED and done.message.startswith("could not record progress")
    assert exports(storage, project) == []


def test_a_failing_cleanup_does_not_mask_the_original_error(
    conn, run_job, job, project, storage, monkeypatch
):
    real = store.append_event

    def fail_on_finish(conn, job_id, event):
        if event.type == "finished":
            raise sqlite3.DatabaseError("disk I/O error")
        real(conn, job_id, event)

    def fail_delete(self, key):
        raise OSError("storage down")

    monkeypatch.setattr(store, "append_event", fail_on_finish)
    monkeypatch.setattr(LocalStorage, "delete", fail_delete)
    done = run_job(job)
    assert done.status is JobStatus.FAILED and done.message.startswith("could not record progress")


def test_a_new_export_replaces_the_older_ones(conn, run_job, owner, project, records, storage):
    first = run_job(submit_export_all(conn, owner, project.id))
    stray = f"projects/{project.id}/exports/stray.zip"
    storage.put(stray, b"old")
    second = run_job(submit_export_all(conn, owner, project.id))
    assert (first.status, second.status) == (JobStatus.DONE, JobStatus.DONE)
    assert exports(storage, project) == [second.result["key"]]


def test_a_failing_removal_of_an_old_export_is_only_logged(
    conn, run_job, owner, project, records, storage, monkeypatch, caplog
):
    first = run_job(submit_export_all(conn, owner, project.id))
    original = type(storage).delete

    def delete(self, key):
        if key == first.result["key"]:
            raise OSError("disk says no")
        original(self, key)

    monkeypatch.setattr(type(storage), "delete", delete)
    second = run_job(submit_export_all(conn, owner, project.id))
    assert second.status is JobStatus.DONE, second.message
    assert sorted(exports(storage, project)) == sorted([first.result["key"], second.result["key"]])
    assert "could not remove the older export" in caplog.text


def test_no_temp_file_is_left_behind(conn, run_job, job, tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path / "scratch"))
    (tmp_path / "scratch").mkdir()
    done = run_job(job)
    assert done.status is JobStatus.DONE, done.message
    assert list((tmp_path / "scratch").iterdir()) == []


# --- submit_export_all ------------------------------------------------------------------------


def test_submit_enqueues_an_export_models_job(conn, owner, project, records):
    job = submit_export_all(conn, owner, project.id)
    assert (job.kind, job.project_id, job.status, job.owner_id) == (
        "export_models",
        project.id,
        JobStatus.QUEUED,
        owner.id,
    )


def test_a_viewer_member_can_submit(conn, owner, project, records):
    viewer = auth.create_user(conn, "viewer", "pw-viewer-1", Role.VIEWER)
    projects.share_project(conn, owner, project.id, "viewer", ProjectAccess.VIEWER)
    assert submit_export_all(conn, viewer, project.id).kind == "export_models"


def test_a_user_outside_the_project_cannot_submit(conn, owner, project, records):
    stranger = auth.create_user(conn, "stranger", "pw-stranger-1", Role.EDITOR)
    with pytest.raises(PermissionError):
        submit_export_all(conn, stranger, project.id)
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_a_missing_project_is_refused(conn, owner):
    with pytest.raises(ProjectNotFound):
        submit_export_all(conn, owner, "nope")
