"""Conversations, messages, proposals and the per-provider sample opt-ins."""

import sqlite3

import pytest

from fione import db
from fione.assistant import store
from fione.assistant.store import (
    ConversationNotFound,
    LimitReached,
    ProposalNotFound,
    TurnBusy,
)
from fione.auth import service as auth
from fione.auth.roles import ProjectAccess, Role
from fione.projects import service as projects
from fione.storage import LocalStorage

TABLES = ("conversations", "chat_messages", "chat_proposals")


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "fione.db")
    db.migrate(c)
    yield c
    c.close()


@pytest.fixture
def owner(conn):
    return auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR)


@pytest.fixture
def member(conn):
    return auth.create_user(conn, "member", "pw-member-1", Role.EDITOR)


@pytest.fixture
def admin(conn):
    return auth.create_user(conn, "root", "pw-admin-1", Role.ADMIN)


@pytest.fixture
def project(conn, owner, member):
    created = projects.create_project(conn, owner, "chat")
    projects.share_project(conn, owner, created.id, "member", ProjectAccess.EDITOR)
    return created


@pytest.fixture
def conversation(conn, owner, project):
    return store.create_conversation(conn, owner, project.id, "First")


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_migration_adds_the_tables(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "old.db")
    first = next(i for i, sql in enumerate(db.MIGRATIONS) if "CREATE TABLE conversations" in sql)
    entry = db.MIGRATIONS[first]
    assert all(f"CREATE TABLE {t}" in entry for t in (*TABLES, "llm_sample_optins"))
    with monkeypatch.context() as m:
        m.setattr(db, "MIGRATIONS", db.MIGRATIONS[:first])
        db.migrate(conn)
    names = "('conversations', 'chat_messages', 'chat_proposals', 'llm_sample_optins')"
    query = f"SELECT name FROM sqlite_master WHERE type = 'table' AND name IN {names}"
    assert conn.execute(query).fetchall() == []
    assert db.migrate(conn) == len(db.MIGRATIONS)
    assert len(conn.execute(query).fetchall()) == 4
    indexes = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert indexes >= {
        "conversations_project_user",
        "conversations_user",
        "chat_messages_conversation",
        "chat_proposals_conversation",
    }
    conn.close()


def test_conversations_are_private(conn, owner, member, admin, project, conversation):
    for other in (member, admin):
        with pytest.raises(ConversationNotFound):
            store.get_conversation(conn, other, project.id, conversation.id)
        assert store.list_conversations(conn, other, project.id) == []
        with pytest.raises(ConversationNotFound):
            store.delete_conversation(conn, other, project.id, conversation.id)
    assert store.get_conversation(conn, owner, project.id, conversation.id) == conversation
    assert store.list_conversations(conn, owner, project.id) == [conversation]
    other_project = projects.create_project(conn, owner, "other")
    with pytest.raises(ConversationNotFound):  # the conversation is in another project
        store.get_conversation(conn, owner, other_project.id, conversation.id)
    with pytest.raises(ConversationNotFound):
        store.get_conversation(conn, owner, project.id, 9999)


def test_conversation_titles_are_cleaned_and_listed_newest_first(conn, owner, project):
    first = store.create_conversation(conn, owner, project.id, "a\n<b>x</b>\t" + "y" * 200)
    assert first.title.startswith("a <b>x</b> y") and len(first.title) <= 80
    second = store.create_conversation(conn, owner, project.id)
    assert second.title == ""
    conn.execute(
        "UPDATE conversations SET updated_at = '2000-01-01 00:00:00' WHERE id = ?", (second.id,)
    )
    assert [c.id for c in store.list_conversations(conn, owner, project.id)] == [
        first.id,
        second.id,
    ]
    store.add_message(conn, second.id, "user", "hi")  # touches updated_at
    assert [c.id for c in store.list_conversations(conn, owner, project.id)] == [
        second.id,
        first.id,
    ]


def test_conversations_are_limited_per_user_and_project(conn, owner, member, project, monkeypatch):
    monkeypatch.setattr(store, "MAX_CONVERSATIONS", 2)
    store.create_conversation(conn, owner, project.id)
    store.create_conversation(conn, owner, project.id)
    with pytest.raises(LimitReached):
        store.create_conversation(conn, owner, project.id)
    store.create_conversation(conn, member, project.id)  # another user's count
    store.create_conversation(conn, owner, projects.create_project(conn, owner, "p2").id)


def test_revoked_share_hides_the_conversation(conn, owner, member, project):
    mine = store.create_conversation(conn, member, project.id)
    assert store.get_conversation(conn, member, project.id, mine.id) == mine
    projects.unshare_project(conn, owner, project.id, "member")
    with pytest.raises(ConversationNotFound):
        store.get_conversation(conn, member, project.id, mine.id)
    assert store.list_conversations(conn, member, project.id) == []
    assert count(conn, "conversations") == 1  # hidden, not deleted


def test_project_deletion_cascades(conn, owner, project, conversation, tmp_path):
    message = store.add_message(conn, conversation.id, "assistant", "x")
    store.add_proposal(conn, message.id, conversation.id, None, {"target": "y"}, {})
    assert all(count(conn, t) for t in TABLES)
    projects.delete_project(conn, LocalStorage(tmp_path / "s"), owner, project.id)
    assert [count(conn, t) for t in TABLES] == [0, 0, 0]


def test_deleting_a_conversation_removes_its_messages_and_proposals(
    conn, owner, project, conversation
):
    message = store.add_message(conn, conversation.id, "assistant", "x")
    store.add_proposal(conn, message.id, conversation.id, None, {}, {})
    store.delete_conversation(conn, owner, project.id, conversation.id)
    assert [count(conn, t) for t in TABLES] == [0, 0, 0]


def test_messages_round_trip(conn, conversation):
    calls = [
        {"id": "c1", "type": "function", "function": {"name": "list_projects", "arguments": "{}"}}
    ]
    user = store.add_message(conn, conversation.id, "user", "hello 日本語")
    call = store.add_message(conn, conversation.id, "assistant", tool_calls=calls)
    tool = store.add_message(
        conn,
        conversation.id,
        "tool",
        '{"projects": []}',
        tool_call_id="c1",
        tool_name="list_projects",
    )
    assert (user.role, user.content, user.state, user.tool_calls) == (
        "user",
        "hello 日本語",
        "done",
        None,
    )
    assert call.tool_calls == calls
    assert (tool.tool_call_id, tool.tool_name) == ("c1", "list_projects")
    assert store.messages(conn, conversation.id) == [user, call, tool]
    assert store.messages(conn, conversation.id, after_id=call.id) == [tool]
    store.update_message(conn, user.id, content="changed", state="failed", error_code="boom")
    store.update_message(conn, call.id, tool_calls=[])
    [updated, again, _] = store.messages(conn, conversation.id)
    assert (updated.content, updated.state, updated.error_code) == ("changed", "failed", "boom")
    assert again.tool_calls == [] and again.content == ""
    with pytest.raises(ValueError):
        store.add_message(conn, conversation.id, "system", "x")
    with pytest.raises(ConversationNotFound):
        store.add_message(conn, 9999, "user", "x")


def test_start_turn_is_one_at_a_time(conn, conversation):
    user, placeholder = store.start_turn(conn, conversation.id, "  What is in it?  ")
    assert (user.role, user.content, user.state) == ("user", "What is in it?", "done")
    assert (placeholder.role, placeholder.content, placeholder.state) == ("assistant", "", "queued")
    assert store.active_message(conn, conversation.id) == placeholder
    with pytest.raises(TurnBusy):
        store.start_turn(conn, conversation.id, "again")
    store.update_message(conn, placeholder.id, state="running")
    with pytest.raises(TurnBusy):
        store.start_turn(conn, conversation.id, "again")
    assert count(conn, "chat_messages") == 2  # nothing was left behind by the refusals
    store.update_message(conn, placeholder.id, content="answer", state="done")
    assert store.active_message(conn, conversation.id) is None
    store.start_turn(conn, conversation.id, "next")

    owner = auth.get_user(conn, conversation.user_id)
    other = store.create_conversation(conn, owner, conversation.project_id)
    store.start_turn(conn, other.id, "independent")  # busy is per conversation


def test_start_turn_checks_the_text_and_the_limit(conn, conversation, monkeypatch):
    for bad in ("", "   \n\t", "x" * 4001):
        with pytest.raises(ValueError):
            store.start_turn(conn, conversation.id, bad)
    assert count(conn, "chat_messages") == 0
    monkeypatch.setattr(store, "MAX_USER_MESSAGES", 2)
    for text in ("x" * 4000, "second"):
        _, placeholder = store.start_turn(conn, conversation.id, text)
        store.update_message(conn, placeholder.id, state="done")
    with pytest.raises(LimitReached):
        store.start_turn(conn, conversation.id, "third")
    with pytest.raises(ConversationNotFound):
        store.start_turn(conn, 9999, "x")


def test_fail_interrupted(conn, conversation):
    _, queued = store.start_turn(conn, conversation.id, "one")
    store.update_message(conn, queued.id, state="done")
    _, running = store.start_turn(conn, conversation.id, "two")
    store.update_message(conn, running.id, state="running")
    assert store.fail_interrupted(conn) == 1
    failed = store.messages(conn, conversation.id, after_id=running.id - 1)[0]
    assert (failed.state, failed.error_code) == ("failed", "interrupted")
    assert store.active_message(conn, conversation.id) is None
    assert store.fail_interrupted(conn) == 0
    _, queued = store.start_turn(conn, conversation.id, "three")
    assert store.fail_interrupted(conn) == 1


def make_proposal(conn, conversation):
    message = store.add_message(conn, conversation.id, "assistant", "see below")
    return store.add_proposal(
        conn, message.id, conversation.id, None, {"target": "y"}, {"warnings": []}
    )


def test_proposals_are_stored_and_found_through_their_conversation(
    conn, owner, member, project, conversation
):
    proposal = make_proposal(conn, conversation)
    assert (proposal.state, proposal.job_id, proposal.config) == ("pending", None, {"target": "y"})
    assert proposal.details == {"warnings": []}
    assert store.proposals_for(conn, conversation.id) == {proposal.message_id: proposal}
    assert store.get_proposal(conn, owner, project.id, proposal.id) == proposal
    with pytest.raises(ProposalNotFound):
        store.get_proposal(conn, member, project.id, proposal.id)
    with pytest.raises(ProposalNotFound):
        store.get_proposal(conn, owner, project.id, 9999)

    theirs = store.create_conversation(conn, member, project.id)
    shared = store.add_proposal(
        conn, store.add_message(conn, theirs.id, "assistant").id, theirs.id, None, {}, {}
    )
    assert store.get_proposal(conn, member, project.id, shared.id) == shared
    projects.unshare_project(conn, owner, project.id, "member")
    with pytest.raises(ProposalNotFound):  # hidden with the conversation
        store.get_proposal(conn, member, project.id, shared.id)


def test_claim_proposal_is_single_shot(conn, owner, conversation):
    proposal = make_proposal(conn, conversation)
    assert store.claim_proposal(conn, proposal.id, owner.id) is True
    assert store.claim_proposal(conn, proposal.id, owner.id) is False
    row = conn.execute("SELECT state, decided_by, decided_at FROM chat_proposals").fetchone()
    assert (row["state"], row["decided_by"]) == ("confirmed", owner.id) and row["decided_at"]
    assert store.dismiss_proposal(conn, proposal.id, owner.id) is False
    store.release_proposal(conn, proposal.id)
    row = conn.execute("SELECT state, decided_by, decided_at FROM chat_proposals").fetchone()
    assert tuple(row) == ("pending", None, None)
    assert store.claim_proposal(conn, proposal.id, owner.id) is True


def test_proposal_job_and_dismissal(conn, owner, conversation):
    from fione.jobs import store as jobs

    proposal = make_proposal(conn, conversation)
    job = jobs.enqueue(conn, "automl", conversation.project_id, owner.id, {})
    store.claim_proposal(conn, proposal.id, owner.id)
    store.set_proposal_job(conn, proposal.id, job.id)
    stored = store.proposals_for(conn, conversation.id)[proposal.message_id]
    assert (stored.state, stored.job_id) == ("confirmed", job.id)

    other = make_proposal(conn, conversation)
    assert store.dismiss_proposal(conn, other.id, owner.id) is True
    assert store.dismiss_proposal(conn, other.id, owner.id) is False
    assert store.claim_proposal(conn, other.id, owner.id) is False
    assert store.proposals_for(conn, conversation.id)[other.message_id].state == "dismissed"


def test_a_deleted_dataset_leaves_the_proposal_without_one(
    conn, owner, project, conversation, tmp_path
):
    import pandas as pd

    from fione.projects import ingest
    from fione.projects.service import DatasetType

    storage = LocalStorage(tmp_path / "s")
    dataset = ingest.ingest_batches(
        storage, conn, project.id, "d", DatasetType.TRAIN, [pd.DataFrame({"x": [1, 2]})]
    )
    message = store.add_message(conn, conversation.id, "assistant")
    proposal = store.add_proposal(conn, message.id, conversation.id, dataset.id, {}, {})
    assert proposal.dataset_id == dataset.id
    projects.delete_dataset(conn, storage, dataset.id)
    assert store.proposals_for(conn, conversation.id)[message.id].dataset_id is None


def test_optin_is_per_normalized_base_url(conn, owner):
    assert store.normal_base_url("HTTP://Host:80/v1/") == "http://host/v1"
    assert store.normal_base_url("https://Host:443") == "https://host"
    assert store.normal_base_url("http://[::1]:11434/v1") == "http://[::1]:11434/v1"
    assert not store.samples_allowed(conn, "http://host/v1")
    store.set_samples_allowed(conn, "HTTP://Host:80/v1/", True, owner.id)
    assert store.samples_allowed(conn, "http://host/v1")
    assert not store.samples_allowed(conn, "http://host:8080/v1")
    assert not store.samples_allowed(conn, "https://host/v1")
    assert not store.samples_allowed(conn, "http://host/v2")
    store.set_samples_allowed(conn, "http://host/v1", True, owner.id)  # again: still one row
    assert conn.execute("SELECT COUNT(*) FROM llm_sample_optins").fetchone()[0] == 1
    store.set_samples_allowed(conn, "http://HOST/v1/", False, owner.id)
    assert not store.samples_allowed(conn, "http://host/v1")


def test_deleting_the_user_who_enabled_samples_keeps_the_opt_in(conn):
    user = auth.create_user(conn, "tmp", "pw-tmp-12345", Role.ADMIN)
    auth.create_user(conn, "keep", "pw-keep-1234", Role.ADMIN)
    store.set_samples_allowed(conn, "http://host/v1", True, user.id)
    auth.delete_user(conn, user.id)
    assert store.samples_allowed(conn, "http://host/v1")


def test_creating_a_conversation_needs_read_access(conn, owner, admin, project):
    stranger = auth.create_user(conn, "stranger", "pw-stranger-1", Role.EDITOR)
    with pytest.raises(ConversationNotFound):
        store.create_conversation(conn, stranger, project.id)
    with pytest.raises(ConversationNotFound):
        store.create_conversation(
            conn, admin, "no-such-project"
        )  # an admin passes the access check
    assert count(conn, "conversations") == 0
    assert store.create_conversation(conn, admin, project.id).user_id == admin.id


def test_finish_message_lets_the_first_terminal_write_win(conn, conversation):
    _, placeholder = store.start_turn(conn, conversation.id, "q")
    assert store.finish_message(conn, placeholder.id, "cancelled", content="part") is True
    assert store.finish_message(conn, placeholder.id, "done", content="late answer") is False
    assert store.finish_message(conn, placeholder.id, "failed", error_code="timeout") is False
    [_, message] = store.messages(conn, conversation.id)
    assert (message.state, message.content, message.error_code) == ("cancelled", "part", None)

    _, running = store.start_turn(conn, conversation.id, "q2")
    store.update_message(conn, running.id, state="running")
    assert store.finish_message(conn, running.id, "failed", error_code="timeout") is True
    assert store.finish_message(conn, running.id, "done", content="x") is False
    assert store.messages(conn, conversation.id, after_id=running.id - 1)[0].error_code == "timeout"

    done = store.add_message(conn, conversation.id, "assistant", "fine")
    assert store.finish_message(conn, done.id, "cancelled") is False  # a done message stays
    assert store.finish_message(conn, 9999, "done") is False
    for state in ("queued", "running", "nonsense"):
        _, fresh = store.start_turn(conn, conversation.id, "q3")
        with pytest.raises(ValueError):
            store.finish_message(conn, fresh.id, state)
        store.finish_message(conn, fresh.id, "done")


def test_update_message_refuses_an_invalid_state(conn, conversation):
    message = store.add_message(conn, conversation.id, "assistant", "x")
    with pytest.raises(ValueError):
        store.update_message(conn, message.id, state="nonsense")


def test_release_proposal_only_reopens_a_claimed_proposal_without_a_job(conn, owner, conversation):
    from fione.jobs import store as jobs

    def state(proposal):
        row = conn.execute("SELECT state, job_id FROM chat_proposals WHERE id = ?", (proposal.id,))
        return tuple(row.fetchone())

    started = make_proposal(conn, conversation)
    job = jobs.enqueue(conn, "automl", conversation.project_id, owner.id, {})
    store.claim_proposal(conn, started.id, owner.id)
    assert store.set_proposal_job(conn, started.id, job.id) is True
    store.release_proposal(conn, started.id)
    assert state(started) == ("confirmed", job.id)  # a job is running for it

    pending = make_proposal(conn, conversation)
    store.release_proposal(conn, pending.id)
    assert state(pending) == ("pending", None)

    dismissed = make_proposal(conn, conversation)
    store.dismiss_proposal(conn, dismissed.id, owner.id)
    store.release_proposal(conn, dismissed.id)
    assert state(dismissed) == ("dismissed", None)  # a dismissal is final
    assert store.claim_proposal(conn, dismissed.id, owner.id) is False


def test_set_proposal_job_only_after_a_claim_and_only_once(conn, owner, conversation):
    from fione.jobs import store as jobs

    job = jobs.enqueue(conn, "automl", conversation.project_id, owner.id, {})
    second = jobs.enqueue(conn, "automl", conversation.project_id, owner.id, {})
    proposal = make_proposal(conn, conversation)
    assert store.set_proposal_job(conn, proposal.id, job.id) is False  # still pending
    store.claim_proposal(conn, proposal.id, owner.id)
    assert store.set_proposal_job(conn, proposal.id, job.id) is True
    assert store.set_proposal_job(conn, proposal.id, second.id) is False
    stored = store.proposals_for(conn, conversation.id)[proposal.message_id]
    assert stored.job_id == job.id

    dismissed = make_proposal(conn, conversation)
    store.dismiss_proposal(conn, dismissed.id, owner.id)
    assert store.set_proposal_job(conn, dismissed.id, second.id) is False


def test_add_proposal_checks_its_message(conn, owner, project, conversation):
    other = store.create_conversation(conn, owner, project.id)
    reply = store.add_message(conn, conversation.id, "assistant", "x")
    with pytest.raises(ValueError):
        store.add_proposal(conn, 9999, conversation.id, None, {}, {})
    with pytest.raises(ValueError):  # the message is in another conversation
        store.add_proposal(conn, reply.id, other.id, None, {}, {})
    asked = store.add_message(conn, conversation.id, "user", "x")
    with pytest.raises(ValueError):  # only an assistant message carries a proposal
        store.add_proposal(conn, asked.id, conversation.id, None, {}, {})
    store.add_proposal(conn, reply.id, conversation.id, None, {}, {})
    with pytest.raises(ValueError):  # one proposal per message
        store.add_proposal(conn, reply.id, conversation.id, None, {}, {})
    assert count(conn, "chat_proposals") == 1


@pytest.mark.parametrize("url", ["", "host", "ftp://host/v1", "http://", "//host/v1", "http:///v1"])
def test_an_unusable_base_url_is_never_allowed(conn, owner, url):
    with pytest.raises(ValueError):
        store.normal_base_url(url)
    assert store.samples_allowed(conn, url) is False
    with pytest.raises(ValueError):
        store.set_samples_allowed(conn, url, True, owner.id)
    assert count(conn, "llm_sample_optins") == 0


def test_the_write_lock_is_held_between_the_check_and_the_insert(
    conn, owner, project, conversation, tmp_path, monkeypatch
):
    other = db.connect(tmp_path / "fione.db")
    other.execute("PRAGMA busy_timeout=50")
    refusals = []

    def probe():
        try:
            other.execute("INSERT INTO llm_sample_optins (base_url) VALUES ('http://probe')")
        except sqlite3.OperationalError as e:
            refusals.append(str(e))

    real_active = store.active_message
    real_access = store.can_access_project

    def active(*args):
        probe()
        return real_active(*args)

    def access(*args):
        probe()
        return real_access(*args)

    monkeypatch.setattr(store, "active_message", active)
    monkeypatch.setattr(store, "can_access_project", access)
    store.start_turn(conn, conversation.id, "q")
    store.create_conversation(conn, owner, project.id)
    assert refusals == ["database is locked"] * 2
    other.close()


def test_deleting_a_user_removes_their_conversations(conn, owner, member, project):
    mine = store.create_conversation(conn, member, project.id)
    reply = store.add_message(conn, mine.id, "assistant", "x")
    store.add_proposal(conn, reply.id, mine.id, None, {}, {})
    kept = store.create_conversation(conn, owner, project.id)
    auth.delete_user(conn, member.id)
    assert [count(conn, t) for t in TABLES] == [1, 0, 0]
    assert conn.execute("SELECT id FROM conversations").fetchone()["id"] == kept.id
