"""The built-in assistant tools (spec section 9): read schema, statistics and results, or
propose a training configuration. None of them writes anything or starts a job.

Privacy matrix, ``allow_samples=False`` (the default) / ``True``:

=====================  ====================================  ================================
what                    off                                   on
=====================  ====================================  ================================
category top values     removed (``top_values_hidden``)        up to 10, each cut to 50 chars
class labels            only ``n_classes``                     up to 50, each cut to 50 chars
diagnostics labels      only ``n_classes`` (``labels_hidden``) up to 50, each cut to 50 chars
regression points       removed (``points_hidden``)            up to 200 pairs
PD category levels      positions (``grid_hidden``)            each cut to 50 chars
PD class outputs        only ``n_outputs`` (``outputs_hidden``) each cut to 50 chars
event/job messages      removed (kind/family/exception kept)   kept, cut to 200 chars
numeric statistics      kept (min, max, quantiles are stats)   kept
names                   cleaned (``clean_text``)               cleaned
=====================  ====================================  ================================

Fields that do not apply to a column (no statistics for text, no outlier rate for anything but
numeric columns, no top values for numbers) are omitted rather than null.

Stored diagnostics and explanations are read as untrusted: an import checks little of their
inside. Each part is rebuilt from the fields it should have, numbers where numbers belong
(anything else becomes null), lists cut to the engine's own caps. These tools only read what
training and the explain job stored; none of them loads a model or computes anything.
"""

import dataclasses
import math
from datetime import datetime

import pandas as pd

from fione.auth.roles import Role, can_access_project
from fione.data.profile import (
    SCORE_REASONS,
    ColumnProfile,
    DatasetProfile,
    LeakCheck,
    leak_check,
    profile_dataset,
)
from fione.engine import diagnostics as diag
from fione.engine.config import ConfigError, TrainConfig
from fione.engine.explain import PD_GRID
from fione.engine.prep import infer_task
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.models import explanations
from fione.models import service as models
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.service import Dataset, DatasetNotFound, DatasetType
from fione.tools.registry import Tool, ToolContext, ToolError, clean_text, fits, register

_MAX_COLUMNS = 200
_SAMPLE_ROWS = 200_000
_TOP_CORRELATIONS = 10
_TOP_VALUES = 10
_VALUE_CHARS = 50
_MAX_CLASS_LABELS = 50
_MAX_IMPORTANCE = 30
_MAX_POINTS = 200  # regression (actual, predicted) pairs, with allow_samples
_MAX_OUTPUTS = 20  # the explain job keeps at most 20 classes per curve
_MESSAGE_CHARS = 200
_RATIONALE_CHARS = 500
_EVENT_DEPTH = 3
_EVENT_LIST = 20

# Event strings that are engine vocabulary rather than user data.
_EVENT_ENUMS = frozenset(
    {
        "kind",
        "family",
        "exception",
        "state",
        "task",
        "sort_metric",
        "stopping_metric",
        "stop_reason",
        "best_single",
        "model",
    }
)
_EVENT_TEXT = frozenset({"message", "error"})  # free text: only with allow_samples
_EVENT_SETTINGS = frozenset({"params", "best_params", "config"})  # hyperparameters and settings
# The names those settings may have: TrainConfig's fields and the families' hyperparameters.
# Any other key (say a class_weight keyed by label) could carry a cell value and is dropped.
_SETTING_KEYS = frozenset(
    {f.name for f in dataclasses.fields(TrainConfig)}
    | {
        "learning_rate",
        "num_leaves",
        "min_child_samples",
        "colsample_bytree",
        "subsample",
        "reg_lambda",
        "max_depth",
        "min_child_weight",
        "depth",
        "l2_leaf_reg",
        "max_features",
        "min_samples_leaf",
        "n_estimators",
        "iterations",
        "criterion",
        "boosting_type",
    }
)
_DROP = object()


def _r(x):
    """``x`` to six significant digits: statistics need no more, and the result stays small."""
    return None if x is None else float(f"{x:.6g}")


def _authorize(ctx: ToolContext, project_id: str | None) -> None:
    """Raise ``PermissionError``/``ProjectNotFound`` unless the user may read the project; a
    job without a project is for admins only."""
    if project_id is None:
        if ctx.user.role != Role.ADMIN:
            raise PermissionError("admin only")
        return
    projects.require_project(ctx.conn, project_id)
    if not can_access_project(ctx.conn, ctx.user, project_id, "read"):
        raise PermissionError("no read access")


def _dataset(ctx: ToolContext, dataset_id: int) -> Dataset:
    dataset = projects.get_dataset(ctx.conn, dataset_id)
    _authorize(ctx, dataset.project_id)
    return dataset


def _resolve_column(names: list[str], given: str, where: str = "dataset") -> str:
    """The schema column called ``given``, or the only one whose cleaned name is ``given``
    (the model sees cleaned names)."""
    if given in names:
        return given
    matches = [n for n in names if clean_text(n) == given]
    if len(matches) != 1:
        raise ToolError(f"column not found in the {where}")
    return matches[0]


def _dataset_block(dataset: Dataset) -> dict:
    return {
        "id": dataset.id,
        "name": clean_text(dataset.name),
        "type": dataset.type.value,
        "n_rows": dataset.n_rows,
        "n_cols": dataset.n_cols,
    }


def _column_entry(col: ColumnProfile, allow_samples: bool) -> dict:
    entry = {
        "name": clean_text(col.name),
        "kind": col.kind,
        "missing_rate": _r(col.missing_rate),
        "n_unique": col.n_unique,
    }
    if col.stats is not None:
        entry["stats"] = {k: _r(v) for k, v in col.stats.items()}
    if col.histogram is not None:
        entry["histogram_bins"] = len(col.histogram)
    if col.kind == "numeric" and col.outlier_rate is not None:
        # an integer-coded categorical has an IQR-based rate too, but it means nothing there
        entry["outlier_rate"] = _r(col.outlier_rate)
    if col.top_values is not None:
        if allow_samples:
            entry["top_values"] = [
                [clean_text(value, _VALUE_CHARS), count] for value, count in col.top_values
            ][:_TOP_VALUES]
        else:
            entry["top_values"] = None
            entry["top_values_hidden"] = True
    return entry


# --- describe_dataset / get_column_stats ---------------------------------


def _fit_columns(result: dict, total: int) -> None:
    """Cut ``columns`` until the result fits the size cap, and say how many are left out."""
    columns = result["columns"]
    while True:
        result["n_columns_listed"] = len(columns)
        if total > len(columns):
            result["n_more_columns"] = total - len(columns)
            result["truncated"] = True
            result["truncated_lists"] = ["columns"]
        if fits(result) or not columns:
            return
        del columns[len(columns) - max(1, len(columns) // 10) :]


def _is_plain(name: str) -> bool:
    """Whether ``name`` has no control characters or odd whitespace (its length is not judged)."""
    return clean_text(name, max_len=len(name) + 1) == name


def _describe_dataset(ctx: ToolContext, args: dict) -> dict:
    dataset = _dataset(ctx, args["dataset_id"])
    names = [name for name, _ in dataset.schema]
    target = _resolve_column(names, args["target"]) if "target" in args else None
    shown = names[:_MAX_COLUMNS]
    read = shown + [target] if target is not None and target not in shown else shown
    frame = ingest.read_dataset_sample(ctx.storage, dataset, _SAMPLE_ROWS, read)
    profile = profile_dataset(frame, target, sample_rows=_SAMPLE_ROWS)
    result = {
        "dataset": _dataset_block(dataset),
        "profile_rows": len(frame),
        "columns": [
            _column_entry(col, ctx.allow_samples) for col in profile.columns if col.name in shown
        ],
        "correlations": [
            {"a": clean_text(a), "b": clean_text(b), "r": _r(r)}
            for a, b, r in profile.correlations[:_TOP_CORRELATIONS]
        ],
        "leak_suspects": [
            {
                "column": clean_text(s.column),
                "reason": clean_text(s.reason),
                "score": _r(s.score),
                "kind": "score" if s.reason in SCORE_REASONS else "exact",
            }
            for s in profile.leak_suspects
        ],
        "leak_check_partial": profile.leak_partial,
    }
    _fit_columns(result, len(names))
    return result


def _get_column_stats(ctx: ToolContext, args: dict) -> dict:
    dataset = _dataset(ctx, args["dataset_id"])
    column = _resolve_column([name for name, _ in dataset.schema], args["column"])
    frame = ingest.read_dataset_sample(ctx.storage, dataset, _SAMPLE_ROWS, [column])
    col = profile_dataset(frame, sample_rows=_SAMPLE_ROWS).columns[0]
    entry = _column_entry(col, ctx.allow_samples)
    if col.histogram is not None:
        entry["histogram"] = [[_r(left), count] for left, count in col.histogram]
    return {"dataset": _dataset_block(dataset), "profile_rows": len(frame), "column": entry}


# --- models ---------------------------------------------------------------


def _model(ctx: ToolContext, model_id: int) -> models.ModelRecord:
    record = models.get_model(ctx.conn, model_id)
    _authorize(ctx, record.project_id)
    return record


def _class_labels(ctx: ToolContext, record: models.ModelRecord) -> list[str] | None:
    """The distinct target values of the dataset the classifier was trained on, if known."""
    if record.task != "classification" or record.dataset_id is None:
        return None
    try:
        dataset = projects.get_dataset(ctx.conn, record.dataset_id)
        if dataset.project_id != record.project_id:
            return None
        target = ingest.read_dataset(ctx.storage, dataset, [record.target])[record.target]
    except (DatasetNotFound, KeyError):  # the dataset or its file is gone
        return None
    return sorted({str(v) for v in target.dropna().unique()})


def _get_leaderboard(ctx: ToolContext, args: dict) -> dict:
    record = _model(ctx, args["model_id"])
    labels = _class_labels(ctx, record)
    result = {
        "model": {
            "id": record.id,
            "name": clean_text(record.name),
            "task": record.task,
            "target": clean_text(record.target),
            "best_model": clean_text(record.best_model),
            "stop_reason": clean_text(record.stop_reason),
            "created_at": record.created_at,
        },
        "leaderboard": [
            {k: clean_text(v) if isinstance(v, str) else v for k, v in row.items()}
            for row in record.leaderboard
        ],
        "metrics": {clean_text(k): v for k, v in record.metrics.items()},
        "n_classes": None if labels is None else len(labels),
    }
    if ctx.allow_samples and labels is not None:
        result["class_labels"] = [clean_text(v, _VALUE_CHARS) for v in labels[:_MAX_CLASS_LABELS]]
        result["class_labels_truncated"] = len(labels) > _MAX_CLASS_LABELS
    return result


def _get_feature_importance(ctx: ToolContext, args: dict) -> dict:
    record = _model(ctx, args["model_id"])
    if args["source"] == "contributions":
        return _contribution_importance(ctx, record)
    ranked = sorted(record.importance.items(), key=lambda kv: (-(kv[1] or 0.0), kv[0]))
    return {
        "model_id": record.id,
        "source": "gain",
        "n_features": len(ranked),
        "importance": [
            {"column": clean_text(column), "importance": _r(value or 0.0)}
            for column, value in ranked[:_MAX_IMPORTANCE]
        ],
    }


# --- stored diagnostics and explanations (untrusted: rebuilt field by field) --------------


def _num(value):
    """``value`` if it is a finite number (never a bool), else None."""
    if type(value) is int or (type(value) is float and math.isfinite(value)):
        return value
    return None


def _nums(value, limit: int) -> list:
    return [_num(v) for v in value[:limit]] if isinstance(value, list) else []


def _flag(value) -> bool | None:
    return value if type(value) is bool else None


def _rows(value, keys: tuple, limit: int) -> list:
    """The first ``limit`` dicts of ``value``, each with only ``keys``, numbers only."""
    if not isinstance(value, list):
        return []
    return [
        {key: _num(row.get(key)) for key in keys} for row in value[:limit] if isinstance(row, dict)
    ]


def _arrays(value, keys: tuple, limit: int) -> dict | None:
    """``{key: numbers}`` for each of ``keys``, all cut to the shortest stored length (the
    arrays run in parallel), or None when ``value`` is not such a dict."""
    if not isinstance(value, dict) or not all(isinstance(value.get(k), list) for k in keys):
        return None
    n = min(limit, *(len(value[k]) for k in keys))
    return {key: _nums(value[key], n) for key in keys}


def _diagnostics_out(record: models.ModelRecord, allow_samples: bool) -> dict:
    found = record.diagnostics
    out = {"model_id": record.id, "task": record.task, "available": False}
    if not isinstance(found, dict) or type(found.get("version")) is not int:
        return out
    if found["version"] != diag.VERSION:
        return out
    out.update(
        available=True, n_rows=_num(found.get("n_rows")), sampled=_flag(found.get("sampled"))
    )
    parts: dict = {}
    if record.task == "classification":
        labels = found.get("labels")
        labels = labels if isinstance(labels, list) else None
        out["n_classes"] = None if labels is None else len(labels)
        if not allow_samples:
            out["labels_hidden"] = True
        elif labels is not None:
            out["labels"] = [clean_text(v, _VALUE_CHARS) for v in labels[:_MAX_CLASS_LABELS]]
            out["labels_truncated"] = len(labels) > _MAX_CLASS_LABELS
        confusion = found.get("confusion")
        if isinstance(confusion, dict):
            size = diag.MAX_CONFUSION + 1
            matrix = confusion.get("matrix")
            parts["confusion"] = {
                "classes": _nums(confusion.get("classes"), size),
                "matrix": [_nums(row, size) for row in matrix[:size]]
                if isinstance(matrix, list)
                else [],
            }
        keys = ("class", "precision", "recall", "f1", "support")
        parts["per_class"] = _rows(found.get("per_class"), keys, diag.MAX_PER_CLASS)
        parts["per_class_truncated"] = _flag(found.get("per_class_truncated"))
        if "auc" in found:  # binary only; null when the stored value is no number
            out["auc"] = _num(found["auc"])
        curves = {"roc": ("fpr", "tpr", "threshold"), "pr": ("precision", "recall", "threshold")}
        for name, keys in curves.items():
            parts[name] = _arrays(found.get(name), keys, diag.MAX_CURVE_POINTS)
        keys = ("predicted", "observed", "count")
        if "calibration" in found:
            parts["calibration"] = _rows(found["calibration"], keys, diag.CALIBRATION_BINS)
    else:
        residuals = found.get("residuals")
        if isinstance(residuals, dict):
            parts["residuals"] = {
                "edges": _nums(residuals.get("edges"), diag.RESIDUAL_BINS + 1),
                "counts": _nums(residuals.get("counts"), diag.RESIDUAL_BINS),
            }
        keys = ("predicted_mean", "residual_mean", "residual_std", "count")
        parts["by_decile"] = _rows(found.get("by_decile"), keys, diag.DECILES)
        if not allow_samples:
            out["points_hidden"] = True
        else:
            points = _arrays(found.get("points"), ("actual", "predicted"), _MAX_POINTS)
            if points is not None:
                out["points"] = points
                out["points_truncated"] = len(found["points"]["actual"]) > len(points["actual"])
    out.update({k: v for k, v in parts.items() if v is not None})
    return out


def _get_model_diagnostics(ctx: ToolContext, args: dict) -> dict:
    return _diagnostics_out(_model(ctx, args["model_id"]), ctx.allow_samples)


def _explanation_status(ctx: ToolContext, record: models.ModelRecord):
    """``(status, stored explanation)``, by the rule of the API's explanations route."""
    stored = explanations.get_explanation(ctx.conn, record.id)
    job = explanations.latest_explain_job(ctx.conn, record.id)
    active = job is not None and job.status in (JobStatus.QUEUED, JobStatus.RUNNING)
    if stored is not None and not active:
        return "done", stored
    return (job.status.value if job is not None else "none"), stored


def _contribution_importance(ctx: ToolContext, record: models.ModelRecord) -> dict:
    stored = explanations.get_explanation(ctx.conn, record.id)
    entries = stored.payload.get("importance") if stored is not None else None
    if not isinstance(entries, list):
        raise ToolError("contribution importance is not computed yet; run the explain job")
    rows = [e for e in entries if isinstance(e, dict) and isinstance(e.get("column"), str)]
    rows.sort(key=lambda e: -(_num(e.get("share")) or 0.0))  # stable: stored order on ties
    return {
        "model_id": record.id,
        "source": "contributions",
        "n_features": len(rows),
        "n_rows": _num(stored.payload.get("n_rows")),
        "computed_at": stored.created_at,
        "importance": [
            {
                "column": clean_text(e["column"]),
                "share": _num(e.get("share")),
                "mean_abs": _num(e.get("mean_abs")),
            }
            for e in rows[:_MAX_IMPORTANCE]
        ],
    }


def _iso(value) -> str | None:
    """A stored datetime grid point, re-rendered from its parsed value (never stored text)."""
    try:
        return datetime.fromisoformat(value).isoformat() if isinstance(value, str) else None
    except ValueError:
        return None


def _curve_out(curve: dict, task: str, allow_samples: bool) -> dict:
    kind = curve.get("kind")
    grid = curve.get("grid") if isinstance(curve.get("grid"), list) else []
    grid = grid[:PD_GRID]
    out: dict = {"kind": kind if kind in ("numeric", "datetime", "category") else None}
    if kind == "numeric":
        out["grid"] = [_num(v) for v in grid]
    elif kind == "datetime":
        out["grid"] = [_iso(v) for v in grid]
    elif allow_samples:
        out["grid"] = [None if v is None else clean_text(v, _VALUE_CHARS) for v in grid]
    else:  # a level's position stands for it; the missing point stays null
        out["grid"] = [None if v is None else i for i, v in enumerate(grid)]
        out["grid_hidden"] = True
    outputs = curve.get("outputs") if isinstance(curve.get("outputs"), list) else []
    outputs = outputs[:_MAX_OUTPUTS]
    if task != "classification":  # the target's name
        out["outputs"] = [clean_text(v) for v in outputs]
    elif allow_samples:
        out["outputs"] = [clean_text(v, _VALUE_CHARS) for v in outputs]
    else:
        out["n_outputs"] = len(outputs)
        out["outputs_hidden"] = True
    average = curve.get("average") if isinstance(curve.get("average"), list) else []
    out["average"] = [_nums(row, len(outputs)) for row in average[: len(grid)]]
    out["n_rows"] = _num(curve.get("n_rows"))
    return out


def _get_partial_dependence(ctx: ToolContext, args: dict) -> dict:
    record = _model(ctx, args["model_id"])
    names = explanations.model_columns(record)
    column = _resolve_column(names, args["column"], "model")
    status, stored = _explanation_status(ctx, record)
    out = {"model_id": record.id, "column": clean_text(column), "status": status}
    curves = stored.payload.get("partial_dependence") if stored is not None else None
    curves = [
        c
        for c in (curves if isinstance(curves, list) else [])
        if isinstance(c, dict) and c.get("column") in names
    ]
    curve = next((c for c in curves if c["column"] == column), None)
    if curve is None:
        out["available"] = False
        if stored is not None:
            out["computed_columns"] = sorted({clean_text(c["column"]) for c in curves})
        return out
    out.update(available=True, computed_at=stored.created_at)
    return {**out, **_curve_out(curve, record.task, ctx.allow_samples)}


# --- jobs -----------------------------------------------------------------


def _event_value(key: str, value, etype: str, allow_samples: bool, depth: int, settings: bool):
    """``value`` if it is a number or engine vocabulary (or, in settings, a short string);
    free text only with ``allow_samples``; ``_DROP`` for everything else."""
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        if settings:
            return clean_text(value)
        if key in _EVENT_ENUMS or (etype == "stopped" and key == "reason"):
            return clean_text(value)
        if allow_samples and key in _EVENT_TEXT:
            return clean_text(value, _MESSAGE_CHARS)
        return _DROP
    if depth >= _EVENT_DEPTH:
        return _DROP
    settings = settings or key in _EVENT_SETTINGS
    if isinstance(value, dict):
        items = (
            (clean_text(k), _event_value(k, v, etype, allow_samples, depth + 1, settings))
            for k, v in value.items()
            if not settings or allow_samples or k in _SETTING_KEYS
        )
        return {k: v for k, v in items if v is not _DROP}
    if isinstance(value, list):
        items = [
            _event_value(key, v, etype, allow_samples, depth + 1, settings)
            for v in value[:_EVENT_LIST]
        ]
        return [v for v in items if v is not _DROP]
    return _DROP


def _event_data(etype: str, data, allow_samples: bool) -> dict:
    if not isinstance(data, dict):
        return {}
    cleaned = _event_value("", data, etype, allow_samples, 0, False)
    return cleaned if isinstance(cleaned, dict) else {}


def _get_training_events(ctx: ToolContext, args: dict) -> dict:
    job = store.get_job(ctx.conn, args["job_id"])
    _authorize(ctx, job.project_id)
    events = store.events_since(ctx.conn, job.id)
    block = {
        "id": job.id,
        "kind": clean_text(job.kind),
        "status": job.status.value,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }
    if job.message:
        # a failure message can quote the user's data (a class label, a cell)
        block["message"] = clean_text(job.message, _MESSAGE_CHARS) if ctx.allow_samples else None
        block["message_hidden"] = not ctx.allow_samples
    return {
        "job": block,
        "n_events": len(events),
        "order": "newest_first",  # so that a size cut drops the oldest
        "events": [
            {
                "id": event_id,
                "type": event.type,
                "ts": event.ts,
                "data": _event_data(event.type, event.data, ctx.allow_samples),
            }
            for event_id, event in reversed(events[-args["last_n"] :])
        ],
    }


# --- propose_training_config ----------------------------------------------


def _runtime_secs(n_rows: int) -> int:
    return 120 if n_rows < 10_000 else 600 if n_rows < 100_000 else 1800


@dataclasses.dataclass(frozen=True)
class Proposal:
    """What a training proposal rests on, with the dataset's raw column names."""

    task: str  # inferred from the whole target column
    profile: DatasetProfile  # of the columns read, profiled with the target
    target: ColumnProfile
    ignore: list[ColumnProfile]  # id and constant columns other than the target
    y: pd.Series  # the whole target column


def propose(
    storage,
    dataset: Dataset,
    target: str,
    columns: list[str],
    sample_rows: int = _SAMPLE_ROWS,
    *,
    profile: DatasetProfile | None = None,
    check: LeakCheck | None = None,
    task: str | None = None,
) -> Proposal:
    """Profile ``columns`` (and ``target``) of ``dataset`` and infer the task: the rules the
    assistant's ``propose_training_config`` and the EasyML analysis screen share.

    ``profile``: a profile without target of the same sample (``sample_profile``), so only
    the target's leak suspects are computed here. ``check`` and ``task``: this target's leak
    check and task from an earlier proposal with that profile; then neither is recomputed.
    """
    read = columns if target in columns else [*columns, target]
    if profile is None:
        frame = ingest.read_dataset_sample(storage, dataset, sample_rows, read)
        profile = profile_dataset(frame, target, sample_rows=sample_rows)
    else:
        if check is None:  # the sample is read only for the leak check
            frame = ingest.read_dataset_sample(storage, dataset, sample_rows, read)
            check = leak_check(frame, profile.columns, target)
        profile = dataclasses.replace(
            profile, leak_suspects=check.suspects, leak_partial=check.partial
        )
    # the whole target column (one column) decides the task, not just the head of the file
    y = ingest.read_dataset(storage, dataset, [target])[target]
    if task is None:
        task = infer_task(y)
    listed = set(columns)
    ignore = [
        col
        for col in profile.columns
        if col.name != target and col.name in listed and col.kind in ("id", "constant")
    ]
    return Proposal(task, profile, next(c for c in profile.columns if c.name == target), ignore, y)


def sample_profile(
    storage, dataset: Dataset, columns: list[str], sample_rows: int = _SAMPLE_ROWS
) -> DatasetProfile:
    """The target-independent profile of the sample ``propose`` reads (pass it as its
    ``profile``)."""
    frame = ingest.read_dataset_sample(storage, dataset, sample_rows, columns)
    return profile_dataset(frame, sample_rows=sample_rows)


def _propose_training_config(ctx: ToolContext, args: dict) -> dict:
    dataset = _dataset(ctx, args["dataset_id"])
    names = [name for name, _ in dataset.schema]
    target = _resolve_column(names, args["target"])
    if not _is_plain(target):
        raise ToolError("the target column name is not plain text and cannot be proposed")
    found = propose(ctx.storage, dataset, target, names[:_MAX_COLUMNS])
    profile, task = found.profile, found.task

    warnings: list[str] = []
    suggestions: list[dict] = []
    ignored: list[str] = []
    if dataset.type != DatasetType.TRAIN:
        warnings.append(f"this is a {dataset.type.value} dataset; training needs a train dataset")
    if len(names) > _MAX_COLUMNS:
        warnings.append(f"only the first {_MAX_COLUMNS} columns were examined")
    ignore = {col.name for col in found.ignore}
    for col in profile.columns:
        if col.name == target:
            if col.kind in ("id", "constant"):
                warnings.append(f"the target looks like a {col.kind} column; check the choice")
            if col.missing_rate > 0:
                warnings.append("the target has missing values, which training refuses")
        elif col.name in ignore:
            suggestions.append({"column": clean_text(col.name), "reason": f"{col.kind} column"})
            if _is_plain(col.name):
                ignored.append(col.name)
            else:
                warnings.append(
                    f"column '{clean_text(col.name)}' is not plain text; ignore it by hand"
                )
    for suspect in profile.leak_suspects:
        name, reason = clean_text(suspect.column), clean_text(suspect.reason)
        if suspect.reason in SCORE_REASONS:  # a strong legitimate column can score as high
            warnings.append(
                f"column '{name}': {reason} (score {_r(suspect.score)}); it may be a target "
                "leak, so check that it is known at prediction time"
            )
            continue
        reason = f"possible target leak: {reason}"
        suggestions.append({"column": name, "reason": reason})
        warnings.append(f"column '{name}': {reason}")
    if profile.leak_partial:
        warnings.append("the leak check ran out of time; some columns were not scored")
    try:
        config = TrainConfig(
            target=target,
            task=task,
            max_runtime_secs=_runtime_secs(dataset.n_rows),
            ignored_columns=ignored,
        ).validate()
    except ConfigError as e:
        raise ToolError(clean_text(e, _MESSAGE_CHARS)) from None
    notes = args.get("notes")
    return {
        "proposal": True,
        "config": config.to_dict(),
        "ignored_suggestions": suggestions,
        "warnings": warnings,
        "rationale": None if notes is None else clean_text(notes, _RATIONALE_CHARS),
    }


# --- registration -----------------------------------------------------------

_ID = {"type": "integer", "minimum": 1, "maximum": 2**63 - 1}  # SQLite integers
_COLUMN = {"type": "string", "maxLength": 500}


def _schema(properties: dict, required: list[str]) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


for _tool in (
    Tool(
        "describe_dataset",
        "Describe a dataset: per-column kind, missing rate, statistics, the strongest "
        "correlations and, when a target is given, columns that may leak it (exact matches, "
        "and columns that predict it suspiciously well on their own). A score-based suspect "
        "may be a legitimate strong column; no score is computed for a target with more than "
        "100 classes.",
        _schema(
            {"dataset_id": _ID, "target": {**_COLUMN, "description": "optional target column"}},
            ["dataset_id"],
        ),
        True,
        _describe_dataset,
    ),
    Tool(
        "get_column_stats",
        "Statistics of one column of a dataset.",
        _schema({"dataset_id": _ID, "column": _COLUMN}, ["dataset_id", "column"]),
        True,
        _get_column_stats,
    ),
    Tool(
        "get_leaderboard",
        "The leaderboard, metrics and task of a trained model.",
        _schema({"model_id": _ID}, ["model_id"]),
        True,
        _get_leaderboard,
    ),
    Tool(
        "get_feature_importance",
        "The most important input columns of a trained model: by the trees' own split "
        "importance, recorded at training (source 'gain'), or by each column's mean absolute "
        "contribution to the predictions (source 'contributions'), which the explain job "
        "computes.",
        _schema(
            {
                "model_id": _ID,
                "source": {"type": "string", "enum": ["gain", "contributions"], "default": "gain"},
            },
            ["model_id"],
        ),
        True,
        _get_feature_importance,
    ),
    Tool(
        "get_model_diagnostics",
        "A model's training-time diagnostics, from its cross-validation predictions (so "
        "slightly optimistic): for classification the confusion matrix and per-class "
        "precision, recall and F1, and with two classes the AUC, ROC and precision-recall "
        "curves and calibration; for regression the residual histogram and residuals by decile "
        "of the prediction. Classes are referred to by index.",
        _schema({"model_id": _ID}, ["model_id"]),
        True,
        _get_model_diagnostics,
    ),
    Tool(
        "get_partial_dependence",
        "How a model's average prediction changes with one input column (partial dependence), "
        "as stored by the explain job for the most important columns; nothing is computed "
        "here. For classification the values are probabilities of each output class.",
        _schema({"model_id": _ID, "column": _COLUMN}, ["model_id", "column"]),
        True,
        _get_partial_dependence,
    ),
    Tool(
        "get_training_events",
        "The most recent progress events of a job, newest first.",
        _schema(
            {
                "job_id": _ID,
                "last_n": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
            },
            ["job_id"],
        ),
        True,
        _get_training_events,
    ),
    Tool(
        "propose_training_config",
        "Propose a training configuration for a dataset and target column. This only returns a "
        "proposal for the user to confirm; nothing is started.",
        _schema(
            {
                "dataset_id": _ID,
                "target": _COLUMN,
                "notes": {"type": "string", "maxLength": 2000},
            },
            ["dataset_id", "target"],
        ),
        True,
        _propose_training_config,
    ),
):
    register(_tool)
