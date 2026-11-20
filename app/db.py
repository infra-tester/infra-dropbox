import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app


def database_path() -> Path:
    return Path(current_app.config["DATABASE_PATH"])


def upload_directory() -> Path:
    return Path(current_app.config["UPLOAD_DIR"])


@contextmanager
def db_connection(timeout=5):
    conn = sqlite3.connect(database_path(), timeout=timeout)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(application):
    with application.app_context():
        database_path().parent.mkdir(parents=True, exist_ok=True)
        upload_directory().mkdir(parents=True, exist_ok=True)
        with db_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS message(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            sender TEXT)"""
            )
            message_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(message)")
            }
            if "sender" not in message_columns:
                conn.execute("ALTER TABLE message ADD COLUMN sender TEXT")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS shared_file(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            stored_name TEXT NOT NULL UNIQUE,
            size INTEGER NOT NULL,
            created_at TEXT NOT NULL)"""
            )
            conn.execute("""
            CREATE TABLE IF NOT EXISTS setting(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL)"""
            )


def insert_message(content: str, sender: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO message (content, created_at, sender) VALUES (?, ?, ?)",
            (content, now, sender),
        )


def fetch_message(limit=None, search=None):
    query = "SELECT id, content, created_at, sender FROM message"
    params = []

    if search:
        escaped = (
            search.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        query += " WHERE content LIKE ? ESCAPE '\\'"
        params.append(f"%{escaped}%")

    query += " ORDER BY id DESC"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    with db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    messages = []
    for row in rows:
        message = {"id": row[0], "content": row[1], "created_at": row[2]}
        if row[3] is not None:
            message["sender"] = row[3]
        messages.append(message)
    return messages


def file_metadata(row):
    return {
        "id": row[0],
        "filename": row[1],
        "size": row[2],
        "created_at": row[3],
    }


def storage_usage(conn) -> int:
    row = conn.execute("SELECT COALESCE(SUM(size), 0) FROM shared_file").fetchone()
    return row[0]
