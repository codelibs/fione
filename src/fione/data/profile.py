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

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from pandas.api import types as pdt

from fione.data.frames import parse_datetimes
from fione.engine.prep import Task, infer_task

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
_SCORE_BINS = 64
_SCORE_SMOOTHING = 10.0
_SCORE_MARGIN = 0.10
_SCORE_MAX_CLASSES = 100  # the one-vs-rest AUCs cost one pass per class
# score -> (threshold, chance)
_SCORE_THRESHOLDS = {"classification": (0.95, 0.5), "regression": (0.90, 0.0)}

IDENTICAL = "identical to target"
DETERMINES = "value determines target"
CORRELATED = "near-perfect correlation with target"
PREDICTS_ALONE = "predicts the target on its own"
ORDERED_BY_TARGET = "row order follows the target"
# reasons that only warn: a legitimate strong column can score as high as a leak
SCORE_REASONS = frozenset({CORRELATED, PREDICTS_ALONE, ORDERED_BY_TARGET})
LEAK_STRONG = 0.99


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
    leak_partial: bool = False  # the leak check's time budget ran out before every column


@dataclass
class LeakCheck:
    suspects: list[LeakSuspect]
    partial: bool


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
        return IDENTICAL, 1.0
    if t_float is not None and _is_plain_numeric(s.dtype):
        x, y = _as_float(sp), t_float[paired]
        ok = ~np.isnan(x) & ~np.isnan(y)
        x, y = x[ok], y[ok]
        if x.size >= 3 and x.std() > 0 and y.std() > 0:
            r = abs(float(np.corrcoef(x, y)[0, 1]))
            if r >= _LEAK_CORRELATION:
                return CORRELATED, r
    n_values = int(s.notna().sum())
    if n_values >= _LEAK_MIN_ROWS and 2 <= col.n_unique <= 0.5 * n_values and tp.nunique() >= 2:
        pairs = pd.DataFrame({"value": sp.to_numpy(), "target": tp.to_numpy()}).drop_duplicates()
        if pairs["value"].is_unique:
            return DETERMINES, 1.0
    return None


def _value_suspects(
    df: pd.DataFrame, columns: list[ColumnProfile], target: str
) -> list[LeakSuspect]:
    """The checks on the values: identical, determines and the Pearson correlation."""
    t = df[target]
    t_float = _as_float(t) if _is_plain_numeric(t.dtype) else None
    suspects = []
    for col in columns:
        if col.name == target or col.kind in ("id", "constant"):
            continue
        found = _leak_reason(col, df[col.name], t, t_float)
        if found:
            suspects.append(LeakSuspect(col.name, found[0], found[1]))
    return suspects


def _ordered_values(s: pd.Series, kind: Kind) -> np.ndarray | None:
    """Float values of ``s`` (NaN where missing) when it is ordered, else ``None``. Strings
    that all parse as numbers count as numbers."""
    if kind == "datetime":
        parsed = s if pdt.is_datetime64_any_dtype(s.dtype) else parse_datetimes(s)
        if isinstance(parsed.dtype, pd.DatetimeTZDtype):
            parsed = parsed.dt.tz_convert(None)
        values = parsed.to_numpy().view("int64").astype("float64")  # in the column's own unit
        return np.where(parsed.isna().to_numpy(), np.nan, values)
    if pdt.is_bool_dtype(s.dtype) or isinstance(s.dtype, pd.CategoricalDtype):
        return None
    if _is_plain_numeric(s.dtype):
        return None if kind == "categorical" else _as_float(s)
    numbers = pd.to_numeric(s, errors="coerce")
    if numbers.notna().sum() < s.notna().sum():
        return None
    return _as_float(numbers)


def _score_bins(s: pd.Series, kind: Kind) -> np.ndarray:
    """Bin codes: quantile bins for ordered values, one bin per value otherwise. Missing values
    share a bin of their own."""
    values = _ordered_values(s, kind)
    if values is None:
        codes, uniques = pd.factorize(s)
        return np.where(codes < 0, len(uniques), codes)
    ok = ~np.isnan(values)
    bins = np.full(len(values), _SCORE_BINS, dtype=np.int64)
    if ok.any():
        edges = np.unique(np.quantile(values[ok], np.linspace(0, 1, _SCORE_BINS + 1)[1:-1]))
        bins[ok] = np.searchsorted(edges, values[ok], side="right")
    return bins


def _out_of_fold_means(bins: np.ndarray, y: np.ndarray, folds: np.ndarray) -> np.ndarray:
    """Each row's prediction: the smoothed mean of ``y`` in its bin over the other fold."""
    n_bins = int(bins.max()) + 1
    out = np.empty(len(y))
    for fold in (0, 1):
        fit, held = folds != fold, folds == fold
        prior = y[fit].mean()
        sums = np.bincount(bins[fit], weights=y[fit], minlength=n_bins)
        counts = np.bincount(bins[fit], minlength=n_bins)
        # a bin unseen in the other fold gets the prior
        out[held] = ((sums + _SCORE_SMOOTHING * prior) / (counts + _SCORE_SMOOTHING))[bins[held]]
    return out


def _auc(pred: np.ndarray, positive: np.ndarray) -> float | None:
    n_pos = int(positive.sum())
    n_neg = len(positive) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    _, inverse, counts = np.unique(pred, return_inverse=True, return_counts=True)
    ranks = (np.cumsum(counts) - (counts - 1) / 2)[inverse]  # ties share their mean rank
    return float((ranks[positive].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def single_column_score(
    s: pd.Series, kind: Kind, t: pd.Series, task: Task, *, seed: int = 0
) -> float | None:
    """How well ``s`` alone predicts ``t``, out of fold: the column is binned, each row is
    predicted by its bin's target mean over the other of two folds, and the predictions are
    scored by AUC (classification; the mean one-vs-rest AUC for more than two classes) or R^2.
    ``None`` when the target leaves nothing to score.

    Known limitation: the smoothing pulls small bins towards the mean, which costs R^2 but not
    AUC. Regression leaks in fewer than about 3,000 rows therefore mostly score below the
    threshold (a noisy log of the target: about 0.6 at 1,000 rows, 0.3 at 300)."""
    if task == "regression":
        y = _as_float(t)
        keep = ~np.isnan(y)
    else:
        keep = t.notna().to_numpy()
        codes, _ = pd.factorize(t[keep])
    if keep.sum() < 2:
        return None
    bins = _score_bins(s[keep], kind)
    n = len(bins)
    folds = np.empty(n, dtype=np.int64)
    folds[np.random.default_rng(seed).permutation(n)] = np.arange(n) % 2
    if task == "regression":
        y = y[keep]
        total = float(((y - y.mean()) ** 2).sum())
        if total == 0:
            return None
        pred = _out_of_fold_means(bins, y, folds)
        return 1 - float(((y - pred) ** 2).sum()) / total
    n_classes = int(codes.max()) + 1
    if n_classes < 2 or n_classes > _SCORE_MAX_CLASSES:
        return None
    # both AUCs are symmetric in the labels, so which label is "positive" does not matter
    classes = [1] if n_classes == 2 else range(n_classes)
    aucs = []
    for k in classes:
        positive = codes == k
        found = _auc(_out_of_fold_means(bins, positive.astype("float64"), folds), positive)
        if found is not None:
            aucs.append(found)
    return float(np.mean(aucs)) if aucs else None


def flag_scores(scores: dict[str, float], task: Task) -> set[str]:
    """Columns whose score is suspiciously high: at least the threshold, and clearly above the
    best column below it (chance when there is none)."""
    threshold, chance = _SCORE_THRESHOLDS[task]
    baseline = max((v for v in scores.values() if v < threshold), default=chance)
    # rounded so that 0.99 - 0.89 counts as the full margin
    return {
        c for c, v in scores.items() if v >= threshold and round(v - baseline, 9) >= _SCORE_MARGIN
    }


def leak_check(
    df: pd.DataFrame,
    columns: list[ColumnProfile],
    target: str,
    *,
    time_budget: float = 3.0,
    max_rows: int = 10_000,
    min_rows: int = 200,
    clock: Callable[[], float] = time.monotonic,
) -> LeakCheck:
    """Columns of ``df`` (profiled as ``columns``) that may reveal ``target``.

    The checks on the values run first: identical values, a value that determines the target,
    and a Pearson correlation of at least 0.99. Every other non-constant column then gets
    ``single_column_score`` on a deterministic sample of at most ``max_rows`` rows with a
    target (no score below ``min_rows``), and ``flag_scores`` picks the suspects. Columns are
    scored in profile order until ``time_budget`` seconds have passed; ``partial`` is then
    true. Each column is listed at most once, with its first reason."""
    start = clock()
    suspects = _value_suspects(df, columns, target)
    listed = {s.column for s in suspects}
    todo = [
        c for c in columns if c.name not in listed and c.name != target and c.kind != "constant"
    ]
    rows = np.flatnonzero(df[target].notna().to_numpy())
    if len(rows) > max_rows:
        rows = np.sort(np.random.default_rng(0).choice(rows, max_rows, replace=False))
    partial = False
    if todo and len(rows) >= min_rows:
        t = df[target].iloc[rows]
        task = infer_task(t)
        scores, kinds = {}, {}
        for col in todo:
            if clock() - start > time_budget:
                partial = True
                break
            score = single_column_score(df[col.name].iloc[rows], col.kind, t, task)
            if score is not None:
                scores[col.name], kinds[col.name] = score, col.kind
        for name in flag_scores(scores, task):
            reason = ORDERED_BY_TARGET if kinds[name] in ("id", "datetime") else PREDICTS_ALONE
            suspects.append(LeakSuspect(name, reason, scores[name]))
    suspects.sort(key=lambda s: (-s.score, s.column))
    return LeakCheck(suspects, partial)


def leak_suspects(df: pd.DataFrame, columns: list[ColumnProfile], target: str) -> list[LeakSuspect]:
    """``leak_check(...).suspects`` with the default budget."""
    return leak_check(df, columns, target).suspects


def profile_dataset(
    df: pd.DataFrame, target: str | None = None, *, sample_rows: int = 200_000
) -> DatasetProfile:
    """Profile ``df``; frames above ``sample_rows`` rows are sampled deterministically."""
    if target is not None and target not in df.columns:
        raise ValueError(f"target column '{target}' not found")
    work = df.sample(sample_rows, random_state=0) if len(df) > sample_rows else df
    columns = [_profile_column(name, work[name]) for name in work.columns]
    check = leak_check(work, columns, target) if target is not None else LeakCheck([], False)
    return DatasetProfile(
        n_rows=len(df),
        n_cols=df.shape[1],
        columns=columns,
        correlations=_correlations(work, columns),
        leak_suspects=check.suspects,
        leak_partial=check.partial,
    )
