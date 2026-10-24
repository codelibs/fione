import sqlite3
from pathlib import Path

# Ordered, append-only: later tasks add their own migration and never edit earlier ones.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
]


def connect(path: Path) -> sqlite3.Connection:
    """Open the metadata database.

    Connections use sqlite3's default ``check_same_thread=True``: create one per
    thread/request rather than sharing a connection across FastAPI worker threads.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def migrate(conn: sqlite3.Connection) -> int:
    """Apply pending MIGRATIONS in order and return the schema version.

    The version is kept in ``PRAGMA user_version``; each migration and its version
    bump commit together or not at all.
    """
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for number, sql in enumerate(MIGRATIONS[version:], start=version + 1):
        try:
            body = sql.strip().rstrip(";")
            conn.executescript(f"BEGIN;\n{body};\nPRAGMA user_version={number};\nCOMMIT;")
        except sqlite3.Error:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    return len(MIGRATIONS)
