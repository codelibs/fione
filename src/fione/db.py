import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Ordered, append-only: later tasks add their own migration and never edit earlier ones.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin', 'editor', 'viewer')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE api_tokens (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        token_sha256 TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        revoked_at TEXT
    );
    CREATE TABLE projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        owner_id INTEGER NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE project_members (
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        access TEXT NOT NULL CHECK (access IN ('editor', 'viewer')),
        PRIMARY KEY (project_id, user_id)
    );
    """,
    """
    CREATE TABLE datasets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('train', 'test', 'predict')),
        n_rows INTEGER NOT NULL,
        n_cols INTEGER NOT NULL,
        schema_json TEXT NOT NULL,
        storage_key TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX datasets_project_id ON datasets(project_id);
    """,
    """
    CREATE TABLE jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
        owner_id INTEGER NOT NULL REFERENCES users(id),
        status TEXT NOT NULL
            CHECK (status IN ('queued', 'running', 'done', 'failed', 'cancelled')),
        payload_json TEXT NOT NULL,
        result_json TEXT,
        message TEXT,
        created_at REAL NOT NULL,
        started_at REAL,
        finished_at REAL,
        pid INTEGER,
        run_token TEXT,
        cancel_requested INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX jobs_status_created_at ON jobs(status, created_at);
    CREATE INDEX jobs_project_id ON jobs(project_id);
    CREATE TABLE job_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
        ts REAL NOT NULL,
        type TEXT NOT NULL,
        data_json TEXT NOT NULL
    );
    CREATE INDEX job_events_job_id ON job_events(job_id, id);
    """,
    """
    CREATE TABLE models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
        job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
        name TEXT NOT NULL,
        task TEXT NOT NULL,
        target TEXT NOT NULL,
        best_model TEXT NOT NULL,
        stop_reason TEXT NOT NULL,
        storage_prefix TEXT NOT NULL,
        trusted INTEGER NOT NULL DEFAULT 1,
        config_json TEXT NOT NULL,
        leaderboard_json TEXT NOT NULL,
        trials_json TEXT NOT NULL,
        metrics_json TEXT NOT NULL,
        importance_json TEXT NOT NULL,
        created_at REAL NOT NULL
    );
    CREATE INDEX models_project_id_created_at ON models(project_id, created_at);
    """,
    """
    CREATE TABLE modules (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        kind TEXT NOT NULL,
        params_json TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,
        uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at REAL NOT NULL
    );
    CREATE TABLE module_models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        module_id TEXT NOT NULL,
        name TEXT NOT NULL,
        state_key TEXT NOT NULL,
        source_dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
        created_at REAL NOT NULL
    );
    CREATE INDEX module_models_project_id ON module_models(project_id);
    """,
    """
    ALTER TABLE models ADD COLUMN diagnostics_json TEXT;
    """,
    """
    CREATE TABLE model_explanations (
        model_id INTEGER PRIMARY KEY REFERENCES models(id) ON DELETE CASCADE,
        job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
        dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
        payload_json TEXT NOT NULL,
        created_at REAL NOT NULL
    );
    """,
    """
    ALTER TABLE api_tokens ADD COLUMN expires_at TEXT;
    ALTER TABLE api_tokens ADD COLUMN scope TEXT NOT NULL DEFAULT 'full'
        CHECK (scope IN ('full', 'notebook'));
    """,
    """
    ALTER TABLE users ADD COLUMN notebook TEXT NOT NULL DEFAULT 'none'
        CHECK (notebook IN ('none', 'run'));
    """,
    """
    CREATE TABLE notebook_sessions (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        nonce TEXT NOT NULL,
        token_id INTEGER NOT NULL REFERENCES api_tokens(id) ON DELETE CASCADE,
        started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE notebook_pending_stops (
        user_id INTEGER PRIMARY KEY,
        purge INTEGER NOT NULL DEFAULT 0,
        since TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX conversations_project_user ON conversations(project_id, user_id);
    CREATE INDEX conversations_user ON conversations(user_id);
    CREATE TABLE chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
        content TEXT NOT NULL DEFAULT '',
        tool_calls_json TEXT,
        tool_call_id TEXT,
        tool_name TEXT,
        state TEXT NOT NULL DEFAULT 'done'
            CHECK (state IN ('queued', 'running', 'done', 'failed', 'cancelled')),
        error_code TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX chat_messages_conversation ON chat_messages(conversation_id, id);
    CREATE TABLE chat_proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL UNIQUE REFERENCES chat_messages(id) ON DELETE CASCADE,
        conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
        config_json TEXT NOT NULL,
        details_json TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'pending'
            CHECK (state IN ('pending', 'confirmed', 'dismissed')),
        job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
        decided_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        decided_at TEXT
    );
    CREATE INDEX chat_proposals_conversation ON chat_proposals(conversation_id);
    CREATE TABLE llm_sample_optins (
        base_url TEXT PRIMARY KEY,
        enabled_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        enabled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
]


def connect(path: Path, *, check_same_thread: bool = True) -> sqlite3.Connection:
    """Open the metadata database.

    Create one connection per thread/request rather than sharing one across FastAPI worker
    threads. ``check_same_thread=False`` is only for a connection used by one request at a
    time that FastAPI may hand from thread to thread (a dependency and its endpoint can run
    in different threadpool threads).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def immediate(conn: sqlite3.Connection) -> Iterator[None]:
    """A ``BEGIN IMMEDIATE`` transaction: committed on exit, rolled back on any exception.

    The write lock is taken up front, so a check and the write it guards cannot interleave
    with another connection's.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


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
