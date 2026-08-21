from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class AIConfigInput(BaseModel):
    base_url: HttpUrl
    api_key: str = Field(default="", max_length=1000)
    model: str = Field(default="", max_length=200)
    enabled: bool = True


class AIModelsInput(BaseModel):
    base_url: HttpUrl | None = None
    api_key: str = Field(default="", max_length=1000)


class AITranslateInput(BaseModel):
    source_locale: Literal["zh-CN", "en"]
    target_locale: Literal["zh-CN", "en"]
    entity_type: str = Field(max_length=80)
    content: dict


class AIResumeParseInput(BaseModel):
    asset_uuid: str
    source_locale: Literal["zh-CN", "en"] = "zh-CN"


class AIResumeApplyInput(BaseModel):
    result: dict
