import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app, rate_limit
from tests.support import make_client


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
        rate_limit.reset()
        self.client = make_client(self.application)
        self.headers = {"Authorization": "Bearer sms-secret"}

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sms_preserves_sender_and_exact_body(self):
        body = " Hello "
        response = self.client.post(
            "/api/integrations/sms",
            json={"sender": "+919198975335", "message": body},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), {"status": "stored"})
        messages = self.client.get("/api/messages").get_json()
        self.assertEqual(messages[0]["sender"], "+919198975335")
        self.assertEqual(messages[0]["content"], body)
        self.assertNotIn("SMS from", messages[0]["content"])
        self.assertNotIn("*/=zN8a1w", messages[0]["content"])
        self.assertIn("created_at", messages[0])

    def test_sms_body_is_not_sanitized_by_removing_suffix_like_text(self):
        body = "Hello*/=zN8a1w"

        response = self.client.post(
            "/api/integrations/sms",
            json={"sender": "+919198975335", "message": body},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.client.get("/api/messages").get_json()[0]["content"], body
        )

    def test_normal_message_submission_and_retrieval_are_unchanged(self):
        response = self.client.post("/send", data={"message": "  Normal message  "})

        self.assertEqual(response.status_code, 302)
        message = self.client.get("/api/messages").get_json()[0]
        self.assertEqual(message["content"], "Normal message")
        self.assertNotIn("sender", message)
        self.assertTrue(message["created_at"])

    def test_existing_database_messages_remain_retrievable(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.db"
        connection = sqlite3.connect(legacy_path)
        try:
            connection.execute(
                "CREATE TABLE message ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "content TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO message (content, created_at) VALUES (?, ?)",
                ("Existing message", "2024-01-02T03:04:05+00:00"),
            )
            connection.commit()
        finally:
            connection.close()

        legacy_app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": legacy_path,
                "UPLOAD_DIR": Path(self.temp_dir.name) / "legacy-uploads",
                "ADMIN_PASSWORD": "admin-secret",
            }
        )
        message = legacy_app.test_client().get("/api/messages").get_json()[0]

        self.assertEqual(message["content"], "Existing message")
        self.assertEqual(message["created_at"], "2024-01-02T03:04:05+00:00")
        self.assertNotIn("sender", message)

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
