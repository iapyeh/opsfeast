"""Read configured hosts and their last successfully saved reference addresses."""
import argparse
import json
import sys
from pathlib import Path

from opsfeast import ConfigError, resolve_root
from console_output import prepare, table, ConsoleDependencyError


def main(argv=None):
    parser = argparse.ArgumentParser(prog='opsfeast.py hosts', allow_abbrev=False,
        description='Read configured hosts and saved reference IPs. No connection, DNS lookup or writes.')
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('list', 'show'):
        sub = commands.add_parser(command, help='read ' + ('all hosts' if command == 'list' else 'one host'),
            description='Read configured host IDs, labels, groups and last successfully saved inventory IPs. '
                        'Reference only; failures retain previous addresses. No connection, DNS lookup or writes.',
            epilog='Example: opsfeast.py hosts ' + ('list' if command == 'list' else 'show node') + ' --profile main --json')
        if command == 'show':
            sub.add_argument('host_id')
        env = sub.add_mutually_exclusive_group()
        env.add_argument('--root', type=Path)
        env.add_argument('--profile')
        sub.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        prepare(args.json)
        from inventory_jobs import profile
        hosts = profile(resolve_root(args.root, args.profile)).hosts
        names = [args.host_id] if args.command == 'show' else sorted(hosts.list())
        rows = []
        for name in names:
            settings = hosts.get(name)
            rows.append({'host_id': name, 'label': settings.get('label', ''),
                         'groups': settings.get('group', []), 'reference_ips': hosts.reference_ips(name)})
        result = {'schema_version': '0.1.0', 'hosts': rows}
        if sys.stdout.isatty() and not args.json:
            print(table(['Host ID', 'Label', 'Groups', 'IPv4', 'IPv6', 'IP observed at', 'State'],
                [(r['host_id'], r['label'], ', '.join(r['groups']),
                  ', '.join(r['reference_ips']['ipv4_addresses']), ', '.join(r['reference_ips']['ipv6_addresses']),
                  r['reference_ips']['observed_at'] or '-', r['reference_ips']['status']) for r in rows]))
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (ConfigError, OSError, ValueError, ConsoleDependencyError) as exc:
        print('ERROR: ' + (str(exc) if isinstance(exc, (ConfigError, ConsoleDependencyError)) else type(exc).__name__), file=sys.stderr)
        return 1
