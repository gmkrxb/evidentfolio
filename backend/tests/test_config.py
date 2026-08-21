import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_ROOT = Path(
    os.environ.get(
        "PORTFOLIO_TEST_RUNTIME",
        str(_ROOT / "backend" / "tests" / ".runtime"),
    )
)

APP_NAME = "Portfolio Test"
DEBUG = False
SECRET_KEY = "test-secret-key-with-at-least-thirty-two-characters"
DATABASE_PATH = _RUNTIME_ROOT / "test.db"
UPLOAD_ROOT = _RUNTIME_ROOT / "uploads"
MAX_UPLOAD_SIZE = 2 * 1024 * 1024
ALLOWED_FILE_TYPES = [
    "image/png",
    "image/jpeg",
    "application/pdf",
    "application/zip",
    "text/plain",
    "text/markdown",
    "application/json",
    "text/csv",
    "application/yaml",
    "text/yaml",
]
TRUSTED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
TRUSTED_PROXY_IPS = ["testclient"]
CORS_ORIGINS = []
SESSION_EXPIRE_HOURS = 1
PUBLIC_BASE_URL = ""
ANALYTICS_ENABLED = True
RAW_IP_STORAGE_ENABLED = False
ANALYTICS_RETENTION_DAYS = 30
THUMBNAIL_WIDTHS = [480]
VIDEO_FFMPEG_PATH = "ffmpeg"
SECURE_COOKIES = False
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_MINUTES = 15
IP_GEOLOCATION_ENABLED = False
IP_GEOLOCATION_API_URL = "https://ipwho.is/{ip}"
IP_GEOLOCATION_TIMEOUT_SECONDS = 0.2
