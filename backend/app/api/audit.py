from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AdminUser, AuditLog
from app.security.network import client_ip, ip_hash


def write_audit(
    db: Session,
    request: Request,
    user: AdminUser | None,
    action: str,
    entity_type: str = "",
    entity_uuid: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            admin_user_uuid=user.uuid if user else None,
            action=action,
            entity_type=entity_type,
            entity_uuid=entity_uuid,
            details=details or {},
            ip_hash=ip_hash(client_ip(request)),
        )
    )

