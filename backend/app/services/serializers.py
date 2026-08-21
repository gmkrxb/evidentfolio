from __future__ import annotations

from app.models import Asset, Certificate, Project, Resume


def translated(source: object, field: str, locale: str | None) -> object:
    value = getattr(source, field)
    if not locale or locale.startswith("zh"):
        return value
    translations = getattr(source, "translations", {}) or {}
    localized = translations.get("en", {}) if isinstance(translations, dict) else {}
    candidate = localized.get(field) if isinstance(localized, dict) else None
    return candidate if candidate not in (None, "", []) else value


def asset_dict(asset: Asset | None, locale: str | None = None) -> dict | None:
    if not asset:
        return None
    return {
        "uuid": asset.uuid,
        "original_name": asset.original_name,
        "display_name": translated(asset, "display_name", locale),
        "mime_type": asset.mime_type,
        "extension": asset.extension,
        "size": asset.size,
        "sha256": asset.sha256,
        "category": asset.category,
        "width": asset.width,
        "height": asset.height,
        "duration": asset.duration,
        "is_public": asset.is_public,
        "description": translated(asset, "description", locale),
        "logical_group": asset.logical_group,
        "folder": (
            {
                "uuid": asset.folder.uuid,
                "name": asset.folder.name,
            }
            if asset.folder
            else None
        ),
        "view_count": asset.view_count,
        "download_count": asset.download_count,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
        "translations": asset.translations or {},
        "content_url": f"/api/v1/public/assets/{asset.uuid}/content",
        "download_url": f"/api/v1/public/assets/{asset.uuid}/download",
        "thumbnail_url": (
            f"/api/v1/public/assets/{asset.uuid}/thumbnail" if asset.thumbnail_path else None
        ),
    }


def resume_dict(resume: Resume) -> dict:
    return {
        "uuid": resume.uuid,
        "name": resume.name,
        "language": resume.language,
        "resume_type": resume.resume_type,
        "is_default": resume.is_default,
        "is_public": resume.is_public,
        "version": resume.version,
        "view_count": resume.view_count,
        "download_count": resume.download_count,
        "created_at": resume.created_at,
        "updated_at": resume.updated_at,
        "asset": asset_dict(resume.asset),
    }


def certificate_dict(
    certificate: Certificate,
    *,
    include_projects: bool = False,
    public_projects_only: bool = False,
    locale: str | None = None,
) -> dict:
    projects = [
        project
        for project in certificate.projects
        if not public_projects_only or project.status == "published"
    ]
    data = {
        "uuid": certificate.uuid,
        "name": translated(certificate, "name", locale),
        "issuer": translated(certificate, "issuer", locale),
        "certificate_type": certificate.certificate_type,
        "issued_at": certificate.issued_at,
        "description": translated(certificate, "description", locale),
        "credential_no": certificate.credential_no,
        "credential_url": certificate.credential_url,
        "is_public": certificate.is_public,
        "sort_order": certificate.sort_order,
        "asset": asset_dict(certificate.asset, locale),
        "icon_asset": asset_dict(certificate.icon_asset, locale),
        "icon_name": certificate.icon_name,
        "icon_svg": certificate.icon_svg,
        "project_count": len(projects),
        "created_at": certificate.created_at,
        "updated_at": certificate.updated_at,
        "translations": certificate.translations or {},
        "content_language_mode": certificate.content_language_mode,
    }
    if include_projects:
        data["projects"] = [
            {
                "uuid": project.uuid,
                "title": translated(project, "title", locale),
                "subtitle": translated(project, "subtitle", locale),
                "summary": translated(project, "summary", locale),
                "start_date": project.start_date,
                "end_date": project.end_date,
                "role": translated(project, "role", locale),
                "status": project.status,
            }
            for project in projects
        ]
    return data


def project_dict(
    project: Project,
    detailed: bool = True,
    locale: str | None = None,
    include_content_relations: bool = True,
) -> dict:
    all_media_assets: dict[str, Asset] = {}
    for relation in project.assets:
        all_media_assets[relation.asset.uuid] = relation.asset
    for album in project.albums:
        for relation in album.assets:
            all_media_assets[relation.asset.uuid] = relation.asset

    auto_cover_assets: list[dict] = []
    if not project.cover_asset:
        for relation in project.assets:
            asset = relation.asset
            if asset.uuid in {item["uuid"] for item in auto_cover_assets}:
                continue
            if asset.is_public and asset.mime_type.startswith("image/"):
                item = asset_dict(asset, locale)
                if item:
                    auto_cover_assets.append(item)
            if len(auto_cover_assets) >= 4:
                break

    albums = [
        {
            "uuid": album.uuid,
            "title": translated(album, "title", locale),
            "description": translated(album, "description", locale),
            "display_mode": album.display_mode,
            "sort_order": album.sort_order,
            "translations": album.translations or {},
            "assets": [
                {
                    "uuid": relation.uuid,
                    "caption": relation.caption,
                    "sort_order": relation.sort_order,
                    "asset": asset_dict(relation.asset, locale),
                }
                for relation in album.assets
            ],
        }
        for album in project.albums
    ]
    albums_by_uuid = {album["uuid"]: album for album in albums}

    return {
        "uuid": project.uuid,
        "title": translated(project, "title", locale),
        "subtitle": translated(project, "subtitle", locale),
        "summary": translated(project, "summary", locale),
        "content": translated(project, "content", locale) if detailed else "",
        "background": translated(project, "background", locale) if detailed else "",
        "problem": translated(project, "problem", locale) if detailed else "",
        "solution": translated(project, "solution", locale) if detailed else "",
        "architecture": translated(project, "architecture", locale) if detailed else "",
        "contributions": translated(project, "contributions", locale),
        "technologies": project.technologies,
        "outcomes": translated(project, "outcomes", locale),
        "start_date": project.start_date,
        "end_date": project.end_date,
        "role": translated(project, "role", locale),
        "team_size": project.team_size,
        "status": project.status,
        "project_state": project.project_state,
        "is_featured": project.is_featured,
        "is_open_source": project.is_open_source,
        "sort_order": project.sort_order,
        "content_layout": project.content_layout or [],
        "translations": project.translations or {},
        "content_language_mode": project.content_language_mode,
        "category": (
            {"uuid": project.category.uuid, "name": translated(project.category, "name", locale), "slug": project.category.slug}
            if project.category
            else None
        ),
        "tags": [
            {"uuid": tag.uuid, "name": translated(tag, "name", locale), "slug": tag.slug, "color": tag.color}
            for tag in project.tags
        ],
        "certificates": [
            certificate_dict(item, include_projects=False, locale=locale)
            for item in project.certificates
        ],
        "cover_asset": asset_dict(project.cover_asset, locale),
        "auto_cover_assets": auto_cover_assets,
        "links": [
            {
                "uuid": link.uuid,
                "label": link.label,
                "url": link.url,
                "link_type": link.link_type,
                "sort_order": link.sort_order,
            }
            for link in project.links
        ],
        "sections": [
            {
                "uuid": section.uuid,
                "title": translated(section, "title", locale),
                "client_key": section.client_key,
                "body": translated(section, "body", locale),
                "section_type": section.section_type,
                "display_mode": section.display_mode,
                "asset_uuids": section.asset_uuids,
                "album_uuid": section.album_uuid,
                "heading_level": section.heading_level,
                "is_visible": section.is_visible,
                "media_assets": [
                    asset_dict(all_media_assets[asset_uuid], locale)
                    for asset_uuid in section.asset_uuids
                    if asset_uuid in all_media_assets
                ],
                "album": albums_by_uuid.get(section.album_uuid or ""),
                "sort_order": section.sort_order,
                "translations": section.translations or {},
            }
            for section in project.sections
        ]
        if detailed
        else [],
        "albums": albums if detailed else [],
        "assets": [
            {
                "uuid": relation.uuid,
                "usage": relation.usage,
                "caption": relation.caption,
                "sort_order": relation.sort_order,
                "asset": asset_dict(relation.asset, locale),
            }
            for relation in project.assets
            if (
                relation.usage != "section"
                if include_content_relations
                else relation.usage not in {"section", "album"}
            )
        ]
        if detailed
        else [],
        "seo_title": translated(project, "seo_title", locale),
        "seo_description": translated(project, "seo_description", locale),
        "published_at": project.published_at,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }
