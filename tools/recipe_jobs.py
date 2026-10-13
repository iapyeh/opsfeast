"""Saved invocation definitions for ordinary reruns; no scheduler or implicit approval."""
import hashlib
import json
from pathlib import Path
import re

from opsfeast import ConfigError
from recipe_catalog import choose
from recipe_inputs import json_object
from recipe_reports import safe_directory

VERSION = '0.1.0'


def job_path(root, name, create=False):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', name):
        raise ConfigError('job name must be a simple name')
    directory = safe_directory(root, 'jobs', create=create)
    path = directory / (name + '.json')
    if path.is_symlink():
        raise ConfigError('job cannot be a symlink')
    return path


def fingerprint(item):
    directory = Path(item['directory'])
    digest = hashlib.sha256()
    for path in sorted(directory.rglob('*')):
        if '__pycache__' in path.parts:
            continue
        if path.is_symlink():
            raise ConfigError('job recipe cannot contain symlinks')
        if path.is_file():
            digest.update(path.relative_to(directory).as_posix().encode() + b'\0')
            digest.update(path.read_bytes())
    return {'descriptor_sha256': hashlib.sha256((directory / 'recipe.yaml').read_bytes()).hexdigest(),
            'content_sha256': digest.hexdigest()}


def save(root, name, specification):
    item = choose(root, specification['recipe'])
    if not item['runnable']:
        raise ConfigError('job recipe is not statically runnable')
    from recipe_cli import validate_invocation
    validate_invocation(root, item, specification['invocation'])
    path = job_path(root, name, create=True)
    if path.exists():
        raise ConfigError('job already exists; preserve and explicitly revise it outside this command')
    document = {'job_version': VERSION, 'name': name, 'recipe': item['reference'],
                'recipe_id': item['id'], 'recipe_version': item['version'], 'recipe_fingerprint': fingerprint(item),
                'invocation': specification['invocation']}
    # Exclusive creation preserves another writer's definition even after the
    # earlier existence check. Readers reject incomplete JSON during a write.
    with path.open('x', encoding='utf-8') as output:
        json.dump(document, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write('\n')
    return document


def load(root, name, verify=True):
    document = json_object(job_path(root, name))
    if document.get('job_version') != VERSION or document.get('name') != name or not isinstance(document.get('invocation'), dict):
        raise ConfigError('invalid job definition')
    if verify:
        item = choose(root, document.get('recipe'))
        if not item['runnable'] or fingerprint(item) != document.get('recipe_fingerprint'):
            raise ConfigError('job recipe changed; review and save a new job definition')
    return document


def listing(root):
    directory = safe_directory(root, 'jobs')
    return sorted(path.stem for path in directory.glob('*.json')) if directory.exists() else []
