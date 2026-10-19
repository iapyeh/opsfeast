"""Static Python-session recipe contract 0.1.0 and JSON result validation."""
import ast
import inspect
import json
from pathlib import Path
import re

from opsfeast import ConfigError, mapping, plain_values
from recipe_dispatch import declared_version
from recipe_inputs import prepare_vars

CONTRACT = 'python-session'
REPORT_CONTRACT = 'python-report'
CORE_CONTRACT = 'python-recipe'
VERSION = '0.1.0'
STATUSES = {'success', 'partial', 'failed', 'skipped', 'unsupported'}


def validate(directory, metadata):
    from recipe_identity import validate as validate_identity
    validate_identity(metadata, directory)
    if metadata.get('access_mode', 'unknown') not in ('read', 'write', 'unknown'):
        raise ConfigError('access_mode must be read, write or unknown')
    from retention_store import validate_retention
    validate_retention(metadata, directory)
    plain_values(metadata, 'recipe descriptor')
    if metadata.get('descriptor_version') != '0.3.0':
        raise ConfigError('Python-session recipes require descriptor_version 0.3.0')
    identifier = metadata.get('id')
    if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', identifier) or identifier == 'inventory-system':
        raise ConfigError('general recipe id must be a unique simple name other than inventory-system')
    if not isinstance(metadata.get('version'), str) or not metadata['version']:
        raise ConfigError('recipe version must be a nonempty string')
    platforms = mapping(metadata.get('platforms', {}), 'recipe platforms', ('planned', 'implemented', 'tested'))
    for values in platforms.values():
        if not isinstance(values, list) or any(not isinstance(item, str) or not item for item in values):
            raise ConfigError('recipe platforms must contain lists of nonempty strings')
    runner = mapping(metadata.get('runner'), 'recipe runner', ('contract', 'version', 'entrypoint'))
    if runner.get('contract') not in (CONTRACT, REPORT_CONTRACT, CORE_CONTRACT) or runner.get('version') != VERSION:
        raise ConfigError('unsupported recipe runner contract/version')
    output = mapping(metadata.get('output'), 'recipe output', ('schema_version',))
    if not isinstance(output.get('schema_version'), str) or not output['schema_version']:
        raise ConfigError('recipe output.schema_version must be a nonempty string')
    if 'implementations' in metadata:
        raise ConfigError('Python-session recipes use one runner.entrypoint, not inventory implementations')
    name = runner.get('entrypoint')
    if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ConfigError('recipe entrypoint must be recipe-relative')
    entry = (directory / name).resolve()
    if not entry.is_relative_to(directory.resolve()) or not entry.is_file() or entry.suffix != '.py':
        raise ConfigError('recipe entrypoint must be a Python file inside its recipe')
    if declared_version(entry) != metadata['version']:
        raise ConfigError('entrypoint VERSION differs from recipe version')
    tree = ast.parse(entry.read_text(encoding='utf-8'))
    functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'execute']
    if len(functions) != 1 or isinstance(functions[0], ast.AsyncFunctionDef):
        raise ConfigError('recipe must define one synchronous execute matching its runner contract')
    args = functions[0].args
    parameters = []
    positional = [*args.posonlyargs, *args.args]
    defaults_start = len(positional) - len(args.defaults)
    for index, arg in enumerate(positional):
        parameters.append(inspect.Parameter(arg.arg, inspect.Parameter.POSITIONAL_ONLY if index < len(args.posonlyargs)
                          else inspect.Parameter.POSITIONAL_OR_KEYWORD,
                          default=None if index >= defaults_start else inspect.Parameter.empty))
    if args.vararg:
        parameters.append(inspect.Parameter(args.vararg.arg, inspect.Parameter.VAR_POSITIONAL))
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        parameters.append(inspect.Parameter(arg.arg, inspect.Parameter.KEYWORD_ONLY,
                          default=None if default is not None else inspect.Parameter.empty))
    if args.kwarg:
        parameters.append(inspect.Parameter(args.kwarg.arg, inspect.Parameter.VAR_KEYWORD))
    try:
        signature = inspect.Signature(parameters)
        if runner['contract'] == CORE_CONTRACT:
            signature.bind(object())
        elif runner['contract'] == REPORT_CONTRACT:
            signature.bind(context=object(), timeout=30)
        else:
            signature.bind(object(), context=object(), timeout=30)
    except (TypeError, ValueError):
        raise ConfigError('recipe execute must accept the runner arguments with no additional required arguments') from None
    for helper in directory.rglob('*.py'):
        if not helper.resolve().is_relative_to(directory.resolve()):
            raise ConfigError('recipe Python helper escapes recipe directory')
    # Validate definitions/defaults without requiring invocation-specific inputs.
    definitions = mapping(mapping(metadata.get('inputs', {}), 'recipe inputs').get('variables', {}), 'inputs.variables')
    probe = dict(metadata, inputs={'variables': {name: dict(mapping(spec, 'input definition'), required=False)
                                               for name, spec in definitions.items()}})
    # Keep required flags validated in their original form too.
    for spec in definitions.values():
        if type(spec.get('required', False)) is not bool:
            raise ConfigError('recipe input required flag must be boolean')
    prepare_vars(probe, {}, {})
    return entry


def validate_result(result):
    if not isinstance(result, dict) or set(result) != {'status', 'reason_code', 'message', 'data'}:
        raise ConfigError('recipe result requires exactly status, reason_code, message and data')
    if not isinstance(result['status'], str) or result['status'] not in STATUSES:
        raise ConfigError('invalid recipe result status')
    if any(not isinstance(result[key], str) or not result[key] for key in ('reason_code', 'message')):
        raise ConfigError('recipe result reason_code and message must be nonempty strings')
    if not isinstance(result['data'], dict):
        raise ConfigError('recipe result data must be an object')
    plain_values(result, 'recipe result')
    def check_keys(value):
        if isinstance(value, dict):
            if any(not isinstance(key, str) for key in value):
                raise ConfigError('recipe result object keys must be strings')
            for item in value.values():
                check_keys(item)
        elif isinstance(value, list):
            for item in value:
                check_keys(item)
    check_keys(result['data'])
    try:
        json.dumps(result, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        raise ConfigError('recipe result must be finite JSON data') from None
    return result
