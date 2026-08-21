from __future__ import annotations

import secrets

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.response import ApiError
from app.core.database import get_db
from app.core.time import utcnow
from app.models import AdminSession, AdminUser
from app.services.auth import digest


def optional_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser | None:
    raw_token = request.cookies.get("portfolio_session")
    if not raw_token:
        return None
    session = db.scalar(
        select(AdminSession).where(
            AdminSession.token_hash == digest(raw_token),
            AdminSession.revoked_at.is_(None),
            AdminSession.expires_at > utcnow(),
        )
    )
    return session.user if session and session.user.is_active else None


def require_admin(user: AdminUser | None = Depends(optional_admin)) -> AdminUser:
    if not user:
        raise ApiError(401, "AUTH_REQUIRED", "请先登录管理后台")
    return user


def require_csrf(
    request: Request,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
) -> AdminUser:
    raw_token = request.cookies.get("portfolio_session")
    cookie_csrf = request.cookies.get("portfolio_csrf")
    header_csrf = request.headers.get("x-csrf-token")
    session = db.scalar(
        select(AdminSession).where(
            AdminSession.token_hash == digest(raw_token or ""),
            AdminSession.admin_user_id == user.id,
            AdminSession.revoked_at.is_(None),
            AdminSession.expires_at > utcnow(),
        )
    )
    if (
        not session
        or not cookie_csrf
        or not header_csrf
        or not secrets.compare_digest(cookie_csrf, header_csrf)
        or not secrets.compare_digest(session.csrf_token, header_csrf)
    ):
        raise ApiError(403, "CSRF_INVALID", "请求验证失败，请刷新页面后重试")
    return user

