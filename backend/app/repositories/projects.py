from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Category,
    Certificate,
    Project,
    ProjectAlbum,
    ProjectAlbumAsset,
    ProjectAsset,
    Tag,
)
from app.schemas.projects import ProjectInput, ProjectListQuery


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def eager() -> tuple:
        return (
            selectinload(Project.category),
            selectinload(Project.tags),
            selectinload(Project.certificates).selectinload(Certificate.asset),
            selectinload(Project.certificates).selectinload(Certificate.icon_asset),
            selectinload(Project.links),
            selectinload(Project.sections),
            selectinload(Project.albums)
            .selectinload(ProjectAlbum.assets)
            .selectinload(ProjectAlbumAsset.asset),
            selectinload(Project.assets).selectinload(ProjectAsset.asset),
            selectinload(Project.cover_asset),
        )

    def get_by_uuid(self, project_uuid: str) -> Project | None:
        return self.db.scalar(
            select(Project).where(Project.uuid == project_uuid).options(*self.eager())
        )

    def list(self, query: ProjectListQuery, public_only: bool = False) -> tuple[list[Project], int]:
        statement: Select[tuple[Project]] = select(Project).options(*self.eager())
        count_statement = select(func.count(Project.id))
        filters = []
        if public_only:
            filters.append(Project.status == "published")
            if query.locale == "en":
                filters.append(Project.content_language_mode != "single_zh")
            elif query.locale == "zh-CN":
                filters.append(Project.content_language_mode != "single_en")
        elif query.status:
            filters.append(Project.status == query.status)
        if query.q:
            term = f"%{query.q.strip()}%"
            filters.append(
                or_(
                    Project.title.ilike(term),
                    Project.summary.ilike(term),
                    Project.role.ilike(term),
                )
            )
        if query.category:
            filters.append(Project.category.has(Category.uuid == query.category))
        if query.tags:
            for tag_uuid in query.tags:
                filters.append(Project.tags.any(Tag.uuid == tag_uuid))
        if query.featured is not None:
            filters.append(Project.is_featured == query.featured)
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
        if query.sort == "latest":
            statement = statement.order_by(Project.published_at.desc(), Project.created_at.desc())
        elif query.sort == "oldest":
            statement = statement.order_by(Project.start_date.asc())
        elif query.sort == "title":
            statement = statement.order_by(Project.title.asc())
        else:
            statement = statement.order_by(
                Project.is_featured.desc(), Project.sort_order.desc(), Project.published_at.desc()
            )
        total = self.db.scalar(count_statement) or 0
        statement = statement.offset((query.page - 1) * query.page_size).limit(query.page_size)
        return list(self.db.scalars(statement).unique()), total

    def create(self, payload: ProjectInput) -> Project:
        project = Project(title=payload.title, summary=payload.summary)
        self.db.add(project)
        self.apply(project, payload)
        self.db.flush()
        return project

    def apply(self, project: Project, payload: ProjectInput) -> None:
        scalar_fields = [
            "title",
            "subtitle",
            "summary",
            "content",
            "background",
            "problem",
            "solution",
            "architecture",
            "contributions",
            "technologies",
            "outcomes",
            "start_date",
            "end_date",
            "role",
            "team_size",
            "status",
            "project_state",
            "is_featured",
            "is_open_source",
            "sort_order",
            "seo_title",
            "seo_description",
            "translations",
            "content_language_mode",
        ]
        for field in scalar_fields:
            setattr(project, field, getattr(payload, field))
        project.content_layout = [item.model_dump(mode="json") for item in payload.content_layout]

        project.category = (
            self.db.scalar(select(Category).where(Category.uuid == payload.category_uuid))
            if payload.category_uuid
            else None
        )
        project.tags = (
            list(self.db.scalars(select(Tag).where(Tag.uuid.in_(payload.tag_uuids))))
            if payload.tag_uuids
            else []
        )
        project.certificates = (
            list(
                self.db.scalars(
                    select(Certificate).where(Certificate.uuid.in_(payload.certificate_uuids))
                )
            )
            if payload.certificate_uuids
            else []
        )
