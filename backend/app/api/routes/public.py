from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import optional_admin
from app.api.response import ApiError, ok
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Asset, Category, Certificate, Project, Resume, SiteSetting, Tag
from app.repositories.projects import ProjectRepository
from app.schemas.projects import ProjectListQuery
from app.security.network import public_base_url
from app.security.asset_access import (
    cipher_material,
    is_cross_site_embed,
    is_view_only,
    issue_ticket,
    limiter,
    redeem_ticket,
    visitor,
)
from app.services.serializers import asset_dict, certificate_dict, project_dict, resume_dict
from app.file_processing.files import (
    FileValidationError,
    absolute_storage_path,
)
from app.file_processing.previews import build_safe_preview

router = APIRouter(prefix="/public", tags=["public"])


def normalize_locale(locale: str | None, request: Request) -> str:
    requested = locale or request.headers.get("accept-language", "zh-CN")
    return "en" if requested.lower().startswith("en") else "zh-CN"


def localized_settings(data: dict, locale: str) -> dict:
    if locale != "en":
        return data
    translations = data.get("translations", {})
    english = translations.get("en", {}) if isinstance(translations, dict) else {}
    def merge(original, translated):
        if isinstance(original, dict) and isinstance(translated, dict):
            return {**original, **{key: merge(original.get(key), value) for key, value in translated.items()}}
        if isinstance(original, list) and isinstance(translated, list):
            return [merge(original[index] if index < len(original) else None, value)
                    for index, value in enumerate(translated)] if translated else original
        if translated is None or isinstance(translated, str) and not translated.strip():
            return original
        return translated
    return merge(data, english) if isinstance(english, dict) else data


@router.get("/site")
def site(request: Request, locale: str | None = None, db: Session = Depends(get_db)) -> dict:
    active_locale = normalize_locale(locale, request)
    settings = db.get(SiteSetting, 1)
    categories = list(
        db.scalars(select(Category).order_by(Category.sort_order.desc(), Category.name))
    )
    tags = list(db.scalars(select(Tag).order_by(Tag.name)))
    return ok(
        request,
        {
            "settings": localized_settings(settings.data if settings else {}, active_locale),
            "categories": [
                {
                    "uuid": category.uuid,
                    "name": (category.translations.get("en", {}).get("name") or category.name) if active_locale == "en" else category.name,
                    "slug": category.slug,
                    "description": (category.translations.get("en", {}).get("description") or category.description) if active_locale == "en" else category.description,
                    "sort_order": category.sort_order,
                    "project_count": len(category.projects),
                }
                for category in categories
            ],
            "tags": [
                {
                    "uuid": tag.uuid,
                    "name": (tag.translations.get("en", {}).get("name") or tag.name) if active_locale == "en" else tag.name,
                    "slug": tag.slug,
                    "color": tag.color,
                    "project_count": len(tag.projects),
                }
                for tag in tags
            ],
            "base_url": public_base_url(request),
        },
    )


@router.get("/projects")
def projects(
    request: Request,
    q: str = "",
    category: str | None = None,
    tags: list[str] = Query(default=[]),
    featured: bool | None = None,
    sort: str = "featured",
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    locale: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    active_locale = normalize_locale(locale, request)
    query = ProjectListQuery(
        q=q,
        category=category,
        tags=tags,
        featured=featured,
        sort=sort,
        page=page,
        page_size=page_size,
        locale=active_locale,
    )
    items, total = ProjectRepository(db).list(query, public_only=True)
    return ok(
        request,
        {
            "items": [project_dict(item, detailed=False, locale=active_locale, include_content_relations=False) for item in items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            },
        },
    )


@router.get("/projects/{project_uuid}")
def project_detail(
    project_uuid: str, request: Request, locale: str | None = None, db: Session = Depends(get_db)
) -> dict:
    project = ProjectRepository(db).get_by_uuid(project_uuid)
    active_locale = normalize_locale(locale, request)
    unavailable = project and (
        (active_locale == "en" and project.content_language_mode == "single_zh")
        or (active_locale == "zh-CN" and project.content_language_mode == "single_en")
    )
    if not project or project.status != "published" or unavailable:
        raise ApiError(404, "PROJECT_NOT_FOUND", "项目不存在或尚未发布")
    return ok(request, project_dict(project, locale=active_locale, include_content_relations=False))


@router.get("/assets/{asset_uuid}")
def asset_metadata(
    asset_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(optional_admin),
    locale: str | None = None,
) -> dict:
    asset = get_accessible_asset(db, asset_uuid, bool(admin))
    return ok(request, asset_dict(asset, normalize_locale(locale, request)))


@router.get("/assets/{asset_uuid}/preview")
def asset_structured_preview(
    asset_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(optional_admin),
) -> dict:
    asset = get_accessible_asset(db, asset_uuid, bool(admin))
    if is_view_only(asset) and not admin:
        raise ApiError(403, "ASSET_VIEW_ONLY", "该资源仅可在网页中查看")
    try:
        preview = build_safe_preview(
            absolute_storage_path(asset.storage_path),
            asset.extension,
        )
    except FileValidationError as exc:
        raise ApiError(422, "PREVIEW_UNAVAILABLE", str(exc)) from exc
    return ok(request, preview)


@router.get("/assets/{asset_uuid}/content")
def asset_content(
    asset_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(optional_admin),
) -> Response:
    asset = get_accessible_asset(db, asset_uuid, bool(admin))
    if not admin:
        if is_view_only(asset):
            raise ApiError(403, "ASSET_VIEW_ONLY", "该资源仅可在网页中查看")
        if is_cross_site_embed(request):
            raise ApiError(403, "HOTLINK_FORBIDDEN", "不允许其他站点引用该资源")
        rate_limit(request, "content", get_settings().ASSET_CONTENT_REQUESTS_PER_MIN, 60)
    if "range" not in request.headers or request.headers.get("range", "").startswith("bytes=0-"):
        asset.view_count += 1
        db.commit()
    return ranged_file_response(request, asset, download=False)


@router.get("/assets/{asset_uuid}/download")
def asset_download(
    asset_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(optional_admin),
) -> Response:
    asset = get_accessible_asset(db, asset_uuid, bool(admin))
    if not admin:
        # 公开下载必须先申请签名票据；直接访问旧链接时回到资源页，由访客在页面上点击下载。
        return RedirectResponse(f"/assets/{asset.uuid}", status_code=303)
    asset.download_count += 1
    db.commit()
    return ranged_file_response(request, asset, download=True)


class TicketRequest(BaseModel):
    purpose: str = "view"
    encrypted: bool = True


@router.post("/assets/{asset_uuid}/ticket")
def asset_ticket(
    asset_uuid: str,
    payload: TicketRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(optional_admin),
) -> dict:
    """申请一张短时有效、带签名的访问票据。下载票据按 IP 每小时限量。"""
    asset = get_accessible_asset(db, asset_uuid, bool(admin))
    settings = get_settings()
    base = f"/api/v1/public/assets/{asset.uuid}/stream?t="
    if payload.purpose == "download":
        if is_view_only(asset) and not admin:
            raise ApiError(403, "ASSET_VIEW_ONLY", "该资源仅可在网页中查看，不提供下载")
        if not admin:
            rate_limit(request, "download", settings.ASSET_DOWNLOADS_PER_HOUR, 3600)
        ticket = issue_ticket(asset.uuid, "download", request)
        return ok(request, {"url": base + ticket.token, "expires_at": ticket.expires_at})
    if payload.purpose != "view":
        raise ApiError(422, "TICKET_PURPOSE_INVALID", "未知的票据用途")
    if not admin:
        rate_limit(request, "view-ticket", settings.ASSET_VIEW_TICKETS_PER_10_MIN, 600)
    if payload.encrypted and asset.size <= settings.ASSET_ENCRYPT_MAX_BYTES:
        ticket = issue_ticket(asset.uuid, "view", request)
        return ok(request, {
            "url": base + ticket.token,
            "expires_at": ticket.expires_at,
            "encrypted": True,
            "algorithm": "AES-CTR",
            "key": base64.b64encode(ticket.key or b"").decode(),
            "counter": base64.b64encode(ticket.counter or b"").decode(),
            "size": asset.size,
            "mime_type": asset.mime_type,
        })
    ticket = issue_ticket(asset.uuid, "stream", request)
    return ok(request, {"url": base + ticket.token, "expires_at": ticket.expires_at, "encrypted": False, "mime_type": asset.mime_type})


@router.get("/assets/{asset_uuid}/stream")
def asset_stream(
    asset_uuid: str,
    request: Request,
    t: str = Query(default="", max_length=200),
    db: Session = Depends(get_db),
    admin=Depends(optional_admin),
) -> Response:
    asset = get_accessible_asset(db, asset_uuid, bool(admin))
    if is_cross_site_embed(request):
        raise ApiError(403, "HOTLINK_FORBIDDEN", "不允许其他站点引用该资源")
    rate_limit(request, "content", get_settings().ASSET_CONTENT_REQUESTS_PER_MIN, 60)
    redeemed = redeem_ticket(asset.uuid, t, request)
    if not redeemed:
        raise ApiError(403, "TICKET_INVALID", "访问票据无效或已过期，请刷新页面")
    if redeemed.purpose == "download":
        if is_view_only(asset) and not admin:
            raise ApiError(403, "ASSET_VIEW_ONLY", "该资源仅可在网页中查看，不提供下载")
        if redeemed.first_use:
            asset.download_count += 1
            db.commit()
        return ranged_file_response(request, asset, download=True, cache_control="private, no-store")
    if redeemed.first_use:
        asset.view_count += 1
        db.commit()
    if redeemed.purpose == "stream":
        return ranged_file_response(request, asset, download=False, cache_control="private, no-store")
    return encrypted_response(asset, redeemed.nonce)


def rate_limit(request: Request, bucket: str, limit: int, window: int) -> None:
    if not limiter.allow(bucket, visitor(request), limit, window):
        raise ApiError(429, "RATE_LIMITED", "请求过于频繁，请稍后再试")


def encrypted_response(asset: Asset, nonce: str) -> Response:
    """以票据派生的一次性密钥做 AES-256-CTR 流式加密：长度不变，前端用 WebCrypto 解密。"""
    path = absolute_storage_path(asset.storage_path)
    key, counter = cipher_material(asset.uuid, nonce)
    size = path.stat().st_size

    def iterator():
        encryptor = Cipher(algorithms.AES(key), modes.CTR(counter)).encryptor()
        with path.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                yield encryptor.update(chunk)
        tail = encryptor.finalize()
        if tail:
            yield tail

    return StreamingResponse(
        iterator(),
        media_type="application/octet-stream",
        headers={
            "Content-Length": str(size),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
            "X-Robots-Tag": "noindex",
        },
    )


@router.get("/assets/{asset_uuid}/thumbnail")
def asset_thumbnail(
    asset_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(optional_admin),
) -> Response:
    asset = get_accessible_asset(db, asset_uuid, bool(admin))
    if not asset.thumbnail_path:
        raise ApiError(404, "THUMBNAIL_NOT_FOUND", "该资源没有缩略图")
    path = absolute_storage_path(asset.thumbnail_path)
    if not path.is_file():
        raise ApiError(404, "THUMBNAIL_NOT_FOUND", "缩略图文件不存在")
    cache_control = public_cache_control(request, asset)
    # 直接返回文件，避免旧运行镜像的内部跳转覆盖缓存策略。
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": cache_control})


@router.get("/resumes")
def resumes(request: Request, locale: str | None = None, db: Session = Depends(get_db)) -> dict:
    items = list(
        db.scalars(
            select(Resume)
            .where(Resume.is_public.is_(True))
            .options(selectinload(Resume.asset))
            .order_by(Resume.is_default.desc(), Resume.updated_at.desc())
        )
    )
    return ok(request, {"items": [resume_dict(item, normalize_locale(locale, request)) for item in items]})


@router.get("/resumes/{resume_uuid}")
def resume_detail(resume_uuid: str, request: Request, locale: str | None = None, db: Session = Depends(get_db)) -> dict:
    resume = db.scalar(
        select(Resume)
        .where(Resume.uuid == resume_uuid, Resume.is_public.is_(True))
        .options(selectinload(Resume.asset))
    )
    if not resume:
        raise ApiError(404, "RESUME_NOT_FOUND", "简历不存在或未公开")
    resume.view_count += 1
    db.commit()
    return ok(request, resume_dict(resume, normalize_locale(locale, request)))


@router.get("/certificates")
def certificates(request: Request, locale: str | None = None, db: Session = Depends(get_db)) -> dict:
    items = list(
        db.scalars(
            select(Certificate)
            .where(Certificate.is_public.is_(True))
            .options(
                selectinload(Certificate.asset),
                selectinload(Certificate.icon_asset),
                selectinload(Certificate.projects),
            )
            .order_by(Certificate.sort_order.desc(), Certificate.issued_at.desc())
        )
    )
    active_locale = normalize_locale(locale, request)
    items = [item for item in items if not ((active_locale == "en" and item.content_language_mode == "single_zh") or (active_locale == "zh-CN" and item.content_language_mode == "single_en"))]
    return ok(request, {"items": [certificate_dict(item, locale=active_locale) for item in items]})


@router.get("/certificates/{certificate_uuid}")
def certificate_detail(
    certificate_uuid: str, request: Request, locale: str | None = None, db: Session = Depends(get_db)
) -> dict:
    item = db.scalar(
        select(Certificate)
        .where(Certificate.uuid == certificate_uuid, Certificate.is_public.is_(True))
        .options(
            selectinload(Certificate.asset),
            selectinload(Certificate.icon_asset),
            selectinload(Certificate.projects),
        )
    )
    active_locale = normalize_locale(locale, request)
    unavailable = item and (
        (active_locale == "en" and item.content_language_mode == "single_zh")
        or (active_locale == "zh-CN" and item.content_language_mode == "single_en")
    )
    if not item or unavailable:
        raise ApiError(404, "CERTIFICATE_NOT_FOUND", "证书不存在或未公开")
    return ok(
        request,
        certificate_dict(
            item,
            include_projects=True,
            public_projects_only=True,
            locale=active_locale,
        ),
    )


def get_accessible_asset(db: Session, asset_uuid: str, is_admin: bool) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.uuid == asset_uuid))
    if not asset or (not asset.is_public and not is_admin):
        raise ApiError(404, "ASSET_NOT_FOUND", "资源不存在或无权访问")
    path = absolute_storage_path(asset.storage_path)
    if not path.is_file():
        raise ApiError(404, "ASSET_FILE_MISSING", "资源文件不存在")
    return asset


def public_cache_control(request: Request, asset: Asset) -> str:
    """带当前内容指纹（?v=）的公开资源可长期缓存；替换文件后指纹变化，旧缓存自然失效。"""
    if not asset.is_public:
        return "private, no-store"
    version = request.query_params.get("v", "")
    if version and asset.sha256 and version == asset.sha256[: len(version)] and len(version) >= 12:
        return "public, max-age=31536000, immutable"
    return "public, no-cache"


def ranged_file_response(
    request: Request, asset: Asset, download: bool, cache_control: str | None = None
) -> Response:
    path = absolute_storage_path(asset.storage_path)
    size = path.stat().st_size
    range_header = request.headers.get("range")
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": cache_control or public_cache_control(request, asset),
        "ETag": f'"{asset.sha256}"',
        "X-Content-Type-Options": "nosniff",
    }
    disposition = "attachment" if download else "inline"
    headers["Content-Disposition"] = (
        f"{disposition}; filename*=UTF-8''{quote(asset.display_name + asset.extension)}"
    )
    if not range_header:
        return FileResponse(
            path,
            media_type=asset.mime_type or mimetypes.guess_type(path.name)[0],
            headers=headers,
        )
    try:
        unit, raw_range = range_header.split("=", 1)
        if unit != "bytes" or "," in raw_range:
            raise ValueError
        start_text, end_text = raw_range.split("-", 1)
        if not size or (not start_text and (not end_text or int(end_text) <= 0)):
            raise ValueError
        start = int(start_text) if start_text else max(0, size - int(end_text))
        end = min(int(end_text), size - 1) if start_text and end_text else size - 1
        if start < 0 or start >= size or start > end:
            raise ValueError
    except (ValueError, TypeError):
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
    length = end - start + 1
    headers.update(
        {
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Content-Length": str(length),
        }
    )

    def iterator():
        remaining = length
        with path.open("rb") as file:
            file.seek(start)
            while remaining:
                chunk = file.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(iterator(), status_code=206, media_type=asset.mime_type, headers=headers)
