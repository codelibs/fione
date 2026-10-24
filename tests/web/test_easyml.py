"""The EasyML wizard through its HTML endpoints: the iris and a regression flow with the job
runner in process, and the refusals (bad files, bad settings, CSRF, other projects, viewers),
escaping, polling, cancelling, error pages and upload limits."""

import csv
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
from fione.auth.roles import Role
from fione.engine.artifact import save_model
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.models import service as models
from fione.projects import service as projects
from fione.web import easyml, uploads
from web_helpers import FAST, iris_test_csv, make_world

INPUTS = ["sepal length (cm)", "sepal width (cm)", "petal length (cm)", "petal width (cm)"]
XSS = ["<script>alert(1)</script>", '"><img src=x onerror=alert(1)>']
HTML = {"Accept": "text/html,application/xhtml+xml"}


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
    assert "Shared with 1 people" in dashboard and ">vi<" in dashboard


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
