import joblib
import numpy as np
import pandas as pd
import pytest

from fione.engine.config import ConfigError
from fione.engine.prep import Prep, infer_task, validate_target

RNG = np.random.default_rng(0)


def _frame(n=6000):
    return pd.DataFrame(
        {
            "num": RNG.normal(size=n),
            "empty": np.full(n, np.nan),
            "const": np.ones(n),
            "ids": [f"user-{i}" for i in range(5000)] + [f"user-{i}" for i in range(n - 5000)],
            "pref": RNG.choice(["東京", "大阪", "名古屋"], size=n),
            "flag": RNG.choice([True, False], size=n),
            "when": pd.date_range("2024-01-01", periods=n, freq="h"),
        }
    )


# --- Prep.fit ---------------------------------------------------------------


def test_fit_drops_all_null_and_constant_columns():
    prep = Prep().fit(_frame())
    assert prep.dropped == ["empty", "const"]


def test_fit_frequency_encodes_high_cardinality_strings():
    prep = Prep().fit(_frame())
    tree = prep.tree(_frame())
    ids = tree.iloc[:, prep.feature_names.index("ids")]
    assert pd.api.types.is_float_dtype(ids)
    assert ids.iloc[0] == pytest.approx(2 / 6000)  # user-0 occurs twice
    assert ids.iloc[2000] == pytest.approx(1 / 6000)


def test_fit_keeps_japanese_categories_and_bool_as_category():
    prep = Prep().fit(_frame())
    tree = prep.tree(_frame())
    pref = tree.iloc[:, prep.feature_names.index("pref")]
    assert isinstance(pref.dtype, pd.CategoricalDtype)
    assert set(pref.cat.categories) == {"東京", "大阪", "名古屋"}
    flag = tree.iloc[:, prep.feature_names.index("flag")]
    assert set(flag.cat.categories) == {"True", "False"}


def test_fit_expands_datetime_columns():
    prep = Prep().fit(_frame())
    parts = [f"when__{p}" for p in ("year", "month", "day", "dayofweek", "ordinal")]
    assert all(p in prep.feature_names for p in parts)
    dense = prep.dense(_frame().head(2))
    row = dense.iloc[1, [prep.feature_names.index(p) for p in parts]].tolist()
    assert row == [2024, 1, 1, 0, pd.Timestamp("2024-01-01 01:00").timestamp()]


def test_feature_names_follow_column_order():
    prep = Prep().fit(_frame())
    assert prep.feature_names[:3] == ["num", "ids", "pref"]
    assert prep.feature_names[-1] == "when__ordinal"


# --- views ------------------------------------------------------------------


def test_views_use_safe_positional_column_names():
    df = pd.DataFrame({"price [USD]": [1.0, 2.0, 3.0], "a,b": ["x", "y", "x"]})
    prep = Prep().fit(df)
    for view in (prep.tree(df), prep.catboost(df), prep.dense(df)):
        assert list(view.columns) == ["f0", "f1"]
    assert prep.feature_names == ["price [USD]", "a,b"]


def test_catboost_view_uses_object_strings_with_na_marker():
    df = pd.DataFrame({"c": ["a", None, "b"], "n": [1.0, 2.0, 3.0]})
    view = Prep().fit(df).catboost(df)
    assert view["f0"].dtype == object
    assert view["f0"].tolist() == ["a", "__na__", "b"]


def test_dense_view_codes_categories_and_imputes_medians():
    df = pd.DataFrame({"c": ["a", None, "b", "a"], "n": [1.0, np.nan, 3.0, 5.0]})
    view = Prep().fit(df).dense(df)
    assert view["f0"].tolist() == [0.0, -1.0, 1.0, 0.0]
    assert view["f1"].tolist() == [1.0, 3.0, 3.0, 5.0]


def test_transform_tolerates_unseen_categories_and_extra_columns():
    prep = Prep().fit(_frame())
    new = (
        _frame(6000)
        .head(3)
        .assign(pref=["札幌", None, "東京"], ids=["new", None, "user-1"], extra=1)
    )
    tree = prep.tree(new)
    pref = tree.iloc[:, prep.feature_names.index("pref")]
    assert pref.isna().tolist() == [True, True, False]
    ids = tree.iloc[:, prep.feature_names.index("ids")].tolist()
    assert ids[0] == 0.0 and np.isnan(ids[1]) and ids[2] > 0
    assert prep.catboost(new).iloc[0, prep.feature_names.index("pref")] == "札幌"
    assert prep.dense(new).shape == (3, len(prep.feature_names))


def test_transform_ignores_missing_dropped_columns():
    prep = Prep().fit(_frame())
    assert prep.tree(_frame().drop(columns=["empty", "const"])).shape[1] == len(prep.feature_names)


def test_transform_lists_all_missing_required_columns():
    prep = Prep().fit(_frame())
    with pytest.raises(ConfigError, match=r"missing columns: \['num', 'pref'\]"):
        prep.tree(_frame().drop(columns=["num", "pref"]))


def test_transform_coerces_numeric_and_datetime_strings():
    df = pd.DataFrame(
        {"n": [1.0, 2.0, np.inf], "d": pd.to_datetime(["2024-01-01", "2024-02-01", None])}
    )
    prep = Prep().fit(df)
    new = pd.DataFrame({"n": ["4", "bad", "6"], "d": ["2024-03-05", "2024年3月5日", "x"]})
    dense = prep.dense(new)
    assert dense["f0"].tolist() == [4.0, 1.5, 6.0]  # median of the finite fitted values
    assert prep.tree(new)["f2"].tolist()[:2] == [3, 3]  # month
    assert prep.tree(df)["f0"].isna().tolist() == [False, False, True]  # inf becomes NaN


@pytest.mark.parametrize(
    "df",
    [
        pd.DataFrame({"empty": [np.nan] * 5, "const": ["a"] * 5}),
        pd.DataFrame(index=range(5)),
    ],
)
def test_fit_without_usable_columns_raises_config_error(df):
    with pytest.raises(ConfigError, match="no usable feature columns"):
        Prep().fit(df)


def test_prep_pickles(tmp_path):
    prep = Prep().fit(_frame())
    joblib.dump(prep, tmp_path / "prep.joblib")
    clone = joblib.load(tmp_path / "prep.joblib")  # a file this test wrote itself
    df = _frame()
    pd.testing.assert_frame_equal(clone.tree(df), prep.tree(df))


# --- infer_task ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("values", "task"),
    [
        (["a", "b"] * 50, "classification"),
        ([True, False] * 50, "classification"),
        ([0, 1] * 500, "classification"),
        (list(range(10)) * 100, "classification"),
        ([0.0, 1.0] * 500, "classification"),
        (list(range(30)) * 100, "regression"),
        (list(np.linspace(0, 1, 1000)), "regression"),
        ([0, 1] * 15, "regression"),  # 2 distinct / 30 rows is above the 0.05 ratio
    ],
)
def test_infer_task(values, task):
    assert infer_task(pd.Series(values)) == task


def test_infer_task_ignores_missing_values():
    assert infer_task(pd.Series([0, 1, None] * 400)) == "classification"


# --- validate_target ----------------------------------------------------------


def test_validate_target_encodes_classes_in_sorted_order():
    y, classes, nfolds = validate_target(pd.Series(["b", "a", "c"] * 10), "classification", 5)
    assert classes == ["a", "b", "c"]
    assert y.tolist()[:3] == [1, 0, 2]
    assert nfolds == 5


def test_validate_target_regression_returns_floats():
    y, classes, nfolds = validate_target(pd.Series(range(100)), "regression", 5)
    assert y.dtype == np.float64 and classes == [] and nfolds == 5


def test_validate_target_rejects_missing_values():
    with pytest.raises(ConfigError, match="target has missing values"):
        validate_target(pd.Series([1.0, None] * 10), "regression", 5)


def test_validate_target_rejects_single_value():
    with pytest.raises(ConfigError, match="single distinct value"):
        validate_target(pd.Series(["a"] * 20), "classification", 5)


def test_validate_target_rejects_too_few_rows():
    with pytest.raises(ConfigError, match="not enough rows"):
        validate_target(pd.Series([0, 1] * 4), "classification", 5)


def test_validate_target_names_classes_with_one_row():
    with pytest.raises(ConfigError, match="class 'rare' has only 1 row"):
        validate_target(pd.Series(["a", "b"] * 10 + ["rare"]), "classification", 5)


def test_validate_target_rejects_very_high_cardinality_classification():
    y = pd.Series([f"label-{i % 250}" for i in range(300)])
    with pytest.raises(ConfigError, match="250 distinct values") as raised:
        validate_target(y, "classification", 5)
    assert "regression" not in str(raised.value)  # a string target cannot be regressed
    assert "choose another column" in str(raised.value)


def test_validate_target_suggests_regression_for_high_cardinality_numbers():
    y = pd.Series([i % 250 for i in range(300)])
    with pytest.raises(ConfigError, match="250 distinct values.*use regression"):
        validate_target(y, "classification", 5)


def test_validate_target_rejects_non_numeric_regression():
    with pytest.raises(ConfigError, match="numeric"):
        validate_target(pd.Series(["a", "b"] * 10), "regression", 5)


def test_validate_target_reduces_folds_for_small_class_and_emits_event():
    events = []
    y = pd.Series(["a"] * 27 + ["b"] * 3)
    _, _, nfolds = validate_target(y, "classification", 5, emit=events.append)
    assert nfolds == 3
    assert [e.type for e in events] == ["started"]
    assert events[0].data["nfolds_reduced_to"] == 3
    assert "smallest class has 3 rows" in events[0].data["reason"]


def test_validate_target_reduces_folds_for_few_rows():
    events = []
    _, _, nfolds = validate_target(pd.Series(range(30)), "regression", 10, emit=events.append)
    assert nfolds == 6
    assert events[0].data == {"nfolds_reduced_to": 6, "reason": "only 30 rows"}


def test_validate_target_keeps_folds_for_balanced_small_data():
    events = []
    _, _, nfolds = validate_target(pd.Series([0, 1] * 20), "classification", 5, emit=events.append)
    assert nfolds == 5 and events == []
