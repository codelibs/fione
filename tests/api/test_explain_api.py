"""The explanation routes: diagnostics, stored explanations, contributions and partial
dependence of a model, the explain job, and ``LiveModels`` behind the synchronous ones."""

import dataclasses
import threading
import time
import uuid
from contextlib import closing
from dataclasses import dataclass

import numpy as np
import pytest

from api_helpers import add_user, bearer, connect, iris_csv, iris_frame, login, tiny_model, upload
from fione.auth.roles import Role
from fione.engine import explain
from fione.engine.artifact import MODEL_FILE, save_model
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.engine.families import CatBoost
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.models import explanations
from fione.models import service as models
from fione.models.live import Busy, LiveModels, Untrusted
from fione.models.service import ModelNotFound
from fione.projects import ingest
from fione.projects import service as projects

FEATURES = ["sepal length (cm)", "sepal width (cm)", "petal length (cm)", "petal width (cm)"]
COLUMN = "petal length (cm)"


@dataclass
class Env:
    client: object
    h: dict  # persona -> bearer headers
    p: str  # the owner's project, shared with "viewer" as viewer
    q: str  # the outsider's project
    d: int  # iris train dataset of p
    dq: int  # iris train dataset of q

    @property
    def storage(self):
        return self.client.app.state.storage

    def model(self, project=None, *, dataset_id=None, trusted=True, model=None):
        """A recorded copy of the tiny iris model (or ``model``) in ``project`` (p)."""
        model = model or tiny_model()
        project = project or self.p
        prefix = f"projects/{project}/models/{uuid.uuid4().hex}/"
        save_model(model, self.storage, prefix, self.client.app.state.secret, image_tag="test")
        with closing(connect(self.client)) as conn:
            return models.add_model(
                conn,
                project_id=project,
                dataset_id=dataset_id,
                job_id=None,
                name="iris model",
                model=model,
                storage_prefix=prefix,
                trusted=trusted,
            )


@pytest.fixture
def env(make_client):
    client = make_client()
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


def instances(rows=slice(0, 3)) -> list[dict]:
    return iris_frame()[FEATURES].iloc[rows].to_dict("records")


def contributions(env, model_id, body, persona="viewer"):
    return env.client.post(
        f"/api/v1/models/{model_id}/contributions", json=body, headers=env.h[persona]
    )


def pd_request(env, model_id, body, persona="viewer"):
    return env.client.post(
        f"/api/v1/models/{model_id}/partial-dependence", json=body, headers=env.h[persona]
    )


def explain_job(env, body, persona="owner", project=None):
    return env.client.post(
        f"/api/v1/projects/{project or env.p}/jobs/explain", json=body, headers=env.h[persona]
    )


# --- diagnostics and stored explanations -------------------------------------------------------


def test_diagnostics_null_for_a_phase1_model(env):
    old = env.model(model=dataclasses.replace(tiny_model(), diagnostics=None))
    r = env.client.get(f"/api/v1/models/{old.id}/diagnostics", headers=env.h["viewer"])
    assert r.status_code == 200, r.text
    assert r.json() == {"model_id": old.id, "diagnostics": None}

    new = env.model()
    assert new.diagnostics is not None
    r = env.client.get(f"/api/v1/models/{new.id}/diagnostics", headers=env.h["viewer"])
    assert r.json() == {"model_id": new.id, "diagnostics": new.diagnostics}


def explanation(env, model_id, persona="viewer") -> dict:
    r = env.client.get(f"/api/v1/models/{model_id}/explanations", headers=env.h[persona])
    assert r.status_code == 200, r.text
    assert set(r.json()) == {
        "model_id",
        "status",
        "job_id",
        "dataset_id",
        "computed_at",
        "explanation",
    }
    return r.json()


def test_explanations_follow_the_latest_job(env):
    record = env.model(dataset_id=env.d)
    none = {"status": "none", "job_id": None, "dataset_id": None, "computed_at": None}
    assert explanation(env, record.id) == {"model_id": record.id, **none, "explanation": None}

    r = explain_job(env, {"model_id": record.id})
    assert r.status_code == 201, r.text
    job = r.json()
    assert (job["kind"], job["status"], job["payload"]) == (
        "explain",
        "queued",
        {"model_id": record.id, "dataset_id": None},
    )
    got = explanation(env, record.id)
    assert (got["status"], got["job_id"], got["explanation"]) == ("queued", job["id"], None)

    payload = {"version": 1, "importance": [{"column": "<b>x</b>", "share": 0.4}]}
    with closing(connect(env.client)) as conn:
        store.claim_job(conn, job["id"], "token")
        explanations.save_explanation(conn, record.id, job["id"], env.d, payload)
        assert explanation(env, record.id)["status"] == "running"  # stored, still running
        store.finish_job(conn, job["id"], JobStatus.DONE)
    got = explanation(env, record.id)
    assert (got["status"], got["job_id"], got["dataset_id"]) == ("done", job["id"], env.d)
    assert got["explanation"] == payload and got["computed_at"] > 0

    # A rerun on another dataset: its status while it runs, the stored one meanwhile.
    rerun = explain_job(env, {"model_id": record.id, "dataset_id": env.d}).json()
    got = explanation(env, record.id)
    assert (got["status"], got["job_id"], got["explanation"]) == ("queued", rerun["id"], payload)
    with closing(connect(env.client)) as conn:
        store.claim_job(conn, rerun["id"], "token")
        store.finish_job(conn, rerun["id"], JobStatus.FAILED, message="boom")
    got = explanation(env, record.id)  # the failed rerun left the stored one
    assert (got["status"], got["job_id"], got["explanation"]) == ("done", job["id"], payload)

    other = env.model(dataset_id=env.d)  # no row: the latest job's status
    failed = explain_job(env, {"model_id": other.id}).json()
    with closing(connect(env.client)) as conn:
        store.claim_job(conn, failed["id"], "token")
        store.finish_job(conn, failed["id"], JobStatus.FAILED, message="boom")
    got = explanation(env, other.id)
    assert (got["status"], got["job_id"], got["explanation"]) == ("failed", failed["id"], None)


# --- contributions ------------------------------------------------------------------------------


def test_contributions_for_instances_are_additive(env):
    record = env.model()
    rows = instances(slice(48, 53))  # setosa and versicolor
    r = contributions(env, record.id, {"instances": rows})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"model_id", "outputs", "rows"}
    assert body["model_id"] == record.id
    assert body["outputs"] == ["setosa", "versicolor", "virginica"]
    proba = tiny_model().predict_proba(iris_frame()[FEATURES].iloc[48:53]).to_numpy()
    assert [row["row"] for row in body["rows"]] == [0, 1, 2, 3, 4]
    for row, expected in zip(body["rows"], proba, strict=True):
        assert set(row) == {"row", "prediction", "class_index", "bias", "contributions"}
        assert list(row["contributions"]) == FEATURES
        assert row["class_index"] == int(np.argmax(expected))
        total = row["bias"] + sum(row["contributions"].values())
        assert total == pytest.approx(row["prediction"], abs=1e-9)
        assert row["prediction"] == pytest.approx(expected[row["class_index"]], abs=1e-5)

    chosen = contributions(env, record.id, {"instances": rows, "class_index": 2}).json()
    for row, expected in zip(chosen["rows"], proba, strict=True):
        assert row["class_index"] == 2
        assert row["prediction"] == pytest.approx(expected[2], abs=1e-5)


def test_contributions_for_dataset_rows(env):
    record = env.model()
    r = contributions(env, record.id, {"dataset_id": env.d, "offset": 5, "limit": 3})
    assert r.status_code == 200, r.text
    rows = r.json()["rows"]
    assert [row["row"] for row in rows] == [5, 6, 7]
    expected = contributions(env, record.id, {"instances": instances(slice(5, 8))}).json()
    for got, want in zip(rows, expected["rows"], strict=True):
        assert got["contributions"] == pytest.approx(want["contributions"])
        assert got["prediction"] == pytest.approx(want["prediction"])

    default = contributions(env, record.id, {"dataset_id": env.d}).json()["rows"]
    assert [row["row"] for row in default] == list(range(10))
    past = contributions(env, record.id, {"dataset_id": env.d, "offset": 1000}).json()
    assert past["rows"] == []


@pytest.mark.parametrize(
    "body",
    [
        {"instances": instances(slice(0, 101))},
        {"instances": []},
        {"instances": instances(slice(0, 1)), "dataset_id": 1},
        {},
        {"dataset_id": 1, "limit": 101},
        {"dataset_id": 1, "limit": 0},
        {"dataset_id": 1, "offset": -1},
        {"instances": [{"sepal length (cm)": [1, 2]}]},
        {"instances": instances(slice(0, 1)), "class_index": True},
        {"instances": instances(slice(0, 1)), "nope": 1},
    ],
    ids=[
        "101 instances",
        "no instances",
        "both sources",
        "neither source",
        "limit 101",
        "limit 0",
        "negative offset",
        "a list value",
        "bool class_index",
        "unknown field",
    ],
)
def test_contributions_limits(env, body):
    record = env.model()
    if body.get("dataset_id") == 1:
        body = {**body, "dataset_id": env.d}
    r = contributions(env, record.id, body)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "invalid"


def test_contributions_refuse_rows_the_model_cannot_read(env):
    record = env.model()
    one = instances(slice(0, 2))
    del one[1][COLUMN]
    r = contributions(env, record.id, {"instances": one})
    assert (r.status_code, r.json()["code"]) == (422, "invalid")
    assert "instance 1" in r.json()["error"] and COLUMN in r.json()["error"]

    text = instances(slice(0, 1))
    text[0][COLUMN] = "<script>"
    r = contributions(env, record.id, {"instances": text})
    assert r.status_code == 422 and "must hold numbers" in r.json()["error"]

    r = contributions(env, record.id, {"instances": instances(slice(0, 1)), "class_index": 3})
    assert r.status_code == 422 and "class_index" in r.json()["error"]

    other = upload(env.client, env.p, b"a,b\n1,2\n", headers=env.h["owner"]).json()["id"]
    r = contributions(env, record.id, {"dataset_id": other})
    assert r.status_code == 422 and "lacks the model's columns" in r.json()["error"]


def test_a_dataset_of_another_project_is_not_found(env):
    record = env.model()
    for dataset in (env.dq, 999_999):
        for r in (
            contributions(env, record.id, {"dataset_id": dataset}),
            pd_request(env, record.id, {"column": COLUMN, "dataset_id": dataset}),
            explain_job(env, {"model_id": record.id, "dataset_id": dataset}),
        ):
            assert r.status_code == 404, r.text
            assert r.json() == {"error": "dataset not found", "code": "not_found"}


def test_regression_contributions_have_no_class_index(env):
    frame = iris_frame()
    config = TrainConfig(target=COLUMN, max_runtime_secs=10, max_models=1, nfolds=2)
    model = AutoML(config, lambda event: None).fit(frame.drop(columns="species"))
    record = env.model(model=model)
    rows = frame.drop(columns=["species", COLUMN]).iloc[:3].to_dict("records")
    body = contributions(env, record.id, {"instances": rows}).json()
    assert body["outputs"] == [COLUMN]
    expected = model.predict(frame.iloc[:3]).to_numpy()
    for row, want in zip(body["rows"], expected, strict=True):
        assert row["class_index"] is None
        assert row["bias"] + sum(row["contributions"].values()) == pytest.approx(want, abs=1e-5)


# --- partial dependence -------------------------------------------------------------------------


PD_FIELDS = {"column", "kind", "grid", "outputs", "average", "ice", "ice_output", "n_rows"}


def test_pd_one_column(env):
    record = env.model(dataset_id=env.d)
    r = pd_request(env, record.id, {"column": COLUMN})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == PD_FIELDS
    assert (body["column"], body["kind"], body["n_rows"]) == (COLUMN, "numeric", 150)
    assert body["outputs"] == ["setosa", "versicolor", "virginica"]
    with closing(connect(env.client)) as conn:
        dataset = projects.get_dataset(conn, env.d)
    background = ingest.read_dataset_spread(env.storage, dataset, 300, FEATURES)
    expected = explain.partial_dependence(tiny_model(), background, COLUMN)
    assert body["grid"] == expected.grid and len(body["grid"]) <= 20
    np.testing.assert_allclose(body["average"], expected.average)
    np.testing.assert_allclose(body["ice"], expected.ice)
    assert body["ice_output"] == expected.ice_output and len(body["ice"]) == 50

    small = {"column": COLUMN, "grid": 5, "rows": 40, "ice": 0, "class_index": 1}
    body = pd_request(env, record.id, small).json()
    assert len(body["grid"]) <= 5 and body["n_rows"] == 40
    assert (body["ice"], body["ice_output"]) == ([], 1)

    elsewhere = env.model()  # no training data: a dataset is chosen
    r = pd_request(env, elsewhere.id, {"column": COLUMN})
    assert (r.status_code, r.json()["error"]) == (422, "choose a dataset")
    r = pd_request(env, elsewhere.id, {"column": COLUMN, "dataset_id": env.d})
    assert r.status_code == 200 and set(r.json()) == PD_FIELDS


@pytest.mark.parametrize(
    "body",
    [
        {"column": COLUMN, "grid": 21},
        {"column": COLUMN, "grid": 1},
        {"column": COLUMN, "rows": 301},
        {"column": COLUMN, "rows": 0},
        {"column": COLUMN, "ice": 51},
        {"column": "x" * 501},
        {"column": ""},
        {"column": "nope"},
        {"column": COLUMN, "class_index": 3},
        {},
    ],
    ids=[
        "grid 21",
        "grid 1",
        "rows 301",
        "rows 0",
        "ice 51",
        "long column",
        "empty column",
        "unknown column",
        "class_index 3",
        "no column",
    ],
)
def test_pd_limits(env, body):
    record = env.model(dataset_id=env.d)
    r = pd_request(env, record.id, body)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "invalid"


# --- access ------------------------------------------------------------------------------------


def test_viewer_may_explain_but_not_recompute(env):
    record = env.model(dataset_id=env.d)
    assert contributions(env, record.id, {"instances": instances()}).status_code == 200
    assert pd_request(env, record.id, {"column": COLUMN}).status_code == 200
    r = explain_job(env, {"model_id": record.id}, persona="viewer")
    assert r.status_code == 403, r.text
    assert explain_job(env, {"model_id": record.id}).status_code == 201


def test_stranger_gets_404(env):
    record = env.model(dataset_id=env.d)
    get = env.client.get
    h = env.h["outsider"]
    for r in (
        get(f"/api/v1/models/{record.id}/diagnostics", headers=h),
        get(f"/api/v1/models/{record.id}/explanations", headers=h),
        contributions(env, record.id, {"instances": instances()}, persona="outsider"),
        pd_request(env, record.id, {"column": COLUMN}, persona="outsider"),
    ):
        assert r.status_code == 404, r.text
        assert r.json() == {"error": "model not found", "code": "not_found"}
    r = explain_job(env, {"model_id": record.id}, persona="outsider")
    assert (r.status_code, r.json()["error"]) == (404, "project not found")
    # The outsider's own project, the owner's model: not found there either.
    r = explain_job(env, {"model_id": record.id}, persona="outsider", project=env.q)
    assert (r.status_code, r.json()["error"]) == (404, "model not found")


def test_cookie_post_needs_csrf(env):
    record = env.model()
    c = env.client
    csrf = login(c, "viewer")
    url = f"/api/v1/models/{record.id}/contributions"
    r = c.post(url, json={"instances": instances()})
    assert (r.status_code, r.json()["code"]) == (403, "csrf")
    assert c.post(url, json={"instances": instances()}, headers={"X-CSRF-Token": csrf}).is_success
    r = c.post(f"/api/v1/projects/{env.p}/jobs/explain", json={"model_id": record.id})
    assert (r.status_code, r.json()["code"]) == (403, "csrf")


def test_untrusted_model_is_refused(env, monkeypatch):
    record = env.model(dataset_id=env.d, trusted=False)
    no_data = env.model(trusted=False)
    loads = []
    real = models.load_trained
    monkeypatch.setattr(models, "load_trained", lambda *a: loads.append(a) or real(*a))
    for r in (
        contributions(env, record.id, {"instances": instances()}),
        contributions(env, record.id, {"dataset_id": env.d}),
        pd_request(env, record.id, {"column": COLUMN}),
        # Refused before the dataset is looked at.
        contributions(env, record.id, {"dataset_id": env.dq}),
        pd_request(env, no_data.id, {"column": COLUMN}),
    ):
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "untrusted"
    assert loads == []
    assert explain_job(env, {"model_id": record.id}).status_code == 201


def test_a_broken_artifact_is_a_clear_error(env):
    record = env.model()
    key = record.storage_prefix + MODEL_FILE
    env.storage.put(key, env.storage.get(key) + b"x")
    r = contributions(env, record.id, {"instances": instances()})
    assert r.status_code == 409, r.text
    assert r.json() == {"error": "the model file failed verification", "code": "conflict"}
    gone = env.model()
    env.storage.delete_prefix(gone.storage_prefix)
    r = contributions(env, gone.id, {"instances": instances()})
    assert r.json() == {"error": "model not found", "code": "not_found"}


# --- LiveModels ---------------------------------------------------------------------------------


def test_busy_is_a_fast_503(env):
    record = env.model()
    live = LiveModels(env.storage, env.client.app.state.secret, wait_secs=0.1)
    env.client.app.state.live_models = live
    assert live.slot.acquire(timeout=1)
    try:
        start = time.monotonic()
        r = contributions(env, record.id, {"instances": instances()})
        assert time.monotonic() - start < 2
        assert r.status_code == 503, r.text
        assert r.json()["code"] == "busy" and r.headers["Retry-After"] == "5"
        r = pd_request(env, record.id, {"column": COLUMN, "dataset_id": env.d})
        assert r.status_code == 503
    finally:
        live.slot.release()
    assert contributions(env, record.id, {"instances": instances()}).status_code == 200


def test_live_models_lru_is_bounded(env):
    secret = env.client.app.state.secret
    first, second, third = (env.model() for _ in range(3))
    live = LiveModels(env.storage, secret)
    for record in (first, second, third):
        with live.use(record) as model:
            assert model.columns == FEATURES
        assert len(live) <= 2
    kept = live._models[(third.id, third.storage_prefix)][0]
    with live.use(third) as again:
        assert again is kept
    assert list(live._models) == [(r.id, r.storage_prefix) for r in (second, third)]

    size = env.storage.size(first.storage_prefix + MODEL_FILE)
    by_bytes = LiveModels(env.storage, secret, max_bytes=size + size // 2)
    for record in (first, second):
        with by_bytes.use(record):
            pass
    assert len(by_bytes) == 1  # two would pass the bytes

    small = LiveModels(env.storage, secret, max_bytes=size - 1)
    with small.use(first) as model:
        assert model.columns == FEATURES  # loaded and used
    assert len(small) == 0  # but not kept


def test_live_models_release_the_slot_on_errors(env, monkeypatch):
    record = env.model()
    live = LiveModels(env.storage, env.client.app.state.secret, wait_secs=0.1)
    with pytest.raises(RuntimeError), live.use(record):
        raise RuntimeError("the request failed")
    failing = env.model()
    monkeypatch.setattr(models, "load_trained", lambda *a: (_ for _ in ()).throw(OSError("x")))
    with pytest.raises(OSError), live.use(failing):
        pass
    with live.use(record):  # neither left the slot taken
        pass
    gone = env.model()
    env.storage.delete_prefix(gone.storage_prefix)
    with pytest.raises(ModelNotFound), live.use(gone):
        pass
    with live.use(record):
        pass


def test_live_models_refuse_untrusted_before_reading(env, monkeypatch):
    record = env.model(trusted=False)
    monkeypatch.setattr(env.storage, "size", lambda key: pytest.fail("read"))
    live = LiveModels(env.storage, env.client.app.state.secret)
    assert live.slot.acquire(timeout=1)  # not even the slot is waited for
    try:
        with pytest.raises(Untrusted), live.use(record):
            pass
    finally:
        live.slot.release()


def test_live_models_wait_then_give_up(env):
    record = env.model()
    live = LiveModels(env.storage, env.client.app.state.secret, wait_secs=0.2)
    assert live.slot.acquire(timeout=1)
    threading.Timer(0.05, live.slot.release).start()
    with live.use(record):  # the slot came free while waiting
        pass
    assert live.slot.acquire(timeout=1)
    try:
        start = time.monotonic()
        with pytest.raises(Busy), live.use(record):
            pass
        assert 0.15 < time.monotonic() - start < 2
    finally:
        live.slot.release()


def thread_counts(model) -> list:
    return [
        member.spec.n_jobs if isinstance(member.spec, CatBoost) else one.get_params()["n_jobs"]
        for member in model.members
        for one in member.models
    ]


def test_live_models_cap_prediction_threads(env, monkeypatch):
    record = env.model()
    assert max(thread_counts(tiny_model())) > 1  # trained on 4 threads
    monkeypatch.setattr(explain, "THREADS", 1)
    live = LiveModels(env.storage, env.client.app.state.secret)
    with live.use(record) as loaded:
        assert thread_counts(loaded) == [1] * len(thread_counts(loaded))
