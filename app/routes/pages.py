from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
)

from app.config import format_size
from app.db import insert_message
from app.network import detect_lan_ips
from app.security import configured_admin_password

pages_bp = Blueprint("pages", __name__)

DEFAULT_SERVICE_PORT = "5000"


def _service_port() -> str:
    host = request.host
    if ":" in host:
        candidate = host.rsplit(":", 1)[1]
        if candidate.isdigit():
            return candidate
    return DEFAULT_SERVICE_PORT


def _requester_ipv4() -> str:
    host = request.host
    if host.startswith("["):
        return ""
    if ":" in host:
        host = host.split(":", 1)[0]
    parts = host.split(".")
    if len(parts) != 4 or not all(part.isdigit() for part in parts):
        return ""
    if any(int(part) > 255 for part in parts):
        return ""
    return host


@pages_bp.route("/")
def home():
    return render_template(
        "dashboard.html",
        max_file_limit=format_size(current_app.config["MAX_FILE_SIZE"]),
        max_message_length=current_app.config["MAX_MESSAGE_LENGTH"],
    )


@pages_bp.route("/api/network")
def network_info():
    ips = list(detect_lan_ips())
    requester = _requester_ipv4()
    if requester and not requester.startswith("127.") and requester not in ips:
        ips.append(requester)

    port = _service_port()
    urls = [f"{request.scheme}://{ip}:{port}" for ip in ips]
    return jsonify({"urls": urls, "detected": bool(urls)})


@pages_bp.route("/send", methods=["POST"])
def send_message():
    message = request.form.get("message")

    if message and message.strip():
        message = message.strip()
        if len(message) > current_app.config["MAX_MESSAGE_LENGTH"]:
            return jsonify({
                "error": (
                    "The message exceeds the "
                    f"{current_app.config['MAX_MESSAGE_LENGTH']} character limit."
                )
            }), 400
        insert_message(message)
    return redirect("/")


@pages_bp.route("/messages")
def messages_page():
    return render_template("messages.html")


@pages_bp.route("/files")
def files_page():
    return render_template("files.html")


@pages_bp.route("/admin")
def admin_page():
    configured = bool(configured_admin_password())
    signed_in = configured and bool(session.get("admin"))
    return render_template(
        "admin.html", configured=configured, signed_in=signed_in
    )
