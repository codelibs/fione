"""Request bodies (unknown fields are rejected) and the JSON shapes of responses.

Responses are built field by field here, so internal fields (password hashes, token hashes,
storage keys) can never leak by being added to a record.
"""

import math
from typing import Annotated, Any, Literal

import numpy as np
from fastapi import Path
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from fione.auth.passwords import MIN_PASSWORD_LENGTH
from fione.auth.roles import ProjectAccess, Role, User
from fione.auth.service import ApiToken
from fione.engine.diagnostics import _label
from fione.engine.events import Event
from fione.engine.explain import ICE_ROWS, PD_GRID, PD_ROWS, Contributions, PartialDependence
from fione.jobs.store import Job
from fione.models.explanations import Explanation
from fione.models.service import ModelRecord
from fione.modules.registry import redact
from fione.modules.service import ModuleInfo
from fione.projects.service import Dataset, Project

MAX_PASSWORD_LENGTH = 1024

# SQLite integers are signed 64-bit; a larger id would be an OverflowError, not a 404.
MAX_ID = 2**63 - 1
IdPath = Annotated[int, Path(ge=1, le=MAX_ID)]
DbId = Annotated[int, Field(ge=1, le=MAX_ID)]

Username = Annotated[str, StringConstraints(min_length=1, max_length=64)]
Password = Annotated[str, StringConstraints(min_length=1, max_length=MAX_PASSWORD_LENGTH)]
NewPassword = Annotated[
    str, StringConstraints(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginIn(Body):
    username: Username
    password: Password


class FirstAdminIn(Body):
    username: Username
    password: NewPassword
    setup_token: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class PasswordChangeIn(Body):
    current_password: Password
    new_password: NewPassword


class UserIn(Body):
    username: Username
    password: NewPassword
    role: Role


class UserPatch(Body):
    role: Role | None = None
    password: NewPassword | None = None


class TokenIn(Body):
    name: Name


class ProjectIn(Body):
    name: Name


class ShareIn(Body):
    username: Username
    access: Literal["editor", "viewer"]


class AutomlIn(Body):
    dataset_id: DbId
    config: dict[str, Any]  # a TrainConfig; checked by models.service.submit_training
    name: Name | None = None


class BatchPredictIn(Body):
    model_id: DbId
    dataset_id: DbId
    include_columns: list[str] | None = None
    name: Name | None = None


class ModuleJobIn(Body):
    module_id: Annotated[str, StringConstraints(min_length=1, max_length=40)]
    dataset_id: DbId
    params: dict[str, Any] = Field(default_factory=dict)
    name: Name | None = None


MAX_CONTRIBUTION_ROWS = 100
Scalar = str | int | float | bool | None
ClassIndex = Annotated[int, Field(strict=True, ge=0)]  # not a bool


class ContributionsIn(Body):
    """The rows to explain: ``instances`` (objects keyed by column, like Fione Serving's), or
    ``limit`` rows of ``dataset_id`` from ``offset``."""

    instances: (
        Annotated[list[dict[str, Scalar]], Field(min_length=1, max_length=MAX_CONTRIBUTION_ROWS)]
        | None
    ) = None
    dataset_id: DbId | None = None
    offset: Annotated[int, Field(ge=0, le=MAX_ID)] = 0
    limit: Annotated[int, Field(ge=1, le=MAX_CONTRIBUTION_ROWS)] = 10
    class_index: ClassIndex | None = None

    @model_validator(mode="after")
    def _one_source(self):
        if (self.instances is None) == (self.dataset_id is None):
            raise ValueError("give either instances or dataset_id")
        return self


class PartialDependenceIn(Body):
    column: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    dataset_id: DbId | None = None
    grid: Annotated[int, Field(ge=2, le=PD_GRID)] = PD_GRID
    rows: Annotated[int, Field(ge=1, le=PD_ROWS)] = PD_ROWS
    ice: Annotated[int, Field(ge=0, le=ICE_ROWS)] = ICE_ROWS
    class_index: ClassIndex | None = None


class ExplainJobIn(Body):
    model_id: DbId
    dataset_id: DbId | None = None


def user_out(user: User) -> dict:
    return {"id": user.id, "username": user.username, "role": user.role.value}


def token_out(token: ApiToken) -> dict:
    return {
        "id": token.id,
        "user_id": token.user_id,
        "name": token.name,
        "created_at": token.created_at,
        "revoked": token.revoked,
    }


def project_out(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "owner_id": project.owner_id,
        "created_at": project.created_at,
    }


def members_out(members: list[tuple[str, ProjectAccess]]) -> list[dict]:
    return [{"username": username, "access": access.value} for username, access in members]


def dataset_out(dataset: Dataset, *, schema: bool = False) -> dict:
    out = {
        "id": dataset.id,
        "project_id": dataset.project_id,
        "name": dataset.name,
        "type": dataset.type.value,
        "n_rows": dataset.n_rows,
        "n_cols": dataset.n_cols,
        "created_at": dataset.created_at,
    }
    if schema:
        out["schema"] = [{"name": name, "type": dtype} for name, dtype in dataset.schema]
    return out


def _first_line(text: str | None) -> str | None:
    """What a non-admin sees of an error: its first line, without file paths."""
    if not text:
        return text
    lines = text.strip().splitlines()
    return redact(lines[0]) if lines else ""


def job_out(job: Job, *, admin: bool) -> dict:
    """The job. ``stop_reason`` and ``degraded`` come from a training result; non-admins get
    only the first line of the error ``message`` (no tracebacks or paths)."""
    result = None if job.result is None else {k: v for k, v in job.result.items() if k != "key"}
    return {
        "id": job.id,
        "kind": job.kind,
        "project_id": job.project_id,
        "owner_id": job.owner_id,
        "status": job.status.value,
        "payload": job.payload,
        "result": result,
        "message": job.message if admin else _first_line(job.message),
        "stop_reason": (result or {}).get("stop_reason"),
        "degraded": bool((result or {}).get("degraded")),
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


_ADMIN_ONLY_FIELDS = ("traceback", "log_tail")


def event_out(event_id: int, event: Event, *, admin: bool) -> dict:
    """The event, never with a storage ``key``. Non-admins get no traceback or worker log
    tail, and only the first line of
    an error: the ``error`` field, and the ``message`` of an engine error notice (one that
    names its ``exception``)."""
    data = event.data
    if isinstance(data, dict) and "key" in data:  # a storage key (export events)
        data = {k: v for k, v in data.items() if k != "key"}
    if not admin and isinstance(data, dict):
        data = {k: v for k, v in data.items() if k not in _ADMIN_ONLY_FIELDS}
        for key in ("error", "message") if "exception" in data else ("error",):
            if isinstance(data.get(key), str):
                data[key] = _first_line(data[key])
    return {"id": event_id, "type": event.type, "ts": event.ts, "data": data}


def model_out(record: ModelRecord, *, detail: bool = False) -> dict:
    out = {
        "id": record.id,
        "project_id": record.project_id,
        "dataset_id": record.dataset_id,
        "job_id": record.job_id,
        "name": record.name,
        "task": record.task,
        "target": record.target,
        "best_model": record.best_model,
        "stop_reason": record.stop_reason,
        # Training hit an error and kept what it had: the model works but may be weaker.
        "degraded": record.stop_reason == "error",
        "trusted": bool(record.trusted),
        "metrics": record.metrics,
        "created_at": record.created_at,
    }
    if detail:
        out |= {
            "config": record.config,
            "leaderboard": record.leaderboard,
            "trials": record.trials,
            "importance": record.importance,
        }
    return out


def _float(value) -> float | None:
    value = float(value)
    return value if math.isfinite(value) else None


def _floats(values: np.ndarray) -> list:
    """``values`` as nested lists of floats (None where not finite)."""
    if values.ndim == 1:
        return [_float(v) for v in values]
    return [_floats(row) for row in values]


def diagnostics_out(record: ModelRecord) -> dict:
    """The model's stored diagnostics (``None`` before Phase 2a, or when they could not be
    stored). Their size is capped when stored; labels in them are data, not markup."""
    return {"model_id": record.id, "diagnostics": record.diagnostics}


def explanation_out(
    model_id: int, status: str, job: Job | None, explanation: Explanation | None
) -> dict:
    """``status`` and its ``job_id``: the stored explanation's job when ``done``, else the
    latest explain job. The stored ``explanation`` (``None`` if there is none) is served even
    while a newer job runs; it may have been trimmed to its size cap, and its names and
    labels are data, not markup."""
    done = status == "done" and explanation is not None
    return {
        "model_id": model_id,
        "status": status,
        "job_id": explanation.job_id if done else (job.id if job is not None else None),
        "dataset_id": explanation.dataset_id if explanation is not None else None,
        "computed_at": explanation.created_at if explanation is not None else None,
        "explanation": explanation.payload if explanation is not None else None,
    }


def contributions_out(
    model_id: int, c: Contributions, slots: np.ndarray, first_row: int, multiclass: bool
) -> dict:
    """Per row, the output ``slots`` picks: its prediction, the bias and each column's
    contribution, which add up to the prediction. ``class_index`` is set for multiclass."""
    rows = []
    for i, slot in enumerate(slots.tolist()):
        values = c.values[i, slot]
        rows.append(
            {
                "row": first_row + i,
                "prediction": _float(c.prediction[i, slot]),
                "class_index": slot if multiclass else None,
                "bias": _float(c.bias[i, slot]),
                "contributions": {
                    column: _float(v) for column, v in zip(c.columns, values, strict=True)
                },
            }
        )
    return {"model_id": model_id, "outputs": [_label(o) for o in c.outputs], "rows": rows}


def partial_dependence_out(curve: PartialDependence) -> dict:
    return {
        "column": curve.column,
        "kind": curve.kind,
        "grid": [_label(value) for value in curve.grid],
        "outputs": [_label(output) for output in curve.outputs],
        "average": _floats(curve.average),
        "ice": _floats(curve.ice),
        "ice_output": curve.ice_output,
        "n_rows": curve.n_rows,
    }


def module_out(info: ModuleInfo) -> dict:
    return {
        "id": info.id,
        "name": info.name,
        "kind": info.kind,
        "params": info.params,
        "builtin": info.builtin,
    }
