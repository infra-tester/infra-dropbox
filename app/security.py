import hmac
from functools import wraps

from flask import current_app, jsonify, request, session


def configured_admin_password() -> str:
    return current_app.config.get("ADMIN_PASSWORD", "")


def admin_authorized(password) -> bool:
    secret = configured_admin_password()
    if not secret or not isinstance(password, str) or not password:
        return False
    return hmac.compare_digest(password, secret)


def require_admin(view):
    """Reject the request unless this session is signed in as administrator."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not configured_admin_password():
            return admin_denied()
        if not session.get("admin"):
            return jsonify({"error": "Administrator sign-in required."}), 401
        return view(*args, **kwargs)

    return wrapped


def configured_sms_webhook_secret() -> str:
    return current_app.config.get("SMS_WEBHOOK_SECRET", "")


def sms_webhook_authorized() -> bool:
    secret = configured_sms_webhook_secret()
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if not secret or not separator or scheme.casefold() != "bearer" or not token:
        return False
    return hmac.compare_digest(token.encode("utf-8"), secret.encode("utf-8"))


def request_json_object():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def admin_denied():
    if not configured_admin_password():
        return jsonify(
            {"error": "Administrator access is not configured on this server."}
        ), 503
    return jsonify({"error": "Incorrect administrator password."}), 401
