import re

from flask import current_app

from app.db import db_connection

SETTING_KEYS = ("max_file_size", "max_storage_size", "allowed_extensions")

_FIELD_BY_KEY = {
    "max_file_size": "max_file_bytes",
    "max_storage_size": "max_storage_bytes",
    "allowed_extensions": "allowed_extensions",
}

MAX_FILE_SIZE_LIMIT = 10 * 1024**3
MAX_STORAGE_SIZE_LIMIT = 100 * 1024**3

_EXTENSION_PATTERN = re.compile(r"^\.[a-z0-9]{1,16}$")
_MAX_EXTENSIONS = 300


class SettingsError(ValueError):
    """Raised when submitted settings fail validation."""


def _serialize(key: str, value) -> str:
    if key == "allowed_extensions":
        return ",".join(sorted(value))
    return str(int(value))


def _deserialize(key: str, raw: str):
    if key == "allowed_extensions":
        return {item for item in raw.split(",") if item}
    return int(raw)


def ensure_settings(application):
    """Create, seed, and sync the settings table for this application."""
    with application.app_context():
        defaults = {
            "max_file_size": application.config["MAX_FILE_SIZE"],
            "max_storage_size": application.config["MAX_STORAGE_SIZE"],
            "allowed_extensions": application.config["ALLOWED_EXTENSIONS"],
        }
        with db_connection() as conn:
            for key in SETTING_KEYS:
                conn.execute(
                    "INSERT OR IGNORE INTO setting (key, value) VALUES (?, ?)",
                    (key, _serialize(key, defaults[key])),
                )
        sync_config(application)


def _load_rows() -> dict:
    with db_connection() as conn:
        rows = conn.execute("SELECT key, value FROM setting").fetchall()
    return {key: _deserialize(key, value) for key, value in rows}


def sync_config(application):
    """Copy persisted settings into app config so all readers see them."""
    settings = _load_rows()
    application.config["MAX_FILE_SIZE"] = settings["max_file_size"]
    application.config["MAX_STORAGE_SIZE"] = settings["max_storage_size"]
    application.config["ALLOWED_EXTENSIONS"] = settings["allowed_extensions"]
    application.config["MAX_CONTENT_LENGTH"] = settings["max_file_size"] + 1024 * 1024


def current_settings() -> dict:
    return {
        "max_file_bytes": current_app.config["MAX_FILE_SIZE"],
        "max_storage_bytes": current_app.config["MAX_STORAGE_SIZE"],
        "allowed_extensions": sorted(current_app.config["ALLOWED_EXTENSIONS"]),
    }


def _positive_int(payload: dict, name: str) -> int:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SettingsError(f"{name} must be a positive whole number of bytes.")
    return value


def validate_settings(payload) -> dict:
    if not isinstance(payload, dict):
        raise SettingsError("Settings must be sent as a JSON object.")

    max_file_bytes = _positive_int(payload, "max_file_bytes")
    max_storage_bytes = _positive_int(payload, "max_storage_bytes")
    if max_file_bytes > MAX_FILE_SIZE_LIMIT:
        raise SettingsError("max_file_bytes is above the supported 10 GB ceiling.")
    if max_storage_bytes > MAX_STORAGE_SIZE_LIMIT:
        raise SettingsError("max_storage_bytes is above the supported 100 GB ceiling.")
    if max_storage_bytes < max_file_bytes:
        raise SettingsError(
            "The total storage limit cannot be smaller than the per-file limit."
        )

    extensions = payload.get("allowed_extensions")
    if not isinstance(extensions, list) or not extensions:
        raise SettingsError("allowed_extensions must be a non-empty list.")
    if len(extensions) > _MAX_EXTENSIONS:
        raise SettingsError("allowed_extensions has too many entries.")

    cleaned = set()
    for extension in extensions:
        if not isinstance(extension, str):
            raise SettingsError("Every allowed extension must be a string.")
        normalized = extension.strip().casefold()
        if not _EXTENSION_PATTERN.match(normalized):
            raise SettingsError(
                f"'{extension}' is not a valid extension. Use forms like '.png'."
            )
        cleaned.add(normalized)
    if not cleaned:
        raise SettingsError("allowed_extensions must be a non-empty list.")

    return {
        "max_file_bytes": max_file_bytes,
        "max_storage_bytes": max_storage_bytes,
        "allowed_extensions": cleaned,
    }


def save_settings(payload) -> dict:
    cleaned = validate_settings(payload)
    with db_connection() as conn:
        for key in SETTING_KEYS:
            conn.execute(
                "INSERT INTO setting (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, _serialize(key, cleaned[_FIELD_BY_KEY[key]])),
            )
    sync_config(current_app)
    return current_settings()
