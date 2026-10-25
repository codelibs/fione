"""The EasyML wizard: project dashboard, upload of training data, data analysis, run, live
progress, prediction summary and new predictions.

Pages use the same services as the API, with its authorization: every id in a path is
resolved and must belong to the path's project (404 otherwise, as for a project the user
cannot read); writes need write access (403 for a viewer). Writes are form posts carrying
the session's CSRF token in ``csrf_token``. Uploads check the session, write access and
``Origin`` before the body is read, and the token right after the form is parsed.
"""

import logging
import math
import time
from dataclasses import dataclass
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from starlette.datastructures import FormData
from starlette.exceptions import HTTPException as StarletteHTTPException

from fione import i18n
from fione.api.deps import Conn
from fione.api.routes_datasets import cell
from fione.api.routes_jobs import cancel
from fione.api.routes_models import serving_bundle_of
from fione.api.schemas import event_out, job_out
from fione.auth.roles import ProjectAccess, Role
from fione.data.profile import (
    CORRELATED,
    DETERMINES,
    IDENTICAL,
    LEAK_STRONG,
    ORDERED_BY_TARGET,
    PREDICTS_ALONE,
    SCORE_REASONS,
    LeakCheck,
)
from fione.engine.artifact import UntrustedArtifactError, read_manifest
from fione.engine.config import TargetError, TrainConfig
from fione.engine.prep import validate_target
from fione.jobs import store
from fione.jobs.store import TERMINAL, Job, JobStatus
from fione.models import service as models
from fione.models.bundle import BundleError
from fione.models.rating import Baseline, Rating, star_rating, target_baseline
from fione.models.service import ModelNotFound, ModelRecord
from fione.modules.registry import redact
from fione.predict.batch import PREDICT
from fione.projects import service as projects
from fione.projects.ingest import read_dataset_sample
from fione.projects.service import Dataset, DatasetNotFound, DatasetType
from fione.tools.builtin import propose, sample_profile
from fione.web.access import Ctx
from fione.web.access import action as _action
from fione.web.access import dataset_in as _dataset
from fione.web.access import job_in as _job
from fione.web.access import model_in as _model
from fione.web.access import page as _page
from fione.web.uploads import UploadProblem as _UploadProblem
from fione.web.uploads import receive_csv as _receive_csv
from fione.web.uploads import size_text as _size
from fione.web.uploads import upload_context as _upload_context
from fione.web.views import UiError, language, render

log = logging.getLogger(__name__)
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
# The analysis profiles the first rows of every column: about PROFILE_CELLS cells, between
# PROFILE_MIN_ROWS and PROFILE_MAX_ROWS rows (fewer rows for wider data).
PROFILE_CELLS = 2_000_000
PROFILE_MAX_ROWS = 50_000
PROFILE_MIN_ROWS = 500
# Form fields a run or prediction post may have (one per checked column); the body itself
# stays under the 1 MiB limit of non-upload requests.
MAX_FORM_FIELDS = 20_000
STOP_POLLING = 286  # the HTMX status that ends hx-trigger polling
# A leak suspect's reason (data.profile) -> the key of its explanation. Reasons in
# SCORE_REASONS only warn: a legitimate strong column can score as high as a leak.
LEAK_REASONS = {
    IDENTICAL: "identical",
    CORRELATED: "correlated",
    DETERMINES: "determines",
    PREDICTS_ALONE: "predicts_alone",
    ORDERED_BY_TARGET: "ordered",
}


def _admin(ctx: Ctx) -> bool:
    return ctx.auth.user.role == Role.ADMIN


def _storage(request: Request):
    return request.app.state.storage


def _names(dataset: Dataset) -> list[str]:
    return [name for name, _ in dataset.schema]


def _baseline(request: Request, conn, record: ModelRecord) -> Baseline:
    """The rating baseline of a model's training target: read from the whole column once,
    then cached (datasets never change)."""
    key = (record.project_id, record.dataset_id, record.target, record.task)
    return request.app.state.ui_baselines.get(
        key, lambda: target_baseline(_storage(request), conn, *key)
    )


def _ratings(request: Request, conn, records: list[ModelRecord]) -> dict[int, Rating]:
    out = {}
    for record in records:
        baseline = _baseline(request, conn, record)
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


def _profile_rows(dataset: Dataset) -> int:
    """How many leading rows the analysis profiles: fewer for wide data, so a profile costs
    about ``PROFILE_CELLS`` cells whatever the shape."""
    rows = PROFILE_CELLS // max(1, dataset.n_cols)
    return max(PROFILE_MIN_ROWS, min(PROFILE_MAX_ROWS, rows))


def _profile(request: Request, dataset: Dataset):
    """The dataset's target-independent column profile, computed once and cached."""
    rows = _profile_rows(dataset)
    return request.app.state.ui_profiles.get(
        dataset.id, lambda: sample_profile(_storage(request), dataset, _names(dataset), rows)
    )


def _chosen(request: Request, dataset: Dataset, target: str | None) -> str:
    """``target`` if it is a column of ``dataset``, else the default target."""
    names = _names(dataset)
    if target in names:
        return target
    return _default_target(names, {c.name: c.kind for c in _profile(request, dataset).columns})


def _leak_check(request: Request, dataset: Dataset, target: str):
    """``(proposal or None, (LeakCheck, task))`` for a column ``target`` of ``dataset``.

    The leak check and the task are cached per dataset and target; the proposal is returned
    only when it had to be made for them. A partial check (its time budget ran out) is not
    kept, so the next request checks again."""
    made = []

    def compute():
        found = propose(
            _storage(request),
            dataset,
            target,
            _names(dataset),
            _profile_rows(dataset),
            profile=_profile(request, dataset),
        )
        made.append(found)
        return LeakCheck(found.profile.leak_suspects, found.profile.leak_partial), found.task

    entry = request.app.state.ui_leaks.get(
        (dataset.id, target), compute, keep=lambda e: not e[0].partial
    )
    return (made[0] if made else None), entry


def _analysis(request: Request, conn, ctx: Ctx, dataset: Dataset, target: str | None):
    """The analysis of ``dataset`` for ``target`` (or the default one) and the defaults."""
    names = _names(dataset)
    profile = _profile(request, dataset)
    chosen = _chosen(request, dataset, target)
    found, (check, task) = _leak_check(request, dataset, chosen)
    if found is None:  # from the cache: only the target column is read
        found = propose(
            _storage(request),
            dataset,
            chosen,
            names,
            _profile_rows(dataset),
            profile=profile,
            check=check,
            task=task,
        )
    reasons = {col.name: col.kind for col in found.ignore}  # id, constant: unchecked
    warnings = {}  # score-based leak suspects: they stay checked
    for suspect in found.profile.leak_suspects:
        key = "leak_" + LEAK_REASONS.get(suspect.reason, "other")
        if suspect.reason in SCORE_REASONS:
            warnings[suspect.column] = (key, suspect.score)
        else:
            reasons.setdefault(suspect.column, key)
    columns = []
    for i, col in enumerate(found.profile.columns, start=1):
        warning, score = warnings.get(col.name, (None, None))
        columns.append(
            {
                "index": i,
                "profile": col,
                "reason": reasons.get(col.name),
                "warning": warning,
                "score": score,
                "target": col.name == chosen,
            }
        )
    defaults = RunForm(
        target=chosen,
        inputs={n for n in names if n != chosen and n not in reasons},
        task=found.task,
        runtime=str(DEFAULT_RUNTIME),
    )
    return found, columns, defaults


def _warnings(dataset: Dataset, found, task: str, inputs: set[str]) -> list[tuple[str, str, dict]]:
    """``(level, key, vars)`` for what training will refuse or should be checked, the leak
    notes counted over the checked ``inputs``. The whole target column goes through the
    engine's own check, as ``submit_training`` does."""
    out = []
    if dataset.type != DatasetType.TRAIN:
        out.append(("danger", "analysis.warn.not_train", {}))
    if dataset.n_cols < 2:
        out.append(("danger", "analysis.warn.one_column", {}))
    try:
        validate_target(found.y, task, TrainConfig.nfolds)
    except TargetError as e:
        out.append(("danger", f"analysis.target_error.{e.code}", e.details))
    if found.target.kind == "id":
        out.append(("warning", "analysis.warn.target_id", {}))
    suspects = found.profile.leak_suspects
    exact = [s for s in suspects if s.reason not in SCORE_REASONS and s.column not in inputs]
    if exact:
        out.append(("info", "analysis.warn.leaks", {"n": len(exact)}))
    # by default every score suspect is checked, except an id or constant column
    scored = [s for s in suspects if s.reason in SCORE_REASONS and s.column in inputs]
    if scored:
        level = "warning" if max(s.score for s in scored) >= LEAK_STRONG else "info"
        out.append((level, "analysis.warn.leak_scores", {"n": len(scored)}))
    if found.profile.leak_partial:
        out.append(("info", "analysis.warn.leak_partial", {}))
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
    cells = [
        [cell(v) for v in row] for row in frame.astype(object).itertuples(index=False, name=None)
    ]
    numeric = [  # right-aligned columns: numbers only (gaps aside)
        all(
            isinstance(r[i], int | float) and not isinstance(r[i], bool)
            for r in cells
            if r[i] is not None
        )
        for i in range(frame.shape[1])
    ]
    return {"columns": list(frame.columns), "rows": cells, "numeric": numeric}


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
    # The language switch comes back here (never to the run form's POST-only path).
    here = f"/projects/{ctx.project.id}/datasets/{dataset.id}/analyze?"
    here += urlencode({"target": defaults.target})
    return _view(
        request,
        "analysis.html",
        ctx,
        status=status,
        here=here,
        dataset=dataset,
        found=found,
        columns=columns,
        form=form,
        detected=defaults.task,
        warnings=_warnings(dataset, found, form.task, form.inputs),
        target_missing=float(found.y.isna().mean()) if len(found.y) else 0.0,
        target_values=int(found.y.nunique()),
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


def _text(form: FormData, name: str) -> str:
    value = form.get(name)
    return value if isinstance(value, str) else ""


def _texts(form: FormData, name: str) -> list[str]:
    return [v for v in form.getlist(name) if isinstance(v, str)]


@router.post("/projects/{pid}/datasets/{did}/run")
def run(request: Request, conn: Conn, pid: str, did: str, form: Posted) -> Response:
    """Queue training from the analysis form; anything wrong goes back to the form, inline,
    with nothing queued."""
    if form is None:  # nothing is changed: shown to whoever may write here
        ctx = _page(request, conn, pid, "write")
        errors = {"form": "analysis.error.too_many_fields"}
        dataset = _dataset(conn, ctx, did)
        return _analysis_view(request, conn, ctx, dataset, None, errors=errors, status=422)
    ctx = _action(request, conn, pid, _text(form, "csrf_token"))
    dataset = _dataset(conn, ctx, did)
    names = _names(dataset)
    target, task = _text(form, "target"), _text(form, "task")
    runtime, runtime_custom = _text(form, "runtime"), _text(form, "runtime_custom")
    chosen = {c for c in _texts(form, "inputs") if c != target}
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
    errors, detail = {}, None
    try:
        job = models.submit_training(
            conn, _storage(request), ctx.auth.user, pid, dataset.id, config
        )
    except TargetError:  # the warning above the columns says why, in the user's language
        errors = {"target": "analysis.error.target_data"}
    except DatasetNotFound:  # its data is gone from storage
        raise UiError(404, "error.not_found") from None
    except (ValueError, PermissionError) as e:  # ConfigError is a ValueError
        errors, detail = {"form": "analysis.error.config"}, redact(str(e))
    if errors:
        return _analysis_view(
            request,
            conn,
            ctx,
            dataset,
            target,
            posted=posted,
            errors=errors,
            detail=detail,
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
    if job.kind in ("export_models", "module"):
        return f"job.stage.{job.kind}", {}
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
    elif job.kind == "export_models" and job.status == JobStatus.DONE:
        next_url = f"/projects/{pid}/models#export"  # the download is offered there
    elif job.kind == "module" and job.status == JobStatus.DONE:
        next_url = f"/projects/{pid}/datasets"  # a module job's result is a new dataset
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
    polling = bool(request.headers.get("hx-request"))
    try:
        ctx = _page(request, conn, pid)
        view = _job_view(request, conn, ctx, _job(conn, ctx, jid))
    except UiError as e:
        if not polling or e.status == 401:  # 401: HTMX is sent to the login page
            raise
        return _polling_stopped(request, e.key, "job.gone_hint")
    except Exception:  # maybe transient (a busy database): reloading may recover
        if not polling:
            raise
        log.exception("the status of job %s could not be shown", jid)
        return _polling_stopped(request, "error.generic", "job.reload_hint")
    response = _view(request, "_job_status.html", ctx, fragment=True, **view)
    if polling and view["job"].status == JobStatus.DONE and view["next_url"]:
        response.headers["HX-Redirect"] = view["next_url"]
    return response


def _polling_stopped(request: Request, key: str, hint: str) -> Response:
    """For the poller, a refusal or failure as a final fragment: HTMX swaps a 286 and stops
    polling (an error status would be left unswapped and polled again forever)."""
    message = i18n.t(key, language(request))
    return render(request, "_job_gone.html", status=STOP_POLLING, message=message, hint=hint)


@router.post("/projects/{pid}/jobs/{jid}/cancel")
def cancel_job(
    request: Request,
    conn: Conn,
    pid: str,
    jid: str,
    csrf_token: Annotated[str, Form()] = "",
    back: Annotated[str, Form()] = "",
) -> Response:
    """Cancel, then back to the job's page, or to the job list when ``back`` is ``list``."""
    ctx = _action(request, conn, pid, csrf_token)
    job = _job(conn, ctx, jid)
    if job.status not in TERMINAL:
        cancel(request, conn, job)
    if back == "list":
        return RedirectResponse(f"/projects/{pid}/jobs", 303)
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
    baseline = _baseline(request, conn, record)  # cached by _ratings
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
    here = f"/projects/{ctx.project.id}/models/{record.id}/predict"  # for the language switch
    here += f"?dataset={dataset.id}" if dataset is not None else ""
    return _view(
        request,
        "predict.html",
        ctx,
        status=status,
        here=here,
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
def predict_run(request: Request, conn: Conn, pid: str, mid: str, form: Posted) -> Response:
    if form is None:
        ctx = _page(request, conn, pid, "write")
        record = _model(conn, ctx, mid)
        problem = _UploadProblem(422, "analysis.error.too_many_fields")
        return _predict_view(request, ctx, record, status=422, problem=problem)
    ctx = _action(request, conn, pid, _text(form, "csrf_token"))
    record = _model(conn, ctx, mid)
    dataset = _dataset(conn, ctx, _text(form, "dataset_id"))
    try:
        job = models.submit_batch_predict(
            conn,
            ctx.auth.user,
            pid,
            record.id,
            dataset.id,
            include_columns=_texts(form, "include"),
            include_contributions=_text(form, "contributions") == "true",
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
