"""Explicit vendor download/import and offline assessment. Never connects to hosts."""
import argparse
import json
import re
from pathlib import Path
import sys

from . import advisories
from .report import generate, render


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest='command', required=True)
    for name in ('fetch', 'import'):
        command = commands.add_parser(name)
        command.add_argument('--vendor', required=True, choices=sorted(advisories.HOSTS))
        command.add_argument('--release', required=True)
        command.add_argument('--codename', default='')
        command.add_argument('--output', required=True, type=Path)
        if name == 'fetch':
            command.add_argument('--advisory', action='append', default=[])
        else:
            command.add_argument('--source', required=True, type=Path)
            command.add_argument('--source-url', required=True)
            command.add_argument('--retrieved-at', required=True)
    command = commands.add_parser('assess')
    command.add_argument('--inventory', required=True, action='append', type=Path)
    command.add_argument('--advisory', required=True, action='append', type=Path)
    command.add_argument('--output-dir', required=True, type=Path)
    command.add_argument('--as-of')
    command.add_argument('--max-inventory-age-hours', type=float, default=24)
    command.add_argument('--max-advisory-age-days', type=float, default=7)
    command.add_argument('--max-findings', type=int, default=100000)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command in ('fetch', 'import'):
            if args.output.exists():
                raise ValueError('output_already_exists')
            scope = {'os_id': advisories.OS_IDS[args.vendor],
                     'version_id':args.release, 'codename':args.codename}
            value = (advisories.fetch(args.vendor, scope, args.advisory) if args.command == 'fetch'
                     else advisories.import_local(args.vendor, scope, args.source, args.source_url, args.retrieved_at))
            # Exclusive creation: immutable snapshots are never silently refreshed.
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
            receipt = {key:value[key] for key in ('kind','vendor','record_count','snapshot_sha256')}
        else:
            inputs = []
            for path in args.inventory + args.advisory:
                if path.stat().st_size > advisories.MAX_SNAPSHOT:
                    raise ValueError('assessment_input_limit')
                inputs.append(advisories.parse(path.read_bytes()))
            data = generate(inputs, {key:getattr(args,key) for key in ('as_of','max_inventory_age_hours','max_advisory_age_days','max_findings')})
            args.output_dir.mkdir(mode=0o700)  # Refuse existing directories and artifact replacement.
            artifacts = render(data, args.output_dir)
            receipt = {'kind':data['kind'], 'artifacts':artifacts,
                       'reports':[{'host_id':r['host_id'],'status':r['status'],'counts':r['counts']} for r in data['reports']]}
        print(json.dumps({'status':'success','data':receipt}, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        # Do not echo private file paths or native exception payloads.
        print(json.dumps({'status':'failed','reason_code':'package_security_operation_failed','error_type':type(error).__name__,'detail_code':str(error) if isinstance(error,ValueError) and re.fullmatch('[a-z][a-z0-9_:]{1,127}',str(error)) else 'invalid_input_or_io_failure'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
