"""The AutoML facade: search, ensemble and package a model within one hard time budget.

``AutoML.fit`` creates one ``Deadline(max_runtime_secs)`` when it starts (the whole job counts,
spec 5.1/5.7) and spends it in phases:

1. Checks, the choice of derived features (``fione.engine.features``; at most
   ``FEATURE_SHARE`` of the time, or ``FEATURE_MIN_SECS`` of a short run, and off with
   ``feature_engineering=False``), ``Prep.fit``
   and the folds (a ``cv_group_column`` keeps the rows of a group in one fold, in the search and
   in the choice of derived features alike): measured, not otherwise budgeted. Call the time left
   after them L.
2. Search: 0.65 L. Families run one after another in ``FAMILY_ORDER``; each gets the search
   time still left times its ``FAMILY_WEIGHTS`` share among the families not yet run, so time a
   family leaves unused flows to the next ones. The search scores trials with log loss / RMSE.
   Each family hands on its ``TOP_TRIALS`` best trials, as candidates ``Family``,
   ``Family#2`` and ``Family#3``.
   After them come the *late* families (``LATE_ORDER``: variants of TextLinear, for data with
   prose). When any applies, ``LATE_SHARE`` of the search time is kept for them, taken from
   the base families' shares (scaled to 0.85) except TextLinear's, which is as without them.
   The late families get what is left of the search time (that and what the base families
   leave), never the time of the later phases:
   each one the search time still left times its ``LATE_WEIGHTS`` share among the late families
   not yet run, and only when its first trial is expected to fit in that share (``cost`` times
   the first trial of TextLinear). A late family that does not apply to the data is not run and
   changes nothing; one that does not improve the ensemble gets weight 0 from ``caruana``.
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
dropped, with a ``notice``, then the lightest-weighted ones until all together fit in
``TOTAL_SIZE_CAP``, and the weights are renormalised; if that would drop every member, the
heaviest-weighted one is kept. ``cv_score``, ``cv_std`` and ``metrics`` come from the fold
models' OOF predictions, blended with the final weights. The returned model holds neither the
fold models nor the OOF arrays unless ``keep_cv_*`` asks; ``keep_cv_models`` keeps every
family's fold models and so works against the artifact size goal (spec 5.2).

When ``should_stop()`` turns true, the search ends, nothing is refit, and the members keep
their fold models; the model has ``stop_reason == "cancelled"``. ``NoModelError`` is raised when
no family completed a trial, because of the cancellation or because the budget is too small.

A family whose first trial does not fit in its share of the search time (a text model fits all
its data in one unit and cannot be cut short) is lent ``LOAD_MARGIN`` times the time the trial
is estimated to need when that is at most ``LEND_LIMIT`` of the search time left; otherwise it
has no model, and a ``notice`` says what the trial needed. The late families that are not run
for lack of time are named in one ``notice``.

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
import time
from collections.abc import Callable

import numpy as np
import pandas as pd

from fione.engine import metrics
from fione.engine.config import ConfigError, Deadline, DeadlineExceeded, NoModelError, TrainConfig
from fione.engine.diagnostics import diagnostics
from fione.engine.ensemble import caruana
from fione.engine.events import Event, EventSink, jsonable
from fione.engine.families import FAMILIES, MAX_ROUNDS, FamilySpec
from fione.engine.features import select_groups
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

FAMILY_ORDER = (
    "LightGBM",
    "TextLinear",
    "CatBoost",
    "XGBoost",
    "RandomForest",
    "ExtraTrees",
    "DeepLearning",
    "Linear",
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
# Run after the others, in the search time they leave (see the module docstring); each only
# when the data suits it (``FamilySpec.applies``) and a model of it would not be too big.
LATE_ORDER = ("TextLinearChar", "TextLinearPlain", "TextLinearWide")
LATE_WEIGHTS = {"TextLinearChar": 0.5, "TextLinearPlain": 0.25, "TextLinearWide": 0.25}
LATE_SHARE = 0.15  # of the search time is kept for the late families, when any applies
# A first trial that cannot be cut short and needs more than its family's share is lent the
# time, ``LOAD_MARGIN`` times what it is estimated to need (the machine may be busy), if that
# is at most ``LEND_LIMIT`` of the search time left.
LOAD_MARGIN = 1.3
LEND_LIMIT = 0.5
FEATURE_SHARE = 0.10  # of the time, at most, goes to choosing derived features
# A short run gets more: the choice needs about this long on a few thousand rows, and without it
# the most useful candidates run out of time unconfirmed. Never over FEATURE_MAX_SHARE.
FEATURE_MIN_SECS = 30.0
FEATURE_MAX_SHARE = 0.30
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
LEADERBOARD_COLUMNS = ["model", "family", "cv_score", "cv_std", "train_secs", "weight"]
TRIAL_COLUMNS = ["family", "trial", "state", "score", "elapsed", "params"]


def _ignore(event: Event) -> None:
    pass


def _never() -> bool:
    return False


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
        known = [*FAMILY_ORDER, *LATE_ORDER]
        unknown = sorted(set(families or ()) - set(known))
        if unknown or families == []:
            raise ConfigError(f"unknown families: {unknown}; choose from {known}")
        self.families = [f for f in FAMILY_ORDER if families is None or f in families]
        self.late = [f for f in LATE_ORDER if families is None or f in families]
        self.explicit = families is not None  # the caller named the families

    def _event(self, type: str, **data) -> None:
        self.emit(Event(type, data=jsonable(data)))

    def _notice(self, message: str, **data) -> None:
        self._event("notice", message=message, **data)

    def fit(self, df: pd.DataFrame) -> TrainedModel:
        """Train on ``df``, which holds the target column and the features."""
        deadline = Deadline(self.config.max_runtime_secs)
        start = time.monotonic()
        c = self.config
        if c.target not in df.columns:
            raise ConfigError(f"target column '{c.target}' is not in the data")
        unknown = [column for column in c.ignored_columns if column not in df.columns]
        if unknown:
            raise ConfigError(f"unknown columns in ignored_columns: {unknown}")
        X = df.drop(columns=[c.target, *c.ignored_columns])
        target = df[c.target]
        task: Task = infer_task(target) if c.task == "auto" else c.task
        sort_metric = metrics.resolve(c.sort_metric, task, "sort_metric")
        stopping_metric = metrics.resolve(c.stopping_metric, task, "stopping_metric")
        notices: list[Event] = []
        y, classes, nfolds = validate_target(target, task, c.nfolds, notices.append)
        # Folds in time order are one fixed partition: another seed would not change them.
        repeats = 1 if c.time_column else c.cv_repeats or repeats_for(len(X))
        row_groups = None
        if c.cv_group_column is not None:
            if c.cv_group_column not in df.columns:
                raise ConfigError(f"cv_group_column '{c.cv_group_column}' is not in the data")
            row_groups = pd.factorize(df[c.cv_group_column], use_na_sentinel=False)[0]
            distinct = int(row_groups.max()) + 1
            if distinct < 2:
                raise ConfigError(
                    f"the group column '{c.cv_group_column}' needs at least 2 groups, "
                    f"it has {distinct}"
                )
            if distinct <= nfolds:
                repeats = 1  # each group is a fold: every seed gives the same partition
            if distinct < nfolds:
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
            n_rows=len(X),
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
        y_seen = y  # the target as the user gave it; ``y`` is what the models learn
        if c.target_transform == "log1p" and task == "classification":
            self._notice("target_transform is ignored for classification")
        elif c.target_transform == "log1p":
            if (y <= -1).any():
                raise ConfigError("target_transform 'log1p' needs target values above -1")
            y = np.log1p(y)
        prior = None
        if c.decision == "balanced" and task == "regression":
            self._notice("decision is ignored for regression")
        elif c.decision == "balanced":
            prior = np.bincount(y) / len(y)
        if c.time_column is None:
            groups, tried = self._engineer(X, y, task, nfolds, deadline, row_groups)
        else:  # the gate judges a feature on shuffled folds, which look at the future
            groups, tried = [], None
            if c.feature_engineering:
                self._notice("derived features are not tried with a time column")
        prep = Prep().fit(X, groups)
        if c.time_column is None:
            folds = repeat_folds(y, task, nfolds, c.seed, row_groups, repeats)
            first_run = folds[:nfolds]  # reported: the other repeats only judge the search
            if row_groups is not None and task == "classification":
                self._check_classes_in_training(y, folds, classes)
        else:
            folds = first_run = make_time_folds(_order_codes(df, c.time_column), y, task, nfolds)
            self._notice(
                f"validating on {len(folds)} later parts of the data in order of "
                f"'{c.time_column}'; the first part is only learned from",
                kind="time_validation",
                folds=len(folds),
            )
        rows = covered(folds, len(y))  # the rows some fold predicts (all but the first part)
        families = self._without_wide_linear_view(prep, len(X))
        # The words are read only from prose columns.
        families = [f for f in families if f != "TextLinear" or prep.prose] or families
        # An explicit list of late families only is run as it is, like TextLinear above.
        late = self._late_families(prep, X, y, task) if families else self.late
        families = [*families, *late]

        left = deadline.remaining()
        reserve = max(MIN_RESERVE_SECS, RESERVE_SHARE * left)
        default_stopping = stopping_metric == metrics.ALLOWED[task][0]
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
            else (lambda oof: metrics.loss(stopping_metric, y[rows], oof[rows])),
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
        weights = caruana(stacked, np.tile(y_valid, repeats), task)
        scores = {name: metrics.value(sort_metric, y_valid, p, prior) for name, p in oof.items()}
        pick = max if sort_metric in metrics.HIGHER_IS_BETTER else min
        self._event(
            "ensemble",
            sort_metric=sort_metric,
            weights=weights,
            scores=scores,
            ensemble_score=metrics.value(sort_metric, y_valid, _blend(oof, weights), prior),
            best_single=pick(scores, key=scores.get),
        )

        refit = deadline.child(deadline.remaining() - reserve)
        members, refit_secs = self._members(
            results, weights, X, y, prep, Clock(refit, self.should_stop), weight, stop_reason
        )
        if self.should_stop():
            stop_reason = "cancelled"
        final = {member.key: member.weight for member in members}
        # What is reported (scores, diagnostics, cv predictions) is in the target's own units.
        original = np.expm1 if y is not y_seen else _same
        blended = original(_blend(oof, final))
        try:
            found = diagnostics(task, y_seen[rows], blended, classes, seed=c.seed, prior=prior)
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
        )
        assignment = np.full(len(y), -1, dtype=np.int64)  # -1: never validated
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
            metrics=metrics.summary(task, y_seen[rows], blended, prior),
            prep=prep,
            members=members,
            label_dtype=target.dtype,
            cv_predictions=_spread(blended, rows, len(y)) if c.keep_cv_predictions else None,
            cv_models={n: r.models for n, r in results.items() if "#" not in n}
            if c.keep_cv_models
            else None,
            fold_assignment=assignment if c.keep_cv_fold_assignment else None,
            diagnostics=found,
            features=tried,
            class_prior=prior,
        )
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
        self._notice(
            "derived features: " + (", ".join(adopted) if adopted else "none added"),
            kind="features",
            groups=tried,
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
        self._notice(
            f"{', '.join(left_out)} left out: the one-hot encoded data "
            f"({n_rows:,} rows x {prep.linear_width:,} columns) would take too much memory",
            kind="families_left_out",
            families=left_out,
        )
        return kept

    def _late_families(self, prep: Prep, X, y, task: Task) -> list[str]:
        """The late families this data suits, whose models would not be too big, and whose view
        is not too wide (see ``_without_wide_linear_view``)."""
        if len(X) * prep.linear_width > LINEAR_MAX_CELLS:
            return []
        outputs = int(y.max()) + 1 if task == "classification" else 1
        outputs = 1 if outputs == 2 else outputs
        return [
            name
            for name in self.late
            if FAMILIES[name].applies(prep, X)
            and FAMILIES[name].coef_bytes(prep, outputs) <= SIZE_CAP
        ]

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
        references = {FAMILIES[f].reference for f in families if f in LATE_ORDER}
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
            weights = LATE_WEIGHTS if late else FAMILY_WEIGHTS
            own = search if late or name in references else base
            left = own.remaining()
            share = left * weights[name] / sum(weights[f] for f in rest)
            if late and not _late_fits(FAMILIES[name], share, results, self.explicit):
                # Without the reference result there was no estimate: not a matter of time.
                if FAMILIES[name].reference in results:
                    skipped.append(name)
                continue

            def attempt(deadline, name=name, max_trials=max_trials):
                return run_family(
                    name,
                    X,
                    y,
                    folds,
                    task,
                    prep,
                    deadline,
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
                )

            try:
                try:
                    result = attempt(own.child(share))
                except NoModelError as e:
                    # A first trial that cannot be cut short and needs more than the share is
                    # lent the time, with a margin for a busy machine, when that is not much of
                    # what is left; the later families share what remains.
                    lent = (e.needed_secs or 0.0) * LOAD_MARGIN
                    if late or not share < lent <= LEND_LIMIT * own.remaining():
                        raise
                    result = attempt(own.child(lent))
            except NoModelError as e:
                if late:
                    skipped.append(name)
                else:
                    reasons[name] = "time"
                    self._notice(_no_time_message(name, share, e.needed_secs), family=name)
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

    def _drop(self, member: Member, why: str) -> None:
        name = member.key or member.spec.name  # "LightGBM#2" for a runner-up
        self._notice(f"{name} dropped from the ensemble: {why}", family=member.spec.name)

    def _members(self, results, weights, X, y, prep, clock, weight, stop_reason):
        """Final members, heaviest first, and the refit time per family."""
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
        kept = [(member, size) for member, size in candidates if size <= SIZE_CAP]
        for member, size in candidates:
            if size > SIZE_CAP:
                self._drop(
                    member, f"its model would take about {_mb(size)} (limit {_mb(SIZE_CAP)})"
                )
        while len(kept) > 1 and sum(size for _, size in kept) > TOTAL_SIZE_CAP:
            together = sum(size for _, size in kept)
            member, _ = kept.pop()  # the lightest weight
            self._drop(
                member,
                f"the members would take about {_mb(together)} together "
                f"(limit {_mb(TOTAL_SIZE_CAP)})",
            )
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


def _no_time_message(name: str, share: float, needed: float | None) -> str:
    """Why a family has no model: its first trial did not fit in its ``share`` of the search time
    (``needed`` seconds, when known)."""
    if needed is None:
        return f"{name}: no model, its share of the search time ({share:.0f} s) was too short"
    return (
        f"{name}: no model, one trial is estimated to need about {needed:.0f} s but its share of "
        f"the search time was {share:.0f} s; a longer max_runtime_secs would let it run"
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


def _order_codes(df: pd.DataFrame, column: str) -> np.ndarray:
    """Whole numbers that put the rows in the order of ``column`` (a number, a date, or text a
    date can be read from), equal for equal values."""
    if column not in df.columns:
        raise ConfigError(f"time column '{column}' is not in the data")
    values = df[column]
    if values.isna().any():
        raise ConfigError(f"time column '{column}' has missing values")
    if not (pd.api.types.is_numeric_dtype(values) or pd.api.types.is_datetime64_any_dtype(values)):
        try:
            values = pd.to_datetime(values)
        except (ValueError, TypeError):
            raise ConfigError(
                f"time column '{column}' must hold numbers or dates it can order by"
            ) from None
    return pd.factorize(values, sort=True)[0].astype(np.int64)


def _spread(values: np.ndarray, rows: np.ndarray, n: int) -> np.ndarray:
    """``values`` of the validated ``rows`` in an array of ``n`` rows, empty (NaN) elsewhere."""
    if len(rows) == n:
        return values
    out = np.full((n, *values.shape[1:]), np.nan)
    out[rows] = values
    return out


def _blend(oof: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    return sum(w * oof[name] for name, w in weights.items() if w > 0)


def _same(values: np.ndarray) -> np.ndarray:
    return values


def _leaderboard(
    results, weights, refit_secs, blended, y, folds: Folds, sort_metric, original, prior, valid_rows
) -> pd.DataFrame:
    """One row per candidate (a family's best trial, then its runners-up) and one for the
    ensemble. The ensemble's weights were chosen on the same OOF predictions it is scored on, so
    its row is slightly optimistic. ``original`` maps an OOF prediction to the units ``y`` and
    ``blended`` are in."""
    rows = []
    for name, result in results.items():
        oof = original(result.oof[valid_rows])
        rows.append(
            {
                "model": f"{result.spec.name}_{result.best_trial}",
                "family": result.spec.name,
                "cv_score": metrics.value(sort_metric, y, oof, prior),
                "cv_std": metrics.fold_std(sort_metric, y, oof, folds, prior),
                "train_secs": result.best_secs + refit_secs.get(name, 0.0),
                "weight": weights.get(name, 0.0),
            }
        )
    rows.append(
        {
            "model": "Ensemble",
            "family": "Ensemble",
            "cv_score": metrics.value(sort_metric, y, blended, prior),
            "cv_std": metrics.fold_std(sort_metric, y, blended, folds, prior),
            "train_secs": sum(row["train_secs"] for row in rows if row["weight"] > 0),
            "weight": np.nan,
        }
    )
    board = pd.DataFrame(rows, columns=LEADERBOARD_COLUMNS)
    ascending = sort_metric not in metrics.HIGHER_IS_BETTER
    return board.sort_values("cv_score", ascending=ascending, kind="stable").reset_index(drop=True)
