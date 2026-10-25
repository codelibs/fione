import functools
import itertools
import time

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import (
    load_breast_cancer,
    load_diabetes,
    load_digits,
    load_iris,
    make_classification,
    make_regression,
)

from fione.data import profile as profile_module
from fione.data.frames import change_column_type
from fione.data.profile import (
    CORRELATED,
    LEAK_STRONG,
    ORDERED_BY_TARGET,
    PREDICTS_ALONE,
    SCORE_REASONS,
    LeakCheck,
    flag_scores,
    leak_check,
    profile_dataset,
    single_column_score,
)


def _col(profile, name):
    return next(c for c in profile.columns if c.name == name)


def _kind(series: pd.Series) -> str:
    return _col(profile_dataset(series.to_frame("x")), "x").kind


RNG = np.random.default_rng(0)


# --- kind inference -------------------------------------------------------


def test_unique_per_row_int_is_id():
    assert _kind(pd.Series(range(100))) == "id"


def test_unique_per_row_string_is_id():
    assert _kind(pd.Series([f"u{i}" for i in range(100)])) == "id"


def test_unique_float_is_numeric_not_id():
    assert _kind(pd.Series(RNG.normal(size=100))) == "numeric"


def test_unique_values_below_twenty_rows_are_not_id():
    assert _kind(pd.Series(range(19))) == "numeric"


def test_single_value_is_constant():
    assert _kind(pd.Series([7] * 50)) == "constant"


def test_all_null_is_constant_with_full_missing_rate():
    p = profile_dataset(pd.DataFrame({"x": [None] * 10, "y": range(10)}))
    col = _col(p, "x")
    assert col.kind == "constant"
    assert col.missing_rate == 1.0
    assert col.n_unique == 0


def test_single_value_plus_nulls_is_constant():
    assert _kind(pd.Series(["a", None, "a", None])) == "constant"


def test_bool_is_categorical():
    assert _kind(pd.Series([True, False] * 50)) == "categorical"


def test_datetime_dtype_is_datetime():
    assert _kind(pd.Series(pd.date_range("2024-01-01", periods=50))) == "datetime"


def test_date_strings_are_datetime():
    assert _kind(pd.Series(["2024-01-01", "2024-02-15", "2024-03-30"] * 10)) == "datetime"


def test_mostly_date_strings_are_datetime_but_mostly_garbage_is_not():
    ok = [f"2024-01-{d % 28 + 1:02d}" for d in range(100)]
    assert _kind(pd.Series(ok[:97] + ["n/a", "tbd", "?"])) == "datetime"
    assert _kind(pd.Series(ok[:90] + ["n/a"] * 10)) != "datetime"


def test_date_strings_without_separator_are_not_datetime():
    assert _kind(pd.Series(["20240101", "20240102"] * 10)) != "datetime"


def test_small_integer_codes_are_categorical():
    assert _kind(pd.Series([0, 1] * 100)) == "categorical"
    assert _kind(pd.Series([1, 2, 3, 4, 5] * 40)) == "categorical"


def test_integers_with_many_distinct_values_are_numeric():
    assert _kind(pd.Series(RNG.integers(0, 1000, size=500))) == "numeric"
    # few distinct values but too high a ratio (n_unique/non-null > 0.05)
    assert _kind(pd.Series([1, 2, 3, 4, 5] * 4)) == "numeric"


def test_low_cardinality_strings_are_categorical():
    assert _kind(pd.Series(["red", "green", "blue"] * 20)) == "categorical"


def test_few_distinct_strings_are_categorical_even_when_ratio_is_high():
    assert _kind(pd.Series(["a", "b", "c", "d", "e", "f"])) == "categorical"


def test_long_high_cardinality_strings_are_text():
    values = [f"this is a fairly long free text comment number {i % 400}" for i in range(500)]
    assert _kind(pd.Series(values)) == "text"


def test_short_mid_cardinality_strings_are_categorical():
    values = [f"c{i % 600}" for i in range(800)]
    assert _kind(pd.Series(values)) == "categorical"


def test_very_high_cardinality_short_strings_are_text():
    values = [f"c{i % 1500}" for i in range(2000)]
    assert _kind(pd.Series(values)) == "text"


def test_category_dtype_is_categorical():
    assert _kind(pd.Series(["a", "b", "c", "a"] * 10, dtype="category")) == "categorical"


# --- per-column details ----------------------------------------------------


def test_numeric_column_details():
    p = profile_dataset(pd.DataFrame({"x": np.arange(1.0, 101.0)}))
    c = _col(p, "x")
    assert c.kind == "numeric"
    assert c.missing_rate == 0.0
    assert c.n_unique == 100
    assert c.stats["min"] == 1.0 and c.stats["max"] == 100.0
    assert c.stats["mean"] == pytest.approx(50.5)
    assert c.stats["median"] == pytest.approx(50.5)
    assert set(c.stats) == {"mean", "std", "min", "q25", "median", "q75", "max"}
    assert len(c.histogram) == 20
    assert sum(n for _, n in c.histogram) == 100
    assert c.histogram[0][0] == 1.0
    assert c.top_values is None


def test_missing_rate():
    p = profile_dataset(pd.DataFrame({"x": [1.0, None, 3.0, None] * 5}))
    assert _col(p, "x").missing_rate == 0.5


def test_categorical_top_values_are_raw_cell_values_sorted_by_count():
    s = pd.Series(["a"] * 5 + ["b"] * 3 + ["c"] * 2 + [None])
    c = _col(profile_dataset(s.to_frame("x")), "x")
    assert c.top_values == [("a", 5), ("b", 3), ("c", 2)]
    assert c.stats is None and c.histogram is None and c.outlier_rate is None


def test_top_values_capped_at_ten():
    s = pd.Series([f"v{i}" for i in range(40)] * 3)
    c = _col(profile_dataset(s.to_frame("x")), "x")
    assert len(c.top_values) == 10


def test_integer_coded_categorical_keeps_numeric_stats():
    c = _col(profile_dataset(pd.DataFrame({"flag": [0, 1, 1, 1] * 25})), "flag")
    assert c.kind == "categorical"
    assert c.stats["mean"] == pytest.approx(0.75)
    assert c.top_values == [("1", 75), ("0", 25)]


def test_id_column_has_top_values():
    c = _col(profile_dataset(pd.DataFrame({"x": range(50)})), "x")
    assert c.kind == "id"
    assert len(c.top_values) == 10


def test_outlier_rate_iqr_rule():
    for values in ([1.0] * 98 + [1000.0] * 2, [1] * 98 + [1000] * 2):
        p = profile_dataset(pd.DataFrame({"x": values}))
        assert _col(p, "x").outlier_rate == pytest.approx(0.02)


def test_outlier_rate_zero_for_uniform_data():
    p = profile_dataset(pd.DataFrame({"x": np.arange(100.0)}))
    assert _col(p, "x").outlier_rate == 0.0


# --- dataset level ---------------------------------------------------------


def test_japanese_names_and_values():
    df = pd.DataFrame(
        {
            "年齢": np.arange(20.0, 120.0),
            "性別": ["男", "女"] * 50,
            "備考": ["あ"] * 100,
        }
    )
    p = profile_dataset(df, target="性別")
    assert [c.name for c in p.columns] == ["年齢", "性別", "備考"]
    assert _col(p, "性別").top_values == [("男", 50), ("女", 50)]
    assert _col(p, "備考").kind == "constant"


def test_does_not_mutate_input():
    df = pd.DataFrame({"a": [1.0, None, 3.0] * 10, "b": ["x", "y", None] * 10})
    before = df.copy()
    profile_dataset(df, target="b")
    pd.testing.assert_frame_equal(df, before)


def test_unknown_target_raises():
    with pytest.raises(ValueError, match="nope"):
        profile_dataset(pd.DataFrame({"a": [1, 2]}), target="nope")


def test_empty_dataframe():
    p = profile_dataset(
        pd.DataFrame({"a": pd.Series([], dtype=float), "b": pd.Series([], dtype=str)})
    )
    assert p.n_rows == 0 and p.n_cols == 2
    assert [c.kind for c in p.columns] == ["constant", "constant"]
    assert all(c.missing_rate == 0.0 for c in p.columns)
    assert p.correlations == [] and p.leak_suspects == []


def test_frame_without_columns():
    p = profile_dataset(pd.DataFrame())
    assert p.n_rows == 0 and p.n_cols == 0 and p.columns == []


def test_single_row_frame():
    p = profile_dataset(pd.DataFrame({"a": [1.0], "b": ["x"]}), target="b")
    assert p.n_rows == 1
    assert [c.kind for c in p.columns] == ["constant", "constant"]
    assert p.leak_suspects == []


# --- sampling --------------------------------------------------------------


def test_large_frame_is_sampled_deterministically(monkeypatch):
    df = pd.DataFrame({"x": np.arange(1000.0), "y": RNG.normal(size=1000)})
    seen = []
    original = pd.DataFrame.sample

    def spy(self, *args, **kwargs):
        out = original(self, *args, **kwargs)
        seen.append((len(self), len(out), kwargs.get("random_state")))
        return out

    monkeypatch.setattr(pd.DataFrame, "sample", spy)
    p = profile_dataset(df, sample_rows=100)
    assert p.n_rows == 1000
    assert seen == [(1000, 100, 0)]
    assert sum(n for _, n in _col(p, "y").histogram) == 100
    assert profile_dataset(df, sample_rows=100) == p


def test_frame_at_sample_limit_is_not_sampled(monkeypatch):
    df = pd.DataFrame({"x": np.arange(50.0)})
    monkeypatch.setattr(pd.DataFrame, "sample", lambda *a, **k: pytest.fail("sampled"))
    assert profile_dataset(df, sample_rows=50).n_rows == 50


# --- correlations ----------------------------------------------------------


def test_correlations_sorted_unique_and_capped():
    base = RNG.normal(size=300)
    df = pd.DataFrame({f"c{i}": base * (i + 1) + RNG.normal(size=300) * i for i in range(10)})
    df["const"] = 1.0
    df["label"] = ["a", "b", "c"] * 100
    corr = profile_dataset(df).correlations
    assert len(corr) == 20  # 10 numeric columns -> 45 pairs, capped
    assert [abs(r) for _, _, r in corr] == sorted((abs(r) for _, _, r in corr), reverse=True)
    pairs = [frozenset((a, b)) for a, b, _ in corr]
    assert len(set(pairs)) == len(pairs)
    assert all(a != b for a, b, _ in corr)
    assert not any("const" in (a, b) or "label" in (a, b) for a, b, _ in corr)


def test_correlation_value_and_sign():
    x = np.arange(100.0)
    df = pd.DataFrame({"x": x, "y": -x + RNG.normal(size=100) * 0.01})
    [(a, b, r)] = profile_dataset(df).correlations
    assert {a, b} == {"x", "y"}
    assert r == pytest.approx(-1.0, abs=1e-3)


def test_correlation_skips_nan_pairs():
    df = pd.DataFrame({"x": np.arange(100.0), "y": [np.nan] * 100})
    assert profile_dataset(df).correlations == []


# --- leak suspects ---------------------------------------------------------


def _suspects(df, target):
    return {s.column: s for s in profile_dataset(df, target=target).leak_suspects}


def test_target_copy_is_leak_suspect():
    t = np.array(["yes", "no", "maybe"] * 40)
    df = pd.DataFrame({"t": t, "copy": t, "noise": RNG.normal(size=120)})
    s = _suspects(df, "t")
    assert s["copy"].reason == "identical to target" and s["copy"].score == 1.0
    assert "noise" not in s and "t" not in s


def test_identical_numeric_copy_with_different_dtype():
    t = pd.Series([0, 1] * 60)
    df = pd.DataFrame({"t": t, "copy": t.astype(float)})
    assert "copy" in _suspects(df, "t")


def test_continuous_target_scaled_copy_flagged_by_correlation():
    t = RNG.normal(size=200)
    df = pd.DataFrame({"t": t, "double": t * 2, "other": RNG.normal(size=200)})
    s = _suspects(df, "t")
    assert s["double"].reason == "near-perfect correlation with target"
    assert s["double"].score == pytest.approx(1.0)
    assert "other" not in s


def test_value_determines_target():
    group = np.array(["a", "b", "c", "d"] * 30)
    target = pd.Series(group).map({"a": 1, "b": 2, "c": 3, "d": 4})
    df = pd.DataFrame({"t": target, "g": group, "r": RNG.choice(["p", "q", "r"], size=120)})
    s = _suspects(df, "t")
    assert s["g"].reason == "value determines target" and s["g"].score == 1.0
    assert "r" not in s


def test_value_determines_target_needs_enough_rows_and_low_cardinality():
    # 10 rows only: too few non-null rows
    df = pd.DataFrame({"t": [0, 1] * 5, "g": ["a", "b"] * 5})
    assert _suspects(df, "t") == {}
    # n_unique > 0.5 * rows
    t = RNG.integers(0, 3, size=40)
    df = pd.DataFrame({"t": t, "g": [f"k{i % 30}" for i in range(40)]})
    assert "g" not in _suspects(df, "t")


def test_id_and_constant_columns_are_never_leak_suspects():
    t = pd.Series(["a", "b"] * 30)
    df = pd.DataFrame({"t": t, "id": range(60), "const": 1, "id_s": [f"u{i}" for i in range(60)]})
    assert _suspects(df, "t") == {}


def test_leak_suspects_sorted_by_score_then_name():
    t = RNG.integers(0, 2, size=200).astype(float)
    df = pd.DataFrame(
        {
            "t": t,
            "z_copy": t,
            "a_copy": t,
            "near": t + RNG.normal(size=200) * 0.05,
        }
    )
    got = profile_dataset(df, target="t").leak_suspects
    assert [s.column for s in got][:2] == ["a_copy", "z_copy"]
    scores = [s.score for s in got]
    assert scores == sorted(scores, reverse=True)


def test_no_leak_suspects_without_target():
    t = np.array(["y", "n"] * 30)
    assert profile_dataset(pd.DataFrame({"t": t, "c": t})).leak_suspects == []


def test_leaks_ignore_rows_where_either_is_null():
    t = pd.Series(["a", "b", None, "a", "b"] * 12)
    c = pd.Series(["a", "b", "zzz", "a", "b"] * 12)
    assert "c" in _suspects(pd.DataFrame({"t": t, "c": c}), "t")


# --- out-of-fold single-column score ------------------------------------------


def _ticking_clock(step=2.0):
    ticks = itertools.count(0.0, step)
    return lambda: next(ticks)


def test_reason_strings_are_exact():
    # Task 6 maps these strings to UI keys
    assert PREDICTS_ALONE == "predicts the target on its own"
    assert ORDERED_BY_TARGET == "row order follows the target"
    assert CORRELATED == "near-perfect correlation with target"
    assert SCORE_REASONS == {CORRELATED, PREDICTS_ALONE, ORDERED_BY_TARGET}
    assert LEAK_STRONG == 0.99


def test_flag_rule():
    cls, reg = "classification", "regression"
    assert flag_scores({"petal": 0.968, "sepal": 0.916}, cls) == set()
    assert flag_scores({"copy": 0.971, "relationship": 0.777}, cls) == {"copy"}
    assert flag_scores({"a": 0.99, "b": 0.98, "c": 0.60}, cls) == {"a", "b"}
    # nothing below the threshold: compared with chance
    assert flag_scores({"a": 0.97, "b": 0.96}, cls) == {"a", "b"}
    assert flag_scores({"log": 0.984, "MedInc": 0.478}, reg) == {"log"}
    assert flag_scores({"x": 0.91, "y": 0.85}, reg) == set()
    assert flag_scores({"a": 0.95}, reg) == {"a"}
    assert flag_scores({"a": 0.99, "b": 0.89}, cls) == {"a"}  # exactly the margin
    # LEAK_STRONG is flagged whatever the baseline
    assert flag_scores({"leak": 0.99, "legit": 0.949}, cls) == {"leak"}
    assert flag_scores({"leak": 0.999, "legit": 0.90}, cls) == {"leak"}
    assert flag_scores({"r": 0.995, "legit": 0.89}, reg) == {"r"}
    # the documented cliff: below LEAK_STRONG, a strong legitimate column hides a leak
    assert flag_scores({"leak": 0.98, "legit": 0.90}, cls) == set()
    assert flag_scores({"leak": 0.98, "legit": 0.949}, cls) == set()
    assert flag_scores({}, cls) == set()


def _flagged(df, target):
    return {s.column: s for s in profile_dataset(df, target=target).leak_suspects}


def test_injected_classification_leaks():
    rng = np.random.default_rng(1)
    X, y = make_classification(n_samples=5000, random_state=0)
    n = len(y)
    df = pd.DataFrame(X, columns=[f"x{i}" for i in range(X.shape[1])])
    df["t"] = y
    df["flipped"] = np.where(rng.random(n) < 0.03, 1 - y, y)
    df["noisy"] = y + rng.normal(0, 0.1, n)
    df["threshold"] = np.where(y == 1, 1 + rng.random(n), rng.random(n))
    rank = np.empty(n, dtype=np.int64)
    rank[np.argsort(y + 0.5 * rng.random(n), kind="stable")] = np.arange(n)
    df["row_id"] = rank
    df["created"] = (pd.Timestamp("2024-01-01") + pd.to_timedelta(rank, unit="min")).astype(str)
    level = np.where(rng.random(n) < 0.99, y, 1 - y) * 750 + rng.integers(0, 750, n)
    df["code"] = [f"L{v}" for v in level]
    df["amount"] = np.where((y == 1) & (rng.random(n) < 0.98), rng.lognormal(3, 1, n), 0.0)
    found = _flagged(df, "t")
    for name in ("flipped", "noisy", "threshold", "row_id", "created", "code", "amount"):
        assert name in found, name
        assert found[name].reason in SCORE_REASONS, name
    assert found["row_id"].reason == ORDERED_BY_TARGET
    assert found["created"].reason == ORDERED_BY_TARGET
    assert found["threshold"].reason == PREDICTS_ALONE


def test_amount_for_most_positives_stays_below_the_threshold():
    """A documented miss: zero for every negative and for 20% of the positives caps the
    AUC at 0.8 + 0.2 / 2 = 0.9, below the threshold."""
    rng = np.random.default_rng(1)
    X, y = make_classification(n_samples=5000, random_state=0)
    df = pd.DataFrame({"t": y, "x": X[:, 0]})
    df["amount"] = np.where((y == 1) & (rng.random(len(y)) < 0.8), rng.lognormal(3, 1, len(y)), 0)
    score = single_column_score(df["amount"], "numeric", df["t"], "classification")
    assert score == pytest.approx(0.9, abs=0.02)
    assert "amount" not in _flagged(df, "t")


def test_injected_regression_leaks():
    rng = np.random.default_rng(1)
    X, t = make_regression(n_samples=5000, n_features=10, noise=10, random_state=0)
    t = t - t.min() + 1
    n = len(t)
    df = pd.DataFrame(X, columns=[f"x{i}" for i in range(X.shape[1])])
    df["t"] = t
    df["log"] = np.log(t) + rng.normal(0, 0.02, n)
    df["square"] = t**2 + rng.normal(0, 100, n)
    df["rounded"] = np.round(t).astype(int).astype(str)
    rank = np.empty(n, dtype=np.int64)
    rank[np.argsort(t, kind="stable")] = np.arange(n)
    df["rank_id"] = rank
    found = _flagged(df, "t")
    for name in ("log", "square", "rounded", "rank_id"):
        assert name in found, name
        assert found[name].reason in SCORE_REASONS, name
    assert found["rank_id"].reason == ORDERED_BY_TARGET
    assert found["rounded"].score >= 0.95
    assert not {f"x{i}" for i in range(X.shape[1])} & set(found)


@pytest.mark.parametrize("loader", [load_breast_cancer, load_digits, load_diabetes])
def test_clean_datasets_raise_no_score_suspects(loader):
    df = loader(as_frame=True).frame
    reasons = {s.reason for s in profile_dataset(df, target="target").leak_suspects}
    assert not reasons & {PREDICTS_ALONE, ORDERED_BY_TARGET}


def test_nominal_whole_number_codes_are_flagged():
    """Codes stored as integers or digit strings: quantile bins would mix unrelated codes, so
    whole numbers are also scored one bin per value."""
    rng = np.random.default_rng(1)
    X, y = make_classification(n_samples=5000, random_state=0)
    n = len(y)
    level = np.where(rng.random(n) < 0.99, y, 1 - y) * 750 + rng.integers(0, 750, n)
    code = rng.permutation(1500)[level]  # numerically unrelated to the class
    df = pd.DataFrame({"t": y, "x": X[:, 0], "int_code": code, "digit_code": code.astype(str)})
    df["float_code"] = df["int_code"].astype(float)
    found = _flagged(df, "t")
    for name in ("int_code", "digit_code", "float_code"):
        assert found[name].reason == PREDICTS_ALONE, name
        assert found[name].score >= 0.96, name


def _breast_cancer_with_copy(flipped: int) -> pd.DataFrame:
    """breast_cancer plus its target with ``flipped`` rows flipped, as text so that Pearson
    does not catch it. The best real column scores 0.945, just below the threshold."""
    df = load_breast_cancer(as_frame=True).frame
    copy = df["target"].to_numpy().copy()
    rows = np.random.default_rng(0).choice(len(df), flipped, replace=False)
    copy[rows] = 1 - copy[rows]
    df["copy"] = copy.astype(str)
    return df


def test_strong_leak_beside_a_strong_legitimate_column_is_flagged():
    found = _flagged(_breast_cancer_with_copy(1), "target")  # scores 0.998
    assert found["copy"].reason == PREDICTS_ALONE and found["copy"].score >= LEAK_STRONG


def test_flipped_copy_beside_a_strong_column_is_a_documented_miss():
    """Beside a column at 0.945 a leak needs LEAK_STRONG. A copy with 2% of its rows flipped
    scores about 0.978 and is not flagged (1% flipped: about 0.987, also missed)."""
    df = _breast_cancer_with_copy(11)
    score = single_column_score(df["copy"], "categorical", df["target"], "classification")
    assert 0.95 <= score <= LEAK_STRONG - 0.01
    assert "copy" not in _flagged(df, "target")


def test_score_bins_give_missing_values_a_bin_of_their_own():
    bins = profile_module._quantile_bins(np.array([np.nan, 1.0, 2.0, 3.0, np.nan]))
    assert bins[0] == bins[4]
    assert bins[0] not in bins[1:4]
    assert len(set(bins[1:4])) == 3
    codes = profile_module._value_bins(pd.Series(["a", None, "b", "a", None]))
    assert codes[1] == codes[4] and codes[1] not in (codes[0], codes[2])
    assert codes[0] == codes[3] != codes[2]


def test_few_rows_skip_the_score():
    p = profile_dataset(load_iris(as_frame=True).frame, target="target")
    assert not {s.reason for s in p.leak_suspects} & {PREDICTS_ALONE, ORDERED_BY_TARGET}
    assert p.leak_partial is False


def test_time_budget_sets_partial(monkeypatch):
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 300)
    df = pd.DataFrame({"t": y, **{f"c{i}": y + rng.normal(0, 0.1, 300) for i in range(5)}})
    columns = profile_dataset(df).columns
    check = leak_check(df, columns, "t", clock=_ticking_clock())
    assert isinstance(check, LeakCheck)
    assert check.partial is True
    assert 1 <= len(check.suspects) < 5  # the clock ran out before every column was scored
    unhurried = leak_check(df, columns, "t", clock=lambda: 0.0)
    assert unhurried.partial is False and len(unhurried.suspects) == 5
    monkeypatch.setattr(
        profile_module, "leak_check", functools.partial(leak_check, clock=_ticking_clock())
    )
    assert profile_dataset(df, target="t").leak_partial is True


def test_exact_reason_wins():
    rng = np.random.default_rng(0)
    t = rng.integers(0, 2, 400)
    df = pd.DataFrame({"t": t, "same": t, "x": rng.normal(size=400)})
    got = [s for s in profile_dataset(df, target="t").leak_suspects if s.column == "same"]
    assert [s.reason for s in got] == ["identical to target"]


def test_correlated_column_is_listed_once():
    rng = np.random.default_rng(0)
    t = rng.normal(size=1000)
    df = pd.DataFrame({"t": t, "double": 2 * t, "x": rng.normal(size=1000)})
    got = [s for s in profile_dataset(df, target="t").leak_suspects if s.column == "double"]
    assert [s.reason for s in got] == [CORRELATED]


def test_high_cardinality_noise_scores_near_chance():
    rng = np.random.default_rng(0)
    n = 10_000
    t = pd.Series(rng.integers(0, 2, n))
    code = pd.Series([f"k{v}" for v in rng.integers(0, 5000, n)])
    assert single_column_score(code, "categorical", t, "classification") <= 0.6


def test_score_is_out_of_fold_and_deterministic():
    rng = np.random.default_rng(0)
    t = pd.Series(rng.integers(0, 2, 2000))
    unique = pd.Series([f"u{i}" for i in range(2000)])  # in-sample this would score 1.0
    assert single_column_score(unique, "id", t, "classification") == pytest.approx(0.5, abs=0.05)
    x = pd.Series(t + rng.normal(0, 1, 2000))
    first = single_column_score(x, "numeric", t, "classification")
    assert first == single_column_score(x, "numeric", t, "classification")
    assert 0.6 < first < 0.9


def test_score_of_missing_values_multiclass_and_constant_target():
    rng = np.random.default_rng(0)
    t = pd.Series(rng.integers(0, 3, 1000))
    # missing exactly where the class is 2: missingness reveals that class
    s = pd.Series(np.where(t == 2, np.nan, rng.normal(size=1000)))
    assert single_column_score(s, "numeric", t, "classification") > 0.6
    assert single_column_score(s, "numeric", pd.Series(np.ones(1000)), "regression") is None


def test_score_of_datetimes_with_time_zone_and_missing_values():
    rng = np.random.default_rng(0)
    t = pd.Series(rng.integers(0, 2, 1000))
    stamps = pd.Series(pd.Timestamp("2024-01-01", tz="Asia/Tokyo") + pd.to_timedelta(t, "D"))
    stamps[::50] = pd.NaT
    assert single_column_score(stamps, "datetime", t, "classification") > 0.95


def test_large_frames_are_sampled_for_the_score(monkeypatch):
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 3000)
    df = pd.DataFrame({"t": y, "near": y + rng.normal(0, 0.1, 3000)})
    columns = profile_dataset(df).columns
    sizes = []
    real = profile_module.single_column_score

    def spy(s, kind, t, task, **kw):
        sizes.append(len(s))
        return real(s, kind, t, task, **kw)

    monkeypatch.setattr(profile_module, "single_column_score", spy)
    first = leak_check(df, columns, "t", max_rows=1000).suspects
    assert sizes == [1000]
    assert first and first == leak_check(df, columns, "t", max_rows=1000).suspects


@pytest.mark.timing
def test_leak_check_of_21_columns_and_10k_rows_takes_at_most_3_seconds():
    rng = np.random.default_rng(0)
    n = 10_000
    data = {f"f{i}": rng.normal(size=n) for i in range(15)}
    data.update({f"c{i}": rng.choice([f"v{j}" for j in range(50)], size=n) for i in range(5)})
    created = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.permutation(n), unit="min")
    data["created"] = created.astype(str)
    data["t"] = rng.integers(0, 2, n)
    df = pd.DataFrame(data)
    columns = profile_dataset(df).columns
    start = time.perf_counter()
    check = leak_check(df, columns, "t", time_budget=60.0)
    assert time.perf_counter() - start <= 3.0
    assert check.partial is False


# --- speed -----------------------------------------------------------------


def test_profile_wide_frame_is_fast():
    import time

    n = 200_000
    data = {f"f{i}": RNG.normal(size=n) for i in range(20)}
    data.update({f"c{i}": RNG.choice(["a", "b", "c", "d"], size=n) for i in range(8)})
    data["id"] = np.arange(n)
    data["target"] = RNG.integers(0, 2, size=n)
    start = time.perf_counter()
    p = profile_dataset(pd.DataFrame(data), target="target")
    assert time.perf_counter() - start < 10  # generous bound; typical is well under 3s
    assert p.n_rows == n and p.n_cols == 30


# --- change_column_type ------------------------------------------------------


def test_change_to_categorical():
    df = pd.DataFrame({"a": ["x", "y", "x"]})
    out = change_column_type(df, "a", "categorical")
    assert isinstance(out["a"].dtype, pd.CategoricalDtype)
    assert not isinstance(df["a"].dtype, pd.CategoricalDtype)


def test_change_to_numeric_keeps_nulls():
    out = change_column_type(pd.DataFrame({"a": ["1", "2.5", None]}), "a", "numeric")
    assert out["a"].tolist()[:2] == [1.0, 2.5] and pd.isna(out["a"].iloc[2])


def test_change_to_numeric_bad_value_raises_and_names_column():
    df = pd.DataFrame({"価格": ["1", "abc", "x", None]})
    with pytest.raises(ValueError, match="2 values in '価格' cannot be converted to numeric"):
        change_column_type(df, "価格", "numeric")


def test_change_to_datetime():
    out = change_column_type(
        pd.DataFrame({"d": ["2024-01-01", "2024-02-03", None]}), "d", "datetime"
    )
    assert pd.api.types.is_datetime64_any_dtype(out["d"])
    assert pd.isna(out["d"].iloc[2])


def test_change_to_datetime_bad_value_raises():
    with pytest.raises(ValueError, match="1 values in 'd' cannot be converted to datetime"):
        change_column_type(pd.DataFrame({"d": ["2024-01-01", "oops"]}), "d", "datetime")


def test_change_to_text_preserves_missing():
    out = change_column_type(pd.DataFrame({"a": [1, 2, None]}), "a", "text")
    assert out["a"].iloc[0] == "1.0" and pd.isna(out["a"].iloc[2])
    out = change_column_type(
        pd.DataFrame({"a": pd.Series(["x", None], dtype="category")}), "a", "text"
    )
    assert out["a"].iloc[0] == "x" and pd.isna(out["a"].iloc[1])


def test_change_column_type_returns_copy():
    df = pd.DataFrame({"a": ["1", "2"], "b": [1, 2]})
    out = change_column_type(df, "a", "numeric")
    assert out is not df
    assert df["a"].tolist() == ["1", "2"]
    pd.testing.assert_series_equal(out["b"], df["b"])


def test_change_column_type_errors():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(KeyError):
        change_column_type(df, "zzz", "numeric")
    with pytest.raises(ValueError, match="bogus"):
        change_column_type(df, "a", "bogus")  # type: ignore[arg-type]


def test_profile_module_exports():
    assert hasattr(profile_module, "ColumnProfile")
    assert hasattr(profile_module, "DatasetProfile")
    assert hasattr(profile_module, "LeakSuspect")


# --- review round 1: timezones, sparse correlations, date heuristic ----------

MIXED_OFFSETS = ["2024-03-05T10:00:00-05:00", "2024-07-05T10:00:00-04:00"] * 10


def test_mixed_utc_offset_timestamps_profile_as_datetime():
    p = profile_dataset(pd.DataFrame({"ts": MIXED_OFFSETS, "n": np.arange(20.0)}))
    assert _col(p, "ts").kind == "datetime"


def test_change_to_datetime_handles_mixed_offsets_as_utc():
    out = change_column_type(pd.DataFrame({"ts": MIXED_OFFSETS}), "ts", "datetime")
    assert str(out["ts"].dt.tz) == "UTC"
    assert out["ts"].iloc[0] == pd.Timestamp("2024-03-05T15:00:00Z")


def test_change_to_datetime_with_mixed_offsets_still_rejects_garbage():
    with pytest.raises(ValueError, match="1 values in 'ts' cannot be converted to datetime"):
        change_column_type(pd.DataFrame({"ts": [*MIXED_OFFSETS, "oops"]}), "ts", "datetime")


def test_change_to_datetime_parses_japanese_dates():
    out = change_column_type(
        pd.DataFrame({"d": ["2024年3月5日", "2024年12月25日"]}), "d", "datetime"
    )
    assert out["d"].tolist() == [pd.Timestamp("2024-03-05"), pd.Timestamp("2024-12-25")]


def test_sparse_overlap_does_not_produce_spurious_correlation():
    x = np.full(100, np.nan)
    y = np.full(100, np.nan)
    x[:3], y[:3] = [1.0, 2.0, 3.0], [2.0, 4.0, 6.0]
    x[3:60] = RNG.normal(size=57)
    y[60:] = RNG.normal(size=40)
    assert profile_dataset(pd.DataFrame({"x": x, "y": y})).correlations == []


def test_fully_populated_perfect_correlation_is_reported():
    x = RNG.normal(size=50)
    [(a, b, r)] = profile_dataset(pd.DataFrame({"x": x, "y": 3 * x + 1})).correlations
    assert {a, b} == {"x", "y"} and r == pytest.approx(1.0)


@pytest.mark.parametrize(
    "values",
    [
        ["1-2", "3-4", "5-6", "2-7", "8-9", "1-9"] * 5,
        ["1/2", "3/4", "1/3", "2/3", "5/8", "7/8"] * 5,
        ["3:2", "1:0", "2:2", "0:0", "4:1", "1:1"] * 5,
        ["12-100", "13-200", "14-300", "15-400", "16-500", "17-600"] * 5,
        ["-1", "-2", "-3", "-4", "-5", "-6"] * 5,
        ["1.5", "2.5", "-3.5", "4.5", "5.5", "6.5"] * 5,
    ],
)
def test_number_like_strings_are_not_datetime(values):
    assert _kind(pd.Series(values)) != "datetime"


def test_mostly_null_column_of_pair_strings_is_not_datetime():
    assert _kind(pd.Series(["1-2", "3-4", None, None, None, None, None, None])) != "datetime"


def test_too_few_non_null_values_are_not_datetime():
    assert _kind(pd.Series(["2024-03-05", "2024-03-06", "2024-03-07", None, None])) != "datetime"


@pytest.mark.parametrize(
    "values",
    [
        ["2024-03-05", "2024-04-06", "2023-12-25", "2022-01-31", "2024-07-04", "2021-09-09"],
        ["2024/03/05", "2024/04/06", "2023/12/25", "2022/01/31", "2024/07/04", "2021/09/09"],
        [f"2024-03-05 10:11:{s:02d}" for s in range(6)],
        [
            "March 5, 2024",
            "April 6, 2023",
            "May 7, 2022",
            "June 8, 2021",
            "July 9, 2020",
            "Dec 1, 2019",
        ],
        [
            "2024年3月5日",
            "2024年4月6日",
            "2023年12月25日",
            "2022年1月31日",
            "2024年7月4日",
            "2021年9月9日",
        ],
        ["2023-01", "2023-02", "2023-03", "2023-04", "2023-05", "2023-06"],
    ],
)
def test_date_strings_are_datetime_across_formats(values):
    assert _kind(pd.Series(values * 5)) == "datetime"


def test_date_detection_samples_beyond_the_head_of_a_sorted_column():
    # head looks like dates, the rest like pairs: a head-only sample would say datetime
    values = ["2024-03-05"] * 1000 + ["1-2"] * 3000
    assert _kind(pd.Series(values)) != "datetime"
