from __future__ import annotations

import pytest

from app.services.ai import api_endpoint


@pytest.mark.parametrize(
    ("base_url", "endpoint", "expected"),
    [
        # 旧行为回归：/v1 结尾原样拼接
        ("https://api.openai.com/v1", "models", "https://api.openai.com/v1/models"),
        ("https://api.openai.com/v1/", "chat/completions", "https://api.openai.com/v1/chat/completions"),
        # 旧行为回归：无版本段时自动补 /v1
        ("https://api.example.com", "models", "https://api.example.com/v1/models"),
        # 非 /v1 版本段结尾：原样使用，不再硬拼 /v1
        ("https://open.bigmodel.cn/api/coding/paas/v4", "models", "https://open.bigmodel.cn/api/coding/paas/v4/models"),
        ("https://generativelanguage.googleapis.com/v1beta", "models", "https://generativelanguage.googleapis.com/v1beta/models"),
        # 版本段在路径中置（网关类地址）：不重复补 /v1
        ("https://gateway.ai.cloudflare.com/v1/account/gateway", "chat/completions", "https://gateway.ai.cloudflare.com/v1/account/gateway/chat/completions"),
        # # 结尾：强制原样使用
        ("https://example.com/custom#", "models", "https://example.com/custom/models"),
        ("https://example.com/custom/#", "models", "https://example.com/custom/models"),
        # 空白与斜杠归一化
        ("  https://api.example.com  ", "models", "https://api.example.com/v1/models"),
        ("/v1", "models", "/v1/models"),
    ],
)
def test_api_endpoint(base_url: str, endpoint: str, expected: str) -> None:
    assert api_endpoint(base_url, endpoint) == expected
