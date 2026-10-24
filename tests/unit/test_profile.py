import numpy as np
import pandas as pd
import pytest

from fione.data import profile as profile_module
from fione.data.frames import change_column_type
from fione.data.profile import profile_dataset


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
