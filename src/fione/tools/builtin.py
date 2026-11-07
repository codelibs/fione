"""The built-in assistant tools (spec section 9): read schema, statistics and results, or
propose a training configuration. None of them writes anything or starts a job.

Privacy matrix, ``ToolContext.allow_samples``: ``True`` for the assistant, which sends example
values to the configured model, ``False`` for MCP, which never gets them:

=====================  ====================================  ================================
what                    False (MCP)                           True (assistant)
=====================  ====================================  ================================
category top values     removed (``top_values_hidden``)        up to 10, each cut to 50 chars
class labels            only ``n_classes``                     up to 50, each cut to 50 chars
diagnostics labels      only ``n_classes`` (``labels_hidden``) up to 50, each cut to 50 chars
regression points       removed (``points_hidden``)            up to 200 pairs
PD category levels      positions (``grid_hidden``)            each cut to 50 chars
PD numeric/time grids   kept (quantile points, like stats)     kept
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
import re
import time
from datetime import datetime

import pandas as pd

from fione.auth.roles import ProjectAccess, Role, can_access_project, project_access
from fione.data.profile import (
    SCORE_REASONS,
    ColumnProfile,
    DatasetProfile,
    LeakCheck,
    leak_check,
    leak_code,
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
from fione.modules.registry import MAX_OUTPUT_CELLS
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.service import Dataset, DatasetNotFound, DatasetType
from fione.tools import link_names
from fione.tools.registry import Tool, ToolContext, ToolError, clean_text, fits, register

_MAX_COLUMNS = 200
# Said in a result, where the model is looking when it chooses its next call: a small model asked
# for a proposal otherwise answers in text far more often than it calls the tool.
_NEXT_AFTER_DESCRIBE = (
    "If the user asked for a training suggestion, call propose_training_config now with this"
    " dataset_id and the target column."
)
_NEXT_TO_TRAIN = (
    "If the user asked for a training suggestion, call describe_dataset on the dataset with the"
    " column to predict first."
)
_NEXT_TO_JOIN = (
    "If the user named two datasets to join, call propose_join with the key of their link."
    " To answer how the datasets should be combined, call propose_first_join now (target: the"
    " column the user wants to predict, if they said which): the user then sees the join as a"
    " card they can confirm. Do not describe the join in text first. "
)
_OVERVIEW_GAPS = 20  # columns named in an overview as the ones with the most missing values
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
_MAX_PROJECTS = 50  # listed at most; the size cap may cut more
_MAX_DATASETS = 200
_MAX_MODELS = 200

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
    job without a project is for admins only. With ``ctx.project_id`` set, any other project,
    and a job without one, is refused whoever asks."""
    if ctx.project_id is not None and project_id != ctx.project_id:
        raise PermissionError("outside the project of this conversation")
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


_LINK_COLUMNS = 20  # column names listed for each dataset of find_table_links


def _linked_dataset(dataset: Dataset, listed: int) -> dict:
    """The dataset block with its first ``listed`` column names, so the model can tell which
    table holds the column to predict and what each one is about."""
    block = _dataset_block(dataset)
    if listed:
        block["columns"] = [clean_text(name) for name, _ in dataset.schema[:listed]]
        if dataset.n_cols > listed:
            block["n_more_columns"] = dataset.n_cols - listed
    return block


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
    listed = len(result["columns"])
    result["n_columns_listed"] = listed
    if len(names) > listed:  # past the first 200 columns
        result["n_more_columns"] = len(names) - listed
        result["truncated"] = True
        result["truncated_lists"] = ["columns"]
    if target is not None:
        result["next_step"] = _NEXT_AFTER_DESCRIBE
    if not fits(result, ctx.max_result_bytes):
        result = _overview(ctx, result, profile, names, target)
    return result


def _overview(
    ctx: ToolContext, detailed: dict, profile, names: list[str], target: str | None
) -> dict:
    """What a wide dataset gets in place of its columns' statistics, which do not fit the room
    of the request: the names of the columns by kind, the missing rates, the target in full and
    the same correlations and leak suspects. ``get_column_stats`` gives one column's figures."""
    by_kind: dict[str, list[str]] = {}
    for col in profile.columns:
        by_kind.setdefault(col.kind, []).append(clean_text(col.name))
    gaps = sorted((c for c in profile.columns if c.missing_rate > 0), key=lambda c: -c.missing_rate)
    result = {
        "dataset": detailed["dataset"],
        "profile_rows": detailed["profile_rows"],
        "overview": "columns are listed by kind without statistics; use get_column_stats for one",
        "columns_by_kind": by_kind,
        "n_columns_with_missing_values": len(gaps),
        "most_missing": {clean_text(c.name): _r(c.missing_rate) for c in gaps[:_OVERVIEW_GAPS]},
        "correlations": detailed["correlations"],
        "leak_suspects": detailed["leak_suspects"],
        "leak_check_partial": detailed["leak_check_partial"],
    }
    if target is not None:
        entry = next((c for c in profile.columns if c.name == target), None)
        if entry is not None:
            result["target"] = _column_entry(entry, ctx.allow_samples)
    if "next_step" in detailed:
        result["next_step"] = detailed["next_step"]
    while True:
        listed = sum(len(v) for v in by_kind.values())
        result["n_columns_listed"] = listed
        if listed < len(names):
            result["n_more_columns"] = len(names) - listed
            result["truncated"] = True
        if fits(result, ctx.max_result_bytes) or not listed:
            break
        longest = max(by_kind.values(), key=len)
        del longest[len(longest) - max(1, len(longest) // 10) :]
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
    names = set(explanations.model_columns(record))  # only the model's own columns
    rows = [
        e
        for e in entries
        if isinstance(e, dict) and isinstance(e.get("column"), str) and e["column"] in names
    ]
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


# One trial (the folds and the refit) costs about this many seconds per cell (rows x columns)
# on the larger sets measured; a run should try about TRIALS_WANTED of them.
SECS_PER_CELL = 6e-6
TRIALS_WANTED = 30
MAX_RUNTIME_SECS = 1800
MIN_RUNTIME_SECS = 120
# Skew above which a target of 0 or more is suggested for target_transform="log1p". On every
# regression set measured with RMSLE that skewed 0.5 or more, the logarithm helped or held; 1.0
# keeps the tip off targets that are nearly symmetric.
TARGET_SKEW = 1.0
RARE_CLASS_SHARE = 0.10  # below this share of the rows, suggest decision="balanced"
# A column named like an identifier (id, user_id, userId, 顧客ID, 番号) that holds each value in
# several rows, at least REPEATED_ID_GROUPS values, may tie rows together: suggest cv_group_column.
REPEATED_ID_GROUPS = 10
REPEATED_ID_MIN_ROWS = 2  # rows per value, on average
_ID_NAME = re.compile(r"(?<![A-Za-z])(?:id|ID|Id)(?![a-z])|[a-z0-9](?:Id|ID)(?![a-z])|番号")


def runtime_need_secs(dataset: Dataset) -> float:
    """Seconds a run needs to try about ``TRIALS_WANTED`` models on ``dataset``."""
    cells = dataset.n_rows * max(1, dataset.n_cols - 1)
    return cells * SECS_PER_CELL * TRIALS_WANTED


def _runtime_secs(dataset: Dataset) -> int:
    """The proposed run time: ``runtime_need_secs`` in whole minutes, from 2 to 30 minutes."""
    minutes = math.ceil(runtime_need_secs(dataset) / 60)
    return min(MAX_RUNTIME_SECS, max(MIN_RUNTIME_SECS, minutes * 60))


def is_skewed_target(y: pd.Series, task: str) -> bool:
    """A non-negative regression target skewed enough (``TARGET_SKEW``) that
    ``target_transform="log1p"`` may pay."""
    y = y.dropna()
    if task != "regression" or len(y) == 0 or not pd.api.types.is_numeric_dtype(y):
        return False
    return bool(y.min() >= 0 and y.skew() > TARGET_SKEW)


def rare_class_share(y: pd.Series, task: str) -> float | None:
    """The share of the rarest class when it is under ``RARE_CLASS_SHARE`` (where
    ``decision="balanced"`` may pay), else None."""
    y = y.dropna()
    if task != "classification" or y.nunique() < 2:
        return None
    share = float(y.value_counts(normalize=True).min())
    return share if share < RARE_CLASS_SHARE else None


def repeated_id_column(profile: DatasetProfile, target: str) -> ColumnProfile | None:
    """The first column other than ``target`` that is named like an identifier and repeats its
    values over rows (``REPEATED_ID_GROUPS`` or more values, ``REPEATED_ID_MIN_ROWS`` rows each on
    average), where ``cv_group_column`` may keep the validation honest; else None."""
    for col in profile.columns:
        if (
            col.name != target
            and col.kind in ("categorical", "numeric", "text")
            and _ID_NAME.search(col.name)
            and col.n_unique >= REPEATED_ID_GROUPS
            and profile.n_rows >= REPEATED_ID_MIN_ROWS * col.n_unique
        ):
            return col
    return None


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


def _warning(code: str, message: str, **params) -> dict:
    """A proposal's warning: ``message`` is English for the model; the card translates the
    ``code`` with its ``params``."""
    return {"code": code, "message": message, "params": params}


def _propose_training_config(ctx: ToolContext, args: dict) -> dict:
    dataset = _dataset(ctx, args["dataset_id"])
    names = [name for name, _ in dataset.schema]
    target = _resolve_column(names, args["target"])
    if not _is_plain(target):
        raise ToolError("the target column name is not plain text and cannot be proposed")
    found = propose(ctx.storage, dataset, target, names[:_MAX_COLUMNS])
    profile, task = found.profile, found.task

    warnings: list[dict] = []
    suggestions: list[dict] = []
    ignored: list[str] = []
    if dataset.type != DatasetType.TRAIN:
        warnings.append(
            _warning(
                "not_train",
                f"this is a {dataset.type.value} dataset; training needs a train dataset",
            )
        )
    if len(names) > _MAX_COLUMNS:
        warnings.append(
            _warning(
                "many_columns",
                f"only the first {_MAX_COLUMNS} columns were examined",
                n=_MAX_COLUMNS,
            )
        )
    ignore = {col.name for col in found.ignore}
    for col in profile.columns:
        if col.name == target:
            if col.kind in ("id", "constant"):
                warnings.append(
                    _warning(
                        f"target_{col.kind}",
                        f"the target looks like a {col.kind} column; check the choice",
                    )
                )
            if col.missing_rate > 0:
                warnings.append(
                    _warning(
                        "target_missing", "the target has missing values, which training refuses"
                    )
                )
        elif col.name in ignore:
            suggestions.append(
                {"column": clean_text(col.name), "reason": f"{col.kind} column", "code": col.kind}
            )
            if _is_plain(col.name):
                ignored.append(col.name)
            else:
                column = clean_text(col.name)
                warnings.append(
                    _warning(
                        "column_not_plain",
                        f"column '{column}' is not plain text; ignore it by hand",
                        column=column,
                    )
                )
    for suspect in profile.leak_suspects:
        name, reason = clean_text(suspect.column), clean_text(suspect.reason)
        code = leak_code(suspect.reason)
        if suspect.reason in SCORE_REASONS:  # a strong legitimate column can score as high
            warnings.append(
                _warning(
                    code,
                    f"column '{name}': {reason} (score {_r(suspect.score)}); it may be a target "
                    "leak, so check that it is known at prediction time",
                    column=name,
                    score=_r(suspect.score),
                )
            )
            continue
        reason = f"possible target leak: {reason}"
        suggestions.append({"column": name, "reason": reason, "code": code})
        warnings.append(_warning(code, f"column '{name}': {reason}", column=name))
    if profile.leak_partial:
        warnings.append(
            _warning("leak_partial", "the leak check ran out of time; some columns were not scored")
        )
    if is_skewed_target(found.y, task):
        warnings.append(
            _warning(
                "skewed_target",
                "the target is not negative and skewed; if the score is a relative error "
                "(such as RMSLE), target_transform 'log1p' may help",
            )
        )
    if (share := rare_class_share(found.y, task)) is not None:
        warnings.append(
            _warning(
                "rare_class",
                f"the rarest class is {share:.1%} of the rows; if the score treats every class "
                "alike (such as balanced accuracy), decision 'balanced' may help",
                share=f"{max(share * 100, 0.1):.1f}",
            )
        )
    overrides = {
        k: args[k] for k in ("max_runtime_secs", "decision", "target_transform") if k in args
    }
    if "group_column" in args:
        group = args["group_column"]
        try:
            group = _resolve_column(names[:_MAX_COLUMNS], group)
        except ToolError:
            raise ToolError("group_column is not a column of the dataset") from None
        if group == target or not _is_plain(group):
            raise ToolError("group_column must be a plain-text column other than the target")
        overrides["cv_group_column"] = group
    elif (repeated := repeated_id_column(profile, target)) is not None:
        column = clean_text(repeated.name)
        warnings.append(
            _warning(
                "repeated_id",
                f"column '{column}' looks like an id that repeats over rows; if rows of one "
                "value are related (the same customer, say), group_column keeps them together "
                "in validation so the score is not too good",
                column=column,
            )
        )
    if overrides.get("decision", "argmax") != "argmax" and task != "classification":
        raise ToolError("decision applies to a classification target only")
    if overrides.get("target_transform", "none") != "none":
        if task != "regression":
            raise ToolError("target_transform applies to a regression target only")
        if pd.api.types.is_numeric_dtype(found.y) and found.y.min() <= -1:
            raise ToolError("target_transform 'log1p' needs target values above -1")
    try:
        config = TrainConfig(
            target=target,
            task=task,
            **{"max_runtime_secs": _runtime_secs(dataset), **overrides},
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


# --- links between the datasets of a project -------------------------------

_LINK_DATASETS = 8
_FLOAT_TYPES = ("halffloat", "float", "double")  # Arrow's names, as the schema keeps them
_LINK_FULL_ROWS = 5_000_000  # a key column of up to this many rows is read whole, else sampled
_LINK_SAMPLE_ROWS = 200_000
_LINK_SECS = 30.0  # the reading stops after this long, and the result says so
_MIN_SHARED = 0.5
_MIN_VALUE_KEYS = 100  # a key found by its values alone needs this many values: small ids overlap
_MIN_SEQUENCE_COVERAGE = 0.3  # of a key that is a run of whole numbers, found by values alone
_MIN_COVERAGE = 0.05  # of the longer key column, for names that are not the same
_MIN_REPEATED_KEYS = 20  # keys that repeat on both sides need this many values to be reported
_MAX_LINKS = 20
_LINK_VALUE_COLUMNS = 8  # columns of a dataset compared by their values, whatever their names
# the names that relate two columns say more than their values alone; the sort puts the most
# certain links first, and the next call is made on the first
_BASIS_RANK = {
    link_names.SAME_NAME: 0,
    link_names.TABLE_ID: 0,
    link_names.SIMILAR_NAME: 1,
    link_names.VALUES: 2,
}
_MAX_REPEATING_LINKS = 2  # links where both sides repeat come last and are the least certain


def _key_set(frame: pd.DataFrame, column: str) -> tuple[set[str], bool] | None:
    """The distinct values of the column as text and whether each appears once, or None if the
    column cannot be a key: constant, or a float that is not a whole number (a whole-number
    column with gaps is read as float)."""
    s = frame[column].dropna()
    if pd.api.types.is_float_dtype(s.dtype):
        if not (s == s.round()).all():
            return None
        s = s.astype("int64")
    distinct = s.drop_duplicates()
    if len(distinct) < 2:
        return None
    return set(distinct.astype(str)), len(distinct) == len(s)


def _key_tuples(frame: pd.DataFrame, columns: list[str]) -> tuple[set[str], bool] | None:
    """What ``_key_set`` gives for several columns that identify a row together: the distinct
    combinations as text and whether each appears once. A row with a missing part is left out."""
    whole = frame[columns].dropna()
    parts = []
    for column in columns:
        s = whole[column]
        if pd.api.types.is_float_dtype(s.dtype):
            if not (s == s.round()).all():
                return None
            s = s.astype("int64")
        parts.append(s.astype(str))
    combined = parts[0].str.cat(parts[1:], sep="\x1f")
    distinct = combined.drop_duplicates()
    if len(distinct) < 2:
        return None
    return set(distinct), len(distinct) == len(combined)


def _read_keys(ctx: ToolContext, dataset: Dataset, columns: list[str]) -> tuple[pd.DataFrame, bool]:
    """The columns of the dataset, whole when it is small enough, else a sample spread over
    the file; and whether it is a sample."""
    if dataset.n_rows <= _LINK_FULL_ROWS:
        return ingest.read_dataset(ctx.storage, dataset, columns), False
    return ingest.read_dataset_spread(ctx.storage, dataset, _LINK_SAMPLE_ROWS, columns), True


def _value_columns(dataset: Dataset, usable: dict[str, str]) -> list[str]:
    """The columns of the dataset compared by their values alone: those with an id-like name
    first, at most ``_LINK_VALUE_COLUMNS``."""
    names = list(usable.values())
    names.sort(key=lambda n: not link_names.is_id_like(n))  # stable: the file's order within
    return names[:_LINK_VALUE_COLUMNS]


def _is_sequence(values: set[str]) -> bool:
    """The values are whole numbers with none missing between the smallest and the largest: a
    row number, or a list of ids that other ids can overlap by chance."""
    try:
        numbers = [int(v) for v in values]
    except ValueError:
        return False
    return max(numbers) - min(numbers) + 1 == len(numbers)


def _link(
    a: Dataset, b: Dataset, column_a: str, column_b: str, basis: str, found, key_ok=(True, True)
) -> dict | None:
    """The link of the two columns given their key sets, or None when the values do not say
    they are one key."""
    (values_a, unique_a), (values_b, unique_b) = found
    if basis != link_names.SAME_NAME and (
        len(values_a & values_b) / max(len(values_a), len(values_b)) < _MIN_COVERAGE
    ):
        return None  # a few small ids inside a long id column: they overlap by chance
    if basis == link_names.VALUES:
        # one side is the key and most values of the other are in it
        if unique_a == unique_b or not all(key_ok):
            return None
        key, other = (values_a, values_b) if unique_a else (values_b, values_a)
        inter = len(key & other)
        if inter < _MIN_VALUE_KEYS or inter / len(other) < _MIN_SHARED:
            return None
        if inter / len(key) < _MIN_SEQUENCE_COVERAGE and _is_sequence(key):
            return None  # a row number or a short list of ids that the other column only touches
        shared = inter / len(other)
    else:
        # the share of the smaller set of values that the larger one has
        shared = len(values_a & values_b) / min(len(values_a), len(values_b))
        if shared < _MIN_SHARED:
            return None
        if not (unique_a or unique_b) and min(len(values_a), len(values_b)) < _MIN_REPEATED_KEYS:
            return None  # few values on both sides: a category such as a label, not a key
    link = {"datasets": [a.id, b.id]}
    if column_a == column_b:
        link["column"] = clean_text(column_a)
    else:
        link["columns"] = [clean_text(column_a), clean_text(column_b)]
    link["relation"] = (
        "one_to_one"
        if unique_a and unique_b
        else "one_to_many"
        if unique_a or unique_b
        else "many_to_many"
    )
    link["one_row_per_key"] = a.id if unique_a else b.id if unique_b else None
    link["shared"] = round(shared, 2)
    if basis != link_names.SAME_NAME:  # the usual case is not said
        link["basis"] = basis
    return link


def _project_links(
    ctx: ToolContext, project_id: str
) -> tuple[list[dict], list[Dataset], list[Dataset], bool, bool]:
    """The links to show for a project, ranked, with the datasets examined and all of them, and
    whether any was sampled and whether the time ran out."""
    every = projects.list_datasets(ctx.conn, project_id)
    datasets = every[:_LINK_DATASETS]
    # a column stored as a float cannot be a key (the file's types are in the schema)
    usable = {
        d.id: {clean_text(n).lower(): n for n, kind in d.schema if kind not in _FLOAT_TYPES}
        for d in datasets
    }
    wanted: dict[int, set[str]] = {d.id: set() for d in datasets}
    id_like = {
        d.id: [n for n in usable[d.id].values() if link_names.is_id_like(n)] for d in datasets
    }
    # a whole-number column is a key by its values only when its name says id (on both sides);
    # a small integer such as a count or a rank overlaps with any other
    key_columns = {
        d.id: {
            n
            for n, kind in d.schema
            if kind not in _FLOAT_TYPES
            and (link_names.is_id_like(n) or not kind.startswith(("int", "uint")))
        }
        for d in datasets
    }
    pairs = []  # (dataset, dataset, column, column, basis): pairs whose names say they may match
    for i, a in enumerate(datasets):
        for b in datasets[i + 1 :]:
            matched = [
                (usable[a.id][k], usable[b.id][k])
                for k in usable[a.id].keys() & usable[b.id].keys()
            ]
            matched += [
                (x, y) for x in id_like[a.id] for y in id_like[b.id] if x.lower() != y.lower()
            ]
            for column_a, column_b in matched:
                basis = link_names.related(a.name, column_a, b.name, column_b)
                if basis is not None:
                    pairs.append((a, b, column_a, column_b, basis))
                    wanted[a.id].add(column_a)
                    wanted[b.id].add(column_b)
    for d in datasets:
        wanted[d.id].update(_value_columns(d, usable[d.id]))
    keys: dict[tuple[int, str], tuple[set[str], bool] | None] = {}
    sampled = cut = False
    started = time.monotonic()
    for d in datasets:
        if not wanted[d.id]:
            continue
        if time.monotonic() - started > _LINK_SECS:
            cut = True
            break
        frame, was_sample = _read_keys(ctx, d, sorted(wanted[d.id]))
        sampled = sampled or was_sample
        for column in wanted[d.id]:
            keys[d.id, column] = _key_set(frame, column)
        del frame
    links = []
    examined = set()  # the pairs the names said to compare: the values judged them already
    for a, b, column_a, column_b, basis in pairs:
        found = keys.get((a.id, column_a)), keys.get((b.id, column_b))
        if None in found:
            continue
        examined.add((a.id, column_a, b.id, column_b))
        link = _link(a, b, column_a, column_b, basis, found)
        if link is not None:
            links.append((len(found[0][0] | found[1][0]), link))
    for i, a in enumerate(datasets):
        for b in datasets[i + 1 :]:
            for column_a in _value_columns(a, usable[a.id]):
                for column_b in _value_columns(b, usable[b.id]):
                    found = keys.get((a.id, column_a)), keys.get((b.id, column_b))
                    if None in found or (a.id, column_a, b.id, column_b) in examined:
                        continue
                    key_ok = (column_a in key_columns[a.id], column_b in key_columns[b.id])
                    link = _link(a, b, column_a, column_b, link_names.VALUES, found, key_ok)
                    if link is not None:
                        links.append((len(found[0][0] | found[1][0]), link))
    links.sort(
        key=lambda item: (
            item[1]["relation"] == "many_to_many",
            -item[0] if item[1]["relation"] == "many_to_many" else 0,
            _BASIS_RANK[item[1].get("basis", link_names.SAME_NAME)],
            -item[1]["shared"],
        )
    )
    links = [link for _, link in links]
    repeating = 0
    shown = []
    for link in links:
        repeating += link["relation"] == "many_to_many"
        if repeating <= _MAX_REPEATING_LINKS:
            shown.append(link)
    return shown[:_MAX_LINKS], datasets, every, sampled, cut


def _find_table_links(ctx: ToolContext, args: dict) -> dict:
    project_id = args["project_id"]
    _authorize(ctx, project_id)
    shown, datasets, every, sampled, cut = _project_links(ctx, project_id)
    result = {
        "links": shown,
        "sampled": sampled,
        "next_step": (_NEXT_TO_JOIN if shown else "") + _NEXT_TO_TRAIN,
    }
    if len(every) > len(datasets):
        result["n_datasets_not_examined"] = len(every) - len(datasets)
    if cut:
        result["truncated"] = True  # the time ran out before every dataset was read
    # the column names go first when the result is too large: the links name datasets by id
    listed = _LINK_COLUMNS
    while True:
        full = {"datasets": [_linked_dataset(d, listed) for d in datasets], **result}
        if listed == 0 or fits(full, ctx.max_result_bytes):
            return full
        listed //= 2


# --- propose_join ---------------------------------------------------------


def _join_columns_added(
    dataset: Dataset, keys: list[str], chosen: list[str], summarize: bool
) -> int:
    """How many columns Join adds: the chosen ones (all but the key if none are chosen), or with
    ``summarize`` a count, and four for each number or one for any other column."""
    kinds = {name: kind for name, kind in dataset.schema if name not in keys}
    if chosen:
        kinds = {name: kinds[name] for name in chosen if name in kinds}
    if not summarize:
        return len(kinds)
    numbers = sum(k.startswith(("int", "uint")) or k in _FLOAT_TYPES for k in kinds.values())
    return 1 + 4 * numbers + len(kinds) - numbers


def _key_args(names: list[str], args: dict, name: str, where: str) -> list[str]:
    """The key columns named by ``args[name]``: one column, or several (comma-separated) that
    identify a row together, as the schema's names."""
    text = args.get(name) or ""
    if text in names:  # one column, whose name may have a comma
        given = [text]
    else:
        given = [c.strip() for c in text.split(",") if c.strip()]
    resolved = [_resolve_column(names, g, where) for g in given]
    if len(set(resolved)) != len(resolved):
        raise ToolError(f"{name} names a column twice")
    return resolved


def _propose_join(ctx: ToolContext, args: dict) -> dict:
    base = _dataset(ctx, args["dataset_id"])
    other = _dataset(ctx, args["other_dataset_id"])
    if base.project_id != other.project_id:
        raise ToolError("the two datasets are in different projects")
    if base.id == other.id:
        raise ToolError("a dataset cannot be joined to itself")
    base_names = [name for name, _ in base.schema]
    other_names = [name for name, _ in other.schema]
    keys = _key_args(base_names, args, "key", "base dataset")
    if not keys:
        raise ToolError("name the key column (key)")
    other_keys = _key_args(other_names, args, "other_key", "other dataset") or [
        _resolve_column(other_names, k, "other dataset") for k in keys
    ]
    if len(keys) != len(other_keys):
        raise ToolError("the key and the other key must name the same number of columns")
    given = args.get("columns", "")
    names = [given] if given in other_names else [c.strip() for c in given.split(",") if c.strip()]
    chosen = [_resolve_column(other_names, c, "other dataset") for c in names]
    chosen = [c for c in dict.fromkeys(chosen) if c not in other_keys]
    if not all(_is_plain(name) for name in (*keys, *other_keys, *chosen)):
        raise ToolError("a column name is not plain text and cannot be proposed")
    summarize = bool(args.get("summarize", False))
    shown = ", ".join(f"'{clean_text(k)}'" for k in other_keys)

    warnings: list[dict] = []
    try:
        base_frame, base_sampled = _read_keys(ctx, base, keys)
        other_frame, other_sampled = _read_keys(ctx, other, other_keys)
        if len(keys) == 1:
            base_set = _key_set(base_frame, keys[0])
            other_set = _key_set(other_frame, other_keys[0])
        else:
            base_set = _key_tuples(base_frame, keys)
            other_set = _key_tuples(other_frame, other_keys)
    except (KeyError, ValueError):  # a column the file cannot give: the checks are skipped
        base_set = other_set = None
        base_sampled = other_sampled = False
    if other_set is not None and not other_set[1] and not summarize:
        warnings.append(
            _warning(
                "join_key_repeats",
                f"the values of {shown} repeat in the other dataset, so the "
                "join is refused unless summarize is on",
                column=", ".join(clean_text(k) for k in other_keys),
            )
        )
    # the share of matching keys is judged on whole columns only: two samples of a large pair
    # of datasets share far fewer keys than the datasets do
    if base_set is not None and other_set is not None and not (base_sampled or other_sampled):
        matched = len(base_set[0] & other_set[0]) / len(base_set[0])
        if matched < _MIN_SHARED:
            warnings.append(
                _warning(
                    "join_few_matches",
                    f"only {matched:.0%} of the key values of the base dataset are in the "
                    "other dataset, so most rows would get empty values",
                    share=f"{matched * 100:.0f}",
                )
            )
    cells = base.n_rows * (
        len(base_names) + _join_columns_added(other, other_keys, chosen, summarize)
    )
    if cells > MAX_OUTPUT_CELLS:
        warnings.append(
            _warning(
                "join_too_large",
                f"the result would have about {cells // 10**6} million cells, over the limit of "
                f"{MAX_OUTPUT_CELLS // 10**6} million; name fewer columns",
                cells=str(cells // 10**6),
                limit=str(MAX_OUTPUT_CELLS // 10**6),
            )
        )
    if len(keys) == 1:
        key_config = {"key": keys[0], "other_key": "" if other_keys == keys else other_keys[0]}
    else:  # several columns identify a row together
        key_config = {
            "key": "",
            "keys": keys,
            "other_key": "",
            "other_keys": [] if other_keys == keys else other_keys,
        }
    config = {
        "other_dataset_id": other.id,
        **key_config,
        "summarize": summarize,
        "columns": chosen,
    }
    notes = args.get("notes")
    return {
        "proposal": True,
        "kind": "join",
        "config": config,
        "warnings": warnings,
        "rationale": None if notes is None else clean_text(notes, _RATIONALE_CHARS),
    }


# --- propose_first_join -----------------------------------------------------


def _sides(link: dict) -> tuple[int, int]:
    """The dataset with one row per key (the first dataset of a one-to-one link), then the other."""
    a, b = link["datasets"]
    return (b, a) if link["one_row_per_key"] == b else (a, b)


def _first_join(links: list[dict], holders: set[int]) -> tuple[dict, int] | None:
    """The best link of a dataset in ``holders`` (those with the column to predict) that a join
    can follow, and the base: the dataset of ``holders`` it links. A link where both sides
    repeat is left out, since one side would have to be summarized first."""
    for link in links:
        base = next((d for d in link["datasets"] if d in holders), None)
        if base is not None and link["relation"] != "many_to_many":
            return link, base
    return None


def _propose_first_join(ctx: ToolContext, args: dict) -> dict:
    project_id = args["project_id"]
    _authorize(ctx, project_id)
    links, datasets, *_ = _project_links(ctx, project_id)
    if not args.get("target"):
        raise ToolError(
            "the first join depends on the column to predict: ask the user which column it is, "
            "then call again with target"
        )
    wanted = args["target"].lower()
    holders = {d.id for d in datasets if any(n.lower() == wanted for n, _ in d.schema)}
    if not holders:
        raise ToolError(f"no dataset of the project has a column named {args['target']!r}")
    chosen = _first_join(links, holders)
    if chosen is None:
        raise ToolError(
            "no dataset with that column has a link that a join can follow; call "
            "find_table_links to see how the datasets relate"
        )
    link, base = chosen
    other = next(d for d in link["datasets"] if d != base)
    column_base, column_other = link.get("columns") or [link["column"]] * 2
    if base != link["datasets"][0]:
        column_base, column_other = column_other, column_base
    join = {
        "dataset_id": base,
        "other_dataset_id": other,
        "key": column_base,
        "other_key": column_other,
        # the other dataset has several rows per key: a row of the base gets their summary
        "summarize": link["one_row_per_key"] == base and link["relation"] == "one_to_many",
    }
    return {**_propose_join(ctx, join), "dataset_id": base}


# --- listings -------------------------------------------------------------


def _listing(key: str, items: list, limit: int) -> dict:
    """``{key: items}`` cut to ``limit``, saying so when it was."""
    result = {key: items[:limit]}
    if len(items) > limit:
        result["truncated"] = True
        result["truncated_lists"] = [key]
        result[f"n_more_{key}"] = len(items) - limit
    return result


def _access_label(ctx: ToolContext, project_id: str) -> str:
    """What the user may do in the project, as the rest of Fione decides it: only an admin
    reaches a project without owning or being a member of it, and a global viewer is held to
    ``viewer`` whatever the membership. A label only; no decision rests on it."""
    access = project_access(ctx.conn, ctx.user, project_id)
    if access is None:
        return Role.ADMIN.value
    return ProjectAccess.VIEWER.value if ctx.user.role == Role.VIEWER else access.value


def _list_projects(ctx: ToolContext, args: dict) -> dict:
    readable = [
        p
        for p in projects.list_projects(ctx.conn, ctx.user)
        if ctx.project_id is None or p.id == ctx.project_id
    ]
    result = _listing("projects", readable, _MAX_PROJECTS)
    result["projects"] = [
        {
            "id": p.id,
            "name": clean_text(p.name),
            "access": _access_label(ctx, p.id),
            "n_datasets": projects.count_datasets(ctx.conn, p.id),
            "n_models": projects.count_models(ctx.conn, p.id),
        }
        for p in result["projects"]
    ]
    return result


def _list_datasets(ctx: ToolContext, args: dict) -> dict:
    _authorize(ctx, args["project_id"])
    datasets = projects.list_datasets(ctx.conn, args["project_id"])
    result = _listing("datasets", datasets, _MAX_DATASETS)
    result["datasets"] = [_dataset_block(d) for d in result["datasets"]]
    return result


def _list_models(ctx: ToolContext, args: dict) -> dict:
    _authorize(ctx, args["project_id"])
    records = models.list_models_brief(ctx.conn, args["project_id"])
    result = _listing("models", records, _MAX_MODELS)
    result["models"] = [
        {
            "id": m.id,
            "name": clean_text(m.name),
            "task": m.task,
            "target": clean_text(m.target),
            "dataset_id": m.dataset_id,
            "best_model": clean_text(m.best_model),
        }
        for m in result["models"]
    ]
    return result


# --- registration -----------------------------------------------------------

_ID = {"type": "integer", "minimum": 1, "maximum": 2**63 - 1}  # SQLite integers
_COLUMN = {"type": "string", "maxLength": 500}
_PROJECT = {"type": "string", "maxLength": 64}


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
        "proposal for the user to confirm; nothing is started. Set the optional max_runtime_secs, "
        "decision ('balanced': a rare class and a score such as balanced accuracy) and "
        "target_transform ('log1p': a skewed target and a score such as RMSLE) only when the "
        "user's goal calls for it. group_column: a repeating id (a customer) whose rows stay "
        "together in validation.",
        _schema(
            {
                "dataset_id": _ID,
                "target": _COLUMN,
                "notes": {"type": "string", "maxLength": 2000},
                "max_runtime_secs": {"type": "integer", "minimum": 1},
                "decision": {"type": "string", "enum": ["argmax", "balanced"]},
                "target_transform": {"type": "string", "enum": ["none", "log1p"]},
                "group_column": _COLUMN,
            },
            ["dataset_id", "target"],
        ),
        True,
        _propose_training_config,
    ),
    Tool(
        "find_table_links",
        "Find datasets of a project that can be joined: columns with related names and mostly "
        "the same values; 'one_row_per_key' names a dataset with one row per value (none: both "
        "repeat, so one must be summarized first). Large datasets are sampled; nothing is "
        "joined.",
        _schema({"project_id": _PROJECT}, ["project_id"]),
        True,
        _find_table_links,
    ),
    Tool(
        "propose_first_join",
        "Call this when the user asks how to combine or join the datasets: Fione picks the first "
        "join of the dataset with the column to predict, and the user confirms its card. To join "
        "two datasets the user named, call propose_join.",
        _schema({"project_id": _PROJECT, "target": _COLUMN}, ["project_id"]),
        True,
        _propose_first_join,
    ),
    Tool(
        "propose_join",
        "Call this whenever the user asks to join datasets, instead of describing it: it "
        "makes the card the user confirms. It proposes the Join of another dataset onto a base "
        "dataset by key columns (comma-separated); "
        "nothing is started. The result is a new dataset. Use "
        "summarize when the other dataset has several rows per key. Name columns to add only "
        "those, leaving out ids and anything not known when the model predicts.",
        _schema(
            {
                "dataset_id": _ID,
                "other_dataset_id": _ID,
                "key": _COLUMN,
                "other_key": {
                    **_COLUMN,
                    "description": "if named differently in the other dataset",
                },
                "summarize": {"type": "boolean"},
                "columns": {
                    "type": "string",
                    "maxLength": 4000,
                    "description": "names, comma-separated",
                },
                "notes": {"type": "string", "maxLength": 2000},
            },
            ["dataset_id", "other_dataset_id"],
        ),
        True,
        _propose_join,
    ),
    Tool(
        "list_projects",
        "The projects the user can read, with the number of datasets and models in each.",
        _schema({}, []),
        True,
        _list_projects,
    ),
    Tool(
        "list_datasets",
        "The datasets of a project: id, name, type and size.",
        _schema({"project_id": _PROJECT}, ["project_id"]),
        True,
        _list_datasets,
    ),
    Tool(
        "list_models",
        "The trained models of a project, newest first: id, name, task, target, the dataset "
        "they were trained on and the best model.",
        _schema({"project_id": _PROJECT}, ["project_id"]),
        True,
        _list_models,
    ),
):
    register(_tool)
