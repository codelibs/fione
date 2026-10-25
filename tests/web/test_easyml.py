"""The EasyML wizard through its HTML endpoints: the iris and a regression flow with the job
runner in process, and the refusals (bad files, bad settings, CSRF, other projects, viewers),
escaping, polling, cancelling, error pages and upload limits."""

import csv
import dataclasses
import io
import re
import time
from contextlib import closing
from html import escape
from urllib.parse import parse_qs, urlsplit

import numpy as np
import pandas as pd
import pytest

from api_helpers import add_user, connect, iris_csv, iris_frame, login
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.engine.artifact import save_model
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.models import service as models
from fione.predict import batch
from fione.projects import service as projects
from fione.tools import builtin
from fione.web import easyml, uploads
from fione.web.headers import CONTENT_SECURITY_POLICY
from web_helpers import FAST, iris_test_csv, make_world

INPUTS = ["sepal length (cm)", "sepal width (cm)", "petal length (cm)", "petal width (cm)"]
XSS = ["<script>alert(1)</script>", '"><img src=x onerror=alert(1)>']
HTML = {"Accept": "text/html,application/xhtml+xml"}
CSP = CONTENT_SECURITY_POLICY


def location(r) -> str:
    assert r.status_code == 303, r.text
    return r.headers["location"]


def upload(client, path, csrf, content, filename="data.csv", **kwargs):
    return client.post(
        path,
        data={"csrf_token": csrf},
        files={"file": (filename, content, "text/csv")},
        follow_redirects=False,
        **kwargs,
    )


def run_form(csrf, target="species", inputs=INPUTS, task="classification", **extra):
    return {
        "csrf_token": csrf,
        "target": target,
        "inputs": inputs,
        "task": task,
        "runtime": "1",
        **extra,
    }


def follow_job(client, job_url, timeout=90.0) -> str:
    """Poll the job's status fragment as HTMX does until it sends us on; returns where."""
    deadline = time.monotonic() + timeout
    while True:
        r = client.get(job_url + "/status", headers={"HX-Request": "true"})
        assert r.status_code == 200, r.text
        if "HX-Redirect" in r.headers:
            assert "hx-trigger" not in r.text  # finished: polling stops
            return r.headers["HX-Redirect"]
        status = re.search(r'data-job-status="(\w+)"', r.text).group(1)
        assert status in ("queued", "running"), r.text
        assert 'hx-trigger="every 2s"' in r.text
        assert time.monotonic() < deadline, f"the job is still {status}"
        time.sleep(0.3)


def stars_of(html: str) -> int:
    found = re.search(r'aria-label="(\d) out of 5 stars" data-stars="(\d)"', html)
    assert found, "no star rating"
    assert found.group(1) == found.group(2)
    return int(found.group(1))


def job_count(client) -> int:
    with closing(connect(client)) as conn:
        return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]


def dataset_count(client) -> int:
    with closing(connect(client)) as conn:
        return conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]


@pytest.fixture
def owner(make_client):
    """A client signed in as ``ed``, the owner of project ``P``: ``(client, pid, csrf)``."""
    client = make_client()
    user = add_user(client, "ed", Role.EDITOR)
    with closing(connect(client)) as conn:
        project = projects.create_project(conn, user, "P")
    return client, project.id, login(client, "ed")


@pytest.fixture
def runner_owner(make_client, monkeypatch):
    """As ``owner``, with the job runner in process and fast training configs."""
    monkeypatch.delenv("FIONE_JOB_HANDLER_MODULES", raising=False)
    monkeypatch.setattr(easyml, "EASYML_CONFIG", FAST)
    client = make_client(start_runner=True)
    add_user(client, "ed", Role.EDITOR)
    csrf = login(client, "ed")
    r = client.post(
        "/ui/projects", data={"name": "Iris"}, headers={"HX-Request": "true", "X-CSRF-Token": csrf}
    )
    assert r.status_code == 200, r.text
    with closing(connect(client)) as conn:
        pid = conn.execute("SELECT id FROM projects").fetchone()[0]
    return client, pid, csrf


# --- the whole flows ----------------------------------------------------------------------


def test_the_iris_flow_ends_with_a_star_rating_and_a_prediction_download(runner_owner):
    client, pid, csrf = runner_owner
    home = client.get("/").text
    assert f'href="/projects/{pid}"' in home  # project cards link to the dashboard
    dashboard = client.get(f"/projects/{pid}").text
    assert f'href="/projects/{pid}/upload"' in dashboard and "Upload training data" in dashboard

    analysis_url = location(upload(client, f"/projects/{pid}/upload", csrf, iris_csv(), "iris.csv"))
    assert re.fullmatch(rf"/projects/{pid}/datasets/\d+/analyze", analysis_url)
    page = client.get(analysis_url).text
    assert '<option value="species" selected>' in page  # the last column
    assert 'id="task-classification" name="task" value="classification" checked' in page
    for name in INPUTS:
        assert f'name="inputs" value="{name}" checked' in page
    assert page.count('<tr><td class="num">') == 10  # the first 10 rows
    assert "3 different values" in page and "150" in page
    assert 'name="runtime" value="3" checked' in page  # 3 minutes by default

    job_url = location(
        client.post(
            analysis_url.replace("/analyze", "/run"), data=run_form(csrf), follow_redirects=False
        )
    )
    assert re.fullmatch(rf"/projects/{pid}/jobs/\d+", job_url)
    page = client.get(job_url).text
    assert 'aria-live="polite"' in page and "Stop training" in page
    summary_url = follow_job(client, job_url)
    assert re.fullmatch(rf"/projects/{pid}/models/\d+/summary", summary_url)

    summary = client.get(summary_url).text
    assert 1 <= stars_of(summary) <= 5
    assert stars_of(summary) >= 4  # iris is easy: well above always guessing one species
    assert "right about" in summary and "Fione-kun" in summary
    assert "Enough models were tried" in summary  # max_models = 1
    assert "/api/v1/models/" in summary and "docker run" in summary
    model_id = summary_url.split("/")[-2]

    predict_url = f"/projects/{pid}/models/{model_id}/predict"
    page = client.get(predict_url).text
    for name in INPUTS:
        assert f"<code>{name}</code>" in page
    columns_url = location(upload(client, predict_url, csrf, iris_test_csv(), "iris_test.csv"))
    dataset_id = parse_qs(urlsplit(columns_url).query)["dataset"][0]
    page = client.get(columns_url).text
    for name in INPUTS:
        assert f'name="include" value="{name}" checked' in page
    form = {"csrf_token": csrf, "dataset_id": dataset_id, "include": ["petal width (cm)"]}
    job_url = location(client.post(predict_url + "/run", data=form, follow_redirects=False))
    result_url = follow_job(client, job_url)
    assert result_url == job_url + "/result"

    result = client.get(result_url).text
    assert result.count("<tr>") == 1 + 20  # header and the first 20 rows
    assert not re.search(r"\d\.\d{10,}<", result)  # probabilities shown to 6 digits
    download = re.search(r'href="(/api/v1/projects/[^"]+/download)"', result).group(1)
    r = client.get(download)
    assert r.status_code == 200
    assert 'filename="predict_iris_test.csv"' in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == ["predict", "p_setosa", "p_versicolor", "p_virginica", "petal width (cm)"]
    assert len(rows) == 1 + 150


def test_a_regression_flow(runner_owner):
    client, pid, csrf = runner_owner
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"size": rng.uniform(20, 200, 80), "rooms": rng.integers(1, 6, 80)})
    frame["price"] = 3 * frame["size"] + 20 * frame["rooms"] + rng.normal(0, 5, 80)
    analysis_url = location(
        upload(client, f"/projects/{pid}/upload", csrf, frame.to_csv(index=False).encode())
    )
    page = client.get(analysis_url).text
    assert '<option value="price" selected>' in page
    assert 'value="regression" checked' in page and "suggests regression" in page
    form = run_form(csrf, "price", ["size", "rooms"], "regression")
    job_url = location(
        client.post(analysis_url.replace("/analyze", "/run"), data=form, follow_redirects=False)
    )
    summary = client.get(follow_job(client, job_url)).text
    assert 1 <= stars_of(summary) <= 5
    assert "typically off by about" in summary and "Regression" in summary


# --- refusals: nothing is stored or queued ------------------------------------------------


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "The file is empty"),
        (b"a,b\n", "no data rows"),
        (bytes(range(128, 256)) * 50, "could not read the text of this file"),
        (b"a,b\n1,2\n3,4,5\n", "could not read the file as CSV"),
    ],
)
def test_a_bad_csv_is_refused_in_plain_words(owner, content, message):
    client, pid, csrf = owner
    r = upload(client, f"/projects/{pid}/upload", csrf, content)
    assert r.status_code == 422, r.text
    assert message in r.text and 'role="alert"' in r.text
    assert dataset_count(client) == 0
    assert "/tmp/" not in r.text and str(client.app.state.settings.data_dir) not in r.text


def test_an_upload_without_a_file_is_refused(owner):
    client, pid, csrf = owner
    r = client.post(
        f"/projects/{pid}/upload", data={"csrf_token": csrf}, files={"other": ("x", b"")}
    )
    assert r.status_code == 422 and "Choose a CSV file" in r.text


@pytest.fixture
def analysis(owner):
    client, pid, csrf = owner
    url = location(upload(client, f"/projects/{pid}/upload", csrf, iris_csv()))
    return client, url.replace("/analyze", "/run"), csrf


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"runtime": "custom", "runtime_custom": "0"}, "whole number of minutes"),
        ({"runtime": "custom", "runtime_custom": "abc"}, "whole number of minutes"),
        ({"runtime": "custom", "runtime_custom": "1.5"}, "whole number of minutes"),
        ({"runtime": "custom", "runtime_custom": "1234567"}, "whole number of minutes"),
        ({"runtime": "7"}, "whole number of minutes"),
        ({"runtime": ""}, "whole number of minutes"),
        ({"inputs": []}, "at least one input column"),
        ({"inputs": ["species"]}, "at least one input column"),
        ({"inputs": ["nope"]}, "not in this data"),
        ({"target": "nope"}, "Choose a column to predict"),
        ({"task": "auto"}, "Choose a prediction type"),
    ],
)
def test_bad_settings_go_back_to_the_analysis_with_nothing_queued(analysis, change, message):
    client, run_url, csrf = analysis
    r = client.post(run_url, data=run_form(csrf) | change)
    assert r.status_code == 422, r.text
    assert message in r.text and 'id="run-errors"' in r.text
    assert job_count(client) == 0


def test_a_custom_runtime_is_used_in_minutes(analysis):
    client, run_url, csrf = analysis
    r = client.post(
        run_url, data=run_form(csrf, runtime="custom", runtime_custom="45"), follow_redirects=False
    )
    job_id = int(location(r).rsplit("/", 1)[1])
    with closing(connect(client)) as conn:
        config = store.get_job(conn, job_id).payload["config"]
    assert config["max_runtime_secs"] == 45 * 60
    assert config["task"] == "classification" and config["target"] == "species"
    assert config["ignored_columns"] == []


def test_unchecked_inputs_are_ignored_columns(analysis):
    client, run_url, csrf = analysis
    r = client.post(run_url, data=run_form(csrf, inputs=INPUTS[:2]), follow_redirects=False)
    job_id = int(location(r).rsplit("/", 1)[1])
    with closing(connect(client)) as conn:
        config = store.get_job(conn, job_id).payload["config"]
    assert config["ignored_columns"] == INPUTS[2:]


def test_a_settings_error_of_the_service_is_shown_inline(owner):
    client, pid, csrf = owner
    url = location(upload(client, f"/projects/{pid}/upload", csrf, iris_csv()))
    with closing(connect(client)) as conn:  # the dataset is no training data
        conn.execute("UPDATE datasets SET type = 'test'")
    r = client.post(url.replace("/analyze", "/run"), data=run_form(csrf))
    assert r.status_code == 422 and "training needs a train dataset" in r.text
    assert "This is not training data" in r.text
    assert job_count(client) == 0


def test_a_prediction_file_missing_columns_lists_them_and_is_not_kept(make_client):
    world = make_world(make_client())
    csrf = world.login("ed")
    before = dataset_count(world.client)
    content = iris_frame()[["sepal length (cm)", "petal width (cm)"]].to_csv(index=False).encode()
    r = upload(world.client, world.path("/projects/{p}/models/{model}/predict"), csrf, content)
    assert r.status_code == 422, r.text
    assert "missing 2 columns" in r.text
    assert "<li><code>sepal width (cm)</code></li>" in r.text
    assert "<li><code>petal length (cm)</code></li>" in r.text
    assert dataset_count(world.client) == before


def test_extra_columns_of_a_prediction_file_are_noted(make_client):
    world = make_world(make_client())
    csrf = world.login("ed")
    frame = iris_frame().drop(columns=["species"]).assign(note="x")
    url = location(
        upload(
            world.client,
            world.path("/projects/{p}/models/{model}/predict"),
            csrf,
            frame.to_csv(index=False).encode(),
        )
    )
    page = world.client.get(url).text
    assert "1 columns are not used by the model" in page
    assert 'value="note" checked' in page and "Not used by the model" in page


def test_the_predict_form_checkbox_sets_the_payload(make_client, monkeypatch):
    world = make_world(make_client())
    csrf = world.login("ed")
    page = world.client.get(world.path("/projects/{p}/models/{model}/predict?dataset={test}")).text
    assert '<input class="checkbox" type="checkbox" id="contributions" name="contributions"' in page
    assert "Explain each prediction" in page and "Up to 100,000 rows" in page
    assert 'name="contributions" value="true" checked' not in page  # off unless asked for
    url = world.path("/projects/{p}/models/{model}/predict/run")
    form = {"csrf_token": csrf, "dataset_id": world.path("{test}"), "include": [INPUTS[0]]}
    payloads = []
    for extra in ({}, {"contributions": "true"}):
        r = world.client.post(url, data={**form, **extra}, follow_redirects=False)
        job_id = int(location(r).rsplit("/", 1)[1])
        with closing(connect(world.client)) as conn:
            payloads.append(store.get_job(conn, job_id).payload)
    assert [p["include_contributions"] for p in payloads] == [False, True]
    monkeypatch.setattr(batch, "MAX_CONTRIBUTION_ROWS", 1)
    before = job_count(world.client)
    r = world.client.post(url, data={**form, "contributions": "true"})
    assert r.status_code == 422 and "contributions are limited to 1 rows" in r.text
    assert job_count(world.client) == before


@pytest.mark.parametrize(
    ("method", "template", "form"),
    [
        ("POST", "/projects/{p}/datasets/{train}/run", {"target": "species"}),
        ("POST", "/projects/{p}/jobs/{job}/cancel", {}),
        ("POST", "/projects/{p}/models/{model}/predict/run", {"dataset_id": "1"}),
        ("UPLOAD", "/projects/{p}/upload", {}),
        ("UPLOAD", "/projects/{p}/models/{model}/predict", {}),
    ],
)
@pytest.mark.parametrize("token", [None, "wrong"])
def test_a_post_without_the_csrf_token_is_a_403_page(make_client, method, template, form, token):
    world = make_world(make_client())
    world.login("ed")
    before = (job_count(world.client), dataset_count(world.client))
    data = form | ({"csrf_token": token} if token else {})
    path = world.path(template)
    if method == "UPLOAD":
        files = {"file": ("d.csv", iris_csv(), "text/csv")}
        r = world.client.post(path, data=data, files=files)
    else:
        r = world.client.post(path, data=data)
    assert r.status_code == 403
    assert "text/html" in r.headers["content-type"] and "This page has expired" in r.text
    assert (job_count(world.client), dataset_count(world.client)) == before
    with closing(connect(world.client)) as conn:
        assert store.get_job(conn, world.ids[world.p]["job"]).status == JobStatus.QUEUED


def test_a_cross_site_upload_is_refused_before_it_is_read(owner):
    client, pid, csrf = owner
    r = upload(
        client,
        f"/projects/{pid}/upload",
        csrf,
        iris_csv(),
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403 and dataset_count(client) == 0


# --- cancelling and polling ---------------------------------------------------------------


def test_cancelling_a_queued_training(make_client):
    world = make_world(make_client())
    csrf = world.login("ed")
    job_url = world.path("/projects/{p}/jobs/{job}")
    page = world.client.get(job_url).text
    assert '<details class="confirm"' in page and "Yes, stop" in page
    assert "onclick" not in page and "confirm(" not in page
    assert 'hx-trigger="every 2s"' in page
    r = world.client.post(job_url + "/cancel", data={"csrf_token": csrf}, follow_redirects=False)
    assert location(r) == job_url
    with closing(connect(world.client)) as conn:
        assert store.get_job(conn, world.ids[world.p]["job"]).status == JobStatus.CANCELLED
    page = world.client.get(job_url).text
    assert "This run was stopped" in page and "Back to data analysis" in page
    assert "hx-trigger" not in page and "Yes, stop" not in page
    fragment = world.client.get(job_url + "/status", headers={"HX-Request": "true"})
    assert "hx-trigger" not in fragment.text and "HX-Redirect" not in fragment.headers
    assert 'id="job-cancel" hx-swap-oob="true"' in fragment.text  # the panel goes too
    # Cancelling a finished job again changes nothing.
    r = world.client.post(job_url + "/cancel", data={"csrf_token": csrf}, follow_redirects=False)
    assert location(r) == job_url


def test_a_viewer_watches_but_cannot_cancel(make_client):
    world = make_world(make_client())
    csrf = world.login("vi")
    job_url = world.path("/projects/{p}/jobs/{job}")
    page = world.client.get(job_url).text
    assert 'hx-trigger="every 2s"' in page and "Yes, stop" not in page
    r = world.client.post(job_url + "/cancel", data={"csrf_token": csrf})
    assert r.status_code == 403
    with closing(connect(world.client)) as conn:
        assert store.get_job(conn, world.ids[world.p]["job"]).status == JobStatus.QUEUED


def test_polling_an_expired_session_sends_htmx_to_the_login_page(make_client):
    world = make_world(make_client())
    path = world.path("/projects/{p}/jobs/{job}/status")
    r = world.client.get(
        path, headers={"HX-Request": "true", "HX-Current-URL": "http://x/projects"}
    )
    assert r.status_code == 401 and r.headers["HX-Redirect"] == "/login?next=%2Fprojects"


def test_a_failed_training_shows_the_redacted_message_and_the_way_back(make_client):
    world = make_world(make_client())
    world.login("ed")
    job_id = world.ids[world.p]["job"]
    message = "target has missing values in 3 rows\nTraceback: /srv/secret/path.py line 1"
    with closing(connect(world.client)) as conn:
        store.claim_job(conn, job_id, "token")
        store.finish_job(conn, job_id, JobStatus.FAILED, message=message)
    page = world.client.get(world.path("/projects/{p}/jobs/{job}")).text
    assert "target has missing values in 3 rows" in page
    assert "Traceback" not in page and "/srv/secret" not in page
    assert "Back to data analysis" in page and "analyze?target=species" in page
    assert "hx-trigger" not in page


def test_a_running_job_shows_what_the_engine_does(make_client):
    from fione.engine.events import Event

    world = make_world(make_client())
    world.login("vi")
    job_id = world.ids[world.p]["job"]
    with closing(connect(world.client)) as conn:
        store.claim_job(conn, job_id, "token")
        store.append_event(conn, job_id, Event("started", data={"n_rows": 150}))
        for trial, best in enumerate([0.4, 0.25]):
            data = {"family": "LightGBM", "trial": trial, "state": "complete", "best_so_far": best}
            store.append_event(conn, job_id, Event("trial", data=data))
    fragment = world.client.get(
        world.path("/projects/{p}/jobs/{job}/status"), headers={"HX-Request": "true"}
    ).text
    assert "Trying LightGBM models" in fragment and 'hx-trigger="every 2s"' in fragment
    assert re.search(r"Models tried</dt><dd>2<", fragment) and "0.25" in fragment
    assert re.search(r'<progress class="progress" max="100" value="\d+"', fragment)


# --- leak warnings ------------------------------------------------------------------------


def leak_frame(noise: float, name: str = "noisy", n: int = 300) -> pd.DataFrame:
    """``name`` is a noisy copy of the target ``label``, ``copy`` an identical one."""
    rng = np.random.default_rng(0)
    label = rng.choice(["no", "yes"], n)
    return pd.DataFrame(
        {
            "x": rng.normal(size=n),
            "z": rng.normal(size=n),
            name: (label == "yes") + rng.normal(0, noise, n),
            "copy": label,
            "label": label,
        }
    )


def alerts(page: str) -> dict[str, str]:
    """The text of each note above the columns -> its level."""
    found = re.findall(
        r'<div class="alert alert-(\w+)" role="note">.*?<span>(.*?)</span>', page, re.S
    )
    return {text: level for level, text in found}


def test_score_suspect_stays_selected(owner):
    client, pid, csrf = owner
    content = leak_frame(0.1, XSS[0]).to_csv(index=False).encode()  # scores 0.995
    page = client.get(location(upload(client, f"/projects/{pid}/upload", csrf, content))).text
    assert f'name="inputs" value="{escape(XSS[0])}" checked' in page
    assert "Predicts the answer suspiciously well on its own" in page
    assert "check that it is known at prediction time" in page
    notes = alerts(page)
    scores = next(text for text in notes if "suspiciously well" in text)
    assert notes[scores] == "warning" and scores.startswith("1 columns predict")
    assert "They stay checked" in scores
    leaks = next(text for text in notes if "might give the answer away" in text)
    assert notes[leaks] == "info" and leaks.startswith("1 columns")  # only the exact copy
    assert XSS[0] not in page


def test_a_weaker_score_suspect_is_an_info_note(owner):
    client, pid, csrf = owner
    content = leak_frame(0.3).to_csv(index=False).encode()  # scores 0.96
    page = client.get(location(upload(client, f"/projects/{pid}/upload", csrf, content))).text
    assert 'name="inputs" value="noisy" checked' in page
    notes = alerts(page)
    assert notes[next(text for text in notes if "suspiciously well" in text)] == "info"


def test_exact_suspect_is_still_deselected(owner):
    client, pid, csrf = owner
    content = leak_frame(0.1).to_csv(index=False).encode()
    page = client.get(location(upload(client, f"/projects/{pid}/upload", csrf, content))).text
    assert 'name="inputs" value="copy"' in page and 'value="copy" checked' not in page
    assert "Is identical to the column to predict" in page


def test_iris_keeps_all_four_inputs_selected(owner):
    """Twice the rows, so the score runs: both petal columns then score as high as a leak."""
    client, pid, csrf = owner
    content = pd.concat([iris_frame()] * 2).to_csv(index=False).encode()
    page = client.get(location(upload(client, f"/projects/{pid}/upload", csrf, content))).text
    for name in INPUTS:
        assert f'name="inputs" value="{name}" checked' in page
    assert "Predicts the answer suspiciously well on its own" in page


def test_an_id_in_the_order_of_the_target_stays_unchecked_with_both_notes(owner):
    client, pid, csrf = owner
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"row": range(300), "x": rng.normal(size=300)})
    frame["label"] = np.where(frame["row"] < 150, "no", "yes")
    content = frame.to_csv(index=False).encode()
    page = client.get(location(upload(client, f"/projects/{pid}/upload", csrf, content))).text
    assert 'value="row" aria-describedby="col-1-why col-1-warn"' in page
    assert "Looks like an ID" in page and "or where they are missing, follow the answer" in page
    assert not any("They stay checked" in text for text in alerts(page))  # it is not


def spy_leak_check(monkeypatch, partial=False) -> list[str]:
    """The targets ``leak_check`` runs for; with ``partial``, every check ran out of time."""
    calls, original = [], builtin.leak_check

    def spy(df, columns, target, **kwargs):
        calls.append(target)
        check = original(df, columns, target, **kwargs)
        return dataclasses.replace(check, partial=True) if partial else check

    monkeypatch.setattr(builtin, "leak_check", spy)
    return calls


def test_the_leak_check_runs_once_per_dataset_and_target(owner, monkeypatch):
    client, pid, csrf = owner
    calls = spy_leak_check(monkeypatch)
    content = leak_frame(0.1).to_csv(index=False).encode()
    url = location(upload(client, f"/projects/{pid}/upload", csrf, content))
    base = url.removesuffix("/analyze")
    hx = {"HX-Request": "true"}
    for target in ("label", "label", "x", "label", "x"):  # the HTMX target switch
        assert client.get(url, params={"target": target}, headers=hx).status_code == 200
    assert client.get(url).status_code == 200
    r = client.post(base + "/run", data=run_form(csrf, "label", ["x"], runtime="7"))
    assert r.status_code == 422  # re-rendered
    for path in ("", "?tab=columns", "/columns/noisy", "/train"):
        assert client.get(base + path).status_code == 200
    r = client.post(base + "/train", data={"csrf_token": csrf, "target": "label"})
    assert r.status_code == 422
    assert calls == ["label", "x"]


def test_a_partial_leak_check_is_noted_and_checked_again(owner, monkeypatch):
    client, pid, csrf = owner
    calls = spy_leak_check(monkeypatch, partial=True)
    content = leak_frame(0.1).to_csv(index=False).encode()
    url = location(upload(client, f"/projects/{pid}/upload", csrf, content))
    page = client.get(url).text
    assert any("some columns were not checked" in text for text in alerts(page))
    client.get(url)
    assert calls == ["label", "label"]  # not kept


def test_a_re_rendered_form_counts_the_posted_checkboxes(owner):
    client, pid, csrf = owner
    content = leak_frame(0.1).to_csv(index=False).encode()
    url = location(upload(client, f"/projects/{pid}/upload", csrf, content))
    form = run_form(csrf, "label", ["x", "copy"], runtime="7")  # copy back on, noisy off
    page = client.post(url.replace("/analyze", "/run"), data=form).text
    assert 'value="copy" checked' in page and 'value="noisy" checked' not in page
    texts = list(alerts(page))
    assert not any("They stay checked" in t or "They are unchecked" in t for t in texts)


# --- what viewers see ---------------------------------------------------------------------


def test_viewers_see_everything_read_only(make_client):
    world = make_world(make_client())
    world.login("vi")
    dashboard = world.client.get(world.path("/projects/{p}")).text
    assert "View only" in dashboard and "Sharing" not in dashboard  # only owners see members
    assert "/upload" not in dashboard and "/predict" not in dashboard
    analysis = world.client.get(world.path("/projects/{p}/datasets/{train}/analyze")).text
    assert 'id="run-form"' not in analysis and "cannot start training" in analysis
    summary = world.client.get(world.path("/projects/{p}/models/{model}/summary")).text
    assert "/predict" not in summary and "cannot make predictions" in summary
    assert stars_of(summary) >= 1


def test_owners_see_who_the_project_is_shared_with(make_client):
    world = make_world(make_client())
    world.login("ed")
    dashboard = world.client.get(world.path("/projects/{p}")).text
    assert "Shared with 2 people" in dashboard and ">vi<" in dashboard and ">co<" in dashboard


# --- escaping -----------------------------------------------------------------------------


def test_column_names_are_escaped_on_every_screen(make_client):
    client = make_client()
    user = add_user(client, "ed", Role.EDITOR)
    csrf = login(client, "ed")
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({XSS[0]: rng.normal(size=60), XSS[1]: rng.normal(size=60)})
    frame["label"] = np.where(frame[XSS[0]] > 0, "yes", "no")
    with closing(connect(client)) as conn:
        project = projects.create_project(conn, user, XSS[0])
    pid = project.id
    analysis_url = location(
        upload(
            client,
            f"/projects/{pid}/upload",
            csrf,
            frame.to_csv(index=False).encode(),
            XSS[1] + ".csv",
        )
    )
    pages = [client.get(analysis_url).text, client.get(f"/projects/{pid}").text]

    model = AutoML(TrainConfig(target="label", **FAST, max_runtime_secs=10)).fit(frame)
    prefix = f"projects/{pid}/models/xss/"
    save_model(model, client.app.state.storage, prefix, client.app.state.secret, image_tag="test")
    with closing(connect(client)) as conn:
        record = models.add_model(
            conn,
            project_id=pid,
            dataset_id=None,
            job_id=None,
            name=XSS[1],
            model=model,
            storage_prefix=prefix,
        )
    pages.append(client.get(f"/projects/{pid}/models/{record.id}/summary").text)
    predict_url = f"/projects/{pid}/models/{record.id}/predict"
    pages.append(client.get(predict_url).text)
    missing = upload(client, predict_url, csrf, b"other\n1\n")
    assert missing.status_code == 422
    pages.append(missing.text)
    columns_url = location(
        upload(
            client, predict_url, csrf, frame.drop(columns=["label"]).to_csv(index=False).encode()
        )
    )
    pages.append(client.get(columns_url).text)
    for html in pages:
        for payload in XSS + [escape(XSS[1], quote=False)]:
            assert payload not in html
        assert escape(XSS[0]) in html


# --- error pages and limits ---------------------------------------------------------------


def test_unknown_pages_are_an_html_404_for_browsers(owner):
    client, pid, _ = owner
    for path in (
        "/nope",
        "/projects/nope",
        f"/projects/{pid}/datasets/abc/analyze",
        f"/projects/{pid}/models/99999999999999999999/summary",
        f"/projects/{pid}/jobs/0",
    ):
        r = client.get(path, headers=HTML)
        assert r.status_code == 404, path
        assert "text/html" in r.headers["content-type"], path
        assert "We could not find that page" in r.text and 'href="/"' in r.text
        assert r.headers["content-security-policy"].startswith("default-src 'self'")
    api = client.get("/api/v1/nope", headers=HTML)
    assert api.status_code == 404 and api.json()["code"] == "not_found"
    assert client.get("/nope").headers["content-type"] == "application/json"  # not a browser


def test_a_404_page_in_japanese(owner):
    client, _, _ = owner
    r = client.get("/nope", headers={**HTML, "Accept-Language": "ja"})
    assert "ページが見つかりませんでした" in r.text and '<html lang="ja">' in r.text


def test_a_viewer_gets_a_friendly_403_page(make_client):
    world = make_world(make_client())
    world.login("vi")
    r = world.client.get(world.path("/projects/{p}/upload"))
    assert r.status_code == 403
    assert "You do not have permission" in r.text and "edit access" in r.text


def test_an_upload_over_the_limit_is_a_413_page(make_client):
    client = make_client(max_upload_bytes=1000)
    user = add_user(client, "ed", Role.EDITOR)
    csrf = login(client, "ed")
    with closing(connect(client)) as conn:
        pid = projects.create_project(conn, user, "P").id
    r = upload(client, f"/projects/{pid}/upload", csrf, iris_csv())  # 4 KB, under the slack
    assert r.status_code == 413 and "larger than the upload limit" in r.text
    big = b"a,b\n" + b"1,2\n" * 300_000  # over the limit plus the multipart slack
    r = upload(client, f"/projects/{pid}/upload", csrf, big, headers=HTML)
    assert r.status_code == 413
    assert "text/html" in r.headers["content-type"] and "too large to upload" in r.text
    assert dataset_count(client) == 0


def test_uploads_are_spooled_under_the_data_dir(owner, monkeypatch):
    client, pid, csrf = owner
    spooled = []
    original = uploads.SpooledTemporaryFile

    def spy(*args, **kwargs):
        spooled.append(kwargs.get("dir"))
        return original(*args, **kwargs)

    monkeypatch.setattr(uploads, "SpooledTemporaryFile", spy)
    assert upload(client, f"/projects/{pid}/upload", csrf, iris_csv()).status_code == 303
    assert spooled == [client.app.state.settings.data_dir / "tmp"]
    assert list((client.app.state.settings.data_dir / "tmp").iterdir()) == []


def test_pages_have_no_inline_script_or_style(make_client):
    world = make_world(make_client())
    world.login("ed")
    for template in (
        "/projects/{p}",
        "/projects/{p}/upload",
        "/projects/{p}/datasets/{train}/analyze",
        "/projects/{p}/jobs/{job}",
        "/projects/{p}/jobs/{predict_job}/result",
        "/projects/{p}/models/{model}/summary",
        "/projects/{p}/models/{model}/predict",
        "/projects/{p}/models/{model}/predict?dataset={test}",
    ):
        r = world.client.get(world.path(template))
        assert r.status_code == 200, template
        assert "style=" not in r.text and "<style" not in r.text, template
        assert not re.search(r"\son[a-z]+=", r.text), template
        assert not re.search(r"<script(?![^>]*\bsrc=\"/static/)", r.text), template


def test_the_wizard_in_japanese_uses_the_product_terms(make_client):
    world = make_world(make_client())
    world.login("ed")
    ja = {"Accept-Language": "ja"}
    analysis = world.client.get(
        world.path("/projects/{p}/datasets/{train}/analyze"), headers=ja
    ).text
    for term in ("データ分析", "予測する列", "入力する列", "最大実行時間", "実行"):
        assert term in analysis, term
    summary = world.client.get(world.path("/projects/{p}/models/{model}/summary"), headers=ja).text
    assert "予測結果サマリー" in summary and "Fione 君" in summary
    assert re.search(r'aria-label="5 段階中 星 \d つ"', summary)


def test_the_language_switch_never_returns_to_a_post_only_path(make_client):
    """Inline errors are rendered by the run posts; switching language must go to a page."""
    world = make_world(make_client())
    csrf = world.login("ed")

    def lang_next(html: str) -> str:
        return re.search(r'<input type="hidden" name="next" value="([^"]+)">', html).group(1)

    r = world.client.post(
        world.path("/projects/{p}/datasets/{train}/run"), data=run_form(csrf, inputs=[])
    )
    assert r.status_code == 422
    assert lang_next(r.text) == world.path("/projects/{p}/datasets/{train}/analyze?target=species")
    r = world.client.post(
        world.path("/projects/{p}/models/{model}/predict/run"),
        data={"csrf_token": csrf, "dataset_id": world.path("{test}"), "include": ["nope"]},
    )
    assert r.status_code == 422 and "unknown columns" in r.text
    assert lang_next(r.text) == world.path("/projects/{p}/models/{model}/predict?dataset={test}")
    for path in (lang_next(r.text).replace("&amp;", "&"),):
        assert world.client.get(path).status_code == 200


# --- fix round 1 ---------------------------------------------------------------------------


def gappy_frame(rows=1200) -> pd.DataFrame:
    """A gap in the column to predict far below the rows the analysis profiles."""
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"x": rng.normal(size=rows), "z": rng.normal(size=rows)})
    frame["y"] = np.where(frame["x"] > 0, "yes", "no")
    frame.loc[rows - 5, "y"] = None
    return frame


@pytest.mark.parametrize(
    ("frame", "form", "message"),
    [
        (gappy_frame(), {"target": "y", "inputs": ["x", "z"]}, "empty in 1 rows"),
        (
            pd.DataFrame({"x": range(20), "y": ["same"] * 20}),
            {"target": "y", "inputs": ["x"]},
            "same value in every row",
        ),
        (
            pd.DataFrame({"x": range(5), "y": ["a", "b", "a", "b", "a"]}),
            {"target": "y", "inputs": ["x"]},
            "at least 10 rows, and this data has 5",
        ),
        (
            pd.DataFrame({"x": range(20), "y": ["a", "b"] * 10}),
            {"target": "y", "inputs": ["x"], "task": "regression"},
            "Regression predicts numbers",
        ),
    ],
)
def test_a_run_the_engine_would_refuse_goes_back_to_the_analysis(
    owner, monkeypatch, frame, form, message
):
    monkeypatch.setattr(easyml, "PROFILE_MAX_ROWS", 500)  # the gap is beyond the sample
    client, pid, csrf = owner
    url = location(
        upload(client, f"/projects/{pid}/upload", csrf, frame.to_csv(index=False).encode())
    )
    page = client.get(url + "?target=y").text
    if "task" not in form:  # the warning is there before running (for the suggested type)
        assert message in page
    r = client.post(url.replace("/analyze", "/run"), data=run_form(csrf, **form))
    assert r.status_code == 422
    assert message in r.text and "Training would refuse the column to predict" in r.text
    assert job_count(client) == 0


def test_the_column_profile_is_computed_once_per_dataset(owner, monkeypatch):
    client, pid, csrf = owner
    calls = []
    original = easyml.sample_profile

    def counting(*args, **kwargs):
        calls.append(args[1].id)
        return original(*args, **kwargs)

    monkeypatch.setattr(easyml, "sample_profile", counting)
    url = location(upload(client, f"/projects/{pid}/upload", csrf, iris_csv()))
    for target in ("species", "petal width (cm)", "species"):
        assert client.get(url, params={"target": target}).status_code == 200
    client.post(url.replace("/analyze", "/run"), data=run_form(csrf, inputs=[]))  # 422
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("columns", "rows"), [(5, 50_000), (41, 48_780), (1000, 2000), (50_000, 500)]
)
def test_wide_data_is_profiled_on_fewer_rows(columns, rows):
    dataset = projects.Dataset(1, "p", "d", projects.DatasetType.TRAIN, 10**6, columns, [], "k", "")
    assert easyml._profile_rows(dataset) == rows


def test_the_summary_reads_the_training_target_once(make_client, monkeypatch):
    world = make_world(make_client())
    world.login("ed")
    calls = []
    original = easyml.target_baseline

    def counting(*args):
        calls.append(args[2:])
        return original(*args)

    monkeypatch.setattr(easyml, "target_baseline", counting)
    world.client.get(world.path("/projects/{p}/models/{model}/summary"))
    world.client.get(world.path("/projects/{p}/models/{model}/summary"))
    world.client.get(world.path("/projects/{p}"))
    assert len(calls) == 1


def test_importance_bars_are_hidden_from_screen_readers(make_client):
    world = make_world(make_client())
    world.login("ed")
    page = world.client.get(world.path("/projects/{p}/models/{model}/summary")).text
    bars = re.findall(r'<progress class="progress importance__bar"[^>]*>', page)
    assert bars and all('aria-hidden="true"' in bar for bar in bars)
    assert re.search(r'class="importance__value">\d+%<', page)  # the number is read instead


def test_polling_stops_when_the_job_cannot_be_shown(make_client, monkeypatch):
    world = make_world(make_client(raise_server_exceptions=False))
    world.login("vi")
    status = world.path("/projects/{p}/jobs/{job}/status")
    hx = {"HX-Request": "true"}
    with closing(connect(world.client)) as conn:  # access revoked
        projects.unshare_project(conn, models_owner(conn), world.p, "vi")
    r = world.client.get(status, headers=hx)
    assert r.status_code == 286 and "hx-trigger" not in r.text
    assert "We could not find that page" in r.text and 'hx-swap-oob="true"' in r.text
    assert "may have been deleted" in r.text and "Reload the page" not in r.text
    assert world.client.get(status, headers=HTML).status_code == 404  # a page view: 404 page

    world.login("ed")

    def boom(*args):
        raise RuntimeError("database gone")

    monkeypatch.setattr(easyml, "_job_view", boom)
    r = world.client.get(status, headers=hx)
    assert r.status_code == 286 and "Something went wrong" in r.text
    assert "database gone" not in r.text
    assert "may still be going" in r.text and "may have been deleted" not in r.text


def models_owner(conn):
    return next(u for u in auth.list_users(conn) if u.username == "ed")


def test_cancel_and_run_forms_are_protected_against_double_submits(make_client):
    world = make_world(make_client())
    world.login("ed")
    job = world.client.get(world.path("/projects/{p}/jobs/{job}")).text
    assert re.search(r'<form [^>]*/cancel" data-busy-form>', job)
    analysis = world.client.get(world.path("/projects/{p}/datasets/{train}/analyze")).text
    assert "data-run-form" in analysis
    script = world.client.get("/static/js/easyml.js").text
    assert 'document.addEventListener("submit"' in script  # delegated: swapped forms too


def test_a_dataset_with_more_than_1000_columns_can_be_run(owner, monkeypatch):
    client, pid, csrf = owner
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(rng.normal(size=(30, 1100)), columns=[f"c{i}" for i in range(1100)])
    frame["y"] = ["a", "b", "c"] * 10
    url = location(
        upload(client, f"/projects/{pid}/upload", csrf, frame.to_csv(index=False).encode())
    )
    inputs = [f"c{i}" for i in range(1100)]
    r = client.post(
        url.replace("/analyze", "/run"), data=run_form(csrf, "y", inputs), follow_redirects=False
    )
    assert r.status_code == 303, r.text
    monkeypatch.setattr(easyml, "MAX_FORM_FIELDS", 50)
    r = client.post(url.replace("/analyze", "/run"), data=run_form(csrf, "y", inputs))
    assert r.status_code == 422 and "too many columns to choose from" in r.text
    assert job_count(client) == 1


def test_an_unexpected_error_is_an_html_page_for_browsers(make_client):
    world = make_world(make_client(raise_server_exceptions=False))
    world.login("ed")
    with closing(connect(world.client)) as conn:
        key = conn.execute(
            "SELECT storage_key FROM datasets WHERE id = ?", (world.ids[world.p]["train"],)
        ).fetchone()[0]
    world.client.app.state.storage.delete(key)
    path = world.path("/projects/{p}/datasets/{train}/analyze")
    r = world.client.get(path, headers=HTML)
    assert r.status_code == 500 and "text/html" in r.headers["content-type"]
    assert "Something went wrong" in r.text and "Sign out" in r.text  # the header is kept
    assert "Traceback" not in r.text
    # Served outside the UI headers middleware, but with the same headers as every page.
    assert r.headers["content-security-policy"] == CSP
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "same-origin"
    api = world.client.get(
        f"/api/v1/projects/{world.p}/datasets/{world.ids[world.p]['train']}/preview", headers=HTML
    )
    assert api.status_code == 500 and api.json() == {"error": "internal error", "code": "internal"}


def test_error_pages_keep_the_signed_in_header(make_client):
    world = make_world(make_client())
    world.login("vi")
    r = world.client.get(world.path("/projects/{p}/upload"))
    assert r.status_code == 403
    assert "Sign out" in r.text and "Signed in as vi" in r.text
    r = world.client.get("/nope", headers=HTML)
    assert r.status_code == 404 and "Sign out" in r.text


def test_an_editor_member_gets_the_write_controls(make_client):
    world = make_world(make_client())
    world.login("co")
    analysis = world.client.get(world.path("/projects/{p}/datasets/{train}/analyze")).text
    assert 'id="run-form"' in analysis
    summary = world.client.get(world.path("/projects/{p}/models/{model}/summary")).text
    assert world.path('href="/projects/{p}/models/{model}/predict"') in summary
    dashboard = world.client.get(world.path("/projects/{p}")).text
    assert "Sharing" not in dashboard  # only owners see members


def test_the_result_of_a_training_job_is_404(make_client):
    world = make_world(make_client())
    world.login("ed")
    r = world.client.get(world.path("/projects/{p}/jobs/{job}/result"))
    assert r.status_code == 404


def test_objects_of_two_projects_cannot_be_mixed(make_client):
    world = make_world(make_client())
    csrf = world.login("ed")
    q_test = world.ids[world.q]["test"]
    r = world.client.get(world.path("/projects/{p}/models/{model}/predict") + f"?dataset={q_test}")
    assert r.status_code == 404
    form = {"csrf_token": csrf, "dataset_id": str(q_test), "include": ["petal width (cm)"]}
    r = world.client.post(world.path("/projects/{p}/models/{model}/predict/run"), data=form)
    assert r.status_code == 404 and job_count(world.client) == 4


def test_training_on_a_dataset_whose_data_is_gone_is_404(make_client):
    """Not a 500: the target check reads the column, and the file is missing."""
    world = make_world(make_client())
    csrf = world.login("ed")
    train = world.ids[world.p]["train"]
    with closing(connect(world.client)) as conn:
        key = conn.execute("SELECT storage_key FROM datasets WHERE id = ?", (train,)).fetchone()[0]
    world.client.app.state.storage.delete(key)
    r = world.client.post(
        f"/api/v1/projects/{world.p}/jobs/automl",
        json={"dataset_id": train, "config": {"target": "species"}},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 404 and r.json()["error"] == "dataset not found"
    r = world.client.post(world.path("/projects/{p}/datasets/{train}/run"), data=run_form(csrf))
    assert r.status_code == 404 and "text/html" in r.headers["content-type"]
    assert job_count(world.client) == 4
