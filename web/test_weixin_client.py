import os
import time
import json
import tempfile
import pytest
from web.weixin_client import TokenCache, WeixinClient


def test_token_cache_set_and_get():
    c = TokenCache(cache_file=None, grace_period=60)
    c.set('tok123', 300)
    assert c.get() == 'tok123'


def test_token_cache_expires_with_grace_period():
    c = TokenCache(cache_file=None, grace_period=60)
    c.set('tok123', 30)
    # 30s expiry - 60s grace = already stale
    assert c.get() is None


def test_token_cache_persistence():
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        path = f.name
    try:
        c = TokenCache(cache_file=path, grace_period=60)
        c.set('abc', 300)
        c2 = TokenCache(cache_file=path, grace_period=60)
        assert c2.get() == 'abc'
    finally:
        os.remove(path)


def test_get_openid_extracts_value(monkeypatch):
    def mock_fetch(url, method='GET', json_payload=None, timeout=10):
        return {'openid': 'oid123', 'session_key': 'sk'}
    client = WeixinClient(app_id='A', secret='S')
    client._fetch_json = mock_fetch
    assert client.get_openid('CODE') == 'oid123'


def test_get_openid_returns_none_on_failure(monkeypatch):
    def mock_fetch(url, method='GET', json_payload=None, timeout=10):
        return None
    client = WeixinClient(app_id='A', secret='S')
    client._fetch_json = mock_fetch
    assert client.get_openid('CODE') is None


def test_send_subscribe_message_returns_result(monkeypatch):
    def mock_fetch(url, method='GET', json_payload=None, timeout=10):
        return {'errcode': 0, 'errmsg': 'ok'}
    client = WeixinClient(app_id='A', secret='S')
    client._fetch_json = mock_fetch
    # pre-warm token so no extra request
    client.token_cache.set('t', 300)
    result = client.send_subscribe_message('oid', 'hello')
    assert result['errcode'] == 0


def test_send_subscribe_message_no_token():
    client = WeixinClient(app_id='A', secret='S')
    # no token and fetch_json will return None for token endpoint
    client._fetch_json = lambda url, method='GET', json_payload=None, timeout=10: None
    result = client.send_subscribe_message('oid', 'hello')
    assert result is None
