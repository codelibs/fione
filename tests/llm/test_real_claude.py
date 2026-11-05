"""Opt-in checks against the real Anthropic API (``-m llm``): a plain reply, a tool round trip
whose thinking goes back, and a round whose earlier reply has no kept thinking. Set
``FIONE_TEST_ANTHROPIC_API_KEY``; ``FIONE_TEST_ANTHROPIC_MODEL`` (default ``claude-opus-5-5``)
and ``FIONE_TEST_ANTHROPIC_BASE_URL`` (default ``https://api.anthropic.com``) are optional.
Each run spends a few requests' tokens."""

import json
import os
import time

import pytest

from fione.assistant.claude import ClaudeClient

pytestmark = pytest.mark.llm

API_KEY = os.environ.get("FIONE_TEST_ANTHROPIC_API_KEY")
if not API_KEY:
    pytest.skip("set FIONE_TEST_ANTHROPIC_API_KEY", allow_module_level=True)
MODEL = os.environ.get("FIONE_TEST_ANTHROPIC_MODEL") or "claude-opus-5-5"
BASE_URL = os.environ.get("FIONE_TEST_ANTHROPIC_BASE_URL") or "https://api.anthropic.com"

TOOL = {
    "type": "function",
    "function": {
        "name": "list_datasets",
        "description": "List the datasets of a project: their ids, names and row counts.",
        "parameters": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
}
QUESTION = [
    {"role": "system", "content": "You answer questions about Fione projects. Use the tools."},
    {"role": "user", "content": "Which datasets does project p1 have? Use list_datasets."},
]
RESULT = json.dumps({"datasets": [{"id": "d1", "name": "iris", "rows": 150}]})


def client() -> ClaudeClient:
    return ClaudeClient(BASE_URL, MODEL, api_key=API_KEY, max_tokens=16000)


def complete(chat: ClaudeClient, messages: list[dict], tools=()):
    completion = chat.complete(messages, list(tools), deadline=time.monotonic() + 300)
    print(f"\ncompletion: {completion}")
    return completion


def with_results(messages: list[dict], completion) -> list[dict]:
    """``messages``, the reply's tool calls and a result for each."""
    calls = [
        {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
        for c in completion.tool_calls
    ]
    return [
        *messages,
        {"role": "assistant", "content": completion.content, "tool_calls": calls},
        *({"role": "tool", "tool_call_id": c.id, "content": RESULT} for c in completion.tool_calls),
    ]


def test_a_plain_reply():
    with client() as chat:
        completion = complete(chat, [{"role": "user", "content": "Say hello in one word."}])
    assert completion.finish_reason == "stop" and completion.content.strip()
    assert completion.tool_calls == []


def test_a_tool_round_trip_sends_the_thinking_back():
    with client() as chat:
        first = complete(chat, QUESTION, [TOOL])
        assert first.finish_reason == "tool_calls"
        assert [c.name for c in first.tool_calls] == ["list_datasets"]
        kept = chat._replies[tuple(c.id for c in first.tool_calls)]
        print(f"kept blocks: {[b.get('type') for b in kept]}")
        assert any(b.get("type") == "tool_use" for b in kept)
        second = complete(chat, with_results(QUESTION, first), [TOOL])
    assert second.finish_reason == "stop" and "iris" in second.content


def test_a_round_whose_earlier_reply_has_no_kept_thinking():
    with client() as chat:
        first = complete(chat, QUESTION, [TOOL])
    assert first.finish_reason == "tool_calls"
    messages = with_results(QUESTION, first)
    # A new client has kept nothing: the reply goes back as text and tool_use blocks only, as
    # after a restart in the middle of a turn.
    with client() as fresh:
        second = complete(fresh, messages, [TOOL])
        assert second.finish_reason == "stop" and "iris" in second.content
        later = [
            *messages,
            {"role": "assistant", "content": second.content},
            {"role": "user", "content": "How many rows does it have? Answer with the number."},
        ]
        third = complete(fresh, later, [TOOL])
    assert third.finish_reason in ("stop", "tool_calls")
    assert "150" in third.content or third.tool_calls
