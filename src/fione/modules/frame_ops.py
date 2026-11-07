"""The built-in frame operations, on pandas.

Each takes one frame (``cbind``, ``concat``, ``join`` and ``rbind`` a second one through
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
    check_cells,
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
# The stop words of tokenize.
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
    check_cells(len(df), len(df.columns) + len(other.columns))
    both = pd.concat([df.reset_index(drop=True), other.reset_index(drop=True)], axis=1)
    return both.set_axis(unique_names([str(c) for c in both.columns]), axis=1)


def _stacked(df: pd.DataFrame, other: pd.DataFrame) -> pd.DataFrame:
    check_cells(len(df) + len(other), len(df.columns.union(other.columns)))
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


_SUMMARIES = ("mean", "min", "max", "sum")
_JOIN_KEY = "\0join_key"  # a name no column has


def _summary(other: pd.DataFrame, key: str) -> pd.DataFrame:
    """One row per value of ``key``: the number of rows, and per column the mean, minimum,
    maximum and sum of a number, or the number of different values of anything else."""
    others = [c for c in other.columns if c != key]
    numeric = [c for c in others if pd.api.types.is_numeric_dtype(other[c])]
    rest = [c for c in others if c not in numeric]
    check_cells(other[key].nunique(), 1 + len(numeric) * len(_SUMMARIES) + len(rest))
    groups = other.groupby(key)
    parts = [groups.size().rename("rows").to_frame()]
    if numeric:
        stats = groups[numeric].agg(list(_SUMMARIES))
        stats.columns = [f"{column}_{how}" for column, how in stats.columns]
        parts.append(stats)
    if rest:
        parts.append(groups[rest].nunique().add_suffix("_nunique"))
    summary = pd.concat(parts, axis=1)
    # a summary column never takes the key's name (a key called "rows" is possible)
    summary.columns = unique_names([str(key)] + [str(c) for c in summary.columns])[1:]
    summary.insert(0, key, summary.index)
    return summary.reset_index(drop=True)


def _as_text(s: pd.Series) -> pd.Series:
    """The values as text, a whole number the same whether it is stored as float or integer."""
    if pd.api.types.is_float_dtype(s.dtype) and (s.dropna() == s.dropna().round()).all():
        s = s.astype("Int64")
    return s.astype(str).where(s.notna())


def join(df, params, ctx):
    """Add the columns of the other dataset to the rows with the same ``key`` (a left join: every
    row stays, with missing values where the other dataset has no such key). The rows of the
    other dataset must each have a different key, unless ``summarize`` replaces them by one row
    per key (the number of rows, and the mean, minimum, maximum and sum of each number). With
    ``columns``, only those columns of the other dataset are added or summarized."""
    other = _other(ctx)
    key = require_column(df, params["key"])
    other_key = require_column(other, params["other_key"] or key)
    if params["columns"]:  # only these columns are added (and summarized)
        unknown = [c for c in params["columns"] if c not in other.columns]
        if unknown:
            raise ModuleError(f"unknown columns of the other dataset: {unknown}")
        other = other[[other_key, *[c for c in params["columns"] if c != other_key]]]
    if params["summarize"]:
        other = _summary(other, other_key)
    elif other[other_key].dropna().duplicated().any():
        raise ModuleError(
            f"the values of '{other_key}' repeat in the other dataset; "
            "summarize it by that column, or the rows would multiply"
        )
    added = [c for c in other.columns if c != other_key]
    names = unique_names([str(c) for c in df.columns] + [str(c) for c in added])[len(df.columns) :]
    right = other[[other_key, *added]].set_axis([_JOIN_KEY, *names], axis=1)
    right = right[right[_JOIN_KEY].notna()]  # a missing key matches nothing
    left = df.assign(**{_JOIN_KEY: df[key]})
    if pd.api.types.is_numeric_dtype(left[_JOIN_KEY]) != pd.api.types.is_numeric_dtype(
        right[_JOIN_KEY]
    ):  # 7 and "7" are the same key
        left[_JOIN_KEY] = _as_text(left[_JOIN_KEY])
        right = right.assign(**{_JOIN_KEY: _as_text(right[_JOIN_KEY])})
    check_cells(len(df), len(df.columns) + len(added))
    try:
        merged = left.merge(right, how="left", on=_JOIN_KEY)
    except ValueError as e:
        raise ModuleError(f"the keys cannot be compared: {e}") from None
    return merged.drop(columns=_JOIN_KEY)


def _lags(text: str) -> list[int]:
    """The whole numbers of a comma-separated list, at least 1 each."""
    try:
        lags = [int(part) for part in text.split(",") if part.strip()]
    except ValueError:
        raise ModuleError(f"lags must be whole numbers separated by commas, got '{text}'") from None
    if not lags or min(lags) < 1:
        raise ModuleError("lags must name one or more whole numbers of at least 1")
    return list(dict.fromkeys(lags))


def lag(df, params, ctx):
    """Add, for each row, the value of the ``columns`` at an earlier ``time`` of the same ``by``
    group: ``column_lag1`` is the value one step of ``time`` before, ``column_lag3`` three steps
    before. ``time`` holds whole numbers (a month number, a day number); the step is counted in
    them, not in rows, so a time with no row gives an empty value instead of the one before
    it. Rows of a group with the same time are first reduced to their ``how`` (mean or sum), so
    ``by`` can be coarser than a row: lagging the mean of an item over all shops. No row reads
    its own time or a later one."""
    time = require_column(df, params["time"])
    by = pick_columns(df, params["by"]) if params["by"] else []
    if time in by:
        raise ModuleError("by cannot include the time column")
    if not params["columns"]:
        raise ModuleError("name the columns to lag")
    columns = [c for c in pick_columns(df, params["columns"]) if c != time and c not in by]
    if not columns:
        raise ModuleError("the columns to lag cannot be only the time or the by columns")
    for column in columns:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ModuleError(f"column '{column}' is not numeric")
    if (
        not pd.api.types.is_numeric_dtype(df[time])
        or not (df[time].dropna() == df[time].dropna().round()).all()
    ):
        raise ModuleError(f"time column '{time}' must hold whole numbers")
    lags = _lags(params["lags"])
    check_cells(len(df), len(df.columns) + len(columns) * len(lags))
    keys = [*by, time]
    reduced = getattr(df.groupby(keys)[columns], params["how"])().reset_index()
    out = df
    for k in lags:
        earlier = reduced.copy()
        earlier[time] = earlier[time] + k  # the value at time t is read by the rows at t + k
        fresh = unique_names([str(c) for c in out.columns] + [f"{c}_lag{k}" for c in columns])[
            len(out.columns) :
        ]
        earlier = earlier.rename(columns=dict(zip(columns, fresh, strict=True)))
        out = out.merge(earlier, how="left", on=keys)
    return out


def cslice(df, params, ctx):
    return df[pick_columns(df, params["columns"])]


def floor(df, params, ctx):
    columns, matrix = numeric_matrix(df, params["columns"])
    return pd.DataFrame(np.floor(matrix), columns=columns)


def fillna(df, params, ctx):
    fill = df.ffill if params["method"] == "forward" else df.bfill
    return fill(axis=params["axis"], limit=params["maxlen"])


def cor(df, params, ctx):
    check_cells(len(pick_columns(df, params["columns"])), len(pick_columns(df, params["columns"])))
    columns, matrix = numeric_matrix(df, params["columns"])
    data = pd.DataFrame(matrix, columns=columns)
    # "use" wins, otherwise na_rm picks 'complete.obs' and its absence 'everything'.
    use = params["use"] or ("complete.obs" if params["na_rm"] else "everything")
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
    check_cells(df[index].nunique(), df[column].nunique() + 1)
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


_WORD = re.compile(r"\w+")  # fixed and linear: no user pattern ever reaches the regex engine


def _split(text: str, mode: str, delimiter: str) -> list[str]:
    if mode == "whitespace":
        return text.split()
    if mode == "word":
        return _WORD.findall(text)
    return text.split(delimiter)


def tokenize(df, params, ctx):
    """One token per row with a gap after each document. ``word`` takes runs of letters, digits
    and ``_`` (a run of Japanese letters is one token: no morphological analysis)."""
    column = require_column(df, params["target_column"])
    if not (pd.api.types.is_string_dtype(df[column]) or pd.api.types.is_object_dtype(df[column])):
        raise ModuleError(f"'{column}' is not a text column")
    mode, delimiter = params["mode"], params["delimiter"]
    if mode == "delimiter" and not delimiter:
        raise ModuleError("the delimiter mode needs a delimiter")
    # every token is at least one character, so this bounds the rows of the result
    check_cells(int(df[column].str.len().fillna(0).sum()) + len(df), 1)
    tokens: list[str | None] = []
    for text in df[column]:
        if isinstance(text, str):
            for token in _split(text.lower() if params["lower_case"] else text, mode, delimiter):
                if (
                    token
                    and len(token) >= params["min_word_len"]
                    and not (params["use_stop_words"] and token in STOP_WORDS)
                ):
                    tokens.append(token)
        tokens.append(None)  # a gap ends each document
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
    "join",
    "Join datasets by a key column",
    {
        "other_dataset_id": _OTHER,
        "key": _NAME,
        "other_key": {**_NAME, "default": ""},
        "summarize": {"type": "boolean", "default": False},
        "columns": _NAMES,
    },
    ("other_dataset_id", "key"),
    join,
)
_op(
    "lag",
    "Add values from earlier times",
    {
        "time": _NAME,
        "by": _NAMES,
        "columns": _NAMES,
        "lags": {"type": "string", "maxLength": 200, "default": "1"},
        "how": {"type": "string", "enum": ["mean", "sum"], "default": "mean"},
    },
    ("time", "columns"),
    lag,
)
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
        "mode": {
            "type": "string",
            "enum": ["whitespace", "word", "delimiter"],
            "default": "word",
        },
        "delimiter": {"type": "string", "maxLength": 20, "default": ""},
        "lower_case": {"type": "boolean", "default": False},
        "min_word_len": {"type": "integer", "minimum": 0, "default": 0},
        "use_stop_words": {"type": "boolean", "default": False},
    },
    ("target_column",),
    tokenize,
)
