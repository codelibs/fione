"""Greedy ensemble selection over out-of-fold predictions (Caruana et al., 2004)."""

import math
from collections.abc import Callable
from functools import partial

import numpy as np

from fione.engine.prep import Task
from fione.engine.search import score


def caruana(
    oof: dict[str, np.ndarray],
    y: np.ndarray,
    task: Task,
    rounds: int = 30,
    metric: Callable[[np.ndarray, np.ndarray], float] | None = None,
) -> dict[str, float]:
    """Ensemble weights for the candidates in ``oof``, summing to 1, keyed in ``oof`` order.

    Each round adds, with replacement, the candidate that gives the averaged predictions the
    lowest ``metric(y, pred)`` (default: log loss or RMSE); ties go to the earlier candidate.
    The best ensemble of all rounds is returned. The first round picks the best single
    candidate, so the result is never worse than it, and is that candidate alone (weight 1)
    when no blend beats it.
    """
    metric = metric or partial(score, task)
    names = list(oof)
    total = np.zeros_like(oof[names[0]], dtype=float)
    counts = dict.fromkeys(names, 0)
    best_loss, best_counts = math.inf, counts
    for size in range(1, rounds + 1):
        losses = [metric(y, (total + oof[name]) / size) for name in names]
        pick = int(np.argmin(losses))  # the first of equal losses
        total += oof[names[pick]]
        counts[names[pick]] += 1
        if losses[pick] < best_loss:
            best_loss, best_counts = losses[pick], dict(counts)
    picked = sum(best_counts.values())
    return {name: best_counts[name] / picked for name in names}
