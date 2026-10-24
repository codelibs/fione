import hashlib
import sqlite3
import time

import pytest

from fione import db
from fione.auth import passwords, roles, service
from fione.auth.roles import Role, User

PW = "correct horse"


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "fione.db")
    db.migrate(c)
    yield c
    c.close()


def add_project(conn, project_id, owner_id):
    conn.execute(
        "INSERT INTO projects (id, name, owner_id) VALUES (?, ?, ?)",
        (project_id, project_id, owner_id),
    )


def add_member(conn, project_id, user_id, access):
    conn.execute(
        "INSERT INTO project_members (project_id, user_id, access) VALUES (?, ?, ?)",
        (project_id, user_id, access),
    )


# --- passwords ---------------------------------------------------------------


def test_hash_round_trip_and_format():
    hashed = passwords.hash_password(PW)
    scheme, n, r, p, salt, key = hashed.split("$")
    assert (scheme, int(n), int(r), int(p)) == ("scrypt", 2**15, 8, 1)
    assert salt and key
    assert PW not in hashed
    assert passwords.verify_password(PW, hashed)


def test_verify_wrong_password_false():
    assert not passwords.verify_password("wrong password", passwords.hash_password(PW))


def test_same_password_hashes_differ():
    assert passwords.hash_password(PW) != passwords.hash_password(PW)


@pytest.mark.parametrize(
    "bad", ["", "garbage", "scrypt$x$8$1$aa$bb", "md5$1$2$3$aa$bb", "scrypt$32768$8$1$!!$!!"]
)
def test_verify_malformed_hash_false(bad):
    assert not passwords.verify_password(PW, bad)


def test_short_password_rejected():
    with pytest.raises(ValueError):
        passwords.hash_password("short12")
    passwords.hash_password("eight888")


# --- users -------------------------------------------------------------------


def test_create_user_and_authenticate(conn):
    user = service.create_user(conn, "alice", PW, Role.EDITOR)
    assert user == User(id=user.id, username="alice", role=Role.EDITOR)
    assert service.authenticate(conn, "alice", PW) == user


def test_password_not_stored_in_plaintext(conn):
    service.create_user(conn, "alice", PW, Role.EDITOR)
    stored = conn.execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored.startswith("scrypt$")
    assert PW not in stored


def test_authenticate_wrong_password_none(conn):
    service.create_user(conn, "alice", PW, Role.EDITOR)
    assert service.authenticate(conn, "alice", "wrong password") is None


def test_authenticate_unknown_user_none_and_runs_dummy_verify(conn, monkeypatch):
    calls = []
    real = passwords.verify_password

    def spy(pw, hashed):
        calls.append(hashed)
        return real(pw, hashed)

    monkeypatch.setattr(service, "verify_password", spy)
    assert service.authenticate(conn, "nobody", PW) is None
    assert len(calls) == 1


def test_authenticate_unknown_user_costs_a_hash(conn):
    service.create_user(conn, "alice", PW, Role.EDITOR)
    start = time.perf_counter()
    service.authenticate(conn, "nobody", PW)
    assert time.perf_counter() - start > 0.005


def test_duplicate_username_value_error(conn):
    service.create_user(conn, "alice", PW, Role.EDITOR)
    with pytest.raises(ValueError, match="username already exists"):
        service.create_user(conn, "alice", PW, Role.VIEWER)


@pytest.mark.parametrize(
    "name", ["", "a b", "a/b", "a' OR '1'='1", "x" * 65, "ü", "a\n", "a;DROP TABLE users"]
)
def test_invalid_username_rejected(conn, name):
    with pytest.raises(ValueError):
        service.create_user(conn, name, PW, Role.EDITOR)
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_valid_username_charset(conn):
    service.create_user(conn, "A.b_c-1", PW, Role.EDITOR)
    service.create_user(conn, "x" * 64, PW, Role.EDITOR)


def test_injection_username_authenticate_none(conn):
    service.create_user(conn, "alice", PW, Role.EDITOR)
    assert service.authenticate(conn, "a' OR '1'='1", PW) is None
    assert service.authenticate(conn, "alice' --", PW) is None


def test_create_user_short_password_value_error(conn):
    with pytest.raises(ValueError):
        service.create_user(conn, "alice", "short", Role.EDITOR)


def test_role_check_constraint(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO users (username, password_hash, role) VALUES ('x', 'h', 'root')")


def test_needs_first_admin(conn):
    assert service.needs_first_admin(conn)
    service.create_user(conn, "ed", PW, Role.EDITOR)
    assert service.needs_first_admin(conn)
    service.create_user(conn, "root", PW, Role.ADMIN)
    assert not service.needs_first_admin(conn)


def test_no_default_user_after_migrate(conn):
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


# --- tokens ------------------------------------------------------------------


def test_token_issue_and_lookup(conn):
    user = service.create_user(conn, "alice", PW, Role.EDITOR)
    token = service.issue_token(conn, user.id, "ci")
    assert token.startswith("fione_")
    assert service.user_from_token(conn, token) == user


def test_tokens_are_unique(conn):
    user = service.create_user(conn, "alice", PW, Role.EDITOR)
    assert service.issue_token(conn, user.id, "a") != service.issue_token(conn, user.id, "b")


def test_unknown_token_none(conn):
    service.create_user(conn, "alice", PW, Role.EDITOR)
    assert service.user_from_token(conn, "fione_nope") is None
    assert service.user_from_token(conn, "") is None


def test_revoked_token_rejected(conn):
    user = service.create_user(conn, "alice", PW, Role.EDITOR)
    token = service.issue_token(conn, user.id, "ci")
    token_id = conn.execute("SELECT id FROM api_tokens").fetchone()[0]
    assert service.user_from_token(conn, token) == user
    service.revoke_token(conn, token_id)
    assert service.user_from_token(conn, token) is None
    assert conn.execute("SELECT revoked_at FROM api_tokens").fetchone()[0] is not None


def test_token_plaintext_never_stored(conn):
    user = service.create_user(conn, "alice", PW, Role.EDITOR)
    token = service.issue_token(conn, user.id, "ci")
    row = conn.execute("SELECT * FROM api_tokens").fetchone()
    assert row["token_sha256"] == hashlib.sha256(token.encode()).hexdigest()
    assert all(token not in str(v) for v in tuple(row))
    dump = "\n".join(conn.iterdump())
    assert token not in dump


def test_issue_token_unknown_user_fails(conn):
    with pytest.raises(sqlite3.IntegrityError):
        service.issue_token(conn, 999, "ci")


def test_deleting_user_removes_tokens(conn):
    user = service.create_user(conn, "alice", PW, Role.EDITOR)
    token = service.issue_token(conn, user.id, "ci")
    conn.execute("DELETE FROM users WHERE id=?", (user.id,))
    assert service.user_from_token(conn, token) is None
    assert conn.execute("SELECT COUNT(*) FROM api_tokens").fetchone()[0] == 0


# --- roles -------------------------------------------------------------------


def test_require_admin():
    roles.require_admin(User(1, "a", Role.ADMIN))
    for role in (Role.EDITOR, Role.VIEWER):
        with pytest.raises(PermissionError):
            roles.require_admin(User(2, "b", role))


def test_user_is_frozen():
    with pytest.raises(AttributeError):
        User(1, "a", Role.ADMIN).role = Role.VIEWER  # type: ignore[misc]


def test_can_access_project_rejects_bad_need(conn):
    with pytest.raises(ValueError):
        roles.can_access_project(conn, User(1, "a", Role.ADMIN), "p1", "delete")  # type: ignore[arg-type]


# (case, expected_read, expected_write)
MATRIX = {
    "admin": (True, True),
    "editor-owner": (True, True),
    "editor-member-editor": (True, True),
    "editor-member-viewer": (True, False),
    "editor-nonmember": (False, False),
    "viewer-member": (True, False),
    "viewer-nonmember": (False, False),
    "viewer-member-as-editor": (True, False),
}


@pytest.fixture
def matrix(conn):
    owner = service.create_user(conn, "owner", PW, Role.EDITOR)
    add_project(conn, "p1", owner.id)
    users = {}
    for case in MATRIX:
        role = (
            Role.ADMIN
            if case == "admin"
            else Role.VIEWER
            if case.startswith("viewer")
            else Role.EDITOR
        )
        users[case] = service.create_user(conn, case, PW, role)
    users["editor-owner"] = owner
    add_member(conn, "p1", users["editor-member-editor"].id, "editor")
    add_member(conn, "p1", users["editor-member-viewer"].id, "viewer")
    add_member(conn, "p1", users["viewer-member"].id, "viewer")
    add_member(conn, "p1", users["viewer-member-as-editor"].id, "editor")
    return users


@pytest.mark.parametrize("case", list(MATRIX))
def test_permission_matrix(conn, matrix, case):
    read, write = MATRIX[case]
    assert roles.can_access_project(conn, matrix[case], "p1", "read") is read
    assert roles.can_access_project(conn, matrix[case], "p1", "write") is write


def test_non_admin_unknown_project_denied(conn, matrix):
    assert not roles.can_access_project(conn, matrix["editor-owner"], "missing", "read")


def test_viewer_owner_capped_at_read(conn):
    viewer = service.create_user(conn, "v", PW, Role.VIEWER)
    add_project(conn, "p2", viewer.id)
    assert roles.can_access_project(conn, viewer, "p2", "read")
    assert not roles.can_access_project(conn, viewer, "p2", "write")


def test_deleting_project_removes_members(conn, matrix):
    conn.execute("DELETE FROM projects WHERE id='p1'")
    assert conn.execute("SELECT COUNT(*) FROM project_members").fetchone()[0] == 0


def test_member_access_check_constraint(conn, matrix):
    other = service.create_user(conn, "other", PW, Role.EDITOR)
    with pytest.raises(sqlite3.IntegrityError):
        add_member(conn, "p1", other.id, "owner")


# --- User role coercion -------------------------------------------------------


def test_user_coerces_string_role():
    assert User(1, "x", "viewer").role is Role.VIEWER  # type: ignore[arg-type]


def test_user_invalid_role_value_error():
    with pytest.raises(ValueError):
        User(1, "x", "bogus")  # type: ignore[arg-type]


def test_string_role_viewer_member_editor_write_denied(conn):
    owner = service.create_user(conn, "owner", PW, Role.EDITOR)
    viewer = service.create_user(conn, "vic", PW, Role.VIEWER)
    add_project(conn, "p", owner.id)
    add_member(conn, "p", viewer.id, "editor")
    from_json = User(viewer.id, "vic", "viewer")  # type: ignore[arg-type]
    assert roles.can_access_project(conn, from_json, "p", "read")
    assert not roles.can_access_project(conn, from_json, "p", "write")


def test_string_role_admin_allowed_and_require_admin(conn):
    admin = User(1, "root", "admin")  # type: ignore[arg-type]
    roles.require_admin(admin)
    assert roles.can_access_project(conn, admin, "anything", "write")
    with pytest.raises(PermissionError):
        roles.require_admin(User(2, "e", "editor"))  # type: ignore[arg-type]
