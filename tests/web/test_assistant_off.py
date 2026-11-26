"""Fione without the assistant (``FIONE_LLM_PROVIDER=none``, the default): no page shows it or
links to it, its routes are not found, nothing is probed, and the System page says it is off."""

import re
from contextlib import closing

import httpx
import pytest
from markupsafe import escape

from api_helpers import ASSISTANT_OFF, connect
from fione import i18n
from fione.assistant.provider import LlmMonitor
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


def test_the_same_pages_offer_it_when_it_is_on(make_client):
    """The check above looks for what these pages really hold."""
    on = _world(make_client)  # ollama on an address nothing listens on: never ready
    on.login("ed")
    for template in (P, P + "/jobs/{failed}", P + "/datasets/{train}/analyze"):
        text = on.client.get(on.path(template)).text
        assert 'href="/projects/' in text and MARKS.search(text) is not None, template
    found = set(MARKS.findall(on.client.get(on.path(P + "/models/{model}/summary")).text))
    assert {"assistant-note", "data-llm-banner", "/assistant?"} <= found


def test_the_assistants_routes_are_not_found(off):
    csrf = off.login("ed")
    ids = off.ids[off.p] | {"pid": off.p, "cid": 1, "prid": 1}
    values = {"did": ids["train"], "mid": ids["model"], "jid": ids["failed"]} | ids
    routes = [r for r in assistant_ui.router.routes if hasattr(r, "methods")]
    assert len(routes) > 10
    for route in routes:
        path = re.sub(r"{(\w+)}", lambda m: str(values[m[1]]), route.path)
        for method in route.methods:
            r = off.client.request(method, path, data={"csrf_token": csrf, "text": "hi"})
            assert r.status_code == 404, (method, path)


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
