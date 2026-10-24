import json
import re
import secrets
import sqlite3
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from fione.auth.roles import ProjectAccess, Role, User, project_access
from fione.storage import Storage

_MAX_NAME_LEN = 100
_MAX_SLUG_LEN = 40


class ProjectNotFound(KeyError):
    pass


class DatasetNotFound(KeyError):
    pass


class DatasetType(StrEnum):
    TRAIN = "train"
    TEST = "test"
    PREDICT = "predict"


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    owner_id: int
    created_at: str


@dataclass(frozen=True)
class Dataset:
    id: int
    project_id: str
    name: str
    type: DatasetType
    n_rows: int
    n_cols: int
    schema: list[tuple[str, str]]
    key: str
    created_at: str


def _project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"], name=row["name"], owner_id=row["owner_id"], created_at=row["created_at"]
    )


def _dataset(row: sqlite3.Row) -> Dataset:
    return Dataset(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        type=DatasetType(row["type"]),
        n_rows=row["n_rows"],
        n_cols=row["n_cols"],
        schema=[(name, dtype) for name, dtype in json.loads(row["schema_json"])],
        key=row["storage_key"],
        created_at=row["created_at"],
    )


def _slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:_MAX_SLUG_LEN].strip("-")
    return slug or "project"


def require_project(conn: sqlite3.Connection, project_id: str) -> Project:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise ProjectNotFound(project_id)
    return _project(row)


def _require_owner_or_admin(conn: sqlite3.Connection, user: User, project_id: str) -> None:
    if user.role != Role.ADMIN and project_access(conn, user, project_id) != ProjectAccess.OWNER:
        raise PermissionError("only the project owner or an admin can do this")


def create_project(conn: sqlite3.Connection, owner: User, name: str) -> Project:
    if owner.role == Role.VIEWER:
        raise PermissionError("viewers cannot create projects")
    name = name.strip()
    if not 1 <= len(name) <= _MAX_NAME_LEN:
        raise ValueError(f"project name must be 1-{_MAX_NAME_LEN} characters")
    slug = _slugify(name)
    while True:
        project_id = f"{slug}-{secrets.token_hex(3)}"
        try:
            conn.execute(
                "INSERT INTO projects (id, name, owner_id) VALUES (?, ?, ?)",
                (project_id, name, owner.id),
            )
            break
        except sqlite3.IntegrityError as e:
            if "projects.id" not in str(e):
                raise
    return require_project(conn, project_id)


def list_projects(conn: sqlite3.Connection, user: User) -> list[Project]:
    if user.role == Role.ADMIN:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at, id").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM projects WHERE owner_id = ?"
            " OR id IN (SELECT project_id FROM project_members WHERE user_id = ?)"
            " ORDER BY created_at, id",
            (user.id, user.id),
        ).fetchall()
    return [_project(r) for r in rows]


def delete_project(conn: sqlite3.Connection, storage: Storage, user: User, project_id: str) -> None:
    require_project(conn, project_id)
    _require_owner_or_admin(conn, user, project_id)
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    storage.delete_prefix(f"projects/{project_id}/")


def share_project(
    conn: sqlite3.Connection,
    owner: User,
    project_id: str,
    username: str,
    access: ProjectAccess,
) -> None:
    require_project(conn, project_id)
    _require_owner_or_admin(conn, owner, project_id)
    access = ProjectAccess(access)
    if access == ProjectAccess.OWNER:
        raise ValueError("access must be 'editor' or 'viewer'")
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        raise ValueError(f"unknown user: {username}")
    if row["id"] == require_project(conn, project_id).owner_id:
        raise ValueError("the owner already has full access")
    conn.execute(
        "INSERT INTO project_members (project_id, user_id, access) VALUES (?, ?, ?)"
        " ON CONFLICT (project_id, user_id) DO UPDATE SET access = excluded.access",
        (project_id, row["id"], access.value),
    )


def unshare_project(conn: sqlite3.Connection, owner: User, project_id: str, username: str) -> bool:
    """Remove a member; False if ``username`` was not one."""
    require_project(conn, project_id)
    _require_owner_or_admin(conn, owner, project_id)
    cur = conn.execute(
        "DELETE FROM project_members WHERE project_id = ?"
        " AND user_id = (SELECT id FROM users WHERE username = ?)",
        (project_id, username),
    )
    return cur.rowcount > 0


def list_members(conn: sqlite3.Connection, project_id: str) -> list[tuple[str, ProjectAccess]]:
    """``(username, access)`` of each member (the owner is not one), by username."""
    require_project(conn, project_id)
    rows = conn.execute(
        "SELECT u.username, m.access FROM project_members m JOIN users u ON u.id = m.user_id"
        " WHERE m.project_id = ? ORDER BY u.username",
        (project_id,),
    )
    return [(r["username"], ProjectAccess(r["access"])) for r in rows]


def reserve_dataset_id(conn: sqlite3.Connection) -> int:
    """Claim the next dataset id before its data is stored, so the storage key can embed it.

    Bumps the AUTOINCREMENT counter, so the id is never handed out again even if the
    ingest fails and no row is ever inserted.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT seq FROM sqlite_sequence WHERE name = 'datasets'").fetchone()
        if row is None:
            dataset_id = 1
            conn.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('datasets', 1)")
        else:
            dataset_id = row["seq"] + 1
            conn.execute(
                "UPDATE sqlite_sequence SET seq = ? WHERE name = 'datasets'", (dataset_id,)
            )
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    return dataset_id


def add_dataset(
    conn: sqlite3.Connection,
    project_id: str,
    name: str,
    type: DatasetType,
    n_rows: int,
    n_cols: int,
    schema: list[tuple[str, str]],
    key: str,
    dataset_id: int | None = None,
) -> Dataset:
    """Record a dataset whose data is already stored under ``key``."""
    cur = conn.execute(
        "INSERT INTO datasets"
        " (id, project_id, name, type, n_rows, n_cols, schema_json, storage_key)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            dataset_id,
            project_id,
            name,
            DatasetType(type).value,
            n_rows,
            n_cols,
            json.dumps(schema),
            key,
        ),
    )
    return get_dataset(conn, cur.lastrowid)


def list_datasets(conn: sqlite3.Connection, project_id: str) -> list[Dataset]:
    require_project(conn, project_id)
    rows = conn.execute(
        "SELECT * FROM datasets WHERE project_id = ? ORDER BY id", (project_id,)
    ).fetchall()
    return [_dataset(r) for r in rows]


def get_dataset(conn: sqlite3.Connection, dataset_id: int) -> Dataset:
    row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    if row is None:
        raise DatasetNotFound(dataset_id)
    return _dataset(row)


def delete_dataset(conn: sqlite3.Connection, storage: Storage, dataset_id: int) -> None:
    dataset = get_dataset(conn, dataset_id)
    conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
    storage.delete(dataset.key)
