"""The EasyML wizard: project dashboard, upload of training data, data analysis, run, live
progress, prediction summary and new predictions.

Pages use the same services as the API, with its authorization: every id in a path is
resolved and must belong to the path's project (404 otherwise, as for a project the user
cannot read); writes need write access (403 for a viewer). Writes are form posts carrying
the session's CSRF token in ``csrf_token``. Uploads check the session, write access and
``Origin`` before the body is read, and the token right after the form is parsed.
"""

import math
import time
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response
from starlette.datastructures import UploadFile

from fione.api.deps import Auth, Conn, authorize, cookie_auth, request_host
from fione.api.downloads import tmp_dir
from fione.api.errors import ApiError
from fione.api.routes_datasets import cell, ingest_upload
from fione.api.routes_jobs import cancel
from fione.api.routes_models import serving_bundle_of
from fione.api.schemas import MAX_ID, event_out, job_out
from fione.api.security import origin_matches, tokens_equal
from fione.auth.roles import ProjectAccess, Role
from fione.engine.artifact import UntrustedArtifactError, read_manifest
from fione.engine.prep import MIN_ROWS, too_many_classes
from fione.jobs import store
from fione.jobs.store import TERMINAL, Job, JobStatus
from fione.models import service as models
from fione.models.bundle import BundleError
from fione.models.rating import Rating, star_rating, target_baseline
from fione.models.service import ModelNotFound, ModelRecord
from fione.modules.registry import redact
from fione.predict.batch import PREDICT
from fione.projects import service as projects
from fione.projects.ingest import IngestError, read_dataset_sample
from fione.projects.service import Dataset, DatasetNotFound, DatasetType, Project, ProjectNotFound
from fione.tools.builtin import propose
from fione.web.uploads import UploadFormError, read_form
from fione.web.views import UiError, action_auth, render

router = APIRouter(include_in_schema=False)

# Merged into every training config the wizard submits (tests make runs fast with it).
EASYML_CONFIG: dict = {}
RUNTIME_PRESETS = (1, 3, 10, 30)  # minutes
DEFAULT_RUNTIME = 3
MAX_RUNTIME_DIGITS = 6  # custom minutes: a whole number of 1 or more, at most 6 digits
TASKS = ("classification", "regression")
PREVIEW_ROWS = 10
RESULT_PREVIEW_ROWS = 20
RECENT_JOBS = 10
TOP_INPUTS = 5
EVENT_DETAILS = 20
MAX_NAME_LEN = 100
WRITE = (ProjectAccess.OWNER, ProjectAccess.EDITOR)
# A leak suspect's reason (data.profile) -> the key of its explanation.
LEAK_REASONS = {
    "identical to target": "identical",
    "near-perfect correlation with target": "correlated",
    "value determines target": "determines",
}
# The start of an ingest error -> the key of its plain-language message.
INGEST_ERRORS = (
    ("could not detect the text encoding", "upload.error.encoding"),
    ("empty file", "upload.error.empty"),
    ("no data rows", "upload.error.no_rows"),
    ("could not parse the CSV", "upload.error.parse"),
)


@dataclass(frozen=True)
class Ctx:
    auth: Auth
    project: Project
    access: ProjectAccess

    @property
    def can_write(self) -> bool:
        return self.access in WRITE


# --- resolving and authorizing ------------------------------------------------------------


def _context(conn, auth: Auth, pid: str, need) -> Ctx:
    """The path project with the API's rules: 404 without read access, 403 without ``need``."""
    try:
        project = projects.require_project(conn, pid)
        access = authorize(conn, auth.user, pid, need, "project not found")
    except ProjectNotFound:
        raise UiError(404, "error.not_found") from None
    except ApiError as e:
        raise UiError(e.status, "error.not_found" if e.status == 404 else "error.forbidden") from e
    return Ctx(auth, project, access)


def _page(request: Request, conn, pid: str, need="read") -> Ctx:
    """A page view: anonymous visitors are sent to the login page (HTMX: told to go there)."""
    auth = cookie_auth(request, conn)
    if auth is None:
        raise UiError(401, "error.session")
    return _context(conn, auth, pid, need)


def _action(request: Request, conn, pid: str, token: str, need="write") -> Ctx:
    """A form post: the session and its CSRF token first, then access to the project."""
    return _context(conn, action_auth(request, conn, token), pid, need)


def _id(text) -> int:
    if not isinstance(text, str) or not text.isascii() or not text.isdigit():
        raise UiError(404, "error.not_found")
    value = int(text)
    if not 1 <= value <= MAX_ID:
        raise UiError(404, "error.not_found")
    return value


def _dataset(conn, ctx: Ctx, did) -> Dataset:
    try:
        dataset = projects.get_dataset(conn, _id(did))
    except DatasetNotFound:
        raise UiError(404, "error.not_found") from None
    if dataset.project_id != ctx.project.id:
        raise UiError(404, "error.not_found")
    return dataset


def _model(conn, ctx: Ctx, mid) -> ModelRecord:
    try:
        record = models.get_model(conn, _id(mid))
    except ModelNotFound:
        raise UiError(404, "error.not_found") from None
    if record.project_id != ctx.project.id:
        raise UiError(404, "error.not_found")
    return record


def _job(conn, ctx: Ctx, jid) -> Job:
    try:
        job = store.get_job(conn, _id(jid))
    except KeyError:
        raise UiError(404, "error.not_found") from None
    if job.project_id != ctx.project.id:
        raise UiError(404, "error.not_found")
    return job


def _admin(ctx: Ctx) -> bool:
    return ctx.auth.user.role == Role.ADMIN


def _storage(request: Request):
    return request.app.state.storage


def _names(dataset: Dataset) -> list[str]:
    return [name for name, _ in dataset.schema]


def _ratings(request: Request, conn, records: list[ModelRecord]) -> dict[int, Rating]:
    """Each model's rating; a training target's baseline is read once per request."""
    baselines: dict = {}
    out = {}
    for record in records:
        key = (record.dataset_id, record.target, record.task)
        if key not in baselines:
            baselines[key] = target_baseline(_storage(request), conn, record.project_id, *key)
        baseline = baselines[key]
        out[record.id] = star_rating(
            record.task,
            record.metrics,
            majority_rate=baseline.majority_rate,
            target_std=baseline.target_std,
            degraded=record.stop_reason == "error",
        )
    return out


def _view(request: Request, template: str, ctx: Ctx, *, status: int = 200, **context) -> Response:
    return render(request, template, ctx.auth, status=status, ctx=ctx, nav="projects", **context)


# --- project dashboard --------------------------------------------------------------------


@router.get("/projects/{pid}")
def dashboard(request: Request, conn: Conn, pid: str) -> Response:
    ctx = _page(request, conn, pid)
    datasets = projects.list_datasets(conn, pid)[::-1]  # newest first
    records = models.list_models(conn, pid)
    ratings = _ratings(request, conn, records)
    ranked = sorted(records, key=lambda r: (-ratings[r.id].stars, -r.created_at, -r.id))
    jobs = store.list_jobs(conn, pid, limit=RECENT_JOBS)
    training = next((j for j in jobs if j.kind == "automl" and j.status not in TERMINAL), None)
    train_sets = [d for d in datasets if d.type == DatasetType.TRAIN]
    members = projects.list_members(conn, pid) if ctx.access == ProjectAccess.OWNER else None
    return _view(
        request,
        "project.html",
        ctx,
        datasets=datasets,
        models=ranked,
        ratings=ratings,
        jobs=jobs,
        training=training,
        latest_train=train_sets[0] if train_sets else None,
        members=members,
    )


# --- uploads ------------------------------------------------------------------------------


class _UploadProblem(Exception):
    """An upload that cannot be used: shown on the upload form as ``key`` (and ``detail``)."""

    def __init__(self, status: int, key: str, detail: str | None = None, **vars):
        super().__init__(key)
        self.status, self.key, self.detail, self.vars = status, key, detail, vars


async def _upload_context(request: Request, conn, pid: str) -> Ctx:
    """Everything an upload is checked for before its body is read."""
    auth = cookie_auth(request, conn)
    if auth is None:
        raise UiError(401, "error.session")
    ctx = _context(conn, auth, pid, "write")
    if not origin_matches(request.headers.get("origin"), request_host(request)):
        raise UiError(403, "error.forbidden")
    return ctx


def _dataset_name(filename: str) -> str:
    """The dataset name for an uploaded file: its base name without ``.csv``."""
    base = PureWindowsPath(PurePosixPath(filename).name).name.strip()
    if base.lower().endswith(".csv"):
        base = base[:-4].strip()
    return base[:MAX_NAME_LEN] or "data"


def _ingest_problem(error: IngestError) -> _UploadProblem:
    text = redact(str(error))
    for start, key in INGEST_ERRORS:
        if text.startswith(start):
            return _UploadProblem(422, key, text if key == "upload.error.parse" else None)
    if "not valid UTF-8" in text:
        return _UploadProblem(422, "upload.error.encoding")
    return _UploadProblem(422, "upload.error.invalid", text)


async def _receive_csv(request: Request, conn, ctx: Ctx, type_: DatasetType) -> Dataset:
    """Read the posted form (``csrf_token`` and one ``file``) and ingest the CSV."""
    settings = request.app.state.settings
    try:
        form = await read_form(request, tmp_dir(settings), max_fields=1)
    except UploadFormError:
        raise _UploadProblem(400, "upload.error.form") from None
    try:
        token = form.get("csrf_token")
        if not tokens_equal(ctx.auth.session.csrf, token if isinstance(token, str) else None):
            raise UiError(403, "error.csrf")
        upload = form.get("file")
        if not isinstance(upload, UploadFile) or not upload.filename:
            raise _UploadProblem(422, "upload.error.missing")
        try:
            return await ingest_upload(
                request, conn, ctx.project.id, _dataset_name(upload.filename), type_, upload
            )
        except ApiError as e:  # 413: over max_upload_bytes
            raise _UploadProblem(e.status, "upload.error.too_large") from e
        except IngestError as e:
            raise _ingest_problem(e) from e
    finally:
        await form.close()


def _size(n: int) -> str:
    for unit, scale in (("GB", 2**30), ("MB", 2**20), ("KB", 2**10)):
        if n >= scale:
            return f"{n / scale:.1f}".removesuffix(".0") + f" {unit}"
    return f"{n} B"


def _upload_view(request: Request, ctx: Ctx, *, status: int = 200, problem=None) -> Response:
    return _view(
        request,
        "upload.html",
        ctx,
        status=status,
        limit=_size(request.app.state.settings.max_upload_bytes),
        problem=problem,
    )


@router.get("/projects/{pid}/upload")
def upload_page(request: Request, conn: Conn, pid: str) -> Response:
    return _upload_view(request, _page(request, conn, pid, "write"))


@router.post("/projects/{pid}/upload")
async def upload(request: Request, conn: Conn, pid: str) -> Response:
    ctx = await _upload_context(request, conn, pid)
    try:
        dataset = await _receive_csv(request, conn, ctx, DatasetType.TRAIN)
    except _UploadProblem as problem:
        return _upload_view(request, ctx, status=problem.status, problem=problem)
    return RedirectResponse(f"/projects/{pid}/datasets/{dataset.id}/analyze", 303)


# --- data analysis and run ----------------------------------------------------------------


@dataclass
class RunForm:
    """What the analysis form holds: the defaults, or what the user posted."""

    target: str
    inputs: set[str]
    task: str
    runtime: str  # a preset (minutes) or "custom"
    custom: str = ""


def _default_target(names: list[str], kinds: dict[str, str]) -> str:
    """The last column, unless it looks like an id or holds one value: then the last that
    does not."""
    usable = [n for n in names if kinds.get(n) not in ("id", "constant")]
    return usable[-1] if usable else names[-1]


def _analysis(request: Request, conn, ctx: Ctx, dataset: Dataset, target: str | None):
    """The analysis of ``dataset`` for ``target`` (or the default one) and the defaults."""
    names = _names(dataset)
    storage = _storage(request)
    chosen = target if target in names else names[-1]
    found = propose(storage, dataset, chosen, names)
    if target not in names:
        kinds = {col.name: col.kind for col in found.profile.columns}
        default = _default_target(names, kinds)
        if default != chosen:
            chosen, found = default, propose(storage, dataset, default, names)
    reasons = {col.name: col.kind for col in found.ignore}  # id, constant
    for suspect in found.profile.leak_suspects:
        reasons.setdefault(suspect.column, "leak_" + LEAK_REASONS.get(suspect.reason, "other"))
    columns = [
        {"index": i, "profile": col, "reason": reasons.get(col.name), "target": col.name == chosen}
        for i, col in enumerate(found.profile.columns, start=1)
    ]
    defaults = RunForm(
        target=chosen,
        inputs={n for n in names if n != chosen and n not in reasons},
        task=found.task,
        runtime=str(DEFAULT_RUNTIME),
    )
    return found, columns, defaults


def _warnings(dataset: Dataset, found, task: str) -> list[tuple[str, str, dict]]:
    """``(level, key, vars)`` for what training will refuse or should be checked, by the
    engine's own limits."""
    target = found.target
    out = []
    if dataset.type != DatasetType.TRAIN:
        out.append(("danger", "analysis.warn.not_train", {}))
    if dataset.n_rows < MIN_ROWS:
        out.append(("danger", "analysis.warn.few_rows", {"n": dataset.n_rows, "min": MIN_ROWS}))
    if dataset.n_cols < 2:
        out.append(("danger", "analysis.warn.one_column", {}))
    if target.missing_rate > 0:
        out.append(("danger", "analysis.warn.target_missing", {"pct": _pct(target.missing_rate)}))
    if target.kind == "constant":
        out.append(("danger", "analysis.warn.target_constant", {}))
    elif target.kind == "id":
        out.append(("warning", "analysis.warn.target_id", {}))
    if task == "classification" and too_many_classes(target.n_unique, dataset.n_rows):
        out.append(("warning", "analysis.warn.many_classes", {"n": f"{target.n_unique:,}"}))
    if found.profile.leak_suspects:
        out.append(("info", "analysis.warn.leaks", {"n": len(found.profile.leak_suspects)}))
    return out


def _pct(rate: float) -> str:
    """A rate as a percentage for people: ``0``, ``<0.1``, ``2.5`` or ``40``."""
    if rate <= 0:
        return "0"
    if rate < 0.001:
        return "<0.1"
    value = rate * 100
    return f"{value:.1f}".removesuffix(".0") if value < 10 else f"{value:.0f}"


def _preview(request: Request, dataset: Dataset, rows: int) -> dict:
    frame = read_dataset_sample(_storage(request), dataset, max_rows=rows)
    return {
        "columns": list(frame.columns),
        "rows": [
            [cell(v) for v in row]
            for row in frame.astype(object).itertuples(index=False, name=None)
        ],
    }


def _analysis_view(
    request: Request,
    conn,
    ctx: Ctx,
    dataset: Dataset,
    target: str | None,
    *,
    posted: RunForm | None = None,
    errors: dict | None = None,
    detail: str | None = None,
    status: int = 200,
) -> Response:
    found, columns, defaults = _analysis(request, conn, ctx, dataset, target)
    form = posted if posted is not None and posted.target == defaults.target else defaults
    missing = [col.missing_rate for col in found.profile.columns]
    return _view(
        request,
        "analysis.html",
        ctx,
        status=status,
        dataset=dataset,
        found=found,
        columns=columns,
        form=form,
        detected=defaults.task,
        warnings=_warnings(dataset, found, form.task),
        missing_pct=_pct(sum(missing) / len(missing)) if missing else "0",
        pct=_pct,
        sample_rows=found.profile.n_rows,  # the rows profiled: the first ones
        preview=_preview(request, dataset, PREVIEW_ROWS),
        presets=RUNTIME_PRESETS,
        n_inputs=len(form.inputs),
        errors=errors or {},
        detail=detail,
    )


@router.get("/projects/{pid}/datasets/{did}/analyze")
def analyze(request: Request, conn: Conn, pid: str, did: str, target: str | None = None):
    ctx = _page(request, conn, pid)
    return _analysis_view(request, conn, ctx, _dataset(conn, ctx, did), target)


def _minutes(runtime: str, custom: str) -> int | None:
    if runtime == "custom":
        text = custom.strip()
        ok = text.isascii() and text.isdigit() and len(text) <= MAX_RUNTIME_DIGITS
        return int(text) if ok and int(text) >= 1 else None
    return int(runtime) if runtime in {str(m) for m in RUNTIME_PRESETS} else None


@router.post("/projects/{pid}/datasets/{did}/run")
def run(
    request: Request,
    conn: Conn,
    pid: str,
    did: str,
    csrf_token: Annotated[str, Form()] = "",
    target: Annotated[str, Form()] = "",
    inputs: Annotated[list[str], Form()] = [],  # noqa: B006 (FastAPI copies defaults)
    task: Annotated[str, Form()] = "",
    runtime: Annotated[str, Form()] = "",
    runtime_custom: Annotated[str, Form()] = "",
) -> Response:
    """Queue training from the analysis form; anything wrong goes back to the form, inline,
    with nothing queued."""
    ctx = _action(request, conn, pid, csrf_token)
    dataset = _dataset(conn, ctx, did)
    names = _names(dataset)
    chosen = {c for c in inputs if c != target}
    posted = RunForm(target, chosen, task, runtime, runtime_custom)
    errors = {}
    if target not in names:
        errors["target"] = "analysis.error.target"
    if not chosen <= set(names):
        errors["inputs"] = "analysis.error.inputs_unknown"
    elif not chosen:
        errors["inputs"] = "analysis.error.inputs_empty"
    if task not in TASKS:
        errors["task"] = "analysis.error.task"
    minutes = _minutes(runtime, runtime_custom)
    if minutes is None:
        errors["runtime"] = "analysis.error.runtime"
    if errors:
        return _analysis_view(
            request, conn, ctx, dataset, target, posted=posted, errors=errors, status=422
        )
    config = {
        "target": target,
        "task": task,
        "max_runtime_secs": minutes * 60,
        "ignored_columns": [n for n in names if n != target and n not in chosen],
        **EASYML_CONFIG,
    }
    try:
        job = models.submit_training(conn, ctx.auth.user, pid, dataset.id, config)
    except (ValueError, PermissionError) as e:  # ConfigError is a ValueError
        return _analysis_view(
            request,
            conn,
            ctx,
            dataset,
            target,
            posted=posted,
            errors={"form": "analysis.error.config"},
            detail=redact(str(e)),
            status=422,
        )
    return RedirectResponse(f"/projects/{pid}/jobs/{job.id}", 303)


# --- job progress -------------------------------------------------------------------------


def _clock(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    return f"{hours}:{rest // 60:02d}:{rest % 60:02d}" if hours else f"{rest // 60}:{rest % 60:02d}"


def _number(value) -> str:
    """A metric for people: three significant digits, thousands separated."""
    if value is None or not math.isfinite(value):
        return "—"
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:.3g}"


def _stage(job: Job, events: list) -> tuple[str, dict]:
    """The i18n key and variables of what the job is doing now, from its events."""
    if job.status in TERMINAL:
        return f"job.stage.{job.status.value}", {}
    if job.status == JobStatus.QUEUED:
        return "job.stage.queued", {}
    last = events[-1][1] if events else None
    if job.kind == "batch_predict":
        if last is None or last.type == "started":
            return "job.stage.reading", {}
        if last.type == "finished":
            return "job.stage.saving", {}
        done, total = last.data.get("rows_done"), last.data.get("rows_total")
        if isinstance(done, int) and isinstance(total, int):
            return "job.stage.predicting", {"done": f"{done:,}", "total": f"{total:,}"}
        return "job.stage.reading", {}
    if last is None or last.type == "started":
        return "job.stage.preparing", {}
    if last.type in ("ensemble", "stopped") and "family" not in last.data:
        return "job.stage.ensemble", {}
    if last.type == "finished":
        return "job.stage.saving", {}
    family = next(
        (e.data["family"] for _, e in reversed(events) if isinstance(e.data.get("family"), str)),
        None,
    )
    return ("job.stage.trying", {"family": family}) if family else ("job.stage.preparing", {})


def _job_view(request: Request, conn, ctx: Ctx, job: Job) -> dict:
    events = store.events_since(conn, job.id)
    admin = _admin(ctx)
    now = time.time()
    started, finished = job.started_at, job.finished_at
    elapsed = None if started is None else (finished or now) - started
    pid = ctx.project.id
    budget = progress = None
    trials = [e for _, e in events if e.type == "trial"]
    scores = [e.data.get("best_so_far") for e in trials]
    scores = [s for s in scores if isinstance(s, int | float) and math.isfinite(s)]
    next_url = back_url = None
    if job.kind == "automl":
        config = job.payload.get("config") or {}
        budget = config.get("max_runtime_secs")
        if isinstance(budget, int) and budget > 0 and elapsed is not None:
            progress = min(1.0, elapsed / budget)
        if job.status == JobStatus.DONE and (job.result or {}).get("model_id"):
            next_url = f"/projects/{pid}/models/{job.result['model_id']}/summary"
        dataset_id, target = job.payload.get("dataset_id"), config.get("target")
        if dataset_id:
            query = urlencode({"target": target}) if isinstance(target, str) else ""
            back_url = f"/projects/{pid}/datasets/{dataset_id}/analyze" + (
                f"?{query}" if query else ""
            )
    elif job.kind == "batch_predict":
        rows = [e.data for _, e in events if isinstance(e.data.get("rows_total"), int)]
        if rows and rows[-1]["rows_total"] > 0:
            progress = min(1.0, rows[-1].get("rows_done", 0) / rows[-1]["rows_total"])
        if job.status == JobStatus.DONE:
            next_url = f"/projects/{pid}/jobs/{job.id}/result"
        if job.payload.get("model_id"):
            back_url = f"/projects/{pid}/models/{job.payload['model_id']}/predict"
    if job.status == JobStatus.DONE:
        progress = 1.0
    stage, stage_vars = _stage(job, events)
    details = []
    for event_id, event in events:
        if event.type in ("notice", "error"):
            data = event_out(event_id, event, admin=admin)["data"]
            text = data.get("message") or data.get("error")
            if isinstance(text, str) and text:
                details.append((event.ts, text))
    return {
        "job": job,
        "info": job_out(job, admin=admin),  # the message as the API shows it to this user
        "terminal": job.status in TERMINAL,
        "stage": stage,
        "stage_vars": stage_vars,
        "elapsed": _clock(elapsed),
        "budget": _clock(budget) if isinstance(budget, int) else None,
        "remaining": _clock(budget - elapsed) if progress is not None and budget else None,
        "progress": progress,
        "n_trials": len(trials),
        "best": _number(min(scores)) if scores else None,
        "next_url": next_url,
        "back_url": back_url,
        "details": details[-EVENT_DETAILS:],
    }


@router.get("/projects/{pid}/jobs/{jid}")
def job_page(request: Request, conn: Conn, pid: str, jid: str) -> Response:
    ctx = _page(request, conn, pid)
    job = _job(conn, ctx, jid)
    return _view(request, "job.html", ctx, **_job_view(request, conn, ctx, job))


@router.get("/projects/{pid}/jobs/{jid}/status")
def job_status(request: Request, conn: Conn, pid: str, jid: str) -> Response:
    """The polled fragment. A finished job's has no trigger, so polling stops; a successful
    one sends HTMX on to its result."""
    ctx = _page(request, conn, pid)
    view = _job_view(request, conn, ctx, _job(conn, ctx, jid))
    response = _view(request, "_job_status.html", ctx, fragment=True, **view)
    if request.headers.get("hx-request") and view["job"].status == JobStatus.DONE:
        if view["next_url"]:
            response.headers["HX-Redirect"] = view["next_url"]
    return response


@router.post("/projects/{pid}/jobs/{jid}/cancel")
def cancel_job(
    request: Request, conn: Conn, pid: str, jid: str, csrf_token: Annotated[str, Form()] = ""
) -> Response:
    ctx = _action(request, conn, pid, csrf_token)
    job = _job(conn, ctx, jid)
    if job.status not in TERMINAL:
        cancel(request, conn, job)
    return RedirectResponse(f"/projects/{pid}/jobs/{job.id}", 303)


# --- prediction summary -------------------------------------------------------------------


def _score_sentence(record: ModelRecord, rating: Rating, baseline) -> tuple[str, dict] | None:
    m = record.metrics
    if rating.metric == "accuracy" and rating.note != "single_class":
        return "summary.score.accuracy", {
            "pct": f"{m['accuracy'] * 100:.0f}",
            "base": f"{baseline.majority_rate * 100:.0f}",
        }
    if rating.metric == "auc":
        return "summary.score.auc", {"auc": f"{m['auc']:.2f}"}
    if rating.metric == "rmse" and rating.note != "constant_target":
        return "summary.score.rmse", {
            "error": _number(m["rmse"]),
            "spread": _number(baseline.target_std),
        }
    if rating.metric == "r2":
        return "summary.score.r2", {"pct": f"{max(0.0, m['r2']) * 100:.0f}"}
    return None


@router.get("/projects/{pid}/models/{mid}/summary")
def summary(request: Request, conn: Conn, pid: str, mid: str) -> Response:
    ctx = _page(request, conn, pid)
    record = _model(conn, ctx, mid)
    rating = _ratings(request, conn, [record])[record.id]
    baseline = target_baseline(
        _storage(request), conn, pid, record.dataset_id, record.target, record.task
    )
    elapsed = None
    if record.job_id is not None:
        try:
            result = store.get_job(conn, record.job_id).result or {}
            elapsed = result.get("elapsed")
        except KeyError:  # the job was deleted
            pass
    ranked = sorted(record.importance.items(), key=lambda kv: (-(kv[1] or 0.0), kv[0]))
    top = [(name, value or 0.0) for name, value in ranked[:TOP_INPUTS]]
    try:
        bundle = serving_bundle_of(request, record)
    except (BundleError, ModelNotFound):  # an unsafe image name, or the manifest is gone
        bundle = None
    return _view(
        request,
        "summary.html",
        ctx,
        record=record,
        rating=rating,
        sentence=_score_sentence(record, rating, baseline),
        elapsed=_clock(elapsed) if isinstance(elapsed, int | float) else None,
        n_trials=len(record.trials),
        top=top,
        top_max=max([v for _, v in top] + [1e-12]),
        bundle=bundle,
        members=sum(1 for row in record.leaderboard if (row.get("weight") or 0) > 0),
    )


# --- new prediction -----------------------------------------------------------------------


def _model_columns(request: Request, record: ModelRecord):
    """``(input columns, prediction columns)`` from the model's manifest, or None if it is
    unreadable. Nothing is unpickled; the prediction job verifies the artifact."""
    try:
        manifest = read_manifest(_storage(request), record.storage_prefix)
    except UntrustedArtifactError:
        return None
    return manifest.columns, [PREDICT] + [f"p_{label}" for label in manifest.classes or []]


def _predict_view(
    request: Request,
    ctx: Ctx,
    record: ModelRecord,
    *,
    dataset: Dataset | None = None,
    status: int = 200,
    problem=None,
    missing=None,
    detail: str | None = None,
) -> Response:
    columns = _model_columns(request, record)
    extra = []
    if dataset is not None and columns is not None:
        extra = [n for n in _names(dataset) if n not in set(columns[0])]
    return _view(
        request,
        "predict.html",
        ctx,
        status=status,
        record=record,
        columns=columns,
        dataset=dataset,
        extra=extra,
        limit=_size(request.app.state.settings.max_upload_bytes),
        problem=problem,
        missing=missing,
        detail=detail,
    )


@router.get("/projects/{pid}/models/{mid}/predict")
def predict_page(
    request: Request, conn: Conn, pid: str, mid: str, dataset: str | None = None
) -> Response:
    """Upload a CSV to predict on, then (``?dataset=``) choose the columns of the result."""
    ctx = _page(request, conn, pid, "write")
    record = _model(conn, ctx, mid)
    chosen = None if dataset is None else _dataset(conn, ctx, dataset)
    return _predict_view(request, ctx, record, dataset=chosen)


@router.post("/projects/{pid}/models/{mid}/predict")
async def predict_upload(request: Request, conn: Conn, pid: str, mid: str) -> Response:
    ctx = await _upload_context(request, conn, pid)
    record = _model(conn, ctx, mid)
    columns = _model_columns(request, record)
    if columns is None:
        return _predict_view(request, ctx, record, status=409)
    try:
        dataset = await _receive_csv(request, conn, ctx, DatasetType.TEST)
    except _UploadProblem as problem:
        return _predict_view(request, ctx, record, status=problem.status, problem=problem)
    names = set(_names(dataset))
    missing = [c for c in columns[0] if c not in names]
    if missing:  # nothing to predict on: the upload is not kept
        projects.delete_dataset(conn, _storage(request), dataset.id)
        return _predict_view(request, ctx, record, status=422, missing=missing)
    return RedirectResponse(f"/projects/{pid}/models/{record.id}/predict?dataset={dataset.id}", 303)


@router.post("/projects/{pid}/models/{mid}/predict/run")
def predict_run(
    request: Request,
    conn: Conn,
    pid: str,
    mid: str,
    csrf_token: Annotated[str, Form()] = "",
    dataset_id: Annotated[str, Form()] = "",
    include: Annotated[list[str], Form()] = [],  # noqa: B006 (FastAPI copies defaults)
) -> Response:
    ctx = _action(request, conn, pid, csrf_token)
    record = _model(conn, ctx, mid)
    dataset = _dataset(conn, ctx, dataset_id)
    try:
        job = models.submit_batch_predict(
            conn, ctx.auth.user, pid, record.id, dataset.id, include_columns=include
        )
    except (ValueError, PermissionError) as e:
        return _predict_view(
            request, ctx, record, dataset=dataset, status=422, detail=redact(str(e))
        )
    return RedirectResponse(f"/projects/{pid}/jobs/{job.id}", 303)


@router.get("/projects/{pid}/jobs/{jid}/result")
def prediction_result(request: Request, conn: Conn, pid: str, jid: str) -> Response:
    ctx = _page(request, conn, pid)
    job = _job(conn, ctx, jid)
    if job.kind != "batch_predict":
        raise UiError(404, "error.not_found")
    if job.status != JobStatus.DONE:
        return RedirectResponse(f"/projects/{pid}/jobs/{job.id}", 303)
    dataset = _dataset(conn, ctx, str((job.result or {}).get("dataset_id", "")))
    return _view(
        request,
        "result.html",
        ctx,
        job=job,
        dataset=dataset,
        preview=_preview(request, dataset, RESULT_PREVIEW_ROWS),
        model_id=job.payload.get("model_id"),
    )
