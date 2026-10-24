"""The built-in frame operations, ported from the v1 ``frame_*.py`` scripts to pandas.

Each takes one frame (``cbind``, ``concat`` and ``rbind`` a second one through
``other_dataset_id``) and returns one frame. Column lists are JSON arrays of names.
"""

import operator
import re

import numpy as np
import pandas as pd

from fione.modules.registry import (
    Module,
    ModuleContext,
    ModuleError,
    ModuleOutput,
    numeric_matrix,
    pick_columns,
    register,
    require_column,
)
from fione.projects.ingest import unique_names

_NAMES = {"type": "array", "items": {"type": "string"}, "maxItems": 1000, "default": []}
_NAME = {"type": "string", "maxLength": 1000}
_OTHER = {"type": "integer", "minimum": 1}
_CONDITIONS = {"type": "string", "maxLength": 1000, "default": ""}
_COMPARE = {
    "==": operator.eq,
    "!=": operator.ne,
    "<=": operator.le,
    ">=": operator.ge,
    "<": operator.lt,
    ">": operator.gt,
}
_CONDITION = re.compile(r"(?P<column>.+?) (?P<op>==|!=|<=|>=|<|>) (?P<value>.*)")
# The v1 stop-word list for tokenize (frame_tokenize.py), unchanged.
STOP_WORDS = frozenset(
    "ax i you edu s t m subject can lines re what there all we one the a an of or in for by on"
    " but is not with as was if they are this and it have from at my be that to com org like"
    " likes so".split()
)


def _schema(properties: dict, required: tuple[str, ...] = ()) -> dict:
    return {"type": "object", "properties": properties, "required": list(required)}


def _op(module_id: str, name: str, properties: dict, required: tuple[str, ...], run) -> None:
    def wrapped(df, params, ctx):
        return ModuleOutput(run(df, params, ctx))

    register(Module(module_id, name, "frame", _schema(properties, required), wrapped))


def _other(ctx: ModuleContext) -> pd.DataFrame:
    if ctx.other is None:
        raise ModuleError("this module needs a second dataset (other_dataset_id)")
    return ctx.other


def _side_by_side(df: pd.DataFrame, other: pd.DataFrame) -> pd.DataFrame:
    if len(df) != len(other):
        raise ModuleError(
            f"the datasets must have the same number of rows ({len(df)} and {len(other)})"
        )
    both = pd.concat([df.reset_index(drop=True), other.reset_index(drop=True)], axis=1)
    return both.set_axis(unique_names([str(c) for c in both.columns]), axis=1)


def _stacked(df: pd.DataFrame, other: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([df, other], ignore_index=True)


def cbind(df, params, ctx):
    return _side_by_side(df, _other(ctx))


def rbind(df, params, ctx):
    other = _other(ctx)
    if set(df.columns) != set(other.columns):
        raise ModuleError("the datasets must have the same columns")
    return _stacked(df, other[list(df.columns)])


def concat(df, params, ctx):
    other = _other(ctx)
    return _side_by_side(df, other) if params["axis"] == 1 else _stacked(df, other)


def cslice(df, params, ctx):
    return df[pick_columns(df, params["columns"])]


def floor(df, params, ctx):
    columns, matrix = numeric_matrix(df, params["columns"])
    return pd.DataFrame(np.floor(matrix), columns=columns)


def fillna(df, params, ctx):
    fill = df.ffill if params["method"] == "forward" else df.bfill
    return fill(axis=params["axis"], limit=params["maxlen"])


def cor(df, params, ctx):
    columns, matrix = numeric_matrix(df, params["columns"])
    data = pd.DataFrame(matrix, columns=columns)
    # H2O: "use" wins; otherwise na_rm decides between 'everything' and 'complete.obs'.
    use = params["use"] or ("everything" if params["na_rm"] else "complete.obs")
    missing = data.isna().any()
    if use == "all.obs" and missing.any():
        raise ModuleError("use 'all.obs' needs data without missing values")
    if use == "complete.obs":
        data = data.dropna()
    result = data.corr(method=params["method"])
    if use == "everything":  # a gap in a column makes every correlation with it unknown
        result.loc[missing.to_numpy(), :] = np.nan
        result.loc[:, missing.to_numpy()] = np.nan
    return pd.DataFrame(result.to_numpy(), columns=columns)


def pivot(df, params, ctx):
    names = [require_column(df, params[k]) for k in ("index", "column", "value")]
    if len(set(names)) != 3:
        raise ModuleError("index, column and value must be three different columns")
    index, column, value = names
    table = df.groupby([index, column])[value].first().unstack()
    table.columns = [str(c) for c in table.columns]
    return table.reset_index()


def _typed(series: pd.Series, column: str, text: str):
    """``text`` converted to what a comparison with (or assignment to) the column needs."""
    dtype = series.dtype
    try:
        if pd.api.types.is_bool_dtype(dtype):
            if text.lower() not in ("true", "false"):
                raise ValueError(text)
            return text.lower() == "true"
        if pd.api.types.is_integer_dtype(dtype):
            return int(text)
        if pd.api.types.is_float_dtype(dtype):
            return float(text)
    except ValueError:
        raise ModuleError(f"'{text}' does not fit column '{column}'") from None
    if pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
        return text
    raise ModuleError(f"column '{column}' of type {dtype} is not supported here")


def _comparison(df: pd.DataFrame, text: str) -> np.ndarray:
    found = _CONDITION.fullmatch(text.strip())
    if found is None:
        raise ModuleError(f"cannot read the condition '{text.strip()}'; use: column == value")
    column = require_column(df, found["column"].strip())
    value = _typed(df[column], column, found["value"].strip())
    return np.asarray(_COMPARE[found["op"]](df[column], value).fillna(False), dtype=bool)


def row_mask(df: pd.DataFrame, conditions: str) -> np.ndarray:
    """Rows matching ``col op value`` terms (ops ``== != < <= > >=``, each with a space on both
    sides) joined by ``&`` and ``|``; ``&`` binds tighter. Empty conditions match every row."""
    if not conditions.strip():
        return np.ones(len(df), dtype=bool)
    mask = np.zeros(len(df), dtype=bool)
    for either in conditions.split("|"):
        both = np.ones(len(df), dtype=bool)
        for term in either.split("&"):
            both &= _comparison(df, term)
        mask |= both
    return mask


def replace(df, params, ctx):
    column = require_column(df, params["column"])
    value = _typed(df[column], column, params["value"])
    df = df.copy()
    df.loc[row_mask(df, params["row_conditions"]), column] = value
    return df


def rslice(df, params, ctx):
    return df[row_mask(df, params["row_conditions"])]


def sort(df, params, ctx):
    column = require_column(df, params["column"])
    return df.sort_values(column, ascending=params["ascending"], kind="stable", na_position="last")


def split(df, params, ctx):
    ratios = {
        "train": params["train_ratio"],
        "valid": params["valid_ratio"],
        "test": params["test_ratio"],
    }
    if ratios["train"] <= 0:
        raise ModuleError("train_ratio must be greater than 0")
    total = sum(ratios.values())
    ends = np.cumsum([ratios["train"], ratios["valid"], ratios["test"]]) / total
    cuts = [0] + [int(len(df) * fraction + 1e-9) for fraction in ends[:2]] + [len(df)]
    first = ("train", "valid", "test").index(params["part"])
    order = np.random.default_rng(params["seed"]).permutation(len(df))
    return df.iloc[np.sort(order[cuts[first] : cuts[first + 1]])]


def tokenize(df, params, ctx):
    column = require_column(df, params["target_column"])
    if not (pd.api.types.is_string_dtype(df[column]) or pd.api.types.is_object_dtype(df[column])):
        raise ModuleError(f"'{column}' is not a text column")
    try:
        pattern = re.compile(params["regex"])
    except re.error as e:
        raise ModuleError(f"the regular expression is not valid: {e}") from None
    tokens: list[str | None] = []
    for text in df[column]:
        if isinstance(text, str):
            for token in pattern.split(text):
                token = token.lower() if params["lower_case"] and token else token
                if (
                    token
                    and len(token) >= params["min_word_len"]
                    and not (params["use_stop_words"] and token in STOP_WORDS)
                ):
                    tokens.append(token)
        tokens.append(None)  # a gap ends each document, as in H2O
    return pd.DataFrame({column: pd.Series(tokens, dtype="str")})


_op("cbind", "Combine columns", {"other_dataset_id": _OTHER}, ("other_dataset_id",), cbind)
_op(
    "concat",
    "Concatenate datasets",
    {"other_dataset_id": _OTHER, "axis": {"type": "integer", "enum": [0, 1], "default": 1}},
    ("other_dataset_id",),
    concat,
)
_op(
    "cor",
    "Compute correlation",
    {
        "columns": _NAMES,
        "method": {"type": "string", "enum": ["pearson", "spearman"], "default": "pearson"},
        "use": {
            "type": "string",
            "enum": ["", "everything", "all.obs", "complete.obs"],
            "default": "",
        },
        "na_rm": {"type": "boolean", "default": False},
    },
    (),
    cor,
)
_op("cslice", "Slice columns", {"columns": _NAMES}, (), cslice)
_op(
    "fillna",
    "Fill missing values",
    {
        "method": {"type": "string", "enum": ["forward", "backward"], "default": "forward"},
        "axis": {"type": "integer", "enum": [0, 1], "default": 0},
        "maxlen": {"type": "integer", "minimum": 1, "default": 1},
    },
    (),
    fillna,
)
_op("floor", "Apply floor", {"columns": _NAMES}, (), floor)
_op(
    "pivot",
    "Pivot table",
    {"index": _NAME, "column": _NAME, "value": _NAME},
    ("index", "column", "value"),
    pivot,
)
_op("rbind", "Combine rows", {"other_dataset_id": _OTHER}, ("other_dataset_id",), rbind)
_op(
    "replace",
    "Replace values",
    {
        "column": _NAME,
        "row_conditions": _CONDITIONS,
        "value": {"type": "string", "maxLength": 1000},
    },
    ("column", "value"),
    replace,
)
_op("rslice", "Slice rows", {"row_conditions": _CONDITIONS}, (), rslice)
_op(
    "sort",
    "Sort",
    {"column": _NAME, "ascending": {"type": "boolean", "default": True}},
    ("column",),
    sort,
)
_op(
    "split",
    "Split into train, valid and test",
    {
        "part": {"type": "string", "enum": ["train", "valid", "test"], "default": "train"},
        "train_ratio": {"type": "number", "minimum": 0, "default": 70},
        "valid_ratio": {"type": "number", "minimum": 0, "default": 15},
        "test_ratio": {"type": "number", "minimum": 0, "default": 15},
        "seed": {"type": "integer", "minimum": 0, "maximum": 2**31 - 1, "default": 0},
    },
    (),
    split,
)
_op(
    "tokenize",
    "Tokenize text",
    {
        "target_column": _NAME,
        "regex": {"type": "string", "maxLength": 200, "default": r"\W+"},
        "lower_case": {"type": "boolean", "default": False},
        "min_word_len": {"type": "integer", "minimum": 0, "default": 0},
        "use_stop_words": {"type": "boolean", "default": False},
    },
    ("target_column",),
    tokenize,
)
