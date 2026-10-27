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
    pieces. The text of a span that never closes is dropped too."""

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self._pending = ""
        self._inside = False

    def feed(self, piece: str) -> str:
        self._pending += piece
        out = []
        while True:
            tag = self.CLOSE if self._inside else self.OPEN
            at = self._pending.find(tag)
            if at >= 0:
                if not self._inside:
                    out.append(self._pending[:at])
                self._pending = self._pending[at + len(tag) :]
                self._inside = not self._inside
                continue
            keep = _partial_tag_length(self._pending, tag)
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
        self._calls: dict[int, dict] = {}
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
        if choices:
            choice = choices[0]
            self.add_delta(choice.get("delta") or choice.get("message") or {})
            self.finish_reason = choice.get("finish_reason") or self.finish_reason

    def add_delta(self, delta) -> None:
        if not isinstance(delta, dict):
            raise LlmError("protocol", "the server sent a malformed message")
        if isinstance(delta.get("content"), str):
            self._add_text(self._think.feed(delta["content"]))
        calls = delta.get("tool_calls") or []
        if not isinstance(calls, list):
            raise LlmError("protocol", "the server sent malformed tool calls")
        for position, call in enumerate(calls):
            if not isinstance(call, dict):
                raise LlmError("protocol", "the server sent a malformed tool call")
            index = call.get("index") if isinstance(call.get("index"), int) else position
            entry = self._calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
            function = call.get("function") or {}
            if not isinstance(function, dict):
                raise LlmError("protocol", "the server sent a malformed tool call")
            if isinstance(call.get("id"), str):
                entry["id"] = entry["id"] or call["id"]
            if isinstance(function.get("name"), str):
                entry["name"] = entry["name"] or function["name"]
            arguments = function.get("arguments")
            if isinstance(arguments, dict):
                arguments = json.dumps(arguments)
            if isinstance(arguments, str):
                entry["arguments"] += arguments

    def _add_text(self, text: str) -> None:
        if text:
            self._text.append(text)
            if self._on_text is not None:
                self._on_text(text)

    def done(self) -> Completion:
        self._add_text(self._think.flush())
        calls = []
        for index, entry in sorted(self._calls.items()):
            if not entry["name"]:
                raise LlmError("protocol", "the server sent a tool call without a name")
            calls.append(
                ToolCall(entry["id"] or f"call_{index}", entry["name"], entry["arguments"])
            )
        return Completion("".join(self._text), calls, self.finish_reason, self.prompt_tokens)


def _error_text(value) -> str:
    """The message of an error body or chunk: ``{"error": {"message": …}}``, ``{"error": …}``."""
    error = value.get("error") if isinstance(value, dict) else None
    if isinstance(error, dict):
        error = error.get("message")
    return error if isinstance(error, str) else ""


def _body(response: httpx.Response) -> Iterator[bytes]:
    """The body of a response as it arrives, bounded in total size."""
    total = 0
    for data in response.iter_bytes():
        total += len(data)
        if total > MAX_RESPONSE_BYTES:
            raise LlmError("protocol", "the response is too large")
        yield data


def _lines(response: httpx.Response) -> Iterator[bytes]:
    buffer = b""
    for data in _body(response):
        *lines, buffer = (buffer + data).split(b"\n")
        yield from lines
    if buffer:
        yield buffer


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
        gets the visible text as it arrives. ``cancelled`` is asked for every chunk."""
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
                    raise self._http_error(response)
                content_type = response.headers.get("content-type", "")
                if "json" in content_type and "event-stream" not in content_type:
                    self._read_json(response, reply, deadline, cancelled)
                else:
                    self._read_stream(response, reply, deadline, cancelled)
        except httpx.ConnectTimeout:
            raise LlmError("unreachable", "cannot connect to the LLM server") from None
        except httpx.TimeoutException:
            raise LlmError("timeout", "the LLM server did not answer in time") from None
        except httpx.RemoteProtocolError:
            raise LlmError("protocol", "the LLM server sent an invalid response") from None
        except httpx.TransportError:
            raise LlmError("unreachable", "cannot reach the LLM server") from None
        return reply.done()

    @staticmethod
    def _check(deadline: float, cancelled: Callable[[], bool]) -> None:
        if cancelled():
            raise LlmError("cancelled", "the request was cancelled")
        if time.monotonic() >= deadline:
            raise LlmError("timeout", "the LLM server did not answer in time")

    def _read_stream(self, response, reply: _Reply, deadline, cancelled) -> None:
        for line in _lines(response):
            self._check(deadline, cancelled)
            if not line.startswith(b"data:"):
                continue  # comments and other SSE fields
            data = line[5:].strip()
            if data == b"[DONE]":
                return
            try:
                chunk = json.loads(data)
            except ValueError:
                raise LlmError("protocol", "the server sent a chunk that is not JSON") from None
            self._guard(reply.add_chunk, chunk)
        if reply.finish_reason is None:
            raise LlmError("protocol", "the stream ended before the reply was complete")

    def _read_json(self, response, reply: _Reply, deadline, cancelled) -> None:
        data = b"".join(_body(response))
        self._check(deadline, cancelled)
        try:
            chunk = json.loads(data)
        except ValueError:
            raise LlmError("protocol", "the server sent a body that is not JSON") from None
        self._guard(reply.add_chunk, chunk)

    def _guard(self, add, chunk) -> None:
        """``add(chunk)`` with the API key taken out of any error message."""
        try:
            add(chunk)
        except LlmError as e:
            raise self._error(e.code, str(e), e.status) from None

    def _http_error(self, response: httpx.Response) -> LlmError:
        data = b""
        try:
            for part in response.iter_bytes():
                data += part
                if len(data) >= MAX_ERROR_BODY_BYTES:
                    break
        except httpx.HTTPError:
            pass  # the status alone is what we report
        text = data[:MAX_ERROR_BODY_BYTES].decode("utf-8", "replace")
        try:
            text = _error_text(json.loads(text)) or text
        except ValueError:
            pass
        return self._error("http", f"HTTP {response.status_code}: {text}", response.status_code)

    def _error(self, code: ErrorCode, message: str, status: int | None = None) -> LlmError:
        if self._api_key:
            message = message.replace(self._api_key, "***")
        return LlmError(code, message, status)
