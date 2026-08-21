from __future__ import annotations

import json

import fitz
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.dependencies import require_admin, require_csrf
from app.api.response import ApiError, ok
from app.core.database import get_db
from app.file_processing.files import absolute_storage_path
from app.models import AISetting, AdminUser, Asset, Certificate, SiteSetting
from app.schemas.ai import AIConfigInput, AIModelsInput, AIResumeApplyInput, AIResumeParseInput, AITranslateInput
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
)
from app.services.projects import ProjectService

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
    if payload.api_key:
        item.encrypted_api_key = encrypt_api_key(payload.api_key)
    write_audit(db, request, user, "ai.config.update", "ai_setting", "1")
    db.commit()
    return ok(request, {"base_url": item.base_url, "model": item.model, "enabled": item.enabled, "has_api_key": bool(item.encrypted_api_key)}, "AI 配置已保存")


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


async def run_stream(db: Session, system: str, user: str):
    try:
        setting, key = setting_or_error(db)
        complete = ""
        yield sse({"type": "started"})
        async for event in stream_chat(setting.base_url, key, setting.model, system, user):
            if event["type"] == "content":
                complete += event["content"]
            yield sse(event)
        result = parse_json_output(complete)
        yield sse({"type": "result", "data": result})
        yield sse({"type": "done"})
    except (AIServiceError, ApiError) as exc:
        message = exc.message if isinstance(exc, ApiError) else str(exc)
        yield sse({"type": "error", "message": message})


@router.post("/translate/stream")
def translate_stream(payload: AITranslateInput, db: Session = Depends(get_db), _: AdminUser = Depends(require_csrf)) -> StreamingResponse:
    user = json.dumps({"source_locale": payload.source_locale, "target_locale": payload.target_locale, "entity_type": payload.entity_type, "content": payload.content}, ensure_ascii=False)
    return StreamingResponse(run_stream(db, TRANSLATION_PROMPT, user), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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
