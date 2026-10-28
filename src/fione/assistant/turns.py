"""Assistant turns (spec section 9): the rounds of one answer, and the pool that runs them.

A turn answers the user's latest message. Each round re-checks that the conversation's user
may still read the project, asks the model, and runs the tool calls it made through
``call_tool``, scoped to the conversation's project. Only the structured ``tool_calls`` of a
completion run anything, and only the read-only tools of the registry. A successful
``propose_training_config`` result becomes a pending proposal that a person confirms in Fione.

A message ends only through ``store.finish_message``, so whichever ending lands first (the
answer, a cancel, the deadline, a restart) wins. A row's error is a code; the provider's own
text goes to the log only.
"""

import json
import logging
import re
import sqlite3
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import closing
from pathlib import Path

from fione import db
from fione.assistant import store
from fione.assistant.client import ChatClient, Completion, LlmError
from fione.assistant.prompt import (
    ContextTooSmall,
    budget_bytes,
    build_messages,
    size,
    system_prompt,
)
from fione.assistant.provider import LlmMonitor
from fione.assistant.store import Message
from fione.auth import service as auth
from fione.auth.roles import User, can_access_project
from fione.config import Settings
from fione.projects import service as projects
from fione.schema import clean_text
from fione.storage import Storage
from fione.tools import ToolContext, ToolError, call_tool, list_tools

log = logging.getLogger("fione.assistant")

MAX_CALLS_PER_ROUND = 4  # run; the others are refused
MAX_CALLS_KEPT = 16  # stored and answered; a reply with more loses the rest
MAX_CONTENT_CHARS = 20_000  # of an assistant message
MAX_ARGUMENT_CHARS = 8_000  # of one call's arguments
WRITE_INTERVAL_SECS = 0.3  # between writes of the text as it streams
_POLL_SECS = 0.05
_CALL_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_TOOL_NAME_CHARS = 64
PROPOSE = "propose_training_config"
_DETAILS = ("warnings", "ignored_suggestions", "rationale")  # of a proposal, kept with it
TOO_MANY_CALLS = {"error": "too many tool calls in one step"}
BAD_ARGUMENTS = {"error": "arguments must be a JSON object"}
ONE_PROPOSAL = {"error": "one training proposal per step"}

# What a failed or ended turn's ``error_code`` can be; the UI has a text for each.
ERROR_CODES = (
    "unavailable",
    "unreachable",
    "http",
    "protocol",
    "timeout",
    "too_many_steps",
    "context_too_small",
    "forbidden",
    "interrupted",
    "cancelled",
    "failed",
)


class LlmUnavailable(Exception):
    """No LLM is configured, or the provider is not ready (unreachable, pulling...)."""


class _Stop(Exception):
    """The turn's message was ended elsewhere, or its conversation is gone: stop quietly."""


class _Failed(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _arguments(text: str) -> dict | None:
    """A call's arguments as a JSON object, or None."""
    if len(text) > MAX_ARGUMENT_CHARS:
        return None
    try:
        value = json.loads(text)
    except (ValueError, RecursionError):
        return None
    return value if isinstance(value, dict) else None


def _dumps(value) -> str | None:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    except ValueError:  # NaN or infinity in what the model sent
        return None


class _Turn:
    def __init__(
        self,
        conn: sqlite3.Connection,
        storage: Storage,
        settings: Settings,
        client: ChatClient | None,
        monitor: LlmMonitor,
        conversation_id: int,
        cancel: threading.Event,
        deadline: float,
        language: str,
    ):
        self.conn = conn
        self.storage = storage
        self.settings = settings
        self.client = client
        self.monitor = monitor
        self.conversation_id = conversation_id
        self.cancel = cancel
        self.deadline = deadline
        self.language = language
        self.row = 0  # the assistant message being written
        self.partial = ""  # its text so far

    def run(self, row: int) -> None:
        self.row = row
        try:
            self._rounds()
        except (_Stop, store.ConversationNotFound):
            pass
        except _Failed as e:
            self._end("failed", error_code=e.code)
        except ContextTooSmall:
            self._end("failed", error_code="context_too_small")
        except LlmError as e:
            log.warning(
                "assistant turn of conversation %d: %s (%s)", self.conversation_id, e, e.code
            )
            if e.code == "cancelled":
                self._end("cancelled", content=self.partial)
            else:
                self._end("failed", content=self.partial, error_code=e.code)
        except Exception:
            log.exception("assistant turn of conversation %d failed", self.conversation_id)
            self._end("failed", error_code="failed")

    def _end(self, state: str, *, content: str | None = None, error_code: str | None = None):
        try:
            store.finish_message(
                self.conn, self.row, state, content=content or None, error_code=error_code
            )
        except sqlite3.Error:  # the row stays active until the next start marks it
            log.exception("ending assistant message %d failed", self.row)

    def _rounds(self) -> None:
        if self.client is None:
            raise _Failed("unavailable")
        first = self.conn.execute(
            "SELECT MAX(id) FROM chat_messages WHERE conversation_id = ? AND role = 'user'"
            " AND id < ?",
            (self.conversation_id, self.row),
        ).fetchone()[0]
        if first is None:
            raise ValueError("the turn has no user message")
        rounds = 0
        while True:
            if self.cancel.is_set():
                raise LlmError("cancelled", "the turn was cancelled")
            if time.monotonic() >= self.deadline:
                raise LlmError("timeout", "the turn took too long")
            if rounds >= self.settings.llm_max_tool_rounds:
                raise _Failed("too_many_steps")
            project_id, user = self._authorize()
            if not store.update_message(self.conn, self.row, state="running"):
                raise _Stop()
            completion = self._complete(project_id, first)
            content = completion.content[:MAX_CONTENT_CHARS]
            if not completion.tool_calls:
                store.finish_message(self.conn, self.row, "done", content=content)
                return
            self.row = self._run_tools(project_id, user, completion, content)
            self.partial = ""
            rounds += 1

    def _authorize(self) -> tuple[str, User]:
        """The conversation's project and its user, who must still be able to read it."""
        row = self.conn.execute(
            "SELECT project_id, user_id FROM conversations WHERE id = ?", (self.conversation_id,)
        ).fetchone()
        if row is None:
            raise _Stop()
        user = auth.get_user(self.conn, row["user_id"])
        if user is None or not can_access_project(self.conn, user, row["project_id"], "read"):
            raise _Failed("forbidden")
        return row["project_id"], user

    def _complete(self, project_id: str, first: int) -> Completion:
        rows = store.messages(self.conn, self.conversation_id)
        project = projects.require_project(self.conn, project_id)
        tools = list_tools()
        messages = build_messages(
            system_prompt(self.language, project_id, project.name),
            [m for m in rows if m.id < first],
            [m for m in rows if m.id >= first],
            budget_bytes(self.monitor.effective_context(), self.settings.llm_max_tokens, tools),
        )
        completion = self._stream(messages, tools)
        self.monitor.refresh_context()
        log.info(
            "assistant request conversation=%d request_bytes=%d prompt_tokens=%s",
            self.conversation_id,
            size(messages) + size(tools),
            completion.prompt_tokens,
        )
        return completion

    def _stream(self, messages: list[dict], tools: list[dict]) -> Completion:
        """One completion, in a thread of its own: the client may not return at the deadline
        (a server can stall before the body), so at the deadline or a cancel the thread is left
        to end by itself. The text is written to the row as it arrives."""
        pieces: list[str] = []
        lock = threading.Lock()
        done = threading.Event()
        abandoned = threading.Event()
        outcome: dict = {}

        def on_text(text: str) -> None:
            with lock:
                pieces.append(text)

        def work() -> None:
            try:
                outcome["completion"] = self.client.complete(
                    messages,
                    tools,
                    deadline=self.deadline,
                    on_text=on_text,
                    cancelled=lambda: self.cancel.is_set() or abandoned.is_set(),
                )
            except BaseException as e:  # handed to the turn
                outcome["error"] = e
            finally:
                done.set()

        threading.Thread(target=work, name="llm-completion", daemon=True).start()
        written, last_write = "", 0.0
        try:
            while True:
                finished = done.wait(_POLL_SECS)
                with lock:
                    pieces[:] = ["".join(pieces)[:MAX_CONTENT_CHARS]]
                    self.partial = pieces[0]
                if finished:
                    break
                now = time.monotonic()
                if self.partial != written and now - last_write >= WRITE_INTERVAL_SECS:
                    if not store.update_message(self.conn, self.row, content=self.partial):
                        raise _Stop()
                    written, last_write = self.partial, now
                if self.cancel.is_set():
                    raise LlmError("cancelled", "the turn was cancelled")
                if now >= self.deadline:
                    raise LlmError("timeout", "the LLM server did not answer in time")
        finally:
            abandoned.set()
        if "error" in outcome:
            raise outcome["error"]
        return outcome["completion"]

    def _run_tools(self, project_id: str, user: User, completion: Completion, content: str) -> int:
        """Run the calls, store the round (the calls, their results, a proposal) and the next
        assistant row in one transaction; the next row's id."""
        ctx = ToolContext(
            self.conn,
            self.storage,
            user,
            allow_samples=store.samples_allowed(self.conn, self.settings.llm_base_url),
            project_id=project_id,
            via="chat",
        )
        calls: list[dict] = []
        runs: list[tuple[dict | None, dict]] = []
        for n, call in enumerate(completion.tool_calls[:MAX_CALLS_KEPT]):
            args = _arguments(call.arguments)
            arguments = None if args is None else _dumps(args)
            if arguments is None:
                args, arguments = None, "{}"  # the history must hold valid JSON objects
            used = {c["id"] for c in calls}
            id_ = call.id if _CALL_ID.fullmatch(call.id) and call.id not in used else ""
            calls.append(
                {
                    "id": id_ or f"call_{self.row}_{n}",
                    "name": clean_text(call.name, _TOOL_NAME_CHARS),
                    "arguments": arguments,
                }
            )
            if n >= MAX_CALLS_PER_ROUND:
                result = TOO_MANY_CALLS
            elif args is None:
                result = BAD_ARGUMENTS
            else:
                try:
                    result = call_tool(call.name, args, ctx)
                except ToolError as e:
                    result = {"error": str(e)}
            runs.append((args, result))

        with db.immediate(self.conn):
            if not store.update_message(self.conn, self.row, content=content, tool_calls=calls):
                raise _Stop()
            proposed = False
            for call, (args, result) in zip(calls, runs, strict=True):
                if call["name"] == PROPOSE and result.get("proposal") is True:
                    result = ONE_PROPOSAL if proposed else self._propose(args, result)
                    proposed = proposed or "error" not in result
                store.add_message(
                    self.conn,
                    self.conversation_id,
                    "tool",
                    json.dumps(result, ensure_ascii=False, allow_nan=False),
                    tool_call_id=call["id"],
                    tool_name=call["name"],
                )
            if not store.finish_message(self.conn, self.row, "done"):
                raise _Stop()
            following = store.add_message(
                self.conn, self.conversation_id, "assistant", "", state="running"
            )
        return following.id

    def _propose(self, args: dict, result: dict) -> dict:
        """Store the proposal of a ``propose_training_config`` result; the result, or an error
        in its place."""
        try:
            store.add_proposal(
                self.conn,
                self.row,
                self.conversation_id,
                dataset_id=args["dataset_id"],
                config=result["config"],
                details={k: result.get(k) for k in _DETAILS},
            )
        except ValueError as e:  # say, the dataset was deleted meanwhile
            return {"error": str(e)}
        return result


def run_turn(
    db_path: Path,
    storage: Storage,
    settings: Settings,
    client: ChatClient | None,
    monitor: LlmMonitor,
    conversation_id: int,
    assistant_id: int,
    cancel: threading.Event,
    *,
    language: str,
) -> None:
    """Answer the conversation's latest user message, starting in the ``queued`` assistant row
    ``assistant_id``. It always ends that row, or the one its rounds got to (``done``,
    ``cancelled`` or ``failed`` with an ``ERROR_CODES`` code), within
    ``llm_turn_timeout_secs`` and soon after ``cancel`` is set; it does not raise."""
    deadline = time.monotonic() + settings.llm_turn_timeout_secs
    with closing(db.connect(db_path)) as conn:
        _Turn(
            conn, storage, settings, client, monitor, conversation_id, cancel, deadline, language
        ).run(assistant_id)


class TurnManager:
    """Runs turns in a pool of ``llm_max_concurrent_turns`` threads, with one chat client for
    them all. ``store.start_turn`` keeps it to one turn at a time per conversation."""

    def __init__(
        self,
        db_path: Path,
        storage: Storage,
        settings: Settings,
        monitor: LlmMonitor,
        *,
        client_factory=ChatClient.from_settings,
    ):
        self._db_path = db_path
        self._storage = storage
        self._settings = settings
        self._monitor = monitor
        self._client: ChatClient | None = client_factory(settings)
        self._pool = ThreadPoolExecutor(
            settings.llm_max_concurrent_turns, thread_name_prefix="assistant-turn"
        )
        self._lock = threading.Lock()
        self._turns: dict[int, tuple[threading.Event, Future]] = {}

    def submit(
        self,
        conn: sqlite3.Connection,
        user: User,
        project_id: str,
        conversation_id: int,
        text: str,
        *,
        language: str,
    ) -> Message:
        """Queue an answer to ``text``; the ``queued`` assistant message.

        ``ConversationNotFound`` unless it is the user's conversation in a project the user
        can read; ``LlmUnavailable`` unless the provider is ready; ``TurnBusy``,
        ``LimitReached`` and ``ValueError`` from ``store.start_turn``."""
        store.get_conversation(conn, user, project_id, conversation_id)
        if self._client is None or self._monitor.snapshot().state != "ready":
            raise LlmUnavailable()
        _, placeholder = store.start_turn(conn, conversation_id, text)
        cancel = threading.Event()
        with self._lock:
            try:
                future = self._pool.submit(
                    self._run, conversation_id, placeholder.id, cancel, language
                )
            except RuntimeError:  # shut down
                store.finish_message(conn, placeholder.id, "failed", error_code="unavailable")
                raise LlmUnavailable() from None
            self._turns[conversation_id] = (cancel, future)
        return placeholder

    def _run(self, conversation_id: int, assistant_id: int, cancel: threading.Event, language):
        try:
            run_turn(
                self._db_path,
                self._storage,
                self._settings,
                self._client,
                self._monitor,
                conversation_id,
                assistant_id,
                cancel,
                language=language,
            )
        except Exception:  # run_turn ends its rows itself; this is a database failure
            log.exception("assistant turn of conversation %d failed", conversation_id)
        finally:
            with self._lock:
                if self._turns.get(conversation_id, (None,))[0] is cancel:
                    del self._turns[conversation_id]

    def cancel(self, conversation_id: int) -> bool:
        """Stop the conversation's turn: a ``queued`` one ends ``cancelled`` at once, a running
        one at its next step with the text it has. False when no turn is active."""
        with self._lock:
            entry = self._turns.get(conversation_id)
        if entry is not None:
            entry[0].set()
        with closing(db.connect(self._db_path)) as conn:
            active = store.active_message(conn, conversation_id)
            if active is not None and active.state == "queued":
                store.finish_message(conn, active.id, "cancelled")
        return active is not None

    def shutdown(self, timeout: float = 5.0) -> None:
        """Cancel every turn and wait up to ``timeout`` seconds for them to end. Rows left
        active are marked ``interrupted`` at the next start."""
        with self._lock:
            entries = list(self._turns.values())
        for cancel, _ in entries:
            cancel.set()
        wait([future for _, future in entries], timeout=timeout)
        self._pool.shutdown(wait=False, cancel_futures=True)
        if self._client is not None:
            self._client.close()
