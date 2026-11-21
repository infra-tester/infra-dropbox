import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app, rate_limit
from tests.support import make_client


def build_app(**overrides):
    temp_dir = tempfile.TemporaryDirectory()
    root = Path(temp_dir.name)
    application = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": root / "messages.db",
            "UPLOAD_DIR": root / "uploads",
            "ADMIN_PASSWORD": "test-admin",
            **overrides,
        }
    )
    return temp_dir, application


class NetworkEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir, self.application = build_app()
        rate_limit.reset()
        self.client = make_client(self.application)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_reports_detected_urls_with_port(self):
        with patch(
            "app.routes.pages.detect_lan_ips", return_value=["192.168.1.5"]
        ):
            data = self.client.get("/api/network").get_json()

        self.assertTrue(data["detected"])
        self.assertIn("http://192.168.1.5:5000", data["urls"])

    def test_includes_non_loopback_requester_when_detection_is_empty(self):
        with patch("app.routes.pages.detect_lan_ips", return_value=[]):
            data = self.client.get(
                "/api/network", base_url="http://192.168.1.9:5000"
            ).get_json()

        self.assertTrue(data["detected"])
        self.assertEqual(data["urls"], ["http://192.168.1.9:5000"])

    def test_requester_already_detected_is_not_duplicated(self):
        with patch(
            "app.routes.pages.detect_lan_ips", return_value=["192.168.1.5"]
        ):
            data = self.client.get(
                "/api/network", base_url="http://192.168.1.5:5000"
            ).get_json()

        self.assertEqual(data["urls"], ["http://192.168.1.5:5000"])

    def test_localhost_requester_with_failed_detection_reports_undetected(self):
        with patch("app.routes.pages.detect_lan_ips", return_value=[]):
            data = self.client.get("/api/network").get_json()

        self.assertFalse(data["detected"])
        self.assertEqual(data["urls"], [])

    def test_loopback_requester_is_excluded(self):
        with patch("app.routes.pages.detect_lan_ips", return_value=[]):
            data = self.client.get(
                "/api/network", base_url="http://127.0.0.1:5000"
            ).get_json()

        self.assertFalse(data["detected"])
        self.assertEqual(data["urls"], [])


class EtagTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir, self.application = build_app()
        rate_limit.reset()
        self.client = make_client(self.application)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_messages_send_etag_and_honor_if_none_match(self):
        first = self.client.get("/api/messages")
        etag = first.headers.get("ETag")

        self.assertTrue(etag)
        self.assertEqual(first.headers["Cache-Control"], "no-cache")

        cached = self.client.get("/api/messages", headers={"If-None-Match": etag})
        self.assertEqual(cached.status_code, 304)
        self.assertEqual(cached.data, b"")

        self.client.post("/send", data={"message": "fresh"})
        after_change = self.client.get(
            "/api/messages", headers={"If-None-Match": etag}
        )
        self.assertEqual(after_change.status_code, 200)
        self.assertEqual(len(after_change.get_json()), 1)

    def test_search_results_use_separate_cache_entries(self):
        self.client.post("/send", data={"message": "alpha one"})
        self.client.post("/send", data={"message": "beta two"})
        plain = self.client.get("/api/messages")
        searched = self.client.get("/api/messages?q=alpha")

        self.assertEqual(len(plain.get_json()), 2)
        self.assertEqual(len(searched.get_json()), 1)
        self.assertNotEqual(plain.headers["ETag"], searched.headers["ETag"])

        cached = self.client.get(
            "/api/messages?q=alpha",
            headers={"If-None-Match": searched.headers["ETag"]},
        )
        self.assertEqual(cached.status_code, 304)

    def test_files_send_etag_and_honor_if_none_match(self):
        first = self.client.get("/api/files")
        etag = first.headers.get("ETag")

        self.assertTrue(etag)

        cached = self.client.get("/api/files", headers={"If-None-Match": etag})
        self.assertEqual(cached.status_code, 304)
        self.assertEqual(cached.data, b"")

        self.client.post(
            "/api/files",
            data={"file": (io.BytesIO(b"hello"), "notes.txt")},
            content_type="multipart/form-data",
        )
        after_change = self.client.get("/api/files", headers={"If-None-Match": etag})
        self.assertEqual(after_change.status_code, 200)
        self.assertEqual(len(after_change.get_json()["files"]), 1)


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir, self.application = build_app()
        rate_limit.reset()
        self.client = make_client(self.application)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_files_page_has_a_status_element(self):
        page = self.client.get("/files")

        self.assertIn(b'id="file-status"', page.data)

    def test_pages_carry_the_connection_badge(self):
        for path in ("/", "/messages", "/files", "/admin"):
            with self.subTest(path=path):
                page = self.client.get(path)
                self.assertIn(b'id="connection-status"', page.data)

    def test_dashboard_has_the_connection_panel_and_send_status(self):
        page = self.client.get("/")

        self.assertIn(b'id="lan-urls"', page.data)
        self.assertIn(b'id="lan-urls-fallback"', page.data)
        self.assertIn(b'id="message-send-status"', page.data)
        self.assertIn(b'id="lan-urls-status"', page.data)


if __name__ == "__main__":
    unittest.main()
