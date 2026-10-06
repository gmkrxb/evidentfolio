"""从部署配置写入双语联系方式，不改动其他网站内容。"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


def read_profile(path: Path) -> dict:
    profile = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError("联系信息必须是 JSON 对象")
    for field in ("email", "phone", "github"):
        value = profile.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 320:
            raise ValueError(f"联系信息缺少有效的 {field}")
        profile[field] = value.strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", profile["email"]):
        raise ValueError("邮箱格式不正确")
    if not re.fullmatch(r"\+?[\d ()-]{5,30}", profile["phone"]):
        raise ValueError("电话号码格式不正确")
    phone = re.sub(r"[^\d+]", "", profile["phone"])
    if not re.fullmatch(r"\+?\d{5,20}", phone):
        raise ValueError("电话号码位数不正确")
    url = urlsplit(profile["github"])
    if (url.scheme != "https" or url.netloc != "github.com"
            or not re.fullmatch(r"/[A-Za-z0-9-]+/?", url.path) or url.query or url.fragment):
        raise ValueError("GitHub 地址需要是 https://github.com/用户名/")
    address = profile.get("address")
    if not isinstance(address, dict):
        raise ValueError("请提供中英文地址")
    for locale in ("zh-CN", "en"):
        value = address.get(locale)
        if not isinstance(value, str) or not value.strip() or len(value) > 1000:
            raise ValueError(f"缺少有效的 {locale} 地址")
        address[locale] = value.strip()
    return profile


def contact_methods(profile: dict, locale: str) -> list[dict]:
    english = locale == "en"
    phone = re.sub(r"[^\d+]", "", profile["phone"])
    values = [
        ("email", "Email" if english else "邮箱", profile["email"], f"mailto:{profile['email']}", "Message"),
        ("phone", "Phone" if english else "电话", profile["phone"], f"tel:{phone}", "Phone"),
        ("location", "Address" if english else "地址", profile["address"][locale], "", "Location"),
        ("github", "GitHub", profile["github"].removeprefix("https://").rstrip("/"), profile["github"], "Github"),
    ]
    return [{"type": kind, "label": label, "value": value, "url": url,
             "description": "", "icon_name": icon, "icon_asset_uuid": "", "icon_svg": ""}
            for kind, label, value, url, icon in values]


def merge_contacts(current: object, desired: list[dict]) -> list[dict]:
    if current is not None and not isinstance(current, list):
        raise ValueError("已有联系方式不是列表，未进行覆盖")
    kinds = {item["type"] for item in desired}
    # 清理空白占位，保留微信等其他类型。
    other = [deepcopy(item) for item in (current or [])
             if isinstance(item, dict) and item.get("type") not in kinds
             and (str(item.get("value") or "").strip() or str(item.get("url") or "").strip())]
    return deepcopy(desired) + other


def configure_contacts(profile: dict) -> bool:
    from app.core.database import get_session_factory
    from app.models import SiteSetting

    with get_session_factory()() as db, db.begin():
        settings = db.get(SiteSetting, 1)
        if settings is None or not isinstance(settings.data, dict):
            raise ValueError("网站设置尚未初始化，未写入联系信息")
        data = deepcopy(settings.data)
        translations = data.setdefault("translations", {})
        if not isinstance(translations, dict):
            raise ValueError("已有翻译数据格式不正确，未进行覆盖")
        english = translations.setdefault("en", {})
        if not isinstance(english, dict):
            raise ValueError("已有英文设置格式不正确，未进行覆盖")
        original_contacts = data.get("contact_methods")
        data["contact_methods"] = merge_contacts(original_contacts, contact_methods(profile, "zh-CN"))
        english["contact_methods"] = merge_contacts(english.get("contact_methods", original_contacts), contact_methods(profile, "en"))
        for target in (data, english):
            target["email"] = profile["email"]
            target["github_url"] = profile["github"]
        changed = data != settings.data
        if changed:
            settings.data = data
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--check", action="store_true", help="只检查配置，不连接数据库")
    args = parser.parse_args()
    try:
        profile = read_profile(args.profile)
        if args.check:
            print("联系信息核对通过：邮箱、电话、地址、GitHub。")
        else:
            changed = configure_contacts(profile)
            print("四项双语联系方式及图标已写入。" if changed else "联系信息已一致，无需重复写入。")
    except (OSError, ValueError) as exc:
        raise SystemExit(f"联系信息处理失败：{exc}") from exc


if __name__ == "__main__":
    main()
