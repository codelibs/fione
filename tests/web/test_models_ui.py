"""The model screens (leaderboard, model page, export and import), the Python modules screens
and the simple/detailed view preference."""

import io
import json
import re
import time
from contextlib import closing
from functools import cache
from html import escape, unescape

import numpy as np
import pytest

from api_helpers import add_user, connect, iris_frame, login, store_model, tiny_model
from fione.api import routes_models
from fione.auth import service as auth_service
from fione.auth.roles import Role
from fione.engine.diagnostics import diagnostics
from fione.jobs import store
from fione.jobs.explain_handler import build_explanation
from fione.jobs.store import JobStatus
from fione.models import explanations
from fione.models import service as models
from fione.modules import service as modules_service
from fione.projects import service as projects
from fione.projects.ingest import ingest_csv
from fione.projects.service import DatasetType
from fione.web import models_ui
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
        assert "not shown" not in page  # trained here: the diagnostics are stored
        if task == "classification":
            assert 'class="table table-compact confusion"' in page
        else:
            assert {"residual-chart", "scatter-chart"} <= set(specs)
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
    model_id = int(location(r).rsplit("/", 1)[1])
    with closing(connect(world.client)) as conn:
        assert models.get_model(conn, model_id).trusted == 0
    page = world.client.get(location(r)).text
    assert "imported from another installation" in page


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
    assert "/train?target=" not in analysis
    assert "Open advanced details" in summary  # ruling: the summary's link is in both views
    dashboard = world.client.get(world.path("/projects/{p}")).text
    assert world.path("/projects/{p}/models/{model}") + '"' not in dashboard  # Details link
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


@pytest.mark.parametrize("token", [None, "wrong"])
@pytest.mark.parametrize(
    "kind", ["import", "module_upload", "module_delete", "model_delete", "export_all"]
)
def test_posts_without_the_csrf_token_change_nothing(world, kind, token):
    world.login("admin")
    with closing(connect(world.client)) as conn:
        user = next(u for u in auth_service.list_users(conn) if u.username == "admin")
        modules_service.upload_module(
            conn,
            world.client.app.state.storage,
            user,
            "mine",
            (MODULE_SOURCE.replace("NAME", '"Mine"')).encode(),
        )
    before = (
        count(world.client, "models"),
        count(world.client, "modules"),
        count(world.client, "jobs"),
    )
    data = {"csrf_token": token} if token else {}
    if kind == "import":
        archive = world.client.get(world.path("/projects/{p}/models/{model}/export")).content
        r = world.client.post(
            world.path("/projects/{p}/models/import"),
            data=data,
            files={"file": ("m.zip", archive, "application/zip")},
        )
    elif kind == "module_upload":
        source = MODULE_SOURCE.replace("NAME", '"Other"').encode()
        r = world.client.post(
            "/modules/upload",
            data=data | {"id": "other", "acknowledge": "yes"},
            files={"file": ("m.py", source, "text/x-python")},
        )
    elif kind == "module_delete":
        r = world.client.post("/modules/mine/delete", data=data)
    elif kind == "model_delete":
        r = world.client.post(world.path("/projects/{p}/models/{model}/delete"), data=data)
    else:
        r = world.client.post(world.path("/projects/{p}/models/export"), data=data)
    assert r.status_code == 403 and "text/html" in r.headers["content-type"]
    after = (
        count(world.client, "models"),
        count(world.client, "modules"),
        count(world.client, "jobs"),
    )
    assert after == before


@pytest.mark.parametrize("kind", ["import", "module_upload"])
def test_cross_site_uploads_are_refused_before_they_are_read(world, kind):
    csrf = world.login("admin")
    evil = {"Origin": "https://evil.example"}
    before = (count(world.client, "models"), count(world.client, "modules"))
    if kind == "import":
        archive = world.client.get(world.path("/projects/{p}/models/{model}/export")).content
        r = world.client.post(
            world.path("/projects/{p}/models/import"),
            data={"csrf_token": csrf},
            files={"file": ("m.zip", archive, "application/zip")},
            headers=evil,
        )
    else:
        source = MODULE_SOURCE.replace("NAME", '"Other"').encode()
        r = world.client.post(
            "/modules/upload",
            data={"csrf_token": csrf, "id": "other", "acknowledge": "yes"},
            files={"file": ("m.py", source, "text/x-python")},
            headers=evil,
        )
    assert r.status_code == 403
    assert (count(world.client, "models"), count(world.client, "modules")) == before


def test_the_export_busy_page_keeps_the_switches_on_a_page(world):
    csrf = world.login("vi")
    world.client.post(world.path("/projects/{p}/models/export"), data={"csrf_token": csrf})
    r = world.client.post(world.path("/projects/{p}/models/export"), data={"csrf_token": csrf})
    assert r.status_code == 409
    nexts = re.findall(r'<input type="hidden" name="next" value="([^"]+)">', r.text)
    assert nexts and set(nexts) == {world.path("/projects/{p}/models")}


def test_export_and_module_jobs_are_linked_from_the_job_list(world):
    csrf = world.login("vi")
    r = world.client.post(
        world.path("/projects/{p}/models/export"), data={"csrf_token": csrf}, follow_redirects=False
    )
    page = world.client.get(world.path("/projects/{p}/jobs")).text
    assert f'href="{location(r)}"' in page


def test_the_model_page_caps_what_it_shows(world):
    """Imported or old records can hold anything: the page shows bounded slices."""
    world.login("ed")
    trials = [
        {
            "family": "LightGBM",
            "trial": i,
            "state": "complete",
            "score": 1 / (i + 1),
            "elapsed": 0.1,
            "params": "{}",
        }
        for i in range(2500)
    ]
    board = [
        {
            "model": f"LightGBM_{i}",
            "family": "LightGBM",
            "cv_score": 0.1,
            "cv_std": 0.0,
            "train_secs": 1.0,
            "weight": 0.0,
        }
        for i in range(60)
    ]
    importance = {f"f{i}": 1 / 50 for i in range(50)}
    big = record_like(world, world.p, trials=trials, leaderboard=board, importance=importance)
    page = world.client.get(world.path("/projects/{p}/models/") + str(big)).text
    specs = chart_specs(page)
    history = specs["history-chart"]
    points = sum(len(series["points"]) for series in history["series"])
    assert points == len(history["values"]) == 2000
    assert len(specs["importance-chart"]["labels"]) == 20
    panel = page[page.index('id="panel-leaderboard"') : page.index('id="panel-importance"')]
    assert panel.count('<th scope="row" class="cell-name">') == 50


# --- the metrics tab: training-time diagnostics ---------------------------------------------


def binary_diagnostics(labels=("no", "yes"), n=400) -> dict:
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, n)
    p1 = np.clip(0.3 * y + rng.random(n) * 0.7, 0, 1)
    return diagnostics("classification", y, np.column_stack([1 - p1, p1]), list(labels))


def diagnostics_page(world, **changes) -> str:
    world.login("vi")
    mid = record_like(world, world.p, **changes)
    r = world.client.get(world.path("/projects/{p}/models/") + f"{mid}?tab=metrics")
    assert r.status_code == 200
    return r.text


def metrics_panel(page: str) -> str:
    return page[page.index('id="panel-metrics"') :]


COLUMN_HEAD = r'<th scope="col" class="cell-name" title="[^"]*">([^<]+)</th>'


def confusion_table(page: str) -> str:
    table = page[page.index('class="table table-compact confusion"') :]
    return table[: table.index("</table>")]


def test_binary_diagnostics_render(world):
    found = binary_diagnostics()
    page = diagnostics_page(world, diagnostics=found)
    panel = metrics_panel(page)
    table = confusion_table(page)
    assert re.findall(COLUMN_HEAD, table) == ["no", "yes"]
    assert re.findall(r'<th scope="row" class="cell-name">([^<]+)</th>', table) == ["no", "yes"]
    counts = [int(n) for n in re.findall(r'<span class="cm-count">(\d+)</span>', table)]
    assert counts == [n for row in found["confusion"]["matrix"] for n in row]
    assert re.findall(r'class="num cm-[0-5]"', table)
    specs = chart_specs(page)
    for name in ("roc-chart", "pr-chart", "calibration-chart"):
        assert specs[name]["type"] == "lines" and specs[name]["series"][0]["points"]
    roc = specs["roc-chart"]
    assert roc["series"][0]["points"] == [
        [x, y] for x, y in zip(found["roc"]["fpr"], found["roc"]["tpr"], strict=True)
    ]
    assert roc["series"][1]["faint"] is True  # the chance diagonal
    assert "yes" in roc["label"]  # the positive class is named
    assert "per-class" in panel.lower() and "Precision" in panel
    assert "residual-chart" not in specs
    assert ECHARTS in page


def test_multiclass_has_no_roc_and_shows_other_beyond_30(world):
    rng = np.random.default_rng(1)
    k, n = 40, 4000
    y = rng.integers(0, k, n)
    pred = rng.random((n, k))
    pred[np.arange(n), y] += 0.5
    pred /= pred.sum(1, keepdims=True)
    found = diagnostics("classification", y, pred, [f"c{i}" for i in range(k)])
    page = diagnostics_page(world, diagnostics=found)
    table = confusion_table(page)
    heads = re.findall(COLUMN_HEAD, table)
    assert len(heads) == 31 and heads[-1] == "Other classes"
    assert table.count('<th scope="row" class="cell-name">') == 31
    specs = chart_specs(page)
    assert not {"roc-chart", "pr-chart", "calibration-chart"} & set(specs)


def test_regression_shows_residuals_and_scatter(world):
    rng = np.random.default_rng(2)
    y = rng.normal(100, 10, 3000)
    found = diagnostics("regression", y, y + rng.normal(0, 2, 3000), None)
    page = diagnostics_page(world, task="regression", diagnostics=found)
    specs = chart_specs(page)
    residual = specs["residual-chart"]
    assert residual["type"] == "bar" and residual["values"] == found["residuals"]["counts"]
    scatter = specs["scatter-chart"]
    assert scatter["type"] == "scatter"
    points = scatter["series"][0]["points"]
    assert len(points) == 2000 == len(found["points"]["actual"])
    assert points[0] == [found["points"]["actual"][0], found["points"]["predicted"][0]]
    assert scatter["line"]["step"] is False  # the y = x diagonal is straight
    assert "2,000" in scatter["label"] and "random order" in scatter["label"]
    assert "confusion" not in metrics_panel(page)


def test_phase1_model_shows_the_missing_note(world):
    page = diagnostics_page(world)  # record_like stores no diagnostics, as Phase 1 did
    assert "trained before Fione kept" in metrics_panel(page)
    assert "cannot be read" not in page
    assert not {"roc-chart", "residual-chart"} & set(chart_specs(page))


@pytest.mark.parametrize(
    "bad",
    [
        {"task": "classification", "confusion": "x"},
        {"version": 1, "task": "classification", "labels": "ab", "confusion": {"matrix": 1}},
        {
            "version": 1,
            "task": "classification",
            "labels": ["a", "b"],
            "confusion": {"classes": [0, 7], "matrix": [[1, 2], [3, 4]]},
            "per_class": [{"class": True, "precision": "x", "support": -1}],
            "roc": {"fpr": [0, 2.0], "tpr": [0], "threshold": None},
            "pr": {"precision": [None, None], "recall": [0, 1]},
            "calibration": [{"predicted": "a"}, 3],
        },
        {"version": 1, "task": "regression", "residuals": {"edges": [0, 1], "counts": [1, 2]}},
        {"version": 1, "task": "classification", "confusion": {"classes": [0], "matrix": [[1]]}},
        {"version": 2, "task": "classification"},
        {"version": 1, "task": "classification", "labels": [{"a": 1}, []], "per_class": "x"},
    ],
)
def test_malformed_diagnostics_do_not_break_the_page(world, bad):
    page = diagnostics_page(world, diagnostics=bad)
    assert "cannot be read" in metrics_panel(page)
    assert not {"roc-chart", "pr-chart", "calibration-chart"} & set(chart_specs(page))


@pytest.mark.parametrize("text", ["[1, 2]", '"x"', "null", "7"])
def test_diagnostics_json_that_is_not_an_object(world, text):
    world.login("vi")
    mid = record_like(world, world.p)
    with closing(connect(world.client)) as conn:
        conn.execute("UPDATE models SET diagnostics_json = ? WHERE id = ?", (text, mid))
        conn.commit()
    r = world.client.get(world.path("/projects/{p}/models/") + f"{mid}?tab=metrics")
    assert r.status_code == 200
    assert ("cannot be read" in r.text) is (text != "null")


def test_a_malformed_part_leaves_the_others(world):
    found = binary_diagnostics()
    found["roc"] = {"fpr": "broken"}
    page = diagnostics_page(world, diagnostics=found)
    specs = chart_specs(page)
    assert "roc-chart" not in specs and "pr-chart" in specs
    assert "cannot be read" not in page


def test_hostile_label_is_escaped(world):
    hostile = "<script>alert(1)</script>"
    page = diagnostics_page(world, diagnostics=binary_diagnostics(("ok", hostile)))
    assert "<script>alert" not in page and escape(hostile) in page
    for block in re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', page, re.S):
        assert "<" not in block
    assert hostile in chart_specs(page)["roc-chart"]["label"]


def test_every_chart_spec_has_matching_labels_and_values(world):
    rng = np.random.default_rng(3)
    y = rng.normal(0, 1, 500)
    for task, found in (
        ("classification", binary_diagnostics()),
        ("regression", diagnostics("regression", y, y * 0.9, None)),
    ):
        page = diagnostics_page(world, task=task, diagnostics=found)
        specs = chart_specs(page)
        assert specs
        for name, spec in specs.items():
            assert len(spec["labels"]) == len(spec["values"]) > 0, name
            assert all(isinstance(label, str) for label in spec["labels"]), name


def test_no_inline_style_attributes(world):
    page = diagnostics_page(world, diagnostics=binary_diagnostics())
    assert not re.search(r"<[^>]+\sstyle=", page)
    assert not re.search(r"<script(?![^>]*\ssrc=)(?![^>]*application/json)[^>]*>", page)


@pytest.mark.parametrize(
    "share,level",
    [(0.0, 0), (0.01, 1), (0.1, 1), (0.11, 2), (0.25, 2), (0.5, 3), (0.75, 4), (0.76, 5), (1, 5)],
)
def test_confusion_shades_bucket_the_row_share(share, level):
    assert models_ui._level(share) == level


def test_undefined_figures_and_japanese(world):
    y = np.array([0, 0, 1, 1, 2, 2])
    pred = np.eye(3)[[0, 0, 0, 1, 0, 1]]  # class 2 is never predicted
    found = diagnostics("classification", y, pred, ["a", "b", "c"])
    world.login("vi")
    mid = record_like(world, world.p, diagnostics=found)
    url = world.path("/projects/{p}/models/") + f"{mid}?tab=metrics"
    page = world.client.get(url).text
    rows = re.findall(r'<th scope="row" class="cell-name">c</th>(.*?)</tr>', page, re.S)
    assert rows and "—" in rows[-1]  # c's precision: never predicted
    ja = world.client.get(url, headers={"Accept-Language": "ja"}).text
    assert "混同行列" in ja and "クラス別の値" in ja


# --- fix round 1: hostile numbers, shares, the scatter's text alternative ------------------


def test_numbers_beyond_the_float_range_do_not_break_the_pages(world):
    """Rows written before the import refused them (or by hand) may hold integers no float
    can hold: every page still renders, leaving those values out."""
    huge = 10**400
    found = binary_diagnostics()
    found["auc"] = huge
    found["pr"]["recall"][1] = huge
    world.login("vi")
    mid = record_like(
        world,
        world.p,
        metrics={"accuracy": huge, "logloss": -huge},
        importance={"x": huge, "y": 0.5},
        leaderboard=[{"model": "LightGBM_0", "family": "LightGBM", "cv_score": huge}],
        diagnostics=found,
    )
    base = world.path("/projects/{p}/models/") + str(mid)
    for url in (
        base,
        base + "/summary",
        world.path("/projects/{p}/models"),
        world.path("/projects/{p}"),
    ):
        assert world.client.get(url).status_code == 200, url
    page = world.client.get(base + "?tab=metrics").text
    specs = chart_specs(page)
    assert "pr-chart" not in specs and "roc-chart" in specs
    assert "could not be read" in page and "Area under the curve: —." in page


def test_an_unexpected_error_in_a_part_only_drops_that_part(world, monkeypatch):
    def broken(*args):
        raise TypeError("unexpected")

    monkeypatch.setattr(models_ui, "_calibration", broken)
    page = diagnostics_page(world, diagnostics=binary_diagnostics())
    specs = chart_specs(page)
    assert "calibration-chart" not in specs and "roc-chart" in specs
    assert "could not be read" in page


def test_a_rate_out_of_range_drops_its_curve(world):
    found = binary_diagnostics()
    found["roc"] = {"fpr": [0.0, 0.5, 1.0], "tpr": [0.0, 1.5, 1.0], "threshold": [1, 0.5, 0]}
    specs = chart_specs(diagnostics_page(world, diagnostics=found))
    assert "roc-chart" not in specs and "pr-chart" in specs


def test_confusion_shares_are_of_the_actual_class_row(world):
    found = binary_diagnostics(("a", "b"))
    found["confusion"] = {"classes": [0, 1], "matrix": [[1, 299], [50, 50]]}
    table = confusion_table(diagnostics_page(world, diagnostics=found))
    cells = re.findall(
        r'<td class="num cm-(\d)"><span class="cm-count">([\d,]+)</span>'
        r'<span class="cm-share">([^<]+)</span>',
        table,
    )
    assert cells == [
        ("1", "1", "&lt;1%"),
        ("5", "299", "&gt;99%"),
        ("3", "50", "50%"),
        ("3", "50", "50%"),
    ]


def test_long_class_labels_keep_their_full_text_in_a_title(world):
    long = "a very long class label " * 4
    page = diagnostics_page(world, diagnostics=binary_diagnostics(("short", long)))
    table = confusion_table(page)
    assert f'<th scope="col" class="cell-name" title="{long}">{long}</th>' in table


def test_the_scatter_text_alternative_is_the_decile_summary(world):
    rng = np.random.default_rng(4)
    y = 1_000_000 + rng.normal(0, 50, 3000)
    found = diagnostics("regression", y, y + rng.normal(0, 5, 3000), None)
    page = diagnostics_page(world, task="regression", diagnostics=found)
    scatter = chart_specs(page)["scatter-chart"]
    deciles = found["by_decile"]
    assert scatter["labels"] == [str(row["predicted_mean"]) for row in deciles]
    assert scatter["values"] == [row["residual_mean"] for row in deciles]
    assert len(set(scatter["labels"])) == 10  # not all "1e+06"
    assert len(scatter["series"][0]["points"]) == 2000  # the chart still draws every point
    figure = page[page.index('id="scatter-chart"') :]
    figure = figure[: figure.index("</figure>")]
    assert "Mean residual" in figure and figure.count("<tr>") == 11


# --- the Explain tab and the partial dependence fragment -----------------------------------

IRIS_COLUMNS = ["sepal length (cm)", "sepal width (cm)", "petal length (cm)", "petal width (cm)"]


@cache
def iris_explanation() -> dict:
    """The explain job's payload for the tiny iris model (the real schema)."""
    return build_explanation(tiny_model(), iris_frame(), lambda: False)


def store_explanation(world, model_id: int, payload=None, *, text: str | None = None) -> None:
    payload = iris_explanation() if payload is None else payload
    with closing(connect(world.client)) as conn:
        if text is None:
            explanations.save_explanation(conn, model_id, None, None, payload)
        else:  # stored as it is, as a hand-edited or imported row could be
            conn.execute(
                "INSERT INTO model_explanations (model_id, payload_json, created_at)"
                " VALUES (?, ?, ?)",
                (model_id, text, time.time()),
            )


def explain_job(world, model_id: int, status=None, message=None) -> int:
    with closing(connect(world.client)) as conn:
        user = conn.execute("SELECT id FROM users WHERE username = 'ed'").fetchone()[0]
        job = store.enqueue(conn, "explain", world.p, user, {"model_id": model_id})
        if status is not None:
            store.claim_job(conn, job.id, "t")
            if status != JobStatus.RUNNING:
                store.finish_job(conn, job.id, status, message=message)
        return job.id


def inline_specs(html: str) -> dict[str, dict]:
    """The chart specs carried in data-chart-spec attributes (charts in swapped fragments)."""
    found = re.findall(r"id=\"([^\"]+)\" data-chart-spec='([^']*)'", html)
    return {name: json.loads(unescape(text)) for name, text in found}


def explain_panel(page: str) -> str:
    panel = page[page.index('id="panel-explain"') :]
    return panel[: panel.index('id="panel-history"')]


class UseSpy:
    """Stands in for ``LiveModels.use``: counts the calls, then lets them through."""

    def __init__(self, live):
        self.live, self.calls, self.real = live, 0, live.use

    def __call__(self, record):
        self.calls += 1
        return self.real(record)


@pytest.fixture
def spy(world):
    live = world.client.app.state.live_models
    found = UseSpy(live)
    live.use = found
    return found


def pd_fragment(world, model_id, **params):
    url = world.path("/projects/{p}/models/") + f"{model_id}/explain/pd"
    r = world.client.get(url, params=params, headers={"HX-Request": "true"})
    assert r.status_code == 200, r.text
    assert "<html" not in r.text
    return r.text


@pytest.mark.parametrize("persona", ["co", "vi"])
@pytest.mark.parametrize("state", ["none", "queued", "done", "failed"])
def test_explain_tab_states(world, spy, state, persona):
    model = world.ids[world.p]["model"]
    job = None
    if state == "queued":
        job = explain_job(world, model)
    elif state == "done":
        store_explanation(world, model)
    elif state == "failed":
        job = explain_job(world, model, JobStatus.FAILED, "the dataset no longer exists\n/srv/x")
    world.login(persona)
    page = world.client.get(world.path("/projects/{p}/models/{model}") + "?tab=explain").text
    assert 'id="tab-explain" aria-controls="panel-explain" aria-selected="true"' in page
    panel = explain_panel(page)
    texts = {
        "none": "This model has no explanation yet.",
        "queued": "An explanation is waiting to start.",
        "done": "Which inputs matter most",
        "failed": "The last explanation run failed.",
    }
    assert texts[state] in panel
    for other in set(texts) - {state, "done"}:
        assert texts[other] not in panel
    if job is not None:
        assert world.path('href="/projects/{p}/jobs/') + f'{job}"' in panel
    if state == "failed":
        assert "the dataset no longer exists" in panel and "/srv/x" not in panel
    if state == "done":
        specs = chart_specs(page)
        shares = {s["share"] for s in iris_explanation()["importance"]}
        assert specs["contrib-chart"]["type"] == "hbar"
        assert set(specs["contrib-chart"]["labels"]) <= set(IRIS_COLUMNS)
        assert sorted(specs["contrib-chart"]["values"]) == sorted(round(s * 100, 2) for s in shares)
        first = iris_explanation()["partial_dependence"][0]
        pd_spec = inline_specs(panel)["pd-chart"]
        assert pd_spec["type"] == "lines" and first["column"] in pd_spec["label"]
    form = 'action="' + world.path("/projects/{p}/models/{model}") + '/explain"'
    assert (form in panel) is (persona == "co")
    assert spy.calls == 0  # a page view never loads the model


def test_precomputed_pd_does_not_load_the_model(world, spy):
    model = world.ids[world.p]["model"]
    store_explanation(world, model)
    curve = iris_explanation()["partial_dependence"][1]
    world.login("vi")
    html = pd_fragment(world, model, column=curve["column"])
    spec = inline_specs(html)["pd-chart"]
    average = spec["series"][0]["points"]
    output = curve["ice_output"]
    assert [y for _, y in average] == [round(row[output] * 100, 4) for row in curve["average"]]
    assert sum(1 for s in spec["series"] if s.get("faint")) == len(curve["ice"])
    assert "From the stored explanation" in html
    other = (output + 1) % len(curve["outputs"])
    html = pd_fragment(world, model, column=curve["column"], **{"class": str(other)})
    spec = inline_specs(html)["pd-chart"]
    assert not any(s.get("faint") for s in spec["series"])  # ICE is stored for one class
    assert f'<option value="{other}" selected>' in html
    assert spy.calls == 0


def test_other_column_pd_is_computed(world, spy):
    trained_on = record_like(world, world.p, dataset_id=world.ids[world.p]["train"])
    payload = dict(iris_explanation())
    stored = payload["partial_dependence"][0]
    payload["partial_dependence"] = [stored]
    store_explanation(world, trained_on, payload)
    other = next(c for c in IRIS_COLUMNS if c != stored["column"])
    world.login("vi")
    html = pd_fragment(world, trained_on, column=other, **{"class": "2"})
    spec = inline_specs(html)["pd-chart"]
    assert spec["x_type"] == "value" and len(spec["series"][0]["points"]) >= 2
    assert "virginica" in spec["y_name"]
    assert sum(1 for s in spec["series"] if s.get("faint")) == 50  # the requested class's rows
    assert "Computed just now from 150 rows of iris" in html
    assert "can differ from the stored" in html
    assert spy.calls == 1


def test_pd_messages_instead_of_errors(world, spy):
    model = world.ids[world.p]["model"]  # no training data
    world.login("vi")
    assert "Choose a column" in pd_fragment(world, model)
    assert "does not use that column" in pd_fragment(world, model, column="nope")
    html = pd_fragment(world, model, column=IRIS_COLUMNS[0])
    assert "training data is no longer available" in html
    assert spy.calls == 0


def test_pd_busy_message(world):
    trained_on = record_like(world, world.p, dataset_id=world.ids[world.p]["train"])
    live = world.client.app.state.live_models
    live.wait_secs = 0.05
    world.login("vi")
    assert live.slot.acquire(timeout=1)
    try:
        html = pd_fragment(world, trained_on, column=IRIS_COLUMNS[0])
    finally:
        live.slot.release()
    assert "Another explanation is being computed right now" in html
    assert "pd-chart" not in html


def test_untrusted_model_is_not_loaded_in_the_web_process(world, spy):
    foreign = record_like(world, world.p, dataset_id=world.ids[world.p]["train"], trusted=False)
    with closing(connect(world.client)) as conn:  # a prediction made with it
        user = conn.execute("SELECT id FROM users WHERE username = 'ed'").fetchone()[0]
        payload = {"model_id": foreign, "dataset_id": world.ids[world.p]["test"]}
        job = store.enqueue(conn, "batch_predict", world.p, user, payload)
        store.claim_job(conn, job.id, "t")
        store.finish_job(conn, job.id, JobStatus.DONE, result={"dataset_id": payload["dataset_id"]})
    world.login("ed")
    html = pd_fragment(world, foreign, column=IRIS_COLUMNS[0])
    assert "imported without this server&#39;s signature" in html
    why = world.client.get(world.path("/projects/{p}/jobs/") + f"{job.id}/result/why")
    assert why.status_code == 200
    assert "imported without this server&#39;s signature" in why.text
    assert spy.calls == 0


def test_hostile_column_names_are_escaped(world, spy):
    payload = json.loads(json.dumps(iris_explanation()))
    first = payload["partial_dependence"][0]
    quoted = "O'Brien</script>"  # the attribute holding the spec is single-quoted
    first.update(column=XSS, kind="category", grid=[XSS, quoted, None], outputs=[XSS, "y", "z"])
    first["average"] = first["average"][:3]
    first["ice"] = [row[:3] for row in first["ice"]]
    payload["importance"][0]["column"] = XSS
    crafted = record_like(world, world.p, importance={XSS: 0.5, "b": 0.5})
    store_explanation(world, crafted, payload)
    world.login("vi")
    page = world.client.get(world.path("/projects/{p}/models/") + f"{crafted}?tab=explain").text
    fragment = pd_fragment(world, crafted, column=XSS)
    for html in (page, fragment):
        assert "<img src=x onerror" not in html
        spec = inline_specs(html)["pd-chart"]
        assert spec["categories"][:2] == [XSS, quoted] and XSS in spec["label"]
        assert "O'Brien" not in html
    assert XSS in chart_specs(page)["contrib-chart"]["labels"]
    assert escape(XSS) in page
    assert spy.calls == 0


def test_a_one_point_grid_and_a_trimmed_payload_still_show(world):
    payload = json.loads(json.dumps(iris_explanation()))
    payload["importance"] = payload["importance"][:1]  # trimmed: shares no longer sum to 1
    first = payload["partial_dependence"][0]
    first.update(grid=[1.5], average=first["average"][:1], ice=[r[:1] for r in first["ice"]])
    payload["partial_dependence"] = [first]
    model = world.ids[world.p]["model"]
    store_explanation(world, model, payload)
    world.login("vi")
    page = world.client.get(world.path("/projects/{p}/models/{model}") + "?tab=explain").text
    spec = inline_specs(explain_panel(page))["pd-chart"]
    assert spec["series"][0]["points"][0][0] == 1.5 and len(spec["series"][0]["points"]) == 1
    assert len(chart_specs(page)["contrib-chart"]["values"]) == 1


@pytest.mark.parametrize(
    "text",
    [
        '{"version": 1}',
        '{"version": 1, "importance": "x", "partial_dependence": 7}',
        '{"version": 1, "importance": [{"column": 1, "share": 0.5}, {"column": "a", "share": '
        + "9" * 400
        + '}], "partial_dependence": [{"column": "a"}, {"column": "a", "kind": "numeric", '
        '"grid": [1, 2], "outputs": ["x"], "average": [[0.1], ["y"]], "ice_output": 0, '
        '"ice": []}]}',
        '{"version": 1, "importance": [], "partial_dependence": [{"column": "a", "kind": '
        '"numeric", "grid": [1, 2], "outputs": ["x"], "average": [[0.1], [0.2]], '
        '"ice_output": 5, "ice": [[1]]}]}',
        '{"version": 2}',
        "not json",
    ],
)
def test_malformed_explanations_never_break_the_tab(world, spy, text):
    model = world.ids[world.p]["model"]
    store_explanation(world, model, text=text)
    world.login("vi")
    r = world.client.get(world.path("/projects/{p}/models/{model}") + "?tab=explain")
    assert r.status_code == 200
    html = pd_fragment(world, model, column="a")
    assert "does not use that column" in html  # the stored curve is never trusted alone
    assert spy.calls == 0


def recompute(world, model_id, data, **headers):
    url = world.path("/projects/{p}/models/") + f"{model_id}/explain"
    return world.client.post(url, data=data, headers=headers, follow_redirects=False)


def test_recompute_needs_csrf_and_same_origin(world):
    model = world.ids[world.p]["model"]
    train = str(world.ids[world.p]["train"])
    csrf = world.login("co")
    before = count(world.client, "jobs")
    for data, headers in (
        ({"dataset_id": train}, {}),
        ({"dataset_id": train, "csrf_token": "wrong"}, {}),
        ({"dataset_id": train, "csrf_token": csrf}, {"Origin": "https://evil.example"}),
    ):
        r = recompute(world, model, data, **headers)
        assert r.status_code == 403 and "text/html" in r.headers["content-type"]
    assert count(world.client, "jobs") == before
    r = recompute(world, model, {"dataset_id": train, "csrf_token": csrf})
    assert location(r) == world.path("/projects/{p}/models/{model}") + "?tab=explain"
    with closing(connect(world.client)) as conn:
        job = explanations.latest_explain_job(conn, model)
    assert job.payload == {"model_id": model, "dataset_id": int(train)}
    csrf = world.login("vi")
    r = recompute(world, model, {"dataset_id": train, "csrf_token": csrf})
    assert r.status_code == 403


def test_imported_model_recompute_offers_a_dataset_choice(world):
    """The model has no training data: the datasets holding its columns are offered, and
    a post without one is refused on the page."""
    model = world.ids[world.p]["model"]
    with closing(connect(world.client)) as conn:
        other = ingest_csv(
            world.client.app.state.storage,
            conn,
            world.p,
            "unrelated",
            DatasetType.TRAIN,
            io.BytesIO(b"a,b\n1,2\n"),
        )
    csrf = world.login("co")
    page = world.client.get(world.path("/projects/{p}/models/{model}") + "?tab=explain").text
    select = re.search(r'<select[^>]*name="dataset_id".*?</select>', page, re.S).group(0)
    offered = set(re.findall(r'<option value="(\d+)"', select))
    ids = world.ids[world.p]
    assert offered == {str(ids["train"]), str(ids["test"]), str(ids["test"] + 1)}
    assert str(other.id) not in offered and 'value=""' not in select
    r = recompute(world, model, {"csrf_token": csrf})
    assert r.status_code == 422
    assert "training data is no longer available" in r.text
    assert 'name="next" value="' + world.path("/projects/{p}/models/{model}") in r.text
    r = recompute(world, model, {"csrf_token": csrf, "dataset_id": str(other.id)})
    assert r.status_code == 422 and "lacks the model" in r.text
    r = recompute(world, model, {"csrf_token": csrf, "dataset_id": str(ids["test"])})
    assert r.status_code == 303


def test_the_training_data_is_offered_first(world):
    trained_on = record_like(world, world.p, dataset_id=world.ids[world.p]["test"])
    world.login("co")
    page = world.client.get(world.path("/projects/{p}/models/") + f"{trained_on}?tab=explain")
    select = re.search(r'<select[^>]*name="dataset_id".*?</select>', page.text, re.S).group(0)
    first = re.search(r'<option value="([^"]*)"[^>]*>([^<]*)<', select)
    assert first.group(1) == "" and "iris_test (training data)" in first.group(2)
