import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "web" / "templates"
ASSETS_DIR = PROJECT_ROOT / "web" / "assets"

DATA_DIR = Path.home() / ".lan-dropbox"
DB_PATH = DATA_DIR / "message.db"
UPLOAD_DIR = DATA_DIR / "uploads"

MAX_FILE_SIZE = 100 * 1024 * 1024
MAX_STORAGE_SIZE = 2 * 1024 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".docx", ".xlsx",
    ".pptx", ".txt", ".md", ".csv", ".zip",
}


def default_config():
    return {
        "DATABASE_PATH": DB_PATH,
        "UPLOAD_DIR": UPLOAD_DIR,
        "MAX_FILE_SIZE": MAX_FILE_SIZE,
        "MAX_STORAGE_SIZE": MAX_STORAGE_SIZE,
        "MAX_CONTENT_LENGTH": MAX_FILE_SIZE + 1024 * 1024,
        # Set ADMIN_PASSWORD in the environment to enable administrator
        # actions. When it is empty, deletion stays disabled instead of
        # falling open.
        "ADMIN_PASSWORD": os.environ.get("ADMIN_PASSWORD", ""),
    }
