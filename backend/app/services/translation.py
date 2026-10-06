from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SiteSetting, Project, ProjectSection, ProjectAlbum, Category, Tag, Asset, Certificate, Resume, ProjectLink, ProjectAsset, ProjectAlbumAsset
from app.services.ai import AIServiceError, PROTECTED_FIELDS, TRANSLATION_PROMPT

SITE_FIELDS = ['site_name', 'person_name', 'headline', 'bio', 'current_identity', 'research_directions', 'location', 'footer_text', 'footer_eyebrow', 'footer_heading', 'hero_eyebrow', 'hero_focus_label', 'hero_focus_value', 'default_seo_title', 'default_seo_description', 'navigation_items', 'home_stats', 'home_capabilities', 'contact_methods', 'page_content', 'home_copy']
PROJECT_FIELDS = ['title', 'subtitle', 'summary', 'content', 'background', 'problem', 'solution', 'architecture', 'role', 'contributions', 'outcomes', 'seo_title', 'seo_description']
REGISTRY = {
    'site': (SiteSetting, '网站文案', SITE_FIELDS),
    'project': (Project, '项目', PROJECT_FIELDS),
    'section': (ProjectSection, '项目章节', ['title', 'body']),
    'album': (ProjectAlbum, '项目相册', ['title', 'description']),
    'link': (ProjectLink, '项目链接', ['label']),
    'project_caption': (ProjectAsset, '附件说明', ['caption']),
    'album_caption': (ProjectAlbumAsset, '相册说明', ['caption']),
    'category': (Category, '分类', ['name', 'description']),
    'tag': (Tag, '标签', ['name']),
    'certificate': (Certificate, '证书', ['name', 'issuer', 'description']),
    'asset': (Asset, '附件信息', ['display_name', 'description']),
    'resume': (Resume, '简历名称', ['name']),
}
LABELS = {'title':'标题','subtitle':'副标题','summary':'摘要','content':'正文','body':'正文','description':'说明','name':'名称','label':'标签','caption':'图注','headline':'个人介绍','bio':'简介','person_name':'姓名','site_name':'站点名称','issuer':'颁发机构','background':'背景','problem':'问题','solution':'方案','architecture':'架构','contributions':'贡献','outcomes':'成果','role':'角色','display_name':'展示名称','seo_title':'SEO 标题','seo_description':'SEO 描述','research_directions':'研究方向','navigation_items':'导航','home_stats':'首页数据','home_capabilities':'能力','contact_methods':'联系方式','page_content':'页面文案','home_copy':'首页文案'}
LABELS.update({'current_identity': '当前身份', 'location': '地区', 'footer_text': '页脚说明', 'footer_eyebrow': '页脚引题', 'footer_heading': '页脚标题', 'hero_eyebrow': '首页引题', 'hero_focus_label': '关注方向标签', 'hero_focus_value': '关注方向', 'default_seo_title': '默认 SEO 标题', 'default_seo_description': '默认 SEO 描述', 'projects_eyebrow': '项目引题', 'projects_title': '项目标题', 'projects_description': '项目说明', 'capabilities_eyebrow': '能力引题', 'capabilities_title': '能力标题', 'capabilities_description': '能力说明', 'categories_eyebrow': '分类引题', 'categories_title': '分类标题', 'contact_eyebrow': '联系引题', 'contact_description': '联系说明', 'hero_title': '页面标题', 'hero_description': '页面说明', 'eyebrow': '引题', 'empty_title': '空状态标题', 'empty_description': '空状态说明', 'projects': '项目页', 'certificates': '证书页', 'resumes': '简历页', 'contact': '联系页'})


def leaves(value: object, path: tuple = ()) -> dict[tuple, str]:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key not in PROTECTED_FIELDS:
                result.update(leaves(item, (*path, key)))
        return result
    if isinstance(value, list):
        return {key: text for index, item in enumerate(value) for key, text in leaves(item, (*path, index)).items()}
    return {path: value} if isinstance(value, str) and value.strip() else {}


def preserve_without_source(source, result, existing):
    # 空白原文不代表删除目标内容。
    if isinstance(source, dict):
        old = existing if isinstance(existing, dict) else {}
        return {**deepcopy(old), **{key: preserve_without_source(value, result[key], old.get(key))
                                  if key not in PROTECTED_FIELDS else result[key]
                                  for key, value in source.items()}}
    if isinstance(source, list):
        old = existing if isinstance(existing, list) else []
        return [preserve_without_source(value, result[index], old[index] if index < len(old) else None)
                for index, value in enumerate(source)] if source else deepcopy(old)
    if isinstance(source, str) and not source.strip():
        return existing if isinstance(existing, str) else source
    return result


def partial_fields(text: str, source: dict) -> list[dict]:
    """解析已返回的 JSON 字段，包括尚未闭合的字符串。"""
    expected = leaves(source)
    found = {}
    start = text.find('{')
    if start < 0:
        return []
    decoder = json.JSONDecoder()
    index = start
    def whitespace():
        nonlocal index
        while index < len(text) and text[index].isspace():
            index += 1
    def value(path):
        nonlocal index
        whitespace()
        if index >= len(text):
            return False
        char = text[index]
        if char in '{[':
            index += 1
            array = char == '['
            offset = 0
            while index < len(text):
                whitespace()
                if index < len(text) and text[index] == (']' if array else '}'):
                    index += 1
                    return True
                if array:
                    key = offset
                else:
                    try:
                        key, end = decoder.raw_decode(text, index)
                    except ValueError:
                        return False
                    if not isinstance(key, str):
                        return False
                    index = end
                    whitespace()
                    if index >= len(text) or text[index] != ':':
                        return False
                    index += 1
                if not value((*path, key)):
                    return False
                offset += 1
                whitespace()
                if index < len(text) and text[index] == ',':
                    index += 1
                elif index < len(text) and text[index] in '}]':
                    continue
                else:
                    return False
            return False
        try:
            item, end = decoder.raw_decode(text, index)
            if path in expected and isinstance(item, str):
                found[path] = (item, True)
            index = end
            return True
        except ValueError:
            if char == '"' and path in expected:
                raw = text[index + 1:]
                # 未闭合的转义序列留待后续分片。
                for cut in range(min(7, len(raw)) + 1):
                    try:
                        found[path] = (json.loads('"' + (raw[:-cut] if cut else raw) + '"'), False)
                        break
                    except ValueError:
                        pass
            return False
    value(())
    # 部分兼容接口会额外包裹 content。
    if not found and re.match(r'\{\s*"content"\s*:', text[start:]):
        inner = text.find('{', start + 1)
        if inner >= 0:
            return partial_fields(text[inner:], source)
    return [{'path': '.'.join(map(str, path)), 'label': ' / '.join(LABELS.get(str(part), str(part + 1) if isinstance(part, int) else str(part)) for part in path), 'text': content, 'done': done} for path, (content, done) in found.items()]


def snapshot(item, kind):
    fields = REGISTRY[kind][2]
    if kind == 'site':
        base = deepcopy(item.data or {})
        target = deepcopy(base.get('translations', {}).get('en', {}))
        return {key: base[key] for key in fields if key in base}, target
    return {key: deepcopy(getattr(item, key)) for key in fields}, deepcopy((item.translations or {}).get('en', {}))


def fingerprint(base, target):
    return hashlib.sha256(json.dumps([base, target], ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def reference_pairs(source: dict, target: dict, kind: str) -> list[dict]:
    translated = leaves(target)
    return [{'module': kind, 'field': '.'.join(map(str, path)), 'source': value, 'target': translated[path]}
            for path, value in leaves(source).items() if path in translated]


def saved_references(db: Session, source_locale: str) -> list[dict]:
    result = []
    for kind, (model, _, _) in REGISTRY.items():
        for item in db.scalars(select(model).order_by(model.id)):
            base, english = snapshot(item, kind)
            source, target = (english, base) if source_locale == 'en' else (base, english)
            result.extend(reference_pairs(source, target, kind))
    return result


def translation_request(content: dict, source_locale: str, kind: str, limit: int,
                        references: list[dict], recent: list[dict] | None = None,
                        existing: dict | None = None) -> tuple[str, dict]:
    """当前正文完整保留，参考按相关性和新近程度装入窗口。"""
    payload = {'source_locale': source_locale, 'target_locale': 'zh-CN' if source_locale == 'en' else 'en',
               'content': content, 'reference_translations': []}
    encode = lambda value: json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    used = len(TRANSLATION_PROMPT) + len(encode(payload))
    if used > limit:
        raise AIServiceError(f'本项正文需 {used} 字符，超过上下文上限 {limit}；请增大窗口或拆分内容后重试')
    candidates = reference_pairs(content, existing or {}, kind)
    candidates += [item for item in reversed(recent or []) if item['module'] == kind]
    candidates += [item for item in references if item['module'] == kind]
    candidates += list(reversed(recent or [])) + references
    seen = set()
    selected = []
    for item in candidates:
        identity = item['source']
        if identity in seen:
            continue
        seen.add(identity)
        size = len(encode(item)) + bool(selected)
        if used + size > limit:
            continue
        selected.append(item)
        used += size
    payload['reference_translations'] = selected
    return encode(payload), {'chars': used, 'limit': limit, 'references': len(selected)}


def roll_references(recent: list[dict], added: list[dict], limit: int) -> list[dict]:
    retained, used = [], 0
    for item in reversed(recent + added):
        size = len(json.dumps(item, ensure_ascii=False))
        if used + size <= limit:
            retained.append(item)
            used += size
    return list(reversed(retained))


def build_plan(db: Session, source_locale: str, overwrite: bool, only: list[str] | None = None) -> list[dict]:
    tasks = []
    for kind, (model, module, fields) in REGISTRY.items():
        for item in db.scalars(select(model).order_by(model.id)):
            key = f'{kind}:{item.id}'
            if only is not None and key not in only:
                continue
            base, english = snapshot(item, kind)
            source, target = (english, base) if source_locale == 'en' else (base, english)
            source = {field: source[field] for field in fields if field in source and leaves(source[field])}
            if not overwrite:
                source = {field: value for field, value in source.items() if not leaves(target.get(field)) or set(leaves(value)) - set(leaves(target.get(field)))}
            if not source:
                continue
            title = str(base.get('title') or base.get('name') or base.get('display_name') or base.get('label') or module)
            parent = getattr(item, 'project', None)
            if parent is not None:
                title = f'{parent.title} · {title}'
            tasks.append({'id':key,'kind':kind,'record_id':item.id,'module':module,'title':title,'content':source,'total':len(leaves(source)),'fingerprint':fingerprint(base,english), 'existing':target, 'overwrite':overwrite})
    return tasks


def fill_missing(existing, incoming):
    if isinstance(incoming, dict):
        old = existing if isinstance(existing, dict) else {}
        return {**old, **{key: fill_missing(old.get(key), value) for key, value in incoming.items()}}
    if isinstance(incoming, list):
        old = existing if isinstance(existing, list) else []
        return [fill_missing(old[index] if index < len(old) else None, value) for index, value in enumerate(incoming)]
    return existing if existing not in (None, "", []) else incoming


def apply_translation(db: Session, task: dict, result: dict, source_locale: str):
    model = REGISTRY[task['kind']][0]
    item = db.get(model, task['record_id'])
    if item is None or fingerprint(*snapshot(item, task['kind'])) != task['fingerprint']:
        raise AIServiceError('内容已被其他操作修改，本项未写入，请刷新后重试')
    if not task['overwrite']:
        result = {key: fill_missing(task['existing'].get(key), value) for key, value in result.items()}
    if task['kind'] == 'site':
        data = deepcopy(item.data or {})
        if source_locale == 'en':
            data.update(result)
        else:
            data['translations'] = {**data.get('translations', {}), 'en': {**data.get('translations', {}).get('en', {}), **result}}
        item.data = data
    elif source_locale == 'en':
        for key, value in result.items():
            setattr(item, key, value)
    else:
        item.translations = {**(item.translations or {}), 'en': {**(item.translations or {}).get('en', {}), **result}}
    # 提供目标语言内容，不自动改变发布状态。
    if hasattr(item, 'content_language_mode'):
        item.content_language_mode = 'bilingual'
    return item
