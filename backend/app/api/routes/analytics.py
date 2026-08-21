from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from app.analytics.service import get_or_create_visitor_session, record_events
from app.api.response import ApiError, ok
from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.analytics import ALLOWED_EVENT_TYPES, AnalyticsBatchInput
from app.security.network import client_ip, ip_hash

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/events")
def events(
    payload: AnalyticsBatchInput,
    request: Request,
    response: Response,
    visitor_cookie: str | None = Cookie(default=None, alias="portfolio_visitor"),
    session_cookie: str | None = Cookie(default=None, alias="portfolio_analytics_session"),
    db: Session = Depends(get_db),
) -> dict:
    settings = get_settings()
    if not settings.ANALYTICS_ENABLED:
        return ok(request, {"accepted": 0, "disabled": True})
    invalid = [item.event_type for item in payload.events if item.event_type not in ALLOWED_EVENT_TYPES]
    if invalid:
        raise ApiError(422, "INVALID_EVENT_TYPE", f"不支持的事件类型：{invalid[0]}")
    raw_ip = client_ip(request)
    digest = ip_hash(raw_ip)
    user_agent = request.headers.get("user-agent", "")
    visitor, session, is_new = get_or_create_visitor_session(
        db,
        visitor_cookie,
        session_cookie,
        digest,
        raw_ip,
        user_agent,
        payload.events[0],
    )
    record_events(db, visitor, session, payload.events, digest, user_agent)
    db.commit()
    max_age = 365 * 24 * 3600
    response.set_cookie(
        "portfolio_visitor",
        visitor.uuid,
        max_age=max_age,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "portfolio_analytics_session",
        session.uuid,
        max_age=45 * 60,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        path="/",
    )
    return ok(
        request,
        {
            "accepted": len(payload.events),
            "visitor_uuid": visitor.uuid,
            "session_uuid": session.uuid,
            "is_new_visitor": is_new,
        },
    )

