"""Generic derived features, and the validation gate that decides which of them a model keeps.

A ``Group`` is a family of derived numeric features that read raw input columns: shape, tokens
and topics of text columns, how much two text columns share, frequencies of categories,
row-wise counts and statistics (also of a set of columns that hold the same kind of value),
date parts and differences, pairwise arithmetic of numbers, group means, frequencies of category
pairs and of pairs of repeated values, parts of structured identifiers, characters of codes, and
numeric columns whose whole numbers are labels
(``CodeLevels``, chosen by ``code_columns`` from the target means of their values, not by the
gate below).
``Prep.fit`` fits the groups it is given on the training features alone, so they never see the
target: a model can be scored on out-of-fold predictions without leaking, however many groups exist.
The one exception is ``ValueEncoding``, which reads the target and hands the training rows values
cross-fitted over folds (a row never sees its own target), while other rows get the rates of all
the training rows.

What does use the target is the choice of groups. ``select_groups`` judges each candidate
group, in order, by what it adds to a small reference LightGBM on rows it samples: the group is
kept only when the loss drops over paired folds by more than ``GATE_Z`` standard errors and
``GATE_MIN_GAIN`` of the loss on average, with at least ``GATE_SHARE`` of the folds improving,
and the kept groups together pass a last check on other folds of the same rows. A few more
candidates cost little (a rejected group is dropped after one repeat of folds if it does not
help at all), and the whole gate is bounded by a deadline: groups not yet confirmed by the last
check when it runs out are not kept, so the search stops judging groups while the time left
still covers that check. The frequencies of categories, of pairs and of repeated numbers are
fitted on all the training rows, not on the sample, and the columns that name an entity are looked
for in all of them: a sample of 20,000 rows of a table in which an entity occurs six times in
130,000 shows it once, so a frequency read from it would not be the one the model gets. That
reading is not bounded by the check's deadline; it takes seconds for a million rows. The reference
model does not sample columns, since that would reward any added column. Groups, not single
features, are judged, which limits the number of comparisons. The folds differ from the search's,
but the rows are the same, so the cross-validation scores of the search stay slightly optimistic;
the report on the model lists every group's gain. A group that reads the target needs more rows
than the gate samples to show its worth, so it is judged last, on up to ``ENCODING_ROWS`` rows.

Derived features count for their source columns in importances and contributions: a feature
with several sources splits its share equally among them.
"""

import copy
import hashlib
import itertools
import re
import time
import warnings
from collections import Counter
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import log_loss

from fione.data.frames import is_day_first
from fione.engine.config import Deadline
from fione.engine.families import n_threads
from fione.engine.prep import Prep, Task, _as_str, _datetimes, is_prose
from fione.engine.search import make_folds

GATE_ROWS = 20_000  # rows the gate samples
GATE_MIN_ROWS = 4_000  # fewest rows a short gate is cut down to
GATE_AFFORDED_REPEATS = 40  # fold repeats the time should cover: six judgments and a last check
GATE_FOLDS = 5
GATE_Z = 3.0  # standard errors of the paired fold-wise loss difference a group must clear
GATE_MIN_GAIN = 0.001  # and this share of the loss
GATE_SHARE = 0.7  # of the folds must improve
GATE_ROUNDS = 150  # of the reference model, a small and smooth one: fewer leaves, more shrinkage
GATE_SEED_OFFSET = 1000  # the gate's folds differ from the search's
GATE_SEED_SPACE = 2**31 - 1000  # keeps the folds' seeds (plus the repeat) valid for any seed
THREAD_ROWS = 5000  # below this the reference model runs on one thread: faster on small data
GATE_REPEATS = 3  # fold repeats a promising group is judged on
FINAL_REPEATS = 2  # fold repeats of the last check, which no choice has seen
FINAL_MARGIN = 1.5  # the time kept for the last check, over what its repeats took before
DECISIVE_GAIN = 0.05  # share of the loss a group saves to be kept when time ends the last check
MAX_CANDIDATES = 40
ENCODING_ROWS = 100_000  # rows the encodings of values are judged on: fewer show no gain
ENCODING_FOLDS = 5  # a training row's encoding is read from the other folds
ENCODING_SMOOTHING = 20.0  # rows' worth of the overall rate a value's own rate is pulled towards
ENCODING_MIN_LEVELS = 20  # a number needs this many distinct keys ...
ENCODING_ROWS_PER_KEY = 5  # ... and at least this many rows per key on average to be encoded
MAX_ENCODED_COLUMNS = 12  # numbers (the most useful by rank) whose values are encoded
CLUSTERS = 8
CLUSTER_ROWS = 20_000  # rows the clusters are fitted on
MAX_CLUSTER_COLUMNS = 10
TEXT_MIN_DISTINCT = 12  # string columns with fewer values are plain categories
TEXT_MIN_STRUCTURED = 0.2  # share of values with several words or letters mixed with digits
MAX_TEXT_COLUMNS = 6  # text columns that get groups (the most useful by rank)
MAX_PAIR_TEXTS = 3  # text columns compared pairwise (running texts first, then by rank)
PAIR_ROWS = 100_000  # rows whose words are held at a time while texts are compared
MAX_REPEATED_VALUES = 10_000  # repeated values stored per column
TOPICS = 32  # components of the word-weight matrix kept per prose column
TOPIC_WORDS = 30_000  # most frequent words the topics are read from
TOPIC_ROWS = 20_000  # rows the topics are fitted on
TOKENS = 8  # tokens kept per text column
TOKEN_SUPPORT = 0.02  # share of the rows a token must occur in (and at least 5 rows)
MAX_PAIR_COLUMNS = 5  # numbers or dates combined pairwise
STATISTIC_CELLS = 20_000_000  # cells the statistics are computed over at a time, to bound memory
MIN_STATISTIC_COLUMNS = 10  # numeric columns a row needs for statistics over them to mean much
SET_COLUMNS = (3, 12)  # fewest and most columns of a set of alike columns
SET_VALUES = 40  # most values (the span from the lowest to the highest) a set's columns take
MAX_SETS = 3  # sets of alike columns that get statistics
ID_DELIMITERS = (
    "_",
    "/",
    "-",
    ":",
    ".",
)  # what the fields of a structured identifier are joined by
ID_FIELDS = (2, 4)  # fewest and most fields of an identifier
ID_SHARE = 0.95  # of the values must split into the same number of fields
MAX_ID_COLUMNS = 2  # identifier columns that get parts
ID_UNIQUE = 0.5  # a field with more distinct values per row than this acts as a row index
ID_GROUPED = 0.9  # the first field gives a group size only when it has fewer distinct values
CODE_LENGTHS = (3, 32)  # fewest and most characters of a code
CODE_SHARE = 0.99  # of the values must have the length of the code
MAX_CODE_COLUMNS = 2  # code columns that get characters
MAX_CODE_POSITIONS = 16  # characters of a code read one by one
CODES_LABEL = "integer codes read as categories"
CODES_REASON = "by the order of their values"  # not by the gate: no gain is measured
CODE_MIN_LEVELS = 30  # a column of whole numbers is a candidate code with more levels than this ...
CODE_ROWS_PER_LEVEL = 3  # ... and at least this many rows per level on average
CODE_MIN_ROWS = 300  # fewer rows show no order
MAX_CODE_CANDIDATES = 100  # columns screened, the most useful first
CODE_BINS = 20  # equal-row parts of the numeric order, to see how much the order explains
CODE_Z = 4.0  # standard deviations the level means must differ from the overall mean by
CODE_ORDER_SHARE = 0.3  # a code has at most this share of that variation explained by the order
MAX_INTEGER_CODES = 10  # the ones the order explains least are read as codes
MAX_GROUP_CATEGORIES = 50  # levels of a category that group means are taken over
ENTITY_SHARE = (
    0.3  # of the rows must share their value with another row for a column to name entities
)
MAX_ENTITY_COLUMNS = 3  # such columns (the ones with the most levels) whose pairs are counted
MIN_GROUP_ROWS = 5  # rows a level needs for its mean
_WORD = re.compile(r"[^\W_]+")  # runs of letters and digits
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
    density = False  # the features count rows, so what a sample of the rows shows is thinner
    reads_as_codes = False  # names numeric columns whose whole numbers are labels (``CodeLevels``)
    uses_target = False  # reads the target too: fitted only when it is given (``ValueEncoding``)

    def fit(self, X: pd.DataFrame, y: np.ndarray | None = None) -> "Group":
        if self.uses_target:
            self._fit(X, y)
        else:
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


class TextPairs(Group):
    """How much two text columns share, for each pair of a few: words in common, their share of
    all the words and of the shorter text, the difference and ratio of the word counts, whether
    the first or the last word and the set of numbers are the same, and whether the words are
    equal. A tree model cannot compare two texts, but it can split on these."""

    _PARTS = (
        "common",
        "jaccard",
        "shorter_share",
        "words_diff",
        "words_ratio",
        "same_first",
        "same_last",
        "same_numbers",
        "equal",
    )

    def __init__(self, columns: list[str]):
        self.label, self.columns = "similarity of texts", tuple(columns)
        self._pairs = list(itertools.combinations(columns, 2))

    def _fit(self, X):
        self._sources = {f"{a} ~ {b}__{p}": (a, b) for a, b in self._pairs for p in self._PARTS}

    @staticmethod
    def _stats(one, other):
        a, b = set(one), set(other)
        common, union = len(a & b), len(a | b)
        longer = max(len(one), len(other))
        digits = lambda words: {w for w in words if w.isdigit()}  # noqa: E731
        return (
            common,
            common / max(union, 1),
            common / max(min(len(a), len(b)), 1),
            abs(len(one) - len(other)),
            min(len(one), len(other)) / max(longer, 1),
            one[:1] == other[:1],
            one[-1:] == other[-1:],
            digits(a) == digits(b),
            one == other,
        )

    def _compute(self, df):
        parts = [self._block(df.iloc[i : i + PAIR_ROWS]) for i in range(0, len(df), PAIR_ROWS)]
        return pd.concat(parts) if parts else self._block(df)

    def _block(self, df):
        # each column is read once, however many pairs it is in
        words = {c: _as_str(df[c]).str.lower().str.findall(_WORD) for c in self.columns}
        out = {}
        for a, b in self._pairs:
            stats = np.full((len(df), len(self._PARTS)), np.nan)
            for i, (one, other) in enumerate(zip(words[a], words[b], strict=True)):
                if isinstance(one, list) and isinstance(other, list):
                    stats[i] = self._stats(one, other)
            for i, part in enumerate(self._PARTS):
                out[f"{a} ~ {b}__{part}"] = stats[:, i]
        return pd.DataFrame(out, index=df.index)


class TextTopics(Group):
    """The main directions of word use in a prose column: the TF-IDF word weights of the column,
    reduced by a truncated SVD (latent semantic analysis) to ``TOPICS`` numbers. A tree model
    cannot read a sentence, but it can split on how much of a topic a text holds."""

    def __init__(self, column: str):
        self.label, self.columns = f"text topics of {column}", (column,)

    def _fit(self, X):
        column = self.columns[0]
        values = _as_str(X[column]).dropna()
        if len(values) > TOPIC_ROWS:
            values = values.sample(TOPIC_ROWS, random_state=0)
        self._topics = None
        try:
            vectorizer = TfidfVectorizer(
                sublinear_tf=True, min_df=3, max_features=TOPIC_WORDS, dtype=np.float32
            )
            weights = vectorizer.fit_transform(values)
        except ValueError:  # no words at all
            weights = None
        if weights is not None and min(weights.shape) > 2:
            size = min(TOPICS, min(weights.shape) - 1)
            self._topics = (vectorizer, TruncatedSVD(size, random_state=0).fit(weights))
        size = self._topics[1].n_components if self._topics else 0
        self._sources = {f"{column}__topic{i}": self.columns for i in range(size)}

    def _compute(self, df):
        column = self.columns[0]
        if self._topics is None:
            return pd.DataFrame(index=df.index)
        vectorizer, svd = self._topics
        s = _as_str(df[column])
        topics = svd.transform(vectorizer.transform(s.fillna("")))
        out = pd.DataFrame(topics.astype(float), index=df.index, columns=list(self._sources))
        out[s.isna().to_numpy()] = np.nan
        return out


class CategoryFrequency(Group):
    """The share of the training rows with the same category, for each categorical column; a
    category not seen in training gets the share of the rarest one."""

    density = True

    _unseen: dict = {}  # class-level default: groups pickled before it existed still load (0)

    def __init__(self, columns: list[str]):
        self.label, self.columns = "frequencies of categories", tuple(columns)

    def _fit(self, X):
        self._shares = {
            c: _as_str(X[c]).value_counts(normalize=True).to_dict() for c in self.columns
        }
        self._unseen = {c: min(shares.values(), default=0.0) for c, shares in self._shares.items()}
        self._sources = {f"{c}__frequency": (c,) for c in self.columns}

    def _compute(self, df):
        out = {}
        for c in self.columns:
            s = _as_str(df[c])
            share = s.map(self._shares[c]).astype(float)
            unseen = self._unseen.get(c, 0.0)
            out[f"{c}__frequency"] = share.mask(share.isna() & s.notna(), unseen)
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


class RowStatistics(Group):
    """Mean, median, maximum and standard deviation of a row's numbers, over those that are
    neither zero nor missing, after a signed log so that columns of different scales weigh alike
    (a row without any gets missing values)."""

    def __init__(self, numbers: list[str]):
        self.label, self.columns = "statistics of numbers per row", tuple(numbers)

    def _fit(self, X):
        self._sources = {
            f"{name}_nonzero": self.columns for name in ("mean", "median", "max", "std")
        }

    def _compute(self, df):
        step = max(1, STATISTIC_CELLS // len(self.columns))
        parts = [self._chunk(df.iloc[i : i + step]) for i in range(0, len(df), step)]
        return pd.concat(parts) if parts else self._chunk(df)

    def _chunk(self, df):
        values = np.column_stack([_number(df[c]).to_numpy() for c in self.columns])
        values = np.sign(values) * np.log1p(np.abs(values))
        values[values == 0] = np.nan
        with warnings.catch_warnings():  # a row of nothing but zeros and gaps
            warnings.simplefilter("ignore", RuntimeWarning)
            out = {
                "mean_nonzero": np.nanmean(values, axis=1),
                "median_nonzero": np.nanmedian(values, axis=1),
                "max_nonzero": np.nanmax(values, axis=1),
                "std_nonzero": np.nanstd(values, axis=1),
            }
        return pd.DataFrame(out, index=df.index)


class SetStatistics(Group):
    """How alike the values of a set of columns that hold the same kind of value are, row by
    row (the cards of a hand, dice, lottery numbers, ratings on one scale): how many distinct values
    the row has, how often the commonest and the second commonest value occur, the range, and
    the values in order. None of them depends on which column holds which value. A row with a
    missing value in the set gets missing features."""

    _KINDS = ("distinct values", "commonest count", "second commonest count", "range")

    def __init__(self, sets: list[list[str]]):
        self.label = "statistics of alike columns per row"
        self._sets = [tuple(columns) for columns in sets]
        self.columns = tuple(c for columns in self._sets for c in columns)

    @staticmethod
    def _name(columns):
        return f"{columns[0]}..{columns[-1]}"

    def _fit(self, X):
        self._sources = {}
        for columns in self._sets:
            name = self._name(columns)
            for kind in self._KINDS:
                self._sources[f"{name} {kind}"] = columns
            for i in range(len(columns)):
                self._sources[f"{name} value {i + 1} in order"] = columns

    def _compute(self, df):
        step = max(1, STATISTIC_CELLS // max(len(self.columns), 1))
        parts = [self._chunk(df.iloc[i : i + step]) for i in range(0, len(df), step)]
        return pd.concat(parts) if parts else self._chunk(df)

    def _chunk(self, df):
        out = {}
        for columns in self._sets:
            name = self._name(columns)
            values = np.column_stack([_number(df[c]).to_numpy() for c in columns])
            missing = np.isnan(values).any(axis=1)
            values = np.sort(np.where(missing[:, None], 0.0, values), axis=1)
            width = values.shape[1]
            starts = np.ones(values.shape, bool)  # where a run of equal values begins
            starts[:, 1:] = values[:, 1:] != values[:, :-1]
            # a run lasts until the next start, so its length is the distance to it
            at = np.where(starts, np.arange(width), width)
            following = np.full(values.shape, width)
            following[:, :-1] = at[:, 1:]
            next_start = np.minimum.accumulate(following[:, ::-1], axis=1)[:, ::-1]
            runs = np.sort(np.where(starts, next_start - np.arange(width), 0), axis=1)
            features = {
                "distinct values": starts.sum(axis=1),
                "commonest count": runs[:, -1],
                "second commonest count": runs[:, -2],
                "range": values[:, -1] - values[:, 0],
            }
            features |= {f"value {i + 1} in order": values[:, i] for i in range(width)}
            for kind, found in features.items():
                out[f"{name} {kind}"] = np.where(missing, np.nan, found.astype(float))
        return pd.DataFrame(out, index=df.index)


class DateParts(Group):
    """Hour, minute, week, quarter, day of the year and weekend flag of date columns; the day and
    the week of the year are left to the base view when it holds them."""

    _PARTS = ("hour", "minute", "week", "quarter", "dayofyear", "is_weekend")
    # class-level defaults: models pickled before them still load
    _dayfirst: frozenset = frozenset()
    _base_hours: frozenset = frozenset()
    _base_calendar: bool = False

    def __init__(self, columns: list[str], base_hours=(), base_calendar=False):
        """``base_hours``: the columns whose hour the base view already holds; ``base_calendar``:
        whether it holds the day and the week of the year of every date."""
        self.label, self.columns = "more parts of dates", tuple(columns)
        self._base_hours = frozenset(base_hours)
        self._base_calendar = base_calendar

    def _parts(self, column):
        return [
            p
            for p in self._PARTS
            if not (p == "hour" and column in self._base_hours)
            and not (p in ("week", "dayofyear") and self._base_calendar)
        ]

    def _fit(self, X):
        self._dayfirst = frozenset(c for c in self.columns if is_day_first(X[c]))
        self._sources = {f"{c}__{p}": (c,) for c in self.columns for p in self._parts(c)}

    def _compute(self, df):
        out = {}
        for c in self.columns:
            when = _datetimes(df[c], c in self._dayfirst)
            if "hour" in self._parts(c):
                out[f"{c}__hour"] = when.dt.hour
            out[f"{c}__minute"] = when.dt.minute
            if "week" in self._parts(c):
                out[f"{c}__week"] = when.dt.isocalendar().week
            out[f"{c}__quarter"] = when.dt.quarter
            if "dayofyear" in self._parts(c):
                out[f"{c}__dayofyear"] = when.dt.day_of_year
            out[f"{c}__is_weekend"] = (when.dt.day_of_week >= 5).astype(float).where(when.notna())
        return pd.DataFrame(out, index=df.index).astype(float)


class DateDifferences(Group):
    """Seconds between each two date columns."""

    _dayfirst: frozenset = frozenset()

    def __init__(self, columns: list[str]):
        self.label, self.columns = "differences between dates", tuple(columns)
        self._pairs = list(itertools.combinations(columns, 2))

    def _fit(self, X):
        self._dayfirst = frozenset(c for c in self.columns if is_day_first(X[c]))
        self._sources = {f"{a} - {b}": (a, b) for a, b in self._pairs}

    def _compute(self, df):
        whens = {c: _datetimes(df[c], c in self._dayfirst) for c in self.columns}
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

    density = True

    def __init__(self, columns: list[str]):
        self.label, self.columns = "frequencies of repeated numbers", tuple(columns)

    def _fit(self, X):
        # Only values that repeat are stored, the most common ``MAX_REPEATED_VALUES`` of them;
        # every other value, seen once or not at all, gets the share of the rarest value.
        self._shares, self._single = {}, {}
        for c in self.columns:
            counts = _number(X[c]).value_counts()
            n = int(counts.sum())
            self._shares[c] = (counts[counts > 1].head(MAX_REPEATED_VALUES) / n).to_dict()
            self._single[c] = int(counts.min()) / n if n else 0.0
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


def encoding_keys(columns: list[str], rows: pd.DataFrame) -> list[tuple[str, str]]:
    """The (column, kind) pairs of numbers worth encoding by value, read from ``rows``: the whole
    part of a number with fractions, and its value (to six decimals), each when it has at least
    ``ENCODING_MIN_LEVELS`` distinct keys and ``ENCODING_ROWS_PER_KEY`` rows per key on average."""
    keys = []
    for column in columns:
        x = _number(rows[column]).dropna()
        value = x.round(6)
        whole = np.floor(x)
        for kind, key in (("whole", whole), ("value", value)):
            if kind == "whole" and (whole == value).all():
                continue  # no fractions: the value is the whole part
            levels = key.nunique()
            if levels >= ENCODING_MIN_LEVELS and len(x) >= ENCODING_ROWS_PER_KEY * levels:
                keys.append((column, kind))
    return keys


class ValueEncoding(Group):
    """The rate (or mean) of the target among the rows that share a number's whole part or its
    value, smoothed towards the overall rate, for numbers whose values repeat. The frame the
    group was fitted on (told by its fingerprint) gets the rate of the other folds, never its
    own target; any other frame gets the rate of all the training rows, and so does a copy or a
    pickle of the fitted group, which do not keep the folds' values. Binary classification and
    regression only."""

    uses_target = True
    _oof = None  # (rows, features) of the training rows' cross-fitted values; kept by no copy
    _seen = None  # (rows, hash of their values in order) the encodings were computed for

    def __init__(self, keys: list[tuple[str, str]]):
        self.label = "target rates of number values"
        self.columns = tuple(dict.fromkeys(c for c, _ in keys))
        self._keys = list(keys)

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if k not in ("_oof", "_seen")}

    @staticmethod
    def _key(values: pd.Series, kind: str) -> np.ndarray:
        x = _number(values)
        return (np.floor(x) if kind == "whole" else x.round(6)).to_numpy()

    def _fingerprint(self, df: pd.DataFrame) -> tuple[int, str]:
        """The rows and the order of their values: the same rows in another order are not the
        training rows, whose encodings are by position."""
        numbers = pd.DataFrame({c: _number(df[c]) for c in self.columns})
        hashes = pd.util.hash_pandas_object(numbers, index=False).to_numpy()
        return len(df), hashlib.blake2b(hashes.tobytes(), digest_size=8).hexdigest()

    def _fit(self, X, y):
        y = np.asarray(y, dtype=float)
        self._prior = float(y.mean())
        task = "classification" if len(np.unique(y)) == 2 else "regression"
        folds = make_folds(y, task, ENCODING_FOLDS, 0)
        m, prior = ENCODING_SMOOTHING, self._prior
        self._rates, self._sources, names = [], {}, []
        oof = np.empty((len(X), len(self._keys)), dtype=np.float32)
        for i, (column, kind) in enumerate(self._keys):
            codes, levels = pd.factorize(self._key(X[column], kind))
            known = codes >= 0
            size = len(levels)
            count = np.bincount(codes[known], minlength=size)
            total = np.bincount(codes[known], weights=y[known], minlength=size)
            self._rates.append(pd.Series((total + prior * m) / (count + m), index=levels))
            oof[:, i] = prior
            for _, held in folds:
                c = codes[held]
                ok = c >= 0
                c = c[ok]
                n_c = np.bincount(c, minlength=size)
                s_c = np.bincount(c, weights=y[held][ok], minlength=size)
                oof[held[ok], i] = (total[c] - s_c[c] + prior * m) / (count[c] - n_c[c] + m)
            name = f"{column}__{kind}_target"
            names.append(name)
            self._sources[name] = (column,)
        self._names = names
        self._oof, self._seen = oof, self._fingerprint(X)

    def _compute(self, df):
        if self._oof is not None and self._fingerprint(df) == self._seen:
            return pd.DataFrame(self._oof, columns=self._names, index=df.index).astype(float)
        out = {}
        for (column, kind), rates, name in zip(self._keys, self._rates, self._names, strict=True):
            key = pd.Series(self._key(df[column], kind), index=df.index)
            out[name] = key.map(rates).astype(float).fillna(self._prior)
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
    """The share of the training rows with the same pair of categories; a pair not seen in
    training gets the share of the rarest one."""

    density = True

    _unseen: dict = {}  # class-level default: groups pickled before it existed still load (0)

    def __init__(self, columns: list[str], label: str = "frequencies of category pairs"):
        self.label, self.columns = label, tuple(columns)
        self._pairs = list(itertools.combinations(columns, 2))

    def _key(self, df, a, b):
        return _as_str(df[a]).fillna("\x00") + "\x1f" + _as_str(df[b]).fillna("\x00")

    def _fit(self, X):
        self._shares = {
            (a, b): self._key(X, a, b).value_counts(normalize=True).to_dict()
            for a, b in self._pairs
        }
        self._unseen = {
            pair: min(shares.values(), default=0.0) for pair, shares in self._shares.items()
        }
        self._sources = {f"{a} x {b} frequency": (a, b) for a, b in self._pairs}

    def _compute(self, df):
        out = {
            f"{a} x {b} frequency": self._key(df, a, b)
            .map(self._shares[a, b])
            .astype(float)
            .fillna(self._unseen.get((a, b), 0.0))
            for a, b in self._pairs
        }
        return pd.DataFrame(out, index=df.index)


class CodeLevels(Group):
    """Numeric columns whose whole numbers are labels (an account, a department): ``Prep`` reads
    each of them also as a category (see ``code_columns``). No feature of its own."""

    reads_as_codes = True

    def __init__(self, columns: list[str]):
        self.label, self.columns = CODES_LABEL, tuple(columns)

    def _compute(self, df):
        return pd.DataFrame(index=df.index)


def _order_share(x: np.ndarray, targets: np.ndarray) -> tuple[float, float]:
    """(how far the means of ``targets`` within each value of ``x`` differ beyond noise, in
    standard deviations; the share of that difference the order of the values explains). The
    first is a chi-square of the level means against the overall mean, less its degrees of
    freedom. The second is the same for ``CODE_BINS`` equal-row parts of the order: a measure
    (an age, a price) has neighbouring values alike, so the parts explain nearly all of it, a
    label's neighbours are unrelated and they explain none."""
    levels, found = np.unique(x, return_inverse=True)
    rows = np.bincount(found, minlength=len(levels)).astype(float)
    sums = np.stack(
        [np.bincount(found, weights=t, minlength=len(levels)) for t in targets.T], axis=1
    )
    mean, var = targets.mean(0), targets.var(0) + 1e-12
    k = targets.shape[1]

    def chi2(groups_sums, groups_rows):
        return float(
            (((groups_sums - groups_rows[:, None] * mean) ** 2) / groups_rows[:, None] / var).sum()
        )

    whole = chi2(sums, rows) - (len(levels) - 1) * k
    part = np.minimum((np.cumsum(rows) - rows) * CODE_BINS // rows.sum(), CODE_BINS - 1).astype(int)
    part_rows = np.bincount(part, weights=rows, minlength=CODE_BINS)
    used = part_rows > 0
    part_sums = np.stack(
        [np.bincount(part, weights=sums[:, j], minlength=CODE_BINS) for j in range(k)], axis=1
    )
    explained = chi2(part_sums[used], part_rows[used]) - (used.sum() - 1) * k
    # The chi-square of a level of ``n`` rows has variance 2 + kurtosis / n under the null, which
    # a rare 0/1 target makes far larger than 2 (its excess kurtosis is 1 / (p q) - 6).
    kurtosis = (((targets - mean) ** 2 / var) ** 2).mean(0) - 3
    spread = float(((2 + kurtosis[None, :] / rows[:, None]).clip(min=2)).sum())
    return whole / np.sqrt(spread), max(0.0, explained) / max(whole, 1e-9)


def code_columns(
    prep: Prep,
    X: pd.DataFrame,
    y: np.ndarray,
    task: Task,
    ranked: list[str] | None = None,
    out_of_time=lambda: False,
) -> list[str]:
    """Numeric columns of whole numbers that are labels, not measures. A candidate has more than
    ``CODE_MIN_LEVELS`` values with ``CODE_ROWS_PER_LEVEL`` rows each on average. It is a code
    when its values' target means differ beyond noise (``CODE_Z``) and the numeric order of the
    values explains at most ``CODE_ORDER_SHARE`` of that. The target is the rank for a regression,
    the 0/1 of each of the (at most ten most frequent) classes for a classification. At most
    ``MAX_INTEGER_CODES``, the ones the order explains least. Of the numeric columns, the first
    ``MAX_CODE_CANDIDATES`` in the order of ``ranked`` are screened, until ``out_of_time``."""
    if len(y) < CODE_MIN_ROWS:
        return []
    if task == "regression":
        ranks = pd.Series(y).rank().to_numpy()
        targets = ((ranks - ranks.mean()) / (ranks.std() + 1e-12))[:, None]
    else:
        top = pd.Series(y).value_counts().index[:10]
        targets = np.stack([(y == c).astype(float) for c in top], axis=1)
    found = []
    order = {column: i for i, column in enumerate(ranked or [])}
    screened = sorted(prep.numeric_columns, key=lambda c: order.get(c, len(order)))
    for column in screened[:MAX_CODE_CANDIDATES]:
        if column in prep.integer_dates:
            continue
        if out_of_time():
            break
        values = _number(X[column])
        have = values.notna().to_numpy()
        distinct = values.nunique()
        if not (
            CODE_MIN_LEVELS < distinct <= have.sum() / CODE_ROWS_PER_LEVEL
            and bool((values[have] % 1 == 0).all())
        ):
            continue
        z, share = _order_share(values.to_numpy()[have], targets[have])
        if z >= CODE_Z and share <= CODE_ORDER_SHARE:
            found.append((share, column))
    return [column for _, column in sorted(found)[:MAX_INTEGER_CODES]]


def _id_layout(s: pd.Series) -> tuple[str, int] | None:
    """The delimiter and the number of fields of a string column whose values are identifiers
    made of two to four fields ("0001_01", "B/0/P"): at least ``ID_SHARE`` of the values split
    into the same number of fields, and the values are not a handful of categories nor text
    (a name or a sentence has spaces)."""
    values = _as_str(s).dropna().head(1000)
    if values.nunique() < TEXT_MIN_DISTINCT or values.str.contains(r"\s").mean() > 1 - ID_SHARE:
        return None
    for delimiter in ID_DELIMITERS:
        sizes = (values.str.count(re.escape(delimiter)) + 1).value_counts(normalize=True)
        if ID_FIELDS[0] <= sizes.index[0] <= ID_FIELDS[1] and sizes.iloc[0] >= ID_SHARE:
            return delimiter, int(sizes.index[0])
    return None


class IdParts(Group):
    """The fields of structured identifiers (a group id and a member number joined by an
    underscore, a deck, number and side joined by slashes). For each field a number is read as
    one and any other field becomes how common its value is among the training rows; the first
    field also gives how many training rows share it (the size of the group). Fields that are
    nearly unique per row give nothing (the first gives a size unless it is almost unique). A
    value the training rows did not have gives a missing feature, never a count of zero. Values
    that do not split into the field count of the column are missing in every part."""

    def __init__(self, columns: list[str]):
        self.label, self.columns = "parts of identifiers", tuple(columns)

    @staticmethod
    def _fields(s: pd.Series, delimiter: str, n: int) -> list[pd.Series]:
        s = _as_str(s)
        rows = [v.split(delimiter) if isinstance(v, str) else [] for v in s]
        return [
            pd.Series(
                [r[i] or None if len(r) == n else None for r in rows], index=s.index, dtype=object
            )
            for i in range(n)
        ]

    def _fit(self, X):
        self._layouts, self._kinds, self._shares, self._sizes = {}, {}, {}, {}
        self._sources = {}
        for c in self.columns:
            layout = _id_layout(X[c])
            if layout is None:
                continue
            fields = self._fields(X[c], *layout)
            counts = [f.value_counts() for f in fields]
            # A field that is nearly unique per row (a running number) acts as a row index and
            # would fall out of range on new rows: it gives no feature, and the first field
            # gives only a size when it actually groups rows.
            unique = [len(k) > ID_UNIQUE * len(X) for k in counts]
            kinds = []
            for i, f in enumerate(fields):
                number = bool(f.notna().any()) and (
                    _number(f).notna().sum() >= ID_SHARE * f.notna().sum()
                )
                kinds.append(None if unique[i] else "number" if number else "share" if i else None)
            self._layouts[c], self._kinds[c] = layout, kinds
            self._shares[c] = [(k / k.sum()).to_dict() if len(k) else {} for k in counts]
            self._sizes[c] = counts[0].to_dict() if len(counts[0]) <= ID_GROUPED * len(X) else None
            for i, kind in enumerate(kinds):
                if kind == "number":
                    self._sources[f"{c}__part{i + 1}"] = (c,)
                elif kind:
                    self._sources[f"{c}__part{i + 1}_frequency"] = (c,)
            if self._sizes[c] is not None:
                self._sources[f"{c}__group_size"] = (c,)

    def _compute(self, df):
        out = {}
        for c, layout in self._layouts.items():
            fields = self._fields(df[c], *layout)
            for i, field in enumerate(fields):
                if self._kinds[c][i] == "number":
                    out[f"{c}__part{i + 1}"] = _number(field)
                elif self._kinds[c][i]:
                    out[f"{c}__part{i + 1}_frequency"] = field.map(self._shares[c][i])
            if self._sizes[c] is not None:
                out[f"{c}__group_size"] = fields[0].map(self._sizes[c])
        return pd.DataFrame(out, index=df.index).astype(float)


def _code_length(s: pd.Series) -> int | None:
    """The length of the values of a string column made of codes of one length ("QJIFGKBCCD"):
    at least ``CODE_SHARE`` of the values have it, it lies within ``CODE_LENGTHS``, and no value
    has a space."""
    values = _as_str(s.dropna().head(1000))
    if not len(values) or values.str.contains(r"\s").any():
        return None
    sizes = values.str.len().value_counts(normalize=True)
    length = int(sizes.index[0])
    if sizes.iloc[0] < CODE_SHARE or not CODE_LENGTHS[0] <= length <= CODE_LENGTHS[1]:
        return None
    return length


class CodeParts(Group):
    """The characters of codes of one length that are nearly unique per row (a string of ten
    letters that no other row shares): the character at each of the first ``MAX_CODE_POSITIONS``
    positions as a number (the rank among the characters of the training rows, so that a
    character they did not have is missing), the number of distinct characters, and how often the
    most repeated character occurs. A value of another length or a missing one is missing in
    every part."""

    def __init__(self, columns: list[str]):
        self.label, self.columns = "characters of codes", tuple(columns)

    @staticmethod
    def _points(s: pd.Series, length: int) -> tuple[np.ndarray, np.ndarray]:
        """The code points of the values of ``length`` characters (a row per value) and the
        rows of ``s`` that have them."""
        s = _as_str(s)
        rows = (s.str.len() == length).to_numpy()
        values = np.array(s[rows].tolist(), dtype=f"U{length}")
        return values.view(np.uint32).reshape(len(values), length), rows

    def _fit(self, X):
        self._lengths, self._alphabets, self._sources = {}, {}, {}
        for c in self.columns:
            length = _code_length(X[c])
            if length is None:
                continue
            self._lengths[c] = length
            self._alphabets[c] = np.unique(self._points(X[c], length)[0])
            positions = min(length, MAX_CODE_POSITIONS)
            for i in range(positions):
                self._sources[f"{c}__char{i + 1}"] = (c,)
            self._sources[f"{c}__distinct_chars"] = (c,)
            self._sources[f"{c}__most_repeated_char"] = (c,)

    def _compute(self, df):
        out = {}
        for c, length in self._lengths.items():
            points, rows = self._points(df[c], length)
            alphabet = self._alphabets[c]
            read = points[:, :MAX_CODE_POSITIONS]
            ranks = np.searchsorted(alphabet, read)
            seen = alphabet[np.minimum(ranks, len(alphabet) - 1)] == read
            ranks = np.where(seen, ranks, np.nan)
            ordered = np.sort(points, axis=1)
            run, longest = np.ones(len(points)), np.ones(len(points))
            for j in range(1, length):
                run = np.where(ordered[:, j] == ordered[:, j - 1], run + 1, 1)
                longest = np.maximum(longest, run)
            parts = {
                f"{c}__char{i + 1}": ranks[:, i] for i in range(min(length, MAX_CODE_POSITIONS))
            }
            parts[f"{c}__distinct_chars"] = 1 + (ordered[:, 1:] != ordered[:, :-1]).sum(axis=1)
            parts[f"{c}__most_repeated_char"] = longest
            for name, values in parts.items():
                column = np.full(len(df), np.nan)
                column[rows] = values
                out[name] = column
        return pd.DataFrame(out, index=df.index).astype(float)


def _repeats(s: pd.Series) -> bool:
    """Whether a number column has many distinct values of which some occur more than once."""
    values = _number(s).dropna()
    return 10 <= values.nunique() < 0.9 * len(values)


def _entity_key(s: pd.Series) -> bool:
    """Whether a column names entities that occur on several rows (a customer, a household): more
    levels than a small category has, and at least ``ENTITY_SHARE`` of the rows have a value that
    occurs again."""
    values = (s if pd.api.types.is_numeric_dtype(s) else _as_str(s)).dropna()
    if values.nunique() <= MAX_GROUP_CATEGORIES:
        return False
    return bool(values.duplicated(keep=False).mean() >= ENTITY_SHARE)


def _structured(s: pd.Series) -> bool:
    """Whether a string column has parts to read: values of several words, or letters mixed with
    digits (a name, a ticket, a cabin), not a single word that is only a category."""
    values = _as_str(s).dropna().head(1000)
    if values.nunique() < TEXT_MIN_DISTINCT:
        return False
    several = values.str.count(r"[^\W_]+") > 1
    mixed = values.str.contains(r"\d") & values.str.contains(r"[^\W\d_]")
    return bool((several | mixed).mean() >= TEXT_MIN_STRUCTURED)


def alike_columns(prep: Prep, X: pd.DataFrame, order: dict[str, int]) -> list[list[str]]:
    """Sets of ``SET_COLUMNS`` numeric columns that hold whole numbers over the same few values
    (the same lowest and highest, fewer than ``SET_VALUES`` apart): the cards of a hand, dice. At
    most ``MAX_SETS``, the ones with the most useful column first; a column keeps its place in
    the table within a set."""
    found: dict[tuple[float, float], list[str]] = {}
    for c in prep.numeric_columns:
        values = _number(X[c]).dropna()
        if len(values) == 0 or not (values % 1 == 0).all():
            continue
        low, high = float(values.min()), float(values.max())
        if 0 < high - low < SET_VALUES:
            found.setdefault((low, high), []).append(c)
    sets = [cs for cs in found.values() if SET_COLUMNS[0] <= len(cs) <= SET_COLUMNS[1]]
    sets.sort(key=lambda cs: min(order.get(c, len(order)) for c in cs))
    return sets[:MAX_SETS]


def candidates(
    prep: Prep, X: pd.DataFrame, ranked: list[str], all_rows: pd.DataFrame | None = None
) -> list[Group]:
    """The groups worth judging for these columns, in the order the gate tries them.
    ``ranked`` lists the input columns, the most useful first, to pick the few that pairwise
    groups combine. ``all_rows`` holds the rows ``X`` was sampled from: only the columns that name
    an entity, and the numbers whose values are encoded, are looked for in it, since a sample
    shows too few repeats of a value."""
    order = {column: i for i, column in enumerate(ranked)}
    columns = prep.columns

    def by_rank(cs):
        return sorted(cs, key=lambda c: order.get(c, len(order)))

    kinds = {c: prep.kind_of(c) for c in columns}
    durations = set(prep.duration_columns)  # the models read their days, not their words
    strings = [c for c in columns if kinds[c] in ("category", "frequency") and c not in durations]
    text = [c for c in strings if _structured(X[c])]
    categories = by_rank(c for c in columns if kinds[c] == "category" and c not in durations)
    small = [c for c in categories if X[c].nunique() <= MAX_GROUP_CATEGORIES]
    numbers = by_rank(prep.numeric_columns)[:MAX_PAIR_COLUMNS]
    dates = by_rank(c for c in columns if kinds[c] == "datetime")
    # The topics of prose come first: they are worth the most, and the gate may run out of time.
    found: list[Group] = [TextTopics(c) for c in by_rank(text)[:MAX_TEXT_COLUMNS] if is_prose(X[c])]
    # Running texts are compared first: their rank is low (nearly every value is unique), but
    # two of them are the pair worth comparing.
    running = [c for c in by_rank(text) if is_prose(X[c])]
    compared = (running + [c for c in by_rank(text) if c not in running])[:MAX_PAIR_TEXTS]
    pairs = TextPairs(compared) if len(compared) > 1 else None
    if pairs and len(running) > 1:
        found.append(pairs)  # worth more than the tokens and shapes after it
        pairs = None
    for column in by_rank(text)[:MAX_TEXT_COLUMNS]:
        found += [TextTokens(column), TextShape(column)]
    # Codes of one length that are nearly unique are frequency encoded and nothing else: their
    # characters come early, being worth more than the generic groups after them.
    codes = [
        c
        for c in by_rank(strings)
        if kinds[c] == "frequency" and _code_length(X[c]) and c not in text
    ]
    if codes:
        found.append(CodeParts(codes[:MAX_CODE_COLUMNS]))
    if categories:
        found.append(CategoryFrequency(categories))
    found.append(RowCounts(columns, prep.numeric_columns))
    if len(prep.numeric_columns) >= MIN_STATISTIC_COLUMNS:  # early: the gate may run out of time
        found.append(RowStatistics(prep.numeric_columns))
    if dates:
        found.append(DateParts(dates, prep.timed, prep.calendar))
    if len(dates) > 1:
        found.append(DateDifferences(dates[:MAX_PAIR_COLUMNS]))
    if small and numbers:
        found.append(GroupMeans(small[:3], numbers[:3]))
    if len(numbers) > 1:
        found += [NumberPairs(op, numbers) for op in NumberPairs._OPS]
    if len(small) > 1:
        found.append(CategoryPairs(small[:4]))
    # Columns that name an entity seen on several rows (an id, a surname, an amount that repeats
    # with it) identify it only together: how often the pair occurs is the size of the entity,
    # which neither column shows.
    seen = X if all_rows is None else all_rows
    entities = sorted(
        (
            c
            for c in columns
            if kinds[c] in ("category", "frequency", "numeric")
            and c not in durations
            and X[c].nunique() > MAX_GROUP_CATEGORIES
            and _entity_key(seen[c])
        ),
        key=lambda c: -seen[c].nunique(),
    )
    if len(entities) > 1:
        found.append(CategoryPairs(entities[:MAX_ENTITY_COLUMNS], "frequencies of repeated pairs"))
    repeated = [c for c in by_rank(prep.numeric_columns) if _repeats(X[c])]
    if repeated:
        found.append(ValueFrequency(repeated[:MAX_PAIR_COLUMNS]))
    encoded = encoding_keys(by_rank(prep.numeric_columns)[:MAX_ENCODED_COLUMNS], seen)
    if encoded:  # judged apart from the others, on more rows (see ``select_groups``)
        found.append(ValueEncoding(encoded))
    cluster_columns = by_rank(prep.numeric_columns)[:MAX_CLUSTER_COLUMNS]
    if len(cluster_columns) > 1:
        found.append(ClusterDistances(cluster_columns))
    if pairs:  # other texts (names, codes): after the rest, which it can then only delay
        found.append(pairs)
    identifiers = [c for c in by_rank(strings) if _id_layout(X[c])]
    if identifiers:  # last: the most specific, built only for data that has such a column
        found.append(IdParts(identifiers[:MAX_ID_COLUMNS]))
    sets = alike_columns(prep, X, order)
    if sets:  # last: it only helps a table of sets of alike columns, and the gate may run out
        found.append(SetStatistics(sets))
    return found[:MAX_CANDIDATES]


def _loss(task: Task, y: np.ndarray, pred: np.ndarray, classes: int) -> float:
    if task == "regression":
        return float(np.sqrt(np.mean((y - pred) ** 2)))
    return float(log_loss(y, pred, labels=range(classes)))


class _OutOfTime(Exception):
    """The gate's deadline passed (or the run was cancelled) in the middle of a comparison."""


class _Fitted:
    """A group of the gate's, whose fit on the gate's rows ``Prep.fit`` takes from the gate
    instead of repeating it: the topics of a long text cost seconds to fit."""

    def __init__(self, gate: "_Gate", group: Group):
        self.gate, self.group = gate, group
        self.label, self.columns = group.label, group.columns
        self.reads_as_codes, self.uses_target = group.reads_as_codes, group.uses_target

    def fit(self, X: pd.DataFrame, y: np.ndarray | None = None) -> Group:
        return self.gate.fitted(self.group)


class _Gate:
    """Paired fold-wise losses of the reference model on a sample of the rows."""

    def __init__(
        self,
        X,
        y,
        task: Task,
        nfolds: int,
        seed: int,
        out_of_time=lambda: False,
        groups=None,
        all_rows=None,
    ):
        self.X, self.y, self.task, self.seed, self.groups = X, y, task, seed, groups
        self.all_rows = X if all_rows is None else all_rows  # what groups that count rows read
        self.out_of_time = out_of_time
        self._cache: dict[tuple, np.ndarray] = {}
        self._fitted: dict[str, Group] = {}
        self._secs: dict[tuple, float] = {}  # seconds a repeat of the folds took, per set of groups
        self.nfolds = max(2, min(GATE_FOLDS, nfolds))
        if groups is not None:  # a sample may hold fewer groups than the run has
            self.nfolds = max(2, min(self.nfolds, len(np.unique(groups))))
        self.classes = int(y.max()) + 1 if task == "classification" else 0
        self.threads = 1 if len(X) < THREAD_ROWS else n_threads(len(X))
        self._folds: dict[int, list] = {}

    def folds(self, repeat: int):
        if repeat not in self._folds:
            self._folds[repeat] = make_folds(
                self.y, self.task, self.nfolds, self.seed + repeat, self.groups
            )
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

    def fitted(self, group: Group) -> Group:
        """``group`` fitted on the gate's rows, once however many views read it."""
        if group.label not in self._fitted:
            self._fitted[group.label] = copy.copy(group).fit(
                self.all_rows if group.density else self.X, self.y
            )
        return self._fitted[group.label]

    def losses(self, groups: list[Group], repeats: range) -> np.ndarray:
        """Fold losses with ``groups``, for each repeat of the folds; ``_OutOfTime`` when the
        deadline passes before they are all done. Results are kept per set of groups."""
        labels = tuple(g.label for g in groups)
        view = None
        out = []
        started, computed = time.monotonic(), 0
        for repeat in repeats:
            if (labels, repeat) not in self._cache:
                if view is None:
                    if self.out_of_time():
                        raise _OutOfTime
                    view = (
                        Prep().fit(self.X, [_Fitted(self, g) for g in groups], self.y).tree(self.X)
                    )
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
                computed += 1
                self._secs[labels] = (time.monotonic() - started) / computed
            out.append(self._cache[labels, repeat])
        return np.concatenate(out)

    def secs(self, groups: list[Group]) -> float:
        """What a repeat of the folds with ``groups`` takes: measured, or as long as the longest
        measured so far."""
        return self._secs.get(tuple(g.label for g in groups), max(self._secs.values(), default=0.0))

    def last_check_secs(self, groups: list[Group]) -> float:
        """What the last check of ``groups`` takes."""
        return FINAL_REPEATS * (self.secs([]) + self.secs(groups))

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
    columns: list[str] | None = None  # the input columns, for a group that is not judged by gain

    def to_dict(self) -> dict:
        out = {
            "group": self.group,
            "features": self.features,
            "adopted": self.adopted,
            "gain": round(self.gain, 5),
            "reason": self.reason,
        }
        return out if self.columns is None else {**out, "columns": self.columns}


def select_groups(
    X: pd.DataFrame,
    y: np.ndarray,
    task: Task,
    nfolds: int,
    seed: int,
    deadline: Deadline,
    should_stop=lambda: False,
    row_groups: np.ndarray | None = None,
) -> tuple[list[Group], list[Verdict]]:
    """The candidate groups worth keeping, and a verdict for every candidate tried. With
    ``row_groups`` (a group label per row) the gate's folds keep the rows of a group together,
    as the search's do."""

    def sampled(X, y, row_groups, size):
        rows = _sample(y, task, seed, size)
        return (
            X.iloc[rows].reset_index(drop=True),
            y[rows],
            None if row_groups is None else row_groups[rows],
        )

    all_rows, all_y = X, y
    encodes = row_groups is None and (task == "regression" or int(y.max()) <= 1)

    def new_gate(X, y, row_groups):
        return _Gate(
            X,
            y,
            task,
            nfolds,
            (seed + GATE_SEED_OFFSET) % GATE_SEED_SPACE,
            lambda: deadline.expired() or should_stop(),
            row_groups,
            all_rows,
        )

    if len(X) > GATE_ROWS:
        X, y, row_groups = sampled(X, y, row_groups, GATE_ROWS)
    gate = new_gate(X, y, row_groups)
    base: list[Group] = []  # the codes, which stay however the gate judges the others
    kept: list[Group] = []
    verdicts: list[Verdict] = []
    pool: list[Group] = []
    try:
        prep, ranked = Prep().fit(X), gate.ranked()
        pool = [g for g in candidates(prep, X, ranked, all_rows) if encodes or not g.uses_target]
        codes = (
            []
            if row_groups is not None
            else code_columns(prep, X, y, task, ranked, gate.out_of_time)
        )
        if codes:  # judged by the order of their values, not by the gate
            base.append(CodeLevels(codes))
            kept.append(base[0])
            verdicts.append(Verdict(CODES_LABEL, len(codes), True, 0.0, CODES_REASON, codes))
        current = gate.losses(kept, range(1))
        # When the time covers too few repeats of the folds to judge the groups, fewer rows do it
        # faster (a repeat takes about as long as the rows are many).
        afforded = deadline.remaining() / (GATE_AFFORDED_REPEATS * max(gate.secs([]), 1e-6))
        if afforded < 1 and len(X) > GATE_MIN_ROWS:
            X, y, row_groups = sampled(X, y, row_groups, max(GATE_MIN_ROWS, int(afforded * len(X))))
            gate = new_gate(X, y, row_groups)
            current = gate.losses(kept, range(1))
        for group in pool:
            if group.uses_target:
                continue  # judged last, on more rows
            # A group not kept for its gain alone must pass the last check, which time may not cut
            # short: the search stops once what is left covers that and one more group that
            # goes through all its repeats.
            unconfirmed = any(
                v.adopted and v.gain < DECISIVE_GAIN for v in verdicts if v.group != CODES_LABEL
            )
            if unconfirmed and deadline.remaining() < (
                FINAL_MARGIN * gate.last_check_secs(kept) + GATE_REPEATS * gate.secs(kept)
            ):
                break
            width = len(gate.fitted(group).names)
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
        if len(kept) > len(base):
            fresh = range(GATE_REPEATS, GATE_REPEATS + FINAL_REPEATS)  # folds no choice has seen
            if not passes(gate.losses(base, fresh), gate.losses(kept, fresh)):
                _drop_adopted(verdicts, "final check")
                kept = list(base)
        for group in pool:
            if group.uses_target:
                _judge_encoding(group, kept, verdicts, gate, new_gate, all_rows, all_y, deadline)
    except _OutOfTime:
        # Their last check did not finish. A gain this large is no fluke of the selection, so
        # those groups stay; the others are not trusted.
        decisive = {v.group for v in verdicts if v.adopted and v.gain >= DECISIVE_GAIN}
        kept = [g for g in kept if g.label in decisive or g in base]
        for verdict in verdicts:
            if verdict.adopted and verdict.group not in decisive and verdict.group != CODES_LABEL:
                verdict.adopted, verdict.reason = False, "time"
    judged = {v.group for v in verdicts}
    verdicts += [Verdict(g.label, 0, False, 0.0, "time") for g in pool if g.label not in judged]
    return kept, verdicts


def _judge_encoding(group, kept, verdicts, gate, new_gate, all_rows, all_y, deadline) -> None:
    """Judge a group that reads the target on up to ``ENCODING_ROWS`` rows (the gate's sample is
    too small for the rates of values to show a gain), against the groups kept so far, and keep
    it when it passes on the repeats of the folds and again on others. ``_OutOfTime`` leaves it
    unjudged."""
    wide = gate
    rows_wide = min(len(all_rows), ENCODING_ROWS)
    repeats = 2 * (1 + GATE_REPEATS + FINAL_REPEATS)  # with and without the group
    if gate.secs([]) * rows_wide / len(gate.X) * repeats > deadline.remaining():
        return  # not enough time left for the judgment: listed as not judged
    if len(gate.X) < rows_wide:
        rows = _sample(all_y, gate.task, gate.seed, rows_wide)
        wide = new_gate(all_rows.iloc[rows].reset_index(drop=True), all_y[rows], None)
    width = len(wide.fitted(group).names)
    try:
        if not width:
            verdicts.append(Verdict(group.label, 0, False, 0.0, "no varying feature"))
            return
        trial = wide.losses([*kept, group], range(1))
        if paired(wide.losses(kept, range(1)), trial)[0] <= 0:
            verdicts.append(
                Verdict(
                    group.label, width, False, _share(wide.losses(kept, range(1)), trial), "no gain"
                )
            )
            return
        both = range(GATE_REPEATS)
        before, after = wide.losses(kept, both), wide.losses([*kept, group], both)
        gain = _share(before, after)
        fresh = range(GATE_REPEATS, GATE_REPEATS + FINAL_REPEATS)
        if not passes(before, after):
            verdicts.append(Verdict(group.label, width, False, gain, "too small a gain"))
        elif not passes(wide.losses(kept, fresh), wide.losses([*kept, group], fresh)):
            verdicts.append(Verdict(group.label, width, False, gain, "final check"))
        else:
            kept.append(group)
            verdicts.append(Verdict(group.label, width, True, gain, "adopted"))
    except _OutOfTime:
        pass  # listed as not judged for lack of time


def _drop_adopted(verdicts: list[Verdict], reason: str) -> None:
    for verdict in verdicts:
        if verdict.adopted and verdict.group != CODES_LABEL:
            verdict.adopted, verdict.reason = False, reason


def _sample(y: np.ndarray, task: Task, seed: int, size: int | None = None) -> np.ndarray:
    """Sorted positions of about ``size`` rows; for classification each class keeps its
    share (and at least ``2 * GATE_FOLDS`` rows, or all of a smaller class). ``size`` is
    ``GATE_ROWS`` unless given."""
    size = size or GATE_ROWS
    rng = np.random.default_rng(seed)
    if task == "regression":
        return np.sort(rng.choice(len(y), size, replace=False))
    picked = []
    for label in np.unique(y):
        where = np.flatnonzero(y == label)
        keep = max(round(size * len(where) / len(y)), min(len(where), 2 * GATE_FOLDS))
        picked.append(rng.choice(where, min(keep, len(where)), replace=False))
    return np.sort(np.concatenate(picked))


def _share(before: np.ndarray, after: np.ndarray) -> float:
    return float((before.mean() - after.mean()) / before.mean()) if before.mean() else 0.0
