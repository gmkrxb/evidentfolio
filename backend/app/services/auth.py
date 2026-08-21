from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utcnow
from app.models import AdminSession, AdminUser, LoginLog

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except VerifyMismatchError:
        return False


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_session(
    db: Session, user: AdminUser, ip_hash: str | None, user_agent: str
) -> tuple[str, AdminSession]:
    settings = get_settings()
    raw_token = secrets.token_urlsafe(48)
    session = AdminSession(
        admin_user_id=user.id,
        token_hash=digest(raw_token),
        csrf_token=secrets.token_urlsafe(36),
        ip_hash=ip_hash,
        user_agent=user_agent[:2000],
        expires_at=utcnow() + timedelta(hours=settings.SESSION_EXPIRE_HOURS),
    )
    db.add(session)
    user.last_login_at = utcnow()
    return raw_token, session


def failed_login_count(db: Session, username: str, ip_hash: str | None) -> int:
    settings = get_settings()
    since = utcnow() - timedelta(minutes=settings.LOGIN_WINDOW_MINUTES)
    statement = select(func.count(LoginLog.id)).where(
        LoginLog.username == username,
        LoginLog.success.is_(False),
        LoginLog.created_at >= since,
    )
    if ip_hash:
        statement = statement.where(LoginLog.ip_hash == ip_hash)
    return db.scalar(statement) or 0

