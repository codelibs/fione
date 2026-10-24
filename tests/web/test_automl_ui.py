"""The AutoML detail screens: datasets (list, upload, delete, download), dataset detail tabs,
column pages and their charts, the full training form, and the job list."""

import csv
import dataclasses
import io
import json
import re
from contextlib import closing
from html import escape, unescape

import numpy as np
import pandas as pd
import pytest

from api_helpers import connect, iris_csv
from fione.auth import service as auth
from fione.engine.config import TrainConfig
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.projects import service as projects
from fione.projects.ingest import ingest_csv
from fione.projects.service import DatasetType
from fione.web import automl
from web_helpers import make_world

HTML = {"Accept": "text/html"}
XSS = "</script><img src=x onerror=alert(1)>"
ECHARTS = "/static/vendor/echarts/echarts.min.js"


def location(r) -> str:
    assert r.status_code == 303, r.text
    return r.headers["location"]


def count(client, table: str, where: str = "1=1", args=()) -> int:
    with closing(connect(client)) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", args).fetchone()[0]


@pytest.fixture
def world(make_client):
    return make_world(make_client())


def add_dataset(world, frame: pd.DataFrame, name="extra", kind=DatasetType.TRAIN) -> int:
    with closing(connect(world.client)) as conn:
        data = io.BytesIO(frame.to_csv(index=False).encode())
        return ingest_csv(world.client.app.state.storage, conn, world.p, name, kind, data).id


def chart_specs(html: str) -> list[dict]:
    blocks = re.findall(r'<script type="application/json" id="[^"]+">(.*?)</script>', html, re.S)
    return [json.loads(block) for block in blocks]


# --- datasets -------------------------------------------------------------------------------


def test_the_dataset_list_shows_every_dataset_with_its_actions(world):
    world.login("ed")
    page = world.client.get(world.path("/projects/{p}/datasets")).text
    for name in ("iris", "iris_test", "predict_iris_test"):
        assert f">{name}</a>" in page
    assert world.path('href="/api/v1/projects/{p}/datasets/{train}/download"') in page
    assert world.path('href="/projects/{p}/datasets/{train}/train"') in page
    assert world.path('/projects/{p}/datasets/{test}/train"') not in page  # training data only
    assert 'action="' + world.path("/projects/{p}/datasets/{test}/delete") + '"' in page
    assert re.search(r"\d+(\.\d)? KB", page)  # the stored size
    assert ECHARTS not in page


def test_viewers_see_the_datasets_read_only(world):
    world.login("vi")
    page = world.client.get(world.path("/projects/{p}/datasets")).text
    assert "/delete" not in page and 'enctype="multipart/form-data"' not in page
    assert "/train" not in page and "/download" in page


@pytest.mark.parametrize("kind", ["train", "test", "predict"])
def test_uploading_a_dataset_of_each_kind(world, kind):
    csrf = world.login("co")  # an editor member
    r = world.client.post(
        world.path("/projects/{p}/datasets"),
        data={"csrf_token": csrf, "kind": kind},
        files={"file": ("flowers.csv", iris_csv(), "text/csv")},
        follow_redirects=False,
    )
    did = int(location(r).rsplit("/", 1)[1])
    with closing(connect(world.client)) as conn:
        row = conn.execute("SELECT name, type FROM datasets WHERE id = ?", (did,)).fetchone()
    assert tuple(row) == ("flowers", kind)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"kind": "other"}, "Choose the kind of data"),
        ({}, "Choose the kind of data"),
    ],
)
def test_a_dataset_upload_needs_a_kind(world, data, message):
    csrf = world.login("ed")
    before = count(world.client, "datasets")
    r = world.client.post(
        world.path("/projects/{p}/datasets"),
        data={"csrf_token": csrf, **data},
        files={"file": ("flowers.csv", iris_csv(), "text/csv")},
    )
    assert r.status_code == 422 and message in r.text
    assert count(world.client, "datasets") == before


def test_a_bad_csv_upload_is_explained_on_the_list(world):
    csrf = world.login("ed")
    r = world.client.post(
        world.path("/projects/{p}/datasets"),
        data={"csrf_token": csrf, "kind": "train"},
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert r.status_code == 422 and "The file is empty" in r.text
    assert '<details class="card card-padded details upload-panel" open>' in r.text


def test_dataset_uploads_are_under_the_upload_limit_not_the_form_limit(make_client):
    world = make_world(make_client(max_upload_bytes=1000))
    csrf = world.login("ed")
    big = b"a,b\n" + b"1,2\n" * 300_000
    r = world.client.post(
        world.path("/projects/{p}/datasets"),
        data={"csrf_token": csrf, "kind": "train"},
        files={"file": ("big.csv", big, "text/csv")},
        headers=HTML,
    )
    assert r.status_code == 413 and "too large to upload" in r.text


def test_deleting_a_dataset(world):
    csrf = world.login("ed")
    test_id = world.ids[world.p]["test"]
    r = world.client.post(
        world.path("/projects/{p}/datasets/{test}/delete"),
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert location(r) == world.path("/projects/{p}/datasets")
    assert count(world.client, "datasets", "id = ?", (test_id,)) == 0
    r = world.client.post(world.path("/projects/{p}/datasets/{train}/delete"), data={})
    assert (
        r.status_code == 403
        and count(world.client, "datasets", "id = ?", (world.ids[world.p]["train"],)) == 1
    )


def test_downloading_a_dataset_uses_the_api_download(world):
    world.login("vi")
    r = world.client.get(world.path("/api/v1/projects/{p}/datasets/{train}/download"))
    assert r.status_code == 200 and 'filename="iris.csv"' in r.headers["content-disposition"]
    assert len(list(csv.reader(io.StringIO(r.text)))) == 151


# --- dataset detail -------------------------------------------------------------------------


@pytest.mark.parametrize("tab", ["summary", "columns", "data", "correlation"])
def test_the_dataset_detail_opens_on_the_requested_tab(world, tab):
    world.login("vi")
    page = world.client.get(world.path("/projects/{p}/datasets/{train}") + f"?tab={tab}").text
    assert f'id="tab-{tab}" aria-controls="panel-{tab}" aria-selected="true"' in page
    assert re.search(rf'id="panel-{tab}"[^>]*tabindex="0">', page)  # not hidden
    for other in {"summary", "columns", "data", "correlation"} - {tab}:
        assert re.search(rf'id="panel-{other}"[^>]*hidden>', page)
    assert ECHARTS in page and "/static/js/charts.js" in page


def test_the_iris_dataset_detail(world):
    world.login("ed")
    page = world.client.get(world.path("/projects/{p}/datasets/{train}")).text
    assert "150 rows × 5 columns" in page
    assert page.count('<th scope="row" class="cell-name"><a href=') == 5  # the Columns tab
    assert "setosa" in page  # the most common species
    assert "Train a model on this dataset" in page
    specs = chart_specs(page)
    assert specs and specs[0]["type"] == "hbar"
    assert any("petal length (cm) × petal width (cm)" == label for label in specs[0]["labels"])


def test_a_regression_dataset_detail(world):
    world.login("ed")
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"size": rng.uniform(20, 200, 80), "rooms": rng.integers(1, 6, 80)})
    frame["price"] = 3 * frame["size"] + rng.normal(0, 5, 80)
    did = add_dataset(world, frame, "houses")
    page = world.client.get(world.path("/projects/{p}/datasets/") + f"{did}").text
    assert "80 rows × 3 columns" in page and "May give the answer away" in page  # size ~ price
    assert (
        world.client.get(world.path("/projects/{p}/datasets/") + f"{did}/columns/price").status_code
        == 200
    )


def test_the_data_tab_pages_through_rows_and_columns(world):
    world.login("ed")
    base = world.path("/projects/{p}/datasets/{train}") + "?tab=data"
    page = world.client.get(base + "&offset=140&limit=200").text
    assert "Rows 141–150 of 150" in page
    assert page.count('<th scope="row" class="num text-muted">') == 10
    page = world.client.get(base + "&offset=999999&limit=999999").text  # clamped
    assert "Rows 150–150 of 150" in page
    long = pd.DataFrame({"n": range(450), "s": [f"v{i}" for i in range(450)]})
    lid = add_dataset(world, long, "long")
    page = world.client.get(
        world.path("/projects/{p}/datasets/") + f"{lid}?tab=data&limit=999999"
    ).text
    assert "Rows 1–200 of 450" in page  # at most 200 rows per page
    assert page.count('<th scope="row" class="num text-muted">') == 200
    page = world.client.get(base + "&limit=5").text
    assert page.count('<th scope="row" class="num text-muted">') == 5
    wide = pd.DataFrame(np.arange(3 * 120).reshape(3, 120), columns=[f"c{i}" for i in range(120)])
    did = add_dataset(world, wide, "wide")
    page = world.client.get(world.path("/projects/{p}/datasets/") + f"{did}?tab=data&col=50").text
    assert "columns 51–100 of 120" in page and ">c50</th>" in page and ">c49</th>" not in page


def test_values_are_escaped_on_every_new_page(world):
    csrf = world.login("ed")
    frame = pd.DataFrame({XSS: [1.0, 2.0, 3.0] * 10, "label": [XSS, "b", "c"] * 10})
    did = add_dataset(world, frame, XSS)
    base = world.path("/projects/{p}/datasets/") + str(did)
    pages = [
        world.client.get(world.path("/projects/{p}/datasets")).text,
        world.client.get(base).text,
        world.client.get(base + "?tab=data").text,
        world.client.get(base + "?tab=columns").text,
        world.client.get(base + "/train").text,
        world.client.get(base + "/columns/" + automl.quote(XSS, safe="")).text,
        world.client.get(base + "/columns/label").text,
        world.client.post(base + "/train", data={"csrf_token": csrf, "target": XSS}).text,
    ]
    for html in pages:
        assert "<img src=x onerror" not in html
        assert escape(XSS) in html or "\\u003c/script\\u003e" in html
    column = world.client.get(base + "/columns/label").text
    blocks = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', column, re.S)
    assert blocks and "</script>" not in blocks[0] and "<img" not in blocks[0]
    assert XSS in json.loads(blocks[0])["labels"]  # the value itself survives


def test_echarts_is_loaded_only_on_chart_pages(world):
    world.login("ed")
    for template, charts in (
        ("/projects/{p}/datasets", False),
        ("/projects/{p}/datasets/{train}", True),
        ("/projects/{p}/datasets/{train}/columns/species", True),
        ("/projects/{p}/datasets/{train}/train", False),
        ("/projects/{p}/jobs", False),
        ("/projects/{p}", False),
    ):
        assert (ECHARTS in world.client.get(world.path(template)).text) is charts, template


# --- column detail --------------------------------------------------------------------------


def test_a_numeric_column_has_a_histogram_and_statistics(world):
    world.login("vi")
    page = world.client.get(
        world.path("/projects/{p}/datasets/{train}/columns/") + "petal%20length%20(cm)"
    ).text
    spec = chart_specs(page)[0]
    assert spec["type"] == "bar" and len(spec["values"]) == 20 and sum(spec["values"]) == 150
    assert "Median" in page and "Outliers" in page
    assert re.search(r"<table>\s*<caption>", page)  # the text alternative


def test_a_categorical_column_has_value_counts(world):
    world.login("vi")
    page = world.client.get(world.path("/projects/{p}/datasets/{train}/columns/species")).text
    spec = chart_specs(page)[0]
    assert spec["type"] == "hbar" and sorted(spec["labels"]) == [
        "setosa",
        "versicolor",
        "virginica",
    ]
    assert spec["values"] == [50, 50, 50]
    assert "default" in page  # species is the column Fione would predict


def test_many_categories_end_with_other(world):
    world.login("ed")
    frame = pd.DataFrame({"code": [f"k{i % 30}" for i in range(300)], "y": range(300)})
    did = add_dataset(world, frame, "codes")
    page = world.client.get(world.path("/projects/{p}/datasets/") + f"{did}/columns/code").text
    spec = chart_specs(page)[0]
    assert spec["labels"][-1] == "(other values)" and spec["values"][-1] == 200
    assert sum(spec["values"]) == 300


@pytest.mark.parametrize("name", ["a/b", "50%", "what?", "#1", "two words", "日本語", ".", ".."])
def test_column_names_with_special_characters_round_trip(world, name):
    world.login("ed")
    did = add_dataset(world, pd.DataFrame({name: range(20), "y": range(20)}), "odd")
    url = automl.column_url(world.p, did, name)
    r = world.client.get(url)
    assert r.status_code == 200, url
    assert f'<h1 class="page-header__title page-header__title-wrap">{escape(name)}</h1>' in r.text
    listing = world.client.get(world.path("/projects/{p}/datasets/") + f"{did}?tab=columns").text
    assert f'href="{escape(url)}"' in listing


def test_an_unknown_column_is_404(world):
    world.login("ed")
    r = world.client.get(world.path("/projects/{p}/datasets/{train}/columns/nope"), headers=HTML)
    assert r.status_code == 404 and "text/html" in r.headers["content-type"]


# --- the full training form ---------------------------------------------------------------


def form_for(csrf: str, **changes) -> dict:
    base = {
        "csrf_token": csrf,
        "target": "species",
        "task": "classification",
        "inputs": ["sepal length (cm)", "petal width (cm)"],
        "max_runtime_minutes": "7",
        "max_runtime_secs_per_model": "30",
        "max_models": "9",
        "nfolds": "4",
        "seed": "4294967295",
        "balance_classes": "on",
        "stopping_rounds": "2",
        "stopping_metric": "logloss",
        "stopping_tolerance": "0.25",
        "sort_metric": "accuracy",
        "keep_cv_predictions": "on",
        "keep_cv_models": "on",
        "keep_cv_fold_assignment": "on",
    }
    return {k: v for k, v in {**base, **changes}.items() if v is not None}


def test_the_form_shows_the_engine_defaults(world):
    world.login("ed")
    page = world.client.get(world.path("/projects/{p}/datasets/{train}/train")).text
    defaults = {
        f.name: f.default
        for f in dataclasses.fields(TrainConfig)
        if f.default is not dataclasses.MISSING
    }
    assert f'name="max_runtime_minutes" value="{defaults["max_runtime_secs"] // 60}"' in page
    for name in ("nfolds", "seed", "stopping_rounds"):
        assert f'name="{name}" value="{defaults[name]}"' in page
    assert f'name="stopping_tolerance" value="{defaults["stopping_tolerance"]:g}"' in page
    assert '<option value="auto" selected>' in page
    assert 'data-task="classification"' in page and 'data-task="regression"' in page
    assert world.path("/projects/{p}/datasets/{train}/analyze?target=species") in page  # guided


def test_every_training_parameter_round_trips_into_the_job(world):
    csrf = world.login("ed")
    r = world.client.post(
        world.path("/projects/{p}/datasets/{train}/train"),
        data=form_for(csrf),
        follow_redirects=False,
    )
    job_id = int(location(r).rsplit("/", 1)[1])
    with closing(connect(world.client)) as conn:
        config = TrainConfig.from_dict(store.get_job(conn, job_id).payload["config"])
    expected = {
        "target": "species",
        "task": "classification",
        "max_runtime_secs": 7 * 60,
        "max_runtime_secs_per_model": 30,
        "max_models": 9,
        "nfolds": 4,
        "seed": 2**32 - 1,
        "balance_classes": True,
        "stopping_rounds": 2,
        "stopping_metric": "logloss",
        "stopping_tolerance": 0.25,
        "sort_metric": "accuracy",
        "keep_cv_predictions": True,
        "keep_cv_models": True,
        "keep_cv_fold_assignment": True,
        "ignored_columns": ["sepal width (cm)", "petal length (cm)"],
    }
    assert {f.name for f in dataclasses.fields(TrainConfig)} == set(expected)  # all covered
    assert config.to_dict() == expected


def test_unchecked_flags_and_empty_optionals_are_false_and_none(world):
    csrf = world.login("ed")
    form = form_for(
        csrf,
        balance_classes=None,
        keep_cv_predictions=None,
        keep_cv_models=None,
        keep_cv_fold_assignment=None,
        max_models="",
        max_runtime_secs_per_model="",
    )
    job_id = int(
        location(
            world.client.post(
                world.path("/projects/{p}/datasets/{train}/train"),
                data=form,
                follow_redirects=False,
            )
        ).rsplit("/", 1)[1]
    )
    with closing(connect(world.client)) as conn:
        config = store.get_job(conn, job_id).payload["config"]
    assert config["max_models"] is None and config["max_runtime_secs_per_model"] is None
    assert not any(
        config[k]
        for k in (
            "balance_classes",
            "keep_cv_predictions",
            "keep_cv_models",
            "keep_cv_fold_assignment",
        )
    )


@pytest.mark.parametrize(
    ("change", "field", "message"),
    [
        ({"nfolds": "1"}, "nfolds", "2 or more"),
        ({"nfolds": "+3"}, "nfolds", "2 or more"),
        ({"nfolds": "３"}, "nfolds", "2 or more"),
        ({"seed": "-1"}, "seed", "0 to 4294967295"),
        ({"seed": "4294967296"}, "seed", "0 to 4294967295"),
        ({"stopping_tolerance": "nan"}, "stopping_tolerance", "0 or more"),
        ({"stopping_tolerance": "1e999"}, "stopping_tolerance", "0 or more"),
        ({"stopping_tolerance": "-0.1"}, "stopping_tolerance", "0 or more"),
        ({"stopping_rounds": "1_000"}, "stopping_rounds", "0 or more"),
        ({"max_models": "0"}, "max_models", "leave it empty"),
        ({"max_runtime_minutes": "0"}, "max_runtime_minutes", "whole number of minutes"),
        ({"max_runtime_minutes": "1234567"}, "max_runtime_minutes", "whole number of minutes"),
        ({"sort_metric": "rmse"}, "sort_metric", "does not fit the prediction type"),
        ({"stopping_metric": "deviance"}, "stopping_metric", "does not fit the prediction type"),
        ({"task": "regression"}, "target", "Training would refuse"),
        ({"task": "binary"}, "task", "Choose a prediction type"),
        ({"inputs": []}, "inputs", "at least one input column"),
        ({"bogus": "1"}, "form", "a field it should not have"),
    ],
)
def test_invalid_settings_go_back_to_the_form_with_nothing_queued(world, change, field, message):
    csrf = world.login("ed")
    before = count(world.client, "jobs")
    form = form_for(csrf, **change)
    if change == {"task": "regression"}:  # a text target as regression: the engine refuses
        form["sort_metric"] = form["stopping_metric"] = "auto"
    r = world.client.post(world.path("/projects/{p}/datasets/{train}/train"), data=form)
    assert r.status_code == 422, r.text
    assert message in unescape(r.text) and 'id="run-errors"' in r.text
    assert count(world.client, "jobs") == before


def test_a_setting_posted_twice_is_refused(world):
    csrf = world.login("ed")
    before = count(world.client, "jobs")
    body = "&".join(
        f"{k}={v}"
        for k, v in [
            ("csrf_token", csrf),
            ("target", "species"),
            ("task", "auto"),
            ("inputs", "petal+width+%28cm%29"),
            ("max_runtime_minutes", "1"),
            ("max_runtime_minutes", "2"),
            ("nfolds", "5"),
            ("seed", "0"),
            ("stopping_rounds", "3"),
            ("stopping_metric", "auto"),
            ("stopping_tolerance", "0.001"),
            ("sort_metric", "auto"),
        ]
    )
    r = world.client.post(
        world.path("/projects/{p}/datasets/{train}/train"),
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 422 and "a setting twice" in r.text
    assert count(world.client, "jobs") == before


def test_too_many_fields_is_a_friendly_error(world, monkeypatch):
    csrf = world.login("ed")
    monkeypatch.setattr(automl, "MAX_FORM_FIELDS", 5)
    r = world.client.post(world.path("/projects/{p}/datasets/{train}/train"), data=form_for(csrf))
    assert r.status_code == 422 and "too many columns to choose from" in r.text


def test_metrics_follow_the_detected_task_when_automatic(world):
    csrf = world.login("ed")
    r = world.client.post(
        world.path("/projects/{p}/datasets/{train}/train"),
        data=form_for(csrf, task="auto", sort_metric="r2", stopping_metric="auto"),
    )
    assert r.status_code == 422 and "does not fit the prediction type" in r.text


def test_a_viewer_cannot_open_the_training_form(world):
    world.login("vi")
    assert world.client.get(world.path("/projects/{p}/datasets/{train}/train")).status_code == 403
    page = world.client.get(world.path("/projects/{p}/datasets/{train}")).text
    assert "/train" not in page


def test_the_wizard_and_the_form_link_to_each_other(world):
    world.login("ed")
    analysis = world.client.get(world.path("/projects/{p}/datasets/{train}/analyze")).text
    assert world.path("/projects/{p}/datasets/{train}/train?target=species") in analysis
    form = world.client.get(world.path("/projects/{p}/datasets/{train}/train")).text
    assert "Back to the guided flow" in form


# --- jobs -----------------------------------------------------------------------------------


def finished(world, project, kind="automl", status=JobStatus.DONE, message=None) -> int:
    with closing(connect(world.client)) as conn:
        user = conn.execute("SELECT id FROM users WHERE username = 'ed'").fetchone()[0]
        job = store.enqueue(conn, kind, project, user, {})
        store.claim_job(conn, job.id, "t")
        store.finish_job(conn, job.id, status, message=message)
        return job.id


def test_the_job_list_with_filters(world):
    world.login("ed")
    failed = finished(
        world, world.p, status=JobStatus.FAILED, message="boom first\n/srv/secret trace"
    )
    page = world.client.get(world.path("/projects/{p}/jobs")).text
    assert f"#{world.ids[world.p]['job']}<" in page and f"#{failed}<" in page
    assert "boom first" in page and "/srv/secret" not in page  # the API's redaction
    assert 'hx-trigger="every 5s"' in page  # a job is queued
    only = world.client.get(world.path("/projects/{p}/jobs") + "?status=failed").text
    assert f"#{failed}<" in only and f"#{world.ids[world.p]['job']}<" not in only
    kind = world.client.get(world.path("/projects/{p}/jobs") + "?kind=batch_predict").text
    assert f"#{world.ids[world.p]['predict_job']}<" in kind and f"#{failed}<" not in kind
    assert world.path("/projects/{p}/jobs/{predict_job}/result") in kind


def test_the_list_polls_fast_while_a_job_is_active_and_slowly_otherwise(world):
    csrf = world.login("ed")
    hx = {"HX-Request": "true"}
    r = world.client.get(world.path("/projects/{p}/jobs"), headers=hx)
    assert r.status_code == 200 and 'hx-trigger="every 5s"' in r.text and "<html" not in r.text
    world.client.post(
        world.path("/projects/{p}/jobs/{job}/cancel"), data={"csrf_token": csrf, "back": "list"}
    )
    r = world.client.get(world.path("/projects/{p}/jobs"), headers=hx)
    assert r.status_code == 200 and 'hx-trigger="every 30s"' in r.text  # notices new jobs
    with closing(connect(world.client)) as conn:  # a job queued elsewhere (the API, a tab)
        user = conn.execute("SELECT id FROM users WHERE username = 'ed'").fetchone()[0]
        store.enqueue(conn, "automl", world.p, user, {})
    r = world.client.get(world.path("/projects/{p}/jobs"), headers=hx)
    assert 'hx-trigger="every 5s"' in r.text


def test_polling_keeps_the_page_and_filters(world):
    world.login("ed")
    for _ in range(automl.JOBS_PER_PAGE + 5):
        finished(world, world.p)
    page = world.client.get(world.path("/projects/{p}/jobs") + "?page=2&status=done").text
    poll = re.search(r'id="job-list"[^>]*hx-get="([^"]+)"', page).group(1)
    assert unescape(poll) == world.path("/projects/{p}/jobs") + "?status=done&page=2"
    again = world.client.get(unescape(poll), headers={"HX-Request": "true"}).text
    shown = re.findall(r">(?:Training|Prediction) #(\d+)<", again)
    first_page = re.findall(
        r">(?:Training|Prediction) #(\d+)<",
        world.client.get(world.path("/projects/{p}/jobs") + "?status=done").text,
    )
    assert shown and not set(shown) & set(first_page)  # still page 2


def test_polling_stops_when_the_list_can_no_longer_be_shown(make_client, monkeypatch):
    world = make_world(make_client(raise_server_exceptions=False))
    world.login("vi")
    hx = {"HX-Request": "true"}
    with closing(connect(world.client)) as conn:
        owner = next(u for u in auth.list_users(conn) if u.username == "ed")
        projects.unshare_project(conn, owner, world.p, "vi")
    r = world.client.get(world.path("/projects/{p}/jobs"), headers=hx)
    assert r.status_code == 286 and "hx-trigger" not in r.text and 'id="job-list"' in r.text
    assert "This list can no longer be shown" in r.text
    world.login("ed")

    def boom(*args):
        raise RuntimeError("database locked")

    monkeypatch.setattr(automl, "_jobs_context", boom)
    r = world.client.get(world.path("/projects/{p}/jobs"), headers=hx)
    assert r.status_code == 286 and "Reload the page" in r.text and "database locked" not in r.text


def test_a_malformed_form_is_not_called_too_many_columns(world):
    csrf = world.login("ed")
    r = world.client.post(
        world.path("/projects/{p}/datasets/{train}/train"),
        content=b"csrf_token=" + csrf.encode(),
        headers={"Content-Type": "multipart/form-data"},  # no boundary: unreadable
    )
    assert r.status_code == 400 and "The form could not be read" in r.text
    assert "too many columns" not in r.text


def test_cancelling_from_the_list_comes_back_to_the_list(world):
    csrf = world.login("co")
    r = world.client.post(
        world.path("/projects/{p}/jobs/{job}/cancel"),
        data={"csrf_token": csrf, "back": "list"},
        follow_redirects=False,
    )
    assert location(r) == world.path("/projects/{p}/jobs")
    r = world.client.post(
        world.path("/projects/{p}/jobs/{job}/cancel"),
        data={"csrf_token": csrf, "back": "https://evil.example"},
        follow_redirects=False,
    )
    assert location(r) == world.path("/projects/{p}/jobs/{job}")  # anything else: the job page
    with closing(connect(world.client)) as conn:
        assert store.get_job(conn, world.ids[world.p]["job"]).status == JobStatus.CANCELLED


def test_deleting_a_finished_job_removes_its_log(world):
    csrf = world.login("ed")
    job_id = world.ids[world.p]["predict_job"]
    log = world.client.app.state.settings.data_dir / "jobs" / f"{job_id}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("log")
    r = world.client.post(
        world.path("/projects/{p}/jobs/{predict_job}/delete"),
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert location(r) == world.path("/projects/{p}/jobs")
    assert count(world.client, "jobs", "id = ?", (job_id,)) == 0 and not log.exists()
    r = world.client.post(world.path("/projects/{p}/jobs/{job}/delete"), data={"csrf_token": csrf})
    assert r.status_code == 409 and "Only a finished job can be deleted" in r.text


def test_delete_all_finished_is_scoped_to_the_project(world):
    csrf = world.login("ed")
    finished(world, world.p)
    finished(world, world.q)
    r = world.client.post(
        world.path("/projects/{p}/jobs/delete-finished"),
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert location(r) == world.path("/projects/{p}/jobs")
    assert count(world.client, "jobs", "project_id = ?", (world.p,)) == 1  # the queued one
    assert count(world.client, "jobs", "project_id = ?", (world.q,)) == 3  # untouched


def test_viewers_see_jobs_without_actions(world):
    world.login("vi")
    page = world.client.get(world.path("/projects/{p}/jobs")).text
    assert "/cancel" not in page and "/delete" not in page and "delete-finished" not in page


def test_the_project_navigation_is_on_every_project_screen(world):
    world.login("ed")
    for template, current in (
        ("/projects/{p}", "Overview"),
        ("/projects/{p}/datasets", "Datasets"),
        ("/projects/{p}/datasets/{train}", "Datasets"),
        ("/projects/{p}/jobs", "Jobs"),
        ("/projects/{p}/datasets/{train}/analyze", None),
    ):
        page = world.client.get(world.path(template)).text
        assert '<nav class="subnav"' in page, template
        for label in ("Overview", "Datasets", "Jobs"):
            assert f">{label}</a>" in page
        if current:
            assert f'aria-current="page">{current}</a>' in page, template
        assert 'class="steps' not in page or "analyze" in template
