from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from app.file_processing.files import FileValidationError


MAX_PREVIEW_MEMBER_SIZE = 5 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 500
MAX_PREVIEW_LINES = 1200


def _safe_member_bytes(archive: zipfile.ZipFile, name: str) -> bytes:
    try:
        info = archive.getinfo(name)
    except KeyError:
        return b""
    if info.file_size > MAX_PREVIEW_MEMBER_SIZE:
        raise FileValidationError("文档预览内容过大，请下载原文件查看")
    return archive.read(info)


def _xml_text_lines(content: bytes, text_tag_suffix: str = "}t") -> list[str]:
    if not content:
        return []
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise FileValidationError("文档 XML 结构无效") from exc
    lines: list[str] = []
    for element in root.iter():
        if element.tag.endswith(text_tag_suffix) and element.text:
            text = re.sub(r"\s+", " ", element.text).strip()
            if text:
                lines.append(text)
        if len(lines) >= MAX_PREVIEW_LINES:
            break
    return lines


def build_safe_preview(path: Path, extension: str) -> dict:
    extension = extension.lower()
    if extension not in {".zip", ".docx", ".xlsx", ".pptx"}:
        raise FileValidationError("该资源没有结构化预览")
    try:
        with zipfile.ZipFile(path) as archive:
            if extension == ".zip":
                entries = []
                for info in archive.infolist()[:MAX_ARCHIVE_ENTRIES]:
                    entries.append(
                        {
                            "name": Path(info.filename).as_posix(),
                            "size": info.file_size,
                            "compressed_size": info.compress_size,
                            "is_directory": info.is_dir(),
                        }
                    )
                return {
                    "kind": "archive",
                    "entry_count": len(archive.infolist()),
                    "entries": entries,
                    "truncated": len(archive.infolist()) > MAX_ARCHIVE_ENTRIES,
                }

            sections: list[dict] = []
            if extension == ".docx":
                lines = _xml_text_lines(
                    _safe_member_bytes(archive, "word/document.xml")
                )
                sections.append({"title": "文档正文", "lines": lines})
            elif extension == ".pptx":
                slide_names = sorted(
                    (
                        name
                        for name in archive.namelist()
                        if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
                    ),
                    key=lambda name: int(re.search(r"\d+", name).group()),  # type: ignore[union-attr]
                )
                for index, name in enumerate(slide_names[:100], start=1):
                    sections.append(
                        {
                            "title": f"第 {index} 页",
                            "lines": _xml_text_lines(_safe_member_bytes(archive, name)),
                        }
                    )
            elif extension == ".xlsx":
                workbook = _safe_member_bytes(archive, "xl/workbook.xml")
                sheet_names: list[str] = []
                if workbook:
                    root = ElementTree.fromstring(workbook)
                    sheet_names = [
                        element.attrib.get("name", f"工作表 {index + 1}")
                        for index, element in enumerate(root.iter())
                        if element.tag.endswith("}sheet")
                    ]
                shared = _xml_text_lines(
                    _safe_member_bytes(archive, "xl/sharedStrings.xml")
                )
                sections.append(
                    {
                        "title": "工作表",
                        "lines": sheet_names or ["未读取到工作表名称"],
                    }
                )
                if shared:
                    sections.append({"title": "文本内容", "lines": shared})
            return {"kind": "office", "sections": sections}
    except (zipfile.BadZipFile, OSError, ElementTree.ParseError) as exc:
        raise FileValidationError("文件无法生成安全预览") from exc
