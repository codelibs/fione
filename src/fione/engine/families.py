"""Model families: their default parameters, search spaces and deadline-bounded fits.

Every ``fit`` checks ``deadline.expired()`` after each boosting iteration (ExtraTrees: between
rounds of trees sized from the measured throughput) and returns the model trained so far when it
fires, so a returned model always has at least one iteration. ``deadline`` needs ``expired()``
and ``remaining()``; the search passes an object that also reports cancellation as expiry.

The first *unit* of a fit (dataset construction plus the first iteration; for ExtraTrees the
first round of trees) cannot be interrupted, so ``fit`` refuses to start, raising
``DeadlineExceeded``, when less than ``UNIT_SAFETY`` times the family's unit time remains. The
unit time is the slowest one measured by this instance's earlier fits. Before the first fit on
more than ``PROBE_ROWS`` rows it is estimated from one unit on a ``PROBE_ROWS`` subsample,
scaled by n·log(n) (measured at 400k rows: right for ExtraTrees, 2-8x too high for boosting).

Still unprotected: that probe (about 0.1-0.3 s), the first fit on at most ``PROBE_ROWS`` rows,
and an iteration that runs slower than the measured ones. Callers should reserve headroom.

Size caps (artifact target, spec 5.2): at most 2,000 boosting rounds with 50-round early
stopping, 256 leaves per tree, XGBoost depth 10, CatBoost depth 8; ExtraTrees 100 trees of at
most 30 levels and 2,048 leaves.
"""

import time
from typing import ClassVar

import joblib
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from catboost import CatBoostClassifier, CatBoostRegressor
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor

from fione.engine.config import DeadlineExceeded
from fione.engine.prep import Task

MAX_ROUNDS = 2000
EARLY_STOPPING_ROUNDS = 50
MAX_LEAVES = 256
SMALL_DATA_ROWS = 20_000
SMALL_DATA_THREADS = 4
PROBE_ROWS = 20_000
UNIT_SAFETY = 1.2


def n_threads(n_rows: int) -> int:
    """Threads per fit: at most 4 below 20,000 rows, all physical cores otherwise.

    On small data, thread start-up and synchronisation cost more than the work they share (the
    spike's n_jobs=-1 managed one LightGBM trial in 8 s on 1.3k rows). ``joblib.cpu_count``
    honours container CPU limits.
    """
    cores = joblib.cpu_count(only_physical_cores=True)
    return min(cores, SMALL_DATA_THREADS) if n_rows < SMALL_DATA_ROWS else cores


class FamilySpec:
    """One model family for one task. ``fit``/``predict`` take the family's ``view`` of Prep."""

    name: ClassVar[str]
    view: ClassVar[str]  # Prep method producing this family's input: tree, catboost or dense
    defaults: ClassVar[dict]  # the first trial's parameters, keyed like ``space``

    def __init__(self, task: Task, n_classes: int, seed: int = 0, n_jobs: int = 1):
        self.task = task
        self.n_classes = n_classes
        self.seed = seed
        self.n_jobs = n_jobs
        self.unit_secs: float | None = None  # see the module docstring
        self._measured = False  # unit_secs comes from a real fit, not the probe

    @property
    def classification(self) -> bool:
        return self.task == "classification"

    def space(self, trial: optuna.Trial) -> dict:
        raise NotImplementedError

    def fit(
        self,
        params: dict,
        X_tr: pd.DataFrame,
        y_tr: np.ndarray,
        X_va: pd.DataFrame,
        y_va: np.ndarray,
        deadline,
    ):
        if deadline.expired():
            raise DeadlineExceeded
        if self.unit_secs is None and len(X_tr) > PROBE_ROWS:
            self.unit_secs = self._probe(params, X_tr, y_tr)
        if self.unit_secs is not None and deadline.remaining() < UNIT_SAFETY * self.unit_secs:
            raise DeadlineExceeded
        timer = _UnitTimer(deadline)
        model = self._fit(params, X_tr, y_tr, X_va, y_va, timer)
        if timer.unit is not None:
            self.unit_secs = max(self.unit_secs, timer.unit) if self._measured else timer.unit
            self._measured = True
        return model

    def _probe(self, params: dict, X: pd.DataFrame, y: np.ndarray) -> float:
        """Estimated unit time on ``X``, from one unit on a subsample."""
        rows = np.random.default_rng(self.seed).choice(len(X), PROBE_ROWS, replace=False)
        if self.classification:  # keep every class: XGBoost needs the labels 0..k-1
            rows = np.union1d(rows, np.unique(y, return_index=True)[1])
        X_sub, y_sub = X.iloc[rows], y[rows]
        start = time.monotonic()
        self._fit(params, X_sub, y_sub, X_sub, y_sub, _Expired())
        n, m = len(X), len(rows)
        return (time.monotonic() - start) * n * np.log(n) / (m * np.log(m))

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline):
        """Fit; training folds hold every class (stratified folds), as XGBoost requires."""
        raise NotImplementedError

    def predict(self, model, X: pd.DataFrame) -> np.ndarray:
        """Class probabilities of shape (n, n_classes), or values of shape (n,) for regression."""
        if not self.classification:
            return np.asarray(model.predict(X), dtype=float)
        proba = np.asarray(model.predict_proba(X), dtype=float)
        if proba.shape[1] == self.n_classes:
            return proba
        full = np.zeros((len(X), self.n_classes))  # a class missing from the training fold
        full[:, np.asarray(model.classes_, dtype=int)] = proba
        return full


class _Expired:
    """A deadline that has passed: the fit stops after its first unit."""

    def expired(self) -> bool:
        return True

    def remaining(self) -> float:
        return 0.0


class _UnitTimer:
    """Passes a deadline through, noting when the fit first consults it: after its first unit."""

    def __init__(self, deadline):
        self.deadline = deadline
        self.start = time.monotonic()
        self.unit: float | None = None

    def _note(self) -> None:
        if self.unit is None:
            self.unit = time.monotonic() - self.start

    def expired(self) -> bool:
        self._note()
        return self.deadline.expired()

    def remaining(self) -> float:
        self._note()
        return self.deadline.remaining()


class _LightGBMDeadline:
    def __init__(self, deadline):
        self.deadline = deadline

    def __call__(self, env) -> None:
        if self.deadline.expired():
            raise lgb.callback.EarlyStopException(env.iteration, env.evaluation_result_list)


class LightGBM(FamilySpec):
    name = "LightGBM"
    view = "tree"
    defaults = {
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_child_samples": 20,
        "colsample_bytree": 0.8,
        "subsample": 0.8,
        "reg_lambda": 1.0,
    }

    def space(self, trial):
        return {
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 8, MAX_LEAVES, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        }

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline):
        cls = lgb.LGBMClassifier if self.classification else lgb.LGBMRegressor
        model = cls(
            n_estimators=MAX_ROUNDS,
            subsample_freq=1,
            n_jobs=self.n_jobs,
            random_state=self.seed,
            verbose=-1,
            **params,
        )
        stopping = lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)
        model.fit(
            X_tr,
            y_tr,
            eval_X=(X_va,),
            eval_y=(y_va,),
            callbacks=[stopping, _LightGBMDeadline(deadline)],
        )
        return model


class _XGBoostDeadline(xgb.callback.TrainingCallback):
    def __init__(self, deadline):
        super().__init__()
        self.deadline = deadline

    def after_iteration(self, model, epoch, evals_log) -> bool:
        return self.deadline.expired()


class XGBoost(FamilySpec):
    name = "XGBoost"
    view = "tree"
    defaults = {
        "learning_rate": 0.05,
        "max_depth": 6,
        "min_child_weight": 1.0,
        "colsample_bytree": 0.8,
        "subsample": 0.8,
        "reg_lambda": 1.0,
    }

    def space(self, trial):
        return {
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 10),
            "min_child_weight": trial.suggest_float("min_child_weight", 0.5, 20.0, log=True),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        }

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline):
        cls = xgb.XGBClassifier if self.classification else xgb.XGBRegressor
        model = cls(
            n_estimators=MAX_ROUNDS,
            early_stopping_rounds=EARLY_STOPPING_ROUNDS,
            max_leaves=MAX_LEAVES,
            tree_method="hist",
            enable_categorical=True,
            n_jobs=self.n_jobs,
            random_state=self.seed,
            verbosity=0,
            callbacks=[_XGBoostDeadline(deadline)],
            **params,
        )
        model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
        # XGBoost keeps constructor callbacks; ours holds the deadline, which may not pickle.
        model.set_params(callbacks=None)
        return model


class _CatBoostDeadline:
    def __init__(self, deadline):
        self.deadline = deadline

    def after_iteration(self, info) -> bool:
        return not self.deadline.expired()  # False stops training


class CatBoost(FamilySpec):
    name = "CatBoost"
    view = "catboost"
    defaults = {"learning_rate": 0.05, "depth": 6, "l2_leaf_reg": 3.0}

    def space(self, trial):
        return {
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.3, log=True),
            "depth": trial.suggest_int("depth", 3, 8),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 20.0, log=True),
        }

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline):
        cls = CatBoostClassifier if self.classification else CatBoostRegressor
        model = cls(
            iterations=MAX_ROUNDS,
            early_stopping_rounds=EARLY_STOPPING_ROUNDS,
            thread_count=self.n_jobs,
            random_seed=self.seed,
            verbose=0,
            allow_writing_files=False,
            **params,
        )
        categorical = [i for i, dtype in enumerate(X_tr.dtypes) if dtype is np.dtype(object)]
        model.fit(
            X_tr,
            y_tr,
            cat_features=categorical,
            eval_set=(X_va, y_va),
            callbacks=[_CatBoostDeadline(deadline)],
        )
        return model


class ExtraTrees(FamilySpec):
    name = "ExtraTrees"
    view = "dense"
    defaults = {"max_features": 0.7, "min_samples_leaf": 2}
    n_trees = 100
    max_depth = 30
    max_leaf_nodes = 2048

    def space(self, trial):
        return {
            "max_features": trial.suggest_float("max_features", 0.3, 1.0),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        }

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline):
        cls = ExtraTreesClassifier if self.classification else ExtraTreesRegressor
        chunk = self.n_jobs  # one tree per thread: measures throughput at the smallest granularity
        model = cls(
            n_estimators=min(chunk, self.n_trees),
            max_depth=self.max_depth,
            max_leaf_nodes=self.max_leaf_nodes,
            warm_start=True,
            n_jobs=self.n_jobs,
            random_state=self.seed,
            **params,
        )
        while True:
            start = time.monotonic()
            added = model.n_estimators - len(getattr(model, "estimators_", []))
            model.fit(X_tr, y_tr)
            rounds = -(-added // chunk)  # a round grows one tree per thread
            per_round = max((time.monotonic() - start) / rounds, 1e-3)
            affordable = int(deadline.remaining() / per_round) * chunk
            grow = min(self.n_trees - model.n_estimators, affordable, 4 * chunk)
            if grow < 1 or deadline.expired():
                return model
            model.set_params(n_estimators=model.n_estimators + grow)


FAMILIES: dict[str, type[FamilySpec]] = {
    spec.name: spec for spec in (LightGBM, XGBoost, CatBoost, ExtraTrees)
}
