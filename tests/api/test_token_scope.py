"""Notebook-scope tokens: where they work, what they cannot do, and how tokens expire.

A notebook token is a bearer token with ``scope == "notebook"`` and an expiry, minted for the
notebook container. It acts as its user capped at editor, and only on the routes of ALLOWED.
Every API route must be in exactly one of ALLOWED, DENIED and PUBLIC.
"""

import re

import pytest

from api_helpers import PW, add_user, bearer, connect, iris_csv, login
from fione.api.deps import NOTEBOOK_SCOPE_ROUTES
from fione.auth import service
from fione.auth.roles import Role
from fione.auth.tokens import TokenScope
from fione.jobs import store
from fione.jobs.store import JobStatus

API = "/api/v1"

PUBLIC = {
    ("POST", "/auth/first-admin"),
    ("POST", "/auth/login"),
    ("GET", "/auth/status"),
    ("GET", "/health"),
}

DENIED = {
    ("POST", "/auth/logout"),
    ("GET", "/auth/me"),
    ("POST", "/auth/password"),
    ("GET", "/tokens"),
    ("POST", "/tokens"),
    ("DELETE", "/tokens/{token_id}"),
    ("GET", "/users"),
    ("POST", "/users"),
    ("PATCH", "/users/{user_id}"),
    ("DELETE", "/users/{user_id}"),
    ("POST", "/modules"),
    ("DELETE", "/modules/{module_id}"),
    ("POST", "/projects/{project_id}/models/import"),
    ("POST", "/projects/{project_id}/share"),
    ("DELETE", "/projects/{project_id}/share/{username}"),
}

ALLOWED = {
    ("GET", "/jobs"),
    ("DELETE", "/jobs"),
    ("GET", "/jobs/{job_id}"),
    ("DELETE", "/jobs/{job_id}"),
    ("POST", "/jobs/{job_id}/cancel"),
    ("GET", "/jobs/{job_id}/events"),
    ("GET", "/models/{model_id}"),
    ("DELETE", "/models/{model_id}"),
    ("POST", "/models/{model_id}/contributions"),
    ("GET", "/models/{model_id}/diagnostics"),
    ("GET", "/models/{model_id}/explanations"),
    ("GET", "/models/{model_id}/export"),
    ("POST", "/models/{model_id}/partial-dependence"),
    ("GET", "/models/{model_id}/serving"),
    ("GET", "/models/{model_id}/serving/info"),
    ("GET", "/modules"),
    ("GET", "/projects"),
    ("POST", "/projects"),
    ("GET", "/projects/{project_id}"),
    ("DELETE", "/projects/{project_id}"),
    ("GET", "/projects/{project_id}/datasets"),
    ("POST", "/projects/{project_id}/datasets"),
    ("GET", "/projects/{project_id}/datasets/{dataset_id}"),
    ("DELETE", "/projects/{project_id}/datasets/{dataset_id}"),
    ("GET", "/projects/{project_id}/datasets/{dataset_id}/columns/{column}"),
    ("GET", "/projects/{project_id}/datasets/{dataset_id}/download"),
    ("GET", "/projects/{project_id}/datasets/{dataset_id}/preview"),
    ("GET", "/projects/{project_id}/datasets/{dataset_id}/profile"),
    ("GET", "/projects/{project_id}/exports/{job_id}"),
    ("POST", "/projects/{project_id}/jobs/automl"),
    ("POST", "/projects/{project_id}/jobs/batch-predict"),
    ("POST", "/projects/{project_id}/jobs/explain"),
    ("POST", "/projects/{project_id}/jobs/export"),
    ("POST", "/projects/{project_id}/jobs/module"),
    ("GET", "/projects/{project_id}/models"),
    ("GET", "/system/status"),
}


def notebook_token(client, user, *, ttl=3600) -> dict:
    """Bearer headers of a notebook-scope token that expires in ``ttl`` seconds."""
    conn = connect(client)
    try:
        expires = service.expiry_after(ttl)
        _, token = service.create_token(
            conn, user.id, "nb", scope=TokenScope.NOTEBOOK, expires_at=expires
        )
        return {"Authorization": f"Bearer {token}"}
    finally:
        conn.close()


def test_every_api_route_is_classified_for_notebook_tokens(client):
    routes = {
        (method.upper(), path.removeprefix(API))
        for path, operations in client.app.openapi()["paths"].items()
        for method in operations
    }
    assert ALLOWED.isdisjoint(DENIED) and ALLOWED.isdisjoint(PUBLIC) and DENIED.isdisjoint(PUBLIC)
    assert routes == ALLOWED | DENIED | PUBLIC
    # The source of truth in deps is the same set (it keeps the path converters).
    registered = {(m, re.sub(r":\w+}", "}", p)) for m, p in NOTEBOOK_SCOPE_ROUTES}
    assert registered == ALLOWED
    assert (len(PUBLIC), len(ALLOWED), len(DENIED)) == (4, 36, 15)


def test_public_routes_grant_a_notebook_token_nothing(client):
    user = add_user(client, "alice")
    headers = notebook_token(client, user)
    requests = {
        ("POST", "/auth/login"): {"json": {"username": "alice", "password": "wrong-password"}},
        ("POST", "/auth/first-admin"): {
            "json": {"username": "root", "password": PW, "setup_token": "nope"}
        },
        ("GET", "/auth/status"): {},
        ("GET", "/health"): {},
    }
    assert set(requests) == PUBLIC
    for (method, path), kwargs in requests.items():
        anonymous = client.request(method, API + path, **kwargs)
        with_token = client.request(method, API + path, headers=headers, **kwargs)
        assert with_token.status_code == anonymous.status_code, path
        assert with_token.json() == anonymous.json(), path
        assert "set-cookie" not in with_token.headers, path
    assert not client.cookies


def counts(client) -> tuple[int, int, int]:
    conn = connect(client)
    try:
        return tuple(
            conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("api_tokens", "users", "modules")
        )
    finally:
        conn.close()


@pytest.mark.parametrize(("method", "route"), sorted(DENIED))
def test_notebook_token_is_refused_on_denied_routes(client, method, route):
    admin = add_user(client, "root", Role.ADMIN)
    headers = notebook_token(client, admin)
    path = API + route.format(
        token_id=1, user_id=2, module_id="sort", project_id="p", username="alice"
    )
    before = counts(client)
    r = client.request(method, path, headers=headers, json={})
    assert r.status_code == 403 and r.json()["code"] == "token_scope", r.text
    assert counts(client) == before


def test_notebook_token_works_on_allowed_routes(client):
    user = add_user(client, "alice")
    headers = notebook_token(client, user)
    assert client.get(f"{API}/projects", headers=headers).status_code == 200
    created = client.post(f"{API}/projects", json={"name": "nb"}, headers=headers)
    assert created.status_code == 201
    pid = created.json()["id"]
    files = {"file": ("iris.csv", iris_csv(), "text/csv")}
    up = client.post(
        f"{API}/projects/{pid}/datasets", data={"name": "iris", "type": "train"},
        files=files, headers=headers,
    )  # fmt: skip
    assert up.status_code == 201, up.text
    config = {"target": "species", "max_runtime_secs": 10, "max_models": 1, "nfolds": 2}
    job = client.post(
        f"{API}/projects/{pid}/jobs/automl",
        json={"dataset_id": up.json()["id"], "config": config, "name": "m"},
        headers=headers,
    )
    assert job.status_code == 201, job.text
    assert client.get(f"{API}/system/status", headers=headers).status_code == 200


def test_admin_notebook_token_has_editor_power(client):
    admin = add_user(client, "root", Role.ADMIN)
    alice = add_user(client, "alice")
    full = bearer(client, admin.id)
    alices = bearer(client, alice.id)
    mine = client.post(f"{API}/projects", json={"name": "mine"}, headers=full).json()["id"]
    theirs = client.post(f"{API}/projects", json={"name": "theirs"}, headers=alices).json()["id"]
    shared = client.post(f"{API}/projects", json={"name": "shared"}, headers=alices).json()["id"]
    r = client.post(
        f"{API}/projects/{shared}/share", json={"username": "root", "access": "editor"},
        headers=alices,
    )  # fmt: skip
    assert r.status_code in (200, 201, 204), r.text
    everything = {p["id"] for p in client.get(f"{API}/projects", headers=full).json()}
    assert everything == {mine, theirs, shared}
    conn = connect(client)
    try:
        failed = store.enqueue(conn, "automl", mine, admin.id, {})
        store.claim_job(conn, failed.id, "t")
        store.finish_job(conn, failed.id, JobStatus.FAILED, message="boom\nTraceback: /srv/x.py")
        orphan = store.enqueue(conn, "automl", None, admin.id, {}).id
    finally:
        conn.close()
    assert client.get(f"{API}/jobs/{failed.id}", headers=full).json()["message"].count("\n") == 1
    assert client.get(f"{API}/jobs/{orphan}", headers=full).status_code == 200
    headers = notebook_token(client, admin)
    listed = client.get(f"{API}/projects", headers=headers)
    assert {p["id"] for p in listed.json()} == {mine, shared}
    assert client.get(f"{API}/projects/{theirs}", headers=headers).status_code == 404
    # job_out and the project-less jobs see an editor, not an admin
    job = client.get(f"{API}/jobs/{failed.id}", headers=headers).json()
    assert job["message"] == "boom"
    assert client.get(f"{API}/jobs/{orphan}", headers=headers).status_code == 404
    assert orphan not in {j["id"] for j in client.get(f"{API}/jobs", headers=headers).json()}
    imported = client.post(
        f"{API}/projects/{mine}/models/import",
        files={"file": ("m.zip", b"x", "application/zip")},
        headers=headers,
    )
    assert imported.status_code == 403 and imported.json()["code"] == "token_scope"


def expire_at(client, user, expires_at: str) -> dict:
    conn = connect(client)
    try:
        record, token = service.create_token(conn, user.id, "x")
        conn.execute("UPDATE api_tokens SET expires_at = ? WHERE id = ?", (expires_at, record.id))
        return {"Authorization": f"Bearer {token}"}
    finally:
        conn.close()


def test_expired_token_is_401(client):
    user = add_user(client, "alice")
    past = expire_at(client, user, service.expiry_after(-1))
    r = client.get(f"{API}/projects", headers=past)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    ahead = expire_at(client, user, service.expiry_after(60))
    assert client.get(f"{API}/projects", headers=ahead).status_code == 200
    assert client.get(f"{API}/projects", headers=past).status_code == 401  # still expired


def test_bearer_created_token_inherits_scope_and_expiry(client):
    alice = add_user(client, "alice")
    conn = connect(client)
    try:
        expires = service.expiry_after(3600)
        _, token = service.create_token(conn, alice.id, "full", expires_at=expires)
        _, forever = service.create_token(conn, alice.id, "forever")
    finally:
        conn.close()
    r = client.post(
        f"{API}/tokens", json={"name": "child"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 201
    assert r.json()["scope"] == "full" and r.json()["expires_at"] == expires
    r = client.post(
        f"{API}/tokens", json={"name": "child"}, headers={"Authorization": f"Bearer {forever}"}
    )
    assert r.status_code == 201
    assert r.json()["scope"] == "full" and r.json()["expires_at"] is None


def test_cookie_session_is_unaffected(client):
    add_user(client, "alice")
    csrf = login(client, "alice")
    r = client.post(f"{API}/tokens", json={"name": "ci"}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 201
    assert r.json()["scope"] == "full" and r.json()["expires_at"] is None


def test_token_list_shows_scope_and_expiry(client):
    alice = add_user(client, "alice")
    notebook_token(client, alice)
    full = bearer(client, alice.id)
    listed = client.get(f"{API}/tokens", headers=full).json()
    by_name = {t["name"]: t for t in listed}
    assert by_name["nb"]["scope"] == "notebook" and by_name["nb"]["expires_at"]
    assert by_name["test"]["scope"] == "full" and by_name["test"]["expires_at"] is None


@pytest.mark.parametrize(("method", "route"), sorted(ALLOWED))
def test_notebook_token_passes_the_scope_check_on_every_allowed_route(client, method, route):
    """The keys of NOTEBOOK_SCOPE_ROUTES are the routes as registered (converters included),
    which OpenAPI spells differently: a key that never matches only shows up as a 403 here."""
    user = add_user(client, "alice")
    headers = notebook_token(client, user)
    path = API + route.format(
        project_id="p", dataset_id=1, column="a", job_id=1, model_id=1, module_id="sort"
    )
    r = client.request(method, path, headers=headers, json={})
    assert not (r.status_code == 403 and r.json().get("code") == "token_scope"), (method, route)
