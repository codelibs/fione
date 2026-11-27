"""The AutoML facade: search, ensemble and package a model within one hard time budget.

``AutoML.fit`` creates one ``Deadline(max_runtime_secs)`` when it starts (the whole job counts,
spec 5.1/5.7) and spends it in phases:

1. Checks, the choice of derived features (``fione.engine.features``; at most
   ``FEATURE_SHARE`` of the time, or ``FEATURE_MIN_SECS`` of a short run, and off with
   ``feature_engineering=False``), ``Prep.fit``, the check for a column that gives the target
   away on its own, or in a difference between two dates (a notice; at most ``LEAK_SHARE`` of
   the time and ``LEAK_SECS``)
   and the folds (a ``cv_group_column`` keeps the rows of a group in one fold, in the search and
   in the choice of derived features alike): measured, not otherwise budgeted. Call the time left
   after them L.
2. Search: 0.65 L. Families run one after another in ``FAMILY_ORDER``; each gets the search
   time still left times its ``FAMILY_WEIGHTS`` share among the families not yet run, so time a
   family leaves unused flows to the next ones. The search scores trials with log loss / RMSE.
   Each family hands on its ``TOP_TRIALS`` best trials, as candidates ``Family``,
   ``Family#2`` and ``Family#3``.
   After them come the *late* families (``LATE_ORDER``: LinearWide, for data with categorical
   columns that the linear view cuts short; the variants of TextLinear, for data with prose; and
   LinearBoost, small trees boosted from a linear model; LinearSpline, a linear model with a
   curve for each number), and for a regression ranked by MAE,
   MEDAE or SMAPE with no ``quantile``, the L1 variants of the boosting families
   (``MEDIAN_ORDER``: LightGBM_L1, XGBoost_L1, CatBoost_L1, which learn the median; each after the
   family it varies). When any applies, ``LATE_SHARE`` of the search
   time is kept for them, taken from
   the base families' shares (scaled to 0.85) except TextLinear's, which is as without them.
   The late families get what is left of the search time (that and what the base families
   leave), never the time of the later phases:
   each one the search time still left times its ``LATE_WEIGHTS`` share among the late families
   not yet run, and only when its first trial is expected to fit in that share (``cost`` times
   the first trial of its reference family: TextLinear, Linear for LinearWide, LinearBoost and
   LinearSpline,
   the boosting family itself for its L1 variant). A late
   family that does not apply to the data is not run and changes nothing; one that does not
   improve the ensemble gets weight 0 from ``caruana``.
   With few rows the folds are drawn again, with other seeds, ``repeats_for`` times (or
   ``cv_repeats``): a trial's score is the mean of the repeats' scores, each judged alone,
   which makes the search less likely to pick parameters that were only lucky on one split.
   Fold models, diagnostics, the leaderboard and the fold assignment come from the first repeat.
3. Ensemble selection: ``caruana`` on the candidates' out-of-fold (OOF) predictions, all repeats
   one below the other; cheap.
4. Final refit: until the reserve (about 0.2 L when the search used its whole share; more when
   it ended early). Each member with weight > 0 is refit once on all rows with its best
   parameters: boosting for 1.1 x the mean best iteration of its fold models, without early
   stopping; the forests as one full forest; Linear as one fit. DeepLearning is not refit: its
   fold models, averaged, are its final model (``FamilySpec.refit``). The fold models are also
   the fallback, averaged, with a ``notice``, for a refit that is not expected to fit in the
   time left (from its best trial's time) or that the deadline cuts short. Time left after
   that buys extra refits with other seeds (up to ``BAG_EXTRA`` per member, each when the time
   left is ``BAG_TIME_FACTOR`` times the member's first refit and the size limits allow),
   averaged with it.
5. Reserve: max(0.5 s, 0.15 L), for packaging and for what deadlines cannot interrupt (the
   families' probes, first fits on small data, an iteration slower than measured). Packaging
   includes ``fione.engine.diagnostics`` on the blended OOF predictions (at most 200,000 rows).

Members whose final models are estimated (``FamilySpec.size_bytes``) above ``SIZE_CAP`` are
cut when they are forests, to their first trees (at least ``MIN_TREE_SHARE`` of them, the
same share in each of the member's models), and dropped otherwise or when that is not enough,
with a ``notice`` that says what the member scored alone in CV and what the ensemble scored.
Then the lightest-weighted ones are cut or dropped the same way until all together fit in
``TOTAL_SIZE_CAP``, and the weights are renormalised; if that would drop every member, the
heaviest-weighted one is kept. The weights are those chosen on the full forests' predictions,
slightly off for a cut forest but still valid. ``cv_score``, ``cv_std`` and ``metrics`` come
from the fold models' OOF predictions, blended with the final weights. The returned model
holds neither the fold models nor the OOF arrays unless ``keep_cv_*`` asks;
``keep_cv_models`` keeps every family's fold models and so works against the artifact size
goal (spec 5.2).

When ``should_stop()`` turns true, the search ends, nothing is refit, and the members keep
their fold models; the model has ``stop_reason == "cancelled"``. ``NoModelError`` is raised when
no family completed a trial, because of the cancellation or because the budget is too small.

The first trial of a base family may take up to ``FIRST_TRIAL_SHARE`` of the search time left
when that is more than the family's share: the cheap linear family comes first, then the
boosting ones by priority, and each finishes a trial (on a large table one takes minutes, and a
trial cut short by a small share scores worse), those after it getting what remains. Later
trials stay within the share. A family whose first trial does not fit even then (a text model
fits all its data in one unit and cannot be cut short) has no model; a ``notice`` says that the
trial did not finish and the least its folds need. The late families that are not run for lack
of time are named in one ``notice``.

A family that raises (a library failure) is skipped with a ``notice`` of kind ``family_error``,
keeping its best trial so far; a refit that raises falls back to the fold models with a
``refit_error`` notice; diagnostics that raise leave ``diagnostics`` None, with a
``diagnostics_error`` notice. ``stop_reason`` is ``error`` when a family failed and nothing
else (time, ``max_models``, cancellation) ended the search. ``NoModelError`` lists every
family's error and is chained to the last one when no family produced a model.

``families`` restricts the search to some of ``FAMILY_ORDER`` and ``LATE_ORDER`` (tests and
advanced use).
"""

import json
import math
import time
from collections.abc import Callable

import numpy as np
import pandas as pd

from fione.data.frames import is_time_counter, parse_datetimes
from fione.data.profile import training_leak_suspects
from fione.engine import embedding, metrics
from fione.engine.config import ConfigError, Deadline, DeadlineExceeded, NoModelError, TrainConfig
from fione.engine.diagnostics import diagnostics
from fione.engine.ensemble import caruana
from fione.engine.events import Event, EventSink, jsonable
from fione.engine.families import FAMILIES, MAX_ROUNDS, FamilySpec
from fione.engine.features import DateDifferences, repeated_blocks, select_groups
from fione.engine.model import Member, TrainedModel, feature_importance
from fione.engine.prep import Prep, Task, infer_task, validate_target
from fione.engine.search import (
    Clock,
    FamilyResult,
    Folds,
    covered,
    error_notice,
    make_time_folds,
    repeat_folds,
    repeats_for,
    run_family,
)
from fione.engine.survival import km_target

FAMILY_ORDER = (
    "Linear",
    "LightGBM",
    "TextLinear",
    "CatBoost",
    "XGBoost",
    "RandomForest",
    "ExtraTrees",
    "DeepLearning",
)
FAMILY_WEIGHTS = {
    "LightGBM": 0.176,
    "TextLinear": 0.2,  # only searched for data with prose, where it matters most
    "CatBoost": 0.176,
    "XGBoost": 0.144,
    "RandomForest": 0.08,
    "ExtraTrees": 0.08,
    "DeepLearning": 0.096,
    "Linear": 0.048,
}
# The families that can learn a quantile, the only ones searched for a ``quantile``.
QUANTILE_FAMILIES = tuple(f for f in FAMILY_ORDER if FAMILIES[f].quantile_objective)
# Run after the others, in the search time they leave (see the module docstring); each only
# when the data suits it (``FamilySpec.applies``) and a model of it would not be too big.
# Searched only when the settings ask for them (as a base family, in the time its weight gives it),
# so that a fit that does not ask is what it was before.
OPT_IN_ORDER = ("TextEmbedding",)
OPT_IN_WEIGHTS = {"TextEmbedding": 0.2}  # like TextLinear: it matters most where there is prose
# The L1 variants of the boosting families are late candidates for a regression ranked by MAE,
# MEDAE or SMAPE (``MEDIAN_METRICS``) with no quantile: the squared error the others learn is not
# the loss they are ranked by, and on a heavy-tailed target the median predicts better.
MEDIAN_ORDER = ("LightGBM_L1", "XGBoost_L1", "CatBoost_L1")
MEDIAN_METRICS = frozenset({"mae", "medae", "smape"})
LATE_ORDER = (
    "LinearWide",
    "TextLinearChar",
    "TextLinearPlain",
    "TextLinearWide",
    "LinearBoost",
    "LinearSpline",
    *MEDIAN_ORDER,
)
# sum 1; LinearBoost comes after the text ones and takes what they leave. LinearSpline has a
# nominal weight: it takes what is left only where no median variant follows it, so LinearBoost
# keeps nearly all the time it had.
LATE_WEIGHTS = {
    "LinearWide": 5 / 64,
    "TextLinearChar": 25 / 128,
    "TextLinearPlain": 25 / 256,
    "TextLinearWide": 25 / 256,
    "LinearBoost": 1 / 16,
    "LinearSpline": 1 / 256,
    "LightGBM_L1": 59 / 256,
    "XGBoost_L1": 15 / 128,
    "CatBoost_L1": 15 / 128,
}
LATE_SHARE = 0.15  # of the search time is kept for the late families, when any applies
# The first trial of a base family may take up to this share of the search time left, if that is
# more than the family's share. Two cases need it: a text model fits all its data in one unit and
# cannot be cut short, so a share below one trial leaves it without a model; and on a large table
# a boosting family needs minutes for one trial, and a trial cut short by a small share scores
# worse. Where every family already fits a trial in its share, it changes nothing.
FIRST_TRIAL_SHARE = 0.5
FEATURE_SHARE = 0.10  # of the time, at most, goes to choosing derived features
# A short run gets more: the choice needs about this long on a few thousand rows, and without it
# the most useful candidates run out of time unconfirmed. Never over FEATURE_MAX_SHARE.
FEATURE_MIN_SECS = 30.0
FEATURE_MAX_SHARE = 0.30
# A table with more columns than this that the run keeps (not the constant ones, which it leaves
# out) gets no derived features: reading its columns once for every repeat of the gate's folds
# takes seconds, which leaves nothing to judge a candidate with.
FEATURE_MAX_COLUMNS = 5_000
DROPPED_SHOWN = 5  # names of left-out columns in the notice
# The check for a column that predicts the target alone (``fione.data.profile.leak_check``) gets
# this share of the time, at most LEAK_SECS, and names at most LEAK_SHOWN columns.
LEAK_SHARE = 0.05
LEAK_SECS = 3.0
LEAK_SHOWN = 5
# The differences between two dates are checked for a leak too (an end date that is only known
# afterwards gives the length of a trip, though neither date does alone), on this many rows.
LEAK_ROWS = 10_000
# A text column of at least this many different values, each on this many rows or more on
# average, may name rows that belong together (see ``AutoML._notice_repeated_values``).
REPEATED_LEVELS = 100
REPEATED_ROWS = 20
REPEATED_SHARED = 0.8  # of the other columns, constant within a value, for the rows to look alike
REPEATED_SAMPLE_ROWS = 50_000
REPEATED_COLUMNS = 40  # other columns looked at
REPEATED_TEXT_SHARE = 0.05  # of the rows with a text identical to another row's, to say so
REPEATED_TEXT_ROWS = 50  # ... and at least this many of them
REPEATED_TEXT_COPIES = 10  # a text on more rows than this is a label or a filler, not a copy
REPEATED_TEXT_DISTINCT = 0.5  # of the filled rows have a text of their own, for copies to stand out
# A frequency-encoded column of codes (see ``_codes``) whose values each come back on this many rows
# or more on average, and that holds at least this share of the importance: see
# ``AutoML._notice_frequency_encoded_values``.
FREQUENCY_ROWS = 3
FREQUENCY_IMPORTANCE = 0.05
CODE_LENGTH = 8  # characters of a value that reads as a code
# A regression target whose neighbouring rows are this alike (correlation of each value with the
# next): see ``AutoML._notice_ordered_target``.
ORDERED_MIN_ROWS = 200
ORDERED_AUTOCORR = 0.8
# A whole-number column that never decreases down the rows, of at least this many different
# values each on this many rows or more on average: see ``AutoML._notice_sorted_column``.
SORTED_VALUES = 20
SORTED_ROWS = 20
# A whole-number target of this many different values, each on this many rows or more on
# average, whose counts do not rise and fall smoothly with the value (the correlation of each
# count with the next under CODE_SMOOTH, as an age or a count would), may be class codes: see
# ``AutoML._notice_class_codes``.
CODE_VALUES = (21, 100)
CODE_ROWS = 50
CODE_SMOOTH = 0.5

# A column of at least this many different values, each on this many rows or more on average, that
# a time column puts in order may name things followed over time (a store, a county, a patient):
# see ``AutoML._notice_history_missing``. The target of each row is compared with that of the row
# before it of the same value, once the mean of the value and of the time are taken off, and a
# column that tells the target at least HISTORY_COVERED of as well counts as the same help.
HISTORY_VALUES = 20
HISTORY_ROWS = 5
HISTORY_PERSISTENCE = 0.7
HISTORY_COVERED = 0.8
HISTORY_SAMPLE_ROWS = 50_000
HISTORY_COLUMNS = 200  # a wider table is not looked at
# A time-ordered validation whose first part spans less than SEASON_DAYS, of dates that span more
# than TWO_SEASONS_DAYS: the first folds learn from less than one yearly cycle, see
# ``AutoML._notice_time_parts``.
SEASON_DAYS = 365
TWO_SEASONS_DAYS = 2 * SEASON_DAYS

# A validated fit this good (or this poor) gets a notice: R-squared, or AUC for two classes.
NEAR_PERFECT_R2 = 0.999
NO_SKILL_R2 = 0.02
NEAR_PERFECT_AUC = 0.9995
NO_SKILL_AUC = 0.55
NO_SKILL_LOGLOSS = 0.02  # of more than two classes: the share of the class shares' log loss
# A fit validated on this many rows or fewer, picked among at least
# ``SMALL_DATA_TRIALS`` finished trials, gets a notice: see ``AutoML._notice_small_data``.
SMALL_DATA_ROWS = 300
SMALL_DATA_TRIALS = 20
ZERO_SHARE = 0.95  # of a target of 0 or more that is exactly 0: the few others decide the score
# The validated rows are scored once more with the numeric column most correlated with the target
# used as the prediction, as it is, when its squared error is less than this share of the target's
# variance (it is on the target's scale): see ``AutoML._notice_baseline``.
BASELINE_ON_SCALE = 0.5
BASELINE_MIN_ROWS = 30
# The ranking metrics of a regression with a constant that is best for them, and a model that
# beats that constant by less than this share of its loss gets a notice: see
# ``AutoML._notice_constant``.
CONSTANT_METRICS = frozenset({"mae", "medae", "pinball"})
CONSTANT_MARGIN = 0.01
SEARCH_SHARE = 0.65
RESERVE_SHARE = 0.15
MIN_RESERVE_SECS = 0.5
REFIT_ROUNDS_FACTOR = 1.1
# The linear view (one-hot levels) of Linear and DeepLearning is built whole, and each fold copies
# most of it again: above this many cells (800 MB as float64) those families are left out.
LINEAR_MAX_CELLS = 100_000_000
# Time left after the refits buys extra refits of a member with other seeds, averaged with the
# first (variance falls with the seeds): up to ``BAG_EXTRA`` more, each only when the time left
# is ``BAG_TIME_FACTOR`` times what the member's first refit took.
BAG_EXTRA = 4
BAG_TIME_FACTOR = 2.0
BAG_SEED_STEP = 7919
BAG_SEED_SPACE = 2**31 - 1
SIZE_CAP = 40 * 1024**2  # per member
TOTAL_SIZE_CAP = 90 * 1024**2  # all members: the artifact target is 100 MB (spec 5.2)
MIN_TREE_SHARE = 0.2  # a forest over a size cap is cut to at least this share of its trees
LEADERBOARD_COLUMNS = ["model", "family", "cv_score", "cv_std", "train_secs", "weight"]
TRIAL_COLUMNS = ["family", "trial", "state", "score", "elapsed", "params"]


def _ignore(event: Event) -> None:
    pass


def _never() -> bool:
    return False


def kept_columns(X: pd.DataFrame) -> int:
    """The columns of ``X`` the models read: those with more than one value (``Prep`` leaves out
    the others)."""
    return int((X.nunique(dropna=False) > 1).sum())


def _shared_values(X: pd.DataFrame, column: str) -> float:
    """The share of the other columns (those that vary, at most ``REPEATED_COLUMNS`` of them)
    that hold one value within every value of ``column``: 1 when rows with the same value are
    identical elsewhere, near 0 when they differ in everything."""
    others = [c for c in X.columns if c != column and X[c].nunique(dropna=False) > 1]
    others = others[:REPEATED_COLUMNS]
    if not others:
        return 0.0
    groups = X.groupby(column, sort=False, dropna=False)
    constant = [(groups[c].nunique(dropna=False) <= 1).mean() for c in others]
    return float(np.mean(constant))


def _centered(values: np.ndarray, *groups: np.ndarray) -> np.ndarray:
    """``values`` with the mean of each group taken off in turn (a missing value is skipped)."""
    for codes in groups:
        present = ~np.isnan(values)
        total = np.bincount(codes, np.where(present, values, 0.0))
        values = values - (total / np.maximum(np.bincount(codes, present), 1))[codes]
    return values


def _correlation(a: np.ndarray, b: np.ndarray) -> float:
    """The correlation of ``a`` and ``b`` on the rows where both are present, 0 if undefined."""
    both = ~np.isnan(a) & ~np.isnan(b)
    if both.sum() < 30 or a[both].std() == 0 or b[both].std() == 0:
        return 0.0
    return float(np.corrcoef(a[both], b[both])[0, 1])


def _persistence(X: pd.DataFrame, y: np.ndarray, order: np.ndarray, column: str) -> float | None:
    """How much the target of a row follows that of the row before it of the same value of
    ``column`` (in the order of ``order``), once the mean of the value and of the time are taken
    off, when no numeric column tells the target at least ``HISTORY_COVERED`` of that well in the
    same terms; ``None`` when ``column`` does not name things seen once at each time, or the
    target does not follow."""
    codes = pd.factorize(X[column], use_na_sentinel=False)[0]
    if len(X) > HISTORY_SAMPLE_ROWS:  # whole values, so that the rows before stay
        keep = np.flatnonzero(codes < max(1, (codes.max() + 1) * HISTORY_SAMPLE_ROWS // len(X)))
        X, y, order, codes = X.iloc[keep], y[keep], order[keep], codes[keep]
    rows = np.lexsort((order, codes))
    codes, order, y = codes[rows], order[rows], y[rows]
    follows = np.r_[False, codes[1:] == codes[:-1]]
    if (follows & np.r_[False, order[1:] == order[:-1]]).sum() > 0.05 * follows.sum():
        return None  # one value seen several times at one time: a category, not a thing over time
    off = _centered(y, codes, order)
    before = np.r_[np.nan, off[:-1]]
    follow = _correlation(np.where(follows, off, np.nan), before)
    if follow < HISTORY_PERSISTENCE:
        return None
    for other in X.columns:
        if other != column and pd.api.types.is_numeric_dtype(X[other]):
            column_off = _centered(
                X[other].to_numpy("float64", na_value=np.nan)[rows], codes, order
            )
            if abs(_correlation(column_off, off)) >= HISTORY_COVERED * follow:
                return None
    return follow


def _codes(values) -> bool:
    """Whether the ``values`` of a text column read as codes, not words (an id, a hash): at least
    ``CODE_LENGTH`` characters with a digit and no space, in nine of ten values."""
    text = pd.Series(list(values), dtype="str")
    code = text.str.len().ge(CODE_LENGTH) & text.str.contains(r"\d") & ~text.str.contains(r"\s")
    return bool(code.mean() >= 0.9)


class AutoML:
    def __init__(
        self,
        config: TrainConfig,
        emit: EventSink = _ignore,
        should_stop: Callable[[], bool] = _never,
        families: list[str] | None = None,
    ):
        self.config = config.validate()
        self.emit = emit
        self.should_stop = should_stop
        known = [*FAMILY_ORDER, *LATE_ORDER, *OPT_IN_ORDER]
        unknown = sorted(set(families or ()) - set(known))
        if unknown or families == []:
            raise ConfigError(f"unknown families: {unknown}; choose from {known}")
        self.explicit = families is not None  # the caller named the families
        if config.quantile is not None:
            other = sorted(set(families or ()) - set(QUANTILE_FAMILIES))
            if other:
                raise ConfigError(
                    f"{', '.join(other)} cannot learn a quantile; choose from {QUANTILE_FAMILIES}"
                )
            families = list(families or QUANTILE_FAMILIES)
        opt_in = OPT_IN_ORDER if config.embedding_backend is not None else ()
        self.families = [f for f in (*FAMILY_ORDER, *opt_in) if families is None or f in families]
        if "TextEmbedding" in (families or ()) and config.embedding_backend is None:
            raise ConfigError("TextEmbedding needs an embedding_backend")
        self.late = [
            f for f in LATE_ORDER if f not in MEDIAN_ORDER and (families is None or f in families)
        ]
        self.median = [f for f in MEDIAN_ORDER if families is None or f in families]
        self._leaked: set[str] = set()  # the columns ``_notice_leaks`` named in this fit

    def _event(self, type: str, **data) -> None:
        self.emit(Event(type, data=jsonable(data)))

    def _notice_repeated_values(self, prep: Prep, X: pd.DataFrame) -> bool:
        """Say when rows seem to belong together while the validation shuffles them: a text
        column of many different values that each come back on many rows, whose rows also share
        the values of most other columns (the rows of one game, one patient, one store look
        alike). Rows of one value then sit on both sides of every split, and the score is better
        than the model will do on rows of other values."""
        n_rows = len(X)
        levels = {**prep.categories, **prep.frequencies}  # the values of each text column
        found = [
            (column, len(values))
            for column, values in levels.items()
            if len(values) >= REPEATED_LEVELS and n_rows / len(values) >= REPEATED_ROWS
        ]
        if not found:
            return False
        sample = (
            X if n_rows <= REPEATED_SAMPLE_ROWS else X.sample(REPEATED_SAMPLE_ROWS, random_state=0)
        )
        shared = {column: _shared_values(sample, column) for column, _ in found}
        column, levels_n = max(
            ((c, k) for c, k in found if shared[c] >= REPEATED_SHARED),
            key=lambda ck: shared[ck[0]],
            default=(None, 0),
        )
        if column is None:
            return False
        self._notice(
            f"{column!r} has {levels_n:,} different values, each on about {n_rows / levels_n:.0f} "
            "rows, and the rows of one value look alike in most other columns. The validation "
            "shuffles the rows, so rows of one value sit on both sides of a split. If the rows "
            "you will predict have other values, the score is probably better than it will be; "
            "name that column as cv_group_column to validate on values the model has not seen",
            kind="repeated_values",
            columns=[column],
            shared=round(shared[column], 2),
        )
        return True

    def _notice_repeated_texts(self, prep: Prep, X: pd.DataFrame) -> bool:
        """Say when the same text is on several rows (a review posted twice, a product listed
        again) while the validation shuffles the rows: the copy of a row's text is usually in the
        training part and a model that reads the text recognises it. Only the prose columns count,
        and only where copies are the exception (at least ``REPEATED_TEXT_DISTINCT`` of the
        filled rows have a text of their own: a short phrase that every row repeats is a label);
        a text on more than ``REPEATED_TEXT_COPIES`` rows is not a copy but a filler ("no
        description"); nor is it said when the rows are already named as belonging together
        (``_notice_repeated_values``, ``_notice_repeated_rows``)."""
        found = {}
        for column in prep.prose:
            codes, texts = pd.factorize(X[column].dropna())
            if not len(codes) or len(texts) / len(codes) < REPEATED_TEXT_DISTINCT:
                continue
            same = np.bincount(codes)[codes]  # the rows with the same text, for each row
            copies = int(((same >= 2) & (same <= REPEATED_TEXT_COPIES)).sum())
            if copies >= REPEATED_TEXT_ROWS and copies / len(X) >= REPEATED_TEXT_SHARE:
                found[column] = copies / len(X)
        if not found:
            return False
        column = max(found, key=found.__getitem__)
        self._notice(
            f"{found[column]:.0%} of the rows have a {column!r} identical to that of another row. "
            "The validation shuffles the rows, so the copy of a text is usually in the training "
            "part, and the model recognises it. If the rows you will predict have new texts, the "
            "score is probably better than it will be; name a column that identifies the text "
            "(or what it describes) as cv_group_column to validate on texts the model has not "
            "seen, or expect a worse score on new texts if there is none",
            kind="repeated_texts",
            columns=list(found),
            share=round(found[column], 2),
        )
        return True

    def _notice_repeated_rows(self, prep: Prep, X: pd.DataFrame) -> bool:
        """Say when several number columns repeat together over groups of rows (see
        ``repeated_blocks``) while the validation shuffles the rows: rows of one group then sit
        on both sides of every split, a model can recognise a group by its numbers, and the score
        is better than the model will do on rows of other groups."""
        found = repeated_blocks(X, list(prep.numeric_columns))
        if found is None:
            return False
        columns = found[0]
        # the groups of the whole table, not of the rows looked at
        size = len(X) / X[columns[0]].astype(float).round(10).nunique()
        shown = ", ".join(repr(c) for c in columns[:4])
        self._notice(
            f"{len(columns)} number columns ({shown}) hold the same values on groups of about "
            f"{size:.1f} rows, as the features of one team, store or place joined onto its rows "
            "do. The validation shuffles the rows, so rows of one group sit on both sides of a "
            "split and the score is probably better than the model will do on rows of other "
            "groups. If you will predict other groups or later times, name a column that "
            "identifies the group as cv_group_column, or the time as time_column",
            kind="repeated_rows",
            columns=columns[:10],
            rows_per_group=round(size, 1),
        )
        return True

    def _notice_missing_history(
        self, df: pd.DataFrame, X: pd.DataFrame, y: np.ndarray, time_column: str | None
    ) -> None:
        """Say when the rows are things followed over time (a store, a county, a patient: a
        column whose values each come back on many rows, once at each time of ``order``), the
        target of a row follows that of the row before it of the same thing, and no column
        tells the target as well: every row is learned and predicted alone, and what the same
        thing did at earlier times is not in the table. It says nothing of a table with a
        column that holds earlier values, or of one whose things are named by several columns
        together. Advisory: a check that fails changes nothing."""
        if time_column is None or X.shape[1] > HISTORY_COLUMNS:
            return
        found = {}
        try:
            order = _order_codes(df, time_column)
            for column in X.columns:
                values = X[column]
                if column == time_column or pd.api.types.is_float_dtype(values):
                    continue
                if HISTORY_VALUES <= values.nunique() <= len(X) / HISTORY_ROWS:
                    follow = _persistence(X, y, order, column)
                    if follow is not None:
                        found[column] = follow
        except Exception:
            return
        if not found:
            return
        column = max(found, key=found.__getitem__)
        self._notice(
            f"the target of a row follows that of the row before it of the same {column!r} "
            f"(correlation {found[column]:.2f} once the mean of each {column!r} and of each time "
            "are taken off), and no column of the table tells the target as well. The model "
            f"sees each row alone, so it cannot use what a {column!r} did at earlier times. To "
            "give it those values, add them with the Add values from earlier times module "
            "(lag), or the Add statistics of nearby values module (rolling), before training",
            kind="missing_history",
            columns=[column],
            correlation=round(found[column], 2),
        )

    def _notice_frequency_encoded_values(
        self, prep: Prep, X: pd.DataFrame, importance: pd.Series
    ) -> list[str]:
        """Say when the model leans on an id or a group code that is read as how often each value
        occurs (``Prep`` does so above ``HIGH_CARDINALITY`` values). The share of each value is
        counted over all the training rows, so the validation rows already have their true share,
        while a value the model has not seen gets the share of the rarest one: the rows of a new
        group all look like a tiny group, which the validation cannot show."""
        found = []
        try:
            for column, values in prep.frequencies.items():
                rows = int(X[column].notna().sum())
                share = float(importance.get(column, 0.0))
                if (
                    rows >= FREQUENCY_ROWS * len(values)
                    and share >= FREQUENCY_IMPORTANCE
                    and _codes(values)
                ):
                    found.append((share, column, len(values), rows))
        except Exception:
            return []
        if not found:
            return []
        found.sort(reverse=True)
        share, column, values, rows = found[0]
        others = [c for _, c, _, _ in found[1:DROPPED_SHOWN]]
        self._notice(
            f"{column!r} holds codes: {values:,} different values, each on about "
            f"{rows / values:.0f} rows, and the model reads it as how often each value occurs "
            f"({share:.0%} of what it relies on). A value the model has not seen gets the share "
            "of the rarest value, so rows of a new value look like they come from a very small "
            "group, and the validation "
            "counts every value over all the training rows, so it cannot show how the model does "
            "on rows of new values. If the rows you will predict have other values, leave the "
            "column out of the inputs (ignored_columns)"
            + (f". Other columns like it: {', '.join(repr(c) for c in others)}" if others else ""),
            kind="frequency_encoded_values",
            columns=[column, *others],
            values=values,
            importance=round(share, 2),
        )
        return [column, *others]

    def _notice_group_column_input(
        self, X: pd.DataFrame, importance: pd.Series, named: list[str]
    ) -> None:
        """Say when the column that keeps the validation groups apart is also an input that the
        model leans on. The validation never shows the model a group it has learned from, so it
        cannot show what the column does on rows of other groups; a number that orders the groups
        (trial 7 next to trial 8) even makes the score better than it will be, as the groups next
        to a validation group are in the training rows."""
        column = self.config.cv_group_column
        share = float(importance.get(column, 0.0)) if column in X.columns else 0.0
        if column is None or column in named or share < FREQUENCY_IMPORTANCE:
            return
        self._notice(
            f"{column!r} is the group column and also an input, and the model relies on it for "
            f"{share:.0%} of what it relies on. The validation never shows the model a group it "
            "has learned from, so it cannot show what the column does on rows of other groups "
            "(groups next to each other in a number or a code may be related, which makes the "
            "score better than it will be). If the rows you will predict hold other groups, "
            "leave the column out of the inputs (ignored_columns)",
            kind="group_column_input",
            columns=[column],
            importance=round(share, 2),
        )

    def _notice_time_trend(self, prep: Prep) -> None:
        """Say that the time column is not read as what only grows with time. The rows to predict
        are later than all the rows the model learns from, so a tree would read the new values of
        the column (as a number, or the year and the seconds of a date) as the latest period it
        knows; the validation parts lie just after the rows they learn from and do not show what
        that costs. Inputs that move with the column keep the level over time learnable."""
        if prep.trend_column is None:
            return
        shown = ", ".join(repr(name) for name in prep.trend_carriers[:DROPPED_SHOWN])
        if prep.trend_column in prep.integer_dates:  # the trees still read its number and year
            read = "is not read as a number or as its year by the linear models"
        else:
            read = "is not read as a number (or as the year and the seconds of a date)"
        self._notice(
            f"{prep.trend_column!r}, the column that orders the rows in time, {read}: the rows to "
            "predict are later than all the rows the model learns from, so it would read their "
            f"values as the latest period it knows. The inputs {shown} move with it and carry the "
            "level over time",
            kind="time_trend_left_out",
            columns=[prep.trend_column],
            carriers=list(prep.trend_carriers[:DROPPED_SHOWN]),
        )

    def _notice_time_parts(self, times: pd.Series, folds, n_rows: int) -> None:
        """Say how the rows are cut for the time-ordered validation: the rows (and, for a date
        column, the days) of the first part, which is only learned from, and of each validation
        part. Warn when dates span over two years and the first part spans less than a year: the
        first folds learn from less than one yearly cycle, so their scores may be pessimistic.
        A date column is one of date type or text read as dates; a numeric column (whole-number
        dates and Unix times too) is not, so it gives the rows only and no warning."""
        column = self.config.time_column
        parts = [np.setdiff1d(np.arange(n_rows), covered(folds, n_rows))] + [v for _, v in folds]
        rows = [len(part) for part in parts]
        dates = times if pd.api.types.is_datetime64_any_dtype(times) else None
        days = None
        if dates is not None:
            days = [(dates.iloc[p].max() - dates.iloc[p].min()).days + 1 for p in parts]
        message = (
            f"validating on {len(folds)} later parts of the data in order of '{column}'; the "
            f"first part is only learned from. It holds {rows[0]:,} rows"
            + (f" ({_span_text(days[0])})" if days else "")
            + ", and each validation part holds "
            + _range_text(rows[1:], lambda n: f"{n:,}")
            + " rows"
            + (f" ({_range_text(days[1:], _span_text)})" if days else "")
        )
        self._notice(
            message, kind="time_validation", folds=len(folds), part_rows=rows, part_days=days
        )
        if dates is None:
            return
        whole = (dates.max() - dates.min()).days + 1
        # with 2 folds (the least) the first part is a third of the rows: no smaller nfolds exists
        # (fewer folds than nfolds come out when groups or equal times end together)
        if len(folds) <= 2 or days[0] >= SEASON_DAYS or whole <= TWO_SEASONS_DAYS:
            return
        self._notice(
            f"the first part of the time-ordered validation spans {_span_text(days[0])} while "
            f"'{column}' spans {_span_text(whole)}: the first folds learn from less than one "
            "year, so a seasonal pattern may not be learned there, and "
            "their scores may be pessimistic. The mean of the folds can hide this: a smaller "
            f"nfolds (now {len(folds)}) cuts the rows into fewer and longer parts, so the first "
            "part holds more history",
            kind="time_short_history",
            first_part_days=days[0],
            days=whole,
            folds=len(folds),
        )

    def _notice_lopsided_parts(self, folds, n_rows: int, nfolds: int) -> None:
        """Say when a part of the time-ordered validation of groups holds far more than its
        share of the rows: the groups end at about the same time (users present at every
        origin of a stacked table), so a fold learns from a few of them and predicts most."""
        sizes = [n_rows - len(covered(folds, n_rows))] + [len(valid) for _, valid in folds]
        if max(sizes) * (nfolds + 1) <= 2 * n_rows:
            return
        self._notice(
            f"the groups of '{self.config.cv_group_column}' end at about the same time of "
            f"'{self.config.time_column}', or are few: the {len(sizes)} validation parts hold "
            f"{', '.join(f'{s:,}' for s in sizes)} rows, so a fold learns from few rows and "
            "predicts many. Groups that stay over the whole range are validated better with "
            "the group column alone, without a time column",
            kind="time_groups_one_part",
            part_rows=sizes,
        )

    def _notice_time_index(self, prep: Prep, X: pd.DataFrame) -> bool:
        """Say when a whole-number column named like a time (date_id, day_idx, week_no) runs
        through consecutive numbers (a few may be missing), at least SORTED_VALUES of them: a
        day or period counter, or the day or period of each row. The shuffled validation does
        not use their order."""
        for column in prep.columns:
            values = X[column]
            if (
                prep.kind_of(column) != "numeric"
                or not pd.api.types.is_integer_dtype(values)
                or values.isna().any()  # a time column cannot have missing values
            ):
                continue
            distinct = values.nunique()
            if (
                distinct < SORTED_VALUES
                or 1 < len(X) / distinct < 2
                or not is_time_counter(
                    column,
                    int(values.min()),
                    int(values.max()),
                    distinct,
                    repeated=distinct < len(X),
                )
            ):
                continue
            if distinct == len(X):
                message = (
                    f"{column!r} holds each whole number on one row and is named like a time, so "
                    "the rows may be one per day or period. No time_column is given, so the "
                    "validation shuffles the rows. If the model will predict later times, the "
                    "score is probably better than it will be; name that column as time_column "
                    "to validate on later parts"
                )
            else:
                message = (
                    f"{column!r} is named like a time and runs through {distinct:,} consecutive "
                    f"whole numbers, each on about {len(X) / distinct:.0f} rows, so it may be the "
                    "day or period of each row. No time_column is given, so the validation "
                    "shuffles the rows. If the rows are ordered in time and the model will "
                    "predict later times, the score is probably better than it will be; name "
                    "that column as time_column to validate on later parts"
                )
            self._notice(message, kind="time_index", columns=[column])
            return True
        return False

    def _notice_sorted_column(self, prep: Prep, X: pd.DataFrame) -> bool:
        """Say when a whole-number column never decreases down the rows and each of its values
        covers many rows (a day number, a period, a group number the file is sorted by): the
        rows may be in time order, or the rows of a value belong together. The validation
        shuffles them, so the rows of every value sit on both sides of a split."""
        n_rows = len(X)
        for column in prep.columns:
            values = X[column]
            if prep.kind_of(column) != "numeric" or not pd.api.types.is_integer_dtype(values):
                continue
            if not values.is_monotonic_increasing:
                continue
            distinct = values.nunique()
            if SORTED_VALUES <= distinct <= n_rows / SORTED_ROWS:
                self._notice(
                    f"{column!r} never decreases down the rows and each of its {distinct:,} "
                    f"values covers about {n_rows / distinct:.0f} rows, so the rows may be "
                    "sorted by time, or the rows of one value may belong together. The "
                    "validation shuffles the rows: if the model will predict rows from later "
                    "times or other groups, the score is probably much better than it will be; "
                    "name that column as time_column, or as cv_group_column if the rows of one "
                    "value belong together",
                    kind="sorted_column",
                    columns=[column],
                )
                return True
        return False

    def _notice_class_codes(self, y: np.ndarray) -> None:
        """Say when a target fitted as a regression because ``task`` is ``auto`` looks like class
        codes: whole numbers, each on many rows, with no smooth shape over the values. Codes are
        not amounts, so the regression, and the advice for a skewed amount, may not suit them."""
        values, counts = np.unique(y, return_counts=True)  # in the order of the values
        if not CODE_VALUES[0] <= len(values) <= CODE_VALUES[1] or len(y) / len(values) < CODE_ROWS:
            return
        if (y % 1).any() or counts.min() == counts.max():
            return
        if not np.corrcoef(counts[:-1], counts[1:])[0, 1] < CODE_SMOOTH:
            return
        self._notice(
            f"the target holds {len(values)} different whole numbers, each on about "
            f"{len(y) / len(values):,.0f} rows, and no smooth shape over them, so it is fitted "
            "as a regression. If they are class codes (a category number, a type id) "
            "rather than amounts, set task to 'classification'",
            kind="class_codes",
            values=len(values),
        )

    def _notice_ordered_target(self, y: np.ndarray, classes: bool = False) -> None:
        """Say when the target of a row is nearly that of the row before it: the rows are in
        time order, or each has near copies beside it. The validation shuffles the rows, so the
        neighbours of every validated row are learned from, and the score is far better than
        the model will do on rows of other times. A table sorted by its target gets the notice
        too: its rows look the same as a trend in time order, and the notice only asks. Of
        ``classes`` (the codes of a classification) the likeness is how far above chance the
        share of rows with the class of the row before them is (1: always the same)."""
        if len(y) < ORDERED_MIN_ROWS or np.ptp(y) == 0:
            return
        if classes:
            chance = float(np.sum((np.bincount(y) / len(y)) ** 2))
            alike = (float(np.mean(y[:-1] == y[1:])) - chance) / (1 - chance)
        else:
            alike = np.corrcoef(y[:-1], y[1:])[0, 1]
        if not alike >= ORDERED_AUTOCORR:
            return
        measure = "agreement" if classes else "correlation"
        self._notice(
            f"the target of a row is nearly that of the row before it ({measure} "
            f"{alike:.2f}), so the rows may be in time order, have near copies beside them or "
            "be sorted by the target. "
            "The validation shuffles the rows: if the model will predict rows from other times or "
            "other groups, the score is probably much better than it will be; name the column "
            "that gives the order (add a row number if none does) as time_column, or the column "
            "that ties related rows together as cv_group_column",
            kind="ordered_target",
            correlation=round(float(alike), 2),
        )

    def _notice_leaks(self, prep: Prep, X: pd.DataFrame, target: pd.Series, secs: float) -> None:
        """Name the input columns that give the target away on their own (the profile's leak
        check, on a sample, within ``secs``): a column the model will not know when it is
        used makes the score better than the model will do. It only warns; a check that fails
        changes nothing."""
        try:
            found = training_leak_suspects(X, target, columns=prep.columns, time_budget=secs)
        except Exception:  # an advisory check must not stop a training run
            return
        if not found:
            return
        shown = found[:LEAK_SHOWN]
        self._leaked = {s.column for s in shown}
        listing = ", ".join(f"{s.column!r} ({s.reason})" for s in shown)
        more = len(found) - len(shown)
        self._notice(
            f"{len(found)} {'column' if len(found) == 1 else 'columns'} may give the answer "
            f"away: {listing}" + (f" and {more} more" if more > 0 else "") + ". A column that "
            "is not known when the model is used makes the score better than the model will "
            "do; check that every input is known at that time, and leave out the ones that "
            "are not",
            kind="leak_suspects",
            columns=[s.column for s in shown],
            reasons=[s.reason for s in shown],
            count=len(found),
        )

    def _notice_derived_leaks(
        self, prep: Prep, X: pd.DataFrame, target: pd.Series, secs: float
    ) -> None:
        """Name the adopted differences between two dates that give the target away (an end
        date that is only known afterwards, minus the start date, is the length): neither date
        does alone, so ``_notice_leaks`` does not see them. Same check, on at most ``LEAK_ROWS``
        rows and within ``secs``; a feature made of a column already named is left out. It only
        warns; a check that fails changes nothing."""
        groups = [g for g in prep.groups if isinstance(g, DateDifferences)]
        if not groups:
            return
        start = time.monotonic()
        try:
            if len(X) > LEAK_ROWS:
                rows = np.sort(np.random.default_rng(0).choice(len(X), LEAK_ROWS, replace=False))
                X, target = X.iloc[rows], target.iloc[rows]
            made: dict[str, tuple[str, tuple[str, ...]]] = {}
            parts = []
            for group in groups:
                derived = group.transform(X)
                for name, sources in zip(group.names, group.sources, strict=True):
                    if not self._leaked.intersection(sources):
                        made[name] = (group.label, sources)
                        parts.append(derived[name].rename(name))
            if not parts:
                return
            found = training_leak_suspects(
                pd.concat(parts, axis=1),
                target,
                time_budget=max(secs - (time.monotonic() - start), 0.0),
            )
        except Exception:  # an advisory check must not stop a training run
            return
        if not found:
            return
        shown = found[:LEAK_SHOWN]
        listing = ", ".join(
            f"{s.column!r} (made of {' and '.join(repr(c) for c in made[s.column][1])}, "
            f"{made[s.column][0]}; {s.reason})"
            for s in shown
        )
        more = len(found) - len(shown)
        columns = list(dict.fromkeys(c for s in shown for c in made[s.column][1]))
        self._leaked.update(columns)  # the importance is by input column: named once
        self._notice(
            f"{len(found)} derived {'feature' if len(found) == 1 else 'features'} may give the "
            f"answer away: {listing}" + (f" and {more} more" if more > 0 else "") + ". The "
            "model leans on columns that together give the target, and at least one of them is "
            "probably not known when the model is used; check that every input is known at that "
            "time, and leave out one of the columns each is made of",
            kind="leak_suspects",
            columns=columns,
            features=[s.column for s in shown],
            reasons=[s.reason for s in shown],
            count=len(found),
        )

    def _notice_baseline(
        self, X: pd.DataFrame, y: np.ndarray, rows: np.ndarray, blended: np.ndarray, metric: str
    ) -> None:
        """Say what the numeric column most correlated with the target scores as the prediction,
        as it is, next to the model, on the validated rows where the column has a value and with
        the metric that ranks the models. It is told when the column was named as a leak suspect
        (a copy of the target at an earlier time is one, and the model may not beat it) and when
        the model does not beat it. A column off the target's scale is no prediction of it, so
        it is not scored. Advisory: a check that fails changes nothing."""
        try:
            numeric = X.select_dtypes("number").iloc[rows].reset_index(drop=True)
            column = numeric.corrwith(pd.Series(y)).abs().idxmax()
            guess = numeric[column].to_numpy("float64", na_value=np.nan)
            present = np.isfinite(guess)
            truth, guess, model = y[present], guess[present], blended[present]
            if len(truth) < BASELINE_MIN_ROWS or (
                np.mean((truth - guess) ** 2) >= BASELINE_ON_SCALE * truth.var()
            ):
                return
            copy = metrics.value(metric, truth, guess)
            ours = metrics.value(metric, truth, model)
        except Exception:
            return
        better = ours > copy if metric in metrics.HIGHER_IS_BETTER else ours < copy
        if not (np.isfinite(copy) and np.isfinite(ours)) or (better and column not in self._leaked):
            return
        self._notice(
            f"on the {len(truth):,} validated rows where {column!r} has a value, using it as the "
            f"prediction as it is scores {metric} {copy:.4g}, and the model scores {ours:.4g}"
            + (
                ""
                if better
                else f": the model does not beat {column!r}, so if it holds the target at an "
                "earlier time, or a near copy of it, that is the score to beat"
            ),
            kind="baseline",
            column=column,
            metric=metric,
            baseline_score=float(copy),
            model_score=float(ours),
        )

    def _notice_constant(
        self,
        y: np.ndarray,
        rows: np.ndarray,
        folds: Folds,
        blended: np.ndarray,
        metric: str,
        quantile: float | None,
        median_ran: bool = False,
    ) -> bool:
        """Say when the model does not beat, by ``CONSTANT_MARGIN``, a constant on the validated
        rows, in the metric that ranks the models: the median of the training part of each fold
        (for ``mae`` and ``medae``), or its ``quantile`` (for the pinball loss), which no model
        that has learned nothing beats. R-squared does not say it for these metrics (a model can
        have a positive one and a worse error than the median, as with a heavy-tailed target).
        Returns whether it was said. Advisory: a check that fails changes nothing."""
        if metric not in CONSTANT_METRICS or (quantile is not None and metric != "pinball"):
            return False  # a quantile fit aims at another quantity than the median
        try:
            level = quantile if metric == "pinball" else 0.5
            constant = np.full(len(rows), np.nan)
            for train, valid in folds:
                constant[np.searchsorted(rows, valid)] = np.quantile(y[train], level)
            truth = y[rows]
            seen = np.isfinite(constant)
            if seen.sum() < BASELINE_MIN_ROWS:
                return False
            kept = metrics.loss(metric, truth[seen], constant[seen], quantile=quantile)
            ours = metrics.loss(metric, truth[seen], blended[seen], quantile=quantile)
        except Exception:
            return False
        if not (np.isfinite(kept) and np.isfinite(ours)) or kept <= 0:
            return False
        if ours < (1 - CONSTANT_MARGIN) * kept:
            return False
        what = f"{level:g} quantile" if metric == "pinball" else "median"
        reason = (
            "the inputs may hold little of what this target needs, or the target is mostly noise, "
            "so more rows, other inputs or another target transform may help"
            if quantile is not None or median_ran
            else "the models learn the average, which a skewed target moves away from the "
            "median that this metric rewards (the quantile setting of the API at 0.5 learns the "
            "median directly), or the inputs hold little of what this target needs"
        )
        self._notice(
            f"the validated {metric} is {ours:.4g} against {kept:.4g} from predicting the {what} "
            f"of the training rows every time, which it does not beat by {CONSTANT_MARGIN:.0%}: "
            f"{reason}; a score this close to a constant can swing by chance between runs",
            kind="no_better_than_constant",
            metric=metric,
            model_score=float(ours),
            constant_score=float(kept),
        )
        return True

    def _fit_quality_notices(
        self,
        task: Task,
        model: TrainedModel,
        constant_said: bool = False,
        validated: np.ndarray | None = None,
    ) -> bool:
        """Say when the validated fit is suspiciously good or no better than the average: a
        column may give the answer away, or the features may not hold it. A quantile is not
        judged by R-squared or AUC, so it gets neither, and nor is a score of a time that may be
        cut short. The average is not named again when ``constant_said``. Of more than two
        classes only the log loss is judged, against that of the class shares of the
        ``validated`` classes (their codes). Returns whether a too-good score was said (or had
        been said already, of a column)."""
        if model.config.quantile is not None or model.config.event_column is not None:
            return False
        scores = model.metrics
        if task == "regression":
            skill, low, high = scores.get("r2"), NO_SKILL_R2, NEAR_PERFECT_R2
            name = "r2"
        elif len(model.classes_ or []) == 2:
            skill, low, high = scores.get("auc"), NO_SKILL_AUC, NEAR_PERFECT_AUC
            name = "auc"
        else:
            self._notice_no_class_skill(scores.get("logloss"), validated, constant_said)
            return False
        if skill is None or not np.isfinite(skill):
            return False
        if skill >= high:
            top = model.feature_importance.index[0]
            if top in self._leaked:  # named already, by ``_notice_leaks``
                return True
            self._notice(
                f"the validation {name} is {skill:.4f}, as good as it gets: a column may give the "
                f"answer away (the most used one is {top!r}) and not be known when the model is "
                "used; check that every input is known at that time",
                kind="near_perfect_fit",
                column=top,
                score=float(skill),
            )
            return True
        if (
            skill <= low
            and not constant_said
            and not self._ranked_off_scale(task, model)
            and not self._ranked_by_a_clear_correlation(task, model)
        ):
            self._notice(
                f"the validation {name} is {skill:.3f}: the model is hardly better than "
                "predicting the average, so the inputs may not hold what the target needs, or "
                "the target is mostly noise; a score this weak can swing by chance between "
                "runs",
                kind="no_skill",
                score=float(skill),
            )
        return False

    def _notice_no_class_skill(
        self, logloss: float | None, validated: np.ndarray | None, constant_said: bool
    ) -> None:
        """Say when the validated log loss of more than two classes is no better than that of
        predicting every class at its share of the rows (its entropy): the models have learned
        nothing, as when the input is a text that no text model had the time to read."""
        if constant_said or validated is None or logloss is None or not np.isfinite(logloss):
            return
        shares = np.bincount(validated) / len(validated)
        entropy = float(-np.sum(shares[shares > 0] * np.log(shares[shares > 0])))
        if entropy <= 0 or 1 - logloss / entropy > NO_SKILL_LOGLOSS:
            return
        self._notice(
            f"the validation log loss is {logloss:.3f}, no better than the {entropy:.3f} of "
            "predicting every class at its share of the rows: the models have learned almost "
            "nothing, so the inputs may not hold what the target needs, or a model that reads "
            "them (a text model for a text column) had no time, which a longer max_runtime_secs "
            "gives it",
            kind="no_skill",
            logloss=logloss,
            prior_logloss=entropy,
        )

    def _notice_small_data(self, task: Task, model: TrainedModel, rows: int, trials: int) -> None:
        """Say that a score from few rows and many trials is too good: every trial is scored on
        the same rows, so the best of them (and the blend of the best) is picked for its luck on
        them, and repeating the fit can score differently. Not for a quantile or a survival fit,
        which the fit-quality notices skip too."""
        if model.config.quantile is not None or model.config.event_column is not None:
            return
        if rows > SMALL_DATA_ROWS or trials < SMALL_DATA_TRIALS:
            return
        if task == "regression":
            off = "the validation error can be too low"
        elif len(model.classes_ or []) == 2:
            off = "the validation AUC can be 0.05 to 0.15 too high"
        else:
            off = "the validation score can be too high"
        self._notice(
            f"validated on only {rows} rows and picked among {trials} trials: {off}, and the "
            "same fit repeated can differ by about as much; trust a held-back test set more "
            "than this score",
            kind="small_data_optimism",
            rows=rows,
            trials=trials,
        )

    @staticmethod
    def _ranked_off_scale(task: Task, model: TrainedModel) -> bool:
        """Whether the models were ranked on another scale than the target's own units (a log
        target, or a relative error), where an R-squared near 0 in those units says little. A
        correlation ranks the models learned on the target as it is, so R-squared still judges."""
        if task != "regression":
            return False
        ranked = metrics.resolve(model.config.sort_metric, task, "sort_metric")
        on_scale = metrics.ORIGINAL_UNITS | metrics.CORRELATIONS
        return model.config.target_transform == "log1p" or ranked not in on_scale

    @staticmethod
    def _ranked_by_a_clear_correlation(task: Task, model: TrainedModel) -> bool:
        """Whether the models were ranked by a correlation that is clearly above 0 (a monotone
        target with heavy tails has an R-squared near 0 and a rank correlation far from it)."""
        if task != "regression":
            return False
        ranked = metrics.resolve(model.config.sort_metric, task, "sort_metric")
        rho = model.metrics.get(ranked) if ranked in metrics.CORRELATIONS else None
        return rho is not None and rho * rho > NO_SKILL_R2

    def _notice_dropped_columns(self, prep: Prep, X: pd.DataFrame) -> None:
        """Name the input columns the models cannot use: no value, or the same one on every row
        of the rows they learn from (whatever the rows to predict hold in them)."""
        if not prep.dropped:
            return
        empty = [c for c in prep.dropped if X[c].isna().all()]
        shown = ", ".join(repr(c) for c in prep.dropped[:DROPPED_SHOWN])
        more = len(prep.dropped) - DROPPED_SHOWN
        self._notice(
            f"{len(prep.dropped)} columns have one value or none on every row of the training "
            f"data and are left out: {shown}" + (f" and {more} more" if more > 0 else ""),
            kind="columns_left_out",
            columns=prep.dropped[:DROPPED_SHOWN],
            empty=len(empty),
        )

    def _cost_threshold(self, y: np.ndarray, blended: np.ndarray, positive) -> np.ndarray:
        """The prior of the threshold with the lowest cost on the validation predictions, and a
        notice with what that cost is per row against the most probable class."""
        miss, alarm = self.config.cost_miss, self.config.cost_false_alarm
        prior = metrics.tune_cost(y, blended, miss, alarm)
        fitted = metrics.cost_per_row(y, blended, prior, miss, alarm)
        argmax = metrics.cost_per_row(y, blended, None, miss, alarm)
        self._notice(
            f"decision 'cost': the class '{positive}' is predicted above a probability of "
            f"{prior[1]:.3g}; on the validation rows a miss (a row of '{positive}' given the "
            f"other class) costs {miss:g} and a false alarm {alarm:g}, which comes to "
            f"{fitted:.4g} per row (the most probable class: {argmax:.4g}); the threshold is "
            "chosen on the same rows, so it is somewhat optimistic",
            kind="decision_cost",
            positive_class=str(positive),
            threshold=float(prior[1]),
            cost_per_row=float(fitted),
            cost_per_row_argmax=float(argmax),
        )
        return prior

    def _zero_inflated_notice(self, y: np.ndarray) -> None:
        """Say when a target of 0 or more is almost always exactly 0: its score rests on the
        few other rows. A quantile is a level of its own, so it gets none."""
        if self.config.quantile is not None or len(y) == 0 or y.min() < 0:
            return
        share = float((y == 0).mean())
        if share >= ZERO_SHARE:
            self._notice(
                f"{share:.1%} of the target values are exactly 0, so the score rests on the few "
                "other rows. To find which rows are above 0, make a column that is 1 there and 0 "
                "elsewhere and classify it; a second model on the rows above 0 can then predict "
                "how much",
                kind="zero_inflated",
                zero_share=share,
            )

    def _target_scale_notices(self, y: np.ndarray, sort_metric: str) -> None:
        """Say when the target's scale and the ranking metric do not go together: a log target
        ranked in the original units, or a skewed one that is learned as it is while it is ranked
        in the original units or by a relative error that nothing weights. A quantile is learned
        as it is on purpose, so it gets none."""
        original = sort_metric in metrics.ORIGINAL_UNITS
        if self.config.quantile is not None or not (
            original or sort_metric in metrics.UNWEIGHTED_RELATIVE
        ):
            return
        if self.config.target_transform == "log1p":
            if original:
                self._notice(
                    f"the models learn the target as log1p, but sort_metric '{sort_metric}' "
                    "ranks them in the target's own units; to rank on the log scale, set "
                    "sort_metric to 'rmsle'",
                    kind="log_target_metric",
                )
        elif (skew := metrics.log1p_skew(y)) is not None:
            advice = (
                "if the score you care about is a relative or logarithmic error (such as "
                "RMSLE), set target_transform to 'log1p' and sort_metric to 'rmsle'"
                if original
                else f"set target_transform to 'log1p' to learn it as the '{sort_metric}' "
                "error is measured"
            )
            self._notice(
                f"the target is 0 or more and skewed (skewness {skew:.1f}), and a model that "
                "learns it as it is gives the many small values predictions far from them; "
                + advice,
                kind="skewed_target",
                skewness=skew,
            )

    def _notice(self, message: str, **data) -> None:
        self._event("notice", message=message, **data)

    def fit(self, df: pd.DataFrame, extra: pd.DataFrame | None = None) -> TrainedModel:
        """Train on ``df``, which holds the target column and the features.

        ``extra``: more rows of the same kind (the target and the input columns), which are only
        learned from: they join the training rows of every fold and of the final fit, and are
        never validated, so every score counts the rows of ``df`` alone (see ``extra_weight``).
        """
        deadline = Deadline(self.config.max_runtime_secs)
        start = time.monotonic()
        c = self.config
        if c.target not in df.columns:
            raise ConfigError(f"target column '{c.target}' is not in the data")
        unknown = [column for column in c.ignored_columns if column not in df.columns]
        if unknown:
            raise ConfigError(f"unknown columns in ignored_columns: {unknown}")
        survival = c.event_column is not None
        if survival and c.event_column not in df.columns:
            raise ConfigError(f"event column '{c.event_column}' is not in the data")
        if extra is not None and (survival or c.time_column is not None):
            raise ConfigError("extra rows cannot be used with an event_column or a time_column")
        not_features = [c.target, *c.ignored_columns, *([c.event_column] if survival else [])]
        own_df, own = df, len(df)
        if extra is not None:
            own_df = df.reset_index(drop=True)  # (numbered as the joined rows are)
        notices: list[Event] = []
        extra = None if extra is None else self._extra_rows(own_df, extra, not_features, notices)
        df = own_df if extra is None else pd.concat([own_df, extra], ignore_index=True)
        X = df.drop(columns=not_features)
        X_own = X.iloc[:own]
        target = own_df[c.target]  # (the notices and the label type are those of the own rows)
        task: Task = infer_task(target) if c.task == "auto" else c.task
        if c.quantile is not None and task != "regression":
            raise ConfigError("quantile needs a regression, but the target is a classification")
        if survival and task != "regression":
            raise ConfigError("event_column needs a regression, but the target is a classification")
        sort_metric = metrics.resolve(c.sort_metric, task, "sort_metric", c.quantile, survival)
        stopping_metric = metrics.resolve(
            c.stopping_metric, task, "stopping_metric", c.quantile, survival
        )
        y, classes, nfolds = validate_target(target, task, c.nfolds, notices.append)
        if extra is not None:
            y = np.concatenate([y, self._extra_target(extra[c.target], task, classes)])
        if c.quantile is not None:
            notices.append(
                Event(
                    "notice",
                    data={
                        "message": (
                            f"learning the quantile {c.quantile:g}: only "
                            f"{', '.join(self.families)} are searched, as the other families "
                            "cannot fit a quantile"
                        ),
                        "kind": "quantile_families",
                        "families": self.families,
                    },
                )
            )
        # Folds in time order are one fixed partition: another seed would not change them.
        # (repeats are paid for by the rows every fold fits, the extra rows included)
        repeats = 1 if c.time_column else c.cv_repeats or repeats_for(len(X))
        row_groups = extra_groups = None
        if c.cv_group_column is not None:
            if c.cv_group_column not in df.columns:
                raise ConfigError(f"cv_group_column '{c.cv_group_column}' is not in the data")
            # (the own rows' groups come first: they are numbered as they would be without extra)
            codes = pd.factorize(df[c.cv_group_column], use_na_sentinel=False)[0]
            row_groups, extra_groups = codes[:own], codes[own:]
            distinct = int(row_groups.max()) + 1
            if distinct < 2:
                raise ConfigError(
                    f"the group column '{c.cv_group_column}' needs at least 2 groups, "
                    f"it has {distinct}"
                )
            if distinct <= nfolds:
                repeats = 1  # each group is a fold: every seed gives the same partition
            if distinct < nfolds and c.time_column is None:
                nfolds = distinct
                notices.append(
                    Event(
                        "notice",
                        data={
                            "message": f"nfolds reduced to {nfolds}: only {distinct} groups",
                            "nfolds_reduced_to": nfolds,
                            "reason": f"only {distinct} groups",
                        },
                    )
                )
        self._event(
            "started",
            config=c.to_dict(),
            n_rows=own,
            n_extra_rows=len(X) - own,
            n_cols=X.shape[1],
            task=task,
            nfolds=nfolds,
            cv_repeats=repeats,
        )
        for notice in notices:
            self.emit(notice)
        weight = None
        if c.balance_classes and task == "regression":
            self._notice("balance_classes is ignored for regression")
        elif c.balance_classes:
            counts = np.bincount(y)
            weight = (len(y) / (len(counts) * counts))[y]
        if task == "regression" and sort_metric in metrics.RELATIVE_ERRORS:
            metrics.check(sort_metric, y, len(classes), "sort_metric")
            weight = metrics.relative_weight(y, sort_metric, c.target_transform == "log1p")
            self._notice(
                f"the rows are weighted by their share of {sort_metric}, in training "
                "and in the blend"
            )
        mix_weight = None  # the weights of the extra rows alone, for the class mix below
        if extra is not None and c.extra_weight != 1.0:  # (training only: scores stay unweighted)
            mix_weight = np.ones(len(y))
            mix_weight[own:] = c.extra_weight
            weight = mix_weight if weight is None else weight * mix_weight
        y_seen = y  # the target as the user gave it; ``y`` is what the models learn
        if survival:
            # the time and the event flag, in two columns so that a metric reads both; the
            # curve is that of every training row (it holds no row's own prediction)
            event = _event_flags(df[c.event_column], c.event_column, y)
            y_seen = np.column_stack([y, event])
            y = km_target(y, event)
            self._notice(
                f"the prediction is a score from 0 to 1 that grows with '{c.target}': a higher "
                "score is a longer time, and it is not a time in its units",
                kind="survival_score",
                target=c.target,
            )
        if c.target_transform == "log1p" and task == "classification":
            self._notice("target_transform is ignored for classification")
        elif c.target_transform == "log1p" and not survival:
            if (y <= -1).any():
                raise ConfigError("target_transform 'log1p' needs target values above -1")
            y = np.log1p(y)
        if task == "regression" and not survival:
            if c.task == "auto" and c.quantile is None:
                self._notice_class_codes(y_seen[:own])
            self._zero_inflated_notice(y_seen[:own])
            self._target_scale_notices(y_seen[:own], sort_metric)
        # What is reported and ranked is in the target's own units.
        original = np.expm1 if y is not y_seen and not survival else _same
        for field, name in (("sort_metric", sort_metric), ("stopping_metric", stopping_metric)):
            metrics.check(name, y_seen, len(classes), field)
        prior = None
        tuned = c.decision == "tuned" and task == "classification"
        cost = c.decision == "cost" and task == "classification"
        if c.decision in ("balanced", "tuned", "cost") and task == "regression":
            self._notice("decision is ignored for regression")
        elif c.decision == "balanced":
            prior = _learned_mix(y, mix_weight, len(classes))
        elif tuned:  # the threshold is fitted on the final blend, after the search
            metrics.check_tuned(sort_metric, len(classes))
        elif cost:  # as is this one, whatever the metric that ranks the models
            metrics.check_cost(len(classes))
        elif sort_metric == "qwk" and 2 < len(classes) <= metrics.MAX_ORDINAL_CLASSES:
            self._notice(
                "qwk at the most probable class is far below what the same probabilities give "
                "with cut points fitted to the order of the classes: set decision to tuned",
                kind="ordinal_decision",
            )
        # balanced_logloss ranks the probabilities as if every class were as common as the others:
        # the model delivers them so (the label is then the largest of them)
        shift = None
        if task == "classification" and sort_metric == "balanced_logloss":
            shift = _learned_mix(y, mix_weight, len(classes))
            # every score, the blend's, the diagnostics and the OOF predictions are of the
            # probabilities as delivered
            original = lambda p: metrics.shift_to_equal_priors(p, shift)  # noqa: E731
            if prior is not None:
                self._notice(
                    "decision is ignored: the probabilities are shifted to equal class "
                    "priors, which is the balanced decision",
                    kind="decision_ignored",
                )
                prior = None
        # whole ratings: the cut points of rounded_qwk are fitted on the final blend
        ratings = np.unique(y_seen) if task == "regression" and sort_metric == "rounded_qwk" else ()
        rating_cuts = 3 <= len(ratings) <= metrics.MAX_ORDINAL_CLASSES and bool(
            (ratings == np.round(ratings)).all()
        )
        if c.time_column is None and c.quantile is None:
            groups, tried = self._engineer(X_own, y[:own], task, nfolds, deadline, row_groups)
        else:  # the gate judges a feature on shuffled folds (the future) and on squared error
            groups, tried = [], None
            if c.feature_engineering:
                self._notice(
                    "derived features are not tried with a time column"
                    if c.time_column
                    else "derived features are not tried with a quantile"
                )
        prep = Prep().fit(X, groups, y, trend=c.time_column)
        self._notice_dropped_columns(prep, X)
        self._notice_time_trend(prep)
        self._leaked = set()
        leak_secs = min(LEAK_SECS, LEAK_SHARE * max(deadline.remaining(), 0.0))
        leak_start = time.monotonic()
        self._notice_leaks(prep, X_own, target, leak_secs)
        self._notice_derived_leaks(
            prep, X_own, target, max(leak_secs - (time.monotonic() - leak_start), 0.0)
        )
        dates: list[str] = []
        if c.time_column is None:
            dates = [column for column in prep.columns if prep.kind_of(column) == "datetime"]
            # whole numbers that are dates (20141021, 14102100) or Unix times order the rows too
            dates += [column for column in prep.columns if column in prep.integer_dates]
            if dates:
                self._notice(
                    f"{', '.join(repr(d) for d in dates[:3])} holds dates, and no time_column is "
                    "given, so the validation shuffles the rows. If the model will predict rows "
                    "later than the ones it learns from, the score is probably better than it "
                    "will be; name that column as time_column to validate on later parts",
                    kind="time_hint",
                    columns=dates[:3],
                )
            if row_groups is None:
                if not self._notice_repeated_values(prep, X_own) and not self._notice_repeated_rows(
                    prep, X_own
                ):
                    self._notice_repeated_texts(prep, X_own)
                if (
                    not dates
                    and not self._notice_sorted_column(prep, X_own)
                    and not self._notice_time_index(prep, X_own)
                ):
                    if task == "regression" and not survival:
                        self._notice_ordered_target(y_seen[:own])
                    elif task == "classification":
                        self._notice_ordered_target(y[:own], classes=True)
            # the folds are drawn over the own rows; the extra rows join every fold's training side
            folds = repeat_folds(y[:own], task, nfolds, c.seed, row_groups, repeats)
            if row_groups is not None and task == "classification":
                self._check_classes_in_training(y[:own], folds, classes)
            if extra is not None:
                folds = _with_extra_rows(folds, own, len(y) - own, row_groups, extra_groups)
            first_run = folds[:nfolds]  # reported: the other repeats only judge the search
        else:
            few = {}
            if row_groups is not None:
                few["few_message"] = (
                    f"the groups of '{c.cv_group_column}' end at too few different values of "
                    f"'{c.time_column}' to make validation parts (groups that stay over the "
                    "whole range need the group column without the time column)"
                )
            times = _time_values(df, c.time_column)
            order = pd.factorize(times, sort=True)[0].astype(np.int64)
            folds = first_run = make_time_folds(order, y, task, nfolds, row_groups, **few)
            self._notice_time_parts(times, folds, len(y))
            if row_groups is not None:
                self._notice_lopsided_parts(folds, len(y), nfolds)
        if task == "regression" and not survival and c.quantile is None:
            self._notice_missing_history(
                own_df, X_own, y_seen[:own], c.time_column or next(iter(dates), None)
            )
        rows = covered(folds, len(y))  # the rows some fold predicts (all but the first part)
        families = self._without_wide_linear_view(prep, len(X))
        # The words are read only from prose columns.
        families = [
            f for f in families if f not in ("TextLinear", *OPT_IN_ORDER) or prep.prose
        ] or (families)
        if "TextEmbedding" in families and not prep.prose:
            raise ConfigError("TextEmbedding needs a column of text, and the data has none")
        # An explicit list of late families only is run as it is, like TextLinear above.
        late = self._late_families(prep, X, y, task) if families else self.late
        # The L1 variants run when asked for, or for a regression ranked by an absolute error.
        median = task == "regression" and not survival and c.quantile is None
        if self.median and self.explicit and not median:
            raise ConfigError(
                f"{', '.join(self.median)} learn the median of a regression with no quantile and "
                "no event column"
            )
        if median and (self.explicit or sort_metric in MEDIAN_METRICS):
            late = [*late, *self.median]
        families = [*families, *late]
        if "TextEmbedding" in families:
            self._embed_rows(prep, X)
        if prep.reads_only_prose and not self.explicit:
            families = self._text_families_only(families)

        left = deadline.remaining()
        reserve = max(MIN_RESERVE_SECS, RESERVE_SHARE * left)
        # (the search's own score is squared error of the learned score, not the concordance)
        default_stopping = not survival and stopping_metric == metrics.automatic(task, c.quantile)
        results, logs, reasons, finished, errors = self._search(
            families,
            X,
            y,
            folds,
            task,
            prep,
            deadline.child(SEARCH_SHARE * left),
            None
            if default_stopping
            else (
                lambda oof: metrics.loss(
                    stopping_metric, y_seen[rows], original(oof[rows]), prior, c.quantile
                )
            ),
            weight,
            repeats,
        )
        stop_reason = self._stop_reason(reasons, finished)
        if not results:
            if stop_reason == "cancelled":
                raise NoModelError("cancelled before any model was trained")
            if errors:
                listing = "; ".join(
                    f"{name}: {type(e).__name__}: {str(e)[:300]}" for name, e in errors.items()
                )
                raise NoModelError(f"no model could be trained: {listing}") from list(
                    errors.values()
                )[-1]
            raise NoModelError("time budget too small to train any model")
        self._event("stopped", reason=stop_reason)

        oof = {name: result.oof[rows] for name, result in results.items()}
        y_valid = y[rows]
        # The weights are chosen on every repeat's predictions, one below the other.
        stacked = {name: result.stacked(rows) for name, result in results.items()}
        blend_metric = None
        if task == "regression" and sort_metric in metrics.BLEND_ON_METRIC:
            blend_metric = lambda y, p: metrics.loss(  # noqa: E731
                sort_metric, original(y), original(p), None, c.quantile
            )
        weights = caruana(
            stacked, np.tile(y_valid, repeats), task, metric=blend_metric, quantile=c.quantile
        )
        scores = {
            name: metrics.value(sort_metric, y_seen[rows], original(p), prior, c.quantile)
            for name, p in oof.items()
        }
        pick = max if sort_metric in metrics.HIGHER_IS_BETTER else min
        # (a tuned decision has no threshold yet: these progress scores count at argmax)
        ensemble_score = metrics.value(
            sort_metric, y_seen[rows], original(_blend(oof, weights)), prior, c.quantile
        )
        self._event(
            "ensemble",
            sort_metric=sort_metric,
            weights=weights,
            scores=scores,
            ensemble_score=ensemble_score,
            best_single=pick(
                {k: v for k, v in scores.items() if np.isfinite(v)} or scores, key=scores.get
            ),
        )

        refit = deadline.child(deadline.remaining() - reserve)
        members, refit_secs = self._members(
            results,
            weights,
            X,
            y,
            prep,
            Clock(refit, self.should_stop),
            weight,
            stop_reason,
            (sort_metric, scores, ensemble_score),
        )
        if self.should_stop():
            stop_reason = "cancelled"
        final = {member.key: member.weight for member in members}
        blended = original(_blend(oof, final))
        if tuned or rating_cuts:
            prior = metrics.tune_prior(sort_metric, y_seen[rows], blended)
        elif cost:
            prior = self._cost_threshold(y_seen[rows], blended, classes[1])
        try:
            # (the diagnostics read one target column: a survival fit has none in its own units)
            found = (
                None
                if survival
                else diagnostics(task, y_seen[rows], blended, classes, seed=c.seed, prior=prior)
            )
        except Exception as e:
            found = None
            self._notice(
                f"the training diagnostics could not be computed: {str(e)[:300]}",
                kind="diagnostics_error",
                exception=type(e).__name__,
            )
        # the folds' rows, counted among the validated rows only
        at = [(None, np.searchsorted(rows, valid)) for _, valid in first_run]
        leaderboard = _leaderboard(
            results,
            final,
            refit_secs,
            blended,
            y_seen[rows],
            at,
            sort_metric,
            original,
            prior,
            rows,
            tuned or rating_cuts,
            c.quantile,
        )
        assignment = np.full(own, -1, dtype=np.int64)  # -1: never validated
        for i, (_, valid) in enumerate(first_run):
            assignment[valid] = i
        model = TrainedModel(
            task=task,
            target=c.target,
            classes_=classes if task == "classification" else None,
            columns=prep.columns,
            leaderboard=leaderboard,
            trials=pd.DataFrame(logs, columns=TRIAL_COLUMNS),
            feature_importance=feature_importance(members, prep),
            stop_reason=stop_reason,
            config=c,
            metrics=metrics.summary(task, y_seen[rows], blended, prior, c.quantile),
            prep=prep,
            members=members,
            label_dtype=target.dtype,
            cv_predictions=_spread(blended, rows, own) if c.keep_cv_predictions else None,
            cv_models={n: r.models for n, r in results.items() if "#" not in n}
            if c.keep_cv_models
            else None,
            fold_assignment=assignment if c.keep_cv_fold_assignment else None,
            diagnostics=found,
            features=tried,
            class_prior=prior,
            proba_shift=shift,
            target_floor=0.0
            if task == "regression" and not survival and not rating_cuts and y_seen[:own].min() >= 0
            else None,
        )
        if task == "regression" and not survival and c.quantile is None and not rating_cuts:
            self._notice_baseline(X, y_seen[rows], rows, blended, sort_metric)
        named = self._notice_frequency_encoded_values(prep, X_own, model.feature_importance)
        self._notice_group_column_input(X_own, model.feature_importance, named)
        median_ran = any(member.spec.median for member in members)
        said = self._notice_constant(
            y_seen, rows, first_run, blended, sort_metric, c.quantile, median_ran
        )
        # (the constant is the verdict of a ranking by an absolute error, not the R-squared)
        judged = sort_metric in CONSTANT_METRICS and (
            c.quantile is None or sort_metric == "pinball"
        )
        too_good = self._fit_quality_notices(
            task, model, constant_said=said or judged, validated=y_seen[rows]
        )
        if not too_good:  # a score that good is the news, whatever the rows
            self._notice_small_data(task, model, len(rows), finished)
        self._event(
            "finished",
            stop_reason=stop_reason,
            elapsed=time.monotonic() - start,
            leaderboard_top=leaderboard.head(3).to_dict("records"),
            metrics=model.metrics,
        )
        return model

    @staticmethod
    def _feature_secs(left: float) -> float:
        return max(FEATURE_SHARE * left, min(FEATURE_MIN_SECS, FEATURE_MAX_SHARE * left))

    def _engineer(
        self, X, y, task, nfolds, deadline, row_groups=None
    ) -> tuple[list, list[dict] | None]:
        """The derived-feature groups to add and the verdict on every candidate (None when
        switched off). The choice gets at most ``FEATURE_SHARE`` of the time, or of a short run
        ``FEATURE_MIN_SECS`` (but under ``FEATURE_MAX_SHARE``)."""
        if not self.config.feature_engineering:
            return [], None
        if X.shape[1] > FEATURE_MAX_COLUMNS and kept_columns(X) > FEATURE_MAX_COLUMNS:
            self._notice(
                f"derived features are not tried on a table of more than "
                f"{FEATURE_MAX_COLUMNS:,} columns"
            )
            return [], None
        try:
            kept, verdicts = select_groups(
                X,
                y,
                task,
                nfolds,
                self.config.seed,
                deadline.child(self._feature_secs(deadline.remaining())),
                self.should_stop,
                row_groups,
            )
        except Exception as e:  # the base features still train
            self.emit(error_notice("features_error", "features", e))
            return [], None
        tried = [v.to_dict() for v in verdicts]
        adopted = [v["group"] for v in tried if v["adopted"]]
        unjudged = [v["group"] for v in tried if not v["adopted"] and v.get("reason") == "time"]
        message = "derived features: " + (", ".join(adopted) if adopted else "none added")
        if unjudged:
            names = ", ".join(unjudged[:DROPPED_SHOWN])
            if len(unjudged) > DROPPED_SHOWN:
                names += f" and {len(unjudged) - DROPPED_SHOWN} more"
            message += (
                f"; {len(unjudged)} of {len(tried)} groups were not judged for lack of time: "
                f"{names} (a longer max_runtime_secs lets the search judge them)"
            )
        self._notice(
            message, kind="features", groups=tried, unjudged=len(unjudged), unjudged_groups=unjudged
        )
        counted = [group.label for group in kept if group.density]
        if counted and row_groups is not None:
            self._notice(
                f"{', '.join(counted)} count rows: the derived features were checked with the "
                "counts of the other groups only, but the validation scores read the counts of "
                "all the training rows, those of each validation group's own rows included, so "
                "they may be better than the model does on rows of new groups",
                kind="counts_in_validation",
                groups=counted,
            )
        return kept, tried

    def _without_wide_linear_view(self, prep: Prep, n_rows: int) -> list[str]:
        """``self.families`` without those that read the linear view when it would be too big
        (unless that leaves none)."""
        if n_rows * prep.linear_width <= LINEAR_MAX_CELLS:
            return self.families
        kept = [
            name for name in self.families if not FAMILIES[name].view.startswith(("linear", "text"))
        ]
        if not kept or kept == self.families:
            return self.families
        left_out = [name for name in self.families if name not in kept]
        self._notice_wide_linear_view(left_out, prep, n_rows)
        return kept

    def _extra_rows(
        self, own: pd.DataFrame, extra: pd.DataFrame, not_features: list[str], notices: list[Event]
    ) -> pd.DataFrame | None:
        """The ``extra`` rows as they join the training: only the columns the models read (and the
        group column), typed as in ``own``, without the rows whose inputs an own row has too (such
        a row would be learned from in a fold that validates its twin, and the score would be too
        good); None when nothing is left. A column the rows lack, or a value that does not fit the
        column's type, is a ``ConfigError``."""
        c = self.config
        inputs = [name for name in own.columns if name not in not_features]
        group = c.cv_group_column
        wanted = [c.target, *inputs]
        missing = [name for name in wanted if name not in extra.columns]
        if missing:
            raise ConfigError(
                f"the extra rows lack columns of the data: {', '.join(map(str, missing[:5]))}"
                + (f" and {len(missing) - 5} more" if len(missing) > 5 else "")
            )
        keep = [*wanted, *([group] if group in extra.columns and group not in wanted else [])]
        extra = extra[keep].reset_index(drop=True)
        for name in keep:
            extra[name] = _typed_like(own[name], extra[name], name)
        if group is not None and group not in extra.columns:
            extra[group] = np.nan
            notices.append(
                Event(
                    "notice",
                    data={
                        "message": f"the extra rows have no column '{group}', so none of them is "
                        "held out with a group: they are learned from in every fold",
                        "kind": "extra_without_group",
                    },
                )
            )
        twin = pd.util.hash_pandas_object(extra[inputs], index=False).isin(
            pd.util.hash_pandas_object(own[inputs], index=False)
        )
        if twin.any():
            notices.append(
                Event(
                    "notice",
                    data={
                        "message": f"{int(twin.sum()):,} of {len(extra):,} extra rows hold the "
                        "same inputs as a row of the data and are left out, as the validation "
                        "would find them learned",
                        "kind": "extra_duplicates",
                        "dropped": int(twin.sum()),
                    },
                )
            )
            extra = extra[~twin].reset_index(drop=True)
        if not len(extra):
            notices.append(
                Event(
                    "notice",
                    data={"message": "no extra row is left to learn from", "kind": "extra_rows"},
                )
            )
            return None
        notices.append(
            Event(
                "notice",
                data={
                    "message": f"{len(extra):,} extra rows join the training rows of every fold "
                    f"and of the final fit (weight {c.extra_weight:g}); the scores count the "
                    f"{len(own):,} rows of the data only",
                    "kind": "extra_rows",
                    "rows": len(extra),
                },
            )
        )
        return extra

    @staticmethod
    def _extra_target(values: pd.Series, task: Task, classes: list) -> np.ndarray:
        """The target of the extra rows as ``validate_target`` coded the data's: class codes for
        labels the data has, floats for a regression."""
        if values.isna().any():
            raise ConfigError("the extra rows have a target with missing values")
        if task == "regression":
            try:
                coded = pd.to_numeric(values).to_numpy(dtype=float)
            except (TypeError, ValueError) as e:
                raise ConfigError("the target of the extra rows must be numeric") from e
            if not np.isfinite(coded).all():
                raise ConfigError("the extra rows have an infinite target")
            return coded
        coded = pd.Index(classes).get_indexer(values)
        if (coded < 0).any():
            unknown = list(dict.fromkeys(values[coded < 0].astype(str)))
            raise ConfigError(
                "the extra rows have labels the data lacks, which could not be validated: "
                + ", ".join(unknown[:5])
            )
        return coded.astype(np.int64)

    def _text_families_only(self, families: list[str]) -> list[str]:
        """``families`` without those that read a view of no more than a constant (see
        ``Prep.reads_only_prose``), unless that leaves none."""
        kept = [name for name in families if FAMILIES[name].view.startswith("text")]
        if not kept or kept == families:
            return families
        self._notice(
            f"{', '.join(n for n in families if n not in kept)} left out: the only input is "
            "text, which only the text families read",
            kind="families_left_out",
            families=[n for n in families if n not in kept],
        )
        return kept

    def _notice_wide_linear_view(self, left_out: list[str], prep: Prep, n_rows: int) -> None:
        self._notice(
            f"{', '.join(left_out)} left out: the one-hot encoded data "
            f"({n_rows:,} rows x {prep.linear_width:,} columns = {n_rows * prep.linear_width:,} "
            f"cells) would take too much memory; the limit is {LINEAR_MAX_CELLS:,} cells",
            kind="families_left_out",
            families=left_out,
        )

    def _embed_rows(self, prep: Prep, X: pd.DataFrame) -> None:
        """Fill the cache with the vectors of every prose text, once, before the search: the
        trials then only read it. A backend that cannot run stops the training here."""
        spec = self.config.embedding
        view = prep.text_prose(X)
        texts = pd.concat([view[c] for c in view.columns])
        todo = embedding.missing(spec, texts.tolist())
        if not todo:
            return
        self._notice(
            f"embedding {todo:,} texts with {spec.model} (layer {spec.layer:g}): the vectors are "
            "computed once and kept in the cache",
            kind="embedding_rows",
            rows=todo,
        )
        embedding.embed_texts(
            spec,
            texts.tolist(),
            lambda done, total: self._event("embedding", done=done, total=total),
        )

    def _late_families(self, prep: Prep, X, y, task: Task) -> list[str]:
        """The late families this data suits, whose models would not be too big, and whose view
        is not too wide (see ``_without_wide_linear_view``)."""
        if len(X) * prep.linear_width > LINEAR_MAX_CELLS:
            left_out = [name for name in self.late if FAMILIES[name].applies(prep, X)]
            if left_out:
                self._notice_wide_linear_view(left_out, prep, len(X))
            return []
        outputs = int(y.max()) + 1 if task == "classification" else 1
        outputs = 1 if outputs == 2 else outputs
        late = [
            name
            for name in self.late
            if FAMILIES[name].applies(prep, X)
            and FAMILIES[name].coef_bytes(prep, outputs) <= SIZE_CAP
        ]
        # The character n-grams are the one variant left out for the length of the text alone.
        if (
            "TextLinearChar" in self.late
            and FAMILIES["TextLinear"].applies(prep, X)
            and not FAMILIES["TextLinearChar"].applies(prep, X)
        ):
            self._notice(
                "TextLinearChar left out: the text is too long for character n-grams, or a "
                "column has no spaces",
                kind="families_left_out",
                families=["TextLinearChar"],
            )
        return late

    def _search(
        self, families, X, y, folds, task, prep, search: Deadline, stopping_score, weight, repeats=1
    ):
        """Run the families in order, the late ones last; returns (results with models, trial
        rows, end reason per family, finished trial count, exception per failed family)."""
        c = self.config
        results: dict[str, FamilyResult] = {}
        logs: list[dict] = []
        reasons: dict[str, str] = {}
        errors: dict[str, Exception] = {}
        finished = 0
        skipped: list[str] = []  # late families not run for lack of time
        # With late families to run, the base ones share the search time less ``LATE_SHARE``:
        # their shares are scaled by 1 - LATE_SHARE; what they leave unused is left over too.
        # The family a late one is a variant of keeps its share as without late families.
        # With no base family (an explicit list of late ones) they have all of it.
        keep = any(f in LATE_ORDER for f in families) and any(f not in LATE_ORDER for f in families)
        base = search.child((1 - LATE_SHARE) * search.remaining()) if keep else search
        references = {
            FAMILIES[f].reference for f in families if f in LATE_ORDER and FAMILIES[f].keeps_share
        }
        for i, name in enumerate(families):
            if self.should_stop():
                reasons[name] = "cancelled"
                break
            late = name in LATE_ORDER
            # The late families take no trials from the others: a family only counts those of
            # its own kind after it.
            rest = [f for f in families[i:] if (f in LATE_ORDER) == late]
            max_trials = None
            if c.max_models is not None:
                if finished >= c.max_models:
                    break
                # Leave one trial for each family after this one.
                max_trials = max(1, c.max_models - finished - (len(rest) - 1))
            weights = LATE_WEIGHTS if late else {**FAMILY_WEIGHTS, **OPT_IN_WEIGHTS}
            own = search if late or name in references else base
            left = own.remaining()
            share = left * weights[name] / sum(weights[f] for f in rest)
            if late and not _late_fits(FAMILIES[name], share, results, self.explicit):
                # Without the reference result there was no estimate: not a matter of time.
                if FAMILIES[name].reference in results:
                    skipped.append(name)
                continue
            # A base family's first trial may take more than the family's share (up to
            # ``FIRST_TRIAL_SHARE`` of the time left): the cheap linear family comes first, then
            # the boosting ones by priority, each finishing a trial while those after it get
            # what remains.
            allowed = share if late else max(share, FIRST_TRIAL_SHARE * left)
            try:
                result = run_family(
                    name,
                    X,
                    y,
                    folds,
                    task,
                    prep,
                    own.child(share),
                    self.emit,
                    self.should_stop,
                    seed=c.seed,
                    max_trial_secs=c.max_runtime_secs_per_model,
                    max_trials=max_trials,
                    stopping_rounds=c.stopping_rounds,
                    stopping_tolerance=c.stopping_tolerance,
                    stopping_score=stopping_score,
                    sample_weight=weight,
                    repeats=repeats,
                    first_deadline=None if late else own.child(allowed),
                    quantile=c.quantile,
                    embedding=c.embedding,
                )
            except NoModelError as e:
                if late:
                    skipped.append(name)
                else:
                    reasons[name] = "time"
                    self._notice(_no_time_message(name, allowed, e.needed_secs), family=name)
                continue
            except Exception as e:  # outside any trial, e.g. building the view
                self.emit(error_notice("family_error", name, e))
                reasons[name], errors[name] = "error", e
                continue
            if result.error is not None:
                errors[name] = result.error
            finished += result.trials
            if not (late and result.reason == "time"):  # a late family is meant to use what is left
                reasons[name] = result.reason
            logs += [
                {**{k: row[k] for k in TRIAL_COLUMNS[:-1]}, "params": json.dumps(row["params"])}
                for row in result.log
            ]
            if result.models:
                results[name] = result
                for rank, runner_up in enumerate(result.runners_up, start=2):
                    results[f"{name}#{rank}"] = runner_up
            if result.reason == "cancelled":
                break
        if skipped:
            self._notice(
                f"{', '.join(skipped)}: not run, the search time left was too short for a first "
                "trial",
                family=skipped[0],
            )
        return results, logs, reasons, finished, errors

    def _check_classes_in_training(self, y, folds, classes) -> None:
        """Group folds do not balance the classes: a class that lives in a single group is
        missing from the training rows of its fold, and several families then fail on it."""
        for train, valid in folds:
            missing = np.setdiff1d(np.unique(y[valid]), np.unique(y[train]))
            if len(missing):
                raise ConfigError(
                    f"class {classes[int(missing[0])]!r} occurs in too few groups of "
                    f"'{self.config.cv_group_column}' to be in the training rows of every fold; "
                    "choose another group column or leave it empty"
                )

    def _stop_reason(self, reasons: dict[str, str], finished: int) -> str:
        ends = set(reasons.values())
        if self.should_stop() or "cancelled" in ends:
            return "cancelled"
        if self.config.max_models is not None and finished >= self.config.max_models:
            return "max_models"
        if "time" in ends:
            return "time"
        if "error" in ends:
            return "error"
        return "no_improvement"  # each family stagnated (or used the trials it was allotted)

    def _drop(self, member: Member, why: str, ranked=None) -> None:
        name = member.key or member.spec.name  # "LightGBM#2" for a runner-up
        metric, scores, ensemble = ranked or ("", {}, float("nan"))
        alone = scores.get(name, float("nan"))
        if np.isfinite(alone) and np.isfinite(ensemble):
            why += f"; alone it scored {metric} {alone:.4g} in CV, the ensemble {ensemble:.4g}"
        self._notice(f"{name} dropped from the ensemble: {why}", family=member.spec.name)

    def _cut(self, member: Member, size: int, budget: int, why: str) -> int | None:
        """Cut a forest member to its first trees so that its models take at most ``budget``
        bytes, the same share of the trees in each model. The member gets copies of its models:
        the fold models and the models of the search stay whole. Returns the new size, or None
        (and leaves the member as it is) when the member is not a forest or would keep less
        than ``MIN_TREE_SHARE`` of its trees."""
        spec, models = member.spec, member.models
        if not spec.shrinkable or budget <= 0:
            return None
        cumulative = [np.cumsum(spec.tree_sizes(m)) for m in models]
        share = budget / size
        for _ in range(20):  # the trees differ in size: look again at the size really kept
            keep = [max(1, int(len(c) * share)) for c in cumulative]
            kept_size = sum(int(c[k - 1]) for c, k in zip(cumulative, keep, strict=True))
            if kept_size <= budget:
                break
            share *= budget / kept_size * 0.99
        else:
            return None
        if any(
            k < math.ceil(MIN_TREE_SHARE * len(c)) for c, k in zip(cumulative, keep, strict=True)
        ):
            return None
        member.models = [spec.cut(m, k) for m, k in zip(models, keep, strict=True)]
        name = member.key or spec.name
        self._notice(
            f"{name} was cut to {sum(keep)} of {sum(len(c) for c in cumulative)} trees "
            f"to fit the size limit: {why}",
            family=spec.name,
        )
        return kept_size

    def _members(self, results, weights, X, y, prep, clock, weight, stop_reason, ranked=None):
        """Final members, heaviest first, and the refit time per family. ``ranked`` is the ranking
        metric, each candidate's CV score and the ensemble's, for the notice of a dropped member."""
        ahead = self.config.time_column is not None
        views: dict[str, pd.DataFrame] = {}
        chosen = sorted((n for n in results if weights[n] > 0), key=lambda n: -weights[n])
        candidates, refit_secs = [], {}
        members_of: dict[str, list] = {}
        refitted: set[str] = set()
        for name in chosen:
            result = results[name]
            # time-ordered fold models learned from 1/(k+1) to k/(k+1) of the rows: only
            # the last, with the most, stands in when there is no refit
            models = result.models[-1:] if ahead else result.models
            if stop_reason != "cancelled" and not self.should_stop() and result.spec.refit:
                start = time.monotonic()
                model, problem = _refit(result, X, y, prep, views, clock, weight, ahead=ahead)
                refit_secs[name] = time.monotonic() - start
                if model is not None:
                    models = [model]
                    refitted.add(name)
                elif isinstance(problem, Exception):
                    self.emit(error_notice("refit_error", result.spec.name, problem))
                else:
                    why = (
                        "was cancelled"
                        if problem == "cancelled"
                        else "did not fit in the time left"
                    )
                    self._notice(
                        f"{name}: the final refit {why}; using its "
                        f"{len(models)} fold model{'s' if len(models) != 1 else ''}",
                        family=result.spec.name,
                    )
            members_of[name] = models
        self._bag(
            results, chosen, members_of, refitted, refit_secs, X, y, prep, views, clock, weight
        )
        for name in chosen:
            result, models = results[name], members_of[name]
            size = sum(result.spec.size_bytes(m) for m in models)
            candidates.append((Member(result.spec, weights[name], models, name), size))
        kept, cut_once = [], set()
        for member, size in candidates:
            why = f"its model would take about {_mb(size)} (limit {_mb(SIZE_CAP)})"
            if size > SIZE_CAP:
                size = self._cut(member, size, SIZE_CAP, why)
                if size is None:
                    self._drop(member, why, ranked)
                    continue
                cut_once.add(member.key)
            kept.append((member, size))
        while len(kept) > 1 and sum(size for _, size in kept) > TOTAL_SIZE_CAP:
            together = sum(size for _, size in kept)
            member, size = kept.pop()  # the lightest weight
            why = (
                f"the members would take about {_mb(together)} together "
                f"(limit {_mb(TOTAL_SIZE_CAP)})"
            )
            room = TOTAL_SIZE_CAP - (together - size)  # what the others leave it
            # (a forest is cut once: a second cut could leave it less than MIN_TREE_SHARE)
            cut = None if member.key in cut_once else self._cut(member, size, room, why)
            if cut is None:
                self._drop(member, why, ranked)
            else:
                kept.append((member, cut))
        if not kept:
            kept = [candidates[0]]
            self._notice(
                f"{kept[0][0].key} kept although it exceeds the size limit: no smaller member",
                family=kept[0][0].spec.name,
            )
        kept = [member for member, _ in kept]
        total = sum(member.weight for member in kept)
        for member in kept:
            member.weight /= total
            member.models = [member.spec.serving(model) for model in member.models]
        return kept, refit_secs

    def _bag(
        self, results, chosen, members_of, refitted, refit_secs, X, y, prep, views, clock, weight
    ):
        """Refit the members that were refit once more, with other seeds, while the time and the
        size limits allow it (heaviest member first, one extra model each per round). An extra
        model is kept only if, at its real size, the member and all the members still fit."""
        sizes = {n: sum(results[n].spec.size_bytes(m) for m in members_of[n]) for n in chosen}
        first_secs = dict(refit_secs)
        for extra in range(1, BAG_EXTRA + 1):
            for name in chosen:
                spec = results[name].spec
                if name not in refitted or not spec.seeded:
                    continue
                if self.should_stop() or clock.remaining() < BAG_TIME_FACTOR * first_secs[name]:
                    continue
                estimate = spec.size_bytes(members_of[name][0])  # a forest's size varies by seed
                if (
                    sizes[name] + estimate > SIZE_CAP
                    or sum(sizes.values()) + estimate > TOTAL_SIZE_CAP
                ):
                    continue
                start = time.monotonic()
                model, problem = _refit(
                    results[name],
                    X,
                    y,
                    prep,
                    views,
                    clock,
                    weight,
                    extra,
                    self.config.time_column is not None,
                )
                refit_secs[name] += time.monotonic() - start
                if isinstance(problem, Exception):
                    self.emit(error_notice("refit_error", spec.name, problem))
                if model is None:
                    continue
                real = spec.size_bytes(model)
                if sizes[name] + real <= SIZE_CAP and sum(sizes.values()) + real <= TOTAL_SIZE_CAP:
                    members_of[name].append(model)
                    sizes[name] += real


def _late_fits(
    spec: type[FamilySpec], share: float, results: dict[str, FamilyResult], explicit: bool
) -> bool:
    """Whether the first trial of a late family is expected to fit in ``share``: ``spec.cost``
    times the first trial of its reference family (a first trial is never interrupted). Without
    that family's result there is no estimate: only an explicit list of families runs it."""
    reference = results.get(spec.reference)
    if reference is None:
        return explicit
    return share >= spec.cost * reference.log[0]["elapsed"]


def _no_time_message(name: str, allowed: float, needed: float | None) -> str:
    """Why a family has no model: its first trial did not finish in the ``allowed`` seconds of
    the search time. ``needed`` (when known) is the least its folds take, so the trial itself
    can take longer than that and still be cut short."""
    if needed is None:
        return f"{name}: no model, the search time it could have ({allowed:.0f} s) was too short"
    if needed <= allowed:  # the least it takes fits, and the trial took longer
        return (
            f"{name}: no model, the first trial took longer than the search time it could have "
            f"({allowed:.0f} s), though its folds need at least about {needed:.0f} s; a longer "
            "max_runtime_secs would let it run"
        )
    return (
        f"{name}: no model, the first trial did not finish in the search time it could have "
        f"({allowed:.0f} s); its folds need at least about {needed:.0f} s, and a longer "
        "max_runtime_secs would let it run"
    )


def _mb(size: float) -> str:
    return f"{size / 2**20:.0f} MB"


def _refit(
    result: FamilyResult, X, y, prep, views, clock: Clock, weight, bag: int = 0, ahead: bool = False
):
    """``(model refit on all rows, None)``, or ``(None, why)`` with why ``"time"``,
    ``"cancelled"`` or the exception the refit raised. ``bag`` > 0 refits with another seed."""
    spec = result.spec
    # A fold trains on (k-1)/k of the rows: the best trial's time / (k-1) per full-data fit. Folds
    # that look ahead in time train on 1/(k+1) to k/(k+1) of them: k/2 full-data fits in all. The
    # trial fitted every fold of every repeat.
    fits = result.repeats * (len(result.models) / 2 if ahead else len(result.models) - 1)
    if clock.remaining() < REFIT_ROUNDS_FACTOR * result.best_secs / fits:
        return None, "cancelled" if clock.should_stop() else "time"
    try:
        if spec.view not in views:
            views[spec.view] = getattr(prep, spec.view)(X)
        # the last fold of the time-ordered ones has the most rows, nearest to all of them
        learned = result.models[-1:] if ahead else result.models
        best = np.mean([spec.rounds(model) for model in learned])
        rounds = min(MAX_ROUNDS, max(1, round(best * REFIT_ROUNDS_FACTOR)))
        seed = spec.seed
        spec.seed = (seed + BAG_SEED_STEP * bag) % BAG_SEED_SPACE
        try:
            model = spec.fit_full(result.best_params, views[spec.view], y, clock, rounds, weight)
        finally:
            spec.seed = seed
        return model, None
    except DeadlineExceeded:
        return None, "cancelled" if clock.should_stop() else "time"
    except Exception as e:
        return None, e


def _time_values(df: pd.DataFrame, column: str) -> pd.Series:
    """The values of ``column`` as numbers or dates (text a date can be read from is parsed)."""
    if column not in df.columns:
        raise ConfigError(f"time column '{column}' is not in the data")
    values = df[column]
    if values.isna().any():
        raise ConfigError(f"time column '{column}' has missing values")
    if not (pd.api.types.is_numeric_dtype(values) or pd.api.types.is_datetime64_any_dtype(values)):
        values = parse_datetimes(values)  # as the date features are read: two-digit years too
        if values.isna().any():
            raise ConfigError(f"time column '{column}' must hold numbers or dates it can order by")
    return values


def _order_codes(df: pd.DataFrame, column: str) -> np.ndarray:
    """Whole numbers that put the rows in the order of ``column`` (a number, a date, or text a
    date can be read from), equal for equal values."""
    return pd.factorize(_time_values(df, column), sort=True)[0].astype(np.int64)


def _span_text(days: int) -> str:
    """A number of days in words: days up to 3 months, then months, then years."""
    if days <= 90:
        return f"{days} days"
    if days < 2 * 365:
        return f"about {round(days / 30.4)} months"
    return f"about {days / 365:.1f} years"


def _range_text(values: list[int], say: Callable[[int], str]) -> str:
    """``say`` of the lowest and highest value: one text when they are alike."""
    low, high = say(min(values)), say(max(values))
    return low if low == high else f"{low} to {high}"


def _spread(values: np.ndarray, rows: np.ndarray, n: int) -> np.ndarray:
    """``values`` of the validated ``rows`` in an array of ``n`` rows, empty (NaN) elsewhere."""
    if len(rows) == n:
        return values
    out = np.full((n, *values.shape[1:]), np.nan)
    out[rows] = values
    return out


def _blend(oof: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    return sum(w * oof[name] for name, w in weights.items() if w > 0)


def _typed_like(own: pd.Series, values: pd.Series, name: str) -> pd.Series:
    """``values`` (a column of the extra rows) in the type of ``own``, the same column of the data,
    so that joining them leaves a column of one type."""
    if values.dtype == own.dtype:
        return values
    try:
        if pd.api.types.is_numeric_dtype(own) and not pd.api.types.is_bool_dtype(own):
            return pd.to_numeric(values)  # (a gap or a fraction makes it a float, as the join does)
        return values.astype(own.dtype)
    except (TypeError, ValueError, OverflowError) as e:
        raise ConfigError(
            f"the column '{name}' of the extra rows cannot be read as {own.dtype}, the type of "
            "the data's"
        ) from e


def _learned_mix(y: np.ndarray, weight: np.ndarray | None, classes: int) -> np.ndarray:
    """The share of each class among the rows the models learn from (weighted, as they are)."""
    counts = np.bincount(y, weights=weight, minlength=classes)
    return counts / counts.sum()


def _with_extra_rows(
    folds: list,
    own: int,
    extra: int,
    own_groups: np.ndarray | None,
    extra_groups: np.ndarray | None,
) -> list:
    """``folds`` (over the first ``own`` rows) with the ``extra`` rows that follow them added to
    every fold's training rows. With groups, the extra rows of a group that a fold validates are
    left out of that fold's training rows."""
    added = np.arange(own, own + extra)
    out = []
    for train, valid in folds:
        keep = added
        if own_groups is not None and extra_groups is not None:
            keep = added[~np.isin(extra_groups, np.unique(own_groups[valid]))]
        out.append((np.concatenate([train, keep]), valid))
    return out


def _same(values: np.ndarray) -> np.ndarray:
    return values


def _event_flags(column: pd.Series, name: str, time: np.ndarray) -> np.ndarray:
    """The 0/1 event flags of ``column`` as floats; ConfigError if they are not 0 or 1 on
    every row, or the times (``time``) are not 0 or more, or no row has an event."""
    flags = pd.to_numeric(column, errors="coerce").to_numpy(dtype=float)
    if not np.isin(flags, (0.0, 1.0)).all():
        raise ConfigError(f"event column '{name}' must hold only 0 (censored) or 1 (event)")
    if (time < 0).any():
        raise ConfigError("the time target must be 0 or more with an event_column")
    if not flags.any():
        raise ConfigError(f"event column '{name}' has no event (no row is 1)")
    return flags


def _leaderboard(
    results,
    weights,
    refit_secs,
    blended,
    y,
    folds: Folds,
    sort_metric,
    original,
    prior,
    valid_rows,
    tuned=False,
    quantile=None,
) -> pd.DataFrame:
    """One row per candidate (a family's best trial, then its runners-up) and one for the
    ensemble. The ensemble's weights were chosen on the same OOF predictions it is scored on, so
    its row is slightly optimistic. ``original`` maps an OOF prediction to the units ``y`` and
    ``blended`` are in. With ``tuned`` every row counts right answers at its own best threshold."""
    rows = []
    for name, result in results.items():
        oof = original(result.oof[valid_rows])
        # a tuned decision is fitted to each row's own predictions
        own = metrics.tune_prior(sort_metric, y, oof) if tuned else prior
        rows.append(
            {
                "model": f"{result.spec.name}_{result.best_trial}",
                "family": result.spec.name,
                "cv_score": metrics.value(sort_metric, y, oof, own, quantile),
                "cv_std": metrics.fold_std(sort_metric, y, oof, folds, own, quantile),
                "train_secs": result.best_secs + refit_secs.get(name, 0.0),
                "weight": weights.get(name, 0.0),
            }
        )
    rows.append(
        {
            "model": "Ensemble",
            "family": "Ensemble",
            "cv_score": metrics.value(sort_metric, y, blended, prior, quantile),
            "cv_std": metrics.fold_std(sort_metric, y, blended, folds, prior, quantile),
            "train_secs": sum(row["train_secs"] for row in rows if row["weight"] > 0),
            "weight": np.nan,
        }
    )
    board = pd.DataFrame(rows, columns=LEADERBOARD_COLUMNS)
    ascending = sort_metric not in metrics.HIGHER_IS_BETTER
    return board.sort_values("cv_score", ascending=ascending, kind="stable").reset_index(drop=True)
