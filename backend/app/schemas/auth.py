from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=256)


class InitializeRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=120)
    site_name: str = Field(min_length=1, max_length=120)
    person_name: str = Field(min_length=1, max_length=120)
    primary_language: Literal["zh-CN", "en"] = "zh-CN"
