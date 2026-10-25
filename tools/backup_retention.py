"""Pure, registered backup-files-check normalization and semantic validation."""
import copy
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import re
from pathlib import PurePosixPath
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from opsfeast import ConfigError, REPOSITORY_ROOT

CONTRACT = 'backup-files-check'
VERSION = '0.1.0'


def shape(value, spec, root):
    if '$ref' in spec:
        return shape(value, root['$defs'][spec['$ref'].split('/')[-1]], root)
    types = {'object': isinstance(value, dict), 'array': isinstance(value, list),
             'string': isinstance(value, str), 'integer': type(value) is int,
             'boolean': type(value) is bool, 'null': value is None}
    kinds = spec.get('type', list(types))
    kinds = [kinds] if isinstance(kinds, str) else kinds
    if not any(types[k] for k in kinds):
        raise ConfigError('invalid backup retained type')
    if 'enum' in spec and value not in spec['enum'] or 'const' in spec and value != spec['const']:
        raise ConfigError('invalid backup retained state')
    if isinstance(value, dict):
        properties = spec.get('properties', {})
        if set(spec.get('required', [])) - set(value) or spec.get('additionalProperties') is False and set(value) - set(properties):
            raise ConfigError('invalid backup retained fields')
        for key, item in value.items():
            if key in properties:
                shape(item, properties[key], root)
    elif isinstance(value, list):
        if len(value) < spec.get('minItems', 0):
            raise ConfigError('missing backup groups')
        for item in value:
            shape(item, spec['items'], root)
    elif type(value) is int and value < spec.get('minimum', value):
        raise ConfigError('negative backup measurement')


def validate(data):
    from observation_store import timestamp, uuid_text
    schema = json.loads((REPOSITORY_ROOT / 'schemas/backup-files-check.schema.json').read_text())
    shape(data, schema, schema)
    from collection_evidence import validate as validate_evidence
    validate_evidence({'contract_version':'0.1.0', 'actor':data['actor'], 'probes':[]})
    uuid_text(data['source_id'])
    if timestamp(data['observed_at']) != data['observed_at']:
        raise ConfigError('backup timestamps must be canonical UTC')
    policy = data['policy']
    try:
        zone = ZoneInfo(policy['timezone'])
    except (ZoneInfoNotFoundError, ValueError):
        raise ConfigError('invalid retained backup timezone') from None
    days = policy['retention_days']
    if days > 365000 or not 1 <= policy['max_entries'] <= 100000:
        raise ConfigError('invalid retained backup policy')
    if len({g['name'] for g in data['backups']}) != len(data['backups']):
        raise ConfigError('duplicate retained backup group')
    check_date = date.fromisoformat(data['check_date'])
    if any(g['scan_status'] != 'complete' or g['health'] != 'healthy' for g in data['backups']) and data['status'] == 'success':
        raise ConfigError('inconsistent successful backup result')
    for group in data['backups']:
        if (not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,62}', group['name'])
                or not group['directory'].startswith('/') or group['directory'] == '/'
                or '..' in PurePosixPath(group['directory']).parts or '\x00' in group['directory']):
            raise ConfigError('invalid retained backup location')
        if not group['patterns'] or len(set(group['patterns'])) != len(group['patterns']):
            raise ConfigError('invalid retained backup patterns')
        expressions = []
        for pattern in group['patterns']:
            if (pattern.count('{date}') != 1 or pattern.startswith('/') or '\x00' in pattern
                    or any(p in ('', '.', '..') for p in pattern.split('/'))
                    or any('{date}' in p for p in pattern.split('/')[:-1])
                    or '{' in pattern.replace('{date}', '') or '}' in pattern.replace('{date}', '')):
                raise ConfigError('unsafe retained backup pattern')
            expressions.append(re.compile('^' + re.escape(pattern).replace(re.escape('{date}'), r'(\d{4}-\d{2}-\d{2})') + '$'))
        observed = datetime.fromisoformat(group['observed_at'])
        if timestamp(group['observed_at']) != group['observed_at'] or observed.astimezone(zone).date() != check_date:
            raise ConfigError('inconsistent backup sample date')
        expected = [p.replace('{date}', data['check_date']) for p in group['patterns']]
        if [f['path'] for f in group['expected_files']] != expected:
            raise ConfigError('inconsistent daily backup filenames')
        if group['cutoff_exclusive'] != (check_date - timedelta(days=days)).isoformat():
            raise ConfigError('inconsistent backup cutoff')
        present = [f['present'] for f in group['expected_files']]
        if group['scan_status'] == 'complete' and any(v is None for v in present):
            raise ConfigError('complete scan must establish daily presence')
        for item in group['expected_files']:
            if (item['present'] is True) != (item['size_bytes'] is not None and item['mtime_ns'] is not None):
                raise ConfigError('inconsistent backup presence metadata')
        if group['health'] == 'healthy' and not all(v is True for v in present):
            raise ConfigError('unverified healthy backup')
        if all(v is True for v in present) and group['health'] != 'healthy':
            raise ConfigError('inconsistent daily backup health')
        if group['scan_status'] == 'incomplete' and group['health'] not in ('unknown', 'healthy'):
            raise ConfigError('incomplete backup scan cannot establish absence')
        if not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', group['ready_after']):
            raise ConfigError('invalid retained daily deadline')
        minutes = int(group['ready_after'][:2])*60 + int(group['ready_after'][3:]) + group['grace_minutes']
        if minutes >= 1440:
            raise ConfigError('retained daily deadline crosses date')
        deadline = datetime.combine(check_date, time.fromisoformat(group['ready_after']), zone) + timedelta(minutes=group['grace_minutes'])
        if group['deadline'] != deadline.astimezone(timezone.utc).isoformat(timespec='microseconds'):
            raise ConfigError('inconsistent retained daily deadline')
        if group['health'] == 'pending' and observed >= deadline or group['health'] == 'missing' and observed < deadline:
            raise ConfigError('inconsistent pending/missing backup state')
        if not len(group['expired_files']) <= group['backup_count'] <= group['scanned_entries'] <= policy['max_entries']:
            raise ConfigError('inconsistent backup counts')
        for field in ('expired_files', 'unexpected_entries'):
            if len({f['path'] for f in group[field]}) != len(group[field]):
                raise ConfigError('duplicate backup entries')
        for item in group['expired_files']:
            age = (check_date - date.fromisoformat(item['backup_date'])).days
            if age != item['age_days'] or age <= days or item['kind'] != 'file':
                raise ConfigError('invalid expired backup age')
            matches = [m.group(1) for expression in expressions if (m := expression.fullmatch(item['path']))]
            if item['backup_date'] not in matches:
                raise ConfigError('expired filename does not match its saved date')
        for item in [*group['expired_files'], *group['unexpected_entries']]:
            if item['path'].startswith('/') or any(p in ('', '.', '..') for p in item['path'].split('/')) or '\x00' in item['path']:
                raise ConfigError('unsafe retained backup relative path')
    json.dumps(data, allow_nan=False)
    return data


def normalize(raw, source):
    from observation_store import timestamp, uuid_text
    from retention_replay import source_identity
    if raw.get('evidence_kind') not in ('local', 'ssh') or raw.get('status') not in ('success', 'partial'):
        return None, 'nonoperational_or_failed_result'
    uuid_text(source)
    data = copy.deepcopy(raw['data'])
    data.update(contract_version=VERSION, source_id=source,
        observation_id=source + ':' + hashlib.sha256(source_identity(raw).encode()).hexdigest(),
        recipe_id=raw['recipe']['id'], recipe_version=raw['recipe']['version'],
        observed_at=timestamp(raw['completed_at']), status=raw['status'])
    return validate(data), None
