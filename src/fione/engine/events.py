"""Structured progress events, read by the job layer and the LLM assistant (spec 5.6).

Event data must stay JSON-serializable: builtin numbers and strings, no NaN or infinity
(``jsonable`` converts). Every ``notice`` carries a human-readable ``message``.
"""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

EventType = Literal[
    "started", "notice", "trial", "family_done", "ensemble", "stopped", "finished", "error"
]


@dataclass(frozen=True)
class Event:
    type: EventType
    # Unix time, for display; deadlines use the monotonic clock.
    ts: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)


EventSink = Callable[[Event], None]


def jsonable(value):
    """``value`` with numpy scalars as builtins and NaN/infinity as None, recursively."""
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [jsonable(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
