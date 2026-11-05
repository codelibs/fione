import re
import warnings
from typing import Literal

import numpy as np
import pandas as pd
from pandas.tseries.api import guess_datetime_format

ColumnType = Literal["numeric", "categorical", "text", "datetime"]

_JAPANESE_DATE = re.compile(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日?")
_YEAR_FIRST = re.compile(r"^\s*\d{4}\D")
_DAY_MONTH = re.compile(r"^\s*(\d{1,2})[-/.](\d{1,2})[-/.]\d{2,4}")
_SAMPLE = 1000
_MIN_PARSED = 0.95
_MIN_VALUES = 5
_MIN_SIGNAL = 0.5
_PLAIN_NUMBER = r"^\s*(?:[-+]?\d+(?:\.\d+)?|\d+/\d+)\s*$"
_YEAR_SIGNAL = r"(?<!\d)(?:19|20)\d{2}(?!\d)|\d{4}年"
_DATE_SIGNAL = (
    _YEAR_SIGNAL + r"|(?i:\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)"
    r"|\d+月"
    r"|\d{1,2}:\d{2}:\d{2}"
)


def _spread(values: pd.Series) -> pd.Series:
    """About ``_SAMPLE`` values spread over the whole column: the head of a sorted file is not
    representative."""
    picks = np.linspace(0, len(values) - 1, min(len(values), _SAMPLE)).astype(int)
    return values.iloc[picks]


def is_day_first(s: pd.Series) -> bool:
    """Whether the strings of ``s`` put the day before the month (``25-12-2012``): the first
    field is above 12 somewhere and the second never is. Otherwise month first, as in ISO and
    US dates."""
    if pd.api.types.is_datetime64_any_dtype(s.dtype) or pd.api.types.is_numeric_dtype(s.dtype):
        return False
    fields = _spread(s.dropna().astype(str)).str.extract(_DAY_MONTH).dropna().astype(int)
    return bool(len(fields) and (fields[0] > 12).any() and not (fields[1] > 12).any())


def looks_like_dates(nonnull: pd.Series, need_year: bool = False) -> bool:
    """Whether the non-missing strings of a column are dates: enough of a sample carries a year,
    a month name or a time, and parses as a date other than a plain number. ``need_year``: it
    must be the year (a time or a month alone would be dated by today's clock)."""
    if len(nonnull) < _MIN_VALUES:
        return False
    sample = _spread(nonnull).astype(str)
    signal = _YEAR_SIGNAL if need_year else _DATE_SIGNAL
    if sample.str.contains(signal, regex=True).mean() < (_MIN_PARSED if need_year else _MIN_SIGNAL):
        return False
    plain = sample.str.match(_PLAIN_NUMBER)
    parsed = parse_datetimes(sample)
    return bool((parsed.notna() & ~plain).mean() >= _MIN_PARSED)


def parse_datetimes(s: pd.Series, dayfirst: bool | None = None) -> pd.Series:
    """Parse ``s`` as datetimes, leaving unparseable values as NaT.

    Japanese dates (``2024年3月5日``) are understood. ``dayfirst`` says whether ``02-10-2012``
    is the 2nd of October; left as ``None`` it is read from ``s`` (``is_day_first``), so give
    the value found on the training data when parsing a batch that may be small. Values are
    naive unless the strings carry differing UTC offsets (e.g. across a DST change); those
    cannot share one naive dtype, so the whole column is converted to tz-aware UTC instead of
    raising.
    """
    if pd.api.types.is_numeric_dtype(s.dtype):
        return pd.to_datetime(s, errors="coerce")
    if pd.api.types.is_datetime64_any_dtype(s.dtype):
        return pd.to_datetime(s, errors="coerce", format="mixed")
    if dayfirst is None:
        dayfirst = is_day_first(s)
    index = s.index
    s = s.astype(str).str.replace(_JAPANESE_DATE, r"\1-\2-\3", regex=True).where(s.notna())
    s = s.reset_index(drop=True)
    try:
        out = _read(s, dayfirst, utc=False)
    except (ValueError, TypeError):  # "Mixed timezones detected"
        out = _read(s, dayfirst, utc=True)
    out.index = index
    return out


def _read(s: pd.Series, dayfirst: bool, utc: bool) -> pd.Series:
    """Strings as datetimes. One format, guessed from the first value and agreeing with
    ``dayfirst``, reads most columns in a single vectorised pass; the values it misses are read
    one by one, and a value that starts with the year is never read day first."""
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns, UTC]" if utc else "datetime64[ns]")
    present = s.dropna()
    first = present.iloc[0] if len(present) else ""
    first_day = dayfirst and not _YEAR_FIRST.match(first)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # "Parsing dates in %d/%m/%Y format ..."
        fmt = guess_datetime_format(first, dayfirst=first_day)
    if fmt and first_day == bool(re.search("%d.*%m", fmt)):
        out = pd.to_datetime(s, errors="coerce", format=fmt, utc=utc)
    missed = out.isna() & s.notna()
    if missed.any():
        year_first = s.str.match(_YEAR_FIRST).fillna(False).to_numpy(bool)
        for rows, day_first in ((missed & year_first, False), (missed & ~year_first, dayfirst)):
            if rows.any():
                out[rows] = pd.to_datetime(
                    s[rows], errors="coerce", format="mixed", dayfirst=day_first, utc=utc
                )
    return out


def _convert_strictly(s: pd.Series, column: str, to: str, convert) -> pd.Series:
    converted = convert(s)
    failed = int((converted.isna() & s.notna()).sum())
    if failed:
        raise ValueError(f"{failed} values in '{column}' cannot be converted to {to}")
    return converted


def change_column_type(df: pd.DataFrame, column: str, to: ColumnType) -> pd.DataFrame:
    """Return a copy of ``df`` with ``column`` converted; bad values raise, never become NaN."""
    if to not in ("numeric", "categorical", "text", "datetime"):
        raise ValueError(f"unknown column type '{to}'")
    if column not in df.columns:
        raise KeyError(column)
    out = df.copy()
    s = out[column]
    if to == "numeric":
        out[column] = _convert_strictly(s, column, to, lambda v: pd.to_numeric(v, errors="coerce"))
    elif to == "datetime":
        out[column] = _convert_strictly(s, column, to, parse_datetimes)
    elif to == "categorical":
        out[column] = s.astype("category")
    else:
        out[column] = s.astype(str)
    return out
