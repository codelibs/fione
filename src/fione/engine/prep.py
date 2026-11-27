"""Target checks and the feature preprocessing shared by all model families."""

import copy
import re
from typing import Literal

import numpy as np
import pandas as pd

from fione.data import frames
from fione.data.frames import is_day_first, looks_like_dates, parse_datetimes
from fione.engine.config import ConfigError, TargetError
from fione.engine.events import Event, EventSink

Task = Literal["classification", "regression"]

HIGH_CARDINALITY = 200  # categorical columns with more categories are frequency encoded
MIN_ROWS = 10
FILLED_SHARE = 0.8  # a column the model learned from filled in at least this share of rows ...
EMPTIED_BY = 0.5  # ... that is this much less filled in the rows to predict, is reported
MAX_DURATION_LEVELS = 5_000  # more different values than this are not durations
LINEAR_LEVELS = 15  # categories one-hot encoded per column in the linear view (the most frequent)
LINEAR_CLIP = 5.0  # standardised numbers are clipped to +-this many standard deviations
LINEAR_SKEW = 2.0  # non-negative numbers more skewed than this are log-transformed in that view
SPLINE_KNOTS = 7  # the splines view bends each number at this many of its quantiles
SPLINE_MIN_VALUES = 12  # a number needs more different values than this to get knots
SPLINE_COLUMNS = 40  # numbers bent in the splines view (the ones with the most values)
PROSE_WORDS = 5  # a column whose median value has this many words is prose, not a label or name
# A shorter text is prose too when its values are mostly different and made of real words (a
# product title of four words): a label repeats, and the frequency of a title says nothing.
SHORT_PROSE_WORDS = 3
SHORT_PROSE_UNIQUE = 0.5  # share of different values in the column
SHORT_PROSE_WORD_CHARS = 3  # mean letters of a word, so that a code such as C_ID_92a is no text
SPACED_PROSE = 0.5  # share of values with a space: words of one letter are text only if spaced
# ... and so is a short text that repeats (a search query) when it takes this many different
# values: a label has a few hundred at most, and a query is read by its words, not as a whole.
REPEATED_PROSE_VALUES = 1000
NOTATION_LENGTH = 15  # mean characters of a notation (a shorter value is a label or code)
NOTATION_LENGTH_VARIATION = 0.3  # std / mean of the lengths: an id or a hash has one length
NOTATION_UNIQUE = 0.9  # share of different values
MAX_PROSE = 3  # prose columns the text view reads (the first ones)
CONSOLIDATE_COLUMNS = 2_000  # a view of more columns is joined into few blocks (see _base)
FEW_LEVELS = (
    30  # a whole-number column with at most this many different values is also read as levels
)
MIN_FEW_LEVELS = 3  # ... and with at least this many (two values are a flag already)
MAX_LEVELS = 20_000  # values with a column of their own in the levels view, per input column
MAX_NATIVE_LEVELS = 1_000_000  # a frequency column with more values is no categorical to CatBoost
NATIVE_REPEAT = 0.9  # ... nor one with more values than this share of its rows (an id)
_LETTERS = re.compile(r"[^\W\d_]+")  # runs of letters, so a timestamp or a code has no words
CALENDAR = True  # whether a new Prep reads the day (1 to 366) and the week of the year of dates
# ordinal: seconds since the Unix epoch; the hour is added for columns that carry a time of day
_DATE_PARTS = ("year", "month", "day", "dayofweek", "dayofyear", "week", "ordinal")
_CALENDAR_PARTS = ("dayofyear", "week")  # the parts a Prep fitted before they were added lacks
_EPOCH = pd.Timestamp("1970-01-01")


def _date_part(when: pd.Series, part: str) -> pd.Series:
    """One part of the datetimes ``when`` as a float (missing for a missing date)."""
    if part == "ordinal":
        return (when - _EPOCH).dt.total_seconds()
    if part == "week":
        return when.dt.isocalendar().week.astype(float)
    attribute = {"dayofweek": "day_of_week", "dayofyear": "day_of_year"}.get(part, part)
    return getattr(when.dt, attribute).astype(float)


def _integer_date_parts(fmt: str, calendar: bool = True) -> tuple[str, ...]:
    """The parts of a whole-number date column besides the number itself: the day parts, and the
    hour when the format has one."""
    timed = "H" in fmt or fmt.startswith("unix")
    days = ("year", "month", "day", "dayofweek") + (_CALENDAR_PARTS if calendar else ())
    return days + (("hour",) if timed else ())


def _repeats(s: pd.Series) -> bool:
    """Whether the values of ``s`` come back (a search query), so that each is a level."""
    return s.nunique() < SHORT_PROSE_UNIQUE * s.notna().sum()


# A duration written as a number and a unit ("2 years", "3 weeks"), the unit's length in days.
_DURATION_DAYS = {
    "second": 1 / 86_400,
    "sec": 1 / 86_400,
    "minute": 1 / 1_440,
    "min": 1 / 1_440,
    "hour": 1 / 24,
    "hr": 1 / 24,
    "day": 1.0,
    "week": 7.0,
    "month": 30.4375,
    "year": 365.25,
    "yr": 365.25,
}
_DURATION = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(" + "|".join(_DURATION_DAYS) + r")s?\s*$", re.IGNORECASE
)
DURATION_SHARE = 0.95  # of the values, for a text column to be read as durations
MIN_DURATIONS = 3  # different values at least


def _holds_durations(s: pd.Series) -> bool:
    """Whether ``s`` is a text column of durations such as ``2 years`` or ``3 weeks``: at least
    ``MIN_DURATIONS`` different values, and ``DURATION_SHARE`` of the non-missing values read as
    one."""
    if not (s.dtype == object or pd.api.types.is_string_dtype(s.dtype)):
        return False
    values = s.dropna().astype(str)
    sample = values.iloc[:200]
    if len(sample) and sum(bool(_DURATION.match(v)) for v in sample) < 0.8 * len(sample):
        return False  # most of a text column fails on its first rows: skip the full count
    counts = values.value_counts()
    if len(counts) < MIN_DURATIONS or len(counts) > MAX_DURATION_LEVELS:
        return False
    fits = counts[[bool(_DURATION.match(v)) for v in counts.index]]
    return len(fits) >= MIN_DURATIONS and fits.sum() >= DURATION_SHARE * counts.sum()


def _duration_days(s: pd.Series) -> pd.Series:
    """``s`` as a number of days (missing where a value is not a duration)."""
    found = _as_str(s).str.extract(_DURATION)
    unit = found[1].str.lower().map(_DURATION_DAYS)
    days = pd.to_numeric(found[0], errors="coerce") * unit.astype(float)
    return days.astype(float)


def _is_categorical(s: pd.Series) -> bool:
    return pd.api.types.is_bool_dtype(s.dtype) or not pd.api.types.is_numeric_dtype(s.dtype)


INTEGER_DATE_FORMATS = (
    ("%Y%m%d", 8),
    ("%y%m%d%H", 8),
    ("%Y%m%d%H", 10),
    ("%Y%m%d%H%M%S", 14),
)
INTEGER_DATE_MIN_VALUES = 10  # different values; a few are codes, not a clock
INTEGER_DATE_SAMPLE = 2_000
# Unix time of 2000-01-01 and of 2100-01-01, in seconds: whole numbers between them may be a clock,
# if they span no more than 50 years (ids spread over the whole range are not one)
UNIX_SECONDS = (946_684_800, 4_102_444_800)
UNIX_MAX_SPAN = 50 * 365 * 86_400


def integer_date_format(s: pd.Series) -> str | None:
    """The format (``%Y%m%d``, ``%y%m%d%H``, ``%Y%m%d%H``, ``%Y%m%d%H%M%S``) when ``s`` holds whole
    numbers that all read as dates in it, such as 20141021, 14102100 or 20141021153045;
    ``unix_s`` or ``unix_ms`` when they all lie between 2000 and 2100 as seconds or milliseconds
    since 1970; ``None`` when it does not."""
    if not (pd.api.types.is_integer_dtype(s.dtype) and not pd.api.types.is_bool_dtype(s.dtype)):
        return None
    values = s.dropna().astype("int64")
    if not len(values):
        return None
    low, high = int(values.min()), int(values.max())
    unix = next(
        (
            name
            for name, scale in (("unix_s", 1), ("unix_ms", 1000))
            if UNIX_SECONDS[0] * scale <= low
            and high <= UNIX_SECONDS[1] * scale
            and high - low <= UNIX_MAX_SPAN * scale
        ),
        None,
    )
    if low < 10_000_000 or (high >= 100_000_000_000_000 and unix is None):
        return None  # most integer columns end here, at the cost of two scans
    if len(values) > INTEGER_DATE_SAMPLE:
        values = values.sample(INTEGER_DATE_SAMPLE, random_state=0)
    if values.nunique() < INTEGER_DATE_MIN_VALUES:
        return None
    text = values.astype(str)
    for fmt, digits in INTEGER_DATE_FORMATS:
        if (text.str.len() == digits).all() and pd.to_datetime(
            text, format=fmt, errors="coerce"
        ).notna().all():
            if fmt == "%Y%m%d" and not values.between(19000101, 21001231).all():
                continue
            if digits == 14 and not values.between(19000101000000, 21001231235959).all():
                continue
            return fmt
    return unix


def _integer_dates(s: pd.Series, fmt: str) -> pd.Series:
    """Whole numbers ``s`` read as datetimes in ``fmt`` (a name from ``integer_date_format``);
    NaT where a value is missing, not whole or not a date. Each different value is read once."""
    numbers = pd.to_numeric(s, errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan)
    codes, values = pd.factorize(numbers)
    when = pd.Series(pd.NaT, index=range(len(values)), dtype="datetime64[ns]")
    if fmt.startswith("unix"):
        when[:] = pd.to_datetime(values, unit="s" if fmt == "unix_s" else "ms", errors="coerce")
    else:
        whole = values % 1 == 0
        text = pd.Series(values[whole].astype("int64")).astype(str)
        when[whole] = pd.to_datetime(text, format=fmt, errors="coerce").to_numpy()
    out = when.reindex(codes)  # -1, a missing value, is no label: NaT
    out.index = s.index
    return out


def _holds_dates(s: pd.Series) -> bool:
    """Whether ``s`` is an object column of dates (a date-only column read from Parquet)."""
    return s.dtype == object and pd.api.types.infer_dtype(s, skipna=True) in ("date", "datetime")


def _has_few_levels(s: pd.Series, kind: str) -> bool:
    """Whether a numeric column holds a few whole numbers (a day of the week, a month, a score)."""
    if kind != "numeric" or pd.api.types.is_bool_dtype(s) or not pd.api.types.is_numeric_dtype(s):
        return False
    values = s.dropna()
    return MIN_FEW_LEVELS <= values.nunique() <= FEW_LEVELS and bool((values % 1 == 0).all())


def _whole(s: pd.Series) -> bool:
    """Whether every value of the column is a whole number (missing ones aside)."""
    values = pd.to_numeric(s, errors="coerce").dropna()
    return bool((values % 1 == 0).all())


def _whole_text(s: pd.Series) -> pd.Series:
    """Whole numbers as text (``5``, not ``5.0``), missing, infinite or huge ones missing."""
    values = pd.to_numeric(s, errors="coerce")
    values = values.where(values.abs() < 2**53).round().astype("Int64")
    return values.astype(str).where(values.notna())


def _as_str(s: pd.Series) -> pd.Series:
    """Values as strings, missing values kept missing."""
    return s.astype(str).where(s.notna())


def is_notation(s: pd.Series) -> bool:
    """Whether a string column holds a notation (a SMILES molecule, a DNA or protein sequence):
    values mostly different, without spaces and of varying length (an id has one length). Its
    character n-grams carry the signal, but the values are no words."""
    values = _as_str(s).dropna()
    first = values.head(1000)
    if len(first) < MIN_ROWS or first.str.contains(r"\s").mean() > 0.05:
        return False
    length = first.str.len()
    if length.mean() < NOTATION_LENGTH or length.std() < NOTATION_LENGTH_VARIATION * length.mean():
        return False
    return bool(values.nunique() >= NOTATION_UNIQUE * len(values))


def is_prose(s: pd.Series) -> bool:
    """Whether a string column holds text: the median value has ``PROSE_WORDS`` words (runs of
    letters, so a timestamp or a code is not prose; nor is a hex id, whose runs are short and
    have no spaces between them), or ``SHORT_PROSE_WORDS`` words in values
    that are mostly different (``SHORT_PROSE_UNIQUE``, of the whole column) or take
    ``REPEATED_PROSE_VALUES`` different values, and have longer words than a code."""
    values = _as_str(s).dropna()
    first = values.head(1000)
    if not len(first):
        return False
    if is_notation(s):
        return True
    words = first.str.findall(_LETTERS.pattern)
    counts = words.str.len()
    # a hex id has as many runs of letters as a sentence has words, but runs of a letter or two
    # and no spaces between them
    spaced = first.str.contains(r"\s").mean() >= SPACED_PROSE
    if counts.median() >= PROSE_WORDS and (
        spaced or words.explode().str.len().mean() >= SHORT_PROSE_WORD_CHARS
    ):
        return True
    if (
        counts.median() < SHORT_PROSE_WORDS
        or words.explode().str.len().mean() < SHORT_PROSE_WORD_CHARS
    ):
        return False
    # a label with hundreds of levels looks all different in 1,000 rows: count them in all
    different = values.nunique()
    return bool(different >= SHORT_PROSE_UNIQUE * len(values) or different >= REPEATED_PROSE_VALUES)


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


TREND_CARRIER_CORR = 0.8  # rank correlation with the time column of an input that moves with it
TREND_SAMPLE_ROWS = 20_000


def _time_numbers(s: pd.Series) -> pd.Series:
    """A column as numbers that grow with time: the numbers themselves, else its dates as seconds
    (NaN where a value is neither)."""
    numbers = pd.to_numeric(s, errors="coerce")
    if numbers.notna().mean() >= 0.9:
        return numbers.astype(float)
    when = _datetimes(s)
    return when.astype("int64").where(when.notna()).astype(float) / 1e9


def _trend_carriers(X: pd.DataFrame, column: str) -> list[str]:
    """The numeric inputs other than the time ``column`` that rank with it (a rank correlation of
    at least ``TREND_CARRIER_CORR``): a day counter, a year, the day of a second date. Where the
    level of the target moves with time, they let a model learn it without the time column
    itself; without them nothing would."""
    step = max(len(X) // TREND_SAMPLE_ROWS, 1)
    sample = X.iloc[::step]
    time = _time_numbers(sample[column]).rank()
    found = []
    for other in sample.columns:
        if other == column:
            continue
        values = pd.to_numeric(sample[other], errors="coerce")
        if values.notna().mean() < 0.9 or values.nunique() <= 1:
            continue
        if abs(values.rank().corr(time)) >= TREND_CARRIER_CORR:
            found.append(other)
    return found


class Prep:
    """Turns raw feature frames into the inputs of each model family.

    ``fit`` decides per column: constant and all-null columns are dropped; datetime and date
    columns are expanded into numeric parts (a column of whole numbers that are dates, such as
    14102103, keeps its number and gets the parts besides it); a text column of durations
    (``2 years``) becomes a number of days; bool and non-numeric columns become categoricals, or
    frequency encodings above ``HIGH_CARDINALITY`` categories (the share of the training rows
    with the value; a value not seen in training gets the share of the rarest one); everything
    else is numeric. The views put the features in ``feature_names`` order under positional
    names ``f0, f1, ...``, because model libraries reject some characters in feature names.
    ``groups`` (see ``fione.engine.features``) add derived numeric features after those; they are
    fitted on ``X`` alone (and on the target ``y``, for the groups that read it, which are skipped
    without it) and skipped when they read a column that is not used. A group that
    ``reads_as_codes`` names numeric columns whose whole numbers are labels: each also gets the
    frequency of its value, which CatBoost reads as text and the levels view as levels.
    """

    groups: tuple = ()  # class-level defaults: models pickled before these existed still load
    _logged: tuple = ()
    _knots: dict = {}  # linear view column -> where the splines view bends it (old: none)
    prose: tuple = ()
    all_different: frozenset = frozenset()  # frequency columns whose values are all different
    dayfirst: tuple = ()  # date string columns that put the day before the month
    integer_dates: dict = {}  # whole-number date column -> its format (``integer_date_format``)
    timed: tuple = ()  # date columns that carry a time of day
    calendar: bool = False  # the views hold the day and week of the year of dates (old: no)
    _unseen: dict = {}  # frequency column -> share given to a value not seen in training (old: 0)
    _no_trend: tuple = ()  # view columns the linear view leaves out (see ``_fit_no_trend``)
    _level_at: dict = {}  # levels view column (``f3_l``) -> the input column it reads
    _native_at: dict = {}  # catboost view column (``f3``) -> frequency column it reads as text
    codes: tuple = ()  # numeric columns also read as categories (``CodeLevels``; old: none)
    _code_shares: dict = {}  # code column -> share of the training rows with each value as text
    _code_unseen: dict = {}  # code column -> share given to a value not seen in training
    _date_now = None  # when a model that reads two-digit years was fitted (old: today's clock)
    fill: dict = {}  # input column -> share of the training rows that have a value (old: none)
    # The time column, when it has no raw value, year or seconds feature because the inputs in
    # ``trend_carriers`` move with it too (a day counter, a year, a second date): see ``fit``.
    trend_column: str | None = None
    trend_carriers: list = []

    def fit(self, X: pd.DataFrame, groups=(), y=None, trend: str | None = None) -> "Prep":
        self.dropped: list[str] = []
        self.trend_carriers = _trend_carriers(X, trend) if trend in X.columns else []
        self.trend_column = trend if self.trend_carriers else None
        self._date_now = None
        self.dayfirst = ()
        self.integer_dates = {}
        self.timed = ()
        self.calendar = CALENDAR
        self._plan: list[
            tuple[str, str]
        ] = []  # (column, kind), kind: numeric/datetime/frequency/category/duration
        self.categories: dict[str, list[str]] = {}
        self.frequencies: dict[str, dict[str, float]] = {}
        self._unseen = {}
        self._code_shares, self._code_unseen = {}, {}
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
                if self._date_now is None and frames.has_two_digit_year(s):
                    self._date_now = frames._now()  # a year read as of today is read so again
                if is_day_first(s):
                    self.dayfirst += (column,)
                when = _datetimes(s, column in self.dayfirst)
                if (when.notna() & (when != when.dt.normalize())).any():
                    self.timed += (column,)
            elif _holds_durations(s):
                self._plan.append((column, "duration"))
            elif _is_categorical(s):
                counts = _as_str(s).value_counts()
                if len(counts) > HIGH_CARDINALITY:
                    self.frequencies[column] = (counts / len(s)).to_dict()
                    self._unseen[column] = float(counts.min() / len(s))
                    self._plan.append((column, "frequency"))
                else:
                    self.categories[column] = sorted(counts.index)
                    self._plan.append((column, "category"))
            elif column == self.trend_column and not integer_date_format(s):
                continue  # a counter of the time: later rows lie beyond every value learned from
            else:
                self._plan.append((column, "numeric"))
                if fmt := integer_date_format(s):
                    self.integer_dates[column] = fmt
        if not self._plan:
            raise ConfigError("no usable feature columns: every column is empty or constant")
        self.codes = tuple(
            dict.fromkeys(
                c
                for g in groups
                if getattr(g, "reads_as_codes", False)
                for c in g.columns
                if dict(self._plan).get(c) == "numeric"
                and c not in self.integer_dates
                and _whole(X[c])
            )
        )
        self.fill = {column: float(X[column].notna().mean()) for column, _ in self._plan}
        self.all_different = frozenset(
            column
            for column, kind in self._plan
            if kind == "frequency" and X[column].nunique() == int(X[column].notna().sum())
        )
        self.prose = tuple(
            [c for c, kind in self._plan if kind in ("category", "frequency") and is_prose(X[c])][
                :MAX_PROSE
            ]
        )
        self.feature_names: list[str] = []
        # The input columns behind each feature; a derived one may have several.
        self.sources: list[tuple[str, ...]] = []
        self._category_at: dict[str, str] = {}  # view column -> categorical source column
        self._level_at = {}
        self._native_at = {}
        for column, kind in self._plan:
            if kind == "category":
                self._category_at[f"f{len(self.feature_names)}"] = column
            elif (
                kind == "frequency"
                and (column not in self.prose or _repeats(X[column]))
                and len(self.frequencies[column]) <= MAX_NATIVE_LEVELS
                and len(self.frequencies[column]) < NATIVE_REPEAT * X[column].notna().sum()
            ):
                self._native_at[f"f{len(self.feature_names)}"] = column
            if (column not in self.prose or _repeats(X[column])) and (
                kind in ("category", "frequency")
                or _has_few_levels(X[column], kind)
                or column in self.codes
            ):
                self._level_at[f"f{len(self.feature_names)}_l"] = column
            if kind == "datetime":
                parts = self._date_parts(column)
                self.feature_names += [f"{column}__{part}" for part in parts]
                self.sources += [(column,)] * len(parts)
            else:
                self.feature_names.append(column)
                self.sources.append((column,))
                if column in self.integer_dates:
                    parts = _integer_date_parts(self.integer_dates[column], self.calendar)
                    self.feature_names += [f"{column}__{part}" for part in parts]
                    self.sources += [(column,)] * len(parts)
        for column in self.codes:
            text = _whole_text(X[column])
            shares = text.value_counts(normalize=True)
            self._code_shares[column] = shares.to_dict()
            self._code_unseen[column] = float(shares.min())
            self._native_at[f"f{len(self.feature_names)}"] = column
            self.feature_names.append(f"{column}__code")
            self.sources.append((column,))
        used = set(self.columns)
        self.groups = tuple(
            fitted
            for fitted in (
                copy.copy(g).fit(X, y)
                for g in groups
                if set(g.columns) <= used and (y is not None or not g.uses_target)
            )
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

    def _date_parts(self, column: str) -> tuple[str, ...]:
        """The features of a date column, in order (a Prep fitted before the day and the week of the
        year were added has neither)."""
        parts = tuple(p for p in _DATE_PARTS if self.calendar or p not in _CALENDAR_PARTS)
        if column == self.trend_column:  # the parts that only grow: later rows lie beyond them
            parts = tuple(p for p in parts if p not in ("year", "ordinal"))
        return parts + (("hour",) if column in self.timed else ())

    @staticmethod
    def _spans_a_day(seconds: pd.Series) -> bool:
        """Whether the dates (as seconds since 1970) of the training rows span a day or more,
        first to last. Within less than a day the month and the day are (nearly) constant, the
        seconds are no line through them, and only the number carries the order of the rows."""
        return bool(seconds.max() - seconds.min() >= 86_400)

    def _fit_no_trend(self, base: pd.DataFrame) -> None:
        """The seconds-since-epoch part of a date column whose year is the same on every training
        row (for a whole-number date, a Unix time or 20240131, the number itself). Within one
        year it is a straight line through month and day, so a linear model splits the same
        effect between them in opposite weights. That holds on the training rows; on a date of
        the next year, where the month starts again, the weights add up to a prediction far
        outside the target's range. A time order of validation cannot show it, because the folds
        stay within the year. A column whose rows span less than a day keeps it (nothing else
        orders them). The time column, when other inputs move with time, loses its seconds
        (or number) and its year whatever the years."""
        off = []
        at = 0  # position of the column's first feature
        for column, kind in self._plan:
            if kind != "datetime":
                if column in self.integer_dates:
                    fmt = self.integer_dates[column]
                    parts = _integer_date_parts(fmt, self.calendar)
                    year = f"f{at + 1 + parts.index('year')}"
                    if column == self.trend_column:  # the parts that only grow
                        off += [f"f{at}", year]
                    elif base[year].nunique() <= 1:
                        when = _integer_dates(base[f"f{at}"], fmt)
                        if self._spans_a_day(_date_part(when, "ordinal")):
                            off.append(f"f{at}")
                    at += len(parts)
                at += 1
                continue
            parts = self._date_parts(column)
            if (
                column != self.trend_column
                and base[f"f{at + parts.index('year')}"].nunique() <= 1
                and self._spans_a_day(base[f"f{at + parts.index('ordinal')}"])
            ):
                off.append(f"f{at + parts.index('ordinal')}")
            at += len(parts)
        self._no_trend = tuple(off)

    def _fit_linear(self, base: pd.DataFrame, numbers: pd.DataFrame) -> None:
        """What the linear view needs: number scales, the missing-value flags and the one-hot
        levels (``LINEAR_LEVELS`` most frequent, ties by name) per categorical column."""
        values = numbers.to_numpy(dtype=float)
        medians = np.array([self._medians[p] for p in numbers.columns])
        filled = pd.DataFrame(
            np.where(np.isnan(values), medians, values),
            index=numbers.index,
            columns=numbers.columns,
        )
        skewed = (numbers.min() >= 0) & (numbers.skew() > LINEAR_SKEW)
        self._logged = tuple(skewed.index[skewed])
        if self._logged:
            at = [filled.columns.get_loc(p) for p in self._logged]
            filled.iloc[:, at] = np.log1p(filled.iloc[:, at])
        means, stds = filled.mean(), filled.std()
        self._scale = {
            position: (float(means[position]), float(stds[position] or 1.0))
            for position in filled.columns
            if position not in self._no_trend
        }
        self._flags = [p for p in base.columns if base[p].isna().any() and p not in self._no_trend]
        self._knots = self._fit_knots(filled)
        self._levels = {}
        for position in self._category_at:
            counts = base[position].value_counts()
            ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            self._levels[position] = [level for level, _ in ranked[:LINEAR_LEVELS]]

    def _fit_knots(self, filled: pd.DataFrame) -> dict[str, np.ndarray]:
        """For the numbers with many different values (at most ``SPLINE_COLUMNS``, the ones with
        most), the quantiles of their standardised, clipped values where a line may bend."""
        counts = {p: filled[p].nunique() for p in self._scale}
        wide = sorted(
            (p for p, n in counts.items() if n > SPLINE_MIN_VALUES), key=lambda p: -counts[p]
        )
        knots = {}
        for position in sorted(wide[:SPLINE_COLUMNS], key=filled.columns.get_loc):
            mean, std = self._scale[position]
            scaled = ((filled[position] - mean) / std).clip(-LINEAR_CLIP, LINEAR_CLIP)
            at = np.arange(1, SPLINE_KNOTS + 1) / (SPLINE_KNOTS + 1)
            found = np.unique(np.quantile(scaled, at))
            if len(found):
                knots[position] = found
        return knots

    def emptier(self, df: pd.DataFrame) -> list[tuple[str, float, float]]:
        """The input columns that are much emptier in ``df`` than in the training rows, as
        (column, share of training rows with a value, share of ``df``'s rows with one), emptiest
        first: a column the model learned from that the rows to predict mostly lack (a lag of the
        target for rows that lie beyond the end of the history). Nothing for fewer than
        ``MIN_ROWS`` rows, or for a model that does not know its training fill."""
        if len(df) < MIN_ROWS:
            return []
        found = []
        for column, trained in self.fill.items():
            if column in df.columns and trained >= FILLED_SHARE:
                now = float(df[column].notna().mean())
                if trained - now >= EMPTIED_BY:
                    found.append((column, trained, now))
        return sorted(found, key=lambda item: item[2] - item[1])

    @property
    def columns(self) -> list[str]:
        """The input columns the views need, in order."""
        return [column for column, _ in self._plan]

    def kind_of(self, column: str) -> Literal["numeric", "datetime", "category", "frequency"]:
        """How the model reads ``column``; ``KeyError`` for a column it does not use."""
        kind = dict(self._plan)[column]
        return "category" if kind == "duration" else kind  # a text, as the data holds it

    @property
    def duration_columns(self) -> list[str]:
        """The input columns that are text of durations, which the models read as days."""
        return [column for column, kind in self._plan if kind == "duration"]

    @property
    def numeric_columns(self) -> list[str]:
        """The input columns the model reads as numbers."""
        return [column for column, kind in self._plan if kind == "numeric"]

    def _base(self, df: pd.DataFrame) -> pd.DataFrame:
        with frames.reference_date(self._date_now):
            return self._read(df)

    def _read(self, df: pd.DataFrame) -> pd.DataFrame:
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
                if column in self.integer_dates:
                    when = _integer_dates(s, self.integer_dates[column])
                    parts = _integer_date_parts(self.integer_dates[column], self.calendar)
                    out += [_date_part(when, part) for part in parts]
            elif kind == "duration":
                out.append(_duration_days(s))
            elif kind == "datetime":
                when = _datetimes(s, column in self.dayfirst)
                out += [_date_part(when, part) for part in self._date_parts(column)]
            elif kind == "frequency":
                values = _as_str(s)
                encoded = values.map(self.frequencies[column]).astype(float)
                # An unseen value gets the share of the rarest value in training: 0 would lie
                # outside the range the models were fitted on (a shift CV cannot see).
                unseen = self._unseen.get(column, 0.0)
                out.append(encoded.mask(encoded.isna() & values.notna(), unseen))
            else:
                out.append(_as_str(s))
        for column in self.codes:
            text = _whole_text(df[column])
            share = text.map(self._code_shares[column]).astype(float)
            out.append(share.mask(share.isna() & text.notna(), self._code_unseen[column]))
        for group in self.groups:
            derived = group.transform(df)
            out += [derived[name] for name in derived.columns]
        frame = pd.concat([o.reset_index(drop=True) for o in out], axis=1)
        frame.columns = [f"f{i}" for i in range(len(self.feature_names))]
        frame.index = df.index
        frame = frame.astype({p: float for p in frame.columns if p not in self._category_at})
        # A frame built from columns holds a block per column, and slicing the rows of tens of
        # thousands of blocks takes half a second. Joining them copies the frame: not worth it
        # unless the columns are very many.
        return frame.copy() if frame.shape[1] > CONSOLIDATE_COLUMNS else frame

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
        """Categoricals as object strings with ``"__na__"`` for missing values, for CatBoost. A
        column of frequencies (many values) is its values as strings too, which CatBoost counts
        and averages the target over by itself; a nearly unique one (an id) stays a frequency."""
        base = self._base(df)
        for position in self._category_at:
            base[position] = base[position].fillna("__na__").astype(object)
        for position, column in self._native_at.items():
            text = _whole_text(df[column]) if column in self.codes else _as_str(df[column])
            base[position] = text.fillna("__na__").astype(object)
        return base

    def dense(self, df: pd.DataFrame) -> pd.DataFrame:
        """All float: category codes (-1 when missing or unseen) and median-imputed numbers."""
        base = self._base(df)
        for position, values in self._categorical(base).items():
            base[position] = values.codes.astype(float)
        filled = base.fillna(self._medians)  # a block per column again
        return filled.copy() if filled.shape[1] > CONSOLIDATE_COLUMNS else filled

    @property
    def reads_only_prose(self) -> bool:
        """Whether no input but prose carries anything for the tree and linear views: every column
        is a prose column read only as words, or one whose values are all different (an id, whose
        frequency is a constant), and no derived feature stands beside them. Those views then hold
        constants, and only the text views read anything."""
        levels = {*self._level_at.values(), *self._native_at.values()}

        def carries(column: str, kind: str) -> bool:
            if column in self.prose:
                return column in levels  # a prose that repeats is read as levels too
            return not (kind == "frequency" and column in self.all_different)

        return bool(
            self.prose
            and not self.groups
            and not any(carries(column, kind) for column, kind in self._plan)
        )

    @property
    def spline_width(self) -> int:
        """Columns of the splines view: the linear view's, and a hinge for each knot."""
        return self.linear_width + sum(len(k) for k in self._knots.values())

    def splines(self, df: pd.DataFrame) -> pd.DataFrame:
        """The linear view and, after it, a hinge ``max(0, x - knot)`` (``f3_s0``) of each
        number with knots, so that a linear model can bend its line at the knots (a piecewise
        linear curve per number). ``x`` is the number as the linear view has it."""
        out = self.linear(df)
        hinges = {
            f"{position}_s{i}": np.maximum(out[position].to_numpy() - knot, 0.0)
            for position, found in self._knots.items()
            for i, knot in enumerate(found)
        }
        return pd.concat([out, pd.DataFrame(hinges, index=out.index)], axis=1) if hinges else out

    def text(self, df: pd.DataFrame) -> pd.DataFrame:
        """The linear view without the prose columns' frequencies, and after it each prose column
        as its text (``f3_t``; missing is empty), for models that read words. The frequency of a
        text says nothing but how often it was repeated."""
        out = self.linear(df)
        spots = {self.feature_names.index(column): column for column in self.prose}
        drop = [c for c in out.columns if int(c[1:].split("_")[0]) in spots]
        out = out.drop(columns=drop)
        # dropping columns leaves a block per column: one concat adds the texts, not an insert each
        texts = [_as_str(df[column]).fillna("").rename(f"f{at}_t") for at, column in spots.items()]
        return pd.concat([out, *texts], axis=1) if texts else out

    def text_prose(self, df: pd.DataFrame) -> pd.DataFrame:
        """Only the prose columns as their texts (``f3_t``; missing is empty), what a language
        model reads."""
        spots = {self.feature_names.index(column): column for column in self.prose}
        texts = [_as_str(df[column]).fillna("").rename(f"f{at}_t") for at, column in spots.items()]
        return pd.concat(texts, axis=1) if texts else pd.DataFrame(index=df.index)

    def text_plain(self, df: pd.DataFrame) -> pd.DataFrame:
        """The text view without the columns of the derived features (``groups``); the frequencies
        of the codes (``Prep.codes``) stay, being input columns' own."""
        out = self.text(df)
        base = len(self.feature_names) - sum(len(group.names) for group in self.groups)
        return out[[c for c in out.columns if int(c[1:].split("_")[0]) < base]]

    def levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """The linear view with the categoricals' one-hot columns replaced by their values as text
        (``f3_l``; missing is its own value), for a model that one-hot encodes every level seen in
        training. Columns that are frequencies keep the frequency beside the text, and a column of
        a few whole numbers is read as levels beside its number."""
        out = self.linear(df)
        read = set(self._level_at.values())  # a prose that does not repeat is not read as levels
        drop = [
            c
            for c in out.columns
            if self._category_at.get(c.split("_")[0]) in read and not c.endswith("_na")
        ]
        out = out.drop(columns=drop)
        texts = []
        for name, column in self._level_at.items():
            values = df[column]
            if self.kind_of(column) == "numeric":  # whole numbers: infinite or huge is missing
                texts.append(_whole_text(values).fillna("__na__").rename(name))
            else:
                texts.append(values.astype(str).where(values.notna(), "__na__").rename(name))
        # one concat: an insert each fragments the frame
        return pd.concat([out, *texts], axis=1) if texts else out

    @property
    def level_width(self) -> int:
        """The most columns the levels view can hold: every level of the columns it reads."""
        width = 0
        for column in self._level_at.values():
            if column in self.frequencies:
                width += min(len(self.frequencies[column]), MAX_LEVELS)
            elif column in self.categories:
                width += len(self.categories[column]) + 1
            elif column in self._code_shares:
                width += min(len(self._code_shares[column]), MAX_LEVELS)
            else:
                width += FEW_LEVELS + 1
        return width

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
        column = "target" if y.name is None else str(y.name)
        raise TargetError(
            f"target has missing values in {missing} rows; remove those rows (the Slice rows "
            f"module with the condition '{column} is not empty') or choose another column",
            "missing",
            n=missing,
            column=column,
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
