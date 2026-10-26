"""Every UI route x {anonymous, logged in}: anonymous visitors are sent to the login page
(or refused, for actions), logged-in users get the page. The API's own matrix is in
tests/api/test_permissions.py; this table covers the routes outside /api."""

from contextlib import closing

import pytest

from api_helpers import PW, add_user, connect, iris_csv, login, make_settings
from fione.api.app import create_app
from fione.auth import service as auth_service
from fione.auth.roles import Role
from fione.models import service as models_service
from fione.models.transfer import export_model
from fione.modules import service as modules_service
from fione.web import (
    account_ui,
    admin_ui,
    automl,
    easyml,
    models_ui,
    modules_ui,
    sharing_ui,
    views,
)
from web_helpers import iris_test_csv, make_world

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
    ("POST", "/ui/mode"): (401, 303),
}
FORMS = {
    "/logout": lambda csrf: {"csrf_token": csrf},
    "/ui/lang": lambda csrf: {"lang": "en", "next": "/"},
    "/ui/projects": lambda csrf: {"name": "p"},
    "/ui/mode": lambda csrf: {"csrf_token": csrf or "", "mode": "detailed", "next": "/"},
}


# The EasyML routes x personas: anonymous, the owner, a member who may edit, a member who may
# only view, and a signed-in user who is no member. Anonymous page views go to the login page
# (303); anonymous form posts get the session-ended page (401). Posts carry the persona's CSRF
# token and a valid form, so the owner's and the editor's succeed (303).
P = "/projects/{p}"
EASYML_ROUTES = {
    ("GET", P): (303, 200, 200, 200, 404),
    ("GET", P + "/upload"): (303, 200, 200, 403, 404),
    ("POST", P + "/upload"): (401, 303, 303, 403, 404),
    ("GET", P + "/datasets/{train}/analyze"): (303, 200, 200, 200, 404),
    ("POST", P + "/datasets/{train}/run"): (401, 303, 303, 403, 404),
    ("GET", P + "/jobs/{job}"): (303, 200, 200, 200, 404),
    ("GET", P + "/jobs/{job}/status"): (303, 200, 200, 200, 404),
    ("POST", P + "/jobs/{job}/cancel"): (401, 303, 303, 403, 404),
    ("GET", P + "/jobs/{predict_job}/result"): (303, 200, 200, 200, 404),
    ("GET", P + "/jobs/{predict_job}/result/why"): (303, 200, 200, 200, 404),
    ("GET", P + "/models/{model}/summary"): (303, 200, 200, 200, 404),
    ("GET", P + "/models/{model}/predict"): (303, 200, 200, 403, 404),
    ("POST", P + "/models/{model}/predict"): (401, 303, 303, 403, 404),
    ("POST", P + "/models/{model}/predict/run"): (401, 303, 303, 403, 404),
}
PERSONAS = {"anonymous": None, "owner": "ed", "editor": "co", "viewer": "vi", "stranger": "st"}
ROUTE_PATHS = {  # the router's path -> the table's template
    "/projects/{pid}": P,
    "/projects/{pid}/upload": P + "/upload",
    "/projects/{pid}/datasets/{did}/analyze": P + "/datasets/{train}/analyze",
    "/projects/{pid}/datasets/{did}/run": P + "/datasets/{train}/run",
    "/projects/{pid}/jobs/{jid}": P + "/jobs/{job}",
    "/projects/{pid}/jobs/{jid}/status": P + "/jobs/{job}/status",
    "/projects/{pid}/jobs/{jid}/cancel": P + "/jobs/{job}/cancel",
    "/projects/{pid}/jobs/{jid}/result": P + "/jobs/{predict_job}/result",
    "/projects/{pid}/jobs/{jid}/result/why": P + "/jobs/{predict_job}/result/why",
    "/projects/{pid}/models/{mid}/summary": P + "/models/{model}/summary",
    "/projects/{pid}/models/{mid}/predict": P + "/models/{model}/predict",
    "/projects/{pid}/models/{mid}/predict/run": P + "/models/{model}/predict/run",
}


def easyml_request(world, method, template, csrf, project=None, objects=None):
    """Send the route's request with a valid form (multipart for uploads)."""
    client, path = world.client, world.path(template, project, objects)
    ids = world.ids[objects or project or world.p]
    if method == "GET":
        return client.get(path, follow_redirects=False)
    token = {"csrf_token": csrf or ""}
    if path.endswith("/upload"):
        files = {"file": ("iris.csv", iris_csv(), "text/csv")}
        return client.post(path, data=token, files=files, follow_redirects=False)
    if path.endswith("/predict"):
        files = {"file": ("new.csv", iris_test_csv(), "text/csv")}
        return client.post(path, data=token, files=files, follow_redirects=False)
    forms = {  # the first suffix that matches
        "/predict/run": {"dataset_id": str(ids["test"]), "include": ["petal width (cm)"]},
        "/run": {"target": "species", "inputs": ["petal width (cm)"], "task": "classification"}
        | {"runtime": "1"},
        "/cancel": {},
    }
    form = next(f for suffix, f in forms.items() if path.endswith(suffix))
    return client.post(path, data=token | form, follow_redirects=False)


# The AutoML routes x personas: anonymous, owner, editor member, viewer member, non-member,
# admin (who acts as an owner of every project).
AUTOML_PERSONAS = {
    "anonymous": None,
    "owner": "ed",
    "editor": "co",
    "viewer": "vi",
    "stranger": "st",
    "admin": "admin",
}
READ = (303, 200, 200, 200, 404, 200)
WRITE_PAGE = (303, 200, 200, 403, 404, 200)
WRITE_POST = (401, 303, 303, 403, 404, 303)
AUTOML_ROUTES = {
    ("GET", P + "/datasets"): READ,
    ("POST", P + "/datasets"): WRITE_POST,
    ("GET", P + "/datasets/{train}"): READ,
    ("POST", P + "/datasets/{test}/delete"): WRITE_POST,
    ("GET", P + "/datasets/{train}/columns/species"): READ,
    ("GET", P + "/datasets/{train}/train"): WRITE_PAGE,
    ("POST", P + "/datasets/{train}/train"): WRITE_POST,
    ("GET", P + "/jobs"): READ,
    ("POST", P + "/jobs/{predict_job}/delete"): WRITE_POST,
    ("POST", P + "/jobs/delete-finished"): WRITE_POST,
}
AUTOML_PATHS = {
    "/projects/{pid}/datasets": P + "/datasets",
    "/projects/{pid}/datasets/{did}": P + "/datasets/{train}",
    "/projects/{pid}/datasets/{did}/delete": P + "/datasets/{test}/delete",
    "/projects/{pid}/datasets/{did}/columns/{name:path}": P + "/datasets/{train}/columns/species",
    "/projects/{pid}/datasets/{did}/train": P + "/datasets/{train}/train",
    "/projects/{pid}/jobs": P + "/jobs",
    "/projects/{pid}/jobs/{jid}/delete": P + "/jobs/{predict_job}/delete",
    "/projects/{pid}/jobs/delete-finished": P + "/jobs/delete-finished",
}
TRAIN_FORM = {
    "target": "species",
    "task": "auto",
    "inputs": ["petal width (cm)"],
    "max_runtime_minutes": "1",
    "nfolds": "5",
    "seed": "0",
    "stopping_rounds": "3",
    "stopping_metric": "auto",
    "stopping_tolerance": "0.001",
    "sort_metric": "auto",
}


def automl_request(world, method, template, csrf, objects=None):
    client, path = world.client, world.path(template, None, objects)
    if method == "GET":
        return client.get(path, follow_redirects=False)
    token = {"csrf_token": csrf or ""}
    if path.endswith("/datasets"):
        files = {"file": ("new.csv", iris_csv(), "text/csv")}
        data = token | {"kind": "train"}
        return client.post(path, data=data, files=files, follow_redirects=False)
    form = TRAIN_FORM if path.endswith("/train") else {}
    return client.post(path, data=token | form, follow_redirects=False)


# The model screens x the AutoML personas. Import is for administrators only, checked before
# the project, as the API's admin dependency does: every other persona gets 403.
ADMIN_PAGE = (303, 403, 403, 403, 403, 200)
ADMIN_POST = (401, 403, 403, 403, 403, 303)
MODEL_ROUTES = {
    ("GET", P + "/models"): READ,
    ("POST", P + "/models/export"): (401, 303, 303, 303, 404, 303),  # readers may export
    ("GET", P + "/models/import"): ADMIN_PAGE,
    ("POST", P + "/models/import"): ADMIN_POST,
    ("GET", P + "/models/{model}"): READ,
    ("GET", P + "/models/{model}/export"): (303, 200, 200, 200, 404, 200),
    ("POST", P + "/models/{model}/delete"): WRITE_POST,
    ("GET", P + "/models/{model}/explain/pd"): READ,
    ("POST", P + "/models/{model}/explain"): WRITE_POST,
}
MODEL_PATHS = {
    "/projects/{pid}/models": P + "/models",
    "/projects/{pid}/models/export": P + "/models/export",
    "/projects/{pid}/models/import": P + "/models/import",
    "/projects/{pid}/models/{mid}": P + "/models/{model}",
    "/projects/{pid}/models/{mid}/export": P + "/models/{model}/export",
    "/projects/{pid}/models/{mid}/delete": P + "/models/{model}/delete",
    "/projects/{pid}/models/{mid}/explain/pd": P + "/models/{model}/explain/pd",
    "/projects/{pid}/models/{mid}/explain": P + "/models/{model}/explain",
}
# The global modules screens x anonymous and the global roles.
MODULE_PERSONAS = {"anonymous": None, "viewer": "gv", "editor": "ed", "admin": "admin"}
MODULE_ROUTES = {
    ("GET", "/modules"): (303, 200, 200, 200),
    ("GET", "/modules/upload"): (303, 403, 403, 200),
    ("POST", "/modules/upload"): (401, 403, 403, 303),
    ("POST", "/modules/{module_id}/delete"): (401, 403, 403, 303),
}
MODULE_SOURCE = b"""
MODULE = {"name": "Add", "kind": "frame", "params": {"type": "object", "properties": {}}}


def run(df, params, ctx):
    return df
"""


# The account and administration screens x anonymous and the global roles (a viewer, an
# editor, an administrator). Posts carry a valid form; the account's revoke is of one's own
# token, the users' changes are made to ``st``, who owns nothing.
GLOBAL_PERSONAS = {"anonymous": None, "viewer": "gv", "editor": "ed", "admin": "admin"}
ACCOUNT_ROUTES = {
    ("GET", "/account"): (303, 200, 200, 200),
    ("POST", "/account/password"): (401, 303, 303, 303),
    ("POST", "/account/tokens"): (401, 303, 303, 303),
    ("POST", "/account/tokens/{tid}/revoke"): (401, 303, 303, 303),
}
ADMIN_ROUTES = {
    ("GET", "/admin/users"): (303, 403, 403, 200),
    ("POST", "/admin/users"): (401, 403, 403, 303),
    ("POST", "/admin/users/{uid}/role"): (401, 403, 403, 303),
    ("POST", "/admin/users/{uid}/password"): (401, 403, 403, 303),
    ("POST", "/admin/users/{uid}/notebook"): (401, 403, 403, 303),
    ("POST", "/admin/users/{uid}/delete"): (401, 403, 403, 303),
    ("GET", "/admin/system"): (303, 403, 403, 200),
}
GLOBAL_FORMS = {
    "/account/password": {"current_password": PW, "new_password": "a-new-password-1"}
    | {"confirm_password": "a-new-password-1"},
    "/account/tokens": {"name": "script"},
    "/admin/users": {"username": "newbie", "password": PW, "role": "viewer"},
    "/role": {"role": "viewer"},
    "/notebook": {"notebook": "run"},
    "/password": {"password": "a-new-password-1"},
}
# Project sharing x the AutoML personas: the owner's (and admins') only, 403 for the
# project's other readers.
OWNER_PAGE = (303, 200, 403, 403, 404, 200)
OWNER_POST = (401, 303, 403, 403, 404, 303)
SHARING_ROUTES = {
    ("GET", P + "/members"): OWNER_PAGE,
    ("POST", P + "/members"): OWNER_POST,
    ("POST", P + "/members/remove"): OWNER_POST,
    ("POST", P + "/delete"): OWNER_POST,
}
SHARING_PATHS = {
    "/projects/{pid}/members": P + "/members",
    "/projects/{pid}/members/remove": P + "/members/remove",
    "/projects/{pid}/delete": P + "/delete",
}


def global_request(world, method, template, csrf, username):
    client = world.client
    with closing(connect(client)) as conn:
        ids = dict(conn.execute("SELECT username, id FROM users").fetchall())
        token, _ = auth_service.create_token(conn, ids[username or "st"], "mine")
    path = template.replace("{uid}", str(ids["st"])).replace("{tid}", str(token.id))
    if method == "GET":
        return client.get(path, follow_redirects=False)
    form = next((f for suffix, f in GLOBAL_FORMS.items() if path.endswith(suffix)), {})
    return client.post(path, data={"csrf_token": csrf or ""} | form, follow_redirects=False)


def sharing_request(world, method, template, csrf):
    client, path = world.client, world.path(template)
    if method == "GET":
        return client.get(path, follow_redirects=False)
    forms = {"/remove": {"username": "co"}, "/delete": {}}
    form = next((f for end, f in forms.items() if path.endswith(end)), None)
    form = {"username": "st", "access": "viewer"} if form is None else form
    return client.post(path, data={"csrf_token": csrf or ""} | form, follow_redirects=False)


def model_request(world, method, template, csrf, objects=None):
    client, path = world.client, world.path(template, None, objects)
    if method == "GET":
        # the fragment computes for a column (the model has no training data: a message)
        params = {"column": "petal width (cm)"} if path.endswith("/explain/pd") else None
        return client.get(path, params=params, follow_redirects=False)
    token = {"csrf_token": csrf or ""}
    if path.endswith("/explain"):  # the model has no training data: a dataset is chosen
        ids = world.ids[objects or world.p]
        return client.post(
            path, data=token | {"dataset_id": str(ids["train"])}, follow_redirects=False
        )
    if path.endswith("/import"):
        with closing(connect(client)) as conn:
            record = models_service.get_model(conn, world.ids[world.q]["model"])
        archive = b"".join(export_model(client.app.state.storage, record))
        files = {"file": ("model.zip", archive, "application/zip")}
        return client.post(path, data=token, files=files, follow_redirects=False)
    return client.post(path, data=token, follow_redirects=False)


def test_table_covers_every_ui_route():
    """Adding a UI route without a row fails here."""
    routes = {(m, r.path) for r in views.router.routes for m in r.methods - {"HEAD"}}
    assert routes == set(UI_ROUTES)
    routes = {(m, ROUTE_PATHS[r.path]) for r in easyml.router.routes for m in r.methods - {"HEAD"}}
    assert routes == set(EASYML_ROUTES)
    routes = {(m, AUTOML_PATHS[r.path]) for r in automl.router.routes for m in r.methods - {"HEAD"}}
    assert routes == set(AUTOML_ROUTES)
    routes = {
        (m, MODEL_PATHS[r.path]) for r in models_ui.router.routes for m in r.methods - {"HEAD"}
    }
    assert routes == set(MODEL_ROUTES)
    routes = {(m, r.path) for r in modules_ui.router.routes for m in r.methods - {"HEAD"}}
    assert routes == set(MODULE_ROUTES)
    routes = {(m, r.path) for r in account_ui.router.routes for m in r.methods - {"HEAD"}}
    assert routes == set(ACCOUNT_ROUTES)
    routes = {(m, r.path) for r in admin_ui.router.routes for m in r.methods - {"HEAD"}}
    assert routes == set(ADMIN_ROUTES)
    routes = {
        (m, SHARING_PATHS[r.path]) for r in sharing_ui.router.routes for m in r.methods - {"HEAD"}
    }
    assert routes == set(SHARING_ROUTES)


@pytest.mark.parametrize("persona", list(GLOBAL_PERSONAS))
@pytest.mark.parametrize("route", sorted(ACCOUNT_ROUTES) + sorted(ADMIN_ROUTES))
def test_account_and_admin_route(make_client, route, persona):
    world = make_world(make_client())
    add_user(world.client, "gv", Role.VIEWER)
    username = GLOBAL_PERSONAS[persona]
    csrf = world.login(username)
    table = ACCOUNT_ROUTES if route in ACCOUNT_ROUTES else ADMIN_ROUTES
    expected = table[route][list(GLOBAL_PERSONAS).index(persona)]
    r = global_request(world, *route, csrf, username)
    assert r.status_code == expected, r.text
    if expected == 303 and persona == "anonymous":
        assert r.headers["location"].startswith("/login?next=")
    if expected in (401, 403, 404):
        assert "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("persona", list(AUTOML_PERSONAS))
@pytest.mark.parametrize("route", sorted(SHARING_ROUTES))
def test_sharing_route(make_client, route, persona):
    world = make_world(make_client())
    csrf = world.login(AUTOML_PERSONAS[persona])
    expected = SHARING_ROUTES[route][list(AUTOML_PERSONAS).index(persona)]
    r = sharing_request(world, *route, csrf)
    assert r.status_code == expected, r.text
    if expected == 303 and persona == "anonymous":
        assert r.headers["location"].startswith("/login?next=")
    if expected in (403, 404):
        assert "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("persona", list(AUTOML_PERSONAS))
@pytest.mark.parametrize("route", sorted(MODEL_ROUTES))
def test_model_route(make_client, route, persona):
    world = make_world(make_client())
    csrf = world.login(AUTOML_PERSONAS[persona])
    expected = MODEL_ROUTES[route][list(AUTOML_PERSONAS).index(persona)]
    r = model_request(world, *route, csrf)
    assert r.status_code == expected, r.text
    if expected == 303 and persona == "anonymous":
        assert r.headers["location"].startswith("/login?next=")
    if expected in (403, 404):
        assert "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("route", sorted(MODEL_ROUTES))
def test_model_ids_of_another_project_are_404(make_client, route):
    world = make_world(make_client())
    csrf = world.login("admin")  # may see every project: only the id/project pairing refuses
    method, template = route
    if "{" not in template.removeprefix(P):
        pytest.skip("no object id in the path")
    r = model_request(world, method, template, csrf, objects=world.q)
    assert r.status_code == 404, r.text


@pytest.mark.parametrize("persona", list(MODULE_PERSONAS))
@pytest.mark.parametrize("route", sorted(MODULE_ROUTES))
def test_module_route(make_client, route, persona):
    client = make_client()
    add_user(client, "gv", Role.VIEWER)
    add_user(client, "ed", Role.EDITOR)
    admin = add_user(client, "admin", Role.ADMIN)
    with closing(connect(client)) as conn:
        modules_service.upload_module(conn, client.app.state.storage, admin, "mine", MODULE_SOURCE)
        assert auth_service.list_users(conn)
    username = MODULE_PERSONAS[persona]
    csrf = login(client, username) if username else None
    method, path = route
    path = path.replace("{module_id}", "mine")
    expected = MODULE_ROUTES[route][list(MODULE_PERSONAS).index(persona)]
    token = {"csrf_token": csrf or ""}
    if method == "GET":
        r = client.get(path, follow_redirects=False)
    elif path == "/modules/upload":
        files = {"file": ("m.py", MODULE_SOURCE, "text/x-python")}
        data = token | {"id": "other", "acknowledge": "yes"}
        r = client.post(path, data=data, files=files, follow_redirects=False)
    else:
        r = client.post(path, data=token, follow_redirects=False)
    assert r.status_code == expected, r.text
    if expected in (403, 404):
        assert "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("persona", list(AUTOML_PERSONAS))
@pytest.mark.parametrize("route", sorted(AUTOML_ROUTES))
def test_automl_route(make_client, route, persona):
    world = make_world(make_client())
    csrf = world.login(AUTOML_PERSONAS[persona])
    expected = AUTOML_ROUTES[route][list(AUTOML_PERSONAS).index(persona)]
    r = automl_request(world, *route, csrf)
    assert r.status_code == expected, r.text
    if expected == 303 and persona == "anonymous":
        assert r.headers["location"].startswith("/login?next=")
    if expected in (403, 404):
        assert "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("route", sorted(AUTOML_ROUTES))
def test_automl_ids_of_another_project_are_404(make_client, route):
    world = make_world(make_client())
    csrf = world.login("ed")
    method, template = route
    if "{" not in template.removeprefix(P):
        pytest.skip("no object id in the path")
    r = automl_request(world, method, template, csrf, objects=world.q)
    assert r.status_code == 404, r.text


@pytest.mark.parametrize("persona", list(PERSONAS))
@pytest.mark.parametrize("route", sorted(EASYML_ROUTES))
def test_easyml_route(make_client, route, persona):
    world = make_world(make_client())
    csrf = world.login(PERSONAS[persona])
    expected = EASYML_ROUTES[route][list(PERSONAS).index(persona)]
    r = easyml_request(world, *route, csrf)
    assert r.status_code == expected, r.text
    if expected == 303 and persona == "anonymous":
        assert r.headers["location"].startswith("/login?next=")
    if expected in (403, 404):
        assert "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("route", sorted(EASYML_ROUTES))
def test_ids_of_another_project_are_404(make_client, route):
    """The owner of both projects, with project p in the path and q's objects in it."""
    world = make_world(make_client())
    csrf = world.login("ed")
    method, template = route
    if template == P or template == P + "/upload":
        pytest.skip("no object id in the path")
    r = easyml_request(world, method, template, csrf, objects=world.q)
    assert r.status_code == 404, r.text


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
