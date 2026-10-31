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

``fit_full`` trains the final model on all rows with a fixed number of rounds and no early
stopping. It refuses like ``fit``, with the unit scaled to the larger row count, and raises
``DeadlineExceeded`` instead of returning a model that is shorter than requested.

``size_bytes`` estimates a fitted model's pickled size from its tree and leaf counts (within
about 10% of the measured pickles; an upper bound for the boosting families).

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
        self._unit_rows = 0  # the training rows unit_secs applies to
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
        sample_weight: np.ndarray | None = None,
    ):
        """A model early-stopped on the validation rows; ``sample_weight`` weights ``X_tr``."""
        if deadline.expired():
            raise DeadlineExceeded
        self.estimate_unit(params, X_tr, y_tr)
        if self.unit_secs is not None and deadline.remaining() < UNIT_SAFETY * self.unit_secs:
            raise DeadlineExceeded
        timer = _UnitTimer(deadline)
        model = self._fit(params, X_tr, y_tr, X_va, y_va, timer, sample_weight)
        self._note_unit(timer, len(X_tr))
        return model

    def fit_full(
        self,
        params: dict,
        X: pd.DataFrame,
        y: np.ndarray,
        deadline,
        rounds: int,
        sample_weight: np.ndarray | None = None,
    ):
        """One model on all rows: ``rounds`` boosting rounds (ExtraTrees: the full forest)."""
        if deadline.expired():
            raise DeadlineExceeded
        if self.unit_secs is not None and self._unit_rows:
            n, m = max(len(X), 2), max(self._unit_rows, 2)
            unit = self.unit_secs * max(1.0, n * np.log(n) / (m * np.log(m)))
            if deadline.remaining() < UNIT_SAFETY * unit:
                raise DeadlineExceeded
        timer = _UnitTimer(deadline)
        model = self._fit(params, X, y, None, None, timer, sample_weight, rounds)
        self._note_unit(timer, len(X))
        if self.rounds(model) < self._full_rounds(rounds):
            raise DeadlineExceeded
        return model

    def estimate_unit(self, params: dict, X_tr: pd.DataFrame, y_tr: np.ndarray) -> None:
        """Probe the unit time before the first fit on more than ``PROBE_ROWS`` rows."""
        if self.unit_secs is None and len(X_tr) > PROBE_ROWS:
            self.unit_secs = self._probe(params, X_tr, y_tr)
            self._unit_rows = len(X_tr)

    def _note_unit(self, timer: "_UnitTimer", rows: int) -> None:
        if timer.unit is None:
            return
        if not self._measured or timer.unit > self.unit_secs:
            self.unit_secs, self._unit_rows = timer.unit, rows
        self._measured = True

    def _full_rounds(self, rounds: int) -> int:
        return rounds

    def rounds(self, model) -> int:
        """Boosting rounds the model predicts with (ExtraTrees: its trees)."""
        raise NotImplementedError

    def serving(self, model):
        """``model`` set up for the final artifact, where predictions must be reproducible."""
        return model

    def size_bytes(self, model) -> int:
        raise NotImplementedError

    def importance(self, model) -> np.ndarray:
        """Non-negative importance per feature, in view column order."""
        raise NotImplementedError

    @property
    def _outputs(self) -> int:
        """Values per leaf: one per class beyond binary, else one."""
        return self.n_classes if self.n_classes > 2 else 1

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

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        """Fit; training folds hold every class (stratified folds), as XGBoost requires.

        Without validation rows (``X_va is None``) there is no early stopping and boosting runs
        ``rounds`` rounds.
        """
        raise NotImplementedError

    def _predict_options(self) -> dict:
        """Keyword arguments for the library's predict calls."""
        return {}

    def predict(self, model, X: pd.DataFrame) -> np.ndarray:
        """Class probabilities of shape (n, n_classes), or values of shape (n,) for regression."""
        options = self._predict_options()
        if not self.classification:
            return np.asarray(model.predict(X, **options), dtype=float)
        proba = np.asarray(model.predict_proba(X, **options), dtype=float)
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

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        cls = lgb.LGBMClassifier if self.classification else lgb.LGBMRegressor
        model = cls(
            n_estimators=MAX_ROUNDS if X_va is not None else rounds,
            subsample_freq=1,
            n_jobs=self.n_jobs,
            random_state=self.seed,
            verbose=-1,
            **params,
        )
        callbacks = [_LightGBMDeadline(deadline)]
        evaluation = {}
        if X_va is not None:
            callbacks.insert(0, lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False))
            evaluation = {"eval_X": (X_va,), "eval_y": (y_va,)}
        model.fit(X_tr, y_tr, sample_weight=sample_weight, callbacks=callbacks, **evaluation)
        return model

    def rounds(self, model) -> int:
        # best_iteration_ is 0 without early stopping; a deadline stop sets it to the rounds done.
        return int(model.best_iteration_ or model.booster_.current_iteration())

    def size_bytes(self, model) -> int:
        return model.booster_.num_trees() * model.get_params()["num_leaves"] * 120

    def importance(self, model) -> np.ndarray:
        return np.asarray(model.booster_.feature_importance(importance_type="gain"), dtype=float)


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

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        cls = xgb.XGBClassifier if self.classification else xgb.XGBRegressor
        stopping = X_va is not None
        model = cls(
            n_estimators=MAX_ROUNDS if stopping else rounds,
            early_stopping_rounds=EARLY_STOPPING_ROUNDS if stopping else None,
            max_leaves=MAX_LEAVES,
            tree_method="hist",
            enable_categorical=True,
            n_jobs=self.n_jobs,
            random_state=self.seed,
            verbosity=0,
            callbacks=[_XGBoostDeadline(deadline)],
            **params,
        )
        evaluation = {"eval_set": [(X_va, y_va)]} if stopping else {}
        model.fit(X_tr, y_tr, sample_weight=sample_weight, verbose=False, **evaluation)
        # XGBoost keeps constructor callbacks; ours holds the deadline, which may not pickle.
        model.set_params(callbacks=None)
        return model

    def rounds(self, model) -> int:
        try:
            return int(model.best_iteration) + 1
        except AttributeError:  # trained without early stopping
            return int(model.get_booster().num_boosted_rounds())

    def size_bytes(self, model) -> int:
        trees = model.get_booster().num_boosted_rounds() * self._outputs
        leaves = min(2 ** model.get_params()["max_depth"], MAX_LEAVES)
        return trees * leaves * 2 * 30

    def importance(self, model) -> np.ndarray:
        booster = model.get_booster()
        gains = booster.get_score(importance_type="total_gain")
        return np.array([gains.get(name, 0.0) for name in booster.feature_names], dtype=float)


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

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        cls = CatBoostClassifier if self.classification else CatBoostRegressor
        stopping = X_va is not None
        model = cls(
            iterations=MAX_ROUNDS if stopping else rounds,
            early_stopping_rounds=EARLY_STOPPING_ROUNDS if stopping else None,
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
            sample_weight=sample_weight,
            eval_set=(X_va, y_va) if stopping else None,
            callbacks=[_CatBoostDeadline(deadline)],
        )
        return model

    def _predict_options(self) -> dict:
        # CatBoost takes its threads per call; its default (-1) is every core.
        return {"thread_count": self.n_jobs}

    def rounds(self, model) -> int:
        return int(model.tree_count_)  # shrunk to the best iteration after early stopping

    def size_bytes(self, model) -> int:
        leaves = 2 ** model.get_params()["depth"]
        return model.tree_count_ * leaves * (16 + 8 * self._outputs)

    def importance(self, model) -> np.ndarray:
        return np.asarray(model.get_feature_importance(), dtype=float)


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

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
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
            model.fit(X_tr, y_tr, sample_weight=sample_weight)
            steps = -(-added // chunk)  # a round grows one tree per thread
            per_round = max((time.monotonic() - start) / steps, 1e-3)
            affordable = int(deadline.remaining() / per_round) * chunk
            grow = min(self.n_trees - model.n_estimators, affordable, 4 * chunk)
            if grow < 1 or deadline.expired():
                return model
            model.set_params(n_estimators=model.n_estimators + grow)

    def _full_rounds(self, rounds: int) -> int:
        return self.n_trees

    def serving(self, model):
        # Threads add up the trees' outputs in varying order, which changes the last bits.
        return model.set_params(n_jobs=1)

    def rounds(self, model) -> int:
        return len(model.estimators_)

    def size_bytes(self, model) -> int:
        # sklearn stores 64 bytes per node plus a float64 value per output and class.
        trees = [estimator.tree_ for estimator in model.estimators_]
        return sum(tree.node_count * (64 + 8 * tree.value[0].size) for tree in trees)

    def importance(self, model) -> np.ndarray:
        return np.asarray(model.feature_importances_, dtype=float)


FAMILIES: dict[str, type[FamilySpec]] = {
    spec.name: spec for spec in (LightGBM, XGBoost, CatBoost, ExtraTrees)
}
