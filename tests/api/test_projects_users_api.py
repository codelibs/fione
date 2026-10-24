"""Users (admin), projects, sharing, and project deletion with running jobs."""

import logging
import threading
import time

import pytest
from api_helpers import PW, add_user, bearer, connect, login, upload

from fione import db
from fione.api import routes_projects
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.jobs import store
from fione.jobs.store import JobStatus


@pytest.fixture
def people(client):
    """An admin, the editor owner of project P, and three more users; bearer headers."""
    users = {
        "root": add_user(client, "root", Role.ADMIN),
        "owner": add_user(client, "owner"),
        "editor": add_user(client, "editor"),
        "viewer": add_user(client, "viewer", Role.VIEWER),
        "outsider": add_user(client, "outsider"),
    }
    return {name: (user, bearer(client, user.id)) for name, user in users.items()}


def h(people, name):
    return people[name][1]


def new_project(client, people, name="P", who="owner") -> str:
    r = client.post("/api/v1/projects", json={"name": name}, headers=h(people, who))
    assert r.status_code == 201, r.text
    return r.json()["id"]


# --- users ---------------------------------------------------------------------------


def test_user_crud(client, people):
    root = h(people, "root")
    r = client.post(
        "/api/v1/users", json={"username": "carol", "password": PW, "role": "viewer"}, headers=root
    )
    assert r.status_code == 201
    carol = r.json()
    assert carol == {"id": carol["id"], "username": "carol", "role": "viewer"}
    listing = client.get("/api/v1/users", headers=root)
    assert [u["username"] for u in listing.json()] == [
        "root",
        "owner",
        "editor",
        "viewer",
        "outsider",
        "carol",
    ]
    assert "scrypt" not in listing.text and "password" not in listing.text
    r = client.patch(f"/api/v1/users/{carol['id']}", json={"role": "editor"}, headers=root)
    assert r.json()["role"] == "editor"
    login(client, "carol")
    r = client.patch(
        f"/api/v1/users/{carol['id']}", json={"password": "reset-password-1"}, headers=root
    )
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401  # the reset ended the session
    login(client, "carol", "reset-password-1")
    assert client.delete(f"/api/v1/users/{carol['id']}", headers=root).status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.delete(f"/api/v1/users/{carol['id']}", headers=root).status_code == 404


@pytest.mark.parametrize(
    ("body", "fragment"),
    [
        ({"username": "bad name", "password": PW, "role": "editor"}, "username"),
        ({"username": "dave", "password": "short", "role": "editor"}, "password"),
        ({"username": "dave", "password": PW, "role": "owner"}, "role"),
        ({"username": "dave", "password": PW}, "role"),
    ],
)
def test_user_create_validation(client, people, body, fragment):
    r = client.post("/api/v1/users", json=body, headers=h(people, "root"))
    assert r.status_code == 422
    assert r.json()["code"] == "invalid" and fragment in r.json()["error"]
    assert "short" not in r.json()["error"]  # inputs are never echoed


def test_patch_needs_a_change(client, people):
    user_id = people["editor"][0].id
    r = client.patch(f"/api/v1/users/{user_id}", json={}, headers=h(people, "root"))
    assert r.status_code == 422


def test_last_admin_cannot_be_demoted_or_deleted(client, people):
    root = h(people, "root")
    root_id = people["root"][0].id
    r = client.patch(f"/api/v1/users/{root_id}", json={"role": "editor"}, headers=root)
    assert r.status_code == 409
    assert r.json() == {"error": "the last admin cannot be removed or demoted", "code": "conflict"}
    assert client.delete(f"/api/v1/users/{root_id}", headers=root).status_code == 409
    editor_id = people["editor"][0].id
    client.patch(f"/api/v1/users/{editor_id}", json={"role": "admin"}, headers=root)
    assert client.delete(f"/api/v1/users/{root_id}", headers=root).status_code == 204


def test_deleting_an_owner_of_projects_or_jobs_is_409(client, people):
    root = h(people, "root")
    project = new_project(client, people)
    r = client.delete(f"/api/v1/users/{people['owner'][0].id}", headers=root)
    assert r.status_code == 409
    assert r.json()["error"] == "the user owns 1 project(s); delete them first"
    conn = connect(client)
    store.enqueue(conn, "automl", project, people["editor"][0].id, {})
    conn.close()
    r = client.delete(f"/api/v1/users/{people['editor'][0].id}", headers=root)
    assert r.status_code == 409 and "job" in r.json()["error"]


# --- projects ---------------------------------------------------------------------------


def test_project_create_list_and_detail(client, people):
    project = new_project(client, people, "売上予測")
    r = client.get(f"/api/v1/projects/{project}", headers=h(people, "owner"))
    detail = r.json()
    assert detail["name"] == "売上予測"
    assert detail["owner"] == "owner" and detail["access"] == "owner"
    assert detail["members"] == []
    assert [p["id"] for p in client.get("/api/v1/projects", headers=h(people, "owner")).json()] == [
        project
    ]
    assert client.get("/api/v1/projects", headers=h(people, "outsider")).json() == []
    assert [p["id"] for p in client.get("/api/v1/projects", headers=h(people, "root")).json()] == [
        project
    ]


def test_share_unshare_and_effective_access(client, people):
    project = new_project(client, people)
    owner = h(people, "owner")
    share = f"/api/v1/projects/{project}/share"
    for username, access in [("editor", "editor"), ("viewer", "editor"), ("outsider", "viewer")]:
        r = client.post(share, json={"username": username, "access": access}, headers=owner)
        assert r.status_code == 204
    detail = client.get(f"/api/v1/projects/{project}", headers=owner).json()
    assert detail["members"] == [
        {"username": "editor", "access": "editor"},
        {"username": "outsider", "access": "viewer"},
        {"username": "viewer", "access": "editor"},
    ]
    expected = {
        "root": "owner",
        "owner": "owner",
        "editor": "editor",
        "viewer": "viewer",
        "outsider": "viewer",
    }
    for name, access in expected.items():
        r = client.get(f"/api/v1/projects/{project}", headers=h(people, name))
        assert r.json()["access"] == access, name
    # read but not write: no upload, no delete, no sharing
    assert upload(client, project, headers=h(people, "outsider")).status_code == 403
    assert upload(client, project, headers=h(people, "viewer")).status_code == 403
    assert upload(client, project, headers=h(people, "editor")).status_code == 201
    r = client.delete(f"/api/v1/projects/{project}", headers=h(people, "editor"))
    assert r.status_code == 403
    assert client.delete(f"{share}/outsider", headers=owner).status_code == 204
    r = client.get(f"/api/v1/projects/{project}", headers=h(people, "outsider"))
    assert r.status_code == 404
    assert client.delete(f"{share}/outsider", headers=owner).status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"username": "owner", "access": "viewer"},
        {"username": "editor", "access": "owner"},
        {"username": "ghost", "access": "editor"},
    ],
    ids=["the-owner", "owner-access", "unknown-user"],
)
def test_share_validation(client, people, body):
    project = new_project(client, people)
    r = client.post(f"/api/v1/projects/{project}/share", json=body, headers=h(people, "owner"))
    assert r.status_code == 422


def test_missing_project_is_404_even_for_admins(client, people):
    for name in ("root", "owner"):
        r = client.get("/api/v1/projects/nope", headers=h(people, name))
        assert r.status_code == 404
        assert r.json() == {"error": "project not found", "code": "not_found"}


# --- deleting a project with jobs ------------------------------------------------------------


class FakeRunner:
    """Cancels like JobRunner (queued -> cancelled, running -> cancelled), recording the
    order of events so the test can check cancellation came before deletion."""

    def __init__(self, db_path, delay=0.0):
        self.db_path = db_path
        self.delay = delay
        self.cancelled = []
        self.project_existed = []

    def cancel(self, job_id):
        time.sleep(self.delay)
        conn = db.connect(self.db_path)
        try:
            job = store.get_job(conn, job_id)
            exists = conn.execute(
                "SELECT 1 FROM projects WHERE id = ?", (job.project_id,)
            ).fetchone()
            self.project_existed.append(exists is not None)
            self.cancelled.append(job_id)
            if store.cancel_queued(conn, job_id):
                return True
            store.request_cancel(conn, job_id)
            return store.finish_job(conn, job_id, JobStatus.CANCELLED)
        finally:
            conn.close()


def _jobs_with_logs(client, project, owner_id):
    conn = connect(client)
    queued = store.enqueue(conn, "automl", project, owner_id, {})
    running = store.enqueue(conn, "automl", project, owner_id, {})
    store.claim_job(conn, running.id, "token")
    done = store.enqueue(conn, "automl", project, owner_id, {})
    store.claim_job(conn, done.id, "token")
    store.finish_job(conn, done.id, JobStatus.DONE)
    conn.close()
    logs = client.app.state.settings.data_dir / "jobs"
    logs.mkdir(parents=True, exist_ok=True)
    for job in (queued, running, done):
        (logs / f"{job.id}.log").write_text("log")
    return queued.id, running.id, done.id


def test_deleting_a_project_cancels_its_jobs_first_and_removes_everything(client, people):
    project = new_project(client, people)
    assert upload(client, project, headers=h(people, "owner")).status_code == 201
    queued, running, done = _jobs_with_logs(client, project, people["owner"][0].id)
    runner = FakeRunner(client.app.state.db_path)
    client.app.state.runner = runner
    r = client.delete(f"/api/v1/projects/{project}", headers=h(people, "owner"))
    assert r.status_code == 204
    assert sorted(runner.cancelled) == [queued, running]
    assert runner.project_existed == [True, True]
    conn = connect(client)
    for table in ("projects", "datasets", "jobs", "project_members"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table
    conn.close()
    assert client.app.state.storage.list(f"projects/{project}/") == []
    assert list((client.app.state.settings.data_dir / "jobs").iterdir()) == []


def test_project_deletion_waits_for_cancels_only_so_long(client, people, monkeypatch, caplog):
    monkeypatch.setattr(routes_projects, "CANCEL_WAIT_SECS", 0.2)
    project = new_project(client, people)
    _jobs_with_logs(client, project, people["owner"][0].id)
    client.app.state.runner = FakeRunner(client.app.state.db_path, delay=1.0)
    started = time.monotonic()
    with caplog.at_level(logging.WARNING):
        r = client.delete(f"/api/v1/projects/{project}", headers=h(people, "owner"))
    assert r.status_code == 204
    assert time.monotonic() - started < 0.9  # both cancels ran in parallel, under the deadline
    assert "did not stop within" in caplog.text
    for thread in threading.enumerate():
        if thread.name.startswith("fione-cancel"):
            thread.join()


def test_deleting_a_project_without_a_runner_still_removes_its_jobs(client, people):
    project = new_project(client, people)
    _jobs_with_logs(client, project, people["owner"][0].id)
    assert client.app.state.runner is None
    r = client.delete(f"/api/v1/projects/{project}", headers=h(people, "root"))
    assert r.status_code == 204
    conn = connect(client)
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    conn.close()


def test_a_viewer_role_owner_cannot_delete_or_share(client, people):
    project = new_project(client, people)
    conn = connect(client)
    auth.set_role(conn, people["owner"][0].id, Role.VIEWER)
    conn.close()
    owner = h(people, "owner")
    assert client.get(f"/api/v1/projects/{project}", headers=owner).json()["access"] == "viewer"
    assert client.delete(f"/api/v1/projects/{project}", headers=owner).status_code == 403
    body = {"username": "editor", "access": "viewer"}
    r = client.post(f"/api/v1/projects/{project}/share", json=body, headers=owner)
    assert r.status_code == 403


def test_project_deletion_uses_at_most_eight_cancel_threads(client, people, monkeypatch):
    project = new_project(client, people)
    conn = connect(client)
    for _ in range(12):
        store.enqueue(conn, "automl", project, people["owner"][0].id, {})
    conn.close()
    sizes = []
    real = routes_projects.ThreadPoolExecutor

    def recording(max_workers, **kwargs):
        sizes.append(max_workers)
        return real(max_workers=max_workers, **kwargs)

    monkeypatch.setattr(routes_projects, "ThreadPoolExecutor", recording)
    runner = FakeRunner(client.app.state.db_path)
    client.app.state.runner = runner
    r = client.delete(f"/api/v1/projects/{project}", headers=h(people, "owner"))
    assert r.status_code == 204
    assert sizes == [routes_projects.MAX_CANCEL_THREADS] == [8]
    assert len(runner.cancelled) == 12
