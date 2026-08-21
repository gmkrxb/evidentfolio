from __future__ import annotations

from collections import Counter
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from user_agents import parse

from app.analytics.geolocation import resolve_ip_location
from app.core.time import utcnow
from app.models import AnalyticsEvent, Project, Visitor, VisitorSession
from app.schemas.analytics import AnalyticsEventInput
from app.security.network import masked_ip


SCORE_RULES: dict[str, tuple[int, str]] = {
    "project_view": (8, "查看项目详情"),
    "project_dwell": (12, "在项目页面深度停留"),
    "image_view": (3, "查看项目图片"),
    "video_start": (6, "播放演示视频"),
    "document_preview": (7, "预览项目文档"),
    "resume_view": (12, "查看简历"),
    "resume_download": (22, "下载简历"),
    "demo_click": (15, "打开在线演示"),
    "repository_click": (12, "打开代码仓库"),
}


def device_details(user_agent: str) -> tuple[str, str, str]:
    parsed = parse(user_agent)
    device = "mobile" if parsed.is_mobile else "tablet" if parsed.is_tablet else "desktop"
    return device, parsed.browser.family or "unknown", parsed.os.family or "unknown"


def get_or_create_visitor_session(
    db: Session,
    visitor_uuid: str | None,
    session_uuid: str | None,
    ip_digest: str | None,
    raw_ip: str,
    user_agent: str,
    first_event: AnalyticsEventInput,
) -> tuple[Visitor, VisitorSession, bool]:
    now = utcnow()
    visitor = (
        db.scalar(select(Visitor).where(Visitor.uuid == visitor_uuid))
        if visitor_uuid
        else None
    )
    is_new = visitor is None
    if visitor is None:
        location = resolve_ip_location(raw_ip)
        visitor = Visitor(
            ip_hash=ip_digest,
            masked_ip=masked_ip(raw_ip),
            country=location.get("country", ""),
            country_code=location.get("country_code", ""),
            region=location.get("region", ""),
            city=location.get("city", ""),
        )
        db.add(visitor)
        db.flush()
    else:
        visitor.last_seen_at = now

    session = (
        db.scalar(
            select(VisitorSession).where(
                VisitorSession.uuid == session_uuid,
                VisitorSession.visitor_id == visitor.id,
                VisitorSession.last_seen_at >= now - timedelta(minutes=45),
            )
        )
        if session_uuid
        else None
    )
    if session is None:
        device, browser, operating_system = device_details(user_agent)
        session = VisitorSession(
            visitor_id=visitor.id,
            user_agent=user_agent[:2000],
            device_type=device,
            browser=browser,
            operating_system=operating_system,
            language=first_event.language,
            timezone=first_event.timezone,
            screen_size=first_event.screen_size,
            referer=first_event.referer,
            utm_source=first_event.utm_source,
            utm_medium=first_event.utm_medium,
            utm_campaign=first_event.utm_campaign,
        )
        db.add(session)
        visitor.visit_count += 0 if is_new else 1
        db.flush()
    else:
        session.last_seen_at = now
    return visitor, session, is_new


def record_events(
    db: Session,
    visitor: Visitor,
    session: VisitorSession,
    inputs: list[AnalyticsEventInput],
    ip_digest: str | None,
    user_agent: str,
) -> None:
    device, browser, operating_system = device_details(user_agent)
    for item in inputs:
        db.add(
            AnalyticsEvent(
                visitor_uuid=visitor.uuid,
                session_uuid=session.uuid,
                event_type=item.event_type,
                page_type=item.page_type,
                page_uuid=item.page_uuid,
                project_uuid=item.project_uuid,
                asset_uuid=item.asset_uuid,
                event_data=item.event_data,
                referer=item.referer,
                utm_source=item.utm_source,
                utm_medium=item.utm_medium,
                utm_campaign=item.utm_campaign,
                ip_hash=ip_digest,
                user_agent=user_agent[:2000],
                device_type=device,
                browser=browser,
                operating_system=operating_system,
            )
        )
    db.flush()
    recalculate_score(db, session)


def recalculate_score(db: Session, session: VisitorSession) -> None:
    events = list(
        db.scalars(
            select(AnalyticsEvent).where(AnalyticsEvent.session_uuid == session.uuid)
        )
    )
    counts = Counter(event.event_type for event in events)
    reasons: list[dict] = []
    score = 0
    for event_type, (points, label) in SCORE_RULES.items():
        count = counts[event_type]
        if count:
            awarded = points * min(count, 3)
            score += awarded
            reasons.append({"rule": label, "count": count, "points": awarded})
    project_count = len({event.project_uuid for event in events if event.project_uuid})
    if project_count >= 2:
        points = min(project_count, 5) * 4
        score += points
        reasons.append({"rule": "查看多个项目", "count": project_count, "points": points})
    dwell_seconds = sum(
        min(int(event.event_data.get("seconds", 0)), 600)
        for event in events
        if event.event_type == "project_dwell"
    )
    if dwell_seconds >= 60:
        points = min(dwell_seconds // 60, 5) * 4
        score += points
        reasons.append({"rule": "项目停留时长", "count": dwell_seconds, "points": points})
    session.attention_score = min(score, 100)
    session.score_reasons = reasons


def overview(db: Session) -> dict:
    today = utcnow().date().isoformat()
    total_views = db.scalar(
        select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.event_type == "page_view")
    ) or 0
    today_views = db.scalar(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.event_type == "page_view",
            func.date(AnalyticsEvent.timestamp) == today,
        )
    ) or 0
    unique_visitors = db.scalar(select(func.count(Visitor.id))) or 0
    returning_visitors = db.scalar(
        select(func.count(Visitor.id)).where(Visitor.visit_count > 1)
    ) or 0
    event_counts = dict(
        db.execute(
            select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
            .group_by(AnalyticsEvent.event_type)
        ).all()
    )
    project_ranking = [
        {
            "project_uuid": project_uuid,
            "project_title": project_title or "已删除项目",
            "views": views,
        }
        for project_uuid, project_title, views in db.execute(
            select(
                AnalyticsEvent.project_uuid,
                Project.title,
                func.count(AnalyticsEvent.id),
            )
            .outerjoin(Project, Project.uuid == AnalyticsEvent.project_uuid)
            .where(
                AnalyticsEvent.event_type == "project_view",
                AnalyticsEvent.project_uuid.is_not(None),
            )
            .group_by(AnalyticsEvent.project_uuid, Project.title)
            .order_by(func.count(AnalyticsEvent.id).desc())
            .limit(10)
        ).all()
    ]
    trend = [
        {"date": date, "views": views}
        for date, views in db.execute(
            select(func.date(AnalyticsEvent.timestamp), func.count(AnalyticsEvent.id))
            .where(AnalyticsEvent.timestamp >= utcnow() - timedelta(days=30))
            .group_by(func.date(AnalyticsEvent.timestamp))
            .order_by(func.date(AnalyticsEvent.timestamp))
        ).all()
    ]
    distributions = {}
    for field_name, field in [
        ("devices", AnalyticsEvent.device_type),
        ("browsers", AnalyticsEvent.browser),
        ("operating_systems", AnalyticsEvent.operating_system),
        ("sources", AnalyticsEvent.utm_source),
    ]:
        distributions[field_name] = [
            {"name": name or "direct", "value": count}
            for name, count in db.execute(
                select(field, func.count(AnalyticsEvent.id))
                .group_by(field)
                .order_by(func.count(AnalyticsEvent.id).desc())
                .limit(8)
            ).all()
        ]
    distributions["locations"] = [
        {
            "name": " · ".join(part for part in [country, region, city] if part) or "未知",
            "value": count,
        }
        for country, region, city, count in db.execute(
            select(
                Visitor.country,
                Visitor.region,
                Visitor.city,
                func.count(Visitor.id),
            )
            .group_by(Visitor.country, Visitor.region, Visitor.city)
            .order_by(func.count(Visitor.id).desc())
            .limit(20)
        ).all()
    ]
    return {
        "today_views": today_views,
        "total_views": total_views,
        "unique_visitors": unique_visitors,
        "returning_visitors": returning_visitors,
        "event_counts": event_counts,
        "project_ranking": project_ranking,
        "trend": trend,
        "distributions": distributions,
    }
