from flask import Blueprint, jsonify

from app.security import admin_denied, admin_authorized, request_json_object

admin_bp = Blueprint("admin_api", __name__)


@admin_bp.route("/api/admin/verify", methods=["POST"])
def verify_admin():
    data = request_json_object()

    if not admin_authorized(data.get("password")):
        return admin_denied()
    return "", 204
