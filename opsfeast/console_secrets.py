"""Single-use Console secret delivery. Values never enter the record service.

One Web process owns this volatile broker. Restart, expiry and cancellation
discard pending values; Python/runtime memory is not a secure memory enclave.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import hmac
import secrets
import threading
import time

from .console_records import RecordError, identifier, string, exact


@dataclass(repr=False)
class _Request:
    session: str
    request_id: str
    label: str
    claim: str
    deadline: float
    expires_at: str
    state: str = 'waiting'
    value: bytearray | None = field(default=None, repr=False)
    timer: object = field(default=None, repr=False)

    def erase(self):
        if self.value is not None:
            self.value[:] = b'\x00' * len(self.value)
        self.value = None


class SecretBroker:
    def __init__(self):
        self._requests = {}
        self._lock = threading.RLock()

    def _expire(self, key):
        with self._lock:
            item = self._requests.pop(key, None)
            if item:
                item.erase()
                item.timer.cancel()

    def _get(self, sid, rid):
        key = (identifier(sid), identifier(rid))
        item = self._requests.get(key)
        if item is None or item.deadline <= time.monotonic():
            self._expire(key)
            raise RecordError('secret_request_unavailable')
        return item

    @staticmethod
    def _public(item):
        return dict(request_id=item.request_id, label=item.label,
                    expires_at=item.expires_at, state=item.state)

    def create(self, sid, body):
        identifier(sid)
        exact(body, 'request_id label timeout')
        rid = identifier(body['request_id'])
        label = string(body['label'], 200)
        seconds = body['timeout']
        if type(seconds) is not int or not 1 <= seconds <= 300:
            raise RecordError('invalid_secret_timeout')
        with self._lock:
            if len(self._requests) >= 64:
                raise RecordError('secret_capacity_reached')
            if any(s == sid for s, _ in self._requests):
                raise RecordError('secret_request_already_active')
            item = _Request(sid, rid, label, secrets.token_urlsafe(32),
                            time.monotonic() + seconds,
                            (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat())
            item.timer = threading.Timer(seconds, self._expire, args=((sid, rid),))
            item.timer.daemon = True
            self._requests[sid, rid] = item
            item.timer.start()
            return {**self._public(item), 'claim': item.claim}

    def pending(self, sid):
        identifier(sid)
        with self._lock:
            return [self._public(item) for key, item in list(self._requests.items())
                    if key[0] == sid and item.deadline > time.monotonic()]

    def submit(self, sid, rid, body):
        exact(body, 'value')
        value = body['value']
        if not isinstance(value, str) or any(c in value for c in '\r\n\x00'):
            raise RecordError('invalid_secret_value')
        try:
            encoded = value.encode()
        except UnicodeError:
            raise RecordError('invalid_secret_value') from None
        if len(encoded) > 4096:
            raise RecordError('invalid_secret_value')
        with self._lock:
            item = self._get(sid, rid)
            if item.state != 'waiting':
                raise RecordError('secret_already_submitted')
            item.value = bytearray(encoded)
            item.state = 'submitted'
            return {'state': 'submitted'}

    def take(self, sid, rid, body):
        exact(body, 'claim')
        with self._lock:
            item = self._get(sid, rid)
            if not isinstance(body['claim'], str) or not hmac.compare_digest(item.claim, body['claim']):
                raise RecordError('secret_claim_rejected')
            if item.state == 'cancelled':
                raise RecordError('secret_request_cancelled')
            if item.state != 'submitted':
                return {'state': 'waiting'}
            value = item.value.decode()
            self._expire((sid, rid))
            return {'state': 'consumed', 'value': value}

    def cancel(self, sid, rid, body=None):
        with self._lock:
            item = self._get(sid, rid)
            if body is not None:
                exact(body, 'claim')
                if not isinstance(body['claim'], str) or not hmac.compare_digest(item.claim, body['claim']):
                    raise RecordError('secret_claim_rejected')
                self._expire((sid, rid))
            else:
                item.erase()
                item.state = 'cancelled'
            return {'state': 'cancelled'}

    def close(self):
        with self._lock:
            for key in list(self._requests):
                self._expire(key)
