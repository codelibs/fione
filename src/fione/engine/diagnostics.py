"""Training-time diagnostics from the ensemble's out-of-fold (OOF) predictions.

``diagnostics`` returns a small dict that is strict JSON: builtins only, floats rounded to 6
significant digits (regression values: 6 significant digits of their spread, when that is
finer), and ``None`` where a value is undefined (never NaN or infinity). Every
result has ``version`` (1), ``task``, ``n_rows`` (the rows used) and ``sampled``: more than
``max_rows`` rows are first sampled without replacement, seeded, so the cost stays bounded.

Classification (``y`` holds class codes 0..k-1 of ``labels``, ``pred`` the (n, k) probabilities):

- ``labels``: ``jsonable(labels)``, with any label JSON lacks (a ``Timestamp``, ``Decimal``, ...)
  as ``str(label)``, as in the artifact manifest; everything else refers to a class by its
  index.
- ``confusion``: ``classes`` (indices, ``-1`` = "other") and ``matrix`` (rows actual, columns the
  argmax). Above ``MAX_CONFUSION`` classes it keeps the largest by support (ties: lower index
  first), in index order, and counts the rest as "other".
- ``per_class``: precision, recall, f1 (as sklearn's with ``zero_division=nan``, so ``None`` when
  undefined) and support, in index order; above ``MAX_PER_CLASS`` classes only the largest by
  support (ties as above), with ``per_class_truncated``.
- Binary only, for the positive class ``labels[1]``: ``auc``; the ``roc`` (fpr, tpr, threshold)
  and ``pr`` (precision, recall, threshold) curves, thinned to ``MAX_CURVE_POINTS`` with both
  ends kept, with the infinite threshold (and PR's last point, which has none) as 1.0; and
  ``calibration``: 10 equal-width bins of p(positive), left-closed ([0, 0.1), ...; sklearn's
  ``calibration_curve`` uses right-closed ones) with p = 1 in the last, empty bins omitted.

Regression (``pred`` of shape (n,)), with residual = actual - predicted:

- ``residuals``: a 30-bin histogram (``edges``, ``counts``);
- ``by_decile``: the rows split into 10 near-equal groups by prediction (empty ones omitted);
- ``points``: at most ``MAX_POINTS`` (actual, predicted) pairs, in a seeded random order (never
  the row order, which would tie each value to its training row).
"""

import math

import numpy as np
from sklearn.metrics import precision_recall_curve, roc_auc_score, roc_curve

from fione.engine.events import jsonable
from fione.engine.prep import Task

VERSION = 1
MAX_CONFUSION = 30
MAX_PER_CLASS = 200
MAX_CURVE_POINTS = 200
CALIBRATION_BINS = 10
RESIDUAL_BINS = 30
DECILES = 10
MAX_POINTS = 2_000


def _num(value) -> float | None:
    value = float(value)
    return float(f"{value:.6g}") if np.isfinite(value) else None


def _nums(values: np.ndarray) -> list:
    return [_num(v) for v in values]


def _fine(values: np.ndarray) -> list:
    """``_nums``, but with 6 significant digits of the values' spread where that is finer, so
    that values large against their spread (1e6 + [0, 1e-3]) stay distinct."""
    finite = values[np.isfinite(values)]
    spread = float(np.ptp(finite)) if len(finite) else 0.0
    if spread <= 0:
        return _nums(values)
    scale = math.floor(math.log10(spread))
    out = []
    for value in values.tolist():
        if not math.isfinite(value) or value == 0:
            out.append(_num(value))
            continue
        digits = min(17, 6 + max(0, math.floor(math.log10(abs(value))) - scale))
        out.append(float(f"{value:.{digits}g}"))
    return out


def _label(value):
    value = jsonable(value)
    return value if value is None or type(value) in (str, int, float, bool) else str(value)


def _largest(support: np.ndarray, count: int) -> np.ndarray:
    """Indices of the ``count`` largest supports (ties: lower index first), in index order."""
    return np.sort(np.argsort(-support, kind="stable")[:count])


def _thin(n: int) -> np.ndarray:
    return np.unique(np.linspace(0, n - 1, min(n, MAX_CURVE_POINTS)).round().astype(np.int64))


def _ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    safe = np.where(denominator > 0, denominator, 1)
    return np.where(denominator > 0, numerator / safe, np.nan)


def diagnostics(
    task: Task,
    y: np.ndarray,
    pred: np.ndarray,
    labels: list | None,
    *,
    max_rows: int = 200_000,
    seed: int = 0,
) -> dict:
    """The diagnostics of ``pred`` against ``y`` (see the module docstring)."""
    y, pred = np.asarray(y), np.asarray(pred, dtype=float)
    rng = np.random.default_rng(seed)
    sampled = len(y) > max_rows
    if sampled:
        rows = np.sort(rng.choice(len(y), max_rows, replace=False))
        y, pred = y[rows], pred[rows]
    out = {"version": VERSION, "task": task, "n_rows": len(y), "sampled": sampled}
    if task == "classification":
        out.update(_classification(y.astype(np.int64), pred, labels))
    else:
        out.update(_regression(y.astype(float), pred, rng))
    return out


def _classification(y: np.ndarray, pred: np.ndarray, labels: list) -> dict:
    k = pred.shape[1]
    predicted = pred.argmax(axis=1)
    support = np.bincount(y, minlength=k)
    n_predicted = np.bincount(predicted, minlength=k)
    tp = np.bincount(y[y == predicted], minlength=k)

    kept = np.arange(k) if k <= MAX_CONFUSION else _largest(support, MAX_CONFUSION)
    size = len(kept) + (k > MAX_CONFUSION)
    slot = np.full(k, len(kept))  # "other"
    slot[kept] = np.arange(len(kept))
    matrix = np.bincount(slot[y] * size + slot[predicted], minlength=size * size)
    classes = [int(c) for c in kept] + ([-1] if k > MAX_CONFUSION else [])

    precision, recall = _ratio(tp, n_predicted), _ratio(tp, support)
    f1 = _ratio(2 * tp, n_predicted + support)
    listed = np.arange(k) if k <= MAX_PER_CLASS else _largest(support, MAX_PER_CLASS)
    out = {
        "labels": [_label(label) for label in labels],
        "confusion": {"classes": classes, "matrix": matrix.reshape(size, size).tolist()},
        "per_class": [
            {
                "class": int(c),
                "precision": _num(precision[c]),
                "recall": _num(recall[c]),
                "f1": _num(f1[c]),
                "support": int(support[c]),
            }
            for c in listed
        ],
        "per_class_truncated": bool(k > MAX_PER_CLASS),
    }
    if k == 2 and support.all():
        out.update(_binary(y, pred[:, 1]))
    return out


def _binary(y: np.ndarray, positive: np.ndarray) -> dict:
    fpr, tpr, roc_threshold = roc_curve(y, positive, drop_intermediate=True)
    precision, recall, pr_threshold = precision_recall_curve(y, positive)
    pr_threshold = np.append(pr_threshold, np.inf)  # the (recall 0, precision 1) end has none
    roc, pr = _thin(len(fpr)), _thin(len(precision))

    bins = np.clip((positive * CALIBRATION_BINS).astype(np.int64), 0, CALIBRATION_BINS - 1)
    count = np.bincount(bins, minlength=CALIBRATION_BINS)
    total = np.bincount(bins, weights=positive, minlength=CALIBRATION_BINS)
    hits = np.bincount(bins, weights=(y == 1).astype(float), minlength=CALIBRATION_BINS)
    return {
        "auc": _num(roc_auc_score(y, positive)),
        "roc": {
            "fpr": _nums(fpr[roc]),
            "tpr": _nums(tpr[roc]),
            "threshold": _nums(np.where(np.isinf(roc_threshold), 1.0, roc_threshold)[roc]),
        },
        "pr": {
            "precision": _nums(precision[pr]),
            "recall": _nums(recall[pr]),
            "threshold": _nums(np.where(np.isinf(pr_threshold), 1.0, pr_threshold)[pr]),
        },
        "calibration": [
            {
                "predicted": _num(total[b] / count[b]),
                "observed": _num(hits[b] / count[b]),
                "count": int(count[b]),
            }
            for b in np.flatnonzero(count)
        ],
    }


def _regression(y: np.ndarray, pred: np.ndarray, rng: np.random.Generator) -> dict:
    residual = y - pred
    counts, edges = np.histogram(residual, bins=RESIDUAL_BINS)
    groups = [g for g in np.array_split(np.argsort(pred, kind="stable"), DECILES) if len(g)]
    means = _fine(np.array([pred[group].mean() for group in groups]))
    by_decile = [
        {
            "predicted_mean": mean,
            "residual_mean": _num(residual[group].mean()),
            "residual_std": _num(residual[group].std()),  # ddof 0
            "count": len(group),
        }
        for group, mean in zip(groups, means, strict=True)
    ]
    points = rng.permutation(len(y))[:MAX_POINTS]
    return {
        "residuals": {"edges": _fine(edges), "counts": counts.tolist()},
        "by_decile": by_decile,
        "points": {"actual": _fine(y[points]), "predicted": _fine(pred[points])},
    }
