import sqlite3
import stat
from pathlib import Path

import pytest

from fione import db
from fione.config import Settings, get_settings, load_secret


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
