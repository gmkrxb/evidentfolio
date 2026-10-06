from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.response import ok
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Visitor, VisitorSession
from app.security.privacy import CONSENT_COOKIE, CONSENT_AGE, decode_consent, encode_consent

router = APIRouter(prefix="/privacy", tags=["privacy"])


class ConsentInput(BaseModel):
    analytics: bool = False
    raw_ip: bool = False


@router.get("/consent")
def consent_status(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    data = decode_consent(request.cookies.get(CONSENT_COOKIE, ""))
    return ok(request, {"decided": bool(data), "analytics": bool(data.get("analytics")), "raw_ip": bool(data.get("raw_ip"))})


@router.put("/consent")
def save_consent(payload: ConsentInput, request: Request, response: Response, db: Session = Depends(get_db)):
    raw_ip = payload.analytics and payload.raw_ip
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(CONSENT_COOKIE, encode_consent(payload.analytics, raw_ip), max_age=CONSENT_AGE, httponly=True, secure=get_settings().SECURE_COOKIES, samesite="lax", path="/")
    if not raw_ip:
        visitor = db.scalar(select(Visitor).where(Visitor.uuid == request.cookies.get("portfolio_visitor", "")))
        if visitor:
            visitor.encrypted_ip = None
            db.execute(update(VisitorSession).where(VisitorSession.visitor_id == visitor.id).values(encrypted_ip=None))
            db.commit()
    if not payload.analytics:
        for name in ("portfolio_visitor", "portfolio_analytics_session"):
            response.delete_cookie(name, path="/")
    return ok(request, {"decided": True, "analytics": payload.analytics, "raw_ip": raw_ip})
