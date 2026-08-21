from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path

from app.core.config import get_settings


def _database_revision(connection: sqlite3.Connection) -> str:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
    ).fetchone()
    if not exists:
        return "legacy"
    row = connection.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
    return str(row[0]) if row else "legacy"


def _check_database(database_path: Path, *, foreign_keys: bool = False) -> str:
    with sqlite3.connect(database_path) as connection:
        quick_check = connection.execute("PRAGMA quick_check").fetchone()
        if not quick_check or quick_check[0] != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {quick_check}")
        if foreign_keys:
            violations = connection.execute("PRAGMA foreign_key_check").fetchmany(10)
            if violations:
                raise RuntimeError(f"SQLite foreign-key check failed: {violations}")
        return _database_revision(connection)


def _backup_before_migration(database_path: Path, revision: str) -> Path:
    backup_root = database_path.parent / "migration-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    safe_revision = "".join(character for character in revision if character.isalnum() or character in "-_")
    backup_path = backup_root / f"{database_path.stem}.before-{safe_revision or 'legacy'}.db"
    if backup_path.exists():
        return backup_path
    temporary = backup_path.with_suffix(".db.tmp")
    source = sqlite3.connect(database_path)
    target = sqlite3.connect(temporary)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    temporary.replace(backup_path)
    return backup_path


def _check_writable(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    marker = path / ".evidentfolio-write-check"
    marker.write_text("ok", encoding="utf-8")
    marker.unlink(missing_ok=True)


def preflight() -> None:
    settings = get_settings()
    settings.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _check_writable(settings.DATABASE_PATH.parent)
    _check_writable(settings.UPLOAD_ROOT)
    if settings.DATABASE_PATH.exists():
        revision = _check_database(settings.DATABASE_PATH)
        backup = _backup_before_migration(settings.DATABASE_PATH, revision)
        print(f"Database preflight passed; migration backup: {backup}")
    else:
        print("No database found; Alembic will create an empty database.")


def postflight() -> None:
    settings = get_settings()
    if not settings.DATABASE_PATH.exists():
        raise RuntimeError("Database migration completed without creating the configured database")
    revision = _check_database(settings.DATABASE_PATH, foreign_keys=True)
    ffmpeg = Path(settings.VIDEO_FFMPEG_PATH)
    if not ffmpeg.is_file() and shutil.which(settings.VIDEO_FFMPEG_PATH) is None:
        raise RuntimeError(f"Configured ffmpeg executable was not found: {ffmpeg}")
    print(f"Startup checks passed; database revision: {revision}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EvidentFolio startup checks")
    parser.add_argument("phase", choices=("preflight", "postflight"))
    args = parser.parse_args()
    preflight() if args.phase == "preflight" else postflight()


if __name__ == "__main__":
    main()
