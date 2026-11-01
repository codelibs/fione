"""Per-row contributions of the input columns to a trained model's output.

Each family's contributions come natively: TreeSHAP in margin space for the boosters (LightGBM
``pred_contrib``, XGBoost ``pred_contribs``, CatBoost ``ShapValues``), Saabas path
contributions in probability or target units for the forests (RandomForest, ExtraTrees), and
margin contributions against the training mean for the linear-view families: exact for Linear,
integrated gradients for DeepLearning. Like the predictions, they are
combined in the ensemble's output space: each fold model's values are converted to
probabilities first, then averaged over the member's models and weight-summed over the
members. Binary margins are rescaled exactly; multiclass margins are integrated along the
softmax path, with the integration error folded back in. So the contributions plus the bias
always add up to the model's output, but they are exact Shapley values only per booster in
margin space. Expanded features (datetime parts) count for their source column.

Global importance is the rows' mean absolute contribution. Partial dependence and ICE curves
vary one input column over a small grid on a sample of background rows.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
import xgboost as xgb
from catboost import Pool
from scipy import sparse
from scipy.special import expit, softmax
from sklearn.base import is_classifier

from fione.engine.families import (
    CatBoost,
    DeepLearning,
    FamilySpec,
    Forest,
    LightGBM,
    Linear,
    XGBoost,
    n_threads,
    owners,
)
from fione.engine.model import TrainedModel
from fione.engine.prep import _EPOCH, _as_str, _datetimes

FLAT_MARGIN = 1e-9  # a binary margin this close to the bias is rescaled by the sigmoid's slope
PATH_ERROR_FACTOR = 10.0  # multiclass path points: see softmax_to_probability
MAX_PATH_STEPS = 256
PD_GRID = 20  # most points of a partial dependence grid
PD_ROWS = 300  # most background rows it averages over
ICE_ROWS = 50  # most single-row (ICE) curves it keeps
THREADS = n_threads(PD_ROWS * PD_GRID)  # explanations make small predictions
CELLS = 10_000_000  # rows x outputs x features of one explanation: 80 MB per float64 array


def explained_outputs(model: TrainedModel) -> list:
    """What the explanations explain: ``[classes_[1]]`` for binary, every class for
    multiclass, ``[target]`` for regression."""
    if model.task == "regression":
        return [model.target]
    return [model.classes_[1]] if len(model.classes_) == 2 else list(model.classes_)


def contribution_rows(model: TrainedModel, limit: int) -> int:
    """How many of ``limit`` rows one ``contributions`` call may take, so that rows x
    classes x features stays within ``CELLS``; 0 for a model too wide for a single row."""
    classes = len(model.classes_) if model.task == "classification" else 1
    return max(0, min(limit, CELLS // (classes * max(1, len(model.prep.sources)))))


def pd_rows(model: TrainedModel, rows: int, grid_size: int) -> int:
    """``rows``, lowered so that the rows x ``grid_size`` copies of the model's columns that
    ``partial_dependence`` predicts on stay within ``CELLS`` (at least 1)."""
    return max(1, min(rows, CELLS // (grid_size * max(1, len(model.columns)))))


def cap_threads(model: TrainedModel, threads: int = THREADS) -> TrainedModel:
    """``model`` with its fold models predicting on at most ``threads`` threads.

    Every family predicts with the threads it was trained with, all cores on large data: the
    fold models' ``n_jobs``, or for CatBoost (which takes a count per call) the spec's. Fewer
    stay as they are (a forest artifact predicts on one, so that its sums are
    reproducible), and an unset or negative count counts as all cores.
    """
    for member in model.members:
        if isinstance(member.spec, CatBoost):
            if _lowered(member.spec.n_jobs, threads):
                member.spec.n_jobs = threads
            continue
        for one in member.models:
            if "n_jobs" in one.get_params() and _lowered(one.get_params()["n_jobs"], threads):
                one.set_params(n_jobs=threads)  # not Ridge and the network, which have none
    return model


def _lowered(current: int | None, threads: int) -> bool:
    return current is None or current <= 0 or current > threads


@dataclass(frozen=True)
class Contributions:
    """``values[row, output, column]`` plus ``bias[row, output]`` equals ``prediction``.

    The outputs are ``[classes_[1]]`` for binary (the negative class is its mirror image),
    every class for multiclass, and ``[target]`` for regression.
    """

    columns: list[str]
    outputs: list
    values: np.ndarray
    bias: np.ndarray
    prediction: np.ndarray

    def slots(self, class_index: int | None = None) -> np.ndarray:
        """The output explained per row: ``class_index``, else the predicted one (multiclass)."""
        if class_index is None:
            return self.prediction.argmax(axis=1)
        _check_int("class_index", class_index, 0, len(self.outputs) - 1)
        return np.full(len(self.prediction), class_index)


def _check_int(name: str, value, low: int, high: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | np.integer)
        or value not in range(low, high + 1)
    ):
        raise ValueError(f"{name} must be an integer in {low}..{high}")


def binary_to_probability(phi: np.ndarray, bias: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Margin contributions (n, f) and bias (n,) as positive-class probability ones.

    Each is scaled by (p(margin) − p(bias)) / (margin − bias): exact, and keeps the signs.
    """
    margin = bias + phi.sum(axis=1)
    step = margin - bias
    flat = np.abs(step) < FLAT_MARGIN
    p, p0 = expit(margin), expit(bias)
    scale = np.where(flat, p0 * (1 - p0), (p - p0) / np.where(flat, 1.0, step))
    return phi * scale[:, None], p0


def softmax_to_probability(
    phi: np.ndarray, bias: np.ndarray, steps: int = 16
) -> tuple[np.ndarray, np.ndarray]:
    """Margin contributions (n, k, f) and bias (n, k) as class probability ones.

    The softmax gradient is integrated along the straight path from the bias to the margin
    with the midpoint rule. A row gets ``steps`` points, doubled (up to ``MAX_PATH_STEPS``)
    while they are fewer than sqrt(``PATH_ERROR_FACTOR`` · max|phi| · spread), where spread
    is the row's largest change of one class's margin against another's: the rule's error
    grows with both. That keeps the error per contribution below about 1e-3 (measured up to a
    spread of 280), and a row's result does not depend on the other rows.

    The integration error is then shared out within each class in proportion to the
    contributions' sizes (evenly when all are 0), so the sums are exact. The sharing keeps
    every sign while the error is below the class's total size. It breaks the exact zero sum
    of each feature's contributions over the classes, by up to about 5e-4.
    """
    total = phi.sum(axis=-1)
    spread = total.max(axis=1) - total.min(axis=1)
    needed = np.sqrt(PATH_ERROR_FACTOR * np.abs(phi).max(axis=(1, 2)) * spread)
    doublings = np.ceil(np.log2(np.maximum(needed / steps, 1.0)))
    counts = np.minimum(steps * 2**doublings, max(steps, MAX_PATH_STEPS)).astype(int)
    phi_p = np.zeros_like(phi)
    for count in np.unique(counts):
        rows = counts == count
        phi_r, bias_r, total_r = phi[rows], bias[rows], total[rows]
        integral = np.zeros_like(phi_r)
        for s in range(count):
            p = softmax(bias_r + (s + 0.5) / count * total_r, axis=1)[:, :, None]
            integral += p * (phi_r - (p * phi_r).sum(axis=1, keepdims=True))
        phi_p[rows] = integral / count
    bias_p = softmax(bias, axis=1)
    residual = softmax(bias + total, axis=1) - bias_p - phi_p.sum(axis=-1)
    size = np.abs(phi_p)
    sizes = size.sum(axis=-1, keepdims=True)
    share = np.where(sizes > 0, size / np.where(sizes > 0, sizes, 1.0), 1.0 / phi.shape[-1])
    return phi_p + residual[:, :, None] * share, bias_p


def saabas(estimator, X: np.ndarray, n_outputs: int) -> tuple[np.ndarray, np.ndarray]:
    """Path contributions (n, k, f) and bias (n, k) of one sklearn tree.

    Each split credits its feature with the change in the node value (class fractions, or the
    regression value) from the parent to the child the row goes to.
    """
    tree = estimator.tree_
    if is_classifier(estimator):
        value = tree.value[:, 0, :]
        value = value / value.sum(axis=1, keepdims=True)
    else:
        value = tree.value[:, 0, :1]
    parent = np.zeros(tree.node_count, dtype=np.intp)
    for children in (tree.children_left, tree.children_right):
        split = np.flatnonzero(children >= 0)
        parent[children[split]] = split
    nodes = np.arange(1, tree.node_count)  # node 0 is the root, without a parent
    delta = value[nodes] - value[parent[nodes]]
    offsets = tree.feature[parent[nodes]][:, None] * n_outputs + np.arange(n_outputs)
    n_features = X.shape[1]
    credit = sparse.csr_matrix(
        (delta.ravel(), (np.repeat(nodes, n_outputs), offsets.ravel())),
        shape=(tree.node_count, n_features * n_outputs),
    )
    phi = (estimator.decision_path(X) @ credit).toarray()
    phi = phi.reshape(len(X), n_features, n_outputs).transpose(0, 2, 1)
    return phi, np.tile(value[0], (len(X), 1))


IG_STEPS = 16  # points of the path integral for DeepLearning


def _fold_in(phi: np.ndarray, residual: np.ndarray) -> np.ndarray:
    """``phi`` (n, k, f) with ``residual`` (n, k) shared out in proportion to the contributions'
    sizes (evenly when all are 0), so that each row's contributions add up to it more."""
    size = np.abs(phi)
    sizes = size.sum(axis=-1, keepdims=True)
    share = np.where(sizes > 0, size / np.where(sizes > 0, sizes, 1.0), 1.0 / phi.shape[-1])
    return phi + residual[:, :, None] * share


def _network(model, X: np.ndarray):
    """Output of the network (n, k) and its gradient with respect to the input (n, k, f)."""
    masks, a = [], X
    for weights, bias in zip(model.coefs_[:-1], model.intercepts_[:-1], strict=True):
        z = a @ weights + bias
        masks.append(z > 0)
        a = np.maximum(z, 0.0)
    out = a @ model.coefs_[-1] + model.intercepts_[-1]
    grad = np.broadcast_to(model.coefs_[-1].T, (len(X), *model.coefs_[-1].T.shape))
    for weights, mask in zip(model.coefs_[-2::-1], masks[::-1], strict=True):
        grad = (grad * mask[:, None, :]) @ weights.T
    return out, grad


def _linear_view_contributions(spec, model, view: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Contributions of the linear view's columns, summed onto the features they derive from.

    The reference point is the training mean of each column (``baseline_``). Linear models are
    exact in margin space (``coef * (x - baseline)``). A network gets the integrated gradients
    along the straight path from the baseline to the row (ReLU: the midpoint rule), with the
    path's integration error shared out so that the sums are exact. Both are margins, like the
    boosters': logits, or the value for regression.
    """
    X, baseline = view.to_numpy(np.float64), model.baseline_
    if isinstance(spec, Linear):
        coef = np.atleast_2d(model.coef_)  # (k, columns)
        phi = (X - baseline)[:, None, :] * coef[None]
        bias = np.tile(np.atleast_1d(model.intercept_) + coef @ baseline, (len(X), 1))
    else:
        delta = X - baseline
        gradient = 0.0
        for s in range(IG_STEPS):
            gradient = gradient + _network(model, baseline + (s + 0.5) / IG_STEPS * delta)[1]
        phi = delta[:, None, :] * gradient / IG_STEPS
        out, _ = _network(model, X)
        base_out = _network(model, baseline[None])[0]
        phi = _fold_in(phi, out - base_out - phi.sum(axis=-1))
        bias = np.tile(base_out, (len(X), 1))
    owner = owners(view.columns)
    by_feature = np.zeros((*phi.shape[:2], owner.max() + 1))
    np.add.at(by_feature, (slice(None), slice(None), owner), phi)
    return by_feature, bias


def native_contributions(
    spec: FamilySpec, model, view: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """Contributions (n, k_m, f) and bias (n, k_m) in the family's own space and class set.

    Boosters and the linear-view families give margins, forests probabilities, regression
    values. k_m is 1 for binary (the model's second class) and regression, else the model's
    number of classes.
    """
    if isinstance(spec, Forest):
        X = view.to_numpy(np.float32)
        k = len(model.classes_) if spec.classification else 1
        phi, bias = np.zeros((len(X), k, X.shape[1])), np.zeros((len(X), k))
        for estimator in model.estimators_:
            tree_phi, tree_bias = saabas(estimator, X, k)
            phi += tree_phi
            bias += tree_bias
        phi, bias = phi / len(model.estimators_), bias / len(model.estimators_)
        return (phi[:, 1:], bias[:, 1:]) if k == 2 else (phi, bias)
    if isinstance(spec, LightGBM):
        raw = model.predict(view, pred_contrib=True, num_iteration=spec.rounds(model))
    elif isinstance(spec, XGBoost):
        matrix = xgb.DMatrix(view, enable_categorical=True, nthread=n_threads(len(view)))
        raw = model.get_booster().predict(
            matrix, pred_contribs=True, iteration_range=(0, spec.rounds(model))
        )
    elif isinstance(spec, Linear | DeepLearning):
        return _linear_view_contributions(spec, model, view)
    elif isinstance(spec, CatBoost):
        categorical = [i for i, dtype in enumerate(view.dtypes) if dtype is np.dtype(object)]
        raw = model.get_feature_importance(
            Pool(view, cat_features=categorical),
            type="ShapValues",
            thread_count=n_threads(len(view)),
        )
    else:
        raise TypeError(f"no contributions for {spec.name}")
    # (n, f+1) for binary and regression; multiclass is (n, k, f+1), or (n, k·(f+1)) class by
    # class for LightGBM. The bias is the last entry.
    n_features = view.shape[1]
    raw = np.asarray(raw, dtype=float).reshape(len(view), -1, n_features + 1)
    return raw[:, :, :n_features], raw[:, :, n_features]


def _probability(spec: FamilySpec, model, view: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """One model's contributions in the ensemble's space: (n, k, f) and (n, k), with k the
    task's class count (a class the model never saw gets 0) or 1 for regression."""
    phi, bias = native_contributions(spec, model, view)
    if not spec.classification:
        return phi, bias
    if not isinstance(spec, Forest):  # margins
        if phi.shape[1] == 1:
            phi, bias = binary_to_probability(phi[:, 0], bias[:, 0])
            phi, bias = phi[:, None], bias[:, None]
        else:
            phi, bias = softmax_to_probability(phi, bias)
    if phi.shape[1] == 1:  # the second class; the first is its mirror image
        phi, bias = np.concatenate([-phi, phi], axis=1), np.concatenate([1 - bias, bias], axis=1)
    if phi.shape[1] == spec.n_classes:
        return phi, bias
    slots = np.asarray(model.classes_, dtype=int)
    full_phi = np.zeros((len(view), spec.n_classes, phi.shape[2]))
    full_bias = np.zeros((len(view), spec.n_classes))
    full_phi[:, slots], full_bias[:, slots] = phi, bias
    return full_phi, full_bias


def contributions(model: TrainedModel, df: pd.DataFrame) -> Contributions:
    """The contributions of ``model.columns`` to ``model``'s output on each row of ``df``."""
    # The views come first, so that missing columns raise even for an empty frame.
    names = dict.fromkeys(member.spec.view for member in model.members)
    views = {name: getattr(model.prep, name)(df) for name in names}
    outputs = explained_outputs(model)
    k = 1 if model.task == "regression" else len(model.classes_)
    phi = np.zeros((len(df), k, len(model.prep.sources)))
    bias = np.zeros((len(df), k))
    if len(df):  # some libraries reject empty input or print about it
        for member in model.members:
            spec = member.spec
            for one in member.models:
                one_phi, one_bias = _probability(spec, one, views[spec.view])
                phi += member.weight / len(member.models) * one_phi
                bias += member.weight / len(member.models) * one_bias
    if len(outputs) < k:  # binary: the positive class
        phi, bias = phi[:, 1:], bias[:, 1:]
    position = {column: i for i, column in enumerate(model.columns)}
    values = np.zeros((len(df), len(outputs), len(model.columns)))
    sources = [position[source] for source in model.prep.sources]
    np.add.at(values, (slice(None), slice(None), sources), phi)
    return Contributions(list(model.columns), outputs, values, bias, values.sum(-1) + bias)


def global_importance(c: Contributions) -> pd.Series:
    """Per column, the mean over the rows of its absolute contributions summed over the
    outputs; largest first. All 0 for no rows."""
    size = np.abs(c.values).sum(axis=1)
    mean = size.mean(axis=0) if len(size) else np.zeros(len(c.columns))
    return pd.Series(mean, index=c.columns).sort_values(ascending=False, kind="stable")


@dataclass(frozen=True)
class PartialDependence:
    """The model's outputs with ``column`` set to each ``grid`` value, over ``n_rows`` rows.

    ``average[point, output]`` is their mean over the rows; ``ice[row, point]`` holds single
    rows' curves for ``outputs[ice_output]``. ``None`` in the grid means missing; datetimes
    are ISO strings, in UTC without a zone marker when the column was tz-aware. ``grid`` has
    a single point when a numeric or datetime column holds a single value in the background.
    """

    column: str
    kind: Literal["numeric", "datetime", "category"]
    grid: list
    outputs: list
    average: np.ndarray
    ice: np.ndarray
    ice_output: int
    n_rows: int


def _spread(values: np.ndarray, size: int, integral: bool) -> np.ndarray:
    """At most ``size`` sorted points from the 2nd to the 98th percentile of ``values``.

    These are the quantiles; where they coincide (a sparse column), evenly spaced points
    between both ends fill up, and ``size`` of the sorted union are kept, evenly by position.
    When both percentiles are one value (a rare indicator), the ends are the minimum and the
    maximum instead, so only a single-valued column gets a single point.
    """
    points = np.unique(np.quantile(values, np.linspace(0.02, 0.98, size)))
    if len(points) < size:
        low, high = (points[0], points[-1]) if len(points) > 1 else (values.min(), values.max())
        union = np.union1d(points, np.linspace(low, high, size))
        points = np.unique(union[np.round(np.linspace(0, len(union) - 1, size)).astype(int)])
    return np.unique(np.round(points)) if integral else points


def _grid(s: pd.Series, kind: str, size: int) -> tuple[list, np.ndarray]:
    """The grid as JSON values, and as the values set into the column; empty when ``s`` has
    no values the model can read."""
    if kind == "numeric":
        values = pd.to_numeric(s, errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan)
        values = values.dropna().to_numpy()
        if not len(values):
            return [], values
        integral = bool((values % 1 == 0).all())
        points = _spread(values, size, integral)
        grid = [int(p) for p in points] if integral else [float(p) for p in points]
        return grid, np.asarray(grid)
    if kind == "datetime":
        seconds = (_datetimes(s) - _EPOCH).dt.total_seconds().dropna().to_numpy()
        if not len(seconds):
            return [], seconds
        stamps = pd.to_datetime(_spread(seconds, size, integral=True), unit="s")
        return [stamp.isoformat() for stamp in stamps], stamps.to_numpy()
    counts = _as_str(s).value_counts()  # how the model reads categories
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[: size - 1]
    levels = [label for label, _ in top]
    if pd.api.types.infer_dtype(s, skipna=True) == "boolean":
        levels = sorted(label == "True" for label in levels)
    if not levels:
        return [], np.array([], dtype=object)
    grid = [*levels, None]
    return grid, np.array(grid, dtype=object)


def partial_dependence(
    model: TrainedModel,
    background: pd.DataFrame,
    column: str,
    *,
    grid_size: int = PD_GRID,
    max_rows: int = PD_ROWS,
    ice_rows: int = ICE_ROWS,
    class_index: int | None = None,
    seed: int = 0,
) -> PartialDependence:
    """Partial dependence and ICE curves of ``model`` on ``column``, varied over a grid.

    The grid comes from all of ``background``: numeric and datetime columns get up to
    ``grid_size`` points between the 2nd and 98th percentiles (whole numbers for integral
    columns, whole seconds for datetimes); categorical ones their ``grid_size − 1`` most
    frequent levels (ties by label; bool in False, True order), then missing. The curves use
    at most ``max_rows`` rows drawn with ``seed`` in random order, of which the first
    ``ice_rows`` give the ICE curves, and one prediction over all their grid copies. ICE shows
    ``class_index``, else the output whose average varies most.
    """
    _check_int("grid_size", grid_size, 2, PD_GRID)
    _check_int("max_rows", max_rows, 1, PD_ROWS)
    _check_int("ice_rows", ice_rows, 0, ICE_ROWS)
    try:
        kind = model.prep.kind_of(column)
    except KeyError:
        raise ValueError(f"the model does not use the column {column!r}") from None
    outputs = explained_outputs(model)
    if class_index is not None:
        _check_int("class_index", class_index, 0, len(outputs) - 1)
    grid, values = [], None
    if column in background.columns:
        grid, values = _grid(background[column], kind, grid_size)
    if not grid:
        raise ValueError(f"the column {column!r} has no values in the background")
    rows = np.random.default_rng(seed).permutation(len(background))[:max_rows]
    needed = set(model.columns)
    used = [c for c in background.columns if c in needed]
    frame = background[used].iloc[np.repeat(rows, len(grid))].reset_index(drop=True)
    frame[column] = np.tile(values, len(rows))
    if model.task == "regression":
        predicted = model.predict(frame).to_numpy()[:, None]
    else:
        predicted = model.predict_proba(frame).to_numpy()  # by position: labels may be bool
        predicted = predicted[:, 1:] if len(outputs) < predicted.shape[1] else predicted
    curves = predicted.reshape(len(rows), len(grid), len(outputs))
    average = curves.mean(axis=0)
    if class_index is None:
        class_index = int(np.argmax(average.max(axis=0) - average.min(axis=0)))
    return PartialDependence(
        column,
        "category" if kind == "frequency" else kind,
        grid,
        outputs,
        average,
        curves[:ice_rows, :, class_index],
        int(class_index),
        len(rows),
    )
