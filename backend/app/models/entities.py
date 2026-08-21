from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import utcnow


def uuid4_string() -> str:
    return str(uuid_lib.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )


class UuidMixin:
    uuid: Mapped[str] = mapped_column(
        String(36), default=uuid4_string, unique=True, index=True
    )


class AdminUser(Base, UuidMixin, TimestampMixin):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="管理员")
    role: Mapped[str] = mapped_column(String(40), default="super_admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AdminSession(Base, UuidMixin):
    __tablename__ = "admin_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(96))
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[AdminUser] = relationship()


class AISetting(Base, TimestampMixin):
    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    base_url: Mapped[str] = mapped_column(String(1000), default="")
    encrypted_api_key: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(200), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


project_tags = Table(
    "project_tags",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="RESTRICT"), primary_key=True),
)

project_certificates = Table(
    "project_certificates",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("certificate_id", ForeignKey("certificates.id", ondelete="RESTRICT"), primary_key=True),
)


class Category(Base, UuidMixin, TimestampMixin):
    __tablename__ = "project_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    translations: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    projects: Mapped[list["Project"]] = relationship(back_populates="category")


class Tag(Base, UuidMixin, TimestampMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    color: Mapped[str] = mapped_column(String(20), default="#315b4f")
    translations: Mapped[dict] = mapped_column(JSON, default=dict)
    projects: Mapped[list["Project"]] = relationship(
        secondary=project_tags, back_populates="tags"
    )


class Project(Base, UuidMixin, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    subtitle: Mapped[str] = mapped_column(String(240), default="")
    summary: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, default="")
    background: Mapped[str] = mapped_column(Text, default="")
    problem: Mapped[str] = mapped_column(Text, default="")
    solution: Mapped[str] = mapped_column(Text, default="")
    architecture: Mapped[str] = mapped_column(Text, default="")
    contributions: Mapped[list[str]] = mapped_column(JSON, default=list)
    technologies: Mapped[list[str]] = mapped_column(JSON, default=list)
    outcomes: Mapped[list[str]] = mapped_column(JSON, default=list)
    start_date: Mapped[str] = mapped_column(String(20), default="")
    end_date: Mapped[str] = mapped_column(String(20), default="")
    role: Mapped[str] = mapped_column(String(160), default="")
    team_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    project_state: Mapped[str] = mapped_column(String(40), default="completed")
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_open_source: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cover_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    seo_title: Mapped[str] = mapped_column(String(180), default="")
    seo_description: Mapped[str] = mapped_column(String(320), default="")
    content_layout: Mapped[list[dict]] = mapped_column(JSON, default=list)
    translations: Mapped[dict] = mapped_column(JSON, default=dict)
    content_language_mode: Mapped[str] = mapped_column(String(20), default="bilingual")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    category: Mapped[Category | None] = relationship(back_populates="projects")
    tags: Mapped[list[Tag]] = relationship(
        secondary=project_tags, back_populates="projects"
    )
    certificates: Mapped[list["Certificate"]] = relationship(
        secondary=project_certificates, back_populates="projects"
    )
    links: Mapped[list["ProjectLink"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectLink.sort_order"
    )
    sections: Mapped[list["ProjectSection"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectSection.sort_order"
    )
    albums: Mapped[list["ProjectAlbum"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectAlbum.sort_order"
    )
    assets: Mapped[list["ProjectAsset"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectAsset.sort_order"
    )
    cover_asset: Mapped["Asset | None"] = relationship(foreign_keys=[cover_asset_id])


class ProjectLink(Base, UuidMixin, TimestampMixin):
    __tablename__ = "project_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(1000))
    link_type: Mapped[str] = mapped_column(String(40), default="other")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    project: Mapped[Project] = relationship(back_populates="links")


class ProjectSection(Base, UuidMixin, TimestampMixin):
    __tablename__ = "project_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(180))
    client_key: Mapped[str] = mapped_column(String(36), default=uuid4_string, index=True)
    body: Mapped[str] = mapped_column(Text)
    section_type: Mapped[str] = mapped_column(String(40), default="markdown")
    display_mode: Mapped[str] = mapped_column(String(40), default="text")
    asset_uuids: Mapped[list[str]] = mapped_column(JSON, default=list)
    album_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    heading_level: Mapped[int] = mapped_column(Integer, default=2)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    translations: Mapped[dict] = mapped_column(JSON, default=dict)
    project: Mapped[Project] = relationship(back_populates="sections")


class ProjectAlbum(Base, UuidMixin, TimestampMixin):
    __tablename__ = "project_albums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    display_mode: Mapped[str] = mapped_column(String(40), default="grid")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    translations: Mapped[dict] = mapped_column(JSON, default=dict)

    project: Mapped[Project] = relationship(back_populates="albums")
    assets: Mapped[list["ProjectAlbumAsset"]] = relationship(
        back_populates="album",
        cascade="all, delete-orphan",
        order_by="ProjectAlbumAsset.sort_order",
    )


class Asset(Base, UuidMixin, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    storage_name: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(160), index=True)
    extension: Mapped[str] = mapped_column(String(20))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    storage_path: Mapped[str] = mapped_column(String(500))
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    logical_group: Mapped[str] = mapped_column(String(120), default="")
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_folders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    translations: Mapped[dict] = mapped_column(JSON, default=dict)

    folder: Mapped["AssetFolder | None"] = relationship(back_populates="assets")


class AssetFolder(Base, UuidMixin, TimestampMixin):
    __tablename__ = "asset_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_folders.id", ondelete="CASCADE"), nullable=True, index=True
    )

    assets: Mapped[list[Asset]] = relationship(back_populates="folder")
    parent: Mapped["AssetFolder | None"] = relationship(
        remote_side="AssetFolder.id", back_populates="children"
    )
    children: Mapped[list["AssetFolder"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )


class ProjectAlbumAsset(Base, UuidMixin, TimestampMixin):
    __tablename__ = "project_album_assets"
    __table_args__ = (UniqueConstraint("album_id", "asset_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    album_id: Mapped[int] = mapped_column(
        ForeignKey("project_albums.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    caption: Mapped[str] = mapped_column(String(300), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    album: Mapped[ProjectAlbum] = relationship(back_populates="assets")
    asset: Mapped[Asset] = relationship()


class Certificate(Base, UuidMixin, TimestampMixin):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    issuer: Mapped[str] = mapped_column(String(200), default="")
    certificate_type: Mapped[str] = mapped_column(String(40), default="other", index=True)
    issued_at: Mapped[str] = mapped_column(String(30), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    credential_no: Mapped[str] = mapped_column(String(160), default="")
    credential_url: Mapped[str] = mapped_column(String(1000), default="")
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    icon_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    icon_name: Mapped[str] = mapped_column(String(100), default="")
    icon_svg: Mapped[str] = mapped_column(Text, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    translations: Mapped[dict] = mapped_column(JSON, default=dict)
    content_language_mode: Mapped[str] = mapped_column(String(20), default="bilingual")

    asset: Mapped[Asset | None] = relationship(foreign_keys=[asset_id])
    icon_asset: Mapped[Asset | None] = relationship(foreign_keys=[icon_asset_id])
    projects: Mapped[list[Project]] = relationship(
        secondary=project_certificates, back_populates="certificates"
    )


class ProjectAsset(Base, UuidMixin, TimestampMixin):
    __tablename__ = "project_assets"
    __table_args__ = (UniqueConstraint("project_id", "asset_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    usage: Mapped[str] = mapped_column(String(40), default="gallery")
    caption: Mapped[str] = mapped_column(String(300), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    project: Mapped[Project] = relationship(back_populates="assets")
    asset: Mapped[Asset] = relationship()


class Resume(Base, UuidMixin, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    language: Mapped[str] = mapped_column(String(20), default="zh-CN")
    resume_type: Mapped[str] = mapped_column(String(40), default="technical")
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), index=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    version: Mapped[str] = mapped_column(String(40), default="1.0")
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    asset: Mapped[Asset] = relationship()


class FileVersion(Base, UuidMixin, TimestampMixin):
    __tablename__ = "file_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_uuid: Mapped[str] = mapped_column(String(36), index=True)
    asset_uuid: Mapped[str] = mapped_column(String(36))
    version_label: Mapped[str] = mapped_column(String(40))


class SiteSetting(Base, TimestampMixin):
    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Visitor(Base, UuidMixin):
    __tablename__ = "visitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    masked_ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    encrypted_ip: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(120), default="", index=True)
    country_code: Mapped[str] = mapped_column(String(10), default="", index=True)
    region: Mapped[str] = mapped_column(String(160), default="", index=True)
    city: Mapped[str] = mapped_column(String(160), default="", index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    visit_count: Mapped[int] = mapped_column(Integer, default=1)
    sessions: Mapped[list["VisitorSession"]] = relationship(
        back_populates="visitor", cascade="all, delete-orphan"
    )


class VisitorSession(Base, UuidMixin):
    __tablename__ = "visitor_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visitor_id: Mapped[int] = mapped_column(
        ForeignKey("visitors.id", ondelete="CASCADE"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, default="")
    device_type: Mapped[str] = mapped_column(String(40), default="unknown")
    browser: Mapped[str] = mapped_column(String(80), default="unknown")
    operating_system: Mapped[str] = mapped_column(String(80), default="unknown")
    language: Mapped[str] = mapped_column(String(40), default="")
    timezone: Mapped[str] = mapped_column(String(80), default="")
    screen_size: Mapped[str] = mapped_column(String(40), default="")
    referer: Mapped[str] = mapped_column(Text, default="")
    utm_source: Mapped[str] = mapped_column(String(200), default="")
    utm_medium: Mapped[str] = mapped_column(String(200), default="")
    utm_campaign: Mapped[str] = mapped_column(String(200), default="")
    attention_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    score_reasons: Mapped[list[dict]] = mapped_column(JSON, default=list)
    visitor: Mapped[Visitor] = relationship(back_populates="sessions")


class AnalyticsEvent(Base, UuidMixin):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visitor_uuid: Mapped[str] = mapped_column(String(36), index=True)
    session_uuid: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    page_type: Mapped[str] = mapped_column(String(80), default="", index=True)
    page_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    project_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    asset_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_data: Mapped[dict] = mapped_column(JSON, default=dict)
    referer: Mapped[str] = mapped_column(Text, default="")
    utm_source: Mapped[str] = mapped_column(String(200), default="")
    utm_medium: Mapped[str] = mapped_column(String(200), default="")
    utm_campaign: Mapped[str] = mapped_column(String(200), default="")
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, default="")
    device_type: Mapped[str] = mapped_column(String(40), default="unknown")
    browser: Mapped[str] = mapped_column(String(80), default="unknown")
    operating_system: Mapped[str] = mapped_column(String(80), default="unknown")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


Index(
    "ix_analytics_session_timestamp",
    AnalyticsEvent.session_uuid,
    AnalyticsEvent.timestamp,
)
Index(
    "ix_analytics_visitor_project",
    AnalyticsEvent.visitor_uuid,
    AnalyticsEvent.project_uuid,
)


class DailyAnalytics(Base):
    __tablename__ = "daily_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    page_views: Mapped[int] = mapped_column(Integer, default=0)
    unique_visitors: Mapped[int] = mapped_column(Integer, default=0)
    project_views: Mapped[int] = mapped_column(Integer, default=0)
    resume_views: Mapped[int] = mapped_column(Integer, default=0)
    resume_downloads: Mapped[int] = mapped_column(Integer, default=0)


class AuditLog(Base, UuidMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_user_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), default="")
    entity_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class LoginLog(Base, UuidMixin):
    __tablename__ = "login_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_agent: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class UploadTask(Base, UuidMixin, TimestampMixin):
    __tablename__ = "upload_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    asset_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True)
