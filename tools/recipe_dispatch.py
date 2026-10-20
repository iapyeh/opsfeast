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
    """Validate the current inventory job descriptor, never a snapshot execution path."""
    from recipe_identity import validate as validate_identity
    validate_identity(metadata, directory)
    if (metadata.get('descriptor_version') != '0.3.0' or metadata.get('id') != 'inventory-system'
        or metadata.get('runner') != {'contract':'inventory-jobs','version':'0.1.0','entrypoint':'jobs.py'}
        or metadata.get('output',{}).get('schema_version') != '0.3.0'):
        raise ConfigError('inventory requires descriptor 0.3.0, inventory-jobs 0.1.0 and raw schema 0.3.0')
    if any(key in metadata.get('output',{}) for key in ('retained_contract_version','exchange_version','retention_adapter')):
        raise ConfigError('declare inventory retention under retention, independently of raw output')
    if metadata.get('access_mode') != 'read':
        raise ConfigError('inventory job collection requires access_mode read')
    if not isinstance(metadata.get('version'),str) or not metadata['version']:
        raise ConfigError('recipe version must be a nonempty string')
    if 'implementations' in metadata:
        raise ConfigError('inventory jobs do not accept snapshot implementations')
    from inventory_jobs import inspect_collection, CONTRACT
    inspect_collection(directory, metadata)
    if metadata.get('retention') != CONTRACT:
        raise ConfigError('inventory requires the registered inventory-job-observations retention contract')
    for path in directory.rglob('*.py'):
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ConfigError('recipe Python helper escapes recipe directory')
    return metadata['collection']



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
    if 'inventory' in report:
        from inventory_values import validate_inventory
        if report.get('inventory_contract_version') != '0.1.0':
            raise ConfigError('unsupported inventory values version')
        validate_inventory(report['inventory'])
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
