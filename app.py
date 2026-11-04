import hmac
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template, redirect

app = Flask(__name__)

DB_PATH = Path.home() / ".lan-dropbox" / "message.db"

# Set ADMIN_PASSWORD in the environment to enable administrator actions.
# When it is empty, deletion stays disabled instead of falling open.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS message(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL)"""
        )

def insert_message(content: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
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

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {"id": r[0], "content": r[1], "created_at": r[2]} for r in rows
    ]


def admin_authorized(password) -> bool:
    if not ADMIN_PASSWORD or not password:
        return False
    return hmac.compare_digest(password, ADMIN_PASSWORD)


def admin_denied():
    if not ADMIN_PASSWORD:
        return jsonify(
            {"error": "Administrator deletion is not configured on this server."}
        ), 503
    return jsonify({"error": "Incorrect administrator password."}), 401

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


@app.route("/api/messages")
def get_messages():
    search = (request.args.get("q") or "").strip()
    return jsonify(fetch_message(search=search or None))


@app.route("/api/admin/verify", methods=["POST"])
def verify_admin():
    data = request.get_json(silent=True) or {}

    if not admin_authorized(data.get("password")):
        return admin_denied()
    return "", 204


@app.route("/api/messages/<int:message_id>/delete", methods=["POST"])
def delete_message(message_id):
    data = request.get_json(silent=True) or {}

    if not admin_authorized(data.get("password")):
        return admin_denied()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM message WHERE id = ?", (message_id,))

    if cursor.rowcount == 0:
        return jsonify({"error": "That message no longer exists."}), 404
    return "", 204


@app.route("/api/messages/clear", methods=["POST"])
def clear_messages():
    data = request.get_json(silent=True) or {}

    if not admin_authorized(data.get("password")):
        return admin_denied()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM message")

    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
