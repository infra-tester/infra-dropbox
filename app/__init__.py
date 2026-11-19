import secrets

from flask import Flask, jsonify

from app.config import TEMPLATES_DIR, ASSETS_DIR, default_config, format_size
from app.db import init_db
from app.routes.admin import admin_bp
from app.routes.files import files_bp
from app.routes.messages import messages_bp
from app.routes.pages import pages_bp
from app.settings import ensure_settings


def create_app(config_overrides=None):
    application = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(ASSETS_DIR),
        static_url_path="/assets",
    )
    application.config.update(default_config())
    if config_overrides:
        application.config.update(config_overrides)

    # Signs administrator session cookies. Generated per process so sessions
    # end when the server restarts; nothing sensitive is written to disk.
    application.secret_key = application.config.get("SECRET_KEY") or secrets.token_hex(32)

    application.register_blueprint(pages_bp)
    application.register_blueprint(messages_bp)
    application.register_blueprint(files_bp)
    application.register_blueprint(admin_bp)

    @application.errorhandler(413)
    def request_too_large(_error):
        limit = format_size(application.config["MAX_FILE_SIZE"])
        return jsonify({
            "error": f"The upload request is too large. The per-file limit is {limit}."
        }), 413

    init_db(application)
    ensure_settings(application)
    return application
