# Weixin Module Stability & Caching Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract WeChat API logic into a dedicated client module with thread-safe token caching, retry handling, and graceful error boundaries.

**Architecture:** Create `web/weixin_client.py` containing `TokenCache` (thread-safe TTL disk-backed cache) and `WeixinClient` (session-based requests with retries). Refactor `web/weibo.py` routes to delegate to `WeixinClient`.

**Tech Stack:** Python 3.7+, Flask, requests, urllib3, threading, json

---

### Task 1: Create `web/weixin_client.py` — TokenCache

**Files:**
- Create: `web/weixin_client.py`

- [ ] **Step 1: Implement `TokenCache` class**

```python
import json
import os
import threading
import time
import logging

logger = logging.getLogger(__name__)
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'weixin_token.json')
TOKEN_FILE = os.path.abspath(TOKEN_FILE)
GRACE_PERIOD = 60  # refresh 60s before expiry


class TokenCache:
    def __init__(self, cache_file=TOKEN_FILE, grace_period=GRACE_PERIOD):
        self.cache_file = cache_file
        self.grace_period = grace_period
        self._lock = threading.Lock()
        self._token = ""
        self._expires_at = 0
        self._load()

    def _load(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._token = data.get('token', '')
                self._expires_at = data.get('expires_at', 0)
                logger.info('Loaded token cache from %s', self.cache_file)
            except Exception as e:
                logger.error('Failed to load token cache: %s', e)
                self._token = ""
                self._expires_at = 0

    def _save(self):
        try:
            with self._lock:
                data = {'token': self._token, 'expires_at': self._expires_at}
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            logger.info('Saved token cache to %s', self.cache_file)
        except Exception as e:
            logger.error('Failed to save token cache: %s', e)

    def get(self):
        with self._lock:
            if self._token and time.time() + self._grace_period < self._expires_at:
                return self._token
            return None

    def set(self, token, expires_in):
        with self._lock:
            self._token = token
            self._expires_at = time.time() + int(expires_in)
        self._save()
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile web/weixin_client.py`
Expected: No output (success)

---

### Task 2: Create `web/weixin_client.py` — WeixinClient

**Files:**
- Modify: `web/weixin_client.py`

- [ ] **Step 1: Add imports and `WeixinClient` class**

```python
import os
import requests
import datetime
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

TEMPLATE_ID = "rJPdhomiyqgRfSkkP-VxopjMkVU8ZuLRIS1tpc9Q3SA"


class WeixinClient:
    def __init__(self, app_id=None, secret=None, token_cache=None):
        self.app_id = app_id or os.getenv('appId')
        self.secret = secret or os.getenv('wx_secret')
        self.token_cache = token_cache or TokenCache()
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def _fetch_json(self, url, method='GET', json_payload=None, timeout=10):
        try:
            if method.upper() == 'POST':
                resp = self.session.post(url, json=json_payload, timeout=timeout)
            else:
                resp = self.session.get(url, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            logger.warning('Non-200 status %s for %s', resp.status_code, url)
        except requests.RequestException as e:
            logger.error('Request error for %s: %s', url, e)
        except Exception as e:
            logger.error('Unexpected error for %s: %s', url, e)
        return None

    def get_access_token(self):
        cached = self.token_cache.get()
        if cached:
            return cached
        url = (
            "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential"
            f"&appid={self.app_id}&secret={self.secret}"
        )
        data = self._fetch_json(url)
        if data:
            token = data.get("access_token")
            expires_in = data.get("expires_in")
            if token and expires_in:
                self.token_cache.set(token, expires_in)
                return token
        logger.error('Failed to fetch WeChat access token')
        return ""

    def get_openid(self, code):
        url = (
            "https://api.weixin.qq.com/sns/jscode2session"
            f"?appid={self.app_id}&secret={self.secret}&js_code={code}&grant_type=authorization_code"
        )
        logger.info('Fetching openid with code')
        data = self._fetch_json(url)
        if data:
            openid = data.get('openid')
            if openid:
                return openid
            logger.warning('No openid in response: %s', data)
        return None

    def send_subscribe_message(self, openid, content):
        token = self.get_access_token()
        if not token:
            return None
        url = 'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token=' + token
        now = datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M')
        payload = {
            'touser': openid,
            'template_id': TEMPLATE_ID,
            'page': 'pages/index/index',
            'data': {
                'date2': {'value': now},
                'thing1': {'value': content},
                'thing3': {'value': 'E大发微博啦'},
                'thing4': {'value': 'weibo'}
            },
            'miniprogram_state': 'trial'
        }
        result = self._fetch_json(url, method='POST', json_payload=payload)
        if result is None:
            logger.error('Failed to send subscribe message')
        return result
```

- [ ] **Step 2: Add module-level default client helper**

At the bottom of `web/weixin_client.py`:

```python
def _create_default_client():
    return WeixinClient()


def get_default_client():
    if not hasattr(get_default_client, '_instance'):
        get_default_client._instance = _create_default_client()
    return get_default_client._instance
```

- [ ] **Step 3: Verify syntax again**

Run: `python -m py_compile web/weixin_client.py`
Expected: No output (success)

---

### Task 3: Refactor `web/weibo.py`

**Files:**
- Modify: `web/weibo.py`

- [ ] **Step 1: Update imports and instantiate client**

Add near the top after existing imports:

```python
from web.weixin_client import WeixinClient

weixin_client = WeixinClient()
```

- [ ] **Step 2: Replace `/get_wx_user` route (no change in behavior)**

Keep as-is:
```python
@app.route('/get_wx_user')
def get_wx_user():
    return renderResultJson(WxUserInfo.query.all())
```

- [ ] **Step 3: Replace `/addWxUser` route**

Replace the old `add_wx_user` body with:

```python
@app.route('/addWxUser')
def add_wx_user():
    print(' add wx user')
    code = request.args.get('code')
    nick_name = request.args.get('nickName')

    print('code: ', code, 'nick_name: ', nick_name)
    openid = weixin_client.get_openid(code)

    if openid is None or openid == '':
        print('获取openid失败')
        return renderResultJson(None, success=False, message='获取openid失败')

    user_info = db.session.query(WxUserInfo).filter_by(open_id=openid).first()
    if user_info is not None:
        return renderResultJson(None, success=False, message='openid已存在')
    now = datetime.datetime.now()
    a = WxUserInfo(openid, nick_name, '', now)
    db.session.add(a)
    db.session.commit()
    return renderResultJson(None)
```

- [ ] **Step 4: Replace `/send_msg/<openid>-<con>` route**

Replace the old `send_singe_msg` body with:

```python
@app.route('/send_msg/<openid>-<con>')
def send_singe_msg(openid, con):
    result = weixin_client.send_subscribe_message(openid, con)
    return renderResultJson(result)
```

- [ ] **Step 5: Remove old global WeChat logic**

Delete from `web/weibo.py`:
- `wechat_token` global dict
- `get_wechat_token()` function
- `get_openid()` function
- Old `send_singe_msg` body (already replaced)
- Any unused imports related to removed code

---

### Task 4: Write tests for TokenCache and WeixinClient

**Files:**
- Create: `web/test_weixin_client.py`

- [ ] **Step 1: Write TokenCache tests**

```python
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
```

- [ ] **Step 2: Write WeixinClient parsing tests**

```python
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
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest web/test_weixin_client.py -v`
Expected: All tests pass.

---

### Task 5: Verify application starts

**Files:**
- Modify: `web/weibo.py`

- [ ] **Step 1: Run syntax check**

Run: `python -m py_compile web/weibo.py`
Expected: No output (success)

- [ ] **Step 2: Import test**

Run: `python -c "from web import weibo; print('import ok')"`
Expected: `import ok`

---

## Plan Self-Review

- **Spec coverage:** TokenCache TTL/thread-safety/persistence covered in Task 1+4. WeixinClient extraction and retry logic covered in Task 2. Route refactoring covered in Task 3. Error handling covered in Task 2+3.
- **Placeholders:** None; all code provided.
- **Type consistency:** `WeixinClient` used consistently across routes. `send_subscribe_message` signature matches route usage.
