import hashlib

from flask import Blueprint, current_app, jsonify, request

from app.db import db_connection, fetch_message, insert_message
from app.security import (
    configured_sms_webhook_secret,
    request_json_object,
    require_admin,
    sms_webhook_authorized,
)

messages_bp = Blueprint("messages_api", __name__)


@messages_bp.route("/api/messages")
def get_messages():
    search = (request.args.get("q") or "").strip()
    response = jsonify(fetch_message(search=search or None))
    response.set_etag(hashlib.sha256(response.get_data()).hexdigest())
    response.headers["Cache-Control"] = "no-cache"
    return response.make_conditional(request)


@messages_bp.route("/api/integrations/sms", methods=["POST"])
def receive_sms():
    if not configured_sms_webhook_secret():
        return jsonify({"error": "SMS integration is not configured."}), 503
    if not sms_webhook_authorized():
        return jsonify({"error": "Invalid SMS integration credentials."}), 401

    data = request_json_object()
    sender = data.get("sender")
    message = data.get("message")
    if (
        not isinstance(sender, str)
        or not sender.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in sender)
        or not isinstance(message, str)
        or not message.strip()
    ):
        return jsonify({
            "error": "Provide a non-empty sender and message as strings."
        }), 400

    max_length = current_app.config["MAX_MESSAGE_LENGTH"]
    if len(message) > max_length:
        return jsonify({
            "error": f"The message exceeds the {max_length} character limit."
        }), 400

    insert_message(message, sender=sender)
    return jsonify({"status": "stored"}), 201


@messages_bp.route("/api/messages/<int:message_id>/delete", methods=["POST"])
@require_admin
def delete_message(message_id):
    with db_connection() as conn:
        cursor = conn.execute("DELETE FROM message WHERE id = ?", (message_id,))

    if cursor.rowcount == 0:
        return jsonify({"error": "That message no longer exists."}), 404
    return "", 204


@messages_bp.route("/api/messages/clear", methods=["POST"])
@require_admin
def clear_messages():
    with db_connection() as conn:
        conn.execute("DELETE FROM message")

    return "", 204
