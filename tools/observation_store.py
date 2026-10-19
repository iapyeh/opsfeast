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
    """Inventory-only exchange adapter; creator-owned normalization is registered by contract."""
    from retention_contracts import normalize, INVENTORY_CONTRACT
    return normalize(INVENTORY_CONTRACT, raw, source)


def validate_record(record):
    """Validate the registered inventory retained-data contract."""
    from retention_contracts import validate_payload, INVENTORY_CONTRACT
    validate_payload(INVENTORY_CONTRACT, record)


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
    from retention_store import settings as vault_settings, retain as vault_retain
    if vault_settings(root) is not None:
        return vault_retain(root, raw)
    with database(root, write=True) as connection:
        record, reason = extract(raw, source_id(connection))
        added = insert(connection, record)
    return {'status': 'stored' if added else 'already_stored', 'observation_id': record['observation_id'],
            'host_key': record['host_key'], 'identity_quality': record['identity_quality'], 'database_path': str(store_path(root))}


def export(root, *, recipe=None, hosts=None, since=None, until=None):
    from retention_store import settings as vault_settings, records as vault_records
    if vault_settings(root) is not None:
        since = timestamp(since) if since else None
        until = timestamp(until) if until else None
        if since and until and since > until:
            raise ConfigError('since must not follow until')
        selected = [item['data'] for item in vault_records(root)
                    if item['kind'] == 'observation' and item['recipe_id'] == 'inventory-system'
                    and (recipe is None or item['recipe_id'] == recipe)
                    and (not hosts or item['host_id'] in hosts)
                    and (since is None or item['observed_at'] >= since)
                    and (until is None or item['observed_at'] <= until)]
        bundle = {'exchange_version': VERSION, 'kind': 'opsfeast-observations',
                  'exported_at': datetime.now(timezone.utc).isoformat(), 'records': selected}
        validate_exchange(bundle)
        return bundle
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
    outgoing.add_argument('--format', choices=('json', 'csv'), default='json', help='CSV missing values are empty cells; JSON remains the exchange format')
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
                from retention_store import settings as vault_settings
                if vault_settings(root) is not None:
                    from retention_store import retain as retain_data
                    for raw in raws:
                        retain_data(root, raw, dry_run=True)
                    result = {'files': [retain(root, raw) for raw in raws]}
                    print(json.dumps(result, ensure_ascii=False))
                    return 1 if any(r.get('content_update', {}).get('status') == 'failed' for r in result['files']) else 0
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
        if args.command == 'export' and args.format == 'csv':
            import csv
            import io
            from inventory_values import csv_text, empty
            writer = csv.writer(sys.stdout)
            writer.writerow(('observation_id', 'host_id', 'observed_at', 'identity_quality', 'collection_mode', 'effective_uid', 'section', 'field', 'item', 'attribute', 'value'))
            for record in result['records']:
                data = record.get('inventory')
                if data is None:
                    data = empty()
                    for field, item in record['observations'].items():
                        data['system'][field] = item['value']
                rows = csv.reader(io.StringIO(csv_text(data)))
                next(rows)
                scope = record.get('collection_scope', {})
                def safe(value):
                    return "'" + value if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else value
                prefix = [safe(record[key]) for key in ('observation_id', 'host_id', 'observed_at', 'identity_quality')] + [scope.get('mode', 'unverified'), scope.get('effective_uid')]
                for row in rows:
                    writer.writerow(prefix + row)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ConfigError, OSError, ValueError, TypeError, AttributeError, sqlite3.Error) as exc:
        print('ERROR: ' + (str(exc) if isinstance(exc, ConfigError) else type(exc).__name__), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
