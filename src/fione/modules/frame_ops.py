"""The built-in frame operations, on pandas.

Each takes one frame (``cbind``, ``concat``, ``join`` and ``rbind`` a second one through
``other_dataset_id``) and returns one frame. Column lists are JSON arrays of names.
"""

import operator
import re
import warnings

import numpy as np
import pandas as pd
from pandas.api.indexers import BaseIndexer

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
        out = run(df, params, ctx)
        return out if isinstance(out, ModuleOutput) else ModuleOutput(out)

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
_JOIN_MATCH = "\0join_match"


def _summary(other: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """One row per value of ``keys``: the number of rows, and per column the mean, minimum,
    maximum and sum of a number, or the number of different values of anything else."""
    others = [c for c in other.columns if c not in keys]
    numeric = [c for c in others if pd.api.types.is_numeric_dtype(other[c])]
    rest = [c for c in others if c not in numeric]
    check_cells(len(other[keys].drop_duplicates()), 1 + len(numeric) * len(_SUMMARIES) + len(rest))
    groups = other.groupby(keys)
    parts = [groups.size().rename("rows").to_frame()]
    if numeric:
        stats = groups[numeric].agg(list(_SUMMARIES))
        stats.columns = [f"{column}_{how}" for column, how in stats.columns]
        parts.append(stats)
    if rest:
        parts.append(groups[rest].nunique().add_suffix("_nunique"))
    summary = pd.concat(parts, axis=1)
    # a summary column never takes a key's name (a key called "rows" is possible)
    names = unique_names([str(k) for k in keys] + [str(c) for c in summary.columns])
    summary.columns = names[len(keys) :]
    return summary.reset_index()


def _as_text(s: pd.Series) -> pd.Series:
    """The values as text, a whole number the same whether it is stored as float or integer."""
    if pd.api.types.is_float_dtype(s.dtype) and (s.dropna() == s.dropna().round()).all():
        s = s.astype("Int64")
    return s.astype(str).where(s.notna())


def _key_columns(frame: pd.DataFrame, params: dict, one: str, many: str) -> list[str]:
    """The key columns named by ``one`` (a column) or ``many`` (several that identify a row
    together), which are not both given."""
    if params[one] and params[many]:
        raise ModuleError(f"give '{one}' or '{many}', not both")
    names = params[many] or ([params[one]] if params[one] else [])
    if len(set(names)) != len(names):
        raise ModuleError(f"'{many}' names a column twice")
    return [require_column(frame, name) for name in names]


def join(df, params, ctx):
    """Add the columns of the other dataset to the rows with the same key (a left join: every
    row stays, with missing values where the other dataset has no such key). The key is one
    column (``key``) or several that identify a row together (``keys``); a row with a missing
    part matches nothing. The rows of the other dataset must each have a different key, unless
    ``summarize`` replaces them by one row per key (the number of rows, and the mean, minimum,
    maximum and sum of each number). With ``columns``, only those columns of the other dataset
    are added or summarized."""
    other = _other(ctx)
    keys = _key_columns(df, params, "key", "keys")
    if not keys:
        raise ModuleError("name the key column ('key') or the key columns ('keys')")
    if params["other_key"] or params["other_keys"]:
        other_keys = _key_columns(other, params, "other_key", "other_keys")
    else:
        other_keys = _key_columns(other, params, "key", "keys")
    if len(keys) != len(other_keys):
        raise ModuleError("the key and the other key must name the same number of columns")
    if params["columns"]:  # only these columns are added (and summarized)
        unknown = [c for c in params["columns"] if c not in other.columns]
        if unknown:
            raise ModuleError(f"unknown columns of the other dataset: {unknown}")
        other = other[[*other_keys, *[c for c in params["columns"] if c not in other_keys]]]
    if params["summarize"]:
        other = _summary(other, other_keys)
    elif other[other_keys].dropna().duplicated().any():
        raise ModuleError(
            f"the values of {', '.join(repr(k) for k in other_keys)} repeat in the other "
            "dataset; summarize it by that column, or the rows would multiply"
        )
    added = [c for c in other.columns if c not in other_keys]
    names = unique_names([str(c) for c in df.columns] + [str(c) for c in added])[len(df.columns) :]
    parts = [f"{_JOIN_KEY}{i}" for i in range(len(keys))]
    right = other[[*other_keys, *added]].set_axis([*parts, *names], axis=1)
    right = right.dropna(subset=parts)  # a missing part matches nothing
    left = df.assign(**{part: df[key] for part, key in zip(parts, keys, strict=True)})
    for part in parts:
        if pd.api.types.is_numeric_dtype(left[part]) != pd.api.types.is_numeric_dtype(
            right[part]
        ):  # 7 and "7" are the same key
            left[part] = _as_text(left[part])
            right = right.assign(**{part: _as_text(right[part])})
    check_cells(len(df), len(df.columns) + len(added))
    try:
        merged = left.merge(right, how="left", on=parts, indicator=_JOIN_MATCH)
    except ValueError as e:
        raise ModuleError(f"the keys cannot be compared: {e}") from None
    missed = int((merged.pop(_JOIN_MATCH) == "left_only").sum())
    return ModuleOutput(merged.drop(columns=parts), notes=_join_notes(missed, len(merged)))


def _join_notes(missed: int, rows: int) -> tuple[dict, ...]:
    """What to tell about the rows that found no row with their key in the other dataset."""
    if not missed:
        return ()
    note = (
        f"{missed} of {rows} rows ({missed / rows:.1%}) have no row with the same key in the "
        "other dataset; their new columns are empty."
    )
    if missed == rows:
        note += " Check that the key columns hold the same kind of values, written the same way."
    return ({"message": note, "kind": "join_unmatched", "rows_unmatched": missed, "rows": rows},)


def _lags(text: str) -> list[int]:
    """The whole numbers of a comma-separated list, at least 1 each."""
    try:
        lags = [int(part) for part in text.split(",") if part.strip()]
    except ValueError:
        raise ModuleError(f"lags must be whole numbers separated by commas, got '{text}'") from None
    if not lags or min(lags) < 1:
        raise ModuleError("lags must name one or more whole numbers of at least 1")
    return list(dict.fromkeys(lags))


# Text read as a date: a day as 2015-07-01 or 2015/07/01 (a time of day may follow), or 20150701.
# A month, a year, a quarter or a day-first date would be read as other days, so they are refused.
_DATE_TEXT = re.compile(r"\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}([ T].*)?|\d{8})\s*")


def _day_numbers(values, name):
    """The days since 1970-01-01 of a column of dates (or of text with year, month and day in
    that order), as whole numbers; a date with a time of day is refused, and a missing date
    stays missing."""
    bad = ModuleError(f"time column '{name}' must hold whole numbers or dates")
    kind = pd.api.types.infer_dtype(values, skipna=True)
    # only dates and text: numbers held as objects would be read as nanoseconds from 1970
    if kind not in ("string", "datetime", "datetime64", "date"):
        raise bad
    if kind == "string" and not values.dropna().astype(str).map(_DATE_TEXT.fullmatch).notna().all():
        raise ModuleError(
            f"time column '{name}' has text that is not a date written year-month-day, "
            "such as 2015-07-01"
        )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # "could not infer format"
            stamps = pd.to_datetime(values)
    except (ValueError, TypeError):
        raise ModuleError(
            f"time column '{name}' has dates that cannot be read in one format (use 2015-07-01)"
        ) from None
    if stamps.dt.tz is not None:
        stamps = stamps.dt.tz_localize(None)
    if not (stamps.isna() | (stamps == stamps.dt.normalize())).all():
        raise ModuleError(f"time column '{name}' has a time of day; it must hold whole days")
    epoch = pd.Timestamp(0).as_unit(stamps.dt.unit)  # a date far from 1970 is out of range in ns
    return ((stamps - epoch) // pd.Timedelta(days=1)).astype("Int64")


def _in_steps(values, step, name):
    """The times as whole numbers of ``step`` from the earliest one: 0.0003 is 3 steps after
    0.0 for a step of 0.0001, and a Monday is 1 step after the Monday before for a step of 7
    days. A time that is not a whole number of steps from the others is refused: for whole
    numbers exactly, for others within what the floats can tell apart."""
    gap = ModuleError(
        f"time column '{name}' has times that are not a whole number of steps ({step:g}) apart"
    )
    present = values.notna().to_numpy()
    if not present.any():
        return values.astype("Int64")
    if pd.api.types.is_integer_dtype(values) and step == int(step) and step >= 1:
        whole = values.to_numpy(dtype="int64", na_value=0)
        count, left = np.divmod(whole - whole[present].min(), int(step))
        if (left[present] != 0).any():
            raise gap
        return pd.Series(count, index=values.index).where(present).astype("Int64")
    numbers = values.to_numpy(dtype="float64", na_value=np.nan)
    away = numbers - numbers[present].min()
    with np.errstate(all="ignore"):
        scaled = np.round(away / step)
    if not np.isfinite(scaled[present]).all() or scaled[present].max() > 2**53:
        raise ModuleError(
            f"time column '{name}' has too many steps ({step:g}) in it; use a larger step"
        )
    # the floats of the times are only as exact as their size: allow for that, not for more
    noise = 4 * np.spacing(np.abs(numbers[present]).max()) + step * 1e-9
    if (np.abs(away[present] - scaled[present] * step) > noise).any():
        raise gap
    return pd.Series(scaled, index=values.index).astype("Int64")


def lag(df, params, ctx):
    """Add, for each row, the value of the ``columns`` at an earlier ``time`` of the same ``by``
    group: ``column_lag1`` is the value one step of ``time`` before, ``column_lag3`` three steps
    before. ``time`` holds whole numbers (a month number, a day number) or dates (the step is
    then a day), or numbers a ``step`` apart (0.0001 for readings every 0.0001; 7 for weekly dates);
    the step is counted in them, not in rows, so a time with no row gives an empty
    value instead of the one before it. Rows of a group with the same time are first reduced to
    their ``how`` (mean or sum), so ``by`` can be coarser than a row: lagging the mean of an item
    over all shops. No row reads its own time or a later one."""
    time = require_column(df, params["time"])
    by = pick_columns(df, params["by"]) if params["by"] else []
    if time in by:
        raise ModuleError("by cannot include the time column")
    if len(set(by)) != len(by) or len(set(params["columns"])) != len(params["columns"]):
        raise ModuleError("by and columns cannot name a column twice")
    if not params["columns"]:
        raise ModuleError("name the columns to lag")
    columns = [c for c in pick_columns(df, params["columns"]) if c != time and c not in by]
    if not columns:
        raise ModuleError("the columns to lag cannot be only the time or the by columns")
    for column in columns:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ModuleError(f"column '{column}' is not numeric")
    step = params["step"]
    if not step > 0:
        raise ModuleError("step must be above 0")
    original_time = wide = df[time]
    if not pd.api.types.is_numeric_dtype(wide) or pd.api.types.is_bool_dtype(wide):
        wide = _day_numbers(wide, time)
    elif step == 1 and not (wide.dropna() == wide.dropna().round()).all():
        raise ModuleError(
            f"time column '{time}' must hold whole numbers or dates "
            "(or set step to the gap between neighbouring times)"
        )
    if step != 1:
        wide = _in_steps(wide, step, time)
    lags = _lags(params["lags"])
    check_cells(len(df), len(df.columns) + len(columns) * len(lags))
    # a narrow integer (a byte of days) would wrap round when a lag is added: work on a wide one
    if pd.api.types.is_integer_dtype(wide):
        wide = wide.astype(
            "Int64" if isinstance(wide.dtype, pd.api.extensions.ExtensionDtype) else "int64"
        )
    df = df.assign(**{time: wide})
    keys = [*by, time]
    grouped = df.groupby(keys)[columns]
    # a group and time whose values are all missing stays empty (a sum would give 0)
    reduced = (grouped.sum(min_count=1) if params["how"] == "sum" else grouped.mean()).reset_index()
    out = df
    for k in lags:
        earlier = reduced.copy()
        earlier[time] = earlier[time] + k  # the value at time t is read by the rows at t + k
        fresh = unique_names([str(c) for c in out.columns] + [f"{c}_lag{k}" for c in columns])[
            len(out.columns) :
        ]
        earlier = earlier.rename(columns=dict(zip(columns, fresh, strict=True)))
        out = out.merge(earlier, how="left", on=keys)
    out[time] = original_time.array  # the column as it came, not the wide copy
    return out


_WINDOW_STATS = ("mean", "std", "min", "max", "sum", "count")


def _window_stats(text: str) -> list[str]:
    """The statistics named in a comma-separated list, without repeats."""
    stats = [part.strip() for part in text.split(",") if part.strip()]
    unknown = [stat for stat in stats if stat not in _WINDOW_STATS]
    if unknown or not stats:
        raise ModuleError(f"stats must name one or more of {', '.join(_WINDOW_STATS)}")
    return list(dict.fromkeys(stats))


def _order_values(values, name):
    """The order column as numbers or dates; text must be a date written year-month-day (a time
    of day may follow)."""
    kind = pd.api.types.infer_dtype(values, skipna=True)
    if kind in ("string", "date", "datetime", "datetime64"):
        if kind == "string" and not (
            values.dropna().astype(str).map(_DATE_TEXT.fullmatch).notna().all()
        ):
            raise ModuleError(
                f"order column '{name}' has text that is not a date written year-month-day, "
                "such as 2015-07-01"
            )
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)  # "could not infer format"
                values = pd.to_datetime(values)
        except (ValueError, TypeError):
            raise ModuleError(
                f"order column '{name}' has dates that cannot be read in one format"
            ) from None
        if values.dt.tz is not None:
            values = values.dt.tz_localize(None)
    elif pd.api.types.is_bool_dtype(values) or not (
        pd.api.types.is_numeric_dtype(values) or pd.api.types.is_datetime64_any_dtype(values)
    ):
        raise ModuleError(f"order column '{name}' must hold numbers or dates")
    return values


class _Rows(BaseIndexer):
    """Window bounds given row by row, for rows sorted by group and order."""

    def __init__(self, start, end):
        super().__init__()
        self.start, self.end = start, end

    def get_window_bounds(
        self, num_values=0, min_periods=None, center=None, closed=None, step=None
    ):
        return self.start, self.end


def _is_date(key):
    return pd.api.types.is_datetime64_any_dtype(key)


def _order_numbers(key):
    """The order column as floats: numbers as they are, dates as days from the earliest."""
    if _is_date(key):
        return ((key - key.min()) / pd.Timedelta(days=1)).to_numpy(dtype="float64", na_value=np.nan)
    return key.to_numpy(dtype="float64", na_value=np.nan)


def _span_rows(run, order, span, around):
    """The first row and the row after the last of each window of a range of the order, for rows
    sorted by group and order: the rows whose order is within ``span`` before the row's (the row's
    own order and later ones are left out), or within half of ``span`` either side of it (itself
    and the rows of its own order included). A group is a ``run``; the order values are replaced
    by their ranks so that a group and an order make one sorted whole number to search."""
    # for 0.3 - 0.1 not being 0.2: a row on the edge of the range is in. The floats of large
    # orders are coarse (1.7e9 has gaps of 2.4e-7), so allow for their size too.
    finite = order[np.isfinite(order)]
    slack = max(span * 1e-6, 4 * np.spacing(np.abs(finite).max()) if len(finite) else 0.0)
    reach = span / 2 if around else span
    low = order - reach - slack
    high = order + reach + slack
    ranked = np.unique(np.concatenate([order, low, high] if around else [order, low]))
    width = len(ranked) + 1

    def key(values):
        return run * width + np.searchsorted(ranked, values)

    rows = key(order)
    start = np.searchsorted(rows, key(low), side="left")
    if around:
        return start, np.searchsorted(rows, key(high), side="right")
    return start, np.searchsorted(rows, rows, side="left")  # before the rows of its own order


def _window_rows(groups, order, same, window, span, around):
    """The first row and the row after the last of each window, for rows sorted by group and
    order: ``window`` rows centred on the row (itself included), or the ``window`` rows whose
    order is earlier than the row's; or, for a ``span``, the rows within a range of the order.
    No window goes over the edge of its group. ``same`` holds the order as it is, to tell rows of
    one order from the others."""
    n = len(groups)
    rows = np.arange(n)
    group_new = np.ones(n, dtype=bool)
    group_new[1:] = groups[1:] != groups[:-1]
    first = np.flatnonzero(group_new)
    last = np.append(first[1:], n)
    run = np.cumsum(group_new) - 1
    if span:
        return _span_rows(run, order, span, around)
    group_start, group_end = first[run], last[run]
    if around:
        reach = window // 2
        return np.maximum(rows - reach, group_start), np.minimum(rows + reach + 1, group_end)
    # the first row of the rows that share the row's order: the window ends before it
    tie_new = group_new.copy()
    tie_new[1:] |= same[1:] != same[:-1]
    tie_start = np.flatnonzero(tie_new)[np.cumsum(tie_new) - 1]
    return np.maximum(tie_start - window, group_start), tie_start


def rolling(df, params, ctx):
    """Add statistics of the values around each row: ``column_before5_mean`` is the mean of the
    5 rows before it, ``column_around5_std`` the standard deviation of the 5 rows centred on it
    (itself included). The rows are taken in the order of the ``order`` column within each ``by``
    group. ``before`` reads only rows whose order is earlier than the row's, so rows with the same
    order do not read each other; ``around`` reads the rows next to the row, whatever their order.
    A row with no ``order`` or no ``by`` value gets empty values and is left out of the windows of
    the others. A window at the edge of a group is shorter."""
    order = require_column(df, params["order"])
    by = pick_columns(df, params["by"]) if params["by"] else []
    if order in by:
        raise ModuleError("by cannot include the order column")
    if len(set(by)) != len(by) or len(set(params["columns"])) != len(params["columns"]):
        raise ModuleError("by and columns cannot name a column twice")
    if not params["columns"]:
        raise ModuleError("name the columns to summarize")
    columns = [c for c in pick_columns(df, params["columns"]) if c != order and c not in by]
    if not columns:
        raise ModuleError("the columns to summarize cannot be only the order or the by columns")
    for column in columns:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ModuleError(f"column '{column}' is not numeric")
    key = _order_values(df[order], order).reset_index(drop=True)
    window, span, side = params["window"], params["span"], params["side"]
    around = side == "around"
    if (window > 0) == (span > 0):
        raise ModuleError("name a window (a number of rows) or a span (a range of the order)")
    if around and window > 0 and window % 2 == 0:
        raise ModuleError("an around window must have an odd number of rows")
    stats = _window_stats(params["stats"])
    check_cells(len(df), len(df.columns) + len(columns) * len(stats))
    base = df[[*by, *columns]].reset_index(drop=True)
    sorting = base[by].set_axis([f"by{i}" for i in range(len(by))], axis=1).assign(order=key.array)
    position = sorting.sort_values(list(sorting.columns), kind="stable").index.to_numpy()
    ordered = base.iloc[position]
    if by:  # a row with no group value is -1: a run of its own, left empty below
        groups = ordered.groupby(by, sort=False).ngroup().to_numpy()
    else:
        groups = np.zeros(len(ordered), dtype=np.int64)
    ordered_key = key.iloc[position]
    numbers = _order_numbers(ordered_key)
    same = ordered_key.to_numpy() if _is_date(ordered_key) else numbers
    start, end = _window_rows(groups, numbers, same, window, span, around)
    label = (
        f"{side}_span{np.format_float_positional(span, trim='-')}" if span else f"{side}{window}"
    )
    usable = ordered_key.notna().to_numpy() & (groups >= 0)  # in the windows and given values
    names = unique_names(
        [str(c) for c in df.columns] + [f"{c}_{label}_{stat}" for c in columns for stat in stats]
    )[len(df.columns) :]
    out = df.copy()
    fresh = iter(names)
    for column in columns:
        values = ordered[column].reset_index(drop=True).where(usable)
        summary = values.rolling(_Rows(start, end), min_periods=1).agg(stats)
        summary[~usable] = np.nan
        summary.index = position
        summary = summary.reindex(range(len(df)))
        for stat in stats:
            out[next(fresh)] = summary[stat].to_numpy()
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
    "Join datasets by key columns",
    {
        "other_dataset_id": _OTHER,
        "key": {**_NAME, "default": ""},
        "keys": _NAMES,
        "other_key": {**_NAME, "default": ""},
        "other_keys": _NAMES,
        "summarize": {"type": "boolean", "default": False},
        "columns": _NAMES,
    },
    ("other_dataset_id",),
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
        "step": {"type": "number", "minimum": 0, "default": 1},
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
_op(
    "rolling",
    "Add statistics of nearby values",
    {
        "order": _NAME,
        "by": _NAMES,
        "columns": _NAMES,
        "window": {"type": "integer", "minimum": 0, "maximum": 1_000_000, "default": 0},
        "span": {"type": "number", "minimum": 0, "default": 0},
        "side": {"type": "string", "enum": ["before", "around"], "default": "before"},
        "stats": {"type": "string", "maxLength": 100, "default": "mean"},
    },
    ("order", "columns"),
    rolling,
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
