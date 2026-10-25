"""The administration screens: users (create, role, new password, delete, with the
last-admin and own-account guards) and the system status (no secrets, polling)."""

import base64
import re
import time
from contextlib import closing
from html import escape

import pytest
from fastapi.testclient import TestClient

from api_helpers import PW, add_user, connect, login
from fione import i18n
from fione.auth import service as auth_service
from fione.auth.roles import Role
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.projects import service as projects
from fione.web import admin_ui

NEW_PW = "a-new-password-1"
EVIL = {"Origin": "https://evil.example"}
XSS = "<img src=x onerror=alert(1)>"


@pytest.fixture
def client(make_client):
    client = make_client()
    add_user(client, "admin", Role.ADMIN)
    add_user(client, "ed", Role.EDITOR)
    add_user(client, "gv", Role.VIEWER)
    return client


def user_id(client, username) -> int | None:
    with closing(connect(client)) as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    return row[0] if row else None


def role_of(client, username) -> str:
    with closing(connect(client)) as conn:
        return conn.execute("SELECT role FROM users WHERE username = ?", (username,)).fetchone()[0]


def second(client, username, password=PW) -> TestClient:
    """Another browser, signed in as ``username``."""
    other = TestClient(client.app)
    login(other, username, password)
    return other


def test_the_users_page_lists_everyone_but_offers_no_change_of_oneself(client):
    login(client, "admin")
    page = client.get("/admin/users").text
    for name in ("admin", "ed", "gv"):
        assert f">{name}" in page
    assert "Administrator" in page and "Viewer" in page and " UTC" in page
    me = user_id(client, "admin")
    assert f"/admin/users/{me}/" not in page and 'href="/account"' in page
    assert f"/admin/users/{user_id(client, 'ed')}/delete" in page
    assert "does not record sign-ins" in page


def test_creating_a_user(client):
    csrf = login(client, "admin")
    form = {"csrf_token": csrf, "username": "carol", "password": PW, "role": "viewer"}
    r = client.post("/admin/users", data=form, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/admin/users?done=created")
    assert role_of(client, "carol") == "viewer"
    page = client.get(r.headers["location"]).text
    assert "The user was created." in page and PW not in page
    login(TestClient(client.app), "carol")


@pytest.mark.parametrize(
    ("form", "message"),
    [
        ({"username": "bad name"}, "Use only letters, digits"),
        ({"username": "ed"}, "already taken"),
        ({"username": ""}, "1 to 64 characters"),
        ({"username": "x" * 65}, "1 to 64 characters"),
        ({"password": "short"}, "at least 8 characters"),
        ({"role": "owner"}, "Choose a role."),
    ],
)
def test_creating_a_user_is_checked_like_the_api(client, form, message):
    csrf = login(client, "admin")
    data = {"csrf_token": csrf, "username": "dave", "password": PW, "role": "editor"} | form
    r = client.post("/admin/users", data=data)
    assert r.status_code == 422 and message in r.text
    assert PW not in r.text and 'value="short"' not in r.text  # passwords are never echoed
    assert user_id(client, "dave") is None


def test_a_role_change_applies_to_the_users_next_request(client):
    csrf = login(client, "admin")
    ed = second(client, "ed")
    assert ed.get("/admin/users", follow_redirects=False).status_code == 403
    uid = user_id(client, "ed")
    r = client.post(
        f"/admin/users/{uid}/role",
        data={"csrf_token": csrf, "role": "admin"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "done=role" in r.headers["location"]
    assert ed.get("/admin/users").status_code == 200
    client.post(f"/admin/users/{uid}/role", data={"csrf_token": csrf, "role": "viewer"})
    assert ed.get("/admin/users").status_code == 403
    assert ed.get("/").text.count("Viewer") >= 1


def test_a_new_password_ends_the_users_sessions(client):
    csrf = login(client, "admin")
    ed = second(client, "ed")
    uid = user_id(client, "ed")
    r = client.post(
        f"/admin/users/{uid}/password",
        data={"csrf_token": csrf, "password": NEW_PW, "page": "1"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == "/admin/users?done=password&page=1"
    page = client.get(r.headers["location"]).text
    assert NEW_PW not in page
    assert ed.get("/account", follow_redirects=False).status_code == 303  # to the login page
    login(ed, "ed", NEW_PW)
    r = client.post(f"/admin/users/{uid}/password", data={"csrf_token": csrf, "password": "short"})
    assert r.status_code == 422 and "at least 8 characters" in r.text and "short" not in r.text


def test_ones_own_password_is_changed_on_the_account_page(client):
    """Not through the admin route, which asks for no current password."""
    csrf = login(client, "admin")
    me = user_id(client, "admin")
    r = client.post(f"/admin/users/{me}/password", data={"csrf_token": csrf, "password": NEW_PW})
    assert r.status_code == 409 and "on your account page" in r.text
    assert 'href="/account"' in r.text and NEW_PW not in r.text
    assert client.get("/admin/users").status_code == 200  # the session goes on
    login(TestClient(client.app), "admin")  # the password is unchanged


def test_users_rows_stack_on_phones(client):
    login(client, "admin")
    page = client.get("/admin/users").text
    assert '<table class="table table-wide table-stack">' in page
    for label in ("Role", "Created", "Actions"):
        assert page.count(f'data-label="{label}"') == 3


def test_deleting_a_user_ends_their_sessions(client):
    csrf = login(client, "admin")
    gv = second(client, "gv")
    r = client.post(
        f"/admin/users/{user_id(client, 'gv')}/delete",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code == 303 and user_id(client, "gv") is None
    assert gv.get("/", follow_redirects=False).status_code == 303


def test_owners_of_projects_cannot_be_deleted(client):
    csrf = login(client, "admin")
    with closing(connect(client)) as conn:
        ed = auth_service.get_user(conn, user_id(client, "ed"))
        projects.create_project(conn, ed, "Mine")
    r = client.post(f"/admin/users/{ed.id}/delete", data={"csrf_token": csrf})
    assert r.status_code == 409
    assert "Nothing was changed for ed." in r.text and "own 1 project(s)" in r.text
    assert user_id(client, "ed") == ed.id


def test_the_last_admin_and_ones_own_account_are_kept(client):
    csrf = login(client, "admin")
    me = user_id(client, "admin")
    for path, form in (("role", {"role": "editor"}), ("delete", {})):
        r = client.post(f"/admin/users/{me}/{path}", data={"csrf_token": csrf} | form)
        assert r.status_code == 409 and "needs at least one administrator" in r.text
    assert role_of(client, "admin") == "admin"
    # With a second administrator, the first still cannot demote or delete themselves...
    client.post(
        f"/admin/users/{user_id(client, 'ed')}/role", data={"csrf_token": csrf, "role": "admin"}
    )
    r = client.post(f"/admin/users/{me}/role", data={"csrf_token": csrf, "role": "viewer"})
    assert r.status_code == 409 and "cannot give up your own administrator role" in r.text
    r = client.post(f"/admin/users/{me}/delete", data={"csrf_token": csrf})
    assert r.status_code == 409 and "cannot delete your own account" in r.text
    assert role_of(client, "admin") == "admin"
    # ...but the other one can.
    ed = TestClient(client.app)
    ed_csrf = login(ed, "ed")
    r = ed.post(f"/admin/users/{me}/role", data={"csrf_token": ed_csrf, "role": "editor"})
    assert r.status_code == 200 and role_of(client, "admin") == "editor"


def test_the_refusal_is_said_in_japanese(client):
    csrf = login(client, "admin")
    client.cookies.set("fione_lang", "ja")
    r = client.post(f"/admin/users/{user_id(client, 'admin')}/delete", data={"csrf_token": csrf})
    assert r.status_code == 409 and "管理者が一人は必要です。" in r.text


@pytest.mark.parametrize("uid", ["999999", "abc", "0", str(2**63)])
@pytest.mark.parametrize("path", ["role", "password", "delete"])
def test_unknown_users_are_not_found(client, uid, path):
    csrf = login(client, "admin")
    form = {"csrf_token": csrf, "role": "viewer", "password": NEW_PW}
    r = client.post(f"/admin/users/{uid}/{path}", data=form)
    assert r.status_code == 404 and "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("path", ["", "/{uid}/role", "/{uid}/password", "/{uid}/delete"])
@pytest.mark.parametrize("refusal", ["no_csrf", "cross_site"])
def test_user_posts_need_the_token_and_this_site(client, path, refusal):
    csrf = login(client, "admin")
    uid = user_id(client, "ed")
    data = {"csrf_token": "" if refusal == "no_csrf" else csrf}
    data |= {"username": "newbie", "password": NEW_PW, "role": "viewer"}
    headers = EVIL if refusal == "cross_site" else {}
    r = client.post("/admin/users" + path.replace("{uid}", str(uid)), data=data, headers=headers)
    assert r.status_code == 403 and "text/html" in r.headers["content-type"]
    assert user_id(client, "newbie") is None and role_of(client, "ed") == "editor"
    login(TestClient(client.app), "ed")  # the password is unchanged


@pytest.mark.parametrize("who", ["ed", "gv"])
def test_others_get_the_403_page_with_a_hint(client, who):
    login(client, who)
    for path in ("/admin/users", "/admin/system"):
        r = client.get(path, headers={"Accept": "text/html"})
        assert r.status_code == 403 and "Only administrators can do this." in r.text
        assert "Ask an administrator" in r.text


def test_usernames_are_escaped(client):
    with closing(connect(client)) as conn:  # the service refuses such names; old data may not
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, 'x', 'editor')", (XSS,)
        )
    login(client, "admin")
    page = client.get("/admin/users").text
    assert XSS not in page and escape(XSS) in page


def test_the_view_preference_changes_no_permission(client):
    for mode in ("simple", "detailed"):
        login(client, "ed")
        client.cookies.set("fione_mode", mode)
        assert client.get("/admin/users", follow_redirects=False).status_code == 403
        login(client, "admin")
        client.cookies.set("fione_mode", mode)
        page = client.get("/").text
        assert 'href="/admin/users"' in page and 'href="/admin/system"' in page


# --- system status ------------------------------------------------------------------------


def test_the_system_page_says_how_the_server_is(client):
    with closing(connect(client)) as conn:
        admin = auth_service.get_user(conn, user_id(client, "admin"))
        old = store.enqueue(conn, "automl", None, admin.id, {})
        store.claim_job(conn, old.id, "token")
        store.finish_job(conn, old.id, JobStatus.FAILED, message="old")
        conn.execute(
            "UPDATE jobs SET finished_at = ? WHERE id = ?", (time.time() - 2 * 86400, old.id)
        )
        recent = store.enqueue(conn, "automl", None, admin.id, {})
        store.claim_job(conn, recent.id, "token")
        store.finish_job(conn, recent.id, JobStatus.FAILED, message="recent")
        store.enqueue(conn, "automl", None, admin.id, {})
    login(client, "admin")
    page = client.get("/admin/system").text
    stat = lambda label: re.search(rf"<dt>{label}</dt><dd>(.*?)</dd>", page).group(1)  # noqa: E731
    assert stat("Queued jobs") == "1" and stat("Running jobs") == "0"
    assert stat("Failed in the last 24 hours") == "1"
    assert stat("Worker processes") == "0"
    assert "Stopped" in stat("Job runner")
    assert re.fullmatch(r"\d+ min", stat("Up for"))
    assert "2.0.0" in stat("Version") and stat("Storage") == "Local disk"
    assert "Not configured" in page and "Ollama" in page
    assert 'hx-trigger="every 10s"' in page and 'aria-live="polite"' in page
    assert "/static/js/system.js" in page


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (59, "0 min"),
        (3 * 60, "3 min"),
        (2 * 3600 + 5 * 60, "2 h 5 min"),
        (3 * 86400 + 7200, "3 d 2 h"),
    ],
)
def test_the_uptime_is_said_in_its_two_largest_units(seconds, text):
    key, values = admin_ui._uptime(seconds)
    assert i18n.t(key, "en", **values) == text


def test_the_system_page_in_japanese(client):
    login(client, "admin")
    client.cookies.set("fione_lang", "ja")
    page = client.get("/admin/system").text
    assert "システムの状態" in page and "未設定" in page and "ローカルディスク" in page


def test_the_system_page_shows_no_secret_path_or_url(client):
    app = client.app
    settings = app.state.settings
    app.state.settings = settings.model_copy(
        update={
            "storage_url": "s3://AKIAEXAMPLEKEY:VerySecretValue@minio.internal:9000/bucket",
            "image_tag": "fione:1.2.3",
        }
    )
    try:
        login(client, "admin")
        page = client.get("/admin/system").text
    finally:
        app.state.settings = settings
    assert "S3-compatible object storage" in page and "fione:1.2.3" in page
    secret = app.state.secret
    for leak in (
        "AKIAEXAMPLEKEY",
        "VerySecretValue",
        "minio.internal",
        "bucket",
        str(settings.data_dir),
        secret.hex(),
        base64.b64encode(secret).decode(),
        base64.urlsafe_b64encode(secret).decode().rstrip("="),
    ):
        assert leak not in page, leak


def test_the_running_runner_and_its_workers(make_client):
    client = make_client(start_runner=True)
    add_user(client, "admin", Role.ADMIN)
    login(client, "admin")
    page = client.get("/admin/system").text
    assert re.search(r"<dt>Job runner</dt><dd><span class=\"badge badge-success\">Running", page)


def test_polling_returns_the_card_and_stops_when_it_cannot_be_shown(client, monkeypatch):
    poll = {"HX-Request": "true"}
    login(client, "admin")
    r = client.get("/admin/system", headers=poll)
    assert r.status_code == 200 and r.text.startswith('<section id="system-status"')
    assert 'hx-trigger="every 10s"' in r.text and "<html" not in r.text
    # No longer an administrator: a final card, and the polling stops.
    login(client, "ed")
    r = client.get("/admin/system", headers=poll)
    assert r.status_code == admin_ui.STOP_POLLING == 286
    assert "hx-trigger" not in r.text and "Only administrators can do this." in r.text
    # An error: the same.
    login(client, "admin")

    def broken(*args):
        raise RuntimeError("boom")

    monkeypatch.setattr(admin_ui, "system_status", broken)
    r = client.get("/admin/system", headers=poll)
    assert r.status_code == 286 and "hx-trigger" not in r.text and "boom" not in r.text
    # Signed out: HTMX is sent to the login page.
    client.cookies.clear()
    r = client.get("/admin/system", headers=poll)
    assert r.status_code == 401 and r.headers["hx-redirect"].startswith("/login?next=")
