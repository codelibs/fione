"""Runs one job: ``python -m fione.jobs.worker <job_id> <run_token>``, started by JobRunner.

The worker owns the job's running -> done/failed/cancelled transition (the runner steps in
only when the worker dies or must be killed). Exit code 0 means the outcome is recorded,
whatever it is; nonzero means the worker itself broke, and the runner records that.
"""

import importlib
import json
import math
import os
import signal
import sqlite3
import sys
import time
import traceback
from pathlib import Path

from fione import db
from fione.config import Settings
from fione.engine.events import Event
from fione.jobs import store
from fione.jobs.handlers import HANDLERS, JobContext
from fione.jobs.store import Job, JobStatus
from fione.storage import open_storage

EXIT_NOT_MINE = 3
EMIT_TRIES = 3
# Per-try lock wait when recording an event: a few seconds of contention in total, then abort.
EMIT_BUSY_MS = 1000
STOP_CHECK_SECS = 0.5
TRACEBACK_CHARS = 4000


class JobAbort(BaseException):
    """Progress could not be recorded.

    A BaseException, so a handler's or the engine's ``except Exception`` recovery cannot
    swallow it and carry on with a run nobody can follow or trust.
    """


class _StopFlag:
    """``should_stop``: the job row, read at most every 0.5 s, or SIGTERM.

    True once a cancel is requested or the job is deleted or no longer running.
    """

    def __init__(self, conn: sqlite3.Connection, job_id: int):
        self._conn = conn
        self._job_id = job_id
        self._stopped = False
        self._checked = -math.inf

    def on_signal(self, signum, frame) -> None:
        self._stopped = True

    def __call__(self, *, force: bool = False) -> bool:
        now = time.monotonic()
        if not self._stopped and (force or now - self._checked >= STOP_CHECK_SECS):
            self._checked = now
            self._stopped = store.stop_requested(self._conn, self._job_id)
        return self._stopped


def _import_handler_modules() -> None:
    for name in os.environ.get("FIONE_JOB_HANDLER_MODULES", "").split(","):
        if name.strip():
            importlib.import_module(name.strip())


def _emitter(conn: sqlite3.Connection, job_id: int):
    busy_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]

    def emit(event: Event) -> None:
        error = None
        for attempt in range(EMIT_TRIES):
            if attempt:
                time.sleep(0.1 * attempt)
            conn.execute(f"PRAGMA busy_timeout={EMIT_BUSY_MS}")
            try:
                store.append_event(conn, job_id, event)
                return
            except sqlite3.OperationalError as e:
                error = e  # e.g. locked: worth another try
            except sqlite3.Error as e:
                raise JobAbort(str(e)) from e  # e.g. the job row is gone: retrying cannot help
            finally:
                conn.execute(f"PRAGMA busy_timeout={busy_ms}")
        raise JobAbort(str(error))

    return emit


def _run(conn: sqlite3.Connection, job: Job, settings: Settings) -> None:
    stop = _StopFlag(conn, job.id)
    signal.signal(signal.SIGTERM, stop.on_signal)
    emit = _emitter(conn, job.id)
    result = None

    def set_result(value: dict) -> None:
        nonlocal result
        json.dumps(value, allow_nan=False)  # fail inside the handler, not at the final write
        result = value

    handler = HANDLERS.get(job.kind)
    status, message, error_event = JobStatus.DONE, None, None
    try:
        if handler is None:
            status, message = JobStatus.FAILED, f"unknown job kind: {job.kind}"
        elif not stop(force=True):  # cancelled before it started: never run the handler
            storage = open_storage(settings)
            handler(JobContext(conn, storage, job, settings, emit, stop, set_result))
    except JobAbort as e:
        status, message = JobStatus.FAILED, f"could not record progress: {e}"
        print(f"job {job.id}: {message}", file=sys.stderr, flush=True)
    except Exception as e:
        status, message = JobStatus.FAILED, f"{type(e).__name__}: {e}"
        tb = traceback.format_exc()
        print(tb, file=sys.stderr, flush=True)
        error_event = Event("error", data={"error": message, "traceback": tb[-TRACEBACK_CHARS:]})
    if conn.in_transaction:  # a handler left its own transaction open
        conn.execute("ROLLBACK")
    if handler is not None and stop(force=True):
        status, message, error_event = JobStatus.CANCELLED, None, None
    if error_event is not None:
        try:
            emit(error_event)
        except JobAbort:
            pass  # the message below still says what failed
    store.finish_job(
        conn,
        job.id,
        status,
        message=message,
        result=result if status is JobStatus.DONE else None,
    )


def main(job_id: int, run_token: str) -> int:
    _import_handler_modules()
    settings = Settings()
    conn = db.connect(Path(os.environ["FIONE_JOB_DB"]))
    try:
        row = conn.execute("SELECT status, run_token FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None or row["run_token"] != run_token or row["status"] != JobStatus.RUNNING:
            print(f"job {job_id}: not this worker's job, leaving it alone", file=sys.stderr)
            return EXIT_NOT_MINE
        _run(conn, store.get_job(conn, job_id), settings)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]), sys.argv[2]))
