from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class AIConfigInput(BaseModel):
    base_url: HttpUrl
    api_key: str = Field(default="", max_length=1000)
    model: str = Field(default="", max_length=200)
    enabled: bool = True
    max_context_chars: int = Field(default=32000, ge=4000, le=200000)


class AIModelsInput(BaseModel):
    base_url: HttpUrl | None = None
    api_key: str = Field(default="", max_length=1000)


class AITranslateInput(BaseModel):
    source_locale: Literal["zh-CN", "en"]
    target_locale: Literal["zh-CN", "en"]
    entity_type: str = Field(max_length=80)
    content: dict
    existing_translation: dict = Field(default_factory=dict)
    max_context_chars: int | None = Field(default=None, ge=4000, le=200000)


class AIResumeParseInput(BaseModel):
    asset_uuid: str
    source_locale: Literal["zh-CN", "en"] = "zh-CN"


class AIResumeApplyInput(BaseModel):
    result: dict


class AIBatchTranslateInput(BaseModel):
    source_locale: Literal["zh-CN", "en"] = "zh-CN"
    overwrite: bool = False
    only: list[str] | None = Field(default=None, max_length=10000)
    max_context_chars: int | None = Field(default=None, ge=4000, le=200000)
