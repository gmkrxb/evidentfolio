from __future__ import annotations

import io
import sys
from pathlib import Path

import fitz
from PIL import Image


def render_thumbnail(source: Path, destination: Path, scale: float = 1.5) -> None:
    with fitz.open(source) as document:
        if document.page_count < 1:
            raise ValueError("PDF does not contain a page")
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        png_data = pixmap.tobytes("png")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(png_data)) as preview:
        rgb_preview = preview.convert("RGB")
        try:
            rgb_preview.save(destination, "WEBP", quality=84, method=6)
        finally:
            rgb_preview.close()


def main() -> int:
    if len(sys.argv) not in {3, 4}:
        print(
            "usage: pdf_thumbnail_worker.py SOURCE DESTINATION [SCALE]",
            file=sys.stderr,
        )
        return 64
    try:
        scale = float(sys.argv[3]) if len(sys.argv) == 4 else 1.5
        if not 0.5 <= scale <= 2.0:
            raise ValueError("scale must be between 0.5 and 2.0")
        render_thumbnail(Path(sys.argv[1]), Path(sys.argv[2]), scale)
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
