"""Uploaded modules, and queueing a module job.

Uploaded modules are arbitrary Python written by an administrator. They are NOT sandboxed: the
only isolation is that they run in a job's worker process (never in the API process) with the
privileges of the application, so uploading is admin-only by design. To read an upload's
metadata its file is imported once in a short-lived subprocess with a scrubbed environment (no
``FIONE_*`` variables, no secrets); the API process never imports or runs it.
"""

import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from fione.auth.roles import User, can_access_project, require_admin
from fione.jobs import store
from fione.jobs.store import Job
from fione.modules import registry
from fione.modules.registry import KINDS, TRAIN_FOR, ModuleError, check_module_id, redact
from fione.projects import service as projects
from fione.projects.service import DatasetNotFound
from fione.schema import check_schema, clean_text, validate_args
from fione.storage import Storage

MAX_SOURCE_BYTES = 256 * 1024
INSPECT_TIMEOUT = 10.0
MAX_METADATA_BYTES = 64 * 1024
_MAX_NAME_LEN = 100


class ModuleNotFound(KeyError):
    pass


@dataclass(frozen=True)
class ModuleInfo:
    id: str
    name: str
    kind: str
    params: dict
    builtin: bool


def module_key(module_id: str) -> str:
    return f"modules/{check_module_id(module_id)}/module.py"


def _row_info(row: sqlite3.Row) -> ModuleInfo:
    return ModuleInfo(
        row["id"], row["name"], row["kind"], json.loads(row["params_json"]), builtin=False
    )


def list_modules(conn: sqlite3.Connection) -> list[ModuleInfo]:
    """The built-in modules, then the uploaded ones."""
    built = [ModuleInfo(m.id, m.name, m.kind, m.params, True) for m in registry.builtin_modules()]
    rows = conn.execute("SELECT * FROM modules ORDER BY id").fetchall()
    return built + [_row_info(r) for r in rows]


def get_module(conn: sqlite3.Connection, module_id) -> ModuleInfo:
    """The module ``module_id`` (built-in or uploaded); ``ModuleNotFound`` for anything else."""
    if isinstance(module_id, str) and (built := registry.get_builtin(module_id)):
        return ModuleInfo(built.id, built.name, built.kind, built.params, True)
    row = (
        conn.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
        if isinstance(module_id, str)
        else None
    )
    if row is None:
        raise ModuleNotFound(module_id)
    return _row_info(row)


# --- reading an upload's metadata in another process -----------------------------------------


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _inspect(path: Path, timeout: float) -> dict:
    """Run ``fione.modules.inspect`` on ``path`` and return what it printed, parsed."""
    with tempfile.TemporaryDirectory(prefix="fione-inspect-") as work:
        home = Path(work)
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "LANG": "C.UTF-8"}
        with (home / "out").open("wb") as out, (home / "err").open("wb") as err:
            proc = subprocess.Popen(
                [sys.executable, "-I", "-m", "fione.modules.inspect", str(path)],
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                cwd=home,
                env=env,
                start_new_session=True,
            )
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                raise ModuleError(f"the module took longer than {timeout:g} s to load") from None
            finally:
                _kill_group(proc)  # nothing it started may outlive the inspection
                proc.wait()
        if proc.returncode != 0:
            lines = (home / "err").read_text("utf-8", "replace").strip().splitlines()
            reason = redact(lines[-1])[:300] if lines else "no message"
            raise ModuleError(
                f"the module could not be loaded (exit code {proc.returncode}): {reason}"
            )
        data = (home / "out").read_bytes()
    try:
        if len(data) > MAX_METADATA_BYTES:
            raise ValueError
        return json.loads(data.decode("utf-8"))
    except ValueError:  # includes bad UTF-8 and bad JSON
        raise ModuleError("the module did not produce valid metadata") from None


def _check_metadata(meta) -> tuple[str, str, dict]:
    """``(name, kind, params)`` of what ``MODULE`` held, or ``ModuleError``."""
    module = meta.get("module") if isinstance(meta, dict) else None
    if not isinstance(module, dict):
        raise ModuleError("MODULE must be a dict with name, kind and params")
    name, kind = module.get("name"), module.get("kind")
    if not isinstance(name, str) or not clean_text(name, _MAX_NAME_LEN):
        raise ModuleError("MODULE['name'] must be a non-empty string")
    if kind not in KINDS:
        raise ModuleError(f"MODULE['kind'] must be one of {list(KINDS)}")
    try:
        params = check_schema(module.get("params"))
    except ValueError as e:
        raise ModuleError(f"MODULE['params'] is not valid: {e}") from None
    props = params["properties"]
    for key in ("other_dataset_id", "module_model_id"):
        if key in props and props[key]["type"] != "integer":
            raise ModuleError(f"parameter '{key}' must be an integer")
    if kind == "predict" and "module_model_id" not in props:
        raise ModuleError("a predict module needs an integer parameter 'module_model_id'")
    return clean_text(name, _MAX_NAME_LEN), kind, params


def _check_source(source) -> str:
    if not isinstance(source, bytes | bytearray):
        raise ValueError("the module source must be bytes")
    if len(source) > MAX_SOURCE_BYTES:
        raise ModuleError("the module source is larger than 256 KB")
    try:
        text = bytes(source).decode("utf-8")
    except UnicodeDecodeError:
        raise ModuleError("the module source must be UTF-8 text") from None
    try:
        compile(text, "module.py", "exec", dont_inherit=True)  # parses; nothing runs
    except SyntaxError as e:
        raise ModuleError(f"syntax error on line {e.lineno}: {e.msg}") from None
    except (ValueError, RecursionError, MemoryError):
        raise ModuleError("the module source cannot be compiled") from None
    return text


def upload_module(
    conn: sqlite3.Connection,
    storage: Storage,
    admin: User,
    module_id: str,
    source: bytes,
    *,
    inspect_timeout: float = INSPECT_TIMEOUT,
) -> ModuleInfo:
    """Store an uploaded module after reading its metadata in a subprocess (admin only)."""
    require_admin(admin)
    key = module_key(module_id)
    if registry.get_builtin(module_id) is not None:
        raise ValueError(f"'{module_id}' is the id of a built-in module")
    _check_source(source)
    if conn.execute("SELECT 1 FROM modules WHERE id = ?", (module_id,)).fetchone():
        raise ValueError(f"module '{module_id}' already exists; delete it first")
    with tempfile.TemporaryDirectory(prefix="fione-upload-") as work:
        path = Path(work) / "module.py"
        path.write_bytes(bytes(source))
        name, kind, params = _check_metadata(_inspect(path, inspect_timeout))
    try:
        conn.execute(
            "INSERT INTO modules (id, name, kind, params_json, source_sha256, uploaded_by,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                module_id,
                name,
                kind,
                json.dumps(params, ensure_ascii=False),
                hashlib.sha256(source).hexdigest(),
                admin.id,
                time.time(),
            ),
        )
    except sqlite3.IntegrityError:
        raise ValueError(f"module '{module_id}' already exists; delete it first") from None
    try:
        storage.put(key, bytes(source))
    except BaseException:
        conn.execute("DELETE FROM modules WHERE id = ?", (module_id,))
        raise
    return ModuleInfo(module_id, name, kind, params, builtin=False)


def delete_module(conn: sqlite3.Connection, storage: Storage, admin: User, module_id) -> None:
    require_admin(admin)
    check_module_id(module_id)
    if registry.get_builtin(module_id) is not None:
        raise ValueError("built-in modules cannot be deleted")
    if conn.execute("SELECT 1 FROM modules WHERE id = ?", (module_id,)).fetchone() is None:
        raise ModuleNotFound(module_id)
    conn.execute("DELETE FROM modules WHERE id = ?", (module_id,))
    storage.delete_prefix(f"modules/{module_id}/")


# --- queueing a job --------------------------------------------------------------------------


def get_module_model(conn: sqlite3.Connection, project_id: str, model_id: int) -> sqlite3.Row:
    """The trained-state row ``model_id`` of the project; ``ValueError`` if there is none."""
    row = conn.execute(
        "SELECT * FROM module_models WHERE id = ? AND project_id = ?", (model_id, project_id)
    ).fetchone()
    if row is None:
        raise ValueError("unknown module model")
    return row


def submit_module(
    conn: sqlite3.Connection,
    user: User,
    project_id: str,
    module_id: str,
    dataset_id: int,
    params: dict,
    *,
    name: str | None = None,
) -> Job:
    """Queue a ``module`` job after checking everything the user can get wrong up front."""
    projects.require_project(conn, project_id)
    if not can_access_project(conn, user, project_id, "write"):
        raise PermissionError("write access to the project is required")
    dataset = projects.get_dataset(conn, dataset_id)
    if dataset.project_id != project_id:
        raise DatasetNotFound(dataset_id)
    try:
        module = get_module(conn, module_id)
    except ModuleNotFound:
        raise ValueError("unknown module") from None
    clean = validate_args(module.params, params)
    other_id = clean.get("other_dataset_id")
    if other_id is not None and projects.get_dataset(conn, other_id).project_id != project_id:
        raise DatasetNotFound(other_id)
    model_id = clean.get("module_model_id")
    if model_id is not None:
        model = get_module_model(conn, project_id, model_id)
        needed = TRAIN_FOR.get(module.id)
        if needed is not None and model["module_id"] != needed:
            raise ValueError(f"{module.id} needs a model made by {needed}")
    if name is not None and not (isinstance(name, str) and 1 <= len(name.strip()) <= _MAX_NAME_LEN):
        raise ValueError(f"name must be 1-{_MAX_NAME_LEN} characters")
    payload = {"module_id": module.id, "dataset_id": dataset_id, "params": clean, "name": name}
    return store.enqueue(conn, "module", project_id, user.id, payload)
