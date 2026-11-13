"""The trained model ``AutoML.fit`` returns.

Everything in it is a top-level class, a library estimator or plain data, so it pickles; it
holds no training rows (see ``fione.engine.automl`` for what it keeps on request), except that
``diagnostics`` holds the class labels and, for regression, up to 2,000 sampled target values.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from fione.engine.config import ConfigError, TrainConfig
from fione.engine.families import FamilySpec, pad_features
from fione.engine.metrics import Cuts, choose, shift_to_equal_priors
from fione.engine.prep import Prep, Task


@dataclass
class Member:
    """One ensemble member: a model refit on all rows, or fold models whose outputs are averaged."""

    spec: FamilySpec
    weight: float
    models: list
    key: str = ""  # the candidate's name in the run (its family, or family#rank for a runner-up)


@dataclass
class TrainedModel:
    task: Task
    target: str
    classes_: list | None  # sorted original labels; None for regression
    columns: list[str]  # the input columns predict needs
    leaderboard: pd.DataFrame  # model, family, cv_score, cv_std, train_secs, weight
    trials: pd.DataFrame  # family, trial, state, score, elapsed, params (JSON)
    feature_importance: pd.Series  # per input column, summing to 1
    stop_reason: str  # time, max_models, no_improvement, cancelled or error
    config: TrainConfig
    metrics: dict[str, float]  # of the ensemble's out-of-fold predictions
    prep: Prep
    members: list[Member]
    label_dtype: object = None  # the target's dtype, for predicted labels
    cv_predictions: np.ndarray | None = None
    cv_models: dict | None = None
    fold_assignment: np.ndarray | None = None
    diagnostics: dict | None = None  # fione.engine.diagnostics of the OOF predictions; JSON
    features: list[dict] | None = None  # derived-feature groups tried, and why (engine.features)
    # The classes' shares (decision="balanced"), or (1 - t, t) for the threshold t ("tuned").
    class_prior: np.ndarray | None = None
    # The classes' shares of the training data when the probabilities are delivered shifted to
    # equal class priors (sort_metric="balanced_logloss"); older models have none.
    proba_shift: np.ndarray | None = None

    def choose(self, proba: np.ndarray) -> np.ndarray:
        """The class index per row of ``proba`` under the model's decision rule."""
        return choose(proba, self.class_prior)

    def _predict(self, df: pd.DataFrame) -> np.ndarray:
        # The views come first, so that missing columns raise even for an empty frame.
        names = dict.fromkeys(member.spec.view for member in self.members)
        views = {name: getattr(self.prep, name)(df) for name in names}
        if len(df) == 0:  # some libraries reject empty input or print about it
            return np.zeros((0, len(self.classes_))) if self.classes_ is not None else np.zeros(0)
        total = 0.0
        for member in self.members:
            spec = member.spec
            outputs = [spec.predict(model, views[spec.view]) for model in member.models]
            total = total + member.weight * np.mean(outputs, axis=0)
        return total

    def predict_proba(self, df: pd.DataFrame) -> pd.DataFrame:
        """Class probabilities, one column per entry of ``classes_``, on ``df``'s index."""
        if self.task != "classification":
            raise ConfigError("predict_proba needs a classification model")
        proba = self._predict(df)
        proba = proba / proba.sum(axis=1, keepdims=True)
        if self.proba_shift is not None and len(proba):
            proba = shift_to_equal_priors(proba, self.proba_shift)
        return pd.DataFrame(proba, index=df.index, columns=self.classes_)

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """Predicted labels (the target's values and dtype) or floats, on ``df``'s index."""
        raw = self._predict(df)
        if self.task == "regression":
            if self.config.target_transform == "log1p":
                raw = np.expm1(raw)
            if isinstance(self.class_prior, Cuts):  # rounded_qwk: the rating its cut points give
                raw = self.class_prior[0] + np.searchsorted(np.asarray(self.class_prior[1:]), raw)
            return pd.Series(raw, index=df.index, name=self.target, dtype=float)
        if self.proba_shift is not None and len(raw):
            raw = shift_to_equal_priors(raw, self.proba_shift)
        labels = np.asarray(self.classes_, dtype=object)[self.choose(raw)]
        return pd.Series(labels, index=df.index, name=self.target).astype(self.label_dtype)


def _normalised(values: np.ndarray) -> np.ndarray:
    total = values.sum()
    return values / total if total > 0 else np.zeros_like(values)


def attribution(prep: Prep) -> np.ndarray:
    """Matrix (columns x features) giving each feature's share per input column; the shares of
    a feature sum to 1."""
    position = {column: i for i, column in enumerate(prep.columns)}
    matrix = np.zeros((len(prep.columns), len(prep.sources)))
    for j, sources in enumerate(prep.sources):
        sources = (sources,) if isinstance(sources, str) else sources  # models of older versions
        for column in sources:
            matrix[position[column], j] += 1 / len(sources)
    return matrix


def feature_importance(members: list[Member], prep: Prep) -> pd.Series:
    """Weight-averaged importance of the members, summed back onto the input columns.

    Each model's importance (boosting: gain; forests: impurity; Linear and DeepLearning:
    absolute weights) is normalised to sum to 1 first, so families are comparable; expanded
    features (datetime parts, derived features) count for their source columns, a feature with
    several sources splitting its share equally. Columns no model uses get 0; if no model uses
    any, all get equal shares.
    """
    total = np.zeros(len(prep.sources))
    for member in members:
        per_model = [
            _normalised(pad_features(member.spec.importance(model), len(prep.sources)))
            for model in member.models
        ]
        total += member.weight * np.mean(per_model, axis=0)
    by_column = pd.Series(attribution(prep) @ total, index=prep.columns)
    if by_column.sum() <= 0:
        by_column[:] = 1.0
    return (by_column / by_column.sum()).sort_values(ascending=False, kind="stable")
