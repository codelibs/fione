"""Job handler registry. A handler runs inside the worker process and gets a ``JobContext``."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

from fione.config import Settings
from fione.engine.events import EventSink
from fione.jobs.store import Job
from fione.storage import Storage


@dataclass(frozen=True)
class JobContext:
    conn: sqlite3.Connection
    storage: Storage
    job: Job
    settings: Settings
    # Records progress; raises JobAbort (a BaseException) when it cannot.
    emit: EventSink
    # True once a cancel was requested; handlers check it between units of work.
    should_stop: Callable[[], bool]
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
