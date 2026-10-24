"""Batch prediction: a frame in, the predictions bound to the chosen input columns out."""

from collections.abc import Iterator, Sequence

import numpy as np
import pandas as pd

from fione.engine.config import ConfigError
from fione.engine.model import TrainedModel

PREDICT = "predict"
CHUNK_ROWS = 50_000
_SHOWN_VALUES = 3


class PredictInputError(ValueError):
    """The data cannot be predicted on; the message is meant for the user."""


def prediction_columns(model: TrainedModel) -> list[str]:
    """``predict``, then ``p_<class>`` per class for classification."""
    return [PREDICT] + [f"p_{label}" for label in model.classes_ or []]


def check_include_columns(columns: Sequence[str], include_columns: Sequence[str] | None) -> None:
    if include_columns is None:
        return
    known = set(columns)
    unknown = [c for c in include_columns if c not in known]
    if unknown:
        raise PredictInputError(f"unknown columns in include_columns: {unknown}")


def included_columns(
    model: TrainedModel, columns: Sequence[str], include_columns: Sequence[str] | None = None
) -> dict[str, str]:
    """Output name -> input column, in output order, for the input columns carried along.

    An input column named like a prediction column is renamed with an ``input_`` prefix (and a
    numeric suffix while that still collides with another output or input column).
    """
    check_include_columns(columns, include_columns)
    chosen = list(columns if include_columns is None else include_columns)
    reserved = set(prediction_columns(model))
    taken = reserved | {c for c in chosen if c not in reserved}
    out: dict[str, str] = {}
    for column in chosen:
        name = column
        if column in reserved:
            name, number = f"input_{column}", 1
            while name in taken:
                number += 1
                name = f"input_{column}_{number}"
            taken.add(name)
        out[name] = column
    return out


def _check_inputs(model: TrainedModel, df: pd.DataFrame) -> None:
    missing = [c for c in model.prep.columns if c not in df.columns]
    if missing:
        raise PredictInputError(f"missing columns: {missing}")
    for column in model.prep.numeric_columns:
        values = df[column]
        if pd.api.types.is_numeric_dtype(values.dtype):
            continue
        unreadable = values[pd.to_numeric(values, errors="coerce").isna() & values.notna()]
        if len(unreadable):
            shown = unreadable.drop_duplicates().head(_SHOWN_VALUES).tolist()
            raise PredictInputError(
                f"column {column!r} must hold numbers, but has values such as {shown}"
            )


def predict_chunks(
    model: TrainedModel,
    df: pd.DataFrame,
    include_columns: Sequence[str] | None = None,
    *,
    chunk_rows: int = CHUNK_ROWS,
) -> Iterator[pd.DataFrame]:
    """``batch_predict`` piece by piece, ``chunk_rows`` input rows at a time (index 0..n-1 within
    each piece; an empty input gives one empty piece with the columns).

    The input is validated before this returns, so ``PredictInputError`` is raised here and
    not midway through the iteration.
    """
    if chunk_rows < 1:
        raise ValueError("chunk_rows must be at least 1")
    kept = included_columns(model, df.columns, include_columns)
    _check_inputs(model, df)
    return (
        _predict(model, df.iloc[start : start + chunk_rows].reset_index(drop=True), kept)
        for start in range(0, len(df), chunk_rows) or [0]
    )


def _predict(model: TrainedModel, part: pd.DataFrame, kept: dict[str, str]) -> pd.DataFrame:
    try:
        if model.classes_ is None:
            result = pd.DataFrame({PREDICT: model.predict(part).to_numpy()})
        else:
            proba = model.predict_proba(part)
            labels = np.asarray(model.classes_, dtype=object)[proba.to_numpy().argmax(axis=1)]
            result = pd.DataFrame({PREDICT: pd.Series(labels).astype(model.label_dtype)})
            result[prediction_columns(model)[1:]] = proba.to_numpy()
    except ConfigError as e:
        raise PredictInputError(str(e)) from e
    inputs = part[list(kept.values())]
    inputs.columns = list(kept)
    return pd.concat([result, inputs], axis=1)


def batch_predict(
    model: TrainedModel,
    df: pd.DataFrame,
    include_columns: Sequence[str] | None = None,
    *,
    chunk_rows: int = CHUNK_ROWS,
) -> pd.DataFrame:
    """Predictions for every row of ``df``, in order, with a fresh 0..n-1 index.

    Columns: ``predict``, one ``p_<class>`` per class (classification), then the input columns
    chosen by ``include_columns`` (all of them by default; see ``included_columns`` for
    renames). Raises ``PredictInputError`` for missing columns, unknown ``include_columns`` or
    text in a column the model reads as numeric. Rows are predicted ``chunk_rows`` at a time.
    """
    return pd.concat(
        predict_chunks(model, df, include_columns, chunk_rows=chunk_rows), ignore_index=True
    )
