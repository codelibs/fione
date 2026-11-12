"""LinearWide: a linear model on every value of the categorical columns (the levels view)."""

import pickle

import numpy as np
import pandas as pd
import pytest

from fione.engine import explain, search
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.engine.families import FAMILIES, Levels, LinearWide
from fione.engine.model import Member, TrainedModel, feature_importance
from fione.engine.prep import LINEAR_LEVELS, MAX_LEVELS, Prep


def _data(n=600, seed=0, values=40):
    """A column of many values that decides the target, a few-valued one, a month and a number."""
    rng = np.random.default_rng(seed)
    weight = {f"u{i}": rng.normal(scale=2.0) for i in range(values)}
    df = pd.DataFrame(
        {
            "user": rng.choice(list(weight), n),
            "kind": rng.choice(list("abc"), n),
            "month": rng.integers(1, 13, n),
            "x": rng.normal(size=n),
        }
    )
    score = df["user"].map(weight) + 0.3 * df["x"]
    df["y"] = (score + rng.logistic(size=n) > score.median()).astype(int)
    return df


def test_the_levels_view_reads_the_values_as_text_beside_the_numbers():
    df = _data()
    X = df.drop(columns="y")
    prep = Prep().fit(X)
    view = prep.levels(X)
    texts = [c for c in view.columns if c.endswith("_l")]
    assert len(texts) == 3  # the two categoricals and the month (a few whole numbers)
    assert set(view[texts[0]]) <= set(X["user"]) | set(X["kind"]) | {str(m) for m in range(1, 13)}
    # the one-hot columns of the categoricals are replaced; the numbers (and the month) stay
    linear = prep.linear(X)
    assert len(view.columns) < len(linear.columns) + len(texts)
    assert not any(c.endswith("_0") for c in view.columns)
    assert prep.level_width >= 40 + 3 + 12


def test_the_levels_view_leaves_prose_and_missing_values_alone():
    rng = np.random.default_rng(1)
    words = "rocket orbit launch moon crew planet bread cheese soup".split()
    X = pd.DataFrame(
        {
            "post": [" ".join(rng.choice(words, 8)) for _ in range(200)],
            "tag": rng.choice(["p", "q", None], 200),
        }
    )
    prep = Prep().fit(X)
    assert prep.prose == ("post",)
    view = prep.levels(X)
    assert [c for c in view.columns if c.endswith("_l")] == ["f1_l"]
    assert "__na__" in set(view["f1_l"])


def test_the_levels_view_reads_infinite_huge_and_text_numbers_like_missing_or_whole_ones():
    X = _data().drop(columns="y")
    prep = Prep().fit(X)
    month = next(n for n, c in prep._level_at.items() if c == "month")
    odd = X.head(4).assign(month=[1.0, np.inf, 1e30, 3.0])
    view = prep.levels(odd)
    assert view[month].tolist() == ["1", "__na__", "__na__", "3"]
    as_text = prep.levels(X.head(2).assign(month=["1.0", "2"]))
    assert as_text[month].tolist() == ["1", "2"]


def test_the_levels_view_keeps_the_one_hot_columns_of_prose():
    rng = np.random.default_rng(2)
    words = "rocket orbit launch moon crew planet bread cheese soup".split()
    X = pd.DataFrame(
        {
            "post": [" ".join(rng.choice(words, 8)) for _ in range(200)],
            "tag": rng.choice(list("pqrstuvwxyzabcdefgh"), 200),
        }
    )
    prep = Prep().fit(X)
    view = prep.levels(X)
    assert any(c.startswith("f0_") and not c.endswith("_l") for c in view.columns)
    assert [c for c in view.columns if c.endswith("_l")] == ["f1_l"]


def test_the_width_of_the_levels_is_capped_per_column():
    X = pd.DataFrame({"id": [f"k{i}" for i in range(2 * MAX_LEVELS + 50)] * 2, "x": 1.0})
    X["x"] = np.arange(len(X), dtype=float)
    prep = Prep().fit(X)
    assert prep.level_width == MAX_LEVELS


def test_levels_are_the_values_seen_often_enough_and_unseen_ones_are_zeros():
    train = pd.Series(["a"] * 5 + ["b"] * 3 + ["c"])  # c is seen once
    levels = Levels(train)
    assert sorted(levels.vocabulary_) == ["a", "b"]
    matrix = levels.transform(pd.Series(["b", "a", "c", "zzz"]))
    assert matrix.shape == (4, 2)
    assert matrix.toarray().tolist() == [[0, 1], [1, 0], [0, 0], [0, 0]]


def test_it_applies_to_data_where_the_linear_view_loses_values():
    many = Prep().fit(_data(values=LINEAR_LEVELS + 5).drop(columns="y"))
    assert LinearWide.applies(many, None)
    few = pd.DataFrame({"kind": list("abc") * 50, "x": np.arange(150.0)})
    assert not LinearWide.applies(Prep().fit(few), None)  # a column of 3 values loses none
    wide = pd.DataFrame({"id": [f"k{i}" for i in range(400)] * 2, "x": np.arange(800.0)})
    assert LinearWide.applies(Prep().fit(wide), None)  # frequency encoded for the other families
    words = pd.DataFrame({"post": [f"w{i} x{i} y{i} z{i} q{i} r{i}" for i in range(300)]})
    assert not LinearWide.applies(Prep().fit(words), None)  # text is no level


def test_it_fits_predicts_pickles_and_explains():
    df = _data(600, seed=3)
    X = df.drop(columns="y")
    y = df["y"].to_numpy()
    prep = Prep().fit(X)
    spec = FAMILIES["LinearWide"]("classification", 2)
    view = prep.levels(X)
    train, valid = slice(0, 450), slice(450, None)
    deadline = search.Deadline(60)
    model = spec.fit(spec.defaults, view.iloc[train], y[train], None, None, deadline)
    proba = spec.predict(model, view.iloc[valid])
    assert proba.shape == (150, 2) and np.allclose(proba.sum(axis=1), 1)
    assert (proba.argmax(axis=1) == y[valid]).mean() > 0.65
    assert spec.size_bytes(model) > 0 and spec.rounds(model) == 1
    restored = pickle.loads(pickle.dumps(model))
    np.testing.assert_array_equal(spec.predict(restored, view.iloc[valid]), proba)

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
    np.testing.assert_allclose(
        c.prediction, spec.predict(model, view.iloc[valid])[:, 1:], atol=1e-6
    )  # a binary target explains its second class
    assert c.values.shape == (150, 1, len(prep.columns))
    importance = feature_importance(trained.members, prep)
    assert importance.sum() == pytest.approx(1.0)
    assert prep.columns[int(np.argmax(np.asarray(importance)))] == "user"  # the column that decides


def test_it_joins_the_search_of_such_data_and_scores_with_the_best_where_the_values_decide():
    df = _data(3000, seed=4, values=150)
    # Each family ends by itself (nothing improves by half), so a loaded machine cannot cut the
    # search short before the late family has had its trials
    config = TrainConfig(
        target="y", max_runtime_secs=600, stopping_rounds=1, stopping_tolerance=0.5
    )
    model = AutoML(config, families=["LightGBM", "LinearWide"]).fit(df)
    assert "LinearWide" in set(model.leaderboard["family"])
    ensemble = model.leaderboard.set_index("model")
    wide = ensemble[ensemble["family"] == "LinearWide"]["cv_score"].min()
    others = ensemble[~ensemble["family"].isin(["LinearWide", "Ensemble"])]["cv_score"].min()
    assert wide < 1.05 * others  # the identity of the user column is all that matters here
