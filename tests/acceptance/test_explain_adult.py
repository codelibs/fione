"""Explanation targets on Adult: additivity, request and job times, stored sizes.

One 120 s training on the engine acceptance split, saved and recorded as the AutoML job does,
then each target checked against it. Slow, needs the network and an idle machine, so it only
runs with ``-m acceptance``:
``uv run pytest -m acceptance tests/acceptance/test_explain_adult.py -q -s``.
"""

import dataclasses
import io
import json
import signal
import time
from types import SimpleNamespace

import numpy as np
import pytest
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split

from api_helpers import make_settings
from fione import db
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.config import load_secret
from fione.engine import explain
from fione.engine.artifact import save_model
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.jobs import explain_handler, store, worker
from fione.jobs.store import JobStatus
from fione.models import explanations
from fione.models import service as models
from fione.models.live import LiveModels
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.service import DatasetType
from fione.storage import open_storage

pytestmark = pytest.mark.acceptance

KIB = 1024


def _download(fetch):
    try:
        return fetch()
    except Exception as e:  # any network, cache or parsing failure means no data to test on
        pytest.skip(f"dataset download failed: {type(e).__name__}: {e}")


def _csv(frame) -> io.BytesIO:
    return io.BytesIO(frame.to_csv(index=False).encode())


@pytest.fixture(scope="module")
def adult(tmp_path_factory):
    """The training split uploaded as a CSV, trained on as read back (as the AutoML job
    does), the model saved and recorded; the test split uploaded as a predict dataset."""
    frame = _download(lambda: fetch_openml("adult", version=2, as_frame=True).frame)
    train, test = train_test_split(frame, test_size=0.25, random_state=0)
    root = tmp_path_factory.mktemp("explain-adult")
    settings = make_settings(root / "data")
    storage = open_storage(settings)
    secret = load_secret(settings)
    conn = db.connect(root / "fione.db")
    db.migrate(conn)
    owner = auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR)
    project = projects.create_project(conn, owner, "adult")
    dataset = ingest.ingest_csv(storage, conn, project.id, "train", DatasetType.TRAIN, _csv(train))
    rows = ingest.ingest_csv(
        storage, conn, project.id, "test", DatasetType.PREDICT, _csv(test.drop(columns="class"))
    )
    model = AutoML(TrainConfig(target="class", max_runtime_secs=120, seed=0)).fit(
        ingest.read_dataset(storage, dataset)
    )
    prefix = f"projects/{project.id}/models/adult/"
    save_model(
        dataclasses.replace(model, diagnostics=None), storage, prefix, secret, image_tag="test"
    )
    record = models.add_model(
        conn,
        project_id=project.id,
        dataset_id=dataset.id,
        job_id=None,
        name="adult",
        model=model,
        storage_prefix=prefix,
    )
    print(f"\n  members: {model.leaderboard[model.leaderboard['weight'] > 0]['model'].tolist()}")
    yield SimpleNamespace(
        conn=conn,
        storage=storage,
        secret=secret,
        settings=settings,
        owner=owner,
        project=project,
        dataset=dataset,
        record=models.get_model(conn, record.id),
        test=ingest.read_dataset(storage, rows),
    )
    conn.close()


def test_diagnostics_stay_small(adult):
    stored = adult.record.diagnostics
    assert stored is not None and stored["task"] == "classification" and "roc" in stored
    size = len(json.dumps(stored))
    print(f"\n  diagnostics {size / KIB:.1f} KiB")
    assert size <= 64 * KIB


def test_contributions_add_up_on_1000_test_rows(adult):
    model = models.load_trained(adult.storage, adult.record, adult.secret)
    rows = adult.test.head(1_000)
    c = explain.contributions(model, rows)
    np.testing.assert_allclose(c.values.sum(-1) + c.bias, c.prediction, rtol=0, atol=1e-12)
    positive = model.predict_proba(rows).to_numpy()[:, 1]  # binary explains classes_[1]
    worst = float(np.abs(c.prediction[:, 0] - positive).max())
    print(f"\n  worst |bias + sum - p({model.classes_[1]})| over 1,000 rows: {worst:.2e}")
    assert worst <= 1e-5


def test_contributions_for_100_rows_through_live_models(adult):
    """The per-request cost, with the model cached, within 2 s; the first request, which
    loads the model, only loosely bounded."""
    live = LiveModels(adult.storage, adult.secret)
    rows = adult.test.head(100)
    started = time.perf_counter()
    with live.use(adult.record) as model:
        explain.contributions(model, rows)
    cold = time.perf_counter() - started
    started = time.perf_counter()
    with live.use(adult.record) as model:
        explain.contributions(model, rows)
    warm = time.perf_counter() - started
    print(f"\n  100 rows of contributions: {cold:.2f} s with the load, {warm:.2f} s cached")
    assert warm <= 2.0
    assert cold <= 10.0


def test_partial_dependence_of_one_column_on_request(adult):
    """As the API computes it: the spread read of the background, then the curve."""
    live = LiveModels(adult.storage, adult.secret)
    times = {}
    with live.use(adult.record) as model:
        n = explain.pd_rows(model, explain.PD_ROWS, explain.PD_GRID)
        for column in model.columns:
            started = time.perf_counter()
            background = ingest.read_dataset_spread(
                adult.storage, adult.dataset, n, model.columns, per_group=n
            )
            explain.partial_dependence(model, background, column, max_rows=n)
            times[column] = time.perf_counter() - started
    slowest = max(times, key=times.get)
    print(f"\n  partial dependence: slowest {slowest} {times[slowest]:.2f} s")
    assert times[slowest] <= 5.0


def test_the_explain_job(adult):
    before = signal.getsignal(signal.SIGTERM)
    job = explanations.submit_explain(adult.conn, adult.owner, adult.project.id, adult.record.id)
    assert store.claim_job(adult.conn, job.id, "token")
    started = time.monotonic()
    try:
        worker._run(adult.conn, store.get_job(adult.conn, job.id), adult.settings)
    finally:
        signal.signal(signal.SIGTERM, before)
    elapsed = time.monotonic() - started
    done = store.get_job(adult.conn, job.id)
    assert done.status is JobStatus.DONE, done.message
    stored = explanations.get_explanation(adult.conn, adult.record.id)
    size = len(explanations.payload_json(stored.payload).encode())
    curves = stored.payload["partial_dependence"]
    print(f"\n  explain job {elapsed:.1f} s, payload {size / KIB:.0f} KiB, {len(curves)} curves")
    assert size <= 1024 * KIB
    assert len(curves) == explain_handler.PD_COLUMNS  # Adult has 14 inputs
    assert elapsed <= 60
