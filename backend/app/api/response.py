from __future__ import annotations

from typing import Any

from fastapi import Request


def ok(request: Request, data: Any = None, message: str | None = None) -> dict:
    return {
        "success": True,
        "data": data,
        "message": message,
        "request_id": getattr(request.state, "request_id", ""),
    }


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: list[dict] | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields
        super().__init__(message)

