"""Tools that start work, for MCP clients only and only when ``FIONE_MCP_WRITE_ENABLED`` is set.

Each calls the service the REST route calls, as the token's user: the same checks, the same
write access to the project, the same job. The chat assistant never lists or calls them."""

import pyarrow as pa

from fione.auth.roles import can_access_project
from fione.engine.config import TargetError
from fione.jobs.store import Job
from fione.models import service as models
from fione.modules import service as modules
from fione.projects import service as projects
from fione.tools.registry import Tool, ToolContext, ToolError, register_action

_ID = {"type": "integer", "minimum": 1, "maximum": 2**63 - 1}  # SQLite integers
_PROJECT = {"type": "string", "maxLength": 64}
_NAME = {"type": "string", "maxLength": 100, "description": "optional name of the job"}


def _schema(properties: dict, required: list[str]) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _writable(ctx: ToolContext, project_id: str) -> None:
    """Unless the user may read the project, it does not exist for them; a reader is told."""
    projects.require_project(ctx.conn, project_id)
    if not can_access_project(ctx.conn, ctx.user, project_id, "read"):
        raise PermissionError("no read access")
    if not can_access_project(ctx.conn, ctx.user, project_id, "write"):
        raise ToolError("write access to the project is required")


def _name(args: dict) -> str | None:
    """The job's name as the REST routes take it: trimmed, and not empty when given."""
    name = args.get("name")
    if name is None:
        return None
    if not name.strip():
        raise ToolError("argument 'name' must not be empty")
    return name.strip()


def _queued(job: Job) -> dict:
    return {
        "job_id": job.id,
        "kind": job.kind,
        "status": job.status.value,
        "project_id": job.project_id,
        "next": "follow it with get_training_events (job_id) until it is done, failed or cancelled",
    }


def _submit(ctx: ToolContext, project_id: str, submit) -> dict:
    """``submit()`` as the REST routes run it: a service's ``ValueError`` is a message for the
    user (an Arrow or encoding error is not), and so is a ``PermissionError`` without an errno;
    one with an errno is left to ``call_tool``, which reports it as not allowed."""
    _writable(ctx, project_id)
    try:
        return _queued(submit())
    except OverflowError:  # an id parameter beyond SQLite's integers
        raise ToolError("a parameter is out of range") from None
    except PermissionError as e:
        if e.errno is not None:
            raise
        raise ToolError(str(e)) from None
    except TargetError as e:
        if e.code == "single_row_class":  # its message names a label, which is a cell value
            raise ToolError("a class of the target has only 1 row; each needs at least 2") from None
        raise ToolError(str(e)) from None
    except ValueError as e:
        if isinstance(e, pa.ArrowException | UnicodeError):
            raise
        raise ToolError(str(e)) from None


def _start_training(ctx: ToolContext, args: dict) -> dict:
    return _submit(
        ctx,
        args["project_id"],
        lambda: models.submit_training(
            ctx.conn,
            ctx.storage,
            ctx.user,
            args["project_id"],
            args["dataset_id"],
            args["config"],
            name=_name(args),
        ),
    )


def _start_batch_predict(ctx: ToolContext, args: dict) -> dict:
    return _submit(
        ctx,
        args["project_id"],
        lambda: models.submit_batch_predict(
            ctx.conn,
            ctx.user,
            args["project_id"],
            args["model_id"],
            args["dataset_id"],
            include_columns=args.get("include_columns"),
            name=_name(args),
            include_contributions=args["include_contributions"],
        ),
    )


def _run_module(ctx: ToolContext, args: dict) -> dict:
    return _submit(
        ctx,
        args["project_id"],
        lambda: modules.submit_module(
            ctx.conn,
            ctx.user,
            args["project_id"],
            args["module_id"],
            args["dataset_id"],
            args["params"],
            name=_name(args),
        ),
    )


def _list_modules(ctx: ToolContext, args: dict) -> dict:
    return {
        "modules": [
            {"id": m.id, "name": m.name, "kind": m.kind, "params": m.params, "builtin": m.builtin}
            for m in modules.list_modules(ctx.conn)
        ]
    }


for _tool in (
    Tool(
        "list_modules",
        "The modules run_module can run (built-in and uploaded) with each one's parameter schema.",
        _schema({}, []),
        True,
        _list_modules,
    ),
    Tool(
        "start_training",
        "Queue AutoML training on a train dataset of a project; returns the job to follow. "
        "`config` is the training configuration (`target` is required); "
        "propose_training_config suggests one.",
        _schema(
            {
                "project_id": _PROJECT,
                "dataset_id": _ID,
                "config": {"type": "object", "description": "the training configuration"},
                "name": _NAME,
            },
            ["project_id", "dataset_id", "config"],
        ),
        False,
        _start_training,
    ),
    Tool(
        "start_batch_predict",
        "Queue a prediction of a dataset by a trained model of the same project; returns the job.",
        _schema(
            {
                "project_id": _PROJECT,
                "model_id": _ID,
                "dataset_id": _ID,
                "include_columns": {
                    "type": "array",
                    "description": "input columns to copy next to the predictions",
                },
                "include_contributions": {"type": "boolean", "default": False},
                "name": _NAME,
            },
            ["project_id", "model_id", "dataset_id"],
        ),
        False,
        _start_batch_predict,
    ),
    Tool(
        "run_module",
        "Queue a module over a dataset of a project; `params` follow the module's parameter "
        "schema (list_modules). Returns the job.",
        _schema(
            {
                "project_id": _PROJECT,
                "module_id": {"type": "string", "maxLength": 40},
                "dataset_id": _ID,
                "params": {"type": "object", "default": {}},
                "name": _NAME,
            },
            ["project_id", "module_id", "dataset_id"],
        ),
        False,
        _run_module,
    ),
):
    register_action(_tool)
