import os
import time
import json
import tempfile
import pytest
from web.weibo_client import WeiboCache, parse_page, parse_time


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
