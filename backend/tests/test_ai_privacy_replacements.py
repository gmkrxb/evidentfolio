from __future__ import annotations

import asyncio
import io
import json

import httpx
import pytest
from PIL import Image
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.models import Asset, AnalyticsEvent, VisitorSession, Visitor
from app.services.ai import ThinkingSplitter, parse_json_output, validate_translation, AIServiceError
from app.security.privacy import reveal_ip


def png(color):
    output = io.BytesIO()
    Image.new("RGB", (50, 40), color).save(output, format="PNG")
    return output.getvalue()


def test_thinking_split_across_every_character():
    splitter = ThinkingSplitter()
    events = []
    for char in '<think>检查 {"假结果":1}</think>```json\n{"title":"正文"}\n```':
        events.extend(splitter.feed(char))
    events.extend(splitter.feed("", final=True))
    assert "假结果" in "".join(e["content"] for e in events if e["type"] == "reasoning")
    body = "".join(e["content"] for e in events if e["type"] == "content")
    assert parse_json_output(body) == {"title": "正文"}
    assert parse_json_output('<analysis>思考</analysis>{"body":"完成"}') == {"body": "完成"}


def test_translation_preserves_identifiers_and_rejects_partial_result():
    original = {"title": "标题", "sections": [{"client_key": "abc", "body": "正文"}], "url": "https://example.com"}
    result = validate_translation(original, {"title": "Title", "sections": [{"client_key": "bad", "body": "Body"}], "url": "bad"})
    assert result["sections"][0]["client_key"] == "abc"
    assert result["url"] == original["url"]
    with pytest.raises(AIServiceError):
        validate_translation(original, {"title": "Title"})
    with pytest.raises(AIServiceError):
        parse_json_output('{"title": "truncated')


def test_provider_reasoning_usage_and_http_errors(monkeypatch):
    from app.services import ai
    original_client = httpx.AsyncClient
    packets = [{"choices": []}, {"choices": [{"delta": {"reasoning_content": "考虑措辞"}}]}]
    for value in ['<thi', 'nk>检查结构</th', 'ink>{"title":', '"Hello"}']:
        packets.append({"choices": [{"delta": {"content": value}}]})
    body = "".join("data: " + json.dumps(item) + "\n\n" for item in packets) + "data: [DONE]\n\n"
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body)), **kwargs))
    async def consume():
        return [event async for event in ai.stream_chat("https://example.com", "test", "model", "system", "user")]
    events = asyncio.run(consume())
    assert json.loads("".join(e["content"] for e in events if e["type"] == "content")) == {"title": "Hello"}
    assert "考虑措辞检查结构" == "".join(e["content"] for e in events if e["type"] == "reasoning")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(lambda request: httpx.Response(401, text="unauthorized")), **kwargs))
    with pytest.raises(AIServiceError, match="401"):
        asyncio.run(consume())


def test_translate_endpoint_body_only(admin_client, csrf_headers, monkeypatch):
    from app.api.routes import ai
    from types import SimpleNamespace
    monkeypatch.setattr(ai, "setting_or_error", lambda db: (SimpleNamespace(base_url="x", model="x"), "key"))
    async def stream(*args):
        yield {"type": "reasoning", "content": '{"title":"不应采用"}'}
        yield {"type": "content", "content": '{"content":{"title":"Translated"}}'}
    monkeypatch.setattr(ai, "stream_chat", stream)
    response = admin_client.post('/api/v1/admin/ai/translate/stream', headers=csrf_headers, json={"source_locale":"zh-CN","target_locale":"en","entity_type":"project","content":{"title":"原文"}})
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert next(e for e in events if e['type']=='result')['data'] == {'title':'Translated'}
    assert events[-1]['type'] == 'done'


def test_replace_preserves_references_and_private_cache(admin_client, csrf_headers, project_payload):
    first = admin_client.post('/api/v1/admin/assets/upload', headers=csrf_headers, data={'is_public':'false'}, files={'file':('one.png',png('navy'),'image/png')}).json()['data']
    project_payload['cover_asset_uuid'] = first['uuid']
    project = admin_client.post('/api/v1/admin/projects', headers=csrf_headers, json=project_payload).json()['data']
    result = admin_client.post(f"/api/v1/admin/assets/{first['uuid']}/replace", headers=csrf_headers, data={'expected_sha256':first['sha256']},files={'file':('two.png',png('red'),'image/png')})
    assert result.status_code == 200, result.text
    second = result.json()['data']
    assert second['uuid'] == first['uuid'] and second['version'] == 2
    assert second['display_name'] == first['display_name']
    assert second['is_public'] is False
    assert second['thumbnail_url'] != first['thumbnail_url']
    assert admin_client.get(first['content_url']).content == png('red')
    assert admin_client.get(f"/api/v1/admin/projects/{project['uuid']}").json()['data']['cover_asset']['sha256'] == second['sha256']
    thumbnail = admin_client.get(second['thumbnail_url'])
    assert thumbnail.headers['cache-control'] == 'private, no-store'
    stale = admin_client.post(f"/api/v1/admin/assets/{first['uuid']}/replace", headers=csrf_headers, data={'expected_sha256':first['sha256']},files={'file':('three.png',png('green'),'image/png')})
    assert stale.status_code == 409
    failed = admin_client.post(f"/api/v1/admin/assets/{first['uuid']}/replace", headers=csrf_headers, data={'expected_sha256':second['sha256']},files={'file':('wrong.txt',b'wrong','text/plain')})
    assert failed.status_code == 422
    assert admin_client.get(first['content_url']).content == png('red')
    admin_client.cookies.clear()
    assert admin_client.get(second['thumbnail_url']).status_code == 404
    assert admin_client.post(f"/api/v1/admin/assets/{first['uuid']}/replace", data={'expected_sha256':second['sha256']}, files={'file':('test.png',png('green'),'image/png')}).status_code == 401


def test_ranges_and_pagination(admin_client, csrf_headers):
    data = b'0123456789' * 10
    asset = admin_client.post('/api/v1/admin/assets/upload', headers=csrf_headers, files={'file':('range.txt',data,'text/plain')}).json()['data']
    for value, expected in [('bytes=-10',data[-10:]), ('bytes=90-999',data[90:]), ('bytes=2-5',data[2:6]), ('bytes=-200',data)]:
        response = admin_client.get(asset['content_url'],headers={'Range':value})
        assert response.status_code == 206
        assert response.content == expected
    assert admin_client.get(asset['content_url'],headers={'Range':'bytes=-0'}).status_code == 416
    for url in ['/api/v1/public/projects?page=0','/api/v1/public/projects?page_size=0','/api/v1/admin/projects?page_size=101']:
        assert admin_client.get(url).status_code == 422


def test_library_replacement_is_independent_and_preserves_references(admin_client, csrf_headers, project_payload):
    def upload(name, color):
        return admin_client.post('/api/v1/admin/assets/upload', headers=csrf_headers, data={'is_public': 'false'}, files={'file': (name, png(color), 'image/png')}).json()['data']
    target, source = upload('original.png', 'navy'), upload('version-two.png', 'red')
    project_payload['cover_asset_uuid'] = target['uuid']
    project = admin_client.post('/api/v1/admin/projects', headers=csrf_headers, json=project_payload).json()['data']
    url = f"/api/v1/admin/assets/{target['uuid']}/replace-from-library"
    payload = {'source_uuid': source['uuid'], 'expected_sha256': target['sha256'], 'source_sha256': source['sha256']}
    assert admin_client.post(url, headers=csrf_headers, json={**payload, 'source_uuid': target['uuid']}).status_code == 422
    assert admin_client.post(url, headers=csrf_headers, json={**payload, 'source_sha256': '0' * 64}).status_code == 409
    response = admin_client.post(url, headers=csrf_headers, json=payload)
    assert response.status_code == 200, response.text
    updated = response.json()['data']
    assert updated['uuid'] == target['uuid'] and updated['version'] == 2
    assert updated['display_name'] == target['display_name'] and updated['is_public'] is False
    assert admin_client.get(source['content_url']).content == png('red')
    assert admin_client.get(target['content_url']).content == png('red')
    assert admin_client.get(f"/api/v1/admin/projects/{project['uuid']}").json()['data']['cover_asset']['sha256'] == source['sha256']
    assert admin_client.post(url, headers=csrf_headers, json=payload).status_code == 409
    assert admin_client.delete(f"/api/v1/admin/assets/{source['uuid']}", headers=csrf_headers).status_code == 200
    assert admin_client.get(target['content_url']).content == png('red')
    admin_client.cookies.clear()
    assert admin_client.post(url, json=payload).status_code == 401


def test_translation_cannot_change_layout_or_asset_selection():
    source = {'title': '标题', 'sections': [{'body': '正文', 'style': {'color': '#123456'}, 'class': 'wide', 'display_mode': 'gallery', 'content_layout': 'split', 'asset_uuids': ['original'], 'sort_order': 3, 'is_visible': True}]}
    translated = {'title': 'Title', 'sections': [{'body': 'Body', 'style': {}, 'class': 'narrow', 'display_mode': 'text', 'content_layout': 'full', 'asset_uuids': ['wrong'], 'sort_order': 0, 'is_visible': False}]}
    result = validate_translation(source, translated)
    assert result == {**source, 'title': 'Title', 'sections': [{**source['sections'][0], 'body': 'Body'}]}


def test_consent_ip_revocation_and_accurate_trend(admin_client, monkeypatch):
    monkeypatch.setattr(get_settings(), 'RAW_IP_STORAGE_ENABLED', True)
    events = {'events':[{'event_type':'page_view'}, {'event_type':'project_dwell','event_data':{'seconds':'nonsense'}}]}
    blocked = admin_client.post('/api/v1/analytics/events',json=events)
    assert blocked.json()['data']['accepted'] == 0
    assert 'portfolio_visitor' not in admin_client.cookies
    admin_client.put('/api/v1/privacy/consent',json={'analytics':True,'raw_ip':True})
    result = admin_client.post('/api/v1/analytics/events',headers={'X-Forwarded-For':'1.2.3.4, 8.8.8.8'},json=events)
    assert result.json()['data']['accepted'] == 2
    with get_session_factory()() as db:
        session = db.scalar(select(VisitorSession))
        assert reveal_ip(session.encrypted_ip) == '8.8.8.8'
        assert '8.8.8.8' not in session.encrypted_ip
    overview = admin_client.get('/api/v1/admin/analytics/overview').json()['data']
    assert len(overview['trend']) == 30
    assert sum(item['views'] for item in overview['trend']) == overview['total_views'] == 1
    admin_client.put('/api/v1/privacy/consent',json={'analytics':False,'raw_ip':False})
    assert 'portfolio_visitor' not in admin_client.cookies
    assert admin_client.post('/api/v1/analytics/events',json=events).json()['data']['accepted'] == 0
    with get_session_factory()() as db:
        assert db.scalar(select(VisitorSession)).encrypted_ip is None
        assert db.scalar(select(Visitor)).encrypted_ip is None
        assert db.scalar(select(func.count(AnalyticsEvent.id))) == 2


def test_partial_fields_nested_and_escaped():
    from app.services.translation import partial_fields
    source = {'title': '标题', 'sections': [{'title': '章节', 'body': '内容'}]}
    text = '{"title":"A \\"quote\\"","sections":[{"title":"Section","body":"Still streaming'
    fields = partial_fields(text, source)
    assert [(field['path'], field['done']) for field in fields] == [('title', True), ('sections.0.title', True), ('sections.0.body', False)]
    assert fields[0]['text'] == 'A "quote"'
    assert fields[-1]['text'] == 'Still streaming'


def mock_translation(monkeypatch, fail_first=False):
    from app.api.routes import ai
    from types import SimpleNamespace
    monkeypatch.setattr(ai, 'setting_or_error', lambda db: (SimpleNamespace(base_url='x', model='x'), 'key'))
    count = 0
    def translate(value):
        if isinstance(value, dict):
            return {key: translate(item) for key, item in value.items()}
        if isinstance(value, list):
            return [translate(item) for item in value]
        return 'Translated ' + value if isinstance(value, str) and value else value
    async def stream(base_url, key, model, system, user):
        nonlocal count
        count += 1
        yield {'type': 'reasoning', 'content': '独立思考'}
        content = 'invalid JSON' if fail_first and count == 1 else json.dumps(translate(json.loads(user)['content']))
        for index in range(0, len(content), 7):
            yield {'type': 'content', 'content': content[index:index + 7]}
    monkeypatch.setattr(ai, 'stream_chat', stream)


def stream_events(response):
    assert response.status_code == 200, response.text
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]


def test_batch_saves_all_modules_and_preserves_existing(admin_client, csrf_headers, project_payload, monkeypatch):
    from app.models import Project
    mock_translation(monkeypatch)
    project_payload['translations'] = {'en': {'title': 'Existing title'}}
    project_payload['sections'] = [{'title': '章节', 'body': '正文', 'section_type': 'text', 'sort_order': 0}]
    result = admin_client.post('/api/v1/admin/projects', headers=csrf_headers, json=project_payload)
    assert result.status_code == 200, result.text
    plan = admin_client.post('/api/v1/admin/ai/translate/plan', headers=csrf_headers, json={}).json()['data']
    assert {'网站文案', '项目', '项目章节'} <= {item['module'] for item in plan['items']}
    events = stream_events(admin_client.post('/api/v1/admin/ai/translate/batch/stream', headers=csrf_headers, json={}))
    assert events[-1] == {'type': 'done', 'saved': len(plan['items']), 'failed': 0}
    assert any(item['type'] == 'fields' and item['completed'] > 0 for item in events)
    with get_session_factory()() as db:
        project = db.scalar(select(Project))
        assert project.status == 'draft'
        assert project.translations['en']['title'] == 'Existing title'
        assert project.translations['en']['summary'].startswith('Translated ')
        assert project.sections[0].translations['en']['body'] == 'Translated 正文'
    assert admin_client.post('/api/v1/admin/ai/translate/plan', headers=csrf_headers, json={}).json()['data']['items'] == []


def test_batch_rejects_concurrent_edits(admin_client):
    from app.models import SiteSetting
    from app.services.translation import build_plan, apply_translation
    with get_session_factory()() as db:
        task = build_plan(db, 'zh-CN', False)[0]
        item = db.get(SiteSetting, 1)
        item.data = {**item.data, 'headline': '编辑中新增的内容'}
        db.commit()
        with pytest.raises(AIServiceError, match='其他操作修改'):
            apply_translation(db, task, task['content'], 'zh-CN')


def test_batch_failure_continues_and_retry_scope(admin_client, csrf_headers, project_payload, monkeypatch):
    mock_translation(monkeypatch, fail_first=True)
    admin_client.post('/api/v1/admin/projects', headers=csrf_headers, json=project_payload)
    events = stream_events(admin_client.post('/api/v1/admin/ai/translate/batch/stream', headers=csrf_headers, json={}))
    assert events[-1] == {'type': 'done', 'saved': 1, 'failed': 1}
    failed_id = next(event['id'] for event in events if event['type'] == 'task_error')
    retry = stream_events(admin_client.post('/api/v1/admin/ai/translate/batch/stream', headers=csrf_headers, json={'only': [failed_id]}))
    assert retry[-1] == {'type': 'done', 'saved': 1, 'failed': 0}


def test_context_window_preserves_current_text_and_rolls_references():
    from app.services.translation import translation_request, roll_references
    from app.services.ai import TRANSLATION_PROMPT
    original = {'title': '证据驱动', 'body': '正文不能截断' * 20}
    references = [{'module': 'site', 'field': 'title', 'source': f'旧文 {index}', 'target': 'Old ' + 'word ' * 70} for index in range(50)]
    recent = [{'module': 'project', 'field': 'title', 'source': '最新术语', 'target': 'Evidence-driven'}]
    user, usage = translation_request(original, 'zh-CN', 'project', 4000, references, recent, {'title': 'Evidence-led'})
    packet = json.loads(user)
    assert packet['content'] == original
    assert packet['reference_translations'][0]['target'] == 'Evidence-led'
    assert packet['reference_translations'][1]['target'] == 'Evidence-driven'
    assert len(user) + len(TRANSLATION_PROMPT) == usage['chars'] <= 4000
    assert usage['references'] < len(references)
    rolled = roll_references(references, recent, 600)
    assert rolled[-1] == recent[0]
    assert sum(len(json.dumps(item, ensure_ascii=False)) for item in rolled) <= 600
    with pytest.raises(AIServiceError, match='正文需'):
        translation_request({'body': '长' * 5000}, 'zh-CN', 'project', 4000, [])


def test_context_uses_saved_and_newly_completed_translations(admin_client, csrf_headers, project_payload, monkeypatch):
    from app.api.routes import ai
    from types import SimpleNamespace
    monkeypatch.setattr(ai, 'setting_or_error', lambda db: (SimpleNamespace(base_url='x', model='x', max_context_chars=4000), 'key'))
    requests = []
    async def stream(base_url, key, model, system, user):
        packet = json.loads(user)
        requests.append(packet)
        assert len(system) + len(user) <= 4000
        yield {'type': 'content', 'content': json.dumps(packet['content'])}
    monkeypatch.setattr(ai, 'stream_chat', stream)
    project_payload['translations'] = {'en': {'title': 'Established project name'}}
    admin_client.post('/api/v1/admin/projects', headers=csrf_headers, json=project_payload)
    response = admin_client.post('/api/v1/admin/ai/translate/batch/stream', headers=csrf_headers, json={})
    assert stream_events(response)[-1]['failed'] == 0
    assert any(item['target'] == 'Established project name' for item in requests[0]['reference_translations'])
    assert any(item['module'] == 'site' for item in requests[1]['reference_translations'])
    response = admin_client.post('/api/v1/admin/ai/translate/stream', headers=csrf_headers, json={
        'source_locale': 'zh-CN', 'target_locale': 'en', 'entity_type': 'project',
        'content': {'title': '未保存的草稿'}, 'existing_translation': {'title': 'Draft terminology'}})
    assert stream_events(response)[-1]['type'] == 'done'
    assert requests[-1]['reference_translations'][0]['target'] == 'Draft terminology'
    assert admin_client.post('/api/v1/admin/ai/translate/plan', headers=csrf_headers, json={'max_context_chars': 10}).status_code == 422


def test_translation_empty_source_preserves_existing_content(admin_client, csrf_headers, monkeypatch):
    from app.api.routes import ai
    from types import SimpleNamespace
    monkeypatch.setattr(ai, 'setting_or_error', lambda db: (SimpleNamespace(base_url='x', model='x', max_context_chars=4000), 'key'))
    async def stream(*args):
        yield {'type': 'content', 'content': json.dumps({'title': '新标题', 'body': '', 'outcomes': [], 'sections': [{'client_key': 'a'}]})}
    monkeypatch.setattr(ai, 'stream_chat', stream)
    response = admin_client.post('/api/v1/admin/ai/translate/stream', headers=csrf_headers, json={
        'source_locale': 'en', 'target_locale': 'zh-CN', 'entity_type': 'project',
        'content': {'title': 'New title', 'body': '', 'outcomes': [], 'sections': [{'client_key': 'a'}]},
        'existing_translation': {'title': '旧标题', 'body': '已有中文正文', 'outcomes': ['已有成果'], 'sections': [{'client_key': 'a', 'body': '已有章节'}]}})
    result = next(event['data'] for event in stream_events(response) if event['type'] == 'result')
    assert result == {'title': '新标题', 'body': '已有中文正文', 'outcomes': ['已有成果'], 'sections': [{'client_key': 'a', 'body': '已有章节'}]}
    response = admin_client.post('/api/v1/admin/ai/translate/stream', headers=csrf_headers, json={
        'content': {'title': ' ', 'sections': [{'client_key': 'a'}]}})
    assert response.status_code == 422


@pytest.mark.parametrize('module', ['categories', 'tags'])
def test_taxonomy_update_conflict_preserves_original(admin_client, csrf_headers, module):
    first = admin_client.post(f'/api/v1/admin/{module}', headers=csrf_headers, json={'name': 'First'}).json()['data']
    admin_client.post(f'/api/v1/admin/{module}', headers=csrf_headers, json={'name': 'Second'})
    response = admin_client.put(f'/api/v1/admin/{module}/{first["uuid"]}', headers=csrf_headers, json={'name': 'Second'})
    assert response.status_code == 409
    response = admin_client.put(f'/api/v1/admin/{module}/{first["uuid"]}', headers=csrf_headers, json={'name': '   '})
    assert response.status_code == 422
    items = admin_client.get(f'/api/v1/admin/{module}').json()['data']['items']
    assert next(item['name'] for item in items if item['uuid'] == first['uuid']) == 'First'
    if module == 'categories':
        assert admin_client.post('/api/v1/admin/categories', headers=csrf_headers, json={'name': 'Third', 'sort_order': 'bad'}).status_code == 422
