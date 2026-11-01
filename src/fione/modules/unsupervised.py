"""K-means and low-rank projection.

Missing values are not modelled: a gap is filled with the column mean found in training (the
mean is part of the state). Only integer and float columns are used; name the ones to use in
``columns``. The state is plain JSON and ``*_predict`` applies it with numpy alone, through the
same function the train module uses for its own output, so both give identical results.
"""

import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import NMF, TruncatedSVD
from sklearn.exceptions import ConvergenceWarning

from fione.modules.registry import (
    Module,
    ModuleError,
    ModuleOutput,
    numeric_matrix,
    pick_columns,
    register,
)

_NAMES = {"type": "array", "items": {"type": "string"}, "maxItems": 1000, "default": []}
_SEED = {"type": "integer", "minimum": 0, "maximum": 2**31 - 1, "default": 0}
_MODEL = {"type": "integer", "minimum": 1}
_NMF_SWEEPS = 200
_NMF_TOLERANCE = 1e-10


def _schema(properties: dict, required: tuple[str, ...] = ()) -> dict:
    return {"type": "object", "properties": properties, "required": list(required)}


def _fill_gaps(columns: list[str], matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``(matrix with gaps at the column means, the means)``."""
    gaps = np.isnan(matrix)
    empty = gaps.all(axis=0)
    if empty.any():
        raise ModuleError(f"column '{columns[int(empty.argmax())]}' has no values")
    means = np.nanmean(matrix, axis=0)
    return np.where(gaps, means, matrix), means


def _with_columns(df: pd.DataFrame, result: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    """``result`` followed by the columns of ``df`` named in ``output_columns``."""
    if not names:
        return result
    kept = df[pick_columns(df, names)].reset_index(drop=True)
    return pd.concat([result, kept], axis=1)


def _state_arrays(state: dict | None, kind: str, label: str, *keys: str) -> tuple:
    if not isinstance(state, dict) or state.get("type") != kind:
        raise ModuleError(f"the model is not a {label} model")
    try:
        columns = state["columns"]
        arrays = [np.asarray(state[key], dtype=float) for key in keys]
        if not (
            isinstance(columns, list)
            and all(isinstance(c, str) for c in columns)
            and all(a.shape[-1] == len(columns) for a in arrays)
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ModuleError("the model state is damaged") from None
    return columns, *arrays


def _model_matrix(df: pd.DataFrame, columns: list[str], means: np.ndarray) -> np.ndarray:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ModuleError(f"missing columns: {missing}")
    _, matrix = numeric_matrix(df, columns)
    return np.where(np.isnan(matrix), means, matrix)


# --- k-means ------------------------------------------------------------------------------


def _nearest(scaled: np.ndarray, centers: np.ndarray) -> np.ndarray:
    return np.argmin((centers**2).sum(axis=1) - 2.0 * scaled @ centers.T, axis=1)


def _cluster(df: pd.DataFrame, state: dict, output_columns: list[str]) -> pd.DataFrame:
    columns, means, scales, centers = _state_arrays(
        state, "kmeans", "k-means", "means", "scales", "centers"
    )
    scaled = (_model_matrix(df, columns, means) - means) / scales
    labels = _nearest(scaled, centers)
    return _with_columns(df, pd.DataFrame({"cluster": labels}), output_columns)


def kmeans_train(df, params, ctx):
    columns, matrix = numeric_matrix(df, params["columns"])
    filled, means = _fill_gaps(columns, matrix)
    k = params["k"]
    if k > len(df):
        raise ModuleError(f"k={k} is more than the {len(df)} rows")
    if len(np.unique(filled, axis=0)) < k:
        raise ModuleError(f"there are fewer than k={k} distinct rows")
    spread = filled.std(axis=0) if params["standardize"] else np.ones(len(columns))
    scales = np.where(spread > 0, spread, 1.0)
    scaled = (filled - means) / scales
    fit = KMeans(
        n_clusters=k,
        init=params["init"],
        n_init=10,
        max_iter=params["max_iterations"],
        random_state=params["seed"],
    ).fit(scaled)
    state = {
        "type": "kmeans",
        "columns": columns,
        "means": means.tolist(),
        "scales": scales.tolist(),
        "centers": fit.cluster_centers_.tolist(),
    }
    return ModuleOutput(_cluster(df, state, params["output_columns"]), state)


def kmeans_predict(df, params, ctx):
    return ModuleOutput(_cluster(df, ctx.state, params["output_columns"]))


# --- low-rank projection --------------------------------------------------------------------


def nmf_project(matrix: np.ndarray, parts: np.ndarray) -> np.ndarray:
    """The non-negative weights ``w`` minimising ``|matrix - w @ parts|`` (cyclic coordinate
    descent from a fixed start), so the same rows always give the same weights."""
    gram = parts @ parts.T
    target = matrix @ parts.T
    weights = np.maximum(target @ np.linalg.pinv(gram), 0.0)
    for _ in range(_NMF_SWEEPS):
        change = 0.0
        for j in range(len(parts)):
            if gram[j, j] <= 1e-12:
                weights[:, j] = 0.0
                continue
            step = np.maximum(
                weights[:, j] + (target[:, j] - weights @ gram[:, j]) / gram[j, j], 0.0
            )
            change = max(change, float(np.abs(step - weights[:, j]).max(initial=0.0)))
            weights[:, j] = step
        if change <= _NMF_TOLERANCE:
            break
    return weights


def _project(method: str, matrix: np.ndarray, components: np.ndarray) -> np.ndarray:
    return matrix @ components.T if method == "svd" else nmf_project(matrix, components)


def _projection(df: pd.DataFrame, state: dict, output_columns: list[str]) -> pd.DataFrame:
    columns, means, components = _state_arrays(state, "lowrank", "low-rank", "means", "components")
    if state.get("method") not in ("svd", "nmf") or components.ndim != 2:
        raise ModuleError("the model state is damaged")
    projected = _project(state["method"], _model_matrix(df, columns, means), components)
    names = [f"component_{i + 1}" for i in range(len(components))]
    return _with_columns(df, pd.DataFrame(projected, columns=names), output_columns)


def lowrank_train(df, params, ctx):
    columns, matrix = numeric_matrix(df, params["columns"])
    filled, means = _fill_gaps(columns, matrix)
    n_components, method = params["n_components"], params["method"]
    limit = min(len(df), len(columns))
    if n_components > limit:
        raise ModuleError(
            f"n_components must be at most {limit} (the smaller of the rows and columns)"
        )
    if method == "nmf":
        negative = [c for c, bad in zip(columns, (filled < 0).any(axis=0), strict=True) if bad]
        if negative:
            raise ModuleError(f"nmf needs values of 0 or more; negative values in {negative}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)  # the fit is as good as it gets
            model = NMF(
                n_components=n_components, init="nndsvda", max_iter=500, random_state=params["seed"]
            ).fit(filled)
    else:
        model = TruncatedSVD(n_components=n_components, random_state=params["seed"]).fit(filled)
    state = {
        "type": "lowrank",
        "method": method,
        "columns": columns,
        "means": means.tolist(),
        "components": model.components_.tolist(),
    }
    return ModuleOutput(_projection(df, state, params["output_columns"]), state)


def lowrank_predict(df, params, ctx):
    return ModuleOutput(_projection(df, ctx.state, params["output_columns"]))


def _train_params(**extra) -> dict:
    return {"columns": _NAMES, "output_columns": _NAMES, "seed": _SEED, **extra}


for module in (
    Module(
        "kmeans_train",
        "K-means (train)",
        "train",
        _schema(
            _train_params(
                k={"type": "integer", "minimum": 1, "maximum": 1000, "default": 3},
                init={"type": "string", "enum": ["k-means++", "random"], "default": "k-means++"},
                max_iterations={"type": "integer", "minimum": 1, "maximum": 10000, "default": 300},
                standardize={"type": "boolean", "default": True},
            )
        ),
        kmeans_train,
    ),
    Module(
        "kmeans_predict",
        "K-means (assign clusters)",
        "predict",
        _schema({"module_model_id": _MODEL, "output_columns": _NAMES}, ("module_model_id",)),
        kmeans_predict,
    ),
    Module(
        "lowrank_train",
        "Low-rank projection (train)",
        "train",
        _schema(
            _train_params(
                method={"type": "string", "enum": ["svd", "nmf"], "default": "svd"},
                n_components={"type": "integer", "minimum": 1, "maximum": 1000, "default": 2},
            )
        ),
        lowrank_train,
    ),
    Module(
        "lowrank_predict",
        "Low-rank projection (project)",
        "predict",
        _schema({"module_model_id": _MODEL, "output_columns": _NAMES}, ("module_model_id",)),
        lowrank_predict,
    ),
):
    register(module)
