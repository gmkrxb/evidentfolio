from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_CONFIG = Path(__file__).with_name("test_config.py")
os.environ["PORTFOLIO_CONFIG"] = str(TEST_CONFIG)

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    runtime = get_settings().UPLOAD_ROOT.parent
    runtime.mkdir(parents=True, exist_ok=True)
    Base.metadata.drop_all(get_engine())
    Base.metadata.create_all(get_engine())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_client(client: TestClient) -> TestClient:
    response = client.post(
        "/api/v1/setup/initialize",
        json={
            "username": "admin",
            "password": "Strong-Test-Password-123",
            "display_name": "Test Admin",
            "site_name": "Test Portfolio",
            "person_name": "Tester",
        },
    )
    assert response.status_code == 200
    return client


@pytest.fixture()
def csrf_headers(admin_client: TestClient) -> dict[str, str]:
    csrf = admin_client.cookies.get("portfolio_csrf")
    assert csrf
    return {"X-CSRF-Token": csrf}


@pytest.fixture()
def project_payload() -> dict:
    return {
        "title": "Test Project",
        "subtitle": "A working test",
        "summary": "This project verifies real CRUD behavior.",
        "content": "",
        "background": "Background",
        "problem": "Problem",
        "solution": "Solution",
        "architecture": "Input -> Model -> Output",
        "contributions": ["Implementation"],
        "technologies": ["Python"],
        "outcomes": ["Passed"],
        "start_date": "2026",
        "end_date": "2026",
        "role": "Owner",
        "team_size": 1,
        "status": "draft",
        "project_state": "completed",
        "is_featured": False,
        "is_open_source": False,
        "sort_order": 0,
        "category_uuid": None,
        "tag_uuids": [],
        "cover_asset_uuid": None,
        "seo_title": "",
        "seo_description": "",
        "links": [],
        "sections": [],
    }

