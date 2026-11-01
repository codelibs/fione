import json
import time

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import load_breast_cancer, load_iris, make_classification, make_friedman1
from sklearn.metrics import r2_score, roc_auc_score
from sklearn.model_selection import train_test_split

from fione.engine import automl as automl_module
from fione.engine import search
from fione.engine.automl import FAMILY_ORDER, AutoML
from fione.engine.config import ConfigError, DeadlineExceeded, NoModelError, TrainConfig
from fione.engine.families import FAMILIES, ExtraTrees, FamilySpec, LightGBM, XGBoost
from fione.engine.search import STARTUP_TRIALS

LEADERBOARD_COLUMNS = ["model", "family", "cv_score", "cv_std", "train_secs", "weight"]
HIGHER_IS_BETTER = {"auc", "accuracy", "r2"}


def _fit(df, events=None, families=None, should_stop=None, **config):
    config.setdefault("max_runtime_secs", 60)
    sink = events.append if events is not None else (lambda e: None)
    kwargs = {} if should_stop is None else {"should_stop": should_stop}
    return AutoML(TrainConfig(**config), sink, families=families, **kwargs).fit(df)


def _binary(n=600, seed=0, **kwargs):
    X, y = make_classification(n, 8, n_informative=5, random_state=seed, **kwargs)
    df = pd.DataFrame(X, columns=[f"x{i}" for i in range(8)])
    df["y"] = y
    return df


def _mixed(n=3_000, seed=0):
    """Numeric, low-cardinality, high-cardinality (frequency encoded) and datetime features."""
    rng = np.random.default_rng(seed)
    when = pd.Timestamp("2020-01-01") + pd.to_timedelta(rng.integers(0, 1_000, n), unit="D")
    df = pd.DataFrame(
        {
            "x": rng.normal(size=n),
            "color": rng.choice(["red", "green", "blue"], n),
            "ids": [f"id{v}" for v in rng.integers(0, 400, n)],
            "when": when,
        }
    )
    signal = df["x"] + (df["color"] == "red") + (df["when"].dt.month >= 7)
    df["label"] = np.where(signal + rng.normal(scale=0.5, size=n) > 1, "yes", "no")
    return df


# --- shared fits ----------------------------------------------------------------


@pytest.fixture(scope="module")
def iris():
    df = load_iris(as_frame=True).frame
    df["target"] = pd.Categorical.from_codes(df["target"], ["setosa", "versicolor", "virginica"])
    df["target"] = df["target"].astype(str)
    df["row_id"] = np.arange(len(df))
    train, test = train_test_split(df, test_size=0.3, stratify=df["target"], random_state=0)
    events = []
    model = _fit(
        train, events, target="target", max_models=len(FAMILY_ORDER), ignored_columns=["row_id"]
    )
    return model, train, test, events


@pytest.fixture(scope="module")
def mixed():
    df = _mixed()
    train, test = df.iloc[:2_500], df.iloc[2_500:]
    return _fit(train, target="label", max_models=4, max_runtime_secs=30), test


def test_iris_holdout_accuracy(iris):
    model, _, test, _ = iris
    pred = model.predict(test)
    assert (pred == test["target"]).mean() >= 0.9
    assert pred.index.equals(test.index)


def test_breast_cancer_holdout_auc():
    df = load_breast_cancer(as_frame=True).frame
    train, test = train_test_split(df, test_size=0.3, stratify=df["target"], random_state=0)
    model = _fit(train, target="target", max_models=4)
    proba = model.predict_proba(test)
    assert roc_auc_score(test["target"], proba[1]) >= 0.95
    assert set(model.metrics) == {"logloss", "accuracy", "auc"}


def test_friedman_regression_returns_floats_on_the_input_index():
    X, y = make_friedman1(3_000, noise=1.0, random_state=0)
    df = pd.DataFrame(X, columns=[f"x{i}" for i in range(10)])
    df["y"] = y
    df.index = np.arange(len(df))[::-1] * 3  # not a default RangeIndex
    train, test = df.iloc[:2_400], df.iloc[2_400:]
    model = _fit(train, target="y", max_models=4, max_runtime_secs=30)
    assert model.task == "regression" and model.classes_ is None
    pred = model.predict(test)
    assert pred.dtype == np.float64 and pred.index.equals(test.index)
    assert r2_score(test["y"], pred) >= 0.8
    assert set(model.metrics) == {"rmse", "mae", "r2"}
    with pytest.raises(ConfigError):
        model.predict_proba(test)


# --- the model's contents ---------------------------------------------------------


def test_classification_labels_keep_their_values(iris):
    model, _, test, _ = iris
    assert model.classes_ == ["setosa", "versicolor", "virginica"]
    proba = model.predict_proba(test)
    assert list(proba.columns) == model.classes_
    assert np.allclose(proba.sum(axis=1), 1)
    assert proba.index.equals(test.index)
    assert set(model.predict(test)) <= set(model.classes_)
    assert set(model.metrics) == {"logloss", "accuracy"}


def test_leaderboard_has_a_row_per_candidate_plus_the_ensemble(iris):
    model, _, _, _ = iris
    board = model.leaderboard
    assert list(board.columns) == LEADERBOARD_COLUMNS
    assert set(board["family"]) == {*FAMILY_ORDER, "Ensemble"}
    assert board["family"].eq("Ensemble").sum() == 1 and board["model"].is_unique
    members = board[board["family"] != "Ensemble"]
    assert members["weight"].sum() == pytest.approx(1.0)
    assert (members["weight"] >= 0).all()
    assert board.loc[board["family"] == "Ensemble", "weight"].isna().all()
    assert board["cv_score"].iloc[0] == board["cv_score"].min()  # logloss: lower is better
    assert (board["cv_std"] >= 0).all() and (board["train_secs"] > 0).all()


def test_trials_table_lists_finished_trials(iris):
    model, _, _, _ = iris
    trials = model.trials
    assert list(trials.columns) == ["family", "trial", "state", "score", "elapsed", "params"]
    assert len(trials) == len(FAMILY_ORDER)  # max_models
    assert isinstance(json.loads(trials["params"].iloc[0]), dict)


def test_every_family_is_listed_once():
    # FAMILIES, FAMILY_ORDER and FAMILY_WEIGHTS must agree.
    core = {"LightGBM", "XGBoost", "RandomForest", "ExtraTrees", "Linear", "DeepLearning"}
    assert core <= set(FAMILY_ORDER)
    assert set(FAMILY_ORDER) == set(FAMILIES) == set(automl_module.FAMILY_WEIGHTS)
    assert sum(automl_module.FAMILY_WEIGHTS.values()) == pytest.approx(1.0)


def test_ignored_columns_are_not_features(iris):
    model, _, _, _ = iris
    assert "row_id" not in model.columns and "target" not in model.columns
    assert "row_id" not in model.feature_importance.index
    assert model.target == "target" and model.config.ignored_columns == ["row_id"]


def test_refit_members_hold_one_model_per_seed_without_cv_data(iris):
    model, _, _, _ = iris
    assert model.stop_reason == "max_models"
    # A refit member is one model per seed (none for Linear: one fit gives one model); one that
    # is never refit keeps its five fold models, which share one seed.
    for member in model.members:
        spec = member.spec
        expected = (1 + automl_module.BAG_EXTRA if spec.seeded else 1) if spec.refit else 5
        assert len(member.models) == expected, spec.name
        if spec.refit and spec.seeded:
            params = [m.get_params() for m in member.models]
            seeds = {p.get("random_state", p.get("random_seed")) for p in params}  # CatBoost: seed
            assert len(seeds) == len(member.models), spec.name  # bagged, not fold models
    assert model.cv_predictions is None and model.cv_models is None
    assert model.fold_assignment is None


def test_feature_importance_sums_to_one_over_input_columns(iris):
    model, _, _, _ = iris
    importance = model.feature_importance
    assert set(importance.index) <= set(model.columns)
    assert importance.sum() == pytest.approx(1.0)
    assert (importance >= 0).all()


def test_importance_of_expanded_columns_rolls_up_to_the_source(mixed):
    model, _ = mixed
    importance = model.feature_importance
    assert set(importance.index) == {"x", "color", "ids", "when"} == set(model.columns)
    assert importance.sum() == pytest.approx(1.0)
    assert importance["when"] > 0 and importance["x"] > 0


def test_events_are_ordered_and_json_serializable(iris):
    _, train, _, events = iris
    types = [e.type for e in events]
    assert types[0] == "started" and types[-1] == "finished"
    for e in events:
        json.dumps(e.data, allow_nan=False)
    started = events[0].data
    assert started["n_rows"] == len(train) and started["n_cols"] == 4
    assert started["task"] == "classification" and started["nfolds"] == 5
    assert started["config"]["target"] == "target"
    overall = [i for i, e in enumerate(events) if e.type == "stopped" and "family" not in e.data]
    ensemble = types.index("ensemble")
    assert len(overall) == 1 and overall[0] < ensemble
    assert events[overall[0]].data["reason"] == "max_models"
    assert sum(events[ensemble].data["weights"].values()) == pytest.approx(1.0)
    assert events[ensemble].data["best_single"] in events[ensemble].data["weights"]
    finished = events[-1].data
    assert set(finished) == {"stop_reason", "elapsed", "leaderboard_top", "metrics"}
    assert len(finished["leaderboard_top"]) == 3
    assert set(finished["leaderboard_top"][0]) == set(LEADERBOARD_COLUMNS)


# --- predicting -------------------------------------------------------------------


def test_predict_tolerates_unseen_categories_and_extra_columns(mixed):
    model, test = mixed
    odd = test.drop(columns=["label"]).assign(color="purple", ids="never-seen", extra=1.0)
    pred = model.predict(odd)
    assert pred.index.equals(odd.index) and set(pred) <= {"yes", "no"}
    plain = test.drop(columns=["label"])
    assert model.predict(plain.assign(extra="x")).equals(model.predict(plain))


def test_predict_lists_every_missing_column(mixed):
    model, test = mixed
    with pytest.raises(ConfigError, match=r"missing columns: \['x', 'when'\]"):
        model.predict(test.drop(columns=["x", "when"]))


def test_model_round_trips_through_joblib(iris, tmp_path):
    model, _, test, _ = iris
    joblib.dump(model, tmp_path / "model.joblib")
    loaded = joblib.load(tmp_path / "model.joblib")  # a file this test wrote itself
    assert loaded.predict_proba(test).equals(model.predict_proba(test))
    assert loaded.leaderboard.equals(model.leaderboard)


# --- parameters -----------------------------------------------------------------


@pytest.mark.parametrize(
    "task, metric",
    [
        ("classification", "logloss"),
        ("classification", "auc"),
        ("classification", "accuracy"),
        ("regression", "rmse"),
        ("regression", "mae"),
        ("regression", "r2"),
    ],
)
def test_leaderboard_is_sorted_by_the_sort_metric(task, metric):
    df = _binary(400)
    if task == "regression":
        df["y"] = df["x0"] * 2 + df["x1"] + np.random.default_rng(0).normal(size=len(df))
    model = _fit(
        df,
        families=["LightGBM", "ExtraTrees"],
        target="y",
        task=task,
        sort_metric=metric,
        max_models=2,
    )
    scores = list(model.leaderboard["cv_score"])
    higher = metric in HIGHER_IS_BETTER
    assert scores == sorted(scores, reverse=higher)
    assert len(scores) == 3


@pytest.mark.parametrize(
    "task, field, metric",
    [
        ("classification", "sort_metric", "rmse"),
        ("regression", "sort_metric", "auc"),
        ("classification", "sort_metric", "aucpr"),
        ("regression", "stopping_metric", "logloss"),
    ],
)
def test_metric_that_does_not_fit_the_task_is_rejected(task, field, metric):
    df = _binary(200)
    with pytest.raises(ConfigError, match=field):
        _fit(df, target="y", task=task, **{field: metric})


def test_max_models_caps_the_completed_trials():
    events = []
    model = _fit(_binary(), events, target="y", max_models=2)
    assert model.stop_reason == "max_models"
    assert len(model.trials) == 2 == sum(e.type == "trial" for e in events)
    assert list(model.trials["family"]) == ["LightGBM", "CatBoost"]  # priority order


def test_no_improvement_ends_a_family_early():
    events = []
    model = _fit(
        _binary(),
        events,
        families=["LightGBM"],
        target="y",
        stopping_rounds=1,
        stopping_tolerance=0.5,  # nothing improves by half: stop after the second trial
    )
    assert model.stop_reason == "no_improvement"
    assert len(model.trials) == STARTUP_TRIALS + 2  # the random startup trials do not count
    done = [e for e in events if e.type == "stopped" and e.data.get("family") == "LightGBM"]
    assert done[0].data["reason"] == "no_improvement"


def test_balance_classes_weights_every_fit_and_lifts_minority_recall(monkeypatch):
    df = _binary(4_000, weights=[0.95], class_sep=0.6, flip_y=0.01)
    train, test = train_test_split(df, test_size=0.3, stratify=df["y"], random_state=0)
    weights = []
    original = LightGBM._fit

    def spy(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        weights.append((y_tr, sample_weight))
        return original(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight, rounds)

    monkeypatch.setattr(LightGBM, "_fit", spy)
    monkeypatch.setattr(automl_module, "BAG_EXTRA", 0)
    recall = {}
    for balance in (False, True):
        weights.clear()
        model = _fit(
            train, families=["LightGBM"], target="y", max_models=1, balance_classes=balance, seed=1
        )
        pred = model.predict(test)
        recall[balance] = (pred[test["y"] == 1] == 1).mean()
    assert recall[True] >= recall[False]
    assert len(weights) == 6  # five folds and the refit
    for y_tr, w in weights:
        assert w is not None and len(w) == len(y_tr)
        assert w[y_tr == 1].mean() > 5 * w[y_tr == 0].mean()


def test_balance_classes_is_ignored_for_regression_with_a_notice():
    df = _binary(300)
    df["y"] = df["x0"] + 0.1
    events = []
    _fit(df, events, families=["LightGBM"], target="y", max_models=1, balance_classes=True)
    notices = [e.data for e in events if e.type == "notice"]
    assert any("balance_classes" in n["message"] for n in notices)


def test_unknown_ignored_column_is_rejected():
    with pytest.raises(ConfigError, match=r"unknown columns in ignored_columns: \['nope'\]"):
        _fit(_binary(100), target="y", ignored_columns=["x0", "nope"])


def test_ignoring_the_target_is_rejected():
    with pytest.raises(ConfigError, match="target"):
        _fit(_binary(100), target="y", ignored_columns=["y"])


def test_missing_target_column_is_rejected():
    with pytest.raises(ConfigError, match="target"):
        _fit(_binary(100), target="label")


def test_unknown_family_is_rejected():
    with pytest.raises(ConfigError, match="unknown families"):
        _fit(_binary(100), families=["nope"], target="y")


def test_cv_data_is_kept_on_request():
    df = _binary(300)
    model = _fit(
        df,
        families=["LightGBM"],
        target="y",
        max_models=1,
        nfolds=3,
        keep_cv_predictions=True,
        keep_cv_models=True,
        keep_cv_fold_assignment=True,
    )
    assert model.cv_predictions.shape == (300, 2)
    assert np.allclose(model.cv_predictions.sum(axis=1), 1)
    assert sorted(set(model.fold_assignment)) == [0, 1, 2]
    assert len(model.cv_models["LightGBM"]) == 3


def test_same_seed_gives_identical_predictions():
    df = _binary(500)
    runs = [
        _fit(df, families=["LightGBM"], target="y", max_models=3, seed=3).predict_proba(df)
        for _ in range(2)
    ]
    assert runs[0].equals(runs[1])


# --- refit fallbacks --------------------------------------------------------------


def test_failed_refit_falls_back_to_the_fold_models(monkeypatch):
    def fail(self, *args, **kwargs):
        raise DeadlineExceeded

    monkeypatch.setattr(FamilySpec, "fit_full", fail)
    events = []
    df = _binary(300)
    model = _fit(df, events, families=["LightGBM"], target="y", max_models=1)
    assert len(model.members) == 1 and len(model.members[0].models) == 5
    assert any("fold models" in e.data["message"] for e in events if e.type == "notice")
    assert model.predict(df).isin([0, 1]).all()


def test_oversized_member_is_dropped_and_weights_renormalised(monkeypatch):
    monkeypatch.setattr(
        automl_module, "caruana", lambda oof, *a, **k: dict.fromkeys(oof, 1 / len(oof))
    )
    monkeypatch.setattr(ExtraTrees, "size_bytes", lambda self, model: 10**9)
    events = []
    model = _fit(
        _binary(300), events, families=["LightGBM", "ExtraTrees"], target="y", max_models=2
    )
    assert [m.spec.name for m in model.members] == ["LightGBM"]
    assert model.members[0].weight == pytest.approx(1.0)
    board = model.leaderboard.set_index("family")
    assert board.loc["ExtraTrees", "weight"] == 0 and board.loc["LightGBM", "weight"] == 1
    assert any("ExtraTrees" in e.data["message"] for e in events if e.type == "notice")


def test_members_are_dropped_lightest_first_until_they_fit_together(monkeypatch):
    weights = {"LightGBM": 0.5, "XGBoost": 0.3, "ExtraTrees": 0.2}
    monkeypatch.setattr(automl_module, "caruana", lambda oof, *a, **k: weights)
    for family in FAMILIES.values():
        monkeypatch.setattr(family, "size_bytes", lambda self, model: 35 * 1024**2)
    events = []
    model = _fit(_binary(300), events, families=list(weights), target="y", max_models=3)
    assert [m.spec.name for m in model.members] == ["LightGBM", "XGBoost"]  # 70 MB together
    assert [m.weight for m in model.members] == pytest.approx([0.625, 0.375])
    notices = [e.data["message"] for e in events if e.type == "notice"]
    assert any(n.startswith("ExtraTrees dropped") and "together" in n for n in notices)


def test_when_every_member_is_oversized_the_heaviest_is_kept(monkeypatch):
    monkeypatch.setattr(
        automl_module, "caruana", lambda oof, *a, **k: {"LightGBM": 0.4, "ExtraTrees": 0.6}
    )
    for family in FAMILIES.values():
        monkeypatch.setattr(family, "size_bytes", lambda self, model: 10**9)
    events = []
    model = _fit(
        _binary(300), events, families=["LightGBM", "ExtraTrees"], target="y", max_models=2
    )
    assert [(m.spec.name, m.weight) for m in model.members] == [("ExtraTrees", 1.0)]
    assert any("kept although" in e.data["message"] for e in events if e.type == "notice")


# --- family failures --------------------------------------------------------------


def _errors(events, kind):
    return [e.data for e in events if e.type == "notice" and e.data.get("kind") == kind]


def _boom(self, *args, **kwargs):
    raise ValueError("library failure")


def test_a_crashing_family_is_skipped_with_a_notice(monkeypatch):
    monkeypatch.setattr(XGBoost, "_fit", _boom)
    events = []
    model = _fit(_binary(300), events, target="y", max_models=4)
    assert "XGBoost" not in set(model.leaderboard["family"])
    assert {"LightGBM", "CatBoost", "ExtraTrees"} <= set(model.leaderboard["family"])
    errors = _errors(events, "family_error")
    assert errors == [
        {
            "kind": "family_error",
            "family": "XGBoost",
            "exception": "ValueError",
            "message": "library failure",
        }
    ]
    for e in events:
        json.dumps(e.data, allow_nan=False)


def test_a_crash_outside_any_trial_is_caught_per_family(monkeypatch):
    monkeypatch.setattr(XGBoost, "estimate_unit", _boom)  # runs before the first trial
    events = []
    model = _fit(_binary(300), events, target="y", max_models=4, max_runtime_secs_per_model=10)
    assert "XGBoost" not in set(model.leaderboard["family"])
    assert [e["family"] for e in _errors(events, "family_error")] == ["XGBoost"]


def test_a_crash_after_a_good_trial_keeps_that_trial(monkeypatch):
    calls = []
    original = LightGBM._fit

    def second_trial_fails(self, *args, **kwargs):
        calls.append(1)
        if len(calls) > 5:  # the first trial's five folds succeed
            raise ValueError("late failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(LightGBM, "_fit", second_trial_fails)
    monkeypatch.setattr(FamilySpec, "fit_full", _boom)  # keep the fold models to inspect
    events = []
    model = _fit(_binary(300), events, families=["LightGBM"], target="y", max_models=3)
    assert len(model.trials) == 1
    assert [len(m.models) for m in model.members] == [5]
    assert _errors(events, "family_error")[0]["message"] == "late failure"
    assert model.stop_reason not in {"no_improvement", "time"}


def test_an_errored_family_never_counts_as_stagnation(monkeypatch):
    monkeypatch.setattr(XGBoost, "_fit", _boom)
    model = _fit(
        _binary(300),
        families=["LightGBM", "XGBoost"],
        target="y",
        stopping_rounds=1,
        stopping_tolerance=0.5,  # LightGBM stagnates after two trials
    )
    assert model.stop_reason == "error"


def test_a_crashing_refit_falls_back_to_the_fold_models(monkeypatch):
    def refit_fails(self, *args, **kwargs):
        raise RuntimeError("refit failure")

    monkeypatch.setattr(FamilySpec, "fit_full", refit_fails)
    events = []
    df = _binary(300)
    model = _fit(df, events, families=["LightGBM"], target="y", max_models=1)
    assert [len(m.models) for m in model.members] == [5]
    assert _errors(events, "refit_error") == [
        {
            "kind": "refit_error",
            "family": "LightGBM",
            "exception": "RuntimeError",
            "message": "refit failure",
        }
    ]
    assert model.predict(df).isin([0, 1]).all()


def test_every_family_crashing_raises_no_model_error_with_the_cause(monkeypatch):
    monkeypatch.setattr(FamilySpec, "fit", _boom)
    with pytest.raises(NoModelError) as caught:
        _fit(_binary(300), target="y")
    assert isinstance(caught.value.__cause__, ValueError)
    for name in ("LightGBM", "CatBoost", "XGBoost", "ExtraTrees"):
        assert f"{name}: ValueError: library failure" in str(caught.value)


def test_keyboard_interrupt_is_not_swallowed(monkeypatch):
    def interrupt(self, *args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(LightGBM, "_fit", interrupt)
    with pytest.raises(KeyboardInterrupt):
        _fit(_binary(300), families=["LightGBM"], target="y")


# --- empty frames -------------------------------------------------------------------


@pytest.mark.parametrize("name", list(FAMILIES))
@pytest.mark.parametrize("task", ["classification", "regression"])
def test_predicting_no_rows_returns_empty_results_quietly(name, task, capfd):
    df = _binary(200)
    if task == "regression":
        df["y"] = df["x0"] * 2 + df["x1"]
    model = _fit(df, families=[name], target="y", task=task, max_models=1)
    capfd.readouterr()
    empty = df.drop(columns=["y"]).iloc[:0]
    pred = model.predict(empty)
    assert len(pred) == 0 and pred.index.equals(empty.index)
    if task == "classification":
        proba = model.predict_proba(empty)
        assert proba.shape == (0, 2) and list(proba.columns) == model.classes_
        assert (proba.dtypes == np.float64).all()
        assert pred.dtype == df["y"].dtype
    else:
        assert pred.dtype == np.float64
    with pytest.raises(ConfigError, match="missing columns"):
        model.predict(empty.drop(columns=["x0"]))
    assert capfd.readouterr() == ("", "")


# --- cancellation -------------------------------------------------------------------


def test_cancelling_after_the_first_family_returns_its_fold_models(monkeypatch):
    monkeypatch.setattr(search, "TOP_TRIALS", 1)
    events = []
    model = _fit(
        _binary(),
        events,
        target="y",
        should_stop=lambda: any(e.type == "family_done" for e in events),
    )
    assert model.stop_reason == "cancelled"
    assert [m.spec.name for m in model.members] == ["LightGBM"]
    assert len(model.members[0].models) == 5  # no refit
    assert events[-1].type == "finished"


def test_cancelling_before_any_trial_raises():
    start = time.monotonic()
    with pytest.raises(NoModelError, match="cancelled before any model was trained"):
        _fit(_binary(), target="y", should_stop=lambda: True)
    assert time.monotonic() - start < 2


# --- time budget, size and latency (wall clock) ------------------------------------


def _adult_like(n=36_000, seed=0):
    """14 features like the Adult census data: 6 numeric, 8 categorical."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({f"num{i}": rng.normal(size=n) * (i + 1) for i in range(6)})
    for i, k in enumerate((2, 5, 7, 9, 16, 15, 6, 41)):
        df[f"cat{i}"] = rng.choice([f"v{j}" for j in range(k)], n)
    logit = df["num0"] + 0.5 * df["num1"] - 0.3 * df["num2"] + (df["cat1"] == "v1") - 1.2
    df["income"] = np.where(rng.random(n) < 1 / (1 + np.exp(-logit)), ">50K", "<=50K")
    return df


@pytest.mark.timing
def test_adult_scale_model_is_small_and_predicts_fast(tmp_path):
    df = _adult_like()
    start = time.monotonic()
    model = _fit(df, target="income", max_runtime_secs=60)
    assert time.monotonic() - start <= 63
    path = tmp_path / "model.joblib"
    joblib.dump(model, path)
    assert path.stat().st_size <= 100 * 1024**2
    loaded = joblib.load(path)  # a file this test wrote itself
    rows = df.drop(columns=["income"]).iloc[:1_000]
    start = time.monotonic()
    loaded.predict(rows)  # the first call after loading: the serving path
    assert time.monotonic() - start <= 0.5


@pytest.mark.timing
def test_adult_scale_model_with_extra_trees_is_small_and_predicts_fast(tmp_path, monkeypatch):
    # The search rarely picks ExtraTrees, the largest and (single-threaded) slowest member.
    monkeypatch.setattr(
        automl_module,
        "caruana",
        lambda oof, *a, **k: {key: 0.5 if "#" not in key else 0.0 for key in oof},
    )
    df = _adult_like()
    model = _fit(df, families=["LightGBM", "ExtraTrees"], target="income", max_runtime_secs=30)
    # Each is refit once, and again with other seeds when the time and size limits allow.
    assert [m.spec.name for m in model.members] == ["LightGBM", "ExtraTrees"]
    assert all(1 <= len(m.models) <= 1 + automl_module.BAG_EXTRA for m in model.members)
    path = tmp_path / "model.joblib"
    joblib.dump(model, path)
    assert path.stat().st_size <= 100 * 1024**2
    loaded = joblib.load(path)  # a file this test wrote itself
    rows = df.drop(columns=["income"]).iloc[:1_000]
    start = time.monotonic()
    loaded.predict(rows)
    assert time.monotonic() - start <= 0.5


@pytest.mark.timing
def test_thirty_second_budget_is_kept():
    X, y = make_classification(20_000, 20, n_informative=10, random_state=0)
    df = pd.DataFrame(X, columns=[f"x{i}" for i in range(20)])
    df["y"] = y
    start = time.monotonic()
    model = _fit(df, target="y", max_runtime_secs=30, stopping_rounds=0)
    assert time.monotonic() - start <= 31.5
    assert model.stop_reason == "time"


@pytest.mark.timing
def test_too_small_budget_raises_promptly():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(400_000, 50)), columns=[f"c{i}" for i in range(50)])
    df["y"] = (df["c0"] + df["c1"] > 0).astype(int)
    start = time.monotonic()
    with pytest.raises(NoModelError):
        _fit(df, target="y", max_runtime_secs=1)
    assert time.monotonic() - start <= 2.0


def test_deep_learning_is_not_refit_but_averages_its_fold_models(monkeypatch):
    monkeypatch.setattr(search, "TOP_TRIALS", 1)
    model = _fit(_binary(400), target="y", families=["DeepLearning"], nfolds=3, max_models=2)
    (member,) = model.members
    assert member.spec.name == "DeepLearning" and len(member.models) == 3  # the fold models
    assert model.leaderboard.set_index("family").loc["DeepLearning", "train_secs"] > 0


def test_a_too_wide_linear_view_leaves_those_families_out(monkeypatch):
    monkeypatch.setattr(automl_module, "LINEAR_MAX_CELLS", 100)
    monkeypatch.setattr(search, "TOP_TRIALS", 1)
    events = []
    model = _fit(
        _binary(300),
        events,
        families=["LightGBM", "DeepLearning", "Linear"],
        target="y",
        max_models=3,
    )
    assert [m.spec.name for m in model.members] == ["LightGBM"]
    notices = [e.data for e in events if e.type == "notice"]
    assert any(n.get("kind") == "families_left_out" for n in notices)
    only = _fit(_binary(300), families=["Linear"], target="y", max_models=1)  # nothing else to run
    assert [m.spec.name for m in only.members] == ["Linear"]


def _bagging_data():
    return _binary(800, seed=3)


def test_extra_seeds_are_averaged_into_a_refit_member(monkeypatch):
    df = _bagging_data()
    model = _fit(df, families=["LightGBM"], target="y", max_models=3)
    (member,) = model.members
    assert len(member.models) == 1 + automl_module.BAG_EXTRA
    seeds = {m.get_params()["random_state"] for m in member.models}
    assert len(seeds) == len(member.models)  # a different seed for each
    probas = [member.spec.predict(m, model.prep.tree(df)) for m in member.models]
    assert not np.allclose(probas[0], probas[1])
    assert np.allclose(model.predict_proba(df).to_numpy()[:, 1], np.mean(probas, axis=0)[:, 1])
    monkeypatch.setattr(automl_module, "BAG_EXTRA", 0)
    (single,) = _fit(df, families=["LightGBM"], target="y", max_models=3).members
    assert len(single.models) == 1


def test_extra_seeds_wait_for_enough_time_left(monkeypatch):
    monkeypatch.setattr(automl_module, "BAG_TIME_FACTOR", 1e12)
    (member,) = _fit(_bagging_data(), families=["LightGBM"], target="y", max_models=3).members
    assert len(member.models) == 1


def test_extra_seeds_respect_the_size_limits(monkeypatch):
    df = _bagging_data()
    monkeypatch.setattr(automl_module, "BAG_EXTRA", 0)
    (member,) = _fit(df, families=["LightGBM"], target="y", max_models=3).members
    one = member.spec.size_bytes(member.models[0])
    monkeypatch.setattr(automl_module, "BAG_EXTRA", 4)
    monkeypatch.setattr(automl_module, "SIZE_CAP", int(one * 2.5))
    (capped,) = _fit(df, families=["LightGBM"], target="y", max_models=3).members
    assert len(capped.models) == 2
    monkeypatch.setattr(automl_module, "SIZE_CAP", 40 * 1024**2)
    monkeypatch.setattr(automl_module, "TOTAL_SIZE_CAP", int(one * 3.5))
    (together,) = _fit(df, families=["LightGBM"], target="y", max_models=3).members
    assert len(together.models) == 3


def test_a_member_without_randomness_is_not_refit_with_other_seeds():
    model = _fit(_bagging_data(), families=["Linear"], target="y", max_models=3)
    assert [len(member.models) for member in model.members] == [1]


def test_runners_up_of_a_family_join_the_ensemble_candidates(monkeypatch):
    monkeypatch.setattr(search, "TOP_TRIALS", 3)
    events = []
    model = _fit(_bagging_data(), events, families=["LightGBM"], target="y", max_models=6)
    board = model.leaderboard
    candidates = board[board["family"] == "LightGBM"]
    assert len(candidates) == 3 and len(set(candidates["model"])) == 3
    assert board.loc[board["family"] == "Ensemble"].shape[0] == 1
    assert board["weight"].dropna().sum() == pytest.approx(1.0)
    weights = [e.data["weights"] for e in events if e.type == "ensemble"][0]
    assert set(weights) == {"LightGBM", "LightGBM#2", "LightGBM#3"}
    keys = [m.key for m in model.members]
    assert len(set(keys)) == len(keys) and set(keys) <= set(weights)
    assert sum(m.weight for m in model.members) == pytest.approx(1.0)
    assert model.predict_proba(_bagging_data()).shape == (800, 2)


def test_an_extra_seed_that_is_bigger_than_estimated_is_not_kept(monkeypatch):
    """A forest's size varies with its seed: the extra model is measured after it is fitted."""
    first = []

    def size(self, model):
        if not first:
            first.append(model)
        return 100 if model is first[0] else 1000

    monkeypatch.setattr(LightGBM, "size_bytes", size)
    monkeypatch.setattr(automl_module, "SIZE_CAP", 1500)
    (member,) = _fit(_bagging_data(), families=["LightGBM"], target="y", max_models=3).members
    assert len(member.models) == 2  # the first (100) and one extra (1000) fit, not a second


def test_a_failing_extra_seed_is_reported_and_the_member_keeps_its_models(monkeypatch):
    original = LightGBM._fit
    calls = []

    def flaky(self, *args, **kwargs):
        if self.seed != 0 and kwargs.get("rounds") is None and args[3] is None:  # a bagged refit
            calls.append(self.seed)
            raise RuntimeError("extra seed failed")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(LightGBM, "_fit", flaky)
    events = []
    (member,) = _fit(
        _bagging_data(), events, families=["LightGBM"], target="y", max_models=3
    ).members
    assert len(member.models) == 1 and calls
    notices = [e.data for e in events if e.type == "notice"]
    assert any(n.get("kind") == "refit_error" and n["family"] == "LightGBM" for n in notices)
