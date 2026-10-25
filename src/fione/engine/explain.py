"""Per-row contributions of the input columns to a trained model's output.

Each family's contributions come natively: TreeSHAP in margin space for the boosters (LightGBM
``pred_contrib``, XGBoost ``pred_contribs``, CatBoost ``ShapValues``) and Saabas path
contributions in probability or target units for ExtraTrees. Like the predictions, they are
combined in the ensemble's output space: each fold model's values are converted to
probabilities first, then averaged over the member's models and weight-summed over the
members. Binary margins are rescaled exactly; multiclass margins are integrated along the
softmax path, with the integration error folded back in. So the contributions plus the bias
always add up to the model's output, but they are exact Shapley values only per booster in
margin space. Expanded features (datetime parts) count for their source column.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import xgboost as xgb
from catboost import Pool
from scipy import sparse
from scipy.special import expit, softmax
from sklearn.base import is_classifier

from fione.engine.families import CatBoost, ExtraTrees, FamilySpec, LightGBM, XGBoost, n_threads
from fione.engine.model import TrainedModel

FLAT_MARGIN = 1e-9  # a binary margin this close to the bias is rescaled by the sigmoid's slope


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
        if class_index not in range(len(self.outputs)):
            raise ValueError(f"class_index must be in 0..{len(self.outputs) - 1}")
        return np.full(len(self.prediction), class_index)


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
    (midpoint rule, ``steps`` points); the integration error is then shared out in proportion
    to the contributions' sizes (evenly when all are 0), so the sums are exact.
    """
    total = phi.sum(axis=-1)
    phi_p = np.zeros_like(phi)
    for s in range(steps):
        p = softmax(bias + (s + 0.5) / steps * total, axis=1)[:, :, None]
        phi_p += p * (phi - (p * phi).sum(axis=1, keepdims=True))
    phi_p /= steps
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


def native_contributions(
    spec: FamilySpec, model, view: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """Contributions (n, k_m, f) and bias (n, k_m) in the family's own space and class set.

    Boosters give margins, ExtraTrees probabilities, regression values. k_m is 1 for binary
    (the model's second class) and regression, else the model's number of classes.
    """
    if isinstance(spec, ExtraTrees):
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
    if not isinstance(spec, ExtraTrees):  # margins
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
    if model.task == "regression":
        outputs, k = [model.target], 1
    else:
        k = len(model.classes_)
        outputs = [model.classes_[1]] if k == 2 else list(model.classes_)
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
