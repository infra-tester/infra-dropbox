import hmac

from flask import current_app, jsonify, request


def configured_admin_password() -> str:
    return current_app.config.get("ADMIN_PASSWORD", "")


def admin_authorized(password) -> bool:
    secret = configured_admin_password()
    if not secret or not isinstance(password, str) or not password:
        return False
    return hmac.compare_digest(password, secret)


def request_json_object():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def admin_denied():
    if not configured_admin_password():
        return jsonify(
            {"error": "Administrator deletion is not configured on this server."}
        ), 503
    return jsonify({"error": "Incorrect administrator password."}), 401
