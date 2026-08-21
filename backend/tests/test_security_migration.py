from __future__ import annotations

import os
import subprocess
import sys
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy.pool import QueuePool

from app.core.database import get_engine
from app.file_processing.files import FileValidationError, absolute_storage_path, ffprobe_path


def test_path_traversal_is_rejected() -> None:
    with pytest.raises(FileValidationError):
        absolute_storage_path("../../outside.txt")


def test_sqlite_uses_bounded_queue_pool() -> None:
    engine = get_engine()
    assert isinstance(engine.pool, QueuePool)
    assert engine.pool.size() == 5


def test_ffprobe_path_only_changes_executable_name() -> None:
    windows_style = "C:/ffmpeg/bin/ffmpeg.exe"
    posix_style = "/usr/bin/ffmpeg"
    assert ffprobe_path(windows_style) == str(
        Path(windows_style).with_name("ffprobe.exe")
    )
    assert ffprobe_path(posix_style) == str(
        Path(posix_style).with_name("ffprobe")
    )


def test_alembic_upgrades_empty_database(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    config_path = tmp_path / "migration_config.py"
    database_path = tmp_path / "migration.db"
    upload_path = tmp_path / "uploads"
    config_path.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "APP_NAME='Migration Test'",
                "DEBUG=False",
                "SECRET_KEY='migration-test-secret-with-thirty-two-characters'",
                f"DATABASE_PATH=Path({str(database_path)!r})",
                f"UPLOAD_ROOT=Path({str(upload_path)!r})",
                "TRUSTED_HOSTS=['testserver']",
                "TRUSTED_PROXY_IPS=[]",
                "CORS_ORIGINS=[]",
                "PUBLIC_BASE_URL=''",
                "VIDEO_FFMPEG_PATH='ffmpeg'",
            ]
        ),
        encoding="utf-8",
    )
    environment = {**os.environ, "PORTFOLIO_CONFIG": str(config_path)}
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    assert database_path.is_file()
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260821_0005"
        assert connection.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM resumes").fetchone()[0] == 0


def test_startup_upgrades_previous_database_and_keeps_content(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    config_path = tmp_path / "upgrade_config.py"
    database_path = tmp_path / "portfolio.db"
    upload_path = tmp_path / "uploads"
    config_path.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "APP_NAME='Upgrade Test'",
                "DEBUG=False",
                "SECRET_KEY='upgrade-test-secret-with-thirty-two-characters'",
                f"DATABASE_PATH=Path({str(database_path)!r})",
                f"UPLOAD_ROOT=Path({str(upload_path)!r})",
                "TRUSTED_HOSTS=['testserver']",
                "TRUSTED_PROXY_IPS=[]",
                "CORS_ORIGINS=[]",
                "PUBLIC_BASE_URL=''",
                f"VIDEO_FFMPEG_PATH={sys.executable!r}",
            ]
        ),
        encoding="utf-8",
    )
    environment = {**os.environ, "PORTFOLIO_CONFIG": str(config_path)}

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *arguments], cwd=backend_root, env=environment,
            capture_output=True, text=True, timeout=60,
        )

    previous = run("-m", "alembic", "-c", "alembic.ini", "upgrade", "20260731_0004")
    assert previous.returncode == 0, previous.stderr
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO site_settings (id, data, created_at, updated_at) VALUES (1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ('{\"site_name\": \"Preserved\"}',),
        )
        connection.commit()

    preflight = run("-m", "app.startup", "preflight")
    assert preflight.returncode == 0, preflight.stderr
    assert (database_path.parent / "migration-backups" / "portfolio.before-20260731_0004.db").is_file()
    upgraded = run("-m", "alembic", "-c", "alembic.ini", "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr
    postflight = run("-m", "app.startup", "postflight")
    assert postflight.returncode == 0, postflight.stderr

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260821_0005"
        assert "Preserved" in connection.execute("SELECT data FROM site_settings WHERE id=1").fetchone()[0]
