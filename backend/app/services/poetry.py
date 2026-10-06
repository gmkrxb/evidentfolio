"""首页默认诗句与通用版块文案：初始化与迁移时写入空缺字段，之后完全由后台维护。"""
from __future__ import annotations

from copy import deepcopy

MANIFESTO = {
    "zh-CN": "结构，是重力写下的诗。\n数据，是时间留下的痕迹。\n我想让机器学会倾听——\n在钢与混凝土的沉默里，找到可以被证明的答案。",
    "en": "Structure is a poem written by gravity.\nData is the trace that time leaves behind.\nI teach machines to listen —\nto find, in the silence of steel and concrete, answers that can be proven.",
}
CLOSING = {
    "zh-CN": "愿每一座结构都被理解，\n每一个结论都有据可依。",
    "en": "May every structure be understood,\nand every conclusion rest on evidence.",
}
FOOTER_QUOTE = {
    "zh-CN": "万物皆有其理，结构是理的形状。",
    "en": "All things have their pattern; structure is the shape it takes.",
}
# 通用的版块文案（不含任何个人信息），只在为空时作为起点。
SITE_COPY = {
    "hero_eyebrow": {"zh-CN": "AI · 土木 · 信息", "en": "AI · Civil · Information"},
    "footer_eyebrow": {"zh-CN": "来信", "en": "Correspondence"},
    "footer_heading": {"zh-CN": "一起建造，可以被证明的未来。", "en": "Let us build what can be proven."},
}
HOME_COPY = {
    "manifesto": MANIFESTO,
    "closing": CLOSING,
    "footer_quote": FOOTER_QUOTE,
    "capabilities_eyebrow": {"zh-CN": "方法", "en": "Method"},
    "capabilities_title": {"zh-CN": "从力学，到语言。", "en": "From mechanics, to language."},
    "projects_eyebrow": {"zh-CN": "作品", "en": "Work"},
    "projects_title": {"zh-CN": "作品，是思考留下的结构。", "en": "Work is the structure thought leaves behind."},
    "categories_eyebrow": {"zh-CN": "方向", "en": "Directions"},
    "categories_title": {"zh-CN": "探索更多方向。", "en": "Explore the directions."},
    "contact_eyebrow": {"zh-CN": "来信", "en": "Correspondence"},
    "agents_eyebrow": {"zh-CN": "协作", "en": "Agents"},
    "agents_title": {"zh-CN": "让智能体，彼此校验。", "en": "Agents that check one another."},
    "agents_description": {
        "zh-CN": "感知、检索、推理、校验与执行，各司其职；每一个结论，都要回到原始数据接受另一位智能体的检验。",
        "en": "Perception, retrieval, reasoning, verification and action — each claim must survive another agent’s check against the raw data.",
    },
}


def _blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def with_default_poetry(data: dict | None) -> tuple[dict, bool]:
    """只填补空缺的宣言与寄语，绝不覆盖已有文字。返回 (新数据, 是否有改动)。"""
    result = deepcopy(data) if isinstance(data, dict) else {}
    primary = "en" if result.get("primary_language") == "en" else "zh-CN"
    changed = False
    home_copy = result.get("home_copy") if isinstance(result.get("home_copy"), dict) else {}
    for key, text in HOME_COPY.items():
        if _blank(home_copy.get(key)):
            home_copy[key] = text[primary]
            changed = True
    result["home_copy"] = home_copy
    for key, text in SITE_COPY.items():
        if _blank(result.get(key)):
            result[key] = text[primary]
            changed = True
    if primary == "zh-CN":
        translations = result.get("translations") if isinstance(result.get("translations"), dict) else {}
        english = translations.get("en") if isinstance(translations.get("en"), dict) else {}
        english_copy = english.get("home_copy") if isinstance(english.get("home_copy"), dict) else {}
        for key, text in HOME_COPY.items():
            if _blank(english_copy.get(key)):
                english_copy[key] = text["en"]
                changed = True
        english["home_copy"] = english_copy
        for key, text in SITE_COPY.items():
            if _blank(english.get(key)):
                english[key] = text["en"]
                changed = True
        translations["en"] = english
        result["translations"] = translations
    return result, changed
