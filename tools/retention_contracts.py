"""Registered retention data contracts; static discovery never loads candidate code."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from opsfeast import ConfigError, REPOSITORY_RECIPES

INVENTORY_CONTRACT = ('inventory-observations', '0.1.0')
# Registration is product code reviewed with its owning recipe, not descriptor executable paths.
STRUCTURED = {INVENTORY_CONTRACT: ('system/inventory/overview', 'retention.py', 'retention.schema.json')}


def location(contract):
    if contract not in STRUCTURED:
        raise ConfigError('unsupported structured retention contract/version')
    directory, module, schema = STRUCTURED[contract]
    root = REPOSITORY_RECIPES / directory
    return root / module, root / schema


def read_schema(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ConfigError('retention schema must have unique object keys')
            result[key] = value
        return result
    try:
        value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
    except (OSError, ValueError, UnicodeError):
        raise ConfigError('retention schema must be a readable JSON object') from None
    if not isinstance(value, dict):
        raise ConfigError('retention schema must be a JSON object')
    return value


def normalizer_digest(declaration):
    contract = (declaration['contract'], declaration['version'])
    module, _ = location(contract)
    if module.is_symlink() or not module.resolve().is_relative_to(REPOSITORY_RECIPES.resolve()):
        raise ConfigError('registered normalizer escapes bundled recipes')
    return hashlib.sha256(module.read_bytes()).hexdigest()


def schema_digest(declaration):
    _, path = location((declaration['contract'], declaration['version']))
    if path.is_symlink() or not path.resolve().is_relative_to(REPOSITORY_RECIPES.resolve()):
        raise ConfigError('registered schema escapes bundled recipes')
    document = read_schema(path)
    document.pop('$comment', None)
    content = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(content.encode()).hexdigest()


@lru_cache(maxsize=None)
def implementation(contract, digest):
    module, _ = location(contract)
    content = module.read_bytes()
    if hashlib.sha256(content).hexdigest() != digest:
        raise ConfigError('registered normalizer changed during loading')
    # Compile the exact reviewed bytes whose digest was checked; no candidate code/import search.
    namespace = {'__file__': str(module), '__name__': '_opsfeast_retention_' + contract[0]}
    exec(compile(content, str(module), 'exec'), namespace)
    if namespace.get('CONTRACT') != contract[0] or namespace.get('VERSION') != contract[1]:
        raise ConfigError('registered normalizer contract/version mismatch')
    if not callable(namespace.get('normalize')) or not callable(namespace.get('validate')):
        raise ConfigError('registered normalizer requires normalize and validate')
    return namespace


def normalize(contract, raw, source):
    declaration = dict(zip(('contract', 'version'), contract))
    return implementation(contract, normalizer_digest(declaration))['normalize'](raw, source)


def validate_payload(contract, data):
    declaration = dict(zip(('contract', 'version'), contract))
    implementation(contract, normalizer_digest(declaration))['validate'](data)


def validate_declaration(metadata, directory=None):
    declaration = metadata.get('retention')
    if declaration is None:
        return None
    if not isinstance(declaration, dict):
        raise ConfigError('invalid retention declaration')
    contract = (declaration.get('contract'), declaration.get('version'))
    if not all(isinstance(v, str) for v in contract):
        raise ConfigError('retention contract/version must be strings')
    if not isinstance(declaration.get('description'), str) or not declaration['description'].strip():
        raise ConfigError('retention.description must explain the retained dataset and limits')
    if contract in STRUCTURED:
        if set(declaration) != {'contract', 'version', 'description', 'schema'}:
            raise ConfigError('structured retention requires contract/version/description/schema')
        _, registered = location(contract)
        if declaration['schema'] != registered.name:
            raise ConfigError('structured retention schema must match its registered contract')
        if directory is not None:
            directory = Path(directory).resolve(strict=True)
            candidate = directory / declaration['schema']
            if candidate.is_symlink() or not candidate.resolve().is_relative_to(directory) or not candidate.is_file():
                raise ConfigError('retention schema escapes recipe or is missing')
            expected = read_schema(registered)
            actual = read_schema(candidate)
            # Schema comments do not alter the data contract.
            expected.pop('$comment', None)
            actual.pop('$comment', None)
            if actual != expected:
                raise ConfigError('retention schema differs from registered contract; register a reviewed new contract/version')
        return declaration
    if contract != ('host-values', '0.2.0'):
        raise ConfigError('unsupported retention contract/version')
    if set(declaration) != {'contract', 'version', 'description', 'fields'}:
        raise ConfigError('invalid scalar retention declaration')
    fields = declaration['fields']
    if not isinstance(fields, dict) or not fields:
        raise ConfigError('retention.fields must declare at least one field')
    for name, spec in fields.items():
        if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', name):
            raise ConfigError('retained field requires a simple lowercase name')
        if not isinstance(spec, dict) or set(spec) != {'type', 'unit', 'description'} or spec['type'] not in ('string', 'number', 'integer', 'boolean') or not isinstance(spec['unit'], str) or not isinstance(spec['description'], str) or not spec['description'].strip():
            raise ConfigError('retained fields require a scalar type, explicit unit and nonempty description')
    return declaration
