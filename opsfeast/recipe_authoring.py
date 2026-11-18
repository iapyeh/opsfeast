"""Unified descriptor authoring and inert content reads; no candidate execution."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from zoneinfo import ZoneInfo

from . import ConfigError, Validator, plain_values, read_yaml
from .core import Instance
from .identity import _locked
from .site import SiteConflict, _atomic

VERSION = '0.1.0'
MAX_BYTES = 1024 * 1024
RUNNABLE = {'valid-python-session', 'valid-python-report', 'valid-python-recipe',
            'valid-python-workflow', 'valid-inventory-system', 'valid-python-routines', 'valid-recipe-meal'}


def new_definition(reference, *, title='', description=''):
    """One ordinary descriptor, with empty optional content and no runner."""
    return {'descriptor_version': '0.3.0', 'id': reference.split('/')[-1].lstrip(':'),
            'version': '', 'title': title, 'description': description, 'runner': {},
            'inputs': {'variables': {}}, 'output': {}, 'resources': {}}


def validate(metadata):
    if not isinstance(metadata, dict):
        raise ConfigError('recipe definition must be a mapping')
    plain_values(metadata, 'recipe definition')
    from .recipe_launch import describe as launch
    launch(metadata)
    if 'draft' in metadata or 'lifecycle' in metadata:
        raise ConfigError('obsolete recipe draft fields; use an ordinary descriptor')
    if metadata.get('descriptor_version', '') not in ('', '0.3.0'):
        raise ConfigError('unsupported recipe descriptor version')
    for key in ('id', 'title', 'description', 'version'):
        if not isinstance(metadata.get(key, ''), str):
            raise ConfigError('recipe text fields must be strings, including empty strings')
    if metadata.get('runner') is not None and not isinstance(metadata['runner'], dict):
        raise ConfigError('recipe runner must be a mapping or null')
    if 'runner' in metadata and metadata['runner'] is None:
        raise ConfigError('use an empty runner mapping for an unconfigured entrypoint')
    resources = metadata.get('resources', {})
    if not isinstance(resources, dict) or len(resources) > 50:
        raise ConfigError('recipe resources must contain at most 50 text entries')
    for name, content in resources.items():
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', name) or any(p in ('', '.', '..') for p in name.split('/')) or PurePosixPath(name).is_absolute():
            raise ConfigError('recipe resource names must be safe relative paths')
        if not isinstance(content, str) or '\x00' in content:
            raise ConfigError('recipe resources must be text without NUL')
    titles=metadata.get('resource_titles',{})
    if not isinstance(titles,dict) or set(titles)-set(resources) or any(not isinstance(value,str) or not value.strip() or len(value)>120 or any(ord(c)<32 for c in value) for value in titles.values()):
        raise ConfigError('resource_titles must label existing resources with nonempty single-line text up to 120 characters')
    authoring = metadata.get('authoring')
    if authoring is not None:
        if not isinstance(authoring, dict) or set(authoring) != {'schema_version', 'change_number', 'updated_at', 'summary'}:
            raise ConfigError('invalid recipe authoring metadata')
        if authoring['schema_version'] != VERSION or type(authoring['change_number']) is not int or authoring['change_number'] < 1 or not isinstance(authoring['summary'], str):
            raise ConfigError('invalid recipe authoring version/change number/summary')
        try:
            if datetime.fromisoformat(authoring['updated_at']).tzinfo is None:
                raise ValueError('timezone required')
        except (TypeError, ValueError):
            raise ConfigError('invalid recipe authoring update time') from None
    if len((json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode()) > MAX_BYTES:
        raise ConfigError('recipe definition exceeds 1 MiB')
    return metadata


def _path(selected, reference, *, create=False):
    from recipe_settings import reference as normalized
    if normalized(reference) != reference:
        raise ConfigError('exact recipe reference required')
    if create and not re.fullmatch(r':[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*', reference):
        raise ConfigError('authoring requires a Profile recipe reference beginning with :')
    if create and (selected.root/'recipes').is_symlink():
        raise ConfigError('Profile recipes directory must not be a symlink')
    config = Validator(selected.root); config.load(selected.root/'hosts.yaml')
    info = config.recipe_location(reference, selected.root/'hosts.yaml', cli=True, check_exists=False)
    if not info['enabled']:
        raise ConfigError('recipe source is disabled')
    base = info['root']; directory = base/info['pattern']
    current = base
    if base.is_symlink():
        raise ConfigError('recipe source must not be a symlink')
    for part in Path(info['pattern']).parts:
        current = current/part
        if part in ('..', '.') or current.is_symlink() or (current.exists() and not current.is_dir()):
            raise ConfigError('recipe path must contain only real directories')
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    path = directory/'recipe.yaml'
    if not path.resolve().is_relative_to(base.resolve()) or path.is_symlink() or (path.exists() and not path.is_file()):
        raise ConfigError('recipe descriptor must be a regular file inside its source')
    return path


def _read(path):
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ConfigError('recipe definition is missing or exceeds 1 MiB')
    raw = path.read_bytes(); metadata = read_yaml(path)
    if path.read_bytes() != raw:
        raise SiteConflict('recipe definition changed while reading; reload')
    validate(metadata)
    return metadata, hashlib.sha256(raw).hexdigest()


def inspect(selected, reference):
    path = _path(selected, reference); metadata, revision = _read(path)
    from recipe_inspection import inspect_one
    report = inspect_one(path.parent, [], metadata=metadata)
    runnable = report['status'] == 'success' and report['runner_contract'] in RUNNABLE
    fields = [name for name in ('id', 'title', 'description', 'version') if not metadata.get(name)]
    if not (metadata.get('runner') or {}).get('entrypoint') and metadata.get('id') != 'inventory-system':
        fields.append('runner.entrypoint')
    authoring = metadata.get('authoring') or {}
    result = {'schema_version': VERSION, 'profile': selected.name, 'reference': reference,
              'revision': revision, 'change_number': authoring.get('change_number', 0),
              'updated_at': authoring.get('updated_at'), 'summary': authoring.get('summary', ''),
              'definition': metadata, 'title': metadata.get('title', ''),
              'description': metadata.get('description', ''), 'version': metadata.get('version', ''),
              'runner': metadata.get('runner') or {}, 'resources': metadata.get('resources', {}),
              'resource_titles': metadata.get('resource_titles', {}),
              'runnable': runnable, 'missing_fields': fields, 'errors': report['errors']}
    from .recipe_launch import describe as launch
    result['launch'] = launch(metadata)
    result['web_runnable'] = runnable and result['launch']['mode'] == 'direct'
    from .recipe_structure import describe
    result.update(describe(path.parent,metadata,report,runnable=runnable))
    from .recipe_menu import display_title
    result['title'] = display_title(reference, result['title'])
    result['view_revision'] = hashlib.sha256(json.dumps([revision,runnable,fields,report['errors'],result['components'],result['execution_blockers']],sort_keys=True).encode()).hexdigest()
    return result


def save(selected, reference, *, expected_revision, definition, summary=''):
    """Replace a Profile descriptor only; resources are inert, real scripts stay put."""
    if expected_revision is not None and (not isinstance(expected_revision, str) or not re.fullmatch('[0-9a-f]{64}', expected_revision)):
        raise ConfigError('expected_revision must be null for creation or the current content digest')
    if not isinstance(summary, str):
        raise ConfigError('summary must be text')
    candidate = deepcopy(validate(definition))
    from recipe_identity import validate as validate_identity
    validate_identity(candidate, external=True)
    path = _path(selected, reference, create=True)
    with _locked(path):
        if path.exists():
            current, revision = _read(path)
            if revision != expected_revision:
                raise SiteConflict('recipe changed; read and reconcile the current definition')
        else:
            current = {}
            if expected_revision is not None:
                raise SiteConflict('recipe does not exist; expected_revision must be null to create')
        candidate['authoring'] = {'schema_version': VERSION,
            'change_number': (current.get('authoring') or {}).get('change_number', 0) + 1,
            'updated_at': datetime.now(ZoneInfo('Asia/Taipei')).isoformat(timespec='seconds'), 'summary': summary}
        validate(candidate)
        if path.exists():
            backups = selected.root/'.recipe-authoring-backups'
            if backups.is_symlink() or (backups.exists() and not backups.is_dir()):
                raise ConfigError('recipe authoring backup directory must be a real directory')
            backups.mkdir(mode=0o700, exist_ok=True)
            _atomic(backups/(revision+'.yaml'), path.read_bytes())
            if _read(path)[1] != revision:
                raise SiteConflict('recipe changed while saving; reload')
        _atomic(path, (json.dumps(candidate, ensure_ascii=False, indent=2) + '\n').encode())
    return inspect(selected, reference)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product', type=Path, default=Path.cwd())
    parser.add_argument('--profile', required=True)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--snapshot', type=Path, help='JSON: expected_revision, definition, summary; omit to read')
    args = parser.parse_args()
    try:
        selected = Instance.open(args.product).profile(args.profile)
        if args.snapshot:
            if args.snapshot.stat().st_size > MAX_BYTES:
                raise ConfigError('snapshot exceeds 1 MiB')
            result = save(selected, args.reference, **json.loads(args.snapshot.read_text()))
        else:
            result = inspect(selected, args.reference)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ConfigError, OSError, ValueError, TypeError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
