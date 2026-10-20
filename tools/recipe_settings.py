"""Reference-keyed recipe policy and deterministic host/group/default inheritance."""
import copy
from pathlib import PurePosixPath
import re
from opsfeast import ConfigError, plain_values


def reference(value):
    if not isinstance(value, str) or not value or '\\' in value or '://' in value:
        raise ConfigError('recipe settings require a source-qualified relative reference')
    if ':' in value:
        source, path = value.split(':', 1)
        if source and not re.fullmatch(r'[a-z][a-z0-9_-]*', source):
            raise ConfigError('invalid recipe source prefix')
        prefix = '' if source == 'bundle' else source + ':'
    else:
        path, prefix = value, ''
    if ':' in path or not path or path.startswith(('/', '~')) or any(part in ('', '.', '..') for part in path.split('/')) or any(c in path for c in '*?['):
        raise ConfigError('recipe settings require one exact relative recipe path')
    return prefix + PurePosixPath(path).as_posix()


def merge(base, update):
    result = copy.deepcopy(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(result.get(key, {}), dict):
            result[key] = merge(result.get(key, {}), value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def normalize(value):
    if not isinstance(value, dict):
        raise ConfigError('recipes must map exact references to enabled/vars')
    result = {}
    for key, options in value.items():
        key = reference(key)
        if key in result:
            raise ConfigError('duplicate normalized recipe reference')
        if not isinstance(options, dict) or set(options) - {'enabled', 'vars'}:
            raise ConfigError('recipe settings permit enabled and vars only')
        if 'enabled' in options and type(options['enabled']) is not bool:
            raise ConfigError('recipe enabled must be Boolean')
        if 'vars' in options and not isinstance(options['vars'], dict):
            raise ConfigError('recipe vars must be a mapping')
        plain_values(options.get('vars', {}), 'recipe vars')
        result[key] = copy.deepcopy(options)
    return result


def resolved(defaults, groups, host):
    result = copy.deepcopy(defaults)
    for group in reversed(groups):
        result = merge(result, group)
    return merge(result, host)
