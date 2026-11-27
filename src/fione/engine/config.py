"""Training configuration, the time budget and the engine's errors."""

import time
from dataclasses import asdict, dataclass, field, fields
from typing import Literal


class ConfigError(ValueError):
    """Bad user input (configuration or data); the message is shown to the user as is."""


class TargetError(ConfigError):
    """The target column cannot be trained on. ``code`` names the rule it breaks and
    ``details`` holds its numbers, so a UI can say it in its own words."""

    def __init__(self, message: str, code: str, **details):
        super().__init__(message)
        self.code = code
        self.details = details


class NoModelError(RuntimeError):
    """No model could be trained, e.g. because the time budget is too small. ``needed_secs`` is
    the time a first trial would have needed, when it is known."""

    def __init__(self, message: str, needed_secs: float | None = None):
        super().__init__(message)
        self.needed_secs = needed_secs


class DeadlineExceeded(Exception):
    """Internal: a fit was aborted by its deadline before it produced a usable iteration."""


_TASKS = ("auto", "classification", "regression")
_DECISIONS = ("argmax", "balanced", "tuned", "cost")
_TRANSFORMS = ("none", "log1p")
# The folds' random_state (numpy's RandomState through scikit-learn) takes 0..2**32 - 1.
MAX_SEED = 2**32 - 1
MAX_COST = 1e12  # the largest cost_miss or cost_false_alarm
MAX_CV_REPEATS = 10  # every repeat refits every fold of every trial
# The metric names, compared case-insensitively: ``auto`` and every metric of
# ``fione.engine.metrics``, which accepts the subset that fits the task.
_METRICS = frozenset(
    {
        "auto",
        "logloss",
        "auc",
        "accuracy",
        "aucpr",
        "gini",
        "lift_top_group",
        "balanced_accuracy",
        "misclassification",
        "mean_per_class_error",
        "f1",
        "macro_f1",
        "precision",
        "recall",
        "mcc",
        "kappa",
        "qwk",
        "brier",
        "balanced_logloss",
        "top3_accuracy",
        "map3",
        "rmse",
        "pinball",
        "concordance",
        "mae",
        "r2",
        "mse",
        "rmsle",
        "mape",
        "rmspe",
        "smape",
        "medae",
        "explained_variance",
        "pearson",
        "spearman",
        "normalized_gini",
        "poisson",
        "rounded_qwk",
    }
)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_int(name: str, value, minimum: int, optional: bool = False) -> None:
    if optional and value is None:
        return
    if not _is_int(value) or value < minimum:
        allowed = " (or empty)" if optional else ""
        raise ConfigError(
            f"{name} must be a whole number of at least {minimum}{allowed}, got {value!r}"
        )


@dataclass
class TrainConfig:
    target: str
    task: Literal["auto", "classification", "regression"] = "auto"
    max_runtime_secs: int = 3600
    max_runtime_secs_per_model: int | None = None
    max_models: int | None = None
    nfolds: int = 5
    seed: int = 0
    balance_classes: bool = False
    decision: Literal["argmax", "balanced", "tuned", "cost"] = "argmax"
    # What a row of the second class given the first (a miss) and a row of the first class given
    # the second (a false alarm) cost, for decision "cost": the threshold with the lowest cost.
    cost_miss: float | None = None
    cost_false_alarm: float | None = None
    target_transform: Literal["none", "log1p"] = "none"
    feature_engineering: bool = True
    stopping_rounds: int = 10
    stopping_metric: str = "auto"
    stopping_tolerance: float = 0.001
    sort_metric: str = "auto"
    keep_cv_predictions: bool = False
    keep_cv_models: bool = False
    keep_cv_fold_assignment: bool = False
    ignored_columns: list[str] = field(default_factory=list)
    # Rows that share a value of this column are kept together in one fold, so the validation
    # rows never hold a group the training rows have seen. None: rows are split at random.
    cv_group_column: str | None = None
    # How many times the folds are drawn again with other seeds, each repeat judging a trial
    # alone and the scores averaged. None: by the number of rows (3 up to 2,000, 2 up to 5,000,
    # else 1); 1: never.
    cv_repeats: int | None = None
    # Validate looking forward in time: the rows ordered by this column (a number or a date, which
    # may also be ignored as a feature) are cut into parts, and each fold learns from the parts
    # before the one it predicts. With cv_group_column too, a group is ordered by its last row and
    # kept in one part. None: shuffled folds.
    time_column: str | None = None
    # Learn this quantile of the target (a regression, 0 < quantile < 1) instead of its mean:
    # the models fit the pinball loss, and only the families that can do so are searched.
    quantile: float | None = None
    # The target is a time that may be cut short (a regression), and this column says for each row
    # whether the event happened at that time (1) or the row was only seen up to it (0). The
    # models then learn a score that grows with the time (``fione.engine.survival``), and
    # ``concordance`` ranks them. The column is not a feature.
    event_column: str | None = None
    # Weight of the extra rows given to ``AutoML.fit`` among the rows the models learn from (1: as
    # the rows of the data). Scores are never weighted.
    extra_weight: float = 1.0
    # Vectors of the prose columns from a pretrained language model (``fione.engine.embedding``):
    # the backend, a label for the model, the layer (a fraction of its depth) and the longest text
    # read, in tokens. With a backend, the TextEmbedding family joins the search (late, so that
    # the cross-validation decides whether it helps); without one it is not tried.
    embedding_backend: str | None = None
    embedding_model: str = ""
    embedding_layer: float = 0.75
    embedding_max_length: int = 384

    @property
    def embedding(self):
        """The ``EmbeddingSpec`` the settings name, or None without a backend."""
        if self.embedding_backend is None:
            return None
        from fione.engine.embedding import EmbeddingSpec

        return EmbeddingSpec(
            self.embedding_backend,
            self.embedding_model,
            self.embedding_layer,
            self.embedding_max_length,
        )

    def validate(self) -> "TrainConfig":
        """Raise ConfigError for the first invalid value; return self when everything is valid."""
        if not isinstance(self.target, str) or not self.target:
            raise ConfigError("target must name a column")
        if self.task not in _TASKS:
            raise ConfigError(f"task must be one of {list(_TASKS)}, got {self.task!r}")
        _check_int("max_runtime_secs", self.max_runtime_secs, 1)
        _check_int("max_runtime_secs_per_model", self.max_runtime_secs_per_model, 1, optional=True)
        _check_int("max_models", self.max_models, 1, optional=True)
        _check_int("nfolds", self.nfolds, 2)
        _check_int("cv_repeats", self.cv_repeats, 1, optional=True)
        if self.cv_repeats is not None and self.cv_repeats > MAX_CV_REPEATS:
            raise ConfigError(
                f"cv_repeats must be a whole number from 1 to {MAX_CV_REPEATS} (or empty), "
                f"got {self.cv_repeats!r}"
            )
        if not _is_int(self.seed) or not 0 <= self.seed <= MAX_SEED:
            raise ConfigError(
                f"seed must be a whole number from 0 to {MAX_SEED}, got {self.seed!r}"
            )
        if self.decision not in _DECISIONS:
            raise ConfigError(f"decision must be one of {list(_DECISIONS)}, got {self.decision!r}")
        if self.target_transform not in _TRANSFORMS:
            raise ConfigError(
                f"target_transform must be one of {list(_TRANSFORMS)}, "
                f"got {self.target_transform!r}"
            )
        _check_int("stopping_rounds", self.stopping_rounds, 0)
        tolerance = self.stopping_tolerance
        if (
            not isinstance(tolerance, int | float)
            or isinstance(tolerance, bool)
            or not tolerance >= 0
        ):
            raise ConfigError(
                f"stopping_tolerance must be a number of at least 0, got {tolerance!r}"
            )
        for name in ("stopping_metric", "sort_metric"):
            value = getattr(self, name)
            if not isinstance(value, str) or value.lower() not in _METRICS:
                raise ConfigError(f"{name} must be one of {sorted(_METRICS)}, got {value!r}")
        for name in (
            "balance_classes",
            "feature_engineering",
            "keep_cv_predictions",
            "keep_cv_models",
            "keep_cv_fold_assignment",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ConfigError(f"{name} must be true or false, got {getattr(self, name)!r}")
        costs = {"cost_miss": self.cost_miss, "cost_false_alarm": self.cost_false_alarm}
        if self.decision == "cost":
            for name, cost in costs.items():
                if not _is_number(cost) or not 0 < cost <= MAX_COST:
                    raise ConfigError(
                        f"decision 'cost' needs {name} above 0 and at most {MAX_COST:.0e}, "
                        f"got {cost!r}"
                    )
        elif any(cost is not None for cost in costs.values()):
            raise ConfigError("cost_miss and cost_false_alarm are used with decision 'cost' only")
        if self.decision == "balanced" and self.balance_classes:
            raise ConfigError(
                "decision 'balanced' and balance_classes both correct for rare classes; use one"
            )
        ignored = self.ignored_columns
        if not isinstance(ignored, list) or not all(isinstance(c, str) for c in ignored):
            raise ConfigError("ignored_columns must be a list of column names")
        if self.target in ignored:
            raise ConfigError(f"the target column '{self.target}' cannot also be ignored")
        group = self.cv_group_column
        if group is not None and (not isinstance(group, str) or not group):
            raise ConfigError("cv_group_column must name a column or be empty")
        if group == self.target:
            raise ConfigError(f"the target column '{self.target}' cannot also be the group column")
        if self.time_column is not None and (
            not isinstance(self.time_column, str) or not self.time_column
        ):
            raise ConfigError("time_column must name a column or be empty")
        if self.time_column == self.target:
            raise ConfigError("the time column cannot be the target")
        q = self.quantile
        if q is not None:
            if not isinstance(q, int | float) or isinstance(q, bool) or not 0 < q < 1:
                raise ConfigError(f"quantile must be a number above 0 and below 1, got {q!r}")
            if self.task == "classification":
                raise ConfigError("quantile needs a regression, not a classification")
        elif "pinball" in (self.stopping_metric.lower(), self.sort_metric.lower()):
            raise ConfigError("the pinball metric needs a quantile")
        weight = self.extra_weight
        if not isinstance(weight, int | float) or isinstance(weight, bool) or not 0 < weight <= 1e6:
            raise ConfigError(f"extra_weight must be a number above 0, got {weight!r}")
        if self.embedding_backend is not None:
            self.embedding.validate()
        event = self.event_column
        if event is None:
            if "concordance" in (self.stopping_metric.lower(), self.sort_metric.lower()):
                raise ConfigError("the concordance metric needs an event_column")
            return self
        if not isinstance(event, str) or not event:
            raise ConfigError("event_column must name a column or be empty")
        if event == self.target:
            raise ConfigError("the event column cannot be the target")
        if self.task == "classification":
            raise ConfigError("event_column needs a regression: the target is the time")
        if q is not None:
            raise ConfigError("event_column and quantile cannot be used together")
        if self.target_transform != "none":
            raise ConfigError("event_column cannot be used with a target_transform")
        for name in ("stopping_metric", "sort_metric"):
            if getattr(self, name).lower() not in ("auto", "concordance"):
                raise ConfigError(f"{name} must be auto or concordance with an event_column")
        return self

    @classmethod
    def from_dict(cls, data: dict) -> "TrainConfig":
        """Build a validated config from a job payload."""
        unknown = sorted(set(data) - {f.name for f in fields(cls)})
        if unknown:
            raise ConfigError(f"unknown parameters: {unknown}")
        if "target" not in data:
            raise ConfigError("target is required")
        return cls(**data).validate()

    def to_dict(self) -> dict:
        return asdict(self)


class Deadline:
    """A wall-clock budget on the monotonic clock."""

    def __init__(self, total_secs: float):
        self._end = time.monotonic() + max(0.0, total_secs)

    def remaining(self) -> float:
        return max(0.0, self._end - time.monotonic())

    def expired(self) -> bool:
        return time.monotonic() >= self._end

    def child(self, secs: float) -> "Deadline":
        """A deadline ``secs`` from now, cut short to never end after this one."""
        child = Deadline(0)
        child._end = min(self._end, time.monotonic() + max(0.0, secs))
        return child
