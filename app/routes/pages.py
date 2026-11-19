from flask import Blueprint, current_app, redirect, render_template, request, session

from app.config import format_size
from app.db import insert_message
from app.security import configured_admin_password

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def home():
    return render_template(
        "dashboard.html",
        max_file_limit=format_size(current_app.config["MAX_FILE_SIZE"]),
    )


@pages_bp.route("/send", methods=["POST"])
def send_message():
    message = request.form.get("message")

    if message and message.strip():
        insert_message(message.strip())
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
