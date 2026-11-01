"""Generic derived features, and the validation gate that decides which of them a model keeps.

A ``Group`` is a family of derived numeric features that read raw input columns: shape and
tokens of text columns, frequencies of categories, row-wise counts, date parts and differences,
pairwise arithmetic of numbers, group means, frequencies of category pairs. ``Prep.fit`` fits
the groups it is given on the training features alone, so they never see the target: a model
can be scored on out-of-fold predictions without leaking, however many groups exist.

What does use the target is the choice of groups. ``select_groups`` judges each candidate
group, in order, by what it adds to a small reference LightGBM on rows it samples: the group is
kept only when the loss drops over paired folds by more than ``GATE_Z`` standard errors and
``GATE_MIN_GAIN`` of the loss on average, with at least ``GATE_SHARE`` of the folds improving,
and the kept groups together pass a last check on other folds of the same rows. A few more
candidates cost little (a rejected group is dropped after one repeat of folds if it does not
help at all), and the whole gate is bounded by a deadline: groups not yet confirmed by the last
check when it runs out are not kept. The reference model does not sample columns, since that
would reward any added column. Groups, not single features, are judged, which limits the
number of comparisons. The folds
differ from the search's, but the rows are the same, so the cross-validation scores of the
search stay slightly optimistic; the report on the model lists every group's gain.

Derived features count for their source columns in importances and contributions: a feature
with several sources splits its share equally among them.
"""

import copy
import itertools
import re
from collections import Counter
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import log_loss

from fione.engine.config import Deadline
from fione.engine.families import n_threads
from fione.engine.prep import Prep, Task, _as_str, _datetimes
from fione.engine.search import make_folds

GATE_ROWS = 20_000  # rows the gate samples
GATE_FOLDS = 5
GATE_Z = 3.0  # standard errors of the paired fold-wise loss difference a group must clear
GATE_MIN_GAIN = 0.001  # and this share of the loss
GATE_SHARE = 0.7  # of the folds must improve
GATE_ROUNDS = 150  # of the reference model, a small and smooth one: fewer leaves, more shrinkage
GATE_SEED_OFFSET = 1000  # the gate's folds differ from the search's
GATE_SEED_SPACE = 2**31 - 1000  # keeps the folds' seeds (plus the repeat) valid for any seed
THREAD_ROWS = 5000  # below this the reference model runs on one thread: faster on small data
GATE_REPEATS = 3  # fold repeats a promising group is judged on
MAX_CANDIDATES = 40
CLUSTERS = 8
CLUSTER_ROWS = 20_000  # rows the clusters are fitted on
MAX_CLUSTER_COLUMNS = 10
TEXT_MIN_DISTINCT = 12  # string columns with fewer values are plain categories
TEXT_MIN_STRUCTURED = 0.2  # share of values with several words or letters mixed with digits
MAX_TEXT_COLUMNS = 6  # text columns that get groups (the most useful by rank)
MAX_REPEATED_VALUES = 10_000  # repeated values stored per column
TOKENS = 8  # tokens kept per text column
TOKEN_SUPPORT = 0.02  # share of the rows a token must occur in (and at least 5 rows)
MAX_PAIR_COLUMNS = 5  # numbers or dates combined pairwise
MAX_GROUP_CATEGORIES = 50  # levels of a category that group means are taken over
MIN_GROUP_ROWS = 5  # rows a level needs for its mean
_TOKEN = re.compile(r"[^\W\d_]+")  # runs of letters, so "C85" gives "c" and "PC 17599" gives "pc"


def _number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan)


class Group:
    """A family of derived features over ``columns``. Subclasses set ``label`` and ``columns``
    and implement ``_fit`` (learn from the training features, set ``_sources`` for every output
    name) and ``_compute`` (a float frame of those names). Outputs constant on the training
    rows are dropped."""

    label: str
    columns: tuple[str, ...]

    def fit(self, X: pd.DataFrame) -> "Group":
        self._fit(X)
        out = self._compute(X)
        self._keep = [name for name in out.columns if out[name].nunique(dropna=False) > 1]
        return self

    def _fit(self, X: pd.DataFrame) -> None:
        pass

    @property
    def names(self) -> list[str]:
        return self._keep

    @property
    def sources(self) -> list[tuple[str, ...]]:
        return [self._sources[name] for name in self._keep]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._compute(df)[self._keep]

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError


class TextShape(Group):
    """Length, word count, digit and capital shares and the first number of a text column."""

    def __init__(self, column: str):
        self.label, self.columns = f"text shape of {column}", (column,)

    def _fit(self, X):
        self._sources = {f"{self.columns[0]}__{part}": self.columns for part in self._PARTS}

    _PARTS = ("length", "words", "digit_share", "upper_share", "number")

    def _compute(self, df):
        column = self.columns[0]
        s = _as_str(df[column])
        length = s.str.len().astype(float)
        safe = length.where(length > 0)
        out = {
            "length": length,
            "words": s.str.count(r"\S+").astype(float),
            "digit_share": s.str.count(r"\d") / safe,
            "upper_share": s.str.count(r"[A-Z]") / safe,
            "number": pd.to_numeric(s.str.extract(r"(\d{1,15})")[0], errors="coerce"),
        }
        return pd.DataFrame({f"{column}__{k}": v.astype(float) for k, v in out.items()})


class TextTokens(Group):
    """0/1 flags for the letter runs (lower case) that occur in enough rows of a text column."""

    def __init__(self, column: str):
        self.label, self.columns = f"text tokens of {column}", (column,)

    @staticmethod
    def _sets(s: pd.Series) -> pd.Series:
        return s.str.findall(_TOKEN).map(
            lambda found: {t.lower() for t in found} if isinstance(found, list) else set()
        )

    def _fit(self, X):
        column = self.columns[0]
        sets = self._sets(_as_str(X[column]).dropna())
        counts = Counter(token for found in sets for token in found)
        floor = max(5, TOKEN_SUPPORT * len(sets))
        common = [(t, n) for t, n in counts.items() if floor <= n <= 0.98 * len(sets)]
        common.sort(key=lambda item: (-item[1], item[0]))
        self._tokens = [t for t, _ in common[:TOKENS]]
        self._sources = {f"{column}__has_{t}": self.columns for t in self._tokens}

    def _compute(self, df):
        column = self.columns[0]
        s = _as_str(df[column])
        sets = self._sets(s)
        missing = s.isna()
        out = {
            f"{column}__has_{t}": sets.map(lambda found, t=t: float(t in found)).where(~missing)
            for t in self._tokens
        }
        return pd.DataFrame(out, index=df.index).astype(float)


class CategoryFrequency(Group):
    """The share of the training rows with the same category, for each categorical column."""

    def __init__(self, columns: list[str]):
        self.label, self.columns = "frequencies of categories", tuple(columns)

    def _fit(self, X):
        self._shares = {
            c: _as_str(X[c]).value_counts(normalize=True).to_dict() for c in self.columns
        }
        self._sources = {f"{c}__frequency": (c,) for c in self.columns}

    def _compute(self, df):
        out = {}
        for c in self.columns:
            s = _as_str(df[c])
            share = s.map(self._shares[c]).astype(float)
            out[f"{c}__frequency"] = share.mask(share.isna() & s.notna(), 0.0)  # unseen: never seen
        return pd.DataFrame(out, index=df.index)


class RowCounts(Group):
    """How many of the columns are missing in a row, and how many numbers are zero."""

    def __init__(self, columns: list[str], numbers: list[str]):
        self.label, self.columns = "missing and zero counts per row", tuple(columns)
        self._numbers = list(numbers)

    def _fit(self, X):
        self._sources = {"missing_count": self.columns, "zero_count": tuple(self._numbers)}

    def _compute(self, df):
        out = {"missing_count": df[list(self.columns)].isna().sum(axis=1).astype(float)}
        zeros = (
            pd.concat([_number(df[c]) for c in self._numbers], axis=1) if self._numbers else None
        )
        out["zero_count"] = (zeros == 0).sum(axis=1).astype(float) if zeros is not None else 0.0
        return pd.DataFrame(out, index=df.index)


class DateParts(Group):
    """Hour, minute, week, quarter, day of the year and weekend flag of date columns."""

    _PARTS = ("hour", "minute", "week", "quarter", "dayofyear", "is_weekend")

    def __init__(self, columns: list[str]):
        self.label, self.columns = "more parts of dates", tuple(columns)

    def _fit(self, X):
        self._sources = {f"{c}__{p}": (c,) for c in self.columns for p in self._PARTS}

    def _compute(self, df):
        out = {}
        for c in self.columns:
            when = _datetimes(df[c])
            out[f"{c}__hour"] = when.dt.hour
            out[f"{c}__minute"] = when.dt.minute
            out[f"{c}__week"] = when.dt.isocalendar().week
            out[f"{c}__quarter"] = when.dt.quarter
            out[f"{c}__dayofyear"] = when.dt.day_of_year
            out[f"{c}__is_weekend"] = (when.dt.day_of_week >= 5).astype(float).where(when.notna())
        return pd.DataFrame(out, index=df.index).astype(float)


class DateDifferences(Group):
    """Seconds between each two date columns."""

    def __init__(self, columns: list[str]):
        self.label, self.columns = "differences between dates", tuple(columns)
        self._pairs = list(itertools.combinations(columns, 2))

    def _fit(self, X):
        self._sources = {f"{a} - {b}": (a, b) for a, b in self._pairs}

    def _compute(self, df):
        whens = {c: _datetimes(df[c]) for c in self.columns}
        out = {f"{a} - {b}": (whens[a] - whens[b]).dt.total_seconds() for a, b in self._pairs}
        return pd.DataFrame(out, index=df.index).astype(float)


class NumberPairs(Group):
    """One arithmetic operation over each two of a few number columns."""

    _OPS = {"sum": "+", "difference": "-", "product": "*", "ratio": "/"}

    def __init__(self, op: str, columns: list[str]):
        self.op, self._columns = op, list(columns)
        self.label, self.columns = f"{op} of numbers", tuple(columns)
        pairs = (
            itertools.permutations(columns, 2)
            if op == "ratio"
            else itertools.combinations(columns, 2)
        )
        self._names = {f"{a} {self._OPS[op]} {b}": (a, b) for a, b in pairs}

    def _fit(self, X):
        self._sources = self._names

    def _compute(self, df):
        numbers = {c: _number(df[c]) for c in self.columns}
        out = {}
        for name, (a, b) in self._names.items():
            x, y = numbers[a], numbers[b]
            if self.op == "sum":
                out[name] = x + y
            elif self.op == "difference":
                out[name] = x - y
            elif self.op == "product":
                out[name] = x * y
            else:
                out[name] = (x / y.where(y != 0)).replace([np.inf, -np.inf], np.nan)
        return pd.DataFrame(out, index=df.index).astype(float)


class GroupMeans(Group):
    """The mean of a number within a category, and the number minus that mean."""

    def __init__(self, categories: list[str], numbers: list[str]):
        self.label = "means of numbers within categories"
        self.columns = tuple(dict.fromkeys([*categories, *numbers]))
        self._pairs = [(c, n) for c in categories for n in numbers]

    def _fit(self, X):
        self._means, self._sources = {}, {}
        for c, n in self._pairs:
            frame = pd.DataFrame({"c": _as_str(X[c]), "n": _number(X[n])}).dropna()
            grouped = frame.groupby("c")["n"].agg(["mean", "size"])
            self._means[c, n] = grouped.loc[grouped["size"] >= MIN_GROUP_ROWS, "mean"].to_dict()
            self._sources[f"{n} mean by {c}"] = (c, n)
            self._sources[f"{n} minus mean by {c}"] = (c, n)

    def _compute(self, df):
        out = {}
        for c, n in self._pairs:
            mean = _as_str(df[c]).map(self._means[c, n]).astype(float)
            out[f"{n} mean by {c}"] = mean
            out[f"{n} minus mean by {c}"] = _number(df[n]) - mean
        return pd.DataFrame(out, index=df.index).astype(float)


class ValueFrequency(Group):
    """The share of the training rows that have exactly the same number (a fare shared by a
    family, a price point), for number columns that repeat their values."""

    def __init__(self, columns: list[str]):
        self.label, self.columns = "frequencies of repeated numbers", tuple(columns)

    def _fit(self, X):
        # Only values that repeat are stored, the most common ``MAX_REPEATED_VALUES`` of them;
        # every other value, seen once or not at all, gets the share of a single row.
        self._shares, self._single = {}, {}
        for c in self.columns:
            counts = _number(X[c]).value_counts()
            n = int(counts.sum())
            self._shares[c] = (counts[counts > 1].head(MAX_REPEATED_VALUES) / n).to_dict()
            self._single[c] = 1 / n if n else 0.0
        self._sources = {f"{c}__value_frequency": (c,) for c in self.columns}

    def _compute(self, df):
        out = {}
        for c in self.columns:
            values = _number(df[c])
            share = values.map(self._shares[c]).astype(float)
            out[f"{c}__value_frequency"] = share.mask(
                share.isna() & values.notna(), self._single[c]
            )
        return pd.DataFrame(out, index=df.index)


class ClusterDistances(Group):
    """The k-means cluster of a row over the (standardised) numbers and the distance to its
    centre; the clusters are fitted on at most ``CLUSTER_ROWS`` rows."""

    def __init__(self, columns: list[str]):
        self.label, self.columns = "clusters of numbers", tuple(columns)

    def _matrix(self, df):
        numbers = pd.concat([_number(df[c]) for c in self.columns], axis=1)
        values = numbers.to_numpy()
        values = np.where(np.isnan(values), self._center, values)
        return (values - self._center) / self._spread

    def _fit(self, X):
        numbers = pd.concat([_number(X[c]) for c in self.columns], axis=1)
        self._center = numbers.median().fillna(0.0).to_numpy()
        self._spread = numbers.std().replace(0.0, 1.0).fillna(1.0).to_numpy()
        sample = X.sample(min(len(X), CLUSTER_ROWS), random_state=0) if len(X) else X
        k = max(2, min(CLUSTERS, len(sample) // 20))
        self._kmeans = KMeans(n_clusters=k, n_init=3, random_state=0).fit(self._matrix(sample))
        self._sources = {"cluster": self.columns, "cluster_distance": self.columns}

    def _compute(self, df):
        if len(df) == 0:  # scikit-learn rejects empty input
            return pd.DataFrame(
                {"cluster": [], "cluster_distance": []}, index=df.index, dtype=float
            )
        matrix = self._matrix(df)
        distances = self._kmeans.transform(matrix)
        return pd.DataFrame(
            {
                "cluster": self._kmeans.predict(matrix).astype(float),
                "cluster_distance": distances.min(axis=1),
            },
            index=df.index,
        )


class CategoryPairs(Group):
    """The share of the training rows with the same pair of categories."""

    def __init__(self, columns: list[str]):
        self.label, self.columns = "frequencies of category pairs", tuple(columns)
        self._pairs = list(itertools.combinations(columns, 2))

    def _key(self, df, a, b):
        return _as_str(df[a]).fillna("\x00") + "\x1f" + _as_str(df[b]).fillna("\x00")

    def _fit(self, X):
        self._shares = {
            (a, b): self._key(X, a, b).value_counts(normalize=True).to_dict()
            for a, b in self._pairs
        }
        self._sources = {f"{a} x {b} frequency": (a, b) for a, b in self._pairs}

    def _compute(self, df):
        out = {
            f"{a} x {b} frequency": self._key(df, a, b)
            .map(self._shares[a, b])
            .astype(float)
            .fillna(0.0)
            for a, b in self._pairs
        }
        return pd.DataFrame(out, index=df.index)


def _repeats(s: pd.Series) -> bool:
    """Whether a number column has many distinct values of which some occur more than once."""
    values = _number(s).dropna()
    return 10 <= values.nunique() < 0.9 * len(values)


def _structured(s: pd.Series) -> bool:
    """Whether a string column has parts to read: values of several words, or letters mixed with
    digits (a name, a ticket, a cabin), not a single word that is only a category."""
    values = _as_str(s).dropna().head(1000)
    if values.nunique() < TEXT_MIN_DISTINCT:
        return False
    several = values.str.count(r"[^\W_]+") > 1
    mixed = values.str.contains(r"\d") & values.str.contains(r"[^\W\d_]")
    return bool((several | mixed).mean() >= TEXT_MIN_STRUCTURED)


def candidates(prep: Prep, X: pd.DataFrame, ranked: list[str]) -> list[Group]:
    """The groups worth judging for these columns, in the order the gate tries them.
    ``ranked`` lists the input columns, the most useful first, to pick the few that pairwise
    groups combine."""
    order = {column: i for i, column in enumerate(ranked)}
    columns = prep.columns

    def by_rank(cs):
        return sorted(cs, key=lambda c: order.get(c, len(order)))

    kinds = {c: prep.kind_of(c) for c in columns}
    strings = [c for c in columns if kinds[c] in ("category", "frequency")]
    text = [c for c in strings if _structured(X[c])]
    categories = by_rank(c for c in columns if kinds[c] == "category")
    small = [c for c in categories if X[c].nunique() <= MAX_GROUP_CATEGORIES]
    numbers = by_rank(prep.numeric_columns)[:MAX_PAIR_COLUMNS]
    dates = by_rank(c for c in columns if kinds[c] == "datetime")
    found: list[Group] = []
    for column in by_rank(text)[:MAX_TEXT_COLUMNS]:
        found += [TextTokens(column), TextShape(column)]
    if categories:
        found.append(CategoryFrequency(categories))
    found.append(RowCounts(columns, prep.numeric_columns))
    if dates:
        found.append(DateParts(dates))
    if len(dates) > 1:
        found.append(DateDifferences(dates[:MAX_PAIR_COLUMNS]))
    if small and numbers:
        found.append(GroupMeans(small[:3], numbers[:3]))
    if len(numbers) > 1:
        found += [NumberPairs(op, numbers) for op in NumberPairs._OPS]
    if len(small) > 1:
        found.append(CategoryPairs(small[:4]))
    repeated = [c for c in by_rank(prep.numeric_columns) if _repeats(X[c])]
    if repeated:
        found.append(ValueFrequency(repeated[:MAX_PAIR_COLUMNS]))
    cluster_columns = by_rank(prep.numeric_columns)[:MAX_CLUSTER_COLUMNS]
    if len(cluster_columns) > 1:
        found.append(ClusterDistances(cluster_columns))
    return found[:MAX_CANDIDATES]


def _loss(task: Task, y: np.ndarray, pred: np.ndarray, classes: int) -> float:
    if task == "regression":
        return float(np.sqrt(np.mean((y - pred) ** 2)))
    return float(log_loss(y, pred, labels=range(classes)))


class _OutOfTime(Exception):
    """The gate's deadline passed (or the run was cancelled) in the middle of a comparison."""


class _Gate:
    """Paired fold-wise losses of the reference model on a sample of the rows."""

    def __init__(self, X, y, task: Task, nfolds: int, seed: int, out_of_time=lambda: False):
        self.X, self.y, self.task, self.seed = X, y, task, seed
        self.out_of_time = out_of_time
        self._cache: dict[tuple, np.ndarray] = {}
        self.nfolds = max(2, min(GATE_FOLDS, nfolds))
        self.classes = int(y.max()) + 1 if task == "classification" else 0
        self.threads = 1 if len(X) < THREAD_ROWS else n_threads(len(X))
        self._folds: dict[int, list] = {}

    def folds(self, repeat: int):
        if repeat not in self._folds:
            self._folds[repeat] = make_folds(self.y, self.task, self.nfolds, self.seed + repeat)
        return self._folds[repeat]

    def _model(self):
        cls = lgb.LGBMClassifier if self.task == "classification" else lgb.LGBMRegressor
        return cls(
            n_estimators=GATE_ROUNDS,
            learning_rate=0.05,
            num_leaves=7,
            min_child_samples=20,
            reg_lambda=5.0,
            colsample_bytree=1.0,  # drawing columns would reward any added column
            subsample=0.8,
            subsample_freq=1,
            n_jobs=self.threads,
            random_state=self.seed,
            verbose=-1,
        )

    def losses(self, groups: list[Group], repeats: range) -> np.ndarray:
        """Fold losses with ``groups``, for each repeat of the folds; ``_OutOfTime`` when the
        deadline passes before they are all done. Results are kept per set of groups."""
        labels = tuple(g.label for g in groups)
        view = None
        out = []
        for repeat in repeats:
            if (labels, repeat) not in self._cache:
                if view is None:
                    view = Prep().fit(self.X, groups).tree(self.X)
                done = []
                for train, valid in self.folds(repeat):
                    if self.out_of_time():
                        raise _OutOfTime
                    model = self._model().fit(view.iloc[train], self.y[train])
                    if self.task == "regression":
                        pred = model.predict(view.iloc[valid])
                    else:
                        pred = np.zeros((len(valid), self.classes))
                        pred[:, model.classes_] = model.predict_proba(view.iloc[valid])
                    done.append(_loss(self.task, self.y[valid], pred, self.classes))
                self._cache[labels, repeat] = np.asarray(done)
            out.append(self._cache[labels, repeat])
        return np.concatenate(out)

    def ranked(self) -> list[str]:
        """Input columns by the gain of one reference fit on all sampled rows."""
        prep = Prep().fit(self.X)
        model = self._model().fit(prep.tree(self.X), self.y)
        gain = model.booster_.feature_importance(importance_type="gain")
        by_column = dict.fromkeys(prep.columns, 0.0)
        for value, sources in zip(gain, prep.sources, strict=True):
            for column in sources:
                by_column[column] += value / len(sources)
        return sorted(prep.columns, key=lambda c: -by_column[c])


def paired(before: np.ndarray, after: np.ndarray) -> tuple[float, float, float]:
    """(mean gain, standard error of it, share of folds that improved) of the fold losses."""
    diff = before - after
    n = len(diff)
    error = float(diff.std(ddof=1) / np.sqrt(n)) if n > 1 else float("inf")
    return float(diff.mean()), error, float((diff > 0).mean())


def passes(before: np.ndarray, after: np.ndarray, z: float = GATE_Z) -> bool:
    gain, error, share = paired(before, after)
    return gain > GATE_MIN_GAIN * float(before.mean()) and gain > z * error and share >= GATE_SHARE


@dataclass
class Verdict:
    group: str
    features: int
    adopted: bool
    gain: float  # share of the loss saved, over the sampled folds
    reason: str  # adopted, no gain, too small a gain, time or final check

    def to_dict(self) -> dict:
        return {
            "group": self.group,
            "features": self.features,
            "adopted": self.adopted,
            "gain": round(self.gain, 5),
            "reason": self.reason,
        }


def select_groups(
    X: pd.DataFrame,
    y: np.ndarray,
    task: Task,
    nfolds: int,
    seed: int,
    deadline: Deadline,
    should_stop=lambda: False,
) -> tuple[list[Group], list[Verdict]]:
    """The candidate groups worth keeping, and a verdict for every candidate tried."""
    if len(X) > GATE_ROWS:
        rows = _sample(y, task, seed)
        X, y = X.iloc[rows].reset_index(drop=True), y[rows]
    gate = _Gate(
        X,
        y,
        task,
        nfolds,
        (seed + GATE_SEED_OFFSET) % GATE_SEED_SPACE,
        lambda: deadline.expired() or should_stop(),
    )
    kept: list[Group] = []
    verdicts: list[Verdict] = []
    try:
        pool = candidates(Prep().fit(X), X, gate.ranked())
        current = gate.losses([], range(1))
        for group in pool:
            fitted = copy.copy(group).fit(X)
            width = len(fitted.names)
            if not width:
                verdicts.append(Verdict(group.label, 0, False, 0.0, "no varying feature"))
                continue
            trial = gate.losses([*kept, group], range(1))
            if paired(current, trial)[0] <= 0:  # no help at all: skip the other repeats
                verdicts.append(
                    Verdict(group.label, width, False, _share(current, trial), "no gain")
                )
                continue
            both = range(GATE_REPEATS)
            before, after = gate.losses(kept, both), gate.losses([*kept, group], both)
            gain = _share(before, after)
            if passes(before, after):
                kept.append(group)
                current = gate.losses(kept, range(1))
                verdicts.append(Verdict(group.label, width, True, gain, "adopted"))
            else:
                verdicts.append(Verdict(group.label, width, False, gain, "too small a gain"))
        if kept:
            fresh = range(GATE_REPEATS, GATE_REPEATS + 2)  # folds no choice has seen
            if not passes(gate.losses([], fresh), gate.losses(kept, fresh)):
                _drop_adopted(verdicts, "final check")
                kept = []
    except _OutOfTime:
        if kept:  # their last check did not finish: they are not trusted
            _drop_adopted(verdicts, "time")
            kept = []
        judged = {v.group for v in verdicts}
        verdicts += [Verdict(g.label, 0, False, 0.0, "time") for g in pool if g.label not in judged]
    return kept, verdicts


def _drop_adopted(verdicts: list[Verdict], reason: str) -> None:
    for verdict in verdicts:
        if verdict.adopted:
            verdict.adopted, verdict.reason = False, reason


def _sample(y: np.ndarray, task: Task, seed: int) -> np.ndarray:
    """Sorted positions of about ``GATE_ROWS`` rows; for classification each class keeps its
    share (and at least ``2 * GATE_FOLDS`` rows, or all of a smaller class)."""
    rng = np.random.default_rng(seed)
    if task == "regression":
        return np.sort(rng.choice(len(y), GATE_ROWS, replace=False))
    picked = []
    for label in np.unique(y):
        where = np.flatnonzero(y == label)
        keep = max(round(GATE_ROWS * len(where) / len(y)), min(len(where), 2 * GATE_FOLDS))
        picked.append(rng.choice(where, min(keep, len(where)), replace=False))
    return np.sort(np.concatenate(picked))


def _share(before: np.ndarray, after: np.ndarray) -> float:
    return float((before.mean() - after.mean()) / before.mean()) if before.mean() else 0.0
