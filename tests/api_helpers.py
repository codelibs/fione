"""Helpers shared by the API tests (fixtures are in conftest.py)."""

import time
import uuid
from functools import cache

from sklearn.datasets import load_iris

from fione import db
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.config import Settings
from fione.engine.artifact import save_model
from fione.engine.automl import AutoML
from fione.engine.config import TrainConfig
from fione.models import service as models
from fione.notebooks.launcher import LauncherError

PW = "password-123"
CSV = b"a,b,label\n1,x,yes\n2,y,no\n3,x,yes\n4,z,no\n"


def make_settings(data_dir, **overrides) -> Settings:
    values = {
        "data_dir": data_dir,
        "storage_url": "",
        "secret_key_path": None,
        "runner_enabled": False,
        "setup_token": None,
        "cookie_secure": False,
        "trust_proxy": False,
        "explain_after_training": False,
        **overrides,
    }
    return Settings(**values)


def connect(client):
    return db.connect(client.app.state.db_path)


def add_user(client, username, role=Role.EDITOR, password=PW):
    conn = connect(client)
    try:
        return auth.create_user(conn, username, password, role)
    finally:
        conn.close()


def login(client, username, password=PW) -> str:
    """Log the client in (its cookie jar keeps the session); returns the CSRF token."""
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["csrf_token"]


def bearer(client, user_id, name="test") -> dict:
    conn = connect(client)
    try:
        return {"Authorization": f"Bearer {auth.issue_token(conn, user_id, name)}"}
    finally:
        conn.close()


def upload(client, project_id, data=CSV, *, name="train", type="train", filename="d.csv", **kw):
    return client.post(
        f"/api/v1/projects/{project_id}/datasets",
        data={"name": name, "type": type},
        files={"file": (filename, data, "text/csv")},
        **kw,
    )


def iris_frame():
    df = load_iris(as_frame=True).frame
    df["species"] = df.pop("target").map({0: "setosa", 1: "versicolor", 2: "virginica"})
    return df


def iris_csv() -> bytes:
    return iris_frame().to_csv(index=False).encode()


# Small enough to train in about a second.
FAST_CONFIG = {"target": "species", "max_runtime_secs": 10, "max_models": 1, "nfolds": 2}


@cache
def tiny_model():
    """An iris classifier, trained once per session."""
    return AutoML(TrainConfig(**FAST_CONFIG), lambda event: None).fit(iris_frame())


def store_model(conn, storage, secret, project_id, name="iris model", model=None):
    """Save ``model`` (the tiny one by default) signed with ``secret`` and record it."""
    model = model or tiny_model()
    prefix = f"projects/{project_id}/models/{uuid.uuid4().hex}/"
    save_model(model, storage, prefix, secret, image_tag="test")
    return models.add_model(
        conn,
        project_id=project_id,
        dataset_id=None,
        job_id=None,
        name=name,
        model=model,
        storage_prefix=prefix,
    )


def wait_job(client, job_id, headers, timeout=60.0) -> dict:
    """Poll ``GET /jobs/{id}`` until the job has finished; returns it."""
    deadline = time.monotonic() + timeout
    while True:
        job = client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()
        if job["status"] in ("done", "failed", "cancelled"):
            return job
        if time.monotonic() > deadline:
            raise AssertionError(f"job {job_id} still {job['status']}")
        time.sleep(0.1)


# The notebook settings of the notebook tests: the launcher is replaced by a FakeLauncher.
NOTEBOOK_SETTINGS = {
    "notebook_url": "http://127.0.0.1:8888",
    "public_url": "http://127.0.0.1:8080",
    "notebook_launcher_url": "http://launcher",
    "notebook_launcher_secret": "x" * 32,
}


class FakeLauncher:
    """Stands in for ``HttpLauncher``: ``calls`` records ``(method, user_id[, body])``,
    ``states`` holds each user's container state, and ``fail`` (a ``LauncherError``) is
    raised by every call while set."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.states: dict[int, str] = {}
        self.fail = None

    def _call(self, *call):
        self.calls.append(call)
        if self.fail is not None:
            raise self.fail

    def ensure(self, user_id, body):
        self._call("ensure", user_id, body)
        if self.states.get(user_id, "absent") != "absent":
            raise LauncherError("exists")
        self.states[user_id] = "starting"
        return "starting"

    def status(self, user_id):
        self._call("status", user_id)
        return self.states.get(user_id, "absent")

    def stop(self, user_id):
        self._call("stop", user_id)
        self.states.pop(user_id, None)

    def purge(self, user_id):
        self._call("purge", user_id)
        self.states.pop(user_id, None)

    def bodies(self) -> list[dict]:
        return [c[2] for c in self.calls if c[0] == "ensure"]


def notebook_client(make_client, **overrides):
    """A client of an install with notebooks, whose launcher is a FakeLauncher."""
    client = make_client(**NOTEBOOK_SETTINGS, **overrides)
    client.app.state.notebook_launcher = FakeLauncher()
    return client
