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


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir, self.application = build_app()
        rate_limit.reset()
        self.client = make_client(self.application)

    def tearDown(self):
        rate_limit.reset()
        self.temp_dir.cleanup()

    def login(self, password="test-admin"):
        return self.client.post("/api/admin/login", json={"password": password})

    def test_repeated_failures_lock_out_even_the_correct_password(self):
        for _ in range(5):
            self.assertEqual(self.login("wrong").status_code, 401)

        response = self.login()

        self.assertEqual(response.status_code, 429)
        waiting = int(response.headers["Retry-After"])
        self.assertGreater(waiting, 0)
        self.assertLessEqual(waiting, 30)
        self.assertIn("Too many failed sign-in attempts", response.get_json()["error"])

        status = self.client.get("/api/admin/status")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.get_json()["unlocked"], False)

    def test_successful_sign_in_resets_the_failure_count(self):
        for _ in range(4):
            self.assertEqual(self.login("wrong").status_code, 401)
        self.assertEqual(self.login().status_code, 204)
        self.client.post("/api/admin/logout")

        for _ in range(4):
            self.assertEqual(self.login("wrong").status_code, 401)
        self.assertEqual(self.login().status_code, 204)

    def test_backoff_grows_after_the_lockout_expires(self):
        for _ in range(5):
            self.assertEqual(self.login("wrong").status_code, 401)

        start = rate_limit._now()
        with patch("app.rate_limit._now", return_value=start + 31):
            self.assertEqual(self.login("wrong").status_code, 401)
            response = self.login()

        self.assertEqual(response.status_code, 429)
        self.assertEqual(int(response.headers["Retry-After"]), 60)

    def test_unconfigured_password_reports_503_without_rate_limiting(self):
        self.application.config["ADMIN_PASSWORD"] = ""

        for _ in range(8):
            self.assertEqual(self.login().status_code, 503)


class SameOriginTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir, self.application = build_app()
        rate_limit.reset()
        self.client = make_client(self.application)

    def tearDown(self):
        rate_limit.reset()
        self.temp_dir.cleanup()

    def messages(self):
        return self.client.get("/api/messages").get_json()

    def test_same_origin_post_is_accepted(self):
        response = self.client.post("/send", data={"message": "hello"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(self.messages()), 1)

    def test_cross_origin_post_is_rejected_before_the_view_runs(self):
        response = self.client.post(
            "/send",
            data={"message": "forged"},
            environ_overrides={"HTTP_ORIGIN": "http://evil.example"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Cross-origin", response.get_json()["error"])
        self.assertEqual(self.messages(), [])

    def test_matching_referer_is_accepted_without_origin(self):
        client = self.application.test_client()
        response = client.post(
            "/send",
            data={"message": "hello"},
            headers={"Referer": "http://localhost/"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(self.messages()), 1)

    def test_cross_origin_referer_is_rejected(self):
        client = self.application.test_client()
        response = client.post(
            "/send",
            data={"message": "forged"},
            headers={"Referer": "http://evil.example/attack"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.messages(), [])

    def test_requests_without_origin_and_referer_are_rejected(self):
        client = self.application.test_client()
        response = client.post("/send", data={"message": "forged"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.messages(), [])

    def test_get_requests_are_not_affected(self):
        client = self.application.test_client()

        self.assertEqual(client.get("/").status_code, 200)
        self.assertEqual(client.get("/api/messages").status_code, 200)

    def test_cross_origin_admin_delete_is_rejected(self):
        self.client.post("/send", data={"message": "keep me"})
        message_id = self.messages()[0]["id"]
        self.client.post("/api/admin/login", json={"password": "test-admin"})

        response = self.client.post(
            f"/api/messages/{message_id}/delete",
            environ_overrides={"HTTP_ORIGIN": "http://evil.example"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(self.messages()), 1)

    def test_sms_webhook_is_exempt_from_the_origin_check(self):
        self.application.config["SMS_WEBHOOK_SECRET"] = "sms-secret"
        client = self.application.test_client()

        response = client.post(
            "/api/integrations/sms",
            json={"sender": "+10000000000", "message": "from a script"},
            headers={"Authorization": "Bearer sms-secret"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.messages()), 1)


class MessageLengthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir, self.application = build_app()
        rate_limit.reset()
        self.client = make_client(self.application)

    def tearDown(self):
        self.temp_dir.cleanup()

    def messages(self):
        return self.client.get("/api/messages").get_json()

    def test_send_rejects_messages_over_the_limit(self):
        response = self.client.post("/send", data={"message": "x" * 1001})

        self.assertEqual(response.status_code, 400)
        self.assertIn("1000 character limit", response.get_json()["error"])
        self.assertEqual(self.messages(), [])

        self.assertEqual(
            self.client.post("/send", data={"message": "x" * 1000}).status_code,
            302,
        )
        self.assertEqual(len(self.messages()), 1)

    def test_sms_rejects_messages_over_the_limit(self):
        self.application.config["SMS_WEBHOOK_SECRET"] = "sms-secret"
        headers = {"Authorization": "Bearer sms-secret"}

        response = self.client.post(
            "/api/integrations/sms",
            json={"sender": "+10000000000", "message": "x" * 1001},
            headers=headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.messages(), [])

    def test_dashboard_limit_follows_the_configured_value(self):
        self.application.config["MAX_MESSAGE_LENGTH"] = 10

        page = self.client.get("/")

        self.assertIn(b'maxlength="10"', page.data)
        self.assertEqual(
            self.client.post("/send", data={"message": "x" * 11}).status_code,
            400,
        )
        self.assertEqual(
            self.client.post("/send", data={"message": "x" * 10}).status_code,
            302,
        )


class SecurityHeaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir, self.application = build_app()
        rate_limit.reset()
        self.client = make_client(self.application)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pages_and_api_responses_carry_security_headers(self):
        for path in ("/", "/api/messages"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(
                    response.headers["X-Content-Type-Options"], "nosniff"
                )
                self.assertEqual(response.headers["X-Frame-Options"], "DENY")
                self.assertEqual(
                    response.headers["Referrer-Policy"], "same-origin"
                )
                csp = response.headers["Content-Security-Policy"]
                self.assertIn("default-src 'self'", csp)
                self.assertIn("frame-ancestors 'none'", csp)
                self.assertIn("form-action 'self'", csp)


class ApiErrorFormatTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir, self.application = build_app()
        rate_limit.reset()
        self.client = make_client(self.application)

        @self.application.route("/api/failed")
        def api_failed():
            from flask import abort

            abort(500)

        @self.application.route("/failed")
        def page_failed():
            from flask import abort

            abort(500)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_unknown_api_paths_return_json(self):
        response = self.client.get("/api/does-not-exist")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.is_json)
        self.assertIn("error", response.get_json())

    def test_unknown_pages_keep_the_html_not_found_page(self):
        response = self.client.get("/does-not-exist")

        self.assertEqual(response.status_code, 404)
        self.assertIn("text/html", response.content_type)

    def test_api_server_errors_return_json(self):
        response = self.client.get("/api/failed")

        self.assertEqual(response.status_code, 500)
        self.assertTrue(response.is_json)
        self.assertIn("error", response.get_json())

    def test_page_server_errors_stay_html(self):
        response = self.client.get("/failed")

        self.assertEqual(response.status_code, 500)
        self.assertIn("text/html", response.content_type)


if __name__ == "__main__":
    unittest.main()
