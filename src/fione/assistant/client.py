"""A client for OpenAI-compatible ``/chat/completions`` servers (OpenAI, Ollama's ``/v1``, vLLM,
llama.cpp), over httpx.

The answer is a ``Completion``. Only the structured ``tool_calls`` field makes a ``ToolCall``:
text, JSON inside the text and the reasoning fields (``reasoning_content``, ``reasoning``,
``thinking``, ``<think>`` spans) are never read as calls, and the last two are dropped.
"""

import json
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Literal

import httpx

from fione.config import Settings
from fione.schema import clean_text

CONNECT_TIMEOUT_SECS = 5.0
MAX_READ_TIMEOUT_SECS = 120.0
MAX_MESSAGE_CHARS = 200
MAX_ERROR_BODY_BYTES = 4096
MAX_RESPONSE_BYTES = 16 * 2**20
MAX_LINE_BYTES = 2**20  # of a line that has not ended yet

ErrorCode = Literal["unreachable", "timeout", "http", "protocol", "cancelled"]


class LlmError(Exception):
    """A failed completion. The message is short, safe to show, and free of the API key."""

    def __init__(self, code: ErrorCode, message: str, status: int | None = None):
        super().__init__(clean_text(message, MAX_MESSAGE_CHARS))
        self.code = code
        self.status = status


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # the raw JSON text, validated by whoever runs the tool


@dataclass
class Completion:
    content: str
    tool_calls: list[ToolCall]
    finish_reason: str | None
    prompt_tokens: int | None  # from the final usage chunk, when the server sends one


class _ThinkFilter:
    """Drops ``<think>…</think>`` spans from streamed text, even when a tag is split across
    pieces. The text of a span that never closes is dropped too.

    Some chat templates open the span in the prompt, so the text starts with the reasoning and
    a lone ``</think>``. While no tag has been seen, that tag sets ``restart``: what came
    before it was reasoning, and the caller drops what it kept (what it already showed stays)."""

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self._pending = ""
        self._inside = False
        self._tagged = False  # a tag has been seen
        self.restart = False

    def feed(self, piece: str) -> str:
        self._pending += piece
        out = []
        while True:
            tag = self.CLOSE if self._inside else self.OPEN
            at = self._pending.find(tag)
            if not self._inside and not self._tagged:
                lone = self._pending.find(self.CLOSE)
                if lone >= 0 and (at < 0 or lone < at):
                    self._pending = self._pending[lone + len(self.CLOSE) :]
                    out.clear()
                    self._tagged = self.restart = True
                    continue
            if at >= 0:
                if not self._inside:
                    out.append(self._pending[:at])
                self._pending = self._pending[at + len(tag) :]
                self._inside = not self._inside
                self._tagged = True
                continue
            keep = _partial_tag_length(self._pending, tag)
            if not self._inside and not self._tagged:
                keep = max(keep, _partial_tag_length(self._pending, self.CLOSE))
            if not self._inside:
                out.append(self._pending[: len(self._pending) - keep])
            self._pending = self._pending[len(self._pending) - keep :]
            return "".join(out)

    def flush(self) -> str:
        rest, self._pending = ("" if self._inside else self._pending), ""
        return rest


def _partial_tag_length(text: str, tag: str) -> int:
    """How much of the end of ``text`` may be the start of ``tag``."""
    for n in range(min(len(tag) - 1, len(text)), 0, -1):
        if tag.startswith(text[-n:]):
            return n
    return 0


class _Reply:
    """What the chunks of one completion add up to."""

    def __init__(self, on_text: Callable[[str], None] | None):
        self._on_text = on_text
        self._think = _ThinkFilter()
        self._text: list[str] = []
        self._calls: list[dict] = []  # in the order they began
        self._filling: dict[int, dict] = {}  # the call each ``index`` is adding to
        self.finish_reason: str | None = None
        self.prompt_tokens: int | None = None

    def add_chunk(self, chunk) -> None:
        if not isinstance(chunk, dict):
            raise LlmError("protocol", "the server sent an unexpected chunk")
        if chunk.get("error"):
            raise LlmError("protocol", f"the server reported an error: {_error_text(chunk)}")
        usage = chunk.get("usage")
        if isinstance(usage, dict) and isinstance(usage.get("prompt_tokens"), int):
            self.prompt_tokens = usage["prompt_tokens"]
        choices = chunk.get("choices") or []
        if not isinstance(choices, list) or not all(isinstance(c, dict) for c in choices):
            raise LlmError("protocol", "the server sent malformed choices")
        # Only the first choice is read: with ``n`` above 1 the others are interleaved.
        choice = next((c for c in choices if c.get("index", 0) == 0), None)
        if choice is not None:
            self.add_delta(choice.get("delta") or choice.get("message") or {})
            if isinstance(choice.get("finish_reason"), str):
                self.finish_reason = choice["finish_reason"]

    def add_delta(self, delta) -> None:
        if not isinstance(delta, dict):
            raise LlmError("protocol", "the server sent a malformed message")
        if isinstance(delta.get("content"), str):
            visible = self._think.feed(delta["content"])
            if self._think.restart:  # the reasoning before a lone </think> is not content
                self._text.clear()
                self._think.restart = False
            self._add_text(visible)
        calls = delta.get("tool_calls") or []
        if not isinstance(calls, list):
            raise LlmError("protocol", "the server sent malformed tool calls")
        for position, call in enumerate(calls):
            function = call.get("function") or {} if isinstance(call, dict) else None
            if not isinstance(function, dict):
                raise LlmError("protocol", "the server sent a malformed tool call")
            index = call.get("index") if isinstance(call.get("index"), int) else position
            id_ = call["id"] if isinstance(call.get("id"), str) else ""
            name = function["name"] if isinstance(function.get("name"), str) else ""
            entry = self._filling.get(index)
            if entry is None or self._begins_new_call(entry, id_, name):
                entry = self._filling[index] = {"id": "", "name": "", "arguments": ""}
                self._calls.append(entry)
            entry["id"] = entry["id"] or id_
            entry["name"] = entry["name"] or name
            arguments = function.get("arguments")
            if isinstance(arguments, dict):
                arguments = json.dumps(arguments)
            if isinstance(arguments, str):
                entry["arguments"] += arguments

    @staticmethod
    def _begins_new_call(entry: dict, id_: str, name: str) -> bool:
        """Whether a delta for the ``index`` of ``entry`` starts another call. Servers that
        send each call whole may reuse an index. The ids differ then; without ids, a name
        arriving after complete arguments, or a different name, is a new call (a name repeated
        in a fragment of the same call is the same name, with partial arguments)."""
        if id_ and entry["id"]:
            return id_ != entry["id"]
        if name and entry["name"] and name != entry["name"]:
            return True
        if name and entry["name"] and entry["arguments"]:
            try:
                return isinstance(json.loads(entry["arguments"]), dict)
            except (ValueError, RecursionError):
                return False
        return False

    def _add_text(self, text: str) -> None:
        if text:
            self._text.append(text)
            if self._on_text is not None:
                self._on_text(text)

    def done(self) -> Completion:
        self._add_text(self._think.flush())
        calls = []
        for n, entry in enumerate(self._calls):
            if not entry["name"]:
                raise LlmError("protocol", "the server sent a tool call without a name")
            calls.append(ToolCall(entry["id"] or f"call_{n}", entry["name"], entry["arguments"]))
        return Completion("".join(self._text), calls, self.finish_reason, self.prompt_tokens)


def _error_text(value) -> str:
    """The message of an error body or chunk: ``{"error": {"message": …}}``, ``{"error": …}``."""
    error = value.get("error") if isinstance(value, dict) else None
    if isinstance(error, dict):
        error = error.get("message")
    return error if isinstance(error, str) else ""


def _body(response: httpx.Response, check: Callable[[], None]) -> Iterator[bytes]:
    """The body of a response as it arrives, bounded in total size; ``check`` runs for every
    block received (it raises to stop)."""
    total = 0
    for data in response.iter_bytes():
        check()
        total += len(data)
        if total > MAX_RESPONSE_BYTES:
            raise LlmError("protocol", "the response is too large")
        yield data


def _lines(response: httpx.Response, check: Callable[[], None]) -> Iterator[bytes]:
    buffer = b""
    for data in _body(response, check):
        *lines, buffer = (buffer + data).split(b"\n")
        if len(buffer) > MAX_LINE_BYTES:
            raise LlmError("protocol", "the server sent a line that is too long")
        yield from lines
    if buffer:
        yield buffer


def _loads(data: bytes):
    try:
        return json.loads(data)
    except (ValueError, RecursionError):
        raise LlmError("protocol", "the server sent data that is not JSON") from None


class ChatClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key: str | None = None,
        extra_body: dict | None = None,
        max_tokens: int = 1024,
        http: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key
        self._extra_body = dict(extra_body or {})
        self._max_tokens = max_tokens
        self._http = http or httpx.Client()
        self._owns_http = http is None

    def close(self) -> None:
        """Close the HTTP client, if this one made it."""
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "ChatClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @classmethod
    def from_settings(cls, settings: Settings) -> "ChatClient | None":
        if settings.llm_base_url is None:
            return None
        key = settings.llm_api_key
        return cls(
            settings.llm_base_url,
            settings.llm_model,
            api_key=key.get_secret_value() if key else None,
            extra_body=settings.llm_extra_body,
            max_tokens=settings.llm_max_tokens,
        )

    def complete(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        deadline: float,
        on_text: Callable[[str], None] | None = None,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> Completion:
        """One completion, streamed. ``deadline`` is a ``time.monotonic()`` value; ``on_text``
        gets the visible text as it arrives. ``cancelled`` is asked for every block received.

        Only ``LlmError`` comes out. The deadline is not a hard bound:
        - Once the body arrives it is checked for every block, and a trickle ends at the next
          block. A body that stalls ends at the read timeout, which is fixed when the request
          starts: up to the time that was left then (at most 120 s) past the deadline, and
          ``cancelled`` is not asked meanwhile.
        - Before the body, while the connection and the response headers are read, nothing
          checks it. A server that sends the headers slowly, a byte at a time, or sends nothing,
          is bounded only by httpx's own timeouts (5 s to connect, then each read), and the
          trickle by nothing but the size of the headers.
        So the caller must not rely on this call to return at the deadline: it owns the overall
        limit of a turn and has to abandon the worker thread at that limit.

        The lone ``</think>`` of a template that opens the span in the prompt drops the
        reasoning before it from ``content``, but ``on_text`` has shown it by then."""
        body = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "max_tokens": self._max_tokens,
            **self._extra_body,
        }
        if tools:
            body["tools"] = tools
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        self._check(deadline, cancelled)
        remaining = deadline - time.monotonic()
        timeout = httpx.Timeout(
            min(remaining, MAX_READ_TIMEOUT_SECS), connect=min(remaining, CONNECT_TIMEOUT_SECS)
        )

        def check() -> None:
            self._check(deadline, cancelled)

        reply = _Reply(on_text)
        try:
            with self._http.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=body,
                headers=headers,
                timeout=timeout,
            ) as response:
                if not response.is_success:
                    raise self._http_error(response, check)
                content_type = response.headers.get("content-type", "")
                if "json" in content_type and "event-stream" not in content_type:
                    self._read_json(response, reply, check)
                else:
                    self._read_stream(response, reply, check)
        except httpx.ConnectTimeout:
            raise LlmError("unreachable", "cannot connect to the LLM server") from None
        except httpx.TimeoutException:
            raise LlmError("timeout", "the LLM server did not answer in time") from None
        except httpx.RemoteProtocolError:
            raise LlmError("protocol", "the LLM server sent an invalid response") from None
        except httpx.TransportError:
            raise LlmError("unreachable", "cannot reach the LLM server") from None
        except httpx.HTTPError:  # a body that cannot be decoded
            raise LlmError("protocol", "the LLM server sent an invalid response") from None
        except httpx.InvalidURL:
            raise LlmError("unreachable", "the LLM server's address is not valid") from None
        return reply.done()

    @staticmethod
    def _check(deadline: float, cancelled: Callable[[], bool]) -> None:
        if cancelled():
            raise LlmError("cancelled", "the request was cancelled")
        if time.monotonic() >= deadline:
            raise LlmError("timeout", "the LLM server did not answer in time")

    def _read_stream(self, response, reply: _Reply, check: Callable[[], None]) -> None:
        for line in _lines(response, check):
            check()
            if not line.startswith(b"data:"):
                continue  # comments and other SSE fields
            data = line[5:].strip()
            if data == b"[DONE]":
                return
            self._guard(reply.add_chunk, _loads(data))
        if reply.finish_reason is None:
            raise LlmError("protocol", "the stream ended before the reply was complete")

    def _read_json(self, response, reply: _Reply, check: Callable[[], None]) -> None:
        self._guard(reply.add_chunk, _loads(b"".join(_body(response, check))))

    def _guard(self, add, chunk) -> None:
        """``add(chunk)`` with the API key taken out of any error message."""
        try:
            add(chunk)
        except LlmError as e:
            raise self._error(e.code, str(e), e.status) from None

    def _http_error(self, response: httpx.Response, check: Callable[[], None]) -> LlmError:
        data = b""
        try:
            for part in _body(response, check):
                data += part
                if len(data) >= MAX_ERROR_BODY_BYTES:
                    break
        except (httpx.HTTPError, LlmError):
            pass  # the status alone is what we report
        text = data[:MAX_ERROR_BODY_BYTES].decode("utf-8", "replace")
        try:
            text = _error_text(json.loads(text)) or text
        except (ValueError, RecursionError):
            pass
        return self._error("http", f"HTTP {response.status_code}: {text}", response.status_code)

    def _error(self, code: ErrorCode, message: str, status: int | None = None) -> LlmError:
        if self._api_key:
            message = message.replace(self._api_key, "***")
        return LlmError(code, message, status)
