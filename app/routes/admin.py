from flask import Blueprint, jsonify, request, session

from app.db import db_connection, storage_usage
from app.security import (
    admin_denied,
    admin_authorized,
    configured_admin_password,
    require_admin,
    request_json_object,
)
from app.settings import SettingsError, current_settings, save_settings

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


@admin_bp.route("/api/admin/settings", methods=["GET", "POST"])
@require_admin
def admin_settings():
    if request.method == "POST":
        try:
            return jsonify(save_settings(request_json_object())), 200
        except SettingsError as error:
            return jsonify({"error": str(error)}), 400
    return jsonify(current_settings())


@admin_bp.route("/api/admin/stats")
@require_admin
def admin_stats():
    with db_connection() as conn:
        messages = conn.execute("SELECT COUNT(*) FROM message").fetchone()[0]
        files = conn.execute("SELECT COUNT(*) FROM shared_file").fetchone()[0]
        used_bytes = storage_usage(conn)

    return jsonify({
        "messages": messages,
        "files": files,
        "used_bytes": used_bytes,
        "max_bytes": current_settings()["max_storage_bytes"],
        "max_file_bytes": current_settings()["max_file_bytes"],
    })
