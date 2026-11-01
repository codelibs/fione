"""The AutoML facade: search, ensemble and package a model within one hard time budget.

``AutoML.fit`` creates one ``Deadline(max_runtime_secs)`` when it starts (the whole job counts,
spec 5.1/5.7) and spends it in phases:

1. Checks, ``Prep.fit`` and the folds: measured, not budgeted. Call the time left after them L.
2. Search: 0.65 L. Families run one after another in ``FAMILY_ORDER``; each gets the search
   time still left times its ``FAMILY_WEIGHTS`` share among the families not yet run, so time a
   family leaves unused flows to the next ones. The search scores trials with log loss / RMSE.
3. Ensemble selection: ``caruana`` on the families' out-of-fold (OOF) predictions; cheap.
4. Final refit: until the reserve (about 0.2 L when the search used its whole share; more when
   it ended early). Each member with weight > 0 is refit once on all rows with its best
   parameters: boosting for 1.1 x the mean best iteration of its fold models, without early
   stopping; the forests as one full forest; Linear as one fit. DeepLearning is not refit: its
   fold models, averaged, are its final model (``FamilySpec.refit``). The fold models are also
   the fallback, averaged, with a ``notice``, for a refit that is not expected to fit in the
   time left (from its best trial's time) or that the deadline cuts short.
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

A family that raises (a library failure) is skipped with a ``notice`` of kind ``family_error``,
keeping its best trial so far; a refit that raises falls back to the fold models with a
``refit_error`` notice; diagnostics that raise leave ``diagnostics`` None, with a
``diagnostics_error`` notice. ``stop_reason`` is ``error`` when a family failed and nothing
else (time, ``max_models``, cancellation) ended the search. ``NoModelError`` lists every
family's error and is chained to the last one when no family produced a model.

``families`` restricts the search to some of ``FAMILY_ORDER`` (tests and advanced use).
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
from fione.engine.families import FAMILIES, MAX_ROUNDS
from fione.engine.model import Member, TrainedModel, feature_importance
from fione.engine.prep import Prep, Task, infer_task, validate_target
from fione.engine.search import (
    Clock,
    FamilyResult,
    Folds,
    error_notice,
    make_folds,
    run_family,
)

FAMILY_ORDER = (
    "LightGBM",
    "CatBoost",
    "XGBoost",
    "RandomForest",
    "ExtraTrees",
    "DeepLearning",
    "Linear",
)
FAMILY_WEIGHTS = {
    "LightGBM": 0.22,
    "CatBoost": 0.22,
    "XGBoost": 0.18,
    "RandomForest": 0.10,
    "ExtraTrees": 0.10,
    "DeepLearning": 0.12,
    "Linear": 0.06,
}
SEARCH_SHARE = 0.65
RESERVE_SHARE = 0.15
MIN_RESERVE_SECS = 0.5
REFIT_ROUNDS_FACTOR = 1.1
# The linear view (one-hot levels) of Linear and DeepLearning is built whole, and each fold copies
# most of it again: above this many cells (800 MB as float64) those families are left out.
LINEAR_MAX_CELLS = 100_000_000
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
        unknown = sorted(set(families or ()) - set(FAMILY_ORDER))
        if unknown or families == []:
            raise ConfigError(f"unknown families: {unknown}; choose from {list(FAMILY_ORDER)}")
        self.families = [f for f in FAMILY_ORDER if families is None or f in families]

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
        self._event(
            "started",
            config=c.to_dict(),
            n_rows=len(X),
            n_cols=X.shape[1],
            task=task,
            nfolds=nfolds,
        )
        for notice in notices:
            self.emit(notice)
        weight = None
        if c.balance_classes and task == "regression":
            self._notice("balance_classes is ignored for regression")
        elif c.balance_classes:
            counts = np.bincount(y)
            weight = (len(y) / (len(counts) * counts))[y]
        prep = Prep().fit(X)
        folds = make_folds(y, task, nfolds, c.seed)
        families = self._without_wide_linear_view(prep, len(X))

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
            None if default_stopping else (lambda oof: metrics.loss(stopping_metric, y, oof)),
            weight,
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

        oof = {name: result.oof for name, result in results.items()}
        weights = caruana(oof, y, task)
        scores = {name: metrics.value(sort_metric, y, p) for name, p in oof.items()}
        pick = max if sort_metric in metrics.HIGHER_IS_BETTER else min
        self._event(
            "ensemble",
            sort_metric=sort_metric,
            weights=weights,
            scores=scores,
            ensemble_score=metrics.value(sort_metric, y, _blend(oof, weights)),
            best_single=pick(scores, key=scores.get),
        )

        refit = deadline.child(deadline.remaining() - reserve)
        members, refit_secs = self._members(
            results, weights, X, y, prep, Clock(refit, self.should_stop), weight, stop_reason
        )
        if self.should_stop():
            stop_reason = "cancelled"
        final = {member.spec.name: member.weight for member in members}
        blended = _blend(oof, final)
        try:
            found = diagnostics(task, y, blended, classes, seed=c.seed)
        except Exception as e:
            found = None
            self._notice(
                f"the training diagnostics could not be computed: {str(e)[:300]}",
                kind="diagnostics_error",
                exception=type(e).__name__,
            )
        leaderboard = _leaderboard(
            results, final, refit_secs, blended, y, folds, sort_metric, scores
        )
        assignment = np.empty(len(y), dtype=np.int64)
        for i, (_, valid) in enumerate(folds):
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
            metrics=metrics.summary(task, y, blended),
            prep=prep,
            members=members,
            label_dtype=target.dtype,
            cv_predictions=blended if c.keep_cv_predictions else None,
            cv_models={n: r.models for n, r in results.items()} if c.keep_cv_models else None,
            fold_assignment=assignment if c.keep_cv_fold_assignment else None,
            diagnostics=found,
        )
        self._event(
            "finished",
            stop_reason=stop_reason,
            elapsed=time.monotonic() - start,
            leaderboard_top=leaderboard.head(3).to_dict("records"),
            metrics=model.metrics,
        )
        return model

    def _without_wide_linear_view(self, prep: Prep, n_rows: int) -> list[str]:
        """``self.families`` without those that read the linear view when it would be too big
        (unless that leaves none)."""
        if n_rows * prep.linear_width <= LINEAR_MAX_CELLS:
            return self.families
        kept = [name for name in self.families if FAMILIES[name].view != "linear"]
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

    def _search(self, families, X, y, folds, task, prep, search: Deadline, stopping_score, weight):
        """Run the families in order; returns (results with models, trial rows, end reason per
        family, finished trial count, exception per failed family)."""
        c = self.config
        results: dict[str, FamilyResult] = {}
        logs: list[dict] = []
        reasons: dict[str, str] = {}
        errors: dict[str, Exception] = {}
        finished = 0
        for i, name in enumerate(families):
            if self.should_stop():
                reasons[name] = "cancelled"
                break
            rest = families[i:]
            max_trials = None
            if c.max_models is not None:
                if finished >= c.max_models:
                    break
                # Leave one trial for each family after this one.
                max_trials = max(1, c.max_models - finished - (len(rest) - 1))
            share = search.remaining() * FAMILY_WEIGHTS[name] / sum(FAMILY_WEIGHTS[f] for f in rest)
            try:
                result = run_family(
                    name,
                    X,
                    y,
                    folds,
                    task,
                    prep,
                    search.child(share),
                    self.emit,
                    self.should_stop,
                    seed=c.seed,
                    max_trial_secs=c.max_runtime_secs_per_model,
                    max_trials=max_trials,
                    stopping_rounds=c.stopping_rounds,
                    stopping_tolerance=c.stopping_tolerance,
                    stopping_score=stopping_score,
                    sample_weight=weight,
                )
            except NoModelError:
                reasons[name] = "time"
                continue
            except Exception as e:  # outside any trial, e.g. building the view
                self.emit(error_notice("family_error", name, e))
                reasons[name], errors[name] = "error", e
                continue
            if result.error is not None:
                errors[name] = result.error
            finished += result.trials
            reasons[name] = result.reason
            logs += [
                {**{k: row[k] for k in TRIAL_COLUMNS[:-1]}, "params": json.dumps(row["params"])}
                for row in result.log
            ]
            if result.models:
                results[name] = result
            if result.reason == "cancelled":
                break
        return results, logs, reasons, finished, errors

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
        name = member.spec.name
        self._notice(f"{name} dropped from the ensemble: {why}", family=name)

    def _members(self, results, weights, X, y, prep, clock, weight, stop_reason):
        """Final members, heaviest first, and the refit time per family."""
        views: dict[str, pd.DataFrame] = {}
        chosen = sorted((n for n in results if weights[n] > 0), key=lambda n: -weights[n])
        candidates, refit_secs = [], {}
        for name in chosen:
            result = results[name]
            models = result.models
            if stop_reason != "cancelled" and not self.should_stop() and result.spec.refit:
                start = time.monotonic()
                model, problem = _refit(result, X, y, prep, views, clock, weight)
                refit_secs[name] = time.monotonic() - start
                if model is not None:
                    models = [model]
                elif isinstance(problem, Exception):
                    self.emit(error_notice("refit_error", name, problem))
                else:
                    why = (
                        "was cancelled"
                        if problem == "cancelled"
                        else "did not fit in the time left"
                    )
                    self._notice(
                        f"{name}: the final refit {why}; using its {len(models)} fold models",
                        family=name,
                    )
            size = sum(result.spec.size_bytes(m) for m in models)
            candidates.append((Member(result.spec, weights[name], models), size))
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
                f"{kept[0][0].spec.name} kept although it exceeds the size limit: "
                "no smaller member",
                family=kept[0][0].spec.name,
            )
        kept = [member for member, _ in kept]
        total = sum(member.weight for member in kept)
        for member in kept:
            member.weight /= total
            member.models = [member.spec.serving(model) for model in member.models]
        return kept, refit_secs


def _mb(size: float) -> str:
    return f"{size / 2**20:.0f} MB"


def _refit(result: FamilyResult, X, y, prep, views, clock: Clock, weight):
    """``(model refit on all rows, None)``, or ``(None, why)`` with why ``"time"``,
    ``"cancelled"`` or the exception the refit raised."""
    spec = result.spec
    # A fold trains on (k-1)/k of the rows: the best trial's time / (k-1) per full-data fit.
    if clock.remaining() < REFIT_ROUNDS_FACTOR * result.best_secs / (len(result.models) - 1):
        return None, "cancelled" if clock.should_stop() else "time"
    try:
        if spec.view not in views:
            views[spec.view] = getattr(prep, spec.view)(X)
        best = np.mean([spec.rounds(model) for model in result.models])
        rounds = min(MAX_ROUNDS, max(1, round(best * REFIT_ROUNDS_FACTOR)))
        model = spec.fit_full(result.best_params, views[spec.view], y, clock, rounds, weight)
        return model, None
    except DeadlineExceeded:
        return None, "cancelled" if clock.should_stop() else "time"
    except Exception as e:
        return None, e


def _blend(oof: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    return sum(w * oof[name] for name, w in weights.items() if w > 0)


def _leaderboard(
    results, weights, refit_secs, blended, y, folds: Folds, sort_metric, scores
) -> pd.DataFrame:
    """One row per family and one for the ensemble. The ensemble's weights were chosen on the
    same OOF predictions it is scored on, so its row is slightly optimistic."""
    rows = []
    for name, result in results.items():
        rows.append(
            {
                "model": f"{name}_{result.best_trial}",
                "family": name,
                "cv_score": scores[name],
                "cv_std": metrics.fold_std(sort_metric, y, result.oof, folds),
                "train_secs": result.best_secs + refit_secs.get(name, 0.0),
                "weight": weights.get(name, 0.0),
            }
        )
    rows.append(
        {
            "model": "Ensemble",
            "family": "Ensemble",
            "cv_score": metrics.value(sort_metric, y, blended),
            "cv_std": metrics.fold_std(sort_metric, y, blended, folds),
            "train_secs": sum(row["train_secs"] for row in rows if row["weight"] > 0),
            "weight": np.nan,
        }
    )
    board = pd.DataFrame(rows, columns=LEADERBOARD_COLUMNS)
    ascending = sort_metric not in metrics.HIGHER_IS_BETTER
    return board.sort_values("cv_score", ascending=ascending, kind="stable").reset_index(drop=True)
