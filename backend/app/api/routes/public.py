from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
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
    return {**data, **english} if isinstance(english, dict) else data


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
                    "name": category.translations.get("en", {}).get("name", category.name) if active_locale == "en" else category.name,
                    "slug": category.slug,
                    "description": category.translations.get("en", {}).get("description", category.description) if active_locale == "en" else category.description,
                    "sort_order": category.sort_order,
                    "project_count": len(category.projects),
                }
                for category in categories
            ],
            "tags": [
                {
                    "uuid": tag.uuid,
                    "name": tag.translations.get("en", {}).get("name", tag.name) if active_locale == "en" else tag.name,
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
    page: int = 1,
    page_size: int = 12,
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
) -> dict:
    asset = get_accessible_asset(db, asset_uuid, bool(admin))
    return ok(request, asset_dict(asset))


@router.get("/assets/{asset_uuid}/preview")
def asset_structured_preview(
    asset_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(optional_admin),
) -> dict:
    asset = get_accessible_asset(db, asset_uuid, bool(admin))
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
    asset.download_count += 1
    db.commit()
    return ranged_file_response(request, asset, download=True)


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
    cache_control = "public, max-age=604800, stale-while-revalidate=86400"
    if request.headers.get("x-accel-supported") == "1":
        return Response(
            status_code=200,
            media_type="image/webp",
            headers={
                "X-Accel-Redirect": f"/_protected_thumbnails/{path.name}",
                "Cache-Control": cache_control,
            },
        )
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": cache_control})


@router.get("/resumes")
def resumes(request: Request, db: Session = Depends(get_db)) -> dict:
    items = list(
        db.scalars(
            select(Resume)
            .where(Resume.is_public.is_(True))
            .options(selectinload(Resume.asset))
            .order_by(Resume.is_default.desc(), Resume.updated_at.desc())
        )
    )
    return ok(request, {"items": [resume_dict(item) for item in items]})


@router.get("/resumes/{resume_uuid}")
def resume_detail(resume_uuid: str, request: Request, db: Session = Depends(get_db)) -> dict:
    resume = db.scalar(
        select(Resume)
        .where(Resume.uuid == resume_uuid, Resume.is_public.is_(True))
        .options(selectinload(Resume.asset))
    )
    if not resume:
        raise ApiError(404, "RESUME_NOT_FOUND", "简历不存在或未公开")
    resume.view_count += 1
    db.commit()
    return ok(request, resume_dict(resume))


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


def ranged_file_response(request: Request, asset: Asset, download: bool) -> Response:
    path = absolute_storage_path(asset.storage_path)
    size = path.stat().st_size
    range_header = request.headers.get("range")
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600" if asset.is_public else "private, no-store",
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
        start = int(start_text) if start_text else max(0, size - int(end_text))
        end = int(end_text) if end_text else size - 1
        if start < 0 or end >= size or start > end:
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
