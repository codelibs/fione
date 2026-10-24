"""Structured progress events, read by the job layer and the LLM assistant (spec 5.6).

Event data must stay JSON-serializable: builtin numbers and strings, no NaN or infinity.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

EventType = Literal["started", "trial", "family_done", "ensemble", "stopped", "finished"]


@dataclass(frozen=True)
class Event:
    type: EventType
    # Unix time, for display; deadlines use the monotonic clock.
    ts: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)


EventSink = Callable[[Event], None]
