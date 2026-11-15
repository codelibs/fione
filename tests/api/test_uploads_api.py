"""The one-time upload URL: ``PUT /api/v1/uploads/{token}`` ingests a CSV as the token's user,
needs no credentials, and answers one 404 for every token it will not use."""

import time
from contextlib import closing

import pytest

from api_helpers import CSV, add_user, connect
from fione.auth.roles import ProjectAccess, Role
from fione.projects import service as projects
from fione.projects import upload_tokens
from fione.projects.service import DatasetType


def new_project(client):
    user = add_user(client, "ed", Role.EDITOR)
    with closing(connect(client)) as conn:
        project = projects.create_project(conn, user, "P")
    return user, project.id


@pytest.fixture
def setup(make_client):
    client = make_client(mcp_enabled=True, mcp_write_enabled=True)
    return (client, *new_project(client))


def make_token(client, user, project_id, *, name="up", type_=DatasetType.TRAIN, **kwargs) -> str:
    with closing(connect(client)) as conn:
        return upload_tokens.create(conn, user.id, project_id, name, type_, **kwargs)


def put(client, token, body=CSV):
    return client.put(f"/api/v1/uploads/{token}", content=body)


def datasets(client, project_id):
    with closing(connect(client)) as conn:
        return projects.list_datasets(conn, project_id)


def test_put_ingests_and_consumes_token(setup):
    client, user, project_id = setup
    token = make_token(client, user, project_id, name="mine", type_=DatasetType.TEST)
    r = put(client, token)
    assert r.status_code == 201, r.text
    record = r.json()
    assert (record["name"], record["type"]) == ("mine", "test")
    assert (record["n_rows"], record["n_cols"]) == (4, 3)
    assert [c["name"] for c in record["schema"]] == ["a", "b", "label"]
    (stored,) = datasets(client, project_id)
    assert stored.id == record["id"] and stored.project_id == project_id


def test_put_twice_is_404(setup):
    client, user, project_id = setup
    token = make_token(client, user, project_id)
    assert put(client, token).status_code == 201
    assert put(client, token).status_code == 404
    assert len(datasets(client, project_id)) == 1


def test_expired_token_is_404(setup):
    client, user, project_id = setup
    token = make_token(client, user, project_id, now=time.time() - 1000)
    assert put(client, token).status_code == 404
    assert datasets(client, project_id) == []


def test_unknown_token_is_404_with_same_body_as_used(setup):
    client, user, project_id = setup
    token = make_token(client, user, project_id)
    put(client, token)
    used = put(client, token)
    unknown = put(client, "no-such-token")
    expired = put(client, make_token(client, user, project_id, now=time.time() - 1000))
    assert used.status_code == unknown.status_code == expired.status_code == 404
    assert used.content == unknown.content == expired.content


def test_failed_ingest_leaves_token_usable(setup):
    client, user, project_id = setup
    token = make_token(client, user, project_id)
    bad = put(client, token, b"a,b\n1,2,3\n")
    assert 400 <= bad.status_code < 500 and bad.status_code != 404
    assert datasets(client, project_id) == []
    assert put(client, token).status_code == 201


def test_write_switch_off_refuses(make_client):
    client = make_client(mcp_enabled=True)
    user, project_id = new_project(client)
    token = make_token(client, user, project_id)
    assert put(client, token).status_code == 404
    assert datasets(client, project_id) == []


def test_mcp_off_refuses(make_client):
    client = make_client(mcp_write_enabled=True)
    user, project_id = new_project(client)
    token = make_token(client, user, project_id)
    assert put(client, token).status_code == 404


def test_refusal_does_not_consume_the_token(make_client):
    client = make_client(mcp_enabled=True)
    user, project_id = new_project(client)
    token = make_token(client, user, project_id)
    assert put(client, token).status_code == 404
    with closing(connect(client)) as conn:
        row = conn.execute("SELECT claimed_at, used_at FROM upload_tokens").fetchone()
    assert tuple(row) == (None, None)


def test_user_who_lost_write_access_refused(setup):
    client, owner, project_id = setup
    other = add_user(client, "vi", Role.EDITOR)
    with closing(connect(client)) as conn:
        projects.share_project(conn, owner, project_id, "vi", ProjectAccess.EDITOR)
    token = make_token(client, other, project_id)
    with closing(connect(client)) as conn:
        assert projects.unshare_project(conn, owner, project_id, "vi")
    assert put(client, token).status_code == 404
    assert datasets(client, project_id) == []


def test_user_demoted_to_viewer_refused(setup):
    client, owner, project_id = setup
    token = make_token(client, owner, project_id)
    with closing(connect(client)) as conn:
        conn.execute("UPDATE users SET role = 'viewer' WHERE id = ?", (owner.id,))
    assert put(client, token).status_code == 404


def test_over_max_upload_bytes_is_413_and_token_survives(make_client):
    client = make_client(mcp_enabled=True, mcp_write_enabled=True, max_upload_bytes=1000)
    user, project_id = new_project(client)
    token = make_token(client, user, project_id)
    r = put(client, token, b"a\n" + b"1\n" * 600)
    assert r.status_code == 413 and r.json()["code"] == "too_large"
    assert datasets(client, project_id) == []
    assert put(client, token, b"a\n1\n").status_code == 201


def test_chunked_body_over_max_upload_bytes_is_413_and_token_survives(make_client):
    # No Content-Length to refuse on: the route counts what it receives.
    client = make_client(mcp_enabled=True, mcp_write_enabled=True, max_upload_bytes=1000)
    user, project_id = new_project(client)
    token = make_token(client, user, project_id)

    def chunks():
        yield b"a\n"
        for _ in range(600):
            yield b"1\n"

    r = client.put(f"/api/v1/uploads/{token}", content=chunks())
    assert r.status_code == 413
    assert r.json() == {"error": "the file exceeds 1000 bytes", "code": "too_large"}
    assert put(client, token, b"a\n1\n").status_code == 201


def test_no_authorization_header_needed(setup):
    client, user, project_id = setup
    token = make_token(client, user, project_id)
    client.cookies.clear()
    r = client.put(f"/api/v1/uploads/{token}", content=CSV)
    assert "authorization" not in r.request.headers
    assert r.status_code == 201


def test_token_stored_hashed(setup):
    client, user, project_id = setup
    token = make_token(client, user, project_id)
    with closing(connect(client)) as conn:
        rows = [tuple(r) for r in conn.execute("SELECT * FROM upload_tokens")]
        columns = [r[1] for r in conn.execute("PRAGMA table_info(upload_tokens)")]
    assert len(rows) == 1 and token not in str(rows)
    assert len(token) >= 22  # 128 bits, URL-safe
    assert len(rows[0][columns.index("token_sha256")]) == 64  # a SHA-256 hex digest


def test_tokens_are_distinct_and_last_15_minutes(setup):
    client, user, project_id = setup
    now = time.time()
    first = make_token(client, user, project_id, now=now)
    assert first != make_token(client, user, project_id, now=now)
    with closing(connect(client)) as conn:
        (expires,) = {r[0] for r in conn.execute("SELECT expires_at FROM upload_tokens")}
    assert expires == pytest.approx(now + 900)


def test_claim_is_single_use_until_released(setup):
    client, user, project_id = setup
    token = make_token(client, user, project_id)
    with closing(connect(client)) as conn:
        claimed = upload_tokens.claim(conn, token)
        assert claimed is not None and upload_tokens.claim(conn, token) is None
        upload_tokens.release(conn, claimed.id)
        assert upload_tokens.claim(conn, token) is not None


def test_deleting_the_project_removes_its_tokens(setup):
    client, user, project_id = setup
    token = make_token(client, user, project_id)
    with closing(connect(client)) as conn:
        projects.delete_project(conn, client.app.state.storage, user, project_id)
    assert put(client, token).status_code == 404
    with closing(connect(client)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM upload_tokens").fetchone()[0] == 0
