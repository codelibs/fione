"""Job handler registry. A handler runs inside the worker process and gets a ``JobContext``."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from fione.config import Settings
from fione.engine.events import EventSink
from fione.jobs.store import Job
from fione.storage import Storage


class JobUserError(Exception):
    """A problem with the user's input; the message is stored on the job as it is."""


class StopCheck(Protocol):
    def __call__(self, *, force: bool = False) -> bool:
        """True once the job should stop. Reads are cached for 0.5 s unless ``force``."""


@dataclass(frozen=True)
class JobContext:
    conn: sqlite3.Connection
    storage: Storage
    job: Job
    settings: Settings
    # Records progress; raises JobAbort (a BaseException) when it cannot.
    emit: EventSink
    # True once a cancel was requested; handlers check it between units of work.
    should_stop: StopCheck
    # The JSON-serializable result stored on the job when the handler returns.
    set_result: Callable[[dict], None]


Handler = Callable[[JobContext], None]

HANDLERS: dict[str, Handler] = {}


def register_handler(kind: str) -> Callable[[Handler], Handler]:
    def register(handler: Handler) -> Handler:
        if kind in HANDLERS:
            raise ValueError(f"job kind already registered: {kind}")
        HANDLERS[kind] = handler
        return handler

    return register
