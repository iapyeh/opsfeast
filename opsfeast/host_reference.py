"""Profile-local reference IPs 0.1.0; never used to select connection endpoints."""
from datetime import datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path

from . import ConfigError


def esxi_ipv4_interfaces(text):
    """Parse the bounded esxcli IPv4 table; reject incomplete/unrecognized rows."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2 or not lines[0].startswith('Name') or 'IPv4 Address' not in lines[0] or 'IPv4 Netmask' not in lines[0]:
        raise ValueError('unrecognized ESXi IPv4 header')
    if not all(char in '- ' for char in lines[1]):
        raise ValueError('unrecognized ESXi IPv4 separator')
    rows = []
    for line in lines[2:]:
        parts = line.split()
        if len(parts) < 6: raise ValueError('incomplete ESXi IPv4 row')
        address = ipaddress.IPv4Address(parts[1])
        prefix = ipaddress.IPv4Network('0.0.0.0/' + parts[2]).prefixlen
        rows.append({'name': parts[0], 'address': str(address), 'prefix_length': prefix, 'kind': 'inet'})
    return rows


def from_interfaces(rows, observed_at, source_id, *, collected_families=(4, 6)):
    """Project a complete interface enumeration, retaining scoped IPv6 addresses."""
    if not isinstance(rows, list):
        raise ValueError('interfaces must be an enumeration')
    if tuple(collected_families) not in ((4,), (4, 6)):
        raise ValueError('invalid address coverage')
    addresses = {4: set(), 6: set()}
    for row in rows:
        if not isinstance(row, dict) or 'entry' in row:
            raise ValueError('interfaces are not normalized')
        if row.get('kind') == 'ether' or row.get('address') is None:
            continue
        if not isinstance(row['address'], str):
            raise ValueError('address must be text')
        address = ipaddress.ip_address(row['address'])
        if address.version not in collected_families:
            raise ValueError('address outside collected families')
        if address.is_loopback:
            continue
        addresses[address.version].add(str(address))
    return {'ipv4_addresses': sorted(addresses[4]), 'ipv6_addresses': sorted(addresses[6]),
            'collected_families': list(collected_families), 'observed_at': observed_at, 'source_id': source_id}


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
    families = value.get('collected_families', [4, 6])
    if families not in ([4], [4, 6]): raise ConfigError('invalid reference address coverage')
    return dict(value, collected_families=families,
                **{'ipv'+str(family)+'_addresses': [a for a in value['ipv'+str(family)+'_addresses'] if not ipaddress.ip_address(a).is_loopback] for family in (4, 6)})


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


def refresh_from_saved(root, host_ids):
    """Repair reference metadata from verified saved evidence, without recollection."""
    from recipe_reports import results, show_result
    from retention_store import show
    from retention_replay import raw_digest
    from .core import Hosts
    root = Path(root).resolve(strict=True)
    hosts = Hosts(root)
    for host in host_ids: hosts.get(host)
    listing = results(root)
    output = []
    for host in host_ids:
        receipt = {'host_id': host, 'status': 'skipped', 'reason_code': 'no_verified_saved_address_source'}
        candidates = [row for row in listing['results'] if row['host_id'] == host and row['recipe_reference'] == 'system/inventory/overview']
        candidates.sort(key=lambda row: row.get('started_at') or '', reverse=True)
        for item in candidates:
            try:
                raw = show_result(root, item['result_id'])
                record_id = raw.get('retention', {}).get('record_id')
                if not record_id or raw.get('execution_errors') or raw.get('cleanup_error'): continue
                retained = show(root, record_id)
                provenance = retained.get('retention_provenance', {})
                if (retained['host_id'] != host or retained['recipe_reference'] != 'system/inventory/overview'
                        or provenance.get('raw_sha256') != raw_digest(raw)
                        or provenance.get('source_observation_id') != raw.get('source_observation_id')): continue
                candidate = raw.get('reference_ips')
                if candidate is None and raw.get('platform') == 'esxi':
                    probe = next((p for p in raw.get('probes', []) if p.get('command') == 'esxcli network ip interface ipv4 get'), None)
                    if (not probe or probe.get('status') != 'success' or probe.get('exitcode') != 0
                            or probe.get('stdout_truncated') or probe.get('stderr_truncated')): continue
                    candidate = from_interfaces(esxi_ipv4_interfaces(probe['stdout']), probe['observed_at'], probe['id'], collected_families=(4,))
                if candidate is None: continue
                receipt = {'host_id': host, **update(root, dict(raw, reference_ips=candidate))}
                receipt['result_id'] = item['result_id']
                break
            except (ConfigError, OSError, ValueError, KeyError, TypeError):
                receipt = {'host_id': host, 'status': 'failed', 'reason_code': 'saved_reference_evidence_invalid'}
        output.append(receipt)
    return {'schema_version': '0.1.0', 'hosts': output, 'invalid_result_count': len(listing['errors'])}
