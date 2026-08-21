from __future__ import annotations

import re
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.analytics.service import overview
from app.api.audit import write_audit
from app.api.dependencies import require_admin, require_csrf
from app.api.response import ApiError, ok
from app.core.config import get_settings
from app.core.database import get_db
from app.core.time import utcnow
from app.file_processing.files import (
    FileValidationError,
    delete_asset_files,
    save_and_process,
)
from app.models import (
    AdminUser,
    AnalyticsEvent,
    Asset,
    AssetFolder,
    AuditLog,
    Category,
    Certificate,
    Project,
    ProjectAlbum,
    ProjectAsset,
    Resume,
    SiteSetting,
    Tag,
    Visitor,
    VisitorSession,
)
from app.repositories.projects import ProjectRepository
from app.schemas.assets import (
    AssetPatch,
    AssetBatchMoveInput,
    AssetFolderInput,
    CertificateInput,
    CertificatePatch,
    ResumeInput,
    ResumePatch,
)
from app.schemas.projects import ProjectInput, ProjectListQuery
from app.services.projects import ProjectService
from app.services.serializers import asset_dict, certificate_dict, project_dict, resume_dict
from app.security.svg import SvgValidationError, sanitize_svg

router = APIRouter(prefix="/admin", tags=["admin"])


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value.lower()).strip("-")
    return slug or "item"


def asset_folder_dict(folder: AssetFolder) -> dict:
    path: list[dict[str, str]] = []
    cursor: AssetFolder | None = folder
    while cursor is not None:
        path.insert(0, {"uuid": cursor.uuid, "name": cursor.name})
        cursor = cursor.parent
    return {
        "uuid": folder.uuid,
        "name": folder.name,
        "description": folder.description,
        "sort_order": folder.sort_order,
        "parent_uuid": folder.parent.uuid if folder.parent else None,
        "asset_count": len(folder.assets),
        "child_count": len(folder.children),
        "path": path,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
    }


def asset_dependencies(db: Session, asset: Asset) -> dict:
    projects: list[dict] = []
    for project in db.scalars(
        select(Project).options(
            selectinload(Project.assets).selectinload(ProjectAsset.asset),
            selectinload(Project.albums).selectinload(ProjectAlbum.assets),
            selectinload(Project.sections),
        )
    ).unique():
        usage_count = 0
        if project.cover_asset_id == asset.id:
            usage_count += 1
        usage_count += sum(1 for relation in project.assets if relation.asset_id == asset.id)
        usage_count += sum(
            1
            for album in project.albums
            for relation in album.assets
            if relation.asset_id == asset.id
        )
        usage_count += sum(
            section.asset_uuids.count(asset.uuid) for section in project.sections
        )
        if usage_count:
            projects.append(
                {
                    "uuid": project.uuid,
                    "title": project.title,
                    "usage_count": usage_count,
                }
            )
    certificates = [
        {"uuid": item.uuid, "name": item.name}
        for item in db.scalars(
            select(Certificate).where(
                or_(
                    Certificate.asset_id == asset.id,
                    Certificate.icon_asset_id == asset.id,
                )
            )
        )
    ]
    resumes = [
        {"uuid": item.uuid, "name": item.name}
        for item in db.scalars(select(Resume).where(Resume.asset_id == asset.id))
    ]
    settings = db.get(SiteSetting, 1)
    site_uses: list[str] = []
    if settings:
        data = settings.data or {}
        if data.get("brand_icon_asset_uuid") == asset.uuid:
            site_uses.append("品牌图标")
        for contact in data.get("contact_methods", []):
            if isinstance(contact, dict) and contact.get("icon_asset_uuid") == asset.uuid:
                site_uses.append(f"联系方式图标：{contact.get('label') or '未命名'}")
    return {
        "asset": {"uuid": asset.uuid, "display_name": asset.display_name},
        "projects": projects,
        "certificates": certificates,
        "resumes": resumes,
        "site_uses": site_uses,
        "has_dependencies": bool(projects or certificates or resumes or site_uses),
    }


def folder_assets(folder: AssetFolder) -> list[Asset]:
    items = list(folder.assets)
    for child in folder.children:
        items.extend(folder_assets(child))
    return items


def folder_dependencies(db: Session, folder: AssetFolder) -> dict:
    assets = folder_assets(folder)
    dependencies = [asset_dependencies(db, asset) for asset in assets]
    projects: dict[str, dict] = {}
    certificates: dict[str, dict] = {}
    resumes: dict[str, dict] = {}
    site_uses: set[str] = set()
    for dependency in dependencies:
        for project in dependency["projects"]:
            current = projects.setdefault(
                project["uuid"],
                {"uuid": project["uuid"], "title": project["title"], "usage_count": 0},
            )
            current["usage_count"] += project["usage_count"]
        for item in dependency["certificates"]:
            certificates[item["uuid"]] = item
        for item in dependency["resumes"]:
            resumes[item["uuid"]] = item
        site_uses.update(dependency["site_uses"])
    return {
        "folder": {"uuid": folder.uuid, "name": folder.name},
        "asset_count": len(assets),
        "folder_count": sum(1 for _ in folder.children),
        "projects": list(projects.values()),
        "certificates": list(certificates.values()),
        "resumes": list(resumes.values()),
        "site_uses": sorted(site_uses),
        "has_dependencies": bool(projects or certificates or resumes or site_uses),
    }


@router.get("/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    counts = {
        "projects": db.scalar(select(func.count(Project.id))) or 0,
        "published_projects": db.scalar(
            select(func.count(Project.id)).where(Project.status == "published")
        )
        or 0,
        "assets": db.scalar(select(func.count(Asset.id))) or 0,
        "resumes": db.scalar(select(func.count(Resume.id))) or 0,
        "certificates": db.scalar(select(func.count(Certificate.id))) or 0,
    }
    return ok(request, {**counts, "analytics": overview(db)})


@router.get("/projects")
def list_projects(
    request: Request,
    q: str = "",
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    items, total = ProjectRepository(db).list(
        ProjectListQuery(q=q, status=status, page=page, page_size=page_size)
    )
    return ok(
        request,
        {
            "items": [project_dict(item, detailed=False) for item in items],
            "pagination": {"page": page, "page_size": page_size, "total": total},
        },
    )


@router.get("/projects/{project_uuid}")
def admin_project(
    project_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    project = ProjectRepository(db).get_by_uuid(project_uuid)
    if not project:
        raise ApiError(404, "PROJECT_NOT_FOUND", "项目不存在")
    return ok(request, project_dict(project))


@router.post("/projects")
def create_project(
    payload: ProjectInput,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    project = ProjectService(db).create(payload)
    write_audit(db, request, user, "project.create", "project", project.uuid)
    db.commit()
    return ok(request, project_dict(project), "项目已创建")


@router.put("/projects/{project_uuid}")
def update_project(
    project_uuid: str,
    payload: ProjectInput,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    project = ProjectRepository(db).get_by_uuid(project_uuid)
    if not project:
        raise ApiError(404, "PROJECT_NOT_FOUND", "项目不存在")
    project = ProjectService(db).update(project, payload)
    write_audit(db, request, user, "project.update", "project", project.uuid)
    db.commit()
    return ok(request, project_dict(project), "项目已保存")


@router.post("/projects/{project_uuid}/duplicate")
def duplicate_project(
    project_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    project = ProjectRepository(db).get_by_uuid(project_uuid)
    if not project:
        raise ApiError(404, "PROJECT_NOT_FOUND", "项目不存在")
    duplicate = ProjectService(db).duplicate(project)
    write_audit(db, request, user, "project.duplicate", "project", duplicate.uuid)
    db.commit()
    return ok(request, project_dict(duplicate), "项目副本已创建")


@router.delete("/projects/{project_uuid}")
def delete_project(
    project_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    project = db.scalar(select(Project).where(Project.uuid == project_uuid))
    if not project:
        raise ApiError(404, "PROJECT_NOT_FOUND", "项目不存在")
    db.delete(project)
    write_audit(db, request, user, "project.delete", "project", project_uuid)
    db.commit()
    return ok(request, None, "项目已删除")


@router.post("/projects/batch")
def batch_projects(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    uuids = payload.get("uuids") or []
    action = payload.get("action")
    items = list(db.scalars(select(Project).where(Project.uuid.in_(uuids))))
    if action == "delete":
        for item in items:
            db.delete(item)
    elif action in {"draft", "published", "hidden", "archived"}:
        for item in items:
            item.status = action
            if action == "published" and not item.published_at:
                item.published_at = utcnow()
    else:
        raise ApiError(422, "INVALID_BATCH_ACTION", "不支持的批量操作")
    write_audit(
        db, request, user, f"project.batch.{action}", "project", details={"uuids": uuids}
    )
    db.commit()
    return ok(request, {"affected": len(items)}, "批量操作已完成")


@router.get("/categories")
def categories(
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    items = list(db.scalars(select(Category).order_by(Category.sort_order.desc())))
    return ok(
        request,
        {
            "items": [
                {
                    "uuid": item.uuid,
                    "name": item.name,
                    "slug": item.slug,
                    "description": item.description,
                    "sort_order": item.sort_order,
                    "project_count": len(item.projects),
                    "translations": item.translations or {},
                }
                for item in items
            ]
        },
    )


@router.post("/categories")
def create_category(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ApiError(422, "VALIDATION_ERROR", "分类名称不能为空")
    item = Category(
        name=name,
        slug=str(payload.get("slug") or slugify(name)),
        description=str(payload.get("description", "")),
        sort_order=int(payload.get("sort_order", 0)),
        translations=payload.get("translations") or {},
    )
    db.add(item)
    write_audit(db, request, user, "category.create", "category", item.uuid)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "CATEGORY_EXISTS", "分类名称或标识已存在") from exc
    return ok(request, {"uuid": item.uuid}, "分类已创建")


@router.put("/categories/{item_uuid}")
def update_category(
    item_uuid: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    item = db.scalar(select(Category).where(Category.uuid == item_uuid))
    if not item:
        raise ApiError(404, "CATEGORY_NOT_FOUND", "分类不存在")
    item.name = str(payload.get("name", item.name)).strip()
    item.slug = str(payload.get("slug") or slugify(item.name))
    item.description = str(payload.get("description", item.description))
    item.sort_order = int(payload.get("sort_order", item.sort_order))
    item.translations = payload.get("translations", item.translations) or {}
    write_audit(db, request, user, "category.update", "category", item.uuid)
    db.commit()
    return ok(request, {"uuid": item.uuid}, "分类已保存")


@router.delete("/categories/{item_uuid}")
def delete_category(
    item_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    item = db.scalar(select(Category).where(Category.uuid == item_uuid))
    if not item:
        raise ApiError(404, "CATEGORY_NOT_FOUND", "分类不存在")
    if item.projects:
        raise ApiError(409, "CATEGORY_IN_USE", "该分类仍有关联项目，不能删除")
    db.delete(item)
    write_audit(db, request, user, "category.delete", "category", item_uuid)
    db.commit()
    return ok(request, None, "分类已删除")


@router.get("/tags")
def tags(
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    items = list(db.scalars(select(Tag).order_by(Tag.name)))
    return ok(
        request,
        {
            "items": [
                {
                    "uuid": item.uuid,
                    "name": item.name,
                    "slug": item.slug,
                    "color": item.color,
                    "project_count": len(item.projects),
                    "translations": item.translations or {},
                }
                for item in items
            ]
        },
    )


@router.post("/tags")
def create_tag(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ApiError(422, "VALIDATION_ERROR", "标签名称不能为空")
    item = Tag(
        name=name,
        slug=str(payload.get("slug") or slugify(name)),
        color=str(payload.get("color", "#315b4f")),
        translations=payload.get("translations") or {},
    )
    db.add(item)
    write_audit(db, request, user, "tag.create", "tag", item.uuid)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "TAG_EXISTS", "标签名称或标识已存在") from exc
    return ok(request, {"uuid": item.uuid}, "标签已创建")


@router.put("/tags/{item_uuid}")
def update_tag(
    item_uuid: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    item = db.scalar(select(Tag).where(Tag.uuid == item_uuid))
    if not item:
        raise ApiError(404, "TAG_NOT_FOUND", "标签不存在")
    item.name = str(payload.get("name", item.name)).strip()
    item.slug = str(payload.get("slug") or slugify(item.name))
    item.color = str(payload.get("color", item.color))
    item.translations = payload.get("translations", item.translations) or {}
    write_audit(db, request, user, "tag.update", "tag", item.uuid)
    db.commit()
    return ok(request, {"uuid": item.uuid}, "标签已保存")


@router.delete("/tags/{item_uuid}")
def delete_tag(
    item_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    item = db.scalar(select(Tag).where(Tag.uuid == item_uuid))
    if not item:
        raise ApiError(404, "TAG_NOT_FOUND", "标签不存在")
    if item.projects:
        raise ApiError(409, "TAG_IN_USE", "该标签仍有关联项目，请先合并或解除关联")
    db.delete(item)
    write_audit(db, request, user, "tag.delete", "tag", item_uuid)
    db.commit()
    return ok(request, None, "标签已删除")


@router.post("/tags/merge")
def merge_tags(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    source_uuids = payload.get("source_uuids") or []
    target_uuid = payload.get("target_uuid")
    target = db.scalar(select(Tag).where(Tag.uuid == target_uuid))
    sources = list(db.scalars(select(Tag).where(Tag.uuid.in_(source_uuids))))
    if not target or not sources:
        raise ApiError(404, "TAG_NOT_FOUND", "来源标签或目标标签不存在")
    for source in sources:
        for project in list(source.projects):
            if target not in project.tags:
                project.tags.append(target)
            project.tags.remove(source)
        db.delete(source)
    write_audit(
        db,
        request,
        user,
        "tag.merge",
        "tag",
        target.uuid,
        {"source_uuids": source_uuids},
    )
    db.commit()
    return ok(request, {"merged": len(sources)}, "标签已合并")


@router.get("/assets")
def assets(
    request: Request,
    q: str = "",
    category: str | None = None,
    folder: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    filters = []
    if q:
        term = f"%{q}%"
        filters.append(
            or_(
                Asset.display_name.ilike(term),
                Asset.original_name.ilike(term),
                Asset.description.ilike(term),
                Asset.logical_group.ilike(term),
                Asset.folder.has(AssetFolder.name.ilike(term)),
            )
        )
    if category:
        filters.append(Asset.category == category)
    # Search is intentionally global. Folder navigation only scopes browsing
    # when no keyword is active.
    if folder and not q:
        if folder == "unfiled":
            filters.append(Asset.folder_id.is_(None))
        else:
            filters.append(Asset.folder.has(AssetFolder.uuid == folder))
    total = db.scalar(select(func.count(Asset.id)).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Asset)
            .where(*filters)
            .order_by(Asset.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return ok(
        request,
        {
            "items": [asset_dict(item) for item in items],
            "pagination": {"page": page, "page_size": page_size, "total": total},
        },
    )


@router.get("/asset-folders")
def asset_folders(
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    folders = list(
        db.scalars(
            select(AssetFolder).order_by(AssetFolder.sort_order, AssetFolder.name)
        )
    )
    return ok(
        request,
        {
            "items": [
                asset_folder_dict(folder)
                for folder in folders
            ]
        },
    )


@router.post("/asset-folders")
def create_asset_folder(
    payload: AssetFolderInput,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    if db.scalar(select(AssetFolder).where(AssetFolder.name == payload.name)):
        raise ApiError(409, "ASSET_FOLDER_EXISTS", "同名文件夹已存在")
    parent = None
    if payload.parent_uuid:
        parent = db.scalar(
            select(AssetFolder).where(AssetFolder.uuid == payload.parent_uuid)
        )
        if not parent:
            raise ApiError(404, "ASSET_FOLDER_NOT_FOUND", "父文件夹不存在")
    folder = AssetFolder(
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        parent=parent,
    )
    db.add(folder)
    write_audit(db, request, user, "asset_folder.create", "asset_folder", folder.uuid)
    db.commit()
    return ok(
        request,
        asset_folder_dict(folder),
        "文件夹已创建",
    )


@router.put("/asset-folders/{folder_uuid}")
def update_asset_folder(
    folder_uuid: str,
    payload: AssetFolderInput,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    folder = db.scalar(select(AssetFolder).where(AssetFolder.uuid == folder_uuid))
    if not folder:
        raise ApiError(404, "ASSET_FOLDER_NOT_FOUND", "文件夹不存在")
    duplicate = db.scalar(
        select(AssetFolder).where(
            AssetFolder.name == payload.name, AssetFolder.id != folder.id
        )
    )
    if duplicate:
        raise ApiError(409, "ASSET_FOLDER_EXISTS", "同名文件夹已存在")
    parent = None
    if payload.parent_uuid:
        parent = db.scalar(
            select(AssetFolder).where(AssetFolder.uuid == payload.parent_uuid)
        )
        if not parent:
            raise ApiError(404, "ASSET_FOLDER_NOT_FOUND", "父文件夹不存在")
        cursor: AssetFolder | None = parent
        while cursor is not None:
            if cursor.id == folder.id:
                raise ApiError(422, "ASSET_FOLDER_CYCLE", "不能把文件夹移动到自身子目录")
            cursor = cursor.parent
    folder.name = payload.name
    folder.description = payload.description
    folder.sort_order = payload.sort_order
    folder.parent = parent
    write_audit(db, request, user, "asset_folder.update", "asset_folder", folder.uuid)
    db.commit()
    return ok(request, asset_folder_dict(folder), "文件夹已保存")


@router.delete("/asset-folders/{folder_uuid}")
def delete_asset_folder(
    folder_uuid: str,
    request: Request,
    delete_contents: bool = False,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    folder = db.scalar(select(AssetFolder).where(AssetFolder.uuid == folder_uuid))
    if not folder:
        raise ApiError(404, "ASSET_FOLDER_NOT_FOUND", "文件夹不存在")
    review = folder_dependencies(db, folder)
    if review["has_dependencies"]:
        raise ApiError(
            409,
            "ASSET_FOLDER_IN_USE",
            "文件夹内有资源正在被使用，请先解除关联",
            [review],
        )
    assets = folder_assets(folder)
    if assets and not delete_contents:
        raise ApiError(
            409,
            "ASSET_FOLDER_NOT_EMPTY",
            "文件夹不为空，请先进行删除预检并明确删除其中资源",
            [review],
        )
    paths = [(asset.storage_path, asset.thumbnail_path) for asset in assets]
    for asset in assets:
        db.delete(asset)
    db.delete(folder)
    write_audit(db, request, user, "asset_folder.delete", "asset_folder", folder_uuid)
    db.commit()
    for storage_path, thumbnail_path in paths:
        delete_asset_files(storage_path, thumbnail_path)
    return ok(request, None, "文件夹、资源记录及物理文件已删除")


@router.get("/asset-folders/{folder_uuid}/dependencies")
def inspect_asset_folder_dependencies(
    folder_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    folder = db.scalar(select(AssetFolder).where(AssetFolder.uuid == folder_uuid))
    if not folder:
        raise ApiError(404, "ASSET_FOLDER_NOT_FOUND", "文件夹不存在")
    return ok(request, folder_dependencies(db, folder))


@router.post("/assets/batch-move")
def batch_move_assets(
    payload: AssetBatchMoveInput,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    folder = None
    if payload.folder_uuid:
        folder = db.scalar(
            select(AssetFolder).where(AssetFolder.uuid == payload.folder_uuid)
        )
        if not folder:
            raise ApiError(404, "ASSET_FOLDER_NOT_FOUND", "目标文件夹不存在")
    items = list(db.scalars(select(Asset).where(Asset.uuid.in_(payload.asset_uuids))))
    for asset in items:
        asset.folder = folder
    write_audit(
        db,
        request,
        user,
        "asset.batch_move",
        "asset",
        details={"count": len(items), "folder_uuid": payload.folder_uuid},
    )
    db.commit()
    return ok(request, {"moved": len(items)}, "资源已移动，UUID 与项目引用保持不变")


@router.post("/assets/upload")
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    is_public: bool = Form(False),
    logical_group: str = Form(""),
    folder_uuid: str = Form(""),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    try:
        processed = await save_and_process(file)
    except FileValidationError as exc:
        raise ApiError(422, "FILE_VALIDATION_FAILED", str(exc)) from exc
    duplicate = db.scalar(select(Asset).where(Asset.sha256 == processed.sha256))
    if duplicate:
        delete_asset_files(processed.storage_path, processed.thumbnail_path)
        raise ApiError(
            409,
            "DUPLICATE_FILE",
            "相同内容的文件已经存在",
            [{"asset_uuid": duplicate.uuid, "display_name": duplicate.display_name}],
        )
    folder = (
        db.scalar(select(AssetFolder).where(AssetFolder.uuid == folder_uuid))
        if folder_uuid
        else None
    )
    if folder_uuid and not folder:
        delete_asset_files(processed.storage_path, processed.thumbnail_path)
        raise ApiError(404, "ASSET_FOLDER_NOT_FOUND", "目标文件夹不存在")
    asset = Asset(
        **processed.__dict__,
        is_public=is_public,
        logical_group=logical_group,
        folder=folder,
    )
    db.add(asset)
    write_audit(db, request, user, "asset.upload", "asset", asset.uuid)
    db.commit()
    return ok(request, asset_dict(asset), "文件上传成功")


@router.post("/assets/batch-upload")
async def batch_upload(
    request: Request,
    files: list[UploadFile] = File(...),
    is_public: bool = Form(False),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    if len(files) > 20:
        raise ApiError(422, "TOO_MANY_FILES", "单次最多上传 20 个文件")
    results = []
    for file in files:
        try:
            processed = await save_and_process(file)
            duplicate = db.scalar(select(Asset).where(Asset.sha256 == processed.sha256))
            if duplicate:
                delete_asset_files(processed.storage_path, processed.thumbnail_path)
                results.append(
                    {"name": file.filename, "success": False, "error": "重复文件", "asset_uuid": duplicate.uuid}
                )
                continue
            asset = Asset(**processed.__dict__, is_public=is_public)
            db.add(asset)
            db.flush()
            results.append({"name": file.filename, "success": True, "asset": asset_dict(asset)})
        except (FileValidationError, OSError) as exc:
            results.append({"name": file.filename, "success": False, "error": str(exc)})
    write_audit(
        db, request, user, "asset.batch_upload", "asset", details={"count": len(files)}
    )
    db.commit()
    return ok(request, {"items": results}, "批量上传已处理")


@router.put("/assets/{asset_uuid}")
def update_asset(
    asset_uuid: str,
    payload: AssetPatch,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    asset = db.scalar(select(Asset).where(Asset.uuid == asset_uuid))
    if not asset:
        raise ApiError(404, "ASSET_NOT_FOUND", "资源不存在")
    asset.display_name = payload.display_name
    asset.description = payload.description
    asset.logical_group = payload.logical_group
    asset.is_public = payload.is_public
    asset.translations = payload.translations
    if payload.folder_uuid:
        folder = db.scalar(
            select(AssetFolder).where(AssetFolder.uuid == payload.folder_uuid)
        )
        if not folder:
            raise ApiError(404, "ASSET_FOLDER_NOT_FOUND", "目标文件夹不存在")
        asset.folder = folder
    else:
        asset.folder = None
    write_audit(db, request, user, "asset.update", "asset", asset.uuid)
    db.commit()
    return ok(request, asset_dict(asset), "资源信息已保存")


@router.post("/assets/{asset_uuid}/projects/{project_uuid}")
def associate_asset(
    asset_uuid: str,
    project_uuid: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    asset = db.scalar(select(Asset).where(Asset.uuid == asset_uuid))
    project = db.scalar(select(Project).where(Project.uuid == project_uuid))
    if not asset or not project:
        raise ApiError(404, "ENTITY_NOT_FOUND", "项目或资源不存在")
    existing = db.scalar(
        select(ProjectAsset).where(
            ProjectAsset.project_id == project.id, ProjectAsset.asset_id == asset.id
        )
    )
    if not existing:
        existing = ProjectAsset(project_id=project.id, asset_id=asset.id)
        db.add(existing)
    existing.usage = str(payload.get("usage", "gallery"))
    existing.caption = str(payload.get("caption", ""))
    existing.sort_order = int(payload.get("sort_order", 0))
    write_audit(db, request, user, "asset.associate", "asset", asset.uuid)
    db.commit()
    return ok(request, {"uuid": existing.uuid}, "资源已关联项目")


@router.delete("/assets/{asset_uuid}")
def delete_asset(
    asset_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    asset = db.scalar(select(Asset).where(Asset.uuid == asset_uuid))
    if not asset:
        raise ApiError(404, "ASSET_NOT_FOUND", "资源不存在")
    dependencies = asset_dependencies(db, asset)
    if dependencies["has_dependencies"]:
        raise ApiError(
            409,
            "ASSET_IN_USE",
            "该资源仍被项目、证书、简历或网站设置引用，请先解除关联",
            [dependencies],
        )
    storage_path, thumbnail_path = asset.storage_path, asset.thumbnail_path
    db.delete(asset)
    write_audit(db, request, user, "asset.delete", "asset", asset_uuid)
    db.commit()
    delete_asset_files(storage_path, thumbnail_path)
    return ok(request, None, "资源及其文件已删除")


@router.get("/assets/{asset_uuid}/dependencies")
def inspect_asset_dependencies(
    asset_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    asset = db.scalar(select(Asset).where(Asset.uuid == asset_uuid))
    if not asset:
        raise ApiError(404, "ASSET_NOT_FOUND", "资源不存在")
    return ok(request, asset_dependencies(db, asset))


@router.get("/resumes")
def admin_resumes(
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    items = list(
        db.scalars(
            select(Resume).options(selectinload(Resume.asset)).order_by(Resume.updated_at.desc())
        )
    )
    return ok(request, {"items": [resume_dict(item) for item in items]})


@router.post("/resumes")
def create_resume(
    payload: ResumeInput,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    asset = db.scalar(select(Asset).where(Asset.uuid == payload.asset_uuid))
    if not asset or asset.mime_type != "application/pdf":
        raise ApiError(422, "INVALID_RESUME_ASSET", "请选择有效的 PDF 资源")
    if payload.is_default:
        for existing in db.scalars(select(Resume).where(Resume.is_default.is_(True))):
            existing.is_default = False
    asset.category = "resumes"
    asset.is_public = payload.is_public
    item = Resume(
        name=payload.name,
        language=payload.language,
        resume_type=payload.resume_type,
        asset_id=asset.id,
        is_default=payload.is_default,
        is_public=payload.is_public,
        version=payload.version,
    )
    db.add(item)
    write_audit(db, request, user, "resume.create", "resume", item.uuid)
    db.commit()
    return ok(request, resume_dict(item), "简历版本已创建")


@router.put("/resumes/{resume_uuid}")
def update_resume(
    resume_uuid: str,
    payload: ResumePatch,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    item = db.scalar(
        select(Resume).where(Resume.uuid == resume_uuid).options(selectinload(Resume.asset))
    )
    asset = db.scalar(select(Asset).where(Asset.uuid == payload.asset_uuid))
    if not item:
        raise ApiError(404, "RESUME_NOT_FOUND", "简历不存在")
    if not asset or asset.mime_type != "application/pdf":
        raise ApiError(422, "INVALID_RESUME_ASSET", "请选择有效的 PDF 资源")
    if payload.is_default:
        for existing in db.scalars(
            select(Resume).where(Resume.is_default.is_(True), Resume.id != item.id)
        ):
            existing.is_default = False
    item.name = payload.name
    item.language = payload.language
    item.resume_type = payload.resume_type
    item.asset = asset
    item.is_default = payload.is_default
    item.is_public = payload.is_public
    item.version = payload.version
    asset.is_public = payload.is_public
    write_audit(db, request, user, "resume.update", "resume", item.uuid)
    db.commit()
    return ok(request, resume_dict(item), "简历版本已保存")


@router.delete("/resumes/{resume_uuid}")
def delete_resume(
    resume_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    item = db.scalar(select(Resume).where(Resume.uuid == resume_uuid))
    if not item:
        raise ApiError(404, "RESUME_NOT_FOUND", "简历不存在")
    db.delete(item)
    write_audit(db, request, user, "resume.delete", "resume", resume_uuid)
    db.commit()
    return ok(request, None, "简历版本已删除，原始资源仍保留")


@router.get("/certificates")
def admin_certificates(
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    items = list(
        db.scalars(
            select(Certificate)
            .options(
                selectinload(Certificate.asset),
                selectinload(Certificate.icon_asset),
                selectinload(Certificate.projects),
            )
            .order_by(Certificate.sort_order.desc(), Certificate.updated_at.desc())
        )
    )
    return ok(request, {"items": [certificate_dict(item) for item in items]})


@router.post("/certificates")
def create_certificate(
    payload: CertificateInput,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    asset = (
        db.scalar(select(Asset).where(Asset.uuid == payload.asset_uuid))
        if payload.asset_uuid
        else None
    )
    icon = (
        db.scalar(select(Asset).where(Asset.uuid == payload.icon_asset_uuid))
        if payload.icon_asset_uuid
        else None
    )
    if payload.asset_uuid and not asset:
        raise ApiError(422, "INVALID_CERTIFICATE_ASSET", "证书文件资源不存在")
    if payload.icon_asset_uuid and not icon:
        raise ApiError(422, "INVALID_ICON_ASSET", "图标资源不存在")
    try:
        safe_svg = sanitize_svg(payload.icon_svg)
    except SvgValidationError as exc:
        raise ApiError(422, "INVALID_SVG_ICON", str(exc)) from exc
    item = Certificate(
        name=payload.name,
        issuer=payload.issuer,
        certificate_type=payload.certificate_type,
        issued_at=payload.issued_at,
        description=payload.description,
        credential_no=payload.credential_no,
        credential_url=payload.credential_url,
        asset=asset,
        icon_asset=icon,
        icon_name=payload.icon_name,
        icon_svg=safe_svg,
        is_public=payload.is_public,
        sort_order=payload.sort_order,
        translations=payload.translations,
        content_language_mode=payload.content_language_mode,
    )
    if asset and payload.is_public:
        asset.is_public = True
    if icon:
        icon.is_public = True
    db.add(item)
    write_audit(db, request, user, "certificate.create", "certificate", item.uuid)
    db.commit()
    item = db.scalar(
        select(Certificate)
        .where(Certificate.uuid == item.uuid)
        .options(
            selectinload(Certificate.asset),
            selectinload(Certificate.icon_asset),
            selectinload(Certificate.projects),
        )
    )
    return ok(request, certificate_dict(item), "证书已创建")


@router.put("/certificates/{certificate_uuid}")
def update_certificate(
    certificate_uuid: str,
    payload: CertificatePatch,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    item = db.scalar(
        select(Certificate)
        .where(Certificate.uuid == certificate_uuid)
        .options(
            selectinload(Certificate.asset),
            selectinload(Certificate.icon_asset),
            selectinload(Certificate.projects),
        )
    )
    if not item:
        raise ApiError(404, "CERTIFICATE_NOT_FOUND", "证书不存在")
    asset = (
        db.scalar(select(Asset).where(Asset.uuid == payload.asset_uuid))
        if payload.asset_uuid
        else None
    )
    icon = (
        db.scalar(select(Asset).where(Asset.uuid == payload.icon_asset_uuid))
        if payload.icon_asset_uuid
        else None
    )
    if payload.asset_uuid and not asset:
        raise ApiError(422, "INVALID_CERTIFICATE_ASSET", "证书文件资源不存在")
    if payload.icon_asset_uuid and not icon:
        raise ApiError(422, "INVALID_ICON_ASSET", "图标资源不存在")
    for field in [
        "name",
        "issuer",
        "certificate_type",
        "issued_at",
        "description",
        "credential_no",
        "credential_url",
        "is_public",
        "sort_order",
        "icon_name",
        "translations",
        "content_language_mode",
    ]:
        setattr(item, field, getattr(payload, field))
    item.asset = asset
    item.icon_asset = icon
    try:
        item.icon_svg = sanitize_svg(payload.icon_svg)
    except SvgValidationError as exc:
        raise ApiError(422, "INVALID_SVG_ICON", str(exc)) from exc
    if asset and payload.is_public:
        asset.is_public = True
    if icon:
        icon.is_public = True
    write_audit(db, request, user, "certificate.update", "certificate", item.uuid)
    db.commit()
    return ok(request, certificate_dict(item), "证书已保存")


@router.delete("/certificates/{certificate_uuid}")
def delete_certificate(
    certificate_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    item = db.scalar(
        select(Certificate)
        .where(Certificate.uuid == certificate_uuid)
        .options(selectinload(Certificate.projects))
    )
    if not item:
        raise ApiError(404, "CERTIFICATE_NOT_FOUND", "证书不存在")
    if item.projects:
        raise ApiError(409, "CERTIFICATE_IN_USE", "证书仍与项目关联，请先解除关联")
    db.delete(item)
    write_audit(db, request, user, "certificate.delete", "certificate", certificate_uuid)
    db.commit()
    return ok(request, None, "证书记录已删除，原始资源仍保留")


@router.get("/settings")
def get_site_settings(
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    settings = db.get(SiteSetting, 1)
    return ok(request, settings.data if settings else {})


@router.put("/settings")
def update_site_settings(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    settings = db.get(SiteSetting, 1)
    if settings is None:
        settings = SiteSetting(id=1, data={})
        db.add(settings)
    allowed = {
        "site_name",
        "person_name",
        "headline",
        "bio",
        "current_identity",
        "research_directions",
        "email",
        "github_url",
        "gitee_url",
        "location",
        "avatar_asset_uuid",
        "background_asset_uuid",
        "default_seo_title",
        "default_seo_description",
        "footer_text",
        "footer_eyebrow",
        "footer_heading",
        "hero_eyebrow",
        "hero_focus_label",
        "hero_focus_value",
        "brand_mark_text",
        "brand_icon_asset_uuid",
        "navigation_items",
        "home_stats",
        "home_capabilities",
        "home_copy",
        "contact_methods",
        "page_content",
        "analytics_enabled",
        "analytics_retention_days",
        "analytics_notice_enabled",
        "max_upload_size",
        "allowed_file_types",
        "featured_project_count",
        "primary_language",
        "translations",
    }
    if isinstance(payload.get("contact_methods"), list):
        try:
            for contact in payload["contact_methods"]:
                if isinstance(contact, dict):
                    contact["icon_svg"] = sanitize_svg(str(contact.get("icon_svg") or ""))
        except SvgValidationError as exc:
            raise ApiError(422, "INVALID_SVG_ICON", str(exc)) from exc
    settings.data = {**(settings.data or {}), **{key: value for key, value in payload.items() if key in allowed}}
    icon_uuids = [
        str(payload.get("brand_icon_asset_uuid") or ""),
        *[
            str(item.get("icon_asset_uuid") or "")
            for item in payload.get("contact_methods", [])
            if isinstance(item, dict)
        ],
    ]
    if any(icon_uuids):
        for asset in db.scalars(select(Asset).where(Asset.uuid.in_([value for value in icon_uuids if value]))):
            asset.is_public = True
    write_audit(db, request, user, "settings.update", "site_setting", "site")
    db.commit()
    return ok(request, settings.data, "网站设置已保存")


@router.get("/analytics/overview")
def analytics_overview(
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    return ok(request, overview(db))


@router.get("/analytics/visitors")
def analytics_visitors(
    request: Request,
    page: int = 1,
    page_size: int = 30,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    sessions = list(
        db.scalars(
            select(VisitorSession)
            .options(selectinload(VisitorSession.visitor))
            .order_by(VisitorSession.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return ok(
        request,
        {
            "items": [
                {
                    "uuid": item.uuid,
                    "visitor_uuid": item.visitor.uuid,
                    "started_at": item.started_at,
                    "last_seen_at": item.last_seen_at,
                    "device_type": item.device_type,
                    "browser": item.browser,
                    "operating_system": item.operating_system,
                    "referer": item.referer,
                    "utm_source": item.utm_source,
                    "attention_score": item.attention_score,
                    "score_reasons": item.score_reasons,
                    "visit_count": item.visitor.visit_count,
                    "country": item.visitor.country,
                    "region": item.visitor.region,
                    "city": item.visitor.city,
                }
                for item in sessions
            ]
        },
    )


@router.get("/analytics/sessions/{session_uuid}")
def analytics_session(
    session_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    session = db.scalar(
        select(VisitorSession)
        .where(VisitorSession.uuid == session_uuid)
        .options(selectinload(VisitorSession.visitor))
    )
    if not session:
        raise ApiError(404, "SESSION_NOT_FOUND", "访问会话不存在")
    events = list(
        db.scalars(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.session_uuid == session_uuid)
            .order_by(AnalyticsEvent.timestamp)
        )
    )
    project_uuids = {event.project_uuid for event in events if event.project_uuid}
    project_titles = (
        dict(
            db.execute(
                select(Project.uuid, Project.title).where(Project.uuid.in_(project_uuids))
            ).all()
        )
        if project_uuids
        else {}
    )
    return ok(
        request,
        {
            "session": {
                "uuid": session.uuid,
                "visitor_uuid": session.visitor.uuid,
                "started_at": session.started_at,
                "last_seen_at": session.last_seen_at,
                "device_type": session.device_type,
                "browser": session.browser,
                "operating_system": session.operating_system,
                "attention_score": session.attention_score,
                "score_reasons": session.score_reasons,
            },
            "events": [
                {
                    "uuid": event.uuid,
                    "event_type": event.event_type,
                    "page_type": event.page_type,
                    "page_uuid": event.page_uuid,
                    "project_uuid": event.project_uuid,
                    "project_title": project_titles.get(event.project_uuid or ""),
                    "asset_uuid": event.asset_uuid,
                    "event_data": event.event_data,
                    "timestamp": event.timestamp,
                }
                for event in events
            ],
        },
    )


@router.delete("/analytics")
def cleanup_analytics(
    request: Request,
    days: int | None = None,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_csrf),
) -> dict:
    retention = days if days is not None else get_settings().ANALYTICS_RETENTION_DAYS
    threshold = utcnow() - timedelta(days=max(retention, 0))
    events_deleted = db.execute(
        delete(AnalyticsEvent).where(AnalyticsEvent.timestamp < threshold)
    ).rowcount
    sessions_deleted = db.execute(
        delete(VisitorSession).where(VisitorSession.last_seen_at < threshold)
    ).rowcount
    visitors_deleted = db.execute(
        delete(Visitor).where(Visitor.last_seen_at < threshold)
    ).rowcount
    write_audit(
        db,
        request,
        user,
        "analytics.cleanup",
        "analytics",
        details={"retention_days": retention},
    )
    db.commit()
    return ok(
        request,
        {
            "events_deleted": events_deleted,
            "sessions_deleted": sessions_deleted,
            "visitors_deleted": visitors_deleted,
        },
        "历史分析数据已清理",
    )


@router.get("/audit-logs")
def audit_logs(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> dict:
    items = list(
        db.scalars(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return ok(
        request,
        {
            "items": [
                {
                    "uuid": item.uuid,
                    "admin_user_uuid": item.admin_user_uuid,
                    "action": item.action,
                    "entity_type": item.entity_type,
                    "entity_uuid": item.entity_uuid,
                    "details": item.details,
                    "created_at": item.created_at,
                }
                for item in items
            ]
        },
    )
