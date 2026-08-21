from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class LinkInput(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    url: HttpUrl
    link_type: str = "other"
    sort_order: int = 0


class SectionInput(BaseModel):
    client_key: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=180)
    body: str = ""
    section_type: str = "markdown"
    display_mode: Literal[
        "text",
        "single",
        "gallery",
        "carousel",
        "album",
        "video",
        "audio",
        "attachments",
        "mixed",
    ] = "text"
    asset_uuids: list[str] = Field(default_factory=list)
    album_uuid: str | None = None
    heading_level: Literal[2, 3, 4] = 2
    is_visible: bool = True
    sort_order: int = 0
    translations: dict[str, dict] = Field(default_factory=dict)


class ContentLayoutInput(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    kind: Literal["builtin", "custom"]
    visible: bool = True
    sort_order: int = 0


class AlbumInput(BaseModel):
    uuid: str | None = None
    title: str = Field(min_length=1, max_length=180)
    description: str = ""
    display_mode: Literal["grid", "carousel"] = "grid"
    asset_uuids: list[str] = Field(default_factory=list)
    sort_order: int = 0
    translations: dict[str, dict] = Field(default_factory=dict)


class ProjectInput(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    subtitle: str = Field(default="", max_length=240)
    summary: str = Field(min_length=1)
    content: str = ""
    background: str = ""
    problem: str = ""
    solution: str = ""
    architecture: str = ""
    contributions: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    role: str = ""
    team_size: int | None = Field(default=None, ge=1)
    status: Literal["draft", "published", "hidden", "archived"] = "draft"
    project_state: str = "completed"
    is_featured: bool = False
    is_open_source: bool = False
    sort_order: int = 0
    category_uuid: str | None = None
    tag_uuids: list[str] = Field(default_factory=list)
    certificate_uuids: list[str] = Field(default_factory=list)
    cover_asset_uuid: str | None = None
    seo_title: str = ""
    seo_description: str = ""
    links: list[LinkInput] = Field(default_factory=list)
    sections: list[SectionInput] = Field(default_factory=list)
    albums: list[AlbumInput] = Field(default_factory=list)
    content_layout: list[ContentLayoutInput] = Field(default_factory=list)
    translations: dict[str, dict] = Field(default_factory=dict)
    content_language_mode: Literal["bilingual", "single_zh", "single_en"] = "bilingual"


class ProjectPatch(ProjectInput):
    pass


class ProjectListQuery(BaseModel):
    q: str = ""
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    featured: bool | None = None
    status: str | None = None
    sort: str = "featured"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=12, ge=1, le=100)
    locale: Literal["zh-CN", "en"] | None = None


class ProjectResponse(BaseModel):
    uuid: str
    title: str
    subtitle: str
    summary: str
    content: str
    background: str
    problem: str
    solution: str
    architecture: str
    contributions: list[str]
    technologies: list[str]
    outcomes: list[str]
    start_date: str
    end_date: str
    role: str
    team_size: int | None
    status: str
    project_state: str
    is_featured: bool
    is_open_source: bool
    sort_order: int
    category: dict | None
    tags: list[dict]
    cover_asset: dict | None
    auto_cover_assets: list[dict]
    links: list[dict]
    sections: list[dict]
    albums: list[dict]
    assets: list[dict]
    seo_title: str
    seo_description: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
