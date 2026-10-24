"""Trained-model records (the ``models`` table), their artifacts in storage, and training jobs."""

import json
import sqlite3
import time
from dataclasses import dataclass

from fione.auth.roles import User, can_access_project
from fione.engine.artifact import load_model
from fione.engine.config import ConfigError, TrainConfig
from fione.engine.events import jsonable
from fione.engine.model import TrainedModel
from fione.jobs import store
from fione.jobs.store import Job
from fione.projects import service as projects
from fione.projects.service import DatasetNotFound, DatasetType
from fione.storage import Storage

ENSEMBLE = "Ensemble"


class ModelNotFound(KeyError):
    pass


@dataclass(frozen=True)
class ModelRecord:
    id: int
    project_id: str
    dataset_id: int | None
    job_id: int | None
    name: str
    task: str
    target: str
    best_model: str
    stop_reason: str
    storage_prefix: str
    trusted: int
    config: dict
    leaderboard: list[dict]  # best first; NaN as None
    trials: list[dict]
    metrics: dict
    importance: dict[str, float]
    created_at: float


def _record(row: sqlite3.Row) -> ModelRecord:
    return ModelRecord(
        id=row["id"],
        project_id=row["project_id"],
        dataset_id=row["dataset_id"],
        job_id=row["job_id"],
        name=row["name"],
        task=row["task"],
        target=row["target"],
        best_model=row["best_model"],
        stop_reason=row["stop_reason"],
        storage_prefix=row["storage_prefix"],
        trusted=row["trusted"],
        config=json.loads(row["config_json"]),
        leaderboard=json.loads(row["leaderboard_json"]),
        trials=json.loads(row["trials_json"]),
        metrics=json.loads(row["metrics_json"]),
        importance=json.loads(row["importance_json"]),
        created_at=row["created_at"],
    )


def _dumps(value) -> str:
    return json.dumps(jsonable(value), ensure_ascii=False, allow_nan=False)


def best_model_name(leaderboard: list[dict]) -> str:
    """The leaderboard's leader: ``Ensemble`` when several members carry weight, else the one
    member that does (the model's predictions are the weighted blend of its members).

    ``leaderboard`` is best first, as ``AutoML`` returns it. A dropped or zero-weight family
    is never the answer, even when its score would rank it above the blend.
    """
    members = [r["model"] for r in leaderboard if r["model"] != ENSEMBLE and (r["weight"] or 0) > 0]
    return members[0] if len(members) == 1 else ENSEMBLE


def add_model(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    dataset_id: int | None,
    job_id: int | None,
    name: str,
    model: TrainedModel,
    storage_prefix: str,
    trusted: bool = True,
) -> ModelRecord:
    """Record a model whose artifact is already saved under ``storage_prefix``."""
    leaderboard = jsonable(model.leaderboard.to_dict("records"))
    cur = conn.execute(
        "INSERT INTO models (project_id, dataset_id, job_id, name, task, target, best_model,"
        " stop_reason, storage_prefix, trusted, config_json, leaderboard_json, trials_json,"
        " metrics_json, importance_json, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            project_id,
            dataset_id,
            job_id,
            name,
            model.task,
            model.target,
            best_model_name(leaderboard),
            model.stop_reason,
            storage_prefix,
            int(trusted),
            _dumps(model.config.to_dict()),
            _dumps(leaderboard),
            _dumps(model.trials.to_dict("records")),
            _dumps(model.metrics),
            _dumps(model.feature_importance.to_dict()),
            time.time(),
        ),
    )
    return get_model(conn, cur.lastrowid)


def get_model(conn: sqlite3.Connection, model_id: int) -> ModelRecord:
    row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    if row is None:
        raise ModelNotFound(model_id)
    return _record(row)


def list_models(conn: sqlite3.Connection, project_id: str) -> list[ModelRecord]:
    """The project's models, newest first."""
    rows = conn.execute(
        "SELECT * FROM models WHERE project_id = ? ORDER BY created_at DESC, id DESC",
        (project_id,),
    ).fetchall()
    return [_record(r) for r in rows]


def load_trained(storage: Storage, record: ModelRecord, secret: bytes) -> TrainedModel:
    """Load the model's artifact. Nothing is unpickled unless its signature and hash verify
    (``UntrustedArtifactError`` otherwise), whatever ``record.trusted`` says."""
    return load_model(storage, record.storage_prefix, secret)


def delete_model(conn: sqlite3.Connection, storage: Storage, model_id: int) -> None:
    """Delete the objects, then the row, so a storage failure never leaves a row pointing at
    deleted data (the retry finds the row and removes what is left). A concurrent
    ``list_models`` can therefore briefly show a row whose objects are going away."""
    record = get_model(conn, model_id)
    storage.delete_prefix(record.storage_prefix)
    conn.execute("DELETE FROM models WHERE id = ?", (model_id,))


def submit_training(
    conn: sqlite3.Connection,
    user: User,
    project_id: str,
    dataset_id: int,
    config: TrainConfig | dict,
    *,
    name: str | None = None,
) -> Job:
    """Queue an ``automl`` job after checking everything the user can get wrong up front."""
    projects.require_project(conn, project_id)
    if not can_access_project(conn, user, project_id, "write"):
        raise PermissionError("write access to the project is required")
    dataset = projects.get_dataset(conn, dataset_id)
    if dataset.project_id != project_id:
        raise DatasetNotFound(dataset_id)
    if dataset.type != DatasetType.TRAIN:
        raise ValueError("training needs a train dataset")
    config = config.validate() if isinstance(config, TrainConfig) else TrainConfig.from_dict(config)
    columns = {column for column, _ in dataset.schema}
    if config.target not in columns:
        raise ConfigError(f"target column '{config.target}' is not in the data")
    unknown = [c for c in config.ignored_columns if c not in columns]
    if unknown:
        raise ConfigError(f"unknown columns in ignored_columns: {unknown}")
    payload = {"dataset_id": dataset_id, "config": config.to_dict(), "name": name}
    return store.enqueue(conn, "automl", project_id, user.id, payload)
