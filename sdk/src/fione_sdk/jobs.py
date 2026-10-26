import contextlib
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import httpx

from fione_sdk.errors import FioneError, JobFailed

if TYPE_CHECKING:
    from fione_sdk.client import Client

TERMINAL = frozenset({"done", "failed", "cancelled"})
EVENT_PAGE = 500
EVENT_POLL = 1.0  # seconds between polls of a followed job that has nothing new

# The clock and the pause, as module attributes so that tests can replace them.
_monotonic = time.monotonic
_sleep = time.sleep


def _unexpected() -> FioneError:
    return FioneError(200, "http", "unexpected response")


class Job:
    """A job on the Fione server. ``data`` is the job as last fetched (``refresh`` fetches it
    again); ``status`` and ``result`` read from it. ``wait`` blocks until the job ends."""

    def __init__(self, client: "Client | None", data: dict):
        if not isinstance(data, dict) or "id" not in data or "status" not in data:
            raise _unexpected()
        self._client = client
        self.id: int = data["id"]
        self.data: dict = data

    def __repr__(self) -> str:
        return f"Job(id={self.id}, kind={self.data.get('kind')!r}, status={self.status!r})"

    def __reduce__(self):
        # A client holds the token and a connection: a pickled job keeps only its data.
        return (Job, (None, self.data))

    @property
    def status(self) -> str:
        return self.data["status"]

    @property
    def result(self) -> dict | None:
        return self.data.get("result")

    def _fetch(self, method: str, path: str) -> "Job":
        if self._client is None:
            raise FioneError(0, "config", "this job has no client (it was unpickled)")
        data = self._client._json(method, path)
        if not isinstance(data, dict) or data.get("id") != self.id or "status" not in data:
            raise _unexpected()
        self.data = data
        return self

    def refresh(self) -> "Job":
        return self._fetch("GET", f"/jobs/{self.id}")

    def cancel(self) -> "Job":
        """Cancel the job (a ``FioneError`` 409 if it has already finished)."""
        return self._fetch("POST", f"/jobs/{self.id}/cancel")

    def wait(
        self, timeout: float | None = None, poll: float = 1.0, max_poll: float = 10.0
    ) -> "Job":
        """Block until the job is done and return it. The polling interval starts at ``poll``
        seconds and doubles up to ``max_poll``. A job that failed or was cancelled raises
        ``JobFailed``; after ``timeout`` seconds ``TimeoutError`` is raised and the job keeps
        running. Interrupting the wait (Ctrl-C) cancels the job."""
        deadline = None if timeout is None else _monotonic() + timeout
        interval = poll
        try:
            while True:
                self.refresh()
                if self.status in TERMINAL:
                    break
                pause = interval
                if deadline is not None:
                    remaining = deadline - _monotonic()
                    if remaining <= 0:
                        raise TimeoutError(f"job {self.id} is still {self.status} after {timeout}s")
                    pause = min(pause, remaining)
                _sleep(pause)
                interval = min(interval * 2, max_poll)
        except KeyboardInterrupt:
            with contextlib.suppress(FioneError, httpx.HTTPError):
                self.cancel()
            raise
        if self.status != "done":
            raise JobFailed(self)
        return self

    def events(self, after: int = 0, *, follow: bool = False) -> Iterator[dict]:
        """The job's events after the event id ``after``, oldest first. With ``follow``, keep
        polling until the job has ended and no event is left."""
        if self._client is None:
            raise FioneError(0, "config", "this job has no client (it was unpickled)")
        while True:
            page: Any = self._client._json(
                "GET", f"/jobs/{self.id}/events", params={"after": after, "limit": EVENT_PAGE}
            )
            if (
                not isinstance(page, dict)
                or not isinstance(page.get("events"), list)
                or not isinstance(page.get("last_id"), int)
                or not isinstance(page.get("status"), str)
                or (page["events"] and page["last_id"] <= after)  # it would never advance
            ):
                raise _unexpected()
            yield from page["events"]
            after = page["last_id"]
            if page["events"]:
                continue
            if not follow or page["status"] in TERMINAL:
                return
            _sleep(EVENT_POLL)
