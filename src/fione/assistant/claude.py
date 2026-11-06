"""A client for the Anthropic Messages API (``POST {base}/v1/messages``), streamed.

It is given the OpenAI-shaped messages and tools the assistant builds and converts them: the
system messages become the top-level ``system``, an assistant's tool calls ``tool_use`` blocks,
the results that follow them ``tool_result`` blocks of one user message, and each tool's
``parameters`` its ``input_schema``. The thinking blocks of a reply with tool calls are kept in
memory, keyed by the calls' ids, and sent back unchanged with that assistant message while it is
in the current turn (after the last user message), as the API asks within a turn of tool use.
Earlier turns go without thinking, which the API allows, so that dropping old rounds does not
change what a sent thinking block was made after. The stored messages never hold them.

The tool definitions and the system prompt are the same on every round of a turn and across the
turns of a project: the system is sent as one text block with a cache breakpoint, which caches
the tools with it (they render first), and the request's top-level ``cache_control`` (automatic
caching) puts a second breakpoint on the conversation's last block as it grows.

Every request sets ``thinking.block_binding.prefix_mismatch_behavior`` to ``drop_block`` (beta
``thinking-binding-controls-2026-08-01``): when the request before a sent thinking block has
changed since the block was made (old rounds dropped, a tool result cut to fit), the API drops
that block and the ones after it instead of refusing the request.
"""

import json
import logging
import threading
from collections import OrderedDict
from collections.abc import Callable

import httpx

from fione.assistant.client import (
    Completion,
    HttpClient,
    LlmError,
    ToolCall,
    _error_text,
    _lines,
    _loads,
)

ANTHROPIC_VERSION = "2026-10-21"
ANTHROPIC_BETA = "thinking-binding-controls-2026-08-01"
THINKING = {"type": "adaptive", "block_binding": {"prefix_mismatch_behavior": "drop_block"}}
MAX_KEPT_REPLIES = 256  # replies whose thinking blocks are kept for the next request
STOP_REASONS = {"tool_use": "tool_calls", "end_turn": "stop", "max_tokens": "length"}
CACHE = {"type": "ephemeral"}
# The ``error.type`` of an error event in the stream -> its code; any other is ``protocol``.
STREAM_ERRORS = {"rate_limit_error": "rate_limited", "overloaded_error": "overloaded"}

log = logging.getLogger(__name__)


def claude_tools(tools: list[dict]) -> list[dict]:
    """OpenAI ``tools`` as Anthropic tools."""
    out = []
    for tool in tools:
        function = tool["function"]
        out.append(
            {
                "name": function["name"],
                "description": function.get("description", ""),
                "input_schema": function.get("parameters") or {"type": "object"},
            }
        )
    return out


def _input(arguments) -> dict:
    """A stored call's arguments as a ``tool_use`` input: a JSON object, or ``{}``."""
    try:
        value = json.loads(arguments or "{}")
    except (TypeError, ValueError, RecursionError):
        return {}
    return value if isinstance(value, dict) else {}


class _Reply:
    """What the events of one streamed message add up to; ``secret`` (the API key) is taken
    out of an error the server reports."""

    def __init__(self, on_text: Callable[[str], None] | None, secret: str | None = None):
        self._on_text = on_text
        self._secret = secret
        self._blocks: dict[int, dict] = {}  # by ``index``, as the API sent them
        self._json: dict[int, list[str]] = {}  # the ``partial_json`` of each tool_use block
        self.finish_reason: str | None = None
        self.prompt_tokens: int | None = None
        self.stopped = False
        self.transformations: list = []  # what the API changed in the request

    def add_event(self, event) -> None:
        if not isinstance(event, dict):
            raise LlmError("protocol", "the server sent an unexpected event")
        kind = event.get("type")
        if kind == "error":
            error = event.get("error")
            raise LlmError(
                STREAM_ERRORS.get(
                    error.get("type") if isinstance(error, dict) else None, "protocol"
                ),
                f"the server reported an error: {_error_text(event)}",
                secret=self._secret,
            )
        if kind == "message_start":
            message = event.get("message") or {}
            if isinstance(message.get("input_transformations"), list):
                self.transformations = message["input_transformations"]
            usage = message.get("usage") or {}
            counts = [
                usage.get(k)
                for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
            ]
            if isinstance(counts[0], int):
                self.prompt_tokens = sum(n for n in counts if isinstance(n, int))
        elif kind == "content_block_start":
            block = event.get("content_block")
            if not isinstance(block, dict) or not isinstance(event.get("index"), int):
                raise LlmError("protocol", "the server sent a malformed content block")
            self._blocks[event["index"]] = dict(block)
            if block.get("type") == "text":
                self._add_text(block.get("text"))
        elif kind == "content_block_delta":
            self._add_delta(event)
        elif kind == "message_delta":
            reason = (event.get("delta") or {}).get("stop_reason")
            if isinstance(reason, str):
                self.finish_reason = STOP_REASONS.get(reason, reason)
        elif kind == "message_stop":
            self.stopped = True

    def _add_delta(self, event: dict) -> None:
        block = self._blocks.get(event.get("index"))
        delta = event.get("delta")
        if block is None or not isinstance(delta, dict):
            raise LlmError("protocol", "the server sent a malformed delta")
        kind = delta.get("type")
        if kind == "text_delta" and block.get("type") == "text":
            block["text"] = (block.get("text") or "") + str(delta.get("text") or "")
            self._add_text(delta.get("text"))
        elif kind == "input_json_delta" and block.get("type") == "tool_use":
            self._json.setdefault(event["index"], []).append(str(delta.get("partial_json") or ""))
        elif kind == "thinking_delta" and block.get("type") == "thinking":
            block["thinking"] = (block.get("thinking") or "") + str(delta.get("thinking") or "")
        elif kind == "signature_delta" and block.get("type") == "thinking":
            block["signature"] = (block.get("signature") or "") + str(delta.get("signature") or "")

    def _add_text(self, text) -> None:
        if isinstance(text, str) and text and self._on_text is not None:
            self._on_text(text)

    def done(self) -> tuple[Completion, list[dict]]:
        """The completion and the content blocks of the message, to send back."""
        text, calls, blocks = [], [], []
        for index in sorted(self._blocks):
            block = self._blocks[index]
            kind = block.get("type")
            if kind == "text":
                if block.get("text"):  # the API refuses an empty text block
                    text.append(block["text"])
                    blocks.append({"type": "text", "text": block["text"]})
            elif kind == "tool_use":
                if not isinstance(block.get("name"), str) or not block["name"]:
                    raise LlmError("protocol", "the server sent a tool call without a name")
                pieces = self._json.get(index)
                arguments = "".join(pieces) if pieces else json.dumps(block.get("input") or {})
                try:
                    value = json.loads(arguments or "{}")
                except (ValueError, RecursionError):
                    raise LlmError("protocol", "the server sent invalid tool arguments") from None
                if not isinstance(value, dict):
                    raise LlmError("protocol", "the server sent invalid tool arguments")
                id_ = block["id"] if isinstance(block.get("id"), str) else f"call_{index}"
                calls.append(ToolCall(id_, block["name"], arguments or "{}"))
                use = {"type": "tool_use", "id": id_, "name": block["name"], "input": value}
                blocks.append(use)
            elif kind in ("thinking", "redacted_thinking"):
                blocks.append(block)
        completion = Completion("".join(text), calls, self.finish_reason, self.prompt_tokens)
        return completion, blocks


class ClaudeClient(HttpClient):
    def __init__(self, base_url: str, model: str, **options):
        super().__init__(base_url, model, **options)
        self._replies: OrderedDict[tuple[str, ...], list[dict]] = OrderedDict()
        self._lock = threading.Lock()  # one client serves the turns of several threads

    def complete(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        deadline: float,
        on_text: Callable[[str], None] | None = None,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> Completion:
        """One completion, streamed; as ``OllamaClient.complete``. A 401 is the error code
        ``unauthorized``, a 429 or a ``rate_limit_error`` event ``rate_limited``, a 529 or an
        ``overloaded_error`` event ``overloaded``."""
        system, converted = self._convert(messages)
        body = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "stream": True,
            "thinking": THINKING,
            "messages": converted,
            "cache_control": CACHE,
        }
        if system:
            body["system"] = [{"type": "text", "text": system, "cache_control": CACHE}]
        if tools:
            body["tools"] = claude_tools(tools)
        headers = {"anthropic-version": ANTHROPIC_VERSION, "anthropic-beta": ANTHROPIC_BETA}
        if self._api_key:
            headers["x-api-key"] = self._api_key
        reply = _Reply(on_text, self._api_key)

        def read(response: httpx.Response, check: Callable[[], None]) -> None:
            for line in _lines(response, check):
                check()
                if line.startswith(b"data:"):  # ``event:`` names the same type as the data
                    reply.add_event(_loads(line[5:].strip()))
                    if reply.stopped:
                        return
            raise LlmError("protocol", "the stream ended before the reply was complete")

        self._post(
            f"{self.base_url}/v1/messages",
            body,
            headers,
            deadline=deadline,
            cancelled=cancelled,
            read=read,
        )
        if reply.finish_reason is None:
            raise LlmError("protocol", "the stream ended without a stop reason")
        if reply.transformations:
            log.debug(
                "the API changed the request: %s",
                [(t.get("type"), t.get("reason"), t.get("path")) for t in reply.transformations
                 if isinstance(t, dict)],
            )  # fmt: skip
        completion, blocks = reply.done()
        if completion.tool_calls:
            with self._lock:
                self._replies[tuple(c.id for c in completion.tool_calls)] = blocks
                while len(self._replies) > MAX_KEPT_REPLIES:
                    self._replies.popitem(last=False)
        return completion

    def _convert(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """The top-level ``system`` and the Anthropic messages of OpenAI-shaped ``messages``."""
        system: list[str] = []
        out: list[dict] = []
        turn = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=0)
        for at, message in enumerate(messages):
            role, content = message.get("role"), message.get("content") or ""
            if role == "system":
                system.append(content)
            elif role == "tool":
                result = {
                    "type": "tool_result",
                    "tool_use_id": message.get("tool_call_id") or "",
                    "content": content,
                }
                last = out[-1] if out else None
                if last and last["role"] == "user" and isinstance(last["content"], list):
                    last["content"].append(result)
                else:
                    out.append({"role": "user", "content": [result]})
            elif role == "assistant":
                calls = message.get("tool_calls") or []
                blocks = self._assistant_blocks(content, calls, kept=at > turn)
                if blocks:
                    out.append({"role": "assistant", "content": blocks})
            else:
                out.append({"role": "user", "content": content})
        return "\n\n".join(system), out

    def _assistant_blocks(self, content: str, calls: list[dict], *, kept: bool) -> list[dict]:
        """The blocks of an assistant message: the kept reply when ``kept`` (in the current
        turn, whose thinking goes back), else built from the message."""
        ids = tuple(call.get("id") or "" for call in calls)
        if calls and kept:
            with self._lock:
                kept = self._replies.get(ids)
            if kept is not None:
                return kept
        blocks = [{"type": "text", "text": content}] if content else []
        for call in calls:
            function = call.get("function") or {}
            blocks.append(
                {
                    "type": "tool_use",
                    "id": call.get("id") or "",
                    "name": function.get("name") or "",
                    "input": _input(function.get("arguments")),
                }
            )
        return blocks
