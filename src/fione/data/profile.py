"""Dataset profiling (EDA): per-column kind, statistics, correlations and target-leak suspects.

Kind inference (first matching rule wins; ``n`` = non-null values, ``u`` = distinct ones):

1. ``constant``: ``u == 0``, or ``u == 1`` on every row (all-null columns, and every column of a
   single-row frame). One value on some rows and missing on the others is a flag (``Yes`` or
   blank), a ``categorical`` column: the gaps tell the rows apart.
2. ``categorical``: bool and ``category`` dtypes.
3. ``datetime``: datetime64 dtype; also string/object columns, judged on a deterministic spread
   sample of at most 1000 non-null values (at least 5 required), where at least 95% parse as
   dates, none of the counted ones is a plain number or fraction (``-1``, ``1.5``, ``1/2``),
   and at least 50% show a date signal: a 4-digit year (19xx/20xx), an English month name,
   ``<n>月`` or a ``hh:mm:ss`` time. So ``1-2``, ``3:2``, ``12-100`` and ``20240101`` are not dates.
4. Integer dtype: ``id`` if ``u == n`` and ``n >= 20``; ``categorical`` if ``u <= 10`` and
   ``u / n <= 0.05`` (0/1 flags, small codes); otherwise ``numeric``.
5. Other numeric dtype (floats): ``numeric``. Floats are never ``id``.
6. String/object: ``list`` if the values are JSON lists of numbers (``number_list_shape``:
   ``[1, 2]`` or ``[[1, 2], [3, 4]]``, judged on a spread sample), whatever their count; ``id``
   if ``u == n`` and ``n >= 20`` and the values are not prose (``is_prose``: comments that are
   all different are ``text``); ``text`` if ``u`` is 1000 or more and the values are prose (a
   search query that repeats); ``categorical`` if ``u / n <= 0.5`` or ``u <= 50``; ``text`` if
   the mean string length is above 30; ``categorical`` if ``u <= 1000``; ``text`` otherwise.

Statistics (``stats``, ``histogram``, ``outlier_rate``) are filled for ``numeric`` columns and for
integer-coded ``categorical`` columns (their numeric dtype makes the mean of a 0/1 flag
meaningful); non-finite values are ignored there. Missing values never count as values.
The outlier rate uses the IQR rule: values outside ``[Q1 - 1.5 IQR, Q3 + 1.5 IQR]``. Consumers
must ignore ``outlier_rate`` unless ``kind == "numeric"``: for a 0/1 flag with a minority below 25%
the IQR is 0, so the rate merely equals the minority fraction.

Correlations need at least ``_CORR_MIN_PERIODS`` rows where both columns are present, so two sparse
columns that overlap on a couple of rows cannot report a spurious ``r = +-1``. A table with more
than ``_CORR_MAX_COLUMNS`` numeric columns lists none: the pairs grow with the square of the
columns, in time and memory, and among that many the strongest are rarely the ones to look at.
"""

import itertools
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from pandas.api import types as pdt

from fione.data.frames import looks_like_dates, parse_datetimes
from fione.engine.prep import (
    REPEATED_PROSE_VALUES,
    Task,
    infer_task,
    integer_date_format,
    is_prose,
    number_list_shape,
)

Kind = Literal["numeric", "categorical", "text", "datetime", "id", "constant", "list"]

_HISTOGRAM_BINS = 20
_TOP_VALUES = 10
_TOP_CORRELATIONS = 20
_ID_MIN_ROWS = 20
_CORR_MIN_PERIODS = 10
_CORR_MAX_COLUMNS = 1000
_LEAK_CORRELATION = 0.99
_LEAK_MIN_ROWS = 20
_DETERMINES_MIN_SINGLES = 2
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
_LEAK_CODES = {
    IDENTICAL: "identical",
    CORRELATED: "correlated",
    DETERMINES: "determines",
    PREDICTS_ALONE: "predicts_alone",
    ORDERED_BY_TARGET: "ordered",
}
LEAK_STRONG = 0.99
# A number target that is a column times a rate that a few categories fix (an amount in a currency
# times the rate of the currency and the period): the share of the variation of its logarithm that
# the categories explain once the column's logarithm is taken off, at least ``_DERIVED_SHARE`` of
# it, while the categories alone explain at most ``_DERIVED_ALONE`` of it.
_DERIVED_SHARE = 0.99
_DERIVED_ALONE = 0.9
_DERIVED_MAX_LEVELS = 300  # a key column of more values is a name, not a category
_DERIVED_MIN_GROUP = 20  # rows per combination of keys, on average
_DERIVED_ROWS = 50_000
_DERIVED_NUMBERS = 15  # number columns looked at
_DERIVED_SINGLES = 8  # key columns that are combined in pairs
_DERIVED_RATIO = 0.001  # of the variation of log(target) that the ratio to the column must keep
_DERIVED_RATE = 0.9  # of the variation of the ratio that the categories must explain
_DERIVED_SECS = 1.0  # the search for such columns stops after this long
# A target that two columns with few values fix together (every combination of their values, over
# at least ``_PAIRED_MIN_GROUP`` rows, has one target value, and the combinations cover
# ``_PAIRED_SHARE`` of the rows) while neither fixes it alone: the AND of two decisions, a code made
# of two letters. The ``_PAIRED_TOP`` columns that leave the target least uncertain are paired.
_PAIRED_MAX_VALUES = 10  # values of a column, a missing one counted
_PAIRED_MAX_CLASSES = 20
_PAIRED_MIN_GROUP = 20
_PAIRED_SHARE = 0.99
_PAIRED_TOP = 12
_PAIRED_ROWS = 100_000
_PAIRED_RANK_ROWS = 20_000  # rows the columns are ranked on
_PAIRED_SECS = 1.0


def leak_code(reason: str) -> str:
    """A leak suspect's reason as its stable code (``leak_correlated``, ...), the key of the
    translated message about it."""
    return "leak_" + _LEAK_CODES.get(reason, "other")


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
    mean_length: float | None = (
        None  # characters per value, of a ``text`` column the engine reads as prose
    )
    span: int | None = None  # last - first + 1 of a column of whole numbers (integer type)


@dataclass
class LeakSuspect:
    column: str
    reason: str
    score: float


@dataclass
class DerivedTarget:
    """A number target that may be computed from ``column`` and the categories ``keys``: within
    each combination of ``keys`` it is nearly a fixed multiple of ``column`` (``share`` of the
    variation of its logarithm is explained)."""

    column: str
    keys: tuple[str, ...]
    share: float


@dataclass
class PairedTarget:
    """A target that the columns ``first`` and ``second`` fix together: every combination of their
    values has one target value (``share`` of the rows lie in such combinations)."""

    first: str
    second: str
    share: float


@dataclass
class DatasetProfile:
    n_rows: int
    n_cols: int
    columns: list[ColumnProfile]
    correlations: list[tuple[str, str, float]]
    leak_suspects: list[LeakSuspect]
    leak_partial: bool = False  # the leak check's time budget ran out before every column
    derived: DerivedTarget | None = None  # see ``derived_target``
    derived_cut: bool = False  # the search for it ran out of time: do not keep the result
    paired: PairedTarget | None = None  # see ``paired_target``
    paired_cut: bool = False  # the search for it ran out of time: do not keep the result


@dataclass
class LeakCheck:
    suspects: list[LeakSuspect]
    partial: bool
    derived: DerivedTarget | None = None
    derived_cut: bool = False  # ``derived_target`` ran out of time (not a ``partial`` check)
    paired: PairedTarget | None = None
    paired_cut: bool = False  # ``paired_target`` ran out of time


def _is_plain_numeric(dtype) -> bool:
    return pdt.is_numeric_dtype(dtype) and not pdt.is_bool_dtype(dtype)


def _as_float(s: pd.Series) -> np.ndarray:
    """Float64 view of a numeric series with missing and infinite values as NaN."""
    arr = s.to_numpy(dtype="float64", na_value=np.nan)
    return np.where(np.isfinite(arr), arr, np.nan)


def _infer_kind(nonnull: pd.Series, n_unique: int, n_missing: int = 0) -> Kind:
    n = len(nonnull)
    if n_unique == 0 or (n_unique == 1 and not n_missing):
        return "constant"
    if n_unique == 1:
        return "categorical"
    dtype = nonnull.dtype
    if pdt.is_bool_dtype(dtype) or isinstance(dtype, pd.CategoricalDtype):
        return "categorical"
    if pdt.is_datetime64_any_dtype(dtype):
        return "datetime"
    if pdt.is_numeric_dtype(dtype):
        if pdt.is_integer_dtype(dtype):
            if n_unique == n and n >= _ID_MIN_ROWS:
                # a clock with one reading per row (20141021, a Unix time) is not a row's name
                return "numeric" if integer_date_format(nonnull) else "id"
            if n_unique <= 10 and n_unique / n <= 0.05:
                return "categorical"
        return "numeric"
    if looks_like_dates(nonnull):
        return "datetime"
    if number_list_shape(nonnull):
        return "list"  # read as numbers, however often its values repeat
    if n_unique == n and n >= _ID_MIN_ROWS:
        return "text" if is_prose(nonnull) else "id"
    if n_unique >= REPEATED_PROSE_VALUES and is_prose(nonnull):
        return "text"  # a short text that repeats, such as a search query
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
    try:
        counts, edges = np.histogram(arr, bins=_HISTOGRAM_BINS)
    except ValueError:  # values within float noise of one number: too close to cut into bins
        counts = np.zeros(_HISTOGRAM_BINS, dtype=int)
        counts[0] = arr.size
        edges = np.linspace(arr.min(), arr.max(), _HISTOGRAM_BINS + 1)
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
    kind = _infer_kind(nonnull, n_unique, len(s) - len(nonnull))
    stats = histogram = top_values = outlier_rate = None
    if kind in ("numeric", "categorical") and _is_plain_numeric(nonnull.dtype):
        stats, histogram, outlier_rate = _numeric_details(nonnull)
    if kind in ("categorical", "text", "id"):
        top_values = _top_values(counts)
    span = None
    if len(nonnull) and pdt.is_integer_dtype(nonnull.dtype):
        span = int(nonnull.max()) - int(nonnull.min()) + 1
    mean_length = None
    if kind == "text" and is_prose(nonnull):
        mean_length = float(nonnull.astype(str).str.len().mean())
    return ColumnProfile(
        name=name,
        kind=kind,
        missing_rate=float(s.isna().mean()) if len(s) else 0.0,
        n_unique=n_unique,
        stats=stats,
        histogram=histogram,
        top_values=top_values,
        outlier_rate=outlier_rate,
        mean_length=mean_length,
        span=span,
    )


def _correlations(df: pd.DataFrame, columns: list[ColumnProfile]) -> list[tuple[str, str, float]]:
    names = [c.name for c in columns if c.kind == "numeric"]
    if not 2 <= len(names) <= _CORR_MAX_COLUMNS:
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


def _only_unusual_targets(singles: pd.Series, target: pd.Series) -> bool:
    """Whether the rows with a value of their own (``singles``) hold, at least
    ``_DETERMINES_MIN_SINGLES`` of them and ``LEAK_STRONG`` of them, a target other than the
    most common one of ``target``: the value tells these rows from the rest."""
    unusual = singles != target.mode().iloc[0]
    return int(unusual.sum()) >= _DETERMINES_MIN_SINGLES and float(unusual.mean()) >= LEAK_STRONG


def _leak_reason(
    col: ColumnProfile, s: pd.Series, t: pd.Series, t_float: np.ndarray | None
) -> tuple[str, float] | None:
    paired = (s.notna() & t.notna()).to_numpy()
    if not paired.any():
        return None
    sp, tp = s[paired], t[paired]
    # a column that has a value on a few rows only is not a copy of the target on those
    if paired.sum() >= min(_LEAK_MIN_ROWS, int(t.notna().sum())) and _same_values(sp, tp):
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
        pairs = pd.DataFrame({"value": sp.to_numpy(), "target": tp.to_numpy()})
        once = ~pairs["value"].duplicated(keep=False)
        repeated = pairs[~once].drop_duplicates()
        if repeated["value"].is_unique and (
            # a value seen on 2+ rows that fixes the target is the evidence; so is a value
            # seen on one row only when, on every such row, the target is not its usual one
            # (a column that holds the target on the few rows where it is not 0)
            repeated["target"].nunique() >= 2 or _only_unusual_targets(pairs["target"][once], tp)
        ):
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


def _value_bins(s: pd.Series) -> np.ndarray:
    """One bin per distinct value; missing values share a bin of their own."""
    codes, uniques = pd.factorize(s)
    return np.where(codes < 0, len(uniques), codes)


def _quantile_bins(values: np.ndarray) -> np.ndarray:
    """At most ``_SCORE_BINS`` quantile bins; NaN values share a bin of their own."""
    ok = ~np.isnan(values)
    bins = np.full(len(values), _SCORE_BINS, dtype=np.int64)
    if ok.any():
        edges = np.unique(np.quantile(values[ok], np.linspace(0, 1, _SCORE_BINS + 1)[1:-1]))
        bins[ok] = np.searchsorted(edges, values[ok], side="right")
    return bins


def _score_binnings(s: pd.Series, kind: Kind) -> list[np.ndarray]:
    """The ways ``s`` is binned for the score: quantile bins for ordered values, one bin per
    value otherwise. Whole numbers get both, since they may be codes rather than quantities."""
    values = _ordered_values(s, kind)
    if values is None:
        return [_value_bins(s)]
    binnings = [_quantile_bins(values)]
    present = values[~np.isnan(values)]
    if kind != "datetime" and np.array_equal(present, np.round(present)):
        binnings.append(_value_bins(s))
    return binnings


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
    A whole-number column is binned both ways and keeps the better score. For more than two
    classes, a column that is missing exactly when the row is in one class (its is-missing
    indicator alone reaches ``LEAK_STRONG`` for that class) scores that AUC instead, since
    the mean dilutes it. ``None`` when the target leaves nothing to score, and for targets
    with more than ``_SCORE_MAX_CLASSES`` classes (one pass per class would not fit the
    budget).

    Known limitation: the smoothing pulls small bins towards the mean, which costs R^2 but not
    AUC. Regression leaks in fewer than roughly 5,000 rows therefore mostly score below the
    threshold (a noisy log of the target: about 0.87 at 3,000 rows, 0.6 at 1,000)."""
    if task == "regression":
        y = _as_float(t)
        keep = ~np.isnan(y)
    else:
        keep = t.notna().to_numpy()
        codes, _ = pd.factorize(t[keep])
    n = int(keep.sum())
    if n < 2:
        return None
    folds = np.empty(n, dtype=np.int64)
    folds[np.random.default_rng(seed).permutation(n)] = np.arange(n) % 2
    if task == "regression":
        y = y[keep]
        total = float(((y - y.mean()) ** 2).sum())
        if total == 0:
            return None

        def score(bins: np.ndarray) -> float | None:
            pred = _out_of_fold_means(bins, y, folds)
            return 1 - float(((y - pred) ** 2).sum()) / total

    else:
        n_classes = int(codes.max()) + 1
        if n_classes < 2 or n_classes > _SCORE_MAX_CLASSES:
            return None
        # both AUCs are symmetric in the labels, so which label is "positive" does not matter
        positives = [codes == k for k in ([1] if n_classes == 2 else range(n_classes))]

        def aucs_of(bins: np.ndarray) -> list[float]:
            aucs = [
                _auc(_out_of_fold_means(bins, positive.astype("float64"), folds), positive)
                for positive in positives
            ]
            return [a for a in aucs if a is not None]

        def score(bins: np.ndarray) -> float | None:
            aucs = aucs_of(bins)
            return float(np.mean(aucs)) if aucs else None

        missing = s[keep].isna().to_numpy()
        if n_classes > 2 and missing.any() and not missing.all():
            best = max(aucs_of(missing.astype(np.int64)), default=0.0)
            if best >= LEAK_STRONG:
                return best

    found = [v for v in map(score, _score_binnings(s[keep], kind)) if v is not None]
    return max(found, default=None)


def flag_scores(scores: dict[str, float], task: Task) -> set[str]:
    """Columns whose score is suspiciously high: at least ``LEAK_STRONG``, or at least the
    threshold and clearly above the best column below it (chance when there is none).

    Known limitation: a legitimate column just below the threshold raises the bar for every
    other column. Once the best column below the threshold scores 0.89 or more, only scores of
    ``LEAK_STRONG`` are flagged, so a dataset that one column already predicts well gets no
    warning for a leak that scores, say, 0.98. A leak beside a column at 0.949 needs 0.99,
    beside one at 0.95 it needs 0.95: the rule is not continuous."""
    threshold, chance = _SCORE_THRESHOLDS[task]
    baseline = max((v for v in scores.values() if v < threshold), default=chance)
    # rounded so that 0.99 - 0.89 counts as the full margin
    return {
        c
        for c, v in scores.items()
        if v >= LEAK_STRONG or (v >= threshold and round(v - baseline, 9) >= _SCORE_MARGIN)
    }


def derived_target(
    df: pd.DataFrame,
    columns: list[ColumnProfile],
    target: str,
    *,
    time_budget: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[DerivedTarget | None, bool]:
    """``(found, cut)``: the number column and the one or two category columns from which the
    number ``target`` may be computed (a pay in a currency from the amount, the currency and the
    period), or None, and whether the search was cut short by ``time_budget`` seconds.

    With ``y`` the target and ``x`` the column, on the rows where both are above 0 (at most
    ``_DERIVED_ROWS``) and ``r = log(y / x)``: the categories must explain at least
    ``_DERIVED_SHARE`` of the variation of ``log(y)`` in ``r`` and at least ``_DERIVED_RATE`` of
    the variation of ``r`` itself (a column that is the target but for noise has a ratio that no
    category explains), while they explain at most ``_DERIVED_ALONE`` of ``log(y)`` alone. The
    ratio must vary a little (``_DERIVED_RATIO`` of the variation of ``log(y)``: else the column
    is the target itself, which other checks name). The categories have 2 to
    ``_DERIVED_MAX_LEVELS`` values and ``_DERIVED_MIN_GROUP`` rows for each combination; one
    category is taken if it is enough, else the best pair of the ``_DERIVED_SINGLES`` best ones,
    if it leaves less than half of what that category leaves. The ``_DERIVED_NUMBERS`` columns
    most correlated with the target in logarithms are tried."""
    start = clock()
    budget = _DERIVED_SECS if time_budget is None else time_budget

    def late() -> bool:
        return clock() - start > budget

    if {c.name: c.kind for c in columns}.get(target) != "numeric":
        return None, False
    y = pd.to_numeric(df[target], errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
    rows = np.flatnonzero(np.isfinite(y) & (y > 0))
    if len(rows) < _LEAK_MIN_ROWS * 25:
        return None, False
    if len(rows) > _DERIVED_ROWS:
        rows = np.sort(np.random.default_rng(0).choice(rows, _DERIVED_ROWS, replace=False))
    work = df.iloc[rows]
    log_y = np.log(y[rows])
    if not log_y.var() > 0:
        return None, False
    keys = [
        c.name
        for c in columns
        if c.kind in ("categorical", "text") and 2 <= c.n_unique <= _DERIVED_MAX_LEVELS
    ]
    candidates = []
    for c in columns:
        if late():
            return None, True
        if c.name == target or c.kind != "numeric" or not _is_plain_numeric(df[c.name].dtype):
            continue
        x = _as_float(work[c.name])
        good = np.isfinite(x) & (x > 0)
        if good.mean() < 0.9 or good.sum() < _LEAK_MIN_ROWS * 25:
            continue
        log_x = np.log(np.where(good, x, 1.0))
        link = abs(np.corrcoef(log_x[good], log_y[good])[0, 1])
        if np.isfinite(link):
            candidates.append((link, c.name, good, log_x))
    if not candidates or not keys:
        return None, False
    candidates.sort(key=lambda c: -c[0])
    codes: dict[str, np.ndarray] = {}

    def unexplained(values: np.ndarray, key: tuple[str, ...], good: np.ndarray) -> float:
        """The variation of ``values`` left within the combinations of ``key``, relative to its
        whole variation (1 when the combinations are too small to say)."""
        code = np.zeros(len(values), dtype=np.int64)
        for k in key:
            if k not in codes:
                codes[k] = pd.factorize(work[k])[0].astype(np.int64)
            code = code * (_DERIVED_MAX_LEVELS + 2) + (codes[k] + 1)
        code, levels = pd.factorize(code[good])
        if good.sum() < _DERIVED_MIN_GROUP * len(levels):
            return 1.0
        v = values[good]
        means = np.bincount(code, weights=v) / np.bincount(code)
        return float(((v - means[code]) ** 2).mean()) / float(v.var())

    best = None
    for _, name, good, log_x in candidates[:_DERIVED_NUMBERS]:
        ratio = log_y - log_x
        spread = float(ratio[good].var()) / float(log_y[good].var())  # relative to log(y)
        if spread < _DERIVED_RATIO:
            continue
        singles = []
        for k in keys:
            if late():
                return best, True
            singles.append((unexplained(ratio, (k,), good), k))
        singles.sort()
        left, key = singles[0][0], (singles[0][1],)
        if 1 - left * spread < _DERIVED_SHARE or 1 - left < _DERIVED_RATE:  # not enough: a pair
            alone, pair_left = left, left
            for pair in itertools.combinations([k for _, k in singles[:_DERIVED_SINGLES]], 2):
                if late():
                    return best, True
                found = unexplained(ratio, pair, good)
                if found < alone * 0.5 and found < pair_left:
                    pair_left, key = found, pair
            left = pair_left if len(key) == 2 else left
        share = 1 - left * spread
        if share >= _DERIVED_SHARE and 1 - left >= _DERIVED_RATE:
            if 1 - unexplained(log_y, key, good) <= _DERIVED_ALONE:
                if best is None or share > best.share:
                    best = DerivedTarget(name, tuple(sorted(key)), share)
    return best, False


def paired_target(
    df: pd.DataFrame,
    columns: list[ColumnProfile],
    target: str,
    *,
    time_budget: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[PairedTarget | None, bool]:
    """``(found, cut)``: the two columns that fix the target of 2 to ``_PAIRED_MAX_CLASSES``
    values together, or None, and whether the search was cut short by ``time_budget`` seconds
    (``_PAIRED_SECS``; nothing is found then). Of the columns with 2 to ``_PAIRED_MAX_VALUES``
    values (``_PAIRED_ROWS`` rows at most), the ``_PAIRED_TOP`` that leave the target least
    uncertain are paired. A pair counts when its combinations of ``_PAIRED_MIN_GROUP`` rows or
    more that hold one target value hold ``_PAIRED_SHARE`` of the rows of every target value
    (so a rare value, a flag on 0.3% of the rows, must be fixed too), and no column does so
    alone (one that fixes the target on every row is a value that determines it, which the leak
    check names)."""
    start = clock()
    budget = _PAIRED_SECS if time_budget is None else time_budget
    if target not in df.columns:
        return None, False
    rows = np.flatnonzero(df[target].notna().to_numpy())
    if len(rows) < _PAIRED_MIN_GROUP * 4:
        return None, False
    if len(rows) > _PAIRED_ROWS:
        rows = np.sort(np.random.default_rng(0).choice(rows, _PAIRED_ROWS, replace=False))
    y, _ = pd.factorize(df[target].iloc[rows])
    classes = int(y.max()) + 1
    if not 2 <= classes <= _PAIRED_MAX_CLASSES:
        return None, False

    def table(code: np.ndarray, size: int) -> np.ndarray:
        return np.bincount(code * classes + y, minlength=size * classes).reshape(size, classes)

    def fixed_share(counts: np.ndarray) -> float:
        """The least, over the target values, of the share of its rows that lie in combinations
        of enough rows that hold that value only."""
        total = counts.sum(1)
        pure = (counts.max(1) == total) & (total >= _PAIRED_MIN_GROUP)
        return float((counts[pure].sum(0) / counts.sum(0)).min())

    # The columns are ranked on a sample (fewer rows than the pairs are judged on: a table of
    # thousands of columns is ranked in a fraction of a second); only the best are read in full.
    few = rows
    if len(rows) > _PAIRED_RANK_ROWS:
        few = np.sort(np.random.default_rng(1).choice(rows, _PAIRED_RANK_ROWS, replace=False))
    y_few, _ = pd.factorize(df[target].iloc[few])
    candidates = [
        c.name
        for c in columns
        if c.name != target
        and c.kind not in ("constant", "text")
        and 2 <= c.n_unique <= _PAIRED_MAX_VALUES
    ]
    sample = df[candidates].iloc[few]  # one take of the rows for all the columns
    ranked = []
    for name in candidates:
        if clock() - start > budget:
            return None, True
        code, _ = pd.factorize(sample[name], use_na_sentinel=False)
        size = int(code.max()) + 1
        if not 2 <= size <= _PAIRED_MAX_VALUES:
            continue
        counts = np.bincount(code * classes + y_few, minlength=size * classes).reshape(
            size, classes
        )
        total = counts.sum(1)
        p = counts / np.maximum(total[:, None], 1)
        entropy = -(np.where(p > 0, p * np.log(np.where(p > 0, p, 1.0)), 0.0)).sum(1)
        ranked.append((float((total * entropy).sum() / len(few)), name))
    ranked.sort()
    codes, alone = {}, {}
    for _, name in ranked[:_PAIRED_TOP]:
        code, _ = pd.factorize(df[name].iloc[rows], use_na_sentinel=False)
        size = int(code.max()) + 1
        if not 2 <= size <= _PAIRED_MAX_VALUES:
            continue
        codes[name] = (code.astype(np.int64), size)
        alone[name] = fixed_share(table(codes[name][0], size))
    for a, b in itertools.combinations(list(codes), 2):
        if clock() - start > budget:
            return None, True
        if alone[a] >= 1.0 or alone[b] >= 1.0:
            continue
        (ca, sa), (cb, sb) = codes[a], codes[b]
        share = fixed_share(table(ca * sb + cb, sa * sb))
        if share >= _PAIRED_SHARE:
            return PairedTarget(*sorted((a, b)), share), False
    return None, False


def leak_check(
    df: pd.DataFrame,
    columns: list[ColumnProfile],
    target: str,
    *,
    time_budget: float = 3.0,
    max_rows: int = 10_000,
    min_rows: int = 200,
    clock: Callable[[], float] = time.monotonic,
    derived: bool = True,
) -> LeakCheck:
    """Columns of ``df`` (profiled as ``columns``) that may reveal ``target``.

    The checks on the values run first: identical values, a value that determines the target,
    and a Pearson correlation of at least 0.99. Every other non-constant column then gets
    ``single_column_score`` on a deterministic sample of at most ``max_rows`` rows with a
    target (no score below ``min_rows``), and ``flag_scores`` picks the suspects. Columns are
    scored in profile order until ``time_budget`` seconds have passed; ``partial`` is then
    true. Each column is listed at most once, with its first reason. With ``derived`` the
    result also holds what ``derived_target`` and ``paired_target`` find (a training run does
    not look)."""
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
    found, cut = derived_target(df, columns, target) if derived else (None, False)
    paired, paired_cut = paired_target(df, columns, target) if derived else (None, False)
    return LeakCheck(suspects, partial, found, cut, paired, paired_cut)


def training_leak_suspects(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    columns: list[str] | None = None,
    time_budget: float = 3.0,
    max_rows: int = 10_000,
    clock: Callable[[], float] = time.monotonic,
) -> list[LeakSuspect]:
    """The columns of the features ``X`` that may reveal the target ``y`` (same rows), for a
    training run: ``leak_check`` on a deterministic sample of at most ``max_rows`` rows, of the
    ``columns`` given (all by default; picked after the sample, which is cheaper). Profiling the
    columns takes up to half of ``time_budget`` seconds (the columns not reached are not
    checked), the check the rest."""
    start = clock()
    if len(X) > max_rows:
        rows = np.sort(np.random.default_rng(0).choice(len(X), max_rows, replace=False))
        X, y = X.iloc[rows], y.iloc[rows]
    if columns is not None:
        X = X[columns]
    target = "target"
    while target in X.columns:
        target += "_"
    work = pd.concat([X.reset_index(drop=True), y.reset_index(drop=True).rename(target)], axis=1)
    profiles = []
    for name in X.columns:
        if clock() - start > time_budget / 2:
            break
        profiles.append(_profile_column(name, work[name]))
    check = leak_check(
        work, profiles, target, time_budget=time_budget - (clock() - start), derived=False
    )
    return check.suspects


def leak_suspects(df: pd.DataFrame, columns: list[ColumnProfile], target: str) -> list[LeakSuspect]:
    """``leak_check(...).suspects`` with the default budget."""
    return leak_check(df, columns, target).suspects


def profile_dataset(
    df: pd.DataFrame, target: str | None = None, *, sample_rows: int = 200_000, derived: bool = True
) -> DatasetProfile:
    """Profile ``df``; frames above ``sample_rows`` rows are sampled deterministically. With
    ``derived`` False the leak check does not look for a target computed from columns."""
    if target is not None and target not in df.columns:
        raise ValueError(f"target column '{target}' not found")
    work = df.sample(sample_rows, random_state=0) if len(df) > sample_rows else df
    columns = [_profile_column(name, work[name]) for name in work.columns]
    check = (
        leak_check(work, columns, target, derived=derived)
        if target is not None
        else LeakCheck([], False)
    )
    return DatasetProfile(
        n_rows=len(df),
        n_cols=df.shape[1],
        columns=columns,
        correlations=_correlations(work, columns),
        leak_suspects=check.suspects,
        leak_partial=check.partial,
        derived=check.derived,
        derived_cut=check.derived_cut,
        paired=check.paired,
        paired_cut=check.paired_cut,
    )
