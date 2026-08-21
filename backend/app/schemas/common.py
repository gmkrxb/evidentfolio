from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ApiEnvelope(BaseModel):
    success: bool = True
    data: Any = None
    message: str | None = None
    request_id: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: list[dict[str, Any]] | None = None

