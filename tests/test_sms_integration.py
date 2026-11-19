import tempfile
import unittest
from pathlib import Path

from app import create_app


class SmsIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.application = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": root / "messages.db",
                "UPLOAD_DIR": root / "uploads",
                "ADMIN_PASSWORD": "admin-secret",
                "SMS_WEBHOOK_SECRET": "sms-secret",
            }
        )
        self.client = self.application.test_client()
        self.headers = {"Authorization": "Bearer sms-secret"}

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_authenticated_sms_is_saved_with_sender(self):
        response = self.client.post(
            "/api/integrations/sms",
            json={"sender": "+919XXXXXXXXX", "message": "Forwarded SMS content"},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), {"status": "stored"})
        messages = self.client.get("/api/messages").get_json()
        self.assertEqual(
            messages[0]["content"],
            "SMS from +919XXXXXXXXX:\nForwarded SMS content",
        )

    def test_requires_the_dedicated_secret(self):
        for headers in ({}, {"Authorization": "Bearer admin-secret"}):
            with self.subTest(headers=headers):
                response = self.client.post(
                    "/api/integrations/sms",
                    json={"sender": "sender", "message": "text"},
                    headers=headers,
                )
                self.assertEqual(response.status_code, 401)

        response = self.client.post(
            "/api/integrations/sms?token=sms-secret",
            json={"sender": "sender", "message": "text"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/api/messages").get_json(), [])

    def test_rejects_invalid_json_and_sms_fields(self):
        invalid_requests = (
            {"data": "not-json", "content_type": "application/json"},
            {"json": []},
            {"json": {"sender": "sender", "message": ""}},
            {"json": {"sender": "sender\nforged", "message": "text"}},
            {"json": {"sender": [], "message": "text"}},
            {"json": {"sender": "sender", "message": 123}},
        )
        for payload in invalid_requests:
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/api/integrations/sms", headers=self.headers, **payload
                )
                self.assertEqual(response.status_code, 400)

        self.assertEqual(self.client.get("/api/messages").get_json(), [])

    def test_returns_unavailable_when_secret_is_not_configured(self):
        self.application.config["SMS_WEBHOOK_SECRET"] = ""

        response = self.client.post(
            "/api/integrations/sms",
            json={"sender": "sender", "message": "text"},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.client.get("/api/messages").get_json(), [])


if __name__ == "__main__":
    unittest.main()
