"""Authentication over HTTP: first admin, login and its throttle, sessions, CSRF, tokens."""

import hashlib
import logging
import threading
import time

import pytest
from fastapi.testclient import TestClient

from api_helpers import PW, add_user, bearer, connect, login, make_settings
from fione.api import security
from fione.api.app import create_app
from fione.auth import passwords
from fione.auth import service as auth
from fione.auth.roles import Role
from fione.config import Settings

ME = "/api/v1/auth/me"
LOGIN = "/api/v1/auth/login"
FIRST = "/api/v1/auth/first-admin"


def setup_token(client) -> str:
    return (client.app.state.settings.data_dir / security.SETUP_TOKEN_FILE).read_text()


def admins(client) -> list[str]:
    conn = connect(client)
    try:
        return [u.username for u in auth.list_users(conn) if u.role == Role.ADMIN]
    finally:
        conn.close()


# --- first admin ---------------------------------------------------------------


def test_startup_logs_the_generated_setup_token_once(make_client, caplog):
    with caplog.at_level(logging.WARNING, logger="fione.setup"):
        client = make_client()
    token = setup_token(client)
    records = [r for r in caplog.records if r.name == "fione.setup"]
    assert len(records) == 1
    assert records[0].getMessage() == f"No administrator exists. Setup token: {token}"
    assert client.get("/api/v1/auth/status").json() == {"needs_first_admin": True}


def test_first_admin_needs_the_setup_token(client):
    body = {"username": "root", "password": PW}
    assert client.post(FIRST, json=body).status_code == 422
    r = client.post(FIRST, json={**body, "setup_token": "wrong"})
    assert r.status_code == 403
    assert r.json() == {"error": "invalid setup token", "code": "invalid_setup_token"}
    assert admins(client) == []
    r = client.post(FIRST, json={**body, "setup_token": setup_token(client)})
    assert r.status_code == 200
    assert r.json()["user"] == {"id": 1, "username": "root", "role": "admin"}
    assert r.json()["csrf_token"]
    assert "fione_session=" in r.headers["set-cookie"]
    assert not (client.app.state.settings.data_dir / security.SETUP_TOKEN_FILE).exists()
    assert client.get(ME).json()["user"]["username"] == "root"
    assert client.get("/api/v1/auth/status").json() == {"needs_first_admin": False}


def test_first_admin_is_409_once_an_admin_exists(client):
    token = setup_token(client)
    body = {"username": "root", "password": PW, "setup_token": token}
    assert client.post(FIRST, json=body).status_code == 200
    r = client.post(FIRST, json={**body, "username": "root2"})
    assert r.status_code == 409 and r.json()["code"] == "already_set_up"
    assert admins(client) == ["root"]


def test_setup_token_from_env_is_used_and_never_logged(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("FIONE_SETUP_TOKEN", "operator-chosen-token")
    settings = Settings(data_dir=tmp_path / "data", runner_enabled=False)
    with caplog.at_level(logging.WARNING, logger="fione.setup"):
        with TestClient(create_app(settings)) as client:
            body = {"username": "root", "password": PW}
            wrong = client.post(FIRST, json={**body, "setup_token": "nope"})
            assert wrong.status_code == 403
            r = client.post(FIRST, json={**body, "setup_token": "operator-chosen-token"})
            assert r.status_code == 200
    assert not (tmp_path / "data" / security.SETUP_TOKEN_FILE).exists()
    assert "operator-chosen-token" not in caplog.text
    assert "FIONE_SETUP_TOKEN" in caplog.text


def test_concurrent_first_admin_requests_create_exactly_one(client):
    token = setup_token(client)
    barrier = threading.Barrier(2)
    statuses = []

    def attempt(name):
        barrier.wait()
        r = client.post(FIRST, json={"username": name, "password": PW, "setup_token": token})
        statuses.append(r.status_code)

    threads = [threading.Thread(target=attempt, args=(n,)) for n in ("root1", "root2")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(statuses) == [200, 409]
    assert len(admins(client)) == 1


def test_wrong_setup_tokens_are_throttled(make_client):
    client = make_client(login_max_failures=2)
    token = setup_token(client)
    for name in ("a", "b"):  # varying the username does not escape the throttle
        body = {"username": name, "password": PW, "setup_token": "wrong"}
        assert client.post(FIRST, json=body).status_code == 403
    r = client.post(FIRST, json={"username": "root", "password": PW, "setup_token": token})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0
    assert admins(client) == []


# --- login ------------------------------------------------------------------------


def test_unknown_user_and_wrong_password_look_the_same(client):
    add_user(client, "alice")
    unknown = client.post(LOGIN, json={"username": "nobody", "password": PW})
    wrong = client.post(LOGIN, json={"username": "alice", "password": "wrong-password"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.content == wrong.content
    assert unknown.json() == {
        "error": "invalid username or password",
        "code": "invalid_credentials",
    }
    assert "set-cookie" not in unknown.headers and "set-cookie" not in wrong.headers


def test_five_failures_lock_the_key_and_success_resets(client):
    add_user(client, "alice")
    bad = {"username": "alice", "password": "wrong-password"}
    for _ in range(4):
        assert client.post(LOGIN, json=bad).status_code == 401
    login(client, "alice")  # a success clears the count
    for _ in range(5):
        assert client.post(LOGIN, json=bad).status_code == 401
    r = client.post(LOGIN, json={"username": "ALICE", "password": PW})  # lowercased key
    assert r.status_code == 429
    assert r.json()["code"] == "throttled"
    assert 0 < int(r.headers["retry-after"]) <= 15 * 60
    r = client.post(LOGIN, json={"username": "alice", "password": PW})  # even the right one
    assert r.status_code == 429
    unknown = {"username": "ghost", "password": "wrong-password"}
    for _ in range(5):
        assert client.post(LOGIN, json=unknown).status_code == 401
    assert client.post(LOGIN, json=unknown).status_code == 429  # existence is not revealed


def test_throttle_is_keyed_by_client_address(make_client):
    client = make_client(trust_proxy=True)
    add_user(client, "alice")
    bad = {"username": "alice", "password": "wrong-password"}
    one = {"X-Forwarded-For": "203.0.113.9, 10.0.0.1"}
    two = {"X-Forwarded-For": "10.0.0.2"}
    for _ in range(5):
        client.post(LOGIN, json=bad, headers=one)
    assert client.post(LOGIN, json={**bad, "password": PW}, headers=one).status_code == 429
    assert client.post(LOGIN, json={**bad, "password": PW}, headers=two).status_code == 200


def test_forwarded_for_is_ignored_unless_trusted(client):
    add_user(client, "alice")
    bad = {"username": "alice", "password": "wrong-password"}
    for n in range(5):
        client.post(LOGIN, json=bad, headers={"X-Forwarded-For": f"10.0.0.{n}"})
    r = client.post(LOGIN, json={**bad, "password": PW}, headers={"X-Forwarded-For": "10.9.9.9"})
    assert r.status_code == 429


def test_at_most_four_password_verifications_run_at_once(client, monkeypatch):
    for n in range(1, 12, 2):
        add_user(client, f"alice{n}")
    active = peak = 0
    lock = threading.Lock()
    real = passwords.verify_password

    def tracked(password, hashed):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            time.sleep(0.05)
            return real(password, hashed)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(auth, "verify_password", tracked)
    statuses = []

    def attempt(n):
        user = f"alice{n}" if n % 2 else f"user{n}"  # one attempt per key: none is throttled
        r = client.post(LOGIN, json={"username": user, "password": PW})
        statuses.append(r.status_code)

    threads = [threading.Thread(target=attempt, args=(n,)) for n in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(statuses) == [200] * 6 + [401] * 6  # waiting requests queue, never fail
    assert 2 <= peak <= security.PASSWORD_SLOTS == 4


@pytest.mark.parametrize(
    "kwargs",
    [
        {"data": {"username": "alice", "password": PW}},
        {"content": b'{"username": "alice"}', "headers": {"Content-Type": "text/plain"}},
        {"content": b'{"username": "alice", "password": "x"}'},
    ],
    ids=["form", "text-plain", "no-content-type"],
)
def test_login_accepts_only_json(client, kwargs):
    add_user(client, "alice")
    r = client.post(LOGIN, **kwargs)
    assert r.status_code == 415 and r.json()["code"] == "unsupported_media_type"


@pytest.mark.parametrize(
    ("origin", "status"),
    [("http://evil.example", 403), ("null", 403), ("http://testserver", 200)],
)
def test_login_refuses_foreign_origins(client, origin, status):
    add_user(client, "alice")
    r = client.post(LOGIN, json={"username": "alice", "password": PW}, headers={"Origin": origin})
    assert r.status_code == status
    if status == 403:
        assert r.json()["code"] == "cross_origin"


# --- session cookie -----------------------------------------------------------------


def test_session_cookie_flags(client):
    user = add_user(client, "alice")
    r = client.post(LOGIN, json={"username": "alice", "password": PW})
    cookie = r.headers["set-cookie"]
    attributes = [a.strip().lower() for a in cookie.split(";")]
    assert "httponly" in attributes
    assert "samesite=lax" in attributes
    assert "path=/" in attributes
    assert f"max-age={7 * 24 * 3600}" in attributes
    assert "secure" not in attributes
    value = cookie.split(";")[0].split("=", 1)[1]
    assert "editor" not in value and "role" not in value
    assert client.app.state.signer.unverified_user_id(value) == user.id


def test_secure_cookie_when_configured(make_client):
    client = make_client(cookie_secure=True, session_max_age_secs=3600)
    add_user(client, "alice")
    r = client.post(LOGIN, json={"username": "alice", "password": PW})
    attributes = [a.strip().lower() for a in r.headers["set-cookie"].split(";")]
    assert "secure" in attributes and "max-age=3600" in attributes


def test_tampered_cookie_is_401(client):
    add_user(client, "alice")
    login(client, "alice")
    value = client.cookies["fione_session"]
    version, payload, signature = value.split(".")
    forged = security._b64e(security._b64d(payload).replace(b'"u":1', b'"u":2'))
    for bad in (f"{version}.{forged}.{signature}", value[:-3] + "AAA", "garbage"):
        client.cookies.set("fione_session", bad)
        r = client.get(ME)
        assert r.status_code == 401 and r.json()["code"] == "unauthorized"


def test_a_cookie_from_another_install_is_401(make_client, tmp_path):
    a = make_client(tmp_path / "a")
    b = make_client(tmp_path / "b")
    add_user(a, "alice")
    add_user(b, "alice")
    login(a, "alice")
    b.cookies.set("fione_session", a.cookies["fione_session"])
    assert b.get(ME).status_code == 401


def test_deleted_user_session_is_401_at_once(client):
    alice = add_user(client, "alice")
    login(client, "alice")
    assert client.get(ME).status_code == 200
    conn = connect(client)
    auth.delete_user(conn, alice.id)
    conn.close()
    assert client.get(ME).status_code == 401


def test_role_change_applies_on_the_next_request(client):
    alice = add_user(client, "alice", Role.VIEWER)
    csrf = login(client, "alice")
    headers = {"X-CSRF-Token": csrf}
    assert client.post("/api/v1/projects", json={"name": "p"}, headers=headers).status_code == 403
    conn = connect(client)
    auth.set_role(conn, alice.id, Role.EDITOR)
    conn.close()
    assert client.get(ME).json()["user"]["role"] == "editor"
    assert client.post("/api/v1/projects", json={"name": "p"}, headers=headers).status_code == 201


def test_a_reused_user_id_does_not_inherit_the_session(client):
    add_user(client, "root", Role.ADMIN)
    alice = add_user(client, "alice")
    login(client, "alice")
    conn = connect(client)
    auth.delete_user(conn, alice.id)
    bob = auth.create_user(conn, "bob", PW, Role.ADMIN)
    conn.close()
    assert bob.id == alice.id  # SQLite reuses the highest rowid
    assert client.get(ME).status_code == 401


def test_password_change_renews_this_session_and_ends_the_others(make_client, tmp_path):
    first = make_client()
    add_user(first, "alice")
    other = TestClient(first.app)
    login(other, "alice")
    csrf = login(first, "alice")
    r = first.post(
        "/api/v1/auth/password",
        json={"current_password": PW, "new_password": "brand-new-password"},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200
    assert r.json()["csrf_token"] != csrf
    assert first.get(ME).status_code == 200
    assert other.get(ME).status_code == 401
    assert first.post(LOGIN, json={"username": "alice", "password": PW}).status_code == 401
    login(first, "alice", "brand-new-password")


def test_password_change_is_throttled(client):
    alice = add_user(client, "alice")
    headers = bearer(client, alice.id)
    body = {"current_password": "wrong-password", "new_password": "brand-new-password"}
    for _ in range(5):
        assert client.post("/api/v1/auth/password", json=body, headers=headers).status_code == 403
    body["current_password"] = PW
    r = client.post("/api/v1/auth/password", json=body, headers=headers)
    assert r.status_code == 429


# --- CSRF -------------------------------------------------------------------------------


def test_cookie_unsafe_requests_need_the_csrf_header(client):
    add_user(client, "alice")
    csrf = login(client, "alice")
    url = "/api/v1/projects"
    r = client.post(url, json={"name": "p"})
    assert r.status_code == 403
    assert r.json() == {"error": "missing or wrong X-CSRF-Token header", "code": "csrf"}
    assert client.post(url, json={"name": "p"}, headers={"X-CSRF-Token": "x"}).status_code == 403
    r = client.post(url, json={"name": "p"}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 201
    project = r.json()["id"]
    assert client.get(url).status_code == 200  # safe methods never need it
    assert client.delete(f"{url}/{project}").status_code == 403
    assert client.delete(f"{url}/{project}", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get(ME).json()["csrf_token"] == csrf


def test_logout_needs_csrf_and_clears_the_cookie(client):
    add_user(client, "alice")
    csrf = login(client, "alice")
    assert client.post("/api/v1/auth/logout").status_code == 403
    r = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 204
    assert 'fione_session=""' in r.headers["set-cookie"] or "Max-Age=0" in r.headers["set-cookie"]
    assert client.get(ME).status_code == 401


def test_bearer_requests_are_csrf_exempt_and_never_fall_back_to_the_cookie(client):
    alice = add_user(client, "alice")
    login(client, "alice")
    headers = bearer(client, alice.id)
    r = client.post("/api/v1/projects", json={"name": "p"}, headers=headers)
    assert r.status_code == 201
    assert client.get(ME, headers=headers).json()["csrf_token"] is None
    for value in ("Bearer fione_unknown", "bearer fione_unknown", "Bearer "):
        r = client.get(ME, headers={"Authorization": value})  # the valid cookie is ignored
        assert r.status_code == 401
        assert r.headers["www-authenticate"] == "Bearer"


# --- API tokens -----------------------------------------------------------------------------


def test_token_lifecycle(client):
    add_user(client, "alice")
    csrf = login(client, "alice")
    r = client.post("/api/v1/tokens", json={"name": " ci "}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 201
    created = r.json()
    token = created.pop("token")
    assert token.startswith("fione_")
    assert created["name"] == "ci" and created["revoked"] is False
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get(ME, headers=headers).json()["user"]["username"] == "alice"
    listing = client.get("/api/v1/tokens", headers=headers)
    assert listing.json() == [created]
    assert token not in listing.text
    assert hashlib.sha256(token.encode()).hexdigest() not in listing.text
    assert client.delete(f"/api/v1/tokens/{created['id']}", headers=headers).status_code == 204
    r = client.get(ME, headers=headers)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


def test_tokens_of_others_are_404_but_admins_manage_any(client):
    root = add_user(client, "root", Role.ADMIN)
    alice = add_user(client, "alice")
    bob = add_user(client, "bob")
    conn = connect(client)
    record, _ = auth.create_token(conn, alice.id, "alice-token")
    conn.close()
    bob_headers = bearer(client, bob.id)
    assert client.delete(f"/api/v1/tokens/{record.id}", headers=bob_headers).status_code == 404
    assert client.delete("/api/v1/tokens/999999", headers=bob_headers).status_code == 404
    root_headers = bearer(client, root.id)
    listing = client.get(f"/api/v1/tokens?user_id={alice.id}", headers=root_headers).json()
    assert [t["name"] for t in listing] == ["alice-token"]
    assert client.delete(f"/api/v1/tokens/{record.id}", headers=root_headers).status_code == 204
    assert client.get(f"/api/v1/tokens?user_id={alice.id}", headers=root_headers).json()[0][
        "revoked"
    ]


def test_settings_used_by_the_app_are_the_ones_given(tmp_path):
    settings = make_settings(tmp_path / "data")
    app = create_app(settings, start_runner=False)
    assert app.state.settings is settings
    assert app.state.db_path == tmp_path / "data" / "fione.db"
    assert app.state.runner is None


# --- fix round 1: atomic throttle, namespaces, cookie ids, auth schemes ----------------------


def _concurrently(n, fn):
    barrier = threading.Barrier(n)
    statuses = []
    lock = threading.Lock()

    def go():
        barrier.wait()
        status = fn()
        with lock:
            statuses.append(status)

    threads = [threading.Thread(target=go) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return statuses


def test_concurrent_wrong_logins_cannot_bypass_the_throttle(client):
    add_user(client, "alice")
    bad = {"username": "alice", "password": "wrong-password"}
    statuses = _concurrently(12, lambda: client.post(LOGIN, json=bad).status_code)
    assert sorted(statuses) == [401] * 5 + [429] * 7


def test_concurrent_wrong_password_changes_cannot_bypass_the_throttle(client):
    alice = add_user(client, "alice")
    headers = bearer(client, alice.id)
    body = {"current_password": "wrong-password", "new_password": "brand-new-password"}
    statuses = _concurrently(
        12, lambda: client.post("/api/v1/auth/password", json=body, headers=headers).status_code
    )
    assert sorted(statuses) == [403] * 5 + [429] * 7


def test_one_address_cannot_spray_many_usernames(make_client):
    client = make_client(login_max_failures_per_ip=3)
    for name in ("a1", "a2", "a3"):
        r = client.post(LOGIN, json={"username": name, "password": "wrong-password"})
        assert r.status_code == 401
    r = client.post(LOGIN, json={"username": "a4", "password": "wrong-password"})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


def test_login_failures_do_not_touch_the_setup_throttle(make_client):
    client = make_client(login_max_failures=2)
    token = setup_token(client)
    for _ in range(3):
        client.post(LOGIN, json={"username": "#first-admin", "password": "wrong-password"})
    r = client.post(FIRST, json={"username": "root", "password": PW, "setup_token": token})
    assert r.status_code == 200


@pytest.mark.parametrize("user_id", [0, -1, 2**63, 2**64])
def test_forged_cookie_ids_out_of_range_are_401(client, user_id):
    payload = security._b64e(b'{"u":%d,"t":%d,"c":"x"}' % (user_id, int(time.time())))
    client.cookies.set("fione_session", f"v1.{payload}.AAAA")
    r = client.get(ME)
    assert r.status_code == 401 and r.json()["code"] == "unauthorized"


def test_non_bearer_authorization_falls_back_to_the_cookie(client):
    add_user(client, "alice")
    csrf = login(client, "alice")
    basic = {"Authorization": "Basic YWxpY2U6cHc="}
    assert client.get(ME, headers=basic).json()["user"]["username"] == "alice"
    r = client.post("/api/v1/projects", json={"name": "p"}, headers=basic)
    assert r.status_code == 403 and r.json()["code"] == "csrf"  # still the cookie path
    r = client.post("/api/v1/projects", json={"name": "p"}, headers={**basic, "X-CSRF-Token": csrf})
    assert r.status_code == 201
    client.cookies.clear()
    r = client.get(ME, headers=basic)
    assert r.status_code == 401 and r.json()["error"] == "authentication required"


# --- fix round 2: the proxy's X-Forwarded-For value ----------------------------------------


@pytest.mark.parametrize(
    "headers",
    [
        [("X-Forwarded-For", "10.0.0.2"), ("X-Forwarded-For", "203.0.113.9")],  # proxy's own line
        [("X-Forwarded-For", "10.0.0.2, 203.0.113.9")],  # proxy appended to the client's line
    ],
    ids=["two-lines", "one-line"],
)
def test_the_address_the_proxy_added_is_used(make_client, headers):
    client = make_client(trust_proxy=True)
    add_user(client, "alice")
    bad = {"username": "alice", "password": "wrong-password"}
    for _ in range(5):
        assert client.post(LOGIN, json=bad, headers=headers).status_code == 401
    # The client spoofed 10.0.0.2; the lockout must land on 203.0.113.9 only.
    spoofed = {"X-Forwarded-For": "10.0.0.2"}
    assert client.post(LOGIN, json={**bad, "password": PW}, headers=spoofed).status_code == 200
    real = {"X-Forwarded-For": "203.0.113.9"}
    assert client.post(LOGIN, json={**bad, "password": PW}, headers=real).status_code == 429
