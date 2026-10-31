"""Metrics for sorting the leaderboard, stopping a search early and reporting (spec 5.4).

Classification predictions are class probabilities of shape (n, k) for labels 0..k-1;
regression predictions are values of shape (n,). AUC is one-vs-rest macro for multiclass.
"""

import numpy as np
from sklearn.metrics import roc_auc_score

from fione.engine.config import ConfigError
from fione.engine.prep import Task
from fione.engine.search import Folds, score

ALLOWED: dict[str, tuple[str, ...]] = {
    "classification": ("logloss", "auc", "accuracy"),
    "regression": ("rmse", "mae", "r2"),
}
HIGHER_IS_BETTER = frozenset({"auc", "accuracy", "r2"})


def resolve(name: str, task: Task, field: str) -> str:
    """The metric ``name`` means (``auto``: logloss or rmse); ConfigError if it does not apply."""
    name = name.lower()
    if name == "auto":
        return ALLOWED[task][0]
    if name not in ALLOWED[task]:
        raise ConfigError(
            f"{field} {name!r} does not apply to {task}; use auto or one of {list(ALLOWED[task])}"
        )
    return name


def value(name: str, y: np.ndarray, pred: np.ndarray) -> float:
    if name == "logloss":
        return score("classification", y, pred)
    if name == "accuracy":
        return float(np.mean(pred.argmax(axis=1) == y))
    if name == "auc":
        if pred.shape[1] == 2:
            return float(roc_auc_score(y, pred[:, 1]))
        labels = np.arange(pred.shape[1])
        return float(roc_auc_score(y, pred, multi_class="ovr", average="macro", labels=labels))
    if name == "rmse":
        return score("regression", y, pred)
    if name == "mae":
        return float(np.mean(np.abs(y - pred)))
    if name == "r2":
        total = float(np.sum((y - np.mean(y)) ** 2))
        return 1.0 - float(np.sum((y - pred) ** 2)) / total if total > 0 else 0.0
    raise ValueError(f"unknown metric {name!r}")


def loss(name: str, y: np.ndarray, pred: np.ndarray) -> float:
    """``value`` oriented so that lower is better."""
    v = value(name, y, pred)
    return -v if name in HIGHER_IS_BETTER else v


def fold_std(name: str, y: np.ndarray, pred: np.ndarray, folds: Folds) -> float:
    """Standard deviation of the metric over the validation folds."""
    return float(np.std([value(name, y[valid], pred[valid]) for _, valid in folds]))


def summary(task: Task, y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    """logloss, accuracy and (binary only) auc; or rmse, mae and r2."""
    names = list(ALLOWED[task])
    if task == "classification" and pred.shape[1] != 2:
        names.remove("auc")
    return {name: value(name, y, pred) for name in names}
