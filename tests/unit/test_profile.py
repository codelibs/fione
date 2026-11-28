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

from fione.data import frames
from fione.data import profile as profile_module
from fione.data.frames import (
    change_column_type,
    is_day_first,
    is_time_counter,
    is_time_name,
    parse_datetimes,
)
from fione.data.profile import (
    CORRELATED,
    LEAK_STRONG,
    ORDERED_BY_TARGET,
    PREDICTS_ALONE,
    SCORE_REASONS,
    LeakCheck,
    flag_scores,
    leak_check,
    leak_code,
    profile_dataset,
    single_column_score,
    training_leak_suspects,
)


def _col(profile, name):
    return next(c for c in profile.columns if c.name == name)


def _kind(series: pd.Series) -> str:
    return _col(profile_dataset(series.to_frame("x")), "x").kind


RNG = np.random.default_rng(0)


# --- kind inference -------------------------------------------------------


def test_unique_per_row_int_is_id():
    assert _kind(pd.Series(range(100))) == "id"


def test_unique_whole_numbers_that_are_dates_are_not_ids():
    days = pd.date_range("2021-01-01", periods=100, freq="D")
    assert _kind(pd.Series(days.strftime("%Y%m%d").astype("int64"))) == "numeric"
    seconds = pd.Timestamp("2014-10-21") + pd.to_timedelta(np.arange(100) * 997, unit="s")
    assert _kind(pd.Series(seconds.strftime("%Y%m%d%H%M%S").astype("int64"))) == "numeric"
    assert _kind(pd.Series(RNG.permutation(10**13 + np.arange(100) * 7919))) == "id"


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


def test_single_value_plus_nulls_is_a_flag_not_constant():
    # Yes or blank: the gaps tell the rows apart, as the engine's own rule does
    for values in (["Yes", None, "Yes", None], [1.0, None, 1.0, None], [True, None, True, None]):
        assert _kind(pd.Series(values)) == "categorical"
    p = profile_dataset(pd.DataFrame({"flag": ["Yes", None] * 30, "same": ["Yes"] * 60}))
    assert [(c.name, c.kind) for c in p.columns] == [("flag", "categorical"), ("same", "constant")]
    assert _col(p, "flag").top_values == [("Yes", 30)] and _col(p, "flag").missing_rate == 0.5


def test_a_flag_on_two_rows_that_match_the_target_is_not_a_leak():
    df = pd.DataFrame({"y": [1, 0, 1, 0] * 25, "flag": [1.0, None, 1.0] + [None] * 97})
    assert profile_dataset(df, target="y").leak_suspects == []


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


def test_a_different_text_in_every_row_with_its_short_values_first_is_text_not_an_id():
    rng = np.random.default_rng(7)
    words = ["film", "story", "actor", "scene", "funny", "dull", "moving", "plot", "cast"]
    short = [" ".join(rng.choice(words, 1 + i % 2)) + f" {i}" for i in range(1200)]
    long = [" ".join(rng.choice(words, 9)) + f" {i}" for i in range(1800)]
    assert _kind(pd.Series(short + long)) == "text"


def test_an_aligned_sequence_of_one_length_is_text_and_a_long_hex_hash_an_id():
    import hashlib

    rng = np.random.default_rng(8)
    base = rng.choice(list("ACGT"), 297)
    rows = []
    for _ in range(300):
        seq = base.copy()
        seq[rng.choice(297, 12, replace=False)] = rng.choice(list("ACGTRYKMN"), 12)
        rows.append("".join(seq))
    assert _kind(pd.Series(rows)) == "text"
    hashes = [hashlib.sha512(rng.bytes(8)).hexdigest() for _ in range(300)]
    assert _kind(pd.Series(hashes)) == "id"


def test_number_lists_are_a_list_however_often_they_repeat():
    rng = np.random.default_rng(3)
    values = [str(rng.integers(0, 256, 40).tolist()) for _ in range(300)]
    assert _kind(pd.Series(values)) == "list"
    values[1] = values[0]  # one repeat made such a column text, all different an id
    assert _kind(pd.Series(values)) == "list"
    tags = pd.Series([f'["pool", "garden", "room {i}"]' for i in range(300)])
    assert _kind(tags) != "list"


def test_a_prose_column_reports_its_mean_length_and_other_columns_do_not():
    text = [f"this is a fairly long free text comment number {i % 400}" for i in range(500)]
    unique = [f"every comment here is different, and this is number {i}" for i in range(500)]
    codes = [f"AB{i % 400}-XY" for i in range(500)]
    df = pd.DataFrame({"t": text, "u": unique, "k": codes, "n": range(500), "c": ["a", "b"] * 250})
    columns = {c.name: c for c in profile_dataset(df).columns}
    assert columns["t"].kind == "text" and columns["u"].kind == "text"  # different, yet prose
    assert columns["t"].mean_length == pytest.approx(np.mean([len(v) for v in text]))
    assert columns["u"].mean_length == pytest.approx(np.mean([len(v) for v in unique]))
    assert [columns[n].mean_length for n in "knc"] == [None, None, None]
    assert columns["k"].kind != "text"
    ids = pd.DataFrame({"i": [f"AB{i:05d}-XY" for i in range(500)]})
    assert profile_dataset(ids).columns[0].kind == "id"  # all different codes stay ids


def test_short_mid_cardinality_strings_are_categorical():
    values = [f"c{i % 600}" for i in range(800)]
    assert _kind(pd.Series(values)) == "categorical"


def test_very_high_cardinality_short_strings_are_text():
    values = [f"c{i % 1500}" for i in range(2000)]
    assert _kind(pd.Series(values)) == "text"


def test_a_short_text_that_repeats_with_many_values_is_text_and_one_with_few_is_categorical():
    rng = np.random.default_rng(0)
    words = [f"tool{w}" for w in "abcdefghijklmnopqrstuvwxyz"]
    pool = [" ".join(rng.choice(words, 3)) for _ in range(1500)]  # queries, each one repeated
    assert _kind(pd.Series(rng.choice(pool, 6000))) == "text"
    assert _kind(pd.Series(rng.choice(pool[:300], 6000))) == "categorical"


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


def test_correlations_are_left_out_of_a_table_with_very_many_numeric_columns(monkeypatch):
    monkeypatch.setattr(profile_module, "_CORR_MAX_COLUMNS", 5)
    base = RNG.normal(size=100)
    df = pd.DataFrame({f"c{i}": base + RNG.normal(size=100) for i in range(6)})
    assert profile_dataset(df).correlations == []
    assert profile_dataset(df.iloc[:, :5]).correlations != []


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


def test_value_determines_target_ignores_a_mostly_zero_target_with_unique_rows():
    # ties only at 0, where the target is 0; the few non-zero targets sit on rows of their own
    flagged = 0
    for seed in range(20):
        rng = np.random.default_rng(seed)
        n = 5000
        repeat = rng.random(n) < 0.4
        span = np.where(repeat, np.round(rng.exponential(30, n) * 86400) / 86400, 0.0)
        target = np.where(repeat & (rng.random(n) < 0.01), np.round(rng.lognormal(3, 1, n), 2), 0.0)
        df = pd.DataFrame({"t": target, "span": span, "x": rng.normal(size=n)})
        flagged += "span" in _suspects(df, "t")
    assert flagged <= 1


@pytest.mark.parametrize("share", [0.002, 0.0005])
def test_a_text_column_that_holds_the_target_on_the_non_zero_rows_is_flagged(share):
    # repeated texts on the zero rows, a text of its own that spells the target on the others
    rng = np.random.default_rng(0)
    n = 10_000
    nonzero = rng.random(n) < share
    target = np.where(nonzero, np.round(rng.lognormal(4, 1, n), 2), 0.0)
    texts = np.array(["pv=1", "pv=2", "pv=3"], dtype=object)[rng.integers(0, 3, n)]
    texts[nonzero] = [f"pv=1;revenue={v}" for v in target[nonzero]]
    df = pd.DataFrame({"t": target, "totals": texts, "x": rng.normal(size=n)})
    assert nonzero.sum() >= 2
    assert _suspects(df, "t")["totals"].reason == "value determines target"
    assert [s.column for s in training_leak_suspects(df.drop(columns="t"), df["t"])] == ["totals"]


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


def test_leak_codes_name_the_reason():
    assert leak_code(CORRELATED) == "leak_correlated"
    assert leak_code(ORDERED_BY_TARGET) == "leak_ordered"
    assert leak_code("anything else") == "leak_other"


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


def _three_class_frame(share=0.2, n=3000, seed=0):
    """A label in {0, 1, 2} where class 2 has the given share of the rows."""
    rng = np.random.default_rng(seed)
    label = rng.choice([0, 1, 2], n, p=[(1 - share) * 0.6, (1 - share) * 0.4, share])
    df = pd.DataFrame({"label": label, "x": rng.normal(size=n) + label * 0.3})
    return df, label, rng


@pytest.mark.parametrize("share", [0.2, 0.03])
def test_column_present_only_for_one_class_is_flagged_in_a_three_class_target(share):
    df, label, rng = _three_class_frame(share)
    df["extra_value"] = np.where(label == 2, rng.lognormal(3, 1, len(df)), np.nan)
    df["extra_code"] = np.where(label == 2, rng.integers(1, 40, len(df)).astype(str), None)
    # the mean one-vs-rest AUC is far below the threshold, the AUC for class 2 alone is 1.0
    found = _flagged(df, "label")
    for name in ("extra_value", "extra_code"):
        assert found[name].reason == PREDICTS_ALONE and found[name].score >= LEAK_STRONG, name
    assert "x" not in found


def test_column_missing_only_for_one_class_is_flagged_in_a_three_class_target():
    df, label, rng = _three_class_frame()
    df["extra_value"] = np.where(label == 0, np.nan, rng.normal(size=len(df)))
    assert _flagged(df, "label")["extra_value"].reason == PREDICTS_ALONE


def test_strong_but_not_leaking_column_in_a_three_class_target_is_not_flagged():
    df, label, rng = _three_class_frame()
    # present for most of class 2 and for 5% of the others: its AUC for that class is about
    # 0.93, below LEAK_STRONG
    df["hint"] = np.where((label == 2) & (rng.random(len(df)) < 0.9), 1.0, np.nan)
    df.loc[(label != 2) & (rng.random(len(df)) < 0.05), "hint"] = 1.0
    assert single_column_score(df["hint"], "numeric", df["label"], "classification") < 0.9
    assert "hint" not in _flagged(df, "label")


def test_a_complete_column_that_separates_one_class_is_not_flagged_in_a_three_class_target():
    """No missing values, so only the mean one-vs-rest AUC counts, as for any strong feature."""
    df, label, _ = _three_class_frame()
    df["sensor"] = (label == 2) * 100.0 + np.random.default_rng(1).normal(size=len(df))
    assert "sensor" not in _flagged(df, "label")


def test_binary_score_is_unchanged_by_the_missing_indicator_rule():
    df, label, _ = _three_class_frame()
    top = pd.Series((label == 2).astype(int))
    present = pd.Series(np.where(label == 2, 1.0, np.nan))
    assert single_column_score(present, "numeric", top, "classification") >= LEAK_STRONG
    assert single_column_score(df["x"], "numeric", top, "classification") < 0.9


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


def test_dates_in_mixed_formats_are_read_value_by_value():
    mixed = pd.Series(["2024-01-05", "5 Mar 2024", "2024/02/03 10:00", "bad", None] * 4)
    parsed = parse_datetimes(mixed).iloc[:5]
    assert parsed.tolist()[:3] == [
        pd.Timestamp("2024-01-05"),
        pd.Timestamp("2024-03-05"),
        pd.Timestamp("2024-02-03 10:00"),
    ]
    assert parsed.isna().tolist() == [False, False, False, True, True]


def test_day_first_dates_are_read_by_their_fields():
    day_first = pd.Series(["25-12-2024", "02-10-2024", "13/01/2024"])
    assert is_day_first(day_first)
    assert parse_datetimes(day_first).tolist()[1] == pd.Timestamp("2024-10-02")
    month_first = pd.Series(["12/25/2024", "02/10/2024"])
    assert not is_day_first(month_first)
    assert parse_datetimes(month_first).tolist()[1] == pd.Timestamp("2024-02-10")
    assert not is_day_first(pd.Series(["2024-10-02", "2024-12-25"]))  # ISO
    assert not is_day_first(pd.Series(["01-02-2024", "03-04-2024"]))  # no field above 12


@pytest.fixture
def today_is_2026_06_15(monkeypatch):
    monkeypatch.setattr(frames, "_now", lambda: pd.Timestamp("2026-06-15"))


def test_dates_with_a_two_digit_year_are_dates_of_the_past(today_is_2026_06_15):
    short = pd.Series(["2/20/15", "5/1/68", "3/3/71", "12/31/99", "1/1/00", "7/4/38"] * 3)
    assert _kind(short) == "datetime"
    assert parse_datetimes(short).tolist()[:6] == [
        pd.Timestamp(d)
        for d in (
            "2015-02-20",
            "1968-05-01",
            "1971-03-03",
            "1999-12-31",
            "2000-01-01",
            "1938-07-04",
        )
    ]


def test_a_two_digit_year_moves_back_a_century_only_over_a_year_after_today(today_is_2026_06_15):
    dates = ["1/1/26", "12/31/26", "6/16/27", "6/17/27", "1/1/28", "1/1/25", "12/31/68"]
    years = parse_datetimes(pd.Series(dates * 3)).dt.year.tolist()[:7]
    assert years == [2026, 2026, 2027, 1927, 1928, 2025, 1968]  # up to 2027-06-16 is kept


def test_a_two_digit_year_is_read_alike_at_every_hour_of_the_day(monkeypatch):
    dates = pd.Series(["6/15/26 18:00", "6/16/27 23:00", "6/17/27 01:00"] * 3)
    for now in ("2026-06-15 00:00", "2026-06-15 10:00", "2026-06-15 23:59"):
        monkeypatch.setattr(frames, "_now", lambda now=now: pd.Timestamp(now))
        assert parse_datetimes(dates).dt.year.tolist()[:3] == [2026, 2027, 1927]
    monkeypatch.setattr(frames, "_now", lambda: pd.Timestamp("2026-06-16 00:01"))
    assert parse_datetimes(dates).dt.year.tolist()[:3] == [2026, 2027, 2027]  # a day later


def test_a_year_of_four_digits_is_never_moved(today_is_2026_06_15):
    future = pd.Series(["12/31/2040", "1/1/2030", "2/20/15", "5/1/1938", "3/3/71"] * 3)
    assert parse_datetimes(future).dt.year.tolist()[:5] == [2040, 2030, 2015, 1938, 1971]


def test_two_digit_years_with_a_time_a_dot_or_a_zone_are_read_alike(today_is_2026_06_15):
    assert parse_datetimes(
        pd.Series(["25.12.68 10:30", "02.10.15", "30.1.28"])
    ).dt.year.tolist() == [
        1968,
        2015,
        1928,
    ]
    zoned = pd.Series(["6/1/68 10:00 +0100", "6/1/15 10:00 +0900"])
    assert parse_datetimes(zoned).dt.year.tolist() == [1968, 2015]


def test_two_digit_years_keep_the_order_of_the_fields(today_is_2026_06_15):
    day_first = pd.Series(["25/12/68", "02/10/15", "13/01/99"] * 3)
    assert is_day_first(day_first)
    assert parse_datetimes(day_first).tolist()[:3] == [
        pd.Timestamp(d) for d in ("1968-12-25", "2015-10-02", "1999-01-13")
    ]
    month_first = pd.Series(["12/25/68", "02/10/15"] * 3)
    assert not is_day_first(month_first)
    assert parse_datetimes(month_first).tolist()[:2] == [
        pd.Timestamp("1968-12-25"),
        pd.Timestamp("2015-02-10"),
    ]


def test_columns_of_codes_that_are_not_dates_are_not_read_as_two_digit_years():
    rng = np.random.default_rng(0)
    for make in (
        lambda: f"{rng.integers(1, 5)}.{rng.integers(0, 60)}.{rng.integers(0, 200)}",  # version
        lambda: f"{rng.integers(1, 255)}.{rng.integers(1, 255)}.{rng.integers(1, 255)}",  # address
        lambda: f"{rng.integers(1, 31)}/{rng.integers(1, 31)}/{rng.integers(10, 99)}",  # code
        lambda: f"{rng.integers(0, 12)}/{rng.integers(0, 12)}/{rng.integers(10, 99)}",  # score
        lambda: f"{rng.integers(1, 9)}/{rng.integers(2, 9)}",  # fraction
    ):
        assert _kind(pd.Series([make() for _ in range(80)])) != "datetime"


def test_small_triples_of_scores_and_ratios_are_not_dates_but_spread_dates_are():
    rng = np.random.default_rng(0)
    for sep in "-/.":
        triples = [f"{rng.integers(1, 10)}{sep}{rng.integers(1, 10)}{sep}{rng.integers(20, 40)}"]
        triples += [f"{rng.integers(1, 10)}{sep}{rng.integers(1, 10)}{sep}34" for _ in range(99)]
        assert _kind(pd.Series(triples)) != "datetime"  # 3-1-20, 4/5/22, 1/2/34
        days = [f"{rng.integers(1, 13)}{sep}{rng.integers(1, 29)}{sep}{rng.integers(0, 99):02d}"]
        days += [f"{rng.integers(1, 13)}{sep}{rng.integers(1, 29)}{sep}15" for _ in range(99)]
        assert _kind(pd.Series(days)) == "datetime"  # a day above 12 in most of the values


def test_the_spread_of_days_gates_only_the_two_digit_year_signal():
    rng = np.random.default_rng(0)
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y"):  # four-digit years, every day at most 12
        days = pd.Timestamp("2015-01-01") + pd.to_timedelta(rng.integers(0, 12, 100), unit="D")
        days += pd.to_timedelta(30 * rng.integers(0, 12, 100), unit="D")
        days = days[days.day <= 12]
        assert len(days) >= 20
        assert _kind(pd.Series(days.strftime(fmt))) == "datetime"
    mixed = [f"{rng.integers(1, 13)}/{rng.integers(1, 13)}/{rng.choice(['2015', '2016'])}"] * 30
    mixed += ["3/4/15"] * 2  # a few two-digit years in a column that has the signal anyway
    assert _kind(pd.Series(mixed)) == "datetime"


def test_dates_of_the_first_twelve_days_of_months_with_a_two_digit_year_are_not_detected():
    rng = np.random.default_rng(0)
    values = [f"{rng.integers(1, 13)}/{rng.integers(1, 13)}/15" for _ in range(100)]
    assert _kind(pd.Series(values)) != "datetime"  # no day above 12: a month, a day, or a ratio?
    values[::3] = [f"{rng.integers(1, 13)}/{rng.integers(13, 29)}/15" for _ in values[::3]]
    assert _kind(pd.Series(values)) == "datetime"  # a third of them have one


def test_a_column_of_two_and_four_digit_years_is_one_column_of_dates(today_is_2026_06_15):
    mixed = pd.Series(["2/20/15", "3/3/1971", "5/1/68", "7/4/2010"] * 5)
    assert _kind(mixed) == "datetime"
    assert parse_datetimes(mixed).dt.year.tolist()[:4] == [2015, 1971, 1968, 2010]


def test_reading_dates_does_not_depend_on_the_batch_or_the_order_of_values():
    month_first = pd.Series(["06/07/2012", "06/18/2012"])
    assert parse_datetimes(month_first, dayfirst=False).tolist()[0] == pd.Timestamp("2012-06-07")
    # a mixed-convention column, read month first as fitted: the same value in any batch
    for batch in (["06/07/2012"], ["25/07/2012", "06/07/2012"], ["06/07/2012", "25/07/2012"]):
        got = parse_datetimes(pd.Series(batch), dayfirst=False)
        assert got[batch.index("06/07/2012")] == pd.Timestamp("2012-06-07")
    # a value that starts with the year is never read day first
    day_first = parse_datetimes(pd.Series(["2012-06-07", "25-06-2012"]), dayfirst=True)
    assert day_first.tolist() == [pd.Timestamp("2012-06-07"), pd.Timestamp("2012-06-25")]
    alone = parse_datetimes(pd.Series(["2012-06-07"]), dayfirst=True)
    assert alone.tolist() == [pd.Timestamp("2012-06-07")]


def test_dates_keep_their_index_and_missing_values():
    s = pd.Series(["02-10-2012 09:00", None, "25-10-2012 10:00"], index=[5, 5, 9])
    out = parse_datetimes(s, dayfirst=True)
    assert out.index.tolist() == [5, 5, 9] and out.isna().tolist() == [False, True, False]


def test_month_names_alone_are_no_dates_and_do_not_break_the_profile():
    # Read alone, a month name is dated year 1, outside what a timestamp column holds.
    months = pd.Series(["may", "jun", "jul", "aug"] * 3000, name="month")
    assert parse_datetimes(months).isna().all()
    mixed = parse_datetimes(pd.Series(["2020-01-02", "may", "3/4/2021"]))
    assert mixed.notna().tolist() == [True, False, True]
    profile = profile_dataset(pd.DataFrame({"month": months, "y": range(len(months))}))
    assert profile.columns[0].kind == "categorical"


def test_training_leak_suspects_samples_rows_and_names_a_column_called_target():
    rng = np.random.default_rng(0)
    n = 30_000
    y = pd.Series(rng.integers(0, 2, n), index=np.arange(n) + 5, name="event")
    X = pd.DataFrame({"target": rng.normal(size=n)}, index=y.index)
    X["x"] = rng.normal(size=n)
    X["after"] = y + rng.normal(0, 0.1, n)
    X["empty"] = np.nan
    found = training_leak_suspects(X, y, max_rows=5_000)
    assert [s.column for s in found] == ["after"]
    assert training_leak_suspects(X.drop(columns="after"), y, max_rows=5_000) == []


def test_training_leak_suspects_stops_profiling_when_the_time_is_up():
    rng = np.random.default_rng(0)
    y = pd.Series(rng.integers(0, 2, 400))
    X = pd.DataFrame({"a": y + 0.0, "b": rng.normal(size=400)})
    ticks = itertools.count(0.0, 1.0)  # each look at the clock is one second
    assert [s.column for s in training_leak_suspects(X, y)] == ["a"]
    assert training_leak_suspects(X, y, time_budget=1.0, clock=lambda: next(ticks)) == []


@pytest.mark.parametrize(
    "name", ["date_id", "DayIdx", "week_no", "Day", "dateId", "time", "years", "step_2", "日付"]
)
def test_names_that_read_as_a_time(name):
    assert is_time_name(name)


@pytest.mark.parametrize(
    "name", ["id", "Id", "index", "row_id", "user_id", "idx", "weekday", "timestamp", "updated"]
)
def test_names_that_do_not_read_as_a_time(name):
    assert not is_time_name(name)


@pytest.mark.parametrize("name", ["date_id", "DayIdx", "week_no", "dateId", "time_id", "month num"])
def test_a_counter_that_repeats_over_rows_is_named_like_a_counter(name):
    assert is_time_counter(name, 0, 99, 100, repeated=True)


@pytest.mark.parametrize("name", ["Day", "YearBuilt", "AGE_DAYS", "years", "time", "days_since"])
def test_a_time_word_alone_is_a_counter_only_when_each_value_is_on_one_row(name):
    assert is_time_counter(name, 0, 99, 100)
    assert not is_time_counter(name, 0, 99, 100, repeated=True)


def test_an_id_column_of_whole_numbers_has_the_span_of_its_values():
    df = pd.DataFrame(
        {"a": np.arange(5, 45), "b": [f"k{i}" for i in range(40)], "c": np.arange(40.0)}
    )
    spans = {c.name: c.span for c in profile_dataset(df).columns}
    assert spans == {"a": 40, "b": None, "c": None}


def test_profile_of_a_column_equal_up_to_float_noise_does_not_fail():
    # a mean-scaled feature (the mean of 12 values each divided by their own mean) is 1 up to
    # rounding; its range is too small to cut into bins
    noise = 1.0 + np.array([0.0, 4e-16, -4e-16, 0.0] * 50)
    frame = pd.DataFrame({"x": noise, "y": np.arange(200.0)})
    column = next(c for c in profile_dataset(frame, "y").columns if c.name == "x")
    assert len(column.histogram) == 20 and sum(n for _, n in column.histogram) == 200


def _revenue(n=6000, seed=0, groups=("a", "b", "c", "d"), tiers=("x", "y", "z")):
    """Revenue = quantity x the unit price that the category and the tier fix (a currency and a
    period fix the rate of an amount), to 0.1 %."""
    rng = np.random.default_rng(seed)
    price = {(g, t): rng.uniform(1, 90) for g in groups for t in tiers}
    df = pd.DataFrame(
        {
            "category": rng.choice(groups, n),
            "tier": rng.choice(tiers, n),
            "quantity": rng.integers(1, 500, n).astype(float),
            "noise": rng.normal(size=n),
        }
    )
    unit = np.array([price[g, t] for g, t in zip(df.category, df.tier, strict=True)])
    df["revenue"] = df.quantity * unit * np.exp(rng.normal(0, 0.001, n))
    return df


def _derived(df, target="revenue", **kwargs):
    columns = [profile_module._profile_column(c, df[c]) for c in df.columns]
    return profile_module.derived_target(df, columns, target, **kwargs)[0]


def test_a_target_that_a_column_times_a_rate_of_two_categories_gives_is_named():
    found = profile_dataset(_revenue(), "revenue").derived
    assert found is not None and found.column == "quantity"
    assert set(found.keys) == {"category", "tier"} and found.share > 0.99


def test_one_category_is_named_alone_and_not_with_a_random_column_beside_it():
    rng = np.random.default_rng(0)
    df = _revenue(groups=tuple("abcdefgh"), tiers=("x",))
    df["junk"] = rng.choice(list("pqrstu"), len(df))
    found = _derived(df)
    assert found is not None and found.keys == ("category",)


def test_a_target_that_is_a_group_mean_with_noise_is_not_derived():
    rng = np.random.default_rng(0)
    df = _revenue()
    df["revenue"] = np.exp(rng.normal(3, 0.3, len(df))) * (1 + 0.5 * (df.category == "a"))
    assert _derived(df) is None
    # a price of a brand that does not depend on the quantity: the categories alone explain it
    df["revenue"] = df.category.map({"a": 10.0, "b": 25.0, "c": 40.0, "d": 90.0}) * np.exp(
        rng.normal(0, 0.001, len(df))
    )
    assert _derived(df) is None


def test_a_noisy_multiple_of_a_column_is_not_derived_by_a_key_that_adds_nothing():
    rng = np.random.default_rng(0)
    n = 20_000
    x = np.exp(rng.normal(3, 1, n))
    df = pd.DataFrame(
        {
            "x": x,
            "k1": rng.choice(list("abcde"), n),
            "k2": rng.choice(list("xyz"), n),
            "revenue": 1.1 * x * np.exp(rng.normal(0, 0.08, n)),
        }
    )
    assert _derived(df) is None  # the column is the target but for noise: not a rate of keys
    stores = df.assign(store=rng.choice([f"s{i}" for i in range(50)], n))
    assert _derived(stores) is None


def test_a_rate_of_a_key_is_found_only_with_20_rows_for_each_of_its_values():
    rng = np.random.default_rng(0)

    def table(n):
        k = rng.integers(0, 250, n)
        rate = np.exp(rng.normal(0, 1.5, 250))
        quantity = np.exp(rng.normal(3, 1.5, n))  # as spread as the rate: the key is no price alone
        df = pd.DataFrame({"key": [f"k{i}" for i in k], "quantity": quantity})
        return df.assign(revenue=quantity * rate[k])

    assert _derived(table(2500)) is None  # 10 rows each: too few to tell a rate from noise
    found = _derived(table(7500))  # 30 rows each
    assert found is not None and found.keys == ("key",)


def test_columns_of_more_than_300_values_are_names_and_not_keys():
    rng = np.random.default_rng(0)
    n = 9000
    k = rng.integers(0, 301, n)
    rate = rng.uniform(1, 90, 301)
    df = pd.DataFrame({"key": [f"k{i}" for i in k], "q": rng.integers(1, 500, n) * 1.0})
    df["revenue"] = df.q * rate[k]
    assert _derived(df) is None
    k = rng.integers(0, 300, n)
    assert _derived(df.assign(key=[f"k{i}" for i in k], revenue=df.q * rate[k])) is not None


def test_the_column_is_found_after_many_other_number_columns():
    df = _revenue()
    others = pd.DataFrame(
        np.random.default_rng(1).lognormal(size=(len(df), 20)), columns=[f"n{i}" for i in range(20)]
    )
    found = _derived(pd.concat([others, df], axis=1))  # 20 columns, then the one that matters
    assert found is not None and found.column == "quantity"


def test_a_target_with_an_infinite_value_is_still_checked():
    df = _revenue()
    df.loc[0, "revenue"] = np.inf
    found = _derived(df)
    assert found is not None and found.column == "quantity"


def test_the_target_s_own_multiple_and_a_target_that_is_not_a_positive_number_are_not_derived():
    same = _revenue()
    same["quantity"] = same.revenue / 3.0
    assert _derived(same) is None
    df = _revenue()
    assert _derived(df.assign(revenue=df.revenue - df.revenue.mean())) is None
    assert _derived(df.assign(revenue=(df.revenue > df.revenue.median()).astype(int))) is None


def test_an_exact_rate_that_varies_little_is_found():
    rng = np.random.default_rng(0)
    n = 6000
    regions = rng.integers(0, 10, n)
    rate = rng.uniform(1.0, 3.0, 10)
    x = np.exp(rng.normal(3, 1, n))
    df = pd.DataFrame({"x": x, "region": [f"r{i}" for i in regions], "y": x * rate[regions]})
    found = _derived(df, "y")
    assert found is not None and found.column == "x" and found.keys == ("region",)


def test_a_key_that_is_just_short_of_enough_is_not_completed_by_a_random_column():
    rng = np.random.default_rng(0)
    n = 50_000
    k = rng.integers(0, 8, n)
    rate = np.exp(rng.normal(0, 1.0, 8))
    x = np.exp(rng.normal(3, 1, n))
    df = pd.DataFrame(
        {
            "x": x,
            "k": [f"k{i}" for i in k],
            "junk": [f"j{i}" for i in rng.integers(0, 300, n)],  # 24 rows for each pair of values
            "y": x * rate[k] * np.exp(rng.normal(0, 0.124, n)),  # 98.97% explained by k alone
        }
    )
    assert (
        _derived(df, "y") is None
    )  # k and the junk column reach 99.02%, from fitting 2,400 groups
    sharper = df.assign(y=x * rate[k] * np.exp(rng.normal(0, 0.05, n)))
    assert _derived(sharper, "y").keys == ("k",)


def test_a_price_that_a_category_fixes_is_not_a_rate_times_a_column_that_hardly_varies():
    rng = np.random.default_rng(0)
    n = 6000
    g = rng.choice(list("abcd"), n)
    price = pd.Series(g).map({"a": 10.0, "b": 25.0, "c": 40.0, "d": 90.0}).to_numpy()
    df = pd.DataFrame(
        {
            "category": g,
            "quantity": np.exp(rng.normal(0, 0.05, n)),
            "revenue": price * np.exp(rng.normal(0, 0.001, n)),
        }
    )
    assert _derived(df) is None


def test_the_search_stops_when_its_time_is_out_and_says_so_and_keeps_what_it_found():
    df = _revenue().assign(
        other=lambda d: d.quantity * np.exp(np.random.default_rng(1).normal(size=len(d)))
    )
    columns = [profile_module._profile_column(c, df[c]) for c in df.columns]

    def run(expires_at):
        calls = []

        def clock():
            calls.append(1)
            return 0.0 if len(calls) < expires_at else 99.0

        return profile_module.derived_target(df, columns, "revenue", clock=clock, time_budget=1.0)

    assert run(10**6)[1] is False and run(10**6)[0] is not None  # in time
    outcomes = [run(k) for k in range(2, 40)]
    assert (None, True) in outcomes  # cut before anything was found
    assert any(found is not None and cut for found, cut in outcomes)  # cut after the column


def test_a_search_cut_by_its_time_is_marked_and_not_a_partial_leak_check(monkeypatch):
    df = _revenue()
    monkeypatch.setattr(profile_module, "_DERIVED_SECS", -1.0)
    columns = [profile_module._profile_column(c, df[c]) for c in df.columns]
    check = leak_check(df, columns, "revenue")
    assert check.derived_cut and check.derived is None and not check.partial
    profile = profile_dataset(df, "revenue")
    assert profile.derived_cut and not profile.leak_partial


def test_a_rate_that_two_categories_fix_with_a_small_spread_is_found():
    rng = np.random.default_rng(3)
    n = 6000
    rate = {(g, t): rng.uniform(1, 1.3) for g in "abcd" for t in "xyz"}
    g, t = rng.choice(list("abcd"), n), rng.choice(list("xyz"), n)
    x = np.exp(rng.normal(3, 1, n))
    df = pd.DataFrame({"g": g, "t": t, "x": x})
    df["y"] = x * np.array([rate[a, b] for a, b in zip(g, t, strict=True)])
    found = _derived(df, "y")
    assert found is not None and found.column == "x" and set(found.keys) == {"g", "t"}


def test_a_large_table_is_read_as_a_sample():
    seen = []
    real = pd.factorize
    big = pd.concat([_revenue()] * 20, ignore_index=True)
    columns = [profile_module._profile_column(c, big[c]) for c in big.columns]

    def spy(values, *args, **kwargs):
        seen.append(len(values))
        return real(values, *args, **kwargs)

    profile_module.pd.factorize = spy
    try:
        assert profile_module.derived_target(big, columns, "revenue")[0] is not None
    finally:
        profile_module.pd.factorize = real
    assert max(seen) <= profile_module._DERIVED_ROWS


def test_a_training_run_does_not_look_for_a_derived_target():
    df = _revenue()
    check = leak_check(
        df, [profile_module._profile_column(c, df[c]) for c in df.columns], "revenue"
    )
    assert check.derived is not None
    assert (
        leak_check(
            df,
            [profile_module._profile_column(c, df[c]) for c in df.columns],
            "revenue",
            derived=False,
        ).derived
        is None
    )


def _decisions(n=3000, seed=0, target="and"):
    """Two decisions, a rating, a noise column and a target they fix: both said yes, or one only."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "decision": rng.integers(0, 2, n),
            "decision_other": rng.integers(0, 2, n),
            "rating": rng.integers(1, 6, n),
            "noise": rng.normal(size=n),
        }
    )
    d, o = df.decision, df.decision_other
    df["match"] = {"and": d & o, "xor": d ^ o, "random": rng.integers(0, 2, n)}[target]
    return df


def _paired(df, target="match", **kwargs):
    return _paired_cut(df, target, **kwargs)[0]


def _paired_cut(df, target="match", **kwargs):
    columns = [profile_module._profile_column(c, df[c]) for c in df.columns]
    return profile_module.paired_target(df, columns, target, **kwargs)


@pytest.mark.parametrize("target", ["and", "xor"])
def test_a_target_that_two_columns_fix_together_is_named(target):
    found = _paired(_decisions(target=target))
    assert found is not None and (found.first, found.second) == ("decision", "decision_other")
    assert found.share == 1.0
    assert profile_dataset(_decisions(target=target), "match").paired == found


def test_a_target_that_one_column_fixes_or_none_do_is_not_paired():
    df = _decisions()
    assert _paired(df.assign(match=df.decision)) is None  # one column fixes it: named elsewhere
    assert _paired(_decisions(target="random")) is None
    assert _paired(df.assign(match=(df.decision & df.decision_other) | (df.rating > 4))) is None


def test_a_pair_of_columns_needs_rows_in_each_combination_and_a_target_of_few_classes():
    df = _decisions(n=3000)
    # 3 values by 3 values by 2 classes on 90 rows: a combination holds about 10 rows
    small = pd.DataFrame(
        {
            "a": np.arange(90) % 3,
            "b": (np.arange(90) // 3) % 3,
            "match": np.random.default_rng(0).integers(0, 2, 90),
        }
    )
    assert _paired(small.assign(match=lambda d: (d.a + d.b) % 2)) is None
    # the target of 21 values is not a decision
    assert (
        _paired(df.assign(match=(df.decision * 10 + df.decision_other * 5 + df.rating) % 21))
        is None
    )


def test_a_training_run_and_a_slow_search_do_not_look_for_a_paired_target():
    df = _decisions()
    columns = [profile_module._profile_column(c, df[c]) for c in df.columns]
    assert leak_check(df, columns, "match").paired is not None
    assert leak_check(df, columns, "match", derived=False).paired is None
    ticks = iter(range(10_000))
    assert _paired_cut(df, clock=lambda: float(next(ticks)), time_budget=1.0) == (None, True)
    assert leak_check(df, columns, "match").paired_cut is False


def test_a_search_out_of_time_in_the_loop_of_pairs_is_cut_and_not_kept():
    df = _decisions(target="random")  # no pair to find: the loop goes on to the next pair
    calls = iter(range(10_000))

    def slow_after_the_columns():
        i = next(calls)
        return 0.0 if i < 5 else 10.0  # the start, three columns and the first pair

    assert _paired_cut(df, clock=slow_after_the_columns, time_budget=1.0) == (None, True)
    assert _paired_cut(df) == (None, False)


def _combinations(impure, n_a=10, n_b=10, rows=50, seed=0):
    """Every combination of two columns of 10 values on 50 rows, the target their parity, but for
    ``impure`` combinations (the first ones), cut to 30 rows where it alternates: each costs 0.6%
    of the rows of a target value."""
    a = np.repeat(np.arange(n_a), n_b * rows)
    b = np.tile(np.repeat(np.arange(n_b), rows), n_a)
    y = (a + b) % 2
    df = pd.DataFrame({"a": a, "b": b, "match": y})
    df["combo"] = df.a * n_b + df.b
    odd = df.groupby("combo").cumcount() % 2
    df["match"] = np.where(df.combo < impure, odd, df.match)
    keep = (df.combo >= impure) | (df.groupby("combo").cumcount() < 30)
    return df[keep].drop(columns="combo").sample(frac=1, random_state=seed)


@pytest.mark.parametrize(("impure", "found"), [(0, True), (1, True), (2, False), (10, False)])
def test_the_share_of_the_rows_in_combinations_with_one_target_value_is_pinned_at_99_percent(
    impure, found
):
    # one impure combination of 100 leaves 99.4% of each target value's rows in pure ones
    result = _paired(_combinations(impure))
    assert (result is not None) is found
    if found:
        assert result.share >= 0.99


def test_a_rare_target_value_must_be_fixed_too():
    rng = np.random.default_rng(0)
    n = 20_000
    flag = (rng.random(n) < 0.015).astype(int)  # 1.5% of the rows
    other = rng.integers(0, 5, n)
    y = np.zeros(n, dtype=int)
    positives = np.flatnonzero((flag == 1) & (other < 2))
    y[rng.choice(positives, len(positives) // 2, replace=False)] = 1  # half of that group: 0.3%
    df = pd.DataFrame({"flag": flag, "other": other, "y": y})
    assert 0.002 < y.mean() < 0.004
    assert _paired(df, "y") is None  # the pure groups hold 99.4% of the rows, but 0% of the 1s
    assert _paired(df.assign(y=flag & (other < 2)), "y") is not None  # the 1s fixed too


def test_a_table_of_more_than_the_rows_read_is_sampled():
    rng = np.random.default_rng(0)
    n = profile_module._PAIRED_ROWS + 30_000
    df = pd.DataFrame({"a": rng.integers(0, 2, n), "b": rng.integers(0, 2, n)})
    df["match"] = df.a & df.b
    found = _paired(df)
    assert found is not None and (found.first, found.second) == ("a", "b")
    assert _paired(df.assign(match=rng.integers(0, 2, n))) is None


def test_columns_are_ranked_on_a_sample_and_the_pair_is_judged_on_the_rows():
    rng = np.random.default_rng(0)
    n = profile_module._PAIRED_RANK_ROWS + 5_000  # more than the rows the columns are ranked on
    df = pd.DataFrame({f"c{i}": rng.integers(0, 2, n) for i in range(60)})
    df["a"], df["b"] = rng.integers(0, 3, n), rng.integers(0, 3, n)
    df["match"] = ((df.a == 1) & (df.b == 2)).astype(int)
    found = _paired(df)
    assert found is not None and (found.first, found.second) == ("a", "b")
    assert _paired(df.assign(match=rng.integers(0, 2, n))) is None
    # an exception in the rows the ranking did not read: the pair must hold on all of them
    broken = df.copy()
    broken.loc[broken.index[-3000:], "match"] = rng.integers(0, 2, 3000)
    assert _paired(broken) is None


def test_a_column_that_fixes_the_target_on_almost_every_row_alone_does_not_hide_a_pair():
    df = _decisions()
    # `decision` alone fixes the target on 99.5% of the rows (but not on every row), so the leak
    # check does not name it, and the pair with the other decision is not hidden by it
    flipped = df.assign(match=df.decision & df.decision_other)
    flipped.loc[flipped.index[:15], "match"] = 1 - flipped.loc[flipped.index[:15], "match"]
    assert _paired(flipped) is None  # the pair is not exact either (a noisy target)
    assert _paired(df.assign(match=df.decision)) is None  # one that does so on every row
