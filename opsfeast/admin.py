"""Single local administrator credentials; no plaintext password or default account."""
import hashlib
import hmac
import json
import re
import secrets

from . import ConfigError
from .identity import _locked
from .site import _root, _regular, _atomic, SiteConflict

FILENAME = '.opsfeast-admin.json'
USERNAME = re.compile(r'^[A-Za-z0-9_.-]{3,64}$')


class InvalidCredentials(ConfigError):
    pass


def _read(data_root):
    path = _regular(_root(data_root) / FILENAME)
    if not path.exists(): return None
    try:
        def pairs(items):
            value={}
            for key,item in items:
                if key in value: raise ValueError()
                value[key]=item
            return value
        data=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=pairs)
        if (not isinstance(data,dict) or set(data)!={'schema_version','revision','username','algorithm','salt','digest'}
                or data['schema_version']!='0.1.0' or data['algorithm']!='scrypt-16384-8-1'
                or type(data['revision']) is not int or data['revision']<1
                or not isinstance(data['username'],str) or not USERNAME.fullmatch(data['username'])
                or not isinstance(data['salt'],str) or not re.fullmatch(r'[0-9a-f]{64}',data['salt'])
                or not isinstance(data['digest'],str) or not re.fullmatch(r'[0-9a-f]{64}',data['digest'])):
            raise ValueError()
        return data
    except (ValueError, UnicodeError):
        raise ConfigError('invalid administrator metadata') from None


def status(data_root):
    value=_read(data_root)
    return {'configured':value is not None,'revision':value['revision'] if value else 0,
            'username':value['username'] if value else None}


def _digest(password,salt):
    return hashlib.scrypt(password.encode('utf-8'),salt=bytes.fromhex(salt),n=16384,r=8,p=1,maxmem=64*1024*1024,dklen=32).hex()


def verify(data_root, username, password):
    value=_read(data_root)
    if not isinstance(password,str) or not 1<=len(password)<=256 or not isinstance(username,str): return False
    try:
        password.encode('utf-8');username.encode('utf-8')
    except UnicodeError:return False
    # Hash even an unknown username to keep the username out of timing shortcuts.
    salt=value['salt'] if value else '00'*32
    digest=_digest(password,salt)
    return bool(value and hmac.compare_digest(str(username).encode(),value['username'].encode())
                and hmac.compare_digest(digest,value['digest']))


def configure(data_root, *, username, password, expected_revision, current_password=None):
    """Bootstrap once or change with the current password. Invalidates old sessions."""
    if not isinstance(username,str) or not USERNAME.fullmatch(username):
        raise ConfigError('username requires 3-64 ASCII letters, digits, dot, hyphen or underscore')
    if not isinstance(password,str) or not 12<=len(password)<=256:
        raise ConfigError('password requires 12-256 characters')
    try:password.encode('utf-8')
    except UnicodeError:raise ConfigError('password must contain valid Unicode text') from None
    if type(expected_revision) is not int or expected_revision<0:
        raise ConfigError('invalid administrator revision')
    root=_root(data_root)
    path=_regular(root/FILENAME)
    with _locked(path):
        current=_read(root)
        revision=current['revision'] if current else 0
        if revision!=expected_revision: raise SiteConflict('administrator changed; reload before saving')
        if current and not verify(root,current['username'],current_password):
            raise InvalidCredentials('current password is required')
        salt=secrets.token_hex(32)
        value={'schema_version':'0.1.0','revision':revision+1,'username':username,
               'algorithm':'scrypt-16384-8-1','salt':salt,'digest':_digest(password,salt)}
        _atomic(path,(json.dumps(value,indent=2)+'\n').encode())
    return status(root)
