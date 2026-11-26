"""Fione without the assistant (``FIONE_LLM_PROVIDER=none``, the default): no page shows it or
links to it, its routes are not found, nothing is probed, and the System page says it is off."""

import re
from contextlib import closing

import httpx
import pytest
from markupsafe import escape

from api_helpers import ASSISTANT_OFF, connect
from fione import i18n
from fione.assistant import store as assistant_store
from fione.assistant.provider import LlmMonitor
from fione.auth import service as users
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.web import assistant_ui
from web_helpers import make_world

P = "/projects/{p}"
PAGES = (
    "/",
    "/account",
    "/admin/system",
    "/admin/users",
    "/modules",
    P,
    P + "/upload",
    P + "/members",
    P + "/datasets",
    P + "/datasets/{train}",
    P + "/datasets/{train}/analyze",
    P + "/datasets/{train}/train",
    P + "/datasets/{train}/columns/species",
    P + "/jobs",
    P + "/jobs/{job}",
    P + "/jobs/{failed}",
    P + "/jobs/{predict_job}/result",
    P + "/models",
    P + "/models/{model}",
    P + "/models/{model}/summary",
    P + "/models/{model}/predict",
)
# What a page holds when it offers the assistant: a link to it, a comment, the state banner.
MARKS = re.compile(r'/assistant"|/assistant\?|assistant-note|data-llm-banner')


def _world(make_client, **settings):
    world = make_world(make_client(**settings))
    with closing(connect(world.client)) as conn:
        for project, ids in world.ids.items():
            job = store.enqueue(conn, "automl", project, 1, {"dataset_id": ids["train"]})
            store.claim_job(conn, job.id, "token")
            store.finish_job(conn, job.id, JobStatus.FAILED, message="no rows")
            ids["failed"] = job.id
    return world


@pytest.fixture
def off(make_client):
    return _world(make_client, **ASSISTANT_OFF)


@pytest.mark.parametrize("mode", [None, "detailed"])
@pytest.mark.parametrize("username", ["ed", "admin"])
def test_no_page_offers_the_assistant(off, username, mode):
    off.mode = mode
    off.login(username)
    for template in PAGES:
        if template.startswith("/admin/") and username != "admin":
            continue
        r = off.client.get(off.path(template), follow_redirects=False)
        assert r.status_code == 200, template
        assert MARKS.search(r.text) is None, (template, MARKS.search(r.text)[0])


def test_the_same_pages_offer_it_when_it_is_on(make_client, monkeypatch):
    """The check above looks for what these pages really hold: with a ready assistant (no
    banner), the project's tab, the links and the comments."""
    monkeypatch.setattr(LlmMonitor, "start", lambda self: None)  # nothing is probed
    on = _world(make_client)
    on.client.app.state.llm_monitor._update(state="ready")
    on.login("ed")
    expected = {
        P: {'/assistant"'},
        P + "/jobs/{failed}": {'/assistant"', "/assistant?", "assistant-note"},
        P + "/datasets/{train}/analyze": {'/assistant"', "/assistant?", "assistant-note"},
        P + "/models/{model}/summary": {'/assistant"', "/assistant?", "assistant-note"},
    }
    for template, marks in expected.items():
        assert set(MARKS.findall(on.client.get(on.path(template)).text)) == marks, template
    on.client.app.state.llm_monitor._update(state="unreachable")
    assert "data-llm-banner" in MARKS.findall(on.client.get(on.path(P)).text)


def _sweep(world) -> dict:
    """The status of each route of the assistant, as ``ed`` with a conversation that holds a
    pending proposal; the conversation is deleted last."""
    csrf = world.login("ed")
    ids = world.ids[world.p]
    with closing(connect(world.client)) as conn:
        uid = conn.execute("SELECT id FROM users WHERE username = 'ed'").fetchone()[0]
        ed = users.get_user(conn, uid)
        cid = assistant_store.create_conversation(conn, ed, world.p).id
        message = assistant_store.add_message(conn, cid, "assistant", "a proposal")
        config = {"target": "species", "max_runtime_secs": 60}
        prid = assistant_store.add_proposal(conn, message.id, cid, ids["train"], config, {}).id
    values = {"pid": world.p, "cid": cid, "prid": prid, "did": ids["train"], "mid": ids["model"]}
    routes = [r for r in assistant_ui.router.routes if hasattr(r, "methods")]
    statuses = {}
    for route in sorted(routes, key=lambda r: r.path.endswith("/delete")):
        jid = ids["predict_job"] if "prediction-comment" in route.path else ids["failed"]
        path = route.path.format(**values, jid=jid)
        for method in route.methods:
            r = world.client.request(method, path, data={"csrf_token": csrf, "text": "hi"})
            statuses[(method, path)] = r.status_code
    assert len(statuses) > 10
    return statuses


def test_the_assistants_routes_are_not_found(off):
    found = {route: status for route, status in _sweep(off).items() if status != 404}
    assert found == {}


def test_the_assistants_routes_are_found_when_it_is_on(make_client, monkeypatch):
    """The sweep above reaches each route: with the assistant on, none is not found."""
    monkeypatch.setattr(LlmMonitor, "start", lambda self: None)
    on = _world(make_client)
    on.client.app.state.llm_monitor._update(state="ready")
    missing = {route: status for route, status in _sweep(on).items() if status == 404}
    assert missing == {}


def test_the_system_page_says_it_is_off(off):
    off.login("admin")
    page = off.client.get("/admin/system").text
    assert str(escape(i18n.t("system.llm_off_hint", "en"))) in page
    assert "/admin/system/llm/pull" not in page
    llm = off.client.get("/api/v1/system/status").json()["llm"]
    assert llm["state"] == "off" and llm["model"] is None and llm["host"] is None
    r = off.client.get("/admin/setup/assistant", follow_redirects=False)
    assert (r.status_code, r.headers["location"]) == (303, "/admin/system")


def test_the_monitor_sends_nothing(tmp_path):
    from api_helpers import make_settings

    def refuse(request):
        raise AssertionError(f"no request expected: {request.url}")

    settings = make_settings(tmp_path, **ASSISTANT_OFF)
    monitor = LlmMonitor(
        settings, tmp_path / "db", http=httpx.Client(transport=httpx.MockTransport(refuse))
    )
    monitor.start()
    assert monitor._thread is None
    status = monitor.snapshot()
    assert (status.state, status.local, status.host) == ("off", True, None)
    assert monitor.pull_now() is False
    monitor.stop()
