# Weixin Module Stability & Caching Enhancement

## Goal

Improve the reliability of WeChat API interactions by extracting WeChat logic into a dedicated client module with thread-safe token caching, robust retry handling, and clearer error boundaries.

## Architecture

Extract all WeChat API logic into a new module `web/weixin_client.py`. `web/weibo.py` keeps only:
- Flask routes (`/addWxUser`, `/get_wx_user`, `/send_msg/<openid>-<con>`)
- SQLAlchemy models (`WxUserInfo`)
- Thin route handlers that delegate to `WeixinClient`

## Components

### 1. TokenCache (`web/weixin_client.py`)

Replace the global `wechat_token` dict with a thread-safe `TokenCache`.

- **Thread-safe:** Protected by `threading.Lock`.
- **TTL-aware:** Uses `time.time()` instead of `datetime` arithmetic to avoid edge cases.
- **Grace period:** Refreshes token 60 seconds before actual expiry to prevent race conditions at boundary.
- **Persistence:** Saves token to `weixin_token.json` and reloads on startup.

### 2. WeixinClient (`web/weixin_client.py`)

Encapsulates all WeChat API communication.

- **`requests.Session`** with `HTTPAdapter` configured for connection pooling and retries (`urllib3.util.retry.Retry` with 3 retries, backoff factor 0.5, status codes 500/502/503/504).
- **Methods:**
  - `get_access_token()` — returns cached or freshly fetched token.
  - `get_openid(code)` — fetches WeChat OpenID with retries and validation.
  - `send_subscribe_message(openid, content)` — sends subscription message with proper error handling and response validation.
- **Error handling:** All API calls catch network errors, log them, and return `None` or empty dicts gracefully instead of crashing.

### 3. Route Integration (`web/weibo.py`)

Routes simplified to delegate to `WeixinClient`:

```python
from web.weixin_client import WeixinClient
weixin_client = WeixinClient()

@app.route('/send_msg/<openid>-<con>')
def send_singe_msg(openid, con):
    result = weixin_client.send_subscribe_message(openid, con)
    return renderResultJson(result)
```

## Files to Change / Create

- **Create:** `web/weixin_client.py`
- **Modify:** `web/weibo.py` (remove WeChat API logic, update imports, delegate to client)
- **Create:** `web/test_weixin_client.py` (unit tests for TokenCache and client)

## Success Criteria

1. All existing WeChat routes continue to return the same JSON shape.
2. Access token is cached thread-safely and refreshed before expiry.
3. Token cache survives a server restart when `weixin_token.json` exists.
4. Network failures on WeChat APIs are retried and fail gracefully.
5. Unit tests cover TokenCache TTL, persistence, and response parsing edge cases.
