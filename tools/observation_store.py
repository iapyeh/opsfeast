"""Stage 2 retained observations and stage 3 portable, validated JSON exchange."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from uuid import UUID, uuid4

from opsfeast import ConfigError, resolve_root
from recipe_dispatch import validate_observations

VERSION = '0.1.0'
FIELDS = ('hostname', 'platform', 'system_name', 'system_version', 'kernel_name', 'kernel_release', 'architecture')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def timestamp(value):
    if not isinstance(value, str):
        raise ConfigError('timestamp must be an ISO-8601 string with timezone')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ConfigError('invalid timestamp') from None
    if parsed.tzinfo is None:
        raise ConfigError('timestamp requires timezone')
    return parsed.astimezone(timezone.utc).isoformat(timespec='microseconds')


def nonempty(value, label):
    if not isinstance(value, str) or not value or '\x00' in value:
        raise ConfigError(f'{label} must be a nonempty string')
    return value


def uuid_text(value):
    try:
        if str(UUID(value)) != value:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ConfigError('invalid source UUID') from None
    return value


def store_path(root):
    root = Path(root).resolve(strict=True)
    directory = root / 'records'
    path = directory / 'observations.sqlite3'
    for item in (directory, path):
        if item.is_symlink():
            raise ConfigError('retained observation storage refuses symlinks')
    if directory.exists() and not directory.is_dir() or path.exists() and not path.is_file():
        raise ConfigError('invalid retained observation storage')
    # SQLite sidecars must not redirect writes either.
    for suffix in ('-journal', '-wal', '-shm'):
        if Path(str(path) + suffix).is_symlink():
            raise ConfigError('retained observation storage refuses sidecar symlinks')
    return path


@contextmanager
def database(root, write=False):
    path = store_path(root)
    if write:
        path.parent.mkdir(exist_ok=True)
        connection = sqlite3.connect(path, timeout=30)
    else:
        if not path.exists():
            raise ConfigError('no retained observation database; run inventory or ingest raw results first')
        connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=30)
    try:
        if write:
            connection.execute('BEGIN IMMEDIATE')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, 2):
                raise ConfigError('unsupported retained database version')
            if version == 0:
                connection.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
                connection.execute('CREATE TABLE observations (observation_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, host_id TEXT NOT NULL, host_key TEXT NOT NULL, recipe_id TEXT NOT NULL, observed_at TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL)')
                connection.execute('CREATE INDEX observation_selection ON observations(recipe_id, host_id, observed_at)')
                connection.execute('INSERT INTO metadata VALUES (?, ?)', ('source_id', str(uuid4())))
            if version in (0, 1):
                columns = ', '.join("json_extract(payload, '$.observations." + field + ".value') AS " + field + ", json_extract(payload, '$.observations." + field + ".status') AS " + field + '_status' for field in FIELDS)
                connection.execute('DROP VIEW IF EXISTS inventory_system')
                connection.execute('CREATE VIEW inventory_system AS SELECT observation_id, source_id, host_id, host_key, observed_at, status, ' + columns + ", COALESCE(NULLIF(json_extract(payload, '$.label'), ''), host_id) AS label, json_extract(payload, '$.description') AS description FROM observations WHERE recipe_id='inventory-system'")
                connection.execute('PRAGMA user_version=2')
        if connection.execute('PRAGMA user_version').fetchone()[0] not in (1, 2):
            raise ConfigError('unsupported retained database version')
        yield connection
        if write:
            connection.commit()
    except BaseException:
        if write:
            connection.rollback()
        raise
    finally:
        connection.close()


def source_id(connection):
    row = connection.execute("SELECT value FROM metadata WHERE key='source_id'").fetchone()
    if row is None:
        raise ConfigError('retained database has no source identity')
    return uuid_text(row[0])


def fallback_key(source, host):
    return 'fallback:' + source + ':' + hashlib.sha256(host.encode()).hexdigest()


def extract(raw, source):
    """Allowlisted inventory adapter: no execution details or arbitrary adapters."""
    if not isinstance(raw, dict):
        raise ConfigError('raw result must be an object')
    if raw.get('status') in ('failed', 'skipped', 'unsupported'):
        return None, 'result_not_retained'
    if raw.get('evidence_kind') not in ('local', 'ssh'):
        return None, 'non_operational_evidence'
    receipt_id = (raw.get('retention') or {}).get('observation_id')
    if receipt_id is not None and not receipt_id.startswith(source + ':'):
        raise ConfigError('raw result belongs to another source; exchange structured data instead')
    if raw.get('schema_version') != '0.2.0' or raw.get('recipe', {}).get('id') != 'inventory-system':
        raise ConfigError('no retained adapter for this recipe/result contract')
    if raw.get('status') not in ('success', 'partial') or raw.get('execution_errors'):
        raise ConfigError('inconsistent raw result status')
    validate_observations(raw)
    states = [item['status'] for item in raw['observations'].values()]
    if raw['status'] == 'success' and any(state != 'success' for state in states) or raw['status'] == 'partial' and ('success' not in states or all(state == 'success' for state in states)):
        raise ConfigError('raw status contradicts observation states')
    host = nonempty(raw.get('host_id'), 'host_id')
    started, finished = timestamp(raw.get('started_at')), timestamp(raw.get('finished_at'))
    if finished < started:
        raise ConfigError('raw completion precedes start')
    observations = {field: {'value': item['value'], 'status': item['status'],
                            'observed_at': timestamp(item['observed_at']) if item['observed_at'] else None}
                    for field, item in raw['observations'].items()}
    identity = raw.get('identity', {})
    method = identity.get('method')
    key = identity.get('os_instance_key')
    derived = (identity.get('schema_version') == VERSION and method == 'linux-machine-id-hmac-sha256-v1'
               and identity.get('quality') == 'machine-derived' and isinstance(key, str)
               and len(key) == 70 and key.startswith('linux:')
               and all(c in '0123456789abcdef' for c in key[6:]))
    assigned = identity.get('identity_key')
    user_assigned = (identity.get('schema_version') == VERSION and method == 'configured-identity-key-v1'
                     and identity.get('quality') == 'user-assigned' and isinstance(assigned, str))
    if method == 'configured-identity-key-v1' and not user_assigned:
        raise ConfigError('invalid configured identity contract')
    if user_assigned:
        key = 'user:' + hashlib.sha256(assigned.encode()).hexdigest()
        if identity.get('os_instance_key') != key:
            raise ConfigError('configured identity evidence/key mismatch')
    evidence = []
    for item in identity.get('evidence', []):
        if item.get('scope') == 'device' and item.get('status') == 'success' and item.get('kind') in ('system-serial', 'enclosure-serial', 'hardware-uuid'):
            evidence.append({'kind': item['kind'], 'scope': 'device', 'value': nonempty(item.get('value'), 'identifier'),
                             'observed_at': timestamp(item.get('observed_at'))})
    identity_raw = {key: value for key, value in raw.items() if key != 'retention'}
    record = {'contract_version': VERSION, 'observation_id': source + ':' + hashlib.sha256(canonical(identity_raw).encode()).hexdigest(),
              'source_id': source, 'host_id': host, 'host_key': key if derived or user_assigned else fallback_key(source, host),
              'identity_method': method if derived or user_assigned else 'source-host-id',
              'identity_quality': 'user-assigned' if user_assigned else 'machine-derived' if derived else 'fallback',
              'identity_evidence': evidence,
              'identity_warning': ('User-assigned key is an assertion, not machine verification; coordinate names and change after reinstall/replacement.' if user_assigned else 'Machine-derived Linux ID may be duplicated by clones or preserved across reinstallations.' if derived else 'Source-scoped fallback cannot establish cross-installation identity or replacement.'),
              'recipe_id': 'inventory-system', 'recipe_version': nonempty(raw['recipe'].get('recipe_version', raw['recipe'].get('version')), 'recipe_version'),
              'raw_schema_version': '0.2.0', 'started_at': started, 'observed_at': finished,
              'evidence_kind': raw['evidence_kind'], 'status': raw['status'], 'observations': observations}
    if user_assigned:
        record['identity_key'] = assigned
    metadata = raw.get('host_metadata', {})
    if not isinstance(metadata, dict) or set(metadata) - {'label', 'description'}:
        raise ConfigError('invalid host display metadata')
    record.update(metadata)
    validate_record(record)
    return record, None


def validate_record(record):
    required = {'contract_version', 'observation_id', 'source_id', 'host_id', 'host_key', 'identity_method', 'identity_quality', 'identity_evidence', 'identity_warning', 'recipe_id', 'recipe_version', 'raw_schema_version', 'started_at', 'observed_at', 'evidence_kind', 'status', 'observations'}
    if not isinstance(record, dict) or not required.issubset(record) or set(record) - required - {'identity_key', 'label', 'description'}:
        raise ConfigError('invalid retained record fields')
    for name in ('label', 'description'):
        if name in record and (not isinstance(record[name], str) or '\x00' in record[name]):
            raise ConfigError('invalid host display metadata')
    source = uuid_text(record['source_id'])
    for name in ('host_id', 'host_key', 'recipe_version', 'identity_warning'):
        nonempty(record[name], name)
    digest = record['observation_id']
    if not isinstance(digest, str) or not digest.startswith(source + ':') or len(digest) != 101 or any(c not in '0123456789abcdef' for c in digest[37:]):
        raise ConfigError('invalid observation ID')
    if record['contract_version'] != VERSION or record['recipe_id'] != 'inventory-system' or record['raw_schema_version'] != '0.2.0' or record['evidence_kind'] not in ('local', 'ssh') or record['status'] not in ('success', 'partial'):
        raise ConfigError('unsupported retained contract or state')
    for name in ('started_at', 'observed_at'):
        if timestamp(record[name]) != record[name]:
            raise ConfigError('retained timestamps must use canonical UTC')
    if record['observed_at'] < record['started_at']:
        raise ConfigError('completion precedes start')
    if record['identity_quality'] == 'user-assigned':
        assigned = nonempty(record.get('identity_key'), 'identity_key')
        if assigned != assigned.strip() or any(ord(char) < 32 for char in assigned):
            raise ConfigError('invalid user-assigned identity key')
        if record['identity_method'] != 'configured-identity-key-v1' or record['host_key'] != 'user:' + hashlib.sha256(assigned.encode()).hexdigest():
            raise ConfigError('invalid user-assigned identity')
    elif record['identity_quality'] == 'fallback':
        if record['identity_method'] != 'source-host-id' or record['host_key'] != fallback_key(source, record['host_id']):
            raise ConfigError('invalid fallback identity')
    elif record['identity_quality'] == 'machine-derived':
        key = record['host_key']
        if record['identity_method'] != 'linux-machine-id-hmac-sha256-v1' or not key.startswith('linux:') or len(key) != 70 or any(c not in '0123456789abcdef' for c in key[6:]):
            raise ConfigError('invalid machine-derived identity')
    else:
        raise ConfigError('unsupported identity quality')
    if record['identity_quality'] != 'user-assigned' and 'identity_key' in record:
        raise ConfigError('identity_key requires user-assigned identity')
    if not isinstance(record['identity_evidence'], list):
        raise ConfigError('identity evidence must be a list')
    for item in record['identity_evidence']:
        if not isinstance(item, dict) or set(item) != {'kind', 'scope', 'value', 'observed_at'} or item['scope'] != 'device' or item['kind'] not in ('system-serial', 'enclosure-serial', 'hardware-uuid'):
            raise ConfigError('invalid device evidence')
        nonempty(item['value'], 'device identifier')
        if timestamp(item['observed_at']) != item['observed_at']:
            raise ConfigError('invalid evidence timestamp')
    observations = record['observations']
    if not isinstance(observations, dict) or set(observations) != set(FIELDS):
        raise ConfigError('invalid retained observations')
    for item in observations.values():
        if not isinstance(item, dict) or set(item) != {'value', 'status', 'observed_at'}:
            raise ConfigError('invalid retained observation fields')
        if item['observed_at'] is not None and timestamp(item['observed_at']) != item['observed_at']:
            raise ConfigError('invalid field timestamp')
    validate_observations({'observations': {name: dict(item, source_ids=[], error=None) for name, item in observations.items()}})
    states = [item['status'] for item in observations.values()]
    if any(item['status'] == 'success' and item['observed_at'] is None for item in observations.values()):
        raise ConfigError('successful observation requires time')
    if record['status'] == 'success' and any(state != 'success' for state in states) or record['status'] == 'partial' and ('success' not in states or all(state == 'success' for state in states)):
        raise ConfigError('retained status contradicts observations')


def insert(connection, record):
    validate_record(record)
    payload = canonical(record)
    old = connection.execute('SELECT payload FROM observations WHERE observation_id=?', (record['observation_id'],)).fetchone()
    if old:
        if old[0] != payload:
            raise ConfigError('observation ID conflicts with existing content')
        return False
    connection.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?)', tuple(record[k] for k in ('observation_id', 'source_id', 'host_id', 'host_key', 'recipe_id', 'observed_at', 'status')) + (payload,))
    return True


def retain(root, raw):
    # Excluded results do not create a database or a new source identity.
    if raw.get('status') not in ('success', 'partial'):
        return {'status': 'skipped', 'reason_code': 'result_not_retained'}
    if raw.get('evidence_kind') not in ('local', 'ssh'):
        return {'status': 'skipped', 'reason_code': 'non_operational_evidence'}
    with database(root, write=True) as connection:
        record, reason = extract(raw, source_id(connection))
        added = insert(connection, record)
    return {'status': 'stored' if added else 'already_stored', 'observation_id': record['observation_id'],
            'host_key': record['host_key'], 'identity_quality': record['identity_quality'], 'database_path': str(store_path(root))}


def export(root, *, recipe=None, hosts=None, since=None, until=None):
    since = timestamp(since) if since else None
    until = timestamp(until) if until else None
    if since and until and since > until:
        raise ConfigError('since must not follow until')
    clauses, args = [], []
    for column, value, operator in (('recipe_id', recipe, '='), ('observed_at', since, '>='), ('observed_at', until, '<=')):
        if value is not None:
            clauses.append(column + operator + '?')
            args.append(value)
    if hosts:
        clauses.append('host_id IN (' + ','.join('?' for _ in hosts) + ')')
        args.extend(hosts)
    with database(root) as connection:
        rows = connection.execute('SELECT payload FROM observations' + (' WHERE ' + ' AND '.join(clauses) if clauses else '') + ' ORDER BY observed_at, observation_id', args)
        records = [json.loads(row[0]) for row in rows]
    bundle = {'exchange_version': VERSION, 'kind': 'opsfeast-observations',
              'exported_at': datetime.now(timezone.utc).isoformat(), 'records': records}
    validate_exchange(bundle)
    return bundle


def validate_exchange(bundle):
    if not isinstance(bundle, dict) or set(bundle) != {'exchange_version', 'kind', 'exported_at', 'records'} or bundle['exchange_version'] != VERSION or bundle['kind'] != 'opsfeast-observations' or not isinstance(bundle['records'], list):
        raise ConfigError('invalid or unsupported exchange envelope')
    timestamp(bundle['exported_at'])
    seen = set()
    for record in bundle['records']:
        validate_record(record)
        if record['observation_id'] in seen:
            raise ConfigError('duplicate observation ID in exchange')
        seen.add(record['observation_id'])
    return len(seen)


def combine(bundles):
    """Union compatible exchange records; never collapse histories by host key."""
    records = {}
    for bundle in bundles:
        validate_exchange(bundle)
        for record in bundle['records']:
            key = record['observation_id']
            if key in records and canonical(records[key]) != canonical(record):
                raise ConfigError('conflicting content for shared observation ID')
            records[key] = record
    return {'exchange_version': VERSION, 'kind': 'opsfeast-observations',
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'records': sorted(records.values(), key=lambda record: (record['observed_at'], record['observation_id']))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest='command', required=True)
    ingest = sub.add_parser('ingest', help='reprocess explicitly selected local raw results')
    ingest.add_argument('files', nargs='+')
    outgoing = sub.add_parser('export', help='print portable JSON; no transmission')
    outgoing.add_argument('--recipe')
    outgoing.add_argument('--host', nargs='+')
    outgoing.add_argument('--since')
    outgoing.add_argument('--until')
    for command in (ingest, outgoing):
        choice = command.add_mutually_exclusive_group()
        choice.add_argument('--root')
        choice.add_argument('--profile')
    check = sub.add_parser('validate', help='validate an exchange file without importing or executing it')
    check.add_argument('file')
    merge = sub.add_parser('combine', help='merge structured exchange files, deduplicate observations, print JSON')
    merge.add_argument('files', nargs='+')
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate':
            result = {'status': 'valid', 'records': validate_exchange(json.loads(Path(args.file).read_text(encoding='utf-8')))}
        elif args.command == 'combine':
            result = combine([json.loads(Path(name).read_text(encoding='utf-8')) for name in args.files])
        else:
            root = resolve_root(args.root, args.profile)
            if args.command == 'export':
                result = export(root, recipe=args.recipe, hosts=args.host, since=args.since, until=args.until)
            else:
                # Validate every eligible input before mutating the database.
                raws = [json.loads(Path(name).read_text(encoding='utf-8')) for name in args.files]
                preflight_source = '00000000-0000-0000-0000-000000000001'
                if store_path(root).exists():
                    with database(root) as existing:
                        preflight_source = source_id(existing)
                for raw in raws:
                    extract(raw, preflight_source)
                if all(raw.get('status') not in ('success', 'partial') or raw.get('evidence_kind') not in ('local', 'ssh') for raw in raws):
                    print(json.dumps({'files': [{'status': 'skipped', 'reason_code': extract(raw, preflight_source)[1]} for raw in raws]}))
                    return 0
                with database(root, write=True) as connection:
                    results = []
                    for raw in raws:
                        record, reason = extract(raw, source_id(connection))
                        results.append({'status': 'skipped', 'reason_code': reason} if record is None else
                                       {'status': 'stored' if insert(connection, record) else 'already_stored',
                                        'observation_id': record['observation_id'], 'host_key': record['host_key'],
                                        'identity_quality': record['identity_quality'], 'identity_warning': record['identity_warning']})
                result = {'files': results}
        if args.command in ('export', 'combine', 'ingest'):
            records = result['files'] if args.command == 'ingest' else result['records']
            fallback_count = sum(record.get('identity_quality') == 'fallback' for record in records)
            if fallback_count:
                print(f'WARNING: {fallback_count} fallback observations: source-scoped host IDs do not prove cross-source identity or host replacement. Supply authorized sudo only if permissions caused missing identity; unsupported installation identity still requires fallback. Read identity_warning and docs/result-data.md.', file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ConfigError, OSError, ValueError, TypeError, AttributeError, sqlite3.Error) as exc:
        print('ERROR: ' + (str(exc) if isinstance(exc, ConfigError) else type(exc).__name__), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
