import pickle

import joblib
import numpy as np
import pandas as pd
import pytest

from fione.engine.config import ConfigError, TargetError
from fione.engine.prep import LINEAR_LEVELS, Prep, infer_task, integer_date_format, validate_target

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
    assert prep.feature_names[-2:] == ["when__ordinal", "when__hour"]  # it carries a time


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


def test_catboost_view_reads_a_frequency_column_as_strings_unless_it_is_nearly_an_id():
    n = 1000
    df = pd.DataFrame(
        {
            "device": [f"d{i % 400}" for i in range(n)],
            "row_id": [f"r{i}" for i in range(n)],
            "near_id": [f"u{i % 950}" for i in range(n)],
            "n": np.arange(n, dtype=float),
        }
    )
    prep = Prep().fit(df)
    assert (
        prep.kind_of("device") == prep.kind_of("row_id") == prep.kind_of("near_id") == "frequency"
    )
    view = prep.catboost(df.assign(device=[None] + ["new"] + df["device"][2:].tolist()))
    assert view["f0"].dtype == object
    assert view["f0"].tolist()[:3] == ["__na__", "new", "d2"]
    assert view["f1"].dtype == view["f2"].dtype == float  # (almost) every value is its own
    assert prep.tree(df)["f0"].dtype == float  # the other views keep the frequency
    assert prep.catboost(df).index.equals(df.index)


def test_dense_view_codes_categories_and_imputes_medians():
    df = pd.DataFrame({"c": ["a", None, "b", "a"], "n": [1.0, np.nan, 3.0, 5.0]})
    view = Prep().fit(df).dense(df)
    assert view["f0"].tolist() == [0.0, -1.0, 1.0, 0.0]
    assert view["f1"].tolist() == [1.0, 3.0, 3.0, 5.0]


def test_linear_view_standardises_numbers_and_one_hot_encodes_the_rest():
    df = pd.DataFrame(
        {
            "num": [1.0, 2.0, 3.0, 4.0, np.nan, 100.0],
            "pref": ["東京", "大阪", "東京", "東京", "大阪", "名古屋"],
        }
    )
    prep = Prep().fit(df)
    view = prep.linear(df)
    assert list(view.columns) == ["f0", "f0_na", "f1_0", "f1_1", "f1_2"]  # f1: 東京 > 大阪 > 名古屋
    assert (view.dtypes == np.float64).all()
    assert view["f0"].abs().max() <= 5.0  # clipped
    assert view["f0_na"].tolist() == [0, 0, 0, 0, 1, 0]
    assert view[["f1_0", "f1_1", "f1_2"]].to_numpy().tolist()[:3] == [
        [1, 0, 0],
        [0, 1, 0],
        [1, 0, 0],
    ]
    odd = prep.linear(pd.DataFrame({"num": [np.inf], "pref": ["京都"]}))  # unseen level
    assert odd[["f1_0", "f1_1", "f1_2"]].to_numpy().sum() == 0


def test_linear_width_counts_the_view_columns():
    df = _frame()
    prep = Prep().fit(df)
    assert prep.linear_width == prep.linear(df).shape[1]


def test_linear_view_keeps_the_most_frequent_levels_only():
    levels = [f"c{i}" for i in range(40)]
    df = pd.DataFrame({"cat": [level for i, level in enumerate(levels) for _ in range(40 - i)]})
    view = Prep().fit(df).linear(df)
    assert view.shape[1] == LINEAR_LEVELS
    assert view.iloc[:, 0].sum() == 40  # c0 is the most frequent


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
    assert ids[0] == pytest.approx(1 / 6000) and np.isnan(ids[1]) and ids[2] > 0
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


def _stamps(n=300):
    return pd.Series(
        pd.date_range(pd.Timestamp("2012-10-02 09:00"), periods=n, freq="7h")
    ).dt.strftime("%d-%m-%Y %H:%M")


def test_date_strings_become_date_parts_and_read_day_first():
    df = pd.DataFrame({"n": RNG.normal(size=300), "stamp": _stamps()})
    prep = Prep().fit(df)
    assert prep.kind_of("stamp") == "datetime" and prep.dayfirst == ("stamp",)
    # one row of a later batch: the day-first reading is the one found when fitting
    one = prep.tree(pd.DataFrame({"n": [0.0], "stamp": ["03-11-2012 10:00"]}))
    assert one["f2"].tolist() == [11] and one["f3"].tolist() == [3]  # month, day


def test_date_strings_month_first_and_iso_are_not_read_day_first():
    iso = pd.Series(pd.date_range("2012-10-02", periods=300, freq="D").strftime("%Y-%m-%d"))
    us = pd.Series(pd.date_range("2012-10-02", periods=300, freq="D").strftime("%m/%d/%Y"))
    for column in (iso, us):
        prep = Prep().fit(pd.DataFrame({"n": RNG.normal(size=300), "d": column}))
        assert prep.kind_of("d") == "datetime" and prep.dayfirst == ()
        assert prep.tree(pd.DataFrame({"n": [0.0], "d": [column[1]]}))["f2"].tolist() == [10]


def test_the_hour_is_a_base_feature_only_for_dates_with_a_time():
    stamps = _stamps()
    days = pd.Series(pd.date_range("2012-10-02", periods=300, freq="D").strftime("%Y-%m-%d"))
    prep = Prep().fit(pd.DataFrame({"n": RNG.normal(size=300), "stamp": stamps, "day": days}))
    assert prep.timed == ("stamp",)
    assert "stamp__hour" in prep.feature_names and "day__hour" not in prep.feature_names
    hour = prep.tree(
        pd.DataFrame({"n": [0.0], "stamp": ["03-11-2012 10:00"], "day": ["2012-11-03"]})
    )
    assert hour[f"f{prep.feature_names.index('stamp__hour')}"].tolist() == [10.0]


def test_times_and_months_alone_are_not_dates():
    """Dated by today's clock they would shift between training and prediction."""
    times = pd.Series(["09:15:00", "17:40:00", "08:00:01", "23:59:59"] * 75)
    months = pd.Series(["Jan", "Feb", "Mar", "Apr", "May", "Jun"] * 50)
    prep = Prep().fit(pd.DataFrame({"n": RNG.normal(size=300), "t": times, "m": months}))
    assert prep.kind_of("t") != "datetime" and prep.kind_of("m") != "datetime"


def test_the_hour_is_not_repeated_by_the_date_parts_group():
    from fione.engine.features import DateParts

    df = pd.DataFrame({"n": RNG.normal(size=300), "stamp": _stamps()})
    prep = Prep().fit(df, groups=[DateParts(["stamp"], base_hours=("stamp",))])
    assert len(prep.feature_names) == len(set(prep.feature_names))
    assert "stamp__hour" in prep.feature_names and "stamp__week" in prep.feature_names


def test_a_prep_pickled_without_dayfirst_still_loads():
    prep = Prep().fit(pd.DataFrame({"n": RNG.normal(size=300), "stamp": _stamps()}))
    del prep.__dict__["dayfirst"], prep.__dict__["timed"]
    loaded = pickle.loads(pickle.dumps(prep))
    assert loaded.dayfirst == () and loaded.timed == ()


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
    assert [e.type for e in events] == ["notice"]
    assert events[0].data["nfolds_reduced_to"] == 3
    assert "smallest class has 3 rows" in events[0].data["reason"]


def test_validate_target_reduces_folds_for_few_rows():
    events = []
    _, _, nfolds = validate_target(pd.Series(range(30)), "regression", 10, emit=events.append)
    assert nfolds == 6
    assert events[0].data == {
        "message": "nfolds reduced to 6: only 30 rows",
        "nfolds_reduced_to": 6,
        "reason": "only 30 rows",
    }


def test_validate_target_keeps_folds_for_balanced_small_data():
    events = []
    _, _, nfolds = validate_target(pd.Series([0, 1] * 20), "classification", 5, emit=events.append)
    assert nfolds == 5 and events == []


@pytest.mark.parametrize(
    ("y", "task", "code", "details"),
    [
        (pd.Series([0, 1] * 4), "classification", "few_rows", {"n": 8, "min": 10}),
        (pd.Series([1.0, None] * 10), "regression", "missing", {"n": 10}),
        (pd.Series(["a"] * 20), "classification", "single_value", {}),
        (pd.Series(["a", "b"] * 10), "regression", "not_numeric", {}),
        (pd.Series([1.0, np.inf] * 10), "regression", "infinite", {}),
        (
            pd.Series([i % 250 for i in range(300)]),
            "classification",
            "too_many_classes",
            {"n": 250},
        ),
        (
            pd.Series(["a", "b"] * 10 + ["rare"]),
            "classification",
            "single_row_class",
            {"label": "rare", "n": 1},
        ),
    ],
)
def test_a_refused_target_names_the_rule_it_breaks(y, task, code, details):
    """UIs say it in their own words from ``code`` and ``details``; the message is unchanged."""
    with pytest.raises(TargetError) as raised:
        validate_target(y, task, 5)
    assert (raised.value.code, raised.value.details) == (code, details)
    assert isinstance(raised.value, ConfigError)


def test_date_only_columns_are_read_as_dates():
    import datetime

    days = [datetime.date(2024, 1, 1) + datetime.timedelta(days=i) for i in range(30)]
    X = pd.DataFrame({"day": days, "x": np.arange(30.0)})
    X.loc[3, "day"] = None
    assert X["day"].dtype == object
    prep = Prep().fit(X)
    assert prep.kind_of("day") == "datetime"
    assert [n for n in prep.feature_names if n.startswith("day__")][-1] == "day__ordinal"
    tree = prep.tree(X)
    assert tree.shape == (30, len(prep.feature_names))
    assert tree.iloc[0, 0] == 2024 and tree.iloc[4, 2] == 5


def test_an_object_column_that_mixes_dates_and_text_is_not_a_date():
    import datetime

    values = [datetime.date(2024, 1, 1 + i % 28) for i in range(40)] + ["n/a"] * 3
    X = pd.DataFrame({"day": values, "x": np.arange(43.0)})
    assert Prep().fit(X).kind_of("day") == "category"


def _posts(n=120):
    subjects = {"space": "rocket orbit launch moon crew", "food": "bread cheese soup butter sauce"}
    rng = np.random.default_rng(1)
    labels = rng.choice(list(subjects), n)
    texts = [" ".join(rng.choice(subjects[label].split(), 7)) for label in labels]
    return pd.DataFrame(
        {"num": rng.normal(size=n), "post": texts, "code": [f"A{i}" for i in range(n)]}
    )


def test_prose_columns_are_the_ones_with_running_text():
    frame = _posts()
    frame["when"] = "2015-02-24 11:35:52 -0800"  # digits are not words
    frame.loc[0, "when"] = "2015-02-25 09:00:00 -0800"
    prep = Prep().fit(frame)
    assert prep.prose == ("post",)


def test_a_short_text_is_prose_only_when_its_values_are_mostly_different_words():
    n = 200
    rng = np.random.default_rng(2)
    words = ["red", "blue", "cotton", "leather", "bag", "shirt", "vintage", "small", "large"]
    frame = pd.DataFrame(
        {
            "num": rng.normal(size=n),
            # four words, mostly different: a product title
            "title": [" ".join(rng.choice(words, 4)) + f" {i}" for i in range(n)],
            # four words but few different values: a label
            "label": rng.choice(["Eastern Time (US Canada)", "Pacific Time (US Canada)"], n),
            # four letter runs of one or two letters, all different: a code
            "code": [f"C_ID_{i:04d}a{i % 7}b" for i in range(n)],
            # two words, all different: a name
            "person": [f"Ann{i} Lee" for i in range(n)],
        }
    )
    assert Prep().fit(frame).prose == ("title",)


def test_a_label_with_hundreds_of_levels_is_not_prose_though_its_first_rows_look_different():
    n = 5000
    levels = [f"fraud_Shop{i}-Toy" for i in range(600)]  # three words each
    frame = pd.DataFrame({"merchant": [levels[i % 600] for i in range(n)], "num": range(n)})
    first = frame["merchant"].head(1000)
    assert first.nunique() > 0.5 * len(first)  # all different, to look at 1,000 rows
    assert Prep().fit(frame).prose == ()


def test_a_search_query_that_repeats_is_prose_and_still_read_as_levels():
    n = 6000
    rng = np.random.default_rng(3)
    words = [f"tool{w}" for w in "abcdefghijklmnopqrstuvwxyz"]
    pool = [" ".join(rng.choice(words, 3)) for _ in range(1500)]  # 1,500 queries, each repeated
    frame = pd.DataFrame({"query": rng.choice(pool, n), "num": rng.normal(size=n)})
    assert frame["query"].nunique() < 0.5 * n
    prep = Prep().fit(frame)
    assert prep.prose == ("query",)
    assert "query" in prep._level_at.values()  # the whole query is a level too
    # a label that repeats with a few hundred levels stays a label
    few = pd.DataFrame({"label": rng.choice(pool[:300], n), "num": rng.normal(size=n)})
    assert Prep().fit(few).prose == ()


def test_a_name_of_three_words_that_is_different_in_every_row_is_prose():
    n = 300
    surnames = ["Braund", "Cumings", "Heikkinen", "Futrelle", "Allen", "Moran", "McCarthy"]
    names = [f"{surnames[i % 7]}{i}, Mr. Owen Harris" for i in range(n)]
    frame = pd.DataFrame({"name": names, "num": range(n)})
    assert Prep().fit(frame).prose == ("name",)


def test_text_view_is_the_linear_view_plus_the_text_of_each_prose_column():
    frame = _posts()
    frame.loc[3, "post"] = None
    prep = Prep().fit(frame)
    view = prep.text(frame)
    linear = prep.linear(frame)
    at = prep.feature_names.index("post")
    name = f"f{at}_t"
    kept = [c for c in linear.columns if int(c[1:].split("_")[0]) != at]  # nothing of the text
    assert list(view.columns) == [*kept, name]
    assert view[name].iloc[0] == frame["post"].iloc[0] and view[name].iloc[3] == ""
    assert Prep().fit(frame.drop(columns=["post"])).prose == ()


# --- frequency encoding of unseen values ----------------------------------------------


def _names(n, start=0):
    """Near-unique strings: most values occur once, every twentieth twice."""
    return [f"name-{start + i // 2 if i % 20 == 0 else start + i}" for i in range(n)]


def _repeated(n=5200, start=0):
    """260 levels, each in 20 rows: no value is seen once."""
    return [f"level-{start + i % 260}" for i in range(n)]


def _with(values, n):
    return pd.DataFrame({"x": RNG.normal(size=n), "name": values})


def test_an_unseen_string_gets_the_share_of_the_rarest_value_in_every_view():
    train = _with(_names(1000), 1000)
    prep = Prep().fit(train)
    new = pd.DataFrame({"x": [0.0, 0.0, 0.0], "name": ["new-1", "new-2", None]})
    at = prep.feature_names.index("name")
    rarest = 1 / len(train)  # a value seen once
    for view in (prep.tree(new), prep.dense(new)):
        assert view.iloc[:2, at].tolist() == [rarest, rarest]
    assert np.isnan(prep.tree(new).iloc[2, at])  # missing stays missing
    assert prep.dense(new).iloc[2, at] == prep._medians[f"f{at}"]
    repeating = _with(_repeated(), 5200)
    assert Prep().fit(repeating)._unseen == {"name": 20 / 5200}


@pytest.mark.parametrize(
    ("train", "new"),
    [
        (_with(_names(1000), 1000), _with([f"new-{i}" for i in range(500)], 500)),
        (_with(_repeated(), 5200), _with([f"new-{i}" for i in range(500)], 500)),
    ],
    ids=["near-unique", "every-level-repeats"],
)
def test_unseen_strings_stay_inside_the_training_range_of_the_linear_and_dense_views(train, new):
    prep = Prep().fit(train)
    at = prep.feature_names.index("name")
    seen, fresh = prep.linear(train)[f"f{at}"], prep.linear(new)[f"f{at}"]
    assert fresh.min() >= seen.min() and fresh.max() <= seen.max()
    assert fresh.abs().max() < 4  # far from the clip at LINEAR_CLIP
    dense_seen, dense_new = prep.dense(train)[f"f{at}"], prep.dense(new)[f"f{at}"]
    assert dense_new.min() >= dense_seen.min() and dense_new.max() <= dense_seen.max()


def test_a_linear_model_of_unrelated_names_predicts_all_new_names_like_old_ones():
    from sklearn.linear_model import LogisticRegression

    n = 2000
    train = pd.DataFrame({"name": _names(n)})
    y = RNG.integers(0, 2, n)  # unrelated to the name
    prep = Prep().fit(train)
    model = LogisticRegression().fit(prep.linear(train), y)
    old = model.predict_proba(prep.linear(train))[:, 1]
    new = model.predict_proba(prep.linear(pd.DataFrame({"name": _names(n, start=10**6)})))[:, 1]
    assert abs(new.mean() - old.mean()) < 0.02


def test_views_without_frequency_columns_do_not_read_the_unseen_share():
    frame = _frame().drop(columns=["ids"])
    prep = Prep().fit(frame)
    assert prep.frequencies == {} and prep._unseen == {}
    views = [prep.tree(frame), prep.catboost(frame), prep.dense(frame), prep.linear(frame)]
    del prep.__dict__["_unseen"]  # what a model pickled without the field looks like
    again = [prep.tree(frame), prep.catboost(frame), prep.dense(frame), prep.linear(frame)]
    for view, same in zip(views, again, strict=True):
        pd.testing.assert_frame_equal(view, same)


def test_a_prep_pickled_without_the_unseen_share_still_loads_and_keeps_zero():
    train = _with(_names(1000), 1000)
    prep = Prep().fit(train)
    assert prep._unseen == {"name": 1 / len(train)}
    del prep.__dict__["_unseen"]
    loaded = pickle.loads(pickle.dumps(prep))
    assert loaded._unseen == {}
    new = pd.DataFrame({"x": [0.0], "name": ["new-1"]})
    assert loaded.tree(new).iloc[0, loaded.feature_names.index("name")] == 0.0


def _days(start, n):
    return pd.DataFrame({"when": pd.date_range(start, periods=n).strftime("%Y-%m-%d")})


def _ordinal_in_linear_view(prep, frame):
    position = f"f{prep.feature_names.index('when__ordinal')}"
    return position in prep.linear(frame).columns


def test_the_linear_view_has_no_epoch_seconds_when_the_year_is_the_same_on_every_row():
    year = _days("2016-01-01", 360)
    prep = Prep().fit(year)
    assert not _ordinal_in_linear_view(prep, year)
    assert "when__ordinal" in prep.feature_names
    assert prep.tree(year).shape[1] == len(prep.feature_names)  # trees keep every part
    assert prep.linear(year).shape[1] == prep.linear_width


def test_the_linear_view_keeps_epoch_seconds_when_the_data_covers_two_years():
    two = _days("2015-07-01", 500)
    assert _ordinal_in_linear_view(Prep().fit(two), two)


def test_a_linear_model_fitted_within_one_year_stays_in_range_in_the_next_january():
    from sklearn.linear_model import Ridge

    year = _days("2016-01-01", 360)
    month = pd.to_datetime(year["when"]).dt.month.to_numpy()
    y = 2.0 + 0.3 * np.sin(month * np.pi / 6)
    prep = Prep().fit(year)
    model = Ridge(alpha=1e-3).fit(prep.linear(year), y)
    ahead = prep.linear(_days("2017-01-01", 31))
    assert np.abs(model.predict(ahead)).max() < 5  # with the epoch seconds it is about -17


def test_epoch_seconds_are_found_by_position_not_by_a_column_name():
    year = _days("2016-01-01", 360)
    year.insert(0, "when__year", np.where(np.arange(360) < 180, 2000, 2001))  # a user column
    prep = Prep().fit(year)
    assert not _ordinal_in_linear_view(prep, year)


def test_a_view_of_very_many_columns_is_joined_into_few_blocks_so_slicing_rows_stays_fast():
    X = pd.DataFrame(RNG.normal(size=(30, 2100)), columns=[f"c{i}" for i in range(2100)])
    X["flag"] = RNG.choice([True, False], size=30)
    X["when"] = pd.date_range("2024-01-01", periods=30, freq="D")
    prep = Prep().fit(X)
    for view in (prep.tree(X), prep.catboost(X), prep.dense(X)):
        assert view._mgr.nblocks < 10  # a block per column took 0.5 s per slice at 50,000


def test_whole_numbers_that_all_read_as_dates_are_found_and_other_numbers_are_not():
    rng = np.random.default_rng(0)
    days = pd.Timestamp("2021-01-01") + pd.to_timedelta(rng.integers(0, 400, 500), unit="D")
    ymd = days.strftime("%Y%m%d").astype("int64")
    assert integer_date_format(pd.Series(ymd)) == "%Y%m%d"
    hours = pd.Timestamp("2014-10-21") + pd.to_timedelta(rng.integers(0, 240, 500), unit="h")
    assert integer_date_format(pd.Series(hours.strftime("%y%m%d%H").astype("int64"))) == "%y%m%d%H"
    assert integer_date_format(pd.Series(hours.strftime("%Y%m%d%H").astype("int64"))) == "%Y%m%d%H"
    assert integer_date_format(pd.Series(rng.integers(10_000_000, 99_999_999, 500))) is None  # ids
    assert integer_date_format(pd.Series(rng.integers(0, 50, 500))) is None  # small numbers
    assert integer_date_format(pd.Series(ymd[:5].repeat(100))) is None  # five values: codes
    assert integer_date_format(pd.Series(ymd.astype(float))) is None  # only integer columns


def test_emptier_reports_a_column_filled_in_training_and_mostly_empty_in_new_rows():
    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame(
        {
            "lag": rng.normal(size=n),
            "sparse": np.where(rng.random(n) < 0.3, 1.0, np.nan),
            "c": rng.choice(["a", "b"], n),
            "n": rng.normal(size=n),
        }
    )
    prep = Prep().fit(df)
    assert prep.fill["lag"] == 1.0 and 0.1 < prep.fill["sparse"] < 0.5
    new = df.head(50).assign(lag=np.nan, sparse=np.nan, c=None)
    found = prep.emptier(new)
    # "sparse" was never well filled; the others lost everything
    assert [column for column, _, _ in found] == ["lag", "c"]
    assert all(trained == 1.0 and now == 0.0 for _, trained, now in found)
    assert prep.emptier(df.head(9).assign(lag=np.nan)) == []  # too few rows to say
    assert prep.emptier(df) == []
