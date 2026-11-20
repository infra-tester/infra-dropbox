import secrets

from flask import Flask, jsonify, request

from app.config import TEMPLATES_DIR, ASSETS_DIR, default_config, format_size
from app.db import init_db
from app.routes.admin import admin_bp
from app.routes.files import files_bp
from app.routes.messages import messages_bp
from app.routes.pages import pages_bp
from app.settings import ensure_settings

# Machine-to-machine endpoint authenticated with a bearer secret; browsers
# never call it, so it sends no Origin/Referer and is exempt from the
# same-origin check below.
CSRF_EXEMPT_PATHS = {"/api/integrations/sms"}
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


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

    @application.before_request
    def reject_cross_origin_writes():
        """Block state-changing requests whose Origin/Referer is not us.

        Browsers attach Origin to every POST, so a cross-site page cannot
        forge one. Requests with neither header are not from a browser and
        are rejected as well.
        """
        if request.method not in STATE_CHANGING_METHODS:
            return None
        if request.path in CSRF_EXEMPT_PATHS:
            return None

        expected = request.url_root.rstrip("/")
        origin = request.headers.get("Origin")
        if origin is not None:
            same_origin = origin.rstrip("/") == expected
        else:
            referer = request.headers.get("Referer")
            same_origin = referer is not None and (
                referer == expected or referer.startswith(expected + "/")
            )

        if same_origin:
            return None
        return jsonify({"error": "Cross-origin request rejected."}), 403

    @application.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'",
        )
        return response

    @application.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "That resource does not exist."}), 404
        return error.get_response(request.environ)

    @application.errorhandler(500)
    def internal_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "An unexpected server error occurred."}), 500
        return error.get_response(request.environ)

    @application.errorhandler(413)
    def request_too_large(_error):
        limit = format_size(application.config["MAX_FILE_SIZE"])
        return jsonify({
            "error": f"The upload request is too large. The per-file limit is {limit}."
        }), 413

    init_db(application)
    ensure_settings(application)
    return application
