"""The AutoML model screens: the project's models (leaderboard), the model page (overview,
leaderboard, importance, trial history, metrics, serving), export and import, and the
project export job.

Same services and authorization as the API: reading a model needs read access, deleting it
write access; exporting needs read access; importing is for administrators only (checked
before anything else, as the API's dependency does). Everything shown comes from the stored
model record, capped; nothing is recomputed or unpickled per request.
"""

import json
import math
import re

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from fione import i18n
from fione.api import routes_models
from fione.api.deps import Conn, cookie_auth, request_host
from fione.api.downloads import tmp_dir
from fione.api.routes_jobs import EXPORT_KIND, start_export
from fione.api.routes_models import (
    export_response,
    import_upload,
    serving_bundle_of,
    too_large_for_import,
)
from fione.api.security import origin_matches, tokens_equal
from fione.auth.roles import Role
from fione.engine import diagnostics
from fione.engine import metrics as engine_metrics
from fione.engine.artifact import UntrustedArtifactError
from fione.engine.config import ConfigError, TrainConfig
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.models import service as models
from fione.models.bundle import BundleError
from fione.models.service import ModelNotFound, ModelRecord
from fione.models.transfer import ModelImportError
from fione.modules.registry import redact
from fione.projects import service as projects
from fione.projects.service import DatasetNotFound
from fione.web.access import Ctx, action, context, model_in, page
from fione.web.automl import Posted, _chart, _int_param, _text
from fione.web.easyml import _baseline, _clock, _ratings, _score_sentence
from fione.web.uploads import UploadFormError, UploadProblem, read_form
from fione.web.views import UiError, language, render

router = APIRouter(include_in_schema=False)

MODELS_PER_PAGE = 50
COMPARE_MODELS = 30  # models per comparison chart
LEADERBOARD_ROWS = 50
IMPORTANCE_ROWS = 20
TRIAL_POINTS = 2000  # trials drawn and listed at most
PARAMS_SHOWN = 6  # hyperparameters summarised per leaderboard row
MAIN_METRIC = {"classification": "accuracy", "regression": "rmse"}
FAMILY_TRIAL = re.compile(r"^(?P<family>.+)_(?P<trial>[0-9]{1,9})$")


def _view(request: Request, template: str, ctx: Ctx, **context) -> Response:
    status = context.pop("status", 200)
    return render(
        request,
        template,
        ctx.auth,
        status=status,
        ctx=ctx,
        nav="projects",
        section="models",
        **context,
    )


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    try:
        return float(value) if math.isfinite(value) else None
    except OverflowError:  # an int beyond the float range (a hand-made record)
        return None


# --- the project's models -----------------------------------------------------------------


def _latest_export(conn, pid: str) -> dict | None:
    """The project's newest export job, with a download only when it is the newest finished
    one (the API keeps only that zip)."""
    jobs = store.page_jobs(conn, pid, kind=EXPORT_KIND, limit=1)
    if not jobs:
        return None
    job = jobs[0]
    return {"job": job, "download": job.status == JobStatus.DONE}


def _models_view(request: Request, conn, ctx: Ctx, *, status=200, export_error=None):
    pid = ctx.project.id
    records = models.list_models_brief(conn, pid)
    ratings = _ratings(request, conn, records)
    ranked = sorted(records, key=lambda r: (-ratings[r.id].stars, -r.created_at, -r.id))
    pages = max(1, math.ceil(len(ranked) / MODELS_PER_PAGE))
    number = _int_param(request.query_params.get("page"), 1, 1, pages)
    shown = ranked[(number - 1) * MODELS_PER_PAGE : number * MODELS_PER_PAGE]
    lang = language(request)
    charts = []
    for task, metric in MAIN_METRIC.items():  # one chart per task: their metrics differ
        rows = [(r.name, _number(r.metrics.get(metric))) for r in ranked if r.task == task]
        rows = [(name, value) for name, value in rows if value is not None][:COMPARE_MODELS]
        if rows:
            charts.append(
                _chart(
                    "hbar",
                    [name for name, _ in rows],
                    [round(value, 6) for _, value in rows],
                    i18n.t(f"models.compare.{task}", lang, n=len(rows)),
                    i18n.t(f"metric.{metric}", lang),
                    "",
                )
            )
    return _view(
        request,
        "models.html",
        ctx,
        status=status,
        here=f"/projects/{pid}/models",  # the switches never return to the POST-only export
        rows=[
            {
                "record": r,
                "rating": ratings[r.id],
                "metric": MAIN_METRIC.get(r.task),
                "score": _number(r.metrics.get(MAIN_METRIC.get(r.task, ""))),
            }
            for r in shown
        ],
        total=len(ranked),
        page_number=number,
        pages=pages,
        charts=charts,
        export=_latest_export(conn, pid),
        export_error=export_error,
    )


@router.get("/projects/{pid}/models")
def models_page(request: Request, conn: Conn, pid: str) -> Response:
    return _models_view(request, conn, page(request, conn, pid))


@router.post("/projects/{pid}/models/export")
def export_all(request: Request, conn: Conn, pid: str, form: Posted) -> Response:
    """Queue the project export (read access is enough, as in the API; one at a time)."""
    ctx = action(request, conn, pid, _text(form, "csrf_token"), "read")
    job = start_export(conn, ctx.auth.user, pid)
    if job is None:
        return _models_view(request, conn, ctx, status=409, export_error="models.export.busy")
    return RedirectResponse(f"/projects/{pid}/jobs/{job.id}", 303)


# --- import (administrators only) ---------------------------------------------------------


def _import_context(request: Request, conn, pid: str) -> Ctx:
    """The session, then the admin role (403 for everyone else, project owners included, as
    the API's admin dependency answers before it looks at the project), then the project."""
    auth = cookie_auth(request, conn)
    if auth is None:
        raise UiError(401, "error.session")
    if auth.user.role != Role.ADMIN:
        raise UiError(403, "error.admin_only")
    return context(conn, auth, pid, "read")


def _import_view(request: Request, ctx: Ctx, *, status=200, problem=None) -> Response:
    return _view(
        request,
        "model_import.html",
        ctx,
        status=status,
        problem=problem,
        limit_mb=routes_models.MAX_ARCHIVE_BYTES // 2**20,
    )


@router.get("/projects/{pid}/models/import")
def import_page(request: Request, conn: Conn, pid: str) -> Response:
    return _import_view(request, _import_context(request, conn, pid))


@router.post("/projects/{pid}/models/import")
async def import_model(request: Request, conn: Conn, pid: str) -> Response:
    ctx = _import_context(request, conn, pid)
    if not origin_matches(request.headers.get("origin"), request_host(request)):
        raise UiError(403, "error.forbidden")
    if too_large_for_import(request):  # before anything is read
        return _import_view(
            request, ctx, status=413, problem=UploadProblem(413, "import.error.too_large")
        )
    try:
        form = await read_form(request, tmp_dir(request.app.state.settings), max_fields=2)
    except UploadFormError:
        return _import_view(
            request, ctx, status=400, problem=UploadProblem(400, "upload.error.form")
        )
    try:
        token = form.get("csrf_token")
        if not tokens_equal(ctx.auth.session.csrf, token if isinstance(token, str) else None):
            raise UiError(403, "error.csrf")
        upload = form.get("file")
        if not isinstance(upload, UploadFile) or not upload.filename:
            problem = UploadProblem(422, "import.error.missing")
            return _import_view(request, ctx, status=422, problem=problem)
        # the archive cap is the API's (one value, read at the call: tests patch it there)
        if upload.size is not None and upload.size > routes_models.MAX_ARCHIVE_BYTES:
            problem = UploadProblem(413, "import.error.too_large")
            return _import_view(request, ctx, status=413, problem=problem)
        trust = form.get("trust_foreign") == "true"

        def run() -> ModelRecord:
            return import_upload(request, conn, ctx.auth.user, pid, upload, trust)

        try:
            record = await run_in_threadpool(run)
        except UntrustedArtifactError as e:
            problem = UploadProblem(422, "import.error.untrusted", redact(str(e)))
            return _import_view(request, ctx, status=422, problem=problem)
        except ModelImportError as e:
            if str(e) == "file too large":  # the service's own spool, with the same cap
                problem = UploadProblem(413, "import.error.too_large")
                return _import_view(request, ctx, status=413, problem=problem)
            problem = UploadProblem(422, "import.error.invalid", redact(str(e)))
            return _import_view(request, ctx, status=422, problem=problem)
    finally:
        await form.close()
    return RedirectResponse(f"/projects/{pid}/models/{record.id}", 303)


# --- the model page -----------------------------------------------------------------------


def _params(text) -> str:
    """A short ``name=value`` summary of a trial's hyperparameters (stored as JSON text)."""
    try:
        params = json.loads(text) if isinstance(text, str) else text
    except ValueError:
        return ""
    if not isinstance(params, dict):
        return ""
    items = []
    for key, value in list(params.items())[:PARAMS_SHOWN]:
        shown = f"{value:.4g}" if isinstance(value, float) else str(value)
        items.append(f"{key}={shown[:24]}")
    return ", ".join(items)


def _leaderboard(record: ModelRecord) -> list[dict]:
    """The stored per-family rows, with the winning trial's parameters where they can be
    matched (``Family_N`` names the trial)."""
    trials = {}
    for row in record.trials[:TRIAL_POINTS] if isinstance(record.trials, list) else []:
        if isinstance(row, dict):
            trials[(row.get("family"), row.get("trial"))] = row.get("params")
    rows = []
    for row in (
        record.leaderboard[:LEADERBOARD_ROWS] if isinstance(record.leaderboard, list) else []
    ):
        if not isinstance(row, dict):
            continue
        model = str(row.get("model", ""))
        found = FAMILY_TRIAL.match(model)
        params = ""
        if found:
            params = _params(trials.get((found["family"], int(found["trial"]))))
        rows.append(
            {
                "model": model,
                "family": str(row.get("family", "")),
                "cv_score": _number(row.get("cv_score")),
                "cv_std": _number(row.get("cv_std")),
                "train_secs": _number(row.get("train_secs")),
                "weight": _number(row.get("weight")),
                "params": params,
            }
        )
    return rows


def _history(record: ModelRecord, lang: str) -> dict | None:
    """The trials in the order they ran (trial numbers restart per family), as one point
    series per family plus the best score so far."""
    rows = record.trials[:TRIAL_POINTS] if isinstance(record.trials, list) else []
    series: dict[str, list] = {}
    labels, values, best, best_points = [], [], math.inf, []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or row.get("state") != "complete":
            continue
        score = _number(row.get("score"))
        if score is None:
            continue
        family = str(row.get("family", ""))
        series.setdefault(family, []).append([index, round(score, 6)])
        labels.append(f"{family} #{index}")
        values.append(round(score, 6))
        best = min(best, score)
        best_points.append([index, round(best, 6)])
    if not values:
        return None
    return {
        "type": "scatter",
        "series": [{"name": name, "points": points} for name, points in series.items()],
        "line": {"name": i18n.t("model.history.best", lang), "points": best_points},
        "labels": labels,
        "values": values,
        "label": i18n.t("model.history.chart", lang, n=len(values)),
        "x_name": i18n.t("model.history.trial", lang),
        "y_name": i18n.t("model.history.loss", lang),
    }


def _config(record: ModelRecord) -> list[tuple[str, tuple[str, str | None]]]:
    """The training settings in ``TrainConfig`` order (unknown keys left out), each as
    ``(text, i18n key)``: flags, the task and metrics are shown in words."""
    config = record.config if isinstance(record.config, dict) else {}
    out = []
    for name in TrainConfig.__dataclass_fields__:
        if name not in config:
            continue
        value, key = config[name], None
        if isinstance(value, bool):
            key = "common.yes" if value else "common.no"
        elif name == "task" and value in ("auto", "classification", "regression"):
            key = f"train.task.{value}"
        elif name in ("stopping_metric", "sort_metric") and isinstance(value, str):
            known = ("auto", "logloss", "auc", "accuracy", "rmse", "mae", "r2")
            key = f"train.metric.{value.lower()}" if value.lower() in known else None
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value) or "—"
        out.append((name, ("—" if value is None else str(value), key)))
    return out


def _sort_metric(record: ModelRecord) -> str | None:
    config = record.config if isinstance(record.config, dict) else {}
    try:
        return engine_metrics.resolve(str(config.get("sort_metric", "auto")), record.task, "sort")
    except (ConfigError, KeyError):
        return None


# --- the metrics tab: the training-time diagnostics ----------------------------------------
#
# The stored diagnostics (``engine.diagnostics``) are read as untrusted data: an imported
# record is checked only for its version, task and size. Each part is checked and capped here
# again; a part that does not fit is left out (and said so), and the page never fails on it.

LABEL_CHARS = 100  # of a class label shown
SHARE_LEVELS = (0.1, 0.25, 0.5, 0.75)  # confusion cell shades cm-1..cm-5 (cm-0: no rows)
DIAGNOSTIC_PARTS = {
    "confusion",
    "per_class",
    "roc_chart",
    "pr_chart",
    "calibration_chart",
    "residual_chart",
    "scatter_chart",
}


class _Unreadable(Exception):
    """A part of the stored diagnostics that cannot be shown."""


# What a malformed part can raise while it is read (beyond the explicit checks).
_PART_ERRORS = (
    _Unreadable,
    TypeError,
    ValueError,
    KeyError,
    IndexError,
    AttributeError,
    ArithmeticError,
)


def _count(value) -> int:
    if type(value) is not int or value < 0:
        raise _Unreadable
    return value


def _unit(value) -> float:
    """A rate or probability: finite, in [0, 1]."""
    number = _number(value)
    if number is None or not 0 <= number <= 1:
        raise _Unreadable
    return number


def _finite(value) -> float:
    number = _number(value)
    if number is None:
        raise _Unreadable
    return number


def _fmt(value: float) -> str:
    return f"{value:.4g}"


def _labels(value) -> list[str] | None:
    """The class labels as display text, or None when they are not a list of plain values."""
    if not isinstance(value, list) or not value:
        return None
    if not all(v is None or isinstance(v, str | int | float | bool) for v in value):
        return None
    out = []
    for v in value:
        text = str(v)
        out.append(text if len(text) <= LABEL_CHARS else text[: LABEL_CHARS - 1] + "…")
    return out


def _pairs(part, keys: tuple[str, str], cap: int, check, least: int = 2) -> list[list[float]]:
    """Two equally long stored arrays as ``[x, y]`` points (the first ``cap``)."""
    if not isinstance(part, dict):
        raise _Unreadable
    xs, ys = part.get(keys[0]), part.get(keys[1])
    if not isinstance(xs, list) or not isinstance(ys, list) or len(xs) != len(ys):
        raise _Unreadable
    points = [[check(x), check(y)] for x, y in zip(xs[:cap], ys[:cap], strict=True)]
    if len(points) < least:
        raise _Unreadable
    return points


def _level(share: float) -> int:
    if share <= 0:
        return 0
    return 1 + sum(share > edge for edge in SHARE_LEVELS)


def _percent(share: float) -> str:
    """A share as a whole percentage, never rounded to 0% or 100% when it is neither."""
    text = f"{share * 100:.0f}%"
    if text == "0%" and share > 0:
        return "<1%"
    if text == "100%" and share < 1:
        return ">99%"
    return text


def _confusion(part, labels: list[str] | None, lang: str) -> dict:
    if labels is None or not isinstance(part, dict):
        raise _Unreadable
    classes, matrix = part.get("classes"), part.get("matrix")
    size = len(classes) if isinstance(classes, list) else 0
    if not 2 <= size <= diagnostics.MAX_CONFUSION + 1 or not isinstance(matrix, list):
        raise _Unreadable
    if len(matrix) != size:
        raise _Unreadable
    names = []
    for index in classes:
        if type(index) is not int or not (index == -1 or 0 <= index < len(labels)):
            raise _Unreadable
        names.append(i18n.t("model.diag.other", lang) if index == -1 else labels[index])
    rows = []
    for row in matrix:
        if not isinstance(row, list) or len(row) != size:
            raise _Unreadable
        counts = [_count(n) for n in row]
        total = sum(counts)
        shares = [n / total if total else 0.0 for n in counts]
        rows.append(
            [
                {"count": n, "share": share, "share_text": _percent(share), "level": _level(share)}
                for n, share in zip(counts, shares, strict=True)
            ]
        )
    return {"labels": names, "rows": rows, "other": -1 in classes}


def _per_class(part, labels: list[str] | None, truncated) -> dict:
    if labels is None or not isinstance(part, list) or not part:
        raise _Unreadable
    rows = []
    for row in part[: diagnostics.MAX_PER_CLASS]:
        if not isinstance(row, dict):
            raise _Unreadable
        index = row.get("class")
        if type(index) is not int or not 0 <= index < len(labels):
            raise _Unreadable
        figures = {
            key: None if row.get(key) is None else _unit(row.get(key))
            for key in ("precision", "recall", "f1")
        }
        rows.append({"label": labels[index], **figures, "support": _count(row.get("support"))})
    return {"rows": rows, "truncated": truncated is True}


def _lines(points, label: str, x_name: str, y_name: str, lang: str, diagonal=None) -> dict:
    """A ``lines`` chart of one curve on the unit square, with an optional faint diagonal."""
    series = [{"name": i18n.t("model.diag.curve", lang), "points": points}]
    if diagonal:
        series.append({"name": diagonal, "points": [[0, 0], [1, 1]], "faint": True})
    return {
        "type": "lines",
        "x_type": "value",
        "series": series,
        "labels": [_fmt(x) for x, _ in points],
        "values": [y for _, y in points],
        "label": label,
        "x_name": x_name,
        "y_name": y_name,
        "x_min": 0,
        "x_max": 1,
        "y_min": 0,
        "y_max": 1,
    }


def _calibration(part, positive: str, lang: str) -> dict:
    if not isinstance(part, list):
        raise _Unreadable
    points = []
    for row in part[: diagnostics.CALIBRATION_BINS]:
        if not isinstance(row, dict):
            raise _Unreadable
        points.append([_unit(row.get("predicted")), _unit(row.get("observed"))])
    if not points:
        raise _Unreadable
    return _lines(
        points,
        i18n.t("model.diag.calibration_chart", lang, positive=positive, n=len(points)),
        i18n.t("model.diag.predicted_p", lang),
        i18n.t("model.diag.observed", lang),
        lang,
        diagonal=i18n.t("model.diag.perfect", lang),
    )


def _residuals(part, lang: str) -> dict:
    if not isinstance(part, dict):
        raise _Unreadable
    edges, counts = part.get("edges"), part.get("counts")
    if not isinstance(edges, list) or not isinstance(counts, list):
        raise _Unreadable
    if not 1 <= len(counts) <= diagnostics.RESIDUAL_BINS or len(edges) != len(counts) + 1:
        raise _Unreadable
    edges = [_finite(edge) for edge in edges]
    return _chart(
        "bar",
        [_fmt((low + high) / 2) for low, high in zip(edges, edges[1:], strict=False)],
        [_count(n) for n in counts],
        i18n.t("model.diag.residual_chart", lang, n=len(counts)),
        i18n.t("model.diag.residual", lang),
        i18n.t("model.diag.rows_axis", lang),
    )


def _deciles(part) -> list[tuple[float, float]]:
    """The stored ``by_decile`` summary as ``(mean predicted, mean residual)`` rows."""
    if not isinstance(part, list) or not part:
        raise _Unreadable
    rows = []
    for row in part[: diagnostics.DECILES]:
        if not isinstance(row, dict):
            raise _Unreadable
        rows.append((_finite(row.get("predicted_mean")), _finite(row.get("residual_mean"))))
    return rows


def _scatter(part, deciles: list[tuple[float, float]] | None, lang: str) -> dict:
    """The sampled points, drawn whole; their text alternative is the decile summary when it
    is stored (10 rows over every row, rather than 2,000), else the points. Values are shown
    as stored (the engine rounded them to their spread), never re-rounded."""
    points = _pairs(part, ("actual", "predicted"), diagnostics.MAX_POINTS, _finite, least=1)
    low = min(min(point) for point in points)
    high = max(max(point) for point in points)
    if deciles:
        labels = [str(predicted) for predicted, _ in deciles]
        values = [residual for _, residual in deciles]
        table = {
            "caption": i18n.t("model.diag.deciles", lang),
            "x_name": i18n.t("model.diag.decile_predicted", lang),
            "y_name": i18n.t("model.diag.decile_residual", lang),
        }
    else:
        labels = [str(actual) for actual, _ in points]
        values = [predicted for _, predicted in points]
        table = None
    return {
        "type": "scatter",
        "series": [{"name": i18n.t("model.diag.sample", lang), "points": points}],
        "line": {
            "name": i18n.t("model.diag.diagonal", lang),
            "points": [[low, low], [high, high]],
            "step": False,
        },
        "labels": labels,
        "values": values,
        "label": i18n.t("model.diag.scatter_chart", lang, n=f"{len(points):,}"),
        "x_name": i18n.t("model.diag.actual", lang),
        "y_name": i18n.t("model.diag.predicted", lang),
        "table": table,
    }


def _diagnostics_view(record: ModelRecord, lang: str) -> dict | None:
    """What the metrics tab shows of ``record.diagnostics``: ``confusion``, ``per_class``,
    ``roc_chart``, ``pr_chart``, ``calibration_chart`` (binary), ``residual_chart`` and
    ``scatter_chart`` (regression), each left out when it is missing or malformed
    (``partial``: a stored part was left out), plus the ``rows`` note. None when nothing can
    be shown."""
    found = record.diagnostics
    if not isinstance(found, dict) or type(found.get("version")) is not int:
        return None
    if found["version"] != diagnostics.VERSION or found.get("task") != record.task:
        return None
    view: dict = {}
    partial = False

    def add(name: str, key: str, build) -> None:
        nonlocal partial
        if key not in found:
            return
        try:
            view[name] = build(found[key])
        except _PART_ERRORS:
            partial = True

    if record.task == "classification":
        labels = _labels(found.get("labels"))
        add("confusion", "confusion", lambda part: _confusion(part, labels, lang))
        add(
            "per_class",
            "per_class",
            lambda part: _per_class(part, labels, found.get("per_class_truncated")),
        )
        if labels is not None and len(labels) == 2:
            positive = labels[1]
            auc = _number(found.get("auc"))
            view["auc"] = "—" if auc is None or not 0 <= auc <= 1 else f"{auc:.3f}"
            view["positive"] = positive
            curve = diagnostics.MAX_CURVE_POINTS
            add(
                "roc_chart",
                "roc",
                lambda part: _lines(
                    _pairs(part, ("fpr", "tpr"), curve, _unit),
                    i18n.t("model.diag.roc_chart", lang, positive=positive),
                    i18n.t("model.diag.fpr", lang),
                    i18n.t("model.diag.tpr", lang),
                    lang,
                    diagonal=i18n.t("model.diag.chance", lang),
                ),
            )
            add(
                "pr_chart",
                "pr",
                lambda part: _lines(
                    _pairs(part, ("recall", "precision"), curve, _unit),
                    i18n.t("model.diag.pr_chart", lang, positive=positive),
                    i18n.t("model.diag.recall", lang),
                    i18n.t("model.diag.precision", lang),
                    lang,
                ),
            )
            add("calibration_chart", "calibration", lambda part: _calibration(part, positive, lang))
    elif record.task == "regression":
        add("residual_chart", "residuals", lambda part: _residuals(part, lang))
        deciles = None
        if "by_decile" in found:
            try:
                deciles = _deciles(found["by_decile"])
            except _PART_ERRORS:
                partial = True
        add("scatter_chart", "points", lambda part: _scatter(part, deciles, lang))
    if not view.keys() & DIAGNOSTIC_PARTS:
        return None
    rows = found.get("n_rows")
    if type(rows) is int and rows > 0:
        key = "model.diag.sampled" if found.get("sampled") is True else "model.diag.rows"
        view["rows"] = i18n.t(key, lang, n=f"{rows:,}")
    view["partial"] = partial
    return view


@router.get("/projects/{pid}/models/{mid}")
def model_page(request: Request, conn: Conn, pid: str, mid: str) -> Response:
    ctx = page(request, conn, pid)
    record = model_in(conn, ctx, mid)
    lang = language(request)
    tab = request.query_params.get("tab")
    tab = (
        tab
        if tab in ("overview", "leaderboard", "importance", "history", "metrics")
        else "overview"
    )
    rating = _ratings(request, conn, [record])[record.id]
    baseline = _baseline(request, conn, record)
    elapsed = dataset = None
    if record.job_id is not None:
        try:
            elapsed = (store.get_job(conn, record.job_id).result or {}).get("elapsed")
        except KeyError:  # the job was deleted
            pass
    if record.dataset_id is not None:
        try:
            dataset = projects.get_dataset(conn, record.dataset_id)
        except DatasetNotFound:
            pass
    importance = record.importance if isinstance(record.importance, dict) else {}
    ranked = sorted(
        ((str(k), _number(v) or 0.0) for k, v in importance.items()),
        key=lambda kv: (-kv[1], kv[0]),
    )[:IMPORTANCE_ROWS]
    importance_chart = None
    if ranked:
        importance_chart = _chart(
            "hbar",
            [name for name, _ in ranked],
            [round(value * 100, 2) for _, value in ranked],
            i18n.t("model.importance.chart", lang, n=len(ranked)),
            i18n.t("model.importance.share", lang),
            "",
        )
    try:
        bundle = serving_bundle_of(request, record)
    except (BundleError, ModelNotFound):  # an unsafe image name, or the manifest is gone
        bundle = None
    metric_rows = [
        (str(name), _number(value))
        for name, value in (record.metrics if isinstance(record.metrics, dict) else {}).items()
    ]
    return _view(
        request,
        "model.html",
        ctx,
        record=record,
        tab=tab,
        rating=rating,
        sentence=_score_sentence(record, rating, baseline),
        elapsed=_clock(elapsed) if isinstance(elapsed, int | float) else None,
        dataset=dataset,
        config=_config(record),
        leaderboard=_leaderboard(record),
        sort_metric=_sort_metric(record),
        n_trials=len(record.trials) if isinstance(record.trials, list) else 0,
        history=_history(record, lang),
        importance=ranked,
        importance_chart=importance_chart,
        metric_rows=metric_rows,
        diagnostics=_diagnostics_view(record, lang),
        diagnostics_stored=record.diagnostics is not None,
        bundle=bundle,
    )


@router.get("/projects/{pid}/models/{mid}/export")
def export_model(request: Request, conn: Conn, pid: str, mid: str) -> Response:
    """The model as an export zip, as the API sends it; a model whose files are gone is a
    clean error page, never a cut download."""
    ctx = page(request, conn, pid)
    record = model_in(conn, ctx, mid)
    try:
        return export_response(request, record)
    except ModelNotFound:
        raise UiError(404, "models.error.export") from None


@router.post("/projects/{pid}/models/{mid}/delete")
def delete_model(request: Request, conn: Conn, pid: str, mid: str, form: Posted) -> Response:
    ctx = action(request, conn, pid, _text(form, "csrf_token"))
    record = model_in(conn, ctx, mid)
    models.delete_model(conn, request.app.state.storage, record.id)
    return RedirectResponse(f"/projects/{pid}/models", 303)
