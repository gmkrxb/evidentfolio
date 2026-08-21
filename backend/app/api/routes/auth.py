from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.dependencies import require_admin, require_csrf
from app.api.response import ApiError, ok
from app.core.config import get_settings
from app.core.database import get_db
from app.core.time import utcnow
from app.models import AdminSession, AdminUser, LoginLog, SiteSetting
from app.schemas.auth import InitializeRequest, LoginRequest
from app.security.network import client_ip, ip_hash
from app.services.auth import (
    create_session,
    digest,
    failed_login_count,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])
setup_router = APIRouter(prefix="/setup", tags=["setup"])


def user_data(user: AdminUser) -> dict:
    return {
        "uuid": user.uuid,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
    }


def initial_site_data(payload: InitializeRequest) -> dict:
    english = payload.primary_language == "en"
    labels = (
        [("Home", "/"), ("Projects", "/projects"), ("Credentials", "/certificates"),
         ("Résumés", "/resumes"), ("Contact", "/contact")]
        if english else
        [("首页", "/"), ("项目", "/projects"), ("证书", "/certificates"),
         ("简历", "/resumes"), ("联系", "/contact")]
    )
    page_content = {
        "projects": {
            "eyebrow": "Case studies" if english else "案例研究",
            "title": "Projects" if english else "项目",
            "description": "",
        },
        "resumes": {
            "eyebrow": "Curriculum vitae" if english else "个人简历",
            "title": "Résumés" if english else "简历",
            "description": "",
        },
        "certificates": {
            "eyebrow": "Credentials" if english else "证书与荣誉",
            "title": "Credentials & honors" if english else "证书与荣誉",
            "description": "",
        },
        "contact": {
            "eyebrow": "Contact" if english else "联系方式",
            "title": "Let's connect" if english else "保持联系",
            "description": "",
        },
    }
    return {
        "site_name": payload.site_name,
        "person_name": payload.person_name,
        "brand_mark_text": payload.person_name[:2].upper(),
        "primary_language": payload.primary_language,
        "navigation_items": [
            {"label": label, "to": path, "kind": "route"} for label, path in labels
        ],
        "page_content": page_content,
        "contact_methods": [],
        "home_stats": [],
        "home_capabilities": [],
        "analytics_enabled": True,
        "analytics_retention_days": 365,
        "analytics_notice_enabled": True,
        "featured_project_count": 3,
    }


@setup_router.get("/status")
def setup_status(request: Request, db: Session = Depends(get_db)) -> dict:
    count = db.scalar(select(func.count(AdminUser.id))) or 0
    return ok(request, {"required": count == 0})


@setup_router.post("/initialize")
def initialize(
    payload: InitializeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    count = db.scalar(select(func.count(AdminUser.id))) or 0
    if count:
        raise ApiError(409, "SETUP_CLOSED", "初始化入口已经关闭")
    user = AdminUser(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    settings = db.get(SiteSetting, 1)
    if settings is None:
        settings = SiteSetting(id=1, data={})
        db.add(settings)
    settings.data = {**(settings.data or {}), **initial_site_data(payload)}
    raw_token, admin_session = create_session(
        db, user, ip_hash(client_ip(request)), request.headers.get("user-agent", "")
    )
    write_audit(db, request, user, "system.initialize", "admin_user", user.uuid)
    db.commit()
    set_auth_cookies(response, raw_token, admin_session.csrf_token)
    return ok(request, {"user": user_data(user)}, "初始化完成")


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    current_ip_hash = ip_hash(client_ip(request))
    if failed_login_count(db, payload.username, current_ip_hash) >= get_settings().LOGIN_MAX_ATTEMPTS:
        raise ApiError(429, "LOGIN_RATE_LIMITED", "登录失败次数过多，请稍后重试")
    user = db.scalar(select(AdminUser).where(AdminUser.username == payload.username))
    authenticated = bool(
        user and user.is_active and verify_password(payload.password, user.password_hash)
    )
    db.add(
        LoginLog(
            username=payload.username,
            success=authenticated,
            ip_hash=current_ip_hash,
            user_agent=request.headers.get("user-agent", "")[:2000],
            reason="" if authenticated else "invalid_credentials",
        )
    )
    if not authenticated or user is None:
        db.commit()
        raise ApiError(401, "INVALID_CREDENTIALS", "用户名或密码错误")
    raw_token, admin_session = create_session(
        db, user, current_ip_hash, request.headers.get("user-agent", "")
    )
    write_audit(db, request, user, "auth.login", "admin_user", user.uuid)
    db.commit()
    set_auth_cookies(response, raw_token, admin_session.csrf_token)
    return ok(request, {"user": user_data(user)})


@router.get("/me")
def me(request: Request, user: AdminUser = Depends(require_admin)) -> dict:
    return ok(request, {"user": user_data(user)})


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    user: AdminUser = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    raw_token = request.cookies.get("portfolio_session", "")
    session = db.scalar(
        select(AdminSession).where(AdminSession.token_hash == digest(raw_token))
    )
    if session:
        session.revoked_at = utcnow()
    write_audit(db, request, user, "auth.logout", "admin_user", user.uuid)
    db.commit()
    response.delete_cookie("portfolio_session", path="/")
    response.delete_cookie("portfolio_csrf", path="/")
    return ok(request, None, "已安全退出")


def set_auth_cookies(response: Response, raw_token: str, csrf_token: str) -> None:
    settings = get_settings()
    max_age = settings.SESSION_EXPIRE_HOURS * 3600
    response.set_cookie(
        "portfolio_session",
        raw_token,
        max_age=max_age,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "portfolio_csrf",
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        path="/",
    )
