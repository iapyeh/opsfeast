"""Single-use, browser-bound first-administrator grants; secrets stay in memory."""
import hashlib
import hmac
import secrets
import threading
import time

LIFETIME = 10 * 60


class InvalidSetupGrant(ValueError):
    pass


def _digest(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise InvalidSetupGrant('invalid_setup_grant')
    return hashlib.sha256(value.encode('utf-8')).digest()


class SetupForms:
    def __init__(self, clock=time.monotonic):
        self.clock=clock
        self.lock=threading.Lock()
        self.grant=None
        self.browser=None
        self.csrf=None
        self.expiry=0

    def issue(self):
        token=secrets.token_urlsafe(32)
        with self.lock:
            self.grant=_digest(token)
            self.browser=self.csrf=None
            self.expiry=self.clock()+LIFETIME
        return token

    def claim(self, token):
        digest=_digest(token)
        with self.lock:
            if self.clock()>=self.expiry or self.grant is None or not hmac.compare_digest(self.grant,digest):
                raise InvalidSetupGrant('invalid_setup_grant')
            browser,csrf=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
            self.grant=None
            self.browser,self.csrf=_digest(browser),_digest(csrf)
            return browser,csrf,max(1,int(self.expiry-self.clock()))

    def complete(self, browser, csrf, save):
        browser,csrf=_digest(browser),_digest(csrf)
        with self.lock:
            if (self.clock()>=self.expiry or self.browser is None or self.csrf is None
                    or not hmac.compare_digest(browser,self.browser) or not hmac.compare_digest(csrf,self.csrf)):
                raise InvalidSetupGrant('invalid_setup_grant')
            # Hold the grant lock through the atomic credential write. Validation
            # failures allow correction; success consumes every outstanding grant.
            save()
            self.grant=self.browser=self.csrf=None
            self.expiry=0
