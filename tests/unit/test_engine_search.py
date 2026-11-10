import json
import pickle
import time

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification, make_regression

from fione.engine import search
from fione.engine.config import ConfigError, Deadline, DeadlineExceeded, NoModelError
from fione.engine.families import (
    FAMILIES,
    MAX_ROUNDS,
    UNIT_SAFETY,
    FamilySpec,
    Forest,
    n_threads,
)
from fione.engine.prep import Prep, validate_target
from fione.engine.search import (
    CAP_MARGIN,
    STARTUP_TRIALS,
    make_folds,
    repeat_folds,
    repeats_for,
    run_family,
    score,
)

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


class _ConstantModel:
    classes_ = np.array([0, 1])

    def predict_proba(self, X):
        return np.full((len(X), 2), 0.5)


class _SlowFamily(FamilySpec):
    """Every fit spends ``unit`` seconds before it first consults its deadline."""

    name = "Slow"
    view = "dense"
    defaults = {}
    unit = 0.2
    starts: list[float] = []

    def space(self, trial):
        return {}

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        self.starts.append(time.monotonic())
        time.sleep(self.unit)
        deadline.expired()
        return _ConstantModel()


class _BoostingFamily(_SlowFamily):
    """After its first ``unit``, iterates until its deadline, then spends ``over`` seconds
    finishing: it overruns its time share a little, as real boosting does."""

    name = "Boosting"
    unit = 0.05
    over = 0.03

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        time.sleep(self.unit)
        while not deadline.expired():
            time.sleep(0.005)
        time.sleep(self.over)
        return _ConstantModel()


@pytest.fixture
def slow(monkeypatch):
    monkeypatch.setitem(FAMILIES, "Slow", _SlowFamily)
    monkeypatch.setattr(_SlowFamily, "starts", [])
    return _SlowFamily


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


def _calibrated(spec, X_tr, y_tr) -> tuple[float, float]:
    """A short deadline this machine can meet, and the overrun allowed past it.

    ``fit`` refuses to start (``DeadlineExceeded``) when less than ``UNIT_SAFETY`` times the
    family's first, uninterruptible unit remains, and that unit is probed on this machine. On a
    fast machine this is a 0.5 s budget with 2 s slack (a busy machine stalls a fit for
    a second or more); on a slow or busy one both grow with the measured unit, so the test still
    proves "stops near the deadline with a usable model" without depending on the hardware.
    """
    spec.estimate_unit(spec.defaults, X_tr, y_tr)  # the probe fit() would run first
    unit = spec.unit_secs or 0.0
    return max(0.5, 3 * UNIT_SAFETY * unit), max(2.0, 4 * unit)


@pytest.mark.parametrize("name", list(FAMILIES))
def test_fit_stops_at_deadline_with_usable_model(name):
    X, y = _classification(50_000, 30)
    prep, y, _ = _setup(X, y)
    spec = FAMILIES[name]("classification", 2, n_jobs=n_threads(len(X)))
    view = getattr(prep, spec.view)(X)
    budget, slack = _calibrated(spec, view.iloc[:40_000], y[:40_000])
    start = time.monotonic()
    model = spec.fit(
        spec.defaults,
        view.iloc[:40_000],
        y[:40_000],
        view.iloc[40_000:],
        y[40_000:],
        Deadline(budget),
    )
    assert time.monotonic() - start < budget + slack
    proba = spec.predict(model, view.iloc[40_000:])
    assert proba.shape == (10_000, 2)
    assert np.allclose(proba.sum(axis=1), 1)


def test_fit_refuses_to_start_a_unit_that_cannot_finish(slow):
    spec = slow("classification", 2)
    X = pd.DataFrame({"a": range(20)})
    y = np.array([0, 1] * 10)
    spec.fit({}, X, y, X, y, Deadline(5))
    assert spec.unit_secs == pytest.approx(slow.unit, abs=0.05)
    with pytest.raises(DeadlineExceeded):
        spec.fit({}, X, y, X, y, Deadline(UNIT_SAFETY * slow.unit * 0.9))
    assert len(slow.starts) == 1


@pytest.mark.parametrize("name", list(FAMILIES))
def test_fit_full_trains_the_requested_rounds_on_all_rows(name):
    X, y = _classification(1_000, 6)
    prep, y, _ = _setup(X, y)
    spec = FAMILIES[name]("classification", 2)
    view = getattr(prep, spec.view)(X)
    model = spec.fit_full(spec.defaults, view, y, Deadline(30), rounds=7)
    one_step = {name: 1 for name in FAMILIES if "Linear" in name}  # fitted in one go: no rounds
    full = Forest.n_trees if issubclass(FAMILIES[name], Forest) else 7
    assert spec.rounds(model) == one_step.get(name, full)
    assert spec.predict(model, view).shape == (1_000, 2)
    assert spec.size_bytes(model) > 0
    importance = spec.importance(model)
    assert importance.shape == (6,) and (importance >= 0).all() and importance.sum() > 0


# The linear families are excluded: one fit takes far less than the shortest calibrated budget,
# so it finishes.
@pytest.mark.parametrize("name", [name for name in FAMILIES if "Linear" not in name])
def test_fit_full_raises_when_it_cannot_finish(name):
    X, y = _classification(50_000, 30)
    prep, y, _ = _setup(X, y)
    spec = FAMILIES[name]("classification", 2, n_jobs=n_threads(len(X)))
    view = getattr(prep, spec.view)(X)
    _, slack = _calibrated(spec, view, y)
    # A fixed short budget, not one that grows with the probed unit: a probe that a busy machine
    # slowed down would give a budget longer than a whole ExtraTrees fit (1 s on this data), and
    # the fit would finish. Without the probed unit ``fit_full`` does not refuse to start, so the
    # fit always runs its first unit and is stopped short by the deadline. The time is a loose
    # check; run to the end, the families here take 7 s (XGBoost) to 5 minutes (DeepLearning).
    budget = 0.3
    spec.unit_secs = None
    start = time.monotonic()
    with pytest.raises(DeadlineExceeded):
        spec.fit_full(spec.defaults, view, y, Deadline(budget), rounds=MAX_ROUNDS)
    assert time.monotonic() - start < budget + slack


def test_fit_full_refuses_when_the_scaled_unit_does_not_fit(slow):
    spec = slow("classification", 2)
    X = pd.DataFrame({"a": range(20)})
    y = np.array([0, 1] * 10)
    spec.fit({}, X.iloc[:10], y[:10], X, y, Deadline(5))  # unit measured on 10 rows
    with pytest.raises(DeadlineExceeded):  # 20 rows: a bigger unit than 1.2 x 0.2 s
        spec.fit_full({}, X, y, Deadline(UNIT_SAFETY * slow.unit * 1.05), rounds=1)
    assert len(slow.starts) == 1


def test_rounds_counts_the_iterations_used_for_prediction():
    X, y = _classification(2_000, 6)
    prep, y, folds = _setup(X, y)
    train, valid = folds[0]
    view = prep.tree(X)
    for name in ("LightGBM", "XGBoost"):
        spec = FAMILIES[name]("classification", 2)
        model = spec.fit(
            spec.defaults, view.iloc[train], y[train], view.iloc[valid], y[valid], Deadline(30)
        )
        assert 1 <= spec.rounds(model) < MAX_ROUNDS


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
    for e in events:
        json.dumps(e.data, allow_nan=False)


@pytest.mark.parametrize("name", list(FAMILIES))
def test_classification_oof_holds_probabilities_and_models_pickle(name, tmp_path):
    X, y = _classification(300, 5)
    prep, y, folds = _setup(X, y)
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
    assert result.oof.shape == (300, 2)
    assert np.allclose(result.oof.sum(axis=1), 1)
    assert len(result.models) == len(folds)
    joblib.dump(result.models, tmp_path / "models.joblib")
    models = joblib.load(tmp_path / "models.joblib")  # a file this test wrote itself
    spec = FAMILIES[name]("classification", 2)
    view = getattr(prep, spec.view)(X)
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
        Deadline(30),
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


def test_cancelling_mid_trial_discards_it_and_returns_promptly():
    X, y = _classification(50_000, 30)
    prep, y, folds = _setup(X, y)
    probe = FAMILIES["LightGBM"]("classification", 2, n_jobs=n_threads(len(X)))
    _, slack = _calibrated(probe, getattr(prep, probe.view)(X).iloc[:40_000], y[:40_000])
    events = []
    start = time.monotonic()
    result = run_family(
        "LightGBM",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(60),
        events.append,
        lambda: time.monotonic() - start > 0.3,
    )
    assert time.monotonic() - start < 0.5 + slack  # the cancel, then at most a unit
    assert result.trials == 0 and result.models == []
    assert [e.data["reason"] for e in events if e.type == "stopped"] == ["cancelled"]


def test_later_trials_never_start_a_fit_that_would_straddle_the_deadline(slow):
    X, y = _classification(40, 4)
    prep, y, folds = _setup(X, y, nfolds=2)
    budget = 1.5
    start = time.monotonic()
    run_family(
        "Slow", X, y, folds, "classification", prep, Deadline(budget), lambda e: None, lambda: False
    )
    elapsed = time.monotonic() - start
    assert len(slow.starts) >= 4  # several trials ran
    assert all(start + budget - t >= UNIT_SAFETY * slow.unit for t in slow.starts)
    assert elapsed <= budget


def test_a_first_trial_with_its_own_deadline_is_finished_and_the_search_then_ends(
    slow, monkeypatch
):
    monkeypatch.setattr(slow, "unit", 0.1)
    X, y = _classification(50, 4)
    prep, y, folds = _setup(X, y)
    events = []

    def run(first_deadline):
        return run_family(
            "Slow",
            X,
            y,
            folds,
            "classification",
            prep,
            Deadline(0.3),  # five folds of 0.1 s cannot fit in this
            events.append,
            lambda: False,
            first_deadline=first_deadline,
        )

    with pytest.raises(NoModelError):
        run(None)
    start = time.monotonic()
    result = run(Deadline(10))
    # The first trial ran to its end, past the family's deadline, and no other was started.
    assert result.trials == 1 and result.reason == "time"
    assert 0.45 <= time.monotonic() - start < 3
    assert len(result.models) == len(folds)


def test_trials_after_the_first_stay_within_the_family_deadline(slow, monkeypatch):
    monkeypatch.setattr(slow, "unit", 0.1)
    X, y = _classification(50, 4)
    prep, y, folds = _setup(X, y)
    start = time.monotonic()
    result = run_family(
        "Slow",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(1.8),  # a trial takes 0.5 s: room for three
        lambda e: None,
        lambda: False,
        first_deadline=Deadline(30),
    )
    # With the first deadline used throughout, the search would run for many seconds.
    assert result.trials >= 2 and result.reason == "time"
    assert time.monotonic() - start < 3.2


def test_first_trial_gives_up_as_soon_as_its_folds_cannot_fit(slow, monkeypatch):
    monkeypatch.setattr(slow, "unit", 0.3)
    X, y = _classification(50, 4)
    prep, y, folds = _setup(X, y)
    start = time.monotonic()
    with pytest.raises(NoModelError) as caught:  # 5 folds x 0.3 s cannot fit in 1 s
        run_family(
            "Slow", X, y, folds, "classification", prep, Deadline(1), lambda e: None, lambda: False
        )
    assert time.monotonic() - start < 0.5
    assert len(slow.starts) == 1
    # The error says what the folds needed: a unit each, with the safety margin.
    assert caught.value.needed_secs == pytest.approx(len(folds) * UNIT_SAFETY * 0.3, rel=0.2)


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
        first_deadline=Deadline(60),  # a busy machine still finishes the first trial
    )
    assert result.trials >= 1
    assert [e.data["reason"] for e in events if e.type == "stopped"] == ["time"]
    # The search ends within the deadline plus the trial that was running when it passed.
    longest = max(row["elapsed"] for row in result.log)
    assert time.monotonic() - start < 1.5 + max(0.5, 3 * longest)


def _cap_limit(events, folds, result, max_trial_secs):
    """The largest per-trial cap the search applied. The single notice reports the cap when it
    was first raised, but the cap keeps rising as the measured unit time does."""
    noticed = max([e.data["max_trial_secs"] for e in events if e.type == "notice"], default=0)
    final = CAP_MARGIN * len(folds) * UNIT_SAFETY * (result.spec.unit_secs or 0)
    return max(max_trial_secs, noticed, final)


def test_max_trial_secs_truncates_trials_instead_of_discarding_them():
    X, y = _classification(20_000, 20)
    prep, y, folds = _setup(X, y)
    # On a busy machine a fold can take longer than the probed unit allows for, and the trial is
    # dropped: the cap grows with the unit measured here, and stays 0.5 s on a quiet one.
    probe = FAMILIES["LightGBM"]("classification", 2, n_jobs=n_threads(len(X)))
    train = folds[0][0]
    probe.estimate_unit(probe.defaults, getattr(prep, probe.view)(X).iloc[train], y[train])
    cap = max(0.5, 15 * (probe.unit_secs or 0.0))
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
        _until_trials(events, 2),
        max_trial_secs=cap,
    )
    trials = [e for e in events if e.type == "trial"]
    assert len(trials) == 2
    limit = _cap_limit(events, folds, result, cap)
    assert all(e.data["elapsed"] < limit + max(0.5, limit / 2) for e in trials)


def test_a_capped_trial_keeps_its_last_fold_when_earlier_folds_overran(monkeypatch):
    """Each fold runs until its share ends and overruns it by part of a round; under a tight
    cap the last fold's share fell below the unit it needs and the whole trial was dropped."""
    monkeypatch.setitem(FAMILIES, "Boosting", _BoostingFamily)
    X, y = _classification(100, 4)
    prep, y, folds = _setup(X, y)
    events = []
    result = run_family(
        "Boosting",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(30),
        events.append,
        _until_trials(events, 2),
        max_trial_secs=0.1,
    )
    trials = [e for e in events if e.type == "trial"]
    assert [e.data["state"] for e in trials] == ["complete", "complete"]
    limit = _cap_limit(events, folds, result, 0.1)
    assert all(e.data["elapsed"] < 2 * limit for e in trials)


def test_max_trials_stops_the_search():
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
        lambda: False,
        max_trials=2,
    )
    assert result.trials == 2 and result.reason == "max_models"
    assert [e.data["reason"] for e in events if e.type == "stopped"] == ["max_models"]
    assert [t["trial"] for t in result.log] == [0, 1]


def test_stagnation_stops_the_search_with_no_improvement():
    X, y = _classification(300, 5)
    prep, y, folds = _setup(X, y)
    seen = []
    result = run_family(
        "LightGBM",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(600),
        lambda e: None,
        lambda: False,
        stopping_rounds=2,
        stopping_tolerance=0.9,
        stopping_score=lambda oof: seen.append(oof.shape) or 1.0,
    )
    # The random startup trials do not count towards the 2 stagnant ones.
    assert result.trials == STARTUP_TRIALS + 3 and result.reason == "no_improvement"
    complete = sum(row["state"] == "complete" for row in result.log)  # a pruned trial has no OOF
    assert seen == [(300, 2)] * complete  # the stopping metric sees each complete trial's OOF


def test_sample_weight_reaches_every_fold_fit(slow, monkeypatch):
    received = []
    original = slow._fit

    def spy(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        received.append((len(X_tr), sample_weight))
        return original(self, params, X_tr, y_tr, X_va, y_va, deadline)

    monkeypatch.setattr(slow, "_fit", spy)
    monkeypatch.setattr(slow, "unit", 0.0)
    X, y = _classification(40, 4)
    prep, y, folds = _setup(X, y, nfolds=2)
    weights = np.arange(40, dtype=float)
    run_family(
        "Slow",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(30),
        lambda e: None,
        lambda: False,
        max_trials=1,
        sample_weight=weights,
    )
    assert [(n, list(w)) for n, w in received] == [
        (len(train), list(weights[train])) for train, _ in folds
    ]


def test_max_trial_secs_is_raised_to_fit_a_unit_per_fold(slow):
    X, y = _classification(40, 4)
    prep, y, folds = _setup(X, y, nfolds=2)
    events = []
    result = run_family(
        "Slow",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(30),
        events.append,
        lambda: False,
        max_trial_secs=0.1,
        max_trials=3,
    )
    assert result.trials == 3  # no trial was refused or discarded
    notices = [e.data for e in events if e.type == "notice"]
    assert len(notices) == 1 and notices[0]["family"] == "Slow"
    assert notices[0]["max_trial_secs"] >= len(folds) * UNIT_SAFETY * slow.unit


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


@pytest.fixture(scope="module")
def wide():
    """400k rows x 102 features (two categoricals) with a binary and a 30-class target."""
    rng = np.random.default_rng(0)
    n = 400_000
    X = pd.DataFrame(rng.normal(size=(n, 100)), columns=[f"c{i}" for i in range(100)])
    X["cat1"] = rng.choice([f"a{i}" for i in range(50)], n)
    X["cat2"] = rng.choice([f"b{i}" for i in range(150)], n)
    signal = X.iloc[:, :10].sum(axis=1).to_numpy() + rng.normal(size=n)
    binary = (signal > 0).astype(np.int64)
    classes = np.searchsorted(np.quantile(signal, np.linspace(0, 1, 31)[1:-1]), signal)
    return X, Prep().fit(X), binary, classes


def _returns_or_raises_within(name, X, y, prep, budget, slack):
    folds = make_folds(y, "classification", 5, 0)
    start = time.monotonic()
    try:
        result = run_family(
            name,
            X,
            y,
            folds,
            "classification",
            prep,
            Deadline(budget),
            lambda e: None,
            lambda: False,
        )
    except NoModelError:
        pass
    else:
        assert result.trials >= 1 and len(result.models) == len(folds)
    assert time.monotonic() - start <= budget + slack


@pytest.mark.timing
@pytest.mark.parametrize("name", list(FAMILIES))
def test_wide_data_does_not_blow_a_two_second_budget(wide, name):
    X, prep, binary, _ = wide
    _returns_or_raises_within(name, X, binary, prep, budget=2, slack=1.0)


@pytest.mark.timing
def test_wide_thirty_class_catboost_does_not_blow_a_two_second_budget(wide):
    X, prep, _, classes = wide
    _returns_or_raises_within("CatBoost", X, classes, prep, budget=2, slack=1.5)


def test_deep_learning_stops_after_patience_and_never_looks_at_the_validation_rows():
    X, y = _classification(600, 6)
    prep, y, _ = _setup(X, y)
    spec = FAMILIES["DeepLearning"]("classification", 2)
    view = prep.linear(X)
    # Large, barely regularised networks overfit 400 noisy rows quickly: the loss turns up and
    # the fit ends long before ``max_epochs``.
    params = {"width": 256, "alpha": 1e-6, "learning_rate_init": 1e-2}
    train, valid = view.iloc[:400], view.iloc[400:]
    model = spec.fit(params, train, y[:400], valid, y[400:], Deadline(30))
    assert 1 <= spec.rounds(model) < spec.max_epochs - spec.patience
    assert spec.predict(model, view).shape == (600, 2)
    # The epoch is chosen on rows set aside from the training fold: other validation labels
    # (or rows) change nothing, or the trial's score would flatter the network.
    other = spec.fit(params, train, y[:400], valid, 1 - y[400:], Deadline(30))
    assert spec.rounds(other) == spec.rounds(model)
    for a, b in zip(model.coefs_, other.coefs_, strict=True):
        np.testing.assert_array_equal(a, b)


def test_deep_learning_regression_learns_targets_of_any_scale():
    X, y = make_regression(400, 5, noise=0.1, random_state=0)
    X = pd.DataFrame(X, columns=[f"x{i}" for i in range(5)])
    errors = []
    for scale in (1.0, 1e5):
        prep, target, _ = _setup(X, y * scale + 3e5 * scale, "regression")
        spec = FAMILIES["DeepLearning"]("regression", 0)
        view = prep.linear(X)
        model = spec.fit(
            spec.defaults,
            view.iloc[:300],
            target[:300],
            view.iloc[300:],
            target[300:],
            Deadline(30),
        )
        errors.append(
            np.sqrt(np.mean((spec.predict(model, view.iloc[300:]) - target[300:]) ** 2)) / scale
        )
    assert errors[1] == pytest.approx(errors[0], rel=0.05)  # the same fit in other units


def test_deep_learning_stops_at_the_deadline_after_one_epoch():
    X, y = _classification(600, 6)
    prep, y, _ = _setup(X, y)
    spec = FAMILIES["DeepLearning"]("classification", 2)
    view = prep.linear(X)
    expired = Deadline(0)
    model = spec._fit(spec.defaults, view, y, view, y, expired)
    assert spec.rounds(model) == 1


def test_linear_regression_and_classification_fit():
    for task in ("regression", "classification"):
        X, y = (
            make_regression(300, 5, noise=0.1, random_state=0)
            if task == "regression"
            else make_classification(300, 5, random_state=0)
        )
        X = pd.DataFrame(X, columns=[f"x{i}" for i in range(5)])
        prep, y, _ = _setup(X, y, task)
        n_classes = 2 if task == "classification" else 0
        spec = FAMILIES["Linear"](task, n_classes)
        view = prep.linear(X)
        model = spec.fit(spec.defaults, view, y, view, y, Deadline(30))
        assert spec.predict(model, view).shape == ((300, 2) if n_classes else (300,))
        assert spec.importance(model).shape == (5,)


def test_deep_learning_size_estimate_matches_its_pickle():
    X, y = _classification(600, 6)
    prep, y, _ = _setup(X, y)
    spec = FAMILIES["DeepLearning"]("classification", 2)
    view = prep.linear(X)
    model = spec.fit(
        spec.defaults, view.iloc[:400], y[:400], view.iloc[400:], y[400:], Deadline(30)
    )
    # The optimiser's moments and the best weights are training state: they must not be kept.
    assert len(pickle.dumps(model)) < 1.3 * spec.size_bytes(model)


def _search_with_runners_up():
    X, y = _classification(300, 5)
    prep, y, folds = _setup(X, y)
    events = []
    result = run_family(
        "LightGBM", X, y, folds, "classification", prep, Deadline(60), events.append,
        _until_trials(events, 6),
    )  # fmt: skip
    return result, y, events


def test_the_best_trials_are_handed_on_best_first(monkeypatch):
    monkeypatch.setattr(search, "TOP_TRIALS", 3)
    result, y, events = _search_with_runners_up()
    assert len(result.runners_up) == 2
    ranked = [result, *result.runners_up]
    scores = [r.best_score for r in ranked]
    assert scores == sorted(scores)
    assert len({r.best_trial for r in ranked}) == 3  # three different trials
    done = {e.data["trial"]: e.data["score"] for e in events if e.data.get("state") == "complete"}
    assert scores == pytest.approx(sorted(done.values())[:3])
    for r in ranked:
        assert r.spec is result.spec and len(r.models) == 5 and r.oof.shape == (300, 2)
        assert r.best_score == pytest.approx(done[r.best_trial])
    assert result.runners_up[0].best_params != result.best_params


def test_one_top_trial_hands_on_no_runners_up(monkeypatch):
    monkeypatch.setattr(search, "TOP_TRIALS", 1)
    result, _, _ = _search_with_runners_up()
    assert result.runners_up == []


def _group_ids(n, groups, seed=0):
    return np.random.default_rng(seed).integers(0, groups, n)


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_group_folds_never_split_a_group_and_cover_every_row(task):
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 300) if task == "classification" else rng.normal(size=300)
    groups = _group_ids(300, 40)
    folds = make_folds(y, task, 5, 0, groups)
    assert len(folds) == 5
    valid_rows = np.concatenate([valid for _, valid in folds])
    assert sorted(valid_rows) == list(range(300))
    for train, valid in folds:
        assert not set(groups[train]) & set(groups[valid])


def test_group_folds_are_deterministic_and_follow_the_seed():
    y = np.random.default_rng(1).integers(0, 2, 300)
    groups = _group_ids(300, 40)
    first = make_folds(y, "classification", 5, 0, groups)
    again = make_folds(y, "classification", 5, 0, groups)
    other = make_folds(y, "classification", 5, 1, groups)
    assert all(np.array_equal(a[1], b[1]) for a, b in zip(first, again, strict=True))
    assert any(not np.array_equal(a[1], b[1]) for a, b in zip(first, other, strict=True))


@pytest.mark.parametrize(
    ("rows", "repeats"), [(10, 3), (2_000, 3), (2_001, 2), (5_000, 2), (5_001, 1), (1_000_000, 1)]
)
def test_the_folds_are_repeated_for_few_rows(rows, repeats):
    assert repeats_for(rows) == repeats


def test_repeated_folds_are_runs_of_other_partitions():
    y = np.random.default_rng(1).integers(0, 2, 200)
    folds = repeat_folds(y, "classification", 4, 3, repeats=3)
    assert len(folds) == 12
    first = make_folds(y, "classification", 4, 3)
    assert all(np.array_equal(a[1], b[1]) for a, b in zip(folds[:4], first, strict=True))
    runs = [folds[i * 4 : (i + 1) * 4] for i in range(3)]
    for run in runs:
        assert sorted(np.concatenate([valid for _, valid in run])) == list(range(200))
    assert not np.array_equal(runs[0][0][1], runs[1][0][1])


def test_repeated_group_folds_keep_each_group_together_in_every_run():
    y = np.random.default_rng(1).integers(0, 2, 300)
    groups = _group_ids(300, 40)
    for train, valid in repeat_folds(y, "classification", 5, 0, groups, 2):
        assert not set(groups[train]) & set(groups[valid])


def test_a_repeated_search_scores_each_repeat_alone_and_keeps_the_first_runs_models():
    X, y = _classification(300, 6)
    prep = Prep().fit(X)
    folds = repeat_folds(y, "classification", 3, 0, repeats=3)
    result = run_family(
        "LightGBM",
        X,
        y,
        folds,
        "classification",
        prep,
        Deadline(30),
        lambda event: None,
        lambda: False,
        max_trials=2,
        repeats=3,
    )
    assert len(result.models) == 3 and result.repeats == 3 and len(result.oofs) == 3
    assert result.oof is result.oofs[0]
    assert result.stacked(np.arange(len(y))).shape == (3 * len(y), 2)
    assert result.stacked(np.arange(10)).shape == (30, 2)
    mean = np.mean([score("classification", y, oof) for oof in result.oofs])
    assert result.best_score == pytest.approx(mean)
    assert not np.allclose(result.oofs[0], result.oofs[1])  # other splits, other predictions


def test_one_repeat_is_the_plain_search():
    X, y = _classification(300, 6)
    prep = Prep().fit(X)
    result = run_family(
        "LightGBM",
        X,
        y,
        make_folds(y, "classification", 3, 0),
        "classification",
        prep,
        Deadline(30),
        lambda event: None,
        lambda: False,
        max_trials=1,
    )
    assert result.repeats == 1 and result.oofs == []
    assert np.array_equal(result.stacked(np.arange(10)), result.oof[:10])


def test_time_folds_learn_only_from_earlier_rows():
    order = np.repeat(np.arange(60), 5)[np.random.default_rng(0).permutation(300)]
    y = np.zeros(300)
    folds = search.make_time_folds(order, y, "regression", 4)
    assert len(folds) == 4
    for train, valid in folds:
        assert order[train].max() < order[valid].min()  # nothing is learned from a later row
        assert len(np.intersect1d(train, valid)) == 0
    # the folds go forward, and the first part is never predicted
    firsts = [order[valid].min() for _, valid in folds]
    assert firsts == sorted(firsts)
    seen = search.covered(folds, 300)
    assert len(seen) == 240 and order[seen].min() == 12


def test_time_folds_keep_rows_of_one_moment_together_and_need_two_parts():
    order = np.array([1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
    folds = search.make_time_folds(order, np.zeros(10), "regression", 5)
    assert len(folds) == 1  # two moments: one learned from, one predicted
    assert set(order[folds[0][0]]) == {1} and set(order[folds[0][1]]) == {2}
    with pytest.raises(ConfigError, match="too few different values"):
        search.make_time_folds(np.ones(10, dtype=int), np.zeros(10), "regression", 3)


def test_time_folds_of_a_classification_refuse_a_class_that_comes_late():
    order = np.arange(40)
    y = np.array([0] * 30 + [1] * 10)  # the class 1 first appears after the early parts
    with pytest.raises(ConfigError, match="a class has no row"):
        search.make_time_folds(order, y, "classification", 4)
    ok = np.arange(40) % 2
    assert len(search.make_time_folds(order, ok, "classification", 4)) == 4


def test_time_folds_refuse_later_parts_with_a_single_class():
    order = np.arange(60)
    y = np.array([0, 1] * 10 + [0] * 40)  # both classes early, only one in the parts to predict
    with pytest.raises(ConfigError, match="single class"):
        search.make_time_folds(order, y, "classification", 2)
