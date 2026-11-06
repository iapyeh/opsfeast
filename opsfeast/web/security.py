"""Bounded, in-memory administrator sessions for the loopback Web service."""
from collections import deque
import hashlib
import secrets
import threading
import time
import re
from urllib.parse import parse_qsl, urlsplit

from opsfeast import admin

LIFETIME = 8 * 60 * 60
EDIT_LIFETIME = 30 * 60


def login_destination(next_url):
    """Allow the same local return destinations as login-navigation.mjs."""
    default = '/workspace'
    if not isinstance(next_url, str) or any(ord(char) < 32 or char == '\\' for char in next_url):
        return default
    if next_url in ('/settings/profiles', '/settings/site', '/setup', '/hosts', '/interactive'):
        return next_url
    uuid = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    if re.fullmatch(r'/interactive\?work=' + uuid, next_url):
        return next_url
    try:
        target = urlsplit(next_url)
    except ValueError:
        return default
    if target.scheme or target.netloc or target.fragment or '#' in next_url:
        return default
    keys = [key for key, _ in parse_qsl(target.query, keep_blank_values=True)]
    if re.fullmatch(r'/console/' + uuid + r'(?:/history)?(?:/blocks/' + uuid + r')?', target.path):
        if len(keys) == len(set(keys)) and set(keys) <= {'profile', 'host_id'}:
            return next_url
    if target.path == '/hosts' and set(keys) <= {'profile', 'host', 'view', 'new'}:
        return next_url
    if target.path == '/logs' and len(keys) == len(set(keys)) and set(keys) <= {'profile', 'entry', 'result'}:
        return next_url
    return default


def cookie_names(data_root):
    """Stable across ports/checkouts sharing site data; distinct for separate roots."""
    from pathlib import Path
    suffix=hashlib.sha256(str(Path(data_root).resolve(strict=True)).encode()).hexdigest()[:24]
    return 'opsfeast_session_'+suffix,'opsfeast_site_edit_'+suffix


class AgentCapability:
    """Verify a per-launch owner capability; retain only its digest."""
    def __init__(self, token=None):
        if token is not None and (not isinstance(token, str) or not 32 <= len(token) <= 256):
            raise ValueError('invalid_agent_capability')
        self.digest = hashlib.sha256(token.encode()).digest() if token else None

    def valid(self, authorization):
        import hmac
        if self.digest is None or not authorization.startswith('Bearer '):
            return False
        value = authorization[7:]
        return len(value) <= 256 and hmac.compare_digest(
            hashlib.sha256(value.encode()).digest(), self.digest)


class EditingSessions:
    """Short-lived site-edit capability, independent of administrator login."""
    def __init__(self):
        self.items={}
        self.lock=threading.Lock()

    def issue(self):
        token=secrets.token_urlsafe(32)
        now=time.monotonic()
        with self.lock:
            self.items={key:expiry for key,expiry in self.items.items() if expiry>now}
            if len(self.items)>=100:self.items.pop(next(iter(self.items)))
            self.items[hashlib.sha256(token.encode()).hexdigest()]=now+EDIT_LIFETIME
        return token

    def valid(self,token):
        if not token or len(token)>128:return False
        with self.lock:return self.items.get(hashlib.sha256(token.encode()).hexdigest(),0)>time.monotonic()

    def revoke(self,token):
        if token and len(token)<=128:
            with self.lock:self.items.pop(hashlib.sha256(token.encode()).hexdigest(),None)


class Sessions:
    def __init__(self):
        self.items={}
        self.attempts=deque()
        self.lock=threading.Lock()

    def allow_login(self):
        now=time.monotonic()
        with self.lock:
            while self.attempts and self.attempts[0]<now-60: self.attempts.popleft()
            if len(self.attempts)>=5: return False
            self.attempts.append(now)
            return True

    def issue(self, revision):
        token=secrets.token_urlsafe(32)
        now=time.monotonic()
        with self.lock:
            self.items={key:value for key,value in self.items.items() if value[1]>now}
            if len(self.items)>=100: self.items.pop(next(iter(self.items)))
            self.items[hashlib.sha256(token.encode()).hexdigest()]=(revision,now+LIFETIME)
        return token

    def authenticated(self, token, data_root):
        if not token or len(token)>128: return False
        key=hashlib.sha256(token.encode()).hexdigest()
        with self.lock: value=self.items.get(key)
        if value is None or value[1]<=time.monotonic(): return False
        state=admin.status(data_root)
        return state['configured'] and value[0]==state['revision']

    def revoke(self, token):
        if token:
            with self.lock:self.items.pop(hashlib.sha256(token.encode()).hexdigest(),None)

    def clear(self):
        with self.lock:self.items.clear()
