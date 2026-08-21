from __future__ import annotations

import importlib.util
import os
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    APP_NAME: str = "EvidentFolio"
    DEBUG: bool = False
    SECRET_KEY: str = Field(min_length=32)
    DATABASE_PATH: Path
    UPLOAD_ROOT: Path
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024
    ALLOWED_FILE_TYPES: list[str] = [
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
    TRUSTED_HOSTS: list[str] = ["localhost", "127.0.0.1", "testserver"]
    TRUSTED_PROXY_IPS: list[str] = ["127.0.0.1"]
    CORS_ORIGINS: list[str] = []
    SESSION_EXPIRE_HOURS: int = 24
    PUBLIC_BASE_URL: str = ""
    ANALYTICS_ENABLED: bool = True
    RAW_IP_STORAGE_ENABLED: bool = False
    ANALYTICS_RETENTION_DAYS: int = 365
    THUMBNAIL_WIDTHS: list[int] = [480, 960, 1440]
    VIDEO_FFMPEG_PATH: str = "ffmpeg"
    SECURE_COOKIES: bool = False
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_MINUTES: int = 15
    IP_GEOLOCATION_ENABLED: bool = True
    IP_GEOLOCATION_API_URL: str = "https://ipwho.is/{ip}"
    IP_GEOLOCATION_TIMEOUT_SECONDS: float = 2.5

    @field_validator("DATABASE_PATH", "UPLOAD_ROOT", mode="before")
    @classmethod
    def expand_path(cls, value: Any) -> Path:
        return Path(str(value)).expanduser().resolve()

    @field_validator("PUBLIC_BASE_URL")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        return value.rstrip("/")


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("portfolio_runtime_config", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"无法加载配置文件：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    configured = os.environ.get("PORTFOLIO_CONFIG")
    candidates = [
        Path(configured) if configured else None,
        Path("/app/config/config.py"),
        Path(__file__).resolve().parents[3] / "deploy" / "config" / "config.py",
    ]
    config_path = next((path for path in candidates if path and path.exists()), None)
    if config_path is None:
        checked = ", ".join(str(path) for path in candidates if path)
        raise RuntimeError(
            "缺少运行配置。请复制 deploy/config/config.example.py 为 config.py，"
            f"或通过 PORTFOLIO_CONFIG 指定路径。已检查：{checked}"
        )
    module = _load_module(config_path)
    values = {
        field_name: getattr(module, field_name)
        for field_name in Settings.model_fields
        if hasattr(module, field_name)
    }
    return Settings.model_validate(values)
