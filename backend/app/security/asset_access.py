"""资源访问票据、内容加密与限流。

公开资源有两种访问方式：
- download（可下载）：网页内可预览；下载必须先申请一张带签名、短时有效、次数有限的下载票据；
- view（仅可查看）：仅对浏览器可预览的格式生效（图片、视频、音频、PDF、Markdown、纯文本），
  原始地址与下载接口一律拒绝；内容只能凭查看票据获取，并以一次性密钥做 AES-CTR 加密后传输，
  由前端在内存中解密渲染。

票据与浏览器 UA 绑定，签名使用 SECRET_KEY 派生的独立密钥；所有入口按访客 IP 限流。
服务为单进程部署（--workers 1），因此限流与票据计数保存在进程内存中即可。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Request

from app.core.config import get_settings
from app.security.network import client_ip

PREVIEWABLE_EXTENSIONS = {".md", ".markdown", ".txt"}
PREVIEWABLE_TEXT_TYPES = {"text/plain", "text/markdown"}
MAX_USES = {"view": 3, "stream": 400, "download": 3}


def is_previewable(mime_type: str, extension: str) -> bool:
    mime = (mime_type or "").lower()
    return (
        mime.startswith(("image/", "video/", "audio/"))
        or mime == "application/pdf"
        or mime in PREVIEWABLE_TEXT_TYPES
        or (extension or "").lower() in PREVIEWABLE_EXTENSIONS
    )


def is_view_only(asset) -> bool:
    return getattr(asset, "access_mode", "download") == "view" and is_previewable(
        asset.mime_type, asset.extension
    )


def _key(purpose: str) -> bytes:
    return hmac.new(
        get_settings().SECRET_KEY.encode("utf-8"), f"asset-access:{purpose}".encode(), hashlib.sha256
    ).digest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _ua(request: Request) -> str:
    return hashlib.sha256(request.headers.get("user-agent", "").encode()).hexdigest()[:16]


class RateLimiter:
    """滑动窗口限流（进程内）。"""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, bucket: str, key: str, limit: int, window: float) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            hits = self._hits[(bucket, key)]
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            if len(self._hits) > 50_000:
                for stale in [k for k, v in self._hits.items() if not v or v[-1] <= now - 3600]:
                    self._hits.pop(stale, None)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


@dataclass
class Ticket:
    token: str
    purpose: str
    expires_at: int
    key: bytes | None = None
    counter: bytes | None = None


class TicketStore:
    def __init__(self) -> None:
        self._uses: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def consume(self, nonce: str, purpose: str, expires_at: int) -> int | None:
        """记一次使用；返回此前已使用的次数，超过上限时返回 None。"""
        now = time.time()
        with self._lock:
            if len(self._uses) > 20_000:
                for stale in [k for k, (_, exp) in self._uses.items() if exp < now]:
                    self._uses.pop(stale, None)
            uses, _ = self._uses.get(nonce, (0, expires_at))
            if uses >= MAX_USES.get(purpose, 1):
                return None
            self._uses[nonce] = (uses + 1, expires_at)
            return uses

    def reset(self) -> None:
        with self._lock:
            self._uses.clear()


tickets = TicketStore()


def _signature(asset_uuid: str, purpose: str, expires_at: int, nonce: str, ua: str) -> str:
    message = f"{asset_uuid}|{purpose}|{expires_at}|{nonce}|{ua}".encode()
    return _b64(hmac.new(_key("ticket"), message, hashlib.sha256).digest()[:20])


def cipher_material(asset_uuid: str, nonce: str) -> tuple[bytes, bytes]:
    """由票据随机数派生的一次性 AES-256 密钥与 CTR 初始计数器（低 64 位从 0 开始）。"""
    digest = hmac.new(_key("cipher"), f"{asset_uuid}|{nonce}".encode(), hashlib.sha512).digest()
    return digest[:32], digest[32:40] + b"\x00" * 8


def issue_ticket(asset_uuid: str, purpose: str, request: Request) -> Ticket:
    settings = get_settings()
    ttl = settings.ASSET_STREAM_TTL_SECONDS if purpose == "stream" else settings.ASSET_TICKET_TTL_SECONDS
    expires_at = int(time.time()) + ttl
    nonce = _b64(secrets.token_bytes(12))
    signature = _signature(asset_uuid, purpose, expires_at, nonce, _ua(request))
    ticket = Ticket(f"{purpose}.{expires_at}.{nonce}.{signature}", purpose, expires_at)
    if purpose == "view":
        ticket.key, ticket.counter = cipher_material(asset_uuid, nonce)
    return ticket


@dataclass
class Redeemed:
    purpose: str
    nonce: str
    first_use: bool


def redeem_ticket(asset_uuid: str, token: str, request: Request) -> Redeemed | None:
    try:
        purpose, expires_text, nonce, signature = token.split(".")
        expires_at = int(expires_text)
    except (ValueError, AttributeError):
        return None
    if purpose not in MAX_USES or expires_at < time.time():
        return None
    expected = _signature(asset_uuid, purpose, expires_at, nonce, _ua(request))
    if not hmac.compare_digest(expected, signature):
        return None
    before = tickets.consume(nonce, purpose, expires_at)
    if before is None:
        return None
    return Redeemed(purpose, nonce, before == 0)


def visitor(request: Request) -> str:
    return client_ip(request) or "unknown"


def is_cross_site_embed(request: Request) -> bool:
    """他站盗链：浏览器明确标记为跨站的子资源请求。直接打开链接（none）与同站请求不受影响。"""
    site = request.headers.get("sec-fetch-site", "")
    dest = request.headers.get("sec-fetch-dest", "")
    return site == "cross-site" and dest in {"image", "video", "audio", "embed", "object", "iframe", "empty"}
