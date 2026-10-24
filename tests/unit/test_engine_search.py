import time

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification, make_regression

from fione.engine.config import Deadline, DeadlineExceeded, NoModelError
from fione.engine.families import FAMILIES, n_threads
from fione.engine.prep import Prep, validate_target
from fione.engine.search import make_folds, run_family

TRIAL_KEYS = {"family", "trial", "score", "params", "elapsed", "best_so_far"}


def _classification(n, features, seed=0):
    X, y = make_classification(n, features, n_informative=min(features - 2, 10), random_state=seed)
    return pd.DataFrame(X, columns=[f"x{i}" for i in range(features)]), y


def _setup(X, y, task="classification", nfolds=5, seed=0):
    y, _, nfolds = validate_target(pd.Series(y), task, nfolds)
    return Prep().fit(X), y, make_folds(y, task, nfolds, seed)


def _until_trials(events, count):
    return lambda: sum(e.type == "trial" for e in events) >= count


def _titanic_like(n=1300, seed=0):
    rng = np.random.default_rng(seed)
    sex = rng.choice(["male", "female"], n)
    pclass = rng.choice([1, 2, 3], n)
    age = np.where(rng.random(n) < 0.2, np.nan, rng.normal(30, 14, n).clip(0.5, 80))
    fare = rng.lognormal(3, 1, n)
    embarked = rng.choice(["S", "C", "Q", None], n, p=[0.7, 0.2, 0.09, 0.01])
    logit = 1.5 * (sex == "female") - 0.8 * (pclass - 2) - 0.02 * np.nan_to_num(age, nan=30) + 0.3
    survived = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    X = pd.DataFrame(
        {
            "pclass": pclass,
            "sex": sex,
            "age": age,
            "sibsp": rng.poisson(0.5, n),
            "fare": fare,
            "embarked": embarked,
        }
    )
    return X, survived


# --- families -----------------------------------------------------------------


def test_n_threads_uses_few_threads_on_small_data():
    assert 1 <= n_threads(1_300) <= 4
    assert n_threads(1_000_000) >= n_threads(1_300)


@pytest.mark.parametrize("name", list(FAMILIES))
def test_fit_with_expired_deadline_raises(name):
    X, y = _classification(200, 5)
    prep, y, _ = _setup(X, y)
    spec = FAMILIES[name]("classification", 2)
    view = getattr(prep, spec.view)(X)
    with pytest.raises(DeadlineExceeded):
        spec.fit(spec.defaults, view, y, view, y, Deadline(0))


@pytest.mark.parametrize("name", list(FAMILIES))
def test_fit_stops_at_deadline_with_usable_model(name):
    X, y = _classification(50_000, 30)
    prep, y, _ = _setup(X, y)
    spec = FAMILIES[name]("classification", 2, n_jobs=n_threads(len(X)))
    view = getattr(prep, spec.view)(X)
    start = time.monotonic()
    model = spec.fit(
        spec.defaults, view.iloc[:40_000], y[:40_000], view.iloc[40_000:], y[40_000:], Deadline(0.3)
    )
    assert time.monotonic() - start < 0.8
    proba = spec.predict(model, view.iloc[40_000:])
    assert proba.shape == (10_000, 2)
    assert np.allclose(proba.sum(axis=1), 1)


# --- run_family -----------------------------------------------------------------


def test_every_trial_emits_an_event_with_the_listed_keys():
    X, y = _classification(300, 5)
    prep, y, folds = _setup(X, y)
    events = []
    result = run_family(
        "LightGBM",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(30),
        events.append,
        _until_trials(events, 3),
    )
    trials = [e for e in events if e.type == "trial"]
    assert len(trials) == result.trials == 3
    for e in trials:
        assert TRIAL_KEYS <= set(e.data)
        assert e.data["family"] == "LightGBM"
        assert isinstance(e.data["score"], float) and isinstance(e.data["elapsed"], float)
    assert trials[0].data["params"] == FAMILIES["LightGBM"].defaults  # first trial = defaults
    assert result.best_score == min(
        e.data["score"] for e in trials if e.data["state"] == "complete"
    )
    assert [e.type for e in events][-2:] == ["stopped", "family_done"]


def test_classification_oof_holds_probabilities_and_models_pickle(tmp_path):
    X, y = _classification(300, 5)
    prep, y, folds = _setup(X, y)
    events = []
    result = run_family(
        "CatBoost",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(30),
        events.append,
        _until_trials(events, 1),
    )
    assert result.oof.shape == (300, 2)
    assert np.allclose(result.oof.sum(axis=1), 1)
    assert len(result.models) == len(folds)
    joblib.dump(result.models, tmp_path / "models.joblib")
    models = joblib.load(tmp_path / "models.joblib")  # a file this test wrote itself
    spec = FAMILIES["CatBoost"]("classification", 2)
    view = prep.catboost(X)
    assert np.allclose(spec.predict(models[0], view), spec.predict(result.models[0], view))


def test_regression_oof_has_one_column():
    X, y = make_regression(500, 5, noise=1.0, random_state=0)
    X = pd.DataFrame(X, columns=list("abcde"))
    prep, y, folds = _setup(X, y, task="regression")
    events = []
    result = run_family(
        "XGBoost",
        X,
        y,
        folds,
        "regression",
        prep,
        Deadline(2),
        events.append,
        _until_trials(events, 1),
    )
    assert result.oof.shape == (500,)
    assert result.best_score < np.std(y)  # better than predicting the mean


def test_should_stop_returns_promptly_with_cancelled_event():
    X, y = _classification(2_000, 10)
    prep, y, folds = _setup(X, y)
    events = []
    start = time.monotonic()
    result = run_family(
        "LightGBM", X, y, folds, "classification", prep, Deadline(60), events.append, lambda: True
    )
    assert time.monotonic() - start < 1
    assert result.trials == 0 and result.models == []
    stopped = [e for e in events if e.type == "stopped"]
    assert stopped[0].data == {"family": "LightGBM", "reason": "cancelled"}


def test_expired_deadline_raises_no_model_error():
    X, y = _classification(200, 5)
    prep, y, folds = _setup(X, y)
    with pytest.raises(NoModelError, match="time budget too small"):
        run_family(
            "LightGBM",
            X,
            y,
            folds,
            "classification",
            prep,
            Deadline(0),
            lambda e: None,
            lambda: False,
        )


def test_time_limit_ends_search_with_time_reason():
    X, y = _classification(300, 5)
    prep, y, folds = _setup(X, y)
    events = []
    start = time.monotonic()
    result = run_family(
        "ExtraTrees",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(1.5),
        events.append,
        lambda: False,
    )
    assert time.monotonic() - start < 2.0
    assert result.trials >= 1
    assert [e.data["reason"] for e in events if e.type == "stopped"] == ["time"]


def test_max_trial_secs_truncates_trials_instead_of_discarding_them():
    X, y = _classification(20_000, 20)
    prep, y, folds = _setup(X, y)
    events = []
    run_family(
        "LightGBM",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(30),
        events.append,
        _until_trials(events, 2),
        max_trial_secs=0.5,
    )
    trials = [e for e in events if e.type == "trial"]
    assert len(trials) == 2
    assert all(e.data["elapsed"] < 1.0 for e in trials)


def test_same_seed_gives_same_best_score():
    X, y = _classification(300, 8)
    prep, y, folds = _setup(X, y)
    scores = []
    for _ in range(2):
        events = []
        result = run_family(
            "LightGBM",
            X,
            y,
            folds,
            "classification",
            prep,
            Deadline(60),
            events.append,
            _until_trials(events, 3),
            seed=7,
        )
        scores.append(result.best_score)
    assert scores[0] == pytest.approx(scores[1], abs=1e-9)


@pytest.mark.parametrize("name", list(FAMILIES))
def test_fewer_than_fifty_rows_with_five_folds(name):
    X, y = _classification(40, 4)
    prep, y, folds = _setup(X, y)
    assert len(folds) == 5
    events = []
    result = run_family(
        name,
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(30),
        events.append,
        _until_trials(events, 1),
    )
    assert result.trials == 1 and len(result.models) == 5


def test_thirty_rows_with_small_class_reduces_folds_and_trains():
    X, _ = _classification(30, 4)
    events = []
    y, _, nfolds = validate_target(
        pd.Series(["a"] * 27 + ["b"] * 3), "classification", 5, emit=events.append
    )
    assert events[0].data["nfolds_reduced_to"] == nfolds == 3
    folds = make_folds(y, "classification", nfolds, 0)
    result = run_family(
        "LightGBM",
        X,
        y,
        folds,
        "classification",
        Prep().fit(X),
        Deadline(30),
        events.append,
        _until_trials(events, 1),
    )
    assert len(result.models) == 3


@pytest.mark.parametrize("name", list(FAMILIES))
def test_awkward_feature_columns_train_with_every_family(name):
    rng = np.random.default_rng(0)
    n = 6_000
    X = pd.DataFrame(
        {
            "num": rng.normal(size=n),
            "empty": np.full(n, np.nan),
            "const": np.ones(n),
            "ids": [f"user-{i % 5000}" for i in range(n)],
            "pref": rng.choice(["東京", "大阪", "名古屋"], n),
            "when": pd.date_range("2020-01-01", periods=n, freq="D"),
        }
    )
    y = (X["num"] + (X["pref"] == "東京") > 0.5).to_numpy().astype(int)
    prep, y, folds = _setup(X, y, nfolds=3)
    events = []
    result = run_family(
        name,
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(30),
        events.append,
        _until_trials(events, 1),
    )
    assert result.trials == 1
    assert result.best_score < 0.6  # learns something (chance is ~0.69)


# --- time budget (wall clock) -------------------------------------------------------


@pytest.mark.timing
def test_all_families_finish_within_a_ten_second_budget():
    start = time.monotonic()
    budget = Deadline(10)
    X, y = _classification(50_000, 30)
    prep, y, folds = _setup(X, y)
    names = list(FAMILIES)
    for i, name in enumerate(names):
        share = budget.child(budget.remaining() / (len(names) - i))
        try:
            run_family(
                name, X, y, folds, "classification", prep, share, lambda e: None, lambda: False
            )
        except NoModelError:
            pass
    assert time.monotonic() - start <= 10.5


@pytest.mark.timing
@pytest.mark.parametrize("name", list(FAMILIES))
def test_two_second_budget_returns_or_raises_without_hanging(name):
    X, y = _classification(50_000, 30)
    prep, y, folds = _setup(X, y)
    start = time.monotonic()
    try:
        result = run_family(
            name, X, y, folds, "classification", prep, Deadline(2), lambda e: None, lambda: False
        )
    except NoModelError:
        pass
    else:
        assert result.trials >= 1 and len(result.models) == len(folds)
    assert time.monotonic() - start <= 2.5


@pytest.mark.timing
def test_small_data_completes_many_lightgbm_trials():
    X, y = _titanic_like()
    prep, y, folds = _setup(X, y)
    events = []
    start = time.monotonic()
    result = run_family(
        "LightGBM",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(20),
        events.append,
        _until_trials(events, 3),
    )
    assert result.trials >= 3
    assert time.monotonic() - start < 20
