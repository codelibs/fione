"""LinearBoost: small trees boosted from a linear model's margin; the small-tree start trials."""

import pickle
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from fione.engine import explain
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.engine.families import FAMILIES
from fione.engine.model import Member, TrainedModel, feature_importance
from fione.engine.prep import Prep
from fione.engine.search import Deadline, make_folds, run_family


def _data(n=900, seed=0, kind="binary"):
    """An additive signal in three columns and a number that says nothing."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "a": rng.normal(size=n),
            "b": rng.normal(size=n),
            "kind": rng.choice(list("xyz"), n),
            "noise": rng.normal(size=n),
        }
    )
    score = 1.5 * df["a"] - df["b"] + df["kind"].map({"x": 1.0, "y": 0.0, "z": -1.0})
    if kind == "regression":
        df["y"] = score + rng.normal(scale=0.3, size=n)
    elif kind == "multiclass":
        df["y"] = pd.cut(score + rng.logistic(size=n), [-np.inf, -1, 1, np.inf], labels=False)
    else:
        df["y"] = (score + rng.logistic(size=n) > 0).astype(int)
    return df


@pytest.mark.parametrize("kind", ["binary", "multiclass", "regression"])
def test_it_fits_predicts_pickles_and_explains(kind):
    df = _data(kind=kind)
    X, y = df.drop(columns="y"), df["y"].to_numpy()
    prep = Prep().fit(X)
    task = "regression" if kind == "regression" else "classification"
    n_classes = len(np.unique(y)) if task == "classification" else 0
    spec = FAMILIES["LinearBoost"](task, n_classes)
    view = prep.linear(X)
    train, valid = slice(0, 650), slice(650, None)
    model = spec.fit(
        spec.defaults, view.iloc[train], y[train], view.iloc[valid], y[valid], Deadline(60)
    )
    pred = spec.predict(model, view.iloc[valid])
    assert spec.rounds(model) >= 1 and spec.size_bytes(model) > 0
    if task == "classification":
        assert pred.shape == (250, n_classes) and np.allclose(pred.sum(axis=1), 1)
        assert (pred.argmax(axis=1) == y[valid]).mean() > 0.55
    else:
        assert np.corrcoef(pred, y[valid])[0, 1] > 0.9
    restored = pickle.loads(pickle.dumps(model))
    np.testing.assert_array_equal(spec.predict(restored, view.iloc[valid]), pred)

    trained = TrainedModel(
        task=task,
        target="y",
        classes_=list(range(n_classes)) if task == "classification" else None,
        columns=prep.columns,
        leaderboard=None,
        trials=None,
        feature_importance=None,
        stop_reason="no_improvement",
        config=TrainConfig(target="y"),
        metrics={},
        prep=prep,
        members=[Member(spec, 1.0, [model], spec.name)],
    )
    c = explain.contributions(trained, X.iloc[valid])
    expected = pred[:, 1:] if n_classes == 2 else pred.reshape(len(pred), -1)
    np.testing.assert_allclose(c.prediction, expected, atol=1e-6)
    importance = np.asarray(feature_importance(trained.members, prep))
    assert importance.sum() == pytest.approx(1.0)
    assert prep.columns[int(np.argmin(importance))] == "noise"  # the column that says nothing


def test_the_trees_add_what_the_linear_model_misses():
    rng = np.random.default_rng(1)
    n = 3000
    X = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n)})
    signal = X["a"] ** 2 - 1.0 + 0.3 * X["b"]  # a line cannot follow the square of a
    y = ((signal + rng.logistic(scale=0.3, size=n)) > 0).astype(int).to_numpy()
    prep = Prep().fit(X)
    view = prep.linear(X)
    spec = FAMILIES["LinearBoost"]("classification", 2)
    train, valid = slice(0, 2200), slice(2200, None)
    boosted = spec.fit(
        spec.defaults, view.iloc[train], y[train], view.iloc[valid], y[valid], Deadline(60)
    )
    linear = FAMILIES["Linear"]("classification", 2)
    plain = linear.fit(
        linear.defaults, view.iloc[train], y[train], view.iloc[valid], y[valid], Deadline(60)
    )
    accuracy = lambda s, m: (s.predict(m, view.iloc[valid]).argmax(axis=1) == y[valid]).mean()  # noqa: E731
    assert accuracy(spec, boosted) > accuracy(linear, plain) + 0.1  # the square of a


def test_it_joins_the_search_as_a_late_family():
    df = _data(1500, seed=2)
    config = TrainConfig(
        target="y", max_runtime_secs=300, stopping_rounds=1, stopping_tolerance=0.5
    )
    model = AutoML(config, families=["Linear", "LightGBM", "LinearBoost"]).fit(df)
    assert "LinearBoost" in set(model.leaderboard["family"])


@pytest.mark.parametrize("name", ["LightGBM", "XGBoost", "CatBoost"])
def test_the_search_starts_with_the_defaults_and_a_trial_of_small_trees(name):
    spec = FAMILIES[name]
    assert len(spec.starts) == 1
    df = _data(400, seed=3)
    X, y = df.drop(columns="y"), df["y"].to_numpy()
    prep = Prep().fit(X)
    folds = make_folds(y, "classification", 3, 0)
    events = []
    run_family(
        name,
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(120),
        events.append,
        lambda: sum(e.type == "trial" for e in events) >= 2,
    )
    trials = [e.data["params"] for e in events if e.type == "trial"]
    assert trials[:2] == [spec.defaults, spec.starts[0]]
    small = {"LightGBM": ("num_leaves", 4), "XGBoost": ("max_depth", 2), "CatBoost": ("depth", 2)}
    key, value = small[name]
    assert trials[1][key] == value < trials[0][key]


def test_explanations_count_the_width_of_the_linear_view():
    from types import SimpleNamespace

    from fione.engine.explain import _width

    linear = SimpleNamespace(coef_=np.zeros((1, 300)))
    member = SimpleNamespace(
        spec=FAMILIES["LinearBoost"]("classification", 2), models=[SimpleNamespace(linear=linear)]
    )
    assert _width(SimpleNamespace(members=[member]), 5) == 300


def test_the_explain_job_caps_the_threads_of_its_trees():
    df = _data(n=300)
    X, y = df.drop(columns="y"), df["y"].to_numpy()
    view = Prep().fit(X).linear(X)
    spec = FAMILIES["LinearBoost"]("classification", 2)
    spec.n_jobs = 8
    model = spec.fit(
        spec.defaults, view.iloc[:200], y[:200], view.iloc[200:], y[200:], Deadline(60)
    )
    before = spec.predict(model, view)
    explain.cap_threads(SimpleNamespace(members=[SimpleNamespace(spec=spec, models=[model])]), 2)
    assert model.booster.get_params()["n_jobs"] == 2
    np.testing.assert_array_equal(spec.predict(model, view), before)
