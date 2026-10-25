"""CLI for local platform objects; dispatch is the only provider operation."""
import argparse
import json
from pathlib import Path
import sqlite3
from opsfeast import ConfigError, resolve_root
from opsfeast.services import Services


def main(argv=None):
    parser = argparse.ArgumentParser(prog='opsfeast.py services', description=(
        'Read notification/todo objects, perform revision-checked local lifecycle changes, '
        'or explicitly dispatch configured presentation and notification delivery adapters. '
        'No host connection or todo execution is performed.'))
    parser.add_argument('action', choices=('inspect', 'list', 'show', 'update', 'history', 'deliveries', 'dispatch'))
    parser.add_argument('object_id', nargs='?')
    parser.add_argument('--kind', choices=('notification', 'todo'))
    parser.add_argument('--host')
    parser.add_argument('--status')
    parser.add_argument('--revision', type=int)
    parser.add_argument('--actor')
    parser.add_argument('--changes', help='JSON object of editable fields; no provider credentials')
    parser.add_argument('--retry-unknown', action='store_true', help='dispatch only; may duplicate an uncertain delivery')
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--root', type=Path)
    choice.add_argument('--profile')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.action in ('show', 'update') and (not args.object_id or not args.kind):
        parser.error('show/update require object ID and --kind')
    if args.action == 'update' and (args.revision is None or not args.actor or args.changes is None):
        parser.error('update requires --revision, --actor and --changes')
    if args.retry_unknown and args.action != 'dispatch':
        parser.error('--retry-unknown requires dispatch')
    try:
        services = Services(resolve_root(args.root, args.profile))
        objects = services.notifications if args.kind == 'notification' else services.todos
        if args.action == 'inspect':
            result = services.inspect()
        elif args.action == 'list':
            result = {'status': 'success', 'objects': [o for o in services._list(args.kind)
                if (args.host is None or o['source']['host_id'] == args.host) and (args.status is None or o['status'] == args.status)]}
        elif args.action == 'show':
            result = {'status': 'success', 'object': objects.show(args.object_id)}
        elif args.action == 'update':
            changes = json.loads(args.changes)
            if not isinstance(changes, dict):
                raise ConfigError('changes must be a JSON object')
            result = {'status': 'success', 'object': objects.update(args.object_id,
                expected_revision=args.revision, actor=args.actor, **changes)}
        elif args.action == 'history':
            result = {'status': 'success', 'history': services.history(args.object_id)}
        elif args.action == 'deliveries':
            result = {'status': 'success', 'deliveries': services.deliveries()}
        else:
            result = services.dispatch(retry_unknown=args.retry_unknown)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return int(result.get('status') == 'failed')
    except (ConfigError, OSError, ValueError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({'status': 'failed', 'reason_code': getattr(exc, 'code', 'service_operation_failed'),
                          'error_type': type(exc).__name__}))
        return 1
