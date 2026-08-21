from __future__ import annotations

import io
import subprocess
import zipfile

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.file_processing import files as file_processing


def png_bytes(color: str = "navy") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), color).save(buffer, format="PNG")
    return buffer.getvalue()


def pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Portfolio resume resource boundary")
    content = document.tobytes()
    document.close()
    return content


def zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", "Safe attachment")
        archive.writestr("results/metrics.json", '{"f1": 0.9067}')
    return buffer.getvalue()


def test_upload_rename_keeps_uuid_url_and_permissions(
    admin_client: TestClient, csrf_headers: dict[str, str]
) -> None:
    response = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        data={"is_public": "false", "logical_group": "tests"},
        files={"file": ("original.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 200, response.text
    asset = response.json()["data"]
    url = asset["content_url"]
    anonymous = TestClient(admin_client.app)
    assert anonymous.get(url).status_code == 404
    renamed = admin_client.put(
        f"/api/v1/admin/assets/{asset['uuid']}",
        headers=csrf_headers,
        json={
            "display_name": "Renamed image",
            "description": "Safe image",
            "logical_group": "tests",
            "is_public": True,
        },
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["content_url"] == url
    public = anonymous.get(url)
    assert public.status_code == 200
    assert public.headers["content-type"].startswith("image/png")


def test_asset_folders_global_search_and_batch_move(
    admin_client: TestClient, csrf_headers: dict[str, str]
) -> None:
    folder = admin_client.post(
        "/api/v1/admin/asset-folders",
        headers=csrf_headers,
        json={"name": "论文插图", "description": "论文图像", "sort_order": 1},
    )
    assert folder.status_code == 200, folder.text
    folder_uuid = folder.json()["data"]["uuid"]
    child_folder = admin_client.post(
        "/api/v1/admin/asset-folders",
        headers=csrf_headers,
        json={
            "name": "Figures",
            "description": "Nested figures",
            "sort_order": 2,
            "parent_uuid": folder_uuid,
        },
    )
    assert child_folder.status_code == 200, child_folder.text
    assert child_folder.json()["data"]["parent_uuid"] == folder_uuid
    assert len(child_folder.json()["data"]["path"]) == 2
    cycle = admin_client.put(
        f"/api/v1/admin/asset-folders/{folder_uuid}",
        headers=csrf_headers,
        json={
            "name": "璁烘枃鎻掑浘",
            "description": "璁烘枃鍥惧儚",
            "sort_order": 1,
            "parent_uuid": child_folder.json()["data"]["uuid"],
        },
    )
    assert cycle.status_code == 422
    assert cycle.json()["error"]["code"] == "ASSET_FOLDER_CYCLE"
    uploaded = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        data={"is_public": "true", "folder_uuid": folder_uuid},
        files={"file": ("evidence-figure.png", png_bytes(), "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    asset_uuid = uploaded.json()["data"]["uuid"]
    assert uploaded.json()["data"]["folder"]["uuid"] == folder_uuid

    searched = admin_client.get(
        "/api/v1/admin/assets",
        params={"q": "evidence", "folder": "unfiled"},
    )
    assert searched.status_code == 200
    assert [item["uuid"] for item in searched.json()["data"]["items"]] == [asset_uuid]

    moved = admin_client.post(
        "/api/v1/admin/assets/batch-move",
        headers=csrf_headers,
        json={"asset_uuids": [asset_uuid], "folder_uuid": None},
    )
    assert moved.status_code == 200
    assert moved.json()["data"]["moved"] == 1
    public_after = admin_client.get(f"/api/v1/public/assets/{asset_uuid}")
    assert public_after.status_code == 200


def test_file_type_validation_and_batch_upload(
    admin_client: TestClient, csrf_headers: dict[str, str]
) -> None:
    blocked = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        files={"file": ("danger.js", b"alert(1)", "application/javascript")},
    )
    assert blocked.status_code == 422
    batch = admin_client.post(
        "/api/v1/admin/assets/batch-upload",
        headers=csrf_headers,
        data={"is_public": "true"},
        files=[
            ("files", ("one.png", png_bytes("red"), "image/png")),
            ("files", ("two.png", png_bytes("green"), "image/png")),
        ],
    )
    assert batch.status_code == 200, batch.text
    assert all(item["success"] for item in batch.json()["data"]["items"])


def test_thumbnail_uses_nginx_internal_redirect_when_available(
    admin_client: TestClient, csrf_headers: dict[str, str]
) -> None:
    uploaded = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        data={"is_public": "true"},
        files={"file": ("accelerated.png", png_bytes(), "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    asset_uuid = uploaded.json()["data"]["uuid"]
    thumbnail = admin_client.get(
        f"/api/v1/public/assets/{asset_uuid}/thumbnail",
        headers={"X-Accel-Supported": "1"},
    )
    assert thumbnail.status_code == 200
    assert thumbnail.headers["x-accel-redirect"].startswith(
        "/_protected_thumbnails/"
    )
    assert thumbnail.content == b""


def test_pdf_resource_is_not_a_resume_until_registered(
    admin_client: TestClient, csrf_headers: dict[str, str]
) -> None:
    uploaded = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        data={"is_public": "true"},
        files={"file": ("document.pdf", pdf_bytes(), "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assets = admin_client.get("/api/v1/admin/assets")
    assert any(item["uuid"] == uploaded.json()["data"]["uuid"] for item in assets.json()["data"]["items"])
    resumes = admin_client.get("/api/v1/public/resumes")
    assert resumes.status_code == 200
    assert resumes.json()["data"]["items"] == []

    asset_uuid = uploaded.json()["data"]["uuid"]
    registered = admin_client.post(
        "/api/v1/admin/resumes",
        headers=csrf_headers,
        json={
            "name": "Dependency protected resume",
            "language": "zh-CN",
            "resume_type": "technical",
            "asset_uuid": asset_uuid,
            "is_default": True,
            "is_public": True,
            "version": "1.0",
        },
    )
    assert registered.status_code == 200, registered.text
    dependencies = admin_client.get(
        f"/api/v1/admin/assets/{asset_uuid}/dependencies"
    )
    assert dependencies.status_code == 200
    dependency_data = dependencies.json()["data"]
    assert dependency_data["has_dependencies"] is True
    assert dependency_data["resumes"][0]["uuid"] == registered.json()["data"]["uuid"]
    blocked_delete = admin_client.delete(
        f"/api/v1/admin/assets/{asset_uuid}",
        headers=csrf_headers,
    )
    assert blocked_delete.status_code == 409
    assert blocked_delete.json()["error"]["code"] == "ASSET_IN_USE"


def test_pdf_native_worker_crash_does_not_terminate_api(
    admin_client: TestClient,
    csrf_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def crashed_worker(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=-11, stdout="", stderr="")

    monkeypatch.setattr(file_processing.subprocess, "run", crashed_worker)
    uploaded = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        data={"is_public": "true"},
        files={"file": ("crashing-document.pdf", pdf_bytes(), "application/pdf")},
    )
    assert uploaded.status_code == 422, uploaded.text
    assert uploaded.json()["error"]["code"] == "FILE_VALIDATION_FAILED"
    assert admin_client.get("/api/health").status_code == 200


def test_zip_attachment_has_safe_online_manifest(
    admin_client: TestClient, csrf_headers: dict[str, str]
) -> None:
    uploaded = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        data={"is_public": "true"},
        files={"file": ("evidence.zip", zip_bytes(), "application/zip")},
    )
    assert uploaded.status_code == 200, uploaded.text
    asset = uploaded.json()["data"]
    assert asset["category"] == "archives"
    preview = admin_client.get(f"/api/v1/public/assets/{asset['uuid']}/preview")
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"]["kind"] == "archive"
    assert [item["name"] for item in preview.json()["data"]["entries"]] == [
        "README.txt",
        "results/metrics.json",
    ]


def test_analytics_recognizes_repeat_visitor(client: TestClient) -> None:
    payload = {
        "events": [
            {
                "event_type": "project_view",
                "page_type": "project_detail",
                "project_uuid": "00000000-0000-0000-0000-000000000001",
                "event_data": {},
                "language": "zh-CN",
                "timezone": "Asia/Shanghai",
                "screen_size": "1440x900",
            }
        ]
    }
    first = client.post("/api/v1/analytics/events", json=payload)
    assert first.status_code == 200
    assert first.json()["data"]["is_new_visitor"] is True
    second = client.post("/api/v1/analytics/events", json=payload)
    assert second.status_code == 200
    assert second.json()["data"]["is_new_visitor"] is False
    assert second.json()["data"]["visitor_uuid"] == first.json()["data"]["visitor_uuid"]


def test_analytics_project_ranking_contains_project_title(
    admin_client: TestClient,
    csrf_headers: dict[str, str],
    project_payload: dict,
) -> None:
    project_payload["status"] = "published"
    project_payload["title"] = "Readable Analytics Project"
    created = admin_client.post(
        "/api/v1/admin/projects",
        json=project_payload,
        headers=csrf_headers,
    )
    assert created.status_code == 200, created.text
    project_uuid = created.json()["data"]["uuid"]
    event = admin_client.post(
        "/api/v1/analytics/events",
        json={
            "events": [
                {
                    "event_type": "project_view",
                    "page_type": "project_detail",
                    "project_uuid": project_uuid,
                    "event_data": {},
                    "language": "zh-CN",
                    "timezone": "Asia/Shanghai",
                    "screen_size": "390x844",
                }
            ]
        },
    )
    assert event.status_code == 200, event.text
    overview = admin_client.get("/api/v1/admin/analytics/overview")
    assert overview.status_code == 200
    ranking = overview.json()["data"]["project_ranking"]
    assert ranking[0]["project_title"] == "Readable Analytics Project"
