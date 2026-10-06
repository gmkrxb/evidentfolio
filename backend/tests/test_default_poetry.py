from app.services.poetry import CLOSING, MANIFESTO, with_default_poetry


def test_fills_missing_poetry_in_both_languages():
    data, changed = with_default_poetry({"person_name": "A", "home_copy": {"projects_title": "Work"}})
    assert changed
    assert data["home_copy"]["projects_title"] == "Work"
    assert data["home_copy"]["manifesto"] == MANIFESTO["zh-CN"]
    assert data["translations"]["en"]["home_copy"]["closing"] == CLOSING["en"]


def test_never_overwrites_existing_text():
    data, _ = with_default_poetry({"hero_eyebrow": "我的引题", "home_copy": {"manifesto": "我的诗", "closing": "再见"}, "translations": {"en": {"home_copy": {"manifesto": "Mine", "closing": "Bye"}}}})
    assert data["hero_eyebrow"] == "我的引题"
    assert data["home_copy"]["manifesto"] == "我的诗" and data["home_copy"]["closing"] == "再见"
    assert data["translations"]["en"]["home_copy"]["manifesto"] == "Mine"
    again, changed = with_default_poetry(data)
    assert not changed and again == data


def test_english_primary_site_uses_english_base():
    data, _ = with_default_poetry({"primary_language": "en"})
    assert data["home_copy"]["manifesto"] == MANIFESTO["en"]
    assert "translations" not in data
