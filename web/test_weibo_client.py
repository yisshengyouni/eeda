import os
import time
import json
import tempfile
import pytest
from web.weibo_client import WeiboCache, parse_page, parse_time, WeiboClient


def test_cache_set_and_get():
    c = WeiboCache(ttl=60, max_size=10, cache_file=None)
    c.set('a', {'x': 1})
    assert c.get('a') == {'x': 1}


def test_cache_ttl_expiration():
    c = WeiboCache(ttl=0, max_size=10, cache_file=None)
    c.set('a', {'x': 1})
    time.sleep(0.1)
    assert c.get('a') is None


def test_cache_lru_eviction():
    c = WeiboCache(ttl=60, max_size=2, cache_file=None)
    c.set('a', 1)
    c.set('b', 2)
    c.set('c', 3)
    assert c.get('a') is None
    assert c.get('b') == 2
    assert c.get('c') == 3


def test_cache_persistence():
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        path = f.name
    try:
        c = WeiboCache(ttl=60, max_size=10, cache_file=path)
        c.set('k', {'v': 99})
        c.save_on_exit()
        c2 = WeiboCache(ttl=60, max_size=10, cache_file=path)
        assert c2.get('k') == {'v': 99}
    finally:
        os.remove(path)


def test_parse_page_empty():
    assert parse_page(None) == []
    assert parse_page({}) == []
    assert parse_page({'data': {}}) == []


def test_parse_page_with_cards():
    json_data = {
        'data': {
            'cards': [
                {
                    'mblog': {
                        'id': '123',
                        'text': '<p>Hello world</p>',
                        'attitudes_count': 5,
                        'comments_count': 2,
                        'reposts_count': 1,
                        'original_pic': 'http://pic.jpg',
                        'pics': [{'url': 'u1', 'large': {'url': 'lu1'}}],
                        'created_at': '10分钟前'
                    }
                }
            ]
        }
    }
    result = parse_page(json_data)
    assert len(result) == 1
    assert result[0]['id'] == '123'
    assert result[0]['text'] == 'Hello world'
    assert result[0]['attitudes'] == 5
    assert result[0]['pics'][0]['large_url'] == 'lu1'


def test_parse_page_card_group():
    json_data = {
        'data': {
            'cards': [
                {
                    'card_group': [
                        {'mblog': {'id': '456', 'text': 'CG', 'attitudes_count': 0, 'comments_count': 0, 'reposts_count': 0}}
                    ]
                }
            ]
        }
    }
    result = parse_page(json_data)
    assert len(result) == 1
    assert result[0]['id'] == '456'


def test_parse_time_formats():
    now = __import__('datetime').datetime.now()
    res = parse_time('5分钟前')
    assert res is not None
    res = parse_time('2小时前')
    assert res is not None
    res = parse_time('昨天 10:33')
    assert '10:33' in res
    res = parse_time('02-10')
    assert res.endswith('02-10')
    res = parse_time('Mon Feb 10 12:00:00 +0800 2020')
    assert '2020' in res


def test_set_cookie_updates_cookie():
    client = WeiboClient(cache=WeiboCache(cache_file=None), cookie='')
    assert client._cookie == ''
    client.set_cookie('SUB=xxx')
    assert client._cookie == 'SUB=xxx'


# =============================================================================
# Integration tests against real Weibo API
# =============================================================================

@pytest.fixture(scope='module')
def real_client():
    cookie = os.getenv('WEIBO_COOKIE', '')
    return WeiboClient(cache=WeiboCache(cache_file=None), cookie=cookie)


@pytest.mark.integration
def test_get_page_real(real_client):
    data = real_client.get_page(1, '2304137519797263')
    assert data is not None, 'Weibo API returned None (possible 432 auth required)'
    assert isinstance(data, dict)
    assert data.get('ok') in (0, 1)
    assert 'data' in data


@pytest.mark.integration
def test_get_weibo_real(real_client):
    posts = real_client.get_weibo(1, '2304137519797263')
    assert isinstance(posts, list)
    assert len(posts) > 0, 'Weibo API returned empty list (possible 432 auth required)'
    post = posts[0]
    assert 'id' in post
    assert 'text' in post
    assert 'created_at' in post
    assert 'pics' in post


@pytest.mark.integration
def test_get_user_info_real(real_client):
    info = real_client.get_user_info('7519797263')
    assert isinstance(info, dict)
    assert info.get('screen_name'), 'Weibo API returned empty screen_name (possible 432 auth required)'
    assert 'profile_image_url' in info


@pytest.mark.integration
def test_get_detail_and_comments_real(real_client):
    posts = real_client.get_weibo(1, '2304137519797263')
    if not posts:
        pytest.skip('No posts available to test detail/comments (possible 432 auth required)')
    weibo_id = posts[0]['id']

    detail = real_client.get_detail(weibo_id)
    assert isinstance(detail, dict)

    comments = real_client.get_comments(weibo_id)
    assert isinstance(comments, list)
