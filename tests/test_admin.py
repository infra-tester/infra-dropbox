import tempfile
import unittest
from pathlib import Path

from app import create_app


class AdminAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.application = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": root / "messages.db",
                "UPLOAD_DIR": root / "uploads",
                "ADMIN_PASSWORD": "test-admin",
            }
        )
        self.client = self.application.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def status(self):
        return self.client.get("/api/admin/status").get_json()

    def login(self, password="test-admin"):
        return self.client.post("/api/admin/login", json={"password": password})

    def seed_message(self, text="hello"):
        self.client.post("/send", data={"message": text})

    def test_login_status_and_logout_lifecycle(self):
        self.assertEqual(
            self.status(), {"configured": True, "unlocked": False}
        )

        self.assertEqual(self.login("wrong").status_code, 401)
        self.assertEqual(self.client.post("/api/admin/login", json={}).status_code, 401)
        self.assertEqual(self.client.post("/api/admin/login", json=[]).status_code, 401)
        self.assertEqual(self.status()["unlocked"], False)

        self.assertEqual(self.login().status_code, 204)
        self.assertEqual(self.status(), {"configured": True, "unlocked": True})

        self.assertEqual(self.client.post("/api/admin/logout").status_code, 204)
        self.assertEqual(self.status()["unlocked"], False)

    def test_admin_routes_require_sign_in(self):
        self.seed_message()
        messages = self.client.get("/api/messages").get_json()
        message_id = messages[0]["id"]

        self.assertEqual(
            self.client.post(f"/api/messages/{message_id}/delete").status_code, 401
        )
        self.assertEqual(self.client.post("/api/messages/clear").status_code, 401)
        self.assertEqual(len(self.client.get("/api/messages").get_json()), 1)

        self.login()
        self.assertEqual(
            self.client.post(f"/api/messages/{message_id}/delete").status_code, 204
        )

        self.seed_message("second")
        self.assertEqual(self.client.post("/api/messages/clear").status_code, 204)
        self.assertEqual(self.client.get("/api/messages").get_json(), [])

        self.client.post("/api/admin/logout")
        self.assertEqual(self.client.post("/api/messages/clear").status_code, 401)

    def test_password_in_request_body_no_longer_authorizes(self):
        self.seed_message()
        message_id = self.client.get("/api/messages").get_json()[0]["id"]

        response = self.client.post(
            f"/api/messages/{message_id}/delete",
            json={"password": "test-admin"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(len(self.client.get("/api/messages").get_json()), 1)

    def test_unconfigured_server_reports_unavailable(self):
        self.application.config["ADMIN_PASSWORD"] = ""

        self.assertEqual(self.login().status_code, 503)
        self.assertEqual(
            self.status(), {"configured": False, "unlocked": False}
        )

        self.seed_message()
        message_id = self.client.get("/api/messages").get_json()[0]["id"]
        response = self.client.post(f"/api/messages/{message_id}/delete")
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
