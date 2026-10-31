"""The jobs and job_events tables (spec 4.3).

State machine: queued -> running (the runner claims it) -> done/failed/cancelled; queued ->
cancelled directly. Leaving ``running`` always goes through ``finish_job``, a conditional
``UPDATE ... WHERE status = 'running'``, so whichever terminal write lands first wins and a
late write can never overwrite it.
"""

import json
import sqlite3
import time
from dataclasses import dataclass
from enum import StrEnum

from fione.engine.events import Event, jsonable

MAX_EVENT_BYTES = 64 * 1024


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL = (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED)


@dataclass(frozen=True)
class Job:
    id: int
    kind: str
    project_id: str | None
    owner_id: int
    status: JobStatus
    payload: dict
    result: dict | None
    message: str | None
    created_at: float
    started_at: float | None
    finished_at: float | None


def _job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        kind=row["kind"],
        project_id=row["project_id"],
        owner_id=row["owner_id"],
        status=JobStatus(row["status"]),
        payload=json.loads(row["payload_json"]),
        result=None if row["result_json"] is None else json.loads(row["result_json"]),
        message=row["message"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


def _dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def enqueue(
    conn: sqlite3.Connection, kind: str, project_id: str | None, owner_id: int, payload: dict
) -> Job:
    cur = conn.execute(
        "INSERT INTO jobs (kind, project_id, owner_id, status, payload_json, created_at)"
        " VALUES (?, ?, ?, 'queued', ?, ?)",
        (kind, project_id, owner_id, _dumps(payload), time.time()),
    )
    return get_job(conn, cur.lastrowid)


def get_job(conn: sqlite3.Connection, job_id: int) -> Job:
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise KeyError(job_id)
    return _job(row)


def list_jobs(
    conn: sqlite3.Connection,
    project_id: str | None,
    *,
    status: JobStatus | None = None,
    limit: int | None = None,
) -> list[Job]:
    """The project's jobs, newest first; at most ``limit`` of them if given."""
    sql = "SELECT * FROM jobs WHERE project_id IS ?"
    args: list = [project_id]
    if status is not None:
        sql += " AND status = ?"
        args.append(status)
    sql += " ORDER BY created_at DESC, id DESC"
    if limit is not None:
        sql += " LIMIT ?"
        args.append(limit)
    return [_job(r) for r in conn.execute(sql, args).fetchall()]


def _where(project_id: str | None, kind: str | None, statuses) -> tuple[str, list]:
    sql, args = " WHERE project_id IS ?", [project_id]
    if kind is not None:
        sql += " AND kind = ?"
        args.append(kind)
    if statuses is not None:
        sql += f" AND status IN ({', '.join('?' * len(statuses))})"
        args += list(statuses)
    return sql, args


def page_jobs(
    conn: sqlite3.Connection,
    project_id: str | None,
    *,
    kind: str | None = None,
    statuses: tuple | None = None,
    limit: int,
    offset: int = 0,
) -> list[Job]:
    """One page of the project's jobs of ``kind`` with one of ``statuses``, newest first."""
    where, args = _where(project_id, kind, statuses)
    sql = "SELECT * FROM jobs" + where + " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
    return [_job(r) for r in conn.execute(sql, [*args, limit, offset]).fetchall()]


def count_jobs(
    conn: sqlite3.Connection,
    project_id: str | None,
    *,
    kind: str | None = None,
    statuses: tuple | None = None,
) -> int:
    where, args = _where(project_id, kind, statuses)
    return conn.execute("SELECT COUNT(*) FROM jobs" + where, args).fetchone()[0]


def append_event(conn: sqlite3.Connection, job_id: int, event: Event) -> None:
    """Store ``event``; data whose JSON exceeds 64 KB is replaced by a size marker.

    Values JSON cannot hold are stored as their ``str`` (NaN and infinity as null), so a
    stray object in event data never fails the job.
    """
    data = json.dumps(jsonable(event.data), ensure_ascii=False, allow_nan=False, default=str)
    size = len(data.encode())
    if size > MAX_EVENT_BYTES:
        data = _dumps({"truncated": True, "size": size})
    conn.execute(
        "INSERT INTO job_events (job_id, ts, type, data_json) VALUES (?, ?, ?, ?)",
        (job_id, event.ts, event.type, data),
    )


def events_since(
    conn: sqlite3.Connection, job_id: int, after_id: int = 0, *, limit: int = -1
) -> list[tuple[int, Event]]:
    """``(event id, event)`` pairs after ``after_id``, oldest first, at most ``limit`` (-1: no
    limit); pass the last id to page."""
    rows = conn.execute(
        "SELECT id, ts, type, data_json FROM job_events WHERE job_id = ? AND id > ?"
        " ORDER BY id LIMIT ?",
        (job_id, after_id, limit),
    ).fetchall()
    return [(r["id"], Event(r["type"], r["ts"], json.loads(r["data_json"]))) for r in rows]


def delete_job(conn: sqlite3.Connection, job_id: int) -> None:
    """Delete a finished job and its events; queued or running jobs raise ValueError."""
    if get_job(conn, job_id).status not in TERMINAL:
        raise ValueError(f"job {job_id} is not finished")
    conn.execute("DELETE FROM jobs WHERE id = ? AND status IN (?, ?, ?)", (job_id, *TERMINAL))


def delete_all_jobs(conn: sqlite3.Connection, project_id: str | None) -> int:
    """Delete the project's finished jobs, leaving queued and running ones; returns the count."""
    cur = conn.execute(
        "DELETE FROM jobs WHERE project_id IS ? AND status IN (?, ?, ?)", (project_id, *TERMINAL)
    )
    return cur.rowcount


# Transitions used by the runner and the worker.


def claim_job(conn: sqlite3.Connection, job_id: int, run_token: str) -> bool:
    """queued -> running with ``run_token``; False if the job is no longer queued."""
    cur = conn.execute(
        "UPDATE jobs SET status = 'running', run_token = ?, started_at = ?"
        " WHERE id = ? AND status = 'queued'",
        (run_token, time.time(), job_id),
    )
    return cur.rowcount == 1


def set_pid(conn: sqlite3.Connection, job_id: int, pid: int) -> None:
    conn.execute("UPDATE jobs SET pid = ? WHERE id = ?", (pid, job_id))


def cancel_queued(conn: sqlite3.Connection, job_id: int) -> bool:
    cur = conn.execute(
        "UPDATE jobs SET status = 'cancelled', finished_at = ? WHERE id = ? AND status = 'queued'",
        (time.time(), job_id),
    )
    return cur.rowcount == 1


def request_cancel(conn: sqlite3.Connection, job_id: int) -> None:
    conn.execute("UPDATE jobs SET cancel_requested = 1 WHERE id = ?", (job_id,))


def stop_requested(conn: sqlite3.Connection, job_id: int) -> bool:
    """Whether the job's worker should stop: cancel requested, job finished or deleted."""
    row = conn.execute(
        "SELECT status, cancel_requested FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()
    return row is None or row["status"] != JobStatus.RUNNING or row["cancel_requested"] == 1


def cancel_requested(conn: sqlite3.Connection, job_id: int) -> bool:
    row = conn.execute("SELECT cancel_requested FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row is not None and row[0] == 1


def finish_job(
    conn: sqlite3.Connection,
    job_id: int,
    status: JobStatus,
    *,
    message: str | None = None,
    result: dict | None = None,
) -> bool:
    """running -> ``status``; False (nothing written) if the job already left running."""
    if status not in TERMINAL:
        raise ValueError(f"not a terminal status: {status}")
    cur = conn.execute(
        "UPDATE jobs SET status = ?, message = ?, result_json = ?, finished_at = ?"
        " WHERE id = ? AND status = 'running'",
        (status, message, None if result is None else _dumps(result), time.time(), job_id),
    )
    return cur.rowcount == 1
