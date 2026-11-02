"""Bounded, in-memory administrator sessions for the loopback Web service."""
from collections import deque
import hashlib
import secrets
import threading
import time

from opsfeast import admin

COOKIE = 'opsfeast_session'
LIFETIME = 8 * 60 * 60
EDIT_COOKIE = 'opsfeast_site_edit'
EDIT_LIFETIME = 30 * 60


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
