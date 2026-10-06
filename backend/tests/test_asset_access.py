from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from fastapi.testclient import TestClient

from app.security.asset_access import limiter, tickets

TEXT = "# 标题\n\n仅可查看的说明文档。\n".encode()


@pytest.fixture(autouse=True)
def reset_limits():
    limiter.reset()
    tickets.reset()
    yield
    limiter.reset()
    tickets.reset()


def upload(admin_client: TestClient, csrf_headers: dict[str, str], name="note.md", body=TEXT, mime="text/markdown") -> dict:
    response = admin_client.post(
        "/api/v1/admin/assets/upload",
        headers=csrf_headers,
        data={"is_public": "true"},
        files={"file": (name, body, mime)},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def set_mode(admin_client, csrf_headers, asset, mode):
    response = admin_client.put(
        f"/api/v1/admin/assets/{asset['uuid']}",
        headers=csrf_headers,
        json={"display_name": asset["display_name"], "is_public": True, "access_mode": mode},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_view_only_asset_is_encrypted_and_not_downloadable(admin_client, csrf_headers):
    asset = upload(admin_client, csrf_headers)
    assert asset["access_mode"] == "download" and asset["previewable"] and not asset["protected"]
    asset = set_mode(admin_client, csrf_headers, asset, "view")
    assert asset["protected"] is True

    visitor = TestClient(admin_client.app)
    meta = visitor.get(f"/api/v1/public/assets/{asset['uuid']}").json()["data"]
    assert meta["protected"] is True
    assert visitor.get(asset["content_url"]).json()["error"]["code"] == "ASSET_VIEW_ONLY"
    assert visitor.get(f"/api/v1/public/assets/{asset['uuid']}/preview").status_code == 403
    blocked = visitor.post(f"/api/v1/public/assets/{asset['uuid']}/ticket", json={"purpose": "download"})
    assert blocked.status_code == 403
    direct = visitor.get(asset["download_url"], follow_redirects=False)
    assert direct.status_code == 303 and direct.headers["location"].endswith(asset["uuid"])

    ticket = visitor.post(f"/api/v1/public/assets/{asset['uuid']}/ticket", json={"purpose": "view"}).json()["data"]
    assert ticket["encrypted"] is True
    response = visitor.get(ticket["url"])
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.content != TEXT and len(response.content) == len(TEXT)
    decryptor = Cipher(
        algorithms.AES(base64.b64decode(ticket["key"])), modes.CTR(base64.b64decode(ticket["counter"]))
    ).decryptor()
    assert decryptor.update(response.content) + decryptor.finalize() == TEXT

    # 票据与 UA 绑定、次数有限、篡改无效
    other_browser = TestClient(admin_client.app, headers={"user-agent": "another-browser"})
    assert other_browser.get(ticket["url"]).status_code == 403
    assert visitor.get(ticket["url"][:-2] + "xx").status_code == 403
    visitor.get(ticket["url"]); visitor.get(ticket["url"])
    assert visitor.get(ticket["url"]).status_code == 403


def test_downloads_need_signed_ticket_and_are_rate_limited(admin_client, csrf_headers, monkeypatch):
    from app.core.config import get_settings

    asset = upload(admin_client, csrf_headers, "readme.txt", b"hello", "text/plain")
    visitor = TestClient(admin_client.app)
    assert visitor.get(asset["content_url"]).status_code == 200
    ticket = visitor.post(f"/api/v1/public/assets/{asset['uuid']}/ticket", json={"purpose": "download"}).json()["data"]
    response = visitor.get(ticket["url"])
    assert response.status_code == 200 and response.content == b"hello"
    assert response.headers["content-disposition"].startswith("attachment")
    assert visitor.get(f"/api/v1/public/assets/{asset['uuid']}").json()["data"]["download_count"] == 1

    monkeypatch.setattr(get_settings(), "ASSET_DOWNLOADS_PER_HOUR", 2)
    limiter.reset()
    codes = [visitor.post(f"/api/v1/public/assets/{asset['uuid']}/ticket", json={"purpose": "download"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    # 管理员不受限，原下载接口仍可直接使用
    assert admin_client.get(asset["download_url"]).status_code == 200


def test_hotlinking_is_refused(admin_client, csrf_headers):
    asset = upload(admin_client, csrf_headers, "plain.txt", b"x", "text/plain")
    visitor = TestClient(admin_client.app)
    response = visitor.get(asset["content_url"], headers={"sec-fetch-site": "cross-site", "sec-fetch-dest": "image"})
    assert response.status_code == 403
    assert visitor.get(asset["content_url"], headers={"sec-fetch-site": "same-origin", "sec-fetch-dest": "image"}).status_code == 200


def test_view_mode_ignored_for_non_previewable(admin_client, csrf_headers):
    asset = upload(admin_client, csrf_headers, "data.json", b"{}", "application/json")
    asset = set_mode(admin_client, csrf_headers, asset, "view")
    assert asset["access_mode"] == "view" and asset["protected"] is False
