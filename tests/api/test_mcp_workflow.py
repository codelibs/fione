"""The MCP workflow tools: follow and cancel jobs, create a project and upload a dataset inline,
each as the token's user with the access the REST routes ask for."""

import json
import threading
from contextlib import closing

import pytest
from test_mcp import bearer, call, iris_dataset, rpc
from test_mcp_actions import CONFIG, writes  # noqa: F401  (the fixture)

from api_helpers import add_user, connect, iris_frame
from fione.auth.roles import ProjectAccess, Role
from fione.jobs import store
from fione.projects import service as projects
from fione.tools.workflow import INLINE_UPLOAD_MAX_BYTES

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
