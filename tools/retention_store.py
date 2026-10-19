"""Retention storage: authoritative journals and rebuildable data projections."""
import argparse
import calendar
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import tempfile
from uuid import uuid4

from opsfeast import ConfigError, REPOSITORY_ROOT, Validator, definition_path, read_yaml, resolve_root

VERSION = '0.1.0'
HOST_VALUES_VERSION = '0.2.0'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')

def validate_settings(data):
    if not isinstance(data.get('namespace'), str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,62}', data['namespace']):
        raise ConfigError('namespace requires 1-63 lowercase letters, digits, hyphens or underscores')
    months = data.get('overview_months', 3)
    if type(months) is not int or not 1 <= months <= 1200:
        raise ConfigError('overview_months must be an integer from 1 to 1200')
    vault = data.get('vault', {})
    if not isinstance(vault, dict) or set(vault) - {'auto_refresh'} or type(vault.get('auto_refresh', True)) is not bool:
        raise ConfigError('vault.auto_refresh must be boolean')
    return {'namespace': data['namespace'], 'overview_months': months, 'vault': {'auto_refresh': vault.get('auto_refresh', True)}}

def settings(root):
    path = definition_path(Path(root))
    if path.is_symlink():
        raise ConfigError('vault definition refuses symlinks')
    data = read_yaml(path) if path.exists() else {}
    return validate_settings(data) if 'namespace' in data else None

def component(value):
    """A reversible UTF-8 path component, also safe for Windows and Markdown URLs."""
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise ConfigError('invalid vault object ID')
    # Ordinary lowercase IDs remain recognizable; encode reserved names and punctuation.
    reserved = bool(re.fullmatch(r'(con|prn|aux|nul|com[1-9]|lpt[1-9])', value))
    return ''.join(chr(b) if not reserved and (48 <= b <= 57 or 97 <= b <= 122 or b in (45, 95))
                   else f'%{b:02X}' for b in value.encode())

def checked(root, *parts):
    root = Path(root).resolve(strict=True)
    path = root
    for part in parts:
        if part in ('', '.', '..') or '/' in part or '\\' in part:
            raise ConfigError('unsafe vault path')
        path /= part
        if path.is_symlink():
            raise ConfigError('vault refuses symlink paths')
    return path

def retention_checked(root, *parts):
    return checked(root, 'retention', *parts)

def choose_namespace(root, requested=None, profile=None):
    existing = settings(root)
    namespace = requested if requested is not None else existing['namespace'] if existing else profile or Path(root).name
    try:
        validate_settings({'namespace': namespace})
    except ConfigError:
        raise ConfigError('namespace requires 1-63 lowercase letters/digits/hyphens/underscores; pass --namespace explicitly when the profile name does not qualify') from None
    if existing and existing['namespace'] != namespace:
        raise ConfigError('namespace is already fixed for this Feast; changing it would relabel host identity')
    return namespace

def enable_configuration(root, namespace, months=None):
    previous = settings(root)
    selected_months = months if months is not None else previous['overview_months'] if previous else 3
    config = validate_settings({'namespace': namespace, 'overview_months': selected_months, 'vault': previous['vault'] if previous else {}})
    if previous:
        if previous != config:
            raise ConfigError('change overview_months explicitly in feast.yaml, then rebuild; namespace is fixed')
        return config
    path = definition_path(Path(root))
    data = read_yaml(path)
    if 'overview_months' in data:
        raise ConfigError('set namespace explicitly beside existing overview_months')
    atomic(path, path.read_text(encoding='utf-8').rstrip() + '\nnamespace: ' + namespace + '\noverview_months: ' + str(selected_months) + '\n')
    return config

def atomic(path, content):
    if path.is_symlink():
        raise ConfigError('vault refuses symlink outputs')
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

@contextmanager
def locked(root):
    import fcntl
    path = checked(root, '.retention.lock')
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        yield

@contextmanager
def database(path, write=False):
    if path.is_symlink() or any(Path(str(path) + suffix).is_symlink() for suffix in ('-journal', '-wal', '-shm')):
        raise ConfigError('vault refuses SQLite symlinks')
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path if write else path.as_uri() + '?mode=ro', uri=not write, timeout=30)
    try:
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        if version not in ((0, 1) if write else (1,)):
            raise ConfigError('unsupported host-vault database version')
        if write:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('CREATE TABLE IF NOT EXISTS records (record_id TEXT PRIMARY KEY, kind TEXT NOT NULL, namespace TEXT NOT NULL, host_id TEXT NOT NULL, recipe_id TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL)')
            connection.execute('CREATE INDEX IF NOT EXISTS record_selection ON records(kind, recipe_id, observed_at)')
            connection.execute('PRAGMA user_version=1')
        yield connection
        if write:
            connection.commit()
    except BaseException:
        if write:
            connection.rollback()
        raise
    finally:
        connection.close()

def validate_record(record):
    required = {'contract_version', 'record_id', 'kind', 'namespace', 'host_id', 'origin', 'recipe_id', 'recipe_reference', 'observed_at', 'data', 'mappings'}
    if not isinstance(record, dict) or not required.issubset(record) or set(record) - required - {'retention_provenance', 'retention_definition'} or record['contract_version'] != VERSION:
        raise ConfigError('invalid vault record contract')
    if 'retention_provenance' in record:
        evidence = record['retention_provenance']
        keys = {'contract_version', 'source_observation_id', 'raw_sha256', 'execution_access_mode', 'snapshot_sha256', 'retention_recipe_version'}
        if not isinstance(evidence, dict) or set(evidence) != keys or evidence['contract_version'] != VERSION:
            raise ConfigError('invalid retention provenance')
        if not isinstance(evidence['source_observation_id'], str) or not evidence['source_observation_id'] or evidence['execution_access_mode'] not in ('read', 'write', 'unknown'):
            raise ConfigError('invalid retained source identity/mode')
        if not isinstance(evidence['raw_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', evidence['raw_sha256']):
            raise ConfigError('invalid raw digest')
        if evidence['snapshot_sha256'] is not None and (not isinstance(evidence['snapshot_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', evidence['snapshot_sha256'])):
            raise ConfigError('invalid snapshot digest')
        if evidence['retention_recipe_version'] is not None and (not isinstance(evidence['retention_recipe_version'], str) or not evidence['retention_recipe_version']):
            raise ConfigError('invalid retention recipe version')
    validate_settings({'namespace': record['namespace']})
    component(record['host_id'])
    if record['kind'] not in ('observation', 'operation') or not isinstance(record['record_id'], str) or not record['record_id']:
        raise ConfigError('invalid record kind or ID')
    from observation_store import timestamp
    if timestamp(record['observed_at']) != record['observed_at']:
        raise ConfigError('record time must be canonical UTC')
    origin = record['origin']
    if not isinstance(origin, dict) or set(origin) != {'namespace', 'host_id', 'instance_id', 'record_id', 'source_id'}:
        raise ConfigError('invalid origin')
    validate_settings({'namespace': origin['namespace']})
    component(origin['host_id'])
    from observation_store import uuid_text
    uuid_text(origin['instance_id'])
    uuid_text(origin['source_id'])
    if not isinstance(origin['record_id'], str) or not origin['record_id'] or not isinstance(record['recipe_id'], str) or not record['recipe_id'] or not isinstance(record['recipe_reference'], str) or not record['recipe_reference']:
        raise ConfigError('invalid origin ID or recipe ID')
    if not isinstance(record['data'], dict) or not isinstance(record['mappings'], list):
        raise ConfigError('invalid record data or mappings')
    if record['kind'] == 'observation' and record['data'].get('contract_version') == HOST_VALUES_VERSION:
        validate_values(record['data'])
    if 'retention_definition' in record:
        declaration = validate_retention({'retention': record['retention_definition']})
        if declaration is None or record['kind'] != 'observation':
            raise ConfigError('retention_definition requires an observation and a declaration')
        if declaration['contract'] != 'host-values':
            from retention_contracts import validate_payload
            validate_payload((declaration['contract'], declaration['version']), record['data'])
    if record['kind'] == 'operation':
        data = record['data']
        if data.get('phase') not in ('intent', 'result') or data.get('access_mode') not in ('write', 'unknown') or data.get('status') not in ('unknown', 'success', 'partial', 'failed', 'skipped', 'unsupported'):
            raise ConfigError('invalid operation lifecycle event')
        if data['phase'] == 'result' and not isinstance(data.get('intent_id'), str):
            raise ConfigError('operation result requires intent_id')
        if 'source_observation_id' in data:
            from retention_replay import source_identity
            source_identity(data)
    if origin['record_id'] != record['record_id']:
        raise ConfigError('record ID must preserve its original identity')
    endpoint = {key: origin[key] for key in ('namespace', 'host_id')}
    for item in record['mappings']:
        if not isinstance(item, dict) or set(item) != {'from', 'to', 'mapped_at', 'basis'}:
            raise ConfigError('invalid identity mapping')
        for end in ('from', 'to'):
            if not isinstance(item[end], dict) or set(item[end]) != {'namespace', 'host_id'}:
                raise ConfigError('invalid mapping endpoint')
            validate_settings(item[end])
            component(item[end]['host_id'])
        timestamp(item['mapped_at'])
        if not isinstance(item['basis'], str) or not item['basis']:
            raise ConfigError('mapping basis is required')
        if item['from'] != endpoint:
            raise ConfigError('identity mapping chain is discontinuous')
        endpoint = item['to']
    if endpoint != {key: record[key] for key in ('namespace', 'host_id')}:
        raise ConfigError('management identity differs from origin without a mapping')
    canonical(record)
    return record

def envelope(root, kind, host, recipe, time, data, identifier=None, source=None, reference=None):
    from opsfeast.identity import read_identity
    from observation_store import timestamp
    config = settings(root)
    if config is None:
        raise ConfigError('retention requires a namespace; initialize the profile first')
    instance = read_identity(REPOSITORY_ROOT)['id']
    identifier = identifier or str(uuid4())
    return validate_record({'contract_version': VERSION, 'record_id': identifier, 'kind': kind,
                           'namespace': config['namespace'], 'host_id': host, 'recipe_id': recipe, 'recipe_reference': reference or recipe,
                           'observed_at': timestamp(time), 'origin': {'namespace': config['namespace'],
                           'host_id': host, 'instance_id': instance, 'source_id': source or instance,
                           'record_id': identifier}, 'data': data, 'mappings': []})

def insert(connection, record):
    validate_record(record)
    payload = canonical(record)
    row = connection.execute('SELECT payload FROM records WHERE record_id=?', (record['record_id'],)).fetchone()
    if row:
        if row[0] != payload:
            old = json.loads(row[0])
            without_provenance = {k: v for k, v in record.items() if k != 'retention_provenance'}
            if 'retention_provenance' not in old and without_provenance == old:
                # Add missing provenance only; never change a historical business value.
                mode = 'read' if old['kind'] == 'observation' and old['recipe_id'] == 'inventory-system' else 'unknown'
                if record['retention_provenance']['execution_access_mode'] != mode:
                    raise ConfigError('legacy execution classification cannot be changed')
                connection.execute('UPDATE records SET payload=? WHERE record_id=?', (payload, record['record_id']))
                return False
            if 'retention_provenance' in old and {k: v for k, v in old.items() if k != 'retention_provenance'} == record:
                return False
            raise ConfigError('vault record ID/content conflict')
        return False
    connection.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?)',
                       tuple(record[k] for k in ('record_id', 'kind', 'namespace', 'host_id', 'recipe_id', 'observed_at')) + (payload,))
    return True

def archive_path(root, record):
    return retention_checked(root, 'hosts', component(record['host_id']), record['observed_at'][:4], 'observations.sqlite3')

def save(root, record, dry_run=False, *, refresh=True):
    """Authoritative commit first. View failures never roll it back; replay repairs views."""
    validate_record(record)
    reject_old_layout(root)
    if dry_run:
        existing = records(root)
        for old in existing:
            if old['record_id'] != record['record_id']:
                continue
            candidate = json.loads(canonical(record))
            candidate['origin']['instance_id'] = old['origin']['instance_id']
            if old['origin']['instance_id'] == '00000000-0000-0000-0000-000000000000':
                candidate['recipe_reference'] = old['recipe_reference']
            missing_new = {k: v for k, v in candidate.items() if k != 'retention_provenance'}
            missing_old = {k: v for k, v in old.items() if k != 'retention_provenance'}
            upgrade = 'retention_provenance' not in old and missing_new == old and observation_mode(old) == observation_mode(candidate)
            if candidate != old and not upgrade and missing_old != candidate:
                raise ConfigError('vault record ID/content conflict')
        return {'status': 'validated', 'record_id': record['record_id'],
                'source_observation_id': observation_source(record), 'execution_access_mode': observation_mode(record)}
    with locked(root):
        for old in records(root):
            if old['record_id'] == record['record_id'] and archive_path(root, old) != archive_path(root, record):
                raise ConfigError('record ID already belongs to another host/year')
        with database(archive_path(root, record), True) as connection:
            previous = connection.execute('SELECT payload FROM records WHERE record_id=?', (record['record_id'],)).fetchone()
            if previous:
                existing = json.loads(previous[0])
                # Replaying identical source evidence after reinstall preserves its original producer.
                candidate = json.loads(canonical(record))
                candidate['origin']['instance_id'] = existing['origin']['instance_id']
                if existing['origin']['instance_id'] == '00000000-0000-0000-0000-000000000000':
                    candidate['recipe_reference'] = existing['recipe_reference']
                legacy_upgrade = 'retention_provenance' not in existing and {k: v for k, v in candidate.items() if k != 'retention_provenance'} == existing
                if candidate == existing or legacy_upgrade:
                    record = candidate
            added = insert(connection, record)
        rebuild_unlocked(root)
    content = refresh_content(root) if refresh else {'status': 'skipped', 'reason_code': 'deferred'}
    return {'content_update': content, 'status': 'stored' if added else 'already_stored', 'record_id': record['record_id'],
            'source_observation_id': observation_source(record), 'execution_access_mode': observation_mode(record),
            'database_path': str(archive_path(root, record))}

def archives(root):
    reject_old_layout(root)
    directory = retention_checked(root, 'hosts')
    if not directory.exists():
        return []
    paths = []
    for host in sorted(directory.iterdir()):
        if host.is_symlink():
            raise ConfigError('vault host directory is a symlink')
        if not host.is_dir():
            continue
        for year in sorted(host.iterdir()):
            if re.fullmatch(r'\d{4}', year.name):
                path = retention_checked(root, 'hosts', host.name, year.name, 'observations.sqlite3')
                if path.exists():
                    paths.append(path)
    return paths

def records(root):
    found = {}
    for path in archives(root):
        with database(path) as connection:
            for (payload,) in connection.execute('SELECT payload FROM records ORDER BY observed_at, record_id'):
                record = validate_record(json.loads(payload))
                if archive_path(root, record) != path:
                    raise ConfigError('record archive location disagrees with identity/time')
                if record['namespace'] != settings(root)['namespace']:
                    raise ConfigError('namespace differs from archive; explicit migration is required')
                if record['record_id'] in found and found[record['record_id']] != record:
                    raise ConfigError('conflicting archived record')
                found[record['record_id']] = record
    return sorted(found.values(), key=lambda r: (r['observed_at'], r['record_id']))

def cutoff(months):
    time = datetime.now(timezone.utc)
    number = time.year * 12 + time.month - 1 - months
    year, month = divmod(number, 12)
    return time.replace(year=year, month=month + 1, day=min(time.day, calendar.monthrange(year, month + 1)[1])).isoformat(timespec='microseconds')

def replace_copy(path, items):
    # Rebuild each SQLite transactionally, never unlink a working copy first.
    with database(path, True) as connection:
        connection.execute('DELETE FROM records')
        for record in items:
            insert(connection, record)

def retain(root, raw, dry_run=False, *, saved_snapshot=None):
    from retention_contracts import normalize
    from retention_replay import select_snapshot, validate_snapshot
    selected = select_snapshot(raw) if saved_snapshot is None else validate_snapshot(saved_snapshot)
    declaration = selected['retention']
    if selected['recipe_id'] != raw.get('recipe', {}).get('id'):
        raise ConfigError('retention snapshot recipe ID mismatch')
    if declaration is None:
        return {'status': 'skipped', 'reason_code': 'no_retention_adapter'}
    if declaration['contract'] == 'host-values':
        return retain_general(root, raw, None, None, saved_snapshot=selected, dry_run=dry_run)
    from retention_replay import provenance, raw_digest, producer_identity
    reject_old_layout(root)
    # Existing validated adapter remains the authority for inventory field semantics.
    source_path = checked(root, '.retention-source.json')
    if dry_run:
        source = json.loads(source_path.read_text())['source_id'] if source_path.exists() else '00000000-0000-0000-0000-000000000001'
    else:
        with locked(root):
            if not source_path.exists():
                atomic(source_path, canonical({'source_id': str(uuid4())}) + '\n')
            source = json.loads(source_path.read_text())['source_id']
    receipt_id = (raw.get('retention') or {}).get('observation_id')
    if receipt_id is not None:
        from observation_store import uuid_text
        source = uuid_text(receipt_id.split(':', 1)[0])
    record, reason = normalize((declaration['contract'], declaration['version']), raw, source)
    if record is None:
        return {'status': 'skipped', 'reason_code': reason}
    envelope_record = envelope(root, 'observation', raw['host_id'], record['recipe_id'], record['observed_at'], record,
                               record['observation_id'], record['source_id'], raw.get('recipe', {}).get('reference'))
    envelope_record['retention_definition'] = declaration
    envelope_record['retention_provenance'] = provenance(raw, raw_digest(raw), selected)
    envelope_record['origin']['instance_id'] = producer_identity(raw)
    result = save(root, envelope_record, dry_run=dry_run)
    return dict(result, observation_id=record['observation_id'], host_key=configured_key(root, raw['host_id']),
                identity_quality='namespace-host-id')

def configured_key(root, host):
    return settings(root)['namespace'] + '/' + host

def validate_package_manifest(value):
    """Validate the future transfer contract only; never read/extract package members."""
    keys = {'contract_version', 'kind', 'created_at', 'source', 'source_instance_id', 'record_contract', 'files', 'mappings'}
    if not isinstance(value, dict) or set(value) != keys or value['contract_version'] != VERSION or value['record_contract'] != VERSION or value['kind'] != 'opsfeast-host-package':
        raise ConfigError('unsupported host package manifest')
    from observation_store import timestamp, uuid_text
    timestamp(value['created_at'])
    uuid_text(value['source_instance_id'])
    source = value['source']
    if not isinstance(source, dict) or set(source) != {'namespace', 'host_id'}:
        raise ConfigError('invalid package source')
    validate_settings(source)
    component(source['host_id'])
    if not isinstance(value['files'], list):
        raise ConfigError('invalid package file list')
    seen = set()
    for item in value['files']:
        if not isinstance(item, dict) or set(item) != {'path', 'size_bytes', 'sha256'}:
            raise ConfigError('invalid package member')
        name = item['path']
        if not isinstance(name, str) or not name or any(ord(c) < 32 for c in name) or name.startswith('/') or '\\' in name or ':' in name or any(part in ('', '.', '..') for part in name.split('/')) or name in seen:
            raise ConfigError('unsafe or duplicate package path')
        if type(item['size_bytes']) is not int or item['size_bytes'] < 0 or not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256']):
            raise ConfigError('invalid package size or digest')
        seen.add(name)
    probe = {'contract_version': VERSION, 'record_id': 'manifest-validation', 'kind': 'observation',
             'namespace': source['namespace'], 'host_id': source['host_id'], 'origin': dict(source,
             instance_id=value['source_instance_id'], source_id=value['source_instance_id'], record_id='manifest-validation'),
             'recipe_id': 'manifest', 'recipe_reference': 'manifest', 'observed_at': timestamp(value['created_at']),
             'data': {}, 'mappings': value['mappings']}
    if isinstance(value['mappings'], list) and value['mappings'] and isinstance(value['mappings'][0], dict) and isinstance(value['mappings'][0].get('from'), dict):
        probe['origin'].update(value['mappings'][0]['from'])
    validate_record(probe)
    return value

def operation_intent(root, host, metadata, descriptor_digest, variable_names, *, reference=None, implementation_digest=None, source_observation_id=None, bundle_digest=None):
    mode = metadata.get('access_mode', 'unknown')
    if mode not in ('read', 'write', 'unknown'):
        raise ConfigError('access_mode must be read, write or unknown')
    if mode == 'read' or settings(root) is None:
        return None
    data = {'phase': 'intent', 'status': 'unknown', 'access_mode': mode,
            'recipe_version': metadata['version'], 'descriptor_sha256': descriptor_digest,
            'implementation_sha256': implementation_digest, 'purpose': metadata.get('title', metadata['id']),
            'controller_user': __import__('getpass').getuser(),
            'variable_names': sorted(variable_names), 'authorization': 'caller invocation; no independently verified approval receipt',
            'verification': 'not_observed', 'verification_observation_ids': []}
    record = envelope(root, 'operation', host, metadata['id'], now(), data, reference=reference)
    if source_observation_id is not None:
        record['data']['source_observation_id'] = source_observation_id
    if bundle_digest is not None:
        record['data']['bundle_sha256'] = bundle_digest
    # Intent is committed before connection or imported recipe code can execute.
    save(root, record, refresh=False)
    return record

def validate_retention(metadata, directory=None):
    from retention_contracts import validate_declaration
    return validate_declaration(metadata, directory)


def validate_values(data):
    required = {'contract_version', 'description', 'recipe_version', 'status', 'observations'}
    if set(data) != required or data['status'] not in ('success', 'partial'):
        raise ConfigError('invalid scalar retention payload')
    if any(not isinstance(data[k], str) or not data[k].strip() for k in ('description', 'recipe_version')):
        raise ConfigError('scalar retention requires dataset semantics and recipe version')
    if not isinstance(data['observations'], dict) or not data['observations']:
        raise ConfigError('scalar retention requires observations')
    from observation_store import timestamp
    for field, item in data['observations'].items():
        if not isinstance(field, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', field):
            raise ConfigError('invalid scalar field name')
        if not isinstance(item, dict) or set(item) != {'description', 'value', 'status', 'observed_at', 'unit'}:
            raise ConfigError('invalid scalar field envelope')
        if not isinstance(item['description'], str) or not item['description'].strip() or not isinstance(item['unit'], str):
            raise ConfigError('scalar field requires semantics and unit')
        if item['status'] != ('unavailable' if item['value'] is None else 'success'):
            raise ConfigError('scalar availability contradicts its value')
        if item['value'] is not None and type(item['value']) not in (str, int, float, bool):
            raise ConfigError('retained value must be scalar')
        timestamp(item['observed_at'])
    canonical(data)
    return data


def retain_general(root, report, metadata, directory, *, saved_snapshot=None, dry_run=False):
    from retention_replay import snapshot, validate_snapshot, source_identity, raw_digest, provenance, producer_identity
    selected = validate_snapshot(saved_snapshot) if saved_snapshot is not None else snapshot(metadata, directory)
    if selected['recipe_id'] != report.get('recipe', {}).get('id', selected['recipe_id']):
        raise ConfigError('retention snapshot recipe ID mismatch')
    declaration = selected['retention']
    if declaration is not None and declaration['contract'] != 'host-values':
        raise ConfigError('scalar retention requires host-values; use retain for registered structured data')
    if declaration is None or settings(root) is None:
        return {'status': 'skipped', 'reason_code': 'no_retention_adapter'}
    if report['status'] not in ('success', 'partial') or report['evidence_kind'] not in ('local', 'ssh'):
        return {'status': 'skipped', 'reason_code': 'result_not_retained'}
    fields = {}
    for name, spec in declaration['fields'].items():
        value = report['data'].get(name)
        types = {'string': str, 'number': (int, float), 'integer': int, 'boolean': bool}
        if value is not None and (not isinstance(value, types[spec['type']]) or spec['type'] in ('number', 'integer') and isinstance(value, bool)):
            raise ConfigError('retained field type differs from declaration')
        fields[name] = {'description': spec['description'], 'value': value, 'status': 'success' if value is not None else 'unavailable',
                        'observed_at': report['completed_at'], 'unit': spec['unit']}
    recipe_version = report.get('recipe', {}).get('recipe_version', report.get('recipe', {}).get('version', selected['recipe_version']))
    data = {'contract_version': HOST_VALUES_VERSION, 'description': declaration['description'], 'recipe_version': recipe_version, 'status': report['status'],
            'observations': fields}
    identifier = source_identity(report, raw_digest(report))
    record = envelope(root, 'observation', report['host_id'], selected['recipe_id'], report['completed_at'], data,
                      identifier, reference=report['recipe'].get('reference'))
    record['retention_definition'] = declaration
    record['retention_provenance'] = provenance(report, identifier, selected)
    record['origin']['instance_id'] = producer_identity(report)
    return save(root, record, dry_run=dry_run)

def observation_source(record):
    if record['kind'] == 'operation':
        return record['data'].get('source_observation_id', record['record_id'])
    fallback = record['record_id'].split(':')[-1] if record['recipe_id'] == 'inventory-system' else record['record_id']
    return record.get('retention_provenance', {}).get('source_observation_id', fallback)

def observation_mode(record):
    if record['kind'] == 'operation':
        return record['data']['access_mode']
    return record.get('retention_provenance', {}).get('execution_access_mode',
        'read' if record['recipe_id'] == 'inventory-system' else 'unknown')

def delete_observation(root, source, dry_run=False):
    """Explicitly remove only read observations; audit records are never deletable."""
    if settings(root) is None:
        raise ConfigError('delete requires a namespace-enabled vault')
    def plan():
        all_records = records(root)
        targets = [r for r in all_records if source in (observation_source(r), r['record_id'])]
        sources = {observation_source(r) for r in targets}
        linked = [r for r in all_records if observation_source(r) in sources]
        target_ids = sources | {r['record_id'] for r in targets}
        if any(r['kind'] == 'operation' and target_ids.intersection(r['data'].get('verification_observation_ids', [])) for r in all_records):
            raise ConfigError('observation is referenced by a protected operation journal')
        if any(r['kind'] == 'operation' or observation_mode(r) != 'read' for r in targets + linked):
            raise ConfigError('write/unknown observations and operation journals cannot be deleted')
        return all_records, targets
    if dry_run:
        _, targets = plan()
        return {'status': 'validated', 'dry_run': True, 'records': [r['record_id'] for r in targets]}
    with locked(root):
        _, targets = plan()
        for record in targets:
            with database(archive_path(root, record), True) as connection:
                connection.execute('DELETE FROM records WHERE record_id=?', (record['record_id'],))
        rebuild_unlocked(root, extra_hosts={r['host_id'] for r in targets})
    content = refresh_content(root)
    return {'content_update': content, 'status': 'deleted' if targets else 'not_found', 'records': [r['record_id'] for r in targets]}

def operation_result(root, intent, report, observation_ids=()):
    if intent is None:
        return
    data = dict(intent['data'], phase='result', intent_id=intent['record_id'],
                status=report['status'], completed_at=now(), reason_code=report.get('reason_code', 'unknown'),
                verification='evidence_linked' if observation_ids else 'not_observed',
                verification_observation_ids=list(observation_ids))
    # Every lifecycle event is append-only; its year follows the intent year.
    result = envelope(root, 'operation', intent['host_id'], intent['recipe_id'], intent['observed_at'], data,
                      reference=intent['recipe_reference'])
    save(root, result, refresh=False)

def initialize(root, namespace=None, months=None, *, profile=None):
    reject_old_layout(root)
    namespace = choose_namespace(root, namespace, profile)
    with locked(root):
        enable_configuration(root, namespace, months)
        result = rebuild_unlocked(root)
    result['content_update'] = refresh_content(root)
    return result


def reject_old_layout(root):
    root = Path(root)
    if not root.exists():
        return
    old = checked(root, 'vault')
    if old.exists() and any(old.rglob('*.sqlite3')):
        raise ConfigError('old vault SQLite layout is incompatible; preserve the old profile and notes, initialize a separate profile with the same namespace, and replay selected raw with retention ingest; no files were moved or deleted')


def rebuild_unlocked(root, extra_hosts=()):
    config = settings(root)
    if config is None:
        raise ConfigError('retention requires a namespace; initialize the profile first')
    items = records(root)
    manifest = retention_checked(root, '.projections.json')
    previous = json.loads(manifest.read_text()) if manifest.exists() else []
    if not isinstance(previous, list) or any(not isinstance(host, str) for host in previous):
        raise ConfigError('invalid retention projection manifest')
    hosts = set(previous) | set(extra_hosts) | {r['host_id'] for r in items}
    for host in hosts:
        replace_copy(retention_checked(root, 'hosts', component(host), 'records', 'observations.sqlite3'),
                     [r for r in items if r['host_id'] == host])
    recent = [r for r in items if r['kind'] == 'observation' and r['observed_at'] >= cutoff(config['overview_months'])]
    replace_copy(retention_checked(root, 'overview', 'observations.sqlite3'), recent)
    atomic(manifest, canonical(sorted(hosts)) + '\n')
    return {'status': 'success', 'retention_directory': str(retention_checked(root)), 'hosts': len(hosts),
            'records': len(items), 'overview_records': len(recent)}


def rebuild(root):
    with locked(root):
        return rebuild_unlocked(root)


def refresh_content(root):
    if not settings(root)['vault']['auto_refresh']:
        return {'status': 'skipped', 'reason_code': 'auto_refresh_disabled'}
    try:
        from host_vault import rebuild
        result = rebuild(root)
        return result
    except Exception as exc:
        return {'status': 'failed', 'reason_code': 'content_update_failed', 'error_type': type(exc).__name__,
                'recovery': 'opsfeast.py vault rebuild --root ' + shlex.quote(str(root)) + ' --json'}


def query(root, *, hosts=None, recipe=None, since=None, until=None, status=None, kind=None):
    """Read validated authoritative records; never creates directories or projections."""
    from observation_store import timestamp
    if settings(root) is None:
        raise ConfigError('retention requires a namespace; initialize the profile first')
    since, until = timestamp(since) if since else None, timestamp(until) if until else None
    if since and until and since > until:
        raise ConfigError('since must not follow until')
    if status is not None and status not in ('success', 'partial', 'failed', 'skipped', 'unsupported', 'unknown'):
        raise ConfigError('invalid retention status')
    if kind is not None and kind not in ('observation', 'operation'):
        raise ConfigError('invalid retention kind')
    if isinstance(hosts, str):
        raise ConfigError('hosts must be a sequence of IDs, not a string')
    selected = [r for r in records(root) if (not hosts or r['host_id'] in hosts)
                and (recipe is None or r['recipe_reference'] == recipe)
                and (since is None or r['observed_at'] >= since)
                and (until is None or r['observed_at'] <= until)
                and (status is None or r['data'].get('status') == status)
                and (kind is None or r['kind'] == kind)]
    return {'contract_version': VERSION, 'kind': 'opsfeast-retention', 'status': 'success',
            'namespace': settings(root)['namespace'], 'records': selected}


def show(root, record_id):
    selected = [r for r in query(root)['records'] if r['record_id'] == record_id]
    if not selected:
        raise ConfigError('retention record not found')
    return selected[0]


class Reader:
    """Read-only report input facade; no session or write API."""
    def __init__(self, root):
        self._root = Path(root)
        self.sources = []

    def query(self, **filters):
        result = query(self._root, **filters)
        self.sources.append({'selection': filters, 'sha256': hashlib.sha256(canonical(result).encode()).hexdigest(),
                             'records': [{'record_id': r['record_id'], 'recipe_reference': r['recipe_reference'], 'observed_at': r['observed_at']} for r in result['records']]})
        return result

    def show(self, record_id):
        result = show(self._root, record_id)
        self.sources.append({'record_id': record_id, 'sha256': hashlib.sha256(canonical(result).encode()).hexdigest(), 'observed_at': result['observed_at']})
        return result


def describe(metadata, directory=None):
    declaration = validate_retention(metadata, directory)
    result = {'declaration': declaration, 'availability': 'declared; execution and retention success must be checked' if declaration else 'not_declared',
            'cli': 'opsfeast.py retention list --recipe SOURCE_QUALIFIED_REFERENCE --profile PROFILE --json',
            'python': 'retention_store.query(profile.root, recipe=SOURCE_QUALIFIED_REFERENCE)'}
    if declaration and declaration['contract'] != 'host-values':
        from retention_contracts import location, normalizer_digest, schema_digest
        module, schema = location((declaration['contract'], declaration['version']))
        result.update(schema_path=str(Path(directory) / declaration['schema']) if directory else str(schema), schema_sha256=schema_digest(declaration),
                      normalizer={'sha256': normalizer_digest(declaration), 'source': str(module), 'execution': 'registered bundled code only; no candidate imports'})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('action', choices=('list', 'show', 'export', 'ingest', 'delete-observation', 'rebuild', 'inspect'))
    parser.add_argument('files', nargs='*')
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--root')
    choice.add_argument('--profile')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--host', action='append')
    parser.add_argument('--recipe', help='exact source-qualified recipe reference')
    parser.add_argument('--since')
    parser.add_argument('--until')
    parser.add_argument('--status')
    parser.add_argument('--kind', choices=('observation', 'operation'))
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--recipe-dir', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = resolve_root(args.root, args.profile).resolve(strict=True)
        filters = dict(hosts=args.host, recipe=args.recipe, since=args.since, until=args.until, status=args.status, kind=args.kind)
        if args.action not in ('list', 'export') and any(v is not None for v in filters.values()):
            raise ConfigError('query filters require list/export')
        if args.action not in ('ingest', 'delete-observation') and (args.all or args.recipe_dir or args.dry_run):
            raise ConfigError('all/recipe-dir/dry-run require ingest/delete-observation')
        if args.action in ('list', 'export'):
            if args.files:
                raise ConfigError('list/export do not accept positional files')
            result = query(root, **filters)
        elif args.action == 'show':
            if len(args.files) != 1:
                raise ConfigError('show requires exactly one record ID')
            result = show(root, args.files[0])
        elif args.action == 'ingest':
            from retention_replay import ingest
            result = ingest(root, args.files, all_files=args.all, recipe_directory=args.recipe_dir, dry_run=args.dry_run)
        elif args.action == 'delete-observation':
            if len(args.files) != 1 or args.all or args.recipe_dir:
                raise ConfigError('delete-observation requires one ID and no all/recipe-dir')
            result = delete_observation(root, args.files[0], args.dry_run)
        else:
            if args.files:
                raise ConfigError('unexpected positional arguments')
            result = rebuild(root) if args.action == 'rebuild' else dict(query(root), settings=settings(root), retention_directory=str(retention_checked(root)))
        print(json.dumps(result, ensure_ascii=False))
        return 1 if result.get('status') == 'failed' or result.get('content_update', {}).get('status') == 'failed' else 0
    except (ConfigError, OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__,
                          'message': str(exc) if isinstance(exc, ConfigError) else 'retention operation failed'}), file=__import__('sys').stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
