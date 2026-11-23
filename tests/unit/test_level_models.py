import pickle
import time

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from fione.engine import features, level_models
from fione.engine.automl import AutoML
from fione.engine.config import Deadline, TrainConfig
from fione.engine.features import Group, select_groups
from fione.engine.level_models import LevelDiscriminant
from fione.engine.prep import Prep

LABEL = level_models.LABEL + "unit"


def per_value(n_levels=40, per_level=300, seed=0, width=12, structured=True):
    """Each value of ``unit`` has its own direction in the first six columns along which the two
    classes lie apart; over all values the classes have the same mean in every column, so no
    global model (and no tree reading ``unit`` as a number) sees them. With ``structured`` False
    the classes are the same for every value (a plain threshold on the first column)."""
    rng = np.random.default_rng(seed)
    unit = np.repeat(np.arange(n_levels), per_level)
    y = rng.integers(0, 2, len(unit))
    X = rng.normal(size=(len(unit), width))
    if structured:
        direction = rng.normal(size=(n_levels, 6))
        direction /= np.linalg.norm(direction, axis=1, keepdims=True)
        X[:, :6] += 1.6 * (2 * y - 1)[:, None] * direction[unit]
    else:
        X[:, 0] += 1.6 * (2 * y - 1)
    frame = pd.DataFrame(X, columns=[f"x{i}" for i in range(width)])
    frame.insert(0, "unit", unit)
    order = rng.permutation(len(frame))
    return frame.iloc[order].reset_index(drop=True), y[order]


def features_of(frame):
    return [c for c in frame.columns if c != "unit"]


def test_the_scores_of_a_model_per_value_separate_classes_that_no_global_model_sees():
    X, y = per_value()
    fresh_X, fresh_y = per_value(seed=1)
    group = LevelDiscriminant("unit", features_of(X)).fit(X, y)
    own = group.transform(X).iloc[:, 0].to_numpy()
    assert roc_auc_score(y, np.nan_to_num(own)) > 0.85  # cross-fitted, so not a fit on itself
    new = group.transform(fresh_X).iloc[:, 0].to_numpy()
    # the same values with other directions: the models do not carry over
    assert abs(roc_auc_score(fresh_y, np.nan_to_num(new)) - 0.5) < 0.1
    same = X.copy()
    held = group.transform(same).iloc[:, 0].to_numpy()
    assert np.allclose(held, own, equal_nan=True)  # a copy of the training rows is the same rows


def test_training_rows_never_see_their_own_label_and_other_rows_get_the_models_of_all_rows():
    X, y = per_value()
    group = LevelDiscriminant("unit", features_of(X)).fit(X, y)
    train = group.transform(X).iloc[:, 0].to_numpy()
    order = np.random.default_rng(0).permutation(len(X))
    shuffled = group.transform(X.iloc[order].reset_index(drop=True)).iloc[:, 0].to_numpy()
    # the rows in another order are not the training rows: they get the scores of all rows,
    # which have seen their own labels
    assert roc_auc_score(y[order], shuffled) > roc_auc_score(y, train) + 0.005


def test_an_unseen_value_or_one_with_too_few_rows_gets_no_score_and_missing_numbers_are_read():
    X, y = per_value(n_levels=30)
    X = pd.concat([X, X.iloc[:5].assign(unit=999)], ignore_index=True)  # 5 rows of a new value
    y = np.append(y, [0, 1, 0, 1, 0])
    group = LevelDiscriminant("unit", features_of(X)).fit(X, y)
    probe = X.iloc[:4].copy().assign(unit=[0, 1, 777, 999])
    probe.loc[probe.index[0], "x3"] = np.nan
    out = group.transform(probe).iloc[:, 0]
    assert out.iloc[:2].notna().all()
    assert out.iloc[2:].isna().all()  # no training row has 777; 999 has too few
    assert group.transform(X.iloc[:0]).shape == (0, 1)


def test_the_group_pickles_without_the_training_scores_and_scores_alike():
    X, y = per_value(n_levels=30)
    group = LevelDiscriminant("unit", features_of(X)).fit(X, y)
    loaded = pickle.loads(pickle.dumps(group))
    assert loaded._oof is None and group._oof is not None
    rows = X.iloc[:50].reset_index(drop=True)
    assert np.allclose(
        loaded.transform(rows).to_numpy(), group.transform(rows).to_numpy(), equal_nan=True
    )
    size = len(pickle.dumps(group))
    assert size < 8 * len(group._models) * 2 * 12 * 13 // 2 + 200_000  # triangles of float32


def test_the_columns_are_cut_so_that_the_fit_and_the_models_stay_within_their_bounds():
    assert level_models._width(20_000, 40, 20) == 20
    wide = level_models._width(1_000_000, 2_000, 300)
    assert 3 <= wide < 300
    assert level_models._estimated_secs(1_000_000, 2_000, wide) <= level_models.MAX_FIT_SECS
    assert 2_000 * 2 * (wide * (wide + 1) // 2) * 4 <= level_models.MAX_MODEL_BYTES


def test_a_table_with_the_same_classes_for_every_value_is_not_given_the_group():
    X, y = per_value(n_levels=30, per_level=120, structured=False)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(600))
    assert all(v.group != LABEL for v in verdicts)  # the screen finds no gain in a model per value
    assert not any(isinstance(g, LevelDiscriminant) for g in kept)


def test_a_table_with_classes_that_depend_on_the_value_is_given_the_group_and_gains_from_it():
    X, y = per_value(n_levels=30, per_level=120)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(600))
    verdict = next(v for v in verdicts if v.group == LABEL)
    assert verdict.adopted and verdict.gain > 0.05
    assert any(isinstance(g, LevelDiscriminant) for g in kept)


def test_the_group_is_tried_for_two_classes_and_for_ungrouped_folds_only(monkeypatch):
    asked = []

    def spy(*args, **kwargs):
        asked.append(1)
        return []

    monkeypatch.setattr(level_models, "level_models", spy)
    X, y = per_value(n_levels=30, per_level=20)
    y3 = y + (np.arange(len(y)) % 3 == 0)
    rows = np.arange(len(X)) // 6
    select_groups(X, y3, "classification", 3, 0, Deadline(30))
    select_groups(X, y.astype(float), "regression", 3, 0, Deadline(30))
    select_groups(X, y, "classification", 3, 0, Deadline(30), row_groups=rows)
    assert not asked
    select_groups(X, y, "classification", 3, 0, Deadline(30))
    assert asked


def test_the_screen_and_the_fit_are_cheap_on_a_small_table():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(20_000, 20)), columns=[f"x{i}" for i in range(20)])
    X.insert(0, "unit", rng.integers(0, 50, len(X)))
    y = rng.integers(0, 2, len(X))
    group = LevelDiscriminant("unit", features_of(X))
    started = time.monotonic()
    level_models._screen(group, X, y, 0)
    group.fit(X, y)
    assert time.monotonic() - started < 15  # about a second on a laptop


def test_automl_keeps_the_model_per_value_honest_and_through_a_save_and_load():
    X, y = per_value(n_levels=30, per_level=150)
    fresh_X, _ = per_value(n_levels=30, per_level=20, seed=0)
    config = TrainConfig(target="label", task="classification", max_runtime_secs=6000, max_models=2)
    model = AutoML(config, families=["LightGBM"]).fit(X.assign(label=y))
    tried = {row["group"]: row for row in model.features}
    assert tried[LABEL]["adopted"]
    # the validation score is that of rows whose scores never saw their own label
    assert model.metrics["auc"] > 0.8
    proba = model.predict_proba(fresh_X)
    loaded = pickle.loads(pickle.dumps(model))
    assert np.allclose(loaded.predict_proba(fresh_X).to_numpy(), proba.to_numpy())


def test_a_value_is_read_the_same_whether_it_is_a_number_or_text_at_fit_and_at_predict():
    X, y = per_value(n_levels=30, per_level=60)
    rows = X.iloc[:40].reset_index(drop=True)
    numbers = LevelDiscriminant("unit", features_of(X)).fit(X, y)
    expected = numbers.transform(rows.assign(unit=rows["unit"] + 0.5 - 0.5)).iloc[:, 0]
    assert expected.notna().all()
    for other in (
        rows["unit"].astype(str),
        rows["unit"].astype(float),
        rows["unit"].astype(object),
    ):
        got = numbers.transform(rows.assign(unit=other)).iloc[:, 0]
        assert np.allclose(got, expected)
    texts = LevelDiscriminant("unit", features_of(X)).fit(X.assign(unit=X["unit"].astype(str)), y)
    for other in (rows["unit"], rows["unit"].astype(float), rows["unit"].astype(str)):
        got = texts.transform(rows.assign(unit=other)).iloc[:, 0]
        assert np.allclose(got, expected)
    assert numbers.transform(rows.assign(unit="north")).iloc[:, 0].isna().all()


def test_a_changed_value_in_any_column_makes_the_frame_not_the_training_rows():
    X, y = per_value(n_levels=30, per_level=60)
    group = LevelDiscriminant("unit", features_of(X)).fit(X, y)
    trained = group.transform(X).iloc[:, 0].to_numpy()
    edited = X.copy()
    edited.loc[edited.index[:30], "x11"] += 1.0  # the last column, which no head of the frame shows
    got = group.transform(edited).iloc[:, 0].to_numpy()
    assert not np.allclose(got, trained, equal_nan=True)
    assert group.transform(X.copy()).iloc[:, 0].to_numpy() == pytest.approx(trained, nan_ok=True)


def test_the_fit_keeps_its_matrix_in_four_bytes_and_cuts_the_columns_to_the_cells_it_may_hold():
    X, y = per_value(n_levels=30, per_level=60)
    group = LevelDiscriminant("unit", features_of(X)).fit(X, y)
    assert group._matrix(X).dtype == np.float32
    assert level_models._width(10_000_000, 10, 255) <= level_models.MAX_CELLS // 10_000_000
    assert level_models._width(1_000_000, 10, 255) * 1_000_000 <= level_models.MAX_CELLS


def test_numbers_beyond_the_range_give_no_error_and_no_infinite_score():
    X, y = per_value(n_levels=30, per_level=60)
    X.loc[X.index[:50], "x1"] = 1e200
    X.loc[X.index[50:80], "x2"] = np.inf
    X["x3"] = 1e300  # a constant of that size
    group = LevelDiscriminant("unit", features_of(X)).fit(X, y)
    scores = group.transform(X).iloc[:, 0].to_numpy()
    assert not np.isinf(scores).any()
    assert np.isfinite(scores).mean() > 0.9
    again = group.transform(X.iloc[:20].reset_index(drop=True)).iloc[:, 0].to_numpy()
    assert not np.isinf(again).any()


def test_the_models_of_all_the_groups_of_a_table_share_the_size_limit(monkeypatch):
    X, y = per_value(n_levels=30, per_level=60)
    X["unit2"] = (X["unit"] + 7) % 30  # the same structure under other names
    limit = 30 * 2 * (12 * 13 // 2) * 4 + 6_000  # one group of 12 columns, and a little more
    monkeypatch.setattr(level_models, "MAX_MODEL_BYTES", limit)
    found = level_models.level_models(Prep().fit(X), X, y, list(X.columns), X, y)
    assert [g.column for g in found] == ["unit", "unit2"]
    sizes = [level_models._model_bytes(30, len(g.features)) for g in found]
    assert sum(sizes) <= limit and len(found[1].features) < len(found[0].features)
    assert level_models._width(1_800, 30, 11, budget=1_000) < level_models.MIN_LEVEL_FEATURES


class Noise(Group):
    """A column that tells nothing, to judge next to the group of a table."""

    uses_target = False

    def __init__(self):
        self.label, self.columns = "noise", ("x5",)

    def _fit(self, X):
        self._sources = {"x5__square": self.columns}

    def _compute(self, df):
        return pd.DataFrame({"x5__square": df["x5"] ** 2 + np.arange(len(df)) % 3})


def test_a_group_that_does_not_help_next_to_the_early_group_is_dropped_and_the_early_one_stays(
    monkeypatch,
):
    monkeypatch.setattr(features, "candidates", lambda *args, **kwargs: [Noise()])
    X, y = per_value(n_levels=30, per_level=120)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(600))
    ours = [v for v in verdicts if v.group == LABEL]
    assert len(ours) == 1 and ours[0].adopted
    assert [v.adopted for v in verdicts if v.group == "noise"] in ([False], [])
    assert [type(g) for g in kept] == [LevelDiscriminant]


def test_the_last_check_of_the_other_groups_is_made_against_the_early_group_and_leaves_it(
    monkeypatch,
):
    seen = []

    def judge(before, after, z=3.0):
        seen.append((before.mean(), after.mean()))
        return len(seen) == 1  # the group is adopted, then the last check fails

    monkeypatch.setattr(features, "candidates", lambda *args, **kwargs: [Noise()])
    monkeypatch.setattr(features, "passes", judge)
    monkeypatch.setattr(features, "paired", lambda before, after: (1.0, 0.1, 1.0))
    X, y = per_value(n_levels=30, per_level=120)
    kept, verdicts = select_groups(X, y, "classification", 5, 0, Deadline(600))
    assert len(seen) == 2
    assert [v.adopted for v in verdicts if v.group == LABEL] == [True]  # one verdict, kept
    assert [(v.adopted, v.reason) for v in verdicts if v.group == "noise"] == [
        (False, "final check")
    ]
    assert [type(g) for g in kept] == [LevelDiscriminant]
