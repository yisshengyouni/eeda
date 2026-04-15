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

WEIBO_COOKIE="""SUB=_2A25E2-CVDeRhGeRL71QY9ibLzzyIHXVnmXxdrDV6PUJbktAYLXTgkW1NUyyu4H7sS8QhjRzfCCKj8tkEJcDwNz8R;SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9W5mOVdIgk9nQ8GnIQwriW3T5NHD95QESKBc1KqRS0B7Ws4Dqcjci--fiK.7iKn0i--NiK.0iKLhi--Ni-i8i-2Xi--Xi-ihiK.Ni--fiK.pi-2Ri--NiK.piKLh;SCF=ArnADx7wqr8O_ahdWyjjYPav5ugcQGTuhBAZ6n-f0dxsRtdmaNCAV4C84JUg4PskYOhU-sWqddsVGQxmFVzhIZw.; SSOLoginState=1776259269; ALF=1778851269; MLOGIN=1; _T_WM=61011888518; XSRF-TOKEN=1c374d;M_WEIBOCN_PARAMS=uicode%3D20000174;WBPSESS=37cCvaJpVHXbfW7WW2gsD8Qnsm1jAfPFv5IrcMR-9_2LhGr91DDnp7mdoQCTDPVanPp9HFWPPBcVaCjW76Np9YXTqM__bJRCNlTGnqY4Bxu0IavRGXMhKP6b05HABu56wt64xrnVIziwEx9DvE222g=="""
                   

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
        if self.cache_file and os.path.exists(self.cache_file):
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
        if not self.cache_file:
            return
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
        logger.debug('parse_page: json_data is empty or not dict: %s', type(json_data))
        return result
    data = json_data.get('data')
    if not data or not isinstance(data, dict):
        logger.debug('parse_page: missing or invalid data field, keys=%s', list(json_data.keys()) if isinstance(json_data, dict) else 'n/a')
        return result
    items = data.get('cards')
    if not items:
        logger.debug('parse_page: no cards found in data, data keys=%s', list(data.keys()))
        return result
    logger.debug('parse_page: processing %s cards', len(items))
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
        logger.debug('_parse_mblog: skipping empty text for id=%s', weibo['id'])
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
    logger.debug('_parse_mblog: parsed id=%s text_len=%s', weibo['id'], len(weibo['text']))
    return weibo


class WeiboClient:
    def __init__(self, cache=None, cookie=None):
        self.cache = cache or WeiboCache()
        self._cookie = cookie or os.getenv('WEIBO_COOKIE', WEIBO_COOKIE)
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

    def set_cookie(self, cookie):
        self._cookie = cookie
        logger.info('WeiboClient cookie updated (length=%s)', len(cookie))

    def _request_headers(self):
        headers = HEADERS.copy()
        if self._cookie:
            headers['Cookie'] = self._cookie
        return headers

    def _cache_key(self, prefix, *parts):
        return '_'.join([prefix] + [str(p) for p in parts])

    def _fetch_json(self, url, timeout=10):
        logger.debug('Fetching URL: %s', url)
        try:
            resp = self.session.get(url, headers=self._request_headers(), timeout=timeout)
            logger.debug('Response status %s for %s, content-length: %s',
 resp.status_code, url, resp.headers.get('Content-Length'))
            if resp.status_code == 200:
                data = resp.json()
                logger.debug('Response OK, keys: %s', list(data.keys()) if isinstance(data, dict) else 'non-dict')
                return data
            logger.warning('Non-200 status %s for %s, body snippet: %.200s',
   resp.status_code, url, resp.text)
        except requests.RequestException as e:
            logger.error('Request error for %s: %s', url, e)
        except Exception as e:
            logger.error('Unexpected error for %s: %s', url, e)
        return None

    def get_page(self, page, containerid, timeout=10):
        cache_key = self._cache_key('page', page, containerid)
        cached = self.cache.get(cache_key)
        logger.debug('get_page cache lookup: key=%s, hit=%s', cache_key, cached is not None)
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
                logger.debug('get_page fetched and cached new data for page=%s', page)
                return json_data
        except Exception as e:
            logger.error('Error fetching page %s: %s', page, e)
        if cached is not None:
            logger.warning('Returning cached page %s due to fetch failure', page)
            return cached
        logger.error('get_page failed and no cache for page=%s containerid=%s', page, containerid)
        return None

    def get_page_async(self, page, containerid, timeout=10):
        # kept for backward compatibility but delegates to sync get_page
        return self.get_page(page, containerid, timeout)

    def get_detail(self, weibo_id, timeout=10):
        cache_key = self._cache_key('detail', weibo_id)
        cached = self.cache.get(cache_key)
        logger.debug('get_detail id=%s cache_hit=%s', weibo_id, cached is not None)
        if cached is not None:
            # if cached already has full text, return it
            if not cached.get('text', '').endswith('...全文'):
                logger.debug('get_detail id=%s returning cached full text', weibo_id)
                return cached
            if cached.get('longTextContent') is not None:
                logger.debug('get_detail id=%s returning cached longTextContent', weibo_id)
                return cached
        url = 'https://m.weibo.cn/statuses/extend?id=' + str(weibo_id)
        data = self._fetch_json(url, timeout)
        if data and isinstance(data, dict) and data.get('data'):
            detail = data['data']
            if cached is not None:
                cached.update(detail)
                self.cache.set(cache_key, cached)
                logger.debug('get_detail id=%s updated cached detail', weibo_id)
                return cached
            self.cache.set(cache_key, detail)
            logger.debug('get_detail id=%s stored new detail', weibo_id)
            return detail
        logger.warning('get_detail id=%s fetch failed, returning cached=%s', weibo_id, cached is not None)
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
        logger.debug('get_weibo called page=%s containerid=%s', page, containerid)
        json_data = self.get_page(page, containerid)
        if json_data is None:
            logger.warning('get_weibo: get_page returned None for page=%s', page)
            return []
        result = parse_page(json_data)
        logger.debug('get_weibo: parsed %s posts for page=%s', len(result), page)
        for res in result:
            # expand long text if needed
            if res['text'].endswith('...全文'):
                detail = self.get_detail(res['id'])
                if detail and detail.get('longTextContent'):
                    res['text'] = detail['longTextContent']
                    logger.debug('get_weibo: expanded long text for id=%s', res['id'])
            self.cache.set(self._cache_key('detail', res['id']), res)
        logger.info('get_weibo returning %s posts for page=%s', len(result), page)
        return result


import atexit

def _create_default_client():
    c = WeiboClient()
    atexit.register(c.cache.save_on_exit)
    return c


def get_default_client():
    if not hasattr(get_default_client, '_instance'):
        get_default_client._instance = _create_default_client()
    return get_default_client._instance
