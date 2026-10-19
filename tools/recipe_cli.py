"""Shared recipe discovery, execution and reusable report/job command surfaces."""
import argparse
import json
import math
from pathlib import Path
import sys
from display_time import format_time, human_times

from opsfeast import ConfigError, resolve_root, positive_timeout
from recipe_catalog import catalog, choose, configuration
from recipe_inputs import json_object, cli_variables, prepare_vars
from recipe_reports import run_report, results, result_path, show_result, show_artifact, page, export_html
from recipe_packages import pack, unpack
import recipe_jobs
from console_output import human_output, table, vertical, prepare as prepare_console, print_report, host_label, display_icons, ConsoleDependencyError


def output(value):
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))


def environment(parser, checkout=False):
    choices = parser.add_mutually_exclusive_group()
    choices.add_argument('--root', type=Path)
    choices.add_argument('--profile')
    if checkout:
        choices.add_argument('--checkout-only', action='store_true', help='inspect bundled recipes without a Feast')


def invocation(parser):
    from run_recipe import TargetAction, positive_threads
    parser.add_argument('recipe')
    parser.add_argument('--host', nargs='+', dest='targets', action=TargetAction)
    parser.add_argument('--group', nargs='+', dest='targets', action=TargetAction)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--exclude', nargs='+')
    parser.add_argument('--threads', type=positive_threads)
    parser.add_argument('--timeout', type=positive_timeout, default=30)
    parser.add_argument('--var', action='append', default=[], dest='assignments')
    parser.add_argument('--vars-file', type=Path)
    parser.add_argument('--input', type=Path, action='append', default=[], help='explicit JSON report input; repeatable')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--json', action='store_true')


def validate_invocation(root, item, inv):
    expected = {'targets', 'all', 'exclude', 'threads', 'timeout', 'assignments', 'vars_file', 'inputs', 'verbose', 'quiet'}
    if not isinstance(inv, dict) or set(inv) != expected:
        raise ConfigError('invocation fields do not match job contract')
    if any(type(inv[key]) is not bool for key in ('all', 'verbose', 'quiet')):
        raise ConfigError('invocation flags must be booleans')
    if type(inv['timeout']) not in (int, float) or not math.isfinite(inv['timeout']) or inv['timeout'] <= 0:
        raise ConfigError('invocation timeout must be positive and finite')
    if inv['threads'] is not None and (type(inv['threads']) is not int or inv['threads'] <= 0):
        raise ConfigError('invocation threads must be a positive integer')
    if not isinstance(inv['targets'], list) or any(not isinstance(t, (list, tuple)) or len(t) != 2 or t[0] not in ('host', 'group') or not isinstance(t[1], str) or not t[1] for t in inv['targets']):
        raise ConfigError('invocation targets must be host/group name pairs')
    if any(not isinstance(inv[key], list) or any(not isinstance(value, str) for value in inv[key]) for key in ('exclude', 'assignments', 'inputs')):
        raise ConfigError('invocation exclusion/input/assignment values must be string lists')
    if inv['vars_file'] is not None and not isinstance(inv['vars_file'], str):
        raise ConfigError('invocation vars_file must be a path string or null')
    if inv['verbose'] and inv['quiet']:
        raise ConfigError('--verbose and --quiet cannot be combined')
    if item['kind'] == 'report':
        if inv['targets'] or inv['all'] or inv['exclude'] or inv['threads']:
            raise ConfigError('offline report recipes do not accept host/group/all/exclude/threads')
        config = configuration(root)
        info = config.recipe_location(item['reference'], config.root / 'hosts.yaml', cli=True)
        values = json_object(Path(inv['vars_file'])) if inv['vars_file'] else None
        prepare_vars(item['descriptor'], info['vars'], {}, cli_variables(item['descriptor'], values, inv['assignments']))
    else:
        if inv['inputs']:
            raise ConfigError('--input is for offline report recipes only')
        if not inv['targets'] and not inv['all']:
            raise ConfigError('operational recipes require --host, --group or --all')
        if inv['all'] and inv['targets'] or inv['exclude'] and not inv['all']:
            raise ConfigError('invalid all/target/exclusion combination')


def execute(root, spec, *, dryrun=False, force=False, json_output=False):
    prepare_console(json_output)
    item = choose(root, spec['recipe'])
    if not item['runnable']:
        raise ConfigError('selected recipe has invalid or unsupported execution contract')
    inv = spec['invocation']
    validate_invocation(root, item, inv)
    if item['kind'] == 'report':
        if dryrun or force:
            raise ConfigError('--dryrun/--force are inventory-only')
        values = json_object(Path(inv['vars_file'])) if inv['vars_file'] else None
        report, path = run_report(root, item, [Path(p) for p in inv['inputs']], values,
                                  inv['assignments'], inv['timeout'])
        print_report({'status': report['status'], 'reason_code': report['reason_code'], 'message': report['message'],
                'result_id': path.relative_to(root).as_posix(), 'result_path': str(path),
                'data': report['data'], 'artifacts': report['artifacts']}, json_output=json_output, kind='execution', recipe=item['reference'], allow_nan=False)
        return 0 if report['status'] == 'success' else 1
    if inv['inputs']:
        raise ConfigError('--input is for offline report recipes only')
    from run_recipe import main as run
    argv = [item['reference'], '--root', str(root), '--timeout', str(inv['timeout'])]
    for kind, name in inv['targets']:
        argv.extend(['--' + kind, name])
    if inv['all']: argv.append('--all')
    if inv['exclude']: argv.extend(['--exclude', *inv['exclude']])
    if inv['threads']: argv.extend(['--threads', str(inv['threads'])])
    for assignment in inv['assignments']: argv.extend(['--var', assignment])
    if inv['vars_file']: argv.extend(['--vars-file', inv['vars_file']])
    if inv['verbose']: argv.append('--verbose')
    if inv['quiet']: argv.append('--quiet')
    if json_output: argv.append('--json')
    if dryrun: argv.append('--dryrun')
    if force: argv.append('--force')
    return run(argv)


def specification(args):
    return {'recipe': args.recipe, 'invocation': {
        'targets': args.targets or [], 'all': args.all, 'exclude': args.exclude or [], 'threads': args.threads,
        'timeout': args.timeout, 'assignments': args.assignments,
        'vars_file': str(args.vars_file.expanduser().resolve()) if args.vars_file else None,
        'inputs': [str(path.expanduser().resolve()) for path in args.input],
        'verbose': args.verbose, 'quiet': args.quiet}}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='opsfeast.py recipes',
        description=('Discover reviewed recipes, run host operations or offline reports, and inspect saved results. '
                     'You can also package recipe files and save recipe invocations as reusable jobs with content fingerprints.'),
        epilog='Run a subcommand with --help to read its purpose, effects and examples.',
        allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    listing = commands.add_parser('list', help='discover available recipes and their declared capabilities',
        description=('List recipes from the bundle, selected profile and enabled registered sources. '
                     'Read metadata to discover purpose, inputs and declared compatibility; no recipe is executed '
                     'and no host is contacted. --html writes a catalog page.'),
        epilog='Example: opsfeast.py recipes list --checkout-only --json')
    environment(listing, checkout=True)
    listing.add_argument('--query')
    listing.add_argument('--kind', choices=('operation', 'report'))
    listing.add_argument('--json', action='store_true')
    listing.add_argument('--html', type=Path, help='save a basic escaped catalog page to a new file')
    show = commands.add_parser('show', help='inspect one recipe before deciding whether to run it',
        description=('Show the purpose, inputs, dependencies, verification evidence and retention consumers for one recipe. '
                     'This is static inspection: it does not run the recipe or verify host applicability.'),
        epilog='Example: opsfeast.py recipes show system/network/check/port --profile main --json')
    environment(show, checkout=True)
    show.add_argument('recipe')
    show.add_argument('--json', action='store_true')
    run = commands.add_parser('run', help='execute one host-operation recipe or offline report',
        description=('Run one selected recipe in a Feast and save its execution results.\n\n'
                     'Operational recipes execute on selected hosts through configured sessions.\n'
                     'They may change targets according to their reviewed implementation. Raw\n'
                     'results are saved; eligible declared data is retained and enabled consumers\n'
                     'are notified.\n\n'
                     'Offline report recipes read explicit JSON inputs or retained data on the\n'
                     'controller and save report results/artifacts without host collection.'),
        epilog=('Examples:\n'
                '  opsfeast.py recipes run system/network/check/port --host node --var port=443\n'
                '  opsfeast.py recipes run feast/report/retention-summary --profile main\n\n'
                'Review the recipe with recipes show first. Inventory --dryrun makes real\n'
                'connections and tests account access without collecting inventory.\n'
                'See docs/cli.md for result and exit-code details.'),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    environment(run)
    invocation(run)
    mode = run.add_mutually_exclusive_group()
    mode.add_argument('--dryrun', action='store_true')
    mode.add_argument('--force', action='store_true')
    result = commands.add_parser('results', help='browse saved execution results without running recipes',
        description=('Read previously saved operation/report results. list shows a filtered index, show emits the '
                     'original saved JSON, and detail includes result metadata and interpreted local timestamps. '
                     'No recipe is rerun; --html writes a local HTML page for list/show.'),
        epilog='Example: opsfeast.py recipes results list --profile main --json')
    environment(result)
    result.add_argument('action', choices=('list', 'show', 'detail'))
    result.add_argument('result_id', nargs='?')
    result.add_argument('--recipe-id')
    result.add_argument('--host')
    result.add_argument('--status', choices=('success', 'partial', 'failed', 'skipped', 'unsupported'))
    result.add_argument('--json', action='store_true')
    result.add_argument('--html', type=Path)
    artifact = commands.add_parser('artifact', help='retrieve a verified saved report artifact',
        description=('Read one declared artifact from a saved report result after checking its recorded integrity '
                     'and safe path. Print JSON metadata including the verified absolute file path; this does not regenerate or stream the artifact.'),
        epilog='Example: opsfeast.py recipes artifact RESULT_ID retention.html --profile main')
    environment(artifact)
    artifact.add_argument('result_id')
    artifact.add_argument('name')
    packaging = commands.add_parser('pack', help='package explicitly selected recipe files for review or sharing',
        description=('Create a recipe bundle archive with metadata and file digests from an explicit file allowlist. '
                     'This packages portable code/documentation; it does not execute, publish or transmit the recipe.'),
        epilog=('Example: opsfeast.py recipes pack :database/mysql/check/replication --profile main '
                '--file recipe.yaml --file main.py --file README.md --file LICENSE --output candidate.zip'))
    environment(packaging, checkout=True)
    packaging.add_argument('recipe')
    packaging.add_argument('--file', action='append', required=True)
    packaging.add_argument('--output', type=Path, required=True)
    candidate = commands.add_parser('unpack', help='validate and extract a recipe bundle into a review directory',
        description=('Validate a bundle manifest, file digests, paths and attribution, then extract it into a new '
                     'candidate directory for review. This does not register, install or execute the recipe.'),
        epilog='Example: opsfeast.py recipes unpack candidate.zip --destination reviewed-candidate')
    candidate.add_argument('archive', type=Path)
    candidate.add_argument('--destination', type=Path, required=True)
    jobs = commands.add_parser('jobs', help='save and reuse verified recipe invocations',
        description=('Manage named recipe invocations and their recorded recipe fingerprints in the selected Feast. '
                     'Saving a job does not execute it or create a schedule; jobs run explicitly executes it.'),
        epilog='Use jobs save, list, show or run with --help for that operation.')
    jobs_commands = jobs.add_subparsers(dest='action', required=True)
    saved = jobs_commands.add_parser('save', help='save a reviewed invocation without executing it',
        description=('Save a new named invocation with its recipe reference, input/target selections and recipe '
                     'fingerprint for later verification. This writes a job definition only; it does not connect, '
                     'run the recipe, replace an existing job or schedule work.'),
        epilog=('Example: opsfeast.py recipes jobs save nightly-summary feast/report/retention-summary '
                '--profile main --json'))
    environment(saved)
    saved.add_argument('name')
    invocation(saved)
    for action in ('list', 'show', 'run'):
        summary, description = {
            'list': ('list saved invocation names',
                     'List named jobs saved in the selected Feast without running their recipes or changing their definitions.'),
            'show': ('inspect a saved invocation before execution',
                     'Read a saved job definition, including its recipe, selections and recorded fingerprint. '
                     'This does not run the recipe or establish that its current content still matches the saved fingerprint.'),
            'run': ('verify and execute a saved invocation',
                    'Verify the saved recipe fingerprint, then execute the recorded operation or offline report with '
                    'its saved targets and inputs. Changed recipe content is refused; execution writes normal '
                    'results and may connect to or change targets according to the reviewed recipe.'),
        }[action]
        job = jobs_commands.add_parser(action, help=summary, description=description,
            epilog='Example: opsfeast.py recipes jobs ' + action + ('' if action == 'list' else ' nightly-summary') + ' --profile main --json')
        environment(job)
        if action != 'list': job.add_argument('name')
        job.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        raw = args.command in ('artifact', 'pack', 'unpack') or args.command == 'results' and args.action in ('show', 'detail') or bool(getattr(args, 'html', None))
        if not raw:
            prepare_console(getattr(args, 'json', False))
        if args.command == 'unpack':
            output(unpack(args.archive, args.destination))
            return 0
        root = None if getattr(args, 'checkout_only', False) else resolve_root(args.root, args.profile).resolve(strict=True)
        if args.command == 'list':
            data = catalog(root, args.query, args.kind)
            rows = [[item['reference'], item['version'], item['kind'], item['title'], 'compatible' if item['runnable'] else 'unavailable', '; '.join(item['errors'])] for item in data['recipes']]
            if args.html:
                output({'html_path': export_html(args.html, page('OpsFeast recipes', ['Recipe', 'Version', 'Kind', 'Purpose', 'Static status', 'Errors'], rows,
                                                               'Static inspection only; dependencies and target/data applicability require review.')),
                        'status': data['status']})
            elif args.json: output(data)
            else:
                if human_output():
                    print(table(['source', 'status'], [[source['name'], source['status']] for source in data['sources']]))
                    print(table(['recipe', 'version', 'kind', 'purpose', 'static status', 'errors'], rows))
                else:
                    for source in data['sources']:
                        print(f"Source {source['name']}: {source['status']}")
                    for row in rows: print(' | '.join(str(value) for value in row))
                print('Static compatibility only; inspect inputs/dependencies with recipes show before execution.')
            return 1 if data['status'] == 'failed' else 0
        if args.command == 'show':
            item = choose(root, args.recipe)
            if args.json: output(item)
            elif human_output():
                print_report({key: item[key] for key in ('reference', 'title', 'version', 'description', 'kind',
                              'contract', 'runnable', 'inputs', 'dependencies', 'verification', 'errors', 'availability_evidence', 'consumers')})
            else:
                print(f"{item['reference']} — {item['title']} ({item['version']})")
                print(item['description'])
                print(f"Kind: {item['kind']}; contract: {item['contract']}; runnable compatibility: {item['runnable']}")
                print('Inputs: ' + json.dumps(item['inputs'], ensure_ascii=False, indent=2))
                print('Consumers: ' + json.dumps(item['consumers'], ensure_ascii=False, indent=2))
                print('Dependencies: ' + json.dumps(item['dependencies'], ensure_ascii=False, indent=2))
                print('Verification: ' + json.dumps(item['verification'], ensure_ascii=False, indent=2))
                if item['errors']: print('Errors: ' + '; '.join(item['errors']))
                print(item['availability_evidence'])
            return 0 if item['runnable'] else 1
        if args.command == 'run':
            return execute(root, specification(args), dryrun=args.dryrun, force=args.force, json_output=args.json)
        if args.command == 'pack':
            item = choose(root, args.recipe)
            if not item['runnable']: raise ConfigError('only compatible reviewed recipes can be packed')
            output(pack(item, args.file, args.output))
            return 0
        if args.command == 'results':
            if args.action == 'detail':
                if args.html:
                    raise ConfigError('results detail does not support --html; use results list/show --html')
                if args.result_id:
                    if args.host or args.recipe_id or args.status:
                        raise ConfigError('results detail RESULT_ID cannot be combined with index filters')
                    data = show_result(root, args.result_id)
                    if args.json:
                        output(data)
                    else:
                        identifier = result_path(root, args.result_id).relative_to(root).as_posix()
                        print(vertical({'result_id': identifier, **data}))
                    return 0
                data = results(root, args.recipe_id, args.host, args.status)
                if args.json:
                    output(data)
                else:
                    for index, item in enumerate(data['results'], 1):
                        print(f'******** Result {index} ********')
                        print(vertical(item))
                        print()
                    if not data['results']:
                        print('No saved results.')
                    for error in data['errors']:
                        print('******** Invalid result ********')
                        print(vertical(error))
                return 0 if data['status'] == 'success' else 1
            if args.action == 'show':
                if not args.result_id: raise ConfigError('results show requires RESULT_ID')
                data = show_result(root, args.result_id)
                if args.html:
                    output({'html_path': export_html(args.html, page('OpsFeast result', ['Field', 'Value'], [[key, json.dumps(human_times(value), ensure_ascii=False)] for key,value in data.items()], 'Raw evidence; timestamps displayed in local time to seconds; check status, data and quality warnings.'))})
                else: output(data)
                return 0
            if args.result_id: raise ConfigError('results list does not accept RESULT_ID')
            data = results(root, args.recipe_id, args.host, args.status)
            rows = [[r.get('short_id', r['result_id']), r['recipe_id'], r['host_id'], r['status'], format_time(r['completed_at']), r.get('collection_user') or 'unknown', json.dumps(r['identity_warnings'], ensure_ascii=False)] for r in data['results']]
            if args.html:
                output({'html_path': export_html(args.html, page('OpsFeast results', ['Result ID', 'Recipe', 'Host', 'Status', 'Completed', 'User', 'Identity warnings'], rows,
                                                               json.dumps(data['errors'], ensure_ascii=False))), 'status': data['status']})
            elif args.json: output(data)
            else:
                if human_output():
                    icons = display_icons(root)
                    for row in rows:
                        row[2] = host_label(row[2], icons) if row[2] else '-'
                    print(table(['result ID', 'recipe', 'host', 'status', 'completed', 'user'],
                                [row[:-1] for row in rows]))
                else:
                    for row in rows: print(' | '.join(str(value) for value in row))
                for error in data['errors']: print('ERROR: ' + error.get('short_id', error['result_id']) + ' invalid result')
            return 0 if data['status'] == 'success' else 1
        if args.command == 'artifact':
            output(show_artifact(root, args.result_id, args.name))
            return 0
        if args.command == 'jobs':
            if args.action == 'list':
                names = recipe_jobs.listing(root)
                if human_output(args.json): print(table(['job'], [[name] for name in names]))
                else: output({'jobs': names})
            elif args.action == 'save': print_report(recipe_jobs.save(root, args.name, specification(args)), json_output=args.json, allow_nan=False)
            elif args.action == 'show': print_report(recipe_jobs.load(root, args.name, verify=False), json_output=args.json, allow_nan=False)
            else:
                document = recipe_jobs.load(root, args.name)
                return execute(root, {'recipe': document['recipe'], 'invocation': document['invocation']}, json_output=args.json)
            return 0
    except (ConfigError, OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as exc:
        print('ERROR: ' + (str(exc) if isinstance(exc, (ConfigError, ConsoleDependencyError)) else type(exc).__name__), file=sys.stderr)
        return 1
