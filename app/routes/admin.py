from flask import Blueprint, jsonify, session

from app.security import (
    admin_denied,
    admin_authorized,
    configured_admin_password,
    request_json_object,
)

admin_bp = Blueprint("admin_api", __name__)


@admin_bp.route("/api/admin/login", methods=["POST"])
def login_admin():
    if not configured_admin_password():
        return admin_denied()

    data = request_json_object()
    if not admin_authorized(data.get("password")):
        return admin_denied()

    session.clear()
    session["admin"] = True
    return "", 204


@admin_bp.route("/api/admin/logout", methods=["POST"])
def logout_admin():
    session.clear()
    return "", 204


@admin_bp.route("/api/admin/status")
def admin_status():
    configured = bool(configured_admin_password())
    return jsonify({
        "configured": configured,
        "unlocked": configured and bool(session.get("admin")),
    })
