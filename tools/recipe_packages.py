"""Explicit-file single-recipe ZIP bundles; unpack only to new review candidates."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile
import yaml

from opsfeast import ConfigError, plain_values, UniqueLoader
from recipe_inputs import parse_json_object

VERSION = '0.1.0'
MAX_BYTES = 25 * 1024 * 1024
MAX_FILES = 2000
PRIVATE_NAMES = {'hosts.yaml', 'feast.yaml', 'my-ops.yaml', 'AGENTS.local.md', 'AGENTS.override.md'}
PRIVATE_DIRS = {'observations', 'reports', 'records', 'retention', 'vault', 'runs', 'jobs', '.git', '.venv', '__pycache__'}


def payload_name(name):
    path = PurePosixPath(name)
    if (not isinstance(name, str) or not name or '\\' in name or path.is_absolute() or
            any(part in ('', '.', '..') for part in name.split('/')) or ':' in name):
        raise ConfigError('bundle payload paths must be normalized relative paths')
    if path.name in PRIVATE_NAMES or any(part in PRIVATE_DIRS or part.startswith('.') for part in path.parts):
        raise ConfigError('bundle cannot include private settings, operational storage or hidden files')
    return path


def descriptor_consistency(payloads, identifier, version):
    if not {'recipe.yaml', 'README.md'}.issubset(payloads):
        raise ConfigError('bundle must include descriptor and README')
    try:
        metadata = yaml.load(payloads['recipe.yaml'], Loader=UniqueLoader)
        plain_values(metadata, 'bundle descriptor')
        if not isinstance(metadata, dict) or metadata.get('id') != identifier or metadata.get('version') != version:
            raise ConfigError('bundle identity/version differs from descriptor')
        runner = metadata.get('runner')
        if isinstance(runner, dict):
            names = [runner.get('entrypoint')]
        else:
            names = [item.get('entrypoint') for item in metadata.get('implementations', []) if isinstance(item, dict)]
        if not names or any(not isinstance(name, str) or name not in payloads for name in names):
            raise ConfigError('bundle must include declared entrypoints')
    except (yaml.YAMLError, TypeError, RecursionError):
        raise ConfigError('invalid bundle descriptor') from None


def pack(item, files, destination):
    directory = Path(item['directory']).resolve()
    if not files:
        raise ConfigError('pack requires an explicit --file allowlist')
    payloads = {}
    for name in files:
        relative = payload_name(name)
        if name in payloads:
            raise ConfigError('duplicate pack file')
        path = directory / str(relative)
        if any(part.is_symlink() for part in [path, *path.parents] if part.is_relative_to(directory)):
            raise ConfigError('pack refuses symlinks')
        if not path.resolve().is_relative_to(directory) or not path.is_file():
            raise ConfigError('pack file is missing or outside recipe')
        payloads[name] = path.read_bytes()
    entry = item['descriptor'].get('runner', {}).get('entrypoint')
    required = {'recipe.yaml', 'README.md'} | ({entry} if entry else {e['entrypoint'] for e in item['descriptor'].get('implementations', [])})
    if not required.issubset(payloads):
        raise ConfigError('allowlist must include descriptor, README and declared entrypoints')
    descriptor_consistency(payloads, item['id'], item['version'])
    from recipe_identity import validate as validate_identity
    identity = validate_identity(yaml.load(payloads['recipe.yaml'], Loader=UniqueLoader), directory)
    if identity != validate_identity(item['descriptor'], directory):
        raise ConfigError('recipe attribution changed since catalog inspection')
    if identity['license'] == 'MIT' and 'LICENSE' not in payloads:
        raise ConfigError('MIT bundles must include LICENSE in their explicit allowlist')
    if len(payloads) > MAX_FILES or sum(map(len, payloads.values())) > MAX_BYTES:
        raise ConfigError('recipe bundle exceeds size/file limits')
    manifest = {'format': 'opsfeast-recipe-bundle', 'version': VERSION,
                'recipe_id': item['id'], 'recipe_version': item['version'],
                'source_reference': item['reference'], 'license': identity['license'], 'author': identity['author'],
                'files': {name: {'sha256': hashlib.sha256(content).hexdigest(), 'size_bytes': len(content)} for name, content in payloads.items()}}
    destination = destination.expanduser()
    if destination.exists() or destination.is_symlink():
        raise ConfigError('pack destination must not exist')
    created = False
    try:
        output = destination.open('xb')
        created = True
        with output, zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
            for name, content in sorted(payloads.items()):
                archive.writestr('recipe/' + name, content)
    except Exception:
        if created and destination.exists(): destination.unlink()
        raise
    return {'bundle_version': VERSION, 'path': str(destination.resolve()), 'files': sorted(payloads),
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'publisher_authentication': 'not-established'}


def unpack(archive_path, destination):
    destination = destination.expanduser()
    if destination.exists() or destination.is_symlink():
        raise ConfigError('candidate destination must not exist')
    try:
        with zipfile.ZipFile(archive_path.expanduser()) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)) or len(names) > MAX_FILES + 1 or sum(entry.file_size for entry in entries) > MAX_BYTES:
                raise ConfigError('bundle has duplicates or exceeds size/file limits')
            if 'MANIFEST.json' not in names:
                raise ConfigError('bundle manifest is missing')
            for entry in entries:
                mode = entry.external_attr >> 16
                if entry.is_dir() or stat.S_ISLNK(mode) or mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    raise ConfigError('bundle entries must be ordinary files')
                if entry.flag_bits & 1:
                    raise ConfigError('encrypted bundle entries are unsupported')
                if entry.filename != 'MANIFEST.json':
                    if not entry.filename.startswith('recipe/'):
                        raise ConfigError('unexpected bundle file')
                    payload_name(entry.filename[len('recipe/'):])
            manifest = parse_json_object(archive.read('MANIFEST.json'))
            if manifest.get('format') != 'opsfeast-recipe-bundle' or manifest.get('version') != VERSION or not isinstance(manifest.get('files'), dict):
                raise ConfigError('unsupported recipe bundle manifest')
            expected = {'MANIFEST.json'} | {'recipe/' + name for name in manifest['files']}
            if set(names) != expected:
                raise ConfigError('bundle payload differs from manifest file set')
            payloads = {}
            for name, evidence in manifest['files'].items():
                payload_name(name)
                content = archive.read('recipe/' + name)
                if not isinstance(evidence, dict) or len(content) != evidence.get('size_bytes') or hashlib.sha256(content).hexdigest() != evidence.get('sha256'):
                    raise ConfigError('bundle payload digest/size mismatch')
                payloads[name] = content
            descriptor_consistency(payloads, manifest.get('recipe_id'), manifest.get('recipe_version'))
            from recipe_identity import validate as validate_identity
            from opsfeast import UniqueLoader
            descriptor = yaml.load(payloads['recipe.yaml'], Loader=UniqueLoader)
            identity = validate_identity(descriptor, external=True)
            if 'author' in manifest and manifest['author'] != identity['author']:
                raise ConfigError('bundle author differs from descriptor')
            if manifest.get('license', 'Unknown') not in (identity['license'], 'not-declared'):
                raise ConfigError('bundle license differs from descriptor')
    except (zipfile.BadZipFile, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ConfigError('invalid recipe bundle') from None
    destination.mkdir(parents=True)
    try:
        for name, content in payloads.items():
            path = destination / 'recipe' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        (destination / 'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    except Exception:
        shutil.rmtree(destination)
        raise
    return {'candidate_directory': str(destination.resolve()), 'recipe_directory': str((destination / 'recipe').resolve()),
            'recipe_id': manifest.get('recipe_id'), 'recipe_version': manifest.get('recipe_version'),
            'publisher_authentication': 'not-established', 'activation': 'not-installed; review before registration/execution'}
