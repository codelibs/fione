"""The ``explain`` job: global importance and the top partial dependence curves of a model,
stored in ``model_explanations``.

The job may load any model the install holds, imports not vouched for (``trusted=0``)
included: it runs in a worker process and needs write access, unlike the web process's
explanation requests.
"""

import json
import logging
import sqlite3
import time
from collections.abc import Callable

import numpy as np
import pandas as pd

from fione import db
from fione.config import load_secret
from fione.engine import explain
from fione.engine.artifact import UntrustedArtifactError
from fione.engine.config import ConfigError
from fione.engine.diagnostics import _label, _num
from fione.engine.events import Event
from fione.engine.families import CatBoost, n_threads
from fione.engine.model import TrainedModel
from fione.jobs.handlers import JobContext, JobUserError, register_handler
from fione.models import explanations
from fione.models import service as models_service
from fione.predict.batch import PredictInputError, _check_inputs
from fione.projects import ingest
from fione.projects import service as projects

log = logging.getLogger(__name__)

SAMPLE_ROWS = 10_000  # read from the dataset; the partial dependence grids come from them
IMPORTANCE_ROWS = 1_000
CONTRIBUTION_CELLS = 10_000_000  # rows x outputs x features: 80 MB per float64 array
PD_COLUMNS = 10
IMPORTANCE_FLOOR = 1_000  # columns kept in the importance list before curves are trimmed
MAX_OUTPUTS = 20  # classes kept in a partial dependence curve
THREADS = n_threads(explain.PD_ROWS * explain.PD_GRID)  # these are small predictions

# Raised for what the user can fix; JobAbort and everything else keep their own handling.
USER_ERRORS = (PredictInputError, ConfigError, ingest.IngestError)


class _Cancelled(Exception):
    """Internal: the job was cancelled between two curves."""


def _cap_threads(model: TrainedModel, threads: int) -> TrainedModel:
    """``model`` with its fold models predicting on at most ``threads`` threads.

    Every family predicts with the threads it was trained with, all cores on large data: the
    fold models' ``n_jobs``, or for CatBoost (which takes a count per call) the spec's. Fewer
    stay as they are (an ExtraTrees artifact predicts on one, so that its sums are
    reproducible), and an unset or negative count counts as all cores.
    """
    for member in model.members:
        if isinstance(member.spec, CatBoost):
            if _lowered(member.spec.n_jobs, threads):
                member.spec.n_jobs = threads
            continue
        for one in member.models:
            if _lowered(one.get_params()["n_jobs"], threads):
                one.set_params(n_jobs=threads)
    return model


def _lowered(current: int | None, threads: int) -> bool:
    return current is None or current <= 0 or current > threads


def _importance_rows(frame: pd.DataFrame, target: str, classify: bool, limit: int) -> np.ndarray:
    """At most ``limit`` row positions, in order: evenly spread over the rows, in random
    order or, for a classifier with the target at hand, grouped by class (so each class keeps
    its share, and one with ``len / limit`` rows or more is never left out)."""
    n = len(frame)
    if n <= limit:
        return np.arange(n)
    order = np.random.default_rng(0).permutation(n)
    if classify and target in frame.columns:
        codes, _ = pd.factorize(frame[target].to_numpy()[order])
        order = order[np.argsort(codes, kind="stable")]
    return np.sort(order[np.round(np.linspace(0, n - 1, limit)).astype(int)])


def _kept_outputs(c: explain.Contributions) -> list[int]:
    """The outputs a curve keeps: all, or the ``MAX_OUTPUTS`` with the highest mean predicted
    probability, in class order."""
    k = len(c.outputs)
    if k <= MAX_OUTPUTS:
        return list(range(k))
    mean = c.prediction.mean(axis=0) if len(c.prediction) else np.zeros(k)
    return sorted(np.argsort(-mean, kind="stable")[:MAX_OUTPUTS].tolist())


def _rounded(values: np.ndarray) -> list:
    return [[_num(v) for v in row] for row in values]


def _curve(model: TrainedModel, background: pd.DataFrame, column: str, kept: list[int]) -> dict:
    """The partial dependence of ``column`` as payload JSON, for the ``kept`` outputs; the
    ICE curves show the kept output that varies most when the overall one is not kept."""
    curve = explain.partial_dependence(model, background, column)
    if curve.ice_output not in kept:
        swing = curve.average.max(axis=0) - curve.average.min(axis=0)
        best = kept[int(np.argmax(swing[kept]))]
        curve = explain.partial_dependence(model, background, column, class_index=best)
    return {
        "column": column,
        "kind": curve.kind,
        "grid": [_label(value) for value in curve.grid],
        "outputs": [_label(curve.outputs[i]) for i in kept],
        "average": _rounded(curve.average[:, kept]),
        "ice_output": kept.index(curve.ice_output),
        "ice": _rounded(curve.ice),
        "n_rows": curve.n_rows,
    }


def build_explanation(
    model: TrainedModel,
    frame: pd.DataFrame,
    should_stop: Callable[[], bool],
    *,
    progress: Callable[[int, int], None] | None = None,
) -> dict:
    """The explanation payload of ``model`` on ``frame`` (version 1, strict JSON values).

    Importance comes from the contributions of at most ``IMPORTANCE_ROWS`` rows (fewer when
    rows x classes x features would pass ``CONTRIBUTION_CELLS``), stratified by the target
    when ``frame`` has it and the model classifies. Partial dependence covers
    the ``PD_COLUMNS`` most important columns, on ``frame`` as the background, skipping a
    column without values there; ``should_stop`` is asked before each curve (``_Cancelled``)
    and ``progress(done, total)`` told after each. Floats keep 6 significant digits.
    """
    start = time.monotonic()
    _check_inputs(model, frame)  # PredictInputError for text in a numeric column...
    classify = model.task == "classification"
    cells = (len(model.classes_) if classify else 1) * max(1, len(model.prep.sources))
    limit = max(1, min(IMPORTANCE_ROWS, CONTRIBUTION_CELLS // cells))  # wide multiclass
    rows = _importance_rows(frame, model.target, classify, limit)
    c = explain.contributions(model, frame.iloc[rows])
    importance = explain.global_importance(c)
    total = float(importance.sum())
    kept = _kept_outputs(c)
    top = list(importance.index[:PD_COLUMNS])
    curves = []
    for done, column in enumerate(top, start=1):
        if should_stop():
            raise _Cancelled
        try:
            curves.append(_curve(model, frame, column, kept))
        except ValueError as e:
            if isinstance(e, ConfigError) or "has no values in the background" not in str(e):
                raise
        if progress is not None:
            progress(done, len(top))
    return {
        "version": explanations.VERSION,
        "n_rows": len(rows),
        "outputs": [_label(output) for output in c.outputs],
        "importance": [
            {
                "column": column,
                "mean_abs": _num(value),
                "share": _num(value / total) if total > 0 else 0.0,
            }
            for column, value in importance.items()
        ],
        "partial_dependence": curves,
        "elapsed": round(time.monotonic() - start, 3),
    }


def _fit_to_cap(payload: dict, limit: int) -> dict:
    """``payload`` (unchanged) or a smaller copy of at most ``limit`` bytes of JSON.

    The least important columns go first, halving the list down to ``IMPORTANCE_FLOOR``
    entries; then the ICE curves, last curve first; then the curves, last first; then the
    importance list again, down to one entry. ``ValueError`` if that is not enough.
    """

    def size(value: dict) -> int:
        return len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"))

    out = {**payload, "partial_dependence": [dict(c) for c in payload["partial_dependence"]]}
    while size(out) > limit:
        curves = out["partial_dependence"]
        with_ice = [c for c in curves if c["ice"]]
        n = len(out["importance"])
        if n > IMPORTANCE_FLOOR:
            out["importance"] = out["importance"][: max(IMPORTANCE_FLOOR, n // 2)]
        elif with_ice:
            with_ice[-1]["ice"] = []
        elif curves:
            curves.pop()
        elif n > 1:
            out["importance"] = out["importance"][: n // 2]
        else:
            raise ValueError(f"the explanation is too large to store: {size(out)} bytes")
    return out


@register_handler("explain")
def explain_model(ctx: JobContext) -> None:
    """Explain the model on its dataset and store the result, replacing an earlier one.

    A cancel leaves the earlier explanation as it was: the stop flag is read forced inside
    the transaction that stores the result, so the two cannot interleave with a cancel.
    """
    payload = ctx.job.payload
    project_id = ctx.job.project_id
    try:
        record = models_service.get_model(ctx.conn, payload["model_id"])
        if record.project_id != project_id:
            raise models_service.ModelNotFound(record.id)
    except models_service.ModelNotFound as e:
        raise JobUserError("the model no longer exists") from e
    dataset_id, gone = payload.get("dataset_id"), "the dataset no longer exists"
    if dataset_id is None:  # the training data, which an import has none of
        dataset_id, gone = record.dataset_id, explanations.NO_TRAINING_DATA
    if dataset_id is None:
        raise JobUserError(gone)
    try:
        dataset = projects.get_dataset(ctx.conn, dataset_id)
        if dataset.project_id != project_id:
            raise projects.DatasetNotFound(dataset.id)
    except projects.DatasetNotFound as e:
        raise JobUserError(gone) from e
    start = time.monotonic()
    try:
        model = models_service.load_trained(ctx.storage, record, load_secret(ctx.settings))
    except UntrustedArtifactError as e:
        if isinstance(e.__cause__, KeyError):  # storage: the files are gone (being deleted)
            raise JobUserError("the model no longer exists") from e
        raise JobUserError("the model file failed verification") from e
    _cap_threads(model, THREADS)
    present = {column for column, _ in dataset.schema}
    missing = [column for column in model.columns if column not in present]
    if missing:
        raise JobUserError(f"the dataset lacks the model's columns: {missing}")
    columns = list(model.columns)
    if model.target in present and model.target not in columns:
        columns.append(model.target)
    try:
        frame = ingest.read_dataset_spread(ctx.storage, dataset, SAMPLE_ROWS, columns)
    except KeyError:  # storage: no such object (the message would name the key)
        raise JobUserError(gone) from None
    ctx.emit(
        Event(
            "started", data={"model_id": record.id, "dataset_id": dataset.id, "n_rows": len(frame)}
        )
    )

    def progress(done: int, total: int) -> None:
        message = f"partial dependence: {done} of {total} columns"
        ctx.emit(
            Event("notice", data={"message": message, "columns_done": done, "columns_total": total})
        )

    try:
        result = build_explanation(model, frame, ctx.should_stop, progress=progress)
    except _Cancelled:  # nothing was stored: the worker records the job as CANCELLED
        return
    except USER_ERRORS as e:
        raise JobUserError(str(e)) from e
    try:
        result = _fit_to_cap(result, explanations.MAX_EXPLANATION_BYTES)
    except ValueError as e:  # long category levels in every curve
        raise JobUserError(str(e)) from e
    try:
        # One write transaction: a cancel (a write too) lands before the check, and is seen,
        # or after the commit, in the window the worker's own final check covers.
        with db.immediate(ctx.conn):
            if ctx.should_stop(force=True):
                raise _Cancelled
            explanations.save_explanation(ctx.conn, record.id, ctx.job.id, dataset.id, result)
    except _Cancelled:  # rolled back: the earlier explanation, if any, stays
        return
    except sqlite3.IntegrityError as e:  # a foreign key: deleted while it was explained
        try:
            models_service.get_model(ctx.conn, record.id)
        except models_service.ModelNotFound:
            raise JobUserError("the model no longer exists") from e
        raise JobUserError(gone) from e
    ctx.set_result(
        {
            "model_id": record.id,
            "dataset_id": dataset.id,
            "n_rows": result["n_rows"],
            "elapsed": time.monotonic() - start,
        }
    )
    ctx.emit(Event("finished", data={"model_id": record.id, "dataset_id": dataset.id}))
