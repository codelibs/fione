import io
import os
import shlex
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest
from starlette.requests import Request

from api_helpers import (
    FAST_CONFIG,
    add_user,
    bearer,
    connect,
    iris_csv,
    store_model,
    upload,
    wait_job,
)
from fione.auth.roles import Role
from fione.engine.events import Event
from fione.jobs import store
from fione.jobs.store import JobStatus

UNIT_TESTS = Path(__file__).parents[1] / "unit"


@dataclass
class Env:
    client: object
    h: dict  # persona -> bearer headers
    p: str  # the owner's project, shared with "viewer" as viewer
    q: str  # the outsider's project
    d: int  # iris train dataset of p
    dq: int  # iris train dataset of q

    def conn(self):
        return connect(self.client)

    @property
    def storage(self):
        return self.client.app.state.storage

    @property
    def data_dir(self) -> Path:
        return self.client.app.state.settings.data_dir


@pytest.fixture
def make_env(make_client):
    def make(**settings) -> Env:
        client = make_client(**settings)
        users = {
            "admin": add_user(client, "admin", Role.ADMIN),
            "owner": add_user(client, "owner"),
            "viewer": add_user(client, "viewer"),
            "outsider": add_user(client, "outsider"),
        }
        h = {name: bearer(client, user.id) for name, user in users.items()}
        p = client.post("/api/v1/projects", json={"name": "P"}, headers=h["owner"]).json()["id"]
        shared = client.post(
            f"/api/v1/projects/{p}/share",
            json={"username": "viewer", "access": "viewer"},
            headers=h["owner"],
        )
        assert shared.status_code == 204
        q = client.post("/api/v1/projects", json={"name": "Q"}, headers=h["outsider"]).json()["id"]
        d = upload(client, p, iris_csv(), headers=h["owner"]).json()["id"]
        dq = upload(client, q, iris_csv(), headers=h["outsider"]).json()["id"]
        return Env(client, h, p, q, d, dq)

    return make


@pytest.fixture
def env(make_env):
    return make_env()


def zip_names(content: bytes) -> set[str]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        return set(zf.namelist())


def tmp_files(env: Env) -> list:
    tmp = env.data_dir / "tmp"
    return list(tmp.iterdir()) if tmp.exists() else []


def finished_job(env: Env, project_id, kind="automl", status=JobStatus.DONE, **finish) -> int:
    """A job that ran and ended with ``status``, recorded straight in the store."""
    conn = env.conn()
    try:
        job = store.enqueue(conn, kind, project_id, 1, {})
        store.claim_job(conn, job.id, "token")
        store.finish_job(conn, job.id, status, **finish)
        return job.id
    finally:
        conn.close()


def queued_job(env: Env, project_id, kind="automl", payload=None) -> int:
    conn = env.conn()
    try:
        return store.enqueue(conn, kind, project_id, 1, payload or {}).id
    finally:
        conn.close()


def job_count(env: Env) -> int:
    conn = env.conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    finally:
        conn.close()


def a_model(env: Env, project_id, secret=None, name="iris model"):
    conn = env.conn()
    try:
        return store_model(
            conn, env.storage, secret or env.client.app.state.secret, project_id, name
        )
    finally:
        conn.close()


# --- the whole flow, with the job runner in process ---------------------------------------------


def test_automl_trains_and_the_model_exports_imports_serves_and_predicts(make_env, monkeypatch):
    monkeypatch.delenv("FIONE_JOB_HANDLER_MODULES", raising=False)
    env = make_env(start_runner=True)
    c, h, p = env.client, env.h, env.p

    r = c.post(
        f"/api/v1/projects/{p}/jobs/automl",
        json={"dataset_id": env.d, "config": FAST_CONFIG, "name": "iris"},
        headers=h["owner"],
    )
    assert r.status_code == 201, r.text
    assert (r.json()["kind"], r.json()["status"]) == ("automl", "queued")
    job = wait_job(c, r.json()["id"], h["owner"])
    assert job["status"] == "done", job
    assert (job["stop_reason"], job["degraded"]) == ("max_models", False)
    model_id = job["result"]["model_id"]

    model = c.get(f"/api/v1/models/{model_id}", headers=h["viewer"]).json()
    assert model["name"] == "iris" and model["project_id"] == p and model["job_id"] == job["id"]
    assert model["metrics"]["accuracy"] > 0.8
    assert (model["stop_reason"], model["degraded"], model["trusted"]) == (
        "max_models",
        False,
        True,
    )
    assert model["leaderboard"] and model["config"]["target"] == "species"
    assert "storage_prefix" not in model
    listed = c.get(f"/api/v1/projects/{p}/models", headers=h["viewer"]).json()
    assert [m["id"] for m in listed] == [model_id]
    events = c.get(f"/api/v1/jobs/{job['id']}/events", headers=h["viewer"]).json()
    assert events["events"] and events["status"] == "done"

    exported = c.get(f"/api/v1/models/{model_id}/export", headers=h["viewer"])
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/zip"
    assert exported.headers["content-disposition"] == (
        "attachment; filename=\"iris.zip\"; filename*=UTF-8''iris.zip"
    )
    assert zip_names(exported.content) == {"manifest.json", "model.joblib", "record.json"}
    imported = c.post(
        f"/api/v1/projects/{env.q}/models/import",
        files={"file": ("iris.zip", exported.content, "application/zip")},
        headers=h["admin"],
    )
    assert imported.status_code == 201, imported.text
    body = imported.json()
    assert (body["project_id"], body["name"], body["trusted"]) == (env.q, "iris (imported)", True)
    assert body["metrics"] == model["metrics"]

    bundle = c.get(f"/api/v1/models/{model_id}/serving", headers=h["viewer"])
    assert bundle.status_code == 200
    assert bundle.headers["content-disposition"].startswith(
        f'attachment; filename="fione-serving-iris-{model_id}.zip"'
    )
    assert zip_names(bundle.content) == {"model/manifest.json", "model/model.joblib"}
    assert tmp_files(env) == []

    r = c.post(
        f"/api/v1/projects/{p}/jobs/batch-predict",
        json={"model_id": model_id, "dataset_id": env.d, "include_columns": ["species"]},
        headers=h["owner"],
    )
    assert r.status_code == 201, r.text
    predicted = wait_job(c, r.json()["id"], h["owner"])
    assert predicted["status"] == "done", predicted
    dataset = c.get(
        f"/api/v1/projects/{p}/datasets/{predicted['result']['dataset_id']}", headers=h["viewer"]
    ).json()
    assert (dataset["type"], dataset["n_rows"]) == ("predict", 150)
    assert [col["name"] for col in dataset["schema"]][:2] == ["predict", "p_setosa"]

    r = c.post(f"/api/v1/projects/{p}/jobs/export", headers=h["viewer"])
    assert r.status_code == 201, r.text
    export_job = wait_job(c, r.json()["id"], h["viewer"])
    assert export_job["status"] == "done", export_job
    assert "key" not in export_job["result"]
    download = c.get(f"/api/v1/projects/{p}/exports/{export_job['id']}", headers=h["viewer"])
    assert download.status_code == 200
    assert download.headers["content-disposition"].startswith(
        f'attachment; filename="fione-export-P-{export_job["id"]}.zip"'
    )
    assert zip_names(download.content) == {f"model-{model_id}.zip"}
    events = c.get(f"/api/v1/jobs/{export_job['id']}/events", headers=h["viewer"]).json()
    assert events["events"] and "key" not in str(events)

    # A second export replaces the first: only the latest zip is kept.
    r = c.post(f"/api/v1/projects/{p}/jobs/export", headers=h["viewer"])
    newer = wait_job(c, r.json()["id"], h["viewer"])
    assert newer["status"] == "done", newer
    exports = f"/api/v1/projects/{p}/exports"
    old = c.get(f"{exports}/{export_job['id']}", headers=h["viewer"])
    assert old.status_code == 404 and "superseded" in old.json()["error"]
    assert c.get(f"{exports}/{newer['id']}", headers=h["viewer"]).status_code == 200
    assert env.storage.list(f"projects/{p}/exports/") == [f"projects/{p}/exports/{newer['id']}.zip"]

    assert c.delete(f"/api/v1/jobs/{newer['id']}", headers=h["owner"]).status_code == 204
    key = f"projects/{p}/exports/{newer['id']}.zip"
    assert not env.storage.exists(key)
    assert not (env.data_dir / "jobs" / f"{newer['id']}.log").exists()


def test_a_running_job_is_cancelled(make_env, monkeypatch):
    monkeypatch.setenv("FIONE_JOB_HANDLER_MODULES", "job_test_handlers")
    path = os.pathsep.join(p for p in (str(UNIT_TESTS), os.environ.get("PYTHONPATH")) if p)
    monkeypatch.setenv("PYTHONPATH", path)
    env = make_env(start_runner=True)
    job_id = queued_job(env, env.p, "sleep", {"seconds": 60})
    deadline = time.monotonic() + 30
    while not env.client.get(f"/api/v1/jobs/{job_id}/events", headers=env.h["owner"]).json()[
        "events"
    ]:
        assert time.monotonic() < deadline, "the job never started"
        time.sleep(0.1)
    assert env.client.get(f"/api/v1/jobs/{job_id}", headers=env.h["owner"]).json()["status"] == (
        "running"
    )
    viewer = env.client.post(f"/api/v1/jobs/{job_id}/cancel", headers=env.h["viewer"])
    assert viewer.status_code == 403
    r = env.client.post(f"/api/v1/jobs/{job_id}/cancel", headers=env.h["owner"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


# --- submitting -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("config", "reason"),
    [
        ({"target": "species", "nfolds": 1}, "nfolds must be a whole number of at least 2"),
        ({"target": "species", "bogus": 1}, "unknown parameters: ['bogus']"),
        ({"target": "nope"}, "target column 'nope' is not in the data"),
        ({"max_models": 1}, "target is required"),
        ({"target": "species", "ignored_columns": ["species"]}, "cannot also be ignored"),
        ({"target": "species", "seed": -1}, "seed must be a whole number from 0 to 4294967295"),
        ({"target": "species", "seed": 2**32}, "seed must be a whole number from 0"),
        ({"target": "species", "sort_metric": "rmse"}, "sort_metric 'rmse' does not apply"),
        ({"target": "species", "stopping_metric": "mae"}, "stopping_metric 'mae' does not apply"),
    ],
)
def test_an_invalid_training_config_is_422_and_nothing_is_queued(env, config, reason):
    r = env.client.post(
        f"/api/v1/projects/{env.p}/jobs/automl",
        json={"dataset_id": env.d, "config": config},
        headers=env.h["owner"],
    )
    assert r.status_code == 422
    assert reason in r.json()["error"]
    assert job_count(env) == 0


def test_training_needs_a_train_dataset_of_the_project(env):
    test_set = upload(env.client, env.p, iris_csv(), type="test", headers=env.h["owner"])
    url = f"/api/v1/projects/{env.p}/jobs/automl"
    cases = [
        ({"dataset_id": test_set.json()["id"], "config": FAST_CONFIG}, 422),
        ({"dataset_id": env.dq, "config": FAST_CONFIG}, 404),
        ({"dataset_id": 2**63, "config": FAST_CONFIG}, 422),
        ({"dataset_id": env.d, "config": FAST_CONFIG, "extra": 1}, 422),
    ]
    for body, status in cases:
        r = env.client.post(url, json=body, headers=env.h["owner"])
        assert r.status_code == status, (body, r.text)
    assert job_count(env) == 0
    viewer = env.client.post(
        url, json={"dataset_id": env.d, "config": FAST_CONFIG}, headers=env.h["viewer"]
    )
    assert viewer.status_code == 403


def test_batch_predict_checks_the_model_dataset_and_columns(env):
    model = a_model(env, env.p)
    other = a_model(env, env.q)
    url = f"/api/v1/projects/{env.p}/jobs/batch-predict"
    cases = [
        ({"model_id": model.id, "dataset_id": env.dq}, 404),
        ({"model_id": other.id, "dataset_id": env.d}, 404),
        ({"model_id": 999999, "dataset_id": env.d}, 404),
        ({"model_id": model.id, "dataset_id": env.d, "include_columns": ["nope"]}, 422),
    ]
    for body, status in cases:
        r = env.client.post(url, json=body, headers=env.h["owner"])
        assert r.status_code == status, (body, r.text)
    assert job_count(env) == 0
    r = env.client.post(
        url, json={"model_id": model.id, "dataset_id": env.d}, headers=env.h["owner"]
    )
    assert r.status_code == 201 and r.json()["kind"] == "batch_predict"
    assert r.json()["payload"] == {
        "model_id": model.id,
        "dataset_id": env.d,
        "include_columns": None,
        "name": None,
    }


def test_module_jobs_are_checked_before_they_are_queued(env):
    url = f"/api/v1/projects/{env.p}/jobs/module"
    column = "sepal length (cm)"
    cases = [
        ({"module_id": "nope", "dataset_id": env.d}, 422),
        ({"module_id": "sort", "dataset_id": env.d, "params": {"bogus": 1}}, 422),
        ({"module_id": "sort", "dataset_id": env.dq, "params": {"column": column}}, 404),
        ({"module_id": "cbind", "dataset_id": env.d, "params": {"other_dataset_id": env.dq}}, 404),
        ({"module_id": "cbind", "dataset_id": env.d, "params": {"other_dataset_id": 2**70}}, 422),
    ]
    for body, status in cases:
        r = env.client.post(url, json=body, headers=env.h["owner"])
        assert r.status_code == status, (body, r.text)
    assert job_count(env) == 0
    r = env.client.post(
        url,
        json={"module_id": "sort", "dataset_id": env.d, "params": {"column": column}},
        headers=env.h["owner"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["payload"]["params"] == {"column": column, "ascending": True}


# --- following, cancelling and deleting ----------------------------------------------------------


def test_cancelling_a_queued_job(env):
    job_id = queued_job(env, env.p)
    assert env.client.post(
        f"/api/v1/jobs/{job_id}/cancel", headers=env.h["viewer"]
    ).status_code == (403)
    assert env.client.post(
        f"/api/v1/jobs/{job_id}/cancel", headers=env.h["outsider"]
    ).status_code == (404)
    r = env.client.post(f"/api/v1/jobs/{job_id}/cancel", headers=env.h["owner"])
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    again = env.client.post(f"/api/v1/jobs/{job_id}/cancel", headers=env.h["owner"])
    assert again.status_code == 409


def test_events_page_with_after(env):
    job_id = queued_job(env, env.p)
    conn = env.conn()
    try:
        for i in range(3):
            store.append_event(conn, job_id, Event("notice", data={"i": i}))
    finally:
        conn.close()
    url = f"/api/v1/jobs/{job_id}/events"
    everything = env.client.get(url, headers=env.h["viewer"]).json()
    ids = [e["id"] for e in everything["events"]]
    assert [e["data"]["i"] for e in everything["events"]] == [0, 1, 2]
    assert ids == sorted(ids) and everything["last_id"] == ids[-1]
    rest = env.client.get(url, params={"after": ids[0]}, headers=env.h["viewer"]).json()
    assert [e["id"] for e in rest["events"]] == ids[1:]
    none = env.client.get(url, params={"after": ids[-1]}, headers=env.h["viewer"]).json()
    assert none["events"] == [] and none["last_id"] == ids[-1]
    assert env.client.get(url, params={"after": -1}, headers=env.h["viewer"]).status_code == 422
    assert env.client.get(url, params={"after": 2**63}, headers=env.h["viewer"]).status_code == 422


def test_events_come_in_pages_of_limit(env):
    job_id = queued_job(env, env.p)
    conn = env.conn()
    try:
        for i in range(7):
            store.append_event(conn, job_id, Event("notice", data={"i": i}))
    finally:
        conn.close()
    url = f"/api/v1/jobs/{job_id}/events"
    seen, after, pages = [], 0, 0
    while True:
        page = env.client.get(url, params={"after": after, "limit": 3}, headers=env.h["viewer"])
        body = page.json()
        if not body["events"]:
            break
        assert len(body["events"]) <= 3
        seen += [e["data"]["i"] for e in body["events"]]
        after, pages = body["last_id"], pages + 1
    assert seen == list(range(7)) and pages == 3
    for bad in (0, 1001):
        assert (
            env.client.get(url, params={"limit": bad}, headers=env.h["viewer"]).status_code == 422
        )


def test_the_job_list_is_newest_first_and_limited(env):
    ids = []
    for _ in range(3):  # alternating projects: the limit applies to the merged list
        ids += [queued_job(env, env.p), queued_job(env, env.q)]
    url = "/api/v1/jobs"
    newest = env.client.get(url, params={"limit": 3}, headers=env.h["admin"]).json()
    assert [j["id"] for j in newest] == ids[::-1][:3]
    ids = ids[0::2]  # the owner's
    one = env.client.get(url, params={"project_id": env.p, "limit": 1}, headers=env.h["owner"])
    assert [j["id"] for j in one.json()] == [ids[-1]]
    assert len(env.client.get(url, headers=env.h["owner"]).json()) == 3
    for bad in (0, 1001):
        assert env.client.get(url, params={"limit": bad}, headers=env.h["owner"]).status_code == 422


def test_deleting_a_job_removes_its_log_and_export_zip(env):
    logs = env.data_dir / "jobs"
    logs.mkdir(parents=True, exist_ok=True)
    job_id = finished_job(env, env.p, kind="export_models")
    key = f"projects/{env.p}/exports/{job_id}.zip"
    env.storage.put(key, b"zip")
    (logs / f"{job_id}.log").write_text("log")
    assert env.client.delete(f"/api/v1/jobs/{job_id}", headers=env.h["viewer"]).status_code == 403
    assert env.client.delete(f"/api/v1/jobs/{job_id}", headers=env.h["owner"]).status_code == 204
    assert not (logs / f"{job_id}.log").exists()
    assert not env.storage.exists(key)
    assert env.client.get(f"/api/v1/jobs/{job_id}", headers=env.h["owner"]).status_code == 404
    queued = queued_job(env, env.p)
    assert env.client.delete(f"/api/v1/jobs/{queued}", headers=env.h["owner"]).status_code == 409


def test_deleting_the_finished_jobs_of_a_project(env):
    logs = env.data_dir / "jobs"
    logs.mkdir(parents=True, exist_ok=True)
    done = finished_job(env, env.p, kind="export_models")
    env.storage.put(f"projects/{env.p}/exports/{done}.zip", b"zip")
    failed = finished_job(env, env.p, status=JobStatus.FAILED, message="boom")
    queued = queued_job(env, env.p)
    elsewhere = finished_job(env, env.q, kind="export_models")
    env.storage.put(f"projects/{env.q}/exports/{elsewhere}.zip", b"zip")
    for job_id in (done, failed, queued, elsewhere):
        (logs / f"{job_id}.log").write_text("log")
    url = "/api/v1/jobs"
    assert env.client.delete(url, headers=env.h["owner"]).status_code == 422  # project_id needed
    params = {"project_id": env.p}
    assert env.client.delete(url, params=params, headers=env.h["viewer"]).status_code == 403
    assert env.client.delete(url, params=params, headers=env.h["outsider"]).status_code == 404
    r = env.client.delete(url, params=params, headers=env.h["owner"])
    assert r.status_code == 200 and r.json() == {"deleted": 2}
    left = env.client.get(url, params={"project_id": env.p}, headers=env.h["owner"]).json()
    assert [j["id"] for j in left] == [queued]
    assert sorted(p.name for p in logs.iterdir()) == sorted([f"{queued}.log", f"{elsewhere}.log"])
    assert env.storage.list(f"projects/{env.p}/exports/") == []
    assert env.storage.exists(f"projects/{env.q}/exports/{elsewhere}.zip")


def test_job_and_model_ids_of_another_project_are_404(env):
    q_job = finished_job(env, env.q)
    q_model = a_model(env, env.q)
    owner = env.h["owner"]
    for path in (
        f"/api/v1/jobs/{q_job}",
        f"/api/v1/jobs/{q_job}/events",
        f"/api/v1/models/{q_model.id}",
        f"/api/v1/models/{q_model.id}/export",
        f"/api/v1/models/{q_model.id}/serving",
        "/api/v1/jobs/999999",
        "/api/v1/models/999999",
    ):
        r = env.client.get(path, headers=owner)
        assert r.status_code == 404, path
    assert env.client.post(f"/api/v1/jobs/{q_job}/cancel", headers=owner).status_code == 404
    assert env.client.delete(f"/api/v1/models/{q_model.id}", headers=owner).status_code == 404
    assert env.client.get(f"/api/v1/jobs/{q_job}", headers=env.h["admin"]).status_code == 200
    assert env.client.get("/api/v1/jobs/999999", headers=env.h["admin"]).status_code == 404

    p_job = finished_job(env, env.p)
    listed = env.client.get("/api/v1/jobs", headers=owner).json()
    assert [j["id"] for j in listed] == [p_job]
    every = env.client.get("/api/v1/jobs", headers=env.h["admin"]).json()
    assert {j["id"] for j in every} == {p_job, q_job}
    assert env.client.get(
        "/api/v1/jobs", params={"project_id": env.q}, headers=owner
    ).status_code == (404)
    missing = env.client.get(
        "/api/v1/jobs", params={"project_id": "missing"}, headers=env.h["admin"]
    )
    assert missing.status_code == 404


def test_export_downloads_are_checked_against_the_path_project(env):
    admin = env.h["admin"]
    q_export = finished_job(env, env.q, kind="export_models")
    env.storage.put(f"projects/{env.q}/exports/{q_export}.zip", b"zip")
    # Even with a zip under this project's prefix, another project's job is not served here.
    env.storage.put(f"projects/{env.p}/exports/{q_export}.zip", b"zip")
    not_an_export = finished_job(env, env.p)
    running = queued_job(env, env.p, kind="export_models")
    base = f"/api/v1/projects/{env.p}/exports"
    assert env.client.get(f"{base}/{q_export}", headers=admin).status_code == 404
    assert env.client.get(f"{base}/{not_an_export}", headers=admin).status_code == 404
    assert env.client.get(f"{base}/{running}", headers=admin).status_code == 409
    assert env.client.get(f"{base}/999999", headers=admin).status_code == 404
    gone = finished_job(env, env.p, kind="export_models")  # done, but its zip is missing
    assert env.client.get(f"{base}/{gone}", headers=admin).status_code == 404
    ok = env.client.get(f"/api/v1/projects/{env.q}/exports/{q_export}", headers=admin)
    assert ok.status_code == 200 and ok.content == b"zip"


def test_only_one_export_is_queued_or_running_per_project(env):
    url = f"/api/v1/projects/{env.p}/jobs/export"
    a_model(env, env.p)
    first = env.client.post(url, headers=env.h["viewer"])
    assert first.status_code == 201
    again = env.client.post(url, headers=env.h["owner"])
    assert again.status_code == 409 and "already" in again.json()["error"]
    assert (
        env.client.post(
            f"/api/v1/projects/{env.q}/jobs/export", headers=env.h["outsider"]
        ).status_code
        == 201
    )
    conn = env.conn()
    try:  # running counts too
        store.claim_job(conn, first.json()["id"], "token")
    finally:
        conn.close()
    assert env.client.post(url, headers=env.h["viewer"]).status_code == 409
    cancelled = env.client.post(f"/api/v1/jobs/{first.json()['id']}/cancel", headers=env.h["owner"])
    assert cancelled.status_code == 200
    conn = env.conn()
    try:  # no runner: settle the cancel the way the worker would
        store.finish_job(conn, first.json()["id"], JobStatus.CANCELLED)
    finally:
        conn.close()
    assert env.client.post(url, headers=env.h["viewer"]).status_code == 201


def test_an_export_that_did_not_complete_is_404(env):
    base = f"/api/v1/projects/{env.p}/exports"
    for status in (JobStatus.FAILED, JobStatus.CANCELLED):
        job_id = finished_job(env, env.p, kind="export_models", status=status)
        r = env.client.get(f"{base}/{job_id}", headers=env.h["viewer"])
        assert r.status_code == 404 and r.json()["error"] == "the export did not complete"
    queued = queued_job(env, env.p, kind="export_models")
    assert env.client.get(f"{base}/{queued}", headers=env.h["viewer"]).status_code == 409


def test_non_admins_see_error_messages_without_tracebacks(env):
    message = "RuntimeError: boom in /tmp/fione-module-x1/module.py\nmore detail"
    job_id = finished_job(env, env.p, status=JobStatus.FAILED, message=message)
    traceback = 'Traceback (most recent call last):\n  File "/srv/app/worker.py", line 1'
    conn = env.conn()
    try:
        data = {"error": message, "traceback": traceback, "log_tail": "secret log"}
        store.append_event(conn, job_id, Event("error", data=data))
        store.append_event(conn, job_id, Event("notice", data={"message": "kept /a/b c"}))
        # What the engine emits when a model family fails (fione.engine.search.error_notice).
        notice = {
            "kind": "family_error",
            "family": "XGBoost",
            "exception": "OSError",
            "message": "cannot write /var/tmp/joblib_x/f.pkl\nsecond line",
        }
        store.append_event(conn, job_id, Event("notice", data=notice))
    finally:
        conn.close()
    shown = "RuntimeError: boom in <path>"
    for persona in ("viewer", "owner"):
        job = env.client.get(f"/api/v1/jobs/{job_id}", headers=env.h[persona]).json()
        assert job["message"] == shown
        listed = env.client.get("/api/v1/jobs", headers=env.h[persona]).json()
        assert listed[0]["message"] == shown
        events = env.client.get(f"/api/v1/jobs/{job_id}/events", headers=env.h[persona]).json()
        assert [e["data"] for e in events["events"]] == [
            {"error": shown},
            {"message": "kept /a/b c"},  # not an error: left alone
            {**notice, "message": "cannot write <path>"},
        ]
        assert "Traceback" not in str(events) and "/tmp" not in str(job)

    admin = env.client.get(f"/api/v1/jobs/{job_id}", headers=env.h["admin"]).json()
    assert admin["message"] == message
    events = env.client.get(f"/api/v1/jobs/{job_id}/events", headers=env.h["admin"]).json()
    assert events["events"][0]["data"] == data
    assert events["events"][2]["data"] == notice


def test_a_degraded_training_job_says_so(env):
    result = {"model_id": 1, "stop_reason": "error", "best_model": "XGBoost", "degraded": True}
    job_id = finished_job(env, env.p, result=result)
    job = env.client.get(f"/api/v1/jobs/{job_id}", headers=env.h["viewer"]).json()
    assert (job["stop_reason"], job["degraded"]) == ("error", True)
    plain = finished_job(env, env.p, result={**result, "stop_reason": "time", "degraded": False})
    job = env.client.get(f"/api/v1/jobs/{plain}", headers=env.h["viewer"]).json()
    assert (job["stop_reason"], job["degraded"]) == ("time", False)


# --- models -------------------------------------------------------------------------------------


def test_a_failing_export_is_a_json_error_not_a_cut_download(env):
    model = a_model(env, env.p)
    env.storage.delete(model.storage_prefix + "model.joblib")
    for path in (f"/api/v1/models/{model.id}/export", f"/api/v1/models/{model.id}/serving"):
        r = env.client.get(path, headers=env.h["viewer"])
        assert r.status_code == 404, path
        assert r.headers["content-type"] == "application/json"
        assert r.json() == {"error": "model not found", "code": "not_found"}
    assert tmp_files(env) == []


def test_a_bundle_that_cannot_be_made_safely_is_409(make_env):
    env = make_env(serving_image="Not An Image")
    model = a_model(env, env.p)
    r = env.client.get(f"/api/v1/models/{model.id}/serving", headers=env.h["viewer"])
    assert r.status_code == 409
    assert r.json()["error"].startswith("the serving image name is not a valid image name")


def test_serving_info_gives_the_command_without_building_the_zip(make_env, monkeypatch):
    env = make_env(serving_image="registry.example:5000/team/serving")
    model = a_model(env, env.p)
    from fione.models import bundle

    def no_zip(*args, **kwargs):
        raise AssertionError("the zip was built")

    monkeypatch.setattr(bundle, "_write_zip", no_zip)
    r = env.client.get(f"/api/v1/models/{model.id}/serving/info", headers=env.h["viewer"])
    assert r.status_code == 200, r.text
    info = r.json()
    image = shlex.quote("registry.example:5000/team/serving:test")
    assert image in info["run_command"] and info["run_command"].startswith("docker run")
    assert info["example_curl"].startswith("curl -s -X POST localhost:8081/invocations")
    assert "sepal length (cm)" in info["example_curl"]
    assert info["files"] == ["model/manifest.json", "model/model.joblib"]
    assert info["filename"] == f"fione-serving-iris-model-{model.id}.zip"
    assert tmp_files(env) == []
    other = a_model(env, env.q)
    url = f"/api/v1/models/{other.id}/serving/info"
    assert env.client.get(url, headers=env.h["owner"]).status_code == 404
    env.storage.delete(model.storage_prefix + "manifest.json")
    gone = env.client.get(f"/api/v1/models/{model.id}/serving/info", headers=env.h["viewer"])
    assert gone.status_code == 404


def test_serving_info_of_a_bundle_that_cannot_be_made_safely_is_409(make_env):
    env = make_env(serving_image="Not An Image")
    model = a_model(env, env.p)
    r = env.client.get(f"/api/v1/models/{model.id}/serving/info", headers=env.h["viewer"])
    assert r.status_code == 409 and "not a valid image name" in r.json()["error"]


@pytest.mark.parametrize("path", ["/api/v1/modules", "/api/v1/projects/{p}/models/import"])
def test_admin_only_uploads_refuse_non_admins_before_reading_the_body(env, path):
    url = path.format(p=env.p)
    for persona in ("owner", "viewer", "outsider"):
        for kwargs in (
            {"json": {"id": "x"}},
            {"content": b"", "headers": {"Content-Type": "application/json"}},
            {},
            {"data": {}, "files": {}},
        ):
            headers = {**env.h[persona], **kwargs.pop("headers", {})}
            r = env.client.post(url, headers=headers, **kwargs)
            assert r.status_code == 403, (persona, kwargs, r.text)


def test_an_import_over_the_archive_limit_is_413(env, monkeypatch):
    from fione.api import routes_models

    monkeypatch.setattr(routes_models, "MAX_ARCHIVE_BYTES", 1000)
    url = f"/api/v1/projects/{env.p}/models/import"

    def post(content):
        return env.client.post(
            url, files={"file": ("m.zip", content, "application/zip")}, headers=env.h["admin"]
        )

    with monkeypatch.context() as m:  # refused from Content-Length alone: the form is never read

        def no_form(*args, **kwargs):
            raise AssertionError("the form was parsed")

        m.setattr(Request, "form", no_form)
        over_declared = post(b"\0" * (2 << 20))  # Content-Length over the limit plus slack
    assert over_declared.status_code == 413
    over_file = post(b"\0" * 5000)  # the body fits the slack, the file does not
    assert over_file.status_code == 413 and over_file.json()["code"] == "too_large"
    assert post(b"\0" * 500).status_code == 422  # under the limit: the import's own check
    assert tmp_files(env) == []


def test_a_degraded_model_says_so(env):
    model = a_model(env, env.p)
    conn = env.conn()
    try:
        conn.execute("UPDATE models SET stop_reason = 'error' WHERE id = ?", (model.id,))
    finally:
        conn.close()
    got = env.client.get(f"/api/v1/models/{model.id}", headers=env.h["viewer"]).json()
    assert (got["stop_reason"], got["degraded"]) == ("error", True)
    listed = env.client.get(f"/api/v1/projects/{env.p}/models", headers=env.h["viewer"]).json()
    assert (listed[0]["stop_reason"], listed[0]["degraded"]) == ("error", True)


def test_deleting_a_model_needs_write_access(env):
    model = a_model(env, env.p)
    url = f"/api/v1/models/{model.id}"
    assert env.client.delete(url, headers=env.h["viewer"]).status_code == 403
    assert env.client.delete(url, headers=env.h["owner"]).status_code == 204
    assert env.client.get(url, headers=env.h["owner"]).status_code == 404
    assert env.storage.list(model.storage_prefix) == []


def test_importing_is_admin_only_and_a_foreign_model_needs_trust(env):
    foreign = a_model(env, env.p, secret=b"x" * 32, name="foreign")
    exported = env.client.get(f"/api/v1/models/{foreign.id}/export", headers=env.h["owner"])
    assert exported.status_code == 200
    url = f"/api/v1/projects/{env.q}/models/import"

    def post(headers, content=exported.content, **form):
        return env.client.post(
            url, data=form, files={"file": ("m.zip", content, "application/zip")}, headers=headers
        )

    for persona in ("owner", "outsider", "viewer"):
        assert post(env.h[persona]).status_code == 403
    refused = post(env.h["admin"])
    assert refused.status_code == 422 and refused.json()["code"] == "untrusted"
    assert post(env.h["admin"], trust_foreign="maybe").status_code == 422
    assert post(env.h["admin"], content=b"not a zip").status_code == 422
    # Over the 1 MiB default body limit: the import path takes uploads.
    big = post(env.h["admin"], content=b"\0" * (2 << 20))
    assert big.status_code == 422 and big.json()["error"] == "this is not a model export file"
    assert env.client.get(f"/api/v1/projects/{env.q}/models", headers=env.h["admin"]).json() == []
    missing = env.client.post(
        "/api/v1/projects/missing/models/import",
        files={"file": ("m.zip", exported.content, "application/zip")},
        headers=env.h["admin"],
    )
    assert missing.status_code == 404
    accepted = post(env.h["admin"], trust_foreign="true")
    assert accepted.status_code == 201, accepted.text
    assert (accepted.json()["name"], accepted.json()["trusted"]) == ("foreign (imported)", False)
    assert tmp_files(env) == []


# --- modules and system --------------------------------------------------------------------------

MODULE_SOURCE = b"""
MODULE = {
    "name": "Add",
    "kind": "frame",
    "params": {"type": "object", "properties": {"by": {"type": "integer", "default": 1}}},
}


def run(df, params, ctx):
    return df.assign(plus=df.iloc[:, 0] + params["by"])
"""


def post_module(env, headers, module_id="add_one", source=MODULE_SOURCE):
    return env.client.post(
        "/api/v1/modules",
        data={"id": module_id},
        files={"file": ("module.py", source, "text/x-python")},
        headers=headers,
    )


def test_modules_upload_list_and_delete(env):
    listed = env.client.get("/api/v1/modules", headers=env.h["viewer"]).json()
    assert {"sort", "kmeans_train"} <= {m["id"] for m in listed}
    assert all(m["builtin"] for m in listed)
    for persona in ("owner", "viewer", "outsider"):
        assert post_module(env, env.h[persona]).status_code == 403
    r = post_module(env, env.h["admin"])
    assert r.status_code == 201, r.text
    body = r.json()
    assert (body["id"], body["name"], body["kind"], body["builtin"]) == (
        "add_one",
        "Add",
        "frame",
        False,
    )
    assert "NOT sandboxed" in body["warning"] and "secret key" in body["warning"]
    listed = env.client.get("/api/v1/modules", headers=env.h["viewer"]).json()
    assert "add_one" in {m["id"] for m in listed}
    assert post_module(env, env.h["admin"]).status_code == 422  # already exists
    assert post_module(env, env.h["admin"], "bad_one", b"def (:\n").status_code == 422
    assert post_module(env, env.h["admin"], "../evil").status_code == 422
    too_big = post_module(env, env.h["admin"], "big_one", b"#" * (2 << 20))
    assert too_big.status_code == 422 and "256 KB" in too_big.json()["error"]

    assert env.client.delete("/api/v1/modules/add_one", headers=env.h["owner"]).status_code == 403
    assert env.client.delete("/api/v1/modules/add_one", headers=env.h["admin"]).status_code == 204
    assert env.client.delete("/api/v1/modules/add_one", headers=env.h["admin"]).status_code == 404
    assert env.client.delete("/api/v1/modules/sort", headers=env.h["admin"]).status_code == 422


def test_system_status_names_no_secret_path_or_credential(make_client):
    client = make_client(
        storage_url="s3://fione-bucket/some/prefix",
        s3_endpoint="http://minio.internal:9000",
        s3_access_key="AKIATESTACCESSKEY",
        s3_secret_key="s3-secret-value-123",
    )
    user = add_user(client, "someone")
    admin = add_user(client, "boss", Role.ADMIN)
    r = client.get("/api/v1/system/status", headers=bearer(client, user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["storage"] == "s3" and body["is_admin"] is False
    assert body["runner"] == "stopped" and body["jobs"] == {"queued": 0, "running": 0}
    assert body["ollama"] == {"configured": False}
    secret = client.app.state.secret
    data_dir = str(client.app.state.settings.data_dir)
    for leaked in (
        "AKIATESTACCESSKEY",
        "s3-secret-value-123",
        "minio.internal",
        "fione-bucket",
        data_dir,
        secret.hex(),
        secret.decode("latin-1"),
    ):
        assert leaked not in r.text
    as_admin = client.get("/api/v1/system/status", headers=bearer(client, admin.id)).json()
    assert as_admin["is_admin"] is True
    assert client.get("/api/v1/system/status").status_code == 401


def test_system_status_counts_the_queue(env):
    queued_job(env, env.p)
    queued_job(env, env.q)
    body = env.client.get("/api/v1/system/status", headers=env.h["viewer"]).json()
    assert body["storage"] == "local" and body["jobs"] == {"queued": 2, "running": 0}
    assert str(env.data_dir) not in str(body)
