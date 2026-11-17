import datetime
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fione import db
from fione.auth import service as auth
from fione.auth.roles import ProjectAccess, Role
from fione.jobs import store
from fione.modules import expression, registry, service, unsupervised
from fione.modules.registry import ModuleContext, ModuleError, get_builtin, validate_output
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.service import DatasetNotFound, DatasetType, ProjectNotFound
from fione.schema import check_schema, validate_args
from fione.storage import LocalStorage

SRC = Path(registry.__file__).resolve().parent


def run_op(op, df, params=None, other=None, state=None):
    """Run a built-in the way the handler does: validated params, checked output."""
    module = get_builtin(op)
    out = module.run(
        df.copy(), validate_args(module.params, params or {}), ModuleContext(other, state)
    )
    return validate_output(out.df), out.state


def frame():
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "x": [3.5, 1.2, np.nan, 4.8, 2.0],
            "名前": ["a", "b", "c", "d", "e"],
            "g": ["u", "v", "u", "v", "u"],
        }
    )


def expect(**columns):
    return pd.DataFrame(columns)


def assert_same(actual, expected):
    pd.testing.assert_frame_equal(
        actual.reset_index(drop=True), expected, check_dtype=False, check_column_type=False
    )


def test_the_built_in_ids_and_kinds():
    modules = registry.builtin_modules()
    ids = [m.id for m in modules]
    frame_ops = (
        "calc cbind concat cor cslice fillna floor join lag pivot rbind replace rolling rslice sort"
        " split tokenize unpivot"
    )
    assert ids == sorted(frame_ops.split()) + [
        "kmeans_predict",
        "kmeans_train",
        "lowrank_predict",
        "lowrank_train",
    ]
    assert {m.id: m.kind for m in modules if m.id.endswith(("_train", "_predict"))} == {
        "kmeans_train": "train",
        "kmeans_predict": "predict",
        "lowrank_train": "train",
        "lowrank_predict": "predict",
    }
    assert all(m.kind == "frame" for m in modules if "_" not in m.id)
    for m in modules:
        assert registry.MODULE_ID.fullmatch(m.id)
        check_schema(m.params)


# --- frame operations ----------------------------------------------------------------------

OTHER_COLS = pd.DataFrame({"y": [10, 20, 30, 40, 50], "x": [0, 0, 0, 0, 0]})
OTHER_ROW = pd.DataFrame({"id": [6], "x": [0.5], "名前": ["f"], "g": ["u"]})
SPLIT_ORDER = np.random.default_rng(0).permutation(10)

CASES = [
    # frame_cbind.py: df.cbind(other); a repeated name gets the ingest suffix instead of failing
    (
        "cbind",
        {"other_dataset_id": 1},
        OTHER_COLS,
        frame(),
        frame().assign(y=[10, 20, 30, 40, 50], x_2=[0, 0, 0, 0, 0]),
    ),
    # frame_rbind.py: df.rbind(other)
    (
        "rbind",
        {"other_dataset_id": 1},
        OTHER_ROW,
        frame(),
        pd.concat([frame(), OTHER_ROW], ignore_index=True),
    ),
    # axis=1 (the default): column-wise
    (
        "concat",
        {"other_dataset_id": 1},
        OTHER_COLS,
        frame(),
        frame().assign(y=[10, 20, 30, 40, 50], x_2=[0, 0, 0, 0, 0]),
    ),
    # frame_concat.py, axis=0: row-wise, columns that only one side has are filled with gaps
    (
        "concat",
        {"other_dataset_id": 1, "axis": 0},
        expect(id=[6], z=["new"]),
        frame(),
        pd.concat([frame(), expect(id=[6], z=["new"])], ignore_index=True),
    ),
    # frame_cslice.py: the listed columns, in the listed order; none listed keeps all
    (
        "cslice",
        {"columns": ["名前", "id"]},
        None,
        frame(),
        expect(名前=list("abcde"), id=[1, 2, 3, 4, 5]),
    ),
    ("cslice", {}, None, frame(), frame()),
    # frame_fillna.py: forward fill down the columns, at most maxlen gaps in a row
    (
        "fillna",
        {"method": "forward"},
        None,
        expect(a=[1.0, np.nan, np.nan, 4.0], b=[np.nan, 2.0, np.nan, np.nan]),
        expect(a=[1.0, 1.0, np.nan, 4.0], b=[np.nan, 2.0, 2.0, np.nan]),
    ),
    (
        "fillna",
        {"method": "forward", "maxlen": 2},
        None,
        expect(a=[1.0, np.nan, np.nan, 4.0]),
        expect(a=[1.0, 1.0, 1.0, 4.0]),
    ),
    (
        "fillna",
        {"method": "backward", "maxlen": 2},
        None,
        expect(a=[1.0, np.nan, np.nan, 4.0]),
        expect(a=[1.0, 4.0, 4.0, 4.0]),
    ),
    # axis=1: along the rows
    (
        "fillna",
        {"method": "forward", "axis": 1},
        None,
        expect(a=[1.0, 2.0], b=[np.nan, np.nan], c=[3.0, np.nan]),
        expect(a=[1.0, 2.0], b=[1.0, 2.0], c=[3.0, np.nan]),
    ),
    # floor of the listed columns only
    ("floor", {"columns": ["x"]}, None, frame(), expect(x=[3.0, 1.0, np.nan, 4.0, 2.0])),
    (
        "floor",
        {},
        None,
        expect(a=[1.5, -0.5], b=[2, 3]),
        expect(a=[1.0, -1.0], b=[2.0, 3.0]),
    ),
    # frame_pivot.py: first occurrence per (index, column); columns named after the values
    (
        "pivot",
        {"index": "k", "column": "c", "value": "v"},
        None,
        expect(k=[1, 1, 2, 2, 2], c=["a", "b", "a", "b", "a"], v=[10, 20, 30, 40, 99]),
        expect(k=[1, 2], a=[10, 30], b=[20, 40]),
    ),
    (
        "pivot",
        {"index": "k", "column": "c", "value": "v"},
        None,
        expect(k=[1, 2], c=[7, 8], v=[1.0, 2.0]),
        expect(k=[1, 2], **{"7": [1.0, np.nan], "8": [np.nan, 2.0]}),
    ),
    # unpivot: the kept columns repeat once per unpivoted column, in column order
    (
        "unpivot",
        {"keep": ["id"], "name": "day", "value": "sales"},
        None,
        expect(id=["a", "b"], d1=[1, 2], d2=[3, 4]),
        expect(id=["a", "b", "a", "b"], day=["d1", "d1", "d2", "d2"], sales=[1, 2, 3, 4]),
    ),
    (
        "unpivot",
        {"keep": ["id"], "columns": ["d2"]},
        None,
        expect(id=["a", "b"], d1=[1, 2], d2=[3, 4]),
        expect(id=["a", "b"], variable=["d2", "d2"], value=[3, 4]),
    ),
    # frame_replace.py: set the column where the row conditions hold; the value takes the type
    (
        "replace",
        {"column": "x", "row_conditions": "id >= 4", "value": "9.5"},
        None,
        frame(),
        frame().assign(x=[3.5, 1.2, np.nan, 9.5, 9.5]),
    ),
    (
        "replace",
        {"column": "名前", "value": "z"},
        None,
        frame(),
        frame().assign(名前=["z"] * 5),
    ),
    # '&' is AND, and binds tighter than '|'
    (
        "replace",
        {"column": "名前", "row_conditions": "g == u & id < 3 | id == 5", "value": "hit"},
        None,
        frame(),
        frame().assign(名前=["hit", "b", "c", "d", "hit"]),
    ),
    # frame_rslice.py: the rows where the conditions hold
    (
        "rslice",
        {"row_conditions": "id > 2 & g == u"},
        None,
        frame(),
        frame().iloc[[2, 4]],
    ),
    ("rslice", {"row_conditions": "id == 1 | id == 5"}, None, frame(), frame().iloc[[0, 4]]),
    ("rslice", {"row_conditions": "x >= 3.5"}, None, frame(), frame().iloc[[0, 3]]),
    ("rslice", {"row_conditions": "名前 != a"}, None, frame(), frame().iloc[1:]),
    ("rslice", {}, None, frame(), frame()),
    # frame_sort.py: by one column; gaps last
    ("sort", {"column": "x", "ascending": False}, None, frame(), frame().iloc[[3, 0, 4, 1, 2]]),
    ("sort", {"column": "x"}, None, frame(), frame().iloc[[1, 4, 0, 3, 2]]),
    # frame_split.py: seeded split in the train/valid/test ratios; a part is one output
    (
        "split",
        {"part": "train", "seed": 0},
        None,
        pd.DataFrame({"i": range(10)}),
        expect(i=sorted(SPLIT_ORDER[:7])),
    ),
    (
        "split",
        {"part": "valid", "seed": 0},
        None,
        pd.DataFrame({"i": range(10)}),
        expect(i=sorted(SPLIT_ORDER[7:8])),
    ),
    (
        "split",
        {"part": "test", "seed": 0},
        None,
        pd.DataFrame({"i": range(10)}),
        expect(i=sorted(SPLIT_ORDER[8:])),
    ),
    # nothing set aside: the whole frame is the training part
    (
        "split",
        {"train_ratio": 100, "valid_ratio": 0, "test_ratio": 0},
        None,
        frame(),
        frame(),
    ),
    # frame_tokenize.py: one token per row, a gap after each document; empty tokens dropped
    (
        "tokenize",
        {"target_column": "t"},
        None,
        expect(t=["Hello, World", "a b", None, ""]),
        expect(t=["Hello", "World", None, "a", "b", None, None, None]),
    ),
    (
        "tokenize",
        {"target_column": "t", "lower_case": True, "min_word_len": 2},
        None,
        expect(t=["Hello, World", "a b"]),
        expect(t=["hello", "world", None, None]),
    ),
    (
        "tokenize",
        {"target_column": "t", "use_stop_words": True},
        None,
        expect(t=["the cat, and a dog"]),
        expect(t=["cat", "dog", None]),
    ),
    (
        "tokenize",
        {"target_column": "文"},
        None,
        expect(文=["猫 は 可愛い"]),
        expect(文=["猫", "は", "可愛い", None]),
    ),
]
CASE_IDS = [f"{c[0]}-{i}" for i, c in enumerate(CASES)]


@pytest.mark.parametrize(("op", "params", "other", "df", "expected"), CASES, ids=CASE_IDS)
def test_frame_ops(op, params, other, df, expected):
    out, state = run_op(op, df, params, other=other)
    assert state is None
    assert_same(out, expected.reset_index(drop=True))
    assert list(out.columns) == list(expected.columns)


def test_cor_pearson_and_spearman():
    df = expect(a=[1.0, 2, 3, 4, 5], b=[1.0, 8, 27, 64, 125], c=[5.0, 4, 3, 2, 1])
    # frame_cor.py: the correlation matrix of the columns, in their order, without labels
    pearson, _ = run_op("cor", df)
    assert list(pearson.columns) == ["a", "b", "c"]
    assert np.allclose(pearson.to_numpy(), np.corrcoef(df.to_numpy().T))
    spearman, _ = run_op("cor", df, {"method": "spearman", "columns": ["a", "b"]})
    assert np.allclose(spearman.to_numpy(), [[1, 1], [1, 1]])


def test_cor_missing_value_handling():
    # With the defaults a column with a gap comes out as NaN.
    df = expect(a=[1.0, 2, 3, 4, np.nan], b=[2.0, 4, 6, 8, 10], c=[5.0, 4, 3, 2, 1])
    default, _ = run_op("cor", df)
    assert default.loc[0].isna().tolist() == [True, True, True]  # a is unknown against all
    assert default.loc[:, "a"].isna().all()
    assert default.loc[1, "c"] == pytest.approx(-1.0) and default.loc[1, "b"] == pytest.approx(1.0)
    removed, _ = run_op("cor", df, {"na_rm": True})  # incomplete rows dropped first
    assert not removed.isna().to_numpy().any()
    assert removed.loc[0, "b"] == pytest.approx(1.0) and removed.loc[0, "c"] == pytest.approx(-1.0)
    # an explicit `use` wins over na_rm
    assert run_op("cor", df, {"use": "everything", "na_rm": True})[0].loc[0].isna().all()
    assert not run_op("cor", df, {"use": "complete.obs"})[0].isna().to_numpy().any()
    with pytest.raises(ModuleError, match="missing values"):
        run_op("cor", df, {"use": "all.obs"})


def test_split_parts_cover_the_frame_exactly_once():
    df = pd.DataFrame({"i": range(50)})
    parts = [
        run_op(
            "split",
            df,
            {"part": p, "seed": 7, "train_ratio": 60, "valid_ratio": 20, "test_ratio": 20},
        )[0]["i"]
        for p in ("train", "valid", "test")
    ]
    assert [len(p) for p in parts] == [30, 10, 10]
    assert sorted(pd.concat(parts)) == list(range(50))
    assert all(list(p) == sorted(p) for p in parts)  # source order kept inside a part


def test_join_adds_the_columns_of_the_row_with_the_same_key():
    df = pd.DataFrame({"id": [3, 1, 2, 9], "x": [1.0, 2.0, 3.0, 4.0]})
    other = pd.DataFrame({"id": [1, 2, 3], "x": ["a", "b", "c"], "n": [10, 20, 30]})
    out, _ = run_op("join", df, {"other_dataset_id": 1, "key": "id"}, other=other)
    assert list(out.columns) == ["id", "x", "x_2", "n"]
    assert list(out["x_2"].fillna("-")) == ["c", "a", "b", "-"]  # every row stays, in its order
    assert list(out["n"].fillna(-1)) == [30, 10, 20, -1]


def test_join_notes_the_rows_without_a_match_and_asks_to_check_the_keys_when_none_match():
    df = pd.DataFrame({"id": ["a", "b", "c"]})
    some = get_builtin("join").run(
        df,
        validate_args(get_builtin("join").params, {"other_dataset_id": 1, "key": "id"}),
        ModuleContext(pd.DataFrame({"id": ["a", "b"], "v": [1, 2]}), None),
    )
    assert some.notes == (
        {
            "message": "1 of 3 rows (33.3%) have no row with the same key in the other dataset; "
            "their new columns are empty.",
            "kind": "join_unmatched",
            "rows_unmatched": 1,
            "rows": 3,
        },
    )
    none = get_builtin("join").run(
        df,
        validate_args(get_builtin("join").params, {"other_dataset_id": 1, "key": "id"}),
        ModuleContext(pd.DataFrame({"id": ["x"], "v": [1]}), None),
    )
    assert "3 of 3 rows (100.0%)" in none.notes[0]["message"]
    assert "Check that the key columns hold the same kind of values" in none.notes[0]["message"]
    full = get_builtin("join").run(
        df,
        validate_args(get_builtin("join").params, {"other_dataset_id": 1, "key": "id"}),
        ModuleContext(pd.DataFrame({"id": ["a", "b", "c"], "v": [1, 2, 3]}), None),
    )
    assert full.notes == ()


def test_join_by_keys_with_other_names_and_missing_keys():
    df = pd.DataFrame({"user": ["a", "b", None], "id": [1, 2, 3]})
    other = pd.DataFrame({"name": ["a", "b", None], "v": [1, 2, 3]})
    out, _ = run_op("join", df, {"other_dataset_id": 1, "key": "user", "other_key": "name"}, other)
    assert list(out.columns) == ["user", "id", "v"]
    assert list(out["v"].fillna(-1)) == [1, 2, -1]  # a missing key matches nothing


def test_join_summarizes_a_table_with_many_rows_per_key():
    df = pd.DataFrame({"id": [1, 2, 3]})
    other = pd.DataFrame(
        {"id": [1, 1, 2], "amount": [10.0, 30.0, 5.0], "kind": ["a", "b", "a"], "n": [1, 2, 3]}
    )
    out, _ = run_op("join", df, {"other_dataset_id": 1, "key": "id", "summarize": True}, other)
    assert list(out.columns) == [
        "id",
        "rows",
        *[f"{c}_{how}" for c in ("amount", "n") for how in ("mean", "min", "max", "sum")],
        "kind_nunique",
    ]
    assert list(out["rows"].fillna(0)) == [2, 1, 0]
    assert list(out["amount_mean"].fillna(-1)) == [20.0, 5.0, -1]
    assert list(out["amount_sum"].fillna(-1)) == [40.0, 5.0, -1]
    assert list(out["kind_nunique"].fillna(-1)) == [2, 1, -1]


def test_join_summarize_takes_the_statistics_named_including_the_last_value_and_the_spread():
    df = pd.DataFrame({"id": [1, 2, 3]})
    other = pd.DataFrame(
        {
            "id": [1, 1, 1, 2],
            "amount": [10.0, 30.0, np.nan, 5.0],
            "n": [1, 2, 3, 4],
            "kind": ["a", "b", "a", "a"],
        }
    )
    params = {"other_dataset_id": 1, "key": "id", "summarize": True, "stats": "last, std,last"}
    out, _ = run_op("join", df, params, other)
    assert list(out.columns) == [
        "id",
        "rows",
        "amount_last",
        "amount_std",
        "n_last",
        "n_std",
        "kind_nunique",
    ]
    # the last value that is not empty, in the order of the rows; a spread needs two values
    assert list(out["amount_last"].fillna(-1)) == [30.0, 5.0, -1]
    assert list(out["n_last"].fillna(-1)) == [3, 4, -1]
    assert out["amount_std"].iloc[0] == pytest.approx(np.std([10.0, 30.0], ddof=1))
    assert np.isnan(out["amount_std"].iloc[1])
    for text in ("median", "", "mean,,bogus"):
        with pytest.raises(ModuleError, match="stats must name"):
            run_op("join", df, {**params, "stats": text}, other)


def test_join_adds_only_the_chosen_columns_and_summarizes_only_those():
    df = pd.DataFrame({"id": [1, 2, 3]})
    other = pd.DataFrame(
        {"id": [1, 1, 2], "ref": [7, 8, 9], "amount": [10.0, 30.0, 5.0], "kind": ["a", "b", "a"]}
    )
    one_each = other.iloc[[0, 2]]
    args = {"other_dataset_id": 1, "key": "id"}
    out, _ = run_op("join", df, {**args, "columns": ["amount", "id"]}, one_each)
    assert list(out.columns) == ["id", "amount"]  # the key is not added twice
    out, _ = run_op("join", df, {**args, "summarize": True, "columns": ["amount"]}, other)
    assert list(out.columns) == [
        "id",
        "rows",
        *[f"amount_{h}" for h in ("mean", "min", "max", "sum")],
    ]
    with pytest.raises(ModuleError, match="unknown columns"):
        run_op("join", df, {**args, "columns": ["zz"]}, one_each)


def test_join_matches_a_number_with_the_same_text():
    df = pd.DataFrame({"id": [1, 2, 3]})
    other = pd.DataFrame({"id": ["2", "3", "x"], "v": [20, 30, 99]})
    out, _ = run_op("join", df, {"other_dataset_id": 1, "key": "id"}, other)
    assert list(out["id"]) == [1, 2, 3]  # the key keeps its type
    assert list(out["v"].fillna(-1)) == [-1, 20, 30]


def test_join_matches_a_whole_float_with_the_same_text():
    df = pd.DataFrame({"id": [1.0, 2.0, None]})
    other = pd.DataFrame({"id": ["1", "2"], "v": [10, 20]})
    out, _ = run_op("join", df, {"other_dataset_id": 1, "key": "id"}, other)
    assert list(out["v"].fillna(-1)) == [10, 20, -1]


def test_join_summarize_works_when_the_key_is_named_like_a_summary_column():
    df = pd.DataFrame({"rows": [1, 2], "x_mean": [5, 6]})
    other = pd.DataFrame({"rows": [1, 1, 2], "x_mean": [3, 4, 5], "k": ["a", "b", "a"]})
    out, _ = run_op("join", df, {"other_dataset_id": 1, "key": "rows", "summarize": True}, other)
    assert list(out["rows_2"]) == [2, 1]  # the number of rows, named apart from the key
    assert list(out["x_mean_mean"]) == [3.5, 5.0]
    out, _ = run_op(
        "join", df, {"other_dataset_id": 1, "key": "x_mean", "other_key": "k", "summarize": True},
        pd.DataFrame({"k": [5, 5, 6], "x_mean": [1, 3, 5]}),
    )  # fmt: skip
    assert list(out["x_mean_mean"].fillna(-1)) == [2.0, 5.0]


def test_join_refuses_repeated_keys_unknown_columns_and_a_missing_dataset():
    df = pd.DataFrame({"id": [1, 2]})
    with pytest.raises(ModuleError, match="summarize it"):
        run_op("join", df, {"other_dataset_id": 1, "key": "id"}, pd.DataFrame({"id": [1, 1]}))
    with pytest.raises(ModuleError, match="unknown column 'zz'"):
        run_op("join", df, {"other_dataset_id": 1, "key": "id", "other_key": "zz"}, df)
    with pytest.raises(ModuleError, match="second dataset"):
        run_op("join", df, {"other_dataset_id": 1, "key": "id"})


def test_join_by_several_key_columns_matches_the_whole_key():
    df = pd.DataFrame({"shop": [1, 1, 2, 2, None], "item": [5, 6, 5, 6, 5]})
    other = pd.DataFrame({"s": [1, 2, 2], "i": ["5", "5", "6"], "n": [10, 20, 30]})
    out, _ = run_op(
        "join",
        df,
        {"other_dataset_id": 1, "keys": ["shop", "item"], "other_keys": ["s", "i"]},
        other,
    )
    assert list(out.columns) == ["shop", "item", "n"]
    # item 5 of shop 1 and of shop 2 differ; a shop and item pair absent from the other
    # dataset, and a pair with a missing part, get nothing
    assert list(out["n"].fillna(-1)) == [10, -1, 20, 30, -1]


def test_join_by_several_key_columns_refuses_a_repeated_pair_and_summarizes_it():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "y", "x"]})
    other = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "x"], "v": [1.0, 3.0, 5.0]})
    with pytest.raises(ModuleError, match="'a', 'b' repeat"):
        run_op("join", df, {"other_dataset_id": 1, "keys": ["a", "b"]}, other)
    out, _ = run_op(
        "join", df, {"other_dataset_id": 1, "keys": ["a", "b"], "summarize": True}, other
    )
    assert list(out.columns)[:2] == ["a", "b"] and "rows" in out.columns
    assert list(out["rows"].fillna(0)) == [2, 0, 1]
    assert list(out["v_mean"].fillna(-1)) == [2.0, -1, 5.0]
    # one name where the other has two does not repeat a pair that is different
    ok = other.assign(b=["x", "y", "x"])
    out, _ = run_op("join", df, {"other_dataset_id": 1, "keys": ["a", "b"]}, ok)
    assert list(out["v"]) == [1.0, 3.0, 5.0]


def test_join_by_several_key_columns_refuses_unclear_keys():
    df = pd.DataFrame({"a": [1], "b": [2]})
    for params, message in (
        ({"key": "a", "keys": ["a", "b"]}, "not both"),
        ({"keys": ["a", "a"]}, "names a column twice"),
        ({"keys": ["a", "b"], "other_key": "a"}, "same number"),
        ({}, "name the key"),
        ({"keys": ["a", "zz"]}, "unknown column 'zz'"),
    ):
        with pytest.raises(ModuleError, match=message):
            run_op("join", df, {"other_dataset_id": 1, **params}, df)


def test_a_japanese_column_passes_through_the_ops():
    df = pd.DataFrame({"年齢": [30, 20, 25], "名前": ["さ", "た", "な"]})
    out, _ = run_op("sort", df, {"column": "年齢"})
    assert list(out["名前"]) == ["た", "な", "さ"]
    out, _ = run_op("cslice", df, {"columns": ["名前"]})
    assert list(out.columns) == ["名前"]
    out, _ = run_op("replace", df, {"column": "名前", "row_conditions": "年齢 > 24", "value": "★"})
    assert list(out["名前"]) == ["★", "た", "★"]


@pytest.mark.parametrize(
    ("op", "params", "other", "message"),
    [
        ("cbind", {"other_dataset_id": 1}, expect(y=[1, 2]), "same number of rows"),
        ("rbind", {"other_dataset_id": 1}, expect(id=[1]), "same columns"),
        ("concat", {"other_dataset_id": 1}, expect(y=[1, 2]), "same number of rows"),
        ("cbind", {"other_dataset_id": 1}, None, "second dataset"),
        ("cslice", {"columns": ["nope"]}, None, "unknown columns: ['nope']"),
        ("floor", {"columns": ["名前"]}, None, "not numeric"),
        ("sort", {"column": "nope"}, None, "unknown column 'nope'"),
        ("pivot", {"index": "id", "column": "nope", "value": "x"}, None, "unknown column 'nope'"),
        ("replace", {"column": "id", "value": "abc"}, None, "'abc'"),
        ("rslice", {"row_conditions": "id ~ 3"}, None, "cannot read the condition"),
        ("rslice", {"row_conditions": "nope == 3"}, None, "unknown column 'nope'"),
        ("rslice", {"row_conditions": "id > abc"}, None, "'abc'"),
        ("split", {"train_ratio": 0}, None, "train_ratio"),
        ("tokenize", {"target_column": "nope"}, None, "unknown column 'nope'"),
        ("tokenize", {"target_column": "id"}, None, "text column"),
        ("tokenize", {"target_column": "g", "mode": "delimiter"}, None, "needs a delimiter"),
    ],
)
def test_bad_op_inputs_are_module_errors(op, params, other, message):
    with pytest.raises(ModuleError, match=re.escape(message)):
        run_op(op, frame(), params, other=other)


# --- k-means and low-rank ------------------------------------------------------------------


def blobs(n=60, seed=0):
    rng = np.random.default_rng(seed)
    centers = np.array([[0.0, 0.0], [8.0, 8.0], [-8.0, 6.0]])
    points = np.vstack([c + rng.normal(scale=0.5, size=(n // 3, 2)) for c in centers])
    return pd.DataFrame({"a": points[:, 0], "b": points[:, 1], "label": ["x"] * n})


def test_kmeans_predict_reproduces_the_training_assignments():
    df = blobs()
    trained, state = run_op("kmeans_train", df, {"columns": ["a", "b"], "k": 3, "seed": 1})
    assert list(trained.columns) == ["cluster"]
    assert sorted(set(trained["cluster"])) == [0, 1, 2]
    # the three blobs are recovered: 20 points each, one label per blob
    assert sorted(np.bincount(trained["cluster"])) == [20, 20, 20]
    assert len(set(trained["cluster"][:20])) == 1
    # the state is plain JSON and is all that predict needs
    again = json.loads(json.dumps(state, allow_nan=False))
    predicted, none = run_op(
        "kmeans_predict", df, {"module_model_id": 1, "output_columns": ["label"]}, state=again
    )
    assert none is None
    assert list(predicted.columns) == ["cluster", "label"]
    assert list(predicted["cluster"]) == list(trained["cluster"])
    # a fresh point near a blob joins it
    near = pd.DataFrame({"a": [7.9], "b": [8.2], "label": ["n"]})
    got = run_op("kmeans_predict", near, {"module_model_id": 1}, state=again)[0]["cluster"][0]
    assert got == trained["cluster"][20]


def test_kmeans_state_is_stable_for_a_seed_and_standardizes():
    df = blobs().assign(c=lambda d: d["a"] * 1000)
    _, s1 = run_op("kmeans_train", df, {"columns": ["a", "b", "c"], "k": 3, "seed": 5})
    _, s2 = run_op("kmeans_train", df, {"columns": ["a", "b", "c"], "k": 3, "seed": 5})
    assert s1 == s2
    assert set(s1) == {"type", "columns", "means", "scales", "centers"}
    assert s1["type"] == "kmeans" and s1["columns"] == ["a", "b", "c"]
    assert s1["scales"][2] == pytest.approx(1000 * s1["scales"][0])
    raw = run_op("kmeans_train", df, {"columns": ["a", "b"], "k": 3, "standardize": False})[1]
    assert raw["scales"] == [1.0, 1.0]


def test_kmeans_fills_gaps_with_the_column_mean_and_handles_constant_columns():
    df = expect(a=[1.0, 2.0, np.nan, 10.0, 11.0, 12.0], k=[7.0] * 6)
    out, state = run_op("kmeans_train", df, {"k": 2, "seed": 0})
    assert state["means"][0] == pytest.approx(np.nanmean(df["a"]))
    assert state["scales"][1] == 1.0  # constant column: no division by zero
    assert out["cluster"][2] == out["cluster"][3]  # the mean (7.2) is nearer 11 than 1.5
    json.dumps(state, allow_nan=False)


def test_kmeans_needs_numbers_and_says_which_columns_are_not():
    df = blobs().assign(flag=True, when=pd.Timestamp("2024-01-01"))
    with pytest.raises(ModuleError, match=r"not numeric: \['label', 'flag', 'when'\]"):
        run_op("kmeans_train", df, {"k": 2})
    out, _ = run_op("kmeans_train", df, {"columns": ["a", "b"], "k": 2})
    assert len(out) == len(df)
    with pytest.raises(ModuleError, match="'columns' parameter"):
        run_op("kmeans_train", df, {"k": 2})


@pytest.mark.parametrize(
    ("df", "params", "message"),
    [
        (blobs(), {"k": 100, "columns": ["a"]}, "k=100"),
        (expect(a=[1.0, 1.0, 1.0]), {"k": 2}, "distinct"),
        (expect(a=[np.nan, np.nan]), {"k": 1}, "no values"),
        (expect(a=[1.0, np.inf]), {"k": 1}, "not finite"),
        (blobs(), {"k": 2, "columns": ["a", "zz"]}, "unknown columns: ['zz']"),
    ],
)
def test_kmeans_rejects_unusable_data(df, params, message):
    with pytest.raises(ModuleError, match=re.escape(message)):
        run_op("kmeans_train", df, params)


def test_kmeans_predict_checks_the_model_and_the_columns():
    _, state = run_op("kmeans_train", blobs(), {"columns": ["a", "b"], "k": 2})
    with pytest.raises(ModuleError, match="missing columns: \\['b'\\]"):
        run_op("kmeans_predict", blobs().drop(columns="b"), {"module_model_id": 1}, state=state)
    with pytest.raises(ModuleError, match="not a k-means model"):
        run_op("kmeans_predict", blobs(), {"module_model_id": 1}, state={"type": "lowrank"})
    with pytest.raises(ModuleError, match="not numeric"):
        run_op("kmeans_predict", blobs().assign(a="s"), {"module_model_id": 1}, state=state)


def low_rank(n=40, seed=0):
    rng = np.random.default_rng(seed)
    w = rng.random((n, 2))
    h = rng.random((2, 6))
    return pd.DataFrame(w @ h, columns=list("abcdef"))


@pytest.mark.parametrize("method", ["svd", "nmf"])
def test_lowrank_projection_is_rebuilt_from_the_json_state(method):
    df = low_rank()
    out, state = run_op("lowrank_train", df, {"method": method, "n_components": 2, "seed": 3})
    assert list(out.columns) == ["component_1", "component_2"]
    assert set(state) == {"type", "method", "columns", "means", "components"}
    rebuilt = json.loads(json.dumps(state, allow_nan=False))
    again, _ = run_op("lowrank_predict", df, {"module_model_id": 1}, state=rebuilt)
    assert list(again.columns) == ["component_1", "component_2"]
    np.testing.assert_allclose(again.to_numpy(), out.to_numpy(), rtol=0, atol=1e-9)
    # the rank-2 data is explained by two components
    recon = out.to_numpy() @ np.array(state["components"])
    assert np.linalg.norm(recon - df.to_numpy()) / np.linalg.norm(df.to_numpy()) < 0.05


def test_lowrank_keeps_requested_columns_and_fills_gaps():
    df = low_rank().assign(keep=range(40))
    df.loc[3, "b"] = np.nan
    out, state = run_op("lowrank_train", df, {"columns": list("abcdef"), "n_components": 3})
    assert state["means"][1] == pytest.approx(df["b"].mean())
    assert out.notna().all().all()
    predicted, _ = run_op(
        "lowrank_predict", df, {"module_model_id": 1, "output_columns": ["keep"]}, state=state
    )
    assert list(predicted.columns) == ["component_1", "component_2", "component_3", "keep"]


@pytest.mark.parametrize(
    ("df", "params", "message"),
    [
        (low_rank(), {"method": "nmf", "n_components": 2, "columns": ["a"]}, "at most 1"),
        (low_rank(), {"n_components": 7}, "at most 6"),
        (low_rank().assign(a=lambda d: d["a"] - 5), {"method": "nmf"}, "negative"),
        (low_rank().assign(s="x"), {}, "not numeric: ['s']"),
    ],
)
def test_lowrank_rejects_unusable_input(df, params, message):
    with pytest.raises(ModuleError, match=re.escape(message)):
        run_op("lowrank_train", df, params)


def test_module_state_is_json_only():
    for path in SRC.rglob("*.py"):
        text = path.read_text()
        assert "pickle" not in text and "joblib" not in text, path


def test_nmf_projection_is_non_negative_and_deterministic():
    h = np.array([[1.0, 0.0, 2.0], [0.0, 1.0, 1.0]])
    x = np.array([[1.0, 2.0, 4.0], [0.0, 0.0, 0.0]])
    w = unsupervised.nmf_project(x, h)
    assert (w >= 0).all() and np.array_equal(w, unsupervised.nmf_project(x, h))
    np.testing.assert_allclose(w @ h, x, atol=1e-3)


# --- output checks -------------------------------------------------------------------------


def test_validate_output_accepts_and_sanitizes_names():
    df = pd.DataFrame([[1, 2, 3]], columns=[" a ", "", "b"])
    out = validate_output(df)
    assert list(out.columns) == ["a", "column_2", "b"]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ([1, 2], "must return a DataFrame"),
        (None, "must return a DataFrame"),
        (pd.DataFrame([[1, 2]], columns=["a", "a"]), "duplicate column names: ['a']"),
        (pd.DataFrame([[1, 2]], columns=["a", 1]), "column names must be text"),
        (pd.DataFrame(index=[0, 1]), "no columns"),
    ],
)
def test_validate_output_rejects(value, message):
    with pytest.raises(ModuleError, match=re.escape(message)):
        validate_output(value)


def test_validate_output_caps_the_size(monkeypatch):
    assert registry.MAX_OUTPUT_CELLS == 150_000_000
    monkeypatch.setattr(registry, "MAX_OUTPUT_CELLS", 4)
    with pytest.raises(ModuleError, match="4 cells"):
        validate_output(pd.DataFrame({"a": [1, 2, 3], "b": [1, 2, 3]}))


# --- the shared flat-schema validator --------------------------------------------------------

ARRAY = {"properties": {"cols": {"type": "array", "items": {"type": "string"}, "maxItems": 2}}}


def test_validate_args_takes_lists_of_strings():
    assert validate_args(ARRAY, {"cols": ["a,b", "c"]}) == {"cols": ["a,b", "c"]}
    for bad in ("a", [1], ["a", "b", "c"], [["a"]]):
        with pytest.raises(ValueError, match="'cols'"):
            validate_args(ARRAY, {"cols": bad})


@pytest.mark.parametrize(
    "schema",
    [
        None,
        {},
        {"properties": []},
        {"properties": {"a": {"type": "object"}}},
        {"properties": {"a": {"type": "string", "pattern": ".*"}}},
        {"properties": {"a": {"type": "integer", "default": "x"}}},
        {"properties": {"a": {"type": "integer"}}, "required": ["b"]},
        {"properties": {"a": {"type": "string", "enum": "ab"}}},
        {"properties": {"a": {"type": "integer", "minimum": "1"}}},
    ],
)
def test_check_schema_rejects_malformed_schemas(schema):
    with pytest.raises(ValueError):
        check_schema(schema)


def test_a_module_cannot_declare_an_array_of_objects():
    check_schema({"properties": {"a": {"type": "array", "items": {"type": "string"}}}})
    with pytest.raises(ValueError, match="unsupported keyword"):
        check_schema({"properties": {"a": {"type": "array", "items": {"type": "object"}}}})


def test_an_array_of_objects_takes_only_lists_of_objects():
    schema = {"properties": {"a": {"type": "array", "items": {"type": "object"}}}}
    assert validate_args(schema, {"a": [{}, {"x": 1}]}) == {"a": [{}, {"x": 1}]}
    for bad in ([{}, 5], [1], "x", {"x": 1}):
        with pytest.raises(ValueError, match="'a' must be of type array"):
            validate_args(schema, {"a": bad})
    strings = {"properties": {"a": {"type": "array"}}}
    with pytest.raises(ValueError, match="'a' must be of type array"):
        validate_args(strings, {"a": [{}]})


# --- uploading, listing, deleting -----------------------------------------------------------

GOOD = """
MODULE = {
    "name": "Add",
    "kind": "frame",
    "params": {"type": "object", "properties": {"by": {"type": "integer", "default": 1}}},
}

def run(df, params, ctx):
    return df.assign(plus=df["id"] + params["by"])
"""


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "fione.db")
    db.migrate(c)
    yield c
    c.close()


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "storage")


@pytest.fixture
def admin(conn):
    return auth.create_user(conn, "root", "pw-admin-1", Role.ADMIN)


@pytest.fixture
def editor(conn):
    return auth.create_user(conn, "ed", "pw-editor-1", Role.EDITOR)


@pytest.fixture
def viewer(conn):
    return auth.create_user(conn, "vi", "pw-viewer-1", Role.VIEWER)


def nothing_stored(conn, storage):
    return (
        storage.list("") == [] and conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0] == 0
    )


def upload(conn, storage, admin, source=GOOD, module_id="add_one", **kw):
    return service.upload_module(conn, storage, admin, module_id, source.encode(), **kw)


def test_an_admin_uploads_a_module_and_its_metadata_is_stored(conn, storage, admin):
    info = upload(conn, storage, admin)
    assert (info.id, info.name, info.kind, info.builtin) == ("add_one", "Add", "frame", False)
    assert info.params["properties"]["by"]["default"] == 1
    assert storage.get("modules/add_one/module.py") == GOOD.encode()
    row = conn.execute("SELECT * FROM modules").fetchone()
    assert row["source_sha256"] == __import__("hashlib").sha256(GOOD.encode()).hexdigest()
    assert row["uploaded_by"] == admin.id and row["created_at"] > 0
    listed = service.list_modules(conn)
    assert [m.id for m in listed[:-1]] == [m.id for m in registry.builtin_modules()]
    assert listed[-1] == info and all(m.builtin for m in listed[:-1])


def test_uploaded_code_is_inspected_in_another_process_and_never_imported_here(
    conn, storage, admin, tmp_path, monkeypatch
):
    canary = tmp_path / "canary"
    source = GOOD + f"\nimport os\nopen({str(canary)!r}, 'a').write(str(os.getpid()) + '\\n')\n"

    def refuse(*args, **kwargs):
        raise AssertionError("uploaded code must not be loaded in this process")

    monkeypatch.setattr(importlib.util, "spec_from_file_location", refuse)
    monkeypatch.setattr(importlib.util, "module_from_spec", refuse)
    before = set(sys.modules)
    upload(conn, storage, admin, source)
    assert canary.read_text().split() != [] and str(os.getpid()) not in canary.read_text().split()
    assert set(sys.modules) - before == set()
    assert not any("add_one" in name or "canary" in name for name in sys.modules)


def test_the_inspect_process_gets_a_scrubbed_environment(
    conn, storage, admin, tmp_path, monkeypatch
):
    monkeypatch.setenv("FIONE_S3_SECRET_KEY", "hunter2")
    monkeypatch.setenv("SOME_TOKEN", "t")
    out = tmp_path / "env.json"
    source = (
        GOOD + f"\nimport os, json\nopen({str(out)!r}, 'w').write(json.dumps(dict(os.environ)))\n"
    )
    upload(conn, storage, admin, source)
    env = json.loads(out.read_text())
    assert not [k for k in env if k.startswith("FIONE")] and "SOME_TOKEN" not in env
    assert set(env) <= {"PATH", "HOME", "LANG", "__PYVENV_LAUNCHER__", "__CF_USER_TEXT_ENCODING"}
    assert env["HOME"] != os.environ["HOME"] and "hunter2" not in out.read_text()


def test_only_an_admin_can_upload_and_nothing_is_read_first(
    conn, storage, editor, viewer, monkeypatch
):
    def boom(*args, **kwargs):
        raise AssertionError("must not look at the upload")

    monkeypatch.setattr(service, "_inspect", boom)
    for user in (editor, viewer):
        with pytest.raises(PermissionError):
            service.upload_module(conn, storage, user, "../evil", b"\xff not even text")
    assert nothing_stored(conn, storage)


@pytest.mark.parametrize(
    "module_id",
    [
        "../x",
        "a/b",
        "a\\b",
        "a\x00b",
        "Upper",
        "日本語",
        "",
        "1abc",
        "a" * 41,
        "a b",
        "a.b",
        ".hidden",
        "x\n",
        None,
        5,
    ],
)
def test_hostile_module_ids_are_refused(conn, storage, admin, module_id):
    with pytest.raises(ValueError):
        service.upload_module(conn, storage, admin, module_id, GOOD.encode())
    assert nothing_stored(conn, storage)
    with pytest.raises(ValueError):
        service.delete_module(conn, storage, admin, module_id)


def test_a_built_in_id_or_an_existing_module_cannot_be_taken(conn, storage, admin):
    with pytest.raises(ValueError, match="built-in"):
        upload(conn, storage, admin, module_id="cbind")
    upload(conn, storage, admin)
    with pytest.raises(ValueError, match="already"):
        upload(conn, storage, admin, GOOD.replace("Add", "Other"))
    assert storage.get("modules/add_one/module.py") == GOOD.encode()


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (b"x = 1\n" + b"#" * (256 * 1024), "256 KB"),
        (b"\xff\xfe nope", "UTF-8"),
        (b"def run(:\n", "syntax error"),
        (
            b"MODULE = {'name': 'x', 'kind': 'frame', 'params': {'properties': {}}}\n"
            b"raise SystemExit(0)\n",
            "did not",
        ),
        (b"x = 1\n", "MODULE"),
    ],
)
def test_bad_sources_are_module_errors_and_nothing_is_stored(conn, storage, admin, source, message):
    with pytest.raises(ModuleError, match=message):
        service.upload_module(conn, storage, admin, "bad", source)
    assert nothing_stored(conn, storage)


def test_a_syntax_error_is_found_without_running_anything(conn, storage, admin, monkeypatch):
    monkeypatch.setattr(service, "_inspect", lambda *a, **k: pytest.fail("ran the source"))
    with pytest.raises(ModuleError, match="line 1"):
        service.upload_module(conn, storage, admin, "bad", b"def run(:\n")


JUNK = "import os\nos.write(1, b'not json at all')\n" + GOOD
SLEEPER = "import time\ntime.sleep(60)\n" + GOOD
RAISER = "raise RuntimeError('boom at /secret/place/x.py')\n" + GOOD
EXITER = "import sys\nsys.exit(3)\n" + GOOD
HUGE = "import os\nos.write(1, b'x' * (2 << 20))\n" + GOOD
DEEP = "import os\nos.write(1, b'[' * 30000 + b']' * 30000)\n" + GOOD
FLOOD = "import os\nos.write(1, b'x' * (200 << 10))\n" + GOOD


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (JUNK, "metadata"),
        (SLEEPER, "longer than 1 s"),
        (RAISER, "RuntimeError"),
        (EXITER, "exit code 3"),
        (FLOOD, "metadata"),
        (HUGE, "File too large"),
        (DEEP, "metadata"),
    ],
)
def test_a_module_that_misbehaves_at_inspection_is_refused(conn, storage, admin, source, message):
    started = time.monotonic()
    with pytest.raises(ModuleError, match=message) as err:
        upload(conn, storage, admin, source, inspect_timeout=1.0)
    assert time.monotonic() - started < 8
    assert "/secret/place" not in str(err.value) and str(storage.root) not in str(err.value)
    assert nothing_stored(conn, storage)


@pytest.mark.parametrize(
    "module",
    [
        "{'name': 5, 'kind': 'frame', 'params': {'properties': {}}}",
        "{'name': 'x', 'kind': 'weird', 'params': {'properties': {}}}",
        "{'name': 'x', 'kind': 'frame', 'params': {'properties': {'a': {'type': 'object'}}}}",
        "{'name': 'x', 'kind': 'frame'}",
        "{'name': 'x', 'kind': 'predict', 'params': {'properties': {}}}",
        "{'name': '', 'kind': 'frame', 'params': {'properties': {}}}",
        "['not', 'a', 'dict']",
    ],
)
def test_malformed_metadata_is_refused(conn, storage, admin, module):
    with pytest.raises(ModuleError):
        upload(conn, storage, admin, f"MODULE = {module}\ndef run(df, params, ctx): return df\n")
    assert nothing_stored(conn, storage)


def test_a_module_without_run_is_refused(conn, storage, admin):
    source = "MODULE = {'name': 'x', 'kind': 'frame', 'params': {'properties': {}}}\n"
    with pytest.raises(ModuleError, match="run"):
        upload(conn, storage, admin, source)


def test_a_failed_store_leaves_no_row(conn, storage, admin, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(storage, "put", fail)
    with pytest.raises(OSError):
        upload(conn, storage, admin)
    assert nothing_stored(conn, storage)


def test_delete_module(conn, storage, admin, editor):
    upload(conn, storage, admin)
    with pytest.raises(PermissionError):
        service.delete_module(conn, storage, editor, "add_one")
    with pytest.raises(ValueError, match="built-in"):
        service.delete_module(conn, storage, admin, "kmeans_train")
    with pytest.raises(service.ModuleNotFound):
        service.delete_module(conn, storage, admin, "nothing_here")
    service.delete_module(conn, storage, admin, "add_one")
    assert nothing_stored(conn, storage) and not [
        m for m in service.list_modules(conn) if not m.builtin
    ]


def test_deleting_a_module_removes_the_states_it_trained(conn, storage, admin, project):
    upload(conn, storage, admin)

    def state(module_id):
        key = f"projects/{project.id}/module_models/{module_id}/state.json"
        storage.put(key, b"{}")
        conn.execute(
            "INSERT INTO module_models (project_id, module_id, name, state_key, created_at)"
            " VALUES (?, ?, ?, ?, 0)",
            (project.id, module_id, module_id, key),
        )
        return key

    mine, other = state("add_one"), state("kmeans_train")
    service.delete_module(conn, storage, admin, "add_one")
    rows = conn.execute("SELECT module_id FROM module_models").fetchall()
    assert [r[0] for r in rows] == ["kmeans_train"]
    assert not storage.exists(mine) and storage.exists(other)


# --- submitting -----------------------------------------------------------------------------


@pytest.fixture
def project(conn, editor):
    return projects.create_project(conn, editor, "demo")


def add_dataset(conn, storage, project, df=None, name="data", type=DatasetType.TRAIN):
    df = frame() if df is None else df
    return ingest.ingest_batches(storage, conn, project.id, name, type, [df])


def add_module_model(conn, project, module_id="kmeans_train", dataset_id=None):
    cur = conn.execute(
        "INSERT INTO module_models (project_id, module_id, name, state_key, source_dataset_id,"
        " created_at) VALUES (?, ?, 'm', 'k', ?, 1.0)",
        (project.id, module_id, dataset_id),
    )
    return cur.lastrowid


def test_submit_queues_a_validated_module_job(conn, storage, editor, project):
    data = add_dataset(conn, storage, project)
    job = service.submit_module(conn, editor, project.id, "sort", data.id, {"column": "x"})
    assert (job.kind, job.project_id, job.owner_id) == ("module", project.id, editor.id)
    assert job.payload == {
        "module_id": "sort",
        "dataset_id": data.id,
        "params": {"column": "x", "ascending": True},
        "name": None,
    }
    named = service.submit_module(
        conn, editor, project.id, "sort", data.id, {"column": "x"}, name="s"
    )
    assert named.payload["name"] == "s"
    assert store.get_job(conn, job.id).status.value == "queued"


def test_submit_permission_matrix(conn, storage, admin, editor, viewer, project):
    data = add_dataset(conn, storage, project)
    other_editor = auth.create_user(conn, "ed2", "pw-editor-2", Role.EDITOR)
    args = (project.id, "sort", data.id, {"column": "x"})
    service.submit_module(conn, admin, *args)
    with pytest.raises(PermissionError):
        service.submit_module(conn, viewer, *args)
    with pytest.raises(PermissionError):
        service.submit_module(conn, other_editor, *args)
    projects.share_project(conn, editor, project.id, "ed2", ProjectAccess.VIEWER)
    with pytest.raises(PermissionError):
        service.submit_module(conn, other_editor, *args)
    projects.share_project(conn, editor, project.id, "ed2", ProjectAccess.EDITOR)
    service.submit_module(conn, other_editor, *args)
    projects.share_project(conn, editor, project.id, "vi", ProjectAccess.EDITOR)
    with pytest.raises(PermissionError):  # a global viewer stays read-only
        service.submit_module(conn, viewer, *args)
    with pytest.raises(ProjectNotFound):
        service.submit_module(conn, editor, "missing", "sort", data.id, {"column": "x"})


@pytest.mark.parametrize(
    ("module_id", "params", "message"),
    [
        ("nope", {}, "unknown module"),
        ("../sort", {}, "unknown module"),
        ("sort", {}, "missing argument 'column'"),
        ("sort", {"column": 5}, "'column' must be of type string"),
        ("sort", {"column": "x", "extra": 1}, "unknown argument 'extra'"),
        ("sort", "x", "arguments must be an object"),
        ("cslice", {"columns": "id"}, "'columns' must be of type array"),
        ("split", {"seed": "1"}, "'seed' must be of type integer"),
        ("cbind", {"other_dataset_id": "1"}, "'other_dataset_id' must be of type integer"),
        ("cbind", {"other_dataset_id": True}, "'other_dataset_id' must be of type integer"),
    ],
)
def test_submit_rejects_bad_requests(conn, storage, editor, project, module_id, params, message):
    data = add_dataset(conn, storage, project)
    with pytest.raises(ValueError, match=re.escape(message)):
        service.submit_module(conn, editor, project.id, module_id, data.id, params)


@pytest.mark.parametrize("bad", [True, "1", 1.0, None])
def test_submit_requires_an_integer_dataset_id(conn, storage, editor, project, bad):
    add_dataset(conn, storage, project)
    with pytest.raises(ValueError, match="dataset_id"):
        service.submit_module(conn, editor, project.id, "sort", bad, {"column": "x"})
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_submit_checks_that_the_datasets_belong_to_the_project(conn, storage, editor, project):
    other_project = projects.create_project(conn, editor, "other")
    mine = add_dataset(conn, storage, project)
    theirs = add_dataset(conn, storage, other_project)
    with pytest.raises(DatasetNotFound):
        service.submit_module(conn, editor, project.id, "sort", theirs.id, {"column": "x"})
    with pytest.raises(DatasetNotFound):
        service.submit_module(conn, editor, project.id, "sort", 999, {"column": "x"})
    with pytest.raises(DatasetNotFound):
        service.submit_module(
            conn, editor, project.id, "cbind", mine.id, {"other_dataset_id": theirs.id}
        )
    ok = service.submit_module(
        conn, editor, project.id, "cbind", mine.id, {"other_dataset_id": mine.id}
    )
    assert ok.payload["params"] == {"other_dataset_id": mine.id}


def test_submit_checks_the_module_model(conn, storage, editor, project):
    other_project = projects.create_project(conn, editor, "other")
    mine = add_module_model(conn, project)
    theirs = add_module_model(conn, other_project)
    wrong_kind = add_module_model(conn, project, "lowrank_train")
    data = add_dataset(conn, storage, project)
    submit = lambda model_id: service.submit_module(  # noqa: E731
        conn, editor, project.id, "kmeans_predict", data.id, {"module_model_id": model_id}
    )
    assert submit(mine).payload["params"]["module_model_id"] == mine
    with pytest.raises(ValueError, match="unknown module model"):
        submit(theirs)
    with pytest.raises(ValueError, match="unknown module model"):
        submit(12345)
    with pytest.raises(ValueError, match="made by kmeans_train"):
        submit(wrong_kind)


def test_submit_accepts_uploaded_modules_and_their_declared_params(
    conn, storage, admin, editor, project
):
    upload(conn, storage, admin)
    data = add_dataset(conn, storage, project)
    job = service.submit_module(conn, editor, project.id, "add_one", data.id, {"by": 3})
    assert job.payload["params"] == {"by": 3}
    with pytest.raises(ValueError, match="'by' must be of type integer"):
        service.submit_module(conn, editor, project.id, "add_one", data.id, {"by": "x"})


def test_deleting_the_project_removes_its_module_models(conn, storage, editor, project):
    add_module_model(conn, project)
    projects.delete_project(conn, storage, editor, project.id)
    assert conn.execute("SELECT COUNT(*) FROM module_models").fetchone()[0] == 0


def test_deleting_the_dataset_keeps_the_model(conn, storage, editor, project):
    data = add_dataset(conn, storage, project)
    model_id = add_module_model(conn, project, dataset_id=data.id)
    projects.delete_dataset(conn, storage, data.id)
    row = conn.execute("SELECT * FROM module_models WHERE id = ?", (model_id,)).fetchone()
    assert row["source_dataset_id"] is None


# --- tokenize without user regexes -------------------------------------------------------------


def tokens(text, **params):
    out, _ = run_op("tokenize", expect(t=[text]), {"target_column": "t", **params})
    return [None if pd.isna(x) else x for x in out["t"]]


def test_tokenize_modes():
    assert tokens("a  b\tc,d", mode="whitespace") == ["a", "b", "c,d", None]
    assert tokens("a  b\tc,d") == ["a", "b", "c", "d", None]  # word is the default
    assert tokens("a,b,,c", mode="delimiter", delimiter=",") == ["a", "b", "c", None]
    # the delimiter is literal text, not a pattern
    assert tokens("a.b.c", mode="delimiter", delimiter=".") == ["a", "b", "c", None]
    assert tokens("a(a+)+b", mode="delimiter", delimiter="(a+)+") == ["a", "b", None]
    # Japanese: a run of letters is one token (no morphological analysis)
    assert tokens("猫は可愛い。犬も、好き") == ["猫は可愛い", "犬も", "好き", None]
    assert tokens("", mode="whitespace") == [None]


def test_tokenize_takes_no_regex():
    with pytest.raises(ValueError, match="unknown argument 'regex'"):
        run_op("tokenize", expect(t=["x"]), {"target_column": "t", "regex": "(a+)+$"})
    with pytest.raises(ModuleError, match="needs a delimiter"):
        tokens("x", mode="delimiter", delimiter="")
    with pytest.raises(ValueError, match="at most 20"):
        tokens("x", mode="delimiter", delimiter="x" * 21)


@pytest.mark.parametrize(
    "params",
    [{"mode": "whitespace"}, {"mode": "word"}, {"mode": "delimiter", "delimiter": "a"}],
)
def test_tokenize_is_linear_on_hostile_text(params):
    text = "a" * 24 + "!" + " ab" * 33_000
    started = time.monotonic()
    out = tokens(text, **params)
    assert time.monotonic() - started < 10 and len(out) > 1


# --- calc: a column computed from other columns ---------------------------------------------


def calc_frame():
    return pd.DataFrame(
        {
            "a": [1.0, 2.0, np.nan, 4.0, -3.0],
            "b": [2.0, 0.0, 5.0, np.nan, 3.0],
            "n": pd.array([1, 2, 3, None, 5], dtype="Int64"),
            "flag_x_1": [1, 0, 1, 1, 0],
            "flag_y_2": [0, 0, 1, np.nan, 1],
            "flag_t": ["u", "v", "u", "v", "u"],
            "unit price": [10.0, 20.0, 40.0, 5.0, 1.0],
            "名前": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )


def calc(expression, df=None, name="out"):
    out, _ = run_op(
        "calc", calc_frame() if df is None else df, {"name": name, "expression": expression}
    )
    return out[name].to_numpy()


def test_calc_adds_one_float_column_and_leaves_the_rest_as_it_is():
    df = calc_frame().set_axis([10, 11, 12, 13, 14])
    out, _ = run_op("calc", df, {"name": " total ", "expression": "a + 1"})
    assert list(out.columns) == [*df.columns, "total"]
    assert out["total"].dtype == np.float64
    pd.testing.assert_frame_equal(out[list(df.columns)], df)
    assert out.index.tolist() == [10, 11, 12, 13, 14]


def test_calc_arithmetic_matches_pandas_with_empty_values():
    df = calc_frame()
    a, b = df["a"], df["b"]
    np.testing.assert_allclose(calc("a + b * 2 - 1"), a + b * 2 - 1, equal_nan=True)
    np.testing.assert_allclose(calc("-a ** 2 + +b"), -(a**2) + b, equal_nan=True)
    ratio = ((a - b) / (a + b)).replace([np.inf, -np.inf], np.nan)  # a + b is 0 in row 4
    np.testing.assert_allclose(calc("(a - b) / (a + b)"), ratio, equal_nan=True)
    np.testing.assert_allclose(calc("n * 2 + 0.5"), df["n"].astype(float) * 2 + 0.5, equal_nan=True)
    np.testing.assert_allclose(calc("a ** 0.5"), np.where(a >= 0, a**0.5, np.nan), equal_nan=True)


def test_calc_division_by_zero_and_other_infinite_results_are_empty():
    out = calc("a / b")  # b is 0 in row 1
    assert np.isnan(out[1]) and out[0] == 0.5 and out[4] == -1.0
    assert np.isnan(calc("1 / 0")).all() and np.isnan(calc("0 / 0")).all()
    assert np.isnan(calc("log(b)")[1]) and np.isnan(calc("exp(1000)")).all()
    inf = pd.DataFrame({"a": [np.inf, -np.inf, 1.0]})
    np.testing.assert_array_equal(calc("a", inf), [np.nan, np.nan, 1.0])


def test_calc_functions_match_numpy_and_pandas():
    df = calc_frame()
    a, b = df["a"], df["b"]
    np.testing.assert_allclose(calc("abs(a)"), a.abs(), equal_nan=True)
    np.testing.assert_allclose(calc("sqrt(abs(a))"), np.sqrt(a.abs()), equal_nan=True)
    np.testing.assert_allclose(calc("log1p(abs(a))"), np.log1p(a.abs()), equal_nan=True)
    np.testing.assert_allclose(calc("exp(a / 4)"), np.exp(a / 4), equal_nan=True)
    assert np.isnan(calc("sqrt(a)")[4]) and np.isnan(calc("log(a)")[4])
    np.testing.assert_allclose(calc("min2(a, b)"), np.minimum(a, b), equal_nan=True)
    np.testing.assert_allclose(calc("max2(a, 1)"), np.maximum(a, 1), equal_nan=True)
    np.testing.assert_allclose(calc("clip(a, -1, 2)"), a.clip(-1, 2), equal_nan=True)
    np.testing.assert_array_equal(calc("isnull(a) + isnull(b)"), a.isna() * 1.0 + b.isna())
    np.testing.assert_array_equal(calc("where(a > 1, a, -1)"), np.where(a > 1, a, -1))
    np.testing.assert_array_equal(calc("where(a > 1, a, nan)"), np.where(a > 1, a, np.nan))


def test_calc_comparisons_and_booleans_give_zero_or_one():
    np.testing.assert_array_equal(calc("a > b"), [0, 1, 0, 0, 0])
    np.testing.assert_array_equal(calc("a == 4"), [0, 0, 0, 1, 0])
    np.testing.assert_array_equal(calc("a != 4"), [1, 1, 1, 0, 1])  # empty is not 4
    np.testing.assert_array_equal(calc("(a > 0) & (b > 0)"), [1, 0, 0, 0, 0])
    np.testing.assert_array_equal(calc("(a > 3) | (b > 4)"), [0, 0, 1, 1, 0])
    np.testing.assert_array_equal(calc("~(a > 0)"), [0, 0, 1, 0, 1])
    with pytest.raises(ModuleError, match="two values at a time"):
        calc("a > 0 & b > 0")  # reads as the chain a > (0 & b) > 0
    with pytest.raises(ModuleError, match="two values at a time"):
        calc("0 < a < 5")
    with pytest.raises(ModuleError, match="and/or"):
        calc("(a > 0) and (b > 0)")


def test_calc_row_functions_over_columns_and_patterns_skip_empty_values():
    df = calc_frame()
    flags = df[["flag_x_1", "flag_y_2"]]
    np.testing.assert_array_equal(calc('rowsum("flag_*_*")'), flags.sum(axis=1))
    np.testing.assert_array_equal(calc('rowcount("flag_*_*")'), flags.count(axis=1))
    np.testing.assert_allclose(calc('rowmean("flag_*_*")'), flags.mean(axis=1))
    np.testing.assert_allclose(calc("rowsum(a, b, 1)"), df[["a", "b"]].sum(axis=1) + 1)
    np.testing.assert_allclose(calc('rowsum("flag_x*", a)'), df[["flag_x_1", "a"]].sum(axis=1))
    both = pd.DataFrame({"a": [np.nan, 1.0], "b": [np.nan, 3.0]})
    out = calc("rowmean(a, b)", both)
    assert np.isnan(out[0]) and out[1] == 2.0
    assert calc("rowsum(a, b)", both).tolist() == [0.0, 4.0]
    with pytest.raises(ModuleError, match="no column matches 'zzz\\*'"):
        calc('rowsum("zzz*")')
    with pytest.raises(ModuleError, match="column 'flag_t' is not numeric"):
        calc('rowsum("flag_*")')
    with pytest.raises(ModuleError, match="at least one"):
        calc("rowsum()")


def test_calc_names_with_spaces_or_symbols_are_written_with_col():
    np.testing.assert_array_equal(calc('col("unit price") / 10'), [1, 2, 4, 0.5, 0.1])
    np.testing.assert_array_equal(calc('col("名前") * 2'), [2, 4, 6, 8, 10])
    np.testing.assert_array_equal(calc("名前 * 2"), [2, 4, 6, 8, 10])
    full = pd.DataFrame({"売上１": [1.0, 2.0], "ｶﾃｺﾞﾘ": [3.0, 4.0]})  # read as 売上1, カテゴリ
    np.testing.assert_array_equal(calc("売上１ + ｶﾃｺﾞﾘ", full), [4, 6])
    np.testing.assert_array_equal(calc('col("売上１") * 2', full), [2, 4])
    odd = pd.DataFrame({"a-b": [1.0, 2.0], "if": [3.0, 4.0], "nan": [5.0, 6.0]})
    np.testing.assert_array_equal(calc('col("a-b") + col("if") + nan', odd), [9, 12])
    with pytest.raises(ModuleError, match=r"unknown column 'unit prize'"):
        calc('col("unit price") + col("unit prize")')
    with pytest.raises(ModuleError, match=r'unknown column \'zz\'; write.*col\("zz"\)'):
        calc("zz + 1")
    with pytest.raises(ModuleError, match="takes one name in quotes"):
        calc("col(a)")


def test_calc_star_is_the_only_wildcard_and_works_in_the_middle():
    odd = pd.DataFrame(
        {"q?": [1.0], "qa": [2.0], "[ab]": [4.0], "a": [8.0], "b": [16.0], "a_x_b": [32.0]}
    )
    assert calc('rowsum("q?")', odd).tolist() == [1.0]  # ? is a question mark
    assert calc('rowsum("[ab]")', odd).tolist() == [4.0]  # not a set of a and b
    assert calc('rowsum("a*b")', odd).tolist() == [32.0]
    assert calc('rowsum("a*x*b", "q*")', odd).tolist() == [35.0]
    assert calc('rowcount("*")', odd).tolist() == [6.0]
    assert calc('rowcount("a_x_b", "a_x_b*", "*a_x_b", "a_x_b")', odd).tolist() == [1.0]  # once
    for pattern in ["a*a", "q?*?", "ab*", "*xa_x_b"]:
        with pytest.raises(ModuleError, match="no column matches"):
            calc(f'rowsum("{pattern}")', odd)


def test_calc_names_the_column_that_is_not_numeric():
    with pytest.raises(ModuleError, match="column 'flag_t' is not numeric"):
        calc("flag_t + 1")
    dates = pd.DataFrame({"d": pd.to_datetime(["2020-01-01"])})
    with pytest.raises(ModuleError, match="column 'd' is not numeric"):
        calc("d + 1", dates)


def test_calc_reads_a_yes_no_column_as_one_and_zero():
    flags = pd.DataFrame(
        {"yes": [True, False, True], "maybe": pd.array([True, None, False], dtype="boolean")}
    )
    assert calc("yes + 1", flags).tolist() == [2.0, 1.0, 2.0]
    np.testing.assert_array_equal(calc("yes + maybe", flags), [2, np.nan, 1])
    np.testing.assert_array_equal(calc('rowsum("*")', flags), [2, 0, 1])


def test_calc_refuses_what_is_not_arithmetic():
    for text, match in [
        ("__import__('os')", "unknown function '__import__'"),
        ("__import__('os').system('true')", "not allowed in an expression: attribute access"),
        ("a.__class__", "attribute access"),
        ("(1).real", "attribute access"),
        ("lambda: 1", "lambda"),
        ("[a for a in b]", "comprehension"),
        ("[1, 2]", "not allowed in an expression: List"),
        ("a[0]", "subscript"),
        ("a if b else 1", "if/else"),
        ("(x := 1)", "assignment"),
        ("'abc'", "only numbers"),
        ("'a' + 'b'", "only numbers"),
        ("f'{a}'", "formatted text"),
        ("abs(a)(b)", "calling the result"),
        ("a.abs()", "attribute access"),
        ("class + 1", r'col\("class"\)'),
        ("1st", r'col\("class"\)'),
        ("abs(*a)", "not allowed in an expression: [*]"),
        ("abs(a, b)", "takes 1 argument"),
        ("abs(x=a)", "no named arguments"),
        ("open('x')", "unknown function 'open'"),
        ("eval('1')", "unknown function 'eval'"),
        ("a % 2", "this operator"),
        ("a // 2", "this operator"),
        ("a ^ 2", "this operator"),
        ("True", "only numbers"),
        ("1e999", "too large"),
        ("a +", "cannot read the expression"),
        ("", "cannot read the expression"),
        ("a; b", "cannot read the expression"),
        ("a\x00", "cannot read the expression"),
    ]:
        with pytest.raises(ModuleError, match=match):
            calc(text)


def test_calc_bounds_the_length_the_depth_and_the_size_of_a_number():
    started = time.monotonic()
    assert np.isnan(calc("9 ** 9 ** 9")).all()  # a float power: no huge integer is built
    assert np.isnan(calc("10 ** 300 * 10 ** 300")).all()  # an overflow is empty
    assert time.monotonic() - started < 10
    with pytest.raises(ModuleError, match="longer than 1000"):
        expression.evaluate("1 + " * 300 + "1", calc_frame())
    np.testing.assert_array_equal(calc("(" * 150 + "a" + ")" * 150), calc_frame()["a"])
    with pytest.raises(ModuleError, match="cannot read the expression"):
        calc("(" * 250 + "a" + ")" * 250)
    with pytest.raises(ModuleError, match="cannot read the expression"):
        calc("(" * 499 + "a" + ")" * 499)
    # a deep or long stack of operators is refused quickly, never a crash of the process
    for deep in [
        "-" * 999 + "a",
        "~" * 999 + "a",
        "+".join(["a"] * 500)[:999],
        "abs(" * 150 + "a" + ")" * 150,
    ]:
        with pytest.raises(ModuleError, match="nested too deeply"):
            calc(deep)
    assert calc("+".join(["1"] * 50)).tolist() == [50.0] * 5  # a chain of 50 terms is fine


def test_calc_bounds_what_the_row_functions_read_before_reading_it(monkeypatch):
    monkeypatch.setattr(registry, "MAX_OUTPUT_CELLS", 20)
    wide = pd.DataFrame({f"c{i}": [1.0, 2.0] for i in range(5)})
    assert calc('rowsum("*")', wide).tolist() == [5.0, 10.0]  # 2 rows x 5 columns
    assert calc('rowsum("*", "c*", "*0", "c0")', wide).tolist() == [5.0, 10.0]  # each read once
    with pytest.raises(ModuleError, match="reads 11 columns and values on each of 2 rows"):
        calc('rowsum("*", 1, 1, 1, 1, 1, 1)', wide)
    cheap = ", ".join(["a"] * 11)  # also a count of operands, not only of columns
    with pytest.raises(ModuleError, match="reads 11 columns"):
        calc(f"rowsum({cheap})", pd.DataFrame({"a": [1.0, 2.0]}))


def test_calc_repeated_patterns_are_read_once_and_the_operands_have_an_absolute_cap():
    started = time.monotonic()
    many = "rowsum(" + ",".join(['"*"'] * 245) + ")"
    nine = pd.DataFrame(np.ones((1, 9000)), columns=[f"c{i}" for i in range(9000)])
    assert calc(many, nine).tolist() == [9000.0]  # 9,000 columns, each read once
    wide = pd.DataFrame(np.ones((1, 20000)), columns=[f"c{i}" for i in range(20000)])
    with pytest.raises(ModuleError, match="more than 10000 columns and values"):
        calc(many, wide)
    with pytest.raises(ModuleError, match="more than 10000 columns and values"):
        calc("rowsum(" + ", ".join(f'"c{i}*"' for i in range(1, 60)) + ")", wide)
    assert time.monotonic() - started < 20


def test_calc_counts_the_arrays_a_nested_expression_holds_at_once(monkeypatch):
    monkeypatch.setattr(registry, "MAX_OUTPUT_CELLS", 1000)
    df = pd.DataFrame({"a": np.arange(10.0)})
    right = "-a+(" * 99 + "a" + ")" * 99  # holds an array for each level while the right is run
    with pytest.raises(ModuleError, match="holds 101 columns of 10 values at once"):
        calc(right, df)
    left = "+".join(["a"] * 24)  # a hand-written sum holds three at most
    assert calc(left, df).tolist() == (df["a"] * 24).tolist()
    assert calc("a + (a + (a + a))", df).tolist() == (df["a"] * 4).tolist()
    assert calc('rowsum(a, "a", a * 2)', df).tolist() == (df["a"] * 4).tolist()


def test_calc_reads_a_name_in_full_width_with_one_pass_over_the_columns(monkeypatch):
    calls = []
    original = expression.unicodedata.normalize
    monkeypatch.setattr(
        expression.unicodedata,
        "normalize",
        lambda form, text: calls.append(1) or original(form, text),
    )
    df = pd.DataFrame(np.ones((2, 2000)), columns=["ａ", *[f"c{i}" for i in range(1999)]])
    assert calc("+".join(["ａ"] * 100), df).tolist() == [100.0, 100.0]
    assert len(calls) < 3000  # not once per reference and column: 200,000


def test_calc_matches_a_pattern_to_a_column_whose_label_is_not_text():
    df = pd.DataFrame({1: [1.0, 2.0], "x": [10.0, 20.0], 12: [100.0, 200.0]})
    values, _ = expression.evaluate('rowsum("1*") + col("x")', df)
    assert values.tolist() == [111.0, 222.0]


def test_calc_a_pattern_does_not_keep_its_columns(monkeypatch):
    kept = []
    original = expression._Evaluator.column

    def spy(self, name, keep=True):
        out = original(self, name, keep)
        kept.append(len(self.columns))
        return out

    monkeypatch.setattr(expression._Evaluator, "column", spy)
    wide = pd.DataFrame({f"c{i}": [1.0, 2.0] for i in range(5)})
    assert calc('rowsum("*")', wide).tolist() == [5.0, 10.0]
    assert max(kept) == 0


def test_calc_tells_how_many_rows_had_an_infinite_result():
    df = pd.DataFrame({"a": [1.0, 0.0, 2.0, 0.0, np.nan], "b": [0.0, 0.0, 4.0, 5.0, 0.0]})

    def notes(expression_text):
        module = get_builtin("calc")
        params = validate_args(module.params, {"name": "r", "expression": expression_text})
        return module.run(df, params, ModuleContext(None, None)).notes

    (note,) = notes("a / b")  # only row 0 is infinite: 0 / 0 and empty / 0 are empty, not infinite
    assert (note["kind"], note["rows_infinite"], note["rows"]) == ("calc_infinite", 1, 5)
    assert note["message"].startswith("1 of 5 rows have an infinite result")
    assert notes("a + b") == ()
    assert notes("where(b == 0, 0, a / b)") == ()  # the infinite step was not used
    assert notes("log(a)")[0]["rows_infinite"] == 2
    assert notes("1 / a + 1 / b")[0]["rows_infinite"] == 4  # rows 0, 1, 3 and 4
    module = get_builtin("calc")  # an infinite value in a column is empty, without a note
    params = validate_args(module.params, {"name": "r", "expression": "a + 1"})
    out = module.run(pd.DataFrame({"a": [np.inf, 1.0]}), params, ModuleContext(None, None))
    assert out.notes == () and np.isnan(out.df["r"][0])


def test_calc_refuses_a_missing_empty_or_existing_name():
    with pytest.raises(ModuleError, match="name the new column"):
        calc("1", name="  ")
    with pytest.raises(ModuleError, match="column 'a' already exists"):
        calc("1", name="a")
    with pytest.raises(ModuleError, match="column 'a' already exists"):
        calc("1", name=" a ")


def test_calc_is_refused_over_the_cell_cap(monkeypatch):
    monkeypatch.setattr(registry, "MAX_OUTPUT_CELLS", 10)
    module = get_builtin("calc")
    with pytest.raises(ModuleError, match="10 cells"):
        module.run(
            expect(a=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
            {"name": "b", "expression": "a"},
            ModuleContext(None, None),
        )


def test_calc_params_are_registered_and_validated():
    module = get_builtin("calc")
    assert module.kind == "frame" and module.name == "Add a calculated column"
    assert module.params["required"] == ["name", "expression"]
    described = module.params["properties"]["expression"]["description"]
    assert "rowsum" in described and "where" in described and len(described) < 450
    check_schema(module.params)
    with pytest.raises(ValueError):
        validate_args(module.params, {"name": "x"})
    with pytest.raises(ValueError):
        validate_args(module.params, {"name": "x", "expression": "1" * 1001})


# --- the output-size estimate runs before the result is built --------------------------------


def test_unpivot_refuses_a_column_kept_and_unpivoted_or_nothing_to_unpivot():
    df = pd.DataFrame({"id": [1], "a": [2]})
    with pytest.raises(ModuleError, match="both kept and unpivoted"):
        run_op("unpivot", df, {"keep": ["id"], "columns": ["id", "a"]})
    with pytest.raises(ModuleError, match="no column is left"):
        run_op("unpivot", df, {"keep": ["id", "a"]})
    with pytest.raises(ModuleError, match="all be different"):
        run_op("unpivot", df, {"keep": ["id"], "name": "id"})


def test_pivot_is_refused_before_it_is_built():
    import tracemalloc

    n = 13_000  # 13,000 x 13,001 cells would be over the 150 million cap
    df = pd.DataFrame(
        {
            "i": np.r_[np.arange(n), np.arange(n)],
            "c": np.r_[np.arange(n), np.arange(n)[::-1]],
            "v": 1.0,
        }
    )
    tracemalloc.start()
    started = time.monotonic()
    try:
        with pytest.raises(ModuleError, match="cells"):
            run_op("pivot", df, {"index": "i", "column": "c", "value": "v"})
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert time.monotonic() - started < 10 and peak < 50_000_000


def _pivot(df, **params):
    module = get_builtin("pivot")
    args = validate_args(module.params, {"index": "k", "column": "c", "value": "v", **params})
    return module.run(df.copy(), args, ModuleContext(None, None))


_PIVOT_ROWS = pd.DataFrame(
    {
        "k": [1, 1, 1, 2, 2, 3],
        "c": ["a", "a", "b", "a", "b", "b"],
        "v": [1.0, np.nan, 5.0, 2.0, 4.0, np.nan],
    }
)


@pytest.mark.parametrize("agg", ["sum", "mean", "min", "max", "count"])
def test_pivot_combines_the_rows_of_a_cell_as_pandas_does(agg):
    out = _pivot(_PIVOT_ROWS, agg=agg)
    want = _PIVOT_ROWS.pivot_table(index="k", columns="c", values="v", aggfunc=agg, dropna=False)
    cells = _PIVOT_ROWS.groupby(["k", "c"]).v.count().unstack()
    if agg == "sum":  # a cell with nothing to add up stays empty rather than 0
        want = want.where(cells > 0)
    if agg == "count":  # a cell with no row at all stays empty
        want = want.where(_PIVOT_ROWS.groupby(["k", "c"]).size().unstack().notna())
    assert out.df["k"].tolist() == [1, 2, 3]
    for c in ("a", "b"):
        assert out.df[c].tolist() == pytest.approx(want[c].tolist(), nan_ok=True)
    assert out.notes == ()


def test_pivot_keeps_the_first_value_by_default_and_says_which_cells_hold_more_values():
    rows = _PIVOT_ROWS.assign(v=[1.0, 9.0, 5.0, 2.0, 4.0, np.nan])  # (1, a) holds 1.0 and 9.0
    out = _pivot(rows)
    assert list(out.df.columns) == ["k", "a", "b"]
    assert out.df["a"].tolist() == pytest.approx([1.0, 2.0, np.nan], nan_ok=True)
    assert out.df["b"].tolist() == pytest.approx([5.0, 4.0, np.nan], nan_ok=True)
    (note,) = out.notes
    assert (note["kind"], note["cells_shared"], note["cells"]) == ("pivot_cells_shared", 1, 5)
    assert "agg" in note["message"] and "1 of 5 cells" in note["message"]
    assert "2 values" in note["message"]
    assert _pivot(rows, agg="first").notes == out.notes
    assert _pivot(rows, agg="sum").notes == ()
    # a second row whose value is empty holds no second value: there is nothing to lose
    assert _pivot(_PIVOT_ROWS).notes == ()
    assert _pivot(rows.drop_duplicates(["k", "c"])).notes == ()


def test_pivot_says_how_many_rows_with_an_empty_index_or_column_are_left_out():
    df = pd.DataFrame(
        {"k": [1, 2, 3, np.nan], "c": ["a", "a", None, "b"], "v": [1.0, 2.0, 3.0, 4.0]}
    )
    for agg in ("first", "sum"):
        out = _pivot(df, agg=agg)
        (note,) = out.notes
        assert (note["kind"], note["rows_left_out"], note["rows"]) == ("pivot_rows_left_out", 2, 4)
        assert note["index_values_lost"] == 1 and out.df["k"].tolist() == [1.0, 2.0]


def test_pivot_refuses_a_value_that_is_not_a_number_for_a_numeric_aggregate():
    df = pd.DataFrame({"k": [1, 1], "c": ["a", "a"], "v": ["x", "y"]})
    for agg in ("sum", "mean", "min", "max"):
        with pytest.raises(ModuleError, match="needs a numeric value column"):
            _pivot(df, agg=agg)
    assert _pivot(df, agg="count").df["a"].tolist() == [2]
    assert _pivot(df).df["a"].tolist() == ["x"]


def test_cor_of_too_many_columns_is_refused():
    wide = pd.DataFrame(np.zeros((3, 13_000)), columns=[f"c{i}" for i in range(13_000)])
    started = time.monotonic()
    with pytest.raises(ModuleError, match="cells"):
        run_op("cor", wide)
    assert time.monotonic() - started < 1.0


def test_tokenize_and_binds_are_refused_by_their_bounds(monkeypatch):
    monkeypatch.setattr(registry, "MAX_OUTPUT_CELLS", 10)

    def run_op(op, df, params, other=None):  # no output check: only the estimate can refuse
        module = get_builtin(op)
        return module.run(df, validate_args(module.params, params), ModuleContext(other, None))

    with pytest.raises(ModuleError, match="10 cells"):
        run_op("tokenize", expect(t=["a b c d e f g h i j k"]), {"target_column": "t"})
    small = expect(a=[1, 2, 3], b=[1, 2, 3])
    with pytest.raises(ModuleError, match="10 cells"):
        run_op(
            "cbind",
            small,
            {"other_dataset_id": 1},
            other=expect(c=[1, 2, 3], d=[1, 2, 3], e=[1, 2, 3]),
        )
    with pytest.raises(ModuleError, match="10 cells"):
        run_op("rbind", small, {"other_dataset_id": 1}, other=small)
    with pytest.raises(ModuleError, match="10 cells"):
        run_op("concat", small, {"other_dataset_id": 1, "axis": 0}, other=small)


def test_a_large_cslice_passes_the_default_cap():
    big = pd.DataFrame(np.zeros((100_000, 20)), columns=[f"c{i}" for i in range(20)])
    out, _ = run_op("cslice", big, {"columns": ["c1", "c2"]})
    assert out.shape == (100_000, 2)
    assert validate_output(big).shape == (100_000, 20)


# --- low-rank size and submit id types --------------------------------------------------------


@pytest.mark.parametrize("method", ["svd", "nmf"])
def test_lowrank_components_are_limited_by_the_rows_too(method):
    with pytest.raises(ModuleError, match="at most 1"):
        run_op(
            "lowrank_train",
            expect(a=[1.0], b=[2.0], c=[3.0]),
            {"method": method, "n_components": 2},
        )


def test_lag_reads_the_value_at_an_earlier_time_not_the_row_before():
    # shop 1 has no row at month 3: the lag of month 4 is empty, not month 2's value
    df = pd.DataFrame(
        {
            "shop": [1, 1, 1, 2, 2, 2],
            "month": [1, 2, 4, 1, 2, 3],
            "sales": [10.0, 20.0, 40.0, 1.0, 2.0, 3.0],
        }
    )
    out, _ = run_op(
        "lag", df, {"time": "month", "by": ["shop"], "columns": ["sales"], "lags": "1,2"}
    )
    assert list(out.columns) == ["shop", "month", "sales", "sales_lag1", "sales_lag2"]
    assert list(out["sales_lag1"].fillna(-1)) == [-1, 10.0, -1, -1, 1.0, 2.0]
    assert list(out["sales_lag2"].fillna(-1)) == [-1, -1, 20.0, -1, -1, 1.0]
    assert list(out["sales"]) == [10.0, 20.0, 40.0, 1.0, 2.0, 3.0]  # rows and order are kept


def test_lag_reduces_the_rows_of_a_group_and_time_to_one_value_first():
    # by "item" only: the mean (or sum) of the item over its shops at the earlier time
    df = pd.DataFrame(
        {
            "item": [7, 7, 7, 7, 9],
            "shop": [1, 2, 1, 2, 1],
            "month": [1, 1, 2, 2, 2],
            "n": [2.0, 4.0, 5.0, 7.0, 1.0],
        }
    )
    mean, _ = run_op("lag", df, {"time": "month", "by": ["item"], "columns": ["n"]})
    assert list(mean["n_lag1"].fillna(-1)) == [-1, -1, 3.0, 3.0, -1]
    total, _ = run_op("lag", df, {"time": "month", "by": ["item"], "columns": ["n"], "how": "sum"})
    assert list(total["n_lag1"].fillna(-1)) == [-1, -1, 6.0, 6.0, -1]
    assert len(mean) == len(df)  # a row is never multiplied


def test_lag_without_a_group_lags_the_whole_frame_and_names_do_not_collide():
    df = pd.DataFrame({"t": [1, 2, 3], "v": [1.0, 2.0, 3.0], "v_lag1": ["a", "b", "c"]})
    out, _ = run_op("lag", df, {"time": "t", "columns": ["v"]})
    assert list(out.columns) == ["t", "v", "v_lag1", "v_lag1_2"]
    assert list(out["v_lag1_2"].fillna(-1)) == [-1, 1.0, 2.0]


def test_lag_leaves_a_missing_time_or_group_empty_and_refuses_unclear_input():
    df = pd.DataFrame(
        {"g": [1, 1, None], "t": [1.0, 2.0, np.nan], "v": [5.0, 6.0, 7.0], "half": [0.5, 1.0, 1.5]}
    )
    out, _ = run_op("lag", df, {"time": "t", "by": ["g"], "columns": ["v"]})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 5.0, -1]
    for params, message in (
        ({"time": "t", "columns": []}, "name the columns"),
        ({"time": "t", "columns": ["g"], "by": ["g"]}, "only the time or the by"),
        ({"time": "t", "by": ["t"], "columns": ["v"]}, "cannot include the time"),
        ({"time": "t", "columns": ["v"], "lags": "0"}, "at least 1"),
        ({"time": "t", "columns": ["v"], "lags": "x"}, "separated by commas"),
        ({"time": "zz", "columns": ["v"]}, "unknown column 'zz'"),
        ({"time": "half", "columns": ["v"]}, "whole numbers"),
    ):
        with pytest.raises(ModuleError, match=message):
            run_op("lag", df, params)
    names = pd.DataFrame({"t": [1, 2], "s": ["a", "b"]})
    with pytest.raises(ModuleError, match="is not numeric"):
        run_op("lag", names, {"time": "t", "columns": ["s"]})


def test_rolling_takes_the_rows_before_in_the_order_of_a_column_within_a_group():
    # the rows are not in time order in the file; the window is the rows before in time order
    df = pd.DataFrame(
        {
            "g": [1, 1, 1, 1, 2, 2],
            "t": [3.5, 1.5, 2.5, 4.5, 1.0, 2.0],
            "v": [30.0, 10.0, 20.0, 40.0, 1.0, 2.0],
        }
    )
    out, _ = run_op(
        "rolling",
        df,
        {"order": "t", "by": ["g"], "columns": ["v"], "window": 2, "stats": "mean,max"},
    )
    assert list(out.columns) == ["g", "t", "v", "v_before2_mean", "v_before2_max"]
    assert list(out["v"]) == [30.0, 10.0, 20.0, 40.0, 1.0, 2.0]  # the rows stay where they were
    assert list(out["v_before2_mean"].fillna(-1)) == [15.0, -1, 10.0, 25.0, -1, 1.0]
    assert list(out["v_before2_max"].fillna(-1)) == [20.0, -1, 10.0, 30.0, -1, 1.0]


def test_rolling_sums_and_counts_all_the_rows_before_with_a_window_wider_than_the_group():
    df = pd.DataFrame(
        {
            "g": [1, 1, 1, 1, 2, 2],
            "t": [3, 1, 2, 4, 1, 2],
            "v": [30.0, 10.0, 20.0, 40.0, 1.0, 2.0],
        }
    )
    out, _ = run_op(
        "rolling",
        df,
        {"order": "t", "by": ["g"], "columns": ["v"], "window": 1_000_000, "stats": "sum,count"},
    )
    assert list(out.columns) == ["g", "t", "v", "v_before1000000_sum", "v_before1000000_count"]
    # a running total of the rows before, per group, in the order of t
    assert list(out["v_before1000000_sum"].fillna(-1)) == [30.0, -1, 10.0, 60.0, -1, 1.0]
    assert list(out["v_before1000000_count"].fillna(-1)) == [2, -1, 1, 3, -1, 1]


def test_rolling_around_includes_the_row_itself_and_is_shorter_at_the_edges():
    values = pd.Series([1.0, 4.0, 2.0, 8.0, 5.0, 7.0])
    df = pd.DataFrame({"t": range(6), "v": values})
    out, _ = run_op(
        "rolling",
        df,
        {"order": "t", "columns": ["v"], "window": 3, "side": "around", "stats": "mean,std,min"},
    )
    expected = values.rolling(3, center=True, min_periods=1)
    np.testing.assert_allclose(out["v_around3_mean"], expected.mean())
    np.testing.assert_allclose(out["v_around3_std"], expected.std(), equal_nan=True)
    np.testing.assert_allclose(out["v_around3_min"], expected.min())


def test_rolling_after_takes_the_rows_later_in_the_order_and_not_the_row_itself():
    df = pd.DataFrame({"t": range(6), "g": [0, 0, 0, 1, 1, 1], "v": [1.0, 4.0, 2.0, 8.0, 5.0, 7.0]})
    out, _ = run_op(
        "rolling",
        df,
        {
            "order": "t",
            "by": ["g"],
            "columns": ["v"],
            "window": 2,
            "side": "after",
            "stats": "mean,count",
        },
    )
    assert list(out.columns[-2:]) == ["v_after2_mean", "v_after2_count"]
    # the next two rows of the group; the last row of a group has none
    expected = [3.0, 2.0, np.nan, 6.0, 7.0, np.nan]
    np.testing.assert_allclose(out["v_after2_mean"].to_numpy(), expected, equal_nan=True)
    np.testing.assert_allclose(
        out["v_after2_count"].to_numpy(), [2, 1, np.nan, 2, 1, np.nan], equal_nan=True
    )
    # rows of one order do not read each other: both rows of order 1 read the first row after them
    tied = pd.DataFrame({"t": [1, 1, 2, 2], "v": [1.0, 3.0, 10.0, 20.0]})
    out, _ = run_op("rolling", tied, {"order": "t", "columns": ["v"], "window": 1, "side": "after"})
    np.testing.assert_allclose(out["v_after1_mean"], [10.0, 10.0, np.nan, np.nan], equal_nan=True)


def test_rolling_leaves_a_row_without_an_order_empty_and_out_of_the_windows():
    df = pd.DataFrame({"t": [1.0, None, 2.0, 3.0], "v": [1.0, 100.0, 2.0, 3.0]})
    out, _ = run_op("rolling", df, {"order": "t", "columns": ["v"], "window": 2})
    assert list(out["v_before2_mean"].fillna(-1)) == [-1, -1, 1.0, 1.5]


def test_rolling_reads_dates_in_any_form_and_rows_of_one_order_do_not_read_each_other():
    dates = ["2015-07-02", "2015-07-01", "2015-07-02", "2015-07-03"]
    df = pd.DataFrame({"day": dates, "v": [2.0, 1.0, 3.0, 4.0]})
    params = {"order": "day", "columns": ["v"], "window": 2}
    out, _ = run_op("rolling", df, params)
    # the two rows of 07-02 read only 07-01, not each other; 07-03 reads both of them
    assert list(out["v_before2_mean"].fillna(-1)) == [1.0, -1, 1.0, 2.5]
    assert list(out["day"]) == dates
    # the same dates as timestamps, as date objects (a CSV import) and far in the future
    for day in (
        pd.to_datetime(dates),
        [datetime.date.fromisoformat(d) for d in dates],
        [datetime.datetime.fromisoformat(d) for d in dates],
    ):
        again, _ = run_op("rolling", df.assign(day=pd.Series(day, dtype=object)), params)
        assert list(again["v_before2_mean"].fillna(-1)) == list(out["v_before2_mean"].fillna(-1))
    far = pd.Series([datetime.date(9999, 12, 31), datetime.date(2015, 7, 1)], dtype=object)
    ahead, _ = run_op("rolling", pd.DataFrame({"day": far, "v": [2.0, 1.0]}), params)
    assert list(ahead["v_before2_mean"].fillna(-1)) == [1.0, -1]
    around, _ = run_op("rolling", df, {**params, "window": 3, "side": "around"})
    assert list(around["v_around3_mean"]) == [2.0, 1.5, 3.0, 3.5]  # around reads the tied rows


def test_rolling_matches_a_window_per_group_on_messy_data():
    rng = np.random.default_rng(3)
    n = 400
    df = pd.DataFrame(
        {
            "g": rng.integers(0, 5, n).astype(float),
            "h": rng.choice(["a", "b"], n),
            "t": rng.permutation(n).astype(float),
            "v": rng.normal(size=n),
        }
    )
    df.loc[rng.choice(n, 20), "g"] = np.nan  # no group: empty values
    df.loc[rng.choice(n, 20), "t"] = np.nan  # no order: empty values, outside every window
    df.loc[rng.choice(n, 40), "v"] = np.nan
    for side, window in (("before", 4), ("around", 5), ("around", 1_001), ("after", 4)):
        out, _ = run_op(
            "rolling",
            df.set_axis(rng.permutation(n)),  # a shuffled index must not matter
            {
                "order": "t",
                "by": ["g", "h"],
                "columns": ["v"],
                "window": window,
                "side": side,
                "stats": "mean,std,min,max",
            },
        )
        expected = pd.DataFrame(np.nan, index=range(n), columns=["mean", "std", "min", "max"])
        usable = df.dropna(subset=["g", "t"])
        for _, part in usable.groupby(["g", "h"]):
            part = part.sort_values("t")
            values = part["v"]
            if side == "before":
                rolled = values.shift(1).rolling(window, min_periods=1)
            elif side == "after":  # the same on the rows read backwards
                rolled = values.iloc[::-1].shift(1).rolling(window, min_periods=1)
            else:
                rolled = values.rolling(window, center=True, min_periods=1)
            for stat in expected.columns:
                expected.loc[part.index, stat] = getattr(rolled, stat)()
        for stat in expected.columns:
            np.testing.assert_allclose(
                out[f"v_{side}{window}_{stat}"].to_numpy(),
                expected[stat].to_numpy(),
                equal_nan=True,
            )


def test_rolling_works_on_nullable_columns_and_an_empty_frame():
    df = pd.DataFrame(
        {
            "t": pd.array([3, 1, None, 2], dtype="Int64"),
            "v": pd.array([3, 1, 9, None], dtype="Int64"),
        }
    )
    out, _ = run_op("rolling", df, {"order": "t", "columns": ["v"], "window": 2})
    assert list(out["v_before2_mean"].fillna(-1)) == [1.0, -1, -1, 1.0]
    empty, _ = run_op("rolling", df.iloc[:0], {"order": "t", "columns": ["v"], "window": 3})
    assert list(empty.columns) == ["t", "v", "v_before3_mean"] and len(empty) == 0


def test_rolling_by_span_counts_the_range_of_the_order_not_the_rows():
    # the readings come every 0.1 but two are missing: a span of 0.3 holds fewer rows there
    t = np.round(np.arange(10) * 0.1, 1)
    df = pd.DataFrame({"t": t, "v": np.arange(10.0)}).drop(index=[3, 4]).reset_index(drop=True)
    out, _ = run_op("rolling", df, {"order": "t", "columns": ["v"], "span": 0.3})
    assert list(out.columns) == ["t", "v", "v_before_span0.3_mean"]
    # the readings from 0.3 before up to, not including, the row's own; the edge is in even though
    # 0.5 - 0.3 is not 0.2 exactly
    expected = [-1, 0.0, 0.5, 2.0, 5.0, 5.5, 6.0, 7.0]
    assert list(out["v_before_span0.3_mean"].fillna(-1)) == expected
    around, _ = run_op(
        "rolling", df, {"order": "t", "columns": ["v"], "span": 0.2, "side": "around"}
    )
    # within 0.1 either side, itself included: t=0.5 sees 0.5 and 0.6, not 0.2
    assert around["v_around_span0.2_mean"].iloc[3] == 5.5


def test_rolling_by_span_matches_the_rows_when_the_readings_are_evenly_spaced():
    rng = np.random.default_rng(1)
    n = 300
    df = pd.DataFrame(
        {"t": np.arange(n) * 0.0001, "g": np.arange(n) // 100, "v": rng.normal(size=n)}
    )
    for side, rows, span in (("before", 5, 0.0005), ("around", 11, 0.0011)):
        by_rows, _ = run_op(
            "rolling",
            df,
            {"order": "t", "by": ["g"], "columns": ["v"], "window": rows, "side": side},
        )
        by_span, _ = run_op(
            "rolling", df, {"order": "t", "by": ["g"], "columns": ["v"], "span": span, "side": side}
        )
        np.testing.assert_allclose(
            by_span.iloc[:, -1].to_numpy(), by_rows.iloc[:, -1].to_numpy(), equal_nan=True
        )


def test_rolling_by_span_matches_a_brute_force_range_on_messy_data():
    rng = np.random.default_rng(5)
    n = 500
    df = pd.DataFrame(
        {
            "g": rng.integers(0, 4, n).astype(float),
            "h": rng.choice(["a", "b"], n),
            "t": rng.integers(0, 60, n).astype(float),  # ties and gaps
            "v": rng.normal(size=n),
        }
    )
    df.loc[rng.choice(n, 15), "g"] = np.nan
    df.loc[rng.choice(n, 15), "t"] = np.nan
    for side, span in (("before", 7.0), ("around", 8.0), ("after", 7.0)):
        out, _ = run_op(
            "rolling",
            df,
            {
                "order": "t",
                "by": ["g", "h"],
                "columns": ["v"],
                "span": span,
                "side": side,
                "stats": "mean,max",
            },
        )
        for stat in ("mean", "max"):
            expected = np.full(n, np.nan)
            for i, row in df.iterrows():
                if np.isnan(row["g"]) or np.isnan(row["t"]):
                    continue
                part = df[(df["g"] == row["g"]) & (df["h"] == row["h"]) & df["t"].notna()]
                if side == "before":
                    part = part[(part["t"] >= row["t"] - span) & (part["t"] < row["t"])]
                elif side == "after":
                    part = part[(part["t"] > row["t"]) & (part["t"] <= row["t"] + span)]
                else:
                    part = part[(part["t"] - row["t"]).abs() <= span / 2]
                if len(part):
                    expected[i] = getattr(part["v"], stat)()
            np.testing.assert_allclose(
                out[f"v_{side}_span{span:g}_{stat}"].to_numpy(), expected, equal_nan=True
            )


def test_span_and_step_allow_for_the_coarse_floats_of_large_times():
    # epoch seconds with a reading every millisecond: neighbours are 0.00099993 or 0.00100017 apart
    t = 1.7e9 + np.arange(6) * 0.001
    df = pd.DataFrame({"t": t, "v": np.arange(6.0)})
    out, _ = run_op("rolling", df, {"order": "t", "columns": ["v"], "span": 0.001})
    assert list(out["v_before_span0.001_mean"].fillna(-1)) == [-1, 0, 1, 2, 3, 4]
    out, _ = run_op("lag", df, {"time": "t", "columns": ["v"], "step": 0.001})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 0, 1, 2, 3, 4]
    # nanoseconds as whole numbers are compared exactly, not as floats
    ns = pd.DataFrame(
        {"t": 1_700_000_000_000_000_123 + np.arange(4) * 10_000_000, "v": [1.0, 2, 3, 4]}
    )
    out, _ = run_op("lag", ns, {"time": "t", "columns": ["v"], "step": 10_000_000})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 1.0, 2.0, 3.0]


def test_lag_step_does_not_merge_different_times_and_refuses_a_step_too_small():
    big = pd.DataFrame({"t": [0, 1, 10_000_000], "v": [1.0, 2.0, 3.0]})
    with pytest.raises(ModuleError, match="whole number of steps"):
        run_op("lag", big, {"time": "t", "columns": ["v"], "step": 1e7})
    with pytest.raises(ModuleError, match="too many steps"):
        run_op("lag", big.iloc[:2], {"time": "t", "columns": ["v"], "step": 1e-20})
    span = pd.DataFrame({"t": [0.0, 1.0], "v": [1.0, 2.0]})
    out, _ = run_op("rolling", span, {"order": "t", "columns": ["v"], "span": 0.00005})
    assert "v_before_span0.00005_mean" in out.columns


def test_rolling_window_bounds_never_go_back_between_groups_and_orders():
    # pandas' windowed statistics are wrong if the first or last row of a window moves back
    from fione.modules import frame_ops

    rng = np.random.default_rng(9)
    for _ in range(300):
        n = int(rng.integers(0, 40))
        groups = np.sort(rng.integers(0, 5, n))
        order = rng.integers(0, 12, n).astype(float)
        order[rng.random(n) < 0.15] = np.nan  # a missing order sorts last in its group
        order = (
            pd.Series(order)
            .groupby(groups)
            .transform(lambda part: part.sort_values(na_position="last").to_numpy())
            .to_numpy()
        )
        for window, span, side in (
            (3, 0, "before"),
            (3, 0, "around"),
            (3, 0, "after"),
            (0, 4.0, "before"),
            (0, 5.0, "around"),
            (0, 4.0, "after"),
        ):
            start, end = frame_ops._window_rows(groups, order, order, window, span, side)
            assert (np.diff(start) >= 0).all() and (np.diff(end) >= 0).all()
            assert (start <= end).all() and (start >= 0).all() and (end <= n).all()


def test_lag_reads_times_a_step_apart_and_refuses_the_others():
    # readings every 0.0001 (float noise included) and Monday dates a week apart
    t = np.arange(6) * 0.0001 + 0.00005
    df = pd.DataFrame({"t": t, "v": np.arange(6.0)}).drop(index=[3])
    out, _ = run_op("lag", df, {"time": "t", "columns": ["v"], "lags": "1,2", "step": 0.0001})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 0.0, 1.0, -1, 4.0]
    assert list(out["v_lag2"].fillna(-1)) == [-1, -1, 0.0, 2.0, -1]
    weeks = pd.DataFrame({"d": ["2015-07-06", "2015-07-13", "2015-07-27"], "v": [1.0, 2.0, 4.0]})
    out, _ = run_op("lag", weeks, {"time": "d", "columns": ["v"], "step": 7})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 1.0, -1]
    with pytest.raises(ModuleError, match="whole number of steps"):
        run_op("lag", df, {"time": "t", "columns": ["v"], "step": 0.0003})
    with pytest.raises(ModuleError, match="whole numbers or dates .*step"):
        run_op("lag", df, {"time": "t", "columns": ["v"]})
    with pytest.raises(ModuleError, match="above 0"):
        run_op("lag", df, {"time": "t", "columns": ["v"], "step": 0})


def test_rolling_refuses_unclear_input():
    df = pd.DataFrame(
        {
            "t": [1, 2, 3],
            "g": [1, 1, 1],
            "v": [1.0, 2.0, 3.0],
            "s": ["a", "b", "c"],
            "b": [True, False, True],
        }
    )
    base = {"order": "t", "columns": ["v"], "window": 3}
    for params, message in (
        ({**base, "window": 4, "side": "around"}, "odd number"),
        ({**base, "window": 0}, "a window .* or a span"),
        ({**base, "span": 2.0}, "a window .* or a span"),
        ({**base, "stats": "median"}, "stats must name"),
        ({**base, "columns": ["s"]}, "not numeric"),
        ({**base, "order": "s"}, "year-month-day"),
        ({**base, "order": "b"}, "numbers or dates"),
        ({**base, "by": ["t"]}, "by cannot include the order"),
        ({"order": "t", "columns": []}, "name the columns"),
    ):
        with pytest.raises(ModuleError, match=message):
            run_op("rolling", df, params)


def test_lag_sum_keeps_an_all_missing_group_empty():
    df = pd.DataFrame({"g": ["a", "a", "a"], "t": [1, 2, 3], "v": [5.0, np.nan, np.nan]})
    out, _ = run_op("lag", df, {"time": "t", "by": ["g"], "columns": ["v"], "how": "sum"})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 5.0, -1]  # not 0.0 for an empty time 2


def test_lag_does_not_wrap_a_narrow_integer_time_and_keeps_its_type():
    df = pd.DataFrame({"t": np.array([250, 4], dtype="uint8"), "v": [1.0, 2.0]})
    out, _ = run_op("lag", df, {"time": "t", "columns": ["v"], "lags": "10"})
    assert list(out["v_lag10"].fillna(-1)) == [-1, -1]  # 250 + 10 is 260, not 4
    assert out["t"].dtype == np.dtype("uint8") and list(out["t"]) == [250, 4]
    nullable = pd.DataFrame({"t": pd.array([1, 2, None], dtype="Int8"), "v": [1.0, 2.0, 3.0]})
    out, _ = run_op("lag", nullable, {"time": "t", "columns": ["v"]})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 1.0, -1]


def test_lag_refuses_a_time_of_booleans_and_a_column_named_twice():
    df = pd.DataFrame({"g": [1, 2], "t": [True, False], "v": [1.0, 2.0]})
    with pytest.raises(ModuleError, match="whole numbers"):
        run_op("lag", df, {"time": "t", "columns": ["v"]})
    ok = df.assign(t=[1, 2])
    with pytest.raises(ModuleError, match="twice"):
        run_op("lag", ok, {"time": "t", "by": ["g", "g"], "columns": ["v"]})
    with pytest.raises(ModuleError, match="twice"):
        run_op("lag", ok, {"time": "t", "columns": ["v", "v"]})


def test_lag_counts_the_steps_of_a_date_column_in_days():
    # shop 1 has no row on the 3rd: the lag of the 4th is empty; the dates come back as given
    dates = ["2015-07-01", "2015-07-02", "2015-07-04", "2015-07-01", "2015-07-02"]
    df = pd.DataFrame(
        {"shop": [1, 1, 1, 2, 2], "day": pd.to_datetime(dates), "sales": [10.0, 20.0, 40, 1, 2]}
    )
    params = {"time": "day", "by": ["shop"], "columns": ["sales"], "lags": "1,3"}
    out, _ = run_op("lag", df, params)
    assert list(out["sales_lag1"].fillna(-1)) == [-1, 10.0, -1, -1, 1.0]
    assert list(out["sales_lag3"].fillna(-1)) == [-1, -1, 10.0, -1, -1]
    assert out["day"].dtype == df["day"].dtype and list(out["day"]) == list(df["day"])
    as_text, _ = run_op("lag", df.assign(day=dates), params)  # text a date can be read from
    assert list(as_text["sales_lag1"].fillna(-1)) == list(out["sales_lag1"].fillna(-1))
    assert list(as_text["day"]) == dates
    # a timezone changes nothing
    zoned = df.assign(day=df["day"].dt.tz_localize("Asia/Tokyo"))
    assert list(run_op("lag", zoned, params)[0]["sales_lag1"].fillna(-1)) == [-1, 10.0, -1, -1, 1.0]
    # a month boundary is one day too; a missing date has no lag
    jump = pd.DataFrame(
        {"day": pd.to_datetime(["2015-06-30", "2015-07-01", None]), "v": [1.0, 2.0, 3.0]}
    )
    out, _ = run_op("lag", jump, {"time": "day", "columns": ["v"]})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 1.0, -1]


def test_lag_refuses_a_date_with_a_time_of_day_and_text_that_is_not_a_date():
    stamps = [pd.Timestamp("2015-07-01 06:00"), pd.Timestamp("2015-07-02")]
    df = pd.DataFrame({"t": stamps, "v": [1.0, 2.0]})
    with pytest.raises(ModuleError, match="time of day"):
        run_op("lag", df, {"time": "t", "columns": ["v"]})
    with pytest.raises(ModuleError, match="year-month-day"):
        run_op("lag", df.assign(t=["x", "y"]), {"time": "t", "columns": ["v"]})


def test_lag_does_not_read_numbers_held_as_text_or_objects_as_dates():
    for values, message in (
        (["1", "2", "3"], "year-month-day"),
        (["201501", "201502", "201503"], "year-month-day"),
        (pd.Series([1, 2, 3], dtype=object), "whole numbers or dates"),
    ):
        df = pd.DataFrame({"t": values, "v": [1.0, 2.0, 3.0]})
        with pytest.raises(ModuleError, match=message):
            run_op("lag", df, {"time": "t", "columns": ["v"]})
    compact = pd.DataFrame({"t": ["20150701", "20150702"], "v": [1.0, 2.0]})  # a date, read as one
    out, _ = run_op("lag", compact, {"time": "t", "columns": ["v"]})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 1.0]


def test_lag_refuses_text_that_a_date_reader_would_take_for_other_days():
    # a month, a year, a quarter or a day-first date would give lags that are empty without a word
    for values in (
        ["2015-01", "2015-02", "2015-03"],
        ["2015", "2016", "2017"],
        ["2015Q1", "2015Q2", "2015Q3"],
        ["01/07/2015", "02/07/2015", "13/07/2015"],
    ):
        df = pd.DataFrame({"t": values, "v": [1.0, 2.0, 3.0]})
        with pytest.raises(ModuleError, match="year-month-day"):
            run_op("lag", df, {"time": "t", "columns": ["v"]})
    mixed = pd.DataFrame(
        {"t": ["2015-07-01T00:00+09:00", "2015-07-02T00:00+00:00"], "v": [1.0, 2.0]}
    )
    with pytest.raises(ModuleError, match="cannot be read in one format"):
        run_op("lag", mixed, {"time": "t", "columns": ["v"]})


def test_lag_reads_dates_far_from_1970():
    # 9999-12-31 is a usual "no end date"; it must not fail the job (nanoseconds stop at 2262)
    far = pd.DataFrame(
        {
            "t": [
                datetime.date(2015, 7, 1),
                datetime.date(2015, 7, 2),
                datetime.date(9999, 12, 31),
            ],
            "v": [1.0, 2.0, 3.0],
        }
    )
    out, _ = run_op("lag", far, {"time": "t", "columns": ["v"]})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 1.0, -1]
    old = pd.DataFrame({"t": ["1500-01-01", "1500-01-02"], "v": [1.0, 2.0]})
    out, _ = run_op("lag", old, {"time": "t", "columns": ["v"]})
    assert list(out["v_lag1"].fillna(-1)) == [-1, 1.0]


def _lag_notes(df):
    module = get_builtin("lag")
    params = {"time": "month", "by": ["shop"], "columns": ["sales"], "lags": "1"}
    return module.run(
        df.copy(), validate_args(module.params, params), ModuleContext(None, None)
    ).notes


def test_lag_says_so_when_it_is_empty_nearly_everywhere():
    months = pd.date_range("2023-01-01", periods=12, freq="MS").strftime("%Y-%m-%d")
    df = pd.DataFrame({"shop": [1] * 12, "month": months, "sales": np.arange(12.0)})
    notes = _lag_notes(df)
    assert [n["kind"] for n in notes] == ["lag_empty"]
    assert notes[0]["column"] == "sales_lag1" and "month number" in notes[0]["message"]
    assert _lag_notes(df.assign(month=range(12))) == ()


def test_lag_note_names_the_new_column_when_the_name_is_taken():
    months = pd.date_range("2023-01-01", periods=12, freq="MS").strftime("%Y-%m-%d")
    df = pd.DataFrame(
        {"shop": [1] * 12, "month": months, "sales": np.arange(12.0), "sales_lag1": 0.0}
    )
    notes = _lag_notes(df)
    assert [n["column"] for n in notes] == ["sales_lag1_2"]
