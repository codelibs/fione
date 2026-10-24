import pytest

from fione import db
from fione.auth import roles
from fione.auth import service as auth
from fione.auth.roles import ProjectAccess, Role
from fione.projects import service
from fione.projects.service import ProjectNotFound
from fione.storage import LocalStorage


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "fione.db")
    db.migrate(c)
    yield c
    c.close()


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "storage")


@pytest.fixture
def owner(conn):
    return auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR)


@pytest.fixture
def other(conn):
    return auth.create_user(conn, "other", "pw-other-1", Role.EDITOR)


@pytest.fixture
def admin(conn):
    return auth.create_user(conn, "root", "pw-admin-1", Role.ADMIN)


def test_create_project_returns_record(conn, owner):
    p = service.create_project(conn, owner, "  Sales Forecast  ")
    assert p.name == "Sales Forecast"
    assert p.owner_id == owner.id
    assert p.created_at
    assert p.id.startswith("sales-forecast-")
    assert len(p.id) == len("sales-forecast-") + 6
    assert service.list_projects(conn, owner) == [p]


def test_project_ids_are_unique_for_same_name(conn, owner):
    a = service.create_project(conn, owner, "demo")
    b = service.create_project(conn, owner, "demo")
    assert a.id != b.id


@pytest.mark.parametrize("name", ["../../etc", "a\\b/c d", "..", "x" * 100])
def test_project_id_is_path_safe(conn, owner, name):
    p = service.create_project(conn, owner, name)
    for bad in ("/", "\\", "..", " ", "\t"):
        assert bad not in p.id
    assert p.name == name.strip()


def test_traversal_name_slug(conn, owner):
    assert service.create_project(conn, owner, "../../etc").id.startswith("etc-")


def test_japanese_name_keeps_display_name(conn, owner):
    p = service.create_project(conn, owner, "売上予測")
    assert p.name == "売上予測"
    assert p.id.startswith("project-")
    assert p.id.isascii()
    assert service.list_projects(conn, owner)[0].name == "売上予測"


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_create_project_rejects_bad_names(conn, owner, name):
    with pytest.raises(ValueError):
        service.create_project(conn, owner, name)


def test_global_viewer_cannot_create_project(conn):
    viewer = auth.create_user(conn, "view", "pw-view-1", Role.VIEWER)
    with pytest.raises(PermissionError):
        service.create_project(conn, viewer, "nope")


def test_list_projects_scopes_by_user(conn, owner, other, admin):
    mine = service.create_project(conn, owner, "mine")
    theirs = service.create_project(conn, other, "theirs")
    shared = service.create_project(conn, other, "shared")
    service.share_project(conn, other, shared.id, owner.username, ProjectAccess.VIEWER)
    assert {p.id for p in service.list_projects(conn, owner)} == {mine.id, shared.id}
    assert {p.id for p in service.list_projects(conn, other)} == {theirs.id, shared.id}
    assert {p.id for p in service.list_projects(conn, admin)} == {mine.id, theirs.id, shared.id}


def test_share_gives_viewer_read_but_not_write(conn, owner, other):
    p = service.create_project(conn, owner, "shared")
    assert not roles.can_access_project(conn, other, p.id, "read")
    service.share_project(conn, owner, p.id, other.username, ProjectAccess.VIEWER)
    assert roles.can_access_project(conn, other, p.id, "read")
    assert not roles.can_access_project(conn, other, p.id, "write")


def test_share_upserts_membership(conn, owner, other):
    p = service.create_project(conn, owner, "shared")
    service.share_project(conn, owner, p.id, other.username, ProjectAccess.VIEWER)
    service.share_project(conn, owner, p.id, other.username, ProjectAccess.EDITOR)
    assert roles.can_access_project(conn, other, p.id, "write")
    rows = conn.execute("SELECT * FROM project_members WHERE project_id = ?", (p.id,)).fetchall()
    assert len(rows) == 1


def test_share_requires_owner_or_admin(conn, owner, other, admin):
    p = service.create_project(conn, owner, "shared")
    service.share_project(conn, owner, p.id, other.username, ProjectAccess.EDITOR)
    with pytest.raises(PermissionError):
        service.share_project(conn, other, p.id, other.username, ProjectAccess.VIEWER)
    service.share_project(conn, admin, p.id, other.username, ProjectAccess.VIEWER)


def test_share_rejects_unknown_user_and_owner_access(conn, owner, other):
    p = service.create_project(conn, owner, "shared")
    with pytest.raises(ValueError):
        service.share_project(conn, owner, p.id, "ghost", ProjectAccess.VIEWER)
    with pytest.raises(ValueError):
        service.share_project(conn, owner, p.id, other.username, ProjectAccess.OWNER)


def test_missing_project_raises(conn, storage, owner, admin):
    with pytest.raises(ProjectNotFound):
        service.delete_project(conn, storage, admin, "nope")
    with pytest.raises(ProjectNotFound):
        service.share_project(conn, admin, "nope", owner.username, ProjectAccess.VIEWER)
    with pytest.raises(ProjectNotFound):
        service.list_datasets(conn, "nope")


def test_delete_project_requires_owner_or_admin(conn, storage, owner, other, admin):
    p = service.create_project(conn, owner, "doomed")
    service.share_project(conn, owner, p.id, other.username, ProjectAccess.EDITOR)
    with pytest.raises(PermissionError):
        service.delete_project(conn, storage, other, p.id)
    service.delete_project(conn, storage, admin, p.id)
    assert service.list_projects(conn, owner) == []


def test_delete_project_removes_objects_rows_and_datasets(conn, storage, owner):
    p = service.create_project(conn, owner, "doomed")
    keep = service.create_project(conn, owner, "keep")
    storage.put(f"projects/{p.id}/datasets/1/data.parquet", b"x")
    storage.put(f"projects/{p.id}/models/m/model.bin", b"y")
    storage.put(f"projects/{keep.id}/datasets/1/data.parquet", b"z")
    ds = service.add_dataset(
        conn,
        p.id,
        "d",
        service.DatasetType.TRAIN,
        1,
        1,
        [("a", "int64")],
        f"projects/{p.id}/datasets/1/data.parquet",
    )
    service.share_project(
        conn,
        owner,
        p.id,
        auth.create_user(conn, "m", "pw-member-1", Role.EDITOR).username,
        ProjectAccess.VIEWER,
    )
    service.delete_project(conn, storage, owner, p.id)
    assert storage.list(f"projects/{p.id}/") == []
    assert storage.list(f"projects/{keep.id}/") == [f"projects/{keep.id}/datasets/1/data.parquet"]
    assert conn.execute("SELECT COUNT(*) FROM datasets WHERE id = ?", (ds.id,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM project_members").fetchone()[0] == 0
    assert [q.id for q in service.list_projects(conn, owner)] == [keep.id]


def test_dataset_records_roundtrip(conn, storage, owner):
    p = service.create_project(conn, owner, "p")
    key = f"projects/{p.id}/datasets/7/data.parquet"
    ds = service.add_dataset(
        conn,
        p.id,
        "train.csv",
        service.DatasetType.TEST,
        3,
        2,
        [("a", "int64"), ("b", "string")],
        key,
    )
    assert service.get_dataset(conn, ds.id) == ds
    assert ds.schema == [("a", "int64"), ("b", "string")]
    assert ds.type == service.DatasetType.TEST
    assert service.list_datasets(conn, p.id) == [ds]
    storage.put(key, b"x")
    service.delete_dataset(conn, storage, ds.id)
    assert service.list_datasets(conn, p.id) == []
    assert not storage.exists(key)
    with pytest.raises(service.DatasetNotFound):
        service.get_dataset(conn, ds.id)
    with pytest.raises(service.DatasetNotFound):
        service.delete_dataset(conn, storage, ds.id)
