"""The Claude client (Anthropic Messages API), each case against a started fake LLM server, and
the factory that picks the client of the configured provider."""

import json
import logging
import time

import httpx
import pytest

from api_helpers import make_settings
from fake_llm import FakeLlm
from fione.assistant.claude import ANTHROPIC_VERSION, ClaudeClient
from fione.assistant.client import ChatClient, Completion, LlmError, OllamaClient

KEY = "sk-ant-test-0123456789"
HELLO = [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "hello"}]
TOOL = {
    "type": "function",
    "function": {
        "name": "describe_dataset",
        "description": "Describe a dataset.",
        "parameters": {"type": "object", "properties": {"dataset_id": {"type": "integer"}}},
    },
}


@pytest.fixture
def fake_llm():
    started = []

    def factory(script=None, **kwargs):
        fake = FakeLlm(script, **kwargs).start()
        started.append(fake)
        return fake

    yield factory
    for fake in started:
        fake.stop()


def _client(fake, **kwargs):
    return ClaudeClient(fake.origin, "claude-opus-5-5", api_key=KEY, **kwargs)


def _complete(client, messages=HELLO, tools=(), seconds=10, **kwargs):
    return client.complete(messages, list(tools), deadline=time.monotonic() + seconds, **kwargs)


def test_claude_streams_text(fake_llm):
    fake = fake_llm([{"text": "Hello world", "chunks": 4, "prompt_tokens": 42}])
    pieces = []
    completion = _complete(_client(fake), on_text=pieces.append)
    assert completion == Completion("Hello world", [], "stop", 42)
    assert len(pieces) == 4 and "".join(pieces) == "Hello world"
    body = fake.requests[-1]
    assert body["system"] == [
        {"type": "text", "text": "Be brief.", "cache_control": {"type": "ephemeral"}}
    ]
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    assert (body["model"], body["max_tokens"], body["stream"]) == ("claude-opus-5-5", 1024, True)
    assert "tools" not in body


def test_claude_tool_use_round_trip(fake_llm):
    calls = [
        {"name": "describe_dataset", "arguments": {"dataset_id": 7, "note": "two words"}},
        {"name": "list_projects", "arguments": {}},
    ]
    fake = fake_llm([{"text": "Let me look.", "tool_calls": calls}, {"text": "Done."}])
    client = _client(fake)
    completion = _complete(client, tools=[TOOL])
    assert completion.finish_reason == "tool_calls"
    assert completion.content == "Let me look."
    assert [(c.name, json.loads(c.arguments)) for c in completion.tool_calls] == [
        ("describe_dataset", {"dataset_id": 7, "note": "two words"}),
        ("list_projects", {}),
    ]
    assert fake.requests[-1]["tools"] == [
        {
            "name": "describe_dataset",
            "description": "Describe a dataset.",
            "input_schema": TOOL["function"]["parameters"],
        }
    ]
    first, second = completion.tool_calls
    messages = [
        *HELLO,
        {
            "role": "assistant",
            "content": completion.content,
            "tool_calls": [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": a}}
                for c, a in ((first, first.arguments), (second, "not json"))
            ],
        },
        {"role": "tool", "tool_call_id": first.id, "content": '{"columns": []}'},
        {"role": "tool", "tool_call_id": second.id, "content": "[]"},
    ]
    assert _complete(client, messages, tools=[TOOL]).content == "Done."
    sent = fake.requests[-1]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    blocks = sent[1]["content"]
    # The thinking block of the reply goes back first, unchanged, with its signature.
    assert blocks[0]["type"] == "thinking" and blocks[0]["signature"]
    assert blocks[1:] == [
        {"type": "text", "text": "Let me look."},
        {"type": "tool_use", "id": first.id, "name": "describe_dataset",
         "input": {"dataset_id": 7, "note": "two words"}},
        {"type": "tool_use", "id": second.id, "name": "list_projects", "input": {}},
    ]  # fmt: skip
    assert sent[2]["content"] == [
        {"type": "tool_result", "tool_use_id": first.id, "content": '{"columns": []}'},
        {"type": "tool_result", "tool_use_id": second.id, "content": "[]"},
    ]

    # In a later turn the reply goes back without its thinking.
    messages += [{"role": "assistant", "content": "Done."}, {"role": "user", "content": "more"}]
    _complete(client, messages, tools=[TOOL])
    later = fake.requests[-1]["messages"][1]["content"]
    assert [b["type"] for b in later] == ["text", "tool_use", "tool_use"]


def test_claude_history_without_a_kept_reply_is_converted(fake_llm):
    fake = fake_llm()
    call = {"id": "call_1", "type": "function", "function": {"name": "x", "arguments": "[1]"}}
    messages = [
        *HELLO,
        {"role": "assistant", "content": None, "tool_calls": [call]},
        {"role": "tool", "tool_call_id": "call_1", "content": "{}"},
        {"role": "assistant", "content": ""},
        {"role": "user", "content": "again"},
    ]
    _complete(_client(fake), messages)
    assert fake.requests[-1]["messages"][1:] == [
        {"role": "assistant",
         "content": [{"type": "tool_use", "id": "call_1", "name": "x", "input": {}}]},
        {"role": "user",
         "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": "{}"}]},
        {"role": "user", "content": "again"},
    ]  # fmt: skip


def test_claude_invalid_tool_json_is_an_llm_error(fake_llm):
    fake = fake_llm(
        [
            {"tool_calls": [{"name": "describe_dataset", "arguments": '{"dataset_id": '}]},
            {"tool_calls": [{"name": "describe_dataset", "arguments": "[1, 2]"}]},
        ]
    )
    client = _client(fake)
    for _ in range(2):
        with pytest.raises(LlmError) as raised:
            _complete(client)
        assert raised.value.code == "protocol"


def test_claude_maps_stop_reasons(fake_llm):
    fake = fake_llm(
        [
            {"tool_calls": [{"name": "list_projects", "arguments": {}}]},
            {"text": "fine"},
            {"text": "cut sh", "stop_reason": "max_tokens"},
            {"text": "", "stop_reason": "refusal"},
        ]
    )
    client = _client(fake)
    reasons = [_complete(client).finish_reason for _ in range(4)]
    assert reasons == ["tool_calls", "stop", "length", "refusal"]


def test_claude_401_names_unauthorized_without_the_key(fake_llm):
    fake = fake_llm(api_key="sk-ant-the-right-one")
    with pytest.raises(LlmError) as raised:
        _complete(_client(fake))
    assert (raised.value.code, raised.value.status) == ("unauthorized", 401)
    assert "invalid x-api-key" in str(raised.value)
    assert KEY not in str(raised.value)


def test_claude_error_event_becomes_llm_error(fake_llm):
    fake = fake_llm([{"text": "par", "error": f"Broken {KEY}", "error_type": "api_error"}])
    pieces = []
    with pytest.raises(LlmError) as raised:
        _complete(_client(fake), on_text=pieces.append)
    assert raised.value.code == "protocol"
    assert "Broken" in str(raised.value) and KEY not in str(raised.value)
    assert pieces == ["par"]


@pytest.mark.parametrize(
    ("kind", "code"), [("rate_limit_error", "rate_limited"), ("overloaded_error", "overloaded")]
)
def test_claude_rate_limit_and_overload_have_their_codes(fake_llm, kind, code):
    fake = fake_llm(
        [{"api_error": kind}, {"text": "par", "error": f"busy {KEY}", "error_type": kind}]
    )
    client = _client(fake)
    with pytest.raises(LlmError) as raised:  # over HTTP
        _complete(client)
    status = {"rate_limit_error": 429, "overloaded_error": 529}[kind]
    assert (raised.value.code, raised.value.status) == (code, status)
    with pytest.raises(LlmError) as raised:  # as an error event in the stream
        _complete(client)
    assert raised.value.code == code and KEY not in str(raised.value)


def test_claude_other_error_statuses_keep_their_codes(fake_llm):
    fake = fake_llm([{"api_error": "api_error"}, {"status": 400, "body": f"bad {KEY}"}])
    client = _client(fake)
    for status in (500, 400):
        with pytest.raises(LlmError) as raised:
            _complete(client)
        assert (raised.value.code, raised.value.status) == ("http", status)
        assert KEY not in str(raised.value)


def test_claude_caches_the_tools_and_system_and_the_conversation(fake_llm):
    fake = fake_llm([{"text": "Let me look.", "tool_calls": [{"name": "describe_dataset"}]}])
    client = _client(fake)
    completion = _complete(client, tools=[TOOL])
    # the system's last block holds tools and system (they render first); the automatic
    # breakpoint at the request's top level follows the conversation as it grows
    assert fake.cache_points[-1] == ["request", "system.0"]
    assert fake.requests[-1]["cache_control"] == {"type": "ephemeral"}
    call = completion.tool_calls[0]
    history = [
        *HELLO,
        {"role": "assistant", "content": completion.content,
         "tool_calls": [{"id": call.id, "type": "function",
                         "function": {"name": call.name, "arguments": call.arguments}}]},
        {"role": "tool", "tool_call_id": call.id, "content": "{}"},
    ]  # fmt: skip
    _complete(client, history, tools=[TOOL])
    assert fake.cache_points[-1] == ["request", "system.0"]
    assert "cache_control" not in json.dumps(fake.requests[-1]["tools"])


def test_claude_error_event_hides_a_key_that_straddles_the_cut(fake_llm):
    # "the server reported an error: " and the filler put the key across the 200th character.
    fake = fake_llm([{"text": "", "error": "x" * 160 + KEY}])
    with pytest.raises(LlmError) as raised:
        _complete(_client(fake))
    assert KEY[:6] not in str(raised.value) and str(raised.value).endswith("***")


def test_claude_stream_that_stops_short_is_a_protocol_error(fake_llm):
    events = [
        {"type": "message_start", "message": {"usage": {"input_tokens": 3}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "x"}},
    ]
    body = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events)
    fake = fake_llm([{"status": 200, "body": body, "content_type": "text/event-stream"}])
    with pytest.raises(LlmError) as raised:
        _complete(_client(fake))
    assert raised.value.code == "protocol"


@pytest.mark.parametrize("error", [{"type": ["x"], "message": "odd"}, "text", None])
def test_claude_malformed_error_event_is_still_an_llm_error(fake_llm, error):
    event = {"type": "error", "error": error}
    body = f"event: error\ndata: {json.dumps(event)}\n\n"
    fake = fake_llm([{"status": 200, "body": body, "content_type": "text/event-stream"}])
    with pytest.raises(LlmError) as raised:
        _complete(_client(fake))
    assert raised.value.code == "protocol"


def test_claude_request_has_required_headers(fake_llm):
    fake = fake_llm(api_key=KEY)
    assert _complete(_client(fake)).content == "ok"
    headers = fake.request_headers[-1]
    assert headers["x-api-key"] == KEY
    assert headers["anthropic-version"] == ANTHROPIC_VERSION
    assert headers["anthropic-beta"] == "thinking-binding-controls-2026-08-01"
    assert fake.requests[-1]["thinking"] == {
        "type": "adaptive",
        "block_binding": {"prefix_mismatch_behavior": "drop_block"},
    }
    assert headers["content-type"] == "application/json"
    assert "authorization" not in headers
    assert fake.paths[-1] == "POST /v1/messages"


def test_claude_timeout_and_cancel(fake_llm):
    fake = fake_llm([{"delay": 2}, {"text": "x" * 50, "chunks": 50, "chunk_delay": 0.05}])
    client = _client(fake)
    started = time.monotonic()
    with pytest.raises(LlmError) as raised:
        _complete(client, seconds=0.5)
    assert raised.value.code == "timeout"
    assert time.monotonic() - started < 1.5
    pieces = []
    with pytest.raises(LlmError) as raised:
        _complete(client, on_text=pieces.append, cancelled=lambda: len(pieces) >= 3)
    assert raised.value.code == "cancelled"


def test_factory_picks_the_provider(fake_llm, tmp_path):
    fake = fake_llm()
    settings = make_settings(
        tmp_path, llm_provider="claude", llm_base_url=fake.origin, llm_api_key=KEY
    )
    with ChatClient.from_settings(settings) as client:
        assert isinstance(client, ClaudeClient)
        assert _complete(client).content == "ok"
    assert fake.request_headers[-1]["x-api-key"] == KEY
    assert fake.requests[-1]["model"] == "claude-opus-5-5"
    with ChatClient.from_settings(make_settings(tmp_path, llm_base_url=fake.url)) as client:
        assert isinstance(client, OllamaClient)


def test_claude_changed_prefix_drops_the_thinking_block(fake_llm, caplog):
    fake = fake_llm([{"tool_calls": [{"name": "list_projects", "arguments": {}}]}, {"text": "ok"}])
    client = _client(fake)
    system, history = (
        HELLO[0],
        [
            {"role": "user", "content": "earlier"},
            {"role": "assistant", "content": "answer"},
        ],
    )
    turn = [{"role": "user", "content": "hello"}]
    [call] = _complete(client, [system, *history, *turn]).tool_calls
    made = {"id": call.id, "type": "function",
            "function": {"name": call.name, "arguments": call.arguments}}  # fmt: skip
    turn += [
        {"role": "assistant", "content": "", "tool_calls": [made]},
        {"role": "tool", "tool_call_id": call.id, "content": "[]"},
    ]
    # The history no longer fits and goes: the kept reply now follows another request.
    sent_system, converted = client._convert([system, *turn])
    assert converted[1]["content"][0]["type"] == "thinking"
    with caplog.at_level(logging.DEBUG, logger="fione.assistant.claude"):
        assert _complete(client, [system, *turn]).content == "ok"
    assert [b["type"] for b in fake.requests[-1]["messages"][1]["content"]] == ["tool_use"]
    assert "prefix_binding_mismatch" in caplog.text

    # Without drop_block, the same request is refused.
    headers = {
        "x-api-key": KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "anthropic-beta": "thinking-binding-controls-2026-08-01",
    }
    body = {"model": "claude-opus-5-5", "max_tokens": 1024, "system": sent_system,
            "thinking": {"type": "adaptive"}, "messages": converted}  # fmt: skip
    response = httpx.post(f"{fake.origin}/v1/messages", json=body, headers=headers)
    assert response.status_code == 400
    assert "bound to a different conversation" in response.json()["error"]["message"]
