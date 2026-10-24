"""The model screens (leaderboard, model page, export and import), the Python modules screens
and the simple/detailed view preference."""

import json
import re
import time
from contextlib import closing
from html import escape

import pytest

from api_helpers import add_user, connect, login, store_model
from fione.api import routes_models
from fione.auth.roles import Role
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.models import service as models
from fione.projects import service as projects
from web_helpers import FAST, make_world

HTML = {"Accept": "text/html"}
XSS = "</script><img src=x onerror=alert(1)>"
ECHARTS = "/static/vendor/echarts/echarts.min.js"
MODULE_SOURCE = """
MODULE = {"name": NAME, "kind": "frame", "params": {"type": "object", "properties": {}}}


def run(df, params, ctx):
    return df
"""


def location(r) -> str:
    assert r.status_code == 303, r.text
    return r.headers["location"]


def count(client, table: str, where: str = "1=1", args=()) -> int:
    with closing(connect(client)) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", args).fetchone()[0]


def chart_specs(html: str) -> dict[str, dict]:
    blocks = re.findall(
        r'<script type="application/json" id="([^"]+)-data">(.*?)</script>', html, re.S
    )
    return {name: json.loads(block) for name, block in blocks}


@pytest.fixture
def world(make_client):
    world = make_world(make_client())
    world.mode = "detailed"
    return world


def record_like(world, project, **changes):
    """A model row with crafted fields (as an imported record could hold)."""
    with closing(connect(world.client)) as conn:
        base = models.get_model(conn, world.ids[project]["model"])
        fields = {
            "project_id": project,
            "dataset_id": base.dataset_id,
            "job_id": None,
            "name": base.name,
            "task": base.task,
            "target": base.target,
            "best_model": base.best_model,
            "stop_reason": base.stop_reason,
            "storage_prefix": base.storage_prefix,
            "trusted": True,
            "config": base.config,
            "leaderboard": base.leaderboard,
            "trials": base.trials,
            "metrics": base.metrics,
            "importance": base.importance,
        } | changes
        return models.insert_model(conn, **fields).id


# --- the models list ----------------------------------------------------------------------


def test_models_are_listed_best_rated_first(world):
    world.login("vi")
    record_like(world, world.p, name="weak", metrics={"accuracy": 0.4, "logloss": 1.0})
    strong = record_like(world, world.p, name="strong", metrics={"accuracy": 0.99, "logloss": 0.1})
    page = world.client.get(world.path("/projects/{p}/models")).text
    names = re.findall(r'<th scope="row" class="cell-name"><a href="[^"]+">([^<]+)</a>', page)
    assert names.index("strong") < names.index("weak")
    assert re.search(rf'href="{world.path("/projects/{p}/models/")}{strong}"', page)
    stars = re.findall(r'data-stars="(\d)"', page)
    assert stars and all(1 <= int(n) <= 5 for n in stars)
    spec = chart_specs(page)["compare-chart-1"]
    assert spec["type"] == "hbar" and spec["labels"][0] == "strong" and spec["values"][0] == 0.99
    assert ECHARTS in page
    assert "/delete" not in page and "/predict" not in page  # a viewer: read only


def test_editors_get_predict_and_delete(world):
    world.login("co")
    page = world.client.get(world.path("/projects/{p}/models")).text
    assert world.path("/projects/{p}/models/{model}/predict") in page
    assert world.path("/projects/{p}/models/{model}/delete") in page


def test_deleting_a_model(world):
    csrf = world.login("ed")
    model_id = world.ids[world.p]["model"]
    with closing(connect(world.client)) as conn:  # a prediction still waiting for it
        user = conn.execute("SELECT id FROM users WHERE username = 'ed'").fetchone()[0]
        payload = {"model_id": model_id, "dataset_id": world.ids[world.p]["test"], "name": None}
        waiting = store.enqueue(
            conn, "batch_predict", world.p, user, payload | {"include_columns": None}
        )
    r = world.client.post(
        world.path("/projects/{p}/models/{model}/delete"),
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert location(r) == world.path("/projects/{p}/models")
    assert count(world.client, "models", "id = ?", (model_id,)) == 0
    assert world.client.get(world.path("/projects/{p}/models/{model}")).status_code == 404
    assert world.client.get(world.path("/projects/{p}/jobs/") + str(waiting.id)).status_code == 200
    assert world.client.get(world.path("/projects/{p}")).status_code == 200


def test_the_project_export_job(world):
    csrf = world.login("vi")  # readers may export, as in the API
    r = world.client.post(
        world.path("/projects/{p}/models/export"), data={"csrf_token": csrf}, follow_redirects=False
    )
    job_url = location(r)
    page = world.client.get(job_url).text
    assert "Exporting the models" in page and "Trying" not in page
    again = world.client.post(world.path("/projects/{p}/models/export"), data={"csrf_token": csrf})
    assert again.status_code == 409 and "already running" in again.text
    job_id = int(job_url.rsplit("/", 1)[1])
    with closing(connect(world.client)) as conn:
        store.claim_job(conn, job_id, "t")
        store.finish_job(conn, job_id, JobStatus.DONE, result={})
    page = world.client.get(world.path("/projects/{p}/models")).text
    assert f'href="/api/v1/projects/{world.p}/exports/{job_id}"' in page
    fragment = world.client.get(job_url + "/status", headers={"HX-Request": "true"})
    assert fragment.headers["HX-Redirect"] == world.path("/projects/{p}/models#export")


# --- the model page -----------------------------------------------------------------------


@pytest.fixture
def trained(make_client, monkeypatch):
    """A world plus a classification and a regression model trained by the in-process runner
    through the full training form."""
    monkeypatch.delenv("FIONE_JOB_HANDLER_MODULES", raising=False)
    world = make_world(make_client(start_runner=True))
    world.mode = "detailed"
    csrf = world.login("ed")
    rows = "\n".join(f"{i},{(i * 7) % 13},{i * 3 + (i % 5)}" for i in range(80))
    houses = ("a,b,price\n" + rows).encode()
    r = world.client.post(
        world.path("/projects/{p}/datasets"),
        data={"csrf_token": csrf, "kind": "train"},
        files={"file": ("houses.csv", houses, "text/csv")},
        follow_redirects=False,
    )
    houses_id = int(location(r).rsplit("/", 1)[1])
    made = {}
    for name, did, target, inputs in (
        (
            "classification",
            world.ids[world.p]["train"],
            "species",
            ["petal width (cm)", "petal length (cm)"],
        ),
        ("regression", houses_id, "price", ["a", "b"]),
    ):
        form = {
            "csrf_token": csrf,
            "target": target,
            "task": "auto",
            "inputs": inputs,
            "max_runtime_minutes": "1",
            "max_models": str(FAST["max_models"] + 1),
            "nfolds": str(FAST["nfolds"]),
            "seed": "0",
            "stopping_rounds": "3",
            "stopping_metric": "auto",
            "stopping_tolerance": "0.001",
            "sort_metric": "auto",
        }
        r = world.client.post(
            world.path("/projects/{p}/datasets/") + f"{did}/train",
            data=form,
            follow_redirects=False,
        )
        job_id = int(location(r).rsplit("/", 1)[1])
        deadline = time.monotonic() + 90
        while True:
            with closing(connect(world.client)) as conn:
                job = store.get_job(conn, job_id)
            if job.status.value in ("done", "failed", "cancelled"):
                break
            assert time.monotonic() < deadline
            time.sleep(0.3)
        assert job.status == JobStatus.DONE, job.message
        made[name] = job.result["model_id"]
    return world, made


def test_the_model_page_for_trained_models(trained):
    world, made = trained
    for task, model_id in made.items():
        base = world.path("/projects/{p}/models/") + str(model_id)
        page = world.client.get(base).text
        for tab in ("overview", "leaderboard", "importance", "history", "metrics"):
            assert f'id="tab-{tab}"' in page and f'id="panel-{tab}"' in page
        assert re.search(r'aria-label="\d out of 5 stars" data-stars="\d"', page)
        assert "Training settings" in page and "Cross-validation folds" in page
        assert page.count('<th scope="row" class="cell-name">') >= 2  # the leaderboard rows
        assert re.search(r"learning_rate=|n_estimators=|depth=|num_leaves=", page)
        specs = chart_specs(page)
        assert specs["importance-chart"]["type"] == "hbar" and specs["importance-chart"]["values"]
        history = specs["history-chart"]
        assert history["type"] == "scatter" and history["series"] and history["line"]["points"]
        assert "confusion matrix" in page  # the note on what is not stored
        assert "docker run" in page and f"/api/v1/models/{model_id}/serving" in page
        metric = "Accuracy" if task == "classification" else "RMSE"
        assert f'<th scope="row">{metric}</th>' in page
    jobs = world.client.get(world.path("/projects/{p}/jobs")).text
    for model_id in made.values():  # finished training jobs link to their model
        assert world.path("/projects/{p}/models/") + f'{model_id}"' in jobs


def test_tabs_without_stored_data_say_so(world):
    world.login("ed")
    bare = record_like(world, world.p, trials=[], importance={}, leaderboard=[], config={})
    page = world.client.get(world.path("/projects/{p}/models/") + str(bare)).text
    assert (
        page.count("Not stored with this model.") == 4
    )  # settings, leaderboard, importance, history
    assert "history-chart" not in page and "importance-chart" not in page


def test_a_model_page_tab_opens_from_the_url(world):
    world.login("ed")
    page = world.client.get(world.path("/projects/{p}/models/{model}") + "?tab=history").text
    assert 'id="tab-history" aria-controls="panel-history" aria-selected="true"' in page


def test_names_are_escaped_on_the_model_screens(world):
    world.login("admin")
    crafted = record_like(
        world,
        world.p,
        name=XSS,
        best_model=XSS,
        importance={XSS: 0.7, "other": 0.3},
        leaderboard=[
            {
                "model": XSS + "_0",
                "family": XSS,
                "cv_score": 0.1,
                "cv_std": 0.0,
                "train_secs": 1.0,
                "weight": 1.0,
            }
        ],
        trials=[
            {
                "family": XSS,
                "trial": 0,
                "state": "complete",
                "score": 0.2,
                "elapsed": 1.0,
                "params": json.dumps({XSS: 1}),
            }
        ],
    )
    for html in (
        world.client.get(world.path("/projects/{p}/models")).text,
        world.client.get(world.path("/projects/{p}/models/") + str(crafted)).text,
        world.client.get(world.path("/projects/{p}")).text,
    ):
        assert "<img src=x onerror" not in html
        for block in re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', html, re.S):
            assert "</script>" not in block and "<img" not in block
    page = world.client.get(world.path("/projects/{p}/models/") + str(crafted)).text
    assert XSS in chart_specs(page)["importance-chart"]["labels"]
    assert escape(XSS) in page


def test_echarts_only_on_the_model_chart_pages(world):
    world.login("admin")
    for template, charts in (
        ("/projects/{p}/models", True),
        ("/projects/{p}/models/{model}", True),
        ("/projects/{p}/models/import", False),
        ("/projects/{p}/models/{model}/summary", False),
    ):
        assert (ECHARTS in world.client.get(world.path(template)).text) is charts, template
    assert ECHARTS not in world.client.get("/modules").text


# --- export and import --------------------------------------------------------------------


def test_the_export_download_is_the_api_one(world):
    world.login("vi")
    ui = world.client.get(world.path("/projects/{p}/models/{model}/export"))
    api = world.client.get(f"/api/v1/models/{world.ids[world.p]['model']}/export")
    assert ui.status_code == api.status_code == 200
    assert ui.content == api.content
    assert ui.headers["content-disposition"] == api.headers["content-disposition"]


def test_a_failing_export_is_a_clean_error_page(world):
    world.login("ed")
    with closing(connect(world.client)) as conn:
        record = models.get_model(conn, world.ids[world.p]["model"])
    world.client.app.state.storage.delete_prefix(record.storage_prefix)
    r = world.client.get(world.path("/projects/{p}/models/{model}/export"), headers=HTML)
    assert r.status_code == 404 and "text/html" in r.headers["content-type"]
    assert "files are missing" in r.text


def import_zip(world, archive: bytes, project: str, csrf: str, **form):
    return world.client.post(
        f"/projects/{project}/models/import",
        data={"csrf_token": csrf, **form},
        files={"file": ("model.zip", archive, "application/zip")},
        follow_redirects=False,
    )


def test_import_round_trip_through_the_ui(world):
    csrf = world.login("admin")
    archive = world.client.get(world.path("/projects/{p}/models/{model}/export")).content
    before = count(world.client, "models", "project_id = ?", (world.q,))
    r = import_zip(world, archive, world.q, csrf)
    target = location(r)
    assert target.startswith(f"/projects/{world.q}/models/")
    assert count(world.client, "models", "project_id = ?", (world.q,)) == before + 1
    page = world.client.get(target).text
    assert "(imported)" in page and "unverified" not in page  # signed here: trusted


@pytest.mark.parametrize("user", ["ed", "co", "vi", "st"])
def test_only_administrators_may_import(world, user):
    csrf = world.login(user)
    archive = b"PK not really"
    assert world.client.get(world.path("/projects/{p}/models/import")).status_code == 403
    r = import_zip(world, archive, world.p, csrf)
    assert r.status_code == 403 and "Only administrators" in r.text


def test_a_bad_zip_is_a_friendly_error_and_trust_stays_unchecked(world):
    csrf = world.login("admin")
    before = count(world.client, "models")
    r = import_zip(world, b"this is not a zip", world.p, csrf, trust_foreign="true")
    assert r.status_code == 422 and "not a model export Fione can import" in r.text
    assert 'name="trust_foreign" value="true" aria-describedby' in r.text  # rendered unchecked
    assert 'value="true" checked' not in r.text
    assert count(world.client, "models") == before


def test_a_foreign_model_needs_trust(world, make_client, tmp_path):
    other = make_client(tmp_path / "other")  # another installation: another secret
    admin = add_user(other, "root", Role.ADMIN)
    with closing(connect(other)) as conn:
        project = projects.create_project(conn, admin, "Elsewhere")
        record = store_model(conn, other.app.state.storage, other.app.state.secret, project.id)
    login(other, "root")
    archive = other.get(f"/api/v1/models/{record.id}/export").content
    csrf = world.login("admin")
    r = import_zip(world, archive, world.p, csrf)
    assert r.status_code == 422 and "Trust a model from another Fione installation" in r.text
    assert "signature" in r.text
    r = import_zip(world, archive, world.p, csrf, trust_foreign="true")
    page = world.client.get(location(r)).text
    assert "Imported, unverified" in page or "imported from another installation" in page


def test_an_import_over_the_archive_limit_is_413(world, monkeypatch):
    monkeypatch.setattr(routes_models, "MAX_ARCHIVE_BYTES", 1000)
    csrf = world.login("admin")
    r = import_zip(world, b"x" * (2 << 20), world.p, csrf)
    assert r.status_code == 413 and "larger than a model export may be" in r.text


# --- modules ------------------------------------------------------------------------------


def upload_module(client, csrf, module_id="mine", name='"Mine"', acknowledge="yes"):
    data = {"csrf_token": csrf, "id": module_id}
    if acknowledge:
        data["acknowledge"] = acknowledge
    source = MODULE_SOURCE.replace("NAME", name).encode()
    return client.post(
        "/modules/upload",
        data=data,
        files={"file": ("m.py", source, "text/x-python")},
        follow_redirects=False,
    )


@pytest.fixture
def admin_client(make_client):
    client = make_client()
    add_user(client, "admin", Role.ADMIN)
    add_user(client, "ed", Role.EDITOR)
    return client


def test_uploading_listing_and_deleting_a_module(admin_client):
    csrf = login(admin_client, "admin")
    assert location(upload_module(admin_client, csrf)) == "/modules"
    page = admin_client.get("/modules").text
    assert "<code>mine</code>" in page and "Mine" in page and "Uploaded" in page
    assert re.search(r"\d+ B<", page)  # its size
    assert "not sandboxed" in page and "secret key" in page
    r = admin_client.post("/modules/mine/delete", data={"csrf_token": csrf}, follow_redirects=False)
    assert location(r) == "/modules" and count(admin_client, "modules") == 0
    r = admin_client.post("/modules/cbind/delete", data={"csrf_token": csrf})
    assert r.status_code == 422 and "Built-in modules cannot be deleted" in r.text
    r = admin_client.post("/modules/nope/delete", data={"csrf_token": csrf})
    assert r.status_code == 404


def test_a_module_upload_needs_the_acknowledgement(admin_client):
    csrf = login(admin_client, "admin")
    r = upload_module(admin_client, csrf, acknowledge=None)
    assert r.status_code == 422 and "confirm you trust this code" in r.text
    r = upload_module(admin_client, csrf, acknowledge="on")
    assert r.status_code == 422
    assert count(admin_client, "modules") == 0


def test_a_refused_module_says_why(admin_client):
    csrf = login(admin_client, "admin")
    r = admin_client.post(
        "/modules/upload",
        data={"csrf_token": csrf, "id": "broken", "acknowledge": "yes"},
        files={"file": ("m.py", b"def (:\n", "text/x-python")},
    )
    assert r.status_code == 422 and "could not be added" in r.text and "syntax error" in r.text


def test_non_admins_read_the_module_list_only(admin_client):
    csrf = login(admin_client, "ed")
    page = admin_client.get("/modules").text
    assert "cbind" in page and "/modules/upload" not in page and "/delete" not in page
    assert admin_client.get("/modules/upload").status_code == 403
    r = upload_module(admin_client, csrf)
    assert r.status_code == 403 and count(admin_client, "modules") == 0


def test_the_module_warning_in_japanese(admin_client):
    login(admin_client, "admin")
    for path in ("/modules", "/modules/upload"):
        page = admin_client.get(path, headers={"Accept-Language": "ja"}).text
        assert "サンドボックス化されていません" in page and "秘密鍵" in page


def test_module_names_are_escaped(admin_client):
    csrf = login(admin_client, "admin")
    assert upload_module(admin_client, csrf, name=json.dumps(XSS)).status_code == 303
    page = admin_client.get("/modules").text
    assert "<img src=x onerror" not in page and escape(XSS) in page


# --- the simple / detailed view -------------------------------------------------------------


def test_the_view_preference_round_trip(make_client):
    world = make_world(make_client())
    csrf = world.login("ed")
    dashboard = world.path("/projects/{p}")
    page = world.client.get(dashboard).text
    assert ">Overview</a>" in page and ">Models</a>" not in page and ">Jobs</a>" not in page
    r = world.client.post(
        "/ui/mode",
        data={"csrf_token": csrf, "mode": "detailed", "next": dashboard},
        follow_redirects=False,
    )
    assert location(r) == dashboard and "fione_mode=detailed" in r.headers["set-cookie"]
    assert "HttpOnly" in r.headers["set-cookie"] and "SameSite=lax" in r.headers["set-cookie"]
    page = world.client.get(dashboard).text
    assert ">Models</a>" in page and ">Jobs</a>" in page
    assert 'name="mode" value="detailed" aria-pressed="true"' in page
    r = world.client.post(
        "/ui/mode",
        data={"csrf_token": csrf, "mode": "expert", "next": "//evil.example"},
        follow_redirects=False,
    )
    assert location(r) == "/" and "set-cookie" not in r.headers  # ignored; next made safe
    assert world.client.post("/ui/mode", data={"mode": "simple"}).status_code == 403  # no CSRF


def test_simple_hides_the_advanced_links(make_client):
    world = make_world(make_client())
    world.login("ed")
    analysis = world.client.get(world.path("/projects/{p}/datasets/{train}/analyze")).text
    summary = world.client.get(world.path("/projects/{p}/models/{model}/summary")).text
    assert "/train?target=" not in analysis and "Open advanced details" not in summary
    assert ">Jobs</a>" not in analysis
    world.mode = "detailed"
    world.login("ed")
    summary = world.client.get(world.path("/projects/{p}/models/{model}/summary")).text
    assert "Open advanced details" in summary


def test_the_view_does_not_change_what_is_allowed(make_client, tmp_path):
    statuses = {}
    for mode in ("simple", "detailed"):
        world = make_world(make_client(tmp_path / mode))
        world.mode = mode
        world.login("vi")
        statuses[mode] = [
            world.client.get(world.path(t), follow_redirects=False).status_code
            for t in (
                "/projects/{p}/models",
                "/projects/{p}/models/{model}",
                "/projects/{p}/jobs",
                "/projects/{p}/datasets/{train}/train",
                "/projects/{p}/models/import",
                "/projects/{p}/datasets",
                "/projects/{p}/datasets/{train}/analyze",
            )
        ]
    assert statuses["simple"] == statuses["detailed"] == [200, 200, 200, 403, 403, 200, 200]


def test_a_section_reached_in_simple_view_stays_marked(make_client):
    world = make_world(make_client())
    world.login("ed")
    page = world.client.get(world.path("/projects/{p}/jobs")).text
    assert 'aria-current="page">Jobs</a>' in page


def test_error_pages_for_model_failures_are_html(world):
    world.login("admin")
    for template in ("/projects/{p}/models/999999", "/projects/{p}/models/abc/export"):
        r = world.client.get(world.path(template), headers=HTML)
        assert r.status_code == 404 and "text/html" in r.headers["content-type"], template


def test_the_wizard_trained_summary_links_to_the_model_page(world):
    world.login("ed")
    page = world.client.get(world.path("/projects/{p}/models/{model}/summary")).text
    assert f'href="{world.path("/projects/{p}/models/{model}")}"' in page
    dashboard = world.client.get(world.path("/projects/{p}")).text
    assert f'href="{world.path("/projects/{p}/models/{model}")}"' in dashboard
