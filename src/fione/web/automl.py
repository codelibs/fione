"""The AutoML detail screens (part 1): datasets with their column profiles and charts, the
full training form, and the project's job list.

Same services and authorization as the API (see ``web/access.py``); every post carries the
session's CSRF token in ``csrf_token``. Profiles and leak suspects come from bounded
per-app caches (datasets never change), and every list or preview is capped.
"""

import dataclasses
import logging
import math
import re
import time
from typing import Annotated
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from starlette.datastructures import FormData
from starlette.exceptions import HTTPException as StarletteHTTPException

from fione import i18n
from fione.api.deps import Conn
from fione.api.routes_datasets import cell
from fione.api.routes_jobs import delete_finished_job, delete_finished_jobs_of
from fione.api.schemas import job_out
from fione.engine import metrics
from fione.engine.config import ConfigError, TargetError, TrainConfig
from fione.jobs import store
from fione.jobs.store import TERMINAL, Job, JobStatus
from fione.models import service as models
from fione.modules.registry import redact
from fione.projects import service as projects
from fione.projects.ingest import read_dataset_rows
from fione.projects.service import Dataset, DatasetType
from fione.web.access import Ctx, action, dataset_in, job_in, page
from fione.web.easyml import (
    LEAK_REASONS,
    MAX_FORM_FIELDS,
    STOP_POLLING,
    _analysis,
    _clock,
    _default_target,
    _names,
    _pct,
    _profile,
)
from fione.web.uploads import UploadProblem, receive_csv, size_text, upload_context
from fione.web.views import UiError, language, render

log = logging.getLogger(__name__)
router = APIRouter(include_in_schema=False)

DATASETS_PER_PAGE = 50
COLUMNS_PER_PAGE = 100  # the Columns tab
DATA_DEFAULT_ROWS = 50
DATA_MAX_ROWS = 200  # the Data tab: rows per page
DATA_MAX_COLUMNS = 50  # and columns per page
TOP_PAIRS = 20  # correlations: what the profile keeps
JOBS_PER_PAGE = 50
POLL_ACTIVE, POLL_IDLE = "5s", "30s"  # job-list refresh
JOB_KINDS = ("automl", "batch_predict", "module", "export_models")
TASKS = ("auto", "classification", "regression")
MAX_RUNTIME_DIGITS = 6  # minutes, as in the wizard
SEED_MAX = 2**32 - 1  # numpy's RandomState (the folds) takes 0..2**32-1
# Training form fields: one value each, except ``inputs`` (one per checked column).
SINGLE_FIELDS = (
    "csrf_token",
    "target",
    "task",
    "max_runtime_minutes",
    "max_runtime_secs_per_model",
    "max_models",
    "nfolds",
    "seed",
    "balance_classes",
    "stopping_rounds",
    "stopping_metric",
    "stopping_tolerance",
    "sort_metric",
    "keep_cv_predictions",
    "keep_cv_models",
    "keep_cv_fold_assignment",
)
FLAGS = ("balance_classes", "keep_cv_predictions", "keep_cv_models", "keep_cv_fold_assignment")
_WHOLE = re.compile(r"[0-9]{1,18}")
_DECIMAL = re.compile(r"[0-9]{1,12}(\.[0-9]{1,12})?")


def _view(request: Request, template: str, ctx: Ctx, section: str, **context) -> Response:
    status = context.pop("status", 200)
    return render(
        request,
        template,
        ctx.auth,
        status=status,
        ctx=ctx,
        nav="projects",
        section=section,
        **context,
    )


def _int_param(value: str | None, default: int, low: int, high: int) -> int:
    """A paging parameter: digits only, clamped to [low, high]; anything else the default."""
    if value is None or not value.isascii() or not value.isdigit() or len(value) > 12:
        return default
    return min(high, max(low, int(value)))


def column_url(pid: str, did: int, name: str) -> str:
    """The column page. Names a path segment cannot carry (``.`` and ``..``, which browsers
    normalise away) go in the query instead."""
    base = f"/projects/{pid}/datasets/{did}/columns/"
    if name in (".", ".."):
        return base + "~?" + urlencode({"name": name})
    return base + quote(name, safe="")


# --- cached facts of immutable datasets ---------------------------------------------------


def _size(request: Request, dataset: Dataset) -> int | None:
    def read():
        try:
            return request.app.state.storage.size(dataset.key)
        except KeyError:  # the file is gone
            return None

    return request.app.state.ui_sizes.get(dataset.id, read)


def _leaks(request: Request, conn, ctx: Ctx, dataset: Dataset, target: str) -> dict:
    """Column name -> leak reason key for ``target`` (cached per dataset and target)."""

    def compute():
        found, _, _ = _analysis(request, conn, ctx, dataset, target)
        return {s.column: LEAK_REASONS.get(s.reason, "other") for s in found.profile.leak_suspects}

    return request.app.state.ui_leaks.get((dataset.id, target), compute)


# --- datasets -------------------------------------------------------------------------------


def _datasets_view(request: Request, conn, ctx: Ctx, *, status=200, problem=None) -> Response:
    total = projects.count_datasets(conn, ctx.project.id)
    pages = max(1, math.ceil(total / DATASETS_PER_PAGE))
    number = _int_param(request.query_params.get("page"), 1, 1, pages)
    offset = (number - 1) * DATASETS_PER_PAGE
    shown = projects.page_datasets(conn, ctx.project.id, limit=DATASETS_PER_PAGE, offset=offset)
    sizes = {d.id: _size(request, d) for d in shown}
    return _view(
        request,
        "datasets.html",
        ctx,
        "datasets",
        status=status,
        datasets=shown,
        total=total,
        page_number=number,
        pages=pages,
        sizes={k: (size_text(v) if v is not None else None) for k, v in sizes.items()},
        kinds=[t.value for t in DatasetType],
        limit=size_text(request.app.state.settings.max_upload_bytes),
        problem=problem,
    )


@router.get("/projects/{pid}/datasets")
def datasets(request: Request, conn: Conn, pid: str) -> Response:
    return _datasets_view(request, conn, page(request, conn, pid))


@router.post("/projects/{pid}/datasets")
async def upload_dataset(request: Request, conn: Conn, pid: str) -> Response:
    ctx = await upload_context(request, conn, pid)
    try:
        dataset = await receive_csv(request, conn, ctx, None)  # the kind comes with the form
    except UploadProblem as problem:
        return _datasets_view(request, conn, ctx, status=problem.status, problem=problem)
    return RedirectResponse(f"/projects/{pid}/datasets/{dataset.id}", 303)


async def _posted(request: Request) -> FormData | None:
    """The posted form, with room for one field per column; None if it has more. A form
    that cannot be read at all is a 400 page."""
    try:
        return await request.form(max_fields=MAX_FORM_FIELDS)
    except StarletteHTTPException as e:
        if e.status_code != 400:
            raise
        if str(e.detail).startswith("Too many fields"):  # Starlette's MultiPartException
            return None
        raise UiError(400, "error.form") from None


Posted = Annotated[FormData | None, Depends(_posted)]


def _text(form: FormData | None, name: str) -> str:
    value = form.get(name) if form is not None else None
    return value if isinstance(value, str) else ""


@router.post("/projects/{pid}/datasets/{did}/delete")
def delete_dataset(request: Request, conn: Conn, pid: str, did: str, form: Posted) -> Response:
    ctx = action(request, conn, pid, _text(form, "csrf_token"))
    dataset = dataset_in(conn, ctx, did)
    projects.delete_dataset(conn, request.app.state.storage, dataset.id)
    return RedirectResponse(f"/projects/{pid}/datasets", 303)


# --- dataset detail -----------------------------------------------------------------------


TABS = ("summary", "columns", "data", "correlation")


def _data_page(request: Request, dataset: Dataset) -> dict:
    """The Data tab's window: rows ``offset``..``offset+limit`` (limit at most 200) and at most
    50 columns from ``col``, read from the row groups that hold them."""
    q = request.query_params
    limit = _int_param(q.get("limit"), DATA_DEFAULT_ROWS, 1, DATA_MAX_ROWS)
    last = max(0, dataset.n_rows - 1)
    offset = _int_param(q.get("offset"), 0, 0, last)
    names = _names(dataset)
    col = _int_param(q.get("col"), 0, 0, max(0, len(names) - 1))
    columns = names[col : col + DATA_MAX_COLUMNS]
    frame = read_dataset_rows(request.app.state.storage, dataset, offset, limit, columns)
    rows = [[cell(v) for v in row] for row in frame.astype(object).itertuples(False, None)]
    numeric = [
        all(
            isinstance(r[i], int | float) and not isinstance(r[i], bool)
            for r in rows
            if r[i] is not None
        )
        for i in range(len(columns))
    ]
    return {
        "columns": columns,
        "rows": rows,
        "numeric": numeric,
        "offset": offset,
        "limit": limit,
        "col": col,
        "first_row": offset + 1 if rows else 0,
        "last_row": offset + len(rows),
        "prev": max(0, offset - limit) if offset > 0 else None,
        "next": offset + limit if offset + limit < dataset.n_rows else None,
        "last_page": max(0, dataset.n_rows - limit),
        "prev_col": max(0, col - DATA_MAX_COLUMNS) if col > 0 else None,
        "next_col": col + DATA_MAX_COLUMNS if col + DATA_MAX_COLUMNS < len(names) else None,
        "n_cols": len(names),
    }


def _chart(
    kind: str, labels: list, values: list, label: str, x_name: str, y_name: str, **axis
) -> dict:
    """What ``charts.js`` draws: plain data, never markup (``axis``: the value axis's
    ``min`` and ``max``)."""
    return {
        "type": kind,
        "labels": [str(v) for v in labels],
        "values": values,
        "label": label,
        "x_name": x_name,
        "y_name": y_name,
        **axis,
    }


@router.get("/projects/{pid}/datasets/{did}")
def dataset_detail(request: Request, conn: Conn, pid: str, did: str) -> Response:
    ctx = page(request, conn, pid)
    dataset = dataset_in(conn, ctx, did)
    q = request.query_params
    tab = q.get("tab") if q.get("tab") in TABS else "summary"
    profile = _profile(request, dataset)
    names = _names(dataset)
    target = None
    leaks: dict = {}
    if dataset.type == DatasetType.TRAIN and names:
        kinds = {c.name: c.kind for c in profile.columns}
        target = q.get("target") if q.get("target") in names else _default_target(names, kinds)
        leaks = _leaks(request, conn, ctx, dataset, target)
    cpages = max(1, math.ceil(len(profile.columns) / COLUMNS_PER_PAGE))
    cpage = _int_param(q.get("cpage"), 1, 1, cpages)
    columns = profile.columns[(cpage - 1) * COLUMNS_PER_PAGE : cpage * COLUMNS_PER_PAGE]
    missing = [c.missing_rate for c in profile.columns]
    pairs = profile.correlations[:TOP_PAIRS]
    lang = language(request)
    chart = _chart(
        "hbar",
        [f"{a} × {b}" for a, b, _ in pairs],
        [round(r, 4) for _, _, r in pairs],
        i18n.t("dataset.corr_chart", lang, n=len(pairs)),
        i18n.t("dataset.corr_r", lang),
        "",
        min=-1,
        max=1,
    )
    size = _size(request, dataset)
    return _view(
        request,
        "dataset.html",
        ctx,
        "datasets",
        dataset=dataset,
        tab=tab,
        profile=profile,
        columns=columns,
        cpage=cpage,
        cpages=cpages,
        first_column=(cpage - 1) * COLUMNS_PER_PAGE,
        target=target,
        leaks=leaks,
        missing_pct=_pct(sum(missing) / len(missing)) if missing else "0",
        sample_rows=profile.n_rows,
        size=size_text(size) if size is not None else None,
        data=_data_page(request, dataset),
        pairs=pairs,
        chart_spec=chart,
        pct=_pct,
        column_url=lambda name: column_url(pid, dataset.id, name),
    )


# --- column detail ------------------------------------------------------------------------


@router.get("/projects/{pid}/datasets/{did}/columns/{name:path}")
def column_detail(request: Request, conn: Conn, pid: str, did: str, name: str) -> Response:
    ctx = page(request, conn, pid)
    dataset = dataset_in(conn, ctx, did)
    if "name" in request.query_params:  # names a path segment cannot carry
        name = request.query_params["name"]
    profile = _profile(request, dataset)
    col = next((c for c in profile.columns if c.name == name), None)
    if col is None:
        raise UiError(404, "error.not_found")
    lang = language(request)
    non_null = round(profile.n_rows * (1 - col.missing_rate))
    chart = other = None
    if col.histogram:
        edges = [left for left, _ in col.histogram]
        labels = [f"{left:.4g}" for left in edges]
        chart = _chart(
            "bar",
            labels,
            [count for _, count in col.histogram],
            i18n.t("column.hist_chart", lang, name=col.name),
            i18n.t("column.value_from", lang),
            i18n.t("column.rows", lang),
        )
    elif col.top_values:
        other = max(0, non_null - sum(count for _, count in col.top_values))
        labels = [value for value, _ in col.top_values]
        values = [count for _, count in col.top_values]
        if other:
            labels.append(i18n.t("column.other", lang))
            values.append(other)
        chart = _chart(
            "hbar",
            labels,
            values,
            i18n.t("column.top_chart", lang, name=col.name),
            i18n.t("column.rows", lang),
            "",
        )
    names = _names(dataset)
    leak = target = None
    if dataset.type == DatasetType.TRAIN and names:
        kinds = {c.name: c.kind for c in profile.columns}
        q = request.query_params
        target = q.get("target") if q.get("target") in names else _default_target(names, kinds)
        if target != col.name:
            leak = _leaks(request, conn, ctx, dataset, target).get(col.name)
    return _view(
        request,
        "column.html",
        ctx,
        "datasets",
        dataset=dataset,
        col=col,
        chart_spec=chart,
        other=other,
        non_null=non_null,
        sample_rows=profile.n_rows,
        target=target,
        leak=leak,
        pct=_pct,
    )


# --- the full training form ---------------------------------------------------------------


def _defaults() -> dict:
    """The engine's own defaults (``TrainConfig``), never copied here."""
    return {
        f.name: f.default
        for f in dataclasses.fields(TrainConfig)
        if f.default is not dataclasses.MISSING
    }


def _form_values(defaults: dict) -> dict:
    """The form's text values for the engine defaults."""
    minutes = defaults["max_runtime_secs"] / 60
    values = {
        "max_runtime_minutes": str(int(minutes)) if minutes.is_integer() else "",
        "max_runtime_secs_per_model": "",
        "max_models": "",
    }
    for name in ("nfolds", "seed", "stopping_rounds", "stopping_metric", "sort_metric", "task"):
        values[name] = str(defaults[name])
    values["stopping_tolerance"] = f"{defaults['stopping_tolerance']:g}"
    for name in FLAGS:
        values[name] = defaults[name]
    for name in ("max_runtime_secs_per_model", "max_models"):
        if defaults[name] is not None:
            values[name] = str(defaults[name])
    return values


def _metric_options() -> list[tuple[str, str]]:
    """``(metric, task)`` for every metric the engine accepts for a task."""
    return [(m, task) for task, names in metrics.ALLOWED.items() for m in names]


def _train_view(
    request: Request,
    conn,
    ctx: Ctx,
    dataset: Dataset,
    target: str | None,
    *,
    values: dict | None = None,
    inputs: set | None = None,
    errors: dict | None = None,
    detail: str | None = None,
    status: int = 200,
) -> Response:
    found, columns, defaults = _analysis(request, conn, ctx, dataset, target)
    here = f"/projects/{ctx.project.id}/datasets/{dataset.id}/train?"
    here += urlencode({"target": defaults.target})
    return _view(
        request,
        "train.html",
        ctx,
        "datasets",
        status=status,
        here=here,
        dataset=dataset,
        found=found,
        columns=columns,
        target=defaults.target,
        detected=defaults.task,
        values=values if values is not None else _form_values(_defaults()),
        inputs=inputs if inputs is not None else defaults.inputs,
        tasks=TASKS,
        metric_options=_metric_options(),
        errors=errors or {},
        detail=detail,
        pct=_pct,
        seed_max=SEED_MAX,
    )


@router.get("/projects/{pid}/datasets/{did}/train")
def train_form(request: Request, conn: Conn, pid: str, did: str, target: str | None = None):
    ctx = page(request, conn, pid, "write")
    return _train_view(request, conn, ctx, dataset_in(conn, ctx, did), target)


def _whole(text: str, low: int, high: int | None = None) -> int | None:
    """A whole number of ASCII digits in [low, high], else None."""
    text = text.strip()
    if not _WHOLE.fullmatch(text):
        return None
    value = int(text)
    return value if value >= low and (high is None or value <= high) else None


def _parse_train(form: FormData, names: list[str], inferred_task: str):
    """``(config dict, inputs, values, errors)`` from the posted form; ``errors`` maps a field
    to an i18n key (``form`` for the form as a whole)."""
    errors: dict[str, str] = {}
    counts: dict[str, int] = {}
    for key, _ in form.multi_items():
        counts[key] = counts.get(key, 0) + 1
    if any(key not in SINGLE_FIELDS and key != "inputs" for key in counts):
        errors["form"] = "train.error.unknown_field"
    elif any(counts[key] > 1 for key in counts if key != "inputs"):
        errors["form"] = "train.error.duplicate_field"
    values = {key: _text(form, key) for key in SINGLE_FIELDS if key not in FLAGS}
    for flag in FLAGS:
        values[flag] = _text(form, flag) == "on"
    target = values["target"]
    inputs = {v for v in form.getlist("inputs") if isinstance(v, str) and v != target}
    config: dict = {"target": target}
    if target not in names:
        errors["target"] = "analysis.error.target"
    if not inputs <= set(names):
        errors["inputs"] = "analysis.error.inputs_unknown"
    elif not inputs:
        errors["inputs"] = "analysis.error.inputs_empty"
    config["ignored_columns"] = [n for n in names if n != target and n not in inputs]
    if values["task"] not in TASKS:
        errors["task"] = "analysis.error.task"
    config["task"] = values["task"]
    minutes = values["max_runtime_minutes"].strip()
    if len(minutes) > MAX_RUNTIME_DIGITS or _whole(minutes, 1) is None:
        errors["max_runtime_minutes"] = "analysis.error.runtime"
    else:
        config["max_runtime_secs"] = int(minutes) * 60
    for name, low, high in (
        ("max_runtime_secs_per_model", 1, None),
        ("max_models", 1, None),
    ):
        if values[name].strip() == "":
            config[name] = None
        elif (number := _whole(values[name], low, high)) is None:
            errors[name] = "train.error.whole_optional"
        else:
            config[name] = number
    for name, low, high, key in (
        ("nfolds", 2, None, "train.error.nfolds"),
        ("seed", 0, SEED_MAX, "train.error.seed"),
        ("stopping_rounds", 0, None, "train.error.whole_zero"),
    ):
        if (number := _whole(values[name], low, high)) is None:
            errors[name] = key
        else:
            config[name] = number
    tolerance = values["stopping_tolerance"].strip()
    if not _DECIMAL.fullmatch(tolerance):
        errors["stopping_tolerance"] = "train.error.tolerance"
    else:
        config["stopping_tolerance"] = float(tolerance)
    task = values["task"] if values["task"] in ("classification", "regression") else inferred_task
    for name in ("stopping_metric", "sort_metric"):
        try:
            metrics.resolve(values[name] or "?", task, name)
        except ConfigError:
            errors[name] = "train.error.metric"
        config[name] = values[name]
    for flag in FLAGS:
        config[flag] = values[flag]
    return config, inputs, values, errors


@router.post("/projects/{pid}/datasets/{did}/train")
def train(request: Request, conn: Conn, pid: str, did: str, form: Posted) -> Response:
    """Queue training with every parameter; anything wrong goes back to the form, inline,
    with nothing queued."""
    if form is None:
        ctx = page(request, conn, pid, "write")
        dataset = dataset_in(conn, ctx, did)
        errors = {"form": "analysis.error.too_many_fields"}
        return _train_view(request, conn, ctx, dataset, None, errors=errors, status=422)
    ctx = action(request, conn, pid, _text(form, "csrf_token"))
    dataset = dataset_in(conn, ctx, did)
    names = _names(dataset)
    target = _text(form, "target")
    found, _, _ = _analysis(request, conn, ctx, dataset, target if target in names else None)
    config, inputs, values, errors = _parse_train(form, names, found.task)

    def again(errors: dict, detail: str | None = None) -> Response:
        return _train_view(
            request,
            conn,
            ctx,
            dataset,
            target if target in names else None,
            values=values,
            inputs=inputs,
            errors=errors,
            detail=detail,
            status=422,
        )

    if errors:
        return again(errors)
    try:
        config = TrainConfig.from_dict(config)  # the engine's own validation
    except ConfigError as e:
        return again({"form": "train.error.config"}, redact(str(e)))
    try:
        job = models.submit_training(
            conn, request.app.state.storage, ctx.auth.user, pid, dataset.id, config
        )
    except TargetError:
        return again({"target": "analysis.error.target_data"})
    except (ValueError, PermissionError) as e:  # ConfigError is a ValueError
        return again({"form": "train.error.config"}, redact(str(e)))
    return RedirectResponse(f"/projects/{pid}/jobs/{job.id}", 303)


# --- jobs ---------------------------------------------------------------------------------


def _job_row(ctx: Ctx, job: Job, now: float) -> dict:
    started, finished = job.started_at, job.finished_at
    duration = None if started is None else (finished or now) - started
    pid = ctx.project.id
    link = f"/projects/{pid}/jobs/{job.id}"
    result = job.result or {}
    if job.status == JobStatus.DONE and job.kind == "automl" and result.get("model_id"):
        link = f"/projects/{pid}/models/{result['model_id']}/summary"
    elif job.status == JobStatus.DONE and job.kind == "batch_predict":
        link = f"/projects/{pid}/jobs/{job.id}/result"
    info = job_out(job, admin=ctx.admin)  # the message as the API shows it to this user
    return {
        "job": job,
        "link": link if job.kind in ("automl", "batch_predict") else None,
        "duration": _clock(duration),
        "started": started,
        "message": info["message"] if job.status == JobStatus.FAILED else None,
        "active": job.status not in TERMINAL,
    }


def _jobs_context(request: Request, conn, ctx: Ctx) -> dict:
    """One page of the filtered jobs and the counts, each read in SQL (polled every 5 s)."""
    q = request.query_params
    kind = q.get("kind") if q.get("kind") in JOB_KINDS else ""
    status = q.get("status") if q.get("status") in {s.value for s in JobStatus} else ""
    pid = ctx.project.id
    filters = {"kind": kind or None, "statuses": (status,) if status else None}
    total = store.count_jobs(conn, pid, **filters)
    pages = max(1, math.ceil(total / JOBS_PER_PAGE))
    number = _int_param(q.get("page"), 1, 1, pages)
    window = store.page_jobs(
        conn, pid, **filters, limit=JOBS_PER_PAGE, offset=(number - 1) * JOBS_PER_PAGE
    )
    now = time.time()
    n_running = store.count_jobs(conn, pid, statuses=(JobStatus.RUNNING,))
    n_queued = store.count_jobs(conn, pid, statuses=(JobStatus.QUEUED,))
    query = urlencode({k: v for k, v in (("kind", kind), ("status", status)) if v})
    poll = urlencode(
        {k: v for k, v in (("kind", kind), ("status", status), ("page", number)) if v and v != 1}
    )
    active = bool(n_running + n_queued)
    return {
        "rows": [_job_row(ctx, j, now) for j in window],
        "total": total,
        "kind_filter": kind,
        "status_filter": status,
        "kinds": JOB_KINDS,
        "statuses": [s.value for s in JobStatus],
        "page_number": number,
        "pages": pages,
        # Every 5 s while a job of the project is active (whatever the filter), else a slow
        # poll that notices a job queued elsewhere (another tab, the API).
        "poll_every": POLL_ACTIVE if active else POLL_IDLE,
        "poll_url": f"/projects/{pid}/jobs" + (f"?{poll}" if poll else ""),
        "n_running": n_running,
        "n_queued": n_queued,
        "n_finished": store.count_jobs(conn, pid, statuses=TERMINAL),
        "query": query,
    }


@router.get("/projects/{pid}/jobs")
def jobs(request: Request, conn: Conn, pid: str) -> Response:
    """The project's jobs. HTMX polls the list (every 5 s while a job is active, every
    30 s otherwise); if the list can no longer be shown (access revoked, project deleted,
    an error), the answer is 286 with a final fragment, and polling stops."""
    polling = bool(request.headers.get("hx-request"))
    try:
        ctx = page(request, conn, pid)
        context = _jobs_context(request, conn, ctx)
    except UiError as e:
        if not polling or e.status == 401:  # 401: HTMX is sent to the login page
            raise
        return _list_gone(request, e.key, "jobs.gone_hint")
    except Exception:
        if not polling:
            raise
        log.exception("the job list of project %s could not be shown", pid)
        return _list_gone(request, "error.generic", "jobs.reload_hint")
    if polling:
        return _view(request, "_jobs_list.html", ctx, "jobs", **context)
    return _view(request, "jobs.html", ctx, "jobs", **context)


def _list_gone(request: Request, key: str, hint: str) -> Response:
    """The poller's last fragment: HTMX swaps a 286 and stops polling."""
    message = i18n.t(key, language(request))
    return render(
        request,
        "_job_gone.html",
        status=STOP_POLLING,
        message=message,
        hint=hint,
        target_id="job-list",
    )


@router.post("/projects/{pid}/jobs/{jid}/delete")
def delete_job(request: Request, conn: Conn, pid: str, jid: str, form: Posted):
    ctx = action(request, conn, pid, _text(form, "csrf_token"))
    job = job_in(conn, ctx, jid)
    try:
        delete_finished_job(request, conn, job)
    except KeyError:
        raise UiError(404, "error.not_found") from None
    except ValueError:  # not finished: nothing is deleted
        raise UiError(409, "jobs.error.not_finished") from None
    return RedirectResponse(f"/projects/{pid}/jobs", 303)


@router.post("/projects/{pid}/jobs/delete-finished")
def delete_finished(request: Request, conn: Conn, pid: str, form: Posted):
    ctx = action(request, conn, pid, _text(form, "csrf_token"))
    delete_finished_jobs_of(request, conn, ctx.project.id)
    return RedirectResponse(f"/projects/{pid}/jobs", 303)
