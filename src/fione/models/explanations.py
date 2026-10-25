"""Precomputed model explanations (the ``model_explanations`` table) and the jobs that make
them.

An explanation is the payload of the ``explain`` job (``fione.jobs.explain_handler``): global
importance from contributions and the top partial dependence curves, at most one per model.
A rerun replaces it; deleting the model deletes it. The stored text is checked again when it
is read, and whoever shows it must still treat its names and labels as untrusted.
"""

import json
import logging
import sqlite3
import time
from dataclasses import dataclass

from fione.auth.roles import User, can_access_project
from fione.jobs import store
from fione.jobs.store import Job, JobStatus
from fione.models.service import ModelNotFound, ModelRecord, get_model
from fione.projects import service as projects
from fione.projects.service import DatasetNotFound

log = logging.getLogger(__name__)

VERSION = 1
MAX_EXPLANATION_BYTES = 1024 * 1024  # of UTF-8 JSON
NO_TRAINING_DATA = (
    "the training data is no longer available; choose a dataset that has the model's columns"
)


@dataclass(frozen=True)
class Explanation:
    model_id: int
    job_id: int | None
    dataset_id: int | None
    payload: dict
    created_at: float


def payload_json(payload: dict) -> str:
    """``payload`` as strict JSON; ``ValueError`` if it is not, or exceeds the cap."""
    text = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    size = len(text.encode("utf-8"))
    if size > MAX_EXPLANATION_BYTES:
        raise ValueError(f"the explanation is too large to store: {size} bytes")
    return text


def save_explanation(
    conn: sqlite3.Connection, model_id: int, job_id: int | None, dataset_id: int | None, payload
) -> None:
    """Store ``payload`` as the model's explanation, replacing any earlier one."""
    conn.execute(
        "INSERT INTO model_explanations (model_id, job_id, dataset_id, payload_json, created_at)"
        " VALUES (?, ?, ?, ?, ?) ON CONFLICT(model_id) DO UPDATE SET job_id = excluded.job_id,"
        " dataset_id = excluded.dataset_id, payload_json = excluded.payload_json,"
        " created_at = excluded.created_at",
        (model_id, job_id, dataset_id, payload_json(payload), time.time()),
    )


def get_explanation(conn: sqlite3.Connection, model_id: int) -> Explanation | None:
    """The model's explanation; None when there is none, or its stored text is not a version
    1 payload (a warning is logged)."""
    row = conn.execute(
        "SELECT * FROM model_explanations WHERE model_id = ?", (model_id,)
    ).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(row["payload_json"])
    except ValueError:
        payload = None
    version = payload.get("version") if isinstance(payload, dict) else None
    if type(version) is not int or version != VERSION:  # True == 1, but is no version
        log.warning("the explanation of model %s is not readable", model_id)
        return None
    return Explanation(
        row["model_id"], row["job_id"], row["dataset_id"], payload, row["created_at"]
    )


def latest_explain_job(conn: sqlite3.Connection, model_id: int) -> Job | None:
    """The newest ``explain`` job of the model, in the model's project, whatever its status."""
    row = conn.execute(
        "SELECT id FROM jobs WHERE kind = 'explain'"
        " AND project_id = (SELECT project_id FROM models WHERE id = ?)"
        " AND json_extract(payload_json, '$.model_id') = ?"
        " ORDER BY created_at DESC, id DESC LIMIT 1",
        (model_id, model_id),
    ).fetchone()
    return None if row is None else store.get_job(conn, row["id"])


def model_columns(record: ModelRecord) -> list[str]:
    """The model's input columns: its importance has one entry per column, so no artifact
    needs loading. Only a full record has them (``list_models_brief`` leaves them out)."""
    return list(record.importance)


def submit_explain(
    conn: sqlite3.Connection,
    user: User,
    project_id: str,
    model_id: int,
    dataset_id: int | None = None,
) -> Job:
    """Queue an ``explain`` job for the model on ``dataset_id``, or on its training data.

    A model without training data (an import, or a deleted dataset) needs a dataset, and the
    dataset must have every model column (``ValueError``). When the model's latest explain
    job, for the same ``dataset_id``, is still queued or running, that job is returned
    instead of a second one.
    """
    projects.require_project(conn, project_id)
    if not can_access_project(conn, user, project_id, "write"):
        raise PermissionError("write access to the project is required")
    record = get_model(conn, model_id)
    if record.project_id != project_id:
        raise ModelNotFound(model_id)
    chosen = record.dataset_id if dataset_id is None else dataset_id
    if chosen is None:
        raise ValueError(NO_TRAINING_DATA)
    dataset = projects.get_dataset(conn, chosen)
    if dataset.project_id != project_id:
        raise DatasetNotFound(chosen)
    present = {column for column, _ in dataset.schema}
    missing = [column for column in model_columns(record) if column not in present]
    if missing:
        raise ValueError(f"the dataset lacks the model's columns: {missing}")
    active = latest_explain_job(conn, model_id)
    if (
        active is not None
        and active.status in (JobStatus.QUEUED, JobStatus.RUNNING)
        and active.payload.get("dataset_id") == dataset_id
    ):
        return active
    payload = {"model_id": model_id, "dataset_id": dataset_id}
    return store.enqueue(conn, "explain", project_id, user.id, payload)
