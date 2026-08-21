from __future__ import annotations

import xml.etree.ElementTree as ET


class SvgValidationError(ValueError):
    pass


ALLOWED_TAGS = {
    "svg",
    "g",
    "path",
    "circle",
    "ellipse",
    "rect",
    "line",
    "polyline",
    "polygon",
}
ALLOWED_ATTRIBUTES = {
    "viewBox",
    "width",
    "height",
    "fill",
    "fill-rule",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
    "stroke-dasharray",
    "stroke-dashoffset",
    "opacity",
    "d",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "points",
    "transform",
}


def sanitize_svg(source: str) -> str:
    value = source.strip()
    if not value:
        return ""
    if len(value) > 20_000:
        raise SvgValidationError("SVG 代码过长")
    try:
        root = ET.fromstring(value)
    except ET.ParseError as exc:
        raise SvgValidationError("SVG 代码不是有效的 XML") from exc
    if root.tag.split("}")[-1] != "svg":
        raise SvgValidationError("图标代码必须以 svg 元素为根节点")
    for element in root.iter():
        name = element.tag.split("}")[-1]
        if name not in ALLOWED_TAGS:
            raise SvgValidationError(f"SVG 包含不允许的元素：{name}")
        element.tag = name
        for attribute in list(element.attrib):
            plain_name = attribute.split("}")[-1]
            lowered = plain_name.lower()
            value_text = element.attrib[attribute].lower()
            if (
                plain_name not in ALLOWED_ATTRIBUTES
                or lowered.startswith("on")
                or "javascript:" in value_text
                or "url(" in value_text
            ):
                del element.attrib[attribute]
    root.set("aria-hidden", "true")
    root.set("focusable", "false")
    return ET.tostring(root, encoding="unicode", short_empty_elements=True)

