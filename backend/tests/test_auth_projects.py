from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image


def image_bytes(color: str = "#224b3f") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (80, 50), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_setup_closes_and_login_works(client: TestClient) -> None:
    status = client.get("/api/v1/setup/status")
    assert status.status_code == 200
    assert status.json()["data"]["required"] is True
    initialized = client.post(
        "/api/v1/setup/initialize",
        json={
            "username": "admin",
            "password": "Strong-Test-Password-123",
            "display_name": "Admin",
            "site_name": "Portfolio",
            "person_name": "Tester",
        },
    )
    assert initialized.status_code == 200
    public_site = client.get("/api/v1/public/site").json()["data"]
    assert public_site["settings"]["site_name"] == "Portfolio"
    assert len(public_site["settings"]["navigation_items"]) == 5
    assert client.get("/api/v1/public/projects").json()["data"]["pagination"]["total"] == 0
    assert client.get("/api/v1/public/resumes").json()["data"]["items"] == []
    assert client.get("/api/v1/public/certificates").json()["data"]["items"] == []
    closed = client.post(
        "/api/v1/setup/initialize",
        json={
            "username": "other",
            "password": "Another-Strong-Password",
            "display_name": "Other",
            "site_name": "Portfolio",
            "person_name": "Other",
        },
    )
    assert closed.status_code == 409
    csrf = client.cookies.get("portfolio_csrf")
    client.post("/api/v1/admin/auth/logout", headers={"X-CSRF-Token": csrf})
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "Strong-Test-Password-123"},
    )
    assert login.status_code == 200
    assert client.cookies.get("portfolio_session")


def test_project_crud_and_draft_is_not_public(
    admin_client: TestClient, csrf_headers: dict[str, str], project_payload: dict
) -> None:
    created = admin_client.post(
        "/api/v1/admin/projects", json=project_payload, headers=csrf_headers
    )
    assert created.status_code == 200, created.text
    project = created.json()["data"]
    assert len(project["uuid"]) == 36
    assert (
        admin_client.get(f"/api/v1/public/projects/{project['uuid']}").status_code
        == 404
    )
    project_payload["status"] = "published"
    project_payload["title"] = "Published Project"
    updated = admin_client.put(
        f"/api/v1/admin/projects/{project['uuid']}",
        json=project_payload,
        headers=csrf_headers,
    )
    assert updated.status_code == 200, updated.text
    public = admin_client.get(f"/api/v1/public/projects/{project['uuid']}")
    assert public.status_code == 200
    assert public.json()["data"]["title"] == "Published Project"
    deleted = admin_client.delete(
        f"/api/v1/admin/projects/{project['uuid']}", headers=csrf_headers
    )
    assert deleted.status_code == 200
    assert (
        admin_client.get(f"/api/v1/public/projects/{project['uuid']}").status_code
        == 404
    )


def test_csrf_required(admin_client: TestClient, project_payload: dict) -> None:
    response = admin_client.post("/api/v1/admin/projects", json=project_payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"


def test_contact_methods_keep_order_and_phone_type(
    admin_client: TestClient, csrf_headers: dict[str, str]
) -> None:
    contacts = [
        {
            "type": "phone",
            "label": "联系电话",
            "value": "+86 132 0000 0000",
            "url": "tel:+8613200000000",
            "description": "工作日可联系",
            "icon_asset_uuid": "",
            "icon_name": "Phone",
            "icon_svg": "",
        },
        {
            "type": "email",
            "label": "工作邮箱",
            "value": "hello@example.com",
            "url": "mailto:hello@example.com",
            "description": "",
            "icon_asset_uuid": "",
            "icon_name": "Mail",
            "icon_svg": "",
        },
    ]
    updated = admin_client.put(
        "/api/v1/admin/settings",
        json={"contact_methods": contacts},
        headers=csrf_headers,
    )
    assert updated.status_code == 200, updated.text
    public = admin_client.get("/api/v1/public/site")
    assert public.status_code == 200
    saved = public.json()["data"]["settings"]["contact_methods"]
    assert [item["type"] for item in saved] == ["phone", "email"]
    assert saved[0]["url"] == "tel:+8613200000000"


def test_project_album_sections_and_dynamic_cover(
    admin_client: TestClient, csrf_headers: dict[str, str], project_payload: dict
) -> None:
    uploaded = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        data={"is_public": "true", "logical_group": "project-content"},
        files={"file": ("case-image.png", image_bytes(), "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    asset_uuid = uploaded.json()["data"]["uuid"]
    section_upload = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        data={"is_public": "true", "logical_group": "project-content"},
        files={"file": ("section-only.png", image_bytes("#884433"), "image/png")},
    )
    assert section_upload.status_code == 200, section_upload.text
    section_asset_uuid = section_upload.json()["data"]["uuid"]
    album_uuid = "e15180ea-e661-48a6-a321-f50953d576f8"
    section_key = "71cd70e3-a290-41ab-9ae0-e2f4ac0dfbca"
    project_payload.update(
        {
            "status": "published",
            "albums": [
                {
                    "uuid": album_uuid,
                    "title": "系统截图",
                    "description": "关键界面",
                    "display_mode": "grid",
                    "asset_uuids": [asset_uuid, asset_uuid],
                    "sort_order": 0,
                }
            ],
            "sections": [
                {
                    "client_key": section_key,
                    "title": "界面与流程",
                    "body": "图片来自项目相册。",
                    "section_type": "markdown",
                    "display_mode": "album",
                    "asset_uuids": [],
                    "album_uuid": album_uuid,
                    "heading_level": 3,
                    "is_visible": True,
                    "sort_order": 0,
                },
                {
                    "client_key": "8d81d125-b2df-454d-976a-a5e677be4460",
                    "title": "Section-only attachment",
                    "body": "This file belongs only to this custom section.",
                    "section_type": "markdown",
                    "display_mode": "single",
                    "asset_uuids": [section_asset_uuid],
                    "album_uuid": None,
                    "heading_level": 2,
                    "is_visible": True,
                    "sort_order": 1,
                }
            ],
            "content_layout": [
                {"key": "overview", "kind": "builtin", "visible": False, "sort_order": 1},
                {
                    "key": f"custom:{section_key}",
                    "kind": "custom",
                    "visible": True,
                    "sort_order": 0,
                },
            ],
        }
    )
    created = admin_client.post(
        "/api/v1/admin/projects", json=project_payload, headers=csrf_headers
    )
    assert created.status_code == 200, created.text
    project = created.json()["data"]
    assert project["cover_asset"] is None
    assert {asset["uuid"] for asset in project["auto_cover_assets"]} == {
        asset_uuid,
        section_asset_uuid,
    }
    assert project["albums"][0]["assets"][0]["asset"]["uuid"] == asset_uuid
    assert project["sections"][0]["album"]["uuid"] == album_uuid
    assert project["sections"][1]["media_assets"][0]["uuid"] == section_asset_uuid
    assert [relation["asset"]["uuid"] for relation in project["assets"]] == [asset_uuid]
    assert project["sections"][0]["client_key"] == section_key
    assert project["sections"][0]["heading_level"] == 3
    assert project["content_layout"][0]["key"] == "overview"
    assert project["content_layout"][0]["visible"] is False

    repeated = admin_client.put(
        f"/api/v1/admin/projects/{project['uuid']}",
        json=project_payload,
        headers=csrf_headers,
    )
    assert repeated.status_code == 200, repeated.text
    assert len(repeated.json()["data"]["albums"][0]["assets"]) == 1

    project_payload["albums"] = []
    project_payload["sections"] = []
    updated = admin_client.put(
        f"/api/v1/admin/projects/{project['uuid']}",
        json=project_payload,
        headers=csrf_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["auto_cover_assets"] == []
