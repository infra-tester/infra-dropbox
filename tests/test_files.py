import io
import tempfile
import unittest
from pathlib import Path

import app as app_module


class FileSharingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.original_config = {
            key: app_module.app.config[key]
            for key in (
                "DATABASE_PATH",
                "UPLOAD_DIR",
                "MAX_FILE_SIZE",
                "MAX_STORAGE_SIZE",
            )
        }
        self.original_password = app_module.ADMIN_PASSWORD
        app_module.app.config.update(
            DATABASE_PATH=root / "messages.db",
            UPLOAD_DIR=root / "uploads",
            MAX_FILE_SIZE=8,
            MAX_STORAGE_SIZE=10,
        )
        app_module.ADMIN_PASSWORD = "test-admin"
        app_module.app.config["TESTING"] = True
        app_module.init_db()
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.app.config.update(self.original_config)
        app_module.app.config["TESTING"] = False
        app_module.ADMIN_PASSWORD = self.original_password
        self.temp_dir.cleanup()

    def upload(self, content=b"data", filename="sample.txt"):
        return self.client.post(
            "/api/files",
            data={"file": (io.BytesIO(content), filename)},
            content_type="multipart/form-data",
        )

    def test_upload_form_is_on_home_and_files_page_only_lists_files(self):
        home = self.client.get("/")
        files = self.client.get("/files")

        self.assertEqual(home.status_code, 200)
        self.assertIn(b"file-upload-form", home.data)
        self.assertEqual(files.status_code, 200)
        self.assertIn(b'href="/files"', files.data)
        self.assertIn(b'id="files"', files.data)
        self.assertNotIn(b"file-upload-form", files.data)

    def test_upload_and_list_metadata(self):
        response = self.upload(b"hello", "../../hello.TXT")

        self.assertEqual(response.status_code, 201)
        listed = self.client.get("/api/files").get_json()
        self.assertEqual(listed["used_bytes"], 5)
        self.assertEqual(listed["max_bytes"], 10)
        self.assertEqual(listed["files"][0]["filename"], "hello.TXT")
        self.assertEqual(listed["files"][0]["size"], 5)

    def test_accepts_empty_files(self):
        response = self.upload(b"", "empty.txt")

        self.assertEqual(response.status_code, 201)
        files = self.client.get("/api/files").get_json()["files"]
        self.assertEqual(files[0]["size"], 0)

    def test_rejects_disallowed_and_oversized_files(self):
        self.assertEqual(self.upload(filename="script.exe").status_code, 415)
        self.assertEqual(self.upload(b"123456789").status_code, 413)
        self.assertEqual(self.client.get("/api/files").get_json()["files"], [])
        self.assertEqual(list((Path(self.temp_dir.name) / "uploads").iterdir()), [])

    def test_rejects_upload_that_would_exceed_storage_quota(self):
        self.assertEqual(self.upload(b"123456").status_code, 201)
        response = self.upload(b"12345", "second.txt")

        self.assertEqual(response.status_code, 413)
        self.assertIn("storage limit", response.get_json()["error"])
        listed = self.client.get("/api/files").get_json()
        self.assertEqual(len(listed["files"]), 1)
        self.assertEqual(listed["used_bytes"], 6)

    def test_download_is_an_attachment(self):
        self.upload(b"hello", "notes.txt")
        file_id = self.client.get("/api/files").get_json()["files"][0]["id"]

        with self.client.get(f"/api/files/{file_id}/download") as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b"hello")
            self.assertIn("attachment", response.headers["Content-Disposition"])
            self.assertIn("notes.txt", response.headers["Content-Disposition"])

    def test_delete_requires_admin_password_and_removes_file(self):
        self.upload(b"hello", "notes.txt")
        file_id = self.client.get("/api/files").get_json()["files"][0]["id"]
        endpoint = f"/api/files/{file_id}/delete"

        self.assertEqual(self.client.post(endpoint, json={}).status_code, 401)
        self.assertEqual(self.client.post(endpoint, json=[]).status_code, 401)
        self.assertEqual(
            self.client.post(endpoint, json={"password": []}).status_code, 401
        )
        self.assertEqual(
            self.client.post(endpoint, json={"password": "wrong"}).status_code, 401
        )
        response = self.client.post(endpoint, json={"password": "test-admin"})

        self.assertEqual(response.status_code, 204)
        listed = self.client.get("/api/files").get_json()
        self.assertEqual(listed["files"], [])
        self.assertEqual(listed["used_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
