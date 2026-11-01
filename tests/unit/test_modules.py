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
from fione.modules import registry, service, unsupervised
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
        "cbind concat cor cslice fillna floor pivot rbind replace rslice sort split tokenize"
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
    assert registry.MAX_OUTPUT_CELLS == 50_000_000
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
    assert time.monotonic() - started < 1.0 and len(out) > 1


# --- the output-size estimate runs before the result is built --------------------------------


def test_pivot_is_refused_before_it_is_built():
    import tracemalloc

    n = 8_000  # 8,000 x 8,001 cells would be over the 50 million cap
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
    assert time.monotonic() - started < 1.0 and peak < 50_000_000


def test_cor_of_too_many_columns_is_refused():
    wide = pd.DataFrame(np.zeros((3, 10_000)), columns=[f"c{i}" for i in range(10_000)])
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
