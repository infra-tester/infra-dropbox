import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template, redirect

app = Flask(__name__)

DB_PATH = Path.home() / ".lan-dropbox" / "message.db"

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

def fetch_message(limit=None):
    query = "SELECT * FROM message ORDER BY id DESC"
    param = ()
    if limit is not None:
        query += " LIMIT ?"
        param = (limit,)
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(query, param).fetchall()
    return [
        {"id": r[0], "content": r[1], "created_at": r[2]} for r in row
    ]

init_db()

@app.route("/")
def home():
    recent_messages = fetch_message(limit=3)

    return render_template(
        "dashboard.html",
        recent_messages=recent_messages
    )


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
    return jsonify(fetch_message())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
