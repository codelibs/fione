"""Target checks and the feature preprocessing shared by all model families."""

from typing import Literal

import numpy as np
import pandas as pd

from fione.data.frames import parse_datetimes
from fione.engine.config import ConfigError
from fione.engine.events import Event, EventSink

Task = Literal["classification", "regression"]

HIGH_CARDINALITY = 200  # categorical columns with more categories are frequency encoded
MIN_ROWS = 10
# ordinal: seconds since the Unix epoch
_DATE_PARTS = ("year", "month", "day", "dayofweek", "ordinal")
_EPOCH = pd.Timestamp("1970-01-01")


def _is_categorical(s: pd.Series) -> bool:
    return pd.api.types.is_bool_dtype(s.dtype) or not pd.api.types.is_numeric_dtype(s.dtype)


def _as_str(s: pd.Series) -> pd.Series:
    """Values as strings, missing values kept missing."""
    return s.astype(str).where(s.notna())


def _datetimes(s: pd.Series) -> pd.Series:
    """``s`` as naive (UTC for tz-aware input) datetimes; unparseable values become NaT."""
    if not pd.api.types.is_datetime64_any_dtype(s.dtype):
        s = parse_datetimes(s)
    if isinstance(s.dtype, pd.DatetimeTZDtype):
        s = s.dt.tz_convert("UTC").dt.tz_localize(None)
    return s


class Prep:
    """Turns raw feature frames into the inputs of each model family.

    ``fit`` decides per column: constant and all-null columns are dropped; datetime columns are
    expanded into numeric parts; bool and non-numeric columns become categoricals, or frequency
    encodings above ``HIGH_CARDINALITY`` categories; everything else is numeric. The views put the
    features in ``feature_names`` order under positional names ``f0, f1, ...``, because model
    libraries reject some characters in feature names.
    """

    def fit(self, X: pd.DataFrame) -> "Prep":
        self.dropped: list[str] = []
        self._plan: list[
            tuple[str, str]
        ] = []  # (column, kind), kind: numeric/datetime/frequency/category
        self.categories: dict[str, list[str]] = {}
        self.frequencies: dict[str, dict[str, float]] = {}
        for column in X.columns:
            s = X[column]
            if s.nunique(dropna=False) <= 1:
                self.dropped.append(column)
            elif pd.api.types.is_datetime64_any_dtype(s.dtype):
                self._plan.append((column, "datetime"))
            elif _is_categorical(s):
                counts = _as_str(s).value_counts()
                if len(counts) > HIGH_CARDINALITY:
                    self.frequencies[column] = (counts / len(s)).to_dict()
                    self._plan.append((column, "frequency"))
                else:
                    self.categories[column] = sorted(counts.index)
                    self._plan.append((column, "category"))
            else:
                self._plan.append((column, "numeric"))
        if not self._plan:
            raise ConfigError("no usable feature columns: every column is empty or constant")
        self.feature_names: list[str] = []
        self.sources: list[str] = []  # the input column behind each feature
        self._category_at: dict[str, str] = {}  # view column -> categorical source column
        for column, kind in self._plan:
            if kind == "category":
                self._category_at[f"f{len(self.feature_names)}"] = column
            if kind == "datetime":
                self.feature_names += [f"{column}__{part}" for part in _DATE_PARTS]
                self.sources += [column] * len(_DATE_PARTS)
            else:
                self.feature_names.append(column)
                self.sources.append(column)
        base = self._base(X)
        self._medians = base.drop(columns=list(self._category_at)).median().fillna(0.0).to_dict()
        return self

    @property
    def columns(self) -> list[str]:
        """The input columns the views need, in order."""
        return [column for column, _ in self._plan]

    @property
    def numeric_columns(self) -> list[str]:
        """The input columns the model reads as numbers."""
        return [column for column, kind in self._plan if kind == "numeric"]

    def _base(self, df: pd.DataFrame) -> pd.DataFrame:
        """Numeric features as float, categorical ones as strings (NaN when missing)."""
        missing = [c for c, _ in self._plan if c not in df.columns]
        if missing:
            raise ConfigError(f"missing columns: {missing}")
        out: list[pd.Series] = []
        for column, kind in self._plan:
            s = df[column]
            if kind == "numeric":
                values = pd.to_numeric(s, errors="coerce").astype(float)
                out.append(values.replace([np.inf, -np.inf], np.nan))
            elif kind == "datetime":
                when = _datetimes(s)
                out += [when.dt.year, when.dt.month, when.dt.day, when.dt.day_of_week]
                out.append((when - _EPOCH).dt.total_seconds())
            elif kind == "frequency":
                values = _as_str(s)
                encoded = values.map(self.frequencies[column]).astype(float)
                out.append(encoded.mask(encoded.isna() & values.notna(), 0.0))  # unseen: never seen
            else:
                out.append(_as_str(s))
        frame = pd.concat([o.reset_index(drop=True) for o in out], axis=1)
        frame.columns = [f"f{i}" for i in range(len(self.feature_names))]
        frame.index = df.index
        for position in frame.columns:
            if position not in self._category_at:
                frame[position] = frame[position].astype(float)
        return frame

    def _categorical(self, base: pd.DataFrame) -> dict[str, pd.Categorical]:
        out = {}
        for position, column in self._category_at.items():
            categories = self.categories[column]
            values = base[position]
            out[position] = pd.Categorical(
                values.where(values.isin(categories)), categories=categories
            )
        return out

    def tree(self, df: pd.DataFrame) -> pd.DataFrame:
        """Categoricals as category dtype (unseen values become NaN), for LightGBM and XGBoost."""
        base = self._base(df)
        for position, values in self._categorical(base).items():
            base[position] = values
        return base

    def catboost(self, df: pd.DataFrame) -> pd.DataFrame:
        """Categoricals as object strings with ``"__na__"`` for missing values, for CatBoost."""
        base = self._base(df)
        for position in self._category_at:
            base[position] = base[position].fillna("__na__").astype(object)
        return base

    def dense(self, df: pd.DataFrame) -> pd.DataFrame:
        """All float: category codes (-1 when missing or unseen) and median-imputed numbers."""
        base = self._base(df)
        for position, values in self._categorical(base).items():
            base[position] = values.codes.astype(float)
        return base.fillna(self._medians)


def infer_task(y: pd.Series) -> Task:
    """Classification for non-numeric/bool targets and few integer values, else regression."""
    if _is_categorical(y):
        return "classification"
    values = y.dropna()
    distinct = values.nunique()
    if (
        len(values)
        and distinct <= 20
        and distinct / len(values) <= 0.05
        and bool((values % 1 == 0).all())
    ):
        return "classification"
    return "regression"


def _sorted_labels(y: pd.Series) -> list:
    labels = [v.item() if isinstance(v, np.generic) else v for v in y.unique()]
    try:
        return sorted(labels)
    except TypeError:  # mixed types
        return sorted(labels, key=str)


def validate_target(
    y: pd.Series, task: Task, nfolds: int, emit: EventSink | None = None
) -> tuple[np.ndarray, list, int]:
    """Check the target and encode it for training.

    Returns ``(encoded, classes, nfolds)``: float values for regression, or class codes 0..k-1
    whose labels are ``classes`` (sorted; ``[]`` for regression); and the fold count reduced to
    min(nfolds, smallest class size, rows // 5), at least 2, emitting a ``notice`` event with
    ``nfolds_reduced_to`` and ``reason`` when it was reduced. ``task`` must already be resolved.
    """
    n = len(y)
    if n < MIN_ROWS:
        raise ConfigError(f"not enough rows: {n} (at least {MIN_ROWS} are needed)")
    missing = int(y.isna().sum())
    if missing:
        raise ConfigError(
            f"target has missing values in {missing} rows; "
            "remove those rows or choose another column"
        )
    distinct = y.nunique()
    if distinct < 2:
        raise ConfigError("target has a single distinct value; there is nothing to predict")
    limit, reason = n // 5, f"only {n} rows"
    if task == "regression":
        if _is_categorical(y):
            raise ConfigError("target must be numeric for regression")
        encoded = y.to_numpy(dtype=float)
        if not np.isfinite(encoded).all():
            raise ConfigError("target has infinite values")
        classes = []
    else:
        if distinct > max(100, 0.5 * n):
            advice = "use regression or " if not _is_categorical(y) else ""
            raise ConfigError(
                f"target has {distinct} distinct values, too many for classification; "
                f"{advice}choose another column"
            )
        classes = _sorted_labels(y)
        encoded = pd.Categorical(y, categories=classes).codes.astype(np.int64)
        counts = np.bincount(encoded)
        singles = [classes[i] for i in np.flatnonzero(counts == 1)]
        if singles:
            raise ConfigError(
                f"class {singles[0]!r} has only 1 row ({len(singles)} such classes); "
                "each class needs at least 2 rows"
            )
        if counts.min() < limit:
            limit, reason = int(counts.min()), f"smallest class has {counts.min()} rows"
    folds = max(2, min(nfolds, limit))
    if folds < nfolds and emit is not None:
        message = f"nfolds reduced to {folds}: {reason}"
        emit(
            Event("notice", data={"message": message, "nfolds_reduced_to": folds, "reason": reason})
        )
    return encoded, classes, folds
