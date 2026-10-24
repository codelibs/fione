"""Every UI route x {anonymous, logged in}: anonymous visitors are sent to the login page
(or refused, for actions), logged-in users get the page. The API's own matrix is in
tests/api/test_permissions.py; this table covers the routes outside /api."""

import pytest

from api_helpers import add_user, login, make_settings
from fione.api.app import create_app
from fione.auth.roles import Role
from fione.web import views

# (method, path) -> (anonymous status, logged-in status); 303s for anonymous page views go
# to /login?next=<path>. Actions are sent with the session's CSRF token when logged in.
UI_ROUTES = {
    ("GET", "/"): (303, 200),
    ("GET", "/_design"): (303, 200),
    ("GET", "/login"): (200, 303),  # logged in: on to ``next``
    ("GET", "/first-admin"): (303, 303),  # an admin exists: to /login
    ("POST", "/logout"): (303, 303),
    ("POST", "/ui/lang"): (303, 303),
    ("POST", "/ui/projects"): (401, 200),
}
FORMS = {
    "/logout": lambda csrf: {"csrf_token": csrf},
    "/ui/lang": lambda csrf: {"lang": "en", "next": "/"},
    "/ui/projects": lambda csrf: {"name": "p"},
}


def test_table_covers_every_ui_route():
    """Adding a UI route without a row fails here."""
    routes = {(m, r.path) for r in views.router.routes for m in r.methods - {"HEAD"}}
    assert routes == set(UI_ROUTES)


def test_ui_routes_stay_out_of_the_api_schema(tmp_path):
    app = create_app(make_settings(tmp_path), start_runner=False)
    assert all(path.startswith("/api/v1/") for path in app.openapi()["paths"])


@pytest.mark.parametrize("persona", ["anonymous", "user"])
@pytest.mark.parametrize("route", sorted(UI_ROUTES))
def test_ui_route(make_client, route, persona):
    client = make_client()
    add_user(client, "ed", Role.EDITOR)
    add_user(client, "admin", Role.ADMIN)
    csrf = login(client, "ed") if persona == "user" else None
    method, path = route
    expected = UI_ROUTES[route][0 if persona == "anonymous" else 1]
    if method == "GET":
        r = client.get(path, follow_redirects=False)
    else:
        headers = {"HX-Request": "true", **({"X-CSRF-Token": csrf} if csrf else {})}
        r = client.post(path, data=FORMS[path](csrf), headers=headers, follow_redirects=False)
    assert r.status_code == expected, r.text
    if persona == "anonymous" and method == "GET" and expected == 303 and path != "/first-admin":
        assert r.headers["location"].startswith("/login?next=")
