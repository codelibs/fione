"""The ``module`` job: run a module over a dataset into a new dataset (and, for a ``train``
module, a stored state).

Built-in modules are plain functions. An uploaded module is arbitrary code: it is loaded here,
in the worker process and nowhere else, from a temporary copy of its stored source after the
source's SHA-256 is checked against the one recorded at upload. It is not sandboxed.
"""

import contextlib
import hashlib
import importlib.util
import json
import logging
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from fione.engine.events import Event
from fione.jobs.handlers import JobContext, JobUserError, register_handler
from fione.modules import registry, service
from fione.modules.registry import (
    TRAIN_FOR,
    Module,
    ModuleContext,
    ModuleError,
    ModuleOutput,
    normalize_result,
    redact,
    validate_output,
)
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.service import Dataset, DatasetType
from fione.schema import validate_args

log = logging.getLogger(__name__)

MAX_STATE_BYTES = 8 * 1024 * 1024
_NO_FILE = "the module file failed verification"


def _dataset(ctx: JobContext, dataset_id: int) -> Dataset:
    try:
        dataset = projects.get_dataset(ctx.conn, dataset_id)
        if dataset.project_id != ctx.job.project_id:
            raise projects.DatasetNotFound(dataset_id)
    except projects.DatasetNotFound as e:
        raise JobUserError("the dataset no longer exists") from e
    return dataset


def _load_uploaded(ctx: JobContext, stack: contextlib.ExitStack, module_id: str) -> Module:
    """The uploaded module, imported from a verified temporary copy that ``stack`` removes."""
    row = ctx.conn.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    if row is None:
        raise JobUserError("the module no longer exists")
    try:
        source = ctx.storage.get(service.module_key(module_id))
    except KeyError as e:
        raise JobUserError(_NO_FILE) from e
    if hashlib.sha256(source).hexdigest() != row["source_sha256"]:
        raise JobUserError(_NO_FILE)
    path = (
        Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="fione-module-"))) / "module.py"
    )
    path.write_bytes(source)
    name = f"fione_user_module_{uuid.uuid4().hex}"
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        loaded = importlib.util.module_from_spec(spec)
        sys.modules[name] = loaded  # decorators such as dataclass look the module up by name
        stack.callback(sys.modules.pop, name, None)
        spec.loader.exec_module(loaded)
        run = loaded.run
    except (Exception, SystemExit) as e:
        log.warning("module %s failed to load", module_id, exc_info=True)
        raise JobUserError(f"the module failed to load: {type(e).__name__}") from e
    info = service.get_module(ctx.conn, module_id)

    def run_uploaded(df, params, context):
        return normalize_result(run(df, params, context))

    return Module(info.id, info.name, info.kind, info.params, run_uploaded)


def _resolve(ctx: JobContext, stack: contextlib.ExitStack, module_id: str) -> Module:
    return registry.get_builtin(module_id) or _load_uploaded(ctx, stack, module_id)


def _load_state(ctx: JobContext, module: Module, model_id: int) -> dict:
    try:
        row = service.get_module_model(ctx.conn, ctx.job.project_id, model_id)
    except ValueError as e:
        raise JobUserError("the module model no longer exists") from e
    needed = TRAIN_FOR.get(module.id)
    if needed is not None and row["module_id"] != needed:
        raise JobUserError(f"{module.id} needs a model made by {needed}")
    try:
        state = json.loads(ctx.storage.get(row["state_key"]))
    except (KeyError, ValueError) as e:
        raise JobUserError("the module model file is damaged") from e
    if not isinstance(state, dict):
        raise JobUserError("the module model file is damaged")
    return state


def _run(module: Module, df, params: dict, context: ModuleContext) -> ModuleOutput:
    try:
        return module.run(df, params, context)
    except ModuleError as e:
        raise JobUserError(str(e)) from e
    except (Exception, SystemExit) as e:  # user code: say what failed, never where
        raise RuntimeError(
            f"module '{module.id}' raised {type(e).__name__}: {redact(str(e))}"
        ) from e


def _encode_state(module: Module, output: ModuleOutput) -> bytes | None:
    if module.kind != "train":
        if output.state is not None:
            raise ModuleError("only a train module can return a state")
        return None
    if output.state is None:
        raise ModuleError("a train module must return a state")
    if not isinstance(output.state, dict):
        raise ModuleError("the state must be a JSON object")
    try:
        data = json.dumps(output.state, ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError) as e:
        raise ModuleError(f"the state is not plain JSON: {e}") from None
    if len(data) > MAX_STATE_BYTES:
        raise ModuleError("the state is larger than 8 MB")
    return data


def _insert_model(
    ctx: JobContext, module_id: str, name: str, key: str, source_dataset_id: int
) -> int:
    cur = ctx.conn.execute(
        "INSERT INTO module_models (project_id, module_id, name, state_key, source_dataset_id,"
        " created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (ctx.job.project_id, module_id, name, key, source_dataset_id, time.time()),
    )
    return cur.lastrowid


def _store_model(
    ctx: JobContext,
    module_id: str,
    name: str,
    source_dataset_id: int,
    state: bytes,
    undo: list[Callable[[], None]],
) -> int:
    """Store the state object, then record it; ``undo`` gets what takes each step back."""
    key = f"projects/{ctx.job.project_id}/module_models/{uuid.uuid4().hex}/state.json"
    ctx.storage.put(key, state)
    undo.append(lambda: ctx.storage.delete(key))
    model_id = _insert_model(ctx, module_id, name, key, source_dataset_id)
    undo.append(lambda: ctx.conn.execute("DELETE FROM module_models WHERE id = ?", (model_id,)))
    return model_id


def _roll_back(undo: list[Callable[[], None]]) -> None:
    for step in reversed(undo):
        try:
            step()
        except Exception:
            # Never mask the original error (a JobAbort must stay a JobAbort).
            log.exception("could not undo a module result")


@register_handler("module")
def module(ctx: JobContext) -> None:
    """Run the module, store its result as a dataset (and model) and record it.

    A cancelled run leaves no dataset row, no model row and no objects: the stop flag is read
    forced right before the result is stored and again once everything is recorded, the second
    time undoing it all. A SIGKILL during the store can leave an unreferenced object under the
    project prefix; ``delete_project`` removes it.
    """
    payload = ctx.job.payload
    project_id = ctx.job.project_id
    start = time.monotonic()
    with contextlib.ExitStack() as stack:
        mod = _resolve(ctx, stack, payload["module_id"])
        try:
            params = validate_args(mod.params, payload["params"])
        except ValueError as e:
            raise JobUserError(str(e)) from e
        dataset = _dataset(ctx, payload["dataset_id"])
        other_id, model_id = params.get("other_dataset_id"), params.get("module_model_id")
        other = (
            ingest.read_dataset(ctx.storage, _dataset(ctx, other_id), nullable_dtypes=True)
            if other_id
            else None
        )
        state = _load_state(ctx, mod, model_id) if model_id else None
        frame = ingest.read_dataset(ctx.storage, dataset, nullable_dtypes=True)
        ctx.emit(
            Event(
                "started",
                data={"module_id": mod.id, "dataset_id": dataset.id, "n_rows": len(frame)},
            )
        )
        if ctx.should_stop():
            return
        try:
            output = _run(mod, frame, params, ModuleContext(other, state))
            result = validate_output(output.df)
            state_bytes = _encode_state(mod, output)
        except ModuleError as e:
            raise JobUserError(str(e)) from e
        if ctx.should_stop(force=True):  # nothing stored yet
            return
        name = payload.get("name") or f"{mod.id}_{dataset.name}"
        kind = DatasetType.PREDICT if mod.kind == "predict" else DatasetType.TRAIN
        try:
            created = ingest.ingest_batches(ctx.storage, ctx.conn, project_id, name, kind, [result])
        except ingest.IngestError as e:
            raise JobUserError(str(e)) from e
    undo: list[Callable[[], None]] = [
        lambda: projects.delete_dataset(ctx.conn, ctx.storage, created.id)
    ]
    try:
        new_model = None
        if state_bytes is not None:
            new_model = _store_model(ctx, mod.id, name, dataset.id, state_bytes, undo)
        if ctx.should_stop(force=True):  # cancelled while storing: take it all back out
            _roll_back(undo)
            return
        ctx.set_result(
            {
                "dataset_id": created.id,
                "n_rows": created.n_rows,
                "module_model_id": new_model,
                "elapsed": time.monotonic() - start,
            }
        )
        ctx.emit(Event("finished", data={"dataset_id": created.id, "n_rows": created.n_rows}))
    except BaseException:
        _roll_back(undo)
        raise
