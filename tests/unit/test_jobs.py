import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from fione import db
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.config import Settings
from fione.engine.events import Event
from fione.jobs import store
from fione.jobs.runner import JobRunner, worker_env
from fione.jobs.store import JobStatus
from fione.projects import service
from fione.storage import LocalStorage

HERE = Path(__file__).parent
TERMINAL = {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED}


def wait_for(predicate, timeout=20.0, interval=0.02):
    deadline = time.monotonic() + timeout
    while True:
        value = predicate()
        if value:
            return value
        if time.monotonic() > deadline:
            raise AssertionError("condition not met in time")
        time.sleep(interval)


def gone(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("FIONE_JOB_HANDLER_MODULES", "job_test_handlers")
    path = os.pathsep.join(p for p in (str(HERE), os.environ.get("PYTHONPATH")) if p)
    monkeypatch.setenv("PYTHONPATH", path)
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
def owner(conn):
    return auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR)


@pytest.fixture
def project(conn, owner):
    return service.create_project(conn, owner, "jobs")


@pytest.fixture
def enqueue(conn, owner, project):
    def make(kind, payload=None):
        return store.enqueue(conn, kind, project.id, owner.id, payload or {})

    return make


@pytest.fixture
def make_runner(settings, db_path, conn):
    runners = []

    def make(start=True, **overrides):
        kwargs = {"poll_secs": 0.05}
        for key in ("poll_secs", "cancel_grace_secs"):
            if key in overrides:
                kwargs[key] = overrides.pop(key)
        runner = JobRunner(settings.model_copy(update=overrides), db_path, **kwargs)
        runners.append(runner)
        if start:
            runner.start()
        return runner

    yield make
    for runner in runners:
        runner.shutdown(kill_running=True)


@pytest.fixture
def spawned():
    """Processes and bare pids a test started; anything still alive is killed in teardown."""
    procs: list[subprocess.Popen] = []
    pids: list[int] = []
    yield procs, pids
    for proc in procs:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def wait_done(conn, job_id):
    return wait_for(lambda: (j := store.get_job(conn, job_id)).status in TERMINAL and j)


def wait_event(conn, job_id, type_):
    def found():
        return next((e for _, e in store.events_since(conn, job_id) if e.type == type_), None)

    return wait_for(found)


def job_pid(conn, job_id):
    return conn.execute("SELECT pid FROM jobs WHERE id = ?", (job_id,)).fetchone()[0]


def claim(conn, job_id, token, pid):
    assert store.claim_job(conn, job_id, token)
    store.set_pid(conn, job_id, pid)


# --- store ---


def test_enqueue_get_and_list(conn, enqueue, project):
    a = enqueue("echo", {"x": 1, "name": "日本語"})
    b = enqueue("sleep")
    assert a.status is JobStatus.QUEUED
    assert a.payload == {"x": 1, "name": "日本語"}
    assert a.project_id == project.id and a.result is None and a.started_at is None
    assert store.get_job(conn, a.id) == a
    assert [j.id for j in store.list_jobs(conn, project.id)] == [b.id, a.id]
    store.claim_job(conn, b.id, "tok")
    assert store.list_jobs(conn, project.id, status=JobStatus.QUEUED) == [a]
    with pytest.raises(KeyError):
        store.get_job(conn, 999)


def test_events_since_paginates_in_order(conn, enqueue):
    job = enqueue("echo")
    for i in range(5):
        store.append_event(conn, job.id, Event("trial", ts=100.0 + i, data={"i": i}))
    page = store.events_since(conn, job.id)
    assert [e.data["i"] for _, e in page] == [0, 1, 2, 3, 4]
    assert page[0][1] == Event("trial", ts=100.0, data={"i": 0})
    after = store.events_since(conn, job.id, after_id=page[1][0])
    assert [e.data["i"] for _, e in after] == [2, 3, 4]
    assert store.events_since(conn, job.id, after_id=page[-1][0]) == []


def test_event_data_over_64kb_is_replaced_by_a_marker(conn, enqueue):
    job = enqueue("echo")
    store.append_event(conn, job.id, Event("notice", data={"message": "あ" * 30000}))
    store.append_event(conn, job.id, Event("notice", data={"message": "a" * 60000}))
    (_, big), (_, small) = store.events_since(conn, job.id)
    size = len(json.dumps({"message": "あ" * 30000}, ensure_ascii=False).encode())
    assert big.data == {"truncated": True, "size": size}
    assert small.data == {"message": "a" * 60000}


def test_late_done_write_cannot_overwrite_cancelled(conn, enqueue):
    job = enqueue("sleep")
    assert store.claim_job(conn, job.id, "tok")
    assert store.finish_job(conn, job.id, JobStatus.CANCELLED)
    assert not store.finish_job(conn, job.id, JobStatus.DONE, result={"ok": True})
    final = store.get_job(conn, job.id)
    assert final.status is JobStatus.CANCELLED and final.result is None


def test_delete_job_only_when_terminal(conn, enqueue):
    job = enqueue("echo")
    store.append_event(conn, job.id, Event("notice", data={"message": "x"}))
    with pytest.raises(ValueError):
        store.delete_job(conn, job.id)
    store.claim_job(conn, job.id, "tok")
    store.finish_job(conn, job.id, JobStatus.DONE)
    store.delete_job(conn, job.id)
    with pytest.raises(KeyError):
        store.get_job(conn, job.id)
    assert conn.execute("SELECT count(*) FROM job_events").fetchone()[0] == 0


def test_delete_all_jobs_removes_terminal_jobs_only(conn, enqueue, project):
    queued, running, done, failed = (enqueue("echo") for _ in range(4))
    for job in (running, done, failed):
        store.claim_job(conn, job.id, "tok")
    store.finish_job(conn, done.id, JobStatus.DONE)
    store.finish_job(conn, failed.id, JobStatus.FAILED, message="x")
    assert store.delete_all_jobs(conn, project.id) == 2
    assert {j.id for j in store.list_jobs(conn, project.id)} == {queued.id, running.id}


def test_deleting_a_project_cascades_to_jobs_and_events(conn, enqueue, owner, project, tmp_path):
    job = enqueue("echo")
    store.append_event(conn, job.id, Event("notice", data={"message": "x"}))
    service.delete_project(conn, LocalStorage(tmp_path / "objects"), owner, project.id)
    assert conn.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM job_events").fetchone()[0] == 0


def test_worker_env_exports_settings(settings, db_path):
    env = worker_env(settings.model_copy(update={"max_concurrent_short_jobs": 7}), db_path)
    assert env["FIONE_DATA_DIR"] == str(settings.data_dir)
    assert env["FIONE_MAX_CONCURRENT_SHORT_JOBS"] == "7"
    assert env["FIONE_JOB_DB"] == str(db_path)
    assert env["FIONE_JOB_HANDLER_MODULES"] == "job_test_handlers"
    assert "FIONE_S3_ENDPOINT" not in env


def test_short_job_limit_setting_reads_env(monkeypatch):
    monkeypatch.setenv("FIONE_MAX_CONCURRENT_SHORT_JOBS", "9")
    assert Settings().max_concurrent_short_jobs == 9
    assert Settings.model_fields["max_concurrent_short_jobs"].default == 4


# --- runner and worker ---


def test_echo_job_runs_in_a_subprocess(conn, enqueue, make_runner, settings):
    make_runner()
    job = enqueue("echo")
    final = wait_done(conn, job.id)
    assert final.status is JobStatus.DONE, final.message
    assert final.result == {"ok": True}
    assert final.started_at <= final.finished_at
    events = [e for _, e in store.events_since(conn, job.id)]
    assert [e.data["message"] for e in events] == ["one", "two", "日本語 ✓"]
    assert job_pid(conn, job.id) != os.getpid()
    assert (settings.data_dir / "jobs" / f"{job.id}.log").exists()


def test_emit_flood_keeps_every_event_in_order(conn, enqueue, make_runner):
    make_runner()
    job = enqueue("emit_flood", {"n": 500})
    assert wait_done(conn, job.id).status is JobStatus.DONE
    assert [e.data["i"] for _, e in store.events_since(conn, job.id)] == list(range(500))


def test_training_jobs_run_one_at_a_time(conn, enqueue, make_runner):
    first, second = enqueue("automl", {"seconds": 1.0}), enqueue("automl", {"seconds": 1.0})
    make_runner(max_concurrent_train_jobs=1)
    a, b = wait_done(conn, first.id), wait_done(conn, second.id)
    assert a.status is b.status is JobStatus.DONE
    assert a.finished_at <= b.started_at


def max_overlap(jobs):
    points = sorted([(j.started_at, 1) for j in jobs] + [(j.finished_at, -1) for j in jobs])
    level = peak = 0
    for _, step in points:
        level += step
        peak = max(peak, level)
    return peak


def test_short_jobs_have_their_own_limit(conn, enqueue, make_runner):
    train = enqueue("automl", {"seconds": 3.0})
    shorts = [enqueue("ignore_stop", {"seconds": 0.6}) for _ in range(3)]
    make_runner(max_concurrent_train_jobs=1, max_concurrent_short_jobs=2)
    done = [wait_done(conn, j.id) for j in shorts]
    assert all(j.status is JobStatus.DONE for j in done)
    assert max_overlap(done) == 2
    t = wait_done(conn, train.id)
    assert min(j.started_at for j in done) < t.finished_at  # not blocked behind training


def test_cancel_running_job_is_cooperative(conn, enqueue, make_runner):
    runner = make_runner(cancel_grace_secs=10)
    job = enqueue("sleep", {"seconds": 60})
    wait_event(conn, job.id, "started")
    t0 = time.monotonic()
    assert runner.cancel(job.id)
    assert time.monotonic() - t0 < 5  # well inside the grace period, so not killed
    final = store.get_job(conn, job.id)
    assert final.status is JobStatus.CANCELLED and final.finished_at


def test_handler_returning_after_cancel_request_is_cancelled(conn, enqueue, make_runner):
    runner = make_runner(cancel_grace_secs=10)
    job = enqueue("ignore_stop", {"seconds": 1.0})
    wait_event(conn, job.id, "started")
    t0 = time.monotonic()
    assert runner.cancel(job.id)
    assert time.monotonic() - t0 < 5
    assert store.get_job(conn, job.id).status is JobStatus.CANCELLED


def test_cancel_kills_a_worker_that_ignores_stop(conn, enqueue, make_runner):
    runner = make_runner(cancel_grace_secs=0.5)
    job = enqueue("ignore_stop")
    wait_event(conn, job.id, "started")
    pid = job_pid(conn, job.id)
    t0 = time.monotonic()
    assert runner.cancel(job.id)
    assert 0.5 <= time.monotonic() - t0 < 5
    final = store.get_job(conn, job.id)
    assert final.status is JobStatus.CANCELLED and final.finished_at
    assert gone(pid)


@pytest.mark.parametrize("cooperative", [False, True])
def test_cancel_kills_grandchildren(conn, enqueue, make_runner, spawned, cooperative):
    runner = make_runner(cancel_grace_secs=0.5)
    job = enqueue("spawn_child", {"cooperative": cooperative})
    child = wait_event(conn, job.id, "started").data["child_pid"]
    spawned[1].append(child)
    assert not gone(child)
    assert runner.cancel(job.id)
    assert store.get_job(conn, job.id).status is JobStatus.CANCELLED
    wait_for(lambda: gone(child))


def test_cancel_queued_job_is_immediate(conn, enqueue, make_runner):
    runner = make_runner(start=False)
    job = enqueue("sleep")
    assert runner.cancel(job.id)
    final = store.get_job(conn, job.id)
    assert final.status is JobStatus.CANCELLED and final.finished_at and final.started_at is None


def test_cancel_terminal_job_returns_false(conn, enqueue, make_runner):
    runner = make_runner(start=False)
    job = enqueue("sleep")
    assert runner.cancel(job.id)
    assert not runner.cancel(job.id)
    assert store.get_job(conn, job.id).status is JobStatus.CANCELLED


def test_crash_fails_with_message_and_traceback(conn, enqueue, make_runner):
    make_runner()
    job = enqueue("crash")
    final = wait_done(conn, job.id)
    assert final.status is JobStatus.FAILED
    assert final.message == "RuntimeError: boom"
    _, last = store.events_since(conn, job.id)[-1]
    assert last.type == "error" and last.data["error"] == "RuntimeError: boom"
    assert (
        "Traceback" in last.data["traceback"]
        and 'raise RuntimeError("boom")' in (last.data["traceback"])
    )


def test_unknown_kind_fails(conn, enqueue, make_runner):
    make_runner()
    job = enqueue("no_such_kind")
    final = wait_done(conn, job.id)
    assert final.status is JobStatus.FAILED and final.message == "unknown job kind: no_such_kind"


def test_worker_killed_from_outside_is_marked_failed(conn, enqueue, make_runner):
    make_runner()
    job = enqueue("sleep", {"seconds": 60})
    wait_event(conn, job.id, "started")
    os.kill(job_pid(conn, job.id), signal.SIGKILL)  # what the OOM killer does
    final = wait_done(conn, job.id)
    assert final.status is JobStatus.FAILED
    assert final.message == "worker exited unexpectedly (code -9)"
    _, last = store.events_since(conn, job.id)[-1]
    assert last.type == "error" and "log_tail" in last.data


def test_unrecordable_progress_fails_the_job(
    conn, enqueue, make_runner, settings, db_path, tmp_path
):
    make_runner()
    go = tmp_path / "go"
    job = enqueue("abort_probe", {"go_file": str(go)})
    wait_for(lambda: job_pid(conn, job.id))
    lock = db.connect(db_path)
    try:
        lock.execute("BEGIN EXCLUSIVE")
        go.touch()
        log = settings.data_dir / "jobs" / f"{job.id}.log"
        wait_for(lambda: log.exists() and "could not record progress" in log.read_text())
    finally:
        lock.execute("ROLLBACK")
        lock.close()
    final = wait_done(conn, job.id)
    assert final.status is JobStatus.FAILED
    assert final.message.startswith("could not record progress: ")
    assert final.result is None


def test_worker_with_wrong_token_leaves_the_job_alone(conn, enqueue, settings, db_path):
    job = enqueue("echo")
    claim(conn, job.id, "right-token", 12345)
    before = store.get_job(conn, job.id)
    proc = subprocess.run(
        [sys.executable, "-m", "fione.jobs.worker", str(job.id), "wrong-token"],
        env=worker_env(settings, db_path),
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 3
    assert store.get_job(conn, job.id) == before
    assert store.events_since(conn, job.id) == []


# --- orphan recovery ---


def test_recover_orphans_fails_running_jobs_with_dead_pids(conn, enqueue, make_runner, spawned):
    dead = subprocess.Popen(["true"])
    dead.wait()
    running, queued = enqueue("sleep"), enqueue("sleep")
    claim(conn, running.id, "tok-dead", dead.pid)
    make_runner(start=False).recover_orphans()
    final = store.get_job(conn, running.id)
    assert final.status is JobStatus.FAILED and final.message == "interrupted by restart"
    assert final.finished_at
    assert store.get_job(conn, queued.id).status is JobStatus.QUEUED


def test_recover_orphans_kills_a_live_worker_with_its_token(
    conn, enqueue, make_runner, settings, db_path, spawned
):
    job = enqueue("sleep", {"seconds": 60})
    token = "a1b2c3d4e5f6a7b8"
    assert store.claim_job(conn, job.id, token)
    worker = subprocess.Popen(
        [sys.executable, "-m", "fione.jobs.worker", str(job.id), token],
        env=worker_env(settings, db_path),
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    spawned[0].append(worker)
    store.set_pid(conn, job.id, worker.pid)
    wait_event(conn, job.id, "started")
    make_runner(start=False).recover_orphans()
    assert worker.wait(timeout=20) == -signal.SIGKILL
    final = store.get_job(conn, job.id)
    assert final.status is JobStatus.FAILED and final.message == "interrupted by restart"


def test_recover_orphans_never_kills_an_unrelated_process(conn, enqueue, make_runner, spawned):
    stranger = subprocess.Popen(["sleep", "60"], start_new_session=True)
    spawned[0].append(stranger)
    job = enqueue("sleep")
    claim(conn, job.id, "f00dfeedf00dfeed", stranger.pid)  # the pid was reused
    make_runner(start=False).recover_orphans()
    with pytest.raises(subprocess.TimeoutExpired):  # a SIGKILL would land well within this
        stranger.wait(timeout=0.3)
    final = store.get_job(conn, job.id)
    assert final.status is JobStatus.FAILED and final.message == "interrupted by restart"
