"""The MCP workflow tools: create a project, upload a dataset inline, follow and cancel jobs,
and predict, as the token's user with the access the REST routes ask for (create a project as
an editor, write to upload or cancel, read to look or predict). Like the other action tools,
they are for MCP clients only and only when ``FIONE_MCP_WRITE_ENABLED`` is set; the chat never
lists them."""

import io
import json
import re
import time
from typing import Literal

from fione.auth.roles import Role, can_access_project
from fione.engine.artifact import UntrustedArtifactError, read_manifest
from fione.engine.events import jsonable
from fione.jobs import store
from fione.jobs.store import TERMINAL, Job, JobStatus
from fione.models import service as models
from fione.models.live import Busy, TooLarge, Untrusted
from fione.models.service import ModelNotFound
from fione.predict.batch import PredictInputError, batch_predict, class_columns, instances_frame
from fione.projects import service as projects
from fione.projects import upload_tokens
from fione.projects.ingest import IngestError, ingest_csv, read_dataset_rows
from fione.projects.service import DatasetType
from fione.tools.actions import _ID, _PROJECT, _schema, _writable
from fione.tools.builtin import _dataset_block
from fione.tools.registry import (
    MAX_RESULT_BYTES,
    Tool,
    ToolContext,
    ToolError,
    clean_text,
    fits,
    register_action,
)

_MESSAGE_CHARS = 200
MAX_WAIT_SECS = 15
_POLL_SECS = 0.5
_LISTED = 50  # jobs of one list_jobs call, the newest
# /mcp bodies are capped at 1 MiB; this leaves room for the JSON around the CSV text.
INLINE_UPLOAD_MAX_BYTES = 512 * 1024
_NAME_CHARS = 100  # a project or dataset name, as the REST routes allow
_UPLOAD_PATH = "/api/v1/uploads"  # routes_uploads, under the API prefix
_PARSE_ERROR = re.compile(r"Expected (\d+) columns?, got (\d+)")
MAX_PREDICT_ROWS = 1000
_PAGE_ROWS = 100  # rows of one get_predictions call unless asked for more or fewer
_SCALARS = (str, int, float, bool, type(None))


def _readable(ctx: ToolContext, project_id: str | None) -> None:
    """``PermissionError`` (or ``KeyError``, for a missing project) unless the user may read
    the project; a job without a project is for admins only."""
    if project_id is None:
        if ctx.user.role != Role.ADMIN:
            raise PermissionError("admin only")
        return
    projects.require_project(ctx.conn, project_id)
    if not can_access_project(ctx.conn, ctx.user, project_id, "read"):
        raise PermissionError("no read access")


def _job(ctx: ToolContext, job_id: int, need: Literal["read", "write"]) -> Job:
    """The job, resolved first and then authorized on its own project, as ``routes_jobs._job``
    does: a missing job and one the user may not read are the same refusal."""
    job = store.get_job(ctx.conn, job_id)
    if need == "write" and job.project_id is not None:
        _writable(ctx, job.project_id)
    else:
        _readable(ctx, job.project_id)
    return job


def _describe(ctx: ToolContext, job: Job) -> dict:
    """What a client needs to follow a job. The failure message can quote the user's data (a
    class label, a cell), so it is shown only where cell values may be."""
    result = None
    if job.result is not None:
        result = jsonable({k: v for k, v in job.result.items() if k != "key"})
    described = {
        "job_id": job.id,
        "kind": clean_text(job.kind),
        "status": job.status.value,
        "project_id": job.project_id,
        "message": clean_text(job.message, _MESSAGE_CHARS)
        if job.message and ctx.allow_samples
        else None,
        "result": result,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }
    if job.message and not ctx.allow_samples:
        described["message_hidden"] = True
    return described


def _get_job(ctx: ToolContext, args: dict) -> dict:
    return _describe(ctx, _job(ctx, args["job_id"], "read"))


def _wait_for_job(ctx: ToolContext, args: dict) -> dict:
    job = _job(ctx, args["job_id"], "read")
    timeout = args["timeout_secs"]
    start = time.monotonic()
    while job.status not in TERMINAL:
        left = timeout - (time.monotonic() - start)
        if left <= 0:
            break
        time.sleep(min(_POLL_SECS, left))
        job = store.get_job(ctx.conn, job.id)
    return {
        **_describe(ctx, job),
        "waited_secs": round(time.monotonic() - start, 1),
        "done": job.status in TERMINAL,
    }


def _list_jobs(ctx: ToolContext, args: dict) -> dict:
    status = JobStatus(args["status"]) if "status" in args else None
    if "project_id" in args:
        _readable(ctx, args["project_id"])
        ids = [args["project_id"]]
    else:
        ids = [p.id for p in projects.list_projects(ctx.conn, ctx.user)]
    found = [
        job for pid in ids for job in store.list_jobs(ctx.conn, pid, status=status, limit=_LISTED)
    ]
    found.sort(key=lambda j: (j.created_at, j.id), reverse=True)
    return {
        "jobs": [
            {
                "job_id": job.id,
                "kind": clean_text(job.kind),
                "status": job.status.value,
                "project_id": job.project_id,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "finished_at": job.finished_at,
            }
            for job in found[:_LISTED]
        ]
    }


def _cancel_job(ctx: ToolContext, args: dict) -> dict:
    job = _job(ctx, args["job_id"], "write")
    if job.status in TERMINAL:
        raise ToolError("the job has already finished")
    if ctx.cancel is None:
        raise ToolError("cancelling is not available")
    return _describe(ctx, ctx.cancel(job))


def _create_project(ctx: ToolContext, args: dict) -> dict:
    try:
        project = projects.create_project(ctx.conn, ctx.user, args["name"])
    except (PermissionError, ValueError) as e:  # fixed texts: no data in them
        raise ToolError(str(e)) from None
    return {"project_id": project.id, "name": clean_text(project.name, _NAME_CHARS)}


def _ingest_message(error: IngestError) -> str:
    """The one-line refusal for a CSV Fione cannot read. The parser's own text quotes the
    offending row, which is data, so only the two field counts are kept."""
    message = str(error)
    if not message.startswith("could not parse the CSV"):
        return clean_text(message, 200)
    found = _PARSE_ERROR.search(message)
    detail = f": a row has {found[2]} fields, the header {found[1]}" if found else ""
    return f"could not parse the CSV{detail}"


def _dataset_name(args: dict) -> str:
    name = args["name"].strip()
    if not 1 <= len(name) <= _NAME_CHARS:
        raise ToolError(f"name must be 1-{_NAME_CHARS} characters")
    return name


def _upload_dataset(ctx: ToolContext, args: dict) -> dict:
    _writable(ctx, args["project_id"])
    name = _dataset_name(args)
    try:
        data = args["csv_text"].encode()
    except UnicodeEncodeError:
        raise ToolError("csv_text is not valid text") from None
    if len(data) > INLINE_UPLOAD_MAX_BYTES:
        raise ToolError(
            f"csv_text is over {INLINE_UPLOAD_MAX_BYTES // 1024} KiB of UTF-8; "
            "use create_upload_url for a larger file"
        )
    try:
        dataset = ingest_csv(
            ctx.storage,
            ctx.conn,
            args["project_id"],
            name,
            DatasetType(args["type"]),
            io.BytesIO(data),
            max_bytes=INLINE_UPLOAD_MAX_BYTES,
        )
    except IngestError as e:
        raise ToolError(_ingest_message(e)) from None
    return {
        **_dataset_block(dataset),
        "schema": [{"name": clean_text(n), "type": clean_text(t)} for n, t in dataset.schema],
    }


def _create_upload_url(ctx: ToolContext, args: dict) -> dict:
    _writable(ctx, args["project_id"])
    name = _dataset_name(args)
    if ctx.base_url is None:
        raise ToolError("upload URLs are not available")
    token = upload_tokens.create(
        ctx.conn, ctx.user.id, args["project_id"], name, DatasetType(args["type"])
    )
    url = f"{ctx.base_url}{_UPLOAD_PATH}/{token}"
    return {
        "url": url,
        "method": "PUT",
        "expires_in": upload_tokens.TTL_SECS,
        "example": f"curl -T file.csv '{url}'",
    }


def _model(ctx: ToolContext, project_id: str, model_id: int) -> models.ModelRecord:
    """The model, resolved first and then authorized on its project, as ``routes_models._model``
    does; one that belongs to another project does not exist here."""
    _readable(ctx, project_id)
    record = models.get_model(ctx.conn, model_id)
    if record.project_id != project_id:
        raise PermissionError("the model belongs to another project")
    return record


def _cell(value):
    """A prediction as plain JSON data; text (a class label) passes through ``clean_text``."""
    value = jsonable(value)
    return clean_text(value) if isinstance(value, str) else value


def _rows(rows: list) -> list[dict]:
    if not rows:
        raise ToolError("argument 'rows' must have at least 1 item")
    for i, row in enumerate(rows):
        if not all(isinstance(v, _SCALARS) for v in row.values()):
            raise ToolError(f"row {i} has a value that is not a number, text, true, false or null")
    return rows


def _predict(ctx: ToolContext, args: dict) -> dict:
    record = _model(ctx, args["project_id"], args["model_id"])
    rows = _rows(args["rows"])
    if ctx.live_models is None:
        raise ToolError("predictions are not available")
    try:
        with ctx.live_models.use(record) as model:
            predictions = batch_predict(model, instances_frame(model, rows, "row"), [])
    except Untrusted:
        raise ToolError(
            "this model is an import this install did not sign; use start_batch_predict"
        ) from None
    except Busy:
        raise ToolError("the model is busy with another request; try again shortly") from None
    except TooLarge:
        raise ToolError(
            "this model is too large to predict here; use start_batch_predict"
        ) from None
    except ModelNotFound:
        raise ToolError("the model's files are gone") from None
    except UntrustedArtifactError:
        raise ToolError("the model's files failed verification") from None
    except PredictInputError as e:
        raise ToolError(clean_text(e, 200)) from None
    result = {
        "predictions": [
            {clean_text(name): _cell(value) for name, value in row.items()}
            for row in predictions.to_dict("records")
        ]
    }
    if not fits(result, ctx.max_result_bytes):  # never a silent cut: the rows are not stored
        limit = min(ctx.max_result_bytes, MAX_RESULT_BYTES)
        fitting = max(1, len(rows) * limit * 9 // 10 // len(json.dumps(result)))
        raise ToolError(
            f"the predictions of {len(rows)} rows would not fit in {limit // 1024} KiB; "
            f"send about {fitting} rows at a time, or use start_batch_predict "
            "(upload_dataset or create_upload_url first) for more"
        )
    return result


def _prediction_columns(ctx: ToolContext, job: Job, dataset: projects.Dataset) -> list[str]:
    """The names of the columns the batch job wrote for the model's predictions, as the model
    names them (the manifest is read, no model is loaded). The result may also hold input
    columns copied by ``include_columns`` and contributions, which this does not name."""
    try:
        record = models.get_model(ctx.conn, job.payload["model_id"])
        if record.project_id != job.project_id:
            raise KeyError
    except KeyError:
        raise ToolError("the model that made these predictions no longer exists") from None
    try:
        names = class_columns(read_manifest(ctx.storage, record.storage_prefix).classes)
    except UntrustedArtifactError:
        raise ToolError("the model's files are not readable") from None
    if not set(names) <= {name for name, _ in dataset.schema}:
        raise ToolError("the dataset does not hold this model's prediction columns")
    return names


def _get_predictions(ctx: ToolContext, args: dict) -> dict:
    _readable(ctx, args["project_id"])
    dataset = projects.get_dataset(ctx.conn, args["dataset_id"])
    if dataset.project_id != args["project_id"]:
        raise PermissionError("the dataset belongs to another project")
    job = store.producer_of(ctx.conn, dataset.id)
    if job is None or job.project_id != dataset.project_id:
        raise ToolError("the dataset is not the result of a batch prediction")
    names = _prediction_columns(ctx, job, dataset)
    frame = read_dataset_rows(ctx.storage, dataset, args["offset"], args["limit"], names)
    rows = [[_cell(v) for v in row] for row in frame.itertuples(index=False, name=None)]
    result = {
        "columns": [clean_text(name) for name in names],
        "rows": rows,
        "offset": args["offset"],
        "n_rows": dataset.n_rows,
    }
    while not fits(result, ctx.max_result_bytes):  # fewer rows, never fewer columns
        if len(rows) <= 1:
            raise ToolError("a row of predictions is too large to return")
        del rows[len(rows) - max(1, len(rows) // 10) :]
        result["truncated"] = True
    return result


for _tool in (
    Tool(
        "create_project",
        "Create a project that you own; returns its project_id.",
        _schema({"name": {"type": "string", "maxLength": _NAME_CHARS}}, ["name"]),
        False,
        _create_project,
    ),
    Tool(
        "upload_dataset",
        "Add a dataset to a project from CSV text sent inline (type train, test or predict), "
        f"at most {INLINE_UPLOAD_MAX_BYTES // 1024} KiB; use create_upload_url for larger "
        "files. Returns the dataset: id, row and column counts, column names and types.",
        _schema(
            {
                "project_id": _PROJECT,
                "name": {"type": "string", "maxLength": _NAME_CHARS},
                "type": {"type": "string", "enum": [t.value for t in DatasetType]},
                "csv_text": {"type": "string"},
            },
            ["project_id", "name", "type", "csv_text"],
        ),
        False,
        _upload_dataset,
    ),
    Tool(
        "create_upload_url",
        "Make a one-time URL for adding a dataset (type train, test or predict) to a project "
        "from a CSV file of any size up to the server's upload limit. It is valid for "
        f"{upload_tokens.TTL_SECS // 60} minutes and for one successful upload: send the file "
        "with the `example` command (an HTTP PUT of the raw CSV, no credentials needed); the "
        "answer is the dataset. Needs a shell; without one use upload_dataset for small files. "
        "Keep the URL private.",
        _schema(
            {
                "project_id": _PROJECT,
                "name": {"type": "string", "maxLength": _NAME_CHARS},
                "type": {"type": "string", "enum": [t.value for t in DatasetType]},
            },
            ["project_id", "name", "type"],
        ),
        False,
        _create_upload_url,
    ),
    Tool(
        "predict",
        f"Predict rows now with a trained model of a project (1 to {MAX_PREDICT_ROWS} rows, each "
        "an object with a value for every column the model reads; other keys are ignored). "
        "Returns one prediction per row, in order: `predict` and, for classification, the "
        "probability `p_<class>` of each class. The rows are not echoed or stored, and the "
        "result must fit in 32 KiB (a few hundred rows of a 3-class model; a larger batch is "
        "refused with the number of rows that fits). For more rows use upload_dataset or "
        "create_upload_url, then start_batch_predict and get_predictions.",
        _schema(
            {
                "project_id": _PROJECT,
                "model_id": _ID,
                "rows": {
                    "type": "array",
                    "items": {"type": "object"},
                    "maxItems": MAX_PREDICT_ROWS,
                },
            },
            ["project_id", "model_id", "rows"],
        ),
        False,
        _predict,
    ),
    Tool(
        "get_predictions",
        "Read the predictions of a finished start_batch_predict: pass the result dataset_id "
        "from its job. Returns `columns` (`predict` and `p_<class>`) and `rows` from `offset` "
        "(row number = offset + position), `limit` rows at most, fewer when the result would be "
        "too large (`truncated`: continue from offset + number of rows returned). The input "
        "columns copied with include_columns are never returned.",
        _schema(
            {
                "project_id": _PROJECT,
                "dataset_id": _ID,
                "offset": {"type": "integer", "minimum": 0, "maximum": 2**63 - 1, "default": 0},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_PREDICT_ROWS,
                    "default": _PAGE_ROWS,
                },
            },
            ["project_id", "dataset_id"],
        ),
        True,
        _get_predictions,
    ),
    Tool(
        "get_job",
        "The status of a job (queued, running, done, failed, cancelled) and, once it has "
        "finished, its result (training: model_id; batch prediction: dataset_id).",
        _schema({"job_id": _ID}, ["job_id"]),
        True,
        _get_job,
    ),
    Tool(
        "wait_for_job",
        f"As get_job, but waits up to timeout_secs (at most {MAX_WAIT_SECS}) for the job to "
        "finish; `done` says whether it has. Call it again while it is false.",
        _schema(
            {
                "job_id": _ID,
                "timeout_secs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_WAIT_SECS,
                    "default": 10,
                },
            },
            ["job_id"],
        ),
        True,
        _wait_for_job,
    ),
    Tool(
        "list_jobs",
        f"The newest jobs (at most {_LISTED}), newest first, of one project or of every project "
        "you can read; optionally only those with one status.",
        _schema(
            {
                "project_id": _PROJECT,
                "status": {"type": "string", "enum": [s.value for s in JobStatus]},
            },
            [],
        ),
        True,
        _list_jobs,
    ),
    Tool(
        "cancel_job",
        "Cancel a queued or running job of a project you may change; a finished job cannot be "
        "cancelled.",
        _schema({"job_id": _ID}, ["job_id"]),
        False,
        _cancel_job,
    ),
):
    register_action(_tool)
