"""Dataset profiling (EDA): per-column kind, statistics, correlations and target-leak suspects.

Kind inference (first matching rule wins; ``n`` = non-null values, ``u`` = distinct ones):

1. ``constant``: ``u <= 1`` (all-null columns, and every column of a single-row frame).
2. ``categorical``: bool and ``category`` dtypes.
3. ``datetime``: datetime64 dtype; also string/object columns, judged on a deterministic spread
   sample of at most 1000 non-null values (at least 5 required), where at least 95% parse as
   dates, none of the counted ones is a plain number or fraction (``-1``, ``1.5``, ``1/2``),
   and at least 50% show a date signal: a 4-digit year (19xx/20xx), an English month name,
   ``<n>月`` or a ``hh:mm:ss`` time. So ``1-2``, ``3:2``, ``12-100`` and ``20240101`` are not dates.
4. Integer dtype: ``id`` if ``u == n`` and ``n >= 20``; ``categorical`` if ``u <= 10`` and
   ``u / n <= 0.05`` (0/1 flags, small codes); otherwise ``numeric``.
5. Other numeric dtype (floats): ``numeric``. Floats are never ``id``.
6. String/object: ``id`` if ``u == n`` and ``n >= 20``; ``categorical`` if ``u / n <= 0.5`` or
   ``u <= 50``; ``text`` if the mean string length is above 30; ``categorical`` if ``u <= 1000``;
   ``text`` otherwise.

Statistics (``stats``, ``histogram``, ``outlier_rate``) are filled for ``numeric`` columns and for
integer-coded ``categorical`` columns (their numeric dtype makes the mean of a 0/1 flag
meaningful); non-finite values are ignored there. Missing values never count as values.
The outlier rate uses the IQR rule: values outside ``[Q1 - 1.5 IQR, Q3 + 1.5 IQR]``. Consumers
must ignore ``outlier_rate`` unless ``kind == "numeric"``: for a 0/1 flag with a minority below 25%
the IQR is 0, so the rate merely equals the minority fraction.

Correlations need at least ``_CORR_MIN_PERIODS`` rows where both columns are present, so two sparse
columns that overlap on a couple of rows cannot report a spurious ``r = +-1``.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from pandas.api import types as pdt

from fione.data.frames import parse_datetimes

Kind = Literal["numeric", "categorical", "text", "datetime", "id", "constant"]

_HISTOGRAM_BINS = 20
_TOP_VALUES = 10
_TOP_CORRELATIONS = 20
_ID_MIN_ROWS = 20
_DATE_SAMPLE = 1000
_DATE_MIN_PARSED = 0.95
_DATE_MIN_VALUES = 5
_DATE_MIN_SIGNAL = 0.5
_PLAIN_NUMBER = r"^\s*(?:[-+]?\d+(?:\.\d+)?|\d+/\d+)\s*$"
_DATE_SIGNAL = (
    r"(?<!\d)(?:19|20)\d{2}(?!\d)"
    r"|(?i:\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)"
    r"|\d+月"
    r"|\d{1,2}:\d{2}:\d{2}"
)
_CORR_MIN_PERIODS = 10
_LEAK_CORRELATION = 0.99
_LEAK_MIN_ROWS = 20


@dataclass
class ColumnProfile:
    name: str
    kind: Kind
    missing_rate: float
    n_unique: int
    stats: dict | None
    histogram: list[tuple[float, int]] | None
    top_values: list[tuple[str, int]] | None
    outlier_rate: float | None


@dataclass
class LeakSuspect:
    column: str
    reason: str
    score: float


@dataclass
class DatasetProfile:
    n_rows: int
    n_cols: int
    columns: list[ColumnProfile]
    correlations: list[tuple[str, str, float]]
    leak_suspects: list[LeakSuspect]


def _is_plain_numeric(dtype) -> bool:
    return pdt.is_numeric_dtype(dtype) and not pdt.is_bool_dtype(dtype)


def _as_float(s: pd.Series) -> np.ndarray:
    """Float64 view of a numeric series with missing and infinite values as NaN."""
    arr = s.to_numpy(dtype="float64", na_value=np.nan)
    return np.where(np.isfinite(arr), arr, np.nan)


def _looks_like_dates(nonnull: pd.Series) -> bool:
    n = len(nonnull)
    if n < _DATE_MIN_VALUES:
        return False
    # spread over the whole column: the head of a sorted file is not representative
    picks = np.linspace(0, n - 1, min(n, _DATE_SAMPLE)).astype(int)
    sample = nonnull.iloc[picks].astype(str)
    if sample.str.contains(_DATE_SIGNAL, regex=True).mean() < _DATE_MIN_SIGNAL:
        return False
    plain = sample.str.match(_PLAIN_NUMBER)
    parsed = parse_datetimes(sample)
    return bool((parsed.notna() & ~plain).mean() >= _DATE_MIN_PARSED)


def _infer_kind(nonnull: pd.Series, n_unique: int) -> Kind:
    n = len(nonnull)
    if n_unique <= 1:
        return "constant"
    dtype = nonnull.dtype
    if pdt.is_bool_dtype(dtype) or isinstance(dtype, pd.CategoricalDtype):
        return "categorical"
    if pdt.is_datetime64_any_dtype(dtype):
        return "datetime"
    if pdt.is_numeric_dtype(dtype):
        if pdt.is_integer_dtype(dtype):
            if n_unique == n and n >= _ID_MIN_ROWS:
                return "id"
            if n_unique <= 10 and n_unique / n <= 0.05:
                return "categorical"
        return "numeric"
    if _looks_like_dates(nonnull):
        return "datetime"
    if n_unique == n and n >= _ID_MIN_ROWS:
        return "id"
    if n_unique / n <= 0.5 or n_unique <= 50:
        return "categorical"
    if nonnull.astype(str).str.len().mean() > 30:
        return "text"
    return "categorical" if n_unique <= 1000 else "text"


def _numeric_details(
    nonnull: pd.Series,
) -> tuple[dict | None, list[tuple[float, int]] | None, float | None]:
    arr = _as_float(nonnull)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return None, None, None
    q1, median, q3 = np.percentile(arr, [25, 50, 75])
    stats = {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        "min": float(arr.min()),
        "q25": float(q1),
        "median": float(median),
        "q75": float(q3),
        "max": float(arr.max()),
    }
    counts, edges = np.histogram(arr, bins=_HISTOGRAM_BINS)
    histogram = [(float(left), int(c)) for left, c in zip(edges[:-1], counts, strict=True)]
    iqr = q3 - q1
    outside = (arr < q1 - 1.5 * iqr) | (arr > q3 + 1.5 * iqr)
    return stats, histogram, float(outside.mean())


def _top_values(counts: pd.Series) -> list[tuple[str, int]]:
    # first-appearance order + stable sort keep ties deterministic
    top = counts.sort_values(ascending=False, kind="stable").head(_TOP_VALUES)
    return [(str(value), int(count)) for value, count in top.items()]


def _profile_column(name: str, s: pd.Series) -> ColumnProfile:
    nonnull = s.dropna()
    counts = nonnull.value_counts(sort=False)
    counts = counts[counts > 0]  # category dtype lists unused categories with a zero count
    n_unique = len(counts)
    kind = _infer_kind(nonnull, n_unique)
    stats = histogram = top_values = outlier_rate = None
    if kind in ("numeric", "categorical") and _is_plain_numeric(nonnull.dtype):
        stats, histogram, outlier_rate = _numeric_details(nonnull)
    if kind in ("categorical", "text", "id"):
        top_values = _top_values(counts)
    return ColumnProfile(
        name=name,
        kind=kind,
        missing_rate=float(s.isna().mean()) if len(s) else 0.0,
        n_unique=n_unique,
        stats=stats,
        histogram=histogram,
        top_values=top_values,
        outlier_rate=outlier_rate,
    )


def _correlations(df: pd.DataFrame, columns: list[ColumnProfile]) -> list[tuple[str, str, float]]:
    names = [c.name for c in columns if c.kind == "numeric"]
    if len(names) < 2:
        return []
    matrix = (
        pd.DataFrame({n: _as_float(df[n]) for n in names})
        .corr(min_periods=_CORR_MIN_PERIODS)
        .to_numpy()
    )
    rows, cols = np.triu_indices(len(names), k=1)
    pairs = [
        (names[i], names[j], float(r))
        for i, j, r in zip(rows, cols, matrix[rows, cols], strict=True)
        if np.isfinite(r)
    ]
    pairs.sort(key=lambda p: (-abs(p[2]), p[0], p[1]))
    return pairs[:_TOP_CORRELATIONS]


def _same_values(a: pd.Series, b: pd.Series) -> bool:
    if _is_plain_numeric(a.dtype) and _is_plain_numeric(b.dtype):
        return bool((_as_float(a) == _as_float(b)).all())
    return bool((a.astype(str).to_numpy() == b.astype(str).to_numpy()).all())


def _leak_reason(
    col: ColumnProfile, s: pd.Series, t: pd.Series, t_float: np.ndarray | None
) -> tuple[str, float] | None:
    paired = (s.notna() & t.notna()).to_numpy()
    if not paired.any():
        return None
    sp, tp = s[paired], t[paired]
    if _same_values(sp, tp):
        return "identical to target", 1.0
    if t_float is not None and _is_plain_numeric(s.dtype):
        x, y = _as_float(sp), t_float[paired]
        ok = ~np.isnan(x) & ~np.isnan(y)
        x, y = x[ok], y[ok]
        if x.size >= 3 and x.std() > 0 and y.std() > 0:
            r = abs(float(np.corrcoef(x, y)[0, 1]))
            if r >= _LEAK_CORRELATION:
                return "near-perfect correlation with target", r
    n_values = int(s.notna().sum())
    if n_values >= _LEAK_MIN_ROWS and 2 <= col.n_unique <= 0.5 * n_values and tp.nunique() >= 2:
        pairs = pd.DataFrame({"value": sp.to_numpy(), "target": tp.to_numpy()}).drop_duplicates()
        if pairs["value"].is_unique:
            return "value determines target", 1.0
    return None


def leak_suspects(df: pd.DataFrame, columns: list[ColumnProfile], target: str) -> list[LeakSuspect]:
    """Columns of ``df`` (profiled as ``columns``) that may reveal ``target``."""
    t = df[target]
    t_float = _as_float(t) if _is_plain_numeric(t.dtype) else None
    suspects = []
    for col in columns:
        if col.name == target or col.kind in ("id", "constant"):
            continue
        found = _leak_reason(col, df[col.name], t, t_float)
        if found:
            suspects.append(LeakSuspect(col.name, found[0], found[1]))
    suspects.sort(key=lambda s: (-s.score, s.column))
    return suspects


def profile_dataset(
    df: pd.DataFrame, target: str | None = None, *, sample_rows: int = 200_000
) -> DatasetProfile:
    """Profile ``df``; frames above ``sample_rows`` rows are sampled deterministically."""
    if target is not None and target not in df.columns:
        raise ValueError(f"target column '{target}' not found")
    work = df.sample(sample_rows, random_state=0) if len(df) > sample_rows else df
    columns = [_profile_column(name, work[name]) for name in work.columns]
    return DatasetProfile(
        n_rows=len(df),
        n_cols=df.shape[1],
        columns=columns,
        correlations=_correlations(work, columns),
        leak_suspects=leak_suspects(work, columns, target) if target is not None else [],
    )
