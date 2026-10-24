import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class Role(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class ProjectAccess(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


@dataclass(frozen=True)
class User:
    id: int
    username: str
    role: Role


def require_admin(user: User) -> None:
    if user.role is not Role.ADMIN:
        raise PermissionError("admin role required")


def project_access(conn: sqlite3.Connection, user: User, project_id: str) -> ProjectAccess | None:
    """The user's access to a project from ownership or membership, ignoring global roles."""
    row = conn.execute(
        "SELECT p.owner_id, m.access FROM projects p"
        " LEFT JOIN project_members m ON m.project_id = p.id AND m.user_id = ?"
        " WHERE p.id = ?",
        (user.id, project_id),
    ).fetchone()
    if row is None:
        return None
    if row["owner_id"] == user.id:
        return ProjectAccess.OWNER
    return ProjectAccess(row["access"]) if row["access"] else None


def can_access_project(
    conn: sqlite3.Connection, user: User, project_id: str, need: Literal["read", "write"]
) -> bool:
    """Admins reach every project; others need ownership or membership.

    A global ``viewer`` is capped at read even as owner or ``editor`` member.
    """
    if need not in ("read", "write"):
        raise ValueError(f"need must be 'read' or 'write', not {need!r}")
    if user.role is Role.ADMIN:
        return True
    access = project_access(conn, user, project_id)
    if access is None:
        return False
    if need == "read":
        return True
    return user.role is not Role.VIEWER and access is not ProjectAccess.VIEWER
