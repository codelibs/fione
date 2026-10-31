"""The app as a whole: health, docs, error shapes, the lifespan and concurrency."""

import logging
import threading

import pyarrow as pa
import pytest
from fastapi.testclient import TestClient

from api_helpers import add_user, bearer, make_settings
from fione.api import app as app_module
from fione.api import routes_projects
from fione.api.app import create_app
from fione.version import __version__


def test_health_is_unauthenticated_and_minimal(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": __version__}


def test_docs_and_schema_need_no_auth(client):
    assert client.get("/api/docs").status_code == 200
    schema = client.get("/api/openapi.json").json()
    assert "/api/v1/projects/{project_id}/datasets" in schema["paths"]
    upload = schema["paths"]["/api/v1/projects/{project_id}/datasets"]["post"]
    assert "multipart/form-data" in upload["requestBody"]["content"]
    assert client.get("/docs").status_code == 404 and client.get("/redoc").status_code == 404
    assert client.get("/api/docs/oauth2-redirect").status_code == 200
    assert client.get("/docs/oauth2-redirect").status_code == 404


def test_unknown_routes_and_methods_use_the_error_shape(client):
    assert client.get("/api/v1/nope").json() == {"error": "Not Found", "code": "not_found"}
    r = client.put("/api/v1/health")
    assert r.status_code == 405 and r.json()["code"] == "method_not_allowed"


def test_ids_beyond_sqlite_integers_are_422_not_500(client):
    headers = bearer(client, add_user(client, "root").id)
    r = client.delete(f"/api/v1/tokens/{2**63}", headers=headers)
    assert r.status_code == 422


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("boom at /data/secret/path"),
        PermissionError(13, "Permission denied", "/data/objects/x"),
        pa.ArrowInvalid("Could not open /data/objects/y"),
    ],
    ids=["runtime", "os-permission", "arrow"],
)
def test_unexpected_errors_are_500_without_internals(make_client, monkeypatch, caplog, error):
    client = make_client(raise_server_exceptions=False)
    headers = bearer(client, add_user(client, "alice").id)

    def broken(*args, **kwargs):
        raise error

    monkeypatch.setattr(routes_projects.service, "create_project", broken)
    with caplog.at_level(logging.ERROR, logger="fione.api"):
        r = client.post("/api/v1/projects", json={"name": "p"}, headers=headers)
    assert r.status_code == 500
    assert r.json() == {"error": "internal error", "code": "internal"}
    assert "/data" not in r.text and "Traceback" not in r.text
    assert "Traceback" in caplog.text and "/data" in caplog.text  # logged only


def test_twenty_concurrent_requests_each_get_their_own_connection(client):
    headers = bearer(client, add_user(client, "alice").id)
    project = client.post("/api/v1/projects", json={"name": "p"}, headers=headers).json()["id"]
    statuses = []
    barrier = threading.Barrier(20)

    def call(n):
        barrier.wait()
        if n % 2:
            r = client.get(f"/api/v1/projects/{project}", headers=headers)
        else:
            r = client.post("/api/v1/projects", json={"name": f"p{n}"}, headers=headers)
        statuses.append(r.status_code)

    threads = [threading.Thread(target=call, args=(n,)) for n in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(statuses) == [200] * 10 + [201] * 10
    assert len(client.get("/api/v1/projects", headers=headers).json()) == 11


class RecordingRunner:
    calls: list[str] = []

    def __init__(self, settings, db_path):
        self.db_path = db_path

    def recover_orphans(self):
        self.calls.append("recover_orphans")

    def start(self):
        self.calls.append("start")

    def stop(self):
        self.calls.append("stop")


def test_lifespan_recovers_orphans_then_starts_the_runner(tmp_path, monkeypatch):
    RecordingRunner.calls = []
    monkeypatch.setattr(app_module, "JobRunner", RecordingRunner)
    app = create_app(make_settings(tmp_path / "data", runner_enabled=True))
    with TestClient(app) as client:
        assert RecordingRunner.calls == ["recover_orphans", "start"]
        assert isinstance(client.app.state.runner, RecordingRunner)
    assert RecordingRunner.calls == ["recover_orphans", "start", "stop"]
    RecordingRunner.calls = []
    with TestClient(create_app(make_settings(tmp_path / "data", runner_enabled=False))):
        pass
    with TestClient(create_app(make_settings(tmp_path / "data"), start_runner=False)):
        pass
    assert RecordingRunner.calls == []


def test_secret_and_hashes_never_reach_responses_or_logs(client, caplog):
    with caplog.at_level(logging.DEBUG):
        add_user(client, "alice")
        body = {"username": "alice", "password": "password-123"}
        r = client.post("/api/v1/auth/login", json=body)
        me = client.get("/api/v1/auth/me")
    secret = client.app.state.secret
    for text in (r.text, me.text, str(r.headers), caplog.text):
        assert secret.hex() not in text and "scrypt$" not in text
        assert "password-123" not in text
