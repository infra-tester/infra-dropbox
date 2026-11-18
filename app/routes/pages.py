from flask import Blueprint, redirect, render_template, request, url_for

from app.db import insert_message

pages_bp = Blueprint("pages", __name__)
MAX_MESSAGE_LENGTH = 200


@pages_bp.route("/")
def home():
    return render_template("dashboard.html")


@pages_bp.route("/send", methods=["POST"])
def send_message():
    message = request.form.get("message")

    if message and message.strip():
        insert_message(message.strip())
    return redirect("/")


@pages_bp.route("/m", methods=["GET", "POST"])
def mobile():
    if request.method == "POST":
        message = request.form.get("message", "")
        normalized_message = message.strip()

        if not normalized_message:
            return _render_mobile(message, "Enter a message before sending.", 400)
        message_length = len(normalized_message.encode("utf-16-le")) // 2
        if message_length > MAX_MESSAGE_LENGTH:
            return _render_mobile(
                message,
                f"Messages must be {MAX_MESSAGE_LENGTH} characters or fewer.",
                400,
            )

        insert_message(normalized_message)
        return redirect(url_for("pages.mobile", sent=1))

    return _render_mobile(sent=request.args.get("sent") == "1")


def _render_mobile(message="", error=None, status_code=200, sent=False):
    return (
        render_template(
            "mobile.html",
            message=message,
            error=error,
            sent=sent,
            max_message_length=MAX_MESSAGE_LENGTH,
        ),
        status_code,
    )


@pages_bp.route("/messages")
def messages_page():
    return render_template("messages.html")


@pages_bp.route("/files")
def files_page():
    return render_template("files.html")
