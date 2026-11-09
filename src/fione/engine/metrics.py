"""Metrics for sorting the leaderboard, stopping a search early and reporting (spec 5.4).

Classification predictions are class probabilities of shape (n, k) for labels 0..k-1;
regression predictions are values of shape (n,). Every metric is one entry of ``REGISTRY``.
A metric that counts right answers (accuracy, F1, kappa, ...) uses the class ``choose`` picks.
The models are trained on log loss or squared error whatever the metric: the metric ranks the
models, stops the search and is reported.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.special import xlogy
from scipy.stats import rankdata
from sklearn.metrics import average_precision_score, matthews_corrcoef, roc_auc_score

from fione.engine.config import ConfigError
from fione.engine.prep import Task
from fione.engine.search import Folds, score

TOP_K = 3  # the k of top3_accuracy and map3
TOP_SHARE = 0.10  # the share of rows lift_top_group looks at
MAX_RATING_RANGE = 1000  # rounded_qwk needs a confusion matrix of range x range


@dataclass(frozen=True)
class Metric:
    name: str
    task: Task
    higher_is_better: bool
    compute: Callable[[np.ndarray, np.ndarray, np.ndarray | None], float]
    # whether the metric is defined for the target ``y`` (class codes or values) of ``classes``
    # classes (0 for regression)
    applies: Callable[[np.ndarray, int], bool] = lambda y, classes: True
    # reported only for two classes (ranking measures; they are still allowed to sort by)
    binary_summary: bool = False
    why: str = ""  # said when ``applies`` is false


def choose(pred: np.ndarray, prior: np.ndarray | None = None) -> np.ndarray:
    """The class index per row: the largest probability, or with ``prior`` (the classes'
    shares of the training data) the largest probability relative to its class's share."""
    return (pred if prior is None else pred / prior).argmax(axis=1)


# --- classification ------------------------------------------------------------------------


def _auc(y, pred, prior):
    if pred.shape[1] == 2:
        return float(roc_auc_score(y, pred[:, 1]))
    labels = np.arange(pred.shape[1])
    return float(roc_auc_score(y, pred, multi_class="ovr", average="macro", labels=labels))


def _one_vs_rest(y, pred, measure) -> float:
    """``measure(is_class, score)`` for the second class of two, or its mean over the classes
    that occur in ``y`` (the others have no positive row)."""
    if pred.shape[1] == 2:
        return float(measure(y == 1, pred[:, 1]))
    present = [c for c in range(pred.shape[1]) if (y == c).any()]
    return float(np.mean([measure(y == c, pred[:, c]) for c in present]))


def _average_precision(y, pred, prior):
    return _one_vs_rest(y, pred, average_precision_score)


def _gini(y, pred, prior):
    return 2.0 * _auc(y, pred, prior) - 1.0


def _lift(is_class: np.ndarray, scores: np.ndarray) -> float:
    base = float(np.mean(is_class))
    if base == 0.0:
        return float("nan")
    cut = max(1, int(np.ceil(TOP_SHARE * len(scores))))
    edge = np.sort(scores)[::-1][cut - 1]
    above, tied = scores > edge, scores == edge
    # The rows tied at the edge share the places left, so the row order does not matter.
    found = float(is_class[above].sum()) + float(is_class[tied].mean()) * (cut - above.sum())
    return found / cut / base


def _lift_top_group(y, pred, prior):
    return _one_vs_rest(y, pred, _lift)


def _accuracy(y, pred, prior):
    return float(np.mean(choose(pred, prior) == y))


def _confusion(y: np.ndarray, picked: np.ndarray, k: int) -> np.ndarray:
    """Counts with the true class in the rows and the picked class in the columns."""
    return np.bincount(y * k + picked, minlength=k * k).reshape(k, k)


def _recalls(table: np.ndarray) -> np.ndarray:
    return np.diag(table) / np.maximum(table.sum(axis=1), 1)


def _balanced_accuracy(y, pred, prior):
    table = _confusion(y, choose(pred, prior), pred.shape[1])
    return float(np.mean(_recalls(table)[table.sum(axis=1) > 0]))


def _misclassification(y, pred, prior):
    return 1.0 - _accuracy(y, pred, prior)


def _mean_per_class_error(y, pred, prior):
    return 1.0 - _balanced_accuracy(y, pred, prior)


def _precision_recall_f1(y, pred, prior) -> tuple[float, float, float]:
    """Of the second class for two classes, else the mean over the classes that occur in the
    answers or the predictions (a class neither has is left out; a zero count gives 0)."""
    k = pred.shape[1]
    table = _confusion(y, choose(pred, prior), k)
    hit, said, truth = np.diag(table), table.sum(axis=0), table.sum(axis=1)
    precision = hit / np.maximum(said, 1)
    recall = hit / np.maximum(truth, 1)
    f1 = 2 * hit / np.maximum(said + truth, 1)
    if k == 2:
        return float(precision[1]), float(recall[1]), float(f1[1])
    seen = (said + truth) > 0
    return float(precision[seen].mean()), float(recall[seen].mean()), float(f1[seen].mean())


def _precision(y, pred, prior):
    return _precision_recall_f1(y, pred, prior)[0]


def _recall(y, pred, prior):
    return _precision_recall_f1(y, pred, prior)[1]


def _f1(y, pred, prior):
    return _precision_recall_f1(y, pred, prior)[2]


def _mcc(y, pred, prior):
    return float(matthews_corrcoef(y, choose(pred, prior)))


def _kappa_of(table: np.ndarray, quadratic: bool) -> float:
    """Cohen's kappa of a confusion matrix, with the squared distance of the classes as the
    weight when ``quadratic`` (the classes are in their order)."""
    k = len(table)
    seen = table / table.sum()
    expected = np.outer(seen.sum(axis=1), seen.sum(axis=0))
    if quadratic:
        steps = np.arange(k)
        weight = (steps[:, None] - steps[None, :]) ** 2
    else:
        weight = 1.0 - np.eye(k)
    worst = float(np.sum(weight * expected))
    return 1.0 - float(np.sum(weight * seen)) / worst if worst > 0 else float("nan")


def _kappa(y, pred, prior):
    return _kappa_of(_confusion(y, choose(pred, prior), pred.shape[1]), quadratic=False)


def _qwk(y, pred, prior):
    return _kappa_of(_confusion(y, choose(pred, prior), pred.shape[1]), quadratic=True)


def _brier(y, pred, prior):
    """The mean squared distance of the probabilities from the answer: for two classes the
    usual squared error of the second class's probability, for more the sum over the classes."""
    if pred.shape[1] == 2:
        return float(np.mean((pred[:, 1] - y) ** 2))
    own = pred[np.arange(len(y)), y]
    return float(np.mean(np.sum(pred**2, axis=1) - 2 * own + 1))


def _rank_of_answer(y, pred) -> np.ndarray:
    """How many classes the model thinks at least as likely as the true one (a tie counts
    against the model, so a model that cannot tell the classes apart gets no credit)."""
    return np.sum(pred >= pred[np.arange(len(y)), y][:, None], axis=1) - 1


def _top_k_accuracy(y, pred, prior):
    return float(np.mean(_rank_of_answer(y, pred) < TOP_K))


def _map_at_k(y, pred, prior):
    rank = _rank_of_answer(y, pred)
    return float(np.mean(np.where(rank < TOP_K, 1.0 / (rank + 1), 0.0)))


# --- regression ----------------------------------------------------------------------------


def _non_negative(y, classes) -> bool:
    return bool((y >= 0).all())


def _rmse(y, pred, prior):
    return score("regression", y, pred)


def _mse(y, pred, prior):
    return float(np.mean((y - pred) ** 2))


def _mae(y, pred, prior):
    return float(np.mean(np.abs(y - pred)))


def _medae(y, pred, prior):
    return float(np.median(np.abs(y - pred)))


def _r2(y, pred, prior):
    total = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - float(np.sum((y - pred) ** 2)) / total if total > 0 else 0.0


def _explained_variance(y, pred, prior):
    total = float(np.var(y))
    return 1.0 - float(np.var(y - pred)) / total if total > 0 else 0.0


def _rmsle(y, pred, prior):
    return float(np.sqrt(np.mean((np.log1p(y) - np.log1p(np.maximum(pred, 0.0))) ** 2)))


def _mape(y, pred, prior):
    return float(np.mean(np.abs(y - pred) / np.abs(y)))


def _smape(y, pred, prior):
    size = np.abs(y) + np.abs(pred)
    return float(
        np.mean(np.divide(2 * np.abs(y - pred), size, out=np.zeros_like(size), where=size > 0))
    )


def _correlation(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a - a.mean(), b - b.mean()
    norm = float(np.sqrt(np.sum(a * a) * np.sum(b * b)))
    return float(np.sum(a * b)) / norm if norm > 0 else float("nan")


def _pearson(y, pred, prior):
    return _correlation(y, pred)


def _spearman(y, pred, prior):
    return _correlation(rankdata(y), rankdata(pred))


def _gini_of(answer: np.ndarray, pred: np.ndarray) -> float:
    """Rows with the same prediction share their answers' mean, so their order does not
    matter."""
    _, group = np.unique(-pred, return_inverse=True)
    mean = np.bincount(group, weights=answer) / np.bincount(group)
    ordered = mean[group][np.argsort(group, kind="stable")]
    n = len(ordered)
    return float(np.cumsum(ordered).sum() / ordered.sum() - (n + 1) / 2) / n


def _normalized_gini(y, pred, prior):
    return _gini_of(y, pred) / _gini_of(y, y)


def _gini_applies(y, classes) -> bool:
    return bool((y >= 0).all()) and float(y.sum()) > 0 and _gini_of(y, y) > 0


def _poisson(y, pred, prior):
    pred = np.maximum(pred, 1e-9)
    return float(2.0 * np.mean(xlogy(y, y / pred) - (y - pred)))


def _whole_ratings(y, classes) -> bool:
    return bool(np.all(y == np.round(y))) and 1 <= y.max() - y.min() < MAX_RATING_RANGE


def _rounded_qwk(y, pred, prior):
    low, high = int(y.min()), int(y.max())
    picked = np.clip(np.round(pred), low, high).astype(int) - low
    return _kappa_of(_confusion(y.astype(int) - low, picked, high - low + 1), quadratic=True)


def _metrics() -> dict[str, Metric]:
    """The default metric of a task comes first: ``auto`` means it."""
    c, r = "classification", "regression"
    over = lambda y, classes: classes > TOP_K  # noqa: E731
    from_k = lambda y, classes: classes >= TOP_K  # noqa: E731
    found = [
        Metric("logloss", c, False, lambda y, p, _: score(c, y, p)),
        Metric("auc", c, True, _auc, binary_summary=True),
        Metric("accuracy", c, True, _accuracy),
        Metric("aucpr", c, True, _average_precision, binary_summary=True),
        Metric("gini", c, True, _gini, binary_summary=True),
        Metric("lift_top_group", c, True, _lift_top_group, binary_summary=True),
        Metric("balanced_accuracy", c, True, _balanced_accuracy),
        Metric("misclassification", c, False, _misclassification),
        Metric("mean_per_class_error", c, False, _mean_per_class_error),
        Metric("f1", c, True, _f1),
        Metric("precision", c, True, _precision),
        Metric("recall", c, True, _recall),
        Metric("mcc", c, True, _mcc),
        Metric("kappa", c, True, _kappa),
        Metric("qwk", c, True, _qwk),
        Metric("brier", c, False, _brier),
        Metric("top3_accuracy", c, True, _top_k_accuracy, over, why=f"needs over {TOP_K} classes"),
        Metric("map3", c, True, _map_at_k, from_k, why=f"needs {TOP_K} classes or more"),
        Metric("rmse", r, False, _rmse),
        Metric("mae", r, False, _mae),
        Metric("r2", r, True, _r2),
        Metric("mse", r, False, _mse),
        Metric("rmsle", r, False, _rmsle, _non_negative, why="needs target values of 0 or more"),
        Metric(
            "mape",
            r,
            False,
            _mape,
            lambda y, k: bool((y != 0).all()),
            why="needs target values other than 0",
        ),
        Metric("smape", r, False, _smape),
        Metric("medae", r, False, _medae),
        Metric("explained_variance", r, True, _explained_variance),
        Metric("pearson", r, True, _pearson),
        Metric("spearman", r, True, _spearman),
        Metric(
            "normalized_gini",
            r,
            True,
            _normalized_gini,
            _gini_applies,
            why="needs target values of 0 or more",
        ),
        Metric(
            "poisson", r, False, _poisson, _non_negative, why="needs target values of 0 or more"
        ),
        Metric(
            "rounded_qwk",
            r,
            True,
            _rounded_qwk,
            _whole_ratings,
            why="needs whole-number target values",
        ),
    ]
    return {m.name: m for m in found}


REGISTRY = _metrics()
ALLOWED: dict[str, tuple[str, ...]] = {
    task: tuple(m.name for m in REGISTRY.values() if m.task == task)
    for task in ("classification", "regression")
}
HIGHER_IS_BETTER = frozenset(m.name for m in REGISTRY.values() if m.higher_is_better)
# What the rating and the model page read; they are always reported.
CORE = frozenset({"logloss", "auc", "accuracy", "rmse", "mae", "r2"})


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


def check(name: str, y: np.ndarray, classes: int, field: str) -> None:
    """ConfigError if the metric is not defined for this target (``y``: class codes, or the
    values in the target's own units; ``classes``: 0 for regression)."""
    metric = REGISTRY[name]
    if not metric.applies(y, classes):
        raise ConfigError(f"{field} {name!r} {metric.why}")


def value(name: str, y: np.ndarray, pred: np.ndarray, prior: np.ndarray | None = None) -> float:
    if name not in REGISTRY:
        raise ValueError(f"unknown metric {name!r}")
    with np.errstate(all="ignore"):
        return REGISTRY[name].compute(y, pred, prior)


def loss(name: str, y: np.ndarray, pred: np.ndarray, prior: np.ndarray | None = None) -> float:
    """``value`` oriented so that lower is better; an undefined value is the worst."""
    v = value(name, y, pred, prior)
    if not np.isfinite(v):
        return float("inf")
    return -v if name in HIGHER_IS_BETTER else v


def fold_std(
    name: str, y: np.ndarray, pred: np.ndarray, folds: Folds, prior: np.ndarray | None = None
) -> float:
    """Standard deviation of the metric over the validation folds, leaving out the folds where
    it is undefined (an AUC of a part with one class); NaN if there is none."""
    values = np.array([value(name, y[valid], pred[valid], prior) for _, valid in folds])
    values = values[np.isfinite(values)]
    return float(np.std(values)) if len(values) else float("nan")


def summary(
    task: Task, y: np.ndarray, pred: np.ndarray, prior: np.ndarray | None = None
) -> dict[str, float]:
    """Every metric of the task that is defined for the data, in the target's own units.
    The ranking measures (AUC, ...) only for two classes. Besides the core metrics, a value
    that is not a number is left out."""
    classes = pred.shape[1] if task == "classification" else 0
    out = {}
    for name in ALLOWED[task]:
        metric = REGISTRY[name]
        if not metric.applies(y, classes) or metric.binary_summary and classes != 2:
            continue
        try:
            v = value(name, y, pred, prior)
        except MemoryError:  # a table over many classes: report what fits
            if name in CORE:
                raise
            continue
        if name in CORE or np.isfinite(v):
            out[name] = v
    return out
