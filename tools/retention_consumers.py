"""Consumer contract 0.1.0: static discovery and durable local event dispatch."""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import sys
import threading
from uuid import uuid4

from opsfeast import ConfigError, REPOSITORY_ROOT, definition_path, read_yaml, resolve_root

VERSION = '0.1.0'
EVENTS = {'retention.observation.created', 'retention.observation.deleted', 'retention.operation.created'}
ID = re.compile(r'[a-z][a-z0-9_-]{0,62}')
_ACTIVE = threading.local()


def registrations(data):
    if not isinstance(data, dict):
        raise ConfigError('consumer configuration requires a mapping')
    selected = data.get('consumers', {})
    if not isinstance(selected, dict):
        raise ConfigError('consumers must be a mapping')
    for name, value in selected.items():
        if not isinstance(name, str) or not ID.fullmatch(name):
            raise ConfigError('invalid consumer ID')
        if (not isinstance(value, dict) or set(value) != {'source', 'enabled'}
                or type(value['enabled']) is not bool or not isinstance(value['source'], str)):
            raise ConfigError('consumer registration requires source and Boolean enabled')
        source = value['source']
        if source.startswith('builtin:'):
            name_path = source.removeprefix('builtin:')
        elif source.startswith('local:consumers/'):
            name_path = source.removeprefix('local:consumers/')
        else:
            raise ConfigError('consumer source must be builtin:NAME or local:consumers/NAME')
        if not ID.fullmatch(name_path):
            raise ConfigError('consumer source must name one consumers/ child')
    return selected


def safe_path(base, relative):
    base = Path(base)
    path = base
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(p in ('.', '..') for p in parts):
        raise ConfigError('unsafe consumer path')
    if base.is_symlink():
        raise ConfigError('consumer refuses symlinks')
    for part in parts:
        path /= part
        if path.is_symlink():
            raise ConfigError('consumer refuses symlinks')
    if not path.resolve().is_relative_to(base.resolve()):
        raise ConfigError('consumer path escapes source')
    return path


def inspect_consumer(base, source):
    directory = safe_path(base, source.split(':', 1)[1])
    descriptor = safe_path(directory, 'consumer.yaml')
    data = read_yaml(descriptor)
    if (not isinstance(data, dict) or set(data) != {'schema_version', 'id', 'description', 'entrypoint', 'subscriptions'}
            or data['schema_version'] != VERSION or not isinstance(data['id'], str) or not ID.fullmatch(data['id'])
            or not isinstance(data['description'], str) or not data['description'].strip()
            or not isinstance(data['entrypoint'], str) or not data['entrypoint'].endswith('.py')):
        raise ConfigError('invalid consumer descriptor 0.1.0')
    entrypoint = safe_path(directory, data['entrypoint'])
    if not entrypoint.is_file():
        raise ConfigError('consumer entrypoint is missing')
    subscriptions = data['subscriptions']
    if not isinstance(subscriptions, list) or not subscriptions:
        raise ConfigError('consumer requires subscriptions')
    for subscription in subscriptions:
        if (not isinstance(subscription, dict) or set(subscription) != {'event', 'selector'}
                or not isinstance(subscription['event'], str) or subscription['event'] not in EVENTS
                or not isinstance(subscription['selector'], dict)):
            raise ConfigError('invalid consumer subscription')
        selector = subscription['selector']
        if set(selector) - {'recipe_reference', 'contract', 'version'}:
            raise ConfigError('invalid consumer selector')
        if any(not isinstance(v, str) or not v.strip() for v in selector.values()):
            raise ConfigError('consumer selectors require nonempty exact strings')
        if ('contract' in selector) != ('version' in selector):
            raise ConfigError('consumer contract/version must be selected together')
    digest = hashlib.sha256(descriptor.read_bytes() + b'\0' + entrypoint.read_bytes()).hexdigest()
    return dict(data, source=source, directory=str(directory), entrypoint_path=str(entrypoint), sha256=digest)


def catalog(root, recipe=None):
    """Read descriptors/configuration only; never import candidate code or write files."""
    root = Path(root).resolve(strict=True)
    definition = definition_path(root)
    if definition.is_symlink():
        raise ConfigError('consumer configuration refuses symlinks')
    data = read_yaml(definition) if definition.exists() else {}
    registered = registrations(data)
    vault = data.get('vault', {})
    if not isinstance(vault, dict) or set(vault) - {'auto_refresh'} or type(vault.get('auto_refresh', True)) is not bool:
        raise ConfigError('vault.auto_refresh must be boolean')
    configured = {'vault': {'source': 'builtin:vault', 'enabled': True}, **registered}
    bundled = REPOSITORY_ROOT / 'consumers'
    sources = {'builtin:vault': bundled}
    if bundled.is_dir():
        for directory in sorted(bundled.iterdir()):
            if (directory.is_dir() or directory.is_symlink()) and (directory / 'consumer.yaml').exists():
                sources['builtin:' + directory.name] = bundled
    local = safe_path(root, 'consumers')
    if local.is_dir():
        for directory in sorted(local.iterdir()):
            if (directory.is_dir() or directory.is_symlink()) and (directory / 'consumer.yaml').exists():
                sources['local:consumers/' + directory.name] = root
    for config in configured.values():
        sources.setdefault(config['source'], REPOSITORY_ROOT / 'consumers' if config['source'].startswith('builtin:') else root)
    items = []
    for source, base in sorted(sources.items()):
        item = {'source': source, 'id': None, 'enabled': False, 'registered': False, 'status': 'success', 'errors': []}
        bindings = [(name, cfg) for name, cfg in configured.items() if cfg['source'] == source]
        try:
            item.update(inspect_consumer(base, source))
            if len(bindings) > 1 or any(name != item['id'] for name, _ in bindings):
                raise ConfigError('consumer registration ID must match descriptor; one binding per source')
            item['registered'] = bool(bindings)
            item['enabled'] = bool(bindings and bindings[0][1]['enabled'])
            if item['id'] == 'vault' and source == 'builtin:vault' and not vault.get('auto_refresh', True):
                item['enabled'] = False
                item['disabled_reason'] = 'auto_refresh_disabled'
        except (ConfigError, OSError, ValueError) as exc:
            item.update(status='failed', errors=[str(exc)], registered=bool(bindings), enabled=bool(bindings and bindings[0][1]['enabled']))
            if bindings:
                item['id'] = bindings[0][0]
        if recipe is None or item.get('status') == 'failed' or any(
                s['selector'].get('recipe_reference', recipe) == recipe for s in item.get('subscriptions', [])):
            items.append(item)
    return {'contract_version': VERSION, 'status': 'failed' if any(i['status'] == 'failed' for i in items) else 'success', 'consumers': items}


def related(root, reference, declaration=None):
    result = []
    for item in catalog(root, reference)['consumers']:
        subscriptions = item.get('subscriptions', [])
        if not any(sub['selector'].get('recipe_reference', reference) == reference and
                   all(key not in sub['selector'] or sub['selector'][key] == (declaration or {}).get(key)
                       for key in ('contract', 'version')) for sub in subscriptions):
            if item['status'] != 'failed':
                continue
        result.append({k: item[k] for k in ('id', 'source', 'enabled', 'registered', 'status', 'errors')})
    return result


def event_tables(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS retention_events (event_id TEXT PRIMARY KEY, emitted_at TEXT NOT NULL, payload TEXT NOT NULL)')
    connection.execute('CREATE TABLE IF NOT EXISTS consumer_deliveries (event_id TEXT NOT NULL, consumer TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(event_id, consumer))')


def enqueue(connection, record, action):
    """Called inside the authoritative record transaction, including deletion tombstones."""
    from retention_store import canonical, now
    event_tables(connection)
    definition = record.get('retention_definition', {})
    event = {'contract_version': VERSION, 'event_id': str(uuid4()), 'event': f"retention.{record['kind']}.{action}",
             'emitted_at': now(), 'record_id': record['record_id'], 'namespace': record['namespace'],
             'host_id': record['host_id'], 'recipe_reference': record['recipe_reference'],
             'contract': definition.get('contract'), 'version': definition.get('version'), 'observed_at': record['observed_at']}
    connection.execute('INSERT INTO retention_events VALUES (?,?,?)', (event['event_id'], event['emitted_at'], canonical(event)))
    return event


def matches(item, event):
    return any(sub['event'] == event['event'] and all(event.get(k) == v for k, v in sub['selector'].items())
               for sub in item['subscriptions'])


def validate_event(event):
    from observation_store import timestamp, uuid_text
    fields = {'contract_version', 'event_id', 'event', 'emitted_at', 'record_id', 'namespace', 'host_id',
              'recipe_reference', 'contract', 'version', 'observed_at'}
    if (not isinstance(event, dict) or set(event) != fields or event['contract_version'] != VERSION
            or not isinstance(event['event'], str) or event['event'] not in EVENTS):
        raise ConfigError('invalid retention consumer event 0.1.0')
    uuid_text(event['event_id'])
    for key in ('emitted_at', 'observed_at'):
        if timestamp(event[key]) != event[key]:
            raise ConfigError('consumer event time must be canonical UTC')
    for key in ('record_id', 'namespace', 'host_id', 'recipe_reference'):
        if not isinstance(event[key], str) or not event[key]:
            raise ConfigError('consumer event identity must be nonempty')
    if any(value is not None and (not isinstance(value, str) or not value) for value in (event['contract'], event['version'])):
        raise ConfigError('invalid consumer data contract/version')
    if (event['contract'] is None) != (event['version'] is None):
        raise ConfigError('consumer data contract/version must appear together')
    return event


def events(root):
    from retention_store import archives, archive_path, database, settings
    namespace = settings(root)
    result = []
    identifiers = set()
    for path in archives(root):
        with database(path) as connection:
            if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='retention_events'").fetchone():
                continue
            for (payload,) in connection.execute('SELECT payload FROM retention_events ORDER BY emitted_at,event_id'):
                event = validate_event(json.loads(payload))
                if namespace is None or event['namespace'] != namespace['namespace'] or archive_path(root, event) != path:
                    raise ConfigError('consumer event archive/namespace disagrees with identity/time')
                if event['event_id'] in identifiers:
                    raise ConfigError('duplicate consumer event ID across archives')
                identifiers.add(event['event_id'])
                result.append((path, event))
    return sorted(result, key=lambda pair: (pair[1]['emitted_at'], pair[1]['event_id']))


@contextmanager
def locked(root):
    import fcntl
    from retention_store import checked
    active = getattr(_ACTIVE, 'roots', set())
    key = str(Path(root).resolve())
    if key in active:
        raise ConfigError('recursive consumer dispatch is unsupported; defer writes and dispatch after returning')
    descriptor = os.open(checked(root, '.consumers.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        _ACTIVE.roots = active | {key}
        try:
            yield
        finally:
            _ACTIVE.roots = active


@dataclass(frozen=True)
class ConsumerContext:
    root: Path
    event: dict
    retention: object


def execute(root, item, event):
    from retention_store import Reader
    # Trusted registered programs run in-process. This is not a sandbox.
    namespace = '_opsfeast_consumer_' + uuid4().hex
    spec = importlib.util.spec_from_file_location(namespace, item['entrypoint_path'], submodule_search_locations=[item['directory']])
    module = importlib.util.module_from_spec(spec)
    sys.modules[namespace] = module
    try:
        # Avoid bytecode writes to read-only installed bundles and stale same-second code.
        entrypoint = safe_path(item['directory'], item['entrypoint'])
        code = entrypoint.read_bytes()
        descriptor = safe_path(item['directory'], 'consumer.yaml').read_bytes()
        if hashlib.sha256(descriptor + b'\0' + code).hexdigest() != item['sha256']:
            raise ConfigError('consumer source changed during dispatch; retry with reviewed current source')
        exec(compile(code, item['entrypoint_path'], 'exec'), module.__dict__)
        result = module.execute(ConsumerContext(Path(root), dict(event), Reader(root)))
        if not isinstance(result, dict) or result.get('status') not in ('success', 'failed', 'skipped'):
            raise ConfigError('consumer execute(context) must return status success/failed/skipped')
        json.dumps(result, allow_nan=False)
        return result
    finally:
        for name in list(sys.modules):
            if name == namespace or name.startswith(namespace + '.'):
                del sys.modules[name]


def inspect_deliveries(root, consumer=None):
    from retention_store import database
    result = []
    for path, event in events(root):
        with database(path) as connection:
            rows = connection.execute('SELECT consumer,status,attempts,payload FROM consumer_deliveries WHERE event_id=?', (event['event_id'],)).fetchall()
        result.append({'event': event, 'deliveries': [dict(json.loads(payload), consumer=name.split('@', 1)[0], source=name.split('@', 1)[1], status=status, attempts=attempts)
                                                     for name, status, attempts, payload in rows if consumer is None or name.split('@', 1)[0] == consumer]})
    return {'contract_version': VERSION, 'status': 'success', 'events': result}


def dispatch(root, consumer=None):
    """Synchronous, serialized at-least-once delivery. Failed/pending pairs retry next call."""
    from retention_store import database, canonical, now, settings
    root = Path(root).resolve(strict=True)
    if settings(root) is None:
        raise ConfigError('consumers require initialized retention')
    results = []
    with locked(root):
        items = catalog(root)['consumers']
        if consumer is not None:
            items = [i for i in items if i['id'] == consumer]
            if not items:
                raise ConfigError('consumer not found')
        for item in items:
            if not item['enabled']:
                continue
            if item['status'] == 'failed':
                results.append({'consumer': item['id'], 'status': 'failed', 'reason_code': 'consumer_unavailable', 'errors': item['errors']})
                continue
            identity = item['id'] + '@' + item['source']
            for path, event in events(root):
                if not matches(item, event):
                    continue
                with database(path, True) as connection:
                    previous = connection.execute('SELECT status,attempts FROM consumer_deliveries WHERE event_id=? AND consumer=?', (event['event_id'], identity)).fetchone()
                    if previous and previous[0] in ('success', 'skipped'):
                        continue
                    attempts = previous[1] + 1 if previous else 1
                    # Persist started before calling arbitrary consumer code.
                    connection.execute('INSERT OR REPLACE INTO consumer_deliveries VALUES (?,?,?,?,?)',
                                       (event['event_id'], identity, 'running', attempts, canonical({'started_at': now(), 'sha256': item['sha256']})))
                try:
                    outcome = execute(root, item, event)
                except Exception as exc:
                    outcome = {'status': 'failed', 'reason_code': 'consumer_failed', 'error_type': type(exc).__name__}
                receipt = dict(outcome, consumer=item['id'], source=item['source'], event_id=event['event_id'],
                               record_id=event['record_id'], attempts=attempts, sha256=item['sha256'], completed_at=now())
                with database(path, True) as connection:
                    connection.execute('UPDATE consumer_deliveries SET status=?,payload=? WHERE event_id=? AND consumer=?',
                                       (receipt['status'], canonical(receipt), event['event_id'], identity))
                results.append(receipt)
    return {'contract_version': VERSION, 'status': 'failed' if any(r['status'] == 'failed' for r in results) else 'success',
            'consumers': results, 'recovery': 'opsfeast.py consumers dispatch --root ' + shlex.quote(str(root)) + ' --json'}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='opsfeast.py consumers',
        description=('Discover programs that react to retained-data changes and inspect their\n'
        'durable delivery results. Dispatch executes enabled reviewed local programs\n'
        'for pending or failed events; their effects follow the selected consumer\n'
        'implementation.'),
        epilog=('Actions:\n'
        '  list [ID]       Discover descriptors and registrations without importing programs.\n'
        '  show ID         Inspect one consumer and its subscriptions without execution.\n'
        '  inspect [ID]    Read event/delivery evidence, including individual failed attempts.\n'
        '  dispatch [ID]   Execute pending/running/failed deliveries; successful pairs stay acked.\n'
        '\n'
        'Delivery is at least once: consumers must tolerate repeated attempts.\n'
        'Example: opsfeast.py consumers list --recipe system/inventory/overview --profile main --json'),
        formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument('action', choices=('list', 'show', 'inspect', 'dispatch'))
    parser.add_argument('consumer', nargs='?')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--root', type=Path)
    selection.add_argument('--profile')
    parser.add_argument('--recipe', help='exact source-qualified recipe reference; static relation filter')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.action == 'show' and not args.consumer:
        parser.error('show requires a consumer ID')
    if args.recipe and args.action not in ('list', 'show'):
        parser.error('--recipe applies to list/show')
    try:
        root = resolve_root(args.root, args.profile)
        if args.action == 'dispatch':
            result = dispatch(root, args.consumer)
        elif args.action == 'inspect':
            result = inspect_deliveries(root, args.consumer)
        else:
            if args.recipe:
                from recipe_catalog import choose
                recipe = choose(root, args.recipe)
                related_sources = {i['source'] for i in related(root, recipe['reference'], (recipe.get('retention') or {}).get('declaration'))}
                result = catalog(root)
                result['consumers'] = [i for i in result['consumers'] if i['source'] in related_sources]
            else:
                result = catalog(root)
            if args.consumer:
                result['consumers'] = [i for i in result['consumers'] if i['id'] == args.consumer]
                if not result['consumers']:
                    raise ConfigError('consumer not found')
            result['status'] = 'failed' if any(i['status'] == 'failed' for i in result['consumers']) else 'success'
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 1 if result['status'] == 'failed' else 0
    except (ConfigError, OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}))
        return 1


def bootstrap(root):
    """Profile initialization creates only the shipped Vault landing content."""
    try:
        item = next(i for i in catalog(root)['consumers'] if i['source'] == 'builtin:vault')
        if not item['enabled']:
            return {'status': 'skipped', 'reason_code': item.get('disabled_reason', 'consumer_disabled'), 'consumers': []}
        if item['status'] != 'success':
            raise ConfigError('bundled vault consumer unavailable')
        outcome = execute(root, item, {'contract_version': VERSION, 'event': 'profile.initialized'})
        return dict(outcome, consumers=[dict(outcome, consumer='vault')])
    except Exception as exc:
        return {'status': 'failed', 'reason_code': 'consumer_bootstrap_failed', 'error_type': type(exc).__name__}
