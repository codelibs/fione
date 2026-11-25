"""Tiny trained models for the batch prediction tests, fitted once per session."""

from functools import cache

import numpy as np
import pandas as pd

from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.engine.model import TrainedModel

LABELS = ["良", "悪", "普通"]
COLORS = ["red", "green", "blue"]


def training_frame(n: int = 300, seed: int = 0) -> pd.DataFrame:
    """Numeric and categorical features with Japanese names; ``判定`` and ``value`` as targets."""
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    width = rng.normal(size=n)
    color = rng.choice(COLORS, n)
    score = x + (color == "red") - width
    return pd.DataFrame(
        {
            "x": x,
            "幅": width,
            "color": color,
            "判定": np.select([score < -0.5, score > 0.5], [LABELS[1], LABELS[0]], LABELS[2]),
            "value": score + rng.normal(scale=0.1, size=n),
        }
    )


def _fit(target: str, drop: str, frame: pd.DataFrame | None = None) -> TrainedModel:
    config = TrainConfig(target=target, max_runtime_secs=10, max_models=2, nfolds=3)
    frame = training_frame() if frame is None else frame
    return AutoML(config, lambda event: None).fit(frame.drop(columns=[drop]))


@cache
def classifier() -> TrainedModel:
    return _fit("判定", "value")


@cache
def binary() -> TrainedModel:
    """``判定`` as ``yes`` (``良``) or ``no``."""
    frame = training_frame()
    frame["判定"] = np.where(frame["判定"] == LABELS[0], "yes", "no")
    return _fit("判定", "value", frame)


@cache
def regressor() -> TrainedModel:
    return _fit("value", "判定")


@cache
def thousands_text_regressor() -> TrainedModel:
    """``color`` as text of numbers with thousands separators, as an older upload kept it."""
    frame = training_frame()
    frame["color"] = frame["color"].map(
        dict(zip(COLORS, ["1,200", "2,500", "13,000"], strict=True))
    )
    return _fit("value", "判定", frame)


@cache
def padded_text_regressor() -> TrainedModel:
    """``color`` as text: numbers with blanks around them and a missing marker with blanks."""
    frame = training_frame()
    frame["color"] = frame["color"].map(dict(zip(COLORS, [" 12", " NA", "7"], strict=True)))
    return _fit("value", "判定", frame)


def features(n: int = 20, seed: int = 1) -> pd.DataFrame:
    return training_frame(n, seed).drop(columns=["判定", "value"])
