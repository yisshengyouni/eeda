# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python Flask application that scrapes Weibo (Chinese microblogging platform) user timelines and provides backend services for a WeChat mini-program. It is deployed to Heroku.

## Development Commands

- **Run the development server:** `python main.py` (serves on `0.0.0.0:5050` by default, or the `PORT` environment variable)
- **Run the app module directly:** `python web/weibo.py`
- **Install dependencies:** `pip install -r requirements.txt`

There are no tests, linting, or build tools currently configured in this project.

## Architecture

### Monolithic Single-File App

Almost all application logic lives in `web/weibo.py`. The `main.py` file simply imports `web/weibo` and calls `weibo.app.run()`.

### Core Responsibilities

1. **Weibo Data Scraping**
   - Fetches user timelines from `m.weibo.cn/api/container/getIndex`.
   - Parses微博 cards and extracts post text, images, likes, comments, and repost counts.
   - Expands truncated posts by calling `m.weibo.cn/statuses/extend`.
   - Fetches hot comments via `m.weibo.cn/comments/hotflow`.

2. **In-Memory Caching**
   - `page_cache` is a global dictionary that stores fetched Weibo pages and individual post details.
   - The async fetcher (`get_page_async`) falls back to `page_cache` on network errors or timeouts.
   - Posts parsed by `get_weibo` are also stored in `page_cache` keyed by their Weibo ID.

3. **WeChat Mini-Program Backend**
   - `WxUserInfo` SQLAlchemy model stores WeChat `open_id` and `nick_name`.
   - Endpoints for adding/retrieving WeChat users (`/addWxUser`, `/get_wx_user`).
   - WeChat token caching (`get_wechat_token`) and OpenID resolution (`get_openid`).
   - Subscription message sending via `/send_msg/<openid>-<con>`.

### Async Pattern

The app uses `asyncio` + `aiohttp` for fetching Weibo pages, but the async function (`get_page_async`) is wrapped in a synchronous function (`get_page`) that creates a new event loop with `asyncio.new_event_loop()`.

### Database

- Uses SQLAlchemy 2.x with a declarative base.
- The engine is hardcoded to `postgresql://user:password@localhost/database` in `web/weibo.py`.
- The `SQLALCHEMY_DATABASE_URI` Flask config is set to an empty string and unused.

### Environment Variables

- `PORT` — Server port (default `5050`).
- `wx_secret` — WeChat API secret key.
- `appId` — WeChat app ID.
