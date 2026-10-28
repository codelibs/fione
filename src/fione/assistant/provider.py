"""The LLM provider's status for the system page and the assistant.

``LlmMonitor`` keeps a ``LlmStatus`` up to date. For ``ollama`` it checks the server, finds out
whether the model is there and pulls it when it is not (``llm_auto_pull``, or an
administrator's request), in a daemon thread that ``stop`` ends. For ``openai`` there is
nothing to ask: the provider is ``ready`` and each turn reports its own failures.

A status never holds the base URL's path, the API key or text from the server: a failed pull
is the code ``pull_failed`` here, and its cleaned text is in the log.
"""

import ipaddress
import json
import logging
import re
import threading
from dataclasses import dataclass, replace
from typing import Literal
from urllib.parse import urlsplit

import httpx

from fione.assistant.store import normal_base_url
from fione.config import Settings
from fione.schema import clean_text

log = logging.getLogger("fione.assistant")

LlmState = Literal["off", "checking", "unreachable", "missing", "pulling", "ready", "error"]

OLLAMA_DEFAULT_CONTEXT = 4096  # what Ollama serves unless it is configured otherwise
READY_RECHECK_SECS = 300.0
CONNECT_TIMEOUT_SECS = 5.0
READ_TIMEOUT_SECS = 10.0
MAX_BODY_BYTES = 4 * 2**20  # of /api/tags and /api/ps
MAX_PULL_LINE_BYTES = 64 * 1024  # a progress line is about 200 bytes
_BAD_ANSWER = (ValueError, RecursionError)  # JSON that is not JSON, too deep, or of the wrong shape
PULL_READ_TIMEOUT_SECS = 120.0  # a pull reports progress much more often than this
_SINGLE_LABEL = re.compile(r"[a-z][a-z0-9_-]*")  # not a number in disguise (3232235781, 0xc0...)


@dataclass(frozen=True)
class LlmStatus:
    state: LlmState
    model: str | None
    local: bool
    host: str | None
    completed: int | None
    total: int | None
    error_code: str | None
    server_context: int | None


def is_local_url(url: str) -> bool:
    """Whether ``url`` names this machine or a service next to Fione: ``localhost``,
    ``*.localhost``, a loopback address, ``host.docker.internal`` or a single-label name (a
    Compose service). Anything else, private address ranges included, may leave the server's
    network, so it is not local."""
    try:
        host = (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    if not host:
        return False
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    return (
        host == "localhost"
        or host.endswith(".localhost")
        or host == "host.docker.internal"
        or _SINGLE_LABEL.fullmatch(host) is not None
    )


def native_root(base_url: str) -> str:
    """``base_url`` without its final ``/v1``: where Ollama's own API lives."""
    root = base_url.rstrip("/")
    return root.removesuffix("/v1")


def _is_count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _lines(response: httpx.Response):
    """The lines of a streamed answer, none longer than ``MAX_PULL_LINE_BYTES`` (``ValueError``)."""
    buffer = b""
    for data in response.iter_bytes():
        *lines, buffer = (buffer + data).split(b"\n")
        if len(buffer) > MAX_PULL_LINE_BYTES or any(
            len(line) > MAX_PULL_LINE_BYTES for line in lines
        ):
            raise ValueError("a line of the answer is too long")
        yield from (line.decode("utf-8", "replace") for line in lines)
    if buffer:
        yield buffer.decode("utf-8", "replace")


def _host(base_url: str) -> str:
    return urlsplit(normal_base_url(base_url)).netloc


class LlmMonitor:
    def __init__(
        self,
        settings: Settings,
        *,
        http: httpx.Client | None = None,
        recheck_secs: float = 30.0,
    ):
        self._settings = settings
        self._recheck_secs = recheck_secs
        self._http = http or httpx.Client()
        self._owns_http = http is None
        self._model = settings.llm_model
        configured = settings.llm_base_url is not None
        self._ollama = configured and settings.llm_provider == "ollama"
        self._root = native_root(settings.llm_base_url) if self._ollama else None
        self._headers = {}
        if settings.llm_api_key is not None:
            self._headers = {"Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}"}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pulling = False
        self._pull_blocked = False  # a pull failed: only an administrator starts the next
        self._status = LlmStatus(
            state="off" if not configured else ("checking" if self._ollama else "ready"),
            model=settings.llm_model if configured else None,
            local=configured and is_local_url(settings.llm_base_url),
            host=_host(settings.llm_base_url) if configured else None,
            completed=None,
            total=None,
            error_code=None,
            server_context=None,
        )

    # --- what others ask

    def snapshot(self) -> LlmStatus:
        with self._lock:
            return self._status

    def effective_context(self) -> int:
        """The tokens a request may use: the setting, and for Ollama no more than the context
        its loaded model has (``OLLAMA_DEFAULT_CONTEXT`` until that is known)."""
        limit = self._settings.llm_context_tokens
        if not self._ollama:
            return limit
        known = self.snapshot().server_context
        return min(limit, OLLAMA_DEFAULT_CONTEXT if known is None else known)

    def refresh_context(self) -> None:
        """Read the loaded model's context from ``/api/ps``; any failure, or an answer that
        does not make sense, keeps the old value."""
        if not self._ollama:
            return
        try:
            entries = self._get_models("/api/ps")
        except (httpx.HTTPError, RuntimeError, *_BAD_ANSWER):
            return
        for entry in entries:
            if isinstance(entry, dict) and self._is_model(entry.get("name"), entry.get("model")):
                context = entry.get("context_length")
                if _is_count(context) and context > 0:
                    self._update(server_context=context)
                    return

    def pull_now(self) -> bool:
        """Start pulling the model in the background; false when a pull is already running
        or the provider is not Ollama."""
        if not self._ollama or not self._begin_pull(forced=True):
            return False
        threading.Thread(target=self._pull, name="llm-pull", daemon=True).start()
        return True

    # --- the thread

    def start(self) -> None:
        if self._ollama and self._thread is None:
            self._thread = threading.Thread(target=self._run, name="llm-monitor", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """End the thread (a pull in progress stops at its next line)."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        if self._owns_http:
            self._http.close()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                wait = self._check()
            except Exception:  # the thread must outlive anything a server can say
                if not self._stop.is_set():
                    log.exception("checking the LLM server (%s) failed", self._status.host)
                self._update_idle(state="error", error_code="probe_failed")
                wait = self._recheck_secs
            self._stop.wait(wait)

    def _check(self) -> float:
        """One look at the server; the seconds until the next."""
        try:
            present = self._model_present()
        except httpx.TransportError:
            self._update_idle(state="unreachable", error_code=None, completed=None, total=None)
            return self._recheck_secs
        except (httpx.HTTPError, *_BAD_ANSWER):
            log.warning("the LLM server (%s) could not be queried", self._status.host)
            self._update_idle(state="error", error_code="probe_failed")
            return self._recheck_secs
        if present:
            with self._lock:
                self._pull_blocked = False  # the model is there, however it got there
            self._update_idle(state="ready", error_code=None, completed=None, total=None)
            self.refresh_context()
            return READY_RECHECK_SECS
        with self._lock:
            if self._pull_blocked:  # stays until the administrator asks again
                self._set_idle(state="error", error_code="pull_failed")
                return self._recheck_secs
            self._set_idle(state="missing", error_code=None, completed=None, total=None)
            pulling = self._pulling
        if not pulling and self._settings.llm_auto_pull and self._begin_pull(forced=False):
            self._pull()
        return self._recheck_secs

    def _is_model(self, *names) -> bool:
        wanted = {self._model}
        if ":" not in self._model:
            wanted.add(f"{self._model}:latest")
        return any(isinstance(n, str) and n in wanted for n in names)

    def _model_present(self) -> bool:
        return any(
            isinstance(m, dict) and self._is_model(m.get("name"), m.get("model"))
            for m in self._get_models("/api/tags")
        )

    def _get_models(self, path: str) -> list:
        """The ``models`` list of an Ollama answer. ``ValueError`` for a body that is too
        large, is not JSON or does not have that shape."""
        data = b""
        with self._http.stream(
            "GET", f"{self._root}{path}", headers=self._headers, timeout=self._timeout()
        ) as response:
            response.raise_for_status()
            for part in response.iter_bytes():
                data += part
                if len(data) > MAX_BODY_BYTES:
                    raise ValueError("the answer is too large")
        body = json.loads(data)
        models = body.get("models") if isinstance(body, dict) else None
        if not isinstance(models, list):
            raise ValueError("the answer has an unexpected shape")
        return models

    @staticmethod
    def _timeout(read: float = READ_TIMEOUT_SECS) -> httpx.Timeout:
        return httpx.Timeout(read, connect=CONNECT_TIMEOUT_SECS)

    # --- pulling

    def _begin_pull(self, *, forced: bool) -> bool:
        """Claim the single pull slot; false when a pull is running."""
        with self._lock:
            if self._pulling:
                return False
            self._pulling = True
            if forced:
                self._pull_blocked = False
            self._status = replace(
                self._status, state="pulling", completed=None, total=None, error_code=None
            )
            return True

    def _pull(self) -> None:
        """Pull the model, reading the progress; the caller holds the pull slot."""
        outcome = "failed"
        try:
            with self._http.stream(
                "POST",
                f"{self._root}/api/pull",
                json={"model": self._model, "stream": True},
                headers=self._headers,
                timeout=self._timeout(PULL_READ_TIMEOUT_SECS),
            ) as response:
                response.raise_for_status()
                outcome = "done"
                for line in _lines(response):
                    if self._stop.is_set():
                        outcome = "stopped"
                        break
                    if self._pull_line(line) == "failed":
                        outcome = "failed"
                        break
        except httpx.TransportError:
            outcome = "stopped" if self._stop.is_set() else "unreachable"
        except (httpx.HTTPError, *_BAD_ANSWER):
            outcome = "failed"
            log.warning("pulling the LLM model from %s failed", self._status.host)
        except Exception:
            outcome = "failed"
            if not self._stop.is_set():  # a shutdown closes the client under the pull
                log.exception("pulling the LLM model from %s failed", self._status.host)
        with self._lock:
            self._pulling = False
            self._pull_blocked = outcome == "failed"
        if outcome == "failed":
            self._update(state="error", error_code="pull_failed")
        elif outcome == "unreachable":
            self._update(state="unreachable", error_code=None, completed=None, total=None)
        elif outcome == "done":
            self._after_pull()

    def _after_pull(self) -> None:
        try:
            present = self._model_present()
        except (httpx.HTTPError, RuntimeError, *_BAD_ANSWER):
            return  # the next check finds out
        if present:
            self._update(state="ready", error_code=None, completed=None, total=None)
            self.refresh_context()
        else:
            self._update(state="missing", completed=None, total=None)

    def _pull_line(self, line: str) -> str | None:
        """Take one NDJSON line of a pull; ``"failed"`` for an error line."""
        if not line.strip():
            return None
        entry = json.loads(line)
        if not isinstance(entry, dict):
            return None
        if entry.get("error"):
            log.warning(
                "pulling the LLM model from %s failed: %s",
                self._status.host,
                clean_text(entry["error"], 200),
            )
            return "failed"
        total, completed = entry.get("total"), entry.get("completed")
        if _is_count(total) and _is_count(completed) and total > 0:
            self._update(completed=completed, total=total)
        return None

    def _update(self, **changes) -> None:
        with self._lock:
            self._status = replace(self._status, **changes)

    def _update_idle(self, **changes) -> None:
        """``_update``, unless a pull is running: it owns the state until it ends."""
        with self._lock:
            self._set_idle(**changes)

    def _set_idle(self, **changes) -> None:
        if not self._pulling:  # the caller holds the lock
            self._status = replace(self._status, **changes)
