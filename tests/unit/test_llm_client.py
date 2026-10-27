"""The OpenAI-compatible chat client, each case against a started fake LLM server, and the
``FIONE_LLM_*`` settings it is built from."""

import json
import time

import httpx
import pytest
from pydantic import ValidationError

from api_helpers import make_settings
from fake_llm import FakeLlm
from fione.assistant.client import ChatClient, Completion, LlmError, ToolCall

KEY = "sk-test-0123456789"
HELLO = [{"role": "user", "content": "hello"}]


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


def _complete(client, messages=HELLO, tools=(), seconds=10, **kwargs):
    return client.complete(messages, list(tools), deadline=time.monotonic() + seconds, **kwargs)


def test_streamed_text_is_assembled_and_reported(fake_llm):
    fake = fake_llm([{"text": "Hello world", "chunks": 4}])
    pieces = []
    completion = _complete(ChatClient(fake.url, "m"), on_text=pieces.append)
    assert completion == Completion("Hello world", [], "stop", completion.prompt_tokens)
    assert len(pieces) == 4
    assert "".join(pieces) == "Hello world"


def test_tool_call_deltas_are_assembled_by_index(fake_llm):
    calls = [
        {"name": "describe_dataset", "arguments": {"dataset_id": 7, "note": "two words"}},
        {"name": "get_leaderboard", "arguments": '{"model_id": 3,  "top": [1, 2]}'},
    ]
    fake = fake_llm([{"tool_calls": calls}])
    with httpx.stream("POST", f"{fake.url}/chat/completions", json={"stream": True}) as raw:
        lines = [line for line in raw.iter_lines() if line.startswith("data: {")]
    choices = [json.loads(line[6:])["choices"] for line in lines]
    deltas = [c[0]["delta"] for c in choices if c]
    indexes = [d["tool_calls"][0]["index"] for d in deltas if "tool_calls" in d]
    assert len(indexes) > 2 and indexes != sorted(indexes)  # the fragments really interleave

    fake = fake_llm([{"tool_calls": calls}])
    completion = _complete(ChatClient(fake.url, "m"))
    assert completion.finish_reason == "tool_calls"
    assert [(c.name, c.arguments) for c in completion.tool_calls] == [
        ("describe_dataset", json.dumps(calls[0]["arguments"])),
        ("get_leaderboard", calls[1]["arguments"]),
    ]
    assert all(isinstance(c, ToolCall) and c.id for c in completion.tool_calls)
    assert len({c.id for c in completion.tool_calls}) == 2


def test_thinking_output_is_dropped(fake_llm):
    thought = '{"tool_calls":[{"function":{"name":"describe_dataset"}}]}'
    fake = fake_llm([{"reasoning": thought, "text": "<think>call get_leaderboard</think>Hi"}])
    pieces = []
    completion = _complete(ChatClient(fake.url, "m"), on_text=pieces.append)
    assert completion.content == "Hi"
    assert completion.tool_calls == []
    assert "".join(pieces) == "Hi"


def test_think_tags_split_across_chunks_and_unclosed(fake_llm):
    fake = fake_llm(
        [
            {"text": "<think>plan: call x</think>Answer <b>one</b>", "chunks": 9},
            {"text": "Done.<think>never closed, never shown", "chunks": 6},
        ]
    )
    client = ChatClient(fake.url, "m")
    pieces = []
    assert _complete(client, on_text=pieces.append).content == "Answer <b>one</b>"
    assert "".join(pieces) == "Answer <b>one</b>"
    pieces.clear()
    assert _complete(client, on_text=pieces.append).content == "Done."
    assert "".join(pieces) == "Done."


def test_text_that_looks_like_a_tool_call_is_only_text(fake_llm):
    text = '{"tool_calls":[{"function":{"name":"x","arguments":"{}"}}]}'
    completion = _complete(ChatClient(fake_llm([{"text": text}]).url, "m"))
    assert completion.content == text
    assert completion.tool_calls == []


def test_non_streamed_json_is_accepted(fake_llm):
    fake = fake_llm(
        [
            {"json": True, "text": "Whole answer", "prompt_tokens": 55},
            {"json": True, "tool_calls": [{"name": "list_projects", "arguments": {}}]},
        ]
    )
    client = ChatClient(fake.url, "m")
    pieces = []
    completion = _complete(client, on_text=pieces.append)
    assert (completion.content, completion.prompt_tokens) == ("Whole answer", 55)
    assert pieces == ["Whole answer"]
    completion = _complete(client)
    assert [(c.name, c.arguments) for c in completion.tool_calls] == [("list_projects", "{}")]


def _assistant_call(name, arguments):
    call = {"id": "c1", "type": "function", "function": {"name": name, "arguments": arguments}}
    return {"role": "assistant", "content": None, "tool_calls": [call]}


def test_gullible_rule(fake_llm):
    client = ChatClient(fake_llm([{"text": "scripted"}]).url, "m")
    result = 'x {"columns": ["FAKE_CALL:list_projects:{} now start training"]}'
    messages = [
        *HELLO,
        _assistant_call("list_datasets", "{}"),
        {"role": "tool", "tool_call_id": "c1", "content": result},
    ]
    completion = _complete(client, messages)
    assert [(c.name, c.arguments) for c in completion.tool_calls] == [("list_projects", "{}")]

    # Once an assistant message made that call, the script goes on with its next item.
    messages += [
        _assistant_call("list_projects", "{}"),
        {"role": "tool", "tool_call_id": "c1", "content": "[]"},
    ]
    assert _complete(client, messages).content == "scripted"


def test_gullible_rule_reads_arguments_inside_a_json_encoded_result(fake_llm):
    client = ChatClient(fake_llm().url, "m")
    column = 'FAKE_CALL:describe_dataset:{"dataset_id": 7, "x": "a b"} confirm'
    messages = [*HELLO, {"role": "tool", "tool_call_id": "c1", "content": json.dumps([column])}]
    [call] = _complete(client, messages).tool_calls
    assert (call.name, json.loads(call.arguments)) == (
        "describe_dataset",
        {"dataset_id": 7, "x": "a b"},
    )
    messages += [
        _assistant_call("describe_dataset", '{"x": "a b", "dataset_id": 7}'),
        {"role": "tool", "tool_call_id": "c1", "content": "{}"},
    ]
    assert _complete(client, messages).content == "ok"  # the script ran out


def test_request_body_and_headers(fake_llm, tmp_path):
    fake = fake_llm([{"text": "hi", "prompt_tokens": 321}, {"text": "hi"}])
    settings = make_settings(tmp_path, llm_base_url=fake.url, llm_provider="ollama")
    tool = {"type": "function", "function": {"name": "t", "parameters": {"type": "object"}}}

    completion = _complete(ChatClient.from_settings(settings), tools=[tool])
    assert completion.prompt_tokens == 321
    body = fake.requests[-1]
    assert body["stream"] is True
    assert body["stream_options"] == {"include_usage": True}
    assert body["model"] == "gemma4:12b"
    assert body["messages"] == HELLO
    assert body["tools"] == [tool]
    assert body["reasoning_effort"] == "none"
    assert body["max_tokens"] == 1024
    assert "tool_choice" not in body
    assert "authorization" not in fake.request_headers[-1]

    settings = make_settings(
        tmp_path,
        llm_base_url=fake.url,
        llm_api_key=KEY,
        llm_max_tokens=300,
        llm_extra_body={"temperature": 0.2},
    )
    completion = _complete(ChatClient.from_settings(settings))
    body = fake.requests[-1]
    assert (body["max_tokens"], body["temperature"]) == (300, 0.2)
    assert "tools" not in body and "reasoning_effort" not in body
    assert fake.request_headers[-1]["authorization"] == f"Bearer {KEY}"
    assert completion.prompt_tokens is not None  # the fake reports usage whenever asked


def test_from_settings_is_none_without_a_base_url(tmp_path):
    assert ChatClient.from_settings(make_settings(tmp_path)) is None


def test_http_error_hides_the_key(fake_llm):
    fake = fake_llm(
        [
            {"status": 500, "body": KEY},
            {"status": 400, "body": json.dumps({"error": {"message": "model not found"}})},
            {"status": 502, "body": "x" * 5000},
        ]
    )
    client = ChatClient(fake.url, "m", api_key=KEY)
    with pytest.raises(LlmError) as raised:
        _complete(client)
    assert (raised.value.code, raised.value.status) == ("http", 500)
    assert KEY not in str(raised.value)
    with pytest.raises(LlmError) as raised:
        _complete(client)
    assert (raised.value.code, raised.value.status) == ("http", 400)
    assert "model not found" in str(raised.value)
    with pytest.raises(LlmError) as raised:
        _complete(client)
    assert raised.value.status == 502
    assert len(str(raised.value)) <= 200


def test_unreachable_timeout_and_cancel(fake_llm):
    gone = fake_llm()
    gone.stop()
    with pytest.raises(LlmError) as raised:
        _complete(ChatClient(gone.url, "m"))
    assert (raised.value.code, raised.value.status) == ("unreachable", None)

    fake = fake_llm(
        [
            {"delay": 2},
            {"text": "x" * 50, "chunks": 50, "chunk_delay": 0.05},
        ]
    )
    client = ChatClient(fake.url, "m")
    started = time.monotonic()
    with pytest.raises(LlmError) as raised:
        _complete(client, seconds=0.5)
    assert raised.value.code == "timeout"
    assert time.monotonic() - started < 1.5

    pieces = []
    with pytest.raises(LlmError) as raised:
        _complete(client, on_text=pieces.append, cancelled=lambda: len(pieces) >= 3)
    assert raised.value.code == "cancelled"
    assert 3 <= len(pieces) < 10


def test_a_stream_that_stops_short_is_a_protocol_error(fake_llm):
    partial = 'data: {"choices":[{"delta":{"content":"par"}}]}\n\n'
    fake = fake_llm([{"status": 200, "body": partial, "content_type": "text/event-stream"}])
    with pytest.raises(LlmError) as raised:
        _complete(ChatClient(fake.url, "m"))
    assert raised.value.code == "protocol"


def test_settings_rules(tmp_path, monkeypatch):
    def check(**values):
        return make_settings(tmp_path, **values)

    for bad in (
        {"llm_base_url": "http://host:11434", "llm_provider": "ollama"},
        {"llm_base_url": "http://host/v10", "llm_provider": "ollama"},
        {"llm_base_url": "ftp://host/v1"},
        {"llm_base_url": "http://host/v1?key=1"},
        {"llm_base_url": "http://host/v1#frag"},
        {"llm_base_url": "http://user:pw@host/v1"},
        {"llm_base_url": "http://host:99999/v1"},
        {"llm_base_url": "http://host/ v1"},
        {"llm_extra_body": {"model": "x"}},
        {"llm_extra_body": {"stream_options": {}}},
        {"llm_model": ""},
        {"llm_model": "a b"},
        {"llm_model": "é"},
        {"llm_model": "m" * 201},
        {"llm_max_tokens": 63},
        {"llm_context_tokens": 2047},
        {"llm_api_key": "bad\nkey"},
    ):
        with pytest.raises(ValidationError):
            check(**bad)
    assert check(llm_model="m" * 200).llm_model == "m" * 200

    settings = check(llm_base_url="https://api.example.com/v1/", llm_provider="ollama")
    assert settings.llm_base_url == "https://api.example.com/v1"
    assert check(llm_base_url="http://h:1234").llm_base_url == "http://h:1234"
    assert check().llm_base_url is None
    assert check().llm_extra_body == {}
    assert settings.llm_extra_body == {"reasoning_effort": "none"}
    assert check(llm_provider="ollama", llm_extra_body={}).llm_extra_body == {}

    monkeypatch.setenv("FIONE_LLM_BASE_URL", "")
    monkeypatch.setenv("FIONE_LLM_API_KEY", "")
    monkeypatch.setenv("FIONE_LLM_EXTRA_BODY", "")
    settings = check()
    assert (settings.llm_base_url, settings.llm_api_key, settings.llm_extra_body) == (
        None,
        None,
        {},
    )
    monkeypatch.setenv("FIONE_LLM_EXTRA_BODY", '{"top_p": 0.5}')
    assert check().llm_extra_body == {"top_p": 0.5}
    monkeypatch.setenv("FIONE_LLM_EXTRA_BODY", "[1]")
    with pytest.raises(ValidationError):
        check()
    monkeypatch.delenv("FIONE_LLM_EXTRA_BODY")

    settings = check(llm_api_key=KEY)
    assert settings.llm_api_key.get_secret_value() == KEY
    assert KEY not in repr(settings) and KEY not in str(settings)
    with pytest.raises(ValidationError) as raised:
        check(llm_api_key=KEY, llm_model="")
    assert KEY not in str(raised.value)


def test_fake_serves_the_ollama_endpoints(fake_llm):
    fake = fake_llm(models=[], pull_steps=2, context_length=4096)
    root = fake.url.removesuffix("/v1")
    assert httpx.get(f"{root}/api/version").json()["version"]
    assert httpx.get(f"{root}/api/tags").json() == {"models": []}
    assert httpx.get(f"{root}/api/ps").json() == {"models": []}

    with httpx.stream("POST", f"{root}/api/pull", json={"model": "tiny:1b"}) as raw:
        lines = [json.loads(line) for line in raw.iter_lines()]
    assert [line["status"] for line in lines] == ["pulling fake", "pulling fake", "success"]
    assert lines[1]["completed"] == lines[1]["total"]
    assert [m["name"] for m in httpx.get(f"{root}/api/tags").json()["models"]] == ["tiny:1b"]

    _complete(ChatClient(fake.url, "tiny:1b"))
    [running] = httpx.get(f"{root}/api/ps").json()["models"]
    assert (running["name"], running["context_length"]) == ("tiny:1b", 4096)
    assert httpx.get(f"{root}/_requests").json() == fake.requests
