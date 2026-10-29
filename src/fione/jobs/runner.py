"""Launches queued jobs as worker subprocesses, cancels them, and cleans up after crashes.

Each worker is a fresh interpreter (never a fork: native libraries such as OpenMP can hang
in a forked child) in its own session, so its process group holds the whole tree, native
threads and grandchildren included, and one ``killpg`` ends it. The runner writes a
terminal status only when the worker cannot: it was killed on cancel, it died (crash,
SIGKILL, OOM), or the server restarted under it.
"""

import json
import logging
import os
import secrets
import signal
import sqlite3
import subprocess
import sys
import threading
from contextlib import closing
from pathlib import Path

from pydantic import SecretStr

from fione import db
from fione.config import Settings
from fione.engine.events import Event
from fione.jobs import store
from fione.jobs.store import JobStatus

log = logging.getLogger(__name__)

TRAINING_KINDS = frozenset({"automl"})
LOG_TAIL_BYTES = 8192
LOG_TAIL_LINES = 20


def _exported(value) -> str:
    """A setting as the text ``Settings`` reads back: JSON for an object (``str`` would give a
    Python dict), the secret itself for a ``SecretStr`` (``str`` would give asterisks)."""
    if isinstance(value, dict):
        return json.dumps(value)
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return str(value)


def worker_env(settings: Settings, db_path: Path) -> dict[str, str]:
    """The worker's environment: ours, with every Settings field exported as ``FIONE_*``."""
    env = dict(os.environ)
    prefix = settings.model_config.get("env_prefix", "")
    for name in type(settings).model_fields:
        key = f"{prefix}{name}".upper()
        value = getattr(settings, name)
        if value is None:
            env.pop(key, None)
        else:
            env[key] = _exported(value)
    env["FIONE_JOB_DB"] = str(db_path)
    return env


def _kill_group(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # nobody left in the group
    except PermissionError:
        pass  # macOS: the group holds only the unreaped worker (a zombie)


def _is_worker(pid: int, run_token: str) -> bool:
    """Whether ``pid`` is still the worker started with ``run_token`` (pids get reused)."""
    try:
        out = subprocess.run(
            ["ps", "-ww", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False  # cannot tell, so never kill
    args = out.stdout.split()
    return out.returncode == 0 and "fione.jobs.worker" in args and run_token in args


def _is_live_worker(row: sqlite3.Row) -> bool:
    return bool(row["pid"] and row["run_token"] and _is_worker(row["pid"], row["run_token"]))


def _kill_worker(pid: int) -> None:
    try:
        if os.getpgid(pid) != pid:
            os.kill(pid, signal.SIGKILL)
            return
    except ProcessLookupError:
        return
    _kill_group(pid)


class JobRunner:
    """Runs the queue of one database. Run exactly one per database: runners do not
    coordinate, and each settles running jobs it does not track as dead."""

    def __init__(
        self,
        settings: Settings,
        db_path: Path,
        *,
        poll_secs: float = 1.0,
        cancel_grace_secs: float = 10.0,
    ):
        self._settings = settings
        self._db_path = db_path
        self._poll_secs = poll_secs
        self._grace = cancel_grace_secs
        # Guards _procs and _cancelling; held across a launch so cancel never sees half of one.
        self._lock = threading.Lock()
        self._procs: dict[int, tuple[subprocess.Popen, str]] = {}  # job id -> (worker, kind)
        self._cancelling: set[int] = set()  # cancel() waits for these; the poller skips them
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("job runner already started")
        self._stopping.clear()
        self._thread = threading.Thread(target=self._loop, name="fione-job-runner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop polling; running workers keep running."""
        self._stopping.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def shutdown(self, kill_running: bool) -> None:
        """``stop``, and with ``kill_running`` also kill the workers (their jobs end failed)."""
        self.stop()
        if not kill_running:
            return
        with self._lock:
            procs = [proc for proc, _ in self._procs.values()]
        for proc in procs:
            _kill_group(proc.pid)
            proc.wait()
        with self._connect() as conn:
            self._reap(conn)

    def worker_count(self) -> int:
        """How many worker processes this runner is tracking now."""
        with self._lock:
            return len(self._procs)

    def recover_orphans(self) -> None:
        """Fail every job left running by a previous server; call once before ``start``.

        A worker that outlived the server is killed first, but only after ``ps`` confirms the
        pid still runs that job's worker command line: the pid may now be someone else's.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, pid, run_token FROM jobs WHERE status = 'running'"
            ).fetchall()
            for row in rows:
                # Also tells a worker we could not kill (or identify) to stop by itself.
                store.request_cancel(conn, row["id"])
                if _is_live_worker(row):
                    _kill_worker(row["pid"])
                store.finish_job(
                    conn, row["id"], JobStatus.FAILED, message="interrupted by restart"
                )

    def cancel(self, job_id: int) -> bool:
        """Cancel a queued or running job; False if it had already finished.

        A running worker gets ``cancel_grace_secs`` to notice ``should_stop`` and wind down,
        then its process group is killed regardless, which also takes any grandchildren.
        Returns whether the job ended cancelled (a worker may finish first). If recording
        that fails, the error propagates and the poller records it later; cancelling again
        is safe.
        """
        with self._connect() as conn:
            with self._lock:
                if store.cancel_queued(conn, job_id):
                    return True
                if store.get_job(conn, job_id).status is not JobStatus.RUNNING:
                    return False
                store.request_cancel(conn, job_id)
                entry = self._procs.get(job_id)
                if entry is not None:
                    self._cancelling.add(job_id)
            if entry is None:
                # Not launched by this runner (its launch failed half way); no worker to wait for.
                row = conn.execute(
                    "SELECT pid, run_token FROM jobs WHERE id = ?", (job_id,)
                ).fetchone()
                if row is not None and _is_live_worker(row):
                    _kill_worker(row["pid"])
                store.finish_job(conn, job_id, JobStatus.CANCELLED)
                return store.get_job(conn, job_id).status is JobStatus.CANCELLED
            proc = entry[0]
            try:
                try:
                    proc.wait(timeout=self._grace)
                except subprocess.TimeoutExpired:
                    pass
                _kill_group(proc.pid)
                proc.wait()
                store.finish_job(conn, job_id, JobStatus.CANCELLED)
                final = store.get_job(conn, job_id).status
            finally:
                # Forget the worker only once its job is recorded as finished; until then the
                # poller keeps it and settles it (cancel_requested makes that CANCELLED).
                with self._lock:
                    self._cancelling.discard(job_id)
            with self._lock:
                self._procs.pop(job_id, None)
            return final is JobStatus.CANCELLED

    def _connect(self) -> closing[sqlite3.Connection]:
        return closing(db.connect(self._db_path))

    def _loop(self) -> None:
        with self._connect() as conn:
            while not self._stopping.is_set():
                try:
                    self._reap(conn)
                    self._launch_queued(conn)
                except Exception:
                    log.exception("job runner poll failed")
                self._stopping.wait(self._poll_secs)

    def _limit(self, kind: str) -> int:
        if kind in TRAINING_KINDS:
            return self._settings.max_concurrent_train_jobs
        return self._settings.max_concurrent_short_jobs

    def _launch_queued(self, conn: sqlite3.Connection) -> None:
        queued = conn.execute(
            "SELECT id, kind FROM jobs WHERE status = 'queued' ORDER BY created_at, id"
        ).fetchall()
        for row in queued:
            training = row["kind"] in TRAINING_KINDS
            with self._lock:
                running = sum((k in TRAINING_KINDS) == training for _, k in self._procs.values())
                if running < self._limit(row["kind"]):
                    self._launch(conn, row["id"], row["kind"])

    def _launch(self, conn: sqlite3.Connection, job_id: int, kind: str) -> None:
        # The token is in the row before the worker exists, so the worker can verify it.
        run_token = secrets.token_hex(16)
        if not store.claim_job(conn, job_id, run_token):
            return  # cancelled since it was listed
        log_path = self._settings.data_dir / "jobs" / f"{job_id}.log"
        # If this fails, or the FAILED write below does, the job is running but untracked
        # and the next poll settles it.
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "ab") as log_file:
                proc = subprocess.Popen(
                    [sys.executable, "-m", "fione.jobs.worker", str(job_id), run_token],
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    env=worker_env(self._settings, self._db_path),
                    start_new_session=True,
                )
        except Exception as e:
            message = f"could not start worker: {type(e).__name__}: {e}"
            store.finish_job(conn, job_id, JobStatus.FAILED, message=message)
            return
        self._procs[job_id] = (proc, kind)
        store.set_pid(conn, job_id, proc.pid)

    def _reap(self, conn: sqlite3.Connection) -> None:
        with self._lock:
            exited = [
                (job_id, proc)
                for job_id, (proc, _) in self._procs.items()
                if job_id not in self._cancelling and proc.poll() is not None
            ]
        for job_id, proc in exited:
            # The worker is gone, but processes it started may linger in its group.
            _kill_group(proc.pid)
            self._settle(conn, job_id, proc.returncode)
            with self._lock:
                self._procs.pop(job_id, None)
        self._settle_untracked(conn)

    def _settle_untracked(self, conn: sqlite3.Connection) -> None:
        """Settle running jobs with no worker: a launch or a terminal write that failed."""
        rows = conn.execute("SELECT id, pid, run_token FROM jobs WHERE status = 'running'")
        for row in rows.fetchall():
            with self._lock:
                tracked = row["id"] in self._procs
            if not tracked and not _is_live_worker(row):
                self._settle(conn, row["id"], None)

    def _settle(self, conn: sqlite3.Connection, job_id: int, code: int | None) -> None:
        """Record the outcome of a worker that exited without recording one itself."""
        try:
            job = store.get_job(conn, job_id)
        except KeyError:
            return  # deleted along with its project
        if job.status is not JobStatus.RUNNING:
            return
        if store.cancel_requested(conn, job_id):
            store.finish_job(conn, job_id, JobStatus.CANCELLED)
            return
        message = "worker exited unexpectedly"
        if code is not None:
            message += f" (code {code})"
        data = {"error": message, "log_tail": self._log_tail(job_id)}
        store.append_event(conn, job_id, Event("error", data=data))
        store.finish_job(conn, job_id, JobStatus.FAILED, message=message)

    def _log_tail(self, job_id: int) -> str:
        path = self._settings.data_dir / "jobs" / f"{job_id}.log"
        try:
            with open(path, "rb") as f:
                f.seek(max(0, path.stat().st_size - LOG_TAIL_BYTES))
                text = f.read().decode(errors="replace")
        except OSError:
            return ""
        return "\n".join(text.splitlines()[-LOG_TAIL_LINES:])
