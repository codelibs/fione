"""A class score from a model of its own for every value of a column.

In some tables a column (a store, a sensor, a machine) selects which of the other columns tell
the classes apart, and how: for each value another handful of columns matters, and the classes
form clusters there that no global model can see. ``LevelDiscriminant`` fits, for each value of
that column, a regularised quadratic discriminant (a Gaussian per class, its covariance shrunk
towards a multiple of the identity) on the numeric columns, and gives each row the log likelihood
ratio of class 1 to class 0 under the model of its own value (the share of each class among the
rows of a value is left out: that is for the encodings of values).

Like ``ValueEncoding`` the group reads the target: the training rows get scores cross-fitted
over ``ENCODING_FOLDS`` folds (a row is scored by the model of its value fitted on the other
folds), any other rows the score of the model fitted on all the training rows, and a value the
training rows did not have (or had too few rows of) gets no score. A column is a candidate when
it has whole numbers or text with at least ``LEVEL_MIN_LEVELS`` values and
``LEVEL_ROWS_PER_LEVEL`` rows per value on the gate's sample; ``level_models`` screens it with a
cheap test on a sample of its values, which it passes when the cross-fitted scores of a model per
value reach an AUC of ``PRETEST_MIN_AUC`` and beat the scores of one model for all the rows of the
sample by ``PRETEST_MARGIN``. The fitted models of all the groups of a table together stay within
``MAX_MODEL_BYTES`` (a fitted group keeps one triangular factor per class and value), and the
fit within ``MAX_FIT_SECS`` and ``MAX_CELLS`` (the columns are cut to fit).

The gate of ``select_groups`` keeps a group early (``judged_early``) when its loss falls by
``DECISIVE_GAIN`` on the gate's own sample and again on folds no choice has seen. A group that
gains less stays in the pool and is judged last on up to ``ENCODING_ROWS`` rows, like
``ValueEncoding``, with the usual thresholds.
"""

import hashlib

import numpy as np
import pandas as pd
from scipy.linalg import solve_triangular
from sklearn.metrics import roc_auc_score

from fione.engine.features import (
    DECISIVE_GAIN,
    ENCODING_FOLDS,
    FINAL_REPEATS,
    GATE_REPEATS,
    Group,
    Verdict,
    _as_str,
    _number,
    _share,
    passes,
)
from fione.engine.prep import _whole_text
from fione.engine.search import make_folds

LEVEL_MIN_LEVELS = 30  # a column needs this many values, ...
LEVEL_ROWS_PER_LEVEL = 30  # ... and this many rows per value on the gate's sample on average
LEVEL_MIN_ROWS = 20  # rows a value needs (at least 5 of a class) to have a model of its own
LEVEL_MIN_CLASS_ROWS = 5
MAX_LEVEL_COLUMNS = 2  # columns kept, the most useful first
MAX_SCREENED_COLUMNS = 6  # columns screened (each takes about half a second)
MAX_LEVEL_FEATURES = 300  # numeric columns a model reads (the most useful first)
MIN_LEVEL_FEATURES = 3
MAX_MODEL_BYTES = (
    160e6  # of the fitted models of all the groups (4-byte triangles per class, value)
)
MAX_CELLS = 300_000_000  # rows times columns a fit holds at once (4 bytes each)
MAX_Z = 50.0  # standardised numbers are clipped to this, so no sum of products overflows
MAX_FIT_SECS = 20.0  # estimated seconds a fit on all the training rows may take
FLOPS_PER_SEC = 6e9  # what the estimate assumes (measured on a laptop: about 1.2e10 at 255 columns)
MAX_LOG_ODDS = 30.0
SHRINK_MIN, SHRINK_MAX = 0.05, 0.95
PRETEST_LEVELS = 30  # values the screen fits models for
PRETEST_ROWS_PER_LEVEL = 400
PRETEST_MARGIN = 0.05  # AUC a model per value must beat the one model for all rows by, at least
PRETEST_MIN_AUC = 0.55
LABEL = "per-value model scores of "


def _keys(s: pd.Series, numeric: bool | None = None) -> pd.Series:
    """The values of a column as labels: floats when it was a number (``numeric``; told by its
    type if None), text otherwise, and then a whole number as ``5`` whatever its type."""
    if numeric is None:
        numeric = pd.api.types.is_numeric_dtype(s)
    if numeric:
        return _number(s)
    if pd.api.types.is_numeric_dtype(s):
        return _as_str(s).where(~(_number(s) % 1 == 0), _whole_text(s))
    return _as_str(s)


def _shrink(rows: float, width: int) -> float:
    """How far a covariance is pulled to a multiple of the identity: the more columns there are
    per row, the further."""
    return float(np.clip(width / (width + rows), SHRINK_MIN, SHRINK_MAX))


def _factor(count: float, total: np.ndarray, scatter: np.ndarray):
    """(mean, lower Cholesky factor of the shrunk covariance) from the sums of a class's rows."""
    width = len(total)
    mean = total / count
    cov = scatter / count - np.outer(mean, mean)
    s = _shrink(count, width)
    cov = (1 - s) * cov + s * (np.trace(cov) / width + 1e-6) * np.eye(width)
    if not (np.isfinite(mean).all() and np.isfinite(cov).all()):
        raise np.linalg.LinAlgError("not finite")
    return mean, np.linalg.cholesky(cov)


def _log_density(z: np.ndarray, mean: np.ndarray, factor: np.ndarray) -> np.ndarray:
    """The log density of the rows ``z`` under a Gaussian, less its constant."""
    whitened = solve_triangular(factor, (z - mean).T, lower=True, check_finite=False)
    return -0.5 * (whitened**2).sum(0) - np.log(np.diag(factor)).sum()


def _log_odds(z, models) -> np.ndarray:
    """The log likelihood ratio of class 1 to class 0 for the rows ``z`` under ``models``, a pair
    of ``(mean, factor)``. The class shares of a value are left out: how often a value has a class
    is for the encodings of values (``ValueEncoding``, the codes), this says how the columns
    tell the classes apart there."""
    (m0, f0), (m1, f1) = models
    out = _log_density(z, m1, f1) - _log_density(z, m0, f0)
    return np.clip(out, -MAX_LOG_ODDS, MAX_LOG_ODDS)


def _models(stats):
    """Models from the sums of a value's rows, ``stats[k] = (count, total, scatter)`` per class,
    or ``None`` when a class has too few rows."""
    if min(stats[0][0], stats[1][0]) < LEVEL_MIN_CLASS_ROWS:
        return None
    try:
        return [_factor(*class_stats) for class_stats in stats]
    except np.linalg.LinAlgError:  # sums that are not finite: no model for this value
        return None


def _sums(z: np.ndarray, labels: np.ndarray):
    """(rows, column sums, sums of products) of ``z`` for each of the classes 0 and 1."""
    return [
        (float(m.sum()), z[m].sum(0), z[m].T @ z[m])
        if m.any()
        else (0.0, np.zeros(z.shape[1]), 0.0)
        for m in (labels == 0, labels == 1)
    ]


def fit_level(z: np.ndarray, labels: np.ndarray, folds: np.ndarray | None):
    """The models of one value fitted on all its rows (``None`` if a class has too few), and,
    with ``folds`` (a fold number per row), the scores of its rows cross-fitted over them
    (NaN where the other folds leave a class too few rows)."""
    parts = (
        [_sums(z[folds == f], labels[folds == f]) for f in range(folds.max() + 1)]
        if (folds is not None)
        else None
    )
    if parts is None:
        return _models(_sums(z, labels)), None
    whole = [tuple(sum(p[k][i] for p in parts) for i in range(3)) for k in (0, 1)]
    scores = np.full(len(z), np.nan)
    for f, held in enumerate(parts):
        rows = folds == f
        if not rows.any():
            continue
        left = [tuple(whole[k][i] - held[k][i] for i in range(3)) for k in (0, 1)]
        models = _models(left)
        if models is not None:
            scores[rows] = _log_odds(z[rows], models)
    return _models(whole), scores


class LevelDiscriminant(Group):
    """The log odds of class 1 under a regularised quadratic discriminant fitted on the rows of
    the row's own value of ``column``, over the numeric ``features``. Binary classification only
    (the labels are 0 and 1). The frame the group was fitted on (told by its fingerprint) gets the
    cross-fitted scores; any other frame gets the scores of the models of all the training rows,
    and a value without a model gets none. Missing numbers are read as the column's median."""

    uses_target = True
    _oof = None  # the training rows' cross-fitted scores; kept by no copy or pickle
    _seen = None  # (rows, hash of their values in order) the scores were computed for

    def __init__(self, column: str, features: list[str]):
        self.label = LABEL + column
        self.column = column
        self.features = tuple(features)
        self.columns = (column, *features)

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if k not in ("_oof", "_seen")}

    def _fingerprint(self, df: pd.DataFrame) -> tuple[int, str]:
        """The rows and the order of all their values: the same rows in another order are not the
        training rows, whose scores are by position."""
        mixed = np.zeros(len(df), dtype=np.uint64)
        columns = [_keys(df[self.column], self._numeric)] + [_number(df[c]) for c in self.features]
        with np.errstate(over="ignore"):
            for values in columns:
                mixed = mixed * np.uint64(1_000_003) + pd.util.hash_array(values.to_numpy())
        return len(df), hashlib.blake2b(mixed.tobytes(), digest_size=8).hexdigest()

    def _column(self, df: pd.DataFrame, at: int) -> np.ndarray:
        """A column's numbers, a missing one at the training median, standardised and clipped."""
        x = _number(df[self.features[at]]).to_numpy(float)
        x = np.where(np.isnan(x), self._median[at], x)
        with np.errstate(all="ignore"):
            return np.clip((x - self._median[at]) / self._scale[at], -MAX_Z, MAX_Z)

    def _matrix(self, df: pd.DataFrame) -> np.ndarray:
        """The features as a standardised matrix of 4-byte numbers, built column by column."""
        z = np.empty((len(df), len(self.features)), dtype=np.float32)
        for at in range(len(self.features)):
            z[:, at] = self._column(df, at)
        return z

    def _rows_of(self, df: pd.DataFrame) -> np.ndarray:
        """The index of each row's value among the training levels (-1: none)."""
        return pd.Index(self._levels).get_indexer(_keys(df[self.column], self._numeric))

    def _fit(self, X, y):
        y = np.asarray(y)
        self._numeric = bool(pd.api.types.is_numeric_dtype(X[self.column]))
        median, scale = [], []
        with np.errstate(all="ignore"):
            for c in self.features:
                x = _number(X[c]).to_numpy(float)
                found = x[~np.isnan(x)]
                at = float(np.median(found)) if len(found) else 0.0
                spread = float(np.std(found)) if len(found) else 0.0
                median.append(at if np.isfinite(at) else 0.0)
                scale.append(spread if np.isfinite(spread) and spread > 0 else 1.0)
        self._median, self._scale = np.array(median), np.array(scale)
        z = self._matrix(X)
        codes, levels = pd.factorize(_keys(X[self.column], self._numeric), sort=True)
        self._levels = levels.to_numpy()
        labels = y.astype(int)
        folds = np.empty(len(y), dtype=int)
        for f, (_, held) in enumerate(make_folds(labels, "classification", ENCODING_FOLDS, 0)):
            folds[held] = f
        oof = np.full(len(y), np.nan)
        order = np.argsort(codes, kind="stable")
        edges = np.searchsorted(codes[order], np.arange(len(levels) + 1))
        self._triangle = np.tril_indices(len(self.features))
        self._models = {}
        for level in range(len(levels)):
            rows = order[edges[level] : edges[level + 1]]
            if len(rows) < LEVEL_MIN_ROWS:
                continue
            whole, scores = fit_level(z[rows].astype(float), labels[rows], folds[rows])
            if whole is not None:  # the lower triangles, in float32: the size of the fitted group
                self._models[level] = [
                    (m.astype(np.float32), f[self._triangle].astype(np.float32)) for m, f in whole
                ]
            oof[rows] = scores
        self._sources = {f"{self.column}__level_score": self.columns}
        self._oof, self._seen = oof.astype(np.float32), self._fingerprint(X)

    def _square(self, packed: np.ndarray) -> np.ndarray:
        factor = np.zeros((len(self.features),) * 2)
        factor[self._triangle] = packed
        return factor

    def _compute(self, df):
        name = f"{self.column}__level_score"
        if self._oof is not None and self._fingerprint(df) == self._seen:
            return pd.DataFrame({name: self._oof}, index=df.index).astype(float)
        out = np.full(len(df), np.nan)
        where = self._rows_of(df)
        z = None
        for level in np.unique(where[where >= 0]):
            if level not in self._models:
                continue
            if z is None:
                z = self._matrix(df)
            rows = np.flatnonzero(where == level)
            models = [(m.astype(float), self._square(f)) for m, f in self._models[level]]
            out[rows] = _log_odds(z[rows].astype(float), models)
        return pd.DataFrame({name: out}, index=df.index)


def _estimated_secs(rows: int, levels: int, width: int) -> float:
    """What a fit on ``rows`` rows takes: the sums of products of each row, and a factor for each
    class and fold of each value."""
    flops = rows * width**2 + levels * (ENCODING_FOLDS + 1) * 2 * width**3 / 3
    return flops / FLOPS_PER_SEC


def _model_bytes(levels: int, width: int) -> int:
    """The size of the fitted models: a triangle of 4-byte numbers for each class and value."""
    return levels * 2 * (width * (width + 1) // 2) * 4


def _width(rows: int, levels: int, available: int, budget: float = MAX_MODEL_BYTES) -> int:
    """The most columns whose fit fits the time, the cell and the size (``budget``) limits."""
    width = min(available, MAX_LEVEL_FEATURES, MAX_CELLS // max(rows, 1))
    while width >= MIN_LEVEL_FEATURES and (
        _estimated_secs(rows, levels, width) > MAX_FIT_SECS or _model_bytes(levels, width) > budget
    ):
        width -= 1
    return width


def _screen(group: LevelDiscriminant, rows: pd.DataFrame, y: np.ndarray, seed: int) -> bool:
    """Whether models per value beat one model for all rows, by ``PRETEST_MARGIN`` of AUC, on
    the cross-fitted scores of a sample of ``PRETEST_LEVELS`` values (the same rows for both)."""
    keys = _keys(rows[group.column])
    counts = keys.value_counts()
    levels = counts[counts >= LEVEL_MIN_ROWS].index.to_numpy()
    if len(levels) < 2:
        return False
    rng = np.random.default_rng(seed)
    picked = rng.choice(levels, min(PRETEST_LEVELS, len(levels)), replace=False)
    take = []
    for level in picked:
        where = np.flatnonzero((keys == level).to_numpy())
        take.append(where[:PRETEST_ROWS_PER_LEVEL])
    take = np.sort(np.concatenate(take))
    sample = rows[list(group.columns)].iloc[take].reset_index(drop=True)
    labels = np.asarray(y)[take].astype(int)
    if labels.min() == labels.max():
        return False
    own = LevelDiscriminant(group.column, list(group.features)).fit(sample, labels)
    one = LevelDiscriminant(group.column, list(group.features))
    one.fit(sample.assign(**{group.column: 0.0}), labels)  # every row has the one value
    a, b = own._oof, one._oof
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 200 or labels[ok].min() == labels[ok].max():
        return False
    auc_own, auc_all = roc_auc_score(labels[ok], a[ok]), roc_auc_score(labels[ok], b[ok])
    return bool(auc_own >= PRETEST_MIN_AUC and auc_own - auc_all >= PRETEST_MARGIN)


def level_models(prep, X, y, ranked, all_rows, all_y, seed: int = 0) -> list[Group]:
    """The groups worth judging: for the columns of whole numbers or text with at least
    ``LEVEL_MIN_LEVELS`` values and ``LEVEL_ROWS_PER_LEVEL`` rows per value on ``X`` (at most
    ``MAX_LEVEL_COLUMNS``, the most useful first) that pass the screen of ``_screen`` on
    ``all_rows``. The numbers they read are the numeric columns, the most useful first, as many as
    the time, cell and size limits allow; the size limit is shared by all the groups."""
    order = {c: i for i, c in enumerate(ranked)}
    durations = set(prep.duration_columns)
    numbers = sorted(prep.numeric_columns, key=lambda c: order.get(c, len(order)))
    found: list[Group] = []
    screened = spent = 0  # columns screened; bytes the models of the groups found may take
    for column in sorted(prep.columns, key=lambda c: order.get(c, len(order))):
        if len(found) >= MAX_LEVEL_COLUMNS or screened >= MAX_SCREENED_COLUMNS:
            break
        kind = prep.kind_of(column)
        if kind == "datetime" or column in durations:
            continue
        values = X[column]
        if kind == "numeric" and not bool((_number(values).dropna() % 1 == 0).all()):
            continue
        levels = values.nunique()
        if levels < LEVEL_MIN_LEVELS or len(X) < LEVEL_ROWS_PER_LEVEL * levels:
            continue
        features = [c for c in numbers if c != column]
        counts = _keys(all_rows[column]).value_counts()
        full_levels = int((counts >= LEVEL_MIN_ROWS).sum())  # the values that get a model
        width = _width(len(all_rows), full_levels, len(features), MAX_MODEL_BYTES - spent)
        if width < MIN_LEVEL_FEATURES:
            continue
        group = LevelDiscriminant(column, features[:width])
        screened += 1
        if _screen(group, all_rows, all_y, seed):
            found.append(group)
            spent += _model_bytes(full_levels, width)
    return found


def judged_early(pool, base, kept, verdicts, gate) -> bool:
    """Keep the groups of ``pool`` that are models per value when they cut the loss on the gate's
    own sample by ``DECISIVE_GAIN`` of it, passing on one repeat of the folds and again on
    ``FINAL_REPEATS`` others that neither this nor the last check of the generic groups uses (the
    screen of ``level_models`` has picked them, so there is hardly a selection to correct for).
    A group kept goes into ``base`` too, so that the last check of the other groups is against
    it, and into ``kept``. The others stay in ``pool`` for the judgment on more rows. Returns
    whether a group was kept."""
    adopted = False
    for group in pool:
        if not isinstance(group, LevelDiscriminant):
            continue
        width = len(gate.fitted(group).names)
        if not width:
            continue
        before, after = gate.losses(kept, range(1)), gate.losses([*kept, group], range(1))
        gain = _share(before, after)
        if gain < DECISIVE_GAIN or not passes(before, after):
            continue
        start = GATE_REPEATS + FINAL_REPEATS  # the repeats after those of the generic groups
        fresh = range(start, start + FINAL_REPEATS)
        if passes(gate.losses(kept, fresh), gate.losses([*kept, group], fresh)):
            base.append(group)
            kept.append(group)
            verdicts.append(Verdict(group.label, width, True, gain, "adopted"))
            adopted = True
    return adopted
