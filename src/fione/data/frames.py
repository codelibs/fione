from typing import Literal

import pandas as pd

ColumnType = Literal["numeric", "categorical", "text", "datetime"]


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
        fmt = "mixed" if not pd.api.types.is_numeric_dtype(s.dtype) else None
        out[column] = _convert_strictly(
            s, column, to, lambda v: pd.to_datetime(v, errors="coerce", format=fmt)
        )
    elif to == "categorical":
        out[column] = s.astype("category")
    else:
        out[column] = s.astype(str)
    return out
