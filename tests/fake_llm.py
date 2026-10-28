"""A fake OpenAI-compatible and Ollama server (stdlib only), for tests and the e2e stack.

Each chat request takes the next item of the script (when it runs out, the reply is the text
"ok"). The one exception is the gullible rule, which stands in for a model that obeys
injected text: when a ``tool`` message holds ``FAKE_CALL:<name>:<json object>`` that no earlier
assistant message acted on (none after that tool message made the call), the reply is that
tool call, and the script keeps its place.

Script items (the keys combine, except ``status``)::

    {"text": str, "chunks": int}             streamed text in about ``chunks`` pieces
    {"tool_calls": [{"name": str, "arguments": dict | str}]}
    {"reasoning": str, "reasoning_field": str}   sent as ``reasoning_content`` unless named
    {"prompt_tokens": int}                   reported in the final usage chunk
    {"delay": float, "chunk_delay": float}   before the reply, between its chunks
    {"json": True}                           one JSON body instead of a stream
    {"whole_calls": True}                    each call in one delta, all at ``index`` 0
    {"status": int, "body": str, "content_type": str, "headers": dict, "chunks": int}
                                             a raw reply, its body sent in ``chunks`` pieces

Run it with ``python fake_llm.py --port N --policy e2e [--missing]``; the ``e2e`` policy is
filled in with the end-to-end tests, until then it behaves as ``script``.
"""

import argparse
import itertools
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal

DEFAULT_MODEL = "gemma4:12b"
_FAKE_CALL = re.compile(r"FAKE_CALL:([A-Za-z_][A-Za-z0-9_]*):")


def _fake_calls(text: str):
    """The ``(name, arguments)`` pairs in ``text``. A tool result that was serialized to JSON
    holds the arguments with escaped quotes, so the text is also read with them unescaped."""
    seen = []
    for variant in (text, text.replace('\\"', '"')):
        for match in _FAKE_CALL.finditer(variant):
            try:
                arguments, _ = json.JSONDecoder().raw_decode(variant, match.end())
            except ValueError:
                continue
            if isinstance(arguments, dict) and (match[1], arguments) not in seen:
                seen.append((match[1], arguments))
    return seen


def _was_called(message: dict, name: str, arguments: dict) -> bool:
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        try:
            made = json.loads(function.get("arguments") or "{}")
        except ValueError:
            continue
        if function.get("name") == name and made == arguments:
            return True
    return False


def gullible_call(messages: list[dict]) -> tuple[str, dict] | None:
    """The first ``FAKE_CALL`` in a tool message that no later assistant message made."""
    for i, message in enumerate(messages):
        if message.get("role") != "tool":
            continue
        for name, arguments in _fake_calls(str(message.get("content") or "")):
            later = (m for m in messages[i + 1 :] if m.get("role") == "assistant")
            if not any(_was_called(m, name, arguments) for m in later):
                return name, arguments
    return None


def _pieces(text: str, count: int) -> list[str]:
    """``text`` in about ``count`` pieces of equal size."""
    if not text:
        return []
    size = -(-len(text) // max(1, min(count, len(text))))
    return [text[i : i + size] for i in range(0, len(text), size)]


class FakeLlm:
    def __init__(
        self,
        script: list[dict] | None = None,
        *,
        policy: Literal["script", "e2e"] = "script",
        models: list[str] | None = None,
        pull_steps: int = 3,
        pull_delay: float = 0.0,
        context_length: int = 16384,
        port: int = 0,
        pull_error: str | None = None,
        pull_garbage: int = 0,
    ):
        self.script = list(script or [])
        self.policy = policy
        self.models = [DEFAULT_MODEL] if models is None else list(models)
        self.pull_steps = pull_steps
        self.pull_delay = pull_delay
        self.context_length = context_length
        self.port = port
        self.pull_error = pull_error  # the pull stops with this error line after its first step
        self.pull_garbage = pull_garbage  # bytes with no newline sent as a pull's first line
        self.raw_replies: dict[str, bytes] = {}  # GET path -> body sent instead of the usual
        self.paths: list[str] = []  # "METHOD /path" of every request
        self.requests: list[dict] = []  # every chat body
        self.request_headers: list[dict] = []  # the matching headers, names in lower case
        self._served: str | None = None  # the model of the last chat request
        self._lock = threading.Lock()
        self._call_ids = itertools.count(1)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> "FakeLlm":
        fake = self

        class Handler(_Handler):
            llm = fake

        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        self._thread.start()
        self.port = self._server.server_port
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join()
            self._server = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def join(self) -> None:
        if self._thread is not None:
            self._thread.join()

    # --- what the handler asks for

    def record_chat(self, body: dict, headers: dict) -> dict:
        """Log a chat request and return the script item that answers it."""
        with self._lock:
            self.requests.append(body)
            self.request_headers.append(headers)
            self._served = body.get("model")
            messages = body.get("messages") or []
            if (call := gullible_call(messages)) is not None:
                return {"tool_calls": [{"name": call[0], "arguments": call[1]}]}
            return self.script.pop(0) if self.script else {"text": "ok"}

    def running_models(self) -> list[dict]:
        with self._lock:
            if self._served is None:
                return []
            return [
                {"name": self._served, "model": self._served, "context_length": self.context_length}
            ]

    def installed_models(self) -> list[dict]:
        with self._lock:
            return [{"name": name, "model": name} for name in self.models]

    def add_model(self, name: str) -> None:
        with self._lock:
            if name not in self.models:
                self.models.append(name)

    def next_call_id(self) -> str:
        return f"call_{next(self._call_ids)}"


class _Handler(BaseHTTPRequestHandler):
    llm: FakeLlm

    def log_message(self, format, *args):
        pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True  # the client gave up

    def do_GET(self):
        path = self.path.split("?")[0]
        self.llm.paths.append(f"GET {path}")
        if path in self.llm.raw_replies:
            return self._send(200, "application/json", self.llm.raw_replies[path])
        if path == "/api/version":
            self._json({"version": "0.0.0-fake"})
        elif path == "/api/tags":
            self._json({"models": self.llm.installed_models()})
        elif path == "/api/ps":
            self._json({"models": self.llm.running_models()})
        elif path == "/_requests":
            self._json(self.llm.requests)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        body = self._read_json()
        path = self.path.split("?")[0]
        self.llm.paths.append(f"POST {path}")
        if path.endswith("/chat/completions"):
            headers = {name.lower(): value for name, value in self.headers.items()}
            self._chat(body, self.llm.record_chat(body, headers))
        elif path == "/api/pull":
            self._pull(body)
        else:
            self._json({"error": "not found"}, 404)

    def _read_json(self) -> dict:
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {}

    def _send(
        self, status: int, content_type: str, data: bytes | None = None, headers: dict | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        if data is not None:
            self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data is not None:
            self.wfile.write(data)

    def _json(self, value, status: int = 200) -> None:
        self._send(status, "application/json", json.dumps(value).encode())

    def _event(self, data: str) -> None:
        self.wfile.write(f"data: {data}\n\n".encode())
        self.wfile.flush()

    def _pull(self, body: dict) -> None:
        name = str(body.get("model") or body.get("name") or "")
        if body.get("stream") is False:
            self.llm.add_model(name)
            return self._json({"status": "success"})
        self._send(200, "application/x-ndjson")
        for _ in range(0, self.llm.pull_garbage, 8192):
            self.wfile.write(b"x" * 8192)
            self.wfile.flush()
        total = 1_000_000
        for step in range(1, self.llm.pull_steps + 1):
            time.sleep(self.llm.pull_delay)
            line = {
                "status": "pulling fake",
                "total": total,
                "completed": total * step // self.llm.pull_steps,
            }
            self.wfile.write(json.dumps(line).encode() + b"\n")
            self.wfile.flush()
            if self.llm.pull_error is not None:
                self.wfile.write(json.dumps({"error": self.llm.pull_error}).encode() + b"\n")
                return
        self.llm.add_model(name)
        self.wfile.write(b'{"status":"success"}\n')

    def _chat(self, body: dict, item: dict) -> None:
        time.sleep(item.get("delay", 0))
        if "status" in item:
            raw = str(item.get("body", ""))
            kind, headers = item.get("content_type", "text/plain"), item.get("headers")
            if "chunks" not in item:
                return self._send(item["status"], kind, raw.encode(), headers)
            self._send(item["status"], kind, headers=headers)
            for piece in _pieces(raw, item["chunks"]):
                self.wfile.write(piece.encode())
                self.wfile.flush()
                time.sleep(item.get("chunk_delay", 0))
            return
        text = item.get("text", "")
        calls = [
            (self.llm.next_call_id(), call["name"], call.get("arguments", {}))
            for call in item.get("tool_calls", [])
        ]
        calls = [
            (id_, name, arguments if isinstance(arguments, str) else json.dumps(arguments))
            for id_, name, arguments in calls
        ]
        finish = "tool_calls" if calls else "stop"
        prompt_tokens = item.get("prompt_tokens")
        if prompt_tokens is None:
            prompt_tokens = len(json.dumps(body.get("messages") or [])) // 4 + 1
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": len(text) // 4 + 1,
            "total_tokens": prompt_tokens + len(text) // 4 + 1,
        }
        if item.get("json") or not body.get("stream"):
            message = {"role": "assistant", "content": text}
            if calls:
                message["tool_calls"] = [
                    {"id": id_, "type": "function", "function": {"name": n, "arguments": a}}
                    for id_, n, a in calls
                ]
            return self._json(
                {
                    "id": "chatcmpl-fake",
                    "object": "chat.completion",
                    "model": body.get("model"),
                    "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                    "usage": usage,
                }
            )

        deltas = [{"role": "assistant", "content": ""}]
        if item.get("reasoning"):
            deltas.append({item.get("reasoning_field", "reasoning_content"): item["reasoning"]})
        deltas += [{"content": piece} for piece in _pieces(text, item.get("chunks", 1))]
        # The fragments of different calls interleave, as a client must cope with.
        fragments = [_pieces(arguments, 3) or [""] for _, _, arguments in calls]
        if item.get("whole_calls"):
            for id_, name, arguments in calls:
                function = {"name": name, "arguments": arguments}
                deltas.append({"tool_calls": [{"index": 0, "id": id_, "function": function}]})
            fragments = []
        for round_ in range(max((len(f) for f in fragments), default=0)):
            for index, (id_, name, _) in enumerate(calls):
                if round_ < len(fragments[index]):
                    function = {"arguments": fragments[index][round_]}
                    call = {"index": index, "function": function}
                    if round_ == 0:
                        call.update(id=id_, type="function")
                        function["name"] = name
                    deltas.append({"tool_calls": [call]})
        chunks = [{"choices": [{"index": 0, "delta": delta}]} for delta in deltas]
        chunks.append({"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]})
        if (body.get("stream_options") or {}).get("include_usage"):
            chunks.append({"choices": [], "usage": usage})

        self._send(200, "text/event-stream")
        for chunk in chunks:
            self._event(json.dumps(chunk))
            time.sleep(item.get("chunk_delay", 0))
        self._event("[DONE]")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--policy", choices=["script", "e2e"], default="script")
    parser.add_argument("--missing", action="store_true", help="start without the model")
    args = parser.parse_args()
    fake = FakeLlm(policy=args.policy, models=[] if args.missing else None, port=args.port)
    fake.start()
    print(f"fake LLM at {fake.url}", flush=True)
    try:
        fake.join()
    except KeyboardInterrupt:
        fake.stop()


if __name__ == "__main__":
    main()
