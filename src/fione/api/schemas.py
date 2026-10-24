"""Request bodies (unknown fields are rejected) and the JSON shapes of responses.

Responses are built field by field here, so internal fields (password hashes, token hashes,
storage keys) can never leak by being added to a record.
"""

from typing import Annotated, Literal

from fastapi import Path
from pydantic import BaseModel, ConfigDict, StringConstraints

from fione.auth.passwords import MIN_PASSWORD_LENGTH
from fione.auth.roles import ProjectAccess, Role, User
from fione.auth.service import ApiToken
from fione.projects.service import Dataset, Project

MAX_PASSWORD_LENGTH = 1024

# SQLite integers are signed 64-bit; a larger id would be an OverflowError, not a 404.
IdPath = Annotated[int, Path(ge=1, le=2**63 - 1)]

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
