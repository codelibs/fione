"""Training configuration, the time budget and the engine's errors."""

import time
from dataclasses import asdict, dataclass, field, fields
from typing import Literal


class ConfigError(ValueError):
    """Bad user input (configuration or data); the message is shown to the user as is."""


class NoModelError(RuntimeError):
    """No model could be trained, e.g. because the time budget is too small."""


class DeadlineExceeded(Exception):
    """Internal: a fit was aborted by its deadline before it produced a usable iteration."""


_TASKS = ("auto", "classification", "regression")
# H2O's metric names, compared case-insensitively.
_METRICS = frozenset(
    {
        "auto",
        "deviance",
        "logloss",
        "mse",
        "rmse",
        "mae",
        "rmsle",
        "auc",
        "aucpr",
        "lift_top_group",
        "misclassification",
        "mean_per_class_error",
    }
)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


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
    stopping_rounds: int = 3
    stopping_metric: str = "auto"
    stopping_tolerance: float = 0.001
    sort_metric: str = "auto"
    keep_cv_predictions: bool = False
    keep_cv_models: bool = False
    keep_cv_fold_assignment: bool = False
    ignored_columns: list[str] = field(default_factory=list)

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
        if not _is_int(self.seed):
            raise ConfigError(f"seed must be a whole number, got {self.seed!r}")
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
            "keep_cv_predictions",
            "keep_cv_models",
            "keep_cv_fold_assignment",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ConfigError(f"{name} must be true or false, got {getattr(self, name)!r}")
        ignored = self.ignored_columns
        if not isinstance(ignored, list) or not all(isinstance(c, str) for c in ignored):
            raise ConfigError("ignored_columns must be a list of column names")
        if self.target in ignored:
            raise ConfigError(f"the target column '{self.target}' cannot also be ignored")
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
