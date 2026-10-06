from copy import deepcopy
import json

import pytest

from app.core.database import get_session_factory
from app.models import SiteSetting
from deploy.configure_contacts import configure_contacts, read_profile


@pytest.fixture()
def contact_profile(tmp_path):
    profile = {
        "email": "hello@example.com", "phone": "13200000000",
        "github": "https://github.com/example/",
        "address": {"zh-CN": "云南省昆明市", "en": "Kunming, Yunnan, China"},
    }
    path = tmp_path / "contacts.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    return path


def test_contact_deployment_is_bilingual_repeatable_and_preserves_content(admin_client, csrf_headers, contact_profile):
    original = admin_client.get("/api/v1/admin/settings").json()["data"]
    wechat = {"type": "message", "label": "微信", "value": "keep-me", "url": ""}
    original.update({
        "bio": "保留介绍", "location": "原有地区",
        "contact_methods": [
            {"type": "email", "value": "old@example.com", "icon_asset_uuid": "old-icon"},
            {"type": "phone", "value": ""}, {"type": "other", "value": ""}, wechat,
        ],
        "translations": {"en": {"bio": "Keep the biography", "contact_methods": [
            {"type": "email", "value": "old@example.com"}, {**wechat, "label": "WeChat"},
        ]}, "fr": {"bio": "A conserver"}},
    })
    assert admin_client.put("/api/v1/admin/settings", json=original, headers=csrf_headers).status_code == 200
    profile = read_profile(contact_profile)
    assert configure_contacts(profile) is True
    assert configure_contacts(profile) is False

    saved = admin_client.get("/api/v1/admin/settings").json()["data"]
    assert saved["bio"] == "保留介绍" and saved["location"] == "原有地区"
    assert saved["translations"]["en"]["bio"] == "Keep the biography"
    assert saved["translations"]["fr"] == original["translations"]["fr"]
    assert saved["email"] == profile["email"] and saved["github_url"] == profile["github"]
    for locale, labels in (("zh-CN", ["邮箱", "电话", "地址", "GitHub"]), ("en", ["Email", "Phone", "Address", "GitHub"])):
        contacts = admin_client.get(f"/api/v1/public/site?locale={locale}").json()["data"]["settings"]["contact_methods"]
        assert len(contacts) == 5
        assert [item["label"] for item in contacts[:4]] == labels
        assert [item["icon_name"] for item in contacts[:4]] == ["Message", "Phone", "Location", "Github"]
        assert all(not item["icon_asset_uuid"] and not item["icon_svg"] for item in contacts[:4])
        assert [item["url"] for item in contacts[:4]] == ["mailto:hello@example.com", "tel:13200000000", "", "https://github.com/example/"]
        assert contacts[2]["value"] == profile["address"][locale]
        assert contacts[4]["value"] == "keep-me"


def test_invalid_existing_translation_does_not_partially_write(admin_client, contact_profile):
    with get_session_factory()() as db, db.begin():
        settings = db.get(SiteSetting, 1)
        data = deepcopy(settings.data)
        data["translations"] = {"en": []}
        settings.data = data
    with pytest.raises(ValueError, match="英文设置格式"):
        configure_contacts(read_profile(contact_profile))
    assert admin_client.get("/api/v1/admin/settings").json()["data"] == data


@pytest.mark.parametrize("field,value", [
    ("email", "not-an-email"), ("phone", "-----"),
    ("github", "https://github.com.attacker.invalid/example"),
    ("github", "javascript:alert(1)"), ("address", {"zh-CN": "昆明"}),
])
def test_invalid_contact_profile_is_rejected_before_deployment(contact_profile, field, value):
    data = json.loads(contact_profile.read_text())
    data[field] = value
    contact_profile.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        read_profile(contact_profile)
