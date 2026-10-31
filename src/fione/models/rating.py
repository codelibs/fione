"""The star rating of a trained model (1 to 5), shown on the EasyML prediction summary.

The rating says how much better than a trivial guess the model's cross-validated
(out-of-fold) predictions are. Its ``skill`` lies in [0, 1]:

- classification: ``(accuracy - majority_rate) / (1 - majority_rate)``, where ``accuracy``
  is the model's out-of-fold accuracy (``metrics["accuracy"]``) and ``majority_rate`` the
  share of the most common class in the training data (always guessing that class). When
  the training data is gone, binary models fall back to ``2 * (auc - 0.5)``.
- regression: ``1 - rmse / baseline_rmse``, where ``baseline_rmse`` is the standard
  deviation (ddof=0) of the training target, the error of always guessing its mean. When the
  training data is gone it is derived from ``r2``: ``rmse / std = sqrt(1 - r2)`` exactly.

Skill is clamped to [0, 1] and rounded to 9 decimals; stars are 1 + the number of
``THRESHOLDS`` it reaches (so 0.8 and above is 5 stars). A degraded model (training hit an
error) gets at most ``DEGRADED_CAP`` stars. Without a usable metric or baseline (missing or
NaN values, a single class, a constant target) the rating is 1 star with a ``note`` saying why.
"""

import math
from dataclasses import dataclass

import numpy as np

from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.service import DatasetNotFound
from fione.storage import Storage

THRESHOLDS = (0.2, 0.4, 0.6, 0.8)
DEGRADED_CAP = 2
SKILL_DIGITS = 9


@dataclass(frozen=True)
class Rating:
    stars: int  # 1..5
    skill: float | None  # in [0, 1]; None when it could not be computed
    metric: str | None  # what the skill was computed from: accuracy, auc, rmse or r2
    # Why the rating is limited: no_metric, single_class, constant_target or degraded.
    note: str | None = None


def _finite(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) else None


def _skill(task: str, metrics: dict, majority_rate, target_std) -> tuple[float | None, str, str]:
    """``(skill, metric, note)``; skill None when there is nothing to rate on."""
    if task == "classification":
        accuracy, majority = _finite(metrics.get("accuracy")), _finite(majority_rate)
        if accuracy is not None and majority is not None:
            if majority >= 1:
                return None, "accuracy", "single_class"
            return (accuracy - majority) / (1 - majority), "accuracy", None
        auc = _finite(metrics.get("auc"))
        if auc is not None:
            return 2 * (auc - 0.5), "auc", None
        return None, None, "no_metric"
    if task == "regression":
        rmse, std = _finite(metrics.get("rmse")), _finite(target_std)
        if rmse is not None and std is not None:
            if std <= 0:
                return None, "rmse", "constant_target"
            return 1 - rmse / std, "rmse", None
        r2 = _finite(metrics.get("r2"))
        if r2 is not None:
            return 1 - math.sqrt(max(0.0, 1 - r2)), "r2", None
    return None, None, "no_metric"


def star_rating(
    task: str,
    metrics: dict,
    *,
    majority_rate: float | None = None,
    target_std: float | None = None,
    degraded: bool = False,
) -> Rating:
    """The rating of a model from its ``metrics`` and its training target's baseline."""
    skill, metric, note = _skill(task, metrics, majority_rate, target_std)
    if skill is None:
        return Rating(1, None, metric, note)
    # Rounded so that float noise cannot drop a skill of exactly 0.2 (say) a band lower.
    skill = round(min(1.0, max(0.0, skill)), SKILL_DIGITS)
    stars = 1 + sum(skill >= threshold for threshold in THRESHOLDS)
    if degraded and stars > DEGRADED_CAP:
        return Rating(DEGRADED_CAP, skill, metric, "degraded")
    return Rating(stars, skill, metric, "degraded" if degraded else None)


@dataclass(frozen=True)
class Baseline:
    """The trivial guess a model is compared with, from its training target."""

    majority_rate: float | None = None  # classification: share of the most common class
    target_std: float | None = None  # regression: standard deviation (ddof=0)


def target_baseline(storage: Storage, conn, project_id: str, dataset_id, target, task) -> Baseline:
    """The baseline of a training target, read from the whole column (one column of the
    dataset); empty when the dataset or the column is gone."""
    if dataset_id is None:
        return Baseline()
    try:
        dataset = projects.get_dataset(conn, dataset_id)
        if dataset.project_id != project_id or target not in {n for n, _ in dataset.schema}:
            return Baseline()
        y = ingest.read_dataset(storage, dataset, [target])[target].dropna()
    except (DatasetNotFound, KeyError):  # the dataset or its file is gone
        return Baseline()
    if not len(y):
        return Baseline()
    if task == "classification":
        return Baseline(majority_rate=float(y.value_counts().iloc[0]) / len(y))
    try:
        values = y.to_numpy(dtype=float)
    except (TypeError, ValueError):  # not numeric: no regression baseline
        return Baseline()
    return Baseline(target_std=float(np.std(values)) if np.isfinite(values).all() else None)
