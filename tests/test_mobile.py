import tempfile
import unittest
from pathlib import Path

from app import create_app


class MobileSharingTests(unittest.TestCase):
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

    def test_mobile_page_has_paste_and_send_without_recent_messages(self):
        self.client.post("/m", data={"message": "A message that should stay hidden"})
        response = self.client.get("/m")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="paste-button"', response.data)
        self.assertIn(b'type="submit"', response.data)
        self.assertNotIn(b"Recent messages", response.data)
        self.assertNotIn(b"A message that should stay hidden", response.data)
        self.assertNotIn(b"file-upload-form", response.data)
        self.assertNotIn(b"admin-panel", response.data)

    def test_valid_submission_is_trimmed_and_shown_after_redirect(self):
        response = self.client.post(
            "/m",
            data={"message": "  Hello from the phone  "},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Message sent.", response.data)
        self.assertNotIn(b"Hello from the phone", response.data)
        self.assertEqual(
            self.client.get("/api/messages").get_json()[0]["content"],
            "Hello from the phone",
        )

    def test_rejects_empty_and_over_limit_messages(self):
        for message in (" \n ", "x" * 201):
            with self.subTest(message_length=len(message)):
                response = self.client.post("/m", data={"message": message})
                self.assertEqual(response.status_code, 400)

        self.assertEqual(self.client.get("/api/messages").get_json(), [])

    def test_accepts_exact_limit_using_browser_character_count(self):
        response = self.client.post("/m", data={"message": "x" * 200})
        self.assertEqual(response.status_code, 302)

        response = self.client.post("/m", data={"message": "\U0001f600" * 101})
        self.assertEqual(response.status_code, 400)

    def test_message_content_is_not_shown_on_mobile_page(self):
        message = "<script>alert(1)</script>"
        response = self.client.post(
            "/m",
            data={"message": message},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"<script>alert(1)</script>", response.data)
        self.assertEqual(
            self.client.get("/api/messages").get_json()[0]["content"],
            message,
        )

    def test_full_application_pages_remain_available(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/messages").status_code, 200)
        self.assertEqual(self.client.get("/files").status_code, 200)


if __name__ == "__main__":
    unittest.main()
