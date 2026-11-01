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
stopping, 256 leaves per tree, XGBoost depth 10, CatBoost depth 8; RandomForest and ExtraTrees
100 trees of at most 30 levels and 2,048 leaves; DeepLearning two layers of at most 256 units.

The families are the model types of H2O AutoML (GBM: LightGBM; XGBoost; DRF: RandomForest; XRT:
ExtraTrees; GLM: Linear; DeepLearning) plus CatBoost. Linear and DeepLearning read the ``linear``
view of Prep (one-hot, standardised); their "rounds" are 1 and the epochs trained.
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
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier, MLPRegressor

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
    view: ClassVar[
        str
    ]  # Prep method producing this family's input: tree, catboost, dense or linear
    defaults: ClassVar[dict]  # the first trial's parameters, keyed like ``space``
    refit: ClassVar[bool] = True  # False: the final model is the average of the fold models

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


class Forest(FamilySpec):
    """A scikit-learn forest grown in rounds of trees, within the deadline (``warm_start``)."""

    view = "dense"
    n_trees = 100
    max_depth = 30
    max_leaf_nodes = 2048
    classifier: ClassVar[type]
    regressor: ClassVar[type]
    extra: ClassVar[dict] = {}  # constructor arguments that make the family what it is

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        cls = self.classifier if self.classification else self.regressor
        chunk = self.n_jobs  # one tree per thread: measures throughput at the smallest granularity
        model = cls(
            n_estimators=min(chunk, self.n_trees),
            max_depth=self.max_depth,
            max_leaf_nodes=self.max_leaf_nodes,
            warm_start=True,
            n_jobs=self.n_jobs,
            random_state=self.seed,
            **self.extra,
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


class ExtraTrees(Forest):
    name = "ExtraTrees"
    defaults = {"max_features": 0.7, "min_samples_leaf": 2}
    classifier = ExtraTreesClassifier
    regressor = ExtraTreesRegressor

    def space(self, trial):
        return {
            "max_features": trial.suggest_float("max_features", 0.3, 1.0),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        }


class RandomForest(Forest):
    name = "RandomForest"
    defaults = {"max_features": 0.5, "min_samples_leaf": 2}
    classifier = RandomForestClassifier
    regressor = RandomForestRegressor

    def space(self, trial):
        return {
            "max_features": trial.suggest_float("max_features", 0.2, 1.0),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        }


def owners(columns) -> np.ndarray:
    """The feature (position in ``Prep.feature_names``) behind each column of the linear view."""
    return np.array([int(name[1:].split("_")[0]) for name in columns])


def by_feature(weights: np.ndarray, columns) -> np.ndarray:
    """``weights`` per column of the linear view, summed per feature (to its highest position)."""
    owner = owners(columns)
    return np.bincount(owner, weights=weights, minlength=owner.max() + 1)


class Linear(FamilySpec):
    """L2-regularised logistic (classification) or ridge (regression) regression on the linear
    view, H2O's GLM. ``C`` is the inverse regularisation strength; ridge uses ``alpha = 1/C``.
    """

    name = "Linear"
    view = "linear"
    defaults = {"C": 1.0}
    max_iter = 300

    def space(self, trial):
        return {"C": trial.suggest_float("C", 1e-3, 1e2, log=True)}

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        # One unit: the solver cannot be interrupted, so the deadline is only checked before it.
        if self.classification:
            model = LogisticRegression(C=params["C"], max_iter=self.max_iter)
        else:
            model = Ridge(alpha=1.0 / params["C"])
        model.fit(X_tr, y_tr, sample_weight=sample_weight)
        model.baseline_ = X_tr.to_numpy(np.float64).mean(axis=0)
        return model

    def _full_rounds(self, rounds: int) -> int:
        return 1

    def rounds(self, model) -> int:
        return 1

    def size_bytes(self, model) -> int:
        return model.coef_.size * 8 + 1024

    def importance(self, model) -> np.ndarray:
        weight = np.abs(np.atleast_2d(model.coef_)).sum(axis=0)
        return by_feature(weight, model.feature_names_in_)


class DeepLearning(FamilySpec):
    """A feed-forward network with two ReLU layers of ``width`` units (scikit-learn's MLP),
    H2O's Deep Learning. It trains epoch by epoch on the linear view, stops after
    ``patience`` epochs without a better loss and keeps the best epoch's weights; ``rounds``
    counts epochs. The best epoch is picked on ``STOPPING_SHARE`` of the training rows, set
    aside inside the fit, never on the validation rows: a network's loss is noisy from epoch
    to epoch, so picking the best epoch on the rows that also score the trial would flatter
    it, and the ensemble would over-trust it. Its final model is the average of the fold
    models (``refit = False``), as one network refit on all rows is as noisy as any other.

    Both linear-view families keep the training mean of each column as ``baseline_``, the
    reference point of their contributions (see ``fione.engine.explain``).
    """

    name = "DeepLearning"
    view = "linear"
    refit = False
    defaults = {"width": 64, "alpha": 1e-3, "learning_rate_init": 1e-3}
    max_epochs = 200
    patience = 10
    stopping_share = 0.15
    batch_size = 128

    def space(self, trial):
        return {
            "width": trial.suggest_int("width", 16, 256, log=True),
            "alpha": trial.suggest_float("alpha", 1e-6, 1e-1, log=True),
            "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-4, 1e-2, log=True),
        }

    def _loss(self, model, X, y) -> float:
        if not self.classification:
            return float(np.sqrt(np.mean((y - model.predict(X)) ** 2)))
        proba = np.clip(model.predict_proba(X), 1e-15, 1.0)
        return float(-np.mean(np.log(proba[np.arange(len(y)), y])))

    def _set_aside(self, X, y, sample_weight):
        """``X, X_stop, y, y_stop, sample_weight`` with a share of the rows set aside (stratified
        when every class has two rows or more)."""
        rows = np.arange(len(X))
        classes = np.bincount(y) if self.classification else None
        stratify = None
        if (
            classes is not None
            and classes.min() >= 2
            and self.stopping_share * len(y) >= len(classes)
        ):
            stratify = y
        fit, stop = train_test_split(
            rows, test_size=self.stopping_share, random_state=self.seed, stratify=stratify
        )
        weight = None if sample_weight is None else sample_weight[fit]
        return X.iloc[fit], X.iloc[stop], y[fit], y[stop], weight

    def _fit(self, params, X_tr, y_tr, X_va, y_va, deadline, sample_weight=None, rounds=None):
        params = dict(params)
        width = params.pop("width")
        stopping = X_va is not None
        if stopping:  # the epoch is picked on rows of the training fold, not on X_va
            X_tr, X_va, y_tr, y_va, sample_weight = self._set_aside(X_tr, y_tr, sample_weight)

        cls = MLPClassifier if self.classification else MLPRegressor
        model = cls(
            hidden_layer_sizes=(width, width),
            batch_size=min(self.batch_size, len(X_tr)),
            random_state=self.seed,
            **params,
        )
        extra = {"classes": np.arange(self.n_classes)} if self.classification else {}
        best, best_epoch, best_state = np.inf, 0, None
        for epoch in range(1, (self.max_epochs if stopping else rounds) + 1):
            model.partial_fit(X_tr, y_tr, sample_weight=sample_weight, **extra)
            if stopping:
                loss = self._loss(model, X_va, y_va)
                if loss < best:
                    best, best_epoch = loss, epoch
                    best_state = [w.copy() for w in model.coefs_ + model.intercepts_]
                elif epoch - best_epoch >= self.patience:
                    break
            if deadline.expired():
                break
        if stopping:
            layers = len(model.coefs_)
            model.coefs_, model.intercepts_ = best_state[:layers], best_state[layers:]
        model.fione_rounds_ = best_epoch if stopping else epoch
        model.baseline_ = X_tr.to_numpy(np.float64).mean(axis=0)
        return model

    def rounds(self, model) -> int:
        return model.fione_rounds_

    def size_bytes(self, model) -> int:
        return sum(w.size for w in model.coefs_ + model.intercepts_) * 8 + 1024

    def importance(self, model) -> np.ndarray:
        return by_feature(np.abs(model.coefs_[0]).sum(axis=1), model.feature_names_in_)


FAMILIES: dict[str, type[FamilySpec]] = {
    spec.name: spec
    for spec in (LightGBM, XGBoost, CatBoost, RandomForest, ExtraTrees, DeepLearning, Linear)
}
