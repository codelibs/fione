"""The assistant chat page against a fake LLM: sending and polling, escaping, who may see
which conversation, the refusals of a send, the provider's state and the entry links."""

import re
import time
from contextlib import closing

import pytest
from markupsafe import escape

from api_helpers import connect
from fione import i18n
from fione.assistant import store
from fione.assistant.provider import LlmMonitor, LlmStatus
from fione.assistant.turns import ERROR_CODES, TooManyTurns, TurnManager
from fione.auth import service as auth_service
from fione.jobs import store as jobs
from fione.jobs.store import JobStatus
from fione.tools import list_tools
from fione.web.headers import CONTENT_SECURITY_POLICY
from web_helpers import make_world

STOP_POLLING = 286
LLM_STATES = (
    "checking", "unreachable", "missing", "pulling", "consent_required", "ready", "error"
)  # fmt: skip
NOT_READY = tuple(s for s in LLM_STATES if s != "ready")
SETUP = "/admin/setup/assistant"
XSS = "<img src=x onerror=alert(1)>"


class StubMonitor:
    """A monitor with a status chosen by the test, for the page and the turn manager."""

    def __init__(self, **status):
        values = dict(
            state="ready", model="m", local=True, host="127.0.0.1:1", completed=None,
            total=None, error_code=None, server_context=None,
        )  # fmt: skip
        self.status = LlmStatus(**{**values, **status})

    def start(self):
        pass

    def stop(self):
        pass

    def snapshot(self):
        return self.status

    def pull_now(self):
        return True

    def effective_context(self):
        return 16384

    def context_known(self):
        return True

    def refresh_context(self):
        pass


def use_monitor(client, **status):
    """Show and decide with ``status``: the page reads the monitor, ``submit`` its own."""
    state = client.app.state
    state.llm_monitor = StubMonitor(**status)
    state.turns.shutdown()
    state.turns = TurnManager(state.db_path, state.storage, state.settings, state.llm_monitor)


@pytest.fixture
def chat(make_client, fake_llm):
    """A world whose app talks to a ready fake LLM, with ``ed`` signed in."""
    fake = fake_llm()
    world = make_world(make_client(llm_base_url=fake.url, llm_provider="ollama"))
    world.fake = fake
    world.csrf = world.login("ed")
    return world


def shown(key, **values) -> str:
    """The English text of ``key`` as the escaped page holds it."""
    return str(escape(i18n.t(key, "en", **values)))


def page_of(world, query=""):
    return world.client.get(f"/projects/{world.p}/assistant{query}")


def new_conversation(world, username="ed", project=None) -> int:
    with closing(connect(world.client)) as conn:
        user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()[0]
        user = auth_service.get_user(conn, user)
        conversation = store.create_conversation(conn, user, project or world.p)
    return conversation.id


def send(world, cid, text="hi", **headers):
    return world.client.post(
        f"/projects/{world.p}/assistant/c/{cid}/messages",
        data={"csrf_token": world.csrf, "text": text},
        headers=headers,
        follow_redirects=False,
    )


def poll(world, cid, timeout=10.0):
    """Poll the thread as HTMX does until it says 286; the last fragment."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        r = world.client.get(
            f"/projects/{world.p}/assistant/c/{cid}/thread", headers={"HX-Request": "true"}
        )
        if r.status_code == STOP_POLLING:
            return r
        assert r.status_code == 200, r.text
        assert 'hx-trigger="every 1s"' in r.text
        time.sleep(0.05)
    raise AssertionError("the thread kept polling")


def textarea(html: str) -> str:
    match = re.search(r"<textarea[^>]*>(.*?)</textarea>", html, re.S)
    assert match, "no textarea"
    return match.group(1)


def test_send_and_poll_until_done(chat):
    chat.fake.script = [{"text": "\n\nHello from the assistant", "chunks": 3}]
    cid = new_conversation(chat)
    r = send(chat, cid)
    assert r.status_code == 303
    assert r.headers["location"] == f"/projects/{chat.p}/assistant?c={cid}"
    final = poll(chat, cid)
    assert "Hello from the assistant" in final.text
    assert "hx-trigger" not in final.text
    assert re.search(
        r'class="chat-text"[^>]*>Hello from the assistant', final.text
    )  # no blank lines
    page = page_of(chat, f"?c={cid}").text
    assert "Hello from the assistant" in page and ">hi<" in page


def test_send_with_htmx_answers_with_the_thread(chat):
    cid = new_conversation(chat)
    r = send(chat, cid, **{"HX-Request": "true"})
    assert r.status_code == 200 and 'id="assistant-thread"' in r.text


def test_reply_is_escaped(chat):
    hostile = "<script>alert(1)</script> ![x](https://evil.example/a.png) [l](javascript:alert(1))"
    chat.fake.script = [{"text": hostile}]
    cid = new_conversation(chat)
    send(chat, cid)
    poll(chat, cid)
    r = page_of(chat, f"?c={cid}")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in r.text
    assert "<script>alert" not in r.text
    assert all(src.startswith("/static/") for src in re.findall(r'<img[^>]*src="([^"]*)"', r.text))
    assert 'href="javascript:' not in r.text
    assert r.headers["content-security-policy"] == CONTENT_SECURITY_POLICY


def test_viewer_can_chat_non_member_404_other_users_conversation_404(chat):
    viewer_cid = new_conversation(chat, "vi")
    owner_cid = new_conversation(chat, "ed")
    chat.csrf = chat.login("vi")
    assert page_of(chat).status_code == 200
    assert send(chat, viewer_cid).status_code == 303
    poll(chat, viewer_cid)
    assert page_of(chat, f"?c={owner_cid}").status_code == 404
    assert send(chat, owner_cid).status_code == 404

    chat.csrf = chat.login("st")
    assert page_of(chat).status_code == 404

    chat.csrf = chat.login("admin")  # conversations are their creator's alone
    assert page_of(chat, f"?c={owner_cid}").status_code == 404
    for path in (f"/c/{owner_cid}/thread",):
        assert chat.client.get(f"/projects/{chat.p}/assistant{path}").status_code == 404
    for action in ("cancel", "delete", "messages"):
        r = chat.client.post(
            f"/projects/{chat.p}/assistant/c/{owner_cid}/{action}",
            data={"csrf_token": chat.csrf, "text": "x"},
            follow_redirects=False,
        )
        assert r.status_code == 404, action
    other_project = new_conversation(chat, "ed", chat.q)
    chat.csrf = chat.login("ed")
    assert page_of(chat, f"?c={other_project}").status_code == 404


def test_busy_unavailable_and_too_long_keep_the_text(chat):
    cid = new_conversation(chat)
    chat.fake.script = [{"text": "slow", "delay": 2}]
    assert send(chat, cid, "first").status_code == 303
    r = send(chat, cid, "second question")
    assert r.status_code == 409
    assert textarea(r.text) == "second question"
    assert shown("assistant.error.busy") in r.text
    poll(chat, cid)

    r = send(chat, cid, "x" * (store.MAX_MESSAGE_CHARS + 1))
    assert r.status_code == 422 and textarea(r.text) == "x" * (store.MAX_MESSAGE_CHARS + 1)
    assert shown("assistant.error.text") in r.text
    r = send(chat, cid, "   ")
    assert r.status_code == 422

    use_monitor(chat.client, state="unreachable")
    r = send(chat, cid, "are you there?")
    assert r.status_code == 503 and textarea(r.text) == "are you there?"


def test_too_many_turns_is_429_and_keeps_the_text(chat, monkeypatch):
    def refuse(*args, **kwargs):
        raise TooManyTurns()

    monkeypatch.setattr(chat.client.app.state.turns, "submit", refuse)
    cid = new_conversation(chat)
    r = send(chat, cid, "one more")
    assert r.status_code == 429 and textarea(r.text) == "one more"
    assert shown("assistant.error.too_many_turns") in r.text


def test_a_full_conversation_list_is_409(chat, monkeypatch):
    monkeypatch.setattr(store, "MAX_CONVERSATIONS", 1)
    url = f"/projects/{chat.p}/assistant/conversations"
    first = chat.client.post(url, data={"csrf_token": chat.csrf}, follow_redirects=False)
    assert first.status_code == 303 and "?c=" in first.headers["location"]
    r = chat.client.post(url, data={"csrf_token": chat.csrf}, follow_redirects=False)
    assert r.status_code == 409
    assert shown("assistant.error.conversation_limit") in r.text


def test_remote_warning_names_the_host(make_client, fake_llm, monkeypatch):
    monkeypatch.setattr(LlmMonitor, "start", lambda self: None)  # the remote host is not probed
    client = make_client(
        llm_base_url="https://api.example.com",
        llm_provider="claude",
        llm_api_key="sk-test-0123456789",
    )
    world = make_world(client)
    world.login("ed")
    r = page_of(world)
    assert r.status_code == 200 and "api.example.com" in r.text

    assert "data-remote-warning" in r.text

    fake = fake_llm()
    other_dir = client.app.state.settings.data_dir.parent / "other"
    local = make_world(make_client(other_dir, llm_base_url=fake.url))
    local.login("ed")
    assert "data-remote-warning" not in page_of(local).text


def test_pulling_disables_input_and_shows_progress(chat):
    use_monitor(chat.client, state="pulling", completed=250, total=1000)
    new_conversation(chat)
    r = page_of(chat)
    assert r.status_code == 200
    assert "<progress" in r.text and 'value="250"' in r.text
    assert shown("assistant.state.pulling") in r.text
    assert re.search(r"<textarea[^>]*disabled", r.text)


def test_entry_links_when_on(chat):
    ids = chat.ids[chat.p]
    base = f"/projects/{chat.p}"
    assert f'href="{base}/assistant"' in chat.client.get(base).text
    model = chat.client.get(f"{base}/models/{ids['model']}").text
    assert f"{base}/assistant?ask=model:{ids['model']}" in model
    summary = chat.client.get(f"{base}/models/{ids['model']}/summary").text
    assert f"{base}/assistant?ask=model:{ids['model']}" in summary
    analysis = chat.client.get(f"{base}/datasets/{ids['train']}/analyze").text
    assert f"{base}/assistant?ask=dataset:{ids['train']}" in analysis


def finish_job(world, job_id, status):
    with closing(connect(world.client)) as conn:
        jobs.claim_job(conn, job_id, "token")
        jobs.finish_job(conn, job_id, JobStatus(status), message="boom")


def job_pages(world, job):
    page = world.client.get(f"/projects/{world.p}/jobs/{job}").text
    fragment = world.client.get(
        f"/projects/{world.p}/jobs/{job}/status", headers={"HX-Request": "true"}
    ).text
    return page, fragment


def test_failed_job_links_to_the_assistant(chat):
    job = chat.ids[chat.p]["job"]
    link = f"/projects/{chat.p}/assistant?ask=job:{job}"
    assert all(link not in text for text in job_pages(chat, job))  # not failed yet
    finish_job(chat, job, "failed")
    assert all(link in text for text in job_pages(chat, job))
    done = chat.ids[chat.q]["job"]
    finish_job(chat, done, "done")
    assert "?ask=job:" not in chat.client.get(f"/projects/{chat.q}/jobs/{done}").text


def test_job_prefill_is_for_a_failed_job_of_the_project(chat):
    job = chat.ids[chat.p]["job"]
    assert textarea(page_of(chat, f"?ask=job:{job}").text) == ""  # not failed
    finish_job(chat, job, "failed")
    r = page_of(chat, f"?ask=job:{job}")
    assert f"job {job}" in textarea(r.text) and chat.fake.requests == []
    finish_job(chat, chat.ids[chat.q]["job"], "failed")
    for query in (f"?ask=job:{chat.ids[chat.q]['job']}", "?ask=job:999999", "?ask=job:x"):
        r = page_of(chat, query)
        assert r.status_code == 200 and textarea(r.text) == "", query


def test_examples_are_shown_on_an_empty_conversation_and_prefill(chat):
    examples = [shown(f"assistant.example_{n}") for n in (1, 2, 3)]
    r = page_of(chat)
    assert all(f">{text}</a>" in r.text for text in examples)
    for n, text in enumerate(examples, 1):
        r = page_of(chat, f"?ask=example:{n}")
        assert textarea(r.text) == text and chat.fake.requests == []
    for query in ("?ask=example:4", "?ask=example:"):
        assert textarea(page_of(chat, query).text) == ""
    cid = new_conversation(chat)
    r = page_of(chat, f"?c={cid}")
    assert f"?c={cid}&amp;ask=example:2" in r.text
    send(chat, cid)
    poll(chat, cid)
    assert "data-examples" not in page_of(chat, f"?c={cid}").text


def test_examples_wait_until_the_assistant_can_answer(chat):
    use_monitor(chat.client, state="pulling", completed=250, total=1000)
    assert "data-examples" not in page_of(chat).text


def test_ask_prefill_is_scoped(chat):
    own = chat.ids[chat.p]
    r = page_of(chat, f"?ask=model:{own['model']}")
    assert textarea(r.text) != "" and chat.fake.requests == []
    r = page_of(chat, f"?ask=dataset:{own['train']}")
    assert "iris" in textarea(r.text)
    other = chat.ids[chat.q]
    for query in (f"?ask=model:{other['model']}", f"?ask=dataset:{other['train']}", "?ask=x:1"):
        r = page_of(chat, query)
        assert r.status_code == 200 and textarea(r.text) == "", query


def test_cancel_and_delete(chat):
    cid = new_conversation(chat)
    chat.fake.script = [{"text": "w " * 200, "chunks": 200, "chunk_delay": 0.05}]
    send(chat, cid)
    r = chat.client.post(
        f"/projects/{chat.p}/assistant/c/{cid}/cancel",
        data={"csrf_token": chat.csrf},
        follow_redirects=False,
    )
    assert r.status_code == 303
    final = poll(chat, cid)
    assert shown("assistant.error.cancelled") in final.text

    r = chat.client.post(
        f"/projects/{chat.p}/assistant/c/{cid}/delete",
        data={"csrf_token": chat.csrf},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == f"/projects/{chat.p}/assistant"
    assert page_of(chat, f"?c={cid}").status_code == 404


def test_cancel_of_other_users_conversation_is_404(chat, monkeypatch):
    cid = new_conversation(chat, "co")
    cancelled = []
    monkeypatch.setattr(chat.client.app.state.turns, "cancel", cancelled.append)
    chat.csrf = chat.login("admin")
    r = chat.client.post(
        f"/projects/{chat.p}/assistant/c/{cid}/cancel",
        data={"csrf_token": chat.csrf},
        follow_redirects=False,
    )
    assert r.status_code == 404 and cancelled == []


def test_posts_check_csrf_and_origin(chat):
    cid = new_conversation(chat)
    url = f"/projects/{chat.p}/assistant/c/{cid}/messages"
    r = chat.client.post(url, data={"text": "hi"}, follow_redirects=False)
    assert r.status_code == 403
    r = chat.client.post(
        url,
        data={"csrf_token": chat.csrf, "text": "hi"},
        headers={"Origin": "http://evil.example"},
        follow_redirects=False,
    )
    assert r.status_code == 403 and chat.fake.requests == []


def test_thread_poll_stops_when_the_conversation_is_gone(chat):
    cid = new_conversation(chat)
    chat.client.post(f"/projects/{chat.p}/assistant/c/{cid}/delete", data={"csrf_token": chat.csrf})
    r = chat.client.get(
        f"/projects/{chat.p}/assistant/c/{cid}/thread", headers={"HX-Request": "true"}
    )
    assert r.status_code == STOP_POLLING and "hx-trigger" not in r.text
    r = chat.client.get(f"/projects/{chat.p}/assistant/c/{cid}/thread")
    assert r.status_code == 404


def test_tool_rows_name_what_was_read_not_what_it_said(chat):
    ids = chat.ids[chat.p]
    chat.fake.script = [
        {"tool_calls": [{"name": "describe_dataset", "arguments": {"dataset_id": ids["train"]}}]},
        {"tool_calls": [{"name": "start_training", "arguments": {}}]},
        {"text": "Done."},
    ]
    cid = new_conversation(chat)
    send(chat, cid)
    final = poll(chat, cid).text
    for tool in ("describe_dataset", "refused"):
        label = i18n.t(f"assistant.tool.{tool}", "en")
        assert shown("assistant.looked_at", label=label) in final
    assert "sepal length" not in final and "start_training" not in final


def test_failed_turn_shows_the_code_text_not_the_provider_text(chat):
    chat.fake.script = [{"status": 500, "body": "secret-provider-detail"}]
    cid = new_conversation(chat)
    send(chat, cid)
    final = poll(chat, cid).text
    assert shown("assistant.error.http") in final
    assert "secret-provider-detail" not in final


def test_context_too_small_text_gives_the_remedy():
    for lang in i18n.LANGUAGES:
        text = i18n.t("assistant.error.context_too_small", lang)
        assert "FIONE_LLM_CONTEXT_TOKENS=16384" in text and "OLLAMA_CONTEXT_LENGTH=16384" in text


def test_every_error_code_has_a_text():
    keys = [f"assistant.error.{code}" for code in (*ERROR_CODES, "too_many_turns")]
    keys += [f"assistant.state.{state}" for state in LLM_STATES]
    keys += [f"assistant.tool.{tool['function']['name']}" for tool in list_tools()]
    keys += ["assistant.tool.refused", "nav.section.assistant", "assistant.remote_warning"]
    for lang in i18n.LANGUAGES:
        catalog = i18n.catalog(lang)
        assert [k for k in keys if k not in catalog] == [], lang


def test_unavailable_page_never_fails(make_client):
    world = make_world(make_client(llm_base_url="http://127.0.0.1:9/v1", llm_provider="ollama"))
    for state in LLM_STATES:
        use_monitor(world.client, state=state)
        world.login("ed")
        assert page_of(world).status_code == 200, state
    cid = new_conversation(world)
    world.csrf = world.login("ed")
    r = send(world, cid, "hello")
    assert r.status_code == 503 and textarea(r.text) == "hello"


def test_navigation_shows_the_assistant_in_the_simple_view(chat):
    nav = chat.client.get(f"/projects/{chat.p}/datasets").text
    assert f'href="/projects/{chat.p}/assistant"' in nav


# --- the consent a remote host needs, and the banner ------------------------------------

REMOTE = {
    "llm_base_url": "https://llm.invalid",
    "llm_provider": "claude",
    "llm_api_key": "sk-test-0123456789",
}


@pytest.fixture
def remote(make_client, monkeypatch):
    """A world whose app uses Claude on a remote host nobody has consented to; the host is never
    probed, and the monitor reports what a probe that the key passed would find."""
    monkeypatch.setattr(LlmMonitor, "start", lambda self: None)
    world = make_world(make_client(**REMOTE))
    world.client.app.state.llm_monitor._update(state="ready")
    return world


def consents(world) -> list[tuple]:
    with closing(connect(world.client)) as conn:
        rows = conn.execute("SELECT host, provider, model, consented_by FROM llm_consents")
        return [tuple(row) for row in rows]


def banner(html: str) -> str | None:
    match = re.search(r"<div[^>]*data-llm-banner[^>]*>(.*?)</div>", html, re.S)
    return match.group(1) if match else None


def test_admin_is_redirected_to_the_consent_page_for_a_remote_host(remote):
    remote.login("admin")
    for path in ("/admin/users", "/admin/system", f"/projects/{remote.p}/assistant"):
        r = remote.client.get(path, follow_redirects=False)
        assert (r.status_code, r.headers.get("location")) == (303, SETUP), path
    polled = remote.client.get("/admin/system", headers={"HX-Request": "true"})
    assert polled.status_code == 200 and 'id="system-status"' in polled.text  # no page in the card
    home = remote.client.get("/")
    assert home.status_code == 200 and f'href="{SETUP}"' in banner(home.text)
    assert remote.client.get(SETUP).status_code == 200


def test_consent_post_records_it_and_unblocks_turns(remote, fake_llm):
    cid = new_conversation(remote)
    remote.csrf = remote.login("ed")
    assert send(remote, cid, "before").status_code == 503

    csrf = remote.login("admin")
    r = remote.client.post(SETUP, data={"csrf_token": csrf}, follow_redirects=False)
    assert (r.status_code, r.headers["location"]) == (303, "/admin/system")
    with closing(connect(remote.client)) as conn:
        admin = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
    assert consents(remote) == [("https://llm.invalid", "claude", "claude-opus-5-5", admin)]
    assert remote.client.get("/admin/system", follow_redirects=False).status_code == 200
    r = remote.client.get(SETUP, follow_redirects=False)
    assert (r.status_code, r.headers["location"]) == (303, "/admin/system")
    assert banner(remote.client.get("/").text) is None

    # The same app's monitor decides; the turn itself goes to a fake server.
    fake = fake_llm([{"text": "after"}])
    state = remote.client.app.state
    settings = state.settings.model_copy(
        update={"llm_base_url": fake.url, "llm_provider": "ollama"}
    )
    state.turns.shutdown()
    state.turns = TurnManager(state.db_path, state.storage, settings, state.llm_monitor)
    remote.csrf = remote.login("ed")
    assert send(remote, cid, "after").status_code == 303
    assert "after" in poll(remote, cid).text and len(fake.requests) == 1


def test_viewer_sees_the_banner_not_the_page(remote):
    remote.login("vi")
    assert remote.client.get(SETUP, follow_redirects=False).status_code == 403
    r = page_of(remote)
    assert r.status_code == 200
    text = shown("assistant.state.consent_required")
    assert text in banner(r.text) and text in r.text.replace(banner(r.text), "")
    assert SETUP not in r.text
    assert text in banner(remote.client.get("/").text)


def test_local_host_has_no_consent_page_redirect(chat):
    csrf = chat.login("admin")
    for path in ("/admin/users", "/admin/system", f"/projects/{chat.p}/assistant"):
        assert chat.client.get(path, follow_redirects=False).status_code == 200, path
    for r in (
        chat.client.get(SETUP, follow_redirects=False),
        chat.client.post(SETUP, data={"csrf_token": csrf}, follow_redirects=False),
    ):
        assert (r.status_code, r.headers["location"]) == (303, "/admin/system")
    assert consents(chat) == []


@pytest.mark.parametrize("state", NOT_READY)
def test_banner_shows_for_every_state_but_ready(chat, state):
    use_monitor(chat.client, state=state)
    for path in ("/", f"/projects/{chat.p}", f"/projects/{chat.p}/datasets"):
        assert shown(f"assistant.state.{state}") in banner(chat.client.get(path).text), path


def test_banner_shows_for_unreachable(chat):
    use_monitor(chat.client, state="unreachable")
    text = shown("assistant.state.unreachable")
    page = chat.client.get(f"/projects/{chat.p}").text
    assert text in banner(page) and f'href="/projects/{chat.p}/assistant"' in banner(page)
    chat.login("admin")
    assert 'href="/admin/system"' in banner(chat.client.get("/").text)
    chat.client.cookies.clear()
    assert banner(chat.client.get("/login").text) is None  # nothing for anonymous visitors
    use_monitor(chat.client, state="ready")
    chat.login("ed")
    assert banner(chat.client.get("/").text) is None


def test_consent_page_is_csrf_protected_and_admin_only(remote):
    anonymous = remote.client.get(SETUP, follow_redirects=False)
    assert anonymous.status_code == 303 and anonymous.headers["location"].startswith("/login?")
    assert remote.client.post(SETUP, data={}, follow_redirects=False).status_code == 401
    csrf = remote.login("ed")
    assert remote.client.get(SETUP).status_code == 403
    assert remote.client.post(SETUP, data={"csrf_token": csrf}).status_code == 403
    csrf = remote.login("admin")
    assert remote.client.post(SETUP, data={}).status_code == 403
    r = remote.client.post(
        SETUP, data={"csrf_token": csrf}, headers={"Origin": "https://evil.example"}
    )
    assert r.status_code == 403
    assert consents(remote) == []
    assert remote.client.app.state.llm_monitor.snapshot().state == "consent_required"


@pytest.mark.parametrize("lang", ["en", "ja"])
def test_consent_page_names_provider_host_and_model(remote, lang):
    remote.login("admin")
    remote.client.cookies.set("fione_lang", lang)
    page = remote.client.get(SETUP).text
    for key in (
        "consent.title",
        "consent.provider.claude",
        "consent.sent.columns",
        "consent.sent.stats",
        "consent.sent.examples",
        "consent.sent.models",
        "consent.sent.jobs",
    ):
        assert str(escape(i18n.t(key, lang))) in page, key
    assert str(escape(i18n.t("consent.not_sent", lang, host="llm.invalid"))) in page
    assert "<code>llm.invalid</code>" in page and "<code>claude-opus-5-5</code>" in page
    form = re.search(rf'<form[^>]*action="{SETUP}".*?</form>', page, re.S).group(0)
    assert form.count("<button") == 1 and 'name="csrf_token"' in form
    assert page.count(f'action="{SETUP}"') == 1 and "sk-test-0123456789" not in page


def test_consent_page_and_banner_escape_hostile_text(remote):
    use_monitor(remote.client, state="consent_required", local=False, host=XSS, model=XSS)
    remote.login("admin")
    page = remote.client.get(SETUP).text
    assert str(escape(XSS)) in page and XSS not in page
    remote.login("ed")
    page = page_of(remote).text
    assert str(escape(XSS)) in page and XSS not in page  # the remote warning names the host
    assert XSS not in banner(page) and str(escape(XSS)) not in banner(page)
