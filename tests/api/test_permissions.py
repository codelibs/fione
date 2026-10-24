"""The permission matrix: every /api/v1 route x every persona -> the expected status code.

Personas: anonymous; a viewer-role user shared the project as *editor* (the global role caps
it at read); an editor-role member (editor access); the editor-role owner; an admin; an
editor-role non-member; an editor-role user shared the project as *viewer* (the membership
caps it at read). Authenticated personas use bearer tokens (CSRF-exempt): cookie
sessions and CSRF are covered in test_auth_api.py. Each case runs on a fresh copy of one
seeded install, so mutating rows cannot affect each other.
"""

import io
import shutil
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass, field

import pytest
from api_helpers import CSV, PW, make_settings, store_model
from fastapi.testclient import TestClient

from fione import db
from fione.api.app import DB_FILE, create_app
from fione.auth import service as auth
from fione.auth.roles import ProjectAccess, Role
from fione.config import load_secret
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.models.transfer import export_model
from fione.modules import service as modules
from fione.projects import service as projects
from fione.projects.ingest import ingest_csv
from fione.projects.service import DatasetType
from fione.storage import open_storage

PERSONAS = (
    "anonymous",
    "viewer_member",
    "editor_member",
    "owner",
    "admin",
    "outsider",
    "editor_viewer",
)
MAX_UPLOAD = 64 * 1024


def e(*codes: int) -> dict[str, int]:
    assert len(codes) == len(PERSONAS)
    return dict(zip(PERSONAS, codes, strict=True))


@dataclass(frozen=True)
class Row:
    method: str
    route: str  # the route's path template, as registered
    path: str  # formatted with the seed
    expect: dict[str, int]
    json: dict | Callable[[dict], dict] | None = None  # a callable gets the seed values
    upload: bytes | None = None  # a dataset CSV
    form: dict | None = None  # with ``file``: another multipart upload
    file: str | None = None  # the seed value holding the file's bytes
    note: str = ""
    extra: dict = field(default_factory=dict)


P = "/api/v1/projects/{P}"
D = P + "/datasets/{D}"
R_P = "/api/v1/projects/{project_id}"
R_DS = R_P + "/datasets"
R_D = R_DS + "/{dataset_id}"
J = "/api/v1/jobs/{job_id}"
M = "/api/v1/models/{model_id}"
MODULE_SOURCE = b"""
MODULE = {"name": "Add", "kind": "frame", "params": {"type": "object", "properties": {}}}


def run(df, params, ctx):
    return df
"""
READ = e(401, 200, 200, 200, 200, 404, 200)
WRITE_201 = e(401, 403, 201, 201, 201, 404, 403)
ADMIN_ONLY = (401, 403, 403, 403)

ROWS = [
    Row("GET", "/api/v1/health", "/api/v1/health", e(200, 200, 200, 200, 200, 200, 200)),
    Row("GET", "/api/v1/auth/status", "/api/v1/auth/status", e(200, 200, 200, 200, 200, 200, 200)),
    Row(
        "POST",
        "/api/v1/auth/login",
        "/api/v1/auth/login",
        e(401, 401, 401, 401, 401, 401, 401),
        json={"username": "owner", "password": "wrong-password"},
    ),
    Row(
        "POST",
        "/api/v1/auth/first-admin",
        "/api/v1/auth/first-admin",
        e(409, 409, 409, 409, 409, 409, 409),
        json={"username": "x", "password": PW, "setup_token": "t"},
    ),
    Row("POST", "/api/v1/auth/logout", "/api/v1/auth/logout", e(401, 204, 204, 204, 204, 204, 204)),
    Row("GET", "/api/v1/auth/me", "/api/v1/auth/me", e(401, 200, 200, 200, 200, 200, 200)),
    Row(
        "POST",
        "/api/v1/auth/password",
        "/api/v1/auth/password",
        e(401, 403, 403, 403, 403, 403, 403),
        json={"current_password": "wrong-password", "new_password": "new-password-1"},
        note="wrong current password",
    ),
    Row(
        "POST",
        "/api/v1/auth/password",
        "/api/v1/auth/password",
        e(401, 422, 422, 422, 422, 422, 422),
        json={"current_password": PW, "new_password": "short"},
        note="new password too short",
    ),
    Row("GET", "/api/v1/users", "/api/v1/users", e(401, 403, 403, 403, 200, 403, 403)),
    Row(
        "POST",
        "/api/v1/users",
        "/api/v1/users",
        e(401, 403, 403, 403, 201, 403, 403),
        json={"username": "newbie", "password": PW, "role": "editor"},
    ),
    Row(
        "POST",
        "/api/v1/users",
        "/api/v1/users",
        e(401, 403, 403, 403, 422, 403, 403),
        json={"username": "victim", "password": PW, "role": "editor"},
        note="duplicate username",
    ),
    Row(
        "PATCH",
        "/api/v1/users/{user_id}",
        "/api/v1/users/{victim}",
        e(401, 403, 403, 403, 200, 403, 403),
        json={"role": "viewer"},
    ),
    Row(
        "PATCH",
        "/api/v1/users/{user_id}",
        "/api/v1/users/{admin_id}",
        e(401, 403, 403, 403, 409, 403, 403),
        json={"role": "editor"},
        note="demoting the last admin",
    ),
    Row(
        "PATCH",
        "/api/v1/users/{user_id}",
        "/api/v1/users/999999",
        e(401, 403, 403, 403, 404, 403, 403),
        json={"role": "editor"},
    ),
    Row(
        "DELETE",
        "/api/v1/users/{user_id}",
        "/api/v1/users/{victim}",
        e(401, 403, 403, 403, 204, 403, 403),
    ),
    Row(
        "DELETE",
        "/api/v1/users/{user_id}",
        "/api/v1/users/{owner_id}",
        e(401, 403, 403, 403, 409, 403, 403),
        note="owns a project",
    ),
    Row(
        "POST",
        "/api/v1/tokens",
        "/api/v1/tokens",
        e(401, 201, 201, 201, 201, 201, 201),
        json={"name": "ci"},
    ),
    Row("GET", "/api/v1/tokens", "/api/v1/tokens", e(401, 200, 200, 200, 200, 200, 200)),
    Row(
        "GET",
        "/api/v1/tokens",
        "/api/v1/tokens?user_id={owner_id}",
        e(401, 403, 403, 200, 200, 403, 403),
        note="another user's tokens",
    ),
    Row(
        "DELETE",
        "/api/v1/tokens/{token_id}",
        "/api/v1/tokens/{owner_token}",
        e(401, 404, 404, 204, 204, 404, 404),
    ),
    Row("GET", "/api/v1/projects", "/api/v1/projects", e(401, 200, 200, 200, 200, 200, 200)),
    Row(
        "POST",
        "/api/v1/projects",
        "/api/v1/projects",
        e(401, 403, 201, 201, 201, 201, 201),
        json={"name": "新しい project"},
    ),
    Row(
        "POST",
        "/api/v1/projects",
        "/api/v1/projects",
        e(401, 422, 422, 422, 422, 422, 422),
        json={"name": "x", "owner_id": 1},
        note="unknown field",
    ),
    Row("GET", R_P, P, e(401, 200, 200, 200, 200, 404, 200)),
    Row("GET", R_P, "/api/v1/projects/missing", e(401, 404, 404, 404, 404, 404, 404)),
    Row("DELETE", R_P, P, e(401, 403, 403, 204, 204, 404, 403)),
    Row(
        "POST",
        R_P + "/share",
        P + "/share",
        e(401, 403, 403, 204, 204, 404, 403),
        json={"username": "outsider", "access": "viewer"},
    ),
    Row(
        "POST",
        R_P + "/share",
        P + "/share",
        e(401, 403, 403, 422, 422, 404, 403),
        json={"username": "ghost", "access": "viewer"},
        note="unknown user",
    ),
    Row(
        "DELETE",
        R_P + "/share/{username}",
        P + "/share/editor_member",
        e(401, 403, 403, 204, 204, 404, 403),
    ),
    Row(
        "DELETE",
        R_P + "/share/{username}",
        P + "/share/outsider",
        e(401, 403, 403, 404, 404, 404, 403),
        note="not a member",
    ),
    Row("GET", R_DS, P + "/datasets", e(401, 200, 200, 200, 200, 404, 200)),
    Row("POST", R_DS, P + "/datasets", e(401, 403, 201, 201, 201, 404, 403), upload=CSV),
    Row(
        "POST",
        R_DS,
        P + "/datasets",
        e(401, 403, 413, 413, 413, 404, 403),
        upload=b"a,b\n" + b"1,2\n" * (MAX_UPLOAD // 4 + 1),
        note="over max_upload_bytes",
    ),
    Row(
        "POST",
        R_DS,
        P + "/datasets",
        e(401, 403, 422, 422, 422, 404, 403),
        upload=b"\xff\xfe\x00\x01" * 10,
        note="not a CSV",
    ),
    Row("GET", R_D, D, e(401, 200, 200, 200, 200, 404, 200)),
    Row(
        "GET",
        R_D,
        P + "/datasets/{D2}",
        e(401, 404, 404, 404, 404, 404, 404),
        note="dataset of another project",
    ),
    Row("GET", R_D + "/download", D + "/download", e(401, 200, 200, 200, 200, 404, 200)),
    Row("GET", R_D + "/preview", D + "/preview?rows=2", e(401, 200, 200, 200, 200, 404, 200)),
    Row(
        "GET",
        R_D + "/preview",
        D + "/preview?rows=201",
        e(401, 422, 422, 422, 422, 404, 422),
        note="too many rows",
    ),
    Row("GET", R_D + "/profile", D + "/profile?target=label", e(401, 200, 200, 200, 200, 404, 200)),
    Row(
        "GET",
        R_D + "/profile",
        D + "/profile?target=nope",
        e(401, 422, 422, 422, 422, 404, 422),
        note="unknown target",
    ),
    Row(
        "GET",
        R_D + "/columns/{column}",
        D + "/columns/a",
        e(401, 200, 200, 200, 200, 404, 200),
    ),
    Row(
        "GET",
        R_D + "/columns/{column}",
        D + "/columns/nope",
        e(401, 404, 404, 404, 404, 404, 404),
        note="unknown column",
    ),
    Row("DELETE", R_D, D, e(401, 403, 204, 204, 204, 404, 403)),
    # jobs
    Row(
        "POST",
        R_P + "/jobs/automl",
        P + "/jobs/automl",
        WRITE_201,
        json=lambda v: {"dataset_id": v["D"], "config": {"target": "label", "max_models": 1}},
    ),
    Row(
        "POST",
        R_P + "/jobs/automl",
        P + "/jobs/automl",
        e(401, 403, 422, 422, 422, 404, 403),
        json=lambda v: {"dataset_id": v["D"], "config": {"target": "label", "nfolds": 1}},
        note="invalid config",
    ),
    Row(
        "POST",
        R_P + "/jobs/automl",
        P + "/jobs/automl",
        e(401, 403, 404, 404, 404, 404, 403),
        json=lambda v: {"dataset_id": v["D2"], "config": {"target": "label"}},
        note="dataset of another project",
    ),
    Row(
        "POST",
        R_P + "/jobs/batch-predict",
        P + "/jobs/batch-predict",
        WRITE_201,
        json=lambda v: {"model_id": v["M"], "dataset_id": v["D"]},
    ),
    Row(
        "POST",
        R_P + "/jobs/batch-predict",
        P + "/jobs/batch-predict",
        e(401, 403, 404, 404, 404, 404, 403),
        json=lambda v: {"model_id": v["M2"], "dataset_id": v["D"]},
        note="model of another project",
    ),
    Row(
        "POST",
        R_P + "/jobs/module",
        P + "/jobs/module",
        WRITE_201,
        json=lambda v: {"module_id": "sort", "dataset_id": v["D"], "params": {"column": "a"}},
    ),
    Row(
        "POST",
        R_P + "/jobs/module",
        P + "/jobs/module",
        e(401, 403, 422, 422, 422, 404, 403),
        json=lambda v: {"module_id": "nope", "dataset_id": v["D"]},
        note="unknown module",
    ),
    Row("POST", R_P + "/jobs/export", P + "/jobs/export", e(401, 201, 201, 201, 201, 404, 201)),
    Row("GET", "/api/v1/jobs", "/api/v1/jobs", e(401, 200, 200, 200, 200, 200, 200)),
    Row("GET", "/api/v1/jobs", "/api/v1/jobs?project_id={P}", READ, note="one project"),
    Row(
        "DELETE",
        "/api/v1/jobs",
        "/api/v1/jobs?project_id={P}",
        e(401, 403, 200, 200, 200, 404, 403),
    ),
    Row(
        "DELETE",
        "/api/v1/jobs",
        "/api/v1/jobs",
        e(401, 422, 422, 422, 422, 422, 422),
        note="no project_id",
    ),
    Row("GET", J, "/api/v1/jobs/{JD}", READ),
    Row(
        "GET",
        J,
        "/api/v1/jobs/{JQ2}",
        e(401, 404, 404, 404, 200, 200, 404),
        note="job of another project",
    ),
    Row("GET", J, "/api/v1/jobs/999999", e(401, 404, 404, 404, 404, 404, 404), note="missing"),
    Row("GET", J + "/events", "/api/v1/jobs/{JD}/events?after=0", READ),
    Row(
        "GET",
        J + "/events",
        "/api/v1/jobs/{JQ2}/events",
        e(401, 404, 404, 404, 200, 200, 404),
        note="job of another project",
    ),
    Row("POST", J + "/cancel", "/api/v1/jobs/{JQ}/cancel", e(401, 403, 200, 200, 200, 404, 403)),
    Row(
        "POST",
        J + "/cancel",
        "/api/v1/jobs/{JD}/cancel",
        e(401, 403, 409, 409, 409, 404, 403),
        note="already finished",
    ),
    Row("DELETE", J, "/api/v1/jobs/{JD}", e(401, 403, 204, 204, 204, 404, 403)),
    Row(
        "DELETE",
        J,
        "/api/v1/jobs/{JQ}",
        e(401, 403, 409, 409, 409, 404, 403),
        note="not finished",
    ),
    # models
    Row("GET", R_P + "/models", P + "/models", READ),
    Row("GET", M, "/api/v1/models/{M}", READ),
    Row(
        "GET",
        M,
        "/api/v1/models/{M2}",
        e(401, 404, 404, 404, 200, 200, 404),
        note="model of another project",
    ),
    Row("GET", M, "/api/v1/models/999999", e(401, 404, 404, 404, 404, 404, 404), note="missing"),
    Row("GET", M + "/export", "/api/v1/models/{M}/export", READ),
    Row("GET", M + "/serving", "/api/v1/models/{M}/serving", READ),
    Row("GET", M + "/serving/info", "/api/v1/models/{M}/serving/info", READ),
    Row(
        "GET",
        M + "/serving/info",
        "/api/v1/models/{M2}/serving/info",
        e(401, 404, 404, 404, 200, 200, 404),
        note="model of another project",
    ),
    Row("DELETE", M, "/api/v1/models/{M}", e(401, 403, 204, 204, 204, 404, 403)),
    Row(
        "POST",
        R_P + "/models/import",
        P + "/models/import",
        e(*ADMIN_ONLY, 201, 403, 403),
        form={},
        file="export_zip",
    ),
    Row(
        "POST",
        R_P + "/models/import",
        P + "/models/import",
        e(*ADMIN_ONLY, 422, 403, 403),
        form={"trust_foreign": "yes"},
        file="export_zip",
        note="trust_foreign not a boolean",
    ),
    Row("GET", R_P + "/exports/{job_id}", P + "/exports/{JX}", READ),
    Row(
        "GET",
        R_P + "/exports/{job_id}",
        P + "/exports/{JD}",
        e(401, 404, 404, 404, 404, 404, 404),
        note="not an export job",
    ),
    # modules and system
    Row("GET", "/api/v1/modules", "/api/v1/modules", e(401, 200, 200, 200, 200, 200, 200)),
    Row(
        "POST",
        "/api/v1/modules",
        "/api/v1/modules",
        e(*ADMIN_ONLY, 201, 403, 403),
        form={"id": "add_one"},
        file="module_source",
    ),
    Row(
        "POST",
        "/api/v1/modules",
        "/api/v1/modules",
        e(*ADMIN_ONLY, 422, 403, 403),
        form={"id": "seeded"},
        file="module_source",
        note="id taken",
    ),
    Row(
        "DELETE",
        "/api/v1/modules/{module_id}",
        "/api/v1/modules/seeded",
        e(*ADMIN_ONLY, 204, 403, 403),
    ),
    Row(
        "DELETE",
        "/api/v1/modules/{module_id}",
        "/api/v1/modules/sort",
        e(*ADMIN_ONLY, 422, 403, 403),
        note="built-in",
    ),
    Row(
        "DELETE",
        "/api/v1/modules/{module_id}",
        "/api/v1/modules/nothing_here",
        e(*ADMIN_ONLY, 404, 403, 403),
        note="missing",
    ),
    Row(
        "GET",
        "/api/v1/system/status",
        "/api/v1/system/status",
        e(401, 200, 200, 200, 200, 200, 200),
    ),
]


@pytest.fixture(scope="session")
def seed(tmp_path_factory):
    """One seeded install: users; project P (owner, three members) with dataset D, model M, a
    finished job JD, a queued job JQ and a finished export job JX; the outsider's project Q
    with dataset D2, model M2 and job JQ2; an uploaded module ``seeded``. Returns (data dir,
    path values and upload files, persona tokens)."""
    data = tmp_path_factory.mktemp("seed") / "data"
    settings = make_settings(data, max_upload_bytes=MAX_UPLOAD)
    load_secret(settings)
    storage = open_storage(settings)
    with closing(db.connect(data / DB_FILE)) as conn:
        db.migrate(conn)
        users = {
            "admin": auth.create_user(conn, "admin", PW, Role.ADMIN),
            "owner": auth.create_user(conn, "owner", PW, Role.EDITOR),
            "editor_member": auth.create_user(conn, "editor_member", PW, Role.EDITOR),
            "viewer_member": auth.create_user(conn, "viewer_member", PW, Role.VIEWER),
            "outsider": auth.create_user(conn, "outsider", PW, Role.EDITOR),
            "editor_viewer": auth.create_user(conn, "editor_viewer", PW, Role.EDITOR),
        }
        victim = auth.create_user(conn, "victim", PW, Role.EDITOR)
        p = projects.create_project(conn, users["owner"], "P")
        for member in ("editor_member", "viewer_member"):
            projects.share_project(conn, users["owner"], p.id, member, ProjectAccess.EDITOR)
        projects.share_project(conn, users["owner"], p.id, "editor_viewer", ProjectAccess.VIEWER)
        q = projects.create_project(conn, users["outsider"], "Q")
        d = ingest_csv(storage, conn, p.id, "d", DatasetType.TRAIN, io.BytesIO(CSV))
        d2 = ingest_csv(storage, conn, q.id, "d2", DatasetType.TRAIN, io.BytesIO(CSV))
        secret = load_secret(settings)
        m = store_model(conn, storage, secret, p.id)
        m2 = store_model(conn, storage, secret, q.id)
        export_zip = b"".join(export_model(storage, m))
        owner_id = users["owner"].id
        jobs = {
            "JD": finished_job(conn, "automl", p.id, owner_id),
            "JQ": store.enqueue(conn, "automl", p.id, owner_id, {}).id,
            "JX": finished_job(conn, "export_models", p.id, owner_id),
            "JQ2": finished_job(conn, "automl", q.id, users["outsider"].id),
        }
        storage.put(f"projects/{p.id}/exports/{jobs['JX']}.zip", export_zip)
        modules.upload_module(conn, storage, users["admin"], "seeded", MODULE_SOURCE)
        tokens = {}
        for persona, user in users.items():
            record, token = auth.create_token(conn, user.id, "matrix")
            tokens[persona] = (record.id, token)
    values = {
        "P": p.id,
        "D": d.id,
        "D2": d2.id,
        "victim": victim.id,
        "admin_id": users["admin"].id,
        "owner_id": users["owner"].id,
        "owner_token": tokens["owner"][0],
        "M": m.id,
        "M2": m2.id,
        **jobs,
        "export_zip": export_zip,
        "module_source": MODULE_SOURCE,
    }
    return data, values, {k: v[1] for k, v in tokens.items()}


def finished_job(conn, kind, project_id, owner_id) -> int:
    job = store.enqueue(conn, kind, project_id, owner_id, {})
    store.claim_job(conn, job.id, "seed")
    store.finish_job(conn, job.id, JobStatus.DONE)
    return job.id


CASES = [
    pytest.param(
        row, persona, id=f"{row.method} {row.path} {row.note} [{persona}]".replace("  ", " ")
    )
    for row in ROWS
    for persona in PERSONAS
]


@pytest.mark.parametrize(("row", "persona"), CASES)
def test_permission_matrix(row, persona, seed, tmp_path):
    data, values, tokens = seed
    copy = tmp_path / "data"
    shutil.copytree(data, copy)
    app = create_app(make_settings(copy, max_upload_bytes=MAX_UPLOAD), start_runner=False)
    headers = {} if persona == "anonymous" else {"Authorization": f"Bearer {tokens[persona]}"}
    kwargs: dict = {"headers": headers}
    if row.json is not None:
        kwargs["json"] = row.json(values) if callable(row.json) else row.json
    if row.upload is not None:
        kwargs["data"] = {"name": "up", "type": "train"}
        kwargs["files"] = {"file": ("up.csv", row.upload, "text/csv")}
    if row.file is not None:
        kwargs["data"] = row.form
        kwargs["files"] = {"file": ("upload", values[row.file], "application/octet-stream")}
    with TestClient(app) as client:
        r = client.request(row.method, row.path.format(**values), **kwargs)
    assert r.status_code == row.expect[persona], r.text
    if r.status_code >= 400:
        body = r.json()
        assert set(body) == {"error", "code"} and body["error"] and body["code"]


def test_matrix_covers_every_route(tmp_path):
    """Adding a route without a row fails here. Routes are read from the OpenAPI schema
    (FastAPI's public view of them), so every API route must stay in the schema; the
    docs routes (/api/docs, /api/openapi.json) are outside /api/v1 and exempt."""
    app = create_app(make_settings(tmp_path), start_runner=False)
    routes = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }
    assert all(path.startswith("/api/v1/") for _, path in routes)
    covered = {(row.method, row.route) for row in ROWS}
    assert routes == covered
