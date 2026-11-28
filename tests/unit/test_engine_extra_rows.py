"""Extra rows: learned from in every fold and in the final fit, never validated."""

import numpy as np
import pandas as pd
import pytest

from fione.engine import automl as automl_module
from fione.engine.automl import AutoML, _learned_mix, _with_extra_rows
from fione.engine.config import ConfigError, TrainConfig


def _table(n, seed, noise=0.8):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n), "c": rng.normal(size=n)})
    score = 1.2 * df["a"] - df["b"] + noise * rng.logistic(size=n)
    df["y"] = np.where(score > 0, "yes", "no")
    return df


def _fit(df, extra=None, events=None, **config):
    config = {"max_runtime_secs": 45, "stopping_rounds": 2, **config}
    sink = events.append if events is not None else (lambda event: None)
    return AutoML(TrainConfig(target="y", **config), sink, families=["LightGBM", "Linear"]).fit(
        df, extra=extra
    )


def _notices(events):
    return {e.data.get("kind"): e.data for e in events if e.type == "notice"}


def test_the_scores_and_outputs_count_the_own_rows_only():
    own, extra = _table(150, 0), _table(900, 1)
    events = []
    model = _fit(own, extra, events, keep_cv_predictions=True, keep_cv_fold_assignment=True)
    assert len(model.cv_predictions) == len(model.fold_assignment) == len(own)
    assert (model.fold_assignment >= 0).all()  # every own row is validated
    started = next(e for e in events if e.type == "started")
    assert started.data["n_rows"] == len(own) and started.data["n_extra_rows"] == len(extra)
    assert _notices(events)["extra_rows"]["rows"] == len(extra)
    assert model.predict(_table(20, 5).drop(columns="y")).shape[0] == 20


def _curved(n, seed):
    """A label that follows a curve in two numbers: a few rows cannot show it."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {"a": rng.uniform(-2, 2, n), "b": rng.uniform(-2, 2, n), "c": rng.normal(size=n)}
    )
    df["y"] = np.where(
        np.sin(2 * df["a"]) * np.cos(2 * df["b"]) + 0.15 * rng.normal(size=n) > 0, "yes", "no"
    )
    return df


def test_extra_rows_of_the_same_kind_help_a_small_table():
    own, extra, test = _curved(150, 0), _curved(3000, 1), _curved(1500, 9)
    X, truth = test.drop(columns="y"), test["y"].to_numpy()

    def accuracy(extra_rows):
        config = TrainConfig(target="y", max_runtime_secs=40, stopping_rounds=2, seed=0)
        model = AutoML(config, lambda event: None, families=["LightGBM"]).fit(own, extra=extra_rows)
        return float((model.predict(X).to_numpy() == truth).mean())

    assert accuracy(extra) > accuracy(None) + 0.05


def test_extra_rows_that_repeat_a_row_of_the_data_are_left_out():
    own = _table(150, 0)
    extra = pd.concat([own.iloc[:40], _table(200, 3)], ignore_index=True)
    events = []
    _fit(own, extra, events)
    found = _notices(events)
    assert found["extra_duplicates"]["dropped"] == 40
    assert found["extra_rows"]["rows"] == 200


def test_extra_rows_all_left_out_train_as_without():
    own = _table(150, 0)
    events = []
    model = _fit(own, own.copy(), events)
    assert "extra_duplicates" in _notices(events)
    assert model.predict(own.drop(columns="y")).shape[0] == len(own)


def test_extra_rows_that_do_not_fit_the_data_are_refused():
    own, extra = _table(150, 0), _table(100, 1)
    with pytest.raises(ConfigError, match="lack columns.*c"):
        _fit(own, extra.drop(columns="c"))
    odd = extra.assign(y=np.where(np.arange(len(extra)) % 7 == 0, "maybe", extra["y"]))
    with pytest.raises(ConfigError, match="labels the data lacks.*maybe"):
        _fit(own, odd)
    with pytest.raises(ConfigError, match="column 'a'.*cannot be read"):
        _fit(own, extra.assign(a="word"))
    with pytest.raises(ConfigError, match="missing values"):
        _fit(own, extra.assign(y=np.where(np.arange(len(extra)) < 3, None, extra["y"])))
    with pytest.raises(ConfigError, match="time_column"):
        _fit(own.assign(t=np.arange(len(own))), extra.assign(t=0), time_column="t")


def test_extra_rows_read_true_and_false_as_the_csv_reader_does():
    """A column of the data that holds booleans takes, from the extra rows, what the CSV reader
    reads as true or false; any other text is refused rather than read as true."""
    own = _table(150, 0).assign(y=lambda d: d["y"] == "yes", f=lambda d: d["a"] > 0)
    extra = _table(100, 1)
    text = extra.assign(
        y=np.where(extra["y"] == "yes", "True", "False"), f=np.where(extra["a"] > 0, "1", "0")
    )
    typed = automl_module._typed_like(own["y"], text["y"], "y")
    assert typed.dtype == bool and typed.tolist() == (extra["y"] == "yes").tolist()
    assert automl_module._typed_like(own["f"], text["f"], "f").tolist() == (extra["a"] > 0).tolist()
    ones = pd.Series([1.0, 0.0, np.nan])  # 1 and 0 with a gap, as a CSV gives them
    assert automl_module._typed_like(own["f"], ones, "f").tolist() == [True, False, None]
    for bad in ("Maybe", "yes"):
        odd = text.assign(y=np.where(np.arange(len(text)) % 7 == 0, bad, text["y"]))
        with pytest.raises(ConfigError, match="column 'y'.*cannot be read as bool"):
            _fit(own, odd)
    with pytest.raises(ConfigError, match="column 'f'.*cannot be read as bool"):
        _fit(own, text.assign(f="word"))
    with pytest.raises(ConfigError, match="missing values"):
        _fit(own, text.assign(y=np.where(np.arange(len(text)) < 3, None, text["y"])))
    gaps = text.assign(f=np.where(np.arange(len(text)) % 4 == 0, None, text["f"]))  # an input
    events = []
    _fit(own, gaps, events, max_runtime_secs=45)
    assert _notices(events)["extra_rows"]["rows"] == len(text)


def test_extra_rows_may_have_gaps_and_fractions_in_a_column_of_whole_numbers():
    own = _table(150, 0).assign(k=lambda d: np.arange(len(d)) % 5)  # int64, no gaps
    extra = _table(200, 1).assign(k=lambda d: np.where(np.arange(len(d)) % 4 == 0, np.nan, 2.5))
    events = []
    _fit(own, extra, events, max_runtime_secs=45)
    assert _notices(events)["extra_rows"]["rows"] == len(extra)


def test_the_own_rows_may_have_any_index():
    own = _table(150, 0)
    own.index = own.index * 3 + 1000  # as after filtering rows
    events = []
    model = _fit(own, _table(200, 1), events, max_runtime_secs=45, keep_cv_predictions=True)
    assert len(model.cv_predictions) == len(own)
    assert "diagnostics_error" not in _notices(events)
    own = own.iloc[:40]  # ... and when every extra row turns out to repeat one of them
    events = []
    _fit(own.iloc[::-1], own.reset_index(drop=True), events, max_runtime_secs=45)
    assert "extra_duplicates" in _notices(events)


def test_the_folds_are_repeated_by_the_rows_every_fold_fits_the_extra_rows_included():
    own = _table(150, 0)
    plain, joined = [], []
    _fit(own, None, plain, max_runtime_secs=20)
    _fit(own, _table(6000, 1), joined, max_runtime_secs=20)
    repeats = lambda events: next(e for e in events if e.type == "started").data["cv_repeats"]  # noqa: E731
    assert repeats(plain) == 3 and repeats(joined) == 1


def test_numbers_written_as_text_are_read_as_the_data_reads_them():
    own, extra = _table(150, 0), _table(100, 1)
    events = []
    _fit(own, extra.astype({"a": str, "b": str}), events)
    assert _notices(events)["extra_rows"]["rows"] == len(extra)


def test_a_regression_learns_from_extra_rows_too():
    rng = np.random.default_rng(0)
    make = lambda n: pd.DataFrame({"x": rng.normal(size=n)}).assign(  # noqa: E731
        y=lambda d: 3 * d["x"] + rng.normal(size=n)
    )
    own, extra = make(80), make(600)
    model = AutoML(
        TrainConfig(target="y", max_runtime_secs=60, stopping_rounds=2), families=["Linear"]
    ).fit(own, extra=extra)
    assert abs(float(model.predict(pd.DataFrame({"x": [2.0]})).iloc[0]) - 6.0) < 1.0
    with pytest.raises(
        ConfigError, match="extra rows cannot be read|extra rows must be numeric|cannot be read"
    ):
        AutoML(TrainConfig(target="y", max_runtime_secs=30), families=["Linear"]).fit(
            own, extra=extra.assign(y="high")
        )


def test_the_folds_get_the_extra_rows_but_not_those_of_the_groups_they_validate():
    folds = [(np.array([0, 1, 2, 3]), np.array([4, 5])), (np.array([2, 3, 4, 5]), np.array([0, 1]))]
    own_groups = np.array([0, 0, 1, 1, 2, 2])
    extra_groups = np.array([0, 2, 7, 7])  # rows 6..9
    plain = _with_extra_rows(folds, 6, 4, None, None)
    assert [t.tolist() for t, _ in plain] == [[0, 1, 2, 3, 6, 7, 8, 9], [2, 3, 4, 5, 6, 7, 8, 9]]
    grouped = _with_extra_rows(folds, 6, 4, own_groups, extra_groups)
    assert grouped[0][0].tolist() == [0, 1, 2, 3, 6, 8, 9]  # group 2 is validated: row 7 is out
    assert grouped[1][0].tolist() == [2, 3, 4, 5, 7, 8, 9]  # group 0 is validated: row 6 is out
    assert [v.tolist() for _, v in grouped] == [[4, 5], [0, 1]]


def test_extra_rows_with_a_group_column_are_held_out_with_their_group():
    own = _table(160, 0).assign(g=lambda d: np.arange(len(d)) % 16)
    extra = _table(300, 2).assign(g=lambda d: np.arange(len(d)) % 40)  # groups 16..39 are new
    events = []
    _fit(own, extra, events, cv_group_column="g", ignored_columns=["g"])
    assert "extra_without_group" not in _notices(events)
    events = []
    _fit(own, extra.drop(columns="g"), events, cv_group_column="g", ignored_columns=["g"])
    assert "extra_without_group" in _notices(events)


def test_the_class_mix_to_correct_is_that_of_the_rows_the_models_learn_from():
    y = np.array([0, 0, 0, 1, 1, 2])
    assert _learned_mix(y, None, 3).tolist() == pytest.approx([0.5, 1 / 3, 1 / 6])
    weight = np.array([1, 1, 1, 1, 1, 4.0])
    assert _learned_mix(y, weight, 3).tolist() == pytest.approx([3 / 9, 2 / 9, 4 / 9])


def test_extra_weight_is_checked():
    for bad in (0, -1, "1", True, float("nan")):
        with pytest.raises(ConfigError, match="extra_weight"):
            TrainConfig(target="y", extra_weight=bad).validate()
    assert TrainConfig.from_dict({"target": "y", "extra_weight": 0.25}).extra_weight == 0.25


def test_the_extra_rows_are_weighted_in_training_only(monkeypatch):
    seen = {}
    real = automl_module.AutoML._search

    def spy(self, families, X, y, folds, task, prep, search, stopping, weight, repeats):
        seen["weight"], seen["n"] = weight, len(y)
        return real(self, families, X, y, folds, task, prep, search, stopping, weight, repeats)

    monkeypatch.setattr(automl_module.AutoML, "_search", spy)
    own, extra = _table(120, 0), _table(300, 1)
    _fit(own, extra, extra_weight=0.25)
    assert seen["n"] == 420
    assert seen["weight"][:120].tolist() == [1.0] * 120
    assert seen["weight"][120:].tolist() == [0.25] * 300
