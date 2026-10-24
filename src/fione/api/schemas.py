"""Request bodies (unknown fields are rejected) and the JSON shapes of responses.

Responses are built field by field here, so internal fields (password hashes, token hashes,
storage keys) can never leak by being added to a record.
"""

from typing import Annotated, Any, Literal

from fastapi import Path
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from fione.auth.passwords import MIN_PASSWORD_LENGTH
from fione.auth.roles import ProjectAccess, Role, User
from fione.auth.service import ApiToken
from fione.engine.events import Event
from fione.jobs.store import Job
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


def event_out(event_id: int, event: Event, *, admin: bool) -> dict:
    """The event; for non-admins an ``error`` event keeps only the first line of its
    message (no traceback, no worker log tail)."""
    data = event.data
    if event.type == "error" and not admin:
        error = data.get("error") if isinstance(data, dict) else None
        data = {"error": _first_line(error) if isinstance(error, str) else None}
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


def module_out(info: ModuleInfo) -> dict:
    return {
        "id": info.id,
        "name": info.name,
        "kind": info.kind,
        "params": info.params,
        "builtin": info.builtin,
    }
