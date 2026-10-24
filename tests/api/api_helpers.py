"""Helpers shared by the API tests (fixtures are in conftest.py)."""

from fione import db
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.config import Settings

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
