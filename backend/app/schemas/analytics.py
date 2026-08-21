from __future__ import annotations

from pydantic import BaseModel, Field


ALLOWED_EVENT_TYPES = {
    "page_view",
    "home_view",
    "project_list_view",
    "project_view",
    "project_dwell",
    "image_view",
    "video_start",
    "video_progress",
    "document_preview",
    "document_download",
    "resume_view",
    "resume_download",
    "demo_click",
    "repository_click",
    "contact_click",
    "filter_use",
    "search",
    "page_exit",
}


class AnalyticsEventInput(BaseModel):
    event_type: str
    page_type: str = ""
    page_uuid: str | None = None
    project_uuid: str | None = None
    asset_uuid: str | None = None
    event_data: dict = {}
    referer: str = Field(default="", max_length=2000)
    utm_source: str = Field(default="", max_length=200)
    utm_medium: str = Field(default="", max_length=200)
    utm_campaign: str = Field(default="", max_length=200)
    language: str = Field(default="", max_length=40)
    timezone: str = Field(default="", max_length=80)
    screen_size: str = Field(default="", max_length=40)


class AnalyticsBatchInput(BaseModel):
    events: list[AnalyticsEventInput] = Field(min_length=1, max_length=50)

