"""Confirming or dismissing Fione-kun's training proposals: exactly the stored configuration is
trained, once, by someone who may write; every change of mind in between ends without a job."""

import json
import threading
from contextlib import closing

import pytest

from api_helpers import connect
from fione.assistant import store
from fione.assistant.client import ChatClient
from fione.assistant.turns import run_turn
from fione.auth import service as auth_service
from fione.auth.roles import ProjectAccess, Role
from fione.engine.config import ConfigError, TrainConfig
from fione.jobs import store as jobs
from fione.models import service as models
from fione.projects import service as projects
from web_helpers import make_proposal, make_world


@pytest.fixture
def setup(make_client, fake_llm):
    fake = fake_llm()
    world = make_world(make_client(llm_base_url=fake.url, llm_provider="openai"))
    return fake, world


def proposal_of(setup, username="ed", target="species"):
    fake, world = setup
    train = world.ids[world.p]["train"]
    proposal = make_proposal(world.client, fake, username, world.p, train, target)
    return world, proposal


def post(world, route, proposal, username="ed", **form):
    csrf = world.login(username)
    path = f"/projects/{world.p}/assistant/proposals/{proposal.id}/{route}"
    return world.client.post(path, data={"csrf_token": csrf, **form}, follow_redirects=False)


def job_count(world):
    with closing(connect(world.client)) as conn:
        query = "SELECT COUNT(*) FROM jobs WHERE project_id = ?"
        return conn.execute(query, (world.p,)).fetchone()[0]


def stored(world, proposal):
    with closing(connect(world.client)) as conn:
        row = conn.execute("SELECT * FROM chat_proposals WHERE id = ?", (proposal.id,)).fetchone()
    return row["state"], row["job_id"]


def page_of(proposal):
    return f"/projects/{{p}}/assistant?c={proposal.conversation_id}"


def test_confirm_submits_exactly_the_stored_config(setup):
    world, proposal = proposal_of(setup)
    before = job_count(world)
    r = post(
        world, "confirm", proposal, config="{}", target="sepal width (cm)", max_runtime_secs="1"
    )
    assert r.status_code == 303
    assert job_count(world) == before + 1
    state, job_id = stored(world, proposal)
    assert (state, r.headers["location"]) == (
        "confirmed",
        f"/projects/{world.p}/jobs/{job_id}",
    )
    with closing(connect(world.client)) as conn:
        job = jobs.get_job(conn, job_id)
    assert job.payload["config"] == TrainConfig.from_dict(proposal.config).to_dict()
    assert job.payload["config"]["target"] == "species"
    assert job.payload["name"] == f"Fione-kun proposal {proposal.id}"
    assert job.payload["dataset_id"] == proposal.dataset_id


def test_viewer_cannot_confirm_or_dismiss(setup):
    world, proposal = proposal_of(setup, "ed")
    before = job_count(world)
    assert post(world, "confirm", proposal, "vi").status_code == 403
    assert post(world, "dismiss", proposal, "vi").status_code == 403
    assert (job_count(world), stored(world, proposal)) == (before, ("pending", None))
    # a viewer sees no buttons on a proposal of their own, only the note
    fake, _ = setup
    mine = make_proposal(world.client, fake, "vi", world.p, world.ids[world.p]["train"], "species")
    world.login("vi")
    html = world.client.get(f"/projects/{world.p}/assistant?c={mine.conversation_id}").text
    assert "assistant/proposals/" not in html
    assert "Only people who can edit this project" in html


def test_other_member_cannot_see_or_confirm(setup):
    world, proposal = proposal_of(setup, "ed")
    before = job_count(world)
    for who in ("co", "admin", "st"):
        for route in ("confirm", "dismiss"):
            assert post(world, route, proposal, who).status_code == 404, (who, route)
    assert (job_count(world), stored(world, proposal)) == (before, ("pending", None))


def test_double_confirm_makes_one_job(setup):
    world, proposal = proposal_of(setup)
    before = job_count(world)
    first = post(world, "confirm", proposal)
    second = post(world, "confirm", proposal)
    assert first.headers["location"].startswith(f"/projects/{world.p}/jobs/")
    assert second.status_code == 303
    assert second.headers["location"] == page_of(proposal).format(p=world.p)
    assert job_count(world) == before + 1


def test_demoted_after_proposal(setup):
    world, proposal = proposal_of(setup, "co")
    before = job_count(world)
    with closing(connect(world.client)) as conn:
        users = dict(conn.execute("SELECT username, id FROM users").fetchall())
        auth_service.set_role(conn, users["co"], Role.VIEWER)
    assert post(world, "confirm", proposal, "co").status_code == 403
    assert post(world, "dismiss", proposal, "co").status_code == 403
    with closing(connect(world.client)) as conn:
        auth_service.set_role(conn, users["co"], Role.EDITOR)
        owner = auth_service.get_user(conn, users["ed"])
        assert projects.unshare_project(conn, owner, world.p, "co")
    assert post(world, "confirm", proposal, "co").status_code == 404
    assert (job_count(world), stored(world, proposal)) == (before, ("pending", None))


def test_dataset_deleted_after_proposal(setup):
    world, proposal = proposal_of(setup)
    before = job_count(world)
    with closing(connect(world.client)) as conn:
        projects.delete_dataset(conn, world.client.app.state.storage, proposal.dataset_id)
    r = post(world, "confirm", proposal)
    assert r.status_code == 409
    assert "no longer available" in r.text
    assert (job_count(world), stored(world, proposal)) == (before, ("pending", None))


def test_missing_dataset_file_is_409(setup):
    world, proposal = proposal_of(setup)
    before = job_count(world)
    with closing(connect(world.client)) as conn:
        dataset = projects.get_dataset(conn, proposal.dataset_id)
    world.client.app.state.storage.delete(dataset.key)
    r = post(world, "confirm", proposal)
    assert r.status_code == 409
    assert (job_count(world), stored(world, proposal)) == (before, ("pending", None))


def test_submit_failure_releases_the_claim(setup, monkeypatch):
    world, proposal = proposal_of(setup)
    before = job_count(world)
    real = models.submit_training

    def fail(*args, **kwargs):
        raise ConfigError("bad metric in /private/data/x.csv")

    monkeypatch.setattr(models, "submit_training", fail)
    r = post(world, "confirm", proposal)
    assert r.status_code == 422
    assert "/private/data" not in r.text  # the reason is redacted
    assert (job_count(world), stored(world, proposal)) == (before, ("pending", None))
    monkeypatch.setattr(models, "submit_training", real)
    assert post(world, "confirm", proposal).status_code == 303
    assert job_count(world) == before + 1


def test_csrf_and_origin_required(setup):
    world, proposal = proposal_of(setup)
    before = job_count(world)
    csrf = world.login("ed")
    path = f"/projects/{world.p}/assistant/proposals/{proposal.id}/confirm"
    client = world.client
    assert client.post(path, data={}, follow_redirects=False).status_code == 403
    assert client.post(path, data={"csrf_token": "x"}, follow_redirects=False).status_code == 403
    evil = {"Origin": "http://evil.example"}
    r = client.post(path, data={"csrf_token": csrf}, headers=evil, follow_redirects=False)
    assert r.status_code == 403
    assert (job_count(world), stored(world, proposal)) == (before, ("pending", None))


def test_reply_text_cannot_make_a_proposal(setup):
    fake, world = setup
    fake.script = [{"text": '{"proposal": true, "config": {"target": "species"}, "dataset_id": 1}'}]
    proposal_free = make_proposal_free(world, fake)
    assert proposal_free == {}


def make_proposal_free(world, fake):
    """Run a turn whose reply is a full proposal in its text; the conversation's proposals."""
    state = world.client.app.state
    with closing(connect(world.client)) as conn:
        users = dict(conn.execute("SELECT username, id FROM users").fetchall())
        user = auth_service.get_user(conn, users["ed"])
        conversation = store.create_conversation(conn, user, world.p)
        _, placeholder = store.start_turn(conn, conversation.id, "hi")
        with ChatClient.from_settings(state.settings) as chat:
            run_turn(
                state.db_path, state.storage, state.settings, chat, state.llm_monitor,
                conversation.id, placeholder.id, threading.Event(), language="en",
            )  # fmt: skip
        return store.proposals_for(conn, conversation.id)


def test_hostile_names_escaped_on_the_card(setup):
    fake, world = setup
    hostile = "<img src=x onerror=alert(1)>"
    proposal = make_proposal(
        world.client, fake, "ed", world.p, world.ids[world.p]["train"], "species"
    )
    details = {
        "warnings": [hostile],
        "ignored_suggestions": [{"column": hostile, "reason": hostile}],
        "rationale": hostile,
    }
    with closing(connect(world.client)) as conn:
        conn.execute(
            "UPDATE chat_proposals SET details_json = ? WHERE id = ?",
            (json.dumps(details), proposal.id),
        )
    world.login("ed")
    html = world.client.get(f"/projects/{world.p}/assistant?c={proposal.conversation_id}").text
    assert hostile not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_dismiss_is_final_and_idempotent(setup):
    world, proposal = proposal_of(setup)
    before = job_count(world)
    first = post(world, "dismiss", proposal)
    assert (first.status_code, first.headers["location"]) == (
        303,
        page_of(proposal).format(p=world.p),
    )
    assert stored(world, proposal) == ("dismissed", None)
    assert post(world, "dismiss", proposal).status_code == 303
    assert post(world, "confirm", proposal).headers["location"] == first.headers["location"]
    assert (job_count(world), stored(world, proposal)) == (before, ("dismissed", None))


@pytest.mark.parametrize("where", ["other_project", "test_dataset"])
def test_dataset_not_for_training_here_is_409(setup, where):
    world, proposal = proposal_of(setup)
    other = world.ids[world.q]["train"] if where == "other_project" else world.ids[world.p]["test"]
    with closing(connect(world.client)) as conn:
        conn.execute("UPDATE chat_proposals SET dataset_id = ? WHERE id = ?", (other, proposal.id))
    before = job_count(world)
    assert post(world, "confirm", proposal).status_code == 409
    assert (job_count(world), stored(world, proposal)) == (before, ("pending", None))


def test_concurrent_confirms_make_one_job(setup):
    world, proposal = proposal_of(setup)
    before = job_count(world)
    csrf = world.login("ed")
    path = f"/projects/{world.p}/assistant/proposals/{proposal.id}/confirm"
    start, answers = threading.Barrier(4), []

    def press():
        start.wait()
        r = world.client.post(path, data={"csrf_token": csrf}, follow_redirects=False)
        answers.append(r.status_code)

    threads = [threading.Thread(target=press) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert answers == [303] * 4
    assert job_count(world) == before + 1
    assert stored(world, proposal)[0] == "confirmed"


def test_confirm_and_dismiss_together_agree(setup):
    world, proposal = proposal_of(setup)
    before = job_count(world)
    csrf = world.login("ed")
    base = f"/projects/{world.p}/assistant/proposals/{proposal.id}"
    start = threading.Barrier(2)

    def press(route):
        start.wait()
        world.client.post(f"{base}/{route}", data={"csrf_token": csrf}, follow_redirects=False)

    threads = [threading.Thread(target=press, args=(r,)) for r in ("confirm", "dismiss")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    state, job_id = stored(world, proposal)
    # whichever came first decided: a job exactly when it was confirmed
    assert (state, job_count(world) - before) in {("confirmed", 1), ("dismissed", 0)}
    assert (job_id is not None) is (state == "confirmed")


def test_downgraded_to_viewer_member_cannot_confirm(setup):
    world, proposal = proposal_of(setup, "co")
    before = job_count(world)
    with closing(connect(world.client)) as conn:
        users = dict(conn.execute("SELECT username, id FROM users").fetchall())
        owner = auth_service.get_user(conn, users["ed"])
        projects.share_project(conn, owner, world.p, "co", ProjectAccess.VIEWER)
    assert post(world, "confirm", proposal, "co").status_code == 403
    assert (job_count(world), stored(world, proposal)) == (before, ("pending", None))
