"""Trained-model records (the ``models`` table), their artifacts in storage, and training jobs."""

import json
import sqlite3
import time
from dataclasses import dataclass

from fione.auth.roles import User, can_access_project
from fione.engine import metrics
from fione.engine.artifact import load_model
from fione.engine.config import ConfigError, TrainConfig
from fione.engine.events import jsonable
from fione.engine.model import TrainedModel
from fione.engine.prep import infer_task, validate_target
from fione.jobs import store
from fione.jobs.store import Job
from fione.predict.batch import check_include_columns
from fione.projects import service as projects
from fione.projects.ingest import read_dataset
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
    return insert_model(
        conn,
        project_id=project_id,
        dataset_id=dataset_id,
        job_id=job_id,
        name=name,
        task=model.task,
        target=model.target,
        best_model=best_model_name(leaderboard),
        stop_reason=model.stop_reason,
        storage_prefix=storage_prefix,
        trusted=trusted,
        config=model.config.to_dict(),
        leaderboard=leaderboard,
        trials=model.trials.to_dict("records"),
        metrics=model.metrics,
        importance=model.feature_importance.to_dict(),
    )


def insert_model(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    dataset_id: int | None,
    job_id: int | None,
    name: str,
    task: str,
    target: str,
    best_model: str,
    stop_reason: str,
    storage_prefix: str,
    trusted: bool,
    config: dict,
    leaderboard: list[dict],
    trials: list[dict],
    metrics: dict,
    importance: dict,
) -> ModelRecord:
    """Insert a ``models`` row from already-validated fields."""
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
            task,
            target,
            best_model,
            stop_reason,
            storage_prefix,
            int(trusted),
            _dumps(config),
            _dumps(leaderboard),
            _dumps(trials),
            _dumps(metrics),
            _dumps(importance),
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
    storage: Storage,
    user: User,
    project_id: str,
    dataset_id: int,
    config: TrainConfig | dict,
    *,
    name: str | None = None,
) -> Job:
    """Queue an ``automl`` job after checking everything the user can get wrong up front,
    the target column included: the whole column goes through the engine's own
    ``validate_target`` (``TargetError`` for gaps, a single value, too few rows...), and the
    metrics must apply to the resolved task (``ConfigError``)."""
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
    task = check_target(storage, dataset, config.target, config.task, config.nfolds)
    for field in ("stopping_metric", "sort_metric"):  # as AutoML.fit resolves them
        metrics.resolve(getattr(config, field), task, field)
    payload = {"dataset_id": dataset_id, "config": config.to_dict(), "name": name}
    return store.enqueue(conn, "automl", project_id, user.id, payload)


def check_target(storage: Storage, dataset, target: str, task: str, nfolds: int = 5) -> str:
    """The task training ``dataset`` on ``target`` would have (``auto`` resolved as the engine
    does); ``TargetError`` if the engine would refuse the whole target column, and
    ``DatasetNotFound`` if the dataset's data is gone from storage."""
    try:
        y = read_dataset(storage, dataset, [target])[target]
    except KeyError:  # storage: no such object
        raise DatasetNotFound(dataset.id) from None
    resolved = infer_task(y) if task == "auto" else task
    validate_target(y, resolved, nfolds)
    return resolved


def submit_batch_predict(
    conn: sqlite3.Connection,
    user: User,
    project_id: str,
    model_id: int,
    dataset_id: int,
    include_columns: list[str] | None = None,
    name: str | None = None,
) -> Job:
    """Queue a ``batch_predict`` job: ``dataset_id`` (of any type) through ``model_id``."""
    projects.require_project(conn, project_id)
    if not can_access_project(conn, user, project_id, "write"):
        raise PermissionError("write access to the project is required")
    if get_model(conn, model_id).project_id != project_id:
        raise ModelNotFound(model_id)
    dataset = projects.get_dataset(conn, dataset_id)
    if dataset.project_id != project_id:
        raise DatasetNotFound(dataset_id)
    check_include_columns([column for column, _ in dataset.schema], include_columns)
    payload = {
        "model_id": model_id,
        "dataset_id": dataset_id,
        "include_columns": include_columns,
        "name": name,
    }
    return store.enqueue(conn, "batch_predict", project_id, user.id, payload)
