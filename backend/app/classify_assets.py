from __future__ import annotations

import re

from sqlalchemy import select

from app.core.database import get_session_factory
from app.models import Asset, AssetFolder


FOLDERS = [
    ("简历", "中文、英文、学术和技术简历", 10),
    ("论文", "论文全文、投稿版本和相关文档", 20),
    ("论文插图", "论文页面图、Figure、以 p+页码命名的图片", 30),
    ("专利", "专利全文、公开文本及页面", 40),
    ("获奖证书", "竞赛获奖证书与荣誉证明", 50),
    ("奖学金", "奖学金证书、截图和证明", 60),
    ("项目媒体", "项目截图、架构图及演示媒体", 70),
    ("其他文档", "尚未归入专门类别的文档和附件", 80),
]


def choose_folder(asset: Asset) -> str:
    name = f"{asset.display_name} {asset.original_name}".lower()
    if asset.category == "resumes" or "简历" in name:
        return "简历"
    if "奖学金" in name:
        return "奖学金"
    if "专利" in name or re.search(r"\bcn\d{6,}", name):
        return "专利"
    if asset.mime_type.startswith("image/") and (
        re.search(r"(?:^|[-_ ])p(?:age)?[-_ ]?\d+\b", name)
        or "figure" in name
        or "论文插图" in name
    ):
        return "论文插图"
    if "论文" in name or "paper" in name:
        return "论文"
    if any(keyword in name for keyword in ("大赛", "竞赛", "特等奖", "一等奖", "二等奖", "三等奖", "证书")):
        return "获奖证书"
    if asset.mime_type.startswith(("image/", "video/", "audio/")):
        return "项目媒体"
    return "其他文档"


def main() -> None:
    session = get_session_factory()()
    try:
        existing = {
            folder.name: folder for folder in session.scalars(select(AssetFolder))
        }
        for name, description, sort_order in FOLDERS:
            folder = existing.get(name)
            if folder is None:
                folder = AssetFolder(
                    name=name,
                    description=description,
                    sort_order=sort_order,
                )
                session.add(folder)
                existing[name] = folder
            else:
                folder.description = description
                folder.sort_order = sort_order
        session.flush()

        counts: dict[str, int] = {name: 0 for name, _, _ in FOLDERS}
        for asset in session.scalars(select(Asset).order_by(Asset.id)):
            folder_name = choose_folder(asset)
            asset.folder = existing[folder_name]
            counts[folder_name] += 1
        session.commit()
        print("Asset folders classified:", counts)
    finally:
        session.close()


if __name__ == "__main__":
    main()
