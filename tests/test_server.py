import threading
import unittest

from werkzeug.test import Client
from werkzeug.wrappers import Response

from server import HOST, PORT, ShutdownMiddleware


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


if __name__ == "__main__":
    unittest.main()
