"""Opt-in checks against a real model (``-m llm``): structured tool calls with thinking off, a
whole turn on iris, and the bytes-per-token estimate. Set ``FIONE_TEST_LLM_BASE_URL`` (for
example ``http://127.0.0.1:11434/v1``) and ``FIONE_TEST_LLM_MODEL``; port 11434 means Ollama.
Nothing is pulled or deleted; the Ollama model is unloaded before each measurement."""

import json
import os
import threading
import time
from urllib.parse import urlsplit

import httpx
import pytest

from api_helpers import iris_frame, make_settings
from fione import db
from fione.assistant import store
from fione.assistant.client import ChatClient
from fione.assistant.prompt import BYTES_PER_TOKEN, size, system_prompt
from fione.assistant.provider import LlmMonitor, native_root
from fione.assistant.turns import run_turn
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.service import DatasetType
from fione.storage import LocalStorage
from fione.tools import ToolContext, call_tool, list_tools

pytestmark = pytest.mark.llm

BASE_URL = os.environ.get("FIONE_TEST_LLM_BASE_URL")
MODEL = os.environ.get("FIONE_TEST_LLM_MODEL")
if not (BASE_URL and MODEL):
    pytest.skip("set FIONE_TEST_LLM_BASE_URL and FIONE_TEST_LLM_MODEL", allow_module_level=True)
OLLAMA = urlsplit(BASE_URL).port == 11434
ENGLISH = (
    "The iris data set has four measurements of each flower: the length and the width of the "
    "sepal and of the petal, in centimetres. Fifty flowers of each of three species were "
    "measured. A model that predicts the species from the measurements is a classic first "
    "exercise in machine learning, because two of the measurements separate the species well. "
) * 5
JAPANESE = (
    "アヤメのデータには、がく片と花弁の長さと幅という四つの測定値があります。三つの品種について"
    "五十本ずつ測りました。測定値から品種を当てるモデルは、機械学習の最初の練習としてよく使われます。"
) * 5


def settings(tmp_path, **values):
    provider = "ollama" if OLLAMA else "openai"
    return make_settings(
        tmp_path / "data", llm_base_url=BASE_URL, llm_model=MODEL, llm_provider=provider, **values
    )


@pytest.fixture
def env(tmp_path):
    conn = db.connect(tmp_path / "fione.db")
    db.migrate(conn)
    storage = LocalStorage(tmp_path / "storage")
    owner = auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR)
    project = projects.create_project(conn, owner, "p1")
    iris = ingest.ingest_batches(
        storage, conn, project.id, "iris", DatasetType.TRAIN, [iris_frame()]
    )
    yield conn, storage, owner, project, iris
    conn.close()


def unload() -> None:
    """Unload the Ollama model, so nothing of a previous prompt is cached."""
    if OLLAMA:
        httpx.post(
            f"{native_root(BASE_URL)}/api/generate",
            json={"model": MODEL, "keep_alive": 0},
            timeout=60,
        ).raise_for_status()


def test_tool_call_arrives_structured_without_thinking(tmp_path, env):
    _, _, _, project, _ = env
    s = settings(tmp_path)
    messages = [
        {"role": "system", "content": system_prompt("en", project.id, project.name)},
        {"role": "user", "content": f"List the datasets of project {project.id}."},
    ]
    with ChatClient.from_settings(s) as client:
        completion = client.complete(messages, list_tools(), deadline=time.monotonic() + 300)
    print(f"\ncompletion: {completion}")
    names = [call.name for call in completion.tool_calls]
    assert "list_datasets" in names
    call = completion.tool_calls[names.index("list_datasets")]
    assert isinstance(json.loads(call.arguments), dict)
    assert "<think>" not in completion.content

    # the raw stream: no reasoning field at all with the configured extra body
    body = {
        "model": MODEL,
        "messages": messages,
        "tools": list_tools(),
        "stream": True,
        **s.llm_extra_body,
    }
    reasoning = []
    with httpx.stream("POST", f"{BASE_URL}/chat/completions", json=body, timeout=300) as r:
        for line in r.iter_lines():
            if line.startswith("data:") and line[5:].strip() != "[DONE]":
                for choice in json.loads(line[5:]).get("choices") or []:
                    delta = choice.get("delta") or {}
                    reasoning += [
                        delta[k]
                        for k in ("reasoning_content", "reasoning", "thinking")
                        if delta.get(k)
                    ]
    print(f"extra body: {s.llm_extra_body}; reasoning pieces: {len(reasoning)}")
    assert reasoning == []


def test_full_turn_on_iris(tmp_path, env):
    conn, storage, owner, project, _ = env
    s = settings(tmp_path)
    conversation = store.create_conversation(conn, owner, project.id)
    _, placeholder = store.start_turn(
        conn, conversation.id, "Which column predicts species best? Propose a training."
    )
    monitor = LlmMonitor(s)
    try:
        with ChatClient.from_settings(s) as client:
            run_turn(
                tmp_path / "fione.db", storage, s, client, monitor, conversation.id,
                placeholder.id, threading.Event(), language="en",
            )  # fmt: skip
    finally:
        monitor.stop()
    rows = store.messages(conn, conversation.id)
    for row in rows:
        print(f"\n{row.role} {row.state} {row.error_code} {row.tool_calls} {row.content[:300]!r}")
    assert any(row.role == "tool" for row in rows)
    proposals = store.proposals_for(conn, conversation.id)
    assert proposals or (rows[-1].state == "done" and rows[-1].content)


def test_bytes_per_token_is_conservative(tmp_path, env):
    conn, storage, owner, project, iris = env
    described = call_tool(
        "describe_dataset",
        {"dataset_id": iris.id},
        ToolContext(conn, storage, owner, project_id=project.id, via="test"),
    )
    texts = {
        "english": ENGLISH,
        "japanese": JAPANESE,
        "describe_dataset": json.dumps(described, ensure_ascii=False, allow_nan=False),
    }
    s = settings(tmp_path, llm_max_tokens=64)
    ratios = {}
    with ChatClient.from_settings(s) as client:
        for name, text in texts.items():
            unload()
            messages = [{"role": "user", "content": text}]
            completion = client.complete(messages, [], deadline=time.monotonic() + 300)
            assert completion.prompt_tokens, "the server reported no prompt_tokens"
            ratios[name] = size(messages) / completion.prompt_tokens
    print(f"\nbytes per token ({MODEL}): {ratios}")
    assert min(ratios.values()) >= BYTES_PER_TOKEN, ratios
