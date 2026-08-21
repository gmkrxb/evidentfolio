from __future__ import annotations

import ipaddress
import logging
from urllib.parse import quote

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def resolve_ip_location(ip: str) -> dict[str, str]:
    settings = get_settings()
    if not settings.IP_GEOLOCATION_ENABLED or not ip:
        return {}
    try:
        address = ipaddress.ip_address(ip)
        if address.is_private or address.is_loopback or address.is_reserved or address.is_multicast:
            return {}
    except ValueError:
        return {}
    url = settings.IP_GEOLOCATION_API_URL.replace("{ip}", quote(ip, safe=""))
    try:
        response = httpx.get(
            url,
            params={"fields": "success,country,country_code,region,city", "lang": "zh-CN"},
            timeout=settings.IP_GEOLOCATION_TIMEOUT_SECONDS,
            follow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success", True):
            return {}
        return {
            "country": str(payload.get("country") or "")[:120],
            "country_code": str(payload.get("country_code") or "")[:10],
            "region": str(payload.get("region") or "")[:160],
            "city": str(payload.get("city") or "")[:160],
        }
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("IP geolocation failed: %s", type(exc).__name__)
        return {}

