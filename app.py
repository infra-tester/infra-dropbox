import hmac
import logging
import os
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
)
from werkzeug.utils import secure_filename

app = Flask(__name__)

DATA_DIR = Path.home() / ".lan-dropbox"
DB_PATH = DATA_DIR / "message.db"
UPLOAD_DIR = DATA_DIR / "uploads"
MAX_FILE_SIZE = 100 * 1024 * 1024
MAX_STORAGE_SIZE = 2 * 1024 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".docx", ".xlsx",
    ".pptx", ".txt", ".md", ".csv", ".zip",
}

app.config.update(
    DATABASE_PATH=DB_PATH,
    UPLOAD_DIR=UPLOAD_DIR,
    MAX_FILE_SIZE=MAX_FILE_SIZE,
    MAX_STORAGE_SIZE=MAX_STORAGE_SIZE,
    MAX_CONTENT_LENGTH=MAX_FILE_SIZE + 1024 * 1024,
)

# Set ADMIN_PASSWORD in the environment to enable administrator actions.
# When it is empty, deletion stays disabled instead of falling open.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


def database_path() -> Path:
    return Path(app.config["DATABASE_PATH"])


def upload_directory() -> Path:
    return Path(app.config["UPLOAD_DIR"])


@contextmanager
def db_connection(timeout=5):
    conn = sqlite3.connect(database_path(), timeout=timeout)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    database_path().parent.mkdir(parents=True, exist_ok=True)
    upload_directory().mkdir(parents=True, exist_ok=True)
    with db_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS message(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL)"""
        )
        conn.execute("""
        CREATE TABLE IF NOT EXISTS shared_file(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        stored_name TEXT NOT NULL UNIQUE,
        size INTEGER NOT NULL,
        created_at TEXT NOT NULL)"""
        )

def insert_message(content: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with db_connection() as conn:
        conn.execute("INSERT INTO message (content, created_at) VALUES (?, ?)",
        (content, now)
        )

def fetch_message(limit=None, search=None):
    query = "SELECT * FROM message"
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

    return [
        {"id": r[0], "content": r[1], "created_at": r[2]} for r in rows
    ]


def admin_authorized(password) -> bool:
    if not ADMIN_PASSWORD or not isinstance(password, str) or not password:
        return False
    return hmac.compare_digest(password, ADMIN_PASSWORD)


def request_json_object():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def admin_denied():
    if not ADMIN_PASSWORD:
        return jsonify(
            {"error": "Administrator deletion is not configured on this server."}
        ), 503
    return jsonify({"error": "Incorrect administrator password."}), 401


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


init_db()

@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/send", methods=["POST"])
def send_message():
    message = request.form.get("message")

    if message and message.strip():
        insert_message(message.strip())
    return redirect("/")


@app.route("/messages")
def messages_page():
    return render_template("messages.html")


@app.route("/files")
def files_page():
    return render_template("files.html")


@app.route("/api/messages")
def get_messages():
    search = (request.args.get("q") or "").strip()
    return jsonify(fetch_message(search=search or None))


@app.route("/api/admin/verify", methods=["POST"])
def verify_admin():
    data = request_json_object()

    if not admin_authorized(data.get("password")):
        return admin_denied()
    return "", 204


@app.route("/api/messages/<int:message_id>/delete", methods=["POST"])
def delete_message(message_id):
    data = request_json_object()

    if not admin_authorized(data.get("password")):
        return admin_denied()

    with db_connection() as conn:
        cursor = conn.execute("DELETE FROM message WHERE id = ?", (message_id,))

    if cursor.rowcount == 0:
        return jsonify({"error": "That message no longer exists."}), 404
    return "", 204


@app.route("/api/messages/clear", methods=["POST"])
def clear_messages():
    data = request_json_object()

    if not admin_authorized(data.get("password")):
        return admin_denied()

    with db_connection() as conn:
        conn.execute("DELETE FROM message")

    return "", 204


@app.route("/api/files")
def get_files():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, filename, size, created_at FROM shared_file ORDER BY id DESC"
        ).fetchall()
        used_bytes = storage_usage(conn)

    return jsonify({
        "files": [file_metadata(row) for row in rows],
        "used_bytes": used_bytes,
        "max_bytes": app.config["MAX_STORAGE_SIZE"],
        "max_file_bytes": app.config["MAX_FILE_SIZE"],
    })


@app.route("/api/files", methods=["POST"])
def upload_file():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Choose a file to upload."}), 400

    raw_filename = uploaded.filename.replace("\\", "/").rsplit("/", 1)[-1]
    extension = Path(raw_filename).suffix.casefold()
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "This file type is not allowed."}), 415

    filename = secure_filename(raw_filename)
    if not filename:
        return jsonify({"error": "The filename is not valid."}), 400

    directory = upload_directory()
    directory.mkdir(parents=True, exist_ok=True)
    temp_path = None
    stored_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=directory, prefix=".upload-", delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            size = 0
            while chunk := uploaded.stream.read(1024 * 1024):
                size += len(chunk)
                if size > app.config["MAX_FILE_SIZE"]:
                    return jsonify({
                        "error": "The file exceeds the 100 MB per-file limit."
                    }), 413
                temp_file.write(chunk)

        stored_name = f"{uuid.uuid4().hex}{extension}"
        stored_path = directory / stored_name
        created_at = datetime.now(timezone.utc).isoformat()

        with db_connection(timeout=30) as conn:
            conn.execute("BEGIN IMMEDIATE")
            used_bytes = storage_usage(conn)
            if used_bytes + size > app.config["MAX_STORAGE_SIZE"]:
                return jsonify({
                    "error": "This upload would exceed the 2 GB shared storage limit."
                }), 413

            os.replace(temp_path, stored_path)
            temp_path = None
            conn.execute(
                """INSERT INTO shared_file (filename, stored_name, size, created_at)
                   VALUES (?, ?, ?, ?)""",
                (filename, stored_name, size, created_at),
            )

        return jsonify({
            "file": {
                "filename": filename,
                "size": size,
                "created_at": created_at,
            }
        }), 201
    except (OSError, sqlite3.Error):
        logging.exception("File upload failed")
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        return jsonify({"error": "The file could not be saved. Please try again."}), 500
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({
        "error": "The upload request is too large. The per-file limit is 100 MB."
    }), 413


@app.route("/api/files/<int:file_id>/download")
def download_file(file_id):
    with db_connection() as conn:
        row = conn.execute(
            "SELECT filename, stored_name FROM shared_file WHERE id = ?",
            (file_id,),
        ).fetchone()

    if row is None:
        abort(404)
    filename, stored_name = row
    if Path(stored_name).name != stored_name:
        abort(404)

    return send_from_directory(
        upload_directory(),
        stored_name,
        as_attachment=True,
        download_name=filename,
        mimetype="application/octet-stream",
    )


@app.route("/api/files/<int:file_id>/delete", methods=["POST"])
def delete_file(file_id):
    data = request_json_object()
    if not admin_authorized(data.get("password")):
        return admin_denied()

    directory = upload_directory()
    quarantined_path = None
    stored_path = None
    conn = sqlite3.connect(database_path(), timeout=30)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT stored_name FROM shared_file WHERE id = ?", (file_id,)
        ).fetchone()
        if row is None:
            conn.rollback()
            return jsonify({"error": "That file no longer exists."}), 404

        stored_name = row[0]
        if Path(stored_name).name != stored_name:
            conn.rollback()
            return jsonify({"error": "The stored file reference is invalid."}), 500

        stored_path = directory / stored_name
        quarantined_path = directory / f".delete-{uuid.uuid4().hex}"
        os.replace(stored_path, quarantined_path)
        conn.execute("DELETE FROM shared_file WHERE id = ?", (file_id,))
        conn.commit()
        quarantined_path.unlink()
        return "", 204
    except (OSError, sqlite3.Error):
        conn.rollback()
        if quarantined_path is not None and quarantined_path.exists():
            try:
                os.replace(quarantined_path, stored_path)
            except OSError:
                logging.exception("Could not restore file after failed deletion")
        logging.exception("File deletion failed")
        return jsonify({"error": "The file could not be deleted. Please try again."}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
