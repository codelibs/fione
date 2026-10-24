import re
from typing import Literal

import pandas as pd

ColumnType = Literal["numeric", "categorical", "text", "datetime"]

_JAPANESE_DATE = re.compile(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日?")


def parse_datetimes(s: pd.Series) -> pd.Series:
    """Parse ``s`` as datetimes, leaving unparseable values as NaT.

    Japanese dates (``2024年3月5日``) are understood. Values are naive unless the strings carry
    differing UTC offsets (e.g. across a DST change); those cannot share one naive dtype, so the
    whole column is converted to tz-aware UTC instead of raising.
    """
    if pd.api.types.is_numeric_dtype(s.dtype):
        return pd.to_datetime(s, errors="coerce")
    if not pd.api.types.is_datetime64_any_dtype(s.dtype):
        s = s.astype(str).str.replace(_JAPANESE_DATE, r"\1-\2-\3", regex=True).where(s.notna())
    try:
        return pd.to_datetime(s, errors="coerce", format="mixed")
    except ValueError:  # "Mixed timezones detected"
        return pd.to_datetime(s, errors="coerce", format="mixed", utc=True)


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
