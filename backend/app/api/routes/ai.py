from __future__ import annotations

import json
import threading
import logging
import time

import fitz
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.api.audit import write_audit
from app.api.dependencies import require_admin, require_csrf
from app.api.response import ApiError, ok
from app.core.database import get_db, get_session_factory
from app.file_processing.files import absolute_storage_path
from app.models import AISetting, AdminUser, Asset, Certificate, SiteSetting
from app.schemas.ai import AIConfigInput, AIModelsInput, AIResumeApplyInput, AIResumeParseInput, AITranslateInput, AIBatchTranslateInput
from app.schemas.projects import ProjectInput
from app.services.ai import (
    AIServiceError,
    RESUME_PROMPT,
    TRANSLATION_PROMPT,
    decrypt_api_key,
    encrypt_api_key,
    fetch_models,
    parse_json_output,
    stream_chat,
    validate_translation,
)
from app.services.projects import ProjectService
from app.services.translation import build_plan, apply_translation, partial_fields, leaves, saved_references, translation_request, reference_pairs, roll_references, snapshot, preserve_without_source

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


def setting_or_error(db: Session) -> tuple[AISetting, str]:
    setting = db.get(AISetting, 1)
    if not setting or not setting.enabled or not setting.base_url or not setting.model:
        raise ApiError(409, "AI_NOT_CONFIGURED", "请先完成并启用 AI 配置")
    try:
        key = decrypt_api_key(setting.encrypted_api_key)
    except AIServiceError as exc:
        raise ApiError(409, "AI_KEY_INVALID", str(exc)) from exc
    if not key:
        raise ApiError(409, "AI_KEY_MISSING", "AI API Key 未配置")
    return setting, key


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.get("/config")
def get_config(request: Request, db: Session = Depends(get_db), _: AdminUser = Depends(require_admin)) -> dict:
    item = db.get(AISetting, 1)
    return ok(request, {
        "base_url": item.base_url if item else "",
        "model": item.model if item else "",
        "enabled": item.enabled if item else False,
        "has_api_key": bool(item and item.encrypted_api_key),
        "max_context_chars": item.max_context_chars if item else 32000,
    })


@router.put("/config")
def save_config(payload: AIConfigInput, request: Request, db: Session = Depends(get_db), user: AdminUser = Depends(require_csrf)) -> dict:
    item = db.get(AISetting, 1)
    if item is None:
        item = AISetting(id=1)
        db.add(item)
    item.base_url = str(payload.base_url).rstrip("/")
    item.model = payload.model.strip()
    item.enabled = payload.enabled
    item.max_context_chars = payload.max_context_chars
    if payload.api_key:
        item.encrypted_api_key = encrypt_api_key(payload.api_key)
    write_audit(db, request, user, "ai.config.update", "ai_setting", "1")
    db.commit()
    return ok(request, {"base_url": item.base_url, "model": item.model, "enabled": item.enabled, "has_api_key": bool(item.encrypted_api_key), "max_context_chars": item.max_context_chars}, "AI 配置已保存")


@router.post("/models")
async def models(payload: AIModelsInput, request: Request, db: Session = Depends(get_db), _: AdminUser = Depends(require_csrf)) -> dict:
    item = db.get(AISetting, 1)
    base_url = str(payload.base_url).rstrip("/") if payload.base_url else (item.base_url if item else "")
    key = payload.api_key or (decrypt_api_key(item.encrypted_api_key) if item else "")
    if not base_url or not key:
        raise ApiError(422, "AI_CONFIG_INCOMPLETE", "请填写 API URL 和 API Key")
    try:
        items = await fetch_models(base_url, key)
    except AIServiceError as exc:
        raise ApiError(502, "AI_MODELS_FAILED", str(exc)) from exc
    return ok(request, {"items": items})


async def run_stream(db: Session, system: str, user: str, source: dict | None = None, translation: AITranslateInput | None = None):
    try:
        with get_session_factory()() as active_db:
            setting, key = setting_or_error(active_db)
            base_url, model = setting.base_url, setting.model
            context = None
            if translation is not None:
                limit = translation.max_context_chars or getattr(setting, 'max_context_chars', 32000)
                user, context = translation_request(translation.content, translation.source_locale, translation.entity_type,
                    limit, saved_references(active_db, translation.source_locale), existing=translation.existing_translation)
        complete = ""
        last_progress = 0.0
        yield sse({"type": "started"})
        if context is not None:
            yield sse({"type": "context", **context})
        async for event in stream_chat(base_url, key, model, system, user):
            if event["type"] == "content":
                complete += event["content"]
            yield sse(event)
            if source is not None and event["type"] == "content" and time.monotonic() - last_progress >= .08:
                last_progress = time.monotonic()
                fields = partial_fields(complete, source)
                yield sse({"type": "fields", "fields": fields, "completed": sum(item["done"] for item in fields), "total": len(leaves(source))})
        result = parse_json_output(complete)
        if source is not None:
            if not source.keys() <= result.keys() and isinstance(result.get("content"), dict):
                result = result["content"]
            result = validate_translation(source, result)
            if translation is not None:
                result = preserve_without_source(source, result, translation.existing_translation)
            fields = partial_fields(json.dumps(result, ensure_ascii=False), source)
            yield sse({"type": "fields", "fields": fields, "completed": len(fields), "total": len(leaves(source))})
        yield sse({"type": "result", "data": result})
        yield sse({"type": "done"})
    except (AIServiceError, ApiError) as exc:
        message = exc.message if isinstance(exc, ApiError) else str(exc)
        yield sse({"type": "error", "message": message})


@router.post("/translate/stream")
def translate_stream(payload: AITranslateInput, db: Session = Depends(get_db), _: AdminUser = Depends(require_csrf)) -> StreamingResponse:
    if not leaves(payload.content):
        raise ApiError(422, "TRANSLATION_SOURCE_EMPTY", "当前语言没有可翻译的内容，请先填写原文或切换语言")
    user = json.dumps({"source_locale": payload.source_locale, "target_locale": payload.target_locale, "entity_type": payload.entity_type, "content": payload.content}, ensure_ascii=False)
    return StreamingResponse(run_stream(db, TRANSLATION_PROMPT, user, payload.content, payload), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/resume/parse/stream")
def parse_resume(payload: AIResumeParseInput, db: Session = Depends(get_db), _: AdminUser = Depends(require_csrf)) -> StreamingResponse:
    asset = db.scalar(select(Asset).where(Asset.uuid == payload.asset_uuid))
    if not asset or asset.mime_type != "application/pdf":
        raise ApiError(422, "RESUME_PDF_REQUIRED", "请选择资源库中的 PDF 简历")
    path = absolute_storage_path(asset.storage_path)
    try:
        with fitz.open(path) as document:
            text = "\n".join(page.get_text("text") for page in document)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ApiError(422, "RESUME_READ_FAILED", "无法读取该 PDF 简历") from exc
    if not text.strip():
        raise ApiError(422, "RESUME_TEXT_EMPTY", "PDF 未提取到文本，请使用可搜索文字版简历")
    user = json.dumps({"source_locale": payload.source_locale, "resume_text": text[:120_000]}, ensure_ascii=False)
    return StreamingResponse(run_stream(db, RESUME_PROMPT, user), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/resume/apply")
def apply_resume(payload: AIResumeApplyInput, request: Request, db: Session = Depends(get_db), user: AdminUser = Depends(require_csrf)) -> dict:
    result = payload.result
    profile = result.get("profile") if isinstance(result.get("profile"), dict) else {}
    settings = db.get(SiteSetting, 1)
    if settings is None:
        settings = SiteSetting(id=1, data={})
        db.add(settings)
    allowed_profile = {key: profile.get(key) for key in ["person_name", "headline", "bio", "current_identity", "location", "email", "research_directions"] if profile.get(key) not in (None, "", [])}
    settings.data = {**(settings.data or {}), **allowed_profile}
    projects_created = 0
    for raw in result.get("projects", []) if isinstance(result.get("projects"), list) else []:
        if not isinstance(raw, dict) or not raw.get("title"):
            continue
        project_state = str(raw.get("project_state") or "completed")
        if project_state not in {"active", "completed", "research"}:
            project_state = "completed"
        project = ProjectInput(
            title=str(raw.get("title")), subtitle=str(raw.get("subtitle", "")),
            summary=str(raw.get("summary") or raw.get("subtitle") or raw.get("title")),
            background=str(raw.get("background", "")), problem=str(raw.get("problem", "")),
            solution=str(raw.get("solution", "")), architecture=str(raw.get("architecture", "")),
            contributions=list(raw.get("contributions") or []), technologies=list(raw.get("technologies") or []),
            outcomes=list(raw.get("outcomes") or []), start_date=str(raw.get("start_date", "")),
            end_date=str(raw.get("end_date", "")), role=str(raw.get("role", "")),
            project_state=project_state, status="draft",
        )
        ProjectService(db).create(project, commit=False)
        projects_created += 1
    certificates_created = 0
    for raw in result.get("certificates", []) if isinstance(result.get("certificates"), list) else []:
        if not isinstance(raw, dict) or not raw.get("name"):
            continue
        certificate_type = str(raw.get("certificate_type") or "other")
        if certificate_type not in {"scholarship", "competition", "patent", "course", "other"}:
            certificate_type = "other"
        db.add(Certificate(name=str(raw["name"]), issuer=str(raw.get("issuer", "")), certificate_type=certificate_type, issued_at=str(raw.get("issued_at", "")), description=str(raw.get("description", "")), is_public=False))
        certificates_created += 1
    write_audit(db, request, user, "ai.resume.apply", "site_setting", "site", {"projects": projects_created, "certificates": certificates_created})
    db.commit()
    return ok(request, {"projects_created": projects_created, "certificates_created": certificates_created}, "简历草稿已导入")


_BATCH_LOCK = threading.Lock()


@router.post("/translate/plan")
def translation_plan(payload: AIBatchTranslateInput, request: Request, db: Session = Depends(get_db), _: AdminUser = Depends(require_csrf)):
    setting_or_error(db)
    tasks = build_plan(db, payload.source_locale, payload.overwrite, payload.only)
    return ok(request, {"items": [{key: task[key] for key in ("id", "module", "title", "total")} for task in tasks], "total_fields": sum(task["total"] for task in tasks)})


async def batch_translation(payload: AIBatchTranslateInput, request: Request, admin_id: int):
    if not _BATCH_LOCK.acquire(blocking=False):
        yield sse({"type": "error", "message": "已有全站翻译正在运行，请稍后重试"})
        return
    try:
        with get_session_factory()() as db:
            setting, key = setting_or_error(db)
            base_url, model = setting.base_url, setting.model
            tasks = build_plan(db, payload.source_locale, payload.overwrite, payload.only)
            references = saved_references(db, payload.source_locale)
            context_limit = payload.max_context_chars or getattr(setting, 'max_context_chars', 32000)
        yield sse({"type": "plan", "items": [{key: task[key] for key in ("id", "module", "title", "total")} for task in tasks]})
        saved, failed = 0, 0
        recent = []
        for task in tasks:
            if await request.is_disconnected():
                return
            yield sse({"type": "task_started", "id": task["id"], "module": task["module"], "title": task["title"], "total": task["total"]})
            try:
                content = ""
                last_progress = 0.0
                user, context = translation_request(task['content'], payload.source_locale, task['kind'], context_limit,
                    references, recent, task['existing'])
                yield sse({"type": "context", **context})
                async for event in stream_chat(base_url, key, model, TRANSLATION_PROMPT, user):
                    if await request.is_disconnected():
                        return
                    if event["type"] == "content":
                        content += event["content"]
                    yield sse(event)
                    if event["type"] == "content" and time.monotonic() - last_progress >= .08:
                        last_progress = time.monotonic()
                        fields = partial_fields(content, task["content"])
                        yield sse({"type": "fields", "fields": fields, "completed": sum(item["done"] for item in fields), "total": task["total"]})
                result = parse_json_output(content)
                if not task["content"].keys() <= result.keys() and isinstance(result.get("content"), dict):
                    result = result["content"]
                result = validate_translation(task["content"], result)
                result = preserve_without_source(task['content'], result, {key: task['existing'].get(key) for key in task['content']})
                fields = partial_fields(json.dumps(result, ensure_ascii=False), task['content'])
                yield sse({"type": "fields", "fields": fields, "completed": len(fields), "total": task['total']})
                if await request.is_disconnected():
                    return
                with get_session_factory()() as db:
                    # SQLite 写锁内核对快照，防止多进程之间覆盖并发编辑。
                    db.connection().exec_driver_sql('BEGIN IMMEDIATE')
                    item = apply_translation(db, task, result, payload.source_locale)
                    base, english = snapshot(item, task['kind'])
                    saved_translation = base if payload.source_locale == 'en' else english
                    admin = db.get(AdminUser, admin_id)
                    write_audit(db, request, admin, "ai.translate.apply", task["kind"], str(task["record_id"]))
                    db.commit()
                recent = roll_references(recent, reference_pairs(task['content'], saved_translation, task['kind']), context_limit)
                saved += 1
                yield sse({"type": "task_done", "id": task["id"]})
            except (AIServiceError, ApiError) as exc:
                failed += 1
                yield sse({"type": "task_error", "id": task["id"], "message": str(exc)})
            except SQLAlchemyError:
                logging.getLogger(__name__).exception('翻译保存失败')
                failed += 1
                yield sse({"type": "task_error", "id": task["id"], "message": "保存失败，本项未写入，请稍后重试"})
        yield sse({"type": "done", "saved": saved, "failed": failed})
    except (AIServiceError, ApiError) as exc:
        yield sse({"type": "error", "message": str(exc)})
    finally:
        _BATCH_LOCK.release()


@router.post("/translate/batch/stream")
def translate_batch(payload: AIBatchTranslateInput, request: Request, user: AdminUser = Depends(require_csrf)):
    return StreamingResponse(batch_translation(payload, request, user.id), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
