import json
from dataclasses import replace
from functools import cache

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose
from predict_models import training_frame
from scipy.special import expit, softmax
from sklearn.tree import ExtraTreeClassifier, ExtraTreeRegressor

from fione.engine import explain
from fione.engine.automl import AutoML
from fione.engine.config import ConfigError, Deadline, TrainConfig
from fione.engine.explain import (
    ICE_ROWS,
    PD_GRID,
    PD_ROWS,
    Contributions,
    binary_to_probability,
    contributions,
    global_importance,
    partial_dependence,
    saabas,
    softmax_to_probability,
)
from fione.engine.families import FAMILIES
from fione.engine.model import Member, TrainedModel
from fione.engine.prep import Prep

TASKS = ("binary", "multiclass", "regression")
TARGETS = {"binary": "good", "multiclass": "判定", "regression": "value"}
HOSTILE = ["<b>x</b>", "幅", "BiasTerm", "contrib_x"]


def _frame(n: int = 300, seed: int = 0) -> pd.DataFrame:
    """``training_frame`` with hostile column names and a datetime column."""
    frame = training_frame(n, seed).rename(columns={"x": "<b>x</b>", "color": "BiasTerm"})
    rng = np.random.default_rng(seed + 100)
    frame["contrib_x"] = rng.normal(size=n)
    days = rng.integers(0, 3 * 365, size=n)
    frame["when"] = pd.Timestamp("2022-01-01") + pd.to_timedelta(days, unit="D")
    frame["good"] = frame["判定"] == "良"
    frame["constant"] = 1  # dropped by the models' prep
    return frame


def _task_frame(task: str, frame: pd.DataFrame) -> pd.DataFrame:
    others = [target for target in TARGETS.values() if target != TARGETS[task]]
    return frame.drop(columns=others)


@cache
def _fit(task: str) -> TrainedModel:
    config = TrainConfig(
        TARGETS[task], max_runtime_secs=15, max_models=4, nfolds=3, keep_cv_models=True
    )
    model = AutoML(config).fit(_task_frame(task, _frame()))
    assert sorted(model.cv_models) == sorted(FAMILIES), f"a family is missing: {model.cv_models}"
    return model


def _spec(model: TrainedModel, name: str, n_classes: int | None = None):
    if n_classes is None:
        n_classes = len(model.classes_) if model.classes_ is not None else 0
    return FAMILIES[name](model.task, n_classes)


def _with_members(model: TrainedModel, members: list[tuple[str, float, list]]) -> TrainedModel:
    return replace(model, members=[Member(_spec(model, n), w, ms) for n, w, ms in members])


def _features(n: int = 40, seed: int = 1) -> pd.DataFrame:
    return _frame(n, seed).drop(columns=list(TARGETS.values()))


def _expected(model: TrainedModel, c, X: pd.DataFrame) -> np.ndarray:
    if model.task == "regression":
        return model.predict(X).to_numpy()[:, None]
    # By position: a bool label like True would select as a mask.
    slots = [model.classes_.index(output) for output in c.outputs]
    return model.predict_proba(X).to_numpy()[:, slots]


def _assert_additive(model: TrainedModel, X: pd.DataFrame):
    c = contributions(model, X)
    assert c.values.shape == (len(X), len(c.outputs), len(model.columns))
    assert c.bias.shape == (len(X), len(c.outputs))
    assert_allclose(c.values.sum(-1) + c.bias, c.prediction, rtol=0, atol=1e-12)
    assert_allclose(c.prediction, _expected(model, c, X), rtol=1e-5, atol=1e-5)
    return c


def _fold_fit(model: TrainedModel, name: str, keep=None, n_classes: int | None = None):
    """One fold model fitted directly on the fixture's training frame (rows ``keep``)."""
    spec = _spec(model, name, n_classes)
    frame = _task_frame(_task_of(model), _frame())
    X = frame.drop(columns=[model.target])
    y = frame[model.target]
    y = pd.Categorical(y, categories=model.classes_).codes if model.classes_ else y.to_numpy()
    keep = np.ones(len(X), bool) if keep is None else keep
    view = getattr(model.prep, spec.view)(X)[keep]
    valid = np.arange(len(view)) % 4 == 0
    fitted = spec.fit(
        spec.defaults, view[~valid], y[keep][~valid], view[valid], y[keep][valid], Deadline(120)
    )
    return spec, fitted


def _task_of(model: TrainedModel) -> str:
    return next(task for task, target in TARGETS.items() if target == model.target)


# --- pure conversions -------------------------------------------------------------------


def test_binary_rescale_is_additive_and_keeps_signs():
    rng = np.random.default_rng(0)
    phi, bias = rng.normal(size=(50, 6)), rng.normal(size=50)
    phi_p, bias_p = binary_to_probability(phi, bias)
    assert_allclose(phi_p.sum(1) + bias_p, expit(bias + phi.sum(1)), rtol=0, atol=1e-12)
    assert_allclose(bias_p, expit(bias), rtol=0, atol=1e-15)
    assert (np.sign(phi_p) == np.sign(phi)).all()


def test_binary_rescale_when_margin_equals_bias():
    phi = np.array([[0.5, -0.5, 0.0], [1.25, -0.75, -0.5]])
    bias = np.array([0.3, -2.0])
    phi_p, bias_p = binary_to_probability(phi, bias)
    assert np.isfinite(phi_p).all()
    slope = expit(bias) * (1 - expit(bias))
    assert_allclose(phi_p, phi * slope[:, None], rtol=1e-12, atol=0)
    assert_allclose(phi_p.sum(1) + bias_p, expit(bias), rtol=0, atol=1e-15)


def test_softmax_path_integral_is_additive():
    rng = np.random.default_rng(1)
    phi, bias = rng.normal(size=(40, 4, 5)), rng.normal(size=(40, 4))
    phi_p, bias_p = softmax_to_probability(phi, bias)
    assert_allclose(phi_p.sum(-1) + bias_p, softmax(bias + phi.sum(-1), axis=1), atol=1e-9)
    assert_allclose(bias_p, softmax(bias, axis=1), rtol=0, atol=1e-15)


@pytest.mark.parametrize(("scale", "atol"), [(1, 5e-4), (5, 1e-3), (20, 1e-3)])
def test_softmax_path_integral_matches_the_two_class_closed_form(scale, atol):
    # With two classes the softmax is the sigmoid of the margin difference, and along a
    # straight path each feature's share of the change is exact: the binary rescale. At
    # scale 1 the default 16 points decide the error (3.6e-4; 7.8e-4 with 1 point).
    rng = np.random.default_rng(5)
    phi, bias = rng.normal(size=(200, 2, 5)) * scale, rng.normal(size=(200, 2))
    phi_p, _ = softmax_to_probability(phi, bias)
    exact, _ = binary_to_probability(phi[:, 1] - phi[:, 0], bias[:, 1] - bias[:, 0])
    assert_allclose(phi_p[:, 1], exact, rtol=0, atol=atol)
    assert_allclose(phi_p[:, 0], -exact, rtol=0, atol=atol)


def test_softmax_path_integral_matches_a_fine_reference():
    rng = np.random.default_rng(6)
    phi, bias = rng.normal(size=(50, 3, 4)) * 5, rng.normal(size=(50, 3))
    total, reference, steps = phi.sum(-1), np.zeros_like(phi), 4096
    for s in range(steps):
        p = softmax(bias + (s + 0.5) / steps * total, axis=1)[:, :, None]
        reference += p * (phi - (p * phi).sum(axis=1, keepdims=True)) / steps
    phi_p, _ = softmax_to_probability(phi, bias)
    assert_allclose(phi_p, reference, rtol=0, atol=1e-3)
    # A row's result is its own: the same as when it is converted alone.
    alone, _ = softmax_to_probability(phi[7:8], bias[7:8])
    assert_allclose(alone, phi_p[7:8], rtol=0, atol=0)


def test_feature_raising_only_class_c_never_lowers_p_c():
    rng = np.random.default_rng(2)
    phi, bias = rng.normal(size=(200, 3, 4)), rng.normal(size=(200, 3))
    c, i = 1, 2
    phi[:, :, i] = 0.0
    phi[:, c, i] = rng.uniform(0.01, 3.0, size=200)
    phi_p, _ = softmax_to_probability(phi, bias)
    assert (phi_p[:, c, i] >= 0).all()


def test_all_zero_contributions_spread_the_residual_evenly():
    phi, bias = np.zeros((5, 3, 4)), np.random.default_rng(3).normal(size=(5, 3))
    phi_p, bias_p = softmax_to_probability(phi, bias)
    assert np.isfinite(phi_p).all()
    assert_allclose(phi_p.sum(-1) + bias_p, softmax(bias, axis=1), rtol=0, atol=1e-15)


@pytest.mark.parametrize("kind", ["classifier", "regressor"])
def test_saabas_matches_the_tree(kind):
    rng = np.random.default_rng(4)
    X = rng.normal(size=(200, 5)).astype(np.float32)
    if kind == "classifier":
        y = (X[:, 0] + X[:, 1] > 0).astype(int) + (X[:, 2] > 1)
        tree = ExtraTreeClassifier(random_state=0).fit(X, y)
        expected, k = tree.predict_proba(X), 3
    else:
        y = X[:, 0] * 2 + X[:, 3]
        tree = ExtraTreeRegressor(random_state=0, min_samples_leaf=3).fit(X, y)
        expected, k = tree.predict(X)[:, None], 1
    phi, bias = saabas(tree, X, k)
    assert phi.shape == (200, k, 5)
    assert bias.shape == (200, k)
    assert_allclose(phi.sum(-1) + bias, expected, rtol=0, atol=1e-12)
    # Each split credits its own feature: walk the tree row by row.
    t = tree.tree_
    value = t.value[:, 0, :k] / (t.value[:, 0, :].sum(1, keepdims=True) if k > 1 else 1)
    for row in range(20):
        walked, node = np.zeros((k, 5)), 0
        while t.children_left[node] >= 0:
            feature = t.feature[node]
            left = X[row, feature] <= t.threshold[node]
            child = t.children_left[node] if left else t.children_right[node]
            walked[:, feature] += value[child] - value[node]
            node = child
        assert_allclose(phi[row], walked, rtol=0, atol=1e-12)
        assert_allclose(bias[row], value[0], rtol=0, atol=0)


# --- real models -------------------------------------------------------------------------


@pytest.mark.parametrize("task", TASKS)
@pytest.mark.parametrize("family", list(FAMILIES))
def test_family_contributions_are_additive(task, family):
    fit = _fit(task)
    model = _with_members(fit, [(family, 1.0, fit.cv_models[family])])
    c = _assert_additive(model, _features())
    expected_outputs = {"binary": [True], "multiclass": fit.classes_, "regression": ["value"]}
    assert c.outputs == expected_outputs[task]
    assert c.values.dtype == np.float64


@pytest.mark.parametrize("task", ["binary", "multiclass"])
def test_mixed_ensemble_refit_like_and_fold_fallback(task):
    fit = _fit(task)
    weights = dict(zip(FAMILIES, [0.4, 0.3, 0.2, 0.1], strict=True))
    X = _features()
    refit_like = [(name, w, fit.cv_models[name][:1]) for name, w in weights.items()]
    _assert_additive(_with_members(fit, refit_like), X)
    folds = [(name, w, fit.cv_models[name]) for name, w in weights.items()]
    _assert_additive(_with_members(fit, folds), X)


def test_mixed_ensemble_regression():
    fit = _fit("regression")
    weights = dict(zip(FAMILIES, [0.4, 0.3, 0.2, 0.1], strict=True))
    folds = [(name, w, fit.cv_models[name]) for name, w in weights.items()]
    _assert_additive(_with_members(fit, folds), _features())


@pytest.mark.parametrize("task", TASKS)
def test_xgboost_early_stopped_fold_model(task):
    fit = _fit(task)
    spec, model = _fold_fit(fit, "XGBoost")
    booster = model.get_booster()
    assert model.best_iteration + 1 < booster.num_boosted_rounds()
    _assert_additive(replace(fit, members=[Member(spec, 1.0, [model])]), _features())


@pytest.mark.parametrize("missing", [0, 2])
@pytest.mark.parametrize("family", ["ExtraTrees", "LightGBM"])
def test_fold_model_missing_a_class(family, missing):
    fit = _fit("multiclass")
    codes = pd.Categorical(_task_frame("multiclass", _frame())["判定"], fit.classes_).codes
    spec, model = _fold_fit(fit, family, keep=codes != missing, n_classes=3)
    assert list(model.classes_) == [c for c in range(3) if c != missing]
    one = replace(fit, members=[Member(spec, 1.0, [model])])
    X = _features()
    c = contributions(one, X)
    expected = spec.predict(model, getattr(fit.prep, spec.view)(X))
    assert_allclose(c.prediction, expected, rtol=1e-5, atol=1e-5)
    assert (c.values[:, missing] == 0).all()
    assert (c.bias[:, missing] == 0).all()
    # Mixed with a fold model that saw every class, still additive against predict_proba.
    full = fit.cv_models[family][0]
    mixed = replace(fit, members=[Member(spec, 1.0, [model, full])])
    _assert_additive(mixed, X)


def test_datetime_parts_sum_into_their_column():
    fit = _fit("multiclass")
    assert any(name.startswith("when__") for name in fit.prep.feature_names)
    c = _assert_additive(fit, _features())
    assert c.columns == fit.columns
    assert "when" in c.columns
    assert not any("__" in column for column in c.columns)
    # Each feature lands on its source column: one unconverted model, grouped independently.
    regression = _fit("regression")
    one = _with_members(regression, [("ExtraTrees", 1.0, regression.cv_models["ExtraTrees"][:1])])
    spec = one.members[0].spec
    X = _features()
    phi, _ = explain.native_contributions(spec, one.members[0].models[0], one.prep.dense(X))
    parts = [i for i, name in enumerate(one.prep.feature_names) if name.startswith("when__")]
    assert np.abs(phi[:, 0, parts]).sum() > 0
    by_feature = pd.DataFrame(phi[:, 0], columns=one.prep.sources)
    expected = by_feature.T.groupby(level=0, sort=False).sum().T[one.columns]
    assert_allclose(contributions(one, X).values[:, 0], expected.to_numpy(), rtol=0, atol=1e-12)


@pytest.mark.parametrize("task", TASKS)
def test_awkward_rows_are_additive(task):
    fit = _fit(task)
    X = _features(6, seed=5)
    X["when"] = X["when"].astype(object)
    X.loc[X.index[0], "<b>x</b>"] = np.nan
    X.loc[X.index[1], "BiasTerm"] = "purple"  # unseen
    X.loc[X.index[2], "BiasTerm"] = None
    X.loc[X.index[3], "when"] = "2023-03-01 12:00:00"
    X.loc[X.index[4], "when"] = "not a date"
    X.loc[X.index[5], "when"] = None
    folds = [(name, 0.25, fit.cv_models[name]) for name in FAMILIES]
    _assert_additive(_with_members(fit, folds), X)
    _assert_additive(fit, X)


@pytest.mark.parametrize("task", TASKS)
def test_empty_frame(task, monkeypatch):
    fit = _fit(task)
    calls = []
    monkeypatch.setattr(explain, "native_contributions", lambda *a: calls.append(a))
    c = contributions(fit, _features().iloc[:0])
    k_out = {"binary": 1, "multiclass": 3, "regression": 1}[task]
    assert c.values.shape == (0, k_out, len(fit.columns))
    assert c.bias.shape == (0, k_out)
    assert c.prediction.shape == (0, k_out)
    assert calls == []
    with pytest.raises(ConfigError, match="missing columns"):
        contributions(fit, _features().iloc[:0].drop(columns=["幅"]))


def test_hostile_column_names_are_kept():
    fit = _fit("regression")
    c = _assert_additive(fit, _features())
    for name in HOSTILE:
        assert name in c.columns
    assert c.columns == fit.columns


def test_slots():
    binary = contributions(_fit("binary"), _features())
    assert (binary.slots() == 0).all()
    multi = contributions(_fit("multiclass"), _features())
    assert (multi.slots() == multi.prediction.argmax(1)).all()
    assert (multi.slots(2) == 2).all()
    assert multi.slots(2).shape == (len(multi.prediction),)
    assert (multi.slots(np.int64(1)) == 1).all()
    for bad in (-1, 3, True, 1.0, "1"):
        with pytest.raises(ValueError):
            multi.slots(bad)
    with pytest.raises(ValueError):
        binary.slots(1)


# --- partial dependence and global importance ----------------------------------------------


def _background(n: int = 40, seed: int = 7) -> pd.DataFrame:
    return _features(n, seed)


def _curves(model: TrainedModel, background: pd.DataFrame, column: str, grid: list):
    """(rows, G, outputs): the outputs with ``column`` set to each grid value, one at a time."""
    curves = []
    for value in grid:
        X = background.copy()
        X[column] = pd.Series([value] * len(X), index=X.index, dtype=object)
        if model.task == "regression":
            curves.append(model.predict(X).to_numpy()[:, None])
        else:
            proba = model.predict_proba(X).to_numpy()
            curves.append(proba[:, 1:] if len(model.classes_) == 2 else proba)
    return np.stack(curves, axis=1)


def _assert_grid(result, kind: str):
    assert result.kind == kind
    assert 2 <= len(result.grid) <= PD_GRID
    json.dumps(result.grid, allow_nan=False)
    assert result.average.shape == (len(result.grid), len(result.outputs))
    assert np.isfinite(result.average).all()


def test_kind_of():
    prep = _fit("regression").prep
    assert prep.kind_of("幅") == "numeric"
    assert prep.kind_of("when") == "datetime"
    assert prep.kind_of("BiasTerm") == "category"
    ids = pd.DataFrame({"id": [f"k{i}" for i in range(300)], "n": np.arange(300.0)})
    assert Prep().fit(ids).kind_of("id") == "frequency"
    for unused in ("constant", "nope"):
        with pytest.raises(KeyError):
            prep.kind_of(unused)


def test_pd_matches_a_hand_computed_average():
    fit = _fit("regression")
    background = _background()
    result = partial_dependence(fit, background, "幅")
    _assert_grid(result, "numeric")
    assert result.column == "幅"
    assert result.outputs == ["value"]
    assert result.n_rows == len(background)
    curves = _curves(fit, background, "幅", result.grid)
    assert_allclose(result.average[:, 0], curves[:, :, 0].mean(0), rtol=0, atol=1e-12)


@pytest.mark.parametrize("ice_rows", [0, 10, ICE_ROWS])
def test_ice_rows_are_the_individual_curves(ice_rows):
    fit = _fit("regression")
    background = _background()
    result = partial_dependence(fit, background, "<b>x</b>", ice_rows=ice_rows)
    assert result.ice.shape == (min(ice_rows, len(background)), len(result.grid))
    curves = _curves(fit, background, "<b>x</b>", result.grid)[:, :, 0]
    # Each ICE curve is one background row's curve, each row at most once.
    matched = [np.flatnonzero(np.abs(curves - ice).max(1) <= 1e-12) for ice in result.ice]
    assert all(len(rows) == 1 for rows in matched)
    assert len({int(rows[0]) for rows in matched}) == len(matched)
    if len(result.ice) == len(background):
        assert_allclose(result.ice.mean(0), result.average[:, 0], rtol=0, atol=1e-12)


def test_sparse_numeric_column_gets_an_even_spread():
    fit = _fit("regression")
    background = _background(200)
    sparse_values = np.zeros(200)
    sparse_values[:10] = np.linspace(0.5, 9.7, 10)  # 95% zeros
    background["contrib_x"] = sparse_values
    result = partial_dependence(fit, background, "contrib_x")
    _assert_grid(result, "numeric")
    p2, p98 = np.quantile(sparse_values, [0.02, 0.98])
    inside = {g for g in result.grid if p2 <= g <= p98}
    assert len(inside) >= 10
    assert result.grid == sorted(set(result.grid))


def test_rare_indicator_column_is_spread_to_its_extremes():
    # 99% zeros: the 2nd and 98th percentiles are both 0.
    fit = _fit("regression")
    background = _background(200)
    background["contrib_x"] = np.where(np.arange(200) < 2, 1, 0)
    assert partial_dependence(fit, background, "contrib_x").grid == [0, 1]
    background["contrib_x"] = np.where(np.arange(200) < 2, [0.3, 2.7] * 100, 0.0)
    result = partial_dependence(fit, background, "contrib_x")
    _assert_grid(result, "numeric")
    assert len(result.grid) >= 10
    assert result.grid[0] == 0.0 and result.grid[-1] == 2.7
    # Only a column with a single value gets a single point.
    background["contrib_x"] = 0.5
    single = partial_dependence(fit, background, "contrib_x", ice_rows=10)
    assert single.grid == [0.5]
    assert single.average.shape == (1, 1)
    assert single.ice.shape == (10, 1)


@pytest.mark.parametrize("high", [4, 100])
def test_integer_column_gets_integer_grid(high):
    fit = _fit("regression")
    background = _background(200)
    background["contrib_x"] = np.random.default_rng(0).integers(0, high, 200).astype(np.int64)
    result = partial_dependence(fit, background, "contrib_x")
    _assert_grid(result, "numeric")
    assert all(type(g) is int for g in result.grid)
    assert result.grid == sorted(set(result.grid))
    assert set(result.grid) <= set(range(high))


def test_categorical_grid_is_top_levels_plus_missing():
    fit = _fit("regression")
    background = _background(170)
    # blue and green tie: by label
    levels = ["purple"] * 30 + ["green"] * 40 + ["red"] * 50 + ["blue"] * 40 + [None] * 10
    background["BiasTerm"] = pd.Series(levels, index=background.index, dtype=object)
    result = partial_dependence(fit, background, "BiasTerm", grid_size=4)
    _assert_grid(result, "category")
    assert result.grid == ["red", "blue", "green", None]
    curves = _curves(fit, background, "BiasTerm", result.grid)
    assert_allclose(result.average, curves.mean(0), rtol=0, atol=1e-12)
    assert partial_dependence(fit, background, "BiasTerm", grid_size=2).grid == ["red", None]


def test_bool_column_gets_false_true_missing():
    fit = _fit("regression")
    background = _background(50)
    background["BiasTerm"] = np.arange(50) % 3 > 0  # True is the more frequent
    result = partial_dependence(fit, background, "BiasTerm")
    _assert_grid(result, "category")
    assert result.grid == [False, True, None]
    assert [type(g) for g in result.grid[:2]] == [bool, bool]


def test_datetime_column_is_varied_on_the_raw_column():
    fit = _fit("regression")
    background = _background()
    background["when"] = background["when"].astype(str)  # raw strings, parsed by the prep
    result = partial_dependence(fit, background, "when")
    _assert_grid(result, "datetime")
    assert all(isinstance(g, str) for g in result.grid)
    assert result.grid == sorted(result.grid)
    stamps = [pd.Timestamp(g) for g in result.grid]
    assert all(stamp == stamp.floor("s") for stamp in stamps)
    curves = _curves(fit, background, "when", result.grid)
    assert_allclose(result.average, curves.mean(0), rtol=0, atol=1e-12)


def test_limits():
    fit = _fit("regression")
    background = _background()
    for bad in (
        {"grid_size": 21},
        {"grid_size": 1},
        {"grid_size": 2.5},
        {"max_rows": 301},
        {"max_rows": 0},
        {"ice_rows": 51},
        {"ice_rows": -1},
    ):
        with pytest.raises(ValueError):
            partial_dependence(fit, background, "幅", **bad)
    assert "constant" in fit.prep.dropped
    for unused in ("constant", "nope"):
        with pytest.raises(ValueError, match=repr(unused)):
            partial_dependence(fit, background, unused)
    for blank in (background.assign(幅=np.nan), background.drop(columns=["幅"])):
        with pytest.raises(ValueError, match="'幅'"):
            partial_dependence(fit, blank, "幅")
    with pytest.raises(ValueError, match="'BiasTerm'"):
        partial_dependence(fit, background.assign(BiasTerm=None), "BiasTerm")
    for limit in (2, PD_GRID):
        assert len(partial_dependence(fit, background, "幅", grid_size=limit).grid) <= limit


def test_background_is_sampled_with_the_seed():
    fit = _fit("regression")
    background = _background(1000)
    first = partial_dependence(fit, background, "幅")
    again = partial_dependence(fit, background, "幅")
    assert first.n_rows == PD_ROWS
    assert first.grid == again.grid
    assert_allclose(first.average, again.average, rtol=0, atol=0)
    assert_allclose(first.ice, again.ice, rtol=0, atol=0)
    other = partial_dependence(fit, background, "幅", seed=1)
    assert other.n_rows == PD_ROWS
    assert not np.array_equal(other.average, first.average)
    assert partial_dependence(fit, background, "幅", max_rows=100).n_rows == 100


def test_multiclass_ice_defaults_to_the_most_varying_class():
    fit = _fit("multiclass")
    background = _background()
    result = partial_dependence(fit, background, "<b>x</b>")
    assert result.outputs == fit.classes_
    assert_allclose(result.average.sum(1), 1.0, rtol=0, atol=1e-12)
    spread = result.average.max(0) - result.average.min(0)
    assert result.ice_output == int(np.argmax(spread))
    assert_allclose(result.ice.mean(0), result.average[:, result.ice_output], rtol=0, atol=1e-12)
    other = (result.ice_output + 1) % 3
    chosen = partial_dependence(fit, background, "<b>x</b>", class_index=other)
    assert chosen.ice_output == other
    assert_allclose(chosen.average, result.average, rtol=0, atol=0)
    assert_allclose(chosen.ice.mean(0), chosen.average[:, other], rtol=0, atol=1e-12)
    for bad in (3, -1, True):
        with pytest.raises(ValueError):
            partial_dependence(fit, background, "<b>x</b>", class_index=bad)
    binary = partial_dependence(_fit("binary"), background, "<b>x</b>")
    assert binary.outputs == [True]
    assert binary.ice_output == 0
    assert binary.average.shape == (len(binary.grid), 1)
    with pytest.raises(ValueError):
        partial_dependence(_fit("binary"), background, "<b>x</b>", class_index=1)


@pytest.mark.parametrize("task", TASKS)
def test_pd_makes_one_predict_call(task, monkeypatch):
    fit = _fit(task)
    calls = []
    original = TrainedModel._predict

    def counting(self, df):
        calls.append(len(df))
        return original(self, df)

    monkeypatch.setattr(TrainedModel, "_predict", counting)
    result = partial_dependence(fit, _background(), "BiasTerm")
    assert calls == [result.n_rows * len(result.grid)]


def test_global_importance_orders_by_mean_abs():
    values = np.array(
        [
            [[0.1, -2.0, 0.5], [0.0, 1.0, -0.5]],
            [[-0.3, 0.0, 0.5], [0.2, -1.0, 3.5]],
        ]
    )
    bias = np.zeros((2, 2))
    c = Contributions(["a", "b", "c"], ["x", "y"], values, bias, values.sum(-1) + bias)
    importance = global_importance(c)
    assert list(importance.index) == ["c", "b", "a"]
    assert_allclose(importance[["a", "b", "c"]], [0.3, 2.0, 2.5], rtol=0, atol=1e-15)
    empty = Contributions(
        ["a", "b"], ["x"], np.zeros((0, 1, 2)), np.zeros((0, 1)), np.zeros((0, 1))
    )
    assert (global_importance(empty) == 0).all()
    fit = _fit("binary")
    real = global_importance(contributions(fit, _features()))
    assert sorted(real.index) == sorted(fit.columns)
    assert (np.diff(real.to_numpy()) <= 0).all()
