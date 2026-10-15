"""Installation identity contract 0.1.0; reads never initialize storage."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
from uuid import UUID, uuid4

from . import ConfigError

NIL_UUID = '00000000-0000-0000-0000-000000000000'
DEVELOPMENT_UUID = '00000000-0000-0000-0000-000000000001'
FILENAME = '.opsfeast-instance.json'


def _path(installation):
    root = Path(installation).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ConfigError('installation must be a directory')
    path = root / FILENAME
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ConfigError('instance metadata must be a regular file')
    return path


def _validate(data):
    if not isinstance(data, dict) or data.get('schema_version') != '0.1.0':
        raise ConfigError('unsupported instance metadata schema')
    if set(data) - {'schema_version', 'id', 'name', 'description', 'installation_path'}:
        raise ConfigError('unknown instance metadata fields')
    identifier = data.get('id', NIL_UUID)
    try:
        if not isinstance(identifier, str) or str(UUID(identifier)) != identifier:
            raise ValueError()
    except (ValueError, AttributeError):
        raise ConfigError('instance id must be a canonical UUID') from None
    name = data.get('name', identifier)
    if not isinstance(name, str) or not name.strip() or any(ord(c) < 32 for c in name):
        raise ConfigError('instance name must be a nonempty single-line string')
    description = data.get('description', '')
    if not isinstance(description, str):
        raise ConfigError('instance description must be a string')
    location = data.get('installation_path')
    if not isinstance(location, str) or not Path(location).is_absolute():
        raise ConfigError('instance installation_path must be absolute')
    return dict(data, id=identifier, name=name, description=description)


def read_identity(installation):
    path = _path(installation)
    if not path.exists():
        return {'schema_version': '0.1.0', 'id': NIL_UUID, 'name': NIL_UUID,
                'description': '', 'identity_status': 'placeholder', 'reason_code': 'identity_missing'}
    try:
        def pairs(items):
            value = {}
            for key, item in items:
                if key in value:
                    raise ValueError('duplicate key')
                value[key] = item
            return value
        data = _validate(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs))
    except (ValueError, UnicodeError):
        raise ConfigError('instance metadata is invalid') from None
    # Copies cannot silently retain their source installation identity.
    if data['installation_path'] != str(path.parent):
        if data['name'] == data['id']:
            data['name'] = NIL_UUID
        data['id'] = NIL_UUID
        return dict(data, identity_status='placeholder', reason_code='installation_location_changed')
    return dict(data, identity_status='placeholder' if data['id'] == NIL_UUID else 'assigned',
                reason_code='identity_placeholder' if data['id'] == NIL_UUID else 'identity_assigned')


@contextmanager
def _locked(path):
    # Supported controller platforms are POSIX; all cooperating writers serialize.
    import fcntl
    lock = path.with_suffix('.lock')
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def _write(path, data):
    _path(path.parent)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.opsfeast-instance-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(_validate(data), stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def initialize_identity(installation, *, identifier=None, name=None, description=None, renew=False, relocate=False):
    path = _path(installation)
    if renew and relocate:
        raise ConfigError('renew and relocate are mutually exclusive')
    with _locked(path):
        existing = read_identity(path.parent)
        moved = existing['reason_code'] == 'installation_location_changed'
        if relocate and moved:
            # Explicit move preserves identity; a copy must instead initialize/renew.
            existing = _validate(json.loads(path.read_text(encoding='utf-8')))
        elif relocate:
            raise ConfigError('relocate requires metadata from another installation path')
        generate = renew or existing['id'] == NIL_UUID
        if identifier is not None and not generate:
            raise ConfigError('changing an assigned id requires renew=True')
        value = identifier if identifier is not None else str(uuid4()) if generate else existing['id']
        old_name = existing['name']
        default_name = value if old_name in (existing['id'], NIL_UUID) else old_name
        data = {'schema_version': '0.1.0', 'id': value, 'name': default_name if name is None else name,
                'description': existing['description'] if description is None else description,
                'installation_path': str(path.parent)}
        _write(path, data)
    return read_identity(path.parent)


def update_identity(installation, *, name=None, description=None):
    path = _path(installation)
    with _locked(path):
        data = read_identity(path.parent)
        if data['reason_code'] in ('identity_missing', 'installation_location_changed'):
            raise ConfigError('initialize this installation identity before editing metadata')
        data = {key: value for key, value in data.items() if key not in ('identity_status', 'reason_code')}
        if name is not None:
            data['name'] = name
        if description is not None:
            data['description'] = description
        _write(path, data)
    return read_identity(path.parent)
