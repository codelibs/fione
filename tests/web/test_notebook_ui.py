"""The notebook page: who may use it, start and stop, the framed JupyterLab and its CSP, and
what happens to a running notebook when its user's permission changes."""

import base64
import json
import logging
import re
import time
from contextlib import closing
from datetime import UTC, datetime
from html import unescape

import pytest

from api_helpers import NOTEBOOK_SETTINGS, add_user, connect, login, notebook_client
from fione.auth import service as auth_service
from fione.auth.roles import NotebookPermission, Role
from fione.notebooks.launch import launch_key
from fione.notebooks.launcher import HttpLauncher, LauncherError

NAV_LINK = 'href="/notebook"'


@pytest.fixture
def nb(make_client):
    """An install with notebooks: ``ed`` may use them, ``vi`` may not, ``admin`` always may."""
    client = notebook_client(make_client)
    ed = add_user(client, "ed", Role.EDITOR)
    add_user(client, "vi", Role.EDITOR)
    add_user(client, "admin", Role.ADMIN)
    with closing(connect(client)) as conn:
        auth_service.set_notebook_permission(conn, ed.id, NotebookPermission.RUN)
    return client


def _start(client, username="ed"):
    client.cookies.clear()
    csrf = login(client, username)
    r = client.post("/notebook/start", data={"csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/notebook", r.text
    return csrf


def _uid(client, username) -> int:
    with closing(connect(client)) as conn:
        return conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()[0]


def _token_works(client, token) -> bool:
    r = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (200, 401), r.text
    return r.status_code == 200


def _frame_src(html: str) -> str:
    match = re.search(r'<iframe class="notebook-frame" src="([^"]+)"', html)
    assert match, html
    return unescape(match.group(1))


def _launch_claims(src: str) -> dict:
    token = re.search(r"launch=([^&]+)", src).group(1)
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def test_page_404_when_disabled_and_403_without_permission(make_client, nb, tmp_path):
    client = make_client(tmp_path / "off")  # notebooks off
    add_user(client, "admin", Role.ADMIN)
    login(client, "admin")
    assert client.get("/notebook").status_code == 404
    assert NAV_LINK not in client.get("/").text
    login(nb, "vi")
    r = nb.get("/notebook")
    assert r.status_code == 403 and "text/html" in r.headers["content-type"]
    assert NAV_LINK not in r.text and NAV_LINK not in nb.get("/").text
    assert nb.app.state.notebook_launcher.calls == []
    for username in ("ed", "admin"):
        nb.cookies.clear()
        login(nb, username)
        home = nb.get("/").text
        assert NAV_LINK in home
        page = nb.get("/notebook")
        assert page.status_code == 200
        assert re.search(r'href="/notebook" aria-current="page"', page.text)


def test_start_requires_csrf_and_same_origin(nb):
    csrf = login(nb, "ed")
    r = nb.post("/notebook/start", data={"csrf_token": "wrong"}, follow_redirects=False)
    assert r.status_code == 403
    r = nb.post(
        "/notebook/start",
        data={"csrf_token": csrf},
        headers={"Origin": "http://evil.example"},
        follow_redirects=False,
    )
    assert r.status_code == 403
    r = nb.post("/notebook/stop", data={}, follow_redirects=False)
    assert r.status_code == 403
    assert nb.app.state.notebook_launcher.calls == []


def test_start_creates_a_notebook_token_and_session(nb):
    before = time.time()
    _start(nb)
    uid = _uid(nb, "ed")
    (body,) = nb.app.state.notebook_launcher.bodies()
    assert set(body) == {"launch_key", "cookie_secret", "token", "fione_origin", "expires_at"}
    assert body["fione_origin"] == "http://127.0.0.1:8080"
    with closing(connect(nb)) as conn:
        _, record = auth_service.token_identity(conn, body["token"])
        nonce = conn.execute(
            "SELECT nonce FROM notebook_sessions WHERE user_id = ?", (uid,)
        ).fetchone()[0]
    assert record.scope == "notebook"
    expires = datetime.strptime(record.expires_at, "%Y-%m-%d %H:%M:%S")
    expires = expires.replace(tzinfo=UTC).timestamp()
    assert abs(expires - (before + 43200)) <= 5
    assert body["launch_key"] == launch_key(nb.app.state.secret, uid, nonce).hex()
    page = nb.get("/notebook")
    assert 'hx-get="/notebook/status"' in page.text and "<iframe" not in page.text
    assert "frame-src" not in page.headers["content-security-policy"]


def test_running_page_frames_the_gateway(nb):
    _start(nb)
    uid = _uid(nb, "ed")
    nb.app.state.notebook_launcher.states[uid] = "running"
    r = nb.get("/notebook")
    assert r.status_code == 200
    src = _frame_src(r.text)
    assert src.startswith(f"http://127.0.0.1:8888/user/{uid}/login?launch=v1.")
    assert src.endswith(f"&next=/user/{uid}/lab")
    csp = r.headers["content-security-policy"]
    assert csp.endswith("; frame-src http://127.0.0.1:8888")
    assert "frame-ancestors 'none'" in csp
    assert r.headers["cache-control"] == "no-store"
    claims = _launch_claims(src)
    assert claims["sub"] == str(uid) and claims["name"] == "ed" and claims["role"] == "editor"


def test_other_pages_have_no_frame_src(nb):
    _start(nb, "admin")
    nb.app.state.notebook_launcher.states[_uid(nb, "admin")] = "running"
    assert "frame-src" in nb.get("/notebook").headers["content-security-policy"]
    for path in ("/", "/account", "/admin/users", "/notebook/status", "/no-such-page"):
        r = nb.get(path, headers={"Accept": "text/html"})
        assert "frame-src" not in r.headers["content-security-policy"], path


def test_launch_token_is_fresh_per_render(nb):
    _start(nb)
    nb.app.state.notebook_launcher.states[_uid(nb, "ed")] = "running"
    first, second = (_launch_claims(_frame_src(nb.get("/notebook").text)) for _ in range(2))
    assert first["jti"] != second["jti"]


def test_status_polls_until_the_notebook_runs(nb):
    _start(nb)
    hx = {"HX-Request": "true"}
    r = nb.get("/notebook/status", headers=hx)
    assert r.status_code == 200 and 'hx-trigger="every 2s"' in r.text
    assert "HX-Refresh" not in r.headers and "launch=" not in r.text
    nb.app.state.notebook_launcher.states[_uid(nb, "ed")] = "running"
    r = nb.get("/notebook/status", headers=hx)
    assert r.headers["HX-Refresh"] == "true"
    assert "hx-trigger" not in r.text and "launch=" not in r.text
    nb.app.state.notebook_launcher.fail = LauncherError("unreachable")
    r = nb.get("/notebook/status", headers=hx)
    assert r.status_code == 286 and "hx-trigger" not in r.text


def test_absent_with_session_revokes_the_token(nb):
    _start(nb)
    fake = nb.app.state.notebook_launcher
    token = fake.bodies()[0]["token"]
    assert _token_works(nb, token)
    fake.states.clear()  # culled or expired
    page = nb.get("/notebook")
    assert 'action="/notebook/start"' in page.text
    assert not _token_works(nb, token)


def test_stop_revokes_and_removes(nb):
    csrf = _start(nb)
    fake = nb.app.state.notebook_launcher
    token = fake.bodies()[0]["token"]
    uid = _uid(nb, "ed")
    r = nb.post("/notebook/stop", data={"csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/notebook"
    assert ("stop", uid) in fake.calls and uid not in fake.states
    assert not _token_works(nb, token)
    with closing(connect(nb)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM notebook_sessions").fetchone()[0] == 0


def test_revoking_permission_stops_the_container(nb):
    fake = nb.app.state.notebook_launcher
    _start(nb, "ed")
    _start(nb, "admin")
    add_user(nb, "admin2", Role.ADMIN)
    _start(nb, "admin2")  # an admin with the stored `none`
    tokens = {
        name: body["token"]
        for name, body in zip(("ed", "admin", "admin2"), fake.bodies(), strict=True)
    }
    ed, admin2 = _uid(nb, "ed"), _uid(nb, "admin2")
    nb.cookies.clear()
    csrf = login(nb, "admin")
    headers = {"X-CSRF-Token": csrf}
    r = nb.patch(f"/api/v1/users/{ed}", json={"notebook": "none"}, headers=headers)
    assert r.status_code == 200, r.text
    assert ("stop", ed) in fake.calls and not _token_works(nb, tokens["ed"])
    r = nb.patch(f"/api/v1/users/{admin2}", json={"role": "editor"}, headers=headers)
    assert r.status_code == 200, r.text
    assert ("stop", admin2) in fake.calls and not _token_works(nb, tokens["admin2"])
    assert _token_works(nb, tokens["admin"])


def test_deleting_a_user_purges_their_notebook_afterwards(nb):
    fake = nb.app.state.notebook_launcher
    _start(nb, "admin")
    token = fake.bodies()[0]["token"]
    admin, ed = _uid(nb, "admin"), _uid(nb, "ed")
    headers = {"X-CSRF-Token": login(nb, "admin")}
    fake.calls.clear()
    # A refused deletion (oneself) leaves the notebook alone.
    assert nb.delete(f"/api/v1/users/{admin}", headers=headers).status_code == 409
    assert fake.calls == [] and _token_works(nb, token)
    exists_at_purge = []
    purge = fake.purge

    def recording_purge(uid):
        with closing(connect(nb)) as conn:
            exists_at_purge.append(auth_service.get_user(conn, uid) is not None)
        purge(uid)

    fake.purge = recording_purge
    assert nb.delete(f"/api/v1/users/{ed}", headers=headers).status_code == 204
    assert exists_at_purge == [False] and fake.calls == [("purge", ed)]


def test_a_new_password_stops_the_notebook(nb):
    fake = nb.app.state.notebook_launcher
    _start(nb, "ed")
    _start(nb, "admin")
    add_user(nb, "ed2", Role.EDITOR)
    ed2 = _uid(nb, "ed2")
    with closing(connect(nb)) as conn:
        auth_service.set_notebook_permission(conn, ed2, NotebookPermission.RUN)
    _start(nb, "ed2")
    ed_token, _, ed2_token = (body["token"] for body in fake.bodies())
    ed = _uid(nb, "ed")
    nb.cookies.clear()
    csrf = login(nb, "admin")
    r = nb.patch(
        f"/api/v1/users/{ed}", json={"password": "a-new-password-1"}, headers={"X-CSRF-Token": csrf}
    )
    assert r.status_code == 200 and ("stop", ed) in fake.calls
    assert not _token_works(nb, ed_token)
    r = nb.post(
        f"/admin/users/{ed2}/password",
        data={"csrf_token": csrf, "password": "a-new-password-1"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and ("stop", ed2) in fake.calls
    assert not _token_works(nb, ed2_token)


def test_admin_ui_changes_stop_the_container(nb):
    fake = nb.app.state.notebook_launcher
    _start(nb, "ed")
    token = fake.bodies()[0]["token"]
    ed = _uid(nb, "ed")
    nb.cookies.clear()
    csrf = login(nb, "admin")
    r = nb.post(
        f"/admin/users/{ed}/role",
        data={"csrf_token": csrf, "role": "viewer"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and ("stop", ed) not in fake.calls  # still allowed
    r = nb.post(
        f"/admin/users/{ed}/notebook",
        data={"csrf_token": csrf, "notebook": "none"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and ("stop", ed) in fake.calls
    assert not _token_works(nb, token)
    fake.calls.clear()
    admin = _uid(nb, "admin")
    r = nb.post(f"/admin/users/{admin}/delete", data={"csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == 409 and fake.calls == []  # refused: nothing stopped
    fake.fail = LauncherError("unreachable")  # logged; the deletion goes on
    r = nb.post(f"/admin/users/{ed}/delete", data={"csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == 303 and fake.calls == [("purge", ed)]
    with closing(connect(nb)) as conn:
        assert auth_service.get_user(conn, ed) is None


def test_admin_role_change_with_the_launcher_down_still_applies(nb):
    fake = nb.app.state.notebook_launcher
    _start(nb, "admin")
    add_user(nb, "admin2", Role.ADMIN)
    _start(nb, "admin2")
    token = fake.bodies()[-1]["token"]
    admin2 = _uid(nb, "admin2")
    nb.cookies.clear()
    csrf = login(nb, "admin")
    fake.fail = LauncherError("unreachable")
    r = nb.patch(f"/api/v1/users/{admin2}", json={"role": "viewer"}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200 and r.json()["role"] == "viewer"
    assert not _token_works(nb, token)


@pytest.mark.parametrize(
    "code,status,key",
    [
        ("limit", 409, "Too many notebooks are running"),
        ("image_missing", 503, "The notebook image is not installed"),
        ("unreachable", 503, "The notebook service is not available"),
        ("refused", 503, "The notebook service is not available"),
    ],
)
def test_launcher_errors_are_not_rendered_verbatim(nb, code, status, key):
    fake = nb.app.state.notebook_launcher
    ensure = fake.ensure

    def failing(uid, body):
        ensure(uid, body)
        raise LauncherError(code, "<script>alert(1)</script>")

    fake.ensure = failing
    csrf = login(nb, "ed")
    r = nb.post("/notebook/start", data={"csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == status
    assert key in r.text and "<script>alert" not in r.text and "&lt;script" not in r.text
    assert 'action="/notebook/start"' in r.text


def test_a_permission_revoked_during_the_start_is_403(nb):
    """The admin's revocation lands while the start waits on the launcher (I1)."""
    fake = nb.app.state.notebook_launcher
    status = fake.status
    ed = _uid(nb, "ed")

    def revoking_status(uid):
        with closing(connect(nb)) as conn:
            auth_service.set_notebook_permission(conn, ed, NotebookPermission.NONE)
        return status(uid)

    fake.status = revoking_status
    csrf = login(nb, "ed")
    r = nb.post("/notebook/start", data={"csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == 403 and "You may not use notebooks" in r.text
    assert fake.bodies() == []
    with closing(connect(nb)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM notebook_sessions").fetchone()[0] == 0
        assert not [t for t in auth_service.list_tokens(conn, ed) if t.scope == "notebook"]


def test_launcher_down_is_a_503_page(nb):
    login(nb, "ed")
    nb.app.state.notebook_launcher.fail = LauncherError("unreachable", "<b>launcher</b>")
    r = nb.get("/notebook")
    assert r.status_code == 503
    assert "The notebook service is not available" in r.text and "launcher</b>" not in r.text
    r = nb.get("/notebook/status")
    assert r.status_code == 503 and "launcher</b>" not in r.text


def test_page_in_japanese(nb):
    login(nb, "ed")
    nb.cookies.set("fione_lang", "ja")
    r = nb.get("/notebook")
    assert "ノートブックを起動" in r.text


def test_no_token_in_fione_logs(nb, caplog):
    with caplog.at_level(logging.DEBUG):
        _start(nb)
        uid = _uid(nb, "ed")
        fake = nb.app.state.notebook_launcher
        fake.states[uid] = "running"
        src = _frame_src(nb.get("/notebook").text)
        nb.get("/notebook/status", headers={"HX-Request": "true"})
        fake.fail = LauncherError("unreachable")
        nb.get("/notebook")
    launch = re.search(r"launch=([^&]+)", src).group(1)
    notebook_token = fake.bodies()[0]["token"]
    assert caplog.records  # the failure above was logged
    body = fake.bodies()[0]
    for secret in (launch, notebook_token, body["launch_key"], body["cookie_secret"]):
        assert secret not in caplog.text


def test_no_secret_in_any_page(nb):
    """Only the launch token reaches a page, and only the running page's frame."""
    csrf = _start(nb)
    uid = _uid(nb, "ed")
    fake = nb.app.state.notebook_launcher
    pages = [nb.get("/notebook"), nb.get("/notebook/status", headers={"HX-Request": "true"})]
    fake.states[uid] = "running"
    pages += [nb.get("/notebook"), nb.get("/notebook/status", headers={"HX-Request": "true"})]
    pages += [nb.get("/"), nb.get("/account")]
    fake.fail = LauncherError("unreachable")
    pages += [nb.get("/notebook"), nb.get("/notebook/status")]
    pages.append(nb.post("/notebook/stop", data={"csrf_token": csrf}, follow_redirects=False))
    body = fake.bodies()[0]
    secrets_ = [body["token"], body["launch_key"], body["cookie_secret"]]
    for page in pages:
        assert not any(secret in page.text for secret in secrets_), page.url
    assert sum("launch=v1." in page.text for page in pages) == 1


def test_the_app_talks_to_the_configured_launcher(make_client, tmp_path):
    launcher = make_client(**NOTEBOOK_SETTINGS).app.state.notebook_launcher
    assert isinstance(launcher, HttpLauncher) and launcher.url == "http://launcher"
    assert make_client(tmp_path / "off").app.state.notebook_launcher is None
