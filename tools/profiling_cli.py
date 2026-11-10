"""Read-only profiling discovery and retained host evidence."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from opsfeast import ConfigError, resolve_root
from opsfeast.profiling import catalog, inspect_host
from console_output import prepare, table, ConsoleDependencyError


def main(argv=None):
    parser = argparse.ArgumentParser(prog='opsfeast.py profiling', allow_abbrev=False,
        description='Discover profiling integrations or read saved host evidence. No connection, collection, scheduling or writes.')
    commands = parser.add_subparsers(dest='command', required=True)
    describe = commands.add_parser('describe', help='read bundled coverage and integration gaps without a profile',
        description='Read the product profiling catalog. Static integrations are not target applicability or complete coverage.')
    host = commands.add_parser('show', help='read retained host property attempts, values and original source times',
        description='Read latest retained property attempts for one registered host. Mixed ages and failed attempts remain explicit; no collection.',
        epilog='Example: opsfeast.py profiling show --profile main --host node --domain storage --json')
    host.add_argument('--host', required=True)
    group = host.add_mutually_exclusive_group()
    group.add_argument('--root', type=Path)
    group.add_argument('--profile')
    host.add_argument('--offset', type=int, default=0)
    host.add_argument('--limit', type=int, default=100)
    for command in (describe, host):
        command.add_argument('--domain', help='one domain ID from profiling describe')
        command.add_argument('--json', action='store_true', help='explicit structured output, including in terminals')
    args = parser.parse_args(argv)
    try:
        prepare(args.json)
        if args.command == 'describe':
            result = catalog(domain=args.domain)
        else:
            from opsfeast.core import Instance
            profile = Instance.open().profile(root=resolve_root(args.root, args.profile))
            result = inspect_host(profile, args.host, domain=args.domain, offset=args.offset, limit=args.limit)
        if sys.stdout.isatty() and not args.json:
            if args.command == 'describe':
                print(table(['Capability', 'Integration', 'Properties', 'Scope'],
                    [(c['id'], c['integration'], len(c['properties']), c['scope_note']) for c in result['capabilities']]))
            else:
                print(table(['Property', 'Evidence state', 'Source times'],
                    [(p['property_id'], p['state'], ', '.join(e['observed_at'] for e in p['evidence'])) for p in result['items']]))
                print('Properties:', result['total'], 'Next offset:', result['next_offset'])
            print('\n'.join(result['limits']))
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0  # Read success is independent of collected coverage/health.
    except (ConfigError, ConsoleDependencyError, OSError, ValueError, sqlite3.Error) as exc:
        print('ERROR: ' + (str(exc) if isinstance(exc, (ConfigError, ConsoleDependencyError)) else type(exc).__name__), file=sys.stderr)
        return 1
