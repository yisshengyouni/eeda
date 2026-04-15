# Weibo Module Stability & Caching Enhancement

## Goal

Improve the reliability of Weibo data fetching and strengthen caching so that temporary network failures, API timeouts, and malformed responses do not break the user-facing endpoints.

## Architecture

Extract all Weibo scraping and caching logic into a new module `web/weibo_client.py`. `web/weibo.py` keeps only:
- Flask app initialization and routes
- SQLAlchemy models and WeChat-related utilities
- Thin route handlers that delegate to `WeiboClient`

## Components

### 1. WeiboCache (`web/weibo_client.py`)

A hybrid in-memory + disk cache with TTL and size limits.

- **In-memory store:** `dict` keyed by `page_{page}_{containerid}` and `detail_{id}`.
- **TTL:** Each entry stores a timestamp; expired entries are evicted on access and during periodic cleanup.
- **Size limit:** Maximum 500 entries; LRU eviction when limit exceeded.
- **Thread-safety:** Protected by `threading.Lock`.
- **Persistence:** Cache is serialized to `weibo_cache.json` on a background timer (every 60s) and on process exit (via `atexit`). Loaded at initialization if the file exists.
- **Cache hit for failures:** If a network request fails and a non-expired cached entry exists, return the cached data immediately.

### 2. WeiboClient (`web/weibo_client.py`)

Encapsulates all Weibo API communication.

- **`requests.Session`** with `HTTPAdapter` configured for connection pooling and retries (`urllib3.util.retry.Retry` with 3 retries, backoff factor 0.5, status codes 500/502/503/504).
- **Endpoints covered:**
  - `get_page(page, containerid)` — fetches timeline via async `aiohttp` wrapper (kept for compatibility) but with unified timeout and retry.
  - `get_detail(id)` — fetches extended post content.
  - `get_comments(id)` — fetches hot comments.
  - `get_user_info(uid)` — fetches user profile.
- **Error handling:** Network errors, timeouts, and non-200 responses all fall back to cache. If no cache, return empty results or `None` gracefully.
- **Response validation:** Check JSON structure before accessing nested keys; log malformed responses instead of crashing.

### 3. Data Parsing Robustness

- **`parse_page(json_data)`** becomes a standalone function in `web/weibo_client.py`.
- Validates that `json_data` contains `data.cards` before iterating.
- Safely extracts fields with `.get()` and provides defaults.
- Handles missing `pics`, `mblog`, or `card_group` without errors.
- `parse_time` remains but is hardened against unexpected string formats.

### 4. Route Integration (`web/weibo.py`)

Existing routes (`/hello`, `/get_detail/<id>`, `/get_comment/<id>`, `/get_weibo_buyer/<uid>`) are simplified to delegate to `WeiboClient`:

```python
client = WeiboClient()

@app.route('/<page>')
def hello(page, prefix='230413', uid='7519797263'):
    containerid = prefix + uid
    data = client.get_page(page, containerid)
    return jsonify({'success': True, 'data': data, 'message': 'suc'})
```

## Files to Change / Create

- **Create:** `web/weibo_client.py`
- **Modify:** `web/weibo.py` (remove scraping logic, update imports, delegate to client)
- **Create:** `web/test_weibo_client.py` (unit tests for cache and parser)

## Success Criteria

1. All existing routes continue to return the same JSON shape.
2. If the Weibo API is temporarily unavailable, endpoints return the last cached data instead of crashing.
3. The cache survives a server restart when `weibo_cache.json` exists.
4. Unit tests cover cache TTL, LRU eviction, disk save/load, and `parse_page` edge cases.
