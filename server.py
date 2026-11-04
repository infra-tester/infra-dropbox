import hmac
import os
import secrets
import threading
from pathlib import Path

from waitress import create_server


HOST = "0.0.0.0"
PORT = 5000
SHUTDOWN_PATH = "/__idb_shutdown"
SHUTDOWN_TOKEN_HEADER = "HTTP_X_IDB_SHUTDOWN_TOKEN"


class ShutdownMiddleware:
    def __init__(self, application, token, shutdown):
        self.application = application
        self.token = token
        self.shutdown = shutdown
        self.stopping = threading.Event()

    def __call__(self, environ, start_response):
        if environ.get("PATH_INFO") != SHUTDOWN_PATH:
            if self.stopping.is_set():
                return self._respond(start_response, "503 Service Unavailable")
            return self.application(environ, start_response)

        if environ.get("REQUEST_METHOD") != "POST":
            return self._respond(start_response, "405 Method Not Allowed")

        remote_addr = environ.get("REMOTE_ADDR")
        supplied_token = environ.get(SHUTDOWN_TOKEN_HEADER, "")
        if remote_addr not in ("127.0.0.1", "::1") or not hmac.compare_digest(
            supplied_token, self.token
        ):
            return self._respond(start_response, "403 Forbidden")

        self.stopping.set()
        threading.Thread(target=self.shutdown, daemon=True).start()
        return self._respond(start_response, "202 Accepted", b"Stopping.")

    @staticmethod
    def _respond(start_response, status, body=b""):
        start_response(
            status,
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(body))),
            ],
        )
        return [body]


def run(application):
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not set; cannot store shutdown control.")

    state_dir = Path(local_app_data) / "InfraDropbox"
    state_dir.mkdir(parents=True, exist_ok=True)
    token_path = state_dir / "shutdown.token"
    token = secrets.token_urlsafe(32)

    server = None

    def shutdown():
        if server is not None:
            server.task_dispatcher.shutdown(timeout=8, cancel_pending=False)
            for channel in tuple(server.active_channels.values()):
                channel.close()
            server.close()
            server.task_dispatcher.shutdown(timeout=2)

    wrapped_app = ShutdownMiddleware(application, token, shutdown)
    try:
        server = create_server(wrapped_app, host=HOST, port=PORT)
        token_path.write_text(token, encoding="utf-8")
        server.run()
    finally:
        if server is not None and not wrapped_app.stopping.is_set():
            shutdown()
        try:
            if token_path.read_text(encoding="utf-8") == token:
                token_path.unlink()
        except FileNotFoundError:
            pass
