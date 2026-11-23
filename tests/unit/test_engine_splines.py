"""LinearSpline: a linear model on the linear view and a hinge at each knot of every number."""

import pickle

import numpy as np
import pandas as pd
import pytest

from fione.engine import automl as automl_module
from fione.engine import explain
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.engine.families import FAMILIES
from fione.engine.model import Member, TrainedModel
from fione.engine.prep import SPLINE_COLUMNS, SPLINE_KNOTS, Prep
from fione.engine.search import Deadline


def _data(n=1500, seed=0):
    """A signal that bends in one number, a few-valued number, a category and a noise column."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "a": rng.normal(size=n),
            "b": rng.uniform(-3, 3, n),
            "few": rng.integers(0, 3, n).astype(float),
            "kind": rng.choice(list("xyz"), n),
            "noise": rng.normal(size=n),
        }
    )
    score = np.sin(2 * df["b"]) + df["a"] ** 2 - 1.0 + df["few"] * 0.5
    df["y"] = (score + rng.logistic(scale=0.4, size=n) > 0).astype(int)
    return df


def test_the_knots_are_quantiles_of_the_numbers_with_many_values():
    df = _data()
    prep = Prep().fit(df.drop(columns="y"))
    names = {prep.feature_names[int(p[1:])] for p in prep._knots}
    assert names == {"a", "b", "noise"}  # not the number of 3 values, not the category
    for knots in prep._knots.values():
        assert len(knots) == SPLINE_KNOTS and (np.diff(knots) > 0).all()
    assert prep.spline_width == prep.linear_width + SPLINE_KNOTS * 3


def test_the_view_is_the_linear_view_and_a_hinge_per_knot():
    df = _data()
    X = df.drop(columns="y")
    prep = Prep().fit(X)
    linear, view = prep.linear(X), prep.splines(X)
    assert list(view.columns[: linear.shape[1]]) == list(linear.columns)
    np.testing.assert_array_equal(view[linear.columns].to_numpy(), linear.to_numpy())
    position, knots = next(iter(prep._knots.items()))
    for i, knot in enumerate(knots):
        np.testing.assert_allclose(view[f"{position}_s{i}"], np.maximum(linear[position] - knot, 0))


def test_a_number_that_repeats_a_few_values_gets_fewer_knots_not_duplicates():
    rng = np.random.default_rng(0)
    values = np.where(rng.random(2000) < 0.9, 0.0, rng.normal(size=2000) + 5)  # most are zero
    X = pd.DataFrame({"a": values, "b": rng.normal(size=2000)})
    prep = Prep().fit(X)
    for knots in prep._knots.values():
        assert (np.diff(knots) > 0).all()


def test_only_the_numbers_with_the_most_values_are_bent():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(300, SPLINE_COLUMNS + 10)))
    X.columns = [f"c{i}" for i in X.columns]
    assert len(Prep().fit(X)._knots) == SPLINE_COLUMNS


def test_a_prep_from_before_the_view_has_no_knots_and_the_family_does_not_apply():
    df = _data()
    X = df.drop(columns="y")
    prep = Prep().fit(X)
    del prep.__dict__["_knots"]  # as an unpickled old one: the class default stands
    assert prep._knots == {}
    assert not FAMILIES["LinearSpline"].applies(prep, X)
    assert prep.splines(X).shape == prep.linear(X).shape


def test_it_does_not_apply_without_a_number_with_many_values_or_for_too_many_cells(monkeypatch):
    X = pd.DataFrame({"kind": list("xyz") * 50, "few": [0.0, 1.0, 2.0] * 50})
    assert not FAMILIES["LinearSpline"].applies(Prep().fit(X), X)
    df = _data()
    X = df.drop(columns="y")
    prep = Prep().fit(X)
    assert FAMILIES["LinearSpline"].applies(prep, X)
    monkeypatch.setattr("fione.engine.families.SPLINE_MAX_CELLS", len(X) * prep.spline_width - 1)
    assert not FAMILIES["LinearSpline"].applies(prep, X)


def test_it_follows_a_curve_the_linear_family_cannot_and_explains_it():
    df = _data()
    X, y = df.drop(columns="y"), df["y"].to_numpy()
    prep = Prep().fit(X)
    train, valid = slice(0, 1100), slice(1100, None)
    spec, plain = (
        FAMILIES["LinearSpline"]("classification", 2),
        FAMILIES["Linear"]("classification", 2),
    )
    view, linear = prep.splines(X), prep.linear(X)
    model = spec.fit(
        spec.defaults, view.iloc[train], y[train], view.iloc[valid], y[valid], Deadline(60)
    )
    base = plain.fit(
        plain.defaults, linear.iloc[train], y[train], linear.iloc[valid], y[valid], Deadline(60)
    )
    pred = spec.predict(model, view.iloc[valid])
    accuracy = lambda p: (p.argmax(axis=1) == y[valid]).mean()  # noqa: E731
    assert accuracy(pred) > accuracy(plain.predict(base, linear.iloc[valid])) + 0.05
    restored = pickle.loads(pickle.dumps(model))
    np.testing.assert_array_equal(spec.predict(restored, view.iloc[valid]), pred)

    trained = TrainedModel(
        task="classification",
        target="y",
        classes_=[0, 1],
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
    np.testing.assert_allclose(c.prediction, pred[:, 1:], atol=1e-6)  # the curves add up


def test_it_joins_the_search_as_a_late_family():
    df = _data(1200, seed=2)
    config = TrainConfig(
        target="y", max_runtime_secs=300, stopping_rounds=1, stopping_tolerance=0.5
    )
    model = AutoML(config, families=["Linear", "LightGBM", "LinearSpline"]).fit(df)
    assert "LinearSpline" in set(model.trials["family"])
    assert model.predict_proba(df.drop(columns="y")).shape == (1200, 2)


def test_it_comes_after_linear_boost_and_takes_little_of_the_time_of_the_others(monkeypatch):
    from test_engine_late import _schedule

    order, weights = automl_module.LATE_ORDER, automl_module.LATE_WEIGHTS
    medians = automl_module.MEDIAN_ORDER
    assert order.index("LinearSpline") == order.index("LinearBoost") + 1
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["LinearSpline"] <= weights["LinearBoost"] / 16
    for late in (("LinearBoost",), ("LinearBoost", *medians)):
        without = {n: s for n, s, _ in _schedule(monkeypatch, 0.1, late=late)}
        spline = {
            n: s
            for n, s, _ in _schedule(
                monkeypatch, 0.1, late=("LinearBoost", "LinearSpline", *late[1:])
            )
        }
        assert list(spline)[-len(late) - 1 :][:2] == ["LinearBoost", "LinearSpline"]
        for name in late:  # no one else loses more than the nominal share
            assert spline[name] > 0.93 * without[name]
    assert spline["LinearSpline"] < 0.1 * spline["LinearBoost"]  # after the median variants
