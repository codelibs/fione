"""Training, prediction and module jobs through the SDK, against a running in-process server."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fione_sdk import Client, FioneError, JobFailed

from api_helpers import FAST_CONFIG, add_user, bearer, iris_frame

CONFIG = {k: v for k, v in FAST_CONFIG.items() if k != "target"}
SEPAL = "sepal length (cm)"


@pytest.fixture
def api(make_client):
    return make_client(start_runner=True)


@pytest.fixture(params=["full", "notebook"])
def fione(request):
    """A client with a full token and one with a notebook token: both run every call."""
    return request.getfixturevalue("sdk" if request.param == "full" else "notebook_sdk")


@pytest.fixture
def iris(fione):
    project = fione.create_project("p")
    dataset = fione.upload(project["id"], iris_frame().sample(frac=1, random_state=1), "iris")
    return project["id"], dataset["id"]


def test_train_wait_and_leaderboard(sdk):
    pid = sdk.create_project("p")["id"]
    dataset = sdk.upload(pid, iris_frame(), "iris")
    job = sdk.train(pid, dataset["id"], "species", name="iris model", **CONFIG)
    assert job.wait(timeout=120, poll=0.1) is job
    assert job.status == "done"
    model_id = job.result["model_id"]
    board = sdk.leaderboard(model_id)
    assert {"model", "cv_score"} <= set(board.columns) and len(board) >= 1
    models = sdk.models(pid)
    assert len(models) == 1 and models.loc[0, "name"] == "iris model"
    assert sdk.model(model_id)["target"] == "species"


def test_events_follow_ends_at_a_terminal_status(sdk):
    pid = sdk.create_project("p")["id"]
    dataset = sdk.upload(pid, iris_frame(), "iris")
    job = sdk.train(pid, dataset["id"], "species", **CONFIG)
    with ThreadPoolExecutor(1) as pool:  # a guard: following must end on its own
        events = pool.submit(lambda: list(job.events(follow=True))).result(timeout=120)
    assert events and events[-1]["type"] in {"finished", "stopped"}
    assert job.refresh().status == "done"
    assert list(job.events(after=events[-1]["id"])) == []


def test_predict_returns_rows_in_order_and_removes_its_input(fione, iris):
    pid, dataset_id = iris
    job = fione.train(pid, dataset_id, "species", **CONFIG).wait(timeout=120, poll=0.1)
    rows = iris_frame().iloc[[100, 0, 50, 1, 101]].drop(columns="species")
    out = fione.predict(pid, job.result["model_id"], rows, include_columns=[SEPAL], timeout=120)
    assert len(out) == 5 and "predict" in out.columns
    assert out[SEPAL].tolist() == rows[SEPAL].tolist()
    assert out["predict"].tolist()[1] == "setosa" and out["predict"].tolist()[0] == "virginica"
    assert not [d for d in fione.datasets(pid) if d["name"].startswith("sdk_predict_")]
    assert fione.job(job.id).status == "done"
    model_id = job.result["model_id"]
    assert {"model", "cv_score"} <= set(fione.leaderboard(model_id).columns)
    assert fione.models(pid)["id"].tolist() == [model_id]
    assert fione.model(model_id)["target"] == "species"


def test_cancel_raises_job_failed_cancelled(sdk):
    pid = sdk.create_project("p")["id"]
    dataset = sdk.upload(pid, iris_frame(), "iris")
    job = sdk.train(pid, dataset["id"], "species", **{**CONFIG, "max_runtime_secs": 60})
    job.cancel()
    with pytest.raises(JobFailed) as err:
        job.wait(timeout=60, poll=0.1)
    assert err.value.code == "cancelled" and err.value.job is job
    assert job.status == "cancelled"


def test_failed_job_raises_with_message(fione, iris):
    pid, dataset_id = iris
    with pytest.raises(FioneError) as refused:  # refused at submission
        fione.train(pid, dataset_id, "missing", **CONFIG)
    assert refused.value.status == 422
    job = fione.run_module(pid, "sort", dataset_id, {"column": "missing"})
    with pytest.raises(JobFailed) as err:  # failed at run time
        job.wait(timeout=60, poll=0.1)
    assert err.value.code == "failed" and "missing" in err.value.message
    assert err.value.job.status == "failed"


def test_run_module_returns_a_dataset(fione, iris):
    pid, dataset_id = iris
    assert "sort" in {m["id"] for m in fione.modules()}
    job = fione.run_module(pid, "sort", dataset_id, {"column": SEPAL}, name="sorted")
    job.wait(timeout=60, poll=0.1)
    frame = fione.read(pid, job.result["dataset_id"])
    assert len(frame) == 150 and frame[SEPAL].is_monotonic_increasing
    assert fione.dataset(pid, job.result["dataset_id"])["name"] == "sorted"


def test_wait_timeout(make_client, tmp_path):
    idle = make_client(tmp_path / "idle")  # no runner: a job stays queued
    client = Client(
        token=bearer(idle, add_user(idle, "idle").id)["Authorization"].removeprefix("Bearer "),
        http=idle,
    )
    pid = client.create_project("p")["id"]
    dataset = client.upload(pid, iris_frame(), "iris")
    job = client.train(pid, dataset["id"], "species", **CONFIG)
    with pytest.raises(TimeoutError):
        job.wait(timeout=0.01)
    assert job.refresh().status == "queued"
