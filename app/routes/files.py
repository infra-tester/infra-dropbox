import logging
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    request,
    send_from_directory,
)
from werkzeug.utils import secure_filename

from app.config import ALLOWED_EXTENSIONS
from app.db import (
    db_connection,
    file_metadata,
    storage_usage,
    upload_directory,
)
from app.security import admin_denied, admin_authorized, request_json_object

files_bp = Blueprint("files_api", __name__)


@files_bp.route("/api/files")
def get_files():
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, filename, size, created_at FROM shared_file ORDER BY id DESC"
        ).fetchall()
        used_bytes = storage_usage(conn)

    return jsonify({
        "files": [file_metadata(row) for row in rows],
        "used_bytes": used_bytes,
        "max_bytes": current_app.config["MAX_STORAGE_SIZE"],
        "max_file_bytes": current_app.config["MAX_FILE_SIZE"],
    })


@files_bp.route("/api/files", methods=["POST"])
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
                if size > current_app.config["MAX_FILE_SIZE"]:
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
            if used_bytes + size > current_app.config["MAX_STORAGE_SIZE"]:
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


@files_bp.route("/api/files/<int:file_id>/download")
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


@files_bp.route("/api/files/<int:file_id>/delete", methods=["POST"])
def delete_file(file_id):
    data = request_json_object()
    if not admin_authorized(data.get("password")):
        return admin_denied()

    directory = upload_directory()
    quarantined_path = None
    stored_path = None
    conn = sqlite3.connect(
        Path(current_app.config["DATABASE_PATH"]), timeout=30
    )
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
