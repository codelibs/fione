import json
import signal
import sqlite3
import sys
import tempfile
import time

import numpy as np
import pandas as pd
import pytest

from fione import db
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.config import Settings
from fione.engine.events import Event
from fione.jobs import module_handler, store, worker
from fione.jobs.runner import TRAINING_KINDS, JobRunner
from fione.jobs.store import JobStatus
from fione.modules import registry, service
from fione.modules.registry import Module, ModuleOutput
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.ingest import read_dataset
from fione.projects.service import DatasetType
from fione.storage import open_storage

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
    return auth.create_user(conn, "root", "pw-admin-1", Role.ADMIN)


@pytest.fixture
def owner(conn):
    return auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR)


@pytest.fixture
def project(conn, owner):
    return projects.create_project(conn, owner, "demo")


def frame():
    rng = np.random.default_rng(0)
    pts = np.vstack([c + rng.normal(scale=0.4, size=(10, 2)) for c in ([0, 0], [9, 9], [-9, 6])])
    return pd.DataFrame(
        {"id": range(30), "a": pts[:, 0], "b": pts[:, 1], "名前": [f"n{i}" for i in range(30)]}
    )


def add_dataset(conn, storage, project, df=None, name="data", type=DatasetType.TEST):
    return ingest.ingest_batches(
        storage, conn, project.id, name, type, [frame() if df is None else df]
    )


@pytest.fixture
def dataset(conn, storage, project):
    return add_dataset(conn, storage, project)


@pytest.fixture
def runner(settings, db_path):
    made = JobRunner(settings, db_path, poll_secs=0.05, cancel_grace_secs=0.5)
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


def submit(conn, owner, project, dataset, module_id, params=None, **kw):
    return service.submit_module(conn, owner, project.id, module_id, dataset.id, params or {}, **kw)


def dataset_objects(storage, project):
    return storage.list(f"projects/{project.id}/")


def n_models(conn):
    return conn.execute("SELECT COUNT(*) FROM module_models").fetchone()[0]


def event_list(conn, job_id):
    return [e for _, e in store.events_since(conn, job_id)]


def upload(conn, storage, admin, module_id, body, kind="frame", props="{}"):
    source = (
        f"MODULE = {{'name': 'M {module_id}', 'kind': {kind!r},"
        f" 'params': {{'properties': {props}}}}}\n{body}\n"
    )
    return service.upload_module(conn, storage, admin, module_id, source.encode())


ADD_ONE = "def run(df, params, ctx):\n    return df.assign(plus=df['id'] + 1)"


# --- through the runner and a worker subprocess ----------------------------------------------


def test_a_built_in_module_runs_end_to_end(conn, runner, owner, project, dataset, storage):
    job = submit(conn, owner, project, dataset, "sort", {"column": "a", "ascending": False})
    done = wait_done(conn, job.id)
    assert done.status is JobStatus.DONE, done.message
    assert set(done.result) == {"dataset_id", "n_rows", "module_model_id", "elapsed"}
    assert done.result["module_model_id"] is None and done.result["n_rows"] == 30
    out = projects.get_dataset(conn, done.result["dataset_id"])
    assert (out.name, out.type, out.project_id) == ("sort_data", DatasetType.TRAIN, project.id)
    expected = read_dataset(storage, dataset).sort_values("a", ascending=False)
    pd.testing.assert_frame_equal(read_dataset(storage, out), expected.reset_index(drop=True))
    types = [e.type for e in event_list(conn, job.id)]
    assert types[0] == "started" and types[-1] == "finished"


def test_an_uploaded_module_runs_only_in_the_worker(
    conn, runner, admin, owner, project, dataset, storage, tmp_path
):
    canary = tmp_path / "canary"
    body = f"import os\nopen({str(canary)!r}, 'a').write(str(os.getpid()) + '\\n')\n" + ADD_ONE
    upload(conn, storage, admin, "add_one", body)
    import os

    before = set(sys.modules)
    done = wait_done(conn, submit(conn, owner, project, dataset, "add_one").id)
    assert done.status is JobStatus.DONE, done.message
    pids = canary.read_text().split()
    assert len(pids) == 2 and str(os.getpid()) not in pids and pids[0] != pids[1]  # inspect, worker
    assert not (set(sys.modules) - before) and "add_one" not in sys.modules
    out = projects.get_dataset(conn, done.result["dataset_id"])
    got = read_dataset(storage, out)
    assert list(got["plus"]) == list(range(1, 31)) and out.name == "add_one_data"
    assert [n for n, _ in out.schema] == ["id", "a", "b", "名前", "plus"]


def test_cancelling_a_running_module_leaves_nothing(
    conn, runner, admin, owner, project, dataset, storage, tmp_path
):
    started = tmp_path / "started"
    body = (
        "import time\ndef run(df, params, ctx):\n"
        f"    open({str(started)!r}, 'w').write('x')\n    time.sleep(120)"
    )
    upload(conn, storage, admin, "slow", body)
    objects = dataset_objects(storage, project)
    job = submit(conn, owner, project, dataset, "slow")
    wait_for(started.exists)
    assert runner.cancel(job.id)
    assert store.get_job(conn, job.id).status is JobStatus.CANCELLED
    assert projects.list_datasets(conn, project.id) == [dataset]
    assert dataset_objects(storage, project) == objects and n_models(conn) == 0


def test_a_train_job_then_a_predict_job_through_the_runner(
    conn, runner, owner, project, dataset, storage
):
    train = wait_done(
        conn,
        submit(conn, owner, project, dataset, "kmeans_train", {"k": 3, "columns": ["a", "b"]}).id,
    )
    assert train.status is JobStatus.DONE, train.message
    model_id = train.result["module_model_id"]
    assert model_id is not None
    done = wait_done(
        conn,
        submit(conn, owner, project, dataset, "kmeans_predict", {"module_model_id": model_id}).id,
    )
    assert done.status is JobStatus.DONE, done.message
    got = read_dataset(storage, projects.get_dataset(conn, done.result["dataset_id"]))
    fit = read_dataset(storage, projects.get_dataset(conn, train.result["dataset_id"]))
    assert list(got["cluster"]) == list(fit["cluster"]) and sorted(set(got["cluster"])) == [0, 1, 2]


def test_the_handler_is_registered_without_extra_modules():
    import os
    import subprocess

    env = {k: v for k, v in os.environ.items() if k != "FIONE_JOB_HANDLER_MODULES"}
    code = (
        "from fione.jobs import worker; worker._import_handler_modules();"
        "from fione.jobs.handlers import HANDLERS; print(sorted(HANDLERS))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    )
    assert "'module'" in out.stdout
    assert "module" not in TRAINING_KINDS  # a short job


# --- the handler run in this process, so failures can be injected -----------------------------


def test_train_stores_the_state_and_a_model_row(conn, run_job, owner, project, dataset, storage):
    done = run_job(
        submit(conn, owner, project, dataset, "kmeans_train", {"k": 3, "columns": ["a", "b"]})
    )
    assert done.status is JobStatus.DONE, done.message
    model_id = done.result["module_model_id"]
    row = conn.execute("SELECT * FROM module_models WHERE id = ?", (model_id,)).fetchone()
    assert (row["project_id"], row["module_id"], row["name"]) == (
        project.id,
        "kmeans_train",
        "kmeans_train_data",
    )
    assert row["source_dataset_id"] == dataset.id and row["created_at"] > 0
    assert row["state_key"].startswith(f"projects/{project.id}/module_models/")
    assert row["state_key"].endswith("/state.json")
    state = json.loads(storage.get(row["state_key"]))
    assert state["type"] == "kmeans" and len(state["centers"]) == 3
    out = projects.get_dataset(conn, done.result["dataset_id"])
    assert out.type is DatasetType.TRAIN and out.n_rows == 30
    # deleting the project removes the dataset, the state object and the row
    projects.delete_project(conn, storage, owner, project.id)
    assert n_models(conn) == 0 and storage.list("") == []


def test_a_predict_job_makes_a_predict_dataset_and_no_model(
    conn, run_job, owner, project, dataset, storage
):
    train = run_job(
        submit(
            conn,
            owner,
            project,
            dataset,
            "lowrank_train",
            {"columns": ["a", "b"], "n_components": 1},
        )
    )
    done = run_job(
        submit(
            conn,
            owner,
            project,
            dataset,
            "lowrank_predict",
            {"module_model_id": train.result["module_model_id"], "output_columns": ["名前"]},
            name="proj",
        )
    )
    assert done.status is JobStatus.DONE, done.message
    assert done.result["module_model_id"] is None and n_models(conn) == 1
    out = projects.get_dataset(conn, done.result["dataset_id"])
    assert (out.name, out.type) == ("proj", DatasetType.PREDICT)
    assert [n for n, _ in out.schema] == ["component_1", "名前"]


def test_a_second_dataset_reaches_the_module(conn, run_job, owner, project, dataset, storage):
    extra = add_dataset(conn, storage, project, pd.DataFrame({"y": range(30)}), "extra")
    done = run_job(submit(conn, owner, project, dataset, "cbind", {"other_dataset_id": extra.id}))
    assert done.status is JobStatus.DONE, done.message
    assert read_dataset(storage, projects.get_dataset(conn, done.result["dataset_id"]))[
        "y"
    ].tolist() == list(range(30))


def test_the_module_sees_the_same_integers_with_gaps(conn, run_job, owner, project, storage):
    ids = pd.array([2**60 + 1, None, 3], dtype="Int64")
    data = add_dataset(conn, storage, project, pd.DataFrame({"id": ids, "v": [1.0, 2.0, 3.0]}))
    done = run_job(submit(conn, owner, project, data, "cslice", {"columns": ["id"]}))
    out = projects.get_dataset(conn, done.result["dataset_id"])
    assert dict(out.schema)["id"] == "int64"
    assert read_dataset(storage, out, nullable_dtypes=True)["id"].tolist()[0] == 2**60 + 1


def failure(conn, run_job, owner, project, dataset, storage, module_id, params=None):
    before = (projects.list_datasets(conn, project.id), dataset_objects(storage, project))
    done = run_job(submit(conn, owner, project, dataset, module_id, params))
    assert done.status is JobStatus.FAILED
    assert (projects.list_datasets(conn, project.id), dataset_objects(storage, project)) == before
    assert n_models(conn) == 0
    return done


def test_a_module_error_is_a_plain_message(conn, run_job, owner, project, dataset, storage):
    done = failure(conn, run_job, owner, project, dataset, storage, "floor", {"columns": ["名前"]})
    assert done.message.startswith("columns are not numeric: ['名前']")


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (
            "def run(df, params, ctx):\n"
            "    raise ValueError('bad thing in /etc/passwd and /tmp/x/y.py')",
            "ValueError",
        ),
        ("import sys\ndef run(df, params, ctx):\n    sys.exit(2)", "SystemExit"),
        ("def run(df, params, ctx):\n    return [1, 2]", "must return a DataFrame"),
        (
            "def run(df, params, ctx):\n    return df[['id', 'id']]",
            "duplicate column names: ['id']",
        ),
        ("def run(df, params, ctx):\n    return df.iloc[:0]", "no data rows"),
        ("def run(df, params, ctx):\n    return df, {'x': 1}", "state"),
        (
            "from fione.modules.registry import ModuleError\n"
            "def run(df, params, ctx):\n    raise ModuleError('my own words')",
            "my own words",
        ),
    ],
)
def test_a_misbehaving_module_fails_the_job_without_leaking_paths(
    conn, run_job, admin, owner, project, dataset, storage, settings, body, message
):
    upload(conn, storage, admin, "bad", body)
    done = failure(conn, run_job, owner, project, dataset, storage, "bad")
    assert message in done.message
    assert str(settings.data_dir) not in done.message and tempfile.gettempdir() not in done.message
    assert "/etc/passwd" not in done.message and "/tmp/x" not in done.message


def test_a_crash_in_user_code_leaves_a_traceback_event(
    conn, run_job, admin, owner, project, dataset, storage
):
    upload(conn, storage, admin, "bad", "def run(df, params, ctx):\n    raise KeyError('nope')")
    done = failure(conn, run_job, owner, project, dataset, storage, "bad")
    errors = [e for e in event_list(conn, done.id) if e.type == "error"]
    assert errors and "KeyError" in errors[0].data["traceback"]


def test_a_module_that_fails_at_load_time_is_a_plain_failure(
    conn, run_job, admin, owner, project, dataset, storage, tmp_path
):
    # passes inspection, then breaks when the worker loads it for the run
    marker = tmp_path / "late"
    body = (
        f"import os\nif os.path.exists({str(marker)!r}):\n    raise RuntimeError('late /x/y')\n"
        + ADD_ONE
    )
    upload(conn, storage, admin, "flaky", body)
    marker.write_text("x")
    done = failure(conn, run_job, owner, project, dataset, storage, "flaky")
    assert done.message == "the module failed to load: RuntimeError"


def test_a_tampered_module_is_refused(
    conn, run_job, admin, owner, project, dataset, storage, tmp_path
):
    marker = tmp_path / "ran"
    upload(conn, storage, admin, "add_one", ADD_ONE)
    evil = f"open({str(marker)!r}, 'w').write('x')\n" + ADD_ONE
    storage.put("modules/add_one/module.py", evil.encode())
    done = failure(conn, run_job, owner, project, dataset, storage, "add_one")
    assert done.message == "the module file failed verification" and not marker.exists()


def test_a_module_whose_object_is_gone_is_a_plain_failure(
    conn, run_job, admin, owner, project, dataset, storage
):
    upload(conn, storage, admin, "add_one", ADD_ONE)
    job = submit(conn, owner, project, dataset, "add_one")
    storage.delete("modules/add_one/module.py")
    done = run_job(job)
    assert done.status is JobStatus.FAILED and done.message == "the module file failed verification"


def test_a_deleted_module_dataset_or_model_is_a_plain_failure(
    conn, run_job, admin, owner, project, dataset, storage
):
    upload(conn, storage, admin, "add_one", ADD_ONE)
    job = submit(conn, owner, project, dataset, "add_one")
    service.delete_module(conn, storage, admin, "add_one")
    assert run_job(job).message == "the module no longer exists"

    job = submit(conn, owner, project, dataset, "sort", {"column": "a"})
    projects.delete_dataset(conn, storage, dataset.id)
    assert run_job(job).message == "the dataset no longer exists"


def test_a_payload_naming_another_projects_data_or_model_is_refused(
    conn, run_job, owner, project, dataset, storage
):
    other = projects.create_project(conn, owner, "other")
    foreign = add_dataset(conn, storage, other)
    model = conn.execute(
        "INSERT INTO module_models (project_id, module_id, name, state_key, created_at)"
        " VALUES (?, 'kmeans_train', 'm', 'k', 1.0)",
        (other.id,),
    ).lastrowid
    for payload, message in [
        (
            {"module_id": "sort", "dataset_id": foreign.id, "params": {"column": "a"}},
            "the dataset no longer exists",
        ),
        (
            {
                "module_id": "cbind",
                "dataset_id": dataset.id,
                "params": {"other_dataset_id": foreign.id},
            },
            "the dataset no longer exists",
        ),
        (
            {
                "module_id": "kmeans_predict",
                "dataset_id": dataset.id,
                "params": {"module_model_id": model},
            },
            "the module model no longer exists",
        ),
        (
            {"module_id": "sort", "dataset_id": dataset.id, "params": {}},
            "missing argument 'column'",
        ),
    ]:
        done = run_job(store.enqueue(conn, "module", project.id, owner.id, payload))
        assert done.status is JobStatus.FAILED and done.message == message


def test_a_state_that_is_not_a_model_of_this_module_fails_plainly(
    conn, run_job, owner, project, dataset, storage
):
    key = f"projects/{project.id}/module_models/abc/state.json"
    storage.put(key, b"not json")
    model = conn.execute(
        "INSERT INTO module_models (project_id, module_id, name, state_key, created_at)"
        " VALUES (?, 'kmeans_train', 'm', ?, 1.0)",
        (project.id, key),
    ).lastrowid
    done = run_job(
        submit(conn, owner, project, dataset, "kmeans_predict", {"module_model_id": model})
    )
    assert done.status is JobStatus.FAILED and done.message == "the module model file is damaged"


def test_an_uploaded_train_module_returns_its_own_state(
    conn, run_job, admin, owner, project, dataset, storage
):
    body = (
        "def run(df, params, ctx):\n"
        "    return df[['id']], {'n': len(df), 'mean': float(df['a'].mean())}"
    )
    upload(conn, storage, admin, "mean_a", body, kind="train")
    done = run_job(submit(conn, owner, project, dataset, "mean_a"))
    assert done.status is JobStatus.DONE, done.message
    row = conn.execute("SELECT * FROM module_models").fetchone()
    assert row["module_id"] == "mean_a" and json.loads(storage.get(row["state_key"]))["n"] == 30

    body = "def run(df, params, ctx):\n    return df.assign(mean=ctx.state['mean'])"
    upload(
        conn,
        storage,
        admin,
        "use_mean",
        body,
        kind="predict",
        props="{'module_model_id': {'type': 'integer'}}",
    )
    done = run_job(
        submit(conn, owner, project, dataset, "use_mean", {"module_model_id": row["id"]})
    )
    assert done.status is JobStatus.DONE, done.message
    out = read_dataset(storage, projects.get_dataset(conn, done.result["dataset_id"]))
    assert out["mean"].nunique() == 1 and out.attrs == {} and len(out) == 30


@pytest.mark.parametrize(
    ("result", "message"),
    [
        ("df", "train module must return a state"),
        ("df, {'bad': float('nan')}", "state"),
        ("df, [1, 2]", "state must be a JSON object"),
        ("df, {'x': object()}", "state"),
        ("df, {'big': 'x' * (9 << 20)}", "state is larger"),
    ],
)
def test_a_train_module_must_return_a_plain_json_state(
    conn, run_job, admin, owner, project, dataset, storage, result, message
):
    upload(
        conn, storage, admin, "t", f"def run(df, params, ctx):\n    return {result}", kind="train"
    )
    done = failure(conn, run_job, owner, project, dataset, storage, "t")
    assert message in done.message


def test_the_module_cannot_load_anything_into_this_process(
    conn, run_job, admin, owner, project, dataset, storage
):
    upload(conn, storage, admin, "add_one", ADD_ONE)
    before = set(sys.modules)
    assert run_job(submit(conn, owner, project, dataset, "add_one")).status is JobStatus.DONE
    assert set(sys.modules) - before == set()


# --- cancelling and failing around the store ------------------------------------------------


def cancel_module(conn, job_id_holder):
    def run(df, params, ctx):
        store.request_cancel(conn, job_id_holder["id"])
        return ModuleOutput(df)

    return Module("cancel_me", "Cancel", "frame", {"type": "object", "properties": {}}, run)


def test_a_cancel_during_the_run_is_seen_before_anything_is_stored(
    conn, run_job, owner, project, dataset, storage, monkeypatch
):
    holder = {}
    monkeypatch.setitem(registry._BUILTIN, "cancel_me", cancel_module(conn, holder))
    job = submit(conn, owner, project, dataset, "cancel_me")
    holder["id"] = job.id
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    assert projects.list_datasets(conn, project.id) == [dataset] and n_models(conn) == 0
    assert len(dataset_objects(storage, project)) == 1


def test_a_cancel_while_storing_takes_the_dataset_back_out(
    conn, run_job, owner, project, dataset, storage, monkeypatch
):
    job = submit(conn, owner, project, dataset, "sort", {"column": "a"})
    real = ingest.ingest_batches

    def ingest_then_cancel(*args, **kwargs):
        created = real(*args, **kwargs)
        store.request_cancel(conn, job.id)
        return created

    monkeypatch.setattr(ingest, "ingest_batches", ingest_then_cancel)
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    assert projects.list_datasets(conn, project.id) == [dataset]
    assert len(dataset_objects(storage, project)) == 1


def test_a_cancel_after_the_model_is_recorded_takes_everything_back_out(
    conn, run_job, owner, project, dataset, storage, monkeypatch
):
    job = submit(conn, owner, project, dataset, "kmeans_train", {"k": 2, "columns": ["a", "b"]})
    real = module_handler._store_model

    def store_then_cancel(*args, **kwargs):
        model_id = real(*args, **kwargs)
        assert n_models(conn) == 1
        store.request_cancel(conn, job.id)
        return model_id

    monkeypatch.setattr(module_handler, "_store_model", store_then_cancel)
    done = run_job(job)
    assert done.status is JobStatus.CANCELLED
    assert projects.list_datasets(conn, project.id) == [dataset] and n_models(conn) == 0
    assert len(dataset_objects(storage, project)) == 1


def test_a_failing_model_insert_removes_the_dataset_and_the_state(
    conn, run_job, owner, project, dataset, storage, monkeypatch
):
    real_put = type(storage).put
    seen = []

    def spy(self, key, data):
        seen.append(key)
        return real_put(self, key, data)

    monkeypatch.setattr(type(storage), "put", spy)
    monkeypatch.setattr(
        module_handler,
        "_insert_model",
        lambda *a, **k: (_ for _ in ()).throw(sqlite3.IntegrityError("no such project")),
    )
    job = submit(conn, owner, project, dataset, "kmeans_train", {"k": 2, "columns": ["a", "b"]})
    done = run_job(job)
    assert done.status is JobStatus.FAILED and "no such project" in done.message
    assert any(k.endswith("state.json") for k in seen)
    assert projects.list_datasets(conn, project.id) == [dataset] and n_models(conn) == 0
    assert len(dataset_objects(storage, project)) == 1


def test_a_failing_dataset_insert_removes_the_object(
    conn, run_job, owner, project, dataset, storage, monkeypatch
):
    def fail(*args, **kwargs):
        raise sqlite3.IntegrityError("no such project")

    monkeypatch.setattr(projects, "add_dataset", fail)
    done = run_job(submit(conn, owner, project, dataset, "sort", {"column": "a"}))
    assert done.status is JobStatus.FAILED and "no such project" in done.message
    assert len(dataset_objects(storage, project)) == 1


def test_a_lost_event_connection_undoes_the_store_and_is_not_swallowed(
    conn, run_job, owner, project, dataset, storage, monkeypatch, caplog
):
    real = store.append_event

    def lose_finished(c, job_id, event: Event):
        if event.type == "finished":
            raise sqlite3.IntegrityError("job row is gone")
        return real(c, job_id, event)

    def broken_delete(*args, **kwargs):
        raise OSError("cannot delete")

    monkeypatch.setattr(store, "append_event", lose_finished)
    monkeypatch.setattr(projects, "delete_dataset", broken_delete)
    done = run_job(submit(conn, owner, project, dataset, "sort", {"column": "a"}))
    # the JobAbort reaches the worker unchanged even though the undo itself failed
    assert done.status is JobStatus.FAILED and done.message.startswith("could not record progress")
    assert "cannot delete" in caplog.text


def test_a_lost_event_connection_removes_the_dataset(
    conn, run_job, owner, project, dataset, storage, monkeypatch
):
    real = store.append_event

    def lose_finished(c, job_id, event: Event):
        if event.type == "finished":
            raise sqlite3.IntegrityError("job row is gone")
        return real(c, job_id, event)

    monkeypatch.setattr(store, "append_event", lose_finished)
    done = run_job(
        submit(conn, owner, project, dataset, "kmeans_train", {"k": 2, "columns": ["a", "b"]})
    )
    assert done.status is JobStatus.FAILED and done.message.startswith("could not record progress")
    assert projects.list_datasets(conn, project.id) == [dataset] and n_models(conn) == 0
    assert len(dataset_objects(storage, project)) == 1


def test_a_failing_cleanup_after_the_store_leaves_no_dataset(
    conn, run_job, owner, project, dataset, storage, monkeypatch
):
    import contextlib

    class FailingStack(contextlib.ExitStack):
        def __exit__(self, *exc):
            super().__exit__(*exc)
            raise OSError("cleanup failed")

    monkeypatch.setattr(module_handler.contextlib, "ExitStack", FailingStack)
    done = run_job(submit(conn, owner, project, dataset, "sort", {"column": "a"}))
    assert done.status is JobStatus.FAILED and done.message == "OSError: cleanup failed"
    assert projects.list_datasets(conn, project.id) == [dataset]
    assert len(dataset_objects(storage, project)) == 1
