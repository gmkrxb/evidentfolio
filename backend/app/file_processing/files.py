from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings


logger = logging.getLogger(__name__)
_PDF_RENDER_SEMAPHORE = threading.BoundedSemaphore(value=1)
_PDF_RENDER_SCALES = (1.5, 1.0)

BLOCKED_EXTENSIONS = {
    ".exe",
    ".dll",
    ".bat",
    ".cmd",
    ".com",
    ".msi",
    ".ps1",
    ".sh",
    ".php",
    ".py",
    ".cgi",
    ".pl",
    ".jar",
    ".html",
    ".htm",
    ".js",
    ".mjs",
}
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".xml", ".log"}
OFFICE_MIME_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class FileValidationError(ValueError):
    pass


@dataclass
class ProcessedFile:
    original_name: str
    display_name: str
    storage_name: str
    mime_type: str
    extension: str
    size: int
    sha256: str
    category: str
    storage_path: str
    thumbnail_path: str | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None


def safe_original_name(filename: str | None) -> str:
    raw = Path(filename or "file").name
    cleaned = re.sub(r"[\x00-\x1f<>:\"/\\|?*]+", "_", raw).strip(" .")
    return cleaned[:255] or "file"


def category_for(mime: str, extension: str) -> str:
    if mime.startswith("image/"):
        return "images"
    if mime.startswith("video/"):
        return "videos"
    if mime.startswith("audio/"):
        return "audio"
    if mime in {"application/zip", "application/x-zip-compressed"}:
        return "archives"
    if mime == "application/pdf":
        return "documents"
    if extension in TEXT_EXTENSIONS or mime.startswith("text/"):
        return "text"
    return "documents"


def ffprobe_path(ffmpeg_path: str) -> str:
    executable = Path(ffmpeg_path)
    probe_name = executable.name.replace("ffmpeg", "ffprobe", 1)
    return str(executable.with_name(probe_name))


def sniff_mime(path: Path, declared: str, extension: str) -> str:
    header = path.read_bytes()[:32]
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    if b"ftyp" in header[:16]:
        return "audio/mp4" if extension in {".m4a", ".aac"} else "video/mp4"
    if header.startswith(b"ID3") or (
        len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0
    ):
        return "audio/mpeg"
    if header.startswith(b"OggS"):
        return "audio/ogg"
    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "audio/wav"
    if header.startswith(b"PK\x03\x04"):
        if extension in OFFICE_MIME_TYPES:
            return OFFICE_MIME_TYPES[extension]
        if extension == ".zip":
            return "application/zip"
    guessed = mimetypes.guess_type(f"file{extension}")[0]
    if extension in TEXT_EXTENSIONS:
        try:
            path.read_text(encoding="utf-8")
            return guessed or "text/plain"
        except UnicodeDecodeError as exc:
            raise FileValidationError("文本文件必须使用 UTF-8 编码") from exc
    return declared or guessed or "application/octet-stream"


async def save_and_process(upload: UploadFile, preferred_category: str | None = None) -> ProcessedFile:
    settings = get_settings()
    original_name = safe_original_name(upload.filename)
    extension = Path(original_name).suffix.lower()
    if extension in BLOCKED_EXTENSIONS:
        raise FileValidationError("不允许上传可执行或可在浏览器执行的文件")
    temp_dir = settings.UPLOAD_ROOT / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}.upload"
    size = 0
    hasher = hashlib.sha256()
    try:
        with temp_path.open("xb") as target:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE:
                    raise FileValidationError(
                        f"文件超过 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB 限制"
                    )
                target.write(chunk)
                hasher.update(chunk)
        mime = sniff_mime(temp_path, upload.content_type or "", extension)
        if mime not in settings.ALLOWED_FILE_TYPES:
            raise FileValidationError(f"不允许的文件类型：{mime}")
        category = preferred_category or category_for(mime, extension)
        if category == "resumes" and mime != "application/pdf":
            raise FileValidationError("简历只允许 PDF 文件")
        storage_name = f"{uuid.uuid4()}{extension}"
        destination_dir = settings.UPLOAD_ROOT / category
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / storage_name
        os.replace(temp_path, destination)
        result = ProcessedFile(
            original_name=original_name,
            display_name=Path(original_name).stem,
            storage_name=storage_name,
            mime_type=mime,
            extension=extension,
            size=size,
            sha256=hasher.hexdigest(),
            category=category,
            storage_path=str(destination.relative_to(settings.UPLOAD_ROOT).as_posix()),
        )
        await run_in_threadpool(_inspect_and_thumbnail, destination, result)
        return result
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _inspect_and_thumbnail(path: Path, result: ProcessedFile) -> None:
    settings = get_settings()
    thumbnail_dir = settings.UPLOAD_ROOT / "thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    if result.mime_type.startswith("image/"):
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                result.width, result.height = image.size
                thumb = image.convert("RGB")
                thumb.thumbnail((960, 960))
                thumb_path = thumbnail_dir / f"{Path(result.storage_name).stem}.webp"
                thumb.save(thumb_path, "WEBP", quality=84, method=6)
                result.thumbnail_path = str(
                    thumb_path.relative_to(settings.UPLOAD_ROOT).as_posix()
                )
        except (UnidentifiedImageError, OSError) as exc:
            path.unlink(missing_ok=True)
            raise FileValidationError("图片无法安全解码") from exc
    elif result.mime_type == "application/pdf":
        thumb_path = thumbnail_dir / f"{Path(result.storage_name).stem}.webp"
        temporary_thumb = thumbnail_dir / (
            f".{Path(result.storage_name).stem}.{uuid.uuid4().hex}.tmp.webp"
        )
        try:
            with _PDF_RENDER_SEMAPHORE:
                _render_pdf_thumbnail_with_fallback(path, temporary_thumb)
            os.replace(temporary_thumb, thumb_path)
            result.thumbnail_path = str(
                thumb_path.relative_to(settings.UPLOAD_ROOT).as_posix()
            )
        except FileValidationError:
            path.unlink(missing_ok=True)
            raise
        except (subprocess.TimeoutExpired, OSError) as exc:
            path.unlink(missing_ok=True)
            logger.warning("PDF thumbnail worker execution failed: %s", exc)
            raise FileValidationError("PDF 预览生成超时或处理程序不可用") from exc
        except Exception as exc:
            path.unlink(missing_ok=True)
            logger.exception("Unexpected PDF thumbnail processing failure")
            raise FileValidationError("PDF 文件损坏或格式无效") from exc
        finally:
            temporary_thumb.unlink(missing_ok=True)
    elif result.mime_type.startswith("video/"):
        command = [
            ffprobe_path(settings.VIDEO_FFMPEG_PATH),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        try:
            probe = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
            metadata = json.loads(probe.stdout)
            video_stream = next(
                stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "video"
            )
            result.width = int(video_stream.get("width") or 0) or None
            result.height = int(video_stream.get("height") or 0) or None
            result.duration = float(metadata.get("format", {}).get("duration") or 0) or None
            thumb_path = thumbnail_dir / f"{Path(result.storage_name).stem}.webp"
            subprocess.run(
                [
                    settings.VIDEO_FFMPEG_PATH,
                    "-y",
                    "-ss",
                    "00:00:01",
                    "-i",
                    str(path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale='min(960,iw)':-2",
                    str(thumb_path),
                ],
                capture_output=True,
                check=True,
                timeout=60,
            )
            result.thumbnail_path = str(
                thumb_path.relative_to(settings.UPLOAD_ROOT).as_posix()
            )
        except (subprocess.SubprocessError, StopIteration, ValueError, json.JSONDecodeError) as exc:
            path.unlink(missing_ok=True)
            raise FileValidationError("视频元信息校验失败") from exc
    elif result.mime_type.startswith("audio/"):
        command = [
            ffprobe_path(settings.VIDEO_FFMPEG_PATH),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        try:
            probe = subprocess.run(
                command, capture_output=True, text=True, check=True, timeout=30
            )
            metadata = json.loads(probe.stdout)
            if not any(
                stream.get("codec_type") == "audio"
                for stream in metadata.get("streams", [])
            ):
                raise FileValidationError("音频文件不包含有效音轨")
            result.duration = (
                float(metadata.get("format", {}).get("duration") or 0) or None
            )
        except (
            subprocess.SubprocessError,
            ValueError,
            json.JSONDecodeError,
            FileValidationError,
        ) as exc:
            path.unlink(missing_ok=True)
            if isinstance(exc, FileValidationError):
                raise
            raise FileValidationError("音频元信息校验失败") from exc
    elif result.mime_type in {
        "application/zip",
        "application/x-zip-compressed",
        *OFFICE_MIME_TYPES.values(),
    }:
        try:
            with zipfile.ZipFile(path) as archive:
                bad_file = archive.testzip()
                if bad_file:
                    raise FileValidationError("压缩文件包含损坏条目")
                if result.extension in OFFICE_MIME_TYPES:
                    names = set(archive.namelist())
                    if "[Content_Types].xml" not in names:
                        raise FileValidationError("Office 文档结构无效")
        except (zipfile.BadZipFile, OSError, FileValidationError) as exc:
            path.unlink(missing_ok=True)
            if isinstance(exc, FileValidationError):
                raise
            raise FileValidationError("压缩文件损坏或格式无效") from exc


def _render_pdf_thumbnail_with_fallback(source: Path, destination: Path) -> None:
    worker_script = Path(__file__).with_name("pdf_thumbnail_worker.py")
    failures: list[str] = []
    for attempt, scale in enumerate(_PDF_RENDER_SCALES, start=1):
        destination.unlink(missing_ok=True)
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(worker_script),
                    str(source),
                    str(destination),
                    str(scale),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=45,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            failures.append(f"PyMuPDF attempt {attempt}: {exc}")
            continue
        if completed.returncode == 0 and destination.is_file():
            if attempt > 1:
                logger.info("PDF thumbnail succeeded on retry %s", attempt)
            return
        failures.append(
            f"PyMuPDF attempt {attempt}: returncode={completed.returncode} "
            f"stderr={completed.stderr.strip()[-300:]}"
        )

    destination.unlink(missing_ok=True)
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        prefix = destination.with_suffix("")
        png_path = Path(f"{prefix}.png")
        png_path.unlink(missing_ok=True)
        try:
            completed = subprocess.run(
                [
                    pdftoppm,
                    "-f",
                    "1",
                    "-l",
                    "1",
                    "-singlefile",
                    "-scale-to",
                    "960",
                    "-png",
                    str(source),
                    str(prefix),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=45,
            )
            if completed.returncode == 0 and png_path.is_file():
                with Image.open(png_path) as preview:
                    rgb_preview = preview.convert("RGB")
                    try:
                        rgb_preview.save(destination, "WEBP", quality=82, method=6)
                    finally:
                        rgb_preview.close()
                if destination.is_file():
                    logger.info("PDF thumbnail rendered with Poppler fallback")
                    return
            failures.append(
                f"Poppler: returncode={completed.returncode} "
                f"stderr={completed.stderr.strip()[-300:]}"
            )
        except (subprocess.TimeoutExpired, OSError, UnidentifiedImageError) as exc:
            failures.append(f"Poppler: {exc}")
        finally:
            png_path.unlink(missing_ok=True)

    logger.warning("All PDF thumbnail renderers failed: %s", " | ".join(failures))
    raise FileValidationError("PDF 两次渲染及备用引擎均未能生成安全预览")


def absolute_storage_path(relative_path: str) -> Path:
    root = get_settings().UPLOAD_ROOT.resolve()
    candidate = (root / relative_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise FileValidationError("非法存储路径")
    return candidate


def delete_asset_files(storage_path: str, thumbnail_path: str | None) -> None:
    absolute_storage_path(storage_path).unlink(missing_ok=True)
    if thumbnail_path:
        absolute_storage_path(thumbnail_path).unlink(missing_ok=True)
