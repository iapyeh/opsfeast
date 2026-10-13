"""Validated inventory implementation manifests and deterministic platform selection."""
import ast
import hashlib
from pathlib import Path
import re
from opsfeast import ConfigError

MATCH_FIELDS = {'os_name', 'distribution_id', 'os_version', 'distribution_version', 'kernel_release', 'architecture'}


def numeric_version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+(?:\.\d+)*', value):
        raise ConfigError('version ranges require dotted numeric versions; use =exact for vendor suffixes')
    return tuple(map(int, value.split('.')))


def compare(a, b):
    length = max(len(a), len(b))
    a, b = a + (0,) * (length - len(a)), b + (0,) * (length - len(b))
    return (a > b) - (a < b)


def version_match(value, spec):
    if not isinstance(spec, str) or not spec:
        raise ConfigError('version condition must be a nonempty string')
    if spec.startswith('=') and not spec.startswith('=='):
        if not spec[1:]:
            raise ConfigError('exact version condition must contain a value')
        return value == spec[1:]
    parts = spec.split(',')
    parsed = []
    for part in parts:
        found = re.fullmatch(r'\s*(>=|<=|==|>|<)?\s*(\d+(?:\.\d+)*)\s*', part)
        if not found:
            raise ConfigError('invalid version condition')
        parsed.append((found[1] or '==', numeric_version(found[2])))
    if value is None:
        return False
    try:
        actual = numeric_version(value)
    except ConfigError:
        return False
    for op, expected in parsed:
        c = compare(actual, expected)
        if not {'==': c == 0, '>': c > 0, '<': c < 0, '>=': c >= 0, '<=': c <= 0}[op]:
            return False
    return True


def declared_version(path):
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except (ValueError, SyntaxError):
        raise ConfigError('implementation has invalid Python syntax') from None
    declarations = [node.value for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'VERSION' for t in node.targets)]
    if len(declarations) != 1 or not isinstance(declarations[0], ast.Constant) or not isinstance(declarations[0].value, str):
        raise ConfigError('implementation must declare one literal VERSION string')
    return declarations[0].value


def validate(directory, metadata):
    if not isinstance(metadata.get('output'), dict):
        raise ConfigError('output contract must be a mapping')
    if (metadata.get('descriptor_version') != '0.2.0' or metadata.get('id') != 'inventory-system'
            or (metadata.get('output') or {}).get('schema_version') != '0.2.0'):
        raise ConfigError('runner requires inventory-system descriptor 0.2.0 and output schema 0.2.0')
    if not isinstance(metadata.get('version'), str) or not metadata['version']:
        raise ConfigError('recipe version must be a nonempty string')
    for key, expected in (('retained_contract_version', '0.1.0'), ('exchange_version', '0.1.0'),
                          ('retention_adapter', 'inventory-system-v1')):
        if key in metadata['output'] and metadata['output'][key] != expected:
            raise ConfigError('unsupported inventory retained/exchange contract')
    entries = metadata.get('implementations')
    if not isinstance(entries, list) or not entries:
        raise ConfigError('recipe must declare implementations')
    ids = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - {'id', 'version', 'entrypoint', 'match', 'priority', 'verification'}:
            raise ConfigError('invalid implementation descriptor')
        if not isinstance(entry.get('id'), str) or not entry['id'] or entry['id'] in ids:
            raise ConfigError('implementation IDs must be unique nonempty strings')
        ids.add(entry['id'])
        name = entry.get('entrypoint')
        if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ConfigError('implementation entrypoint must be recipe-relative')
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file() or path.suffix != '.py':
            raise ConfigError('implementation must be a Python file inside its recipe')
        if declared_version(path) != entry.get('version'):
            raise ConfigError('implementation VERSION differs from descriptor')
        if type(entry.get('priority', 0)) is not int:
            raise ConfigError('implementation priority must be an integer')
        conditions = entry.get('match')
        if not isinstance(conditions, dict) or not conditions or set(conditions) - MATCH_FIELDS:
            raise ConfigError('invalid implementation match fields')
        for key, spec in conditions.items():
            if not isinstance(spec, str) or not spec:
                raise ConfigError('match conditions must be nonempty strings')
            if key in ('os_version', 'distribution_version', 'kernel_release'):
                version_match(None, spec)
    # Include recipe helpers in provenance and reject symlink escapes too.
    for path in directory.rglob('*.py'):
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ConfigError('recipe Python helper escapes recipe directory')
    return entries


def select(entries, facts):
    matches = []
    for entry in entries:
        conditions = entry['match']
        if all(version_match(facts.get(k), v) if k in ('os_version', 'distribution_version', 'kernel_release')
               else facts.get(k) == v for k, v in conditions.items()):
            matches.append(entry)
    if not matches:
        return None
    rank = lambda entry: (entry.get('priority', 0), len(entry['match']))
    top = max(map(rank, matches))
    winners = [entry for entry in matches if rank(entry) == top]
    if len(winners) != 1:
        raise ConfigError('ambiguous platform implementation selection')
    return winners[0]


def bundle_digest(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob('*.py')):
        digest.update(path.relative_to(directory).as_posix().encode() + b'\0')
        digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_observations(report):
    """Enforce the seven-field interface without adding a JSON Schema dependency."""
    fields = {'hostname', 'platform', 'system_name', 'system_version', 'kernel_name', 'kernel_release', 'architecture'}
    statuses = {'success', 'unavailable', 'unsupported', 'permission_denied', 'timeout', 'command_failed', 'parsing_failed', 'not_attempted'}
    observations = report.get('observations')
    if not isinstance(observations, dict) or set(observations) != fields:
        raise ConfigError('implementation returned invalid inventory fields')
    for item in observations.values():
        if (not isinstance(item, dict) or item.get('status') not in statuses
                or not {'value', 'status', 'observed_at', 'source_ids', 'error'}.issubset(item)
                or item['value'] is not None and not isinstance(item['value'], str)
                or item['observed_at'] is not None and not isinstance(item['observed_at'], str)
                or not isinstance(item['source_ids'], list)
                or any(not isinstance(source, str) for source in item['source_ids'])
                or item['error'] is not None and not isinstance(item['error'], dict)
                or item['status'] == 'success' and not item['value']
                or item['status'] != 'success' and item['value'] is not None):
            raise ConfigError('implementation returned invalid inventory observation')
