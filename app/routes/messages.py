from flask import Blueprint, jsonify, request

from app.db import db_connection, fetch_message
from app.security import admin_denied, admin_authorized, request_json_object

messages_bp = Blueprint("messages_api", __name__)


@messages_bp.route("/api/messages")
def get_messages():
    search = (request.args.get("q") or "").strip()
    return jsonify(fetch_message(search=search or None))


@messages_bp.route("/api/messages/<int:message_id>/delete", methods=["POST"])
def delete_message(message_id):
    data = request_json_object()

    if not admin_authorized(data.get("password")):
        return admin_denied()

    with db_connection() as conn:
        cursor = conn.execute("DELETE FROM message WHERE id = ?", (message_id,))

    if cursor.rowcount == 0:
        return jsonify({"error": "That message no longer exists."}), 404
    return "", 204


@messages_bp.route("/api/messages/clear", methods=["POST"])
def clear_messages():
    data = request_json_object()

    if not admin_authorized(data.get("password")):
        return admin_denied()

    with db_connection() as conn:
        conn.execute("DELETE FROM message")

    return "", 204
