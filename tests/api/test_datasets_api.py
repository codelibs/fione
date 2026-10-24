"""Datasets over HTTP: upload, limits, download, preview, profiles, cross-project ids."""

import io
import json

import pandas as pd
import pytest
from api_helpers import CSV, add_user, bearer, connect, upload

from fione.api import routes_datasets
from fione.auth.roles import Role


@pytest.fixture
def owner(client):
    user = add_user(client, "owner")
    return bearer(client, user.id)


@pytest.fixture
def project(client, owner):
    r = client.post("/api/v1/projects", json={"name": "P"}, headers=owner)
    return r.json()["id"]


def base(project):
    return f"/api/v1/projects/{project}/datasets"


def strict_json(text):
    def refuse(constant):
        raise AssertionError(f"non-standard JSON constant {constant}")

    return json.loads(text, parse_constant=refuse)


def stored(client, project):
    conn = connect(client)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
    finally:
        conn.close()
    return rows, client.app.state.storage.list(f"projects/{project}/")


def test_upload_list_get_and_delete(client, owner, project):
    r = upload(client, project, headers=owner)
    assert r.status_code == 201
    record = r.json()
    assert record["name"] == "train" and record["type"] == "train"
    assert (record["n_rows"], record["n_cols"]) == (4, 3)
    assert record["schema"] == [
        {"name": "a", "type": "int64"},
        {"name": "b", "type": "string"},
        {"name": "label", "type": "string"},
    ]
    listing = client.get(base(project), headers=owner).json()
    assert listing == [{k: v for k, v in record.items() if k != "schema"}]
    detail = client.get(f"{base(project)}/{record['id']}", headers=owner)
    assert detail.json() == record
    assert "parquet" not in detail.text and "projects/" not in detail.text  # no storage keys
    assert client.delete(f"{base(project)}/{record['id']}", headers=owner).status_code == 204
    assert stored(client, project) == (0, [])
    assert client.get(f"{base(project)}/{record['id']}", headers=owner).status_code == 404


@pytest.mark.parametrize(
    ("data", "fields", "fragment"),
    [
        ({"name": "x", "type": "other"}, True, "type"),
        ({"name": "  ", "type": "train"}, True, "name"),
        ({"name": "x" * 101, "type": "train"}, True, "name"),
        ({"type": "train"}, True, "name"),
        ({"name": "x", "type": "train"}, False, "file"),
    ],
)
def test_upload_form_validation(client, owner, project, data, fields, fragment):
    part = "file" if fields else "other"
    files = {part: ("d.csv", CSV if fields else b"", "text/csv")}
    r = client.post(base(project), data=data, files=files, headers=owner)
    assert r.status_code == 422
    assert fragment in r.json()["error"]
    assert stored(client, project) == (0, [])


def test_upload_requires_multipart(client, owner, project):
    r = client.post(base(project), json={"name": "x"}, headers=owner)
    assert r.status_code == 415


def test_oversize_upload_is_413_and_leaves_nothing(make_client):
    client = make_client(max_upload_bytes=1000)
    headers = bearer(client, add_user(client, "owner").id)
    project = client.post("/api/v1/projects", json={"name": "P"}, headers=headers).json()["id"]
    r = upload(client, project, b"a\n" + b"1\n" * 600, headers=headers)
    assert r.status_code == 413
    assert r.json() == {"error": "the file exceeds 1000 bytes", "code": "too_large"}
    assert stored(client, project) == (0, [])


def test_bodies_far_over_the_limit_are_refused_before_authentication(make_client):
    client = make_client(max_upload_bytes=1000)
    big = b"x" * (2 << 20)
    r = upload(client, "any-project", big)  # anonymous: refused on Content-Length alone
    assert r.status_code == 413 and r.json()["code"] == "too_large"

    def chunks():
        for _ in range(3):
            yield b"x" * (1 << 20)

    r = client.post(
        "/api/v1/auth/login", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 413  # chunked, no Content-Length: counted as it arrives


def test_json_bodies_are_limited_to_one_mib(client):
    r = client.post(
        "/api/v1/auth/login",
        content=b'{"username": "' + b"a" * (1 << 20) + b'"}',
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 413


def test_a_5mb_upload_is_streamed_to_ingest(client, owner, project, monkeypatch):
    reads = []
    real = routes_datasets.ingest_csv

    class Spy:
        def __init__(self, stream):
            self.stream = stream

        def read(self, size=-1):
            reads.append(size)
            return self.stream.read(size)

    def spying(storage, conn, project_id, name, type, stream, **kwargs):
        return real(storage, conn, project_id, name, type, Spy(stream), **kwargs)

    monkeypatch.setattr(routes_datasets, "ingest_csv", spying)
    rows = b"".join(b"%d,%d,label%d\n" % (i, i * 7, i % 3) for i in range(400_000))
    data = b"a,b,c\n" + rows
    assert len(data) > 5 << 20
    r = upload(client, project, data, headers=owner)
    assert r.status_code == 201 and r.json()["n_rows"] == 400_000
    assert len(reads) > 5
    assert all(0 < size <= 1 << 20 for size in reads)  # chunks, never read() of everything


def test_cp932_csv_upload(client, owner, project):
    data = "名前,値\n山田,1\n佐藤,2\n".encode("cp932")
    r = upload(client, project, data, name="日本語", headers=owner)
    assert r.status_code == 201
    assert [c["name"] for c in r.json()["schema"]] == ["名前", "値"]
    preview = client.get(f"{base(project)}/{r.json()['id']}/preview", headers=owner).json()
    assert preview == {"columns": ["名前", "値"], "rows": [["山田", 1], ["佐藤", 2]]}


@pytest.mark.parametrize(
    ("data", "message"),
    [(b"", "empty file"), (b"a,b\n", "no data rows"), (b"\xff\xfe\x00\x81" * 50, "encoding")],
)
def test_invalid_csv_is_422_with_the_reason(client, owner, project, data, message):
    r = upload(client, project, data, headers=owner)
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_csv" and message in r.json()["error"]
    assert stored(client, project) == (0, [])


def test_download_round_trip(client, owner, project):
    data = 'id,name,score\n1,alice,0.5\n2,ボブ,\n3,"c, d",1.25\n'.encode()
    dataset = upload(client, project, data, name="scores", headers=owner).json()
    r = client.get(f"{base(project)}/{dataset['id']}/download", headers=owner)
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/csv; charset=utf-8"
    assert r.headers["content-disposition"] == (
        "attachment; filename=\"scores.csv\"; filename*=UTF-8''scores.csv"
    )
    pd.testing.assert_frame_equal(pd.read_csv(io.BytesIO(r.content)), pd.read_csv(io.BytesIO(data)))


def test_download_filename_is_header_safe(client, owner, project):
    japanese = upload(client, project, name="売上 データ", headers=owner).json()
    r = client.get(f"{base(project)}/{japanese['id']}/download", headers=owner)
    assert r.headers["content-disposition"] == (
        'attachment; filename="dataset.csv"; '
        "filename*=UTF-8''%E5%A3%B2%E4%B8%8A%20%E3%83%87%E3%83%BC%E3%82%BF.csv"
    )
    hostile = 'evil"\r\nSet-Cookie: x=1;\\.csv'
    record = upload(client, project, name=hostile, headers=owner).json()
    assert record["name"] == hostile.strip()
    r = client.get(f"{base(project)}/{record['id']}/download", headers=owner)
    disposition = r.headers["content-disposition"]
    assert disposition.isascii()
    assert not any(c in disposition for c in "\r\n\\")
    assert disposition.count('"') == 2
    assert disposition.startswith('attachment; filename="evil_Set-Cookie_x_1.csv"; filename*=')
    assert "set-cookie" not in r.headers


def test_preview_is_strict_json(client, owner, project):
    data = (
        b"when,amount,flag,label,count\n"
        b"2024-01-01T10:00:00,1.5,true,a,1\n"
        b",,,,\n"
        b"2024-01-03T00:00:00,2.5,false,c,3\n"
    )
    dataset = upload(client, project, data, headers=owner).json()
    r = client.get(f"{base(project)}/{dataset['id']}/preview?rows=2", headers=owner)
    preview = strict_json(r.text)
    assert preview["columns"] == ["when", "amount", "flag", "label", "count"]
    assert preview["rows"] == [
        ["2024-01-01T10:00:00", 1.5, True, "a", 1],
        [None, None, None, None, None],
    ]
    r = client.get(f"{base(project)}/{dataset['id']}/preview", headers=owner)
    assert len(strict_json(r.text)["rows"]) == 3


def test_profile_for_the_ui_includes_top_values(client, owner, project):
    data = b"x,color,label\n" + b"".join(
        b"%d,%s,%s\n" % (i, [b"red", b"blue"][i % 2], [b"yes", b"no"][i % 3 == 0])
        for i in range(60)
    )
    dataset = upload(client, project, data, headers=owner).json()
    r = client.get(f"{base(project)}/{dataset['id']}/profile?target=label", headers=owner)
    profile = strict_json(r.text)
    assert (profile["n_rows"], profile["sample_rows"], profile["n_cols"]) == (60, 60, 3)
    columns = {c["name"]: c for c in profile["columns"]}
    assert columns["color"]["kind"] == "categorical"
    assert sorted(columns["color"]["top_values"]) == [["blue", 30], ["red", 30]]
    assert isinstance(profile["leak_suspects"], list)
    assert client.get(f"{base(project)}/{dataset['id']}/profile", headers=owner).status_code == 200


def test_column_profile(client, owner, project):
    data = b"a/b,c\n" + b"".join(b"%d,%d\n" % (i, i % 2) for i in range(30))
    dataset = upload(client, project, data, headers=owner).json()
    url = f"{base(project)}/{dataset['id']}/columns"
    column = strict_json(client.get(f"{url}/a/b", headers=owner).text)
    assert column["name"] == "a/b" and column["kind"] in ("numeric", "id")
    assert column["missing_rate"] == 0.0
    numeric = strict_json(client.get(f"{url}/c", headers=owner).text)
    assert numeric["histogram"] and numeric["stats"]["mean"] == 0.5
    r = client.get(f"{url}/nope", headers=owner)
    assert r.status_code == 404 and r.json()["error"] == "column not found"


def test_dataset_ids_are_checked_against_the_path_project(client, owner, project):
    other = add_user(client, "other")
    other_headers = bearer(client, other.id)
    theirs = client.post("/api/v1/projects", json={"name": "Q"}, headers=other_headers).json()
    dataset = upload(client, theirs["id"], headers=other_headers).json()
    mine = upload(client, project, headers=owner).json()
    for suffix in ("", "/download", "/preview", "/profile", "/columns/a"):
        r = client.get(f"{base(project)}/{dataset['id']}{suffix}", headers=owner)
        assert r.status_code == 404, suffix
    assert client.delete(f"{base(project)}/{dataset['id']}", headers=owner).status_code == 404
    assert client.get(f"{base(theirs['id'])}/{dataset['id']}", headers=other_headers).is_success
    assert client.get(f"{base(project)}/{mine['id']}", headers=other_headers).status_code == 404


def test_viewer_reads_but_cannot_write(client, owner, project):
    viewer = add_user(client, "viewer", Role.VIEWER)
    client.post(
        f"/api/v1/projects/{project}/share",
        json={"username": "viewer", "access": "editor"},
        headers=owner,
    )
    headers = bearer(client, viewer.id)
    dataset = upload(client, project, headers=owner).json()
    assert client.get(f"{base(project)}/{dataset['id']}/preview", headers=headers).is_success
    assert upload(client, project, headers=headers).status_code == 403
    assert client.delete(f"{base(project)}/{dataset['id']}", headers=headers).status_code == 403
