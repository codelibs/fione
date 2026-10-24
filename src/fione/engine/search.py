"""Time-boxed hyperparameter search for one model family (spec 5.1).

``run_family`` runs Optuna TPE trials until its deadline expires or ``should_stop()`` turns
true. Each trial fits every fold; its score is the out-of-fold loss (lower is better): log loss
for classification, RMSE for regression. The first trial uses the family defaults and splits the
remaining time evenly over its folds, so it always completes, with truncated models if need be;
if even that is impossible, ``NoModelError`` is raised. Later trials run their folds to the end
and are discarded when the deadline or a cancellation interrupts them. Optuna's median pruner
abandons trials whose running fold loss is clearly behind.

``max_trial_secs`` caps every trial; its time is also split over the folds, so a capped trial is
kept with truncated models instead of being discarded.

``should_stop`` is polled after every boosting iteration and must be cheap.
"""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import optuna
import pandas as pd
from sklearn.model_selection import KFold, StratifiedKFold

from fione.engine.config import Deadline, DeadlineExceeded, NoModelError
from fione.engine.events import Event, EventSink
from fione.engine.families import FAMILIES, FamilySpec, n_threads
from fione.engine.prep import Prep, Task

optuna.logging.set_verbosity(optuna.logging.WARNING)

Folds = list[tuple[np.ndarray, np.ndarray]]


@dataclass
class FamilyResult:
    """The best completed trial. A search cancelled before any trial completed has no models,
    ``trials == 0``, an all-NaN ``oof`` and ``best_score == inf``."""

    oof: np.ndarray  # (n,) for regression, (n, k) class probabilities for classification
    models: list  # one fitted model per fold, in fold order
    best_params: dict
    trials: int  # trials that finished (completed or pruned)
    best_score: float
    elapsed: float


def make_folds(y: np.ndarray, task: Task, nfolds: int, seed: int = 0) -> Folds:
    """Shuffled K folds, stratified by class for classification."""
    splitter = StratifiedKFold if task == "classification" else KFold
    return list(splitter(nfolds, shuffle=True, random_state=seed).split(np.zeros(len(y)), y))


def score(task: Task, y: np.ndarray, pred: np.ndarray) -> float:
    """Log loss of class probabilities (labels 0..k-1) or RMSE; lower is better."""
    if task == "classification":
        picked = np.clip(pred[np.arange(len(y)), y], 1e-15, 1.0)
        return float(-np.mean(np.log(picked)))
    return float(np.sqrt(np.mean((y - pred) ** 2)))


class _Clock:
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


def _run_trial(
    spec: FamilySpec,
    params: dict,
    X: pd.DataFrame,
    y: np.ndarray,
    folds: Folds,
    trial: optuna.Trial,
    deadline: Deadline,
    trial_deadline: Deadline,
    split: bool,
    keep_late: bool,
    should_stop: Callable[[], bool],
) -> _Outcome | None:
    """Fit all folds; None when cancelled or, unless ``keep_late``, cut off by ``deadline``."""
    oof = np.zeros((len(y), spec.n_classes)) if spec.classification else np.zeros(len(y))
    models, losses = [], []
    for i, (train, valid) in enumerate(folds):
        share = (
            trial_deadline.child(trial_deadline.remaining() / (len(folds) - i))
            if split
            else trial_deadline
        )
        try:
            model = spec.fit(
                params, X.iloc[train], y[train], X.iloc[valid], y[valid], _Clock(share, should_stop)
            )
        except DeadlineExceeded:
            return None
        if should_stop() or (deadline.expired() and not keep_late):
            return None
        pred = spec.predict(model, X.iloc[valid])
        oof[valid] = pred
        models.append(model)
        losses.append(score(spec.task, y[valid], pred))
        trial.report(float(np.mean(losses)), i)
        if trial.should_prune():
            return _Outcome("pruned", float(np.mean(losses)))
    return _Outcome("complete", score(spec.task, y, oof), oof, models)


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
) -> FamilyResult:
    """Search family ``name`` within ``deadline``; ``y`` is float targets or class codes 0..k-1."""
    start = time.monotonic()
    n_classes = int(y.max()) + 1 if task == "classification" else 0
    spec = FAMILIES[name](task, n_classes, seed=seed, n_jobs=n_threads(len(X)))
    view = None
    study = optuna.create_study(
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=seed),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=3),
    )
    study.enqueue_trial(spec.defaults)
    best: _Outcome | None = None
    best_params: dict = {}
    finished = 0
    while True:
        if should_stop():
            reason = "cancelled"
            break
        if deadline.expired():
            reason = "time"
            break
        if view is None:
            view = getattr(prep, spec.view)(X)
        trial = study.ask()
        params = spec.space(trial)
        first = finished == 0
        trial_start = time.monotonic()
        trial_deadline = deadline if max_trial_secs is None else deadline.child(max_trial_secs)
        split = first or max_trial_secs is not None
        outcome = _run_trial(
            spec, params, view, y, folds, trial, deadline, trial_deadline, split, first, should_stop
        )
        if outcome is None:
            study.tell(trial, state=optuna.trial.TrialState.FAIL)
            reason = "cancelled" if should_stop() else "time"
            break
        if outcome.state == "pruned":
            study.tell(trial, state=optuna.trial.TrialState.PRUNED)
        else:
            study.tell(trial, outcome.score)
            if best is None or outcome.score < best.score:
                best, best_params = outcome, params  # drops the previous best's models
        finished += 1
        emit(
            Event(
                "trial",
                data={
                    "family": name,
                    "trial": trial.number,
                    "state": outcome.state,
                    "score": outcome.score,
                    "params": params,
                    "elapsed": time.monotonic() - trial_start,
                    "best_so_far": best.score if best is not None else None,
                },
            )
        )
    emit(Event("stopped", data={"family": name, "reason": reason}))
    if best is None and reason == "time":
        raise NoModelError("time budget too small to train any model")
    elapsed = time.monotonic() - start
    emit(
        Event(
            "family_done",
            data={
                "family": name,
                "trials": finished,
                "best_score": best.score if best is not None else None,
                "best_params": best_params,
                "elapsed": elapsed,
            },
        )
    )
    if best is None:
        shape = (len(y), n_classes) if task == "classification" else (len(y),)
        return FamilyResult(np.full(shape, np.nan), [], {}, finished, math.inf, elapsed)
    return FamilyResult(best.oof, best.models, best_params, finished, best.score, elapsed)
