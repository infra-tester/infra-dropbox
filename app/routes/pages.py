from flask import Blueprint, render_template, redirect, request

from app.db import insert_message

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def home():
    return render_template("dashboard.html")


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
