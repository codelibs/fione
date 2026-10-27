"""The assistant's tables: conversations, their messages, the training proposals the model
made, and the per-provider opt-in to send sample values.

A conversation is private to its creator (admins included) and is visible only while its
creator can still read the project. Only one turn runs per conversation: ``start_turn`` inserts
the user's message and a ``queued`` assistant placeholder in one transaction, and refuses while
an earlier placeholder is ``queued`` or ``running``.
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
MAX_CONVERSATIONS = 100  # per user and project
MAX_TITLE_CHARS = 80
_ACTIVE = ("queued", "running")
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
    with db.immediate(conn):
        count = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE project_id = ? AND user_id = ?",
            (project_id, user.id),
        ).fetchone()[0]
        if count >= MAX_CONVERSATIONS:
            raise LimitReached(f"at most {MAX_CONVERSATIONS} conversations per project")
        cur = conn.execute(
            "INSERT INTO conversations (project_id, user_id, title) VALUES (?, ?, ?)",
            (project_id, user.id, clean_text(title, MAX_TITLE_CHARS)),
        )
    return _conversation(
        conn.execute("SELECT * FROM conversations WHERE id = ?", (cur.lastrowid,)).fetchone()
    )


def list_conversations(conn: sqlite3.Connection, user: User, project_id: str) -> list[Conversation]:
    """The user's own conversations in the project, most recently active first; none when the
    user can no longer read the project."""
    if not can_access_project(conn, user, project_id, "read"):
        return []
    rows = conn.execute(
        "SELECT * FROM conversations WHERE project_id = ? AND user_id = ?"
        " ORDER BY updated_at DESC, id DESC",
        (project_id, user.id),
    ).fetchall()
    return [_conversation(r) for r in rows]


def get_conversation(
    conn: sqlite3.Connection, user: User, project_id: str, conversation_id: int
) -> Conversation:
    """The user's conversation in ``project_id``, if the user can read the project now."""
    row = conn.execute(
        "SELECT * FROM conversations WHERE id = ? AND project_id = ? AND user_id = ?",
        (conversation_id, project_id, user.id),
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
) -> None:
    """Set the given fields (``None`` leaves a field as it is)."""
    values = {
        "content": content,
        "tool_calls_json": None if tool_calls is None else _dumps(tool_calls),
        "state": state,
        "error_code": error_code,
    }
    changes = {column: value for column, value in values.items() if value is not None}
    if changes:
        assignments = ", ".join(f"{column} = ?" for column in changes)
        conn.execute(
            f"UPDATE chat_messages SET {assignments} WHERE id = ?", (*changes.values(), message_id)
        )


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


# --- proposals --------------------------------------------------------------


def add_proposal(
    conn: sqlite3.Connection,
    message_id: int,
    conversation_id: int,
    dataset_id: int | None,
    config: dict,
    details: dict,
) -> Proposal:
    cur = conn.execute(
        "INSERT INTO chat_proposals (message_id, conversation_id, dataset_id, config_json,"
        " details_json) VALUES (?, ?, ?, ?, ?)",
        (message_id, conversation_id, dataset_id, _dumps(config), _dumps(details)),
    )
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
    """The proposal, only through a conversation the user can see (``get_conversation``)."""
    row = conn.execute("SELECT * FROM chat_proposals WHERE id = ?", (proposal_id,)).fetchone()
    if row is None:
        raise ProposalNotFound(proposal_id)
    try:
        get_conversation(conn, user, project_id, row["conversation_id"])
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


def set_proposal_job(conn: sqlite3.Connection, proposal_id: int, job_id: int) -> None:
    conn.execute("UPDATE chat_proposals SET job_id = ? WHERE id = ?", (job_id, proposal_id))


def dismiss_proposal(conn: sqlite3.Connection, proposal_id: int, user_id: int) -> bool:
    return (
        conn.execute(
            "UPDATE chat_proposals SET state = 'dismissed', decided_by = ?,"
            " decided_at = CURRENT_TIMESTAMP WHERE id = ? AND state = 'pending'",
            (user_id, proposal_id),
        ).rowcount
        == 1
    )


# --- sample opt-ins ---------------------------------------------------------


def normal_base_url(url: str) -> str:
    """``url`` in the form opt-ins are keyed by: scheme and host in lower case, the default
    port and any trailing ``/`` removed."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if ":" in host:
        host = f"[{host}]"  # an IPv6 literal
    port = parts.port
    netloc = host if port is None or port == _DEFAULT_PORTS.get(scheme) else f"{host}:{port}"
    return f"{scheme}://{netloc}{parts.path.rstrip('/')}"


def samples_allowed(conn: sqlite3.Connection, base_url: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM llm_sample_optins WHERE base_url = ?", (normal_base_url(base_url),)
        ).fetchone()
        is not None
    )


def set_samples_allowed(
    conn: sqlite3.Connection, base_url: str, allowed: bool, user_id: int
) -> None:
    key = normal_base_url(base_url)
    if allowed:
        conn.execute(
            "INSERT INTO llm_sample_optins (base_url, enabled_by) VALUES (?, ?)"
            " ON CONFLICT(base_url) DO UPDATE SET enabled_by = excluded.enabled_by,"
            " enabled_at = CURRENT_TIMESTAMP",
            (key, user_id),
        )
    else:
        conn.execute("DELETE FROM llm_sample_optins WHERE base_url = ?", (key,))
