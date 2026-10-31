"""Batch prediction: a frame in, the predictions bound to the chosen input columns out."""

from collections.abc import Iterator, Sequence

import numpy as np
import pandas as pd

from fione.engine import explain
from fione.engine.config import ConfigError
from fione.engine.model import TrainedModel

PREDICT = "predict"
CHUNK_ROWS = 50_000
MAX_CONTRIBUTION_ROWS = 100_000  # contributions cost 30-300x a prediction
CONTRIBUTION_CHUNK_ROWS = 5_000
_SHOWN_VALUES = 3


class PredictInputError(ValueError):
    """The data cannot be predicted on; the message is meant for the user."""


def prediction_columns(model: TrainedModel) -> list[str]:
    """``predict``, then ``p_<class>`` per class for classification."""
    return [PREDICT] + [f"p_{label}" for label in model.classes_ or []]


def contribution_columns(model: TrainedModel) -> list[str]:
    """``contrib_<column>`` per model column, then the bias: ``contrib_bias``, or
    ``contrib_bias_2``... while a model column's name takes it (a column named ``bias``)."""
    names = [f"contrib_{column}" for column in model.columns]
    bias, number = "contrib_bias", 1
    while bias in names:
        number += 1
        bias = f"contrib_bias_{number}"
    return [*names, bias]


def check_contribution_rows(n_rows: int) -> None:
    if n_rows > MAX_CONTRIBUTION_ROWS:
        raise PredictInputError(f"contributions are limited to {MAX_CONTRIBUTION_ROWS:,} rows")


def check_include_columns(columns: Sequence[str], include_columns: Sequence[str] | None) -> None:
    if include_columns is None:
        return
    known = set(columns)
    unknown = [c for c in include_columns if c not in known]
    if unknown:
        raise PredictInputError(f"unknown columns in include_columns: {unknown}")


def included_columns(
    model: TrainedModel,
    columns: Sequence[str],
    include_columns: Sequence[str] | None = None,
    *,
    contributions: bool = False,
) -> dict[str, str]:
    """Output name -> input column, in output order, for the input columns carried along.

    An input column named like a prediction column (or, with ``contributions``, a contribution
    column) is renamed with an ``input_`` prefix (and a numeric suffix while that still
    collides with another output or input column).
    """
    check_include_columns(columns, include_columns)
    chosen = list(columns if include_columns is None else include_columns)
    reserved = set(prediction_columns(model))
    if contributions:
        reserved |= set(contribution_columns(model))
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


def encodable(text: str) -> bool:
    """False for text that cannot be written as UTF-8, such as a lone surrogate."""
    if text.isascii():
        return True
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def unencodable_text(values: pd.Series) -> pd.Series:
    """True where ``values`` holds text that is not valid Unicode (see ``encodable``).

    Pandas' string handling raises ``UnicodeEncodeError`` on such text, so it is found before
    anything else looks at the column.
    """
    if pd.api.types.is_numeric_dtype(values.dtype) or pd.api.types.is_datetime64_any_dtype(
        values.dtype
    ):
        return pd.Series(False, index=values.index)
    return pd.Series([isinstance(v, str) and not encodable(v) for v in values], index=values.index)


def unreadable_numbers(values: pd.Series) -> pd.Series:
    """True where ``values`` holds something a numeric column cannot read as a number.

    Missing values and blank text count as missing, as in the engine, so they are readable.
    Text that is not valid Unicode is unreadable. A value like ``1e999`` reads as infinity,
    which the engine treats as missing.
    """
    if pd.api.types.is_numeric_dtype(values.dtype):
        return pd.Series(False, index=values.index)
    broken = unencodable_text(values)
    values = values.mask(broken)
    blank = values.astype(str).str.strip() == ""
    return (pd.to_numeric(values, errors="coerce").isna() & values.notna() & ~blank) | broken


def check_inputs(model: TrainedModel, df: pd.DataFrame) -> None:
    missing = [c for c in model.prep.columns if c not in df.columns]
    if missing:
        raise PredictInputError(f"missing columns: {missing}")
    numeric = model.prep.numeric_columns
    for column in model.prep.columns:
        if column not in numeric and unencodable_text(df[column]).any():
            raise PredictInputError(f"column {column!r} has text that is not valid Unicode")
    for column in numeric:
        values = df[column]
        unreadable = values[unreadable_numbers(values)]
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
    contributions: bool = False,
) -> Iterator[pd.DataFrame]:
    """``batch_predict`` piece by piece, ``chunk_rows`` input rows at a time (index 0..n-1 within
    each piece; an empty input gives one empty piece with the columns).

    With ``contributions`` the pieces are at most ``CONTRIBUTION_CHUNK_ROWS`` rows, fewer for
    a model whose rows x classes x columns would pass the explanations' cell cap, and the
    input is limited to ``MAX_CONTRIBUTION_ROWS`` rows.

    The input is validated before this returns, so ``PredictInputError`` is raised here and
    not midway through the iteration.
    """
    if chunk_rows < 1:
        raise ValueError("chunk_rows must be at least 1")
    kept = included_columns(model, df.columns, include_columns, contributions=contributions)
    check_inputs(model, df)
    if contributions:
        check_contribution_rows(len(df))
        rows = explain.contribution_rows(model, CONTRIBUTION_CHUNK_ROWS)
        if rows == 0:
            raise PredictInputError("this model is too wide to explain row by row")
        chunk_rows = min(chunk_rows, rows)
    return (
        _predict(
            model, df.iloc[start : start + chunk_rows].reset_index(drop=True), kept, contributions
        )
        for start in range(0, len(df), chunk_rows) or [0]
    )


def _predict(
    model: TrainedModel, part: pd.DataFrame, kept: dict[str, str], contributions: bool = False
) -> pd.DataFrame:
    try:
        if model.classes_ is None:
            result = pd.DataFrame({PREDICT: model.predict(part).to_numpy()})
            slots = np.zeros(len(part), dtype=int)
        else:
            proba = model.predict_proba(part).to_numpy()
            chosen = proba.argmax(axis=1)
            labels = np.asarray(model.classes_, dtype=object)[chosen]
            result = pd.DataFrame({PREDICT: pd.Series(labels).astype(model.label_dtype)})
            result[prediction_columns(model)[1:]] = proba
            # binary explains its positive class; multiclass the class in ``predict``
            slots = chosen if len(model.classes_) > 2 else np.zeros(len(part), dtype=int)
        parts = [result]
        if contributions:
            parts.append(_contributions(model, part, slots))
    except ConfigError as e:
        raise PredictInputError(str(e)) from e
    inputs = part[list(kept.values())]
    inputs.columns = list(kept)
    return pd.concat([*parts, inputs], axis=1)


def _contributions(model: TrainedModel, part: pd.DataFrame, slots: np.ndarray) -> pd.DataFrame:
    """Each row's contributions to its explained output, then that output's bias."""
    c = explain.contributions(model, part)
    rows = np.arange(len(part))
    values = np.column_stack([c.values[rows, slots], c.bias[rows, slots]])
    return pd.DataFrame(values, columns=contribution_columns(model))


def batch_predict(
    model: TrainedModel,
    df: pd.DataFrame,
    include_columns: Sequence[str] | None = None,
    *,
    chunk_rows: int = CHUNK_ROWS,
    contributions: bool = False,
) -> pd.DataFrame:
    """Predictions for every row of ``df``, in order, with a fresh 0..n-1 index.

    Columns: ``predict``, one ``p_<class>`` per class (classification), with ``contributions``
    the ``contribution_columns`` (to ``p_<classes_[1]>`` for binary, to the predicted class's
    ``p_`` for multiclass, to ``predict`` for regression; they and the bias add up to it), then
    the input columns chosen by ``include_columns`` (all of them by default; see
    ``included_columns`` for renames). Raises ``PredictInputError`` for missing columns,
    unknown ``include_columns`` or text in a column the model reads as numeric. Rows are
    predicted ``chunk_rows`` at a time.
    """
    return pd.concat(
        predict_chunks(
            model, df, include_columns, chunk_rows=chunk_rows, contributions=contributions
        ),
        ignore_index=True,
    )
