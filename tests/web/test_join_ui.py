"""The Join proposal of the datasets page and the dashboard: Fione's own link search, with no
language model (the assistant is off), and the Join job it starts once confirmed."""

import io
import re
from contextlib import closing
from html import unescape

import pandas as pd
import pytest

from api_helpers import ASSISTANT_OFF, add_user, bearer, connect, login, wait_job
from fione.auth.roles import ProjectAccess, Role
from fione.jobs import store as jobs
from fione.projects import service as projects
from fione.projects.ingest import ingest_csv, read_dataset
from fione.projects.service import DatasetType
from fione.tools import ToolError
from fione.web import automl

HX = {"HX-Request": "true"}
CUSTOMERS = pd.DataFrame({"id": range(1, 61), "churned": [0, 1, 0] * 20})
# several orders per customer: they are summarized into one row per customer
ORDERS = pd.DataFrame({"customer_id": [i % 60 + 1 for i in range(120)], "total": range(120)})


def ingest(client, pid, name, frame, kind=DatasetType.TRAIN) -> int:
    with closing(connect(client)) as conn:
        data = io.BytesIO(frame.to_csv(index=False).encode())
        return ingest_csv(client.app.state.storage, conn, pid, name, kind, data).id


class Shop:
    """Project ``Shop`` of ``ed`` (``vi`` may view it, ``st`` is no member) holding customers
    and their orders, on an app without the assistant."""

    def __init__(self, client):
        self.client = client
        self.owner = add_user(client, "ed", Role.EDITOR)
        for name in ("vi", "st"):
            add_user(client, name, Role.EDITOR)
        with closing(connect(client)) as conn:
            self.pid = projects.create_project(conn, self.owner, "Shop").id
            projects.share_project(conn, self.owner, self.pid, "vi", ProjectAccess.VIEWER)
        self.customers = ingest(client, self.pid, "customers", CUSTOMERS)
        self.orders = ingest(client, self.pid, "orders", ORDERS)
        self.url = f"/projects/{self.pid}/join"

    def login(self, username: str | None) -> str | None:
        self.client.cookies.clear()
        return login(self.client, username) if username else None

    def propose(self, target="churned", **headers):
        return self.client.get(self.url, params={"target": target}, headers=HX | headers)

    def fields(self, html: str) -> dict:
        form = re.search(rf'<form method="post" action="{self.url}".*?</form>', html, re.S)
        assert form, html
        pairs = re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)">', form[0])
        return {name: unescape(value) for name, value in pairs if name != "csrf_token"}

    def post(self, csrf, fields):
        data = {"csrf_token": csrf or "", **fields}
        return self.client.post(self.url, data=data, follow_redirects=False)

    def job_count(self) -> int:
        with closing(connect(self.client)) as conn:
            return len(jobs.list_jobs(conn, self.pid, limit=100))


@pytest.fixture
def shop(make_client):
    return Shop(make_client(**ASSISTANT_OFF))


def shown(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html)))


# --- where the button is ------------------------------------------------------------------


def test_the_button_shows_only_with_two_train_datasets(make_client):
    client = make_client(**ASSISTANT_OFF)
    owner = add_user(client, "ed", Role.EDITOR)
    with closing(connect(client)) as conn:
        pid = projects.create_project(conn, owner, "Shop").id
    login(client, "ed")
    ingest(client, pid, "customers", CUSTOMERS)
    ingest(client, pid, "customers_test", CUSTOMERS, DatasetType.TEST)  # one table's test data
    for page in (f"/projects/{pid}", f"/projects/{pid}/datasets"):
        html = client.get(page).text
        assert "data-join-form" not in html and "Propose a join" not in html
    ingest(client, pid, "orders", ORDERS)
    for page in (f"/projects/{pid}", f"/projects/{pid}/datasets"):
        html = client.get(page).text
        assert "data-join-form" in html and "Propose a join" in html, page
        assert f'hx-get="/projects/{pid}/join"' in html
        assert '<option value="churned">' in html and '<option value="customer_id">' in html
        assert "/assistant" not in html and "assistant-note" not in html
    html = client.get(f"/projects/{pid}/datasets", headers={"Accept-Language": "ja"}).text
    assert "結合を提案" in html


# --- the proposal -------------------------------------------------------------------------


def test_two_related_tables_get_a_summarized_join(shop):
    shop.login("ed")
    r = shop.propose()
    assert r.status_code == 200, r.text
    text = shown(r.text)
    assert "Join proposal" in text
    assert "Base dataset customers" in text and "Dataset to add orders" in text
    assert "Key column id = customer_id" in text
    assert "Summarized to one row per key" in text and "All columns" in text
    assert "Join only what is known when the model predicts" in text
    assert "Create the joined dataset" in text and "assistant" not in r.text.lower()
    assert shop.fields(r.text) == {
        "dataset_id": str(shop.customers),
        "other_dataset_id": str(shop.orders),
        "key": "id",
        "other_key": "customer_id",
        "summarize": "true",
        "columns": "",
    }
    ja = shown(shop.propose(**{"Accept-Language": "ja"}).text)
    assert "結合したデータセットを作る" in ja and "キーごとに 1 行にまとめる" in ja
    # without HTMX it is a page of its own
    page = shop.client.get(shop.url, params={"target": "churned"})
    assert page.status_code == 200 and "<html" in page.text and "Join proposal" in page.text


def test_the_warnings_are_translated(shop, monkeypatch):
    shop.login("ed")
    real = automl.call_tool

    def few_matches(name, args, ctx):
        found = real(name, args, ctx)
        found["warnings"] = [
            {"code": "join_few_matches", "message": "English", "params": {"share": "12"}}
        ]
        return found

    monkeypatch.setattr(automl, "call_tool", few_matches)
    assert "Only 12% of the key values" in shown(shop.propose().text)
    ja = shown(shop.propose(**{"Accept-Language": "ja"}).text)
    assert "12% だけです" in ja


@pytest.mark.parametrize(
    ("target", "en", "ja"),
    [
        ("", "Choose the column to predict.", "予測する列を選んでください。"),
        ("nope", "No dataset of this project has the column “nope”.", "「nope」という列"),
        ("total", "No dataset with this column has a link", "結合に使えるつながりがありません"),
    ],
)
def test_each_refusal_is_said_in_the_page_language(shop, target, en, ja):
    shop.login("ed")
    if target == "total":  # the orders repeat on both sides of a new link: none to follow
        with closing(connect(shop.client)) as conn:
            projects.delete_dataset(conn, shop.client.app.state.storage, shop.customers)
        ingest(shop.client, shop.pid, "refunds", ORDERS.rename(columns={"total": "refund"}))
    r = shop.propose(target)
    assert r.status_code == 200 and 'data-join="message"' in r.text
    assert en in shown(r.text) and "find_table_links" not in r.text
    assert ja in shown(shop.propose(target, **{"Accept-Language": "ja"}).text)


def test_a_tool_failure_and_an_error_are_a_message_not_a_spinner(shop, monkeypatch):
    shop.login("ed")

    def fails(name, args, ctx):
        raise ToolError("tool failed")

    monkeypatch.setattr(automl, "call_tool", fails)
    r = shop.propose()
    assert r.status_code == 200 and "The join could not be proposed" in shown(r.text)

    def breaks(name, args, ctx):
        raise RuntimeError("boom")

    monkeypatch.setattr(automl, "call_tool", breaks)
    r = shop.propose()
    assert r.status_code == 200 and "The join could not be proposed" in shown(r.text)
    assert "boom" not in r.text


def test_the_tool_runs_as_mcp_does(shop, monkeypatch):
    shop.login("ed")
    seen = []
    real = automl.call_tool

    def spy(name, args, ctx):
        seen.append((name, args, ctx.allow_samples, ctx.project_id, ctx.ask_model, ctx.via))
        return real(name, args, ctx)

    monkeypatch.setattr(automl, "call_tool", spy)
    shop.propose()
    target = {"project_id": shop.pid, "target": "churned"}
    assert seen == [("propose_first_join", target, False, shop.pid, None, "ui")]


# --- creating the joined dataset ----------------------------------------------------------


def test_the_confirmed_join_is_the_shown_one(shop):
    csrf = shop.login("ed")
    fields = shop.fields(shop.propose().text)
    r = shop.post(csrf, fields)
    assert r.status_code == 303, r.text
    job_id = int(r.headers["location"].rsplit("/", 1)[1])
    assert r.headers["location"] == f"/projects/{shop.pid}/jobs/{job_id}"
    with closing(connect(shop.client)) as conn:
        job = jobs.get_job(conn, job_id)
    assert job.kind == "module" and job.payload["module_id"] == "join"
    assert job.payload["dataset_id"] == shop.customers
    params = job.payload["params"]
    assert params["other_dataset_id"] == shop.orders
    assert (params["key"], params["other_key"], params["summarize"]) == ("id", "customer_id", True)


@pytest.mark.parametrize(
    "change",
    [
        {"key": "nope"},  # no such column
        {"columns": "customer_id"},  # the key is never added: not what the tool proposes
        {"summarize": "yes"},
        {"other_dataset_id": "{customers}"},  # onto itself
        {"dataset_id": "x"},
        {"dataset_id": ""},
    ],
)
def test_a_tampered_join_is_refused(shop, change):
    csrf = shop.login("ed")
    fields = shop.fields(shop.propose().text)
    before = shop.job_count()
    change = {k: v.format(customers=shop.customers) for k, v in change.items()}
    r = shop.post(csrf, fields | change)
    assert r.status_code == 409, r.text
    assert "This join no longer matches the datasets" in shown(r.text)
    assert shop.job_count() == before


def test_a_join_of_a_deleted_dataset_or_of_another_project_is_refused(shop):
    csrf = shop.login("ed")
    fields = shop.fields(shop.propose().text)
    before = shop.job_count()
    with closing(connect(shop.client)) as conn:
        other = projects.create_project(conn, shop.owner, "Other").id
    elsewhere = ingest(shop.client, other, "orders", ORDERS)
    r = shop.post(csrf, fields | {"other_dataset_id": str(elsewhere)})
    assert r.status_code == 409 and "no longer available" in shown(r.text)
    with closing(connect(shop.client)) as conn:
        projects.delete_dataset(conn, shop.client.app.state.storage, shop.orders)
    r = shop.post(csrf, fields)
    assert r.status_code == 409 and "no longer available" in shown(r.text)
    r = shop.client.post(
        shop.url, data={"csrf_token": csrf, **fields}, headers={"Accept-Language": "ja"}
    )
    assert r.status_code == 409 and "もう使えません" in shown(r.text)
    assert shop.job_count() == before


# --- who may do what ----------------------------------------------------------------------


def test_a_viewer_sees_the_proposal_without_the_button(shop):
    shop.login("ed")
    fields = shop.fields(shop.propose().text)
    csrf = shop.login("vi")
    r = shop.propose()
    assert r.status_code == 200 and "Join proposal" in r.text
    assert "Create the joined dataset" not in r.text and 'method="post"' not in r.text
    assert "Only people who can edit this project can create this dataset" in shown(r.text)
    before = shop.job_count()
    assert shop.post(csrf, fields).status_code == 403
    assert shop.job_count() == before


def test_a_stranger_and_an_anonymous_visitor_are_refused(shop):
    shop.login("ed")
    fields = shop.fields(shop.propose().text)
    csrf = shop.login("st")
    assert shop.client.get(shop.url, params={"target": "churned"}).status_code == 404
    r = shop.propose()  # HTMX: a message in place of the proposal
    assert r.status_code == 200 and "We could not find that page" in shown(r.text)
    assert shop.post(csrf, fields).status_code == 404
    shop.login(None)
    r = shop.client.get(shop.url, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login?next=")
    assert shop.post(None, fields).status_code == 401
    assert shop.job_count() == 0


# --- the whole flow -----------------------------------------------------------------------


def test_the_join_job_makes_the_joined_dataset(make_client, monkeypatch):
    monkeypatch.delenv("FIONE_JOB_HANDLER_MODULES", raising=False)
    shop = Shop(make_client(start_runner=True, **ASSISTANT_OFF))
    csrf = shop.login("ed")
    r = shop.post(csrf, shop.fields(shop.propose().text))
    assert r.status_code == 303, r.text
    job_id = int(r.headers["location"].rsplit("/", 1)[1])
    job = wait_job(shop.client, job_id, bearer(shop.client, shop.owner.id))
    assert job["status"] == "done", job
    with closing(connect(shop.client)) as conn:
        joined = projects.get_dataset(conn, job["result"]["dataset_id"])
    assert joined.project_id == shop.pid and joined.type == DatasetType.TRAIN
    frame = read_dataset(shop.client.app.state.storage, joined)
    assert len(frame) == 60 and frame["rows"].tolist() == [2] * 60
    assert {"id", "churned", "total_mean", "total_sum"} <= set(frame.columns)
    assert shop.client.get(r.headers["location"]).status_code == 200


def test_only_the_datasets_the_search_reads_are_offered(make_client):
    client = make_client(**ASSISTANT_OFF)
    owner = add_user(client, "ed", Role.EDITOR)
    with closing(connect(client)) as conn:
        pid = projects.create_project(conn, owner, "Shop").id
    login(client, "ed")
    ingest(client, pid, "customers", CUSTOMERS)
    ingest(client, pid, "orders", ORDERS)
    for i in range(6):
        ingest(client, pid, f"test_{i}", CUSTOMERS, DatasetType.TEST)
    late = CUSTOMERS.rename(columns={"churned": "late_target"})
    ingest(client, pid, "late", late)  # the 9th: the link search never reads it
    html = client.get(f"/projects/{pid}/datasets").text
    assert '<option value="churned">' in html and "late_target" not in html


def test_a_search_beyond_the_limit_is_asked_to_wait(shop):
    shop.login("ed")
    slots = shop.client.app.state.join_slots
    held = [slots.acquire(blocking=False) for _ in range(2)]
    try:
        assert all(held)
        r = shop.client.get(f"/projects/{shop.pid}/join?target=churned", headers=HX)
        assert r.status_code == 200 and "Try again in a moment" in r.text
    finally:
        for _ in held:
            slots.release()
    r = shop.client.get(f"/projects/{shop.pid}/join?target=churned", headers=HX)
    assert "Create the joined dataset" in r.text
