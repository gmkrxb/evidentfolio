from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import (
    Asset,
    Project,
    ProjectAlbum,
    ProjectAlbumAsset,
    ProjectAsset,
    ProjectLink,
    ProjectSection,
)
from app.models.entities import uuid4_string
from app.repositories.projects import ProjectRepository
from app.schemas.projects import ProjectInput


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ProjectRepository(db)

    def create(self, payload: ProjectInput, *, commit: bool = True) -> Project:
        project = self.repository.create(payload)
        self._apply_relations(project, payload)
        self._apply_publication(project)
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return self.repository.get_by_uuid(project.uuid)  # type: ignore[return-value]

    def update(self, project: Project, payload: ProjectInput) -> Project:
        self.repository.apply(project, payload)
        self._apply_relations(project, payload)
        self._apply_publication(project)
        self.db.commit()
        return self.repository.get_by_uuid(project.uuid)  # type: ignore[return-value]

    def duplicate(self, project: Project) -> Project:
        duplicate = Project(
            title=f"{project.title}（副本）",
            subtitle=project.subtitle,
            summary=project.summary,
            content=project.content,
            background=project.background,
            problem=project.problem,
            solution=project.solution,
            architecture=project.architecture,
            contributions=list(project.contributions),
            technologies=list(project.technologies),
            outcomes=list(project.outcomes),
            start_date=project.start_date,
            end_date=project.end_date,
            role=project.role,
            team_size=project.team_size,
            status="draft",
            project_state=project.project_state,
            is_featured=False,
            is_open_source=project.is_open_source,
            sort_order=project.sort_order,
            category=project.category,
            tags=list(project.tags),
            certificates=list(project.certificates),
            cover_asset=project.cover_asset,
            seo_title=project.seo_title,
            seo_description=project.seo_description,
            content_layout=list(project.content_layout),
            translations=dict(project.translations or {}),
            content_language_mode=project.content_language_mode,
        )
        duplicate.links = [
            ProjectLink(
                label=link.label,
                url=link.url,
                link_type=link.link_type,
                sort_order=link.sort_order,
            )
            for link in project.links
        ]
        album_uuid_map = {album.uuid: uuid4_string() for album in project.albums}
        duplicate.sections = [
            ProjectSection(
                title=section.title,
                client_key=section.client_key,
                body=section.body,
                section_type=section.section_type,
                display_mode=section.display_mode,
                asset_uuids=list(section.asset_uuids),
                album_uuid=album_uuid_map.get(section.album_uuid or ""),
                heading_level=section.heading_level,
                is_visible=section.is_visible,
                sort_order=section.sort_order,
                translations=dict(section.translations or {}),
            )
            for section in project.sections
        ]
        duplicate.albums = [
            ProjectAlbum(
                uuid=album_uuid_map[album.uuid],
                title=album.title,
                description=album.description,
                display_mode=album.display_mode,
                sort_order=album.sort_order,
                translations=dict(album.translations or {}),
                assets=[
                    ProjectAlbumAsset(
                        asset=relation.asset,
                        caption=relation.caption,
                        sort_order=relation.sort_order,
                    )
                    for relation in album.assets
                ],
            )
            for album in project.albums
        ]
        duplicate.assets = [
            ProjectAsset(
                asset=relation.asset,
                usage=relation.usage,
                caption=relation.caption,
                sort_order=relation.sort_order,
            )
            for relation in project.assets
        ]
        self.db.add(duplicate)
        self.db.commit()
        return self.repository.get_by_uuid(duplicate.uuid)  # type: ignore[return-value]

    def _apply_relations(self, project: Project, payload: ProjectInput) -> None:
        if payload.cover_asset_uuid:
            project.cover_asset = self.db.scalar(
                select(Asset).where(Asset.uuid == payload.cover_asset_uuid)
            )
        else:
            project.cover_asset = None
        project.links = [
            ProjectLink(
                label=str(link.label),
                url=str(link.url),
                link_type=link.link_type,
                sort_order=link.sort_order,
            )
            for link in payload.links
        ]
        self._apply_albums(project, payload)
        project.sections = [
            ProjectSection(
                title=section.title,
                client_key=section.client_key,
                body=section.body,
                section_type=section.section_type,
                display_mode=section.display_mode,
                asset_uuids=list(dict.fromkeys(section.asset_uuids)),
                album_uuid=section.album_uuid,
                heading_level=section.heading_level,
                is_visible=section.is_visible,
                sort_order=section.sort_order,
                translations=dict(section.translations or {}),
            )
            for section in payload.sections
        ]
        self._sync_content_assets(project, payload)

    def _apply_albums(self, project: Project, payload: ProjectInput) -> None:
        current = {album.uuid: album for album in project.albums}
        next_albums: list[ProjectAlbum] = []
        for album_input in payload.albums:
            album = current.get(album_input.uuid or "")
            if album is None:
                album = ProjectAlbum(uuid=album_input.uuid or uuid4_string())
            album.title = album_input.title
            album.description = album_input.description
            album.display_mode = album_input.display_mode
            album.sort_order = album_input.sort_order
            album.translations = album_input.translations
            assets = (
                list(
                    self.db.scalars(
                        select(Asset).where(Asset.uuid.in_(album_input.asset_uuids))
                    )
                )
                if album_input.asset_uuids
                else []
            )
            assets_by_uuid = {asset.uuid: asset for asset in assets}
            existing_relations = {
                relation.asset.uuid: relation for relation in album.assets
            }
            next_relations: list[ProjectAlbumAsset] = []
            for index, asset_uuid in enumerate(dict.fromkeys(album_input.asset_uuids)):
                asset = assets_by_uuid.get(asset_uuid)
                if not asset:
                    continue
                relation = existing_relations.get(asset_uuid)
                if relation is None:
                    relation = ProjectAlbumAsset(asset=asset)
                relation.sort_order = index
                next_relations.append(relation)
            album.assets = next_relations
            next_albums.append(album)
        project.albums = next_albums

    def _sync_content_assets(self, project: Project, payload: ProjectInput) -> None:
        desired_album = {
            asset_uuid
            for album in payload.albums
            for asset_uuid in album.asset_uuids
        }
        desired_section = {
            asset_uuid
            for section in payload.sections
            for asset_uuid in section.asset_uuids
        }
        desired = desired_album | desired_section
        retained: list[ProjectAsset] = []
        existing_asset_uuids: set[str] = set()
        for relation in project.assets:
            if relation.usage in {"album", "section"} and relation.asset.uuid not in desired:
                continue
            retained.append(relation)
            existing_asset_uuids.add(relation.asset.uuid)
        missing = desired - existing_asset_uuids
        assets = (
            list(self.db.scalars(select(Asset).where(Asset.uuid.in_(missing))))
            if missing
            else []
        )
        for index, asset in enumerate(assets, start=len(retained)):
            retained.append(
                ProjectAsset(
                    asset=asset,
                    usage="album" if asset.uuid in desired_album else "section",
                    sort_order=index,
                )
            )
        project.assets = retained

    @staticmethod
    def _apply_publication(project: Project) -> None:
        if project.status == "published" and not project.published_at:
            project.published_at = utcnow()
