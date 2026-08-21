from __future__ import annotations

import hashlib
import hmac
import ipaddress

from fastapi import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str:
    settings = get_settings()
    direct = request.client.host if request.client else ""
    if is_trusted_proxy(direct):
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        real = request.headers.get("x-real-ip", "").strip()
        candidate = forwarded or real or direct
    else:
        candidate = direct
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return ""


def is_trusted_proxy(ip: str) -> bool:
    if not ip:
        return False
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return ip in get_settings().TRUSTED_PROXY_IPS
    for entry in get_settings().TRUSTED_PROXY_IPS:
        try:
            if address in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            if ip == entry:
                return True
    return False


def ip_hash(ip: str) -> str | None:
    if not ip:
        return None
    return hmac.new(
        get_settings().SECRET_KEY.encode("utf-8"), ip.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def masked_ip(ip: str) -> str | None:
    if not ip:
        return None
    try:
        value = ipaddress.ip_address(ip)
        if value.version == 4:
            parts = ip.split(".")
            return ".".join(parts[:2] + ["*", "*"])
        return ":".join(value.exploded.split(":")[:3]) + ":*:*:*:*:*"
    except ValueError:
        return None


def public_base_url(request: Request) -> str:
    configured = get_settings().PUBLIC_BASE_URL
    if configured:
        return configured
    direct = request.client.host if request.client else ""
    trust_proxy = is_trusted_proxy(direct)
    scheme = (
        request.headers.get("x-forwarded-proto", request.url.scheme)
        if trust_proxy
        else request.url.scheme
    )
    host = (
        request.headers.get("x-forwarded-host", request.headers.get("host", ""))
        if trust_proxy
        else request.headers.get("host", "")
    )
    return f"{scheme}://{host}".rstrip("/")
