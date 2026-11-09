"""Target checks and the feature preprocessing shared by all model families."""

import copy
import re
from typing import Literal

import numpy as np
import pandas as pd

from fione.data.frames import is_day_first, looks_like_dates, parse_datetimes
from fione.engine.config import ConfigError, TargetError
from fione.engine.events import Event, EventSink

Task = Literal["classification", "regression"]

HIGH_CARDINALITY = 200  # categorical columns with more categories are frequency encoded
MIN_ROWS = 10
LINEAR_LEVELS = 15  # categories one-hot encoded per column in the linear view (the most frequent)
LINEAR_CLIP = 5.0  # standardised numbers are clipped to +-this many standard deviations
LINEAR_SKEW = 2.0  # non-negative numbers more skewed than this are log-transformed in that view
PROSE_WORDS = 5  # a column whose median value has this many words is prose, not a label or name
# A shorter text is prose too when its values are mostly different and made of real words (a
# product title of four words): a label repeats, and the frequency of a title says nothing.
SHORT_PROSE_WORDS = 3
SHORT_PROSE_UNIQUE = 0.5  # share of different values in the column
SHORT_PROSE_WORD_CHARS = 3  # mean letters of a word, so that a code such as C_ID_92a is no text
MAX_PROSE = 3  # prose columns the text view reads (the first ones)
_LETTERS = re.compile(r"[^\W\d_]+")  # runs of letters, so a timestamp or a code has no words
# ordinal: seconds since the Unix epoch; the hour is added for columns that carry a time of day
_DATE_PARTS = ("year", "month", "day", "dayofweek", "ordinal")
_EPOCH = pd.Timestamp("1970-01-01")


def _is_categorical(s: pd.Series) -> bool:
    return pd.api.types.is_bool_dtype(s.dtype) or not pd.api.types.is_numeric_dtype(s.dtype)


def _holds_dates(s: pd.Series) -> bool:
    """Whether ``s`` is an object column of dates (a date-only column read from Parquet)."""
    return s.dtype == object and pd.api.types.infer_dtype(s, skipna=True) in ("date", "datetime")


def _as_str(s: pd.Series) -> pd.Series:
    """Values as strings, missing values kept missing."""
    return s.astype(str).where(s.notna())


def is_prose(s: pd.Series) -> bool:
    """Whether a string column holds text: the median value has ``PROSE_WORDS`` words (runs of
    letters, so a timestamp or a code is not prose), or ``SHORT_PROSE_WORDS`` words in values
    that are mostly different (``SHORT_PROSE_UNIQUE``, of the whole column) and have longer
    words than a code."""
    values = _as_str(s).dropna()
    first = values.head(1000)
    if not len(first):
        return False
    words = first.str.findall(_LETTERS.pattern)
    counts = words.str.len()
    if counts.median() >= PROSE_WORDS:
        return True
    if (
        counts.median() < SHORT_PROSE_WORDS
        or words.explode().str.len().mean() < SHORT_PROSE_WORD_CHARS
    ):
        return False
    # a label with hundreds of levels looks all different in 1,000 rows: count them in all
    return bool(values.nunique() >= SHORT_PROSE_UNIQUE * len(values))


def _holds_date_strings(s: pd.Series) -> bool:
    """Whether ``s`` is a column of strings that are dates (``2012-10-02 09:00``)."""
    strings = s.dtype == object or pd.api.types.is_string_dtype(s.dtype)
    return bool(strings and looks_like_dates(s.dropna(), need_year=True))


def _datetimes(s: pd.Series, dayfirst: bool = False) -> pd.Series:
    """``s`` as naive (UTC for tz-aware input) datetimes; unparseable values become NaT.
    ``dayfirst``: ``02-10-2012`` is the 2nd of October (found on the training data)."""
    if not pd.api.types.is_datetime64_any_dtype(s.dtype):
        s = parse_datetimes(s, dayfirst)
    if isinstance(s.dtype, pd.DatetimeTZDtype):
        s = s.dt.tz_convert("UTC").dt.tz_localize(None)
    return s


class Prep:
    """Turns raw feature frames into the inputs of each model family.

    ``fit`` decides per column: constant and all-null columns are dropped; datetime and date
    columns are expanded into numeric parts; bool and non-numeric columns become categoricals, or
    frequency encodings above ``HIGH_CARDINALITY`` categories (the share of the training rows
    with the value; a value not seen in training gets the share of the rarest one); everything
    else is numeric. The views put the features in ``feature_names`` order under positional
    names ``f0, f1, ...``, because model libraries reject some characters in feature names.
    ``groups`` (see ``fione.engine.features``) add derived numeric features after those; they are
    fitted on ``X`` alone and skipped when they read a column that is not used.
    """

    groups: tuple = ()  # class-level defaults: models pickled before these existed still load
    _logged: tuple = ()
    prose: tuple = ()
    dayfirst: tuple = ()  # date string columns that put the day before the month
    timed: tuple = ()  # date columns that carry a time of day
    _unseen: dict = {}  # frequency column -> share given to a value not seen in training (old: 0)
    _no_trend: tuple = ()  # view columns the linear view leaves out (see ``_fit_no_trend``)

    def fit(self, X: pd.DataFrame, groups=()) -> "Prep":
        self.dropped: list[str] = []
        self.dayfirst = ()
        self.timed = ()
        self._plan: list[
            tuple[str, str]
        ] = []  # (column, kind), kind: numeric/datetime/frequency/category
        self.categories: dict[str, list[str]] = {}
        self.frequencies: dict[str, dict[str, float]] = {}
        self._unseen = {}
        for column in X.columns:
            s = X[column]
            if s.nunique(dropna=False) <= 1:
                self.dropped.append(column)
            elif (
                pd.api.types.is_datetime64_any_dtype(s.dtype)
                or _holds_dates(s)
                or _holds_date_strings(s)
            ):
                self._plan.append((column, "datetime"))
                if is_day_first(s):
                    self.dayfirst += (column,)
                when = _datetimes(s, column in self.dayfirst)
                if (when.notna() & (when != when.dt.normalize())).any():
                    self.timed += (column,)
            elif _is_categorical(s):
                counts = _as_str(s).value_counts()
                if len(counts) > HIGH_CARDINALITY:
                    self.frequencies[column] = (counts / len(s)).to_dict()
                    self._unseen[column] = float(counts.min() / len(s))
                    self._plan.append((column, "frequency"))
                else:
                    self.categories[column] = sorted(counts.index)
                    self._plan.append((column, "category"))
            else:
                self._plan.append((column, "numeric"))
        if not self._plan:
            raise ConfigError("no usable feature columns: every column is empty or constant")
        self.prose = tuple(
            [c for c, kind in self._plan if kind in ("category", "frequency") and is_prose(X[c])][
                :MAX_PROSE
            ]
        )
        self.feature_names: list[str] = []
        # The input columns behind each feature; a derived one may have several.
        self.sources: list[tuple[str, ...]] = []
        self._category_at: dict[str, str] = {}  # view column -> categorical source column
        for column, kind in self._plan:
            if kind == "category":
                self._category_at[f"f{len(self.feature_names)}"] = column
            if kind == "datetime":
                parts = _DATE_PARTS + (("hour",) if column in self.timed else ())
                self.feature_names += [f"{column}__{part}" for part in parts]
                self.sources += [(column,)] * len(parts)
            else:
                self.feature_names.append(column)
                self.sources.append((column,))
        used = set(self.columns)
        self.groups = tuple(
            fitted
            for fitted in (copy.copy(g).fit(X) for g in groups if set(g.columns) <= used)
            if fitted.names
        )
        for group in self.groups:
            self.feature_names += group.names
            self.sources += group.sources
        base = self._base(X)
        numbers = base.drop(columns=list(self._category_at))
        self._medians = numbers.median().fillna(0.0).to_dict()
        self._fit_no_trend(base)
        self._fit_linear(base, numbers)
        return self

    def _fit_no_trend(self, base: pd.DataFrame) -> None:
        """The seconds-since-epoch part of a date column whose year is the same on every training
        row. Within one year it is a straight line through month and day, so a linear model
        splits the same effect between them in opposite weights. That holds on the training rows;
        on a date of the next year, where the month starts again, the weights add up to a
        prediction far outside the target's range. A time order of validation cannot show it,
        because the folds stay within the year."""
        off = []
        at = 0  # position of the column's first feature
        for column, kind in self._plan:
            if kind != "datetime":
                at += 1
                continue
            if base[f"f{at + _DATE_PARTS.index('year')}"].nunique() <= 1:
                off.append(f"f{at + _DATE_PARTS.index('ordinal')}")
            at += len(_DATE_PARTS) + (column in self.timed)
        self._no_trend = tuple(off)

    def _fit_linear(self, base: pd.DataFrame, numbers: pd.DataFrame) -> None:
        """What the linear view needs: number scales, the missing-value flags and the one-hot
        levels (``LINEAR_LEVELS`` most frequent, ties by name) per categorical column."""
        filled = numbers.fillna(self._medians)
        self._logged = tuple(
            p for p in filled.columns if numbers[p].min() >= 0 and numbers[p].skew() > LINEAR_SKEW
        )
        for position in self._logged:
            filled[position] = np.log1p(filled[position])
        self._scale = {
            position: (float(filled[position].mean()), float(filled[position].std() or 1.0))
            for position in filled.columns
            if position not in self._no_trend
        }
        self._flags = [p for p in base.columns if base[p].isna().any() and p not in self._no_trend]
        self._levels = {}
        for position in self._category_at:
            counts = base[position].value_counts()
            ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            self._levels[position] = [level for level, _ in ranked[:LINEAR_LEVELS]]

    @property
    def columns(self) -> list[str]:
        """The input columns the views need, in order."""
        return [column for column, _ in self._plan]

    def kind_of(self, column: str) -> Literal["numeric", "datetime", "category", "frequency"]:
        """How the model reads ``column``; ``KeyError`` for a column it does not use."""
        return dict(self._plan)[column]

    @property
    def numeric_columns(self) -> list[str]:
        """The input columns the model reads as numbers."""
        return [column for column, kind in self._plan if kind == "numeric"]

    def _base(self, df: pd.DataFrame) -> pd.DataFrame:
        """Numeric features as float, categorical ones as strings (NaN when missing)."""
        missing = [c for c, _ in self._plan if c not in df.columns]
        if missing:
            raise ConfigError(f"missing columns: {missing}")
        out: list[pd.Series] = []
        for column, kind in self._plan:
            s = df[column]
            if kind == "numeric":
                values = pd.to_numeric(s, errors="coerce").astype(float)
                out.append(values.replace([np.inf, -np.inf], np.nan))
            elif kind == "datetime":
                when = _datetimes(s, column in self.dayfirst)
                out += [when.dt.year, when.dt.month, when.dt.day, when.dt.day_of_week]
                out.append((when - _EPOCH).dt.total_seconds())
                if column in self.timed:
                    out.append(when.dt.hour.astype(float))
            elif kind == "frequency":
                values = _as_str(s)
                encoded = values.map(self.frequencies[column]).astype(float)
                # An unseen value gets the share of the rarest value in training: 0 would lie
                # outside the range the models were fitted on (a shift CV cannot see).
                unseen = self._unseen.get(column, 0.0)
                out.append(encoded.mask(encoded.isna() & values.notna(), unseen))
            else:
                out.append(_as_str(s))
        for group in self.groups:
            derived = group.transform(df)
            out += [derived[name] for name in derived.columns]
        frame = pd.concat([o.reset_index(drop=True) for o in out], axis=1)
        frame.columns = [f"f{i}" for i in range(len(self.feature_names))]
        frame.index = df.index
        for position in frame.columns:
            if position not in self._category_at:
                frame[position] = frame[position].astype(float)
        return frame

    def _categorical(self, base: pd.DataFrame) -> dict[str, pd.Categorical]:
        out = {}
        for position, column in self._category_at.items():
            categories = self.categories[column]
            values = base[position]
            out[position] = pd.Categorical(
                values.where(values.isin(categories)), categories=categories
            )
        return out

    def tree(self, df: pd.DataFrame) -> pd.DataFrame:
        """Categoricals as category dtype (unseen values become NaN), for LightGBM and XGBoost."""
        base = self._base(df)
        for position, values in self._categorical(base).items():
            base[position] = values
        return base

    def catboost(self, df: pd.DataFrame) -> pd.DataFrame:
        """Categoricals as object strings with ``"__na__"`` for missing values, for CatBoost."""
        base = self._base(df)
        for position in self._category_at:
            base[position] = base[position].fillna("__na__").astype(object)
        return base

    def dense(self, df: pd.DataFrame) -> pd.DataFrame:
        """All float: category codes (-1 when missing or unseen) and median-imputed numbers."""
        base = self._base(df)
        for position, values in self._categorical(base).items():
            base[position] = values.codes.astype(float)
        return base.fillna(self._medians)

    def text(self, df: pd.DataFrame) -> pd.DataFrame:
        """The linear view without the prose columns' frequencies, and after it each prose column
        as its text (``f3_t``; missing is empty), for models that read words. The frequency of a
        text says nothing but how often it was repeated."""
        out = self.linear(df)
        spots = {self.feature_names.index(column): column for column in self.prose}
        drop = [c for c in out.columns if int(c[1:].split("_")[0]) in spots]
        out = out.drop(columns=drop)
        for position, column in spots.items():
            out[f"f{position}_t"] = _as_str(df[column]).fillna("")
        return out

    def text_plain(self, df: pd.DataFrame) -> pd.DataFrame:
        """The text view without the columns of the derived features (``groups``)."""
        out = self.text(df)
        base = len(self.feature_names) - sum(len(group.names) for group in self.groups)
        return out[[c for c in out.columns if int(c[1:].split("_")[0]) < base]]

    @property
    def linear_width(self) -> int:
        """Columns of the linear view: one per number, one per kept level, one per flag."""
        levels = sum(len(found) for found in self._levels.values())
        return len(self._scale) + levels + len(self._flags)

    def linear(self, df: pd.DataFrame) -> pd.DataFrame:
        """For linear models: standardised, clipped numbers (``f3``), a 0/1 flag for each column
        that had missing values (``f3_na``) and one-hot levels of the categoricals (``f3_0``).
        The digits after ``f`` name the feature (position in ``feature_names``) a column
        derives from. Unseen and rare levels are all zeros."""
        base = self._base(df)
        base = base.drop(columns=list(self._no_trend))
        names = []
        for position in base.columns:
            if position in self._category_at:
                names += [f"{position}_{i}" for i in range(len(self._levels[position]))]
            else:
                names.append(position)
            if position in self._flags:
                names.append(f"{position}_na")
        out = np.zeros((len(base), len(names)))  # filled in place: one copy of the view
        at = {name: i for i, name in enumerate(names)}
        for position in base.columns:
            values = base[position]
            if position in self._category_at:
                for i, level in enumerate(self._levels[position]):
                    out[:, at[f"{position}_{i}"]] = values == level
            else:
                mean, std = self._scale[position]
                filled = values.fillna(self._medians[position])
                if position in self._logged:
                    filled = np.log1p(filled.clip(lower=0))
                scaled = (filled - mean) / std
                out[:, at[position]] = scaled.clip(-LINEAR_CLIP, LINEAR_CLIP)
            if position in self._flags:
                out[:, at[f"{position}_na"]] = values.isna()
        return pd.DataFrame(out, index=df.index, columns=names, copy=False)


def infer_task(y: pd.Series) -> Task:
    """Classification for non-numeric/bool targets and few integer values, else regression."""
    if _is_categorical(y):
        return "classification"
    values = y.dropna()
    distinct = values.nunique()
    if (
        len(values)
        and distinct <= 20
        and distinct / len(values) <= 0.05
        and bool((values % 1 == 0).all())
    ):
        return "classification"
    return "regression"


def too_many_classes(distinct: int, n_rows: int) -> bool:
    """Whether a target with ``distinct`` values in ``n_rows`` rows is refused for
    classification."""
    return distinct > max(100, 0.5 * n_rows)


def _sorted_labels(y: pd.Series) -> list:
    labels = [v.item() if isinstance(v, np.generic) else v for v in y.unique()]
    try:
        return sorted(labels)
    except TypeError:  # mixed types
        return sorted(labels, key=str)


def validate_target(
    y: pd.Series, task: Task, nfolds: int, emit: EventSink | None = None
) -> tuple[np.ndarray, list, int]:
    """Check the target and encode it for training.

    Returns ``(encoded, classes, nfolds)``: float values for regression, or class codes 0..k-1
    whose labels are ``classes`` (sorted; ``[]`` for regression); and the fold count reduced to
    min(nfolds, smallest class size, rows // 5), at least 2, emitting a ``notice`` event with
    ``nfolds_reduced_to`` and ``reason`` when it was reduced. ``task`` must already be resolved.
    """
    n = len(y)
    if n < MIN_ROWS:
        raise TargetError(
            f"not enough rows: {n} (at least {MIN_ROWS} are needed)", "few_rows", n=n, min=MIN_ROWS
        )
    missing = int(y.isna().sum())
    if missing:
        raise TargetError(
            f"target has missing values in {missing} rows; "
            "remove those rows or choose another column",
            "missing",
            n=missing,
        )
    distinct = y.nunique()
    if distinct < 2:
        raise TargetError(
            "target has a single distinct value; there is nothing to predict", "single_value"
        )
    limit, reason = n // 5, f"only {n} rows"
    if task == "regression":
        if _is_categorical(y):
            raise TargetError("target must be numeric for regression", "not_numeric")
        encoded = y.to_numpy(dtype=float)
        if not np.isfinite(encoded).all():
            raise TargetError("target has infinite values", "infinite")
        classes = []
    else:
        if too_many_classes(distinct, n):
            advice = "use regression or " if not _is_categorical(y) else ""
            raise TargetError(
                f"target has {distinct} distinct values, too many for classification; "
                f"{advice}choose another column",
                "too_many_classes",
                n=distinct,
            )
        classes = _sorted_labels(y)
        encoded = pd.Categorical(y, categories=classes).codes.astype(np.int64)
        counts = np.bincount(encoded)
        singles = [classes[i] for i in np.flatnonzero(counts == 1)]
        if singles:
            raise TargetError(
                f"class {singles[0]!r} has only 1 row ({len(singles)} such classes); "
                "each class needs at least 2 rows",
                "single_row_class",
                label=str(singles[0]),
                n=len(singles),
            )
        if counts.min() < limit:
            limit, reason = int(counts.min()), f"smallest class has {counts.min()} rows"
    folds = max(2, min(nfolds, limit))
    if folds < nfolds and emit is not None:
        message = f"nfolds reduced to {folds}: {reason}"
        emit(
            Event("notice", data={"message": message, "nfolds_reduced_to": folds, "reason": reason})
        )
    return encoded, classes, folds
