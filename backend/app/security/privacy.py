from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from app.core.config import get_settings
from app.services.ai import decrypt_api_key, encrypt_api_key, AIServiceError

CONSENT_COOKIE = "portfolio_consent"
CONSENT_AGE = 180 * 24 * 3600


def encode_consent(analytics: bool, raw_ip: bool) -> str:
    value = json.dumps({"analytics": analytics, "raw_ip": analytics and raw_ip, "expires": int(time.time()) + CONSENT_AGE}, separators=(",", ":"))
    body = base64.urlsafe_b64encode(value.encode()).decode()
    signature = hmac.new(get_settings().SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def decode_consent(value: str) -> dict:
    try:
        body, signature = value.split(".", 1)
        expected = hmac.new(get_settings().SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return {}
        data = json.loads(base64.urlsafe_b64decode(body))
        if data.get("expires", 0) <= time.time():
            return {}
        return data
    except (ValueError, TypeError):
        return {}


def encrypt_ip(ip: str) -> str | None:
    return encrypt_api_key(ip) if ip else None


def reveal_ip(value: str | None) -> str | None:
    try:
        return decrypt_api_key(value) if value else None
    except AIServiceError:
        return None
