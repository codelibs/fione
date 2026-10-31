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


def _fit(target: str, drop: str) -> TrainedModel:
    config = TrainConfig(target=target, max_runtime_secs=10, max_models=2, nfolds=3)
    return AutoML(config, lambda event: None).fit(training_frame().drop(columns=[drop]))


@cache
def classifier() -> TrainedModel:
    return _fit("判定", "value")


@cache
def regressor() -> TrainedModel:
    return _fit("value", "判定")


def features(n: int = 20, seed: int = 1) -> pd.DataFrame:
    return training_frame(n, seed).drop(columns=["判定", "value"])
