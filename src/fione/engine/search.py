"""Time-boxed hyperparameter search for one model family (spec 5.1).

``run_family`` runs Optuna TPE trials until its deadline expires or ``should_stop()`` turns
true. Each trial fits every fold; its score is the out-of-fold loss (lower is better): log loss
for classification, RMSE for regression. The first trial uses the family defaults and splits the
remaining time evenly over its folds, so it always completes, with truncated models if need be;
if even that is impossible, ``NoModelError`` is raised, as soon as a fold's time share is
shorter than the family's first unit (see ``families``) rather than after burning the budget.
Later trials run their folds to the end and are discarded when the deadline or a cancellation
interrupts them; one is not started when the time left cannot cover a unit per fold. Optuna's
median pruner abandons trials whose running fold loss is clearly behind.

``max_trial_secs`` caps every trial; its time is also split over the folds, so a capped trial is
kept with truncated models instead of being discarded. The cap is raised, with a ``notice``
event, to ``UNIT_SAFETY`` measured units per fold, since a smaller one could not fit a fold, and
a fold whose share was eaten by the previous folds' overruns still gets that much: a cap can
make a trial run somewhat longer, never discard it.

The search also ends after ``max_trials`` finished trials (reason ``max_models``), or when the
best ``stopping_score`` (by default the search score; lower is better) of the finished trials
has not improved by a relative ``stopping_tolerance`` over the last ``stopping_rounds`` of them
(reason ``no_improvement``; a pruned trial counts as no improvement). The first
``STARTUP_TRIALS`` trials are the sampler's random startup and never count towards the
stagnation, so a family always gets ``STARTUP_TRIALS + stopping_rounds + 1`` trials unless
something else ends its search. ``sample_weight`` is
passed to every fold fit; scores stay unweighted.

A trial that raises an ``Exception`` (a library failure) ends the search with reason ``error``
and a ``notice`` (``error_notice``); the best trial so far is kept, and ``FamilyResult.error``
holds the exception. Other ``BaseException``s (KeyboardInterrupt, SystemExit) propagate.

``should_stop`` is polled after every boosting iteration and must be cheap.
"""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import optuna
import pandas as pd
from sklearn.model_selection import GroupKFold, KFold, StratifiedGroupKFold, StratifiedKFold

from fione.engine.config import ConfigError, Deadline, DeadlineExceeded, NoModelError
from fione.engine.events import Event, EventSink
from fione.engine.families import FAMILIES, UNIT_SAFETY, FamilySpec, n_threads
from fione.engine.prep import Prep, Task

optuna.logging.set_verbosity(optuna.logging.WARNING)

Folds = list[tuple[np.ndarray, np.ndarray]]
# A capped trial's folds get this much more than the UNIT_SAFETY units they need.
CAP_MARGIN = 1.25
# TPE draws its first trials at random; stagnation is only judged on the trials after them, so
# a small ``stopping_rounds`` cannot end the search before the sampler has learned anything.
STARTUP_TRIALS = 10
# A family hands on its best trials, not only the best one, so that the ensemble can blend
# models of one family that make different mistakes.
TOP_TRIALS = 3


@dataclass
class FamilyResult:
    """The best completed trial. A search cancelled or failed before any trial completed has no
    models, an all-NaN ``oof`` and ``best_score == inf``."""

    oof: np.ndarray  # (n,) for regression, (n, k) class probabilities for classification
    models: list  # one fitted model per fold, in fold order
    best_params: dict
    trials: int  # trials that finished (completed or pruned)
    best_score: float
    elapsed: float
    spec: FamilySpec  # the instance that fitted the models, with its measured unit time
    reason: str  # why the search ended: time, cancelled, max_models, no_improvement or error
    best_trial: int = -1
    best_secs: float = 0.0  # wall time of the best trial
    log: list[dict] = field(default_factory=list)  # the ``trial`` event data, in order
    error: Exception | None = None  # what ended the search when ``reason == "error"``
    runners_up: list["FamilyResult"] = field(default_factory=list)  # next best trials, best first
    # With repeated folds (``repeats`` > 1): the out-of-fold predictions of every repeat, ``oof``
    # being the first. ``models`` and ``oof`` are the first repeat's alone; ``best_score`` is the
    # mean of the repeats' scores. Empty when the folds are not repeated.
    oofs: list[np.ndarray] = field(default_factory=list)
    repeats: int = 1

    def stacked(self, rows: np.ndarray) -> np.ndarray:
        """The predictions of ``rows`` in all repeats, one repeat below the other."""
        return np.concatenate([oof[rows] for oof in self.oofs or [self.oof]])


def error_notice(kind: str, family: str, error: Exception) -> Event:
    """The ``notice`` reporting that ``family`` failed with ``error`` (kind: family/refit_error)."""
    data = {
        "kind": kind,
        "family": family,
        "exception": type(error).__name__,
        "message": str(error)[:300],
    }
    return Event("notice", data=data)


def make_folds(
    y: np.ndarray, task: Task, nfolds: int, seed: int = 0, groups: np.ndarray | None = None
) -> Folds:
    """Shuffled K folds, stratified by class for classification. With ``groups`` (one label per
    row) the rows of a group stay in one fold, and the classes are balanced as far as that
    allows."""
    classification = task == "classification"
    if groups is None:
        splitter = StratifiedKFold if classification else KFold
        return list(splitter(nfolds, shuffle=True, random_state=seed).split(np.zeros(len(y)), y))
    splitter = StratifiedGroupKFold if classification else GroupKFold
    split = splitter(nfolds, shuffle=True, random_state=seed)
    return list(split.split(np.zeros(len(y)), y, groups))


def make_time_folds(order: np.ndarray, y: np.ndarray, task: Task, nfolds: int) -> Folds:
    """Folds that look forward in time. The rows, ordered by ``order`` (whole numbers, equal for
    rows of the same moment), are cut into ``nfolds + 1`` parts of about the same size; the
    fold ``j`` validates on part ``j`` and trains on the parts before it, so no model learns
    from a later row than the ones it predicts. The first part is never validated. Rows that
    share a value of ``order`` are in the same part, so fewer folds come out when it has few
    different values."""
    n = len(order)
    ranked = np.argsort(order, kind="stable")
    starts = np.searchsorted(order[ranked], order[ranked], side="left")
    part = np.empty(n, dtype=np.int64)
    part[ranked] = np.minimum(starts * (nfolds + 1) // n, nfolds)
    present = np.unique(part)
    if len(present) < 2:
        raise ConfigError("the time column has too few different values to make validation parts")
    folds = [(np.flatnonzero(part < p), np.flatnonzero(part == p)) for p in present[1:]]
    if task == "classification":
        classes = np.unique(y)
        if len(np.unique(y[np.concatenate([valid for _, valid in folds])])) < 2:
            raise ConfigError("the later parts hold a single class, which cannot be validated")
        for train, _ in folds:
            if len(np.unique(y[train])) < len(classes):
                raise ConfigError(
                    "a class has no row in the earlier part of a time-ordered validation; "
                    "use fewer folds or validate without a time column"
                )
    return folds


def covered(folds: Folds, n: int) -> np.ndarray:
    """The rows (of ``n``) that some fold validates, in order: all of them for shuffled folds."""
    rows = np.zeros(n, dtype=bool)
    for _, valid in folds:
        rows[valid] = True
    return np.flatnonzero(rows)


# The folds of repeat r use the seed plus r times this step (a prime, so repeats never share one).
REPEAT_SEED_STEP = 104_729
# With few rows a validation score is noisy, and a search over many trials then picks parameters
# that were lucky on the folds. Up to each row count the folds are repeated with other seeds.
REPEATS_BY_ROWS = ((2_000, 3), (5_000, 2))


def repeats_for(n_rows: int) -> int:
    """How many times the folds are repeated for ``n_rows`` rows (1: not at all)."""
    for rows, repeats in REPEATS_BY_ROWS:
        if n_rows <= rows:
            return repeats
    return 1


def repeat_folds(
    y: np.ndarray,
    task: Task,
    nfolds: int,
    seed: int = 0,
    groups: np.ndarray | None = None,
    repeats: int = 1,
) -> Folds:
    """``make_folds`` ``repeats`` times with other seeds, one after another: the first
    ``nfolds`` folds are those of ``make_folds`` itself."""
    return [
        fold
        for r in range(repeats)
        for fold in make_folds(y, task, nfolds, (seed + r * REPEAT_SEED_STEP) % 2**32, groups)
    ]


def score(task: Task, y: np.ndarray, pred: np.ndarray) -> float:
    """Log loss of class probabilities (labels 0..k-1) or RMSE; lower is better."""
    if task == "classification":
        picked = np.clip(pred[np.arange(len(y)), y], 1e-15, 1.0)
        return float(-np.mean(np.log(picked)))
    return float(np.sqrt(np.mean((y - pred) ** 2)))


class Clock:
    """The deadline a fit sees: its time share, which a cancellation also ends."""

    def __init__(self, deadline: Deadline, should_stop: Callable[[], bool]):
        self.deadline = deadline
        self.should_stop = should_stop

    def expired(self) -> bool:
        return self.deadline.expired() or self.should_stop()

    def remaining(self) -> float:
        return 0.0 if self.should_stop() else self.deadline.remaining()


@dataclass
class _Outcome:
    state: str  # complete or pruned
    score: float
    oof: np.ndarray | None = None
    models: list | None = None
    oofs: list | None = None  # every repeat's oof; ``oof`` is the first


def _run_trial(
    spec: FamilySpec,
    params: dict,
    X: pd.DataFrame,
    y: np.ndarray,
    folds: Folds,
    trial: optuna.Trial,
    deadline: Deadline,
    cap: Callable[[], float | None],
    split: bool,
    keep_late: bool,
    should_stop: Callable[[], bool],
    sample_weight: np.ndarray | None,
    repeats: int = 1,
) -> _Outcome | None:
    """Fit all folds; None when cancelled or, unless ``keep_late``, cut off by ``deadline``.

    ``folds`` holds ``repeats`` runs of folds one after another. Only the first run's models are
    kept (the others only score the parameters), and the score is the mean over the runs of
    their out-of-fold score, so each run is judged alone, as a single run would be.

    ``cap()`` is the trial's time limit, re-read before each fold because the unit time it is
    raised to is only measured by the first fit on small data. A capped trial truncates its
    folds and never refuses one for the cap alone: every fold gets at least its quota of the
    smallest cap (``CAP_MARGIN x UNIT_SAFETY x`` the unit), even when earlier folds overran their
    shares by a prediction or an iteration, so only ``deadline`` can still end the trial.
    """
    shape = (len(y), spec.n_classes) if spec.classification else (len(y),)
    per_run = len(folds) // repeats
    oofs = [np.zeros(shape) for _ in range(repeats)]
    models, losses = [], []
    start = time.monotonic()
    for i, (train, valid) in enumerate(folds):
        limit = cap()
        trial_deadline = (
            deadline if limit is None else deadline.child(limit - (time.monotonic() - start))
        )
        share = (
            trial_deadline.child(trial_deadline.remaining() / (len(folds) - i))
            if split
            else trial_deadline
        )
        if limit is not None and spec.unit_secs:
            quota = CAP_MARGIN * UNIT_SAFETY * spec.unit_secs
            if share.remaining() < quota:
                share = deadline.child(quota)  # the cap truncates folds, it never discards them
        weight = None if sample_weight is None else sample_weight[train]
        try:
            model = spec.fit(
                params,
                X.iloc[train],
                y[train],
                X.iloc[valid],
                y[valid],
                Clock(share, should_stop),
                weight,
            )
        except DeadlineExceeded:
            return None
        if should_stop() or (deadline.expired() and not keep_late):
            return None
        pred = spec.predict(model, X.iloc[valid])
        oofs[i // per_run][valid] = pred
        if i < per_run:
            models.append(model)
        losses.append(score(spec.task, y[valid], pred))
        trial.report(float(np.mean(losses)), i)
        if trial.should_prune():
            return _Outcome("pruned", float(np.mean(losses)))
    rows = covered(folds, len(y))
    total = float(np.mean([score(spec.task, y[rows], oof[rows]) for oof in oofs]))
    return _Outcome("complete", total, oofs[0], models, oofs)


def run_family(
    name: str,
    X: pd.DataFrame,
    y: np.ndarray,
    folds: Folds,
    task: Task,
    prep: Prep,
    deadline: Deadline,
    emit: EventSink,
    should_stop: Callable[[], bool],
    seed: int = 0,
    max_trial_secs: float | None = None,
    max_trials: int | None = None,
    stopping_rounds: int = 0,
    stopping_tolerance: float = 0.0,
    stopping_score: Callable[[np.ndarray], float] | None = None,
    sample_weight: np.ndarray | None = None,
    repeats: int = 1,
    first_deadline: Deadline | None = None,
) -> FamilyResult:
    """Search family ``name`` within ``deadline``; ``y`` is float targets or class codes 0..k-1.
    ``folds`` holds ``repeats`` runs of folds (see ``repeat_folds``).

    ``first_deadline`` (a later one than ``deadline``) bounds the first trial instead of
    ``deadline``: a family whose share is too short for one trial still gets a whole one, and
    its search ends at ``deadline`` as soon as that trial is done."""
    start = time.monotonic()
    n_classes = int(y.max()) + 1 if task == "classification" else 0
    spec = FAMILIES[name](task, n_classes, seed=seed, n_jobs=n_threads(len(X)))

    def cap() -> float | None:
        if max_trial_secs is None or not spec.unit_secs:
            return max_trial_secs
        # A quarter more than the minimum, so timing jitter cannot make a fold refuse.
        return max(max_trial_secs, CAP_MARGIN * len(folds) * UNIT_SAFETY * spec.unit_secs)

    view = None
    study = optuna.create_study(
        direction="minimize",
        sampler=optuna.samplers.TPESampler(
            seed=seed, n_startup_trials=STARTUP_TRIALS, multivariate=True
        ),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=3),
    )
    study.enqueue_trial(spec.defaults)
    best: _Outcome | None = None
    leaders: list[
        tuple[_Outcome, dict, int, float]
    ] = []  # best first: outcome, params, trial, secs
    log: list[dict] = []
    stop_best, stop_history = math.inf, []  # best stopping score after each finished trial
    raised = False  # the max_trial_secs notice was sent
    error: Exception | None = None
    finished = 0
    while True:
        if should_stop():
            reason = "cancelled"
            break
        if max_trials is not None and finished >= max_trials:
            reason = "max_models"
            break
        if stopping_rounds and len(stop_history) > STARTUP_TRIALS + stopping_rounds:
            ref = stop_history[-1 - stopping_rounds]
            if not ref - stop_history[-1] > stopping_tolerance * abs(ref):
                reason = "no_improvement"
                break
        unit = spec.unit_secs
        until = first_deadline if finished == 0 and first_deadline is not None else deadline
        if until.expired() or (
            finished and unit and deadline.remaining() < len(folds) * UNIT_SAFETY * unit
        ):
            reason = "time"
            break
        if view is None:
            view = getattr(prep, spec.view)(X)
            if max_trial_secs is not None:  # a probe now lets the first trial's cap be raised
                spec.estimate_unit(spec.defaults, view.iloc[folds[0][0]], y[folds[0][0]])
        trial = study.ask()
        params = spec.space(trial)
        first = finished == 0
        trial_start = time.monotonic()
        split = first or max_trial_secs is not None
        try:
            outcome = _run_trial(
                spec,
                params,
                view,
                y,
                folds,
                trial,
                until,
                cap,
                split,
                first,
                should_stop,
                sample_weight,
                repeats,
            )
        except Exception as e:
            study.tell(trial, state=optuna.trial.TrialState.FAIL)
            emit(error_notice("family_error", name, e))
            error, reason = e, "error"
            break
        limit = cap()
        if limit is not None and limit > max_trial_secs and not raised:
            raised = True
            message = (
                f"max_runtime_secs_per_model raised to {limit:.2f} s for {name}: "
                f"each of the {len(folds)} folds needs at least {UNIT_SAFETY} x "
                f"{spec.unit_secs:.2f} s to train"
            )
            emit(
                Event("notice", data={"message": message, "family": name, "max_trial_secs": limit})
            )
        if outcome is None:
            study.tell(trial, state=optuna.trial.TrialState.FAIL)
            reason = "cancelled" if should_stop() else "time"
            break
        trial_secs = time.monotonic() - trial_start
        if outcome.state == "pruned":
            study.tell(trial, state=optuna.trial.TrialState.PRUNED)
        else:
            study.tell(trial, outcome.score)
            leaders.append((outcome, params, trial.number, trial_secs))
            leaders.sort(key=lambda leader: leader[0].score)  # stable: earlier trials first
            del leaders[TOP_TRIALS:]  # drops the models of the trials left behind
            best = leaders[0][0]
            value = (
                outcome.score
                if stopping_score is None
                else float(np.mean([stopping_score(oof) for oof in outcome.oofs]))
            )
            stop_best = min(stop_best, value)
        stop_history.append(stop_best)
        finished += 1
        data = {
            "family": name,
            "trial": trial.number,
            "state": outcome.state,
            "score": outcome.score,
            "params": params,
            "elapsed": trial_secs,
            "best_so_far": best.score if best is not None else None,
        }
        log.append(data)
        emit(Event("trial", data=data))
    emit(Event("stopped", data={"family": name, "reason": reason}))
    if best is None and reason == "time":
        # What the first trial needed, by the rule that refused it: every fold gets a unit.
        needed = len(folds) * UNIT_SAFETY * spec.unit_secs if spec.unit_secs else None
        raise NoModelError("time budget too small to train any model", needed)
    elapsed = time.monotonic() - start
    emit(
        Event(
            "family_done",
            data={
                "family": name,
                "trials": finished,
                "best_score": best.score if best is not None else None,
                "best_params": leaders[0][1] if leaders else {},
                "elapsed": elapsed,
            },
        )
    )
    if best is None:
        shape = (len(y), n_classes) if task == "classification" else (len(y),)
        return FamilyResult(
            np.full(shape, np.nan),
            [],
            {},
            finished,
            math.inf,
            elapsed,
            spec,
            reason,
            log=log,
            error=error,
        )

    def result(outcome, params, trial_number, secs, runners_up=()):
        return FamilyResult(
            outcome.oof,
            outcome.models,
            params,
            finished,
            outcome.score,
            elapsed,
            spec,
            reason,
            trial_number,
            secs,
            log,
            error,
            list(runners_up),
            outcome.oofs if repeats > 1 else [],
            repeats,
        )

    return result(*leaders[0][:4], [result(*leader) for leader in leaders[1:]])
