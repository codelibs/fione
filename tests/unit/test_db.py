import sqlite3
import stat
from pathlib import Path

import pytest

from fione import db
from fione.config import Settings, get_settings, load_secret
from fione.models import service as models


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "fione.db")
    yield c
    c.close()


def test_connect_pragmas(conn):
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert conn.row_factory is sqlite3.Row


def test_connect_creates_parent_dir(tmp_path):
    c = db.connect(tmp_path / "nested" / "fione.db")
    c.close()
    assert (tmp_path / "nested" / "fione.db").exists()


def test_migrate_creates_schema_meta_and_returns_version(conn):
    assert db.migrate(conn) == len(db.MIGRATIONS)
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "schema_meta" in tables


def test_migrate_is_idempotent(conn):
    first = db.migrate(conn)
    second = db.migrate(conn)
    assert first == second == len(db.MIGRATIONS)


def test_migrate_applies_only_new_migrations(conn, monkeypatch):
    db.migrate(conn)
    monkeypatch.setattr(db, "MIGRATIONS", [*db.MIGRATIONS, "CREATE TABLE t (id INTEGER)"])
    assert db.migrate(conn) == len(db.MIGRATIONS)
    assert conn.execute("SELECT count(*) FROM t").fetchone()[0] == 0


def test_failed_migration_rolls_back(conn, monkeypatch):
    db.migrate(conn)
    good = len(db.MIGRATIONS)
    monkeypatch.setattr(
        db, "MIGRATIONS", [*db.MIGRATIONS, "CREATE TABLE t (id INTEGER); SELECT * FROM missing"]
    )
    with pytest.raises(sqlite3.Error):
        db.migrate(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == good
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='t'").fetchone() is None


def test_migration_gives_existing_users_no_notebook_permission(conn, monkeypatch):
    before = next(i for i, sql in enumerate(db.MIGRATIONS) if "ADD COLUMN notebook" in sql)
    with monkeypatch.context() as m:
        m.setattr(db, "MIGRATIONS", db.MIGRATIONS[:before])
        db.migrate(conn)
    for name, role in (("a", "admin"), ("e", "editor"), ("v", "viewer")):
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, 'x', ?)", (name, role)
        )
    assert db.migrate(conn) == len(db.MIGRATIONS)
    rows = conn.execute("SELECT username, notebook FROM users ORDER BY id").fetchall()
    assert [tuple(r) for r in rows] == [("a", "none"), ("e", "none"), ("v", "none")]


def test_migration_keeps_existing_models(conn, monkeypatch):
    before = next(i for i, sql in enumerate(db.MIGRATIONS) if "diagnostics_json" in sql)
    with monkeypatch.context() as m:
        m.setattr(db, "MIGRATIONS", db.MIGRATIONS[:before])
        db.migrate(conn)
    conn.execute("INSERT INTO users (username, password_hash, role) VALUES ('u', 'x', 'admin')")
    conn.execute("INSERT INTO projects (id, name, owner_id) VALUES ('p', 'p', 1)")
    conn.execute(
        "INSERT INTO models (project_id, name, task, target, best_model, stop_reason,"
        " storage_prefix, config_json, leaderboard_json, trials_json, metrics_json,"
        " importance_json, created_at)"
        " VALUES ('p', 'old', 'regression', 'y', 'A_1', 'time', 'projects/p/models/a/',"
        " '{}', '[]', '[]', '{}', '{}', 1.0)"
    )
    assert db.migrate(conn) == len(db.MIGRATIONS)
    record = models.get_model(conn, 1)
    assert record.name == "old" and record.diagnostics is None
    assert conn.execute("SELECT diagnostics_json FROM models").fetchone()[0] is None


def test_data_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("FIONE_DATA_DIR", str(tmp_path / "d"))
    s = Settings()
    assert s.data_dir == tmp_path / "d"
    assert s.secret_key_path == tmp_path / "d" / "secret.key"
    assert s.storage_url == (tmp_path / "d" / "objects").as_uri()


def test_settings_defaults(monkeypatch):
    for name in ("DATA_DIR", "STORAGE_URL", "IMAGE_TAG", "MAX_CONCURRENT_TRAIN_JOBS"):
        monkeypatch.delenv(f"FIONE_{name}", raising=False)
    s = Settings()
    assert s.data_dir == Path("/data")
    assert s.image_tag == "dev"
    assert s.max_concurrent_train_jobs == 1


def test_env_overrides_storage_and_image_tag(monkeypatch):
    monkeypatch.setenv("FIONE_STORAGE_URL", "s3://bucket")
    monkeypatch.setenv("FIONE_IMAGE_TAG", "1.2.3")
    s = Settings()
    assert s.storage_url == "s3://bucket"
    assert s.image_tag == "1.2.3"


def test_get_settings_is_cached(monkeypatch, tmp_path):
    get_settings.cache_clear()
    monkeypatch.setenv("FIONE_DATA_DIR", str(tmp_path))
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()


def test_load_secret_creates_then_reuses(tmp_path):
    s = Settings(data_dir=tmp_path / "d")
    first = load_secret(s)
    assert len(first) == 32
    assert stat.S_IMODE(s.secret_key_path.stat().st_mode) == 0o600
    assert load_secret(s) == first


@pytest.mark.parametrize("size", [0, 16, 33])
def test_load_secret_rejects_wrong_length(tmp_path, size):
    s = Settings(data_dir=tmp_path)
    s.secret_key_path.write_bytes(b"x" * size)
    with pytest.raises(RuntimeError, match="corrupt"):
        load_secret(s)
    assert s.secret_key_path.read_bytes() == b"x" * size


def test_load_secret_ignores_stale_temp_file(tmp_path):
    s = Settings(data_dir=tmp_path)
    (tmp_path / ".secret.key.stale.tmp").write_bytes(b"")
    key = load_secret(s)
    assert len(key) == 32
    assert load_secret(s) == key


def test_load_secret_leaves_no_temp_file(tmp_path):
    s = Settings(data_dir=tmp_path)
    load_secret(s)
    assert [p.name for p in tmp_path.iterdir()] == ["secret.key"]


def test_create_secret_loses_race_keeps_winner(tmp_path):
    from fione.config import _create_secret

    path = tmp_path / "secret.key"
    _create_secret(path)
    winner = path.read_bytes()
    _create_secret(path)
    assert path.read_bytes() == winner
    assert [p.name for p in tmp_path.iterdir()] == ["secret.key"]


def test_connect_default_is_bound_to_its_thread(tmp_path):
    import threading

    c = db.connect(tmp_path / "fione.db")
    errors = []
    t = threading.Thread(target=lambda: _try_select(c, errors))
    t.start()
    t.join()
    c.close()
    assert len(errors) == 1 and isinstance(errors[0], sqlite3.ProgrammingError)


def test_connect_check_same_thread_false_allows_other_thread(tmp_path):
    import threading

    c = db.connect(tmp_path / "fione.db", check_same_thread=False)
    errors = []
    t = threading.Thread(target=lambda: _try_select(c, errors))
    t.start()
    t.join()
    c.close()
    assert errors == []


def _try_select(c, errors):
    try:
        c.execute("SELECT 1").fetchone()
    except Exception as e:
        errors.append(e)


def test_immediate_commits_or_rolls_back(conn):
    conn.execute("CREATE TABLE t (x INTEGER)")
    with db.immediate(conn):
        conn.execute("INSERT INTO t VALUES (1)")
    assert not conn.in_transaction
    with pytest.raises(RuntimeError):
        with db.immediate(conn):
            conn.execute("INSERT INTO t VALUES (2)")
            raise RuntimeError("boom")
    assert not conn.in_transaction
    assert [r[0] for r in conn.execute("SELECT x FROM t")] == [1]


def test_api_settings_defaults(tmp_path, monkeypatch):
    for name in ("RUNNER_ENABLED", "COOKIE_SECURE", "SETUP_TOKEN", "TRUST_PROXY"):
        monkeypatch.delenv(f"FIONE_{name}", raising=False)
    s = Settings(data_dir=tmp_path)
    assert s.runner_enabled is True
    assert s.cookie_secure is False
    assert s.session_max_age_secs == 7 * 24 * 3600
    assert (s.login_max_failures, s.login_window_secs) == (5, 900)
    assert s.trust_proxy is False
    assert s.max_upload_bytes == 2**30
    assert s.setup_token is None
    monkeypatch.setenv("FIONE_RUNNER_ENABLED", "false")
    monkeypatch.setenv("FIONE_SETUP_TOKEN", "from-env-0123456789")
    s = Settings(data_dir=tmp_path)
    assert s.runner_enabled is False
    assert s.setup_token == "from-env-0123456789"


def test_create_private_file_is_0600_and_keeps_first(tmp_path):
    from fione.config import create_private_file

    path = tmp_path / "token"
    assert create_private_file(path, b"first") is True
    assert create_private_file(path, b"second") is False
    assert path.read_bytes() == b"first"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in tmp_path.iterdir()] == ["token"]


def test_setup_token_must_be_long_enough(tmp_path):
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="at least 16 characters"):
        Settings(data_dir=tmp_path, setup_token="short-token")
    assert Settings(data_dir=tmp_path, setup_token="").setup_token is None
    assert Settings(data_dir=tmp_path, setup_token="x" * 16).setup_token == "x" * 16


@pytest.mark.parametrize("field", ["login_max_failures", "login_max_failures_per_ip"])
def test_login_limits_must_be_positive(tmp_path, field):
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match=f"{field}[\\s\\S]*greater than or equal to 1"):
        Settings(data_dir=tmp_path, **{field: 0})
    assert getattr(Settings(data_dir=tmp_path, **{field: 1}), field) == 1
