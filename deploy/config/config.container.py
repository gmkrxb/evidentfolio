"""Environment-backed configuration used by the published all-in-one image.

It does not read a .env file. Operators may still override it by mounting the
regular Python config and setting PORTFOLIO_CONFIG=/app/config/config.py.
"""
from __future__ import annotations

import os
from pathlib import Path


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


_STORAGE_ROOT = Path(os.environ.get("EVIDENTFOLIO_STORAGE_ROOT", "/app")).resolve()

APP_NAME = os.environ.get("EVIDENTFOLIO_APP_NAME", "EvidentFolio")
DEBUG = False
SECRET_KEY = _required("EVIDENTFOLIO_SECRET_KEY")
DATABASE_PATH = _STORAGE_ROOT / "data" / "portfolio.db"
UPLOAD_ROOT = _STORAGE_ROOT / "uploads"
MAX_UPLOAD_SIZE = int(os.environ.get("EVIDENTFOLIO_MAX_UPLOAD_SIZE", 200 * 1024 * 1024))
ALLOWED_FILE_TYPES = [
    "image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4", "video/webm",
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "application/pdf",
    "application/zip", "application/x-zip-compressed",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain", "text/markdown", "application/json", "text/csv", "application/yaml", "text/yaml",
]
TRUSTED_HOSTS = _list("EVIDENTFOLIO_TRUSTED_HOSTS", "localhost,127.0.0.1,*.onrender.com")
TRUSTED_PROXY_IPS = _list("EVIDENTFOLIO_TRUSTED_PROXY_IPS", "127.0.0.1,172.16.0.0/12")
CORS_ORIGINS = _list("EVIDENTFOLIO_CORS_ORIGINS")
SESSION_EXPIRE_HOURS = int(os.environ.get("EVIDENTFOLIO_SESSION_EXPIRE_HOURS", "24"))
PUBLIC_BASE_URL = os.environ.get("EVIDENTFOLIO_PUBLIC_BASE_URL", "").rstrip("/")
ANALYTICS_ENABLED = os.environ.get("EVIDENTFOLIO_ANALYTICS_ENABLED", "true").lower() == "true"
RAW_IP_STORAGE_ENABLED = False
ANALYTICS_RETENTION_DAYS = int(os.environ.get("EVIDENTFOLIO_ANALYTICS_RETENTION_DAYS", "365"))
THUMBNAIL_WIDTHS = [480, 960, 1440]
VIDEO_FFMPEG_PATH = "/usr/bin/ffmpeg"
SECURE_COOKIES = os.environ.get("EVIDENTFOLIO_SECURE_COOKIES", "true").lower() == "true"
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_MINUTES = 15
IP_GEOLOCATION_ENABLED = os.environ.get("EVIDENTFOLIO_IP_GEOLOCATION_ENABLED", "true").lower() == "true"
IP_GEOLOCATION_API_URL = os.environ.get("EVIDENTFOLIO_IP_GEOLOCATION_API_URL", "https://ipwho.is/{ip}")
IP_GEOLOCATION_TIMEOUT_SECONDS = 2.5
