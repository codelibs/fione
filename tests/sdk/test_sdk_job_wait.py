"""Waiting, events and prediction clean-up against scripted responses: no server, no sleeping."""

import json
import pickle
import re

import httpx
import pandas as pd
import pytest
from fione_sdk import Client, FioneError, Job, JobFailed
from fione_sdk import jobs as jobs_module


class Clock:
    """A fake clock whose pauses advance it, replacing the module's own."""

    def __init__(self, monkeypatch):
        self.now = 0.0
        self.sleeps: list[float] = []
        monkeypatch.setattr(jobs_module, "_monotonic", lambda: self.now)
        monkeypatch.setattr(jobs_module, "_sleep", self.sleep)

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    return Clock(monkeypatch)


def job_json(status="running", **extra):
    return {"id": 3, "kind": "automl", "status": status, "result": None, "message": "", **extra}


def scripted(handler) -> tuple[Client, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request):
        seen.append(request)
        return handler(request)

    http = httpx.Client(transport=httpx.MockTransport(record), base_url="http://fione.test")
    return Client(token="secret", http=http), seen


def sequence(*statuses):
    """GET /jobs/3 answers the statuses in turn, then the last one for good."""
    left = list(statuses)

    def handler(request):
        if request.method == "POST":
            return httpx.Response(200, json=job_json("cancelled"))
        status = left.pop(0) if len(left) > 1 else left[0]
        return httpx.Response(200, json=job_json(status))

    return scripted(handler)


def test_the_poll_interval_doubles_up_to_max_poll(clock):
    client, _ = sequence(*["running"] * 6, "done")
    assert Job(client, job_json("queued")).wait().status == "done"
    assert clock.sleeps == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0]


def test_poll_and_max_poll_are_options(clock):
    client, _ = sequence(*["running"] * 4, "done")
    Job(client, job_json()).wait(poll=0.5, max_poll=1.5)
    assert clock.sleeps == [0.5, 1.0, 1.5, 1.5]


def test_timeout_clips_the_last_pause_and_raises(clock):
    client, seen = sequence("running")
    with pytest.raises(TimeoutError, match="job 3"):
        Job(client, job_json()).wait(timeout=5)
    assert clock.sleeps == [1.0, 2.0, 2.0]
    assert all(r.method == "GET" for r in seen)  # a timeout leaves the job running


def test_a_finished_job_is_returned_without_sleeping(clock):
    client, _ = sequence("done")
    assert Job(client, job_json()).wait(timeout=0).status == "done"
    assert clock.sleeps == []


@pytest.mark.parametrize("status", ["failed", "cancelled"])
def test_failed_and_cancelled_jobs_raise_job_failed(clock, status):
    def handler(request):
        return httpx.Response(200, json=job_json(status, message="boom"))

    client, _ = scripted(handler)
    with pytest.raises(JobFailed) as err:
        Job(client, job_json()).wait()
    assert (err.value.code, err.value.message) == (status, "boom")
    assert isinstance(err.value, FioneError) and err.value.job.status == status


def test_ctrl_c_while_waiting_cancels_the_job_and_reraises(monkeypatch):
    def interrupt(seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(jobs_module, "_sleep", interrupt)
    client, seen = sequence("running")
    with pytest.raises(KeyboardInterrupt):
        Job(client, job_json()).wait()
    assert [(r.method, r.url.path) for r in seen] == [
        ("GET", "/api/v1/jobs/3"),
        ("POST", "/api/v1/jobs/3/cancel"),
    ]


def test_ctrl_c_still_reraises_when_the_cancel_fails(monkeypatch):
    conflict = httpx.Response(409, json={"error": "done", "code": "conflict"})

    def interrupt(seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(jobs_module, "_sleep", interrupt)
    client, seen = scripted(
        lambda request: (
            conflict if request.method == "POST" else httpx.Response(200, json=job_json())
        )
    )
    with pytest.raises(KeyboardInterrupt):
        Job(client, job_json()).wait()
    assert seen[-1].method == "POST"


def test_job_failed_pickles_without_the_client_or_token(clock):
    client, _ = scripted(
        lambda request: httpx.Response(200, json=job_json("failed", message="boom"))
    )
    with pytest.raises(JobFailed) as err:
        Job(client, job_json()).wait()
    copy = pickle.loads(pickle.dumps(err.value))
    assert isinstance(copy, JobFailed) and (copy.code, copy.message) == ("failed", "boom")
    assert copy.job.data == err.value.job.data and copy.job.id == 3
    with pytest.raises(FioneError, match="no client"):
        copy.job.refresh()
    for shown in (repr(err.value), str(err.value), repr(err.value.job), repr(copy.job)):
        assert "secret" not in shown
    assert pickle.loads(pickle.dumps(err.value.job)).status == "failed"


def test_a_response_that_is_not_a_job_is_an_error():
    client, _ = scripted(lambda request: httpx.Response(200, json={"detail": "portal"}))
    with pytest.raises(FioneError, match="unexpected response"):
        client.job(3)
    with pytest.raises(FioneError):
        Job(client, {}).refresh()
    gone, _ = scripted(
        lambda request: httpx.Response(404, json={"error": "no", "code": "not_found"})
    )
    with pytest.raises(FioneError) as err:
        gone.job(3)
    assert err.value.status == 404


def events_handler(pages, statuses):
    """GET /jobs/3/events: ``pages`` maps ``after`` to the events after it."""

    def handler(request):
        after = int(request.url.params["after"])
        events = pages.get(after, [])
        last = events[-1]["id"] if events else after
        return httpx.Response(
            200, json={"events": events, "last_id": last, "status": statuses.pop(0)}
        )

    return handler


def ev(i, type="progress"):
    return {"id": i, "type": type, "ts": 0, "data": {}}


def test_events_page_by_last_id():
    pages = {0: [ev(1), ev(2)], 2: [ev(3)]}
    client, seen = scripted(events_handler(pages, ["running"] * 3))
    got = list(Job(client, job_json()).events())
    assert [e["id"] for e in got] == [1, 2, 3]
    assert [r.url.params["after"] for r in seen] == ["0", "2", "3"]
    assert {r.url.params["limit"] for r in seen} == {"500"}


def test_events_follow_polls_until_terminal_and_empty(clock):
    # (events, status) answered per poll: an empty poll while running, then a late event, then
    # a terminal status with nothing left.
    answers = [
        ([ev(1)], "running"),
        ([], "running"),
        ([ev(2, "finished")], "running"),
        ([], "done"),
    ]
    calls = []

    def handler(request):
        calls.append(int(request.url.params["after"]))
        events, status = answers.pop(0)
        last = events[-1]["id"] if events else calls[-1]
        return httpx.Response(200, json={"events": events, "last_id": last, "status": status})

    client, _ = scripted(handler)
    got = list(Job(client, job_json()).events(follow=True))
    assert [e["id"] for e in got] == [1, 2]
    assert calls == [0, 1, 1, 2]
    assert clock.sleeps == [jobs_module.EVENT_POLL]


def test_events_without_follow_stop_at_an_empty_page(clock):
    client, seen = scripted(events_handler({}, ["running"]))
    assert list(Job(client, job_json()).events()) == []
    assert len(seen) == 1 and clock.sleeps == []


def test_events_reject_a_malformed_page():
    client, _ = scripted(lambda request: httpx.Response(200, json={"events": []}))
    with pytest.raises(FioneError, match="unexpected response"):
        list(Job(client, job_json()).events())


class PredictServer:
    """Routes for ``predict``: an upload, a batch-predict job, the job, a download, a delete."""

    def __init__(self, job_status="done", delete_status=204, result=None):
        self.job_status = job_status
        self.result = {"dataset_id": 9} if result is None else result
        self.delete_status = delete_status

    def __call__(self, request):
        path, method = request.url.path.removeprefix("/api/v1"), request.method
        if (method, path) == ("POST", "/projects/p/datasets"):
            return httpx.Response(201, json={"id": 7, "name": "x", "type": "predict"})
        if (method, path) == ("POST", "/projects/p/jobs/batch-predict"):
            return httpx.Response(201, json=job_json("queued", kind="batch_predict"))
        if (method, path) == ("GET", "/jobs/3"):
            result = self.result if self.job_status == "done" else None
            return httpx.Response(
                200, json=job_json(self.job_status, result=result, message="model broke")
            )
        if (method, path) == ("POST", "/jobs/3/cancel"):
            return httpx.Response(200, json=job_json("cancelled"))
        if (method, path) == ("GET", "/projects/p/datasets/9/download"):
            return httpx.Response(200, text="predict\nsetosa\n")
        if (method, path) == ("DELETE", "/projects/p/datasets/7"):
            return httpx.Response(self.delete_status, json={"error": "no", "code": "x"})
        raise AssertionError(f"unexpected {method} {path}")


FRAME = pd.DataFrame({"a": [1.0]})


def routes(seen):
    return [(r.method, r.url.path.removeprefix("/api/v1")) for r in seen]


def test_predict_uploads_waits_reads_and_removes_its_input(clock):
    client, seen = scripted(PredictServer())
    out = client.predict("p", 5, FRAME, include_columns=["a"])
    assert out["predict"].tolist() == ["setosa"]
    assert routes(seen) == [
        ("POST", "/projects/p/datasets"),
        ("POST", "/projects/p/jobs/batch-predict"),
        ("GET", "/jobs/3"),
        ("GET", "/projects/p/datasets/9/download"),
        ("DELETE", "/projects/p/datasets/7"),
    ]
    body = json.loads(seen[1].content)
    assert body == {"model_id": 5, "dataset_id": 7, "include_columns": ["a"]}
    upload = seen[0].content.decode()
    assert 'name="type"' in upload and "predict" in upload
    assert re.search(r'name="name"\r\n\r\nsdk_predict_[0-9a-f]{8}\r\n', upload)


def test_predict_removes_its_input_when_the_job_fails(clock):
    client, seen = scripted(PredictServer("failed"))
    with pytest.raises(JobFailed):
        client.predict("p", 5, FRAME)
    assert routes(seen)[-1] == ("DELETE", "/projects/p/datasets/7")


def test_predict_removes_its_input_and_cancels_the_job_on_timeout(clock):
    client, seen = scripted(PredictServer("running"))
    with pytest.raises(TimeoutError):
        client.predict("p", 5, FRAME, timeout=3)
    assert ("POST", "/jobs/3/cancel") in routes(seen)
    assert routes(seen)[-1] == ("DELETE", "/projects/p/datasets/7")


def test_a_failed_clean_up_does_not_hide_the_job_error(clock):
    client, seen = scripted(PredictServer("failed", delete_status=500))
    with pytest.raises(JobFailed):
        client.predict("p", 5, FRAME)
    assert routes(seen)[-1] == ("DELETE", "/projects/p/datasets/7")


def test_a_failed_clean_up_after_success_is_reported(clock):
    client, _ = scripted(PredictServer(delete_status=500))
    with pytest.raises(FioneError) as err:
        client.predict("p", 5, FRAME)
    assert err.value.status == 500


def test_predict_does_not_start_a_job_when_the_upload_fails():
    client, seen = scripted(
        lambda r: httpx.Response(413, json={"error": "big", "code": "too_large"})
    )
    with pytest.raises(FioneError):
        client.predict("p", 5, FRAME)
    assert len(seen) == 1


def test_predict_without_a_result_dataset_is_an_error_and_still_cleans_up(clock):
    client, seen = scripted(PredictServer(result={"n_rows": 1}))
    with pytest.raises(FioneError, match="no result dataset"):
        client.predict("p", 5, FRAME)
    assert routes(seen)[-1] == ("DELETE", "/projects/p/datasets/7")
