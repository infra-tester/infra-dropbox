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
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff",
    ".heic", ".heif", ".avif",
    ".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac",
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".3gp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".odp", ".rtf",
    ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".log",
    ".zip", ".7z", ".rar", ".tar", ".gz",
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
        # Set SMS_WEBHOOK_SECRET in the environment to enable authenticated
        # SMS forwarding. When empty, the integration stays unavailable.
        "SMS_WEBHOOK_SECRET": os.environ.get("SMS_WEBHOOK_SECRET", ""),
    }
