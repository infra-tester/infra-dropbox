import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from werkzeug.test import Client
from werkzeug.wrappers import Response

from server import HOST, PORT, ShutdownMiddleware, _acquire_instance_lock


class ShutdownMiddlewareTests(unittest.TestCase):
    def setUp(self):
        self.shutdown_requested = threading.Event()

        def application(environ, start_response):
            start_response("200 OK", [("Content-Length", "2")])
            return [b"ok"]

        self.application = ShutdownMiddleware(
            application,
            "test-token",
            self.shutdown_requested.set,
        )
        self.client = Client(self.application, Response)

    def test_normal_requests_pass_through(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"ok")
        self.assertFalse(self.shutdown_requested.is_set())

    def test_shutdown_requires_loopback_and_token(self):
        remote_client = Client(self.application, Response)
        response = remote_client.post(
            "/__idb_shutdown",
            headers={"X-IDB-Shutdown-Token": "test-token"},
            environ_overrides={"REMOTE_ADDR": "192.168.1.25"},
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            "/__idb_shutdown",
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.shutdown_requested.is_set())

    def test_authenticated_loopback_shutdown_is_accepted(self):
        response = self.client.post(
            "/__idb_shutdown",
            headers={"X-IDB-Shutdown-Token": "test-token"},
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
        )

        self.assertEqual(response.status_code, 202)
        self.assertTrue(self.shutdown_requested.wait(timeout=1))
        self.assertEqual(self.client.get("/").status_code, 503)

    def test_shutdown_requires_post(self):
        response = self.client.get(
            "/__idb_shutdown",
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
        )

        self.assertEqual(response.status_code, 405)
        self.assertFalse(self.shutdown_requested.is_set())

    def test_runtime_binds_for_lan_access(self):
        self.assertEqual(HOST, "0.0.0.0")
        self.assertEqual(PORT, 5000)

    def test_instance_lock_prevents_a_second_server_process(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "server.lock"
            lock_file = _acquire_instance_lock(lock_path)
            try:
                code = (
                    "from pathlib import Path; "
                    "from server import _acquire_instance_lock; "
                    f"_acquire_instance_lock(Path({str(lock_path)!r}))"
                )
                result = subprocess.run(
                    [sys.executable, "-c", code],
                    cwd=Path(__file__).resolve().parents[1],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("instance lock", result.stderr)
            finally:
                lock_file.close()


if __name__ == "__main__":
    unittest.main()
