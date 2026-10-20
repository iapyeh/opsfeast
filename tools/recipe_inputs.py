"""Typed recipe inputs and per-execution context; no environment/global injection."""
import ast
import copy
import json
from dataclasses import dataclass
import math

from opsfeast import ConfigError, mapping, plain_values, string


@dataclass
class RecipeContext:
    host_id: str
    vars: dict


TYPES = {
    'string': lambda value: isinstance(value, str),
    'integer': lambda value: type(value) is int,
    'number': lambda value: type(value) is int or type(value) is float and math.isfinite(value),
    'boolean': lambda value: type(value) is bool,
    'object': lambda value: isinstance(value, dict),
    'array': lambda value: isinstance(value, list),
}


def validate_value(name, spec, value):
    plain_values(value, f'recipe variable {name}')
    if not TYPES[spec['type']](value):
        raise ConfigError(f'recipe variable {name}: incorrect type')
    if 'minimum' in spec and (value <= spec['minimum'] if spec.get('exclusive_minimum') else value < spec['minimum']):
        raise ConfigError(f'recipe variable {name}: below minimum')
    if 'maximum' in spec and value > spec['maximum']:
        raise ConfigError(f'recipe variable {name}: above maximum')


def parse_json_object(content):
    """Read explicit input data without YAML coercions or duplicate-key guessing."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate input key')
            result[key] = value
        return result
    try:
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        values = json.loads(content, object_pairs_hook=pairs)
        if not isinstance(values, dict):
            raise ValueError('input file must be an object')
        plain_values(values, 'CLI recipe variables')
        return values
    except (OSError, ValueError, UnicodeError, RecursionError, ConfigError):
        raise ConfigError('--vars-file must be a readable JSON object with unique keys and finite plain values') from None


def json_object(path):
    try:
        return parse_json_object(path.expanduser().read_text(encoding='utf-8'))
    except (OSError, UnicodeError):
        raise ConfigError('JSON input file must be readable UTF-8') from None


def cli_variables(metadata, values=None, assignments=()):
    """Strings stay literal; all other types use JSON, validated by prepare_vars."""
    values = copy.deepcopy(mapping({} if values is None else values, 'CLI recipe variables'))
    definitions = mapping(mapping(metadata.get('inputs', {}), 'recipe inputs').get('variables', {}), 'inputs.variables')
    seen = set()
    for assignment in assignments:
        name, separator, text = assignment.partition('=')
        if not separator or not name or name in seen:
            raise ConfigError('--var requires unique NAME=VALUE assignments')
        seen.add(name)
        if name not in definitions:
            raise ConfigError('CLI recipe vars contain undeclared inputs')
        spec = mapping(definitions[name], 'recipe variable definition')
        if spec.get('type') == 'string':
            values[name] = text
        else:
            try:
                values[name] = json.loads(text)
            except (ValueError, RecursionError):
                raise ConfigError('--var non-string values must use JSON syntax') from None
    return values


def prepare_vars(metadata, source_vars, host_vars, cli_vars=None):
    inputs = mapping(metadata.get('inputs', {}), 'recipe inputs')
    definitions = mapping(inputs.get('variables', {}), 'inputs.variables')
    defaults = {}
    for name, spec in definitions.items():
        string(name, 'variable name')
        mapping(spec, f'variable {name}', ('type', 'required', 'default', 'minimum', 'maximum', 'exclusive_minimum'))
        if not isinstance(spec.get('type'), str) or spec['type'] not in TYPES or type(spec.get('required', False)) is not bool:
            raise ConfigError(f'variable {name}: invalid type or required flag')
        if type(spec.get('exclusive_minimum', False)) is not bool:
            raise ConfigError(f'variable {name}: exclusive_minimum must be boolean')
        if spec.get('exclusive_minimum') and 'minimum' not in spec:
            raise ConfigError(f'variable {name}: exclusive_minimum requires minimum')
        for bound in ('minimum', 'maximum'):
            if bound in spec and (spec['type'] not in ('integer', 'number') or
                                  not TYPES['number'](spec[bound])):
                raise ConfigError(f'variable {name}: invalid numeric bound')
        if 'minimum' in spec and 'maximum' in spec and spec['minimum'] > spec['maximum']:
            raise ConfigError(f'variable {name}: minimum exceeds maximum')
        if 'default' in spec:
            validate_value(name, spec, spec['default'])
            defaults[name] = spec['default']
    from recipe_settings import merge
    values = merge(merge(merge(defaults, source_vars), host_vars), cli_vars or {})
    plain_values(values, 'recipe variables')
    if set(values) - set(definitions):
        raise ConfigError('recipe vars contain undeclared inputs; declare inputs.variables')
    for name, spec in definitions.items():
        if name not in values:
            if spec.get('required', False):
                raise ConfigError(f'missing required recipe variable: {name}')
            continue
        validate_value(name, spec, values[name])
    return values


def supports_context(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'collect':
            return (node.args.kwarg is not None or
                    any(arg.arg == 'context' for arg in [*node.args.args, *node.args.kwonlyargs]))
    return False
