from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 50), "#315b4f").save(output, format="PNG")
    return output.getvalue()


def test_empty_english_settings_fall_back_to_original_content():
    from app.api.routes.public import localized_settings
    source = {'headline': '原始标题', 'page_content': {'contact': {'hero_title': '联系我', 'hero_description': '保持联系'}},
              'navigation_items': [{'label': '项目', 'to': '/projects'}], 'home_capabilities': ['研究'],
              'translations': {'en': {'headline': '', 'page_content': {'contact': {'hero_title': 'Contact', 'hero_description': ' '}},
                                      'navigation_items': [{'label': '', 'to': '/projects'}], 'home_capabilities': []}}}
    localized = localized_settings(source, 'en')
    assert localized['headline'] == '原始标题'
    assert localized['page_content']['contact'] == {'hero_title': 'Contact', 'hero_description': '保持联系'}
    assert localized['navigation_items'][0]['label'] == '项目'
    assert localized['home_capabilities'] == ['研究']
    assert source['page_content']['contact']['hero_title'] == '联系我'


def test_public_english_project_uses_album_title_without_duplicate_global_asset(
    admin_client: TestClient,
    csrf_headers: dict[str, str],
    project_payload: dict,
) -> None:
    uploaded = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        data={"is_public": "true"},
        files={"file": ("architecture.png", image_bytes(), "image/png")},
    )
    asset_uuid = uploaded.json()["data"]["uuid"]
    album_uuid = "fe579b83-cbf0-47f5-b99a-c43e4e10bb9d"
    project_payload.update({
        "status": "published",
        "translations": {"en": {"title": "English project", "summary": "English summary"}},
        "content_language_mode": "bilingual",
        "albums": [{
            "uuid": album_uuid,
            "title": "系统架构图",
            "description": "中文说明",
            "display_mode": "grid",
            "asset_uuids": [asset_uuid],
            "sort_order": 0,
            "translations": {"en": {"title": "System architecture", "description": "Architecture figures"}},
        }],
    })
    created = admin_client.post("/api/v1/admin/projects", json=project_payload, headers=csrf_headers)
    assert created.status_code == 200, created.text
    project_uuid = created.json()["data"]["uuid"]

    public = admin_client.get(f"/api/v1/public/projects/{project_uuid}?locale=en")
    assert public.status_code == 200, public.text
    data = public.json()["data"]
    assert data["title"] == "English project"
    assert data["albums"][0]["title"] == "System architecture"
    assert data["albums"][0]["assets"][0]["asset"]["uuid"] == asset_uuid
    assert data["assets"] == []


def test_ai_config_masks_saved_api_key(
    admin_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    saved = admin_client.put(
        "/api/v1/admin/ai/config",
        headers=csrf_headers,
        json={
            "base_url": "https://api.example.com/v1",
            "api_key": "test-secret-key",
            "model": "example-model",
            "enabled": True,
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["data"]["has_api_key"] is True
    assert "test-secret-key" not in saved.text

    loaded = admin_client.get("/api/v1/admin/ai/config")
    assert loaded.status_code == 200
    assert loaded.json()["data"] == {
        "base_url": "https://api.example.com/v1",
        "model": "example-model",
        "enabled": True,
        "has_api_key": True,
        "max_context_chars": 32000,
    }
    assert "test-secret-key" not in loaded.text
