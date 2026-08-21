from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import AsyncIterator

import httpx
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class AIServiceError(RuntimeError):
    pass


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_api_key(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii") if value else ""


def decrypt_api_key(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise AIServiceError("AI API Key 无法解密，请重新保存配置") from exc


def api_endpoint(base_url: str, endpoint: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/{endpoint.lstrip('/')}"
    return f"{base}/v1/{endpoint.lstrip('/')}"


async def fetch_models(base_url: str, api_key: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(api_endpoint(base_url, "models"), headers=headers)
            response.raise_for_status()
            data = response.json().get("data", [])
    except (httpx.HTTPError, ValueError) as exc:
        raise AIServiceError(f"拉取模型失败：{exc}") from exc
    return sorted(
        [{"id": str(item.get("id", "")), "owned_by": str(item.get("owned_by", ""))} for item in data if item.get("id")],
        key=lambda item: item["id"],
    )


async def stream_chat(base_url: str, api_key: str, model: str, system: str, user: str) -> AsyncIterator[dict]:
    payload = {
        "model": model,
        "stream": True,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=20)) as client:
            async with client.stream("POST", api_endpoint(base_url, "chat/completions"), headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        delta = json.loads(raw).get("choices", [{}])[0].get("delta", {})
                    except json.JSONDecodeError:
                        continue
                    reasoning = delta.get("reasoning_content") or delta.get("reasoning")
                    content = delta.get("content")
                    if reasoning:
                        yield {"type": "reasoning", "content": reasoning}
                    if content:
                        yield {"type": "content", "content": content}
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise AIServiceError(f"AI 服务返回 {exc.response.status_code}：{detail}") from exc
    except httpx.HTTPError as exc:
        raise AIServiceError(f"AI 服务连接失败：{exc}") from exc


TRANSLATION_PROMPT = """You are the bilingual content translator for a professional portfolio CMS.
Translate every human-readable value from the source language to the target language. Preserve keys, arrays,
Markdown, numbers, URLs, product names and technical terms. Return one valid JSON object only, with exactly the
same structure and no commentary. Do not invent achievements or metrics."""

RESUME_PROMPT = """You extract a resume into a portfolio CMS draft. Return one valid JSON object only.
Schema: {profile:{person_name,headline,bio,current_identity,location,email,research_directions:[string],skills:[string]},
projects:[{title,subtitle,summary,background,problem,solution,architecture,contributions:[string],technologies:[string],outcomes:[string],start_date,end_date,role,project_state}],
certificates:[{name,issuer,certificate_type,issued_at,description}], warnings:[string]}.
Use only evidence in the resume. Keep exact metrics. Unknown values must be empty strings or empty arrays.
certificate_type must be scholarship, competition, patent, course, or other. project_state must be active,
completed, or research. The output is a reviewable draft, never claim unsupported facts."""


def parse_json_output(value: str) -> dict:
    cleaned = value.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIServiceError("模型未返回有效的结构化 JSON，请重试或更换模型") from exc
    if not isinstance(result, dict):
        raise AIServiceError("模型输出必须是 JSON 对象")
    return result
