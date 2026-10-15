#!/usr/bin/env python3
"""Manage OpsFeast profiles, inspect configuration and explicitly test connections."""
from __future__ import annotations

import argparse
import copy
import fnmatch
import getpass
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import traceback
import unicodedata

try:
    import yaml
except ImportError:
    raise SystemExit('PyYAML is required. Install it with this Python: python -m pip install PyYAML')


class ConfigError(ValueError):
    pass


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if not (REPOSITORY_ROOT / 'tools' / 'opsfeast.py').is_file():
    from importlib.resources import files
    REPOSITORY_ROOT = Path(str(files('_opsfeast_data')))
# Transitional private tool imports; callers only import the public package.
_tools = str(REPOSITORY_ROOT / 'tools')
if Path(_tools).is_dir() and _tools not in sys.path:
    sys.path.append(_tools)
REPOSITORY_RECIPES = REPOSITORY_ROOT / 'recipes'
INSTANCE_DEFINITION = 'feast.yaml'
INSTANCE_SCHEMA = {'schema_version': 1, 'kind': 'opsfeast'}
DEFAULT_HOST_ICON = '🍎'
LEGACY_INSTANCE_DEFINITION = 'my-ops.yaml'
LEGACY_INSTANCE_SCHEMA = {'schema_version': 1, 'kind': 'sshscript-ops'}


def exclusive_path(root, current, legacy, label):
    """Use one naming generation; never silently choose between two files."""
    current_path, legacy_path = root / current, root / legacy
    current_present = current_path.exists() or current_path.is_symlink()
    legacy_present = legacy_path.exists() or legacy_path.is_symlink()
    if current_present and legacy_present:
        raise ConfigError(f'conflicting {label}: {current_path} and {legacy_path}; keep one after reviewing both')
    return legacy_path if legacy_present else current_path


def registry_path(installation=None):
    return exclusive_path(Path(installation) if installation is not None else REPOSITORY_ROOT, '.opsfeast.yaml', '.my-ops.yaml', 'profile registries')


def definition_path(root):
    return exclusive_path(root, INSTANCE_DEFINITION, LEGACY_INSTANCE_DEFINITION, 'Feast definitions')


def instance_definition(root):
    path = definition_path(root)
    if path.is_symlink():
        raise ConfigError(f'refuses scaffold symlink: {path}')
    expected = LEGACY_INSTANCE_SCHEMA if path.name == LEGACY_INSTANCE_DEFINITION else INSTANCE_SCHEMA
    data = mapping(read_yaml(path), str(path), expected)
    if type(data.get('schema_version')) is not int or data != expected:
        raise ConfigError(f'{path}: unsupported management directory definition')


def profile_name(value):
    string(value, 'profile name')
    if (value in ('.', '..') or value != value.strip() or '/' in value or '\\' in value or
            any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ConfigError('profile name cannot contain path separators, control characters or surrounding whitespace, or be . or ..')
    return value


def profile_root(location, installation=None):
    path = Path(location).expanduser()
    return (path if path.is_absolute() else (Path(installation) if installation is not None else REPOSITORY_ROOT) / path).resolve()


def load_profiles(installation=None):
    pointer = registry_path(installation)
    if not pointer.exists() and not pointer.is_symlink():
        return {'schema_version': 2, 'default_profile': None, 'profiles': {}}
    if pointer.is_symlink() or not pointer.is_file():
        raise ConfigError(f'profile registry must be a regular file: {pointer}')
    data = mapping(read_yaml(pointer), str(pointer))
    version = data.get('schema_version')
    if type(version) is not int:
        raise ConfigError(f'{pointer}: unsupported locator version')
    if version == 1:
        mapping(data, str(pointer), ('schema_version', 'root'))
        location = string(data.get('root'), f'{pointer}: root')
        return {'schema_version': 2, 'default_profile': 'default',
                'profiles': {'default': {'root': location}}}
    if version != 2:
        raise ConfigError(f'{pointer}: unsupported locator version')
    mapping(data, str(pointer), ('schema_version', 'default_profile', 'profiles'))
    if 'default_profile' not in data:
        raise ConfigError('profile registry must contain default_profile')
    profiles = mapping(data.get('profiles'), f'{pointer}: profiles')
    paths = set()
    for name, item in profiles.items():
        profile_name(name)
        item = mapping(item, f'{pointer}: profile', ('root',))
        root = profile_root(string(item.get('root'), f'{pointer}: root'), installation)
        if root in paths:
            raise ConfigError('multiple profiles refer to the same management directory')
        paths.add(root)
    default = data.get('default_profile')
    if (profiles and (not isinstance(default, str) or default not in profiles)) or (not profiles and default is not None):
        raise ConfigError('default_profile must identify a registered profile')
    return data


def save_profiles(data, installation=None):
    pointer = registry_path(installation)
    if pointer.is_symlink() or (pointer.exists() and not pointer.is_file()):
        raise ConfigError(f'profile registry must be a regular file: {pointer}')
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=pointer.parent,
                                     prefix='.opsfeast-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=True)
            stream.close()
            os.replace(temporary, pointer)
        finally:
            temporary.unlink(missing_ok=True)


def registered_root(data, name, installation=None):
    if name not in data['profiles']:
        raise ConfigError(f'unknown profile: {name}')
    root = profile_root(data['profiles'][name]['root'], installation)
    if not root.is_dir():
        raise ConfigError(f'management directory not found: {root}')
    definition = definition_path(root)
    if definition.exists() or definition.is_symlink():
        instance_definition(root)
    entry = root / 'hosts.yaml'
    if not entry.is_file() or not entry.resolve().is_relative_to(root):
        raise ConfigError(f'management entry hosts.yaml missing or outside root: {root}')
    return root


def resolve_root(root=None, profile=None):
    if root is not None:
        if profile is not None:
            raise ConfigError('specify either a management directory or --profile, not both')
        root = Path(root).expanduser()
        definition = definition_path(root)
        if definition.exists() or definition.is_symlink():
            instance_definition(root)
        return root
    data = load_profiles()
    name = profile if profile is not None else data['default_profile']
    if name is None:
        raise ConfigError('no registered profiles; run opsfeast.py init or specify a directory')
    return registered_root(data, name)


def init_plan(argument=None, profile=None):
    if argument is None:
        name = 'main'
        root = REPOSITORY_ROOT / 'feasts' / name
    elif '/' in argument or '\\' in argument or Path(argument).is_absolute():
        root = Path(argument).expanduser()
    else:
        name = profile_name(argument)
        root = REPOSITORY_ROOT / 'feasts' / name
    if argument is None or not ('/' in argument or '\\' in argument or Path(argument).is_absolute()):
        registered = load_profiles()['profiles'].get(name)
        if registered is not None:
            root = profile_root(registered['root'])
    return registration_plan(root, profile)


def registration_plan(root, profile=None):
    data = load_profiles()
    root = root.expanduser().resolve()
    for existing, item in data['profiles'].items():
        if profile_root(item['root']) == root:
            if profile is not None and profile != existing:
                raise ConfigError(f'directory already registered as {existing}; its profile name is preserved')
            return root, existing, data
    name = profile_name(profile if profile is not None else root.name)
    suggestion = f'{root.parent.name}.{root.name}'
    while name in data['profiles']:
        message = f'profile {name} already refers to another directory; choose a name (suggestion: {suggestion})'
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ConfigError(message + '; pass --profile NAME')
        print(message)
        try:
            choice = input('New profile name (Enter to cancel): ').strip()
        except (EOFError, KeyboardInterrupt):
            raise ConfigError('registration cancelled') from None
        if not choice:
            raise ConfigError('registration cancelled')
        try:
            name = profile_name(choice)
        except ConfigError:
            print('Invalid profile name; try again.')
    return root, name, data


def register_profile(root, name, data):
    checkout = REPOSITORY_ROOT.resolve(strict=True)
    location = root.relative_to(checkout).as_posix() if root.is_relative_to(checkout) else str(root)
    data['profiles'][name] = {'root': location}
    if data['default_profile'] is None:
        data['default_profile'] = name
    save_profiles(data)


def list_profiles(data=None, numbered=False):
    data = load_profiles() if data is None else data
    if not data['profiles']:
        print('No registered profiles. Run opsfeast.py init or opsfeast.py attach <directory> first.')
        return
    print('PROFILE  ROOT  STATUS  DEFAULT')
    for index, (name, item) in enumerate(data['profiles'].items(), 1):
        prefix = f'{index}. ' if numbered else ''
        mark = (' [current default]' if numbered else ' *') if name == data['default_profile'] else ''
        root = profile_root(item['root'])
        status = 'available'
        try:
            registered_root(data, name)
        except ConfigError:
            try:
                root.stat()
                status = 'invalid'
            except FileNotFoundError:
                status = 'missing'
            except OSError:
                status = 'unavailable'
        except OSError:
            status = 'unavailable'
        print(f"{prefix}{name}  {root}  {status}{mark}")


def detach_profile(name):
    name = profile_name(name)
    if name == 'main':
        raise ConfigError('main is a reserved profile and cannot be detached')
    data = load_profiles()
    if name not in data['profiles']:
        raise ConfigError(f'unknown profile: {name}')
    root = profile_root(data['profiles'][name]['root'])
    was_default = data['default_profile'] == name
    if was_default:
        if 'main' not in data['profiles']:
            raise ConfigError('cannot detach the default profile: main is not registered; use another profile first')
        registered_root(data, 'main')
        data['default_profile'] = 'main'
    del data['profiles'][name]
    save_profiles(data)
    print(f'Detached profile: {name}  {root}')
    print(f'Default profile: {data["default_profile"]}')
    print('Management directory and its contents preserved; no connection or recipe execution performed.')
    return 0


def set_default_profile(name):
    data = load_profiles()
    registered_root(data, name)
    data['default_profile'] = name
    save_profiles(data)
    return name


def use_profile(name=None):
    data = load_profiles()
    if not data['profiles']:
        list_profiles(data)
        return 1
    if name is None:
        list_profiles(data, numbered=True)
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            print('Select explicitly with opsfeast.py use <profile>.')
            return 1
        names = list(data['profiles'])
        while True:
            try:
                selection = input('Enter number or profile name (Enter to cancel): ').strip()
            except (EOFError, KeyboardInterrupt):
                print('Cancelled.')
                return 0
            if not selection:
                print('Cancelled.')
                return 0
            if selection in data['profiles']:
                name = selection
                break
            if selection.isdecimal() and 1 <= int(selection) <= len(names):
                name = names[int(selection) - 1]
                break
            print('Invalid selection; choose a listed number or profile name.')
    set_default_profile(name)
    print(f'Default profile: {name}')
    return 0


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys and YAML merge keys rather than silently overriding."""


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        if key_node.tag == 'tag:yaml.org,2002:merge':
            raise ConfigError('YAML merge keys (<<) are not supported')
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ConfigError(f'mapping keys must be strings (line {key_node.start_mark.line + 1})')
        if key in result:
            raise ConfigError(f'duplicate YAML key (line {key_node.start_mark.line + 1})')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def read_yaml(path):
    try:
        return yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        # Parser snippets may contain passwords; report location without the input.
        mark = getattr(exc, 'problem_mark', None)
        location = f' line {mark.line + 1}, column {mark.column + 1}' if mark else ''
        raise ConfigError(f'{path}:{location} invalid YAML or unsupported tag') from None
    except (OSError, UnicodeError, ConfigError) as exc:
        raise ConfigError(f'{path}: {exc}') from None


def mapping(value, where, allowed=None):
    if not isinstance(value, dict):
        raise ConfigError(f'{where}: expected a mapping')
    if allowed is not None and set(value) - set(allowed):
        raise ConfigError(f'{where}: unsupported fields')
    return value


def string(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f'{where}: expected a non-empty string')
    return value


def group_names(value, where):
    """Validate membership without rewriting the user's scalar/list representation."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise ConfigError(f'{where}: expected a string or list of strings')
    for name in value:
        string(name, where + ': group name')
    return value


def plain_values(value, where, active=None):
    """Keep vars JSON-like; reject dates, binary values, and recursive YAML aliases."""
    active = set() if active is None else active
    if isinstance(value, (list, dict)):
        if id(value) in active:
            raise ConfigError(f'{where}: recursive YAML alias')
        active.add(id(value))
        if isinstance(value, dict):
            for item in value.values():
                plain_values(item, where, active)
        else:
            for item in value:
                plain_values(item, where, active)
        active.remove(id(value))
    elif type(value) is float and not math.isfinite(value):
        raise ConfigError(f'{where}: non-finite numbers are not supported')
    elif value is not None and type(value) not in (str, int, float, bool):
        raise ConfigError(f'{where}: unsupported YAML value type; quote date-like strings')


class Validator:
    def __init__(self, root):
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise ConfigError('management root must be a directory')
        self.hosts = {}
        self.sources = {}
        self.documents = {}
        self.loaded = set()
        self.active = []
        self.edges = {}
        self.selected = {}
        self.recipe_sources = {}
        self.default_recipe_sources = {name: {'enabled': True, 'vars': {}} for name in ('bundle', 'profile')}
        self.recipe_entries = {}
        self.recipe_skips = {}
        self.execution_recipe = None
        self.notes = []

    def inside(self, path):
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise ConfigError(f'path outside management root: {path}')
        return resolved

    def path(self, text, source):
        string(text, f'{source}: path')
        if '://' in text:
            raise ConfigError(f'{source}: remote URLs are not supported')
        path = Path(text)
        return self.inside(path if path.is_absolute() else source.parent / path)

    def recipe_location(self, text, source, cli=False, check_exists=True):
        """Resolve one source explicitly; never fall back to another source."""
        string(text, f'{source}: recipe path')
        if '://' in text:
            raise ConfigError('remote recipe URLs are not supported')
        path = Path(text)
        info = {'name': 'repository', 'root': REPOSITORY_RECIPES, 'reference': text,
                **self.default_recipe_sources['bundle']}
        if ':' in text and not path.is_absolute() and not text.startswith(('./', '../')):
            name, relative = text.split(':', 1)
            if not relative or Path(relative).is_absolute() or relative.startswith('~'):
                raise ConfigError('source-qualified recipe requires a nonempty relative path')
            if name:
                if name not in self.recipe_sources:
                    raise ConfigError(f'unknown recipe source: {name}')
                info.update(self.recipe_sources[name], name=name)
            else:
                info.update(self.default_recipe_sources['profile'], name='profile', root=self.root / 'recipes')
            pattern = relative
        elif text == 'recipes' or text.startswith('recipes/'):
            if cli:
                raise ConfigError('omit the recipes/ prefix from --recipe; use inventory/system')
            pattern = text[len('recipes'):].lstrip('/') or '.'
        elif path.is_absolute() and path.is_relative_to(REPOSITORY_RECIPES):
            pattern = text
        elif path.is_absolute() or text.startswith(('./', '../')):
            info.update(self.default_recipe_sources['profile'], name='profile', root=self.root)
            self.path(text, source)  # Check containment even when this source is disabled.
            info['scope'] = self
            info['pattern'], info['origin'] = text, source
            return info
        else:
            pattern = text
        # Validate relative containment even for a disabled/missing source,
        # without requiring the source to exist or opening recipe files.
        root = Path(info['root']).resolve()
        candidate = Path(pattern)
        candidate = (candidate if candidate.is_absolute() else root / candidate).resolve()
        if not candidate.is_relative_to(root):
            raise ConfigError('recipe path outside its source root')
        info.update(root=root, pattern=pattern, origin=root / 'selection.yaml')
        info['scope'] = Validator(root) if info['enabled'] and check_exists else None
        return info

    def recipe_scope(self, text, source):
        info = self.recipe_location(text, source)
        if not info['enabled']:
            raise ConfigError('recipe source is disabled')
        return info['scope'], info['pattern'], info['origin']

    def recipe_inside(self, path):
        if path.is_relative_to(REPOSITORY_RECIPES):
            return Validator(REPOSITORY_RECIPES).inside(path)
        for item in self.recipe_sources.values():
            if item['enabled'] and path.is_relative_to(item['root']):
                return Validator(item['root']).inside(path)
        return self.inside(path)

    def load(self, path):
        path = self.inside(path)
        if path in self.active:
            raise ConfigError('include cycle: ' + ' -> '.join(map(str, self.active + [path])))
        if path in self.loaded:
            return
        entry = path == self.inside(self.root / 'hosts.yaml') and not self.active
        data = mapping(read_yaml(path), str(path), ('include', 'hosts', 'recipe_sources') if entry else ('include', 'hosts'))
        if entry:
            for name, settings in mapping(data.get('recipe_sources', {}), 'recipe_sources').items():
                if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', name) or name == 'repository':
                    raise ConfigError('recipe source names must be simple identifiers; repository is reserved')
                where = f'{path}: recipe_sources.{name}'
                if name in self.default_recipe_sources:
                    settings = mapping(settings, where, ('path', 'enabled', 'vars'))
                    if 'path' in settings:
                        text = string(settings['path'], where + '.path')
                        if '://' in text:
                            raise ConfigError(f'{where}.path: must be a local default recipe root')
                        supplied = Path(text).expanduser()
                        supplied = (supplied if supplied.is_absolute() else path.parent / supplied).resolve()
                        expected = (REPOSITORY_RECIPES if name == 'bundle' else self.root / 'recipes').resolve()
                        if supplied != expected:
                            raise ConfigError(f'{where}.path: must resolve to the default recipe root; register a separate source for another path')
                    enabled = settings.get('enabled', True)
                    if type(enabled) is not bool:
                        raise ConfigError(f'{where}.enabled: expected a boolean')
                    variables = mapping(settings.get('vars', {}), where + '.vars')
                    plain_values(variables, where + '.vars')
                    self.default_recipe_sources[name] = {'enabled': enabled, 'vars': variables}
                    continue
                settings = mapping(settings, where, ('path', 'enabled', 'vars'))
                text = string(settings.get('path'), where + '.path')
                if '://' in text:
                    raise ConfigError(f'{where}: source path must be local')
                enabled = settings.get('enabled', True)
                if type(enabled) is not bool:
                    raise ConfigError(f'{where}.enabled: expected a boolean')
                variables = mapping(settings.get('vars', {}), where + '.vars')
                plain_values(variables, where + '.vars')
                location = Path(text).expanduser()
                location = (location if location.is_absolute() else path.parent / location).resolve()
                self.recipe_sources[name] = {'root': location, 'enabled': enabled, 'vars': variables}
        self.documents[path] = data
        includes = data.get('include', [])
        if not isinstance(includes, list):
            raise ConfigError(f'{path}: include must be a list')
        self.active.append(path)
        for item in includes:
            string(item, f'{path}: include')
            if any(char in item for char in '*?['):
                raise ConfigError(f'{path}: include cannot contain glob patterns')
            self.load(self.path(item, path))
        hosts = mapping(data.get('hosts', {}), f'{path}: hosts')
        for host, config in hosts.items():
            string(host, f'{path}: host ID')
            if host in self.hosts:
                raise ConfigError(f'duplicate host {host}: {self.sources[host]} and {path}')
            if isinstance(config, dict) and 'groups' in config:
                raise ConfigError(f'{path}: {host}: groups has been renamed to group; use group: NAME or group: [NAME, ...]')
            host_config = dict(mapping(config, f'{path}: {host}', ('connection', 'enabled', 'group', 'users', 'vars', 'recipes', 'identity_key', 'label', 'description', 'icon')))
            icon = host_config.get('icon', DEFAULT_HOST_ICON)
            if not isinstance(icon, str) or len(icon) != 1 or not unicodedata.category(icon).startswith('S'):
                raise ConfigError(f'{path}: {host}.icon: expected exactly one Unicode Symbol code point')
            host_config['icon'] = icon
            self.hosts[host] = host_config
            self.sources[host] = path
        self.active.pop()
        self.loaded.add(path)

    def connection(self, value, where, active=None, reference=False):
        active = set() if active is None else active
        value = mapping(value, where)
        if id(value) in active:
            raise ConfigError(f'{where}: recursive connection alias')
        active.add(id(value))
        if 'local' in value:
            mapping(value, where, ('local',))
            if value['local'] is not True or reference:
                raise ConfigError(f'{where}: local must be true and cannot be used as a jump host')
            active.remove(id(value))
            return []
        if 'host' in value:
            if not reference or set(value) != {'host'}:
                raise ConfigError(f'{where}: host reference is only allowed alone under via')
            target = string(value['host'], where + '.host')
            if target not in self.hosts:
                raise ConfigError(f'{where}: unknown host reference {target}')
            target_connection = self.hosts[target].get('connection')
            if isinstance(target_connection, dict) and target_connection.get('local') is True:
                raise ConfigError(f'{where}: local host cannot be used as a jump host')
            active.remove(id(value))
            return [target]
        alias = 'ssh_config_alias' in value
        allowed = {'ssh_config_alias', 'via'} if alias else {'hostname', 'port', 'user', 'identity_file', 'via', 'proxy_command'}
        mapping(value, where, allowed)
        string(value.get('ssh_config_alias' if alias else 'hostname'), where)
        for field in ('user', 'identity_file', 'proxy_command'):
            if field in value:
                string(value[field], where + '.' + field)
        if 'proxy_command' in value and 'via' in value:
            raise ConfigError(f'{where}: proxy_command and via cannot be combined')
        if 'port' in value and (type(value['port']) is not int or not 1 <= value['port'] <= 65535):
            raise ConfigError(f'{where}: port must be an integer from 1 to 65535')
        if alias:
            self.notes.append(f'{where}: SSH config alias and jump conflicts require execution-time validation')
        result = self.connection(value['via'], where + '.via', active, True) if 'via' in value else []
        active.remove(id(value))
        return result

    def check_cycles(self):
        done, active = set(), []
        def visit(host):
            if host in active:
                start = active.index(host)
                chain = active[start:] + [host]
                sources = ', '.join(f'{h}: {self.sources[h]}' for h in dict.fromkeys(chain))
                raise ConfigError('via cycle: ' + ' -> '.join(chain) + f' ({sources})')
            if host in done:
                return
            active.append(host)
            for target in self.edges[host]:
                visit(target)
            active.pop()
            done.add(host)
        for host in self.hosts:
            visit(host)

    def child_dirs(self, parent):
        """Inspect boundaries before descending; do not follow directory symlinks."""
        for child in sorted(parent.iterdir()):
            checked = self.inside(child)
            if child.is_dir():
                yield child, checked

    def descendants(self, parent, recursive):
        for child, checked in self.child_dirs(parent):
            yield checked
            if recursive and not child.is_symlink():
                yield from self.descendants(checked, True)

    def glob_dirs(self, pattern, source):
        string(pattern, f'{source}: glob')
        if '://' in pattern:
            raise ConfigError(f'{source}: remote glob is not supported')
        path = Path(pattern)
        parts = path.parts
        first = next((i for i, part in enumerate(parts) if any(c in part for c in '*?[')), len(parts))
        if first == len(parts):
            candidate = self.path(pattern, source)
            return [candidate] if candidate.is_dir() else []
        if '..' in parts[first:]:
            raise ConfigError(f'{source}: glob cannot contain .. after a wildcard')
        prefix = Path(*parts[:first]) if first else Path('.')
        start = self.path(str(prefix), source)
        if not start.is_dir():
            raise ConfigError(f'{source}: glob search directory does not exist')
        def expand(parent, remaining, ancestry):
            if not remaining:
                yield parent
                return
            part, rest = remaining[0], remaining[1:]
            if part == '**':
                yield from expand(parent, rest, ancestry)
                for child, checked in self.child_dirs(parent):
                    if not child.is_symlink() and checked not in ancestry:
                        yield from expand(checked, remaining, ancestry | {checked})
            else:
                for child, checked in self.child_dirs(parent):
                    if fnmatch.fnmatchcase(child.name, part):
                        yield from expand(checked, rest, ancestry | {checked})
        return list(expand(start, parts[first:], {start}))

    def recipe_selector(self, selector, where):
        if isinstance(selector, str):
            selector = {'recipe': selector}
        selector = mapping(selector, where, ('recipe', 'directory', 'glob', 'recursive', 'vars'))
        kinds = set(selector) & {'recipe', 'directory', 'glob'}
        if len(kinds) != 1:
            raise ConfigError(f'{where}: specify exactly one of recipe, directory, glob')
        kind = next(iter(kinds))
        string(selector[kind], where)
        if 'recursive' in selector and (kind != 'directory' or type(selector['recursive']) is not bool):
            raise ConfigError(f'{where}: recursive is a boolean for directory only')
        variables = mapping(selector.get('vars', {}), where + '.vars')
        plain_values(variables, where + '.vars')
        return selector, kind

    def recipe_candidates(self, selector, kind, info):
        scope, pattern, source = info['scope'], info['pattern'], info['origin']
        if kind == 'glob':
            return scope.glob_dirs(pattern, source)
        directory = scope.path(pattern, source)
        if not directory.is_dir():
            raise ConfigError('recipe/directory does not exist')
        return [directory] if kind == 'recipe' else list(scope.descendants(directory, selector.get('recursive', False)))

    def recipes(self, host, config):
        source = self.sources[host]
        where = f'{source}: {host}.recipes'
        selectors = config.get('recipes', [])
        if not isinstance(selectors, list):
            raise ConfigError(f'{where}: expected a list')
        selected, ids, entries, skipped = [], {}, [], []
        host_enabled = config.get('enabled', True)
        for selector in selectors:
            selector, kind = self.recipe_selector(selector, where)
            info = self.recipe_location(selector[kind], source, check_exists=host_enabled)
            if not host_enabled or not info['enabled']:
                skipped.append({'reference': selector[kind], 'source': info['name'], 'status': 'skipped',
                                'reason_code': 'host_disabled' if not host_enabled else 'source_disabled'})
                continue
            scope = info['scope']
            candidates = self.recipe_candidates(selector, kind, info)
            matches = []
            for directory in candidates:
                descriptor = scope.inside(directory / 'recipe.yaml')
                if not descriptor.is_file():
                    if kind == 'recipe':
                        raise ConfigError(f'{where}: recipe.yaml missing: {directory}')
                    continue
                matches.append(directory)
            if not matches:
                raise ConfigError(f'{where}: selector matched no recipes')
            for directory in sorted(set(matches), key=lambda p: p.relative_to(scope.root).as_posix()):
                if directory in selected:
                    continue
                data = mapping(read_yaml(scope.inside(directory / 'recipe.yaml')), str(directory / 'recipe.yaml'))
                if 'id' in data:
                    recipe_id = string(data['id'], str(directory / 'recipe.yaml') + ': id')
                    qualified = (info['name'], recipe_id)
                    if qualified in ids and ids[qualified] != directory:
                        raise ConfigError(f'{where}: duplicate recipe ID {recipe_id} in source {info["name"]}')
                    ids[qualified] = directory
                selected.append(directory)
                entries.append(dict(info, directory=directory, host_vars=selector.get('vars', {})))
        self.selected[host], self.recipe_entries[host], self.recipe_skips[host] = selected, entries, skipped

    def matching_recipe_vars(self, host, directory, selected_info):
        # CLI selects one concrete directory. Do not validate/expand unrelated
        # host selections; the first matching selector supplies its vars.
        selectors = self.hosts[host].get('recipes', [])
        if not isinstance(selectors, list):
            return {}
        for raw in selectors:
            candidate = {'recipe': raw} if isinstance(raw, str) else raw
            if not isinstance(candidate, dict):
                continue
            kinds = set(candidate) & {'recipe', 'directory', 'glob'}
            if len(kinds) != 1:
                continue
            kind = next(iter(kinds))
            text = candidate[kind]
            if not isinstance(text, str):
                continue
            try:
                info = self.recipe_location(text, self.sources[host], check_exists=False)
                if info['name'] != selected_info['name'] or not info['enabled']:
                    continue
                scope = info['scope'] or Validator(info['root'])
                if kind == 'glob':
                    matches = directory in scope.glob_dirs(info['pattern'], info['origin'])
                else:
                    base = scope.path(info['pattern'], info['origin'])
                    matches = (directory == base if kind == 'recipe' else
                               directory != base and (directory.is_relative_to(base) if candidate.get('recursive') is True
                                                      else directory.parent == base))
            except (ConfigError, OSError):
                continue
            if matches:
                selector, _ = self.recipe_selector(candidate, f'{self.sources[host]}: {host}.recipes')
                return copy.deepcopy(selector.get('vars', {}))
        return {}

    def check_connections(self):
        identity_keys = set()
        for host, config in self.hosts.items():
            for name in ('label', 'description'):
                if name in config and (not isinstance(config[name], str) or '\x00' in config[name]):
                    raise ConfigError(f'host {host}: {name} must be a string')
            if 'identity_key' in config:
                key = string(config['identity_key'], f'host {host}: identity_key')
                if key != key.strip() or any(ord(char) < 32 for char in key):
                    raise ConfigError(f'host {host}: identity_key must not contain edge whitespace or control characters')
                if key in identity_keys:
                    raise ConfigError('duplicate identity_key within the resolved host configuration')
                identity_keys.add(key)
            where = f'{self.sources[host]}: {host}'
            if type(config.get('enabled', True)) is not bool:
                raise ConfigError(f'{where}.enabled: expected a boolean')
            self.edges[host] = self.connection(config.get('connection'), where + '.connection')
            group_names(config.get('group', []), where + '.group')
            if 'users' in config:
                users = mapping(config['users'], where + '.users')
                for user, account in users.items():
                    string(user, where + '.users: account name')
                    account_where = where + '.users.' + user
                    account = mapping(account, account_where, ('password', 'vars', 'sudo', 'sudo-password'))
                    if 'password' in account and not isinstance(account['password'], str):
                        raise ConfigError(f'{account_where}.password: expected a string')
                    if 'sudo' in account and type(account['sudo']) is not bool:
                        raise ConfigError(f'{account_where}.sudo: expected a boolean; use false to disable or true to enable')
                    if 'sudo-password' in account and account['sudo-password'] is not None and not isinstance(account['sudo-password'], str):
                        raise ConfigError(f'{account_where}.sudo-password: expected string or null')
                    if 'vars' in account:
                        mapping(account['vars'], account_where + '.vars')
                        plain_values(account['vars'], account_where + '.vars')
            if 'vars' in config:
                mapping(config['vars'], where + '.vars')
                plain_values(config['vars'], where + '.vars')
        self.check_cycles()
        return self

    def check(self):
        self.load(self.root / 'hosts.yaml')
        self.check_connections()
        for host, config in self.hosts.items():
            self.recipes(host, config)
        return self


TEMPLATE = '''# First host: read docs/first-host.md for minimal examples and test commands.
# host-01 / host.example below is synthetic and NOT ready to connect.
# Replace the example host ID and hostname before use.
# Bare recipe names select this checkout; :names select this profile's recipes/.
# Optional recipe_sources at this entrypoint registers external local roots.
# recipe_sources:
#   bundle: {enabled: true}  # Optional controls for checkout recipes; no path.
#   profile: {enabled: true}  # Optional controls for :profile recipes; no path.
#   community:
#     path: ~/Download/recipes
#     enabled: true
#     vars: {command_timeout_seconds: 15}
hosts:
  # Each host ID requires connection; icon defaults to 🍎 (one Unicode Symbol code point).
  # enabled, group, users, vars, recipes, identity_key, label and description are optional.
  # Available fields, for example:
  # host-01:
  #   connection:
  #     hostname: host.example  # Required hostname or IP address.
  #     port: 22  # Optional SSH port (1-65535).
  #     user: operator  # Optional SSH login user.
  #     # Password login: set users.operator.password below, not connection.password.
  #     identity_file: /path/to/id_rsa  # RSA key on the parent Session's host; omit for password login.
  #     # For a target reached via a jump host, the key file is on that jump host.
  #     # Paths are passed literally to pkey_path; prefer absolute paths.
  #     # For key login, users.operator.password may be omitted.
  #     # Optional proxy command, instead of via; use literal destination values:
  #     # proxy_command: "ssh -W host.example:22 jump-user@jump.example"
  #     # Alternatively, replace hostname/port/user/identity_file with:
  #     # ssh_config_alias: my-host  # Host alias from SSH config.
  #     via:  # Optional jump host; choose a reference or inline connection.
  #       host: jump-host-id  # Reference another host ID in this configuration.
  #     # Or use an inline connection under via (which may have its own via):
  #     # via:
  #     #   hostname: jump.example
  #     #   port: 22
  #     #   user: operator
  #   enabled: true  # Optional; false disables the host and its use as a jump host.
  #   group: web  # Optional; a string for one group or [web, production] for multiple.
  #   users:  # Optional account names, credentials and account-specific vars.
  #     operator:  # SSH login account selected by connection.user.
  #       password: example-login-password  # Optional string; omit for key auth.
  #       vars:
  #         workspace: /home/operator
  #     appuser:  # An account you may explicitly select for su.
  #       password: example-su-password
  #       vars:
  #         app_root: /srv/app
  #   vars:  # Optional host variables passed to recipes.
  #     sudo:
  #       user: root
  #       password: example-password
  #   recipes:  # Optional; select recipe directories from the checkout.
  #     - inventory/system
  #     # - recipe: community:inventory/system
  #     #   vars: {command_timeout_seconds: 15}
  #     # Use ./recipes/... for custom recipes inside this management directory.
  #     # Or select recipe directories with either of these entries:
  #     # - directory: recipes/inventory
  #     #   recursive: false  # Optional; only valid with directory.
  #     # - glob: recipes/inventory/*
  # See docs/hosts-yaml.md in the OpsFeast repository for details.
  localhost:
    connection:
      local: true  # Execute locally without SSH; no hostname is required.
    users: {}
    vars: {}
    recipes: []
  host-01:
    connection:
      hostname: host.example
    users: {}
    vars: {}
    recipes: []
# Optional split files, relative to this YAML:
# include:
#   - hosts/production.yaml
'''


def initialize(root, *, quiet=False):
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve(strict=True)
    # Preflight existing entries before writing anything inside the root.
    definition = definition_path(root)
    for name in ('hosts', 'observations', 'records', 'runs', 'hosts.yaml', INSTANCE_DEFINITION, LEGACY_INSTANCE_DEFINITION):
        item = root / name
        if item.is_symlink():
            raise ConfigError(f'init refuses scaffold symlink: {item}')
        if item.exists() and (not item.is_file() if name in ('hosts.yaml', INSTANCE_DEFINITION, LEGACY_INSTANCE_DEFINITION) else not item.is_dir()):
            raise ConfigError(f'wrong scaffold entry type: {item}')
    if definition.exists():
        instance_definition(root)
    for name in ('hosts', 'observations', 'records', 'runs'):
        (root / name).mkdir(exist_ok=True)
    path = root / 'hosts.yaml'
    if not path.exists():
        with path.open('x', encoding='utf-8') as handle:
            handle.write(TEMPLATE)
        if not quiet:
            print(f'Created {path}')
    else:
        if not quiet:
            print(f'Preserved {path}')
    if not definition.exists():
        with definition.open('x', encoding='utf-8') as handle:
            yaml.safe_dump(INSTANCE_SCHEMA, handle, sort_keys=False)
    return root


def load_session_class():
    try:
        from sshscript import Session
    except ImportError:
        raise ConfigError('test-connection requires SSHScript >=4.0.1 installed in this Python environment') from None
    return Session


def connection_plan(config, host, session_class, contexts=None):
    """Resolve every hop before connecting; credentials belong to each hop's host."""
    def expand(connection, owner, source, host_id):
        if host_id in config.hosts and not config.hosts[host_id].get('enabled', True):
            raise ConfigError(f'host is disabled and cannot participate in a connection: {host_id}')
        if 'host' in connection:
            target = connection['host']
            return expand(config.hosts[target]['connection'], config.hosts[target], config.sources[target], target)
        if connection.get('local') is True:
            return []
        hops = expand(connection['via'], {}, source, f'{host_id}.via') if 'via' in connection else []
        options = {}
        if 'identity_file' in connection:
            options['pkey_path'] = connection['identity_file']
        if 'proxy_command' in connection:
            options['proxyCommand'] = connection['proxy_command']
        alias = 'ssh_config_alias' in connection
        settings = session_class.resolve_connection(
            connection['ssh_config_alias' if alias else 'hostname'],
            username=connection.get('user'), port=connection.get('port'),
            ssh_config=None if alias else False, **options,
        )
        if hops and settings.get('proxyCommand'):
            raise ConfigError('SSH config proxy or proxy_command conflicts with YAML via')
        if settings.get('username') is None:
            settings['username'] = getpass.getuser()
        account = owner.get('users', {}).get(settings['username'], {})
        if 'password' in account:
            settings['password'] = account['password']
            # Select the supplied password rather than silently using another identity.
            if not settings.get('pkey_path') and not settings.get('key_filename'):
                settings.update(allow_agent=False, look_for_keys=False)
        hops.append(settings)
        if contexts is not None:
            contexts.append({'host': host_id, 'hostname': settings['hostname'],
                             'user': settings['username'], 'port': settings['port']})
        return hops

    return expand(config.hosts[host]['connection'], config.hosts[host], config.sources[host], host)


def connection_error(exc):
    """Expose actionable categories without echoing third-party exception text."""
    error = {'type': type(exc).__name__}
    message = str(exc).lower()
    if error['type'] == 'BadHostKeyException':
        error['reason'] = 'host_key_mismatch'
    elif error['type'] == 'AuthenticationException':
        error['reason'] = 'authentication_failed'
    elif isinstance(exc, TimeoutError):
        error['reason'] = 'timeout'
    elif error['type'] == 'gaierror':
        error['reason'] = 'name_resolution_failed'
    elif isinstance(exc, ConnectionRefusedError):
        error['reason'] = 'connection_refused'
    elif error['type'] == 'SSHException':
        if 'not found in known_hosts' in message:
            error['reason'] = 'unknown_host_key'
        elif 'error reading ssh protocol banner' in message:
            error['reason'] = 'ssh_banner_unavailable'
    return error


def diagnostic_traceback(exc):
    # Omit source lines, locals and exception text, which may contain credentials.
    print(f'Traceback (frames only): {type(exc).__name__}', file=sys.stderr)
    for frame, lineno in traceback.walk_tb(exc.__traceback__):
        print(f'  {frame.f_code.co_filename}:{lineno} in {frame.f_code.co_name}', file=sys.stderr)


def test_connection(root, host, timeout, verbose=False, debug=False, show_traceback=False, init_host=False):
    config = Validator(root)
    config.load(config.root / 'hosts.yaml')
    if host not in config.hosts:
        raise ConfigError(f'unknown host ID: {host}')
    config.check_connections()
    if init_host:
        from host_runtime import runtime_class
        session_class = runtime_class()
    else:
        session_class = load_session_class()
    report = {'host': host, 'connected': False, 'hops': [], 'commands': [], 'success': False}
    local = None
    current_hop = None
    stage = 'connection settings'
    def progress(message):
        from terminal_events import emit
        emit('stage', host=host, stage=message)
        if verbose or debug:
            print(message, file=sys.stderr)

    def trace(exc):
        if show_traceback:
            diagnostic_traceback(exc)

    try:
        contexts = []
        plan = connection_plan(config, host, session_class, contexts)
        local = session_class()
        session = local
        stage = 'connection'
        parent = 'localhost'
        for index, (settings, context) in enumerate(zip(plan, contexts), 1):
            current_hop = dict(context, hop=index, parent=parent, connected=False)
            if settings.get('pkey_path'):
                current_hop['key_source'] = parent
            report['hops'].append(current_hop)
            progress(f'[{index}/{len(plan)}] {parent} -> {context["host"]}: connecting')
            if debug:
                details = dict(current_hop, timeout=timeout,
                               proxy_command=bool(settings.get('proxyCommand')),
                               password_supplied='password' in settings,
                               identity_file=bool(settings.get('pkey_path')),
                               local_key_filename=bool(settings.get('key_filename')),
                               allow_agent=settings.get('allow_agent', True),
                               look_for_keys=settings.get('look_for_keys', True))
                print('DEBUG ' + json.dumps(details, ensure_ascii=False), file=sys.stderr)
            options = dict(settings)
            hostname = options.pop('hostname')
            session = session.connect(
                hostname, ssh_config=False, timeout=timeout,
                banner_timeout=timeout, auth_timeout=timeout, **options,
            )
            current_hop['connected'] = True
            progress(f'[{index}/{len(plan)}] {context["host"]}: connected')
            parent = context['host']
        report['connected'] = True
        for command in ('hostname', 'date'):
            stage = command
            progress(f'{host}: executing {command}')
            try:
                stdout, stderr, exitcode = session.exec_command(
                    [command], check=False, command_timeout=timeout,
                )
                report['commands'].append({'command': command, 'stdout': stdout, 'stderr': stderr, 'exitcode': exitcode})
            except Exception as exc:
                # Third-party errors may contain proxy commands or credentials.
                report['commands'].append({'command': command, 'error': type(exc).__name__})
                trace(exc)
        report['success'] = all(item.get('exitcode') == 0 for item in report['commands'])
    except Exception as exc:
        report['error'] = {'stage': stage, **connection_error(exc)}
        if current_hop is not None:
            report['error']['hop'] = dict(current_hop)
            if not current_hop['connected']:
                hint = f'Check SSH reachability and authentication for {current_hop["host"]} via {current_hop["parent"]}.'
                if 'key_source' in current_hop:
                    hint += f' identity_file must be readable by the SSH login account on {current_hop["key_source"]} (RSA; path passed literally).'
                report['error']['hint'] = hint
        progress(f'{host}: failed at {stage} ({type(exc).__name__})')
        trace(exc)
    finally:
        if local is not None:
            try:
                local.close(strict=True)
            except Exception as exc:
                report['success'] = False
                report['cleanup_error'] = type(exc).__name__
                trace(exc)
    if init_host:
        if report['connected']:
            from host_runtime import initialize_host
            report['host_init'] = initialize_host(config, host, timeout, session_class, refresh=True)
            report['success'] = report['success'] and report['host_init']['status'] == 'success'
        else:
            report['host_init'] = {'status': 'skipped', 'reason_code': 'connection_failed'}
    print(json.dumps(report, indent=4, ensure_ascii=False))
    return 0 if report['success'] else 1


def positive_timeout(value):
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError('timeout must be a positive finite number')
    return seconds


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        from landing_ui import launch as launch_home
        return launch_home()
    if argv == ['recipes']:
        from recipe_workbench import launch as launch_workbench
        return launch_workbench()
    if '--tui' in argv:
        from terminal_ui import launch
        return launch(REPOSITORY_ROOT / 'tools' / 'opsfeast.py', argv)
    if argv[:1] == ['recipes']:
        from recipe_cli import main as recipe_main
        return recipe_main(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.epilog = 'Add --tui to supported inspection, check, diagnostic or recipes commands for an optional Textual display.'
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('recipes', help='catalog, execution, results, report artifacts, packages and reusable jobs')
    commands.add_parser('profiles', help='list all registered profiles')
    instance_parser = commands.add_parser('instance', help='inspect or explicitly initialize/update installation identity')
    instance_parser.add_argument('action', choices=('inspect', 'init', 'set', 'renew', 'relocate'))
    instance_parser.add_argument('--installation', type=Path, default=REPOSITORY_ROOT)
    instance_parser.add_argument('--name')
    instance_parser.add_argument('--description')

    inspection = commands.add_parser('inspect-recipe', help='inspect recipe metadata, platform coverage and entrypoints without executing code')
    inspection.add_argument('recipe', nargs='?', help='checkout short path or explicit directory; omitted: discover checkout recipes')
    inspection.add_argument('--platform', action='append', default=[], help='requested os_name to compare with declared implemented platforms; repeat as needed')
    inspection_output = inspection.add_mutually_exclusive_group()
    inspection_output.add_argument('--json', action='store_true', help='emit complete descriptor and static inspection report as JSON')
    inspection_output.add_argument('--details', action='store_true', help='show the full human-readable report instead of a focused summary')
    use = commands.add_parser('use', help='select the default profile')
    use.add_argument('profile', nargs='?')
    attach = commands.add_parser('attach', help='validate and register an existing management directory without modifying it')
    attach.add_argument('root', type=Path)
    attach.add_argument('--profile', help='registration name (default: directory name)')
    detach = commands.add_parser('detach', help='remove a profile registration and preserve its directory; main is protected')
    detach.add_argument('profile', help='exact registered profile name; main cannot be detached')
    for command in ('init', 'check', 'dump', 'test-connection'):
        command_parser = commands.add_parser(command)
        if command == 'dump':
            command_parser.add_argument('setting', help='dot-separated setting path, such as hosts.host-01')
        if command == 'test-connection':
            command_parser.add_argument('host', help='host ID from hosts.yaml')
            command_parser.add_argument('--host-init', action='store_true', help='also refresh saved platform facts after connecting')
            command_parser.add_argument('--timeout', type=positive_timeout, default=30, help='per-stage connection and command timeout in seconds (default: 30)')
            command_parser.add_argument('-v', '--verbose', action='store_true', help='show hop and command progress on stderr')
            command_parser.add_argument('--debug', action='store_true', help='show safe effective connection details on stderr; implies verbose')
            command_parser.add_argument('--traceback', action='store_true', help='show exception stack frames on stderr, without source, locals or exception text')
        command_parser.add_argument('root', type=str if command == 'init' else Path, nargs='?', help='init: name or path (default: feasts/main; existing named profiles are reused); other commands: optional management directory')
        command_parser.add_argument('--profile', help='init: registration name; other commands: profile for this invocation')
    for command in ('host-init', 'test-su', 'test-sudo', 'test-host'):
        diagnostic = commands.add_parser(command)
        diagnostic.add_argument('host', help='host ID from hosts.yaml')
        if command in ('test-su', 'test-sudo'):
            diagnostic.add_argument('usernames', nargs='*', help='independent account tests')
        if command == 'test-su':
            diagnostic.add_argument('--chain', nargs='+', action='append', help='one ordered su chain; repeat for independent chains')
        if command == 'test-sudo':
            diagnostic.add_argument('--run-as', default='root', help='sudo target account (default: root)')
        diagnostic.add_argument('--root', type=Path, help='management directory (default: selected profile)')
        diagnostic.add_argument('--profile', help='profile for this invocation')
        diagnostic.add_argument('--timeout', type=positive_timeout, default=30)
        diagnostic.add_argument('-v', '--verbose', action='store_true', help='show diagnostic progress on stderr')
        diagnostic.add_argument('--debug', action='store_true', help='show safe connection and credential-source details on stderr; implies verbose')
        diagnostic.add_argument('--traceback', action='store_true', help='show exception frames without source, locals or exception text')
    access = commands.add_parser('check-access', help='test login and configured users via su/sudo without inventory')
    access.add_argument('--root', type=Path)
    access.add_argument('--profile')
    access.add_argument('--host', nargs='+', action='extend', default=[])
    access.add_argument('--group', nargs='+', action='extend', default=[])
    access.add_argument('--all', dest='all_hosts', action='store_true')
    access.add_argument('--exclude', nargs='+')
    access.add_argument('--threads', type=int, default=1)
    access.add_argument('--timeout', type=positive_timeout, default=30)
    access.add_argument('--json', action='store_true', help='output the full access report as JSON')
    access.add_argument('-q', '--quiet', action='store_true', help='suppress access progress on stderr')
    args = parser.parse_args(argv)
    try:
        if args.command == 'instance':
            from .core import Instance
            instance = Instance.open(args.installation)
            if args.action in ('inspect', 'renew', 'relocate') and (args.name is not None or args.description is not None):
                raise ConfigError('name/description apply only to init or set')
            if args.action == 'inspect':
                result = instance.inspect()
            elif args.action == 'init':
                result = instance.initialize(name=args.name, description=args.description)
            elif args.action == 'set':
                result = instance.update_metadata(name=args.name, description=args.description)
            elif args.action == 'renew':
                result = instance.renew_identity()
            else:
                result = instance.relocate_identity()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 1 if result.get('status') == 'partial' else 0
        if args.command == 'check-access':
            from run_recipe import select_hosts
            from access_check import check_many, format_summary, progress_printer, table_formatter
            root = resolve_root(args.root, args.profile)
            targets = [('host', h) for h in args.host] + [('group', g) for g in args.group]
            if args.threads <= 0:
                raise ConfigError('--threads must be positive')
            if not targets and not args.all_hosts or targets and args.all_hosts or args.exclude and not args.all_hosts:
                raise ConfigError('choose --host/--group or --all; --exclude requires --all')
            excluded = []
            hosts = select_hosts(root, targets, args.all_hosts, args.exclude, excluded)
            if not args.json:
                table_formatter()
            report = check_many(root, hosts, args.timeout, args.threads,
                                progress=None if args.quiet else progress_printer(len(hosts)), include_users=True)
            report['excluded_hosts'] = excluded
            print(json.dumps(report, indent=2) if args.json else format_summary(report))
            return 0 if report['status'] == 'success' else 1
        if args.command == 'inspect-recipe':
            from recipe_inspection import inspect_recipes, format_report
            report = inspect_recipes(args.recipe, args.platform)
            print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else format_report(report, details=args.details))
            return 1 if report['status'] == 'failed' else 0
        if args.command == 'profiles':
            list_profiles()
            return 0
        if args.command == 'use':
            return use_profile(args.profile)
        if args.command == 'detach':
            return detach_profile(args.profile)
        if args.command == 'attach':
            root = args.root.expanduser().resolve(strict=True)
            definition = definition_path(root)
            if definition.exists() or definition.is_symlink():
                instance_definition(root)
            Validator(root).check()
            root, name, registry = registration_plan(root, args.profile)
            register_profile(root, name, registry)
            print(f'Registered profile: {name}  {root}')
            print('Existing management files preserved; no connection or recipe execution performed.')
            return 0
        if args.command == 'init':
            args.root, name, registry = init_plan(args.root, args.profile)
        else:
            args.root = resolve_root(args.root, args.profile)
        if args.command in ('host-init', 'test-su', 'test-sudo', 'test-host'):
            from host_runtime import load_config, initialize_host, privilege_test, test_host, diagnostic_options
            config = load_config(args.root, args.host)
            with diagnostic_options(args.verbose, args.debug, args.traceback):
                if args.command == 'host-init':
                    report = initialize_host(config, args.host, args.timeout, refresh=True)
                elif args.command == 'test-host':
                    report = test_host(config, args.host, args.timeout)
                else:
                    report = privilege_test(config, args.host, args.command[5:], args.usernames,
                                            getattr(args, 'chain', None), getattr(args, 'run_as', 'root'), args.timeout)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 1 if report['status'] == 'failed' else 0
        if args.command == 'test-connection' and args.host_init:
            return test_connection(args.root, args.host, args.timeout, args.verbose, args.debug, args.traceback, init_host=True)
        if args.command == 'test-connection':
            return test_connection(args.root, args.host, args.timeout, args.verbose, args.debug, args.traceback)
        if args.command == 'dump':
            result = Validator(args.root)
            result.load(result.root / 'hosts.yaml')
            value = dict(result.documents[result.root / 'hosts.yaml'])
            value['hosts'] = result.hosts
            for key in args.setting.split('.'):
                if not key or not isinstance(value, dict) or key not in value:
                    raise ConfigError(f'setting not found: {args.setting}')
                value = value[key]
            plain_values(value, args.setting)
            try:
                output = json.dumps(value, indent=4, ensure_ascii=False, allow_nan=False)
            except ValueError:
                raise ConfigError('selected setting cannot be represented as JSON') from None
            print(output)
            return 0
        root = initialize(args.root) if args.command == 'init' else args.root
        result = Validator(root).check()
        if args.command == 'init':
            register_profile(root, name, registry)
            from .identity import initialize_identity
            initialize_identity(REPOSITORY_ROOT)
            print(f'Registered profile: {name}  {root}')
        print(f'OK: {len(result.loaded)} YAML files, {len(result.hosts)} hosts; configuration checks passed.')
        for host, recipes in result.selected.items():
            print(f'  {host}: {len(recipes)} selected recipes')
            for skipped in result.recipe_skips.get(host, []):
                print(f"    skipped {skipped['reference']}: {skipped['reason_code']}")
        for note in result.notes:
            print(f'NOTE: {note}')
        print('No SSH connection or recipe execution performed; platform, authentication and full recipe contracts are not validated.')
        return 0
    except (ConfigError, OSError, RuntimeError, RecursionError) as exc:
        if getattr(args, 'traceback', False):
            diagnostic_traceback(exc)
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())


API_VERSION = '0.1.0'

def __getattr__(name):
    if name in {'Instance', 'Profile', 'Recipe', 'CoreError'}:
        from . import core
        return getattr(core, name)
    raise AttributeError(name)

__all__ = ['API_VERSION', 'Instance', 'Profile', 'Recipe', 'CoreError', 'ConfigError']
