"""The assistant's tables: conversations, their messages, the training proposals the model
made, and the administrator's consent to a remote language model host.

A conversation is private to its creator (admins included) and is visible only while its
creator can still read the project. Only one turn runs per conversation: ``start_turn`` inserts
the user's message and a ``queued`` assistant placeholder in one transaction, and refuses while
an earlier placeholder is ``queued`` or ``running``.

A note is the assistant's one answer about one subject (a model, a failed job) in one language,
shared by the project's readers. It is held by a hidden conversation (kind ``note``) of the
member who first asked for it, which is never listed and does not count toward the limits.
"""

import json
import sqlite3
from dataclasses import dataclass
from urllib.parse import urlsplit

from fione import db
from fione.auth.roles import User, can_access_project
from fione.schema import clean_text

MAX_MESSAGE_CHARS = 4000
MAX_USER_MESSAGES = 100  # per conversation
NOTE_KINDS = ("model", "failed_job", "dataset")  # what a note can be about
MAX_CONVERSATIONS = 100  # per user and project
MAX_TITLE_CHARS = 80
TERMINAL_STATES = ("done", "failed", "cancelled")
_DEFAULT_PORTS = {"http": 80, "https": 443}


class ConversationNotFound(KeyError):
    pass


class ProposalNotFound(KeyError):
    pass


class LimitReached(ValueError):
    pass


class TurnBusy(ValueError):
    pass


@dataclass(frozen=True)
class Conversation:
    id: int
    project_id: str
    user_id: int
    title: str
    created_at: str
    updated_at: str
    kind: str = "chat"  # or "note": a hidden conversation holding a note


@dataclass(frozen=True)
class Note:
    id: int
    project_id: str
    kind: str  # what the comment is about: "model" or "failed_job" (set by the routes)
    subject_id: str
    language: str
    conversation_id: int


@dataclass(frozen=True)
class Message:
    id: int
    conversation_id: int
    role: str
    content: str
    tool_calls: list[dict] | None
    tool_call_id: str | None
    tool_name: str | None
    state: str
    error_code: str | None
    created_at: str


@dataclass(frozen=True)
class Proposal:
    id: int
    message_id: int
    conversation_id: int
    dataset_id: int | None
    config: dict
    details: dict
    state: str
    job_id: int | None


def _conversation(row: sqlite3.Row) -> Conversation:
    return Conversation(
        id=row["id"],
        project_id=row["project_id"],
        user_id=row["user_id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        kind=row["kind"],
    )


def _note(row: sqlite3.Row) -> Note:
    return Note(
        id=row["id"],
        project_id=row["project_id"],
        kind=row["kind"],
        subject_id=row["subject_id"],
        language=row["language"],
        conversation_id=row["conversation_id"],
    )


def _message(row: sqlite3.Row) -> Message:
    calls = row["tool_calls_json"]
    return Message(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=row["role"],
        content=row["content"],
        tool_calls=None if calls is None else json.loads(calls),
        tool_call_id=row["tool_call_id"],
        tool_name=row["tool_name"],
        state=row["state"],
        error_code=row["error_code"],
        created_at=row["created_at"],
    )


def _proposal(row: sqlite3.Row) -> Proposal:
    return Proposal(
        id=row["id"],
        message_id=row["message_id"],
        conversation_id=row["conversation_id"],
        dataset_id=row["dataset_id"],
        config=json.loads(row["config_json"]),
        details=json.loads(row["details_json"]),
        state=row["state"],
        job_id=row["job_id"],
    )


def _dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


# --- conversations ----------------------------------------------------------


def create_conversation(
    conn: sqlite3.Connection, user: User, project_id: str, title: str = ""
) -> Conversation:
    """A new conversation of the user in the project, which the user must be able to read
    (``ConversationNotFound`` otherwise, also for a project that does not exist)."""
    with db.immediate(conn):
        if not can_access_project(conn, user, project_id, "read"):
            raise ConversationNotFound(project_id)
        count = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE project_id = ? AND user_id = ?"
            " AND kind = 'chat'",
            (project_id, user.id),
        ).fetchone()[0]
        if count >= MAX_CONVERSATIONS:
            raise LimitReached(f"at most {MAX_CONVERSATIONS} conversations per project")
        try:
            cur = conn.execute(
                "INSERT INTO conversations (project_id, user_id, title) VALUES (?, ?, ?)",
                (project_id, user.id, clean_text(title, MAX_TITLE_CHARS)),
            )
        except sqlite3.IntegrityError:  # no such project (an admin passes the access check)
            raise ConversationNotFound(project_id) from None
    return _conversation(
        conn.execute("SELECT * FROM conversations WHERE id = ?", (cur.lastrowid,)).fetchone()
    )


def list_conversations(conn: sqlite3.Connection, user: User, project_id: str) -> list[Conversation]:
    """The user's own conversations in the project, most recently active first; none when the
    user can no longer read the project."""
    if not can_access_project(conn, user, project_id, "read"):
        return []
    rows = conn.execute(
        "SELECT * FROM conversations WHERE project_id = ? AND user_id = ? AND kind = 'chat'"
        " ORDER BY updated_at DESC, id DESC",
        (project_id, user.id),
    ).fetchall()
    return [_conversation(r) for r in rows]


def get_conversation(
    conn: sqlite3.Connection,
    user: User,
    project_id: str,
    conversation_id: int,
    kind: str | None = "chat",
) -> Conversation:
    """The user's conversation of ``kind`` (``None``: any) in ``project_id``, if the user can
    read the project now."""
    row = conn.execute(
        "SELECT * FROM conversations WHERE id = ? AND project_id = ? AND user_id = ?"
        " AND kind = COALESCE(?, kind)",
        (conversation_id, project_id, user.id, kind),
    ).fetchone()
    if row is None or not can_access_project(conn, user, project_id, "read"):
        raise ConversationNotFound(conversation_id)
    return _conversation(row)


def delete_conversation(
    conn: sqlite3.Connection, user: User, project_id: str, conversation_id: int
) -> None:
    get_conversation(conn, user, project_id, conversation_id)
    conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


# --- messages ---------------------------------------------------------------


def _insert_message(
    conn: sqlite3.Connection,
    conversation_id: int,
    role: str,
    content: str,
    tool_calls: list[dict] | None,
    tool_call_id: str | None,
    tool_name: str | None,
    state: str,
) -> Message:
    try:
        cur = conn.execute(
            "INSERT INTO chat_messages (conversation_id, role, content, tool_calls_json,"
            " tool_call_id, tool_name, state) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                conversation_id,
                role,
                content,
                None if tool_calls is None else _dumps(tool_calls),
                tool_call_id,
                tool_name,
                state,
            ),
        )
    except sqlite3.IntegrityError as e:
        if "FOREIGN KEY" in str(e):  # deleted meanwhile, say while its turn was running
            raise ConversationNotFound(conversation_id) from None
        raise ValueError("invalid message") from None
    conn.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,)
    )
    return _message(
        conn.execute("SELECT * FROM chat_messages WHERE id = ?", (cur.lastrowid,)).fetchone()
    )


def add_message(
    conn: sqlite3.Connection,
    conversation_id: int,
    role: str,
    content: str = "",
    *,
    tool_calls: list[dict] | None = None,
    tool_call_id: str | None = None,
    tool_name: str | None = None,
    state: str = "done",
) -> Message:
    return _insert_message(
        conn, conversation_id, role, content, tool_calls, tool_call_id, tool_name, state
    )


def update_message(
    conn: sqlite3.Connection,
    message_id: int,
    *,
    content: str | None = None,
    tool_calls: list[dict] | None = None,
    state: str | None = None,
    error_code: str | None = None,
) -> bool:
    """Edit a ``queued`` or ``running`` message (``None`` leaves a field as it is); false when
    nothing was changed because the message has ended (or does not exist), so a worker whose
    turn was cancelled, timed out or interrupted learns it and stops.

    The only ``state`` it sets is ``running`` (a worker starting its turn). A turn ends only
    with ``finish_message``, so an ending cannot be undone or overwritten from here."""
    if state not in (None, "running"):
        raise ValueError("update_message only sets the state 'running'; use finish_message")
    values = {
        "content": content,
        "tool_calls_json": None if tool_calls is None else _dumps(tool_calls),
        "state": state,
        "error_code": error_code,
    }
    changes = {column: value for column, value in values.items() if value is not None}
    if not changes:
        return False
    assignments = ", ".join(f"{column} = ?" for column in changes)
    cur = conn.execute(
        f"UPDATE chat_messages SET {assignments} WHERE id = ? AND state IN ('queued', 'running')",
        (*changes.values(), message_id),
    )
    return cur.rowcount == 1


def finish_message(
    conn: sqlite3.Connection,
    message_id: int,
    state: str,
    *,
    content: str | None = None,
    error_code: str | None = None,
) -> bool:
    """End a ``queued`` or ``running`` message in a terminal ``state``; true if this call did.
    Whichever ending lands first wins: a late answer cannot overwrite a cancellation, a
    timeout or an interruption, nor the other way round."""
    if state not in TERMINAL_STATES:
        raise ValueError(f"{state!r} is not a terminal state")
    sets = ["state = ?"]
    values = [state]
    for column, value in (("content", content), ("error_code", error_code)):
        if value is not None:
            sets.append(f"{column} = ?")
            values.append(value)
    cur = conn.execute(
        f"UPDATE chat_messages SET {', '.join(sets)}"
        " WHERE id = ? AND state IN ('queued', 'running')",
        (*values, message_id),
    )
    return cur.rowcount == 1


def messages(conn: sqlite3.Connection, conversation_id: int, after_id: int = 0) -> list[Message]:
    rows = conn.execute(
        "SELECT * FROM chat_messages WHERE conversation_id = ? AND id > ? ORDER BY id",
        (conversation_id, after_id),
    ).fetchall()
    return [_message(r) for r in rows]


def active_message(conn: sqlite3.Connection, conversation_id: int) -> Message | None:
    row = conn.execute(
        "SELECT * FROM chat_messages WHERE conversation_id = ? AND state IN ('queued', 'running')"
        " ORDER BY id DESC LIMIT 1",
        (conversation_id,),
    ).fetchone()
    return None if row is None else _message(row)


def start_turn(
    conn: sqlite3.Connection, conversation_id: int, text: str
) -> tuple[Message, Message]:
    """Insert the user's message and a ``queued`` assistant placeholder, atomically.

    ``TurnBusy`` while an earlier placeholder is active; ``ValueError`` for empty or too long
    text; ``LimitReached`` at ``MAX_USER_MESSAGES``.
    """
    text = text.strip()
    if not text:
        raise ValueError("the message is empty")
    if len(text) > MAX_MESSAGE_CHARS:
        raise ValueError(f"the message is longer than {MAX_MESSAGE_CHARS} characters")
    with db.immediate(conn):
        if active_message(conn, conversation_id) is not None:
            raise TurnBusy("an answer is still being written")
        used = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE conversation_id = ? AND role = 'user'",
            (conversation_id,),
        ).fetchone()[0]
        if used >= MAX_USER_MESSAGES:
            raise LimitReached(f"at most {MAX_USER_MESSAGES} messages per conversation")
        return _insert_turn(conn, conversation_id, text)


def _insert_turn(conn: sqlite3.Connection, conversation_id: int, text: str):
    user = _insert_message(conn, conversation_id, "user", text, None, None, None, "done")
    placeholder = _insert_message(
        conn, conversation_id, "assistant", "", None, None, None, "queued"
    )
    return user, placeholder


def fail_interrupted(conn: sqlite3.Connection) -> int:
    """Mark the messages left ``queued`` or ``running`` (by a restart) as failed."""
    return conn.execute(
        "UPDATE chat_messages SET state = 'failed', error_code = 'interrupted'"
        " WHERE state IN ('queued', 'running')"
    ).rowcount


# --- notes ------------------------------------------------------------------


def get_note(
    conn: sqlite3.Connection, project_id: str, kind: str, subject_id: str, language: str
) -> Note | None:
    row = conn.execute(
        "SELECT * FROM assistant_notes WHERE project_id = ? AND kind = ? AND subject_id = ?"
        " AND language = ?",
        (project_id, kind, subject_id, language),
    ).fetchone()
    return None if row is None else _note(row)


def create_note(
    conn: sqlite3.Connection,
    user: User,
    project_id: str,
    kind: str,
    subject_id: str,
    language: str,
    text: str,
) -> tuple[Note, Message | None]:
    """The note, with its hidden conversation of ``user`` holding ``text`` as the user's
    message and a ``queued`` assistant placeholder, all in one transaction; or the note someone
    made first, with no placeholder. ``ConversationNotFound`` unless the user can read the
    project; ``ValueError`` for an unknown kind."""
    if kind not in NOTE_KINDS:
        raise ValueError(f"unknown note kind {kind!r}")
    with db.immediate(conn):
        if not can_access_project(conn, user, project_id, "read"):
            raise ConversationNotFound(project_id)
        existing = get_note(conn, project_id, kind, subject_id, language)
        if existing is not None:
            return existing, None
        try:
            conversation_id = conn.execute(
                "INSERT INTO conversations (project_id, user_id, kind) VALUES (?, ?, 'note')",
                (project_id, user.id),
            ).lastrowid
            note_id = conn.execute(
                "INSERT INTO assistant_notes (project_id, kind, subject_id, language,"
                " conversation_id) VALUES (?, ?, ?, ?, ?)",
                (project_id, kind, subject_id, language, conversation_id),
            ).lastrowid
        except sqlite3.IntegrityError:
            raise ConversationNotFound(project_id) from None  # no such project
        _, placeholder = _insert_turn(conn, conversation_id, text)
    row = conn.execute("SELECT * FROM assistant_notes WHERE id = ?", (note_id,)).fetchone()
    return _note(row), placeholder


def note_of(conn: sqlite3.Connection, conversation_id: int) -> Note | None:
    """The note a conversation holds, if it is a note's."""
    row = conn.execute(
        "SELECT * FROM assistant_notes WHERE conversation_id = ?", (conversation_id,)
    ).fetchone()
    return None if row is None else _note(row)


def note_answer(conn: sqlite3.Connection, conversation_id: int) -> Message | None:
    """The last assistant message of the first turn of a note's conversation, whoever owns it:
    the callers check that the reader can read the project. Nothing written after that turn
    can change the shared text."""
    row = conn.execute(
        "SELECT * FROM chat_messages WHERE conversation_id = ? AND role = 'assistant'"
        " AND id < COALESCE((SELECT id FROM chat_messages WHERE conversation_id = ?"
        " AND role = 'user' ORDER BY id LIMIT 1 OFFSET 1), 9223372036854775807)"
        " ORDER BY id DESC LIMIT 1",
        (conversation_id, conversation_id),
    ).fetchone()
    return None if row is None else _message(row)


def delete_note(conn: sqlite3.Connection, note: Note) -> None:
    """Remove the note with its conversation (a later ``create_note`` writes a new one)."""
    conn.execute("DELETE FROM conversations WHERE id = ?", (note.conversation_id,))


# --- proposals --------------------------------------------------------------


def add_proposal(
    conn: sqlite3.Connection,
    message_id: int,
    conversation_id: int,
    dataset_id: int | None,
    config: dict,
    details: dict,
) -> Proposal:
    """Attach a proposal to an assistant message of the conversation (``ValueError`` for any
    other message, or one that has a proposal already)."""
    message = conn.execute(
        "SELECT conversation_id, role FROM chat_messages WHERE id = ?", (message_id,)
    ).fetchone()
    if message is None or message["conversation_id"] != conversation_id:
        raise ValueError("no such message in the conversation")
    if message["role"] != "assistant":
        raise ValueError("only an assistant message carries a proposal")
    try:
        cur = conn.execute(
            "INSERT INTO chat_proposals (message_id, conversation_id, dataset_id, config_json,"
            " details_json) VALUES (?, ?, ?, ?, ?)",
            (message_id, conversation_id, dataset_id, _dumps(config), _dumps(details)),
        )
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e):
            raise ValueError("the message has a proposal already") from None
        if (
            dataset_id is not None
            and not conn.execute("SELECT 1 FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        ):
            raise ValueError("no such dataset") from None
        raise ValueError("the message no longer exists") from None
    return _proposal(
        conn.execute("SELECT * FROM chat_proposals WHERE id = ?", (cur.lastrowid,)).fetchone()
    )


def proposals_for(conn: sqlite3.Connection, conversation_id: int) -> dict[int, Proposal]:
    """The conversation's proposals, keyed by the id of the message that carries each."""
    rows = conn.execute(
        "SELECT * FROM chat_proposals WHERE conversation_id = ? ORDER BY id", (conversation_id,)
    ).fetchall()
    return {r["message_id"]: _proposal(r) for r in rows}


def get_proposal(
    conn: sqlite3.Connection, user: User, project_id: str, proposal_id: int
) -> Proposal:
    """The proposal, only through a conversation the user can see (``get_conversation``),
    a note's included."""
    row = conn.execute("SELECT * FROM chat_proposals WHERE id = ?", (proposal_id,)).fetchone()
    if row is None:
        raise ProposalNotFound(proposal_id)
    try:
        get_conversation(conn, user, project_id, row["conversation_id"], kind=None)
    except ConversationNotFound:
        raise ProposalNotFound(proposal_id) from None
    return _proposal(row)


def claim_proposal(conn: sqlite3.Connection, proposal_id: int, user_id: int) -> bool:
    """Take a pending proposal for confirming; true for exactly one caller."""
    return (
        conn.execute(
            "UPDATE chat_proposals SET state = 'confirmed', decided_by = ?,"
            " decided_at = CURRENT_TIMESTAMP WHERE id = ? AND state = 'pending'",
            (user_id, proposal_id),
        ).rowcount
        == 1
    )


def release_proposal(conn: sqlite3.Connection, proposal_id: int) -> None:
    """Give a claimed proposal back (submitting its job failed)."""
    conn.execute(
        "UPDATE chat_proposals SET state = 'pending', decided_by = NULL, decided_at = NULL"
        " WHERE id = ? AND state = 'confirmed' AND job_id IS NULL",
        (proposal_id,),
    )


def set_proposal_job(conn: sqlite3.Connection, proposal_id: int, job_id: int) -> bool:
    """Record the job of a claimed proposal, once; true if this call did."""
    return (
        conn.execute(
            "UPDATE chat_proposals SET job_id = ? WHERE id = ? AND state = 'confirmed'"
            " AND job_id IS NULL",
            (job_id, proposal_id),
        ).rowcount
        == 1
    )


def dismiss_proposal(conn: sqlite3.Connection, proposal_id: int, user_id: int) -> bool:
    return (
        conn.execute(
            "UPDATE chat_proposals SET state = 'dismissed', decided_by = ?,"
            " decided_at = CURRENT_TIMESTAMP WHERE id = ? AND state = 'pending'",
            (user_id, proposal_id),
        ).rowcount
        == 1
    )


# --- consent keys -------------------------------------------------------------


def normal_base_url(url: str) -> str:
    """``url`` in the form consents are keyed by: scheme and host in lower case, the default
    port and any trailing ``/`` removed. ``ValueError`` unless it is an http(s) URL with a host."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if ":" in host:
        host = f"[{host}]"  # an IPv6 literal
    if scheme not in _DEFAULT_PORTS or not host:
        raise ValueError("a base URL is http(s)://host[:port][/path]")
    port = parts.port
    netloc = host if port is None or port == _DEFAULT_PORTS.get(scheme) else f"{host}:{port}"
    return f"{scheme}://{netloc}{parts.path.rstrip('/')}"


# --- consent for remote language models --------------------------------------


def _consent_host(base_url: str) -> str:
    """The scheme, host and port of ``base_url``, which with the provider is what a consent
    covers (``ValueError`` for a URL that is not an http(s) URL with a host)."""
    parts = urlsplit(normal_base_url(base_url))
    return f"{parts.scheme}://{parts.netloc}"


def consent_needed(provider: str, base_url: str) -> bool:
    """Whether sending to ``base_url`` needs an administrator's consent: always for Claude (its
    data reaches Anthropic even through a gateway next to Fione), and for any Ollama host that
    is not local."""
    from fione.assistant.provider import is_local_url  # provider imports this module

    return provider == "claude" or not is_local_url(base_url)


def has_consent(conn: sqlite3.Connection, base_url: str, *, provider: str) -> bool:
    """Whether data may go to ``base_url``: without ``consent_needed`` at once, else only with
    an administrator's recorded consent for its host and ``provider``. A URL that is not usable
    is never consented."""
    try:
        host = _consent_host(base_url)
    except ValueError:
        return False
    if not consent_needed(provider, base_url):
        return True
    row = conn.execute(
        "SELECT 1 FROM llm_consents WHERE host = ? AND provider = ?", (host, provider)
    ).fetchone()
    return row is not None


def record_consent(
    conn: sqlite3.Connection, user: User, *, provider: str, model: str, base_url: str
) -> None:
    """Record ``user``'s consent for the host of ``base_url`` and ``provider``. A host has one
    record: a new consent for it replaces the old one, which a change of provider needs."""
    conn.execute(
        "INSERT INTO llm_consents (host, provider, model, consented_by) VALUES (?, ?, ?, ?)"
        " ON CONFLICT(host) DO UPDATE SET provider = excluded.provider, model = excluded.model,"
        " consented_by = excluded.consented_by, consented_at = CURRENT_TIMESTAMP",
        (_consent_host(base_url), provider, model, user.id),
    )
