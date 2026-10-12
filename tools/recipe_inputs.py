"""Typed recipe inputs and per-execution context; no environment/global injection."""
import ast
import copy
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


def prepare_vars(metadata, source_vars, host_vars):
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
    # Deliberately shallow overlay, followed by a deep copy to isolate threads.
    values = copy.deepcopy({**defaults, **source_vars, **host_vars})
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
