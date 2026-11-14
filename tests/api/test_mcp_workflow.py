"""The MCP job tools: get, wait for, list and cancel a job, as the token's user with the
access the REST job routes ask for."""

from contextlib import closing

import pytest
from test_mcp import bearer, call, iris_dataset
from test_mcp_actions import CONFIG, writes  # noqa: F401  (the fixture)

from api_helpers import add_user, connect
from fione.auth.roles import ProjectAccess, Role
from fione.jobs import store
from fione.projects import service as projects

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
