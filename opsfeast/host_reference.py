"""Profile-local reference IPs 0.1.0; never used to select connection endpoints."""
from datetime import datetime
import hashlib
import ipaddress
import json
import os

from . import ConfigError


def from_interfaces(rows, observed_at, source_id):
    """Project a complete interface enumeration, retaining scoped IPv6 addresses."""
    if not isinstance(rows, list):
        raise ValueError('interfaces must be an enumeration')
    addresses = {4: set(), 6: set()}
    for row in rows:
        if not isinstance(row, dict) or 'entry' in row:
            raise ValueError('interfaces are not normalized')
        if row.get('kind') == 'ether' or row.get('address') is None:
            continue
        if not isinstance(row['address'], str):
            raise ValueError('address must be text')
        address = ipaddress.ip_address(row['address'])
        addresses[address.version].add(str(address))
    return {'ipv4_addresses': sorted(addresses[4]), 'ipv6_addresses': sorted(addresses[6]),
            'observed_at': observed_at, 'source_id': source_id}


def _path(root, host_id):
    from retention_store import checked
    key = hashlib.sha256(host_id.encode('utf-8')).hexdigest()
    return checked(root, '.host-reference-ips', key + '.json')


def read(root, host_id):
    """Read without creating files, refreshing inventory or resolving DNS."""
    path = _path(root, host_id)
    if not path.exists():
        return {'schema_version': '0.1.0', 'host_id': host_id, 'status': 'unknown',
                'ipv4_addresses': [], 'ipv6_addresses': [], 'observed_at': None}
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('schema_version') != '0.1.0' or value.get('host_id') != host_id or value.get('status') != 'known':
        raise ConfigError('invalid host reference IP record')
    try:
        if datetime.fromisoformat(value['observed_at']).utcoffset() is None:
            raise ValueError('missing timezone')
        for family in (4, 6):
            addresses = value['ipv' + str(family) + '_addresses']
            if not isinstance(addresses, list) or any(not isinstance(a, str) or ipaddress.ip_address(a).version != family for a in addresses):
                raise ValueError('invalid addresses')
        for field in ('source_id', 'source_record_id', 'source_observation_id', 'recipe'):
            if not isinstance(value[field], str) or not value[field]:
                raise ValueError('missing provenance')
    except (KeyError, TypeError, ValueError):
        raise ConfigError('invalid host reference IP record') from None
    return value


def update(root, report):
    """Persist live, successfully saved enumeration; older concurrent results cannot win."""
    from retention_store import atomic, canonical, checked
    candidate = report.get('reference_ips')
    if not candidate or report.get('execution_errors') or report.get('cleanup_error'):
        return {'status': 'skipped', 'reason_code': 'no_successful_address_collection'}
    if report.get('retention', {}).get('status') != 'stored':
        return {'status': 'skipped', 'reason_code': 'retention_not_stored'}
    import fcntl
    lock = checked(root, '.host-reference-ips.lock')
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        previous = read(root, report['host_id'])
        if previous['observed_at'] and datetime.fromisoformat(previous['observed_at']) > datetime.fromisoformat(candidate['observed_at']):
            return {'status': 'skipped', 'reason_code': 'newer_success_already_saved'}
        value = dict(candidate, schema_version='0.1.0', host_id=report['host_id'], status='known',
                     source_observation_id=report['source_observation_id'],
                     source_record_id=report['retention']['record_id'], recipe=report['recipe']['reference'])
        atomic(_path(root, report['host_id']), canonical(value) + '\n')
    return {'status': 'updated', 'observed_at': value['observed_at']}
