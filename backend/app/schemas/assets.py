from __future__ import annotations

from pydantic import BaseModel, Field


class AssetPatch(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    description: str = ""
    logical_group: str = Field(default="", max_length=120)
    is_public: bool = False
    folder_uuid: str | None = None
    translations: dict[str, dict] = Field(default_factory=dict)


class AssetFolderInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    sort_order: int = 0
    parent_uuid: str | None = None


class AssetBatchMoveInput(BaseModel):
    asset_uuids: list[str] = Field(min_length=1, max_length=500)
    folder_uuid: str | None = None


class ResumeInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    language: str = "zh-CN"
    resume_type: str = "technical"
    asset_uuid: str
    is_default: bool = False
    is_public: bool = False
    version: str = "1.0"


class ResumePatch(ResumeInput):
    pass


class CertificateInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    issuer: str = Field(default="", max_length=200)
    certificate_type: str = Field(default="other", max_length=40)
    issued_at: str = Field(default="", max_length=30)
    description: str = ""
    credential_no: str = Field(default="", max_length=160)
    credential_url: str = Field(default="", max_length=1000)
    asset_uuid: str | None = None
    icon_asset_uuid: str | None = None
    icon_name: str = Field(default="", max_length=100)
    icon_svg: str = Field(default="", max_length=20_000)
    is_public: bool = False
    sort_order: int = 0
    translations: dict[str, dict] = Field(default_factory=dict)
    content_language_mode: str = Field(default="bilingual", pattern="^(bilingual|single_zh|single_en)$")


class CertificatePatch(CertificateInput):
    pass
