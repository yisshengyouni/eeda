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
        if self.cache_file and os.path.exists(self.cache_file):
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
        if not self.cache_file:
            return
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
            if self._token and time.time() + self.grace_period < self._expires_at:
                return self._token
            return None

    def set(self, token, expires_in):
        with self._lock:
            self._token = token
            self._expires_at = time.time() + int(expires_in)
        self._save()


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


def _create_default_client():
    return WeixinClient()


def get_default_client():
    if not hasattr(get_default_client, '_instance'):
        get_default_client._instance = _create_default_client()
    return get_default_client._instance
