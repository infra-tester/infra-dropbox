import io
import tempfile
import unittest
from pathlib import Path

from app import create_app, rate_limit
from tests.support import make_client


class AdminDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.application = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": self.root / "messages.db",
                "UPLOAD_DIR": self.root / "uploads",
                "MAX_FILE_SIZE": 8,
                "MAX_STORAGE_SIZE": 10,
                "ADMIN_PASSWORD": "test-admin",
            }
        )
        rate_limit.reset()
        self.client = make_client(self.application)

    def tearDown(self):
        self.temp_dir.cleanup()

    def login(self, password="test-admin"):
        return self.client.post("/api/admin/login", json={"password": password})

    def upload(self, content=b"data", filename="sample.txt"):
        return self.client.post(
            "/api/files",
            data={"file": (io.BytesIO(content), filename)},
            content_type="multipart/form-data",
        )

    def test_admin_page_gates_the_dashboard_behind_sign_in(self):
        page = self.client.get("/admin")

        self.assertEqual(page.status_code, 200)
        self.assertIn(b'id="admin-signin-form"', page.data)
        self.assertNotIn(b"id=\"admin-settings-form\"", page.data)

        self.login()
        page = self.client.get("/admin")

        self.assertIn(b'id="admin-settings-form"', page.data)
        self.assertIn(b'id="admin-clear-messages"', page.data)
        self.assertIn(b'id="admin-clear-files"', page.data)
        self.assertNotIn(b'id="admin-signin-form"', page.data)

    def test_admin_page_explains_missing_configuration(self):
        self.application.config["ADMIN_PASSWORD"] = ""

        page = self.client.get("/admin")

        self.assertEqual(page.status_code, 200)
        self.assertIn(b"not configured", page.data)
        self.assertNotIn(b'id="admin-signin-form"', page.data)

    def test_settings_round_trip_and_validation(self):
        self.assertEqual(
            self.client.get("/api/admin/settings").status_code, 401
        )

        self.login()
        current = self.client.get("/api/admin/settings").get_json()
        self.assertEqual(current["max_file_bytes"], 8)
        self.assertEqual(current["max_storage_bytes"], 10)
        self.assertIn(".txt", current["allowed_extensions"])

        response = self.client.post(
            "/api/admin/settings",
            json={
                "max_file_bytes": 6,
                "max_storage_bytes": 20,
                "allowed_extensions": [".TXT", ". .", ".md"],
            },
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/admin/settings",
            json={
                "max_file_bytes": 5,
                "max_storage_bytes": 9,
                "allowed_extensions": [".txt", ".md"],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["max_file_bytes"], 5)

        saved = self.client.get("/api/admin/settings").get_json()
        self.assertEqual(saved["allowed_extensions"], [".md", ".txt"])

    def test_settings_reject_invalid_payloads(self):
        self.login()
        invalid_payloads = (
            {},
            {"max_file_bytes": True, "max_storage_bytes": 10,
             "allowed_extensions": [".txt"]},
            {"max_file_bytes": 5, "max_storage_bytes": 4,
             "allowed_extensions": [".txt"]},
            {"max_file_bytes": 5, "max_storage_bytes": 10,
             "allowed_extensions": []},
            {"max_file_bytes": 5, "max_storage_bytes": 10,
             "allowed_extensions": ["png"]},
            {"max_file_bytes": 5, "max_storage_bytes": 10,
             "allowed_extensions": ["png.exe"]},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/api/admin/settings", json=payload
                )
                self.assertEqual(response.status_code, 400)

    def test_saved_settings_are_enforced_by_uploads(self):
        self.login()
        self.client.post(
            "/api/admin/settings",
            json={
                "max_file_bytes": 4,
                "max_storage_bytes": 100,
                "allowed_extensions": [".txt"],
            },
        )

        self.assertEqual(self.upload(b"12345", "ok.txt").status_code, 413)
        self.assertEqual(self.upload(b"1234", "image.png").status_code, 415)
        response = self.upload(b"1234", "ok.txt")
        self.assertEqual(response.status_code, 201)

    def test_stats_endpoint_is_protected_and_reports_counts(self):
        self.assertEqual(self.client.get("/api/admin/stats").status_code, 401)

        self.client.post("/send", data={"message": "hello"})
        self.upload(b"abc", "notes.txt")

        self.login()
        stats = self.client.get("/api/admin/stats").get_json()
        self.assertEqual(stats["messages"], 1)
        self.assertEqual(stats["files"], 1)
        self.assertEqual(stats["used_bytes"], 3)
        self.assertEqual(stats["max_bytes"], 10)
        self.assertEqual(stats["max_file_bytes"], 8)

    def test_clear_files_requires_sign_in_and_removes_everything(self):
        self.upload(b"abc", "notes.txt")
        upload_dir = self.root / "uploads"
        self.assertEqual(len(list(upload_dir.iterdir())), 1)

        self.assertEqual(self.client.post("/api/files/clear").status_code, 401)
        self.assertEqual(len(list(upload_dir.iterdir())), 1)

        self.login()
        self.assertEqual(self.client.post("/api/files/clear").status_code, 204)
        self.assertEqual(self.client.get("/api/files").get_json()["files"], [])
        self.assertEqual(list(upload_dir.iterdir()), [])

    def test_content_pages_no_longer_ship_an_admin_panel(self):
        for path in ("/messages", "/files"):
            with self.subTest(path=path):
                page = self.client.get(path)
                self.assertEqual(page.status_code, 200)
                self.assertNotIn(b"Administrator actions", page.data)
                self.assertNotIn(b'id="admin-unlock"', page.data)
                self.assertNotIn(b'id="admin-clear"', page.data)

    def test_home_page_shows_the_configured_file_limit(self):
        page = self.client.get("/")

        self.assertIn(b"Up to 8 B per file", page.data)


if __name__ == "__main__":
    unittest.main()
