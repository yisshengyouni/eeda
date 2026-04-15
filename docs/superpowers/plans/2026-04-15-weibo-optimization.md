# Weibo Module Stability & Caching Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract Weibo scraping logic into a dedicated client module with TTL+LRU hybrid caching and robust retry/error handling.

**Architecture:** Create `web/weibo_client.py` containing `WeiboCache` (thread-safe TTL/LRU disk-backed cache) and `WeiboClient` (session-based requests with retries). Refactor `web/weibo.py` routes to delegate to `WeiboClient`.

**Tech Stack:** Python 3.7+, Flask, requests, urllib3, aiohttp, threading, json, atexit

---

### Task 1: Create `web/weibo_client.py` — Cache Layer

**Files:**
- Create: `web/weibo_client.py`

**Context:** Need a thread-safe cache with TTL, LRU eviction, and disk persistence.

- [ ] **Step 1: Implement `WeiboCache` class**

```python
import json
import os
import threading
import time
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)
CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', 'weibo_cache.json')
CACHE_FILE = os.path.abspath(CACHE_FILE)
MAX_CACHE_SIZE = 500
DEFAULT_TTL = 300  # 5 minutes
SAVE_INTERVAL = 60


class WeiboCache:
    def __init__(self, ttl=DEFAULT_TTL, max_size=MAX_CACHE_SIZE, cache_file=CACHE_FILE):
        self.ttl = ttl
        self.max_size = max_size
        self.cache_file = cache_file
        self._store = OrderedDict()
        self._lock = threading.Lock()
        self._last_save = 0
        self._load()

    def _load(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                with self._lock:
                    for key, (value, timestamp) in data.items():
                        if time.time() - timestamp < self.ttl:
                            self._store[key] = (value, timestamp)
                logger.info('Loaded %s cache entries from %s', len(self._store), self.cache_file)
            except Exception as e:
                logger.error('Failed to load cache file: %s', e)

    def _save(self, force=False):
        now = time.time()
        if not force and now - self._last_save < SAVE_INTERVAL:
            return
        self._last_save = now
        try:
            with self._lock:
                data = {k: v for k, v in self._store.items()}
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            logger.info('Saved %s cache entries to %s', len(data), self.cache_file)
        except Exception as e:
            logger.error('Failed to save cache file: %s', e)

    def get(self, key):
        with self._lock:
            if key not in self._store:
                return None
            value, timestamp = self._store[key]
            if time.time() - timestamp > self.ttl:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return value

    def set(self, key, value):
        with self._lock:
            self._store[key] = (value, time.time())
            self._store.move_to_end(key)
            while len(self._store) > self.max_size:
                self._store.popitem(last=False)
        self._save()

    def clear_expired(self):
        now = time.time()
        with self._lock:
            expired = [k for k, (_, ts) in self._store.items() if now - ts > self.ttl]
            for k in expired:
                del self._store[k]

    def save_on_exit(self):
        self._save(force=True)
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile web/weibo_client.py`
Expected: No output (success)

---

### Task 2: Create `web/weibo_client.py` — Client & Parsing Layer

**Files:**
- Modify: `web/weibo_client.py`

- [ ] **Step 1: Add imports and `parse_time` + `parse_page`**

```python
import asyncio
import datetime
import aiohttp
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dateutil import parser
from pyquery import PyQuery as pq

HEADERS = {
    'Host': 'm.weibo.cn',
    'Referer': 'https://m.weibo.cn/u/5687069307',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}


def parse_time(create_at):
    if not create_at or not isinstance(create_at, str):
        return create_at
    create_at = create_at.strip()
    minutes_index = create_at.find('分钟前')
    if minutes_index >= 0:
        minutes = create_at[0:minutes_index]
        now = datetime.datetime.now()
        delta = datetime.timedelta(minutes=int(minutes))
        return (now - delta).strftime('%Y-%m-%d %H:%M:%S')
    hours_index = create_at.find('小时前')
    if hours_index >= 0:
        hours = create_at[0:hours_index]
        now = datetime.datetime.now()
        delta = datetime.timedelta(hours=int(hours))
        return (now - delta).strftime('%Y-%m-%d %H:%M:%S')
    day_index = create_at.find('昨天')
    if day_index >= 0:
        now = datetime.datetime.now()
        delta = datetime.timedelta(days=1)
        n_now = now - delta
        res = n_now.strftime('%Y-%m-%d')
        return res + create_at[2:8]
    if len(create_at) == 5:
        now = datetime.datetime.now()
        return now.strftime('%Y') + '-' + create_at
    if create_at.find('+0800') > 0:
        try:
            f_date = parser.parse(create_at)
            return f_date.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return create_at
    return create_at


def parse_page(json_data):
    result = []
    if not json_data or not isinstance(json_data, dict):
        return result
    data = json_data.get('data')
    if not data or not isinstance(data, dict):
        return result
    items = data.get('cards')
    if not items:
        return result
    for item in items:
        card_group = item.get('card_group')
        if card_group is not None:
            for card in card_group:
                mblog = card.get('mblog')
                if mblog:
                    parsed = _parse_mblog(mblog)
                    if parsed:
                        result.append(parsed)
        else:
            mblog = item.get('mblog')
            if mblog:
                parsed = _parse_mblog(mblog)
                if parsed:
                    result.append(parsed)
    return result


def _parse_mblog(item):
    weibo = {}
    weibo['id'] = item.get('id')
    text = item.get('text', '').strip()
    if text:
        weibo['text'] = pq(text).text()
    else:
        weibo['text'] = ''
    if weibo['text'] == '':
        return None
    weibo['attitudes'] = item.get('attitudes_count')
    weibo['comments'] = item.get('comments_count')
    weibo['reposts'] = item.get('reposts_count')
    weibo['original_pic'] = item.get('original_pic')
    pics = item.get('pics')
    pics_data = []
    if pics:
        for pic in pics:
            pic_data = {
                'url': pic.get('url'),
                'large_url': pic.get('large', {}).get('url')
            }
            pics_data.append(pic_data)
    weibo['pics'] = pics_data
    weibo['created_at'] = parse_time(item.get('created_at'))
    if weibo['text'].endswith('...全文') and item.get('isTop') != 1:
        # long text will be expanded later by client
        pass
    return weibo
```

- [ ] **Step 2: Implement `WeiboClient` class**

```python
class WeiboClient:
    def __init__(self, cache=None):
        self.cache = cache or WeiboCache()
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def _cache_key(self, prefix, *parts):
        return '_'.join([prefix] + [str(p) for p in parts])

    def _fetch_json(self, url, timeout=10):
        try:
            resp = self.session.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            logger.warning('Non-200 status %s for %s', resp.status_code, url)
        except requests.RequestException as e:
            logger.error('Request error for %s: %s', url, e)
        except Exception as e:
            logger.error('Unexpected error for %s: %s', url, e)
        return None

    def get_page(self, page, containerid, timeout=10):
        cache_key = self._cache_key('page', page, containerid)
        cached = self.cache.get(cache_key)
        try:
            if containerid is None:
                containerid = '2304137519797263'
            url = (
                'https://m.weibo.cn/api/container/getIndex?containerid='
                + containerid + '_-_WEIBO_SECOND_PROFILE_WEIBO&page_type=03&page='
                + str(page)
            )
            logger.info('Fetching weibo page: %s', url)
            json_data = self._fetch_json(url, timeout)
            if json_data is not None:
                self.cache.set(cache_key, json_data)
                return json_data
        except Exception as e:
            logger.error('Error fetching page %s: %s', page, e)
        if cached is not None:
            logger.warning('Returning cached page %s due to fetch failure', page)
            return cached
        return None

    def get_page_async(self, page, containerid, timeout=10):
        # kept for backward compatibility but delegates to sync get_page
        return self.get_page(page, containerid, timeout)

    def get_detail(self, weibo_id, timeout=10):
        cache_key = self._cache_key('detail', weibo_id)
        cached = self.cache.get(cache_key)
        if cached is not None:
            # if cached already has full text, return it
            if not cached.get('text', '').endswith('...全文'):
                return cached
            if cached.get('longTextContent') is not None:
                return cached
        url = 'https://m.weibo.cn/statuses/extend?id=' + str(weibo_id)
        data = self._fetch_json(url, timeout)
        if data and isinstance(data, dict) and data.get('data'):
            detail = data['data']
            if cached is not None:
                cached.update(detail)
                self.cache.set(cache_key, cached)
                return cached
            self.cache.set(cache_key, detail)
            return detail
        return cached or {}

    def get_comments(self, weibo_id, timeout=10):
        url = (
            'https://m.weibo.cn/comments/hotflow?id='
            + str(weibo_id) + '&mid=' + str(weibo_id) + '&max_id_type=0'
        )
        data = self._fetch_json(url, timeout)
        if data and isinstance(data, dict) and data.get('data'):
            return data['data'].get('data', [])
        return []

    def get_user_info(self, uid, timeout=10):
        url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value=' + str(uid)
        data = self._fetch_json(url, timeout)
        if not data or not isinstance(data, dict):
            return {'desc': '', 'screen_name': '', 'profile_image_url': ''}
        user_info = data.get('data', {}).get('userInfo', {})
        return {
            'desc': user_info.get('description', ''),
            'screen_name': user_info.get('screen_name', ''),
            'profile_image_url': user_info.get('profile_image_url', ''),
            'following': user_info.get('follow_count'),
            'followers': user_info.get('followers_count'),
            'statuses_count': user_info.get('statuses_count')
        }

    def get_weibo(self, page, containerid):
        json_data = self.get_page(page, containerid)
        if json_data is None:
            return []
        result = parse_page(json_data)
        for res in result:
            # expand long text if needed
            if res['text'].endswith('...全文'):
                detail = self.get_detail(res['id'])
                if detail and detail.get('longTextContent'):
                    res['text'] = detail['longTextContent']
            self.cache.set(self._cache_key('detail', res['id']), res)
        return result
```

- [ ] **Step 3: Add module-level cleanup hook**

At the bottom of `web/weibo_client.py`:

```python
import atexit

def _create_default_client():
    c = WeiboClient()
    atexit.register(c.cache.save_on_exit)
    return c


def get_default_client():
    if not hasattr(get_default_client, '_instance'):
        get_default_client._instance = _create_default_client()
    return get_default_client._instance
```

---

### Task 3: Refactor `web/weibo.py`

**Files:**
- Modify: `web/weibo.py`

- [ ] **Step 1: Update imports and remove duplicated logic**

Replace the scraping imports/definitions at the top with:

```python
from web.weibo_client import WeiboClient, parse_time, HEADERS
```

Keep Flask, SQLAlchemy, datetime, json, os, requests, logging imports as needed.

Remove: global `page_cache`, `get_page`, `get_page_async`, `get_extend`, `parse_page`, `get_weibo`, `get_weibo_buyer` body, `get_comment` body.

- [ ] **Step 2: Instantiate client and update routes**

Add near the top after app creation:

```python
weibo_client = WeiboClient()
```

Update `/hello` route:

```python
@app.route('/<page>')
@app.route('/<page>/<prefix>')
@app.route('/<page>/<prefix>/<uid>')
def hello(page, prefix='230413', uid='7519797263'):
    print('get weibo, page -> ', page)
    containerid = prefix + uid
    data = weibo_client.get_weibo(page, containerid)
    return jsonify({'success': True, 'data': data, 'message': 'suc'})
```

Update `/get_weibo_buyer/<uid>` route:

```python
@app.route('/get_weibo_buyer/<uid>')
def get_weibo_buyer(uid):
    return weibo_client.get_user_info(uid)
```

Update `/get_detail/<id>` route:

```python
@app.route('/get_detail/<id>')
def get_detail(id):
    return weibo_client.get_detail(id)
```

Update `/get_comment/<id>` route:

```python
@app.route('/get_comment/<id>')
def get_comment(id):
    return weibo_client.get_comments(id)
```

- [ ] **Step 3: Remove dead code**

Delete the old `get_page`, `get_page_async`, `get_extend`, `parse_page`, `get_weibo`, and global `page_cache` definitions that have been moved to `web/weibo_client.py`.

---

### Task 4: Write tests for cache and parser

**Files:**
- Create: `web/test_weibo_client.py`

- [ ] **Step 1: Write cache tests**

```python
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
```

- [ ] **Step 2: Write parser tests**

```python
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
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest web/test_weibo_client.py -v`
Expected: All tests pass.

---

### Task 5: Verify application starts

**Files:**
- Modify: `web/weibo.py`

- [ ] **Step 1: Run syntax check on modified file**

Run: `python -m py_compile web/weibo.py`
Expected: No output (success)

- [ ] **Step 2: Import test**

Run: `python -c "from web import weibo; print('import ok')"`
Expected: `import ok`

---

## Plan Self-Review

- **Spec coverage:** Cache TTL/LRU/persistence covered in Task 1+4. Client extraction and retry logic covered in Task 2. Route refactoring covered in Task 3. Parser robustness covered in Task 2+4.
- **Placeholders:** None; all code provided.
- **Type consistency:** `WeiboClient` used consistently across routes. Cache keys use `page_{page}_{containerid}` and `detail_{id}` as specified.
