"""EvidentFolio runtime configuration.

Copy this file to config.py, generate a new SECRET_KEY, and mount it read-only
into the API container. This is executable Python configuration, not a .env file.
"""
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent
_APP_ROOT = Path("/app") if _CONFIG_DIR == Path("/app/config") else _CONFIG_DIR.parents[1]

APP_NAME = "EvidentFolio"
DEBUG = False
SECRET_KEY = "replace-with-at-least-32-random-characters"
DATABASE_PATH = _APP_ROOT / "data" / "portfolio.db"
UPLOAD_ROOT = _APP_ROOT / "uploads"
MAX_UPLOAD_SIZE = 200 * 1024 * 1024
ALLOWED_FILE_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "video/webm",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/mp4",
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/markdown",
    "application/json",
    "text/csv",
    "application/yaml",
    "text/yaml",
]
TRUSTED_HOSTS = ["localhost", "127.0.0.1", "testserver", "your-domain.example"]
TRUSTED_PROXY_IPS = ["127.0.0.1", "172.16.0.0/12"]
CORS_ORIGINS = []
SESSION_EXPIRE_HOURS = 24
PUBLIC_BASE_URL = ""
ANALYTICS_ENABLED = True
RAW_IP_STORAGE_ENABLED = False
ANALYTICS_RETENTION_DAYS = 365
THUMBNAIL_WIDTHS = [480, 960, 1440]
VIDEO_FFMPEG_PATH = "/usr/bin/ffmpeg"
SECURE_COOKIES = False
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_MINUTES = 15
IP_GEOLOCATION_ENABLED = True
IP_GEOLOCATION_API_URL = "https://ipwho.is/{ip}"
IP_GEOLOCATION_TIMEOUT_SECONDS = 2.5
