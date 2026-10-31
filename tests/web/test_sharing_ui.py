"""Project sharing: the members page of a project's owner (and administrators), with the
API's service and messages."""

from contextlib import closing
from html import escape

import pytest
from fastapi.testclient import TestClient

from api_helpers import add_user, connect, login
from fione.auth import service as auth_service
from fione.auth.roles import Role
from fione.projects import service as projects
from web_helpers import make_world

EVIL = {"Origin": "https://evil.example"}
XSS = "<img src=x onerror=alert(1)>"


@pytest.fixture
def world(make_client):
    return make_world(make_client())


def members(world, project=None) -> dict:
    with closing(connect(world.client)) as conn:
        return {
            name: access.value for name, access in projects.list_members(conn, project or world.p)
        }


def share(world, csrf, username, access="viewer", **kw):
    data = {"csrf_token": csrf, "username": username, "access": access}
    return world.client.post(world.path("/projects/{p}/members"), data=data, **kw)


def test_the_owner_sees_who_has_access(world):
    world.login("ed")
    page = world.client.get(world.path("/projects/{p}/members")).text
    assert ">ed</th>" in page and "The owner always has full access." in page
    assert ">co</th>" in page and ">vi</th>" in page and ">st</th>" not in page
    assert page.count('action="' + world.path("/projects/{p}/members/remove") + '"') == 2


def test_add_change_and_remove_a_member(world):
    csrf = world.login("ed")
    r = share(world, csrf, "st", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("/members?done=saved")
    assert members(world)["st"] == "viewer"
    st = TestClient(world.client.app)
    login(st, "st")
    assert st.get(world.path("/projects/{p}")).status_code == 200
    assert st.get(world.path("/projects/{p}/upload")).status_code == 403
    share(world, csrf, "st", "editor")
    assert members(world)["st"] == "editor"
    assert st.get(world.path("/projects/{p}/upload")).status_code == 200
    r = world.client.post(
        world.path("/projects/{p}/members/remove"),
        data={"csrf_token": csrf, "username": "st"},
        follow_redirects=False,
    )
    assert r.headers["location"].endswith("/members?done=removed")
    assert "st" not in members(world)
    assert st.get(world.path("/projects/{p}")).status_code == 404


@pytest.mark.parametrize(
    ("username", "access", "status", "message"),
    [
        ("ghost", "viewer", 422, "There is no user named ghost."),
        ("ed", "editor", 422, "ed owns the project and already has full access."),
        ("st", "owner", 422, "Choose Can edit or View only."),
        ("", "viewer", 422, "Enter a username of 1 to 64 characters."),
    ],
)
def test_refusals_are_said_on_the_page(world, username, access, status, message):
    """Unknown users are named as the API names them (422 "unknown user"), nothing more."""
    csrf = world.login("ed")
    before = members(world)
    r = share(world, csrf, username, access)
    assert r.status_code == status and message in r.text
    assert members(world) == before
    api = world.client.post(
        f"/api/v1/projects/{world.p}/share",
        json={"username": username or "x", "access": access if access != "owner" else "viewer"},
        headers={"X-CSRF-Token": csrf},
    )
    if username == "ghost":
        assert api.status_code == 422 and api.json()["error"] == "unknown user: ghost"


def test_the_username_is_taken_as_typed_like_the_api(world):
    csrf = world.login("ed")
    r = share(world, csrf, " st")
    assert r.status_code == 422 and "There is no user named  st." in r.text
    assert "st" not in members(world)
    api = world.client.post(
        f"/api/v1/projects/{world.p}/share",
        json={"username": " st", "access": "viewer"},
        headers={"X-CSRF-Token": csrf},
    )
    assert api.status_code == 422 and api.json()["error"] == "unknown user:  st"


def test_member_rows_stack_on_phones(world):
    world.login("ed")
    page = world.client.get(world.path("/projects/{p}/members")).text
    assert '<table class="table table-stack">' in page
    assert page.count('data-label="Access"') == 3  # the owner and two members


def test_removing_someone_who_is_not_a_member(world):
    csrf = world.login("ed")
    for username in ("st", "ed", "ghost"):
        r = world.client.post(
            world.path("/projects/{p}/members/remove"),
            data={"csrf_token": csrf, "username": username},
        )
        assert r.status_code == 404 and f"{username} is not a member of this project." in r.text
    assert members(world) == {"co": "editor", "vi": "viewer"}


def test_administrators_manage_any_project(world):
    csrf = world.login("admin")
    assert world.client.get(world.path("/projects/{p}/members")).status_code == 200
    share(world, csrf, "st")
    assert members(world)["st"] == "viewer"


def test_a_global_viewer_who_owns_a_project_cannot_share_it(world):
    """As in the API: a viewer is capped at view access, also in their own project."""
    with closing(connect(world.client)) as conn:
        owner = auth_service.get_user(conn, add_user(world.client, "old", Role.EDITOR).id)
        mine = projects.create_project(conn, owner, "Mine")
        auth_service.set_role(conn, owner.id, Role.VIEWER)
    world.login("old")
    r = world.client.get(f"/projects/{mine.id}/members", headers={"Accept": "text/html"})
    assert r.status_code == 403 and "text/html" in r.headers["content-type"]
    assert "/members" not in world.client.get(f"/projects/{mine.id}").text


@pytest.mark.parametrize("who", ["ed", "admin", "co", "vi"])
def test_the_dashboard_links_sharing_for_owners_only(world, who):
    world.login(who)
    link = f'href="{world.path("/projects/{p}/members")}"'
    page = world.client.get(world.path("/projects/{p}")).text
    assert (link in page) == (who in ("ed", "admin"))
    world.client.cookies.set("fione_mode", "detailed")
    page = world.client.get(world.path("/projects/{p}/datasets")).text
    assert (f"<li><a {link}" in page) == (who in ("ed", "admin"))  # the sub-nav entry
    world.client.cookies.set("fione_mode", "simple")
    page = world.client.get(world.path("/projects/{p}/datasets")).text
    assert f"<li><a {link}" not in page


@pytest.mark.parametrize("path", ["/members", "/members/remove"])
@pytest.mark.parametrize("refusal", ["no_csrf", "cross_site"])
def test_sharing_posts_need_the_token_and_this_site(world, path, refusal):
    csrf = world.login("ed")
    data = {
        "csrf_token": "" if refusal == "no_csrf" else csrf,
        "username": "co",
        "access": "viewer",
    }
    headers = EVIL if refusal == "cross_site" else {}
    r = world.client.post(world.path("/projects/{p}" + path), data=data, headers=headers)
    assert r.status_code == 403 and "text/html" in r.headers["content-type"]
    assert members(world) == {"co": "editor", "vi": "viewer"}


def test_names_are_escaped(world):
    with closing(connect(world.client)) as conn:
        conn.execute("UPDATE projects SET name = ? WHERE id = ?", (XSS, world.p))
        conn.execute("UPDATE users SET username = ? WHERE username = 'co'", (XSS,))
    csrf = world.login("ed")
    page = world.client.get(world.path("/projects/{p}/members")).text
    assert XSS not in page and escape(XSS) in page
    r = share(world, csrf, XSS + "x" * 70)
    assert r.status_code == 422 and XSS not in r.text


def count(world, table: str, project: str) -> int:
    with closing(connect(world.client)) as conn:
        sql = f"SELECT COUNT(*) FROM {table} WHERE project_id = ?"
        return conn.execute(sql, (project,)).fetchone()[0]


def test_the_owner_deletes_the_project_with_its_jobs_and_data(world):
    """The API's steps: queued and running jobs stopped, rows, objects and job logs gone."""
    csrf = world.login("ed")
    storage = world.client.app.state.storage
    logs = world.client.app.state.settings.data_dir / "jobs"
    with closing(connect(world.client)) as conn:
        rows = conn.execute("SELECT id FROM jobs WHERE project_id = ?", (world.p,))
        job_ids = [row[0] for row in rows]
    logs.mkdir(parents=True, exist_ok=True)
    for job_id in job_ids:
        (logs / f"{job_id}.log").write_text("log")
    assert storage.list(f"projects/{world.p}/") and count(world, "jobs", world.p)
    page = world.client.get(world.path("/projects/{p}")).text
    assert f'action="/projects/{world.p}/delete"' in page
    r = world.client.post(
        world.path("/projects/{p}/delete"), data={"csrf_token": csrf}, follow_redirects=False
    )
    assert r.status_code == 303 and r.headers["location"] == "/"
    for table in ("jobs", "datasets", "models"):
        assert count(world, table, world.p) == 0, table
    assert storage.list(f"projects/{world.p}/") == []
    assert not any((logs / f"{job_id}.log").exists() for job_id in job_ids)
    assert world.client.get(world.path("/projects/{p}")).status_code == 404
    assert count(world, "datasets", world.q) > 0  # the other project is untouched


@pytest.mark.parametrize("who", ["ed", "admin", "co", "vi"])
def test_the_delete_button_is_for_owners_and_administrators(world, who):
    world.login(who)
    page = world.client.get(world.path("/projects/{p}")).text
    assert (f'action="/projects/{world.p}/delete"' in page) == (who in ("ed", "admin"))


@pytest.mark.parametrize("refusal", ["no_csrf", "cross_site"])
def test_deleting_needs_the_token_and_this_site(world, refusal):
    csrf = world.login("ed")
    data = {"csrf_token": "" if refusal == "no_csrf" else csrf}
    headers = EVIL if refusal == "cross_site" else {}
    r = world.client.post(world.path("/projects/{p}/delete"), data=data, headers=headers)
    assert r.status_code == 403 and "text/html" in r.headers["content-type"]
    assert world.client.get(world.path("/projects/{p}")).status_code == 200


def test_the_delete_question_escapes_the_name(world):
    with closing(connect(world.client)) as conn:
        conn.execute("UPDATE projects SET name = ? WHERE id = ?", (XSS, world.p))
    world.login("ed")
    page = world.client.get(world.path("/projects/{p}")).text
    assert XSS not in page and escape(XSS) in page
