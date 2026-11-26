"""The MCP workflow tools: follow and cancel jobs, create a project and upload a dataset inline,
each as the token's user with the access the REST routes ask for."""

import json
import logging
import re
import signal
import threading
import time
from contextlib import closing
from functools import cache
from urllib.parse import urlsplit

import pytest
from test_mcp import bearer, call, iris_dataset, rpc
from test_mcp_actions import CONFIG, writes  # noqa: F401  (the fixture)

from api_helpers import (
    ASSISTANT_OFF,
    FAST_CONFIG,
    add_user,
    connect,
    iris_frame,
    store_model,
    tiny_model,
)
from fione.auth.roles import ProjectAccess, Role
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.jobs import builtin, store, worker  # noqa: F401  (builtin registers the handlers)
from fione.predict import batch_predict
from fione.projects import service as projects
from fione.tools.workflow import INLINE_UPLOAD_MAX_BYTES, MAX_PREDICT_ROWS

NOT_ALLOWED = "not found or not allowed"


def queue(client, headers, project, dataset) -> int:
    result = call(
        client,
        headers,
        "start_training",
        {"project_id": project.id, "dataset_id": dataset.id, "config": CONFIG},
    )
    assert result["isError"] is False, result
    return result["structuredContent"]["job_id"]


def finish(client, job_id, status=store.JobStatus.DONE, **kwargs):
    with closing(connect(client)) as conn:
        assert store.claim_job(conn, job_id, "t")
        assert store.finish_job(conn, job_id, status, **kwargs)


def status_of(client, job_id):
    with closing(connect(client)) as conn:
        return store.get_job(conn, job_id).status


def text(result) -> str:
    return result["content"][0]["text"]


def test_get_job_returns_status_and_result(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    job_id = queue(client, headers, project, dataset)
    out = call(client, headers, "get_job", {"job_id": job_id})
    assert out["isError"] is False, out
    job = out["structuredContent"]
    assert job["job_id"] == job_id and job["kind"] == "automl" and job["status"] == "queued"
    assert job["project_id"] == project.id and job["result"] is None
    assert job["started_at"] is None and job["finished_at"] is None
    finish(client, job_id, result={"model_id": 7, "key": "projects/x/models/7.zip"})
    done = call(client, headers, "get_job", {"job_id": job_id})["structuredContent"]
    assert done["status"] == "done" and done["result"] == {"model_id": 7}
    assert done["finished_at"] is not None


def test_a_failure_message_is_not_shown(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    job_id = queue(client, headers, project, dataset)
    finish(client, job_id, store.JobStatus.FAILED, message="class 'setosa' has one row")
    job = call(client, headers, "get_job", {"job_id": job_id})["structuredContent"]
    assert job["status"] == "failed" and job["message"] is None
    assert job["message_hidden"] is True and "setosa" not in str(job)


def test_wait_for_job_returns_when_terminal(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    job_id = queue(client, headers, project, dataset)
    finish(client, job_id, result={"model_id": 3})
    out = call(client, headers, "wait_for_job", {"job_id": job_id, "timeout_secs": 5})
    job = out["structuredContent"]
    assert job["done"] is True and job["status"] == "done" and job["waited_secs"] < 1
    assert job["result"] == {"model_id": 3}


def test_wait_for_job_notices_a_job_that_finishes_while_waiting(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    job_id = queue(client, headers, project, dataset)
    timer = threading.Timer(0.6, finish, args=(client, job_id), kwargs={"result": {"model_id": 5}})
    timer.start()
    try:
        out = call(client, headers, "wait_for_job", {"job_id": job_id, "timeout_secs": 10})
    finally:
        timer.join()
    job = out["structuredContent"]
    assert job["done"] is True and job["status"] == "done" and job["result"] == {"model_id": 5}
    assert 0.5 <= job["waited_secs"] < 5


def test_wait_for_job_times_out_with_current_state(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    job_id = queue(client, headers, project, dataset)
    out = call(client, headers, "wait_for_job", {"job_id": job_id, "timeout_secs": 1})
    job = out["structuredContent"]
    assert job["done"] is False and job["status"] == "queued" and job["waited_secs"] >= 1


def test_wait_for_job_caps_timeout(writes):  # noqa: F811
    client, user = writes
    headers = bearer(client, user)
    out = call(client, headers, "wait_for_job", {"job_id": 1, "timeout_secs": 99})
    assert out["isError"] is True and "15" in text(out) and "timeout_secs" in text(out)
    zero = call(client, headers, "wait_for_job", {"job_id": 1, "timeout_secs": 0})
    assert zero["isError"] is True


def test_job_of_unreadable_project_is_not_allowed(writes):  # noqa: F811
    client, owner = writes
    project, dataset = iris_dataset(client, owner)
    job_id = queue(client, bearer(client, owner), project, dataset)
    stranger = bearer(client, add_user(client, "st", Role.EDITOR))
    missing = call(client, stranger, "get_job", {"job_id": 99999})
    assert missing["isError"] is True and text(missing) == NOT_ALLOWED
    for name in ("get_job", "wait_for_job", "cancel_job"):
        other = call(client, stranger, name, {"job_id": job_id})
        assert other["isError"] is True and other["content"] == missing["content"], name
    assert status_of(client, job_id) == store.JobStatus.QUEUED


def test_list_jobs_filters_by_project_and_status(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    first = queue(client, headers, project, dataset)
    second = queue(client, headers, project, dataset)
    finish(client, first)
    with closing(connect(client)) as conn:
        other = projects.create_project(conn, user, "Q")
        store.enqueue(conn, "automl", other.id, user.id, {})
    everything = call(client, headers, "list_jobs")["structuredContent"]["jobs"]
    assert len(everything) == 3
    of_project = call(client, headers, "list_jobs", {"project_id": project.id})
    assert [j["job_id"] for j in of_project["structuredContent"]["jobs"]] == [second, first]
    queued = call(client, headers, "list_jobs", {"project_id": project.id, "status": "queued"})
    jobs = queued["structuredContent"]["jobs"]
    assert [j["job_id"] for j in jobs] == [second] and jobs[0]["status"] == "queued"
    assert call(client, headers, "list_jobs", {"status": "bogus"})["isError"] is True
    stranger = bearer(client, add_user(client, "st", Role.EDITOR))
    assert call(client, stranger, "list_jobs")["structuredContent"]["jobs"] == []
    hidden = call(client, stranger, "list_jobs", {"project_id": project.id})
    missing = call(client, stranger, "list_jobs", {"project_id": "zz"})
    assert hidden["isError"] is True and text(hidden) == NOT_ALLOWED
    assert missing["content"] == hidden["content"]


def test_cancel_job_cancels_queued_and_refuses_finished(writes):  # noqa: F811
    client, owner = writes
    project, dataset = iris_dataset(client, owner)
    headers = bearer(client, owner)
    viewer = add_user(client, "vi", Role.EDITOR)
    with closing(connect(client)) as conn:
        projects.share_project(conn, owner, project.id, "vi", ProjectAccess.VIEWER)
    queued, finished = (queue(client, headers, project, dataset) for _ in range(2))
    seen = call(client, bearer(client, viewer), "cancel_job", {"job_id": queued})
    assert seen["isError"] is True and "write access" in text(seen)
    assert call(client, bearer(client, viewer), "get_job", {"job_id": queued})["isError"] is False
    out = call(client, headers, "cancel_job", {"job_id": queued})
    assert out["isError"] is False, out
    assert out["structuredContent"]["status"] == "cancelled"
    finish(client, finished)
    done = call(client, headers, "cancel_job", {"job_id": finished})
    assert done["isError"] is True and text(done) == "the job has already finished"
    assert status_of(client, queued) == store.JobStatus.CANCELLED
    assert status_of(client, finished) == store.JobStatus.DONE


@pytest.mark.parametrize("name", ["get_job", "wait_for_job", "cancel_job"])
def test_job_id_is_required(writes, name):  # noqa: F811
    client, user = writes
    out = call(client, bearer(client, user), name, {})
    assert out["isError"] is True and "job_id" in text(out)


def upload(client, headers, project_id, csv_text, name="d", type="train"):
    return call(
        client,
        headers,
        "upload_dataset",
        {"project_id": project_id, "name": name, "type": type, "csv_text": csv_text},
    )


def one_line(result) -> str:
    assert result["isError"] is True, result
    message = text(result)
    assert "\n" not in message and "Traceback" not in message and message.strip()
    return message


def new_project(client, user) -> str:
    with closing(connect(client)) as conn:
        return projects.create_project(conn, user, "P").id


def test_create_project_owns_it(writes):  # noqa: F811
    client, user = writes
    out = call(client, bearer(client, user), "create_project", {"name": "  Sales  "})
    assert out["isError"] is False, out
    created = out["structuredContent"]
    assert set(created) - {"_data_notice"} == {"project_id", "name"} and created["name"] == "Sales"
    with closing(connect(client)) as conn:
        project = projects.require_project(conn, created["project_id"])
        assert project.owner_id == user.id and project.name == "Sales"
        assert [p.id for p in projects.list_projects(conn, user)] == [project.id]


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_create_project_refuses_a_bad_name(writes, name):  # noqa: F811
    client, user = writes
    out = call(client, bearer(client, user), "create_project", {"name": name})
    one_line(out)
    with closing(connect(client)) as conn:
        assert projects.list_projects(conn, user) == []


def test_upload_dataset_ingests_csv(writes):  # noqa: F811
    client, user = writes
    headers = bearer(client, user)
    project_id = new_project(client, user)
    csv_text = iris_frame().to_csv(index=False)
    out = upload(client, headers, project_id, csv_text, name="  iris  ")
    assert out["isError"] is False, out
    dataset = out["structuredContent"]
    assert dataset["name"] == "iris" and dataset["type"] == "train"
    assert dataset["n_rows"] == 150 and dataset["n_cols"] == len(iris_frame().columns)
    assert [c["name"] for c in dataset["schema"]] == list(iris_frame().columns)
    assert all(set(c) == {"name", "type"} for c in dataset["schema"])
    assert "setosa" not in str(dataset)  # no cell values
    listed = call(client, headers, "list_datasets", {"project_id": project_id})
    (entry,) = listed["structuredContent"]["datasets"]
    assert entry["id"] == dataset["id"] and entry["n_rows"] == 150


def test_upload_over_512_kib_names_create_upload_url(writes):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    csv_text = "a\n" + "1\n" * (INLINE_UPLOAD_MAX_BYTES // 2)  # just over, and under the body cap
    assert len(csv_text.encode()) == INLINE_UPLOAD_MAX_BYTES + 2
    out = upload(client, bearer(client, user), project_id, csv_text)
    assert "create_upload_url" in one_line(out)
    with closing(connect(client)) as conn:
        assert projects.list_datasets(conn, project_id) == []


def test_upload_limit_is_in_bytes(writes):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    csv_text = "列\n" + "あ\n" * 200_000
    assert len(csv_text) < INLINE_UPLOAD_MAX_BYTES < len(csv_text.encode())
    out = upload(client, bearer(client, user), project_id, csv_text)
    assert "create_upload_url" in one_line(out)
    with closing(connect(client)) as conn:
        assert projects.list_datasets(conn, project_id) == []


def test_upload_just_under_the_limit_is_accepted(writes):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    row = "1\n"
    csv_text = "a\n" + row * ((INLINE_UPLOAD_MAX_BYTES - 2) // len(row))
    assert len(csv_text.encode()) <= INLINE_UPLOAD_MAX_BYTES
    out = upload(client, bearer(client, user), project_id, csv_text)
    assert out["isError"] is False, out


@pytest.mark.parametrize(
    ("csv_text", "message"),
    [
        ("", "empty file"),
        ("   \n\n", "empty file"),
        ("a,b\n", "no data rows"),
        ("a,b\n1,2\n3,SECRET,5\n", "could not parse the CSV: a row has 3 fields, the header 2"),
        ('a,b\n1,2\n"SECRET\n', "could not parse the CSV: a row has 1 fields, the header 2"),
    ],
)
def test_upload_bad_csv_is_one_line(writes, csv_text, message):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    out = upload(client, bearer(client, user), project_id, csv_text)
    assert one_line(out) == message
    with closing(connect(client)) as conn:
        assert projects.list_datasets(conn, project_id) == []


def test_upload_text_that_is_not_unicode_is_one_line(writes):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    arguments = {"project_id": project_id, "name": "d", "type": "train", "csv_text": "SECRET"}
    body = json.dumps(rpc("tools/call", {"name": "upload_dataset", "arguments": arguments}))
    # the JSON escape of a lone surrogate, which a client's JSON library can send
    body = body.replace("SECRET", "a\\ud800")
    headers = bearer(client, user) | {"Content-Type": "application/json"}
    r = client.post("/mcp", content=body, headers=headers)
    assert r.status_code == 200, r.text
    assert "not valid text" in one_line(r.json()["result"])


@pytest.mark.parametrize(
    ("csv_text", "names"),
    [
        ("\ufeffa,b\n1,2\n", ["a", "b"]),  # a BOM is not part of the first name
        ("a,a,\n1,2,3\n", ["a", "a_2", "column_3"]),  # duplicate and empty names
        ("名前,値\nあ,1\n", ["名前", "値"]),
    ],
)
def test_upload_odd_headers_are_made_usable(writes, csv_text, names):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    out = upload(client, bearer(client, user), project_id, csv_text)
    assert out["isError"] is False, out
    assert [c["name"] for c in out["structuredContent"]["schema"]] == names


def test_upload_needs_write_access(writes):  # noqa: F811
    client, owner = writes
    project_id = new_project(client, owner)
    viewer = add_user(client, "vi", Role.EDITOR)
    stranger = add_user(client, "st", Role.EDITOR)
    with closing(connect(client)) as conn:
        projects.share_project(conn, owner, project_id, "vi", ProjectAccess.VIEWER)
    csv_text = "a\n1\n"
    seen = upload(client, bearer(client, viewer), project_id, csv_text)
    assert "write access" in one_line(seen)
    hidden = upload(client, bearer(client, stranger), project_id, csv_text)
    missing = upload(client, bearer(client, stranger), "no-such-project", csv_text)
    assert text(hidden) == NOT_ALLOWED and missing["content"] == hidden["content"]
    with closing(connect(client)) as conn:
        assert projects.list_datasets(conn, project_id) == []


@pytest.mark.parametrize("type_", ["", "TRAIN", "validation", "predict "])
def test_upload_type_must_be_train_test_predict(writes, type_):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    out = upload(client, bearer(client, user), project_id, "a\n1\n", type=type_)
    assert "type" in one_line(out)
    with closing(connect(client)) as conn:
        assert projects.list_datasets(conn, project_id) == []


@pytest.mark.parametrize("type_", ["train", "test", "predict"])
def test_upload_takes_each_type(writes, type_):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    out = upload(client, bearer(client, user), project_id, "a\n1\n", type=type_)
    assert out["structuredContent"]["type"] == type_


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_upload_name_is_checked(writes, name):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    out = upload(client, bearer(client, user), project_id, "a\n1\n", name=name)
    one_line(out)
    with closing(connect(client)) as conn:
        assert projects.list_datasets(conn, project_id) == []


def test_upload_of_a_wide_csv_has_a_bounded_result(writes):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    names = [f"column_{i}" for i in range(5000)]
    csv_text = ",".join(names) + "\n" + ",".join("1" for _ in names) + "\n"
    out = upload(client, bearer(client, user), project_id, csv_text)
    assert out["isError"] is False, out
    assert len(text(out).encode()) <= 32 * 1024
    dataset = out["structuredContent"]
    assert dataset["n_cols"] == 5000 and dataset["truncated"] is True
    assert dataset["truncated_lists"] == ["schema"]


def upload_url(client, headers, project_id, name="big", type="train"):
    return call(
        client, headers, "create_upload_url", {"project_id": project_id, "name": name, "type": type}
    )


def test_create_upload_url_returns_absolute_url_and_works_end_to_end(writes):  # noqa: F811
    client, user = writes
    headers = bearer(client, user)
    project_id = new_project(client, user)
    out = upload_url(client, headers, project_id, name="  big  ")
    assert out["isError"] is False, out
    result = out["structuredContent"]
    assert set(result) - {"_data_notice"} == {"url", "method", "expires_in", "example"}
    assert result["method"] == "PUT" and result["expires_in"] == 900
    assert result["url"].startswith(f"{client.base_url}/api/v1/uploads/")
    assert result["example"] == f"curl -T file.csv '{result['url']}'"
    path = urlsplit(result["url"]).path
    r = client.put(path, content=iris_frame().to_csv(index=False).encode())
    assert r.status_code == 201, r.text
    listed = call(client, headers, "list_datasets", {"project_id": project_id})
    (entry,) = listed["structuredContent"]["datasets"]
    assert entry["id"] == r.json()["id"] and entry["n_rows"] == 150 and entry["name"] == "big"
    assert client.put(path, content=b"a\n1\n").status_code == 404


def test_create_upload_url_uses_public_url_when_set(make_client):
    client = make_client(
        mcp_enabled=True, mcp_write_enabled=True, public_url="https://fione.example.com"
    )
    user = add_user(client, "ed", Role.EDITOR)
    project_id = new_project(client, user)
    out = upload_url(client, bearer(client, user), project_id)
    url = out["structuredContent"]["url"]
    assert url.startswith("https://fione.example.com/api/v1/uploads/")


def test_each_upload_url_is_new(writes):  # noqa: F811
    client, user = writes
    headers = bearer(client, user)
    project_id = new_project(client, user)
    urls = {upload_url(client, headers, project_id)["structuredContent"]["url"] for _ in range(2)}
    assert len(urls) == 2


def test_create_upload_url_needs_write_access(writes):  # noqa: F811
    client, owner = writes
    project_id = new_project(client, owner)
    viewer = add_user(client, "vi", Role.EDITOR)
    stranger = add_user(client, "st", Role.EDITOR)
    with closing(connect(client)) as conn:
        projects.share_project(conn, owner, project_id, "vi", ProjectAccess.VIEWER)
    assert "write access" in one_line(upload_url(client, bearer(client, viewer), project_id))
    hidden = upload_url(client, bearer(client, stranger), project_id)
    missing = upload_url(client, bearer(client, stranger), "no-such-project")
    assert text(hidden) == NOT_ALLOWED and missing["content"] == hidden["content"]
    with closing(connect(client)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM upload_tokens").fetchone()[0] == 0


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_create_upload_url_name_is_checked(writes, name):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    one_line(upload_url(client, bearer(client, user), project_id, name=name))


def test_create_upload_url_type_must_be_train_test_predict(writes):  # noqa: F811
    client, user = writes
    project_id = new_project(client, user)
    out = upload_url(client, bearer(client, user), project_id, type="model")
    assert out["isError"] is True


# --- predict and get_predictions ---------------------------------------------------------------

FEATURES = ["sepal length (cm)", "sepal width (cm)", "petal length (cm)", "petal width (cm)"]
CLASSES = ["setosa", "versicolor", "virginica"]
PREDICTION_COLUMNS = ["predict", *(f"p_{c}" for c in CLASSES)]


def iris_rows(picked) -> list[dict]:
    return iris_frame()[FEATURES].iloc[picked].to_dict("records")


@cache
def colour_model():
    """A classifier that also reads a text column (``colour``)."""
    frame = iris_frame()
    frame["colour"] = [("red", "green", "blue")[i % 3] for i in range(len(frame))]
    return AutoML(TrainConfig(**FAST_CONFIG), lambda event: None).fit(frame)


def add_model(client, project_id, **kwargs) -> int:
    with closing(connect(client)) as conn:
        secret = client.app.state.secret
        return store_model(conn, client.app.state.storage, secret, project_id, **kwargs).id


def predict(client, headers, project_id, model_id, rows):
    return call(
        client, headers, "predict", {"project_id": project_id, "model_id": model_id, "rows": rows}
    )


def run_batch(client, headers, project_id, model_id, dataset_id, **extra) -> int:
    """Queue a batch prediction through MCP and run its job here; the result dataset's id."""
    arguments = {"project_id": project_id, "model_id": model_id, "dataset_id": dataset_id}
    out = call(client, headers, "start_batch_predict", {**arguments, **extra})
    assert out["isError"] is False, out
    job_id = out["structuredContent"]["job_id"]
    before = signal.getsignal(signal.SIGTERM)
    try:
        with closing(connect(client)) as conn:
            assert store.claim_job(conn, job_id, "t")
            worker._run(conn, store.get_job(conn, job_id), client.app.state.settings)
            job = store.get_job(conn, job_id)
    finally:
        signal.signal(signal.SIGTERM, before)
    assert job.status == store.JobStatus.DONE, job.message
    return job.result["dataset_id"]


def get_predictions(client, headers, project_id, dataset_id, **extra):
    return call(
        client,
        headers,
        "get_predictions",
        {"project_id": project_id, "dataset_id": dataset_id, **extra},
    )


def test_predict_returns_one_prediction_per_row_in_order(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    picked = [149, 0, 75, 100, 3]
    out = predict(client, bearer(client, user), project.id, model_id, iris_rows(picked))
    assert out["isError"] is False, out
    predictions = out["structuredContent"]["predictions"]
    expected = batch_predict(tiny_model(), iris_frame()[FEATURES].iloc[picked], [])
    assert [p["predict"] for p in predictions] == expected["predict"].tolist()
    assert predictions[0]["predict"] == "virginica" and predictions[1]["predict"] == "setosa"
    for got, want in zip(predictions, expected.to_dict("records"), strict=True):
        assert list(got) == PREDICTION_COLUMNS
        assert got["p_setosa"] == pytest.approx(want["p_setosa"])
        assert sum(got[f"p_{c}"] for c in CLASSES) == pytest.approx(1.0)


def test_predict_does_not_echo_inputs(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    rows = iris_rows([0, 1])
    rows[0]["sepal length (cm)"] = 5.123456
    out = predict(client, bearer(client, user), project.id, model_id, rows)
    assert out["isError"] is False, out
    shown = json.dumps(out["structuredContent"])
    assert "5.123456" not in shown and "sepal" not in shown
    assert set(out["structuredContent"]) == {"_data_notice", "predictions"}


def test_predict_ignores_keys_the_model_does_not_read(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    rows = [{**row, "extra": "x"} for row in iris_rows([0, 1])]
    out = predict(client, bearer(client, user), project.id, model_id, rows)
    assert out["isError"] is False, out
    assert len(out["structuredContent"]["predictions"]) == 2


def test_predict_missing_column_names_the_column_only(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    rows = iris_rows([0, 1])
    rows[1]["sepal length (cm)"] = 7.654321
    del rows[1]["petal width (cm)"]
    message = one_line(predict(client, bearer(client, user), project.id, model_id, rows))
    assert "row 1" in message and "petal width (cm)" in message
    assert "7.654321" not in message and "5.1" not in message


def test_predict_unseen_category_and_blank_value_do_not_fail_the_call(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id, model=colour_model())
    rows = [{**row, "colour": "red"} for row in iris_rows([0, 1, 2, 3])]
    rows[1]["colour"] = "ultraviolet-never-seen"
    rows[2]["colour"] = None
    rows[3]["petal width (cm)"] = ""
    rows[3]["colour"] = ""
    out = predict(client, bearer(client, user), project.id, model_id, rows)
    assert out["isError"] is False, out
    assert len(out["structuredContent"]["predictions"]) == 4
    assert "ultraviolet" not in json.dumps(out["structuredContent"])


def test_predict_text_in_a_number_column_is_refused_in_one_line(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    rows = iris_rows([0, 1])
    rows[1]["petal width (cm)"] = "wide"
    message = one_line(predict(client, bearer(client, user), project.id, model_id, rows))
    assert "petal width (cm)" in message
    rows[1]["petal width (cm)"] = True
    flagged = one_line(predict(client, bearer(client, user), project.id, model_id, rows))
    assert "row 1" in flagged and "petal width (cm)" in flagged


@pytest.mark.parametrize("value", [[1], {"a": 1}])
def test_predict_cell_values_must_be_scalars(writes, value):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    rows = iris_rows([0])
    rows[0]["petal width (cm)"] = value
    assert "row 0" in one_line(predict(client, bearer(client, user), project.id, model_id, rows))


def test_predict_needs_rows_that_are_objects(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    headers = bearer(client, user)
    assert "at least 1" in one_line(predict(client, headers, project.id, model_id, []))
    assert "'rows'" in one_line(predict(client, headers, project.id, model_id, [{}, 5]))
    assert "row 0: missing columns" in one_line(
        predict(client, headers, project.id, model_id, [{}])
    )


def test_predict_over_1000_rows_refused(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    rows = iris_rows([0]) * 1001
    assert "1000" in one_line(predict(client, bearer(client, user), project.id, model_id, rows))


def test_predict_refuses_a_result_over_32_kib_naming_the_rows_that_fit(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    headers = bearer(client, user)
    message = one_line(
        predict(client, headers, project.id, model_id, iris_rows([0]) * MAX_PREDICT_ROWS)
    )
    assert "start_batch_predict" in message and "32 KiB" in message
    fitting = int(re.search(r"send about (\d+) rows", message)[1])
    assert 100 < fitting < MAX_PREDICT_ROWS
    out = predict(client, headers, project.id, model_id, iris_rows([0]) * fitting)
    assert out["isError"] is False, out
    assert len(text(out).encode()) <= 32 * 1024


def test_predict_a_batch_that_fits_returns_every_row_in_order(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    picked = [0, 100, 50, 149] * 50
    out = predict(client, bearer(client, user), project.id, model_id, iris_rows(picked))
    assert out["isError"] is False, out
    result = out["structuredContent"]
    assert "truncated" not in result and "truncated_lists" not in result
    expected = batch_predict(tiny_model(), iris_frame()[FEATURES].iloc[picked], [])
    assert [p["predict"] for p in result["predictions"]] == expected["predict"].tolist()


def test_predict_busy_model_slot_is_a_toolerror(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    live = client.app.state.live_models
    live.wait_secs = 0.05
    assert live.slot.acquire(timeout=1)
    try:
        busy = predict(client, bearer(client, user), project.id, model_id, iris_rows([0]))
    finally:
        live.slot.release()
    assert "busy" in one_line(busy)
    ok = predict(client, bearer(client, user), project.id, model_id, iris_rows([0]))
    assert ok["isError"] is False


def test_predict_untrusted_model_is_refused(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    model_id = add_model(client, project.id)
    with closing(connect(client)) as conn:
        conn.execute("UPDATE models SET trusted = 0 WHERE id = ?", (model_id,))
    message = one_line(predict(client, bearer(client, user), project.id, model_id, iris_rows([0])))
    assert "start_batch_predict" in message


def test_predict_follows_read_access_and_the_model_project(writes):  # noqa: F811
    client, owner = writes
    project, _ = iris_dataset(client, owner)
    model_id = add_model(client, project.id)
    viewer = add_user(client, "vi", Role.EDITOR)
    stranger = add_user(client, "st", Role.EDITOR)
    with closing(connect(client)) as conn:
        projects.share_project(conn, owner, project.id, "vi", ProjectAccess.VIEWER)
        other = projects.create_project(conn, owner, "Q").id
    rows = iris_rows([0])
    assert predict(client, bearer(client, viewer), project.id, model_id, rows)["isError"] is False
    hidden = predict(client, bearer(client, stranger), project.id, model_id, rows)
    missing = predict(client, bearer(client, stranger), project.id, 99999, rows)
    wrong = predict(client, bearer(client, owner), other, model_id, rows)
    for refused in (hidden, missing, wrong):
        assert refused["isError"] is True and text(refused) == NOT_ALLOWED


def test_get_predictions_pages_prediction_columns_only(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    model_id = add_model(client, project.id)
    result = run_batch(
        client, headers, project.id, model_id, dataset.id, include_columns=["sepal length (cm)"]
    )
    with closing(connect(client)) as conn:
        names = [name for name, _ in projects.get_dataset(conn, result).schema]
    assert names[: len(PREDICTION_COLUMNS)] == PREDICTION_COLUMNS and "sepal length (cm)" in names
    out = get_predictions(client, headers, project.id, result, offset=2, limit=3)
    assert out["isError"] is False, out
    page = out["structuredContent"]
    assert page["columns"] == PREDICTION_COLUMNS
    assert page["offset"] == 2 and page["n_rows"] == 150 and len(page["rows"]) == 3
    assert "truncated" not in page and "sepal length (cm)" not in json.dumps(page)
    expected = batch_predict(tiny_model(), iris_frame()[FEATURES].iloc[2:5], [])
    assert [row[0] for row in page["rows"]] == expected["predict"].tolist()
    assert page["rows"][0][1] == pytest.approx(expected["p_setosa"].iloc[0])
    first = get_predictions(client, headers, project.id, result)["structuredContent"]
    assert first["offset"] == 0 and len(first["rows"]) == 100


def test_get_predictions_offset_past_end_is_empty_not_error(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    result = run_batch(client, headers, project.id, add_model(client, project.id), dataset.id)
    out = get_predictions(client, headers, project.id, result, offset=150)
    assert out["isError"] is False, out
    page = out["structuredContent"]
    assert page["rows"] == [] and page["columns"] == PREDICTION_COLUMNS and page["n_rows"] == 150
    far = get_predictions(client, headers, project.id, result, offset=10**9)
    assert far["isError"] is False and far["structuredContent"]["rows"] == []


def test_get_predictions_result_is_under_32_kib(writes):  # noqa: F811
    client, user = writes
    project, _ = iris_dataset(client, user)
    headers = bearer(client, user)
    frame = iris_frame()
    big = frame.loc[frame.index.repeat(10)].to_csv(index=False)
    uploaded = upload(client, headers, project.id, big, name="big", type="predict")
    assert uploaded["isError"] is False, uploaded
    dataset_id = uploaded["structuredContent"]["id"]
    result = run_batch(client, headers, project.id, add_model(client, project.id), dataset_id)
    out = get_predictions(client, headers, project.id, result, limit=1000)
    assert out["isError"] is False, out
    assert len(text(out).encode()) <= 32 * 1024
    page = out["structuredContent"]
    assert page["truncated"] is True and 0 < len(page["rows"]) < 1000
    assert page["columns"] == PREDICTION_COLUMNS and page["n_rows"] == 1500
    shown = len(page["rows"])
    follow = get_predictions(client, headers, project.id, result, offset=shown, limit=5)
    assert follow["structuredContent"]["offset"] == shown
    assert len(follow["structuredContent"]["rows"]) == 5


def test_get_predictions_of_non_result_dataset_refused(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    assert "batch prediction" in one_line(get_predictions(client, headers, project.id, dataset.id))
    uploaded = upload(client, headers, project.id, "a,b\n1,2\n", name="p", type="predict")
    plain = get_predictions(client, headers, project.id, uploaded["structuredContent"]["id"])
    assert "batch prediction" in one_line(plain)


def test_get_predictions_follows_read_access_and_the_project(writes):  # noqa: F811
    client, owner = writes
    project, dataset = iris_dataset(client, owner)
    headers = bearer(client, owner)
    result = run_batch(client, headers, project.id, add_model(client, project.id), dataset.id)
    viewer = add_user(client, "vi", Role.EDITOR)
    stranger = add_user(client, "st", Role.EDITOR)
    with closing(connect(client)) as conn:
        projects.share_project(conn, owner, project.id, "vi", ProjectAccess.VIEWER)
        other = projects.create_project(conn, owner, "Q").id
    seen = get_predictions(client, bearer(client, viewer), project.id, result)
    assert seen["isError"] is False
    hidden = get_predictions(client, bearer(client, stranger), project.id, result)
    missing = get_predictions(client, bearer(client, stranger), project.id, 99999)
    wrong = get_predictions(client, headers, other, result)
    for refused in (hidden, missing, wrong):
        assert refused["isError"] is True and text(refused) == NOT_ALLOWED


def test_get_predictions_when_the_model_is_gone_says_so(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    model_id = add_model(client, project.id)
    result = run_batch(client, headers, project.id, model_id, dataset.id)
    with closing(connect(client)) as conn:
        conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
    assert "model" in one_line(get_predictions(client, headers, project.id, result))


def test_get_predictions_when_the_file_is_gone_says_so(writes):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    model_id = add_model(client, project.id)
    result = run_batch(client, headers, project.id, model_id, dataset.id)
    with closing(connect(client)) as conn:
        client.app.state.storage.delete(projects.get_dataset(conn, result).key)
    message = one_line(get_predictions(client, headers, project.id, result))
    assert "gone" in message and message != NOT_ALLOWED


def test_the_log_line_has_no_cell_values(writes, caplog):  # noqa: F811
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    model_id = add_model(client, project.id)
    rows = iris_rows([0, 1])
    rows[0]["note"] = "ssn-123-45-6789"
    csv_text = "name,salary\nalice-cell,90000\n"
    with caplog.at_level(logging.INFO, logger="fione.tools"):
        up = upload(client, headers, project.id, csv_text, name="kept-name")
        out = predict(client, headers, project.id, model_id, rows)
    assert up["isError"] is False and out["isError"] is False
    lines = [r.getMessage() for r in caplog.records if r.name == "fione.tools"]
    log = "\n".join(lines)
    assert "tool=upload_dataset" in log and "tool=predict" in log and "kept-name" in log
    assert "<2 items>" in log and f"<{len(csv_text)} chars>" in log
    for value in ("alice-cell", "salary", "90000", "ssn-123-45-6789", "5.1"):
        assert value not in log


def test_an_ai_tool_trains_and_predicts_without_the_assistant(make_client, monkeypatch):
    """The flow of an MCP client such as Claude Code, with real workers and no language model
    in Fione: create, upload, propose, train, wait, read the leaderboard and predict."""
    monkeypatch.delenv("FIONE_JOB_HANDLER_MODULES", raising=False)
    client = make_client(
        start_runner=True, mcp_enabled=True, mcp_write_enabled=True, **ASSISTANT_OFF
    )
    headers = bearer(client, add_user(client, "ed", Role.EDITOR))

    def ok(name, arguments):
        out = call(client, headers, name, arguments)
        assert out["isError"] is False, out
        return out["structuredContent"]

    project_id = ok("create_project", {"name": "Iris"})["project_id"]
    csv_text = iris_frame().to_csv(index=False)
    dataset = ok(
        "upload_dataset",
        {"project_id": project_id, "name": "iris", "type": "train", "csv_text": csv_text},
    )
    proposed = ok(
        "propose_training_config",
        {"dataset_id": dataset["id"], "target": "species"},
    )
    config = proposed["config"] | {k: v for k, v in FAST_CONFIG.items() if k != "target"}
    job_id = ok(
        "start_training",
        {"project_id": project_id, "dataset_id": dataset["id"], "config": config},
    )["job_id"]
    deadline = time.monotonic() + 300
    while not (job := ok("wait_for_job", {"job_id": job_id, "timeout_secs": 15}))["done"]:
        assert time.monotonic() < deadline, job
    assert job["status"] == "done", job
    model_id = job["result"]["model_id"]
    assert ok("get_leaderboard", {"model_id": model_id})["model"]
    rows = iris_frame().drop(columns=["species"]).head(3).to_dict(orient="records")
    predicted = ok("predict", {"project_id": project_id, "model_id": model_id, "rows": rows})
    assert len(predicted["predictions"]) == 3
