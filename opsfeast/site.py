"""Installation presentation 0.1.0. Separate display overrides from identity."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile

from . import ConfigError
from .identity import _locked, read_identity

FILENAME = '.opsfeast-site.json'
ASSET_DIRECTORY = '.opsfeast-site-assets'
MAX_UPLOAD = 2 * 1024 * 1024
ASSET_ID = re.compile(r'^[0-9a-f]{64}\.png$')
DEFAULT = {'schema_version': '0.1.0', 'revision': 0, 'site_name': None,
           'slogan': '', 'logo': None, 'avatar': None}


class SiteConflict(ConfigError):
    """A cooperating writer has saved a newer revision."""


def _root(installation):
    root = Path(installation).resolve(strict=True)
    if not root.is_dir():
        raise ConfigError('installation must be a directory')
    from .storage import resolve_data_root
    return resolve_data_root(root, required=True)


def _regular(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ConfigError('site file must be a regular file')
    return path


def _assets(root, *, create=False):
    path = root / ASSET_DIRECTORY
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ConfigError('site asset directory must be a real directory')
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    return path


def validate_site(data):
    if not isinstance(data, dict) or set(data) != set(DEFAULT):
        raise ConfigError('site settings fields do not match schema 0.1.0')
    if data['schema_version'] != '0.1.0':
        raise ConfigError('unsupported site settings version')
    if type(data['revision']) is not int or data['revision'] < 0:
        raise ConfigError('site revision must be a nonnegative integer')
    for key, limit, nullable in [('site_name', 80, True), ('slogan', 160, False)]:
        value = data[key]
        if value is None and nullable:
            continue
        if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ConfigError(f'{key} must be single-line text within {limit} characters')
        if key == 'site_name' and not value.strip():
            raise ConfigError('site_name must be nonblank or null')
    for key in ('logo', 'avatar'):
        if data[key] is not None and (not isinstance(data[key], str) or not ASSET_ID.fullmatch(data[key])):
            raise ConfigError(f'{key} must be a saved asset id or null')
    return dict(data)


def read_site(installation):
    """Read raw presentation settings. Never initialize identity or storage."""
    root = _root(installation)
    path = _regular(root / FILENAME)
    if not path.exists():
        return dict(DEFAULT)
    def pairs(items):
        data = {}
        for key, value in items:
            if key in data:
                raise ValueError('duplicate site field')
            data[key] = value
        return data
    try:
        return validate_site(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs))
    except (ValueError, UnicodeError) as exc:
        raise ConfigError('site settings are invalid') from exc


def public_site(installation):
    """Public-before-login fields only. No UUID, namespace or user directory."""
    root = _root(installation)
    data = read_site(root)
    identity = read_identity(root)
    inherited = identity['name'] if identity['identity_status'] == 'assigned' and identity['name'] != identity['id'] else None
    # A null name lets the browser localize a neutral unconfigured label.
    return dict(data, site_name=data['site_name'] or inherited)


def _atomic(path, data):
    _regular(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.opsfeast-site-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def save_site(installation, data, *, expected_revision):
    """Replace settings with revision checking; never change UUID/name/namespace."""
    root = _root(installation)
    candidate = validate_site(data)
    if type(expected_revision) is not int or expected_revision < 0:
        raise ConfigError('expected_revision must be a nonnegative integer')
    if candidate['revision'] != expected_revision:
        raise ConfigError('candidate revision must match expected_revision')
    path = _regular(root / FILENAME)
    with _locked(path):
        current = read_site(root)
        if current['revision'] != expected_revision:
            raise SiteConflict('site settings changed; reload before saving')
        for key in ('logo', 'avatar'):
            if candidate[key] is not None:
                asset = _regular(_assets(root) / candidate[key])
                if not asset.is_file():
                    raise ConfigError('selected site asset is unavailable')
        candidate['revision'] = expected_revision + 1
        _atomic(path, (json.dumps(candidate, ensure_ascii=False, indent=2) + '\n').encode())
    return candidate


def upload_image(installation, payload):
    """Validate PNG/JPEG, flatten frames, strip metadata and save immutable PNG."""
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError:
        raise ConfigError('Pillow from requirements-web.txt is required for image ingestion') from None
    import warnings
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_UPLOAD:
        raise ConfigError('image must contain 1 byte to 2 MiB')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(payload)) as source:
                if source.format not in ('PNG', 'JPEG'):
                    raise ConfigError('only PNG and JPEG images are supported')
                if source.width > 4096 or source.height > 4096 or source.width * source.height > 16_000_000:
                    raise ConfigError('image dimensions exceed the supported limit')
                source.load()
                normalized = ImageOps.exif_transpose(source).convert('RGBA')
                normalized.thumbnail((1024, 1024))
                clean = Image.new('RGBA', normalized.size)
                clean.paste(normalized)
                output = io.BytesIO()
                clean.save(output, format='PNG')
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ConfigError('invalid image data') from exc
    content = output.getvalue()
    asset_id = hashlib.sha256(content).hexdigest() + '.png'
    directory = _assets(_root(installation), create=True)
    _atomic(directory / asset_id, content)
    return {'asset_id': asset_id, 'width': clean.width, 'height': clean.height}


def image_path(installation, asset_id):
    """Only currently referenced assets are published before login."""
    root = _root(installation)
    if not ASSET_ID.fullmatch(asset_id) or asset_id not in (read_site(root)['logo'], read_site(root)['avatar']):
        raise ConfigError('site asset is not published')
    path = _regular(_assets(root) / asset_id)
    if not path.is_file():
        raise ConfigError('site asset is unavailable')
    return path
