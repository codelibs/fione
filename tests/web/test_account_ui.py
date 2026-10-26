"""The account page: the role in plain words, the password change (the API's throttle and
policy, the session re-issued) and API tokens (the secret shown exactly once)."""

import re
from contextlib import closing
from html import escape
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_helpers import PW, add_user, connect, login
from fione.auth import service as auth_service
from fione.auth.roles import Role
from fione.auth.tokens import TokenScope, hash_token
from fione.web import account_ui
from web_helpers import make_world

XSS = "</script><img src=x onerror=alert(1)>"
NEW_PW = "a-new-password-1"
EVIL = {"Origin": "https://evil.example"}
SECRET = re.compile(r"fione_[A-Za-z0-9_-]{20,}")


@pytest.fixture
def client(make_client):
    client = make_client(login_max_failures=3)
    add_user(client, "ed", Role.EDITOR)
    add_user(client, "gv", Role.VIEWER)
    add_user(client, "admin", Role.ADMIN)
    return client


def tokens_of(client, username):
    with closing(connect(client)) as conn:
        (user_id,) = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        return auth_service.list_tokens(conn, user_id)


def change(client, csrf, current=PW, new=NEW_PW, confirm=None, **kw):
    form = {
        "csrf_token": csrf,
        "current_password": current,
        "new_password": new,
        "confirm_password": new if confirm is None else confirm,
    }
    return client.post("/account/password", data=form, follow_redirects=False, **kw)


def test_the_page_says_who_one_is_and_what_each_role_can_do(client):
    login(client, "gv")
    page = client.get("/account").text
    assert "gv" in page and "Viewer" in page
    for words in ("manages users", "uploads data", "without changing anything"):
        assert words in page
    assert re.search(r"is-current\">\s*<p><strong>Viewer", page)
    client.cookies.set("fione_lang", "ja")
    page = client.get("/account").text
    assert "アカウント" in page and "あなたのロール" in page


def test_the_password_form_posts_and_never_shows_a_password(client):
    csrf = login(client, "ed")
    page = client.get("/account").text
    form = re.search(r'<form[^>]*action="/account/password".*?</form>', page, re.S).group(0)
    assert 'method="post"' in form
    for name, autocomplete in (
        ("username", "username"),
        ("current_password", "current-password"),
        ("new_password", "new-password"),
        ("confirm_password", "new-password"),
    ):
        tag = re.search(rf'<input[^>]*name="{name}"[^>]*>', form).group(0)
        assert f'autocomplete="{autocomplete}"' in tag
        if name != "username":
            assert "value=" not in tag
    r = change(client, csrf, current="wrong-password-1", new="new-secret-777")
    assert r.status_code == 403
    for text in ("wrong-password-1", "new-secret-777"):
        assert text not in r.text
    assert "The current password is not correct." in r.text


def test_changing_the_password_keeps_this_session_and_ends_the_others(client):
    csrf = login(client, "ed")
    old_cookie = client.cookies.get("fione_session")
    r = change(client, csrf)
    assert r.status_code == 303 and r.headers["location"] == "/account?done=password"
    assert "fione_session=" in r.headers["set-cookie"]
    assert client.cookies.get("fione_session") != old_cookie
    page = client.get(r.headers["location"])
    assert page.status_code == 200 and "Your password was changed." in page.text
    # The old cookie ended with the old password.
    client.cookies.set("fione_session", old_cookie)
    assert client.get("/account", follow_redirects=False).status_code == 303
    r = client.post("/api/v1/auth/login", json={"username": "ed", "password": PW})
    assert r.status_code == 401
    login(client, "ed", NEW_PW)


@pytest.mark.parametrize(
    ("form", "message"),
    [
        ({"new": "short"}, "needs at least 8 characters"),
        ({"new": "x" * 1025}, "needs at least 8 characters"),
        ({"confirm": "something-else-1"}, "do not match"),
        ({"current": ""}, "Enter your current password."),
    ],
)
def test_invalid_changes_change_nothing_and_cost_no_attempt(client, form, message):
    csrf = login(client, "ed")
    for _ in range(4):  # more than the throttle allows: none of these is an attempt
        r = change(client, csrf, **form)
        assert r.status_code == 422 and message in r.text
    assert change(client, csrf, current="wrong-password-1").status_code == 403
    login(client, "ed")  # the old password still works


def test_the_ui_and_the_api_share_the_throttle(client):
    csrf = login(client, "ed")
    assert change(client, csrf, current="wrong-password-1").status_code == 403
    r = client.post(
        "/api/v1/auth/password",
        json={"current_password": "wrong-password-2", "new_password": NEW_PW},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 403
    assert change(client, csrf, current="wrong-password-3").status_code == 403
    r = change(client, csrf)  # the right password, but the throttle has had 3 failures
    assert r.status_code == 429 and r.headers["retry-after"].isdigit()
    assert "Too many failed attempts" in r.text
    r = client.post(
        "/api/v1/auth/password",
        json={"current_password": PW, "new_password": NEW_PW},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 429


def test_a_new_token_is_shown_exactly_once(client):
    csrf = login(client, "ed")
    r = client.post(
        "/account/tokens", data={"csrf_token": csrf, "name": "nightly"}, follow_redirects=False
    )
    assert r.status_code == 303 and r.headers["location"] == "/account"
    assert "set-cookie" not in r.headers  # nothing about the token travels in a cookie
    page = client.get("/account")
    assert page.headers["cache-control"] == "no-store"
    secrets = SECRET.findall(page.text)
    assert len(set(secrets)) == 1
    assert "data-secret-panel" in page.text
    (record,) = tokens_of(client, "ed")
    with closing(connect(client)) as conn:
        stored = conn.execute(
            "SELECT token_sha256 FROM api_tokens WHERE id = ?", (record.id,)
        ).fetchone()[0]
    assert stored == hash_token(secrets[0])
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {secrets[0]}"})
    assert r.json()["user"]["username"] == "ed"
    again = client.get("/account").text  # a reload shows the name, never the secret
    assert "nightly" in again and not SECRET.search(again)


def test_the_secret_never_reaches_another_session_or_user(client):
    csrf = login(client, "ed")
    second = TestClient(client.app)
    login(second, "ed")  # the same user, another session
    third = TestClient(client.app)
    login(third, "admin")
    r = client.post(
        "/account/tokens", data={"csrf_token": csrf, "name": "t"}, follow_redirects=False
    )
    for session in (second, third):
        assert not SECRET.search(session.get("/account").text)
    assert SECRET.search(client.get("/account").text)  # still waiting for its own session
    assert r.status_code == 303


def test_the_handoff_expires_and_is_bounded(monkeypatch):
    handoff = account_ui.SecretHandoff(size=2, ttl=60)
    clock = [1000.0]
    monkeypatch.setattr(account_ui.time, "monotonic", lambda: clock[0])
    handoff.put("a", 1)
    handoff.put("b", 2)
    handoff.put("c", 3)  # "a" is dropped
    assert handoff.take("a") is None and handoff.take("b") == 2 and handoff.take("b") is None
    clock[0] += 61
    assert handoff.take("c") is None


def test_one_users_sessions_cannot_push_out_anothers_secret():
    handoff = account_ui.SecretHandoff(size=100, ttl=60, per_user=8)
    handoff.put((2, "victim"), "theirs")
    for session in range(20):  # one user, many sessions
        handoff.put((1, f"s{session}"), session)
    assert handoff.take((2, "victim")) == "theirs"
    assert [handoff.take((1, f"s{n}")) for n in range(20)] == [None] * 12 + list(range(12, 20))


def test_the_secret_panel_goes_on_back_and_forward():
    """Restored from the page cache, the page drops the panel (easyml.js, on pageshow)."""
    script = (Path(account_ui.__file__).parent / "static/js/easyml.js").read_text()
    assert 'querySelectorAll("[data-secret-panel]")' in script and "event.persisted" in script


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_a_token_needs_a_name(client, name):
    csrf = login(client, "ed")
    r = client.post("/account/tokens", data={"csrf_token": csrf, "name": name})
    assert r.status_code == 422 and "1 to 100 characters" in r.text
    assert tokens_of(client, "ed") == []


def test_viewers_have_tokens_too(client):
    csrf = login(client, "gv")
    client.post("/account/tokens", data={"csrf_token": csrf, "name": "read-only script"})
    assert [t.name for t in tokens_of(client, "gv")] == ["read-only script"]


def test_revoking_ones_own_token(client):
    csrf = login(client, "ed")
    client.post("/account/tokens", data={"csrf_token": csrf, "name": "old"})
    secret = SECRET.search(client.get("/account").text)
    assert secret is None  # the redirect was followed: shown already, then gone
    (record,) = tokens_of(client, "ed")
    r = client.post(
        f"/account/tokens/{record.id}/revoke", data={"csrf_token": csrf}, follow_redirects=False
    )
    assert r.headers["location"] == "/account?done=revoked"
    assert tokens_of(client, "ed")[0].revoked
    page = client.get("/account?done=revoked").text
    assert "Revoked" in page and f"/account/tokens/{record.id}/revoke" not in page


def test_the_token_table_shows_scope_and_expiry(client):
    login(client, "ed")
    with closing(connect(client)) as conn:
        (user_id,) = conn.execute("SELECT id FROM users WHERE username = 'ed'").fetchone()
        auth_service.create_token(conn, user_id, "plain")
        live, _ = auth_service.create_token(
            conn, user_id, "from-nb", scope=TokenScope.NOTEBOOK,
            expires_at=auth_service.expiry_after(3600),
        )  # fmt: skip
        old, _ = auth_service.create_token(
            conn, user_id, "stale", expires_at=auth_service.expiry_after(-5)
        )
    page = client.get("/account").text
    rows = {m[1]: m[0] for m in re.findall(r"<tr>(.*?<th[^>]*>([^<]+)</th>.*?)</tr>", page, re.S)}
    assert "Notebook" not in rows["plain"] and "Expired" not in rows["plain"]
    assert "Notebook" in rows["from-nb"] and "Active" in rows["from-nb"]
    assert "Expires" in rows["from-nb"] and "UTC" in rows["from-nb"]
    assert "Expired" in rows["stale"] and "Active" not in rows["stale"]
    assert f"/account/tokens/{old.id}/revoke" not in page
    assert f"/account/tokens/{live.id}/revoke" in page
    client.cookies.set("fione_lang", "ja")
    assert "ノートブック" in client.get("/account").text


@pytest.mark.parametrize("who", ["ed", "admin"])
def test_another_users_token_is_not_found(client, who):
    with closing(connect(client)) as conn:
        (gv,) = conn.execute("SELECT id FROM users WHERE username = 'gv'").fetchone()
        record, secret = auth_service.create_token(conn, gv, "theirs")
    csrf = login(client, who)
    page = client.get("/account").text
    assert "theirs" not in page and secret not in page
    for tid in (str(record.id), "abc", "0", str(2**63)):
        r = client.post(f"/account/tokens/{tid}/revoke", data={"csrf_token": csrf})
        assert r.status_code == 404 and "text/html" in r.headers["content-type"]
    assert not tokens_of(client, "gv")[0].revoked


@pytest.mark.parametrize("kind", ["password", "create", "revoke"])
@pytest.mark.parametrize("refusal", ["no_csrf", "cross_site"])
def test_posts_need_the_token_and_this_site(client, kind, refusal):
    csrf = login(client, "ed")
    with closing(connect(client)) as conn:
        (ed,) = conn.execute("SELECT id FROM users WHERE username = 'ed'").fetchone()
        record, _ = auth_service.create_token(conn, ed, "kept")
    token = "" if refusal == "no_csrf" else csrf
    headers = EVIL if refusal == "cross_site" else {}
    if kind == "password":
        r = change(client, token, headers=headers)
    elif kind == "create":
        data = {"csrf_token": token, "name": "new"}
        r = client.post("/account/tokens", data=data, headers=headers)
    else:
        data = {"csrf_token": token}
        r = client.post(f"/account/tokens/{record.id}/revoke", data=data, headers=headers)
    assert r.status_code == 403 and "text/html" in r.headers["content-type"]
    assert [(t.name, t.revoked) for t in tokens_of(client, "ed")] == [("kept", False)]
    login(client, "ed")  # the password is unchanged


def test_token_names_are_escaped(client):
    csrf = login(client, "ed")
    client.post("/account/tokens", data={"csrf_token": csrf, "name": XSS})
    page = client.get("/account").text
    assert XSS not in page and page.count(escape(XSS)) >= 2  # the list and the new panel
    r = client.post("/account/tokens", data={"csrf_token": csrf, "name": XSS + "x" * 100})
    assert r.status_code == 422 and XSS not in r.text


def test_the_curl_example_has_a_placeholder(client):
    csrf = login(client, "ed")
    client.post("/account/tokens", data={"csrf_token": csrf, "name": "t"}, follow_redirects=False)
    page = client.get("/account").text
    example = re.search(r"curl -H [^<]*", page).group(0)
    assert "YOUR_TOKEN" in example and not SECRET.search(example)


def test_the_account_is_in_the_menu_of_everyone(client):
    for who in ("gv", "ed", "admin"):
        login(client, who)
        page = client.get("/").text
        assert 'href="/account"' in page
        assert ('href="/admin/users"' in page) == (who == "admin")
        assert ('href="/admin/system"' in page) == (who == "admin")
        client.cookies.set("fione_mode", "simple")
        assert 'href="/account"' in client.get("/").text


def test_world_personas_reach_their_account(make_client):
    world = make_world(make_client())
    for who in ("ed", "co", "vi", "st", "admin"):
        world.login(who)
        assert world.client.get("/account").status_code == 200
