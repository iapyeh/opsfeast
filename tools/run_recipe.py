"""Run one selected inventory-system recipe from the checkout and save its result."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import runpy
import sys
import threading
import time
from uuid import uuid4

from host_runtime import discover, cached_facts, cache_path, save_facts, target_fingerprint
from recipe_dispatch import validate, select, bundle_digest, validate_observations
from recipe_inputs import RecipeContext, prepare_vars, supports_context

from opsfeast import ConfigError, Validator, REPOSITORY_ROOT, REPOSITORY_RECIPES, connection_plan, connection_error, positive_timeout, read_yaml, mapping, resolve_root, group_names

BUNDLE = Path(__file__).resolve().parents[1] / 'recipes/inventory/system'
collector = runpy.run_path(str(BUNDLE / 'main.py'))
_progress = ContextVar('recipe_progress', default=None)
_progress_output_lock = threading.Lock()
_implementation_lock = threading.Lock()


def progress_line(message):
    with _progress_output_lock:
        print(message, file=sys.stderr, flush=True)


def default_threads():
    return min(8, os.cpu_count() or 1)


def positive_threads(value):
    try:
        count = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError('--threads must be a positive integer') from None
    if count < 1:
        raise argparse.ArgumentTypeError('--threads must be a positive integer')
    return count


def progress(message):
    reporter = _progress.get()
    if reporter is not None:
        reporter.update(message)


class RunProgress:
    """Stage messages and a waiting heartbeat without probing the target."""
    def __init__(self, label, interval=5):
        self.label, self.interval = label, interval
        self.stage = 'starting'
        self.changed = time.monotonic()
        self.stop = threading.Event()
        self.lock = threading.Lock()

    def update(self, message):
        with self.lock:
            self.stage, self.changed = message, time.monotonic()
            progress_line(f'{self.label} {message}')

    def heartbeat(self):
        while not self.stop.wait(self.interval):
            with self.lock:
                elapsed = time.monotonic() - self.changed
                if elapsed >= self.interval:
                    progress_line(f'{self.label} still {self.stage} ({elapsed:.0f}s in this stage)')


@contextmanager
def reporting(enabled, label):
    reporter = RunProgress(label) if enabled else None
    token = _progress.set(reporter)
    worker = None
    try:
        if reporter is not None:
            reporter.update('starting')
            worker = threading.Thread(target=reporter.heartbeat, daemon=True)
            worker.start()
        yield
    finally:
        if reporter is not None:
            reporter.stop.set()
            if worker is not None:
                worker.join()
        _progress.reset(token)


def load_runtime():
    import sshscript
    installed = version('sshscript')
    if installed != sshscript.__version__ or installed != '5.0.0':
        raise ConfigError('runner requires matching SSHScript import/distribution 5.0.0; no automatic upgrade')
    return sshscript.Session, {'python': sys.version.split()[0], 'interpreter': sys.executable,
                               'sshscript_import': sshscript.__version__, 'sshscript_distribution': installed}


def preflight(root, host, recipe=None):
    config = Validator(root)
    config.load(config.root / 'hosts.yaml')
    config.check_connections()
    if host not in config.hosts:
        raise ConfigError(f'unknown host ID: {host}')
    if not config.hosts[host].get('enabled', True):
        if recipe is not None:
            config.recipe_location(str(recipe), config.root / 'hosts.yaml', cli=True, check_exists=False)
        else:
            config.recipes(host, config.hosts[host])
        config.execution_recipe = {'reason_code': 'host_disabled', 'reference': recipe}
        return config, None, None, None
    if recipe is not None:
        info = config.recipe_location(str(recipe), config.root / 'hosts.yaml', cli=True)
        if not info['enabled']:
            config.execution_recipe = dict(info, reason_code='source_disabled')
            return config, None, None, None
        scope = info['scope']
        directory = scope.path(info['pattern'], info['origin'])
        if not directory.is_dir():
            raise ConfigError('CLI recipe directory does not exist')
        host_vars = config.matching_recipe_vars(host, directory, info)
    else:
        config.recipes(host, config.hosts[host])
        entries = config.recipe_entries[host]
        matches = [entry for entry in entries if read_yaml(entry['directory'] / 'recipe.yaml').get('id') == 'inventory-system']
        if not matches and config.recipe_skips[host]:
            config.execution_recipe = dict(config.recipe_skips[host][0])
            return config, None, None, None
        if len(matches) != 1:
            raise ConfigError('select exactly one inventory-system recipe for this host or pass --recipe DIRECTORY')
        info = matches[0]
        directory, scope, host_vars = info['directory'], info['scope'], info['host_vars']
    descriptor = scope.inside(directory / 'recipe.yaml')
    if not descriptor.is_file():
        raise ConfigError('selected recipe directory must contain recipe.yaml')
    metadata = mapping(read_yaml(descriptor), str(descriptor))
    if metadata.get('id') != 'inventory-system':
        raise ConfigError('this minimal runner only supports inventory-system')
    validate(directory, metadata)
    variables = prepare_vars(metadata, info['vars'], host_vars)
    if variables and any(not supports_context(directory / entry['entrypoint']) for entry in metadata['implementations']):
        raise ConfigError('implementations receiving vars must accept collect(..., context=...)')
    config.execution_recipe = dict(info, effective_vars=variables)
    # The shared report helper is still internal to the trusted runner.
    digest = bundle_digest(directory)
    cache_path(config, host)
    output_dir = config.root / 'observations'
    if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
        raise ConfigError('observations must be a real directory within management root')
    return config, directory, digest, output_dir


def run(root, host, timeout=30, session_class=None, runtime=None, recipe=None):
    timeout = positive_timeout(timeout)
    progress('validating configuration and recipe')
    config, directory, digest, output_dir = preflight(root, host, recipe)
    if directory is None:
        info = config.execution_recipe
        code = info['reason_code']
        report = {'host_id': host, 'status': 'skipped', 'reason_code': code,
                  'message': 'Host is disabled.' if code == 'host_disabled' else 'Recipe source is disabled.',
                  'detected_kernel': None, 'supported_platforms': [], 'evidence_kind': 'not-executed',
                  'recipe': {'id': None, 'reference': info.get('reference'), 'source_name': info.get('name', info.get('source'))}}
        progress('skipped: ' + code)
        return report, None
    context = RecipeContext(host, config.execution_recipe['effective_vars'])
    if session_class is None:
        progress('checking execution runtime')
        session_class, runtime = load_runtime()
    report = collector['new_report'](host, 'local' if config.hosts[host]['connection'].get('local') else 'ssh')
    report['runtime'] = runtime or {'verification': 'mock'}
    if runtime is None:
        report['evidence_kind'] = 'mock'
    metadata = read_yaml(directory / 'recipe.yaml')
    report['schema_version'] = metadata['output']['schema_version']
    report['recipe'].update(version=metadata['version'], recipe_version=metadata['version'], bundle_sha256=digest)
    report['recipe']['descriptor_sha256'] = hashlib.sha256((directory / 'recipe.yaml').read_bytes()).hexdigest()
    report['supported_platforms'] = sorted({e['match'].get('os_name') for e in metadata['implementations'] if e['match'].get('os_name')})
    info = config.execution_recipe
    repository_recipe = info['name'] == 'repository'
    relative_root = REPOSITORY_ROOT.resolve() if repository_recipe else info['root']
    report['recipe']['installed_path'] = directory.relative_to(relative_root).as_posix()
    report['recipe']['location_source'] = 'repository' if repository_recipe else ('instance' if info['name'] == 'profile' else 'external')
    report['recipe']['source_name'] = info['name']
    report['recipe']['source_root'] = str(info['root'])
    report['recipe']['reference'] = info['reference']
    # Variable values can contain secrets; provenance records names only.
    report['recipe']['variable_names'] = sorted(context.vars)
    report['recipe']['resolved_path'] = str(directory)
    report['recipe']['selection_source'] = 'cli' if recipe is not None else 'hosts'
    report['hops'] = []
    local = None
    stage = 'connection_settings'
    dispatch_status = None
    try:
        progress('preparing connection')
        plan = connection_plan(config, host, session_class)
        local = session_class()
        session = local
        stage = 'connection'
        for index, settings in enumerate(plan, 1):
            options = dict(settings)
            hostname = options.pop('hostname')
            hop = {'index': index, 'connected': False}
            report['hops'].append(hop)
            progress(f'connecting hop {index}/{len(plan)} (per-stage timeout {timeout:g}s)')
            session = session.connect(hostname, ssh_config=False, timeout=timeout,
                                      banner_timeout=timeout, auth_timeout=timeout, **options)
            hop['connected'] = True
        stage = 'host_init'
        progress('checking cached host facts')
        facts = cached_facts(config, host)
        if facts is not None:
            try:
                if select(metadata['implementations'], facts['facts']) is None:
                    # Missing required facts may become available on a fresh probe.
                    facts = None
            except ConfigError:
                pass  # Preserve ambiguity for the explicit selection result below.
        if facts is None:
            progress('discovering host platform')
            facts = discover(session, host, timeout)
            facts.update(target_fingerprint=target_fingerprint(config, host), selection_source='probe')
            save_facts(config, host, facts)
        else:
            progress('using cached host facts')
            facts = dict(facts, selection_source='cache')
        report['host_init'] = facts
        report['sources'].append({'id': 'host-init', 'kind': 'host-facts',
                                  'observed_at': facts['observed_at'], 'facts': facts['facts']})
        if facts['status'] != 'success':
            dispatch_status = ('skipped', 'host_init_failed', 'Host initialization failed; recipe was not executed.')
        else:
            stage = 'implementation_selection'
            progress('selecting platform implementation')
            try:
                implementation = select(metadata['implementations'], facts['facts'])
            except ConfigError:
                implementation = None
                dispatch_status = ('failed', 'ambiguous_implementation', 'Multiple equally ranked implementations match this host.')
            if implementation is None and dispatch_status is None:
                dispatch_status = ('unsupported', 'unsupported_platform', 'No implementation matches the observed host facts.')
            if implementation is not None:
                entry = directory / implementation['entrypoint']
                report['recipe'].update(implementation_id=implementation['id'],
                                       implementation_version=implementation['version'],
                                       implementation_path=implementation['entrypoint'],
                                       implementation_sha256=hashlib.sha256(entry.read_bytes()).hexdigest())
                stage = 'implementation_loading'
                # runpy temporarily changes process-wide import state. Serialize
                # loading only; independent collectors execute concurrently.
                with _implementation_lock:
                    selected = runpy.run_path(str(entry))
                if selected.get('VERSION') != implementation['version'] or not callable(selected.get('collect')):
                    raise ConfigError('implementation runtime VERSION or collect function does not match contract')
                stage = 'collection'
                progress('collecting inventory with ' + json.dumps(implementation['id'], ensure_ascii=True))
                options = {'context': context} if supports_context(entry) else {}
                selected['collect'](session, report, timeout, facts['facts'], **options)
                stage = 'result_validation'
                progress('validating inventory result')
                validate_observations(report)
        if dispatch_status:
            kernel = facts.get('facts', {}).get('kernel_name')
            if kernel:
                collector['observe'](report, 'kernel_name', kernel, 'success', ['host-init'])

    except Exception as exc:
        progress(f'execution error at {stage}: {type(exc).__name__}')
        report['execution_errors'].append({'stage': stage, **connection_error(exc)})
    finally:
        if local is not None:
            try:
                progress('closing session')
                local.close(strict=True)
            except Exception as exc:
                progress(f'session cleanup failed: {type(exc).__name__}')
                report['execution_errors'].append({'stage': 'cleanup', 'type': type(exc).__name__})
                if report.get('host_init', {}).get('selection_source') == 'probe':
                    report['host_init'].update(status='failed', reason_code='cleanup_failed')
                    save_facts(config, host, report['host_init'])
    try:
        validate_observations(report)
    except ConfigError:
        report['observations'] = collector['new_report'](host, 'unknown')['observations']
        if not any(e['stage'] == 'result_validation' for e in report['execution_errors']):
            report['execution_errors'].append({'stage': 'result_validation', 'type': 'ConfigError'})
    platforms = report['supported_platforms']
    collector['finish'](report)
    report['supported_platforms'] = platforms
    if dispatch_status and not report['execution_errors']:
        report.update(status=dispatch_status[0], reason_code=dispatch_status[1], message=dispatch_status[2])
    progress('saving result')
    output_dir.mkdir(exist_ok=True)
    path = output_dir / f'inventory-system-{uuid4()}.json'
    with path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    return report, path


def select_hosts(root, selectors, all_hosts=False, exclude=None, excluded=None):
    """Resolve target union and exclusions before any host is executed."""
    config = Validator(root)
    config.load(config.root / 'hosts.yaml')
    config.check_connections()
    excluded = [] if excluded is None else excluded
    exclude = set(exclude or [])
    for host in exclude:
        if host not in config.hosts:
            raise ConfigError(f'unknown excluded host ID: {host}')
    groups = {}
    for host, settings in config.hosts.items():
        for group in group_names(settings.get('group', []), f'{config.sources[host]}: {host}.group'):
            groups.setdefault(group, []).append(host)
    selected, omitted = [], {}
    for kind, name in selectors:
        if kind == 'host':
            if name not in config.hosts:
                raise ConfigError(f'unknown host ID: {name}')
            matches = [name]  # Explicit disabled hosts produce a skipped result.
        elif kind == 'group':
            if name not in groups:
                raise ConfigError(f'unknown group: {name}')
            matches = []
            for host in groups[name]:
                if config.hosts[host].get('enabled', True):
                    matches.append(host)
                else:
                    omitted[host] = 'host_disabled'
        else:
            raise ConfigError(f'unknown target kind: {kind}')
        selected.extend(matches)
    if all_hosts:
        for host, settings in config.hosts.items():
            if not settings.get('enabled', True):
                omitted[host] = 'host_disabled'
            elif host in exclude:
                omitted[host] = 'cli_excluded'
            else:
                selected.append(host)
    selected = list(dict.fromkeys(selected))
    excluded.extend({'host': host, 'reason_code': reason} for host, reason in omitted.items() if host not in selected)
    if not selected:
        raise ConfigError('no hosts selected after filtering')
    return selected


class TargetAction(argparse.Action):
    """Preserve the argument order across repeated host and group options."""
    def __call__(self, parser, namespace, values, option_string=None):
        targets = getattr(namespace, self.dest, None) or []
        targets.extend((option_string[2:], value) for value in values)
        setattr(namespace, self.dest, targets)


class RecipeAction(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            parser.error('--recipe may only be specified once')
        setattr(namespace, self.dest, value)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('recipe_positional', nargs='?', metavar='RECIPE', help='recipe directory; must be the first argument')
    parser.add_argument('--root', type=Path, help='management directory (default: selected profile)')
    parser.add_argument('--host', nargs='+', metavar='HOST', dest='targets', action=TargetAction, help='one or more exact host IDs; repeatable')
    parser.add_argument('--group', nargs='+', metavar='GROUP', dest='targets', action=TargetAction, help='one or more exact group names; repeatable')
    parser.add_argument('--exclude', nargs='+', metavar='HOST', help='exclude exact host IDs for this invocation; requires --all')
    parser.add_argument('--all', dest='all_hosts', action='store_true', help='select every configured host, including local and jump hosts')
    parser.add_argument('--profile', help='profile for this invocation; does not change the default')
    parser.add_argument('--recipe', metavar='DIRECTORY', action=RecipeAction,
                        help='recipe directory at any argument position; alternative to leading RECIPE; omit recipes/ for checkout recipes')
    parser.add_argument('--timeout', type=positive_timeout, default=30,
                        help='per-hop connection stages and per-command seconds; not a whole-run deadline')
    parser.add_argument('--threads', type=positive_threads, default=default_threads(), metavar='N',
                        help='concurrent hosts (default: min(8, CPU count), fallback 1); use 1 for sequential execution')
    output_options = parser.add_mutually_exclusive_group()
    output_options.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                                help='show progress on stderr even when stdout is redirected')
    output_options.add_argument('-q', '--quiet', dest='verbose', action='store_false',
                                help='suppress progress; errors and final JSON remain visible')
    parser.set_defaults(verbose=None)
    args = parser.parse_args(argv)
    if args.recipe_positional is not None and (not argv or argv[0] != args.recipe_positional):
        parser.error('positional RECIPE must be the first argument; use --recipe elsewhere')
    if args.recipe_positional is not None and args.recipe is not None:
        parser.error('specify either leading RECIPE or --recipe, not both')
    recipe = args.recipe_positional if args.recipe_positional is not None else args.recipe
    if recipe is None:
        parser.error('specify leading RECIPE or --recipe DIRECTORY')
    if not args.targets and not args.all_hosts:
        parser.error('specify --host, --group, or --all')
    if args.targets and args.all_hosts:
        parser.error('--all cannot be combined with --host or --group')
    if args.exclude and not args.all_hosts:
        parser.error('--exclude requires --all')
    show_progress = sys.stdout.isatty() if args.verbose is None else args.verbose
    excluded = []
    try:
        with reporting(show_progress, '[setup]'):
            progress('resolving environment and targets')
            root = resolve_root(args.root, args.profile)
            hosts = select_hosts(root, args.targets or [], args.all_hosts, args.exclude, excluded)
            workers = min(args.threads, len(hosts))
            progress(f'selected {len(hosts)} host(s); concurrency {workers}')
        def execute(host, index):
            label = f'[{index}/{len(hosts)}] {json.dumps(host, ensure_ascii=True)}:'
            with reporting(show_progress, label):
                try:
                    item, path = run(root, host, args.timeout, recipe=recipe)
                except Exception as exc:
                    progress(f'failed before completion: {type(exc).__name__}')
                    raise
                progress(f"completed: {item['status']} ({item['reason_code']})")
                return item, path
        if args.all_hosts or len(hosts) > 1:
            def execute_summary(target):
                index, host = target
                try:
                    item, path = execute(host, index)
                    return dict(host=host, status=item['status'], reason_code=item['reason_code'], result_path=str(path) if path is not None else None)
                except Exception as exc:
                    return dict(host=host, status='failed', error=type(exc).__name__)
            targets = enumerate(hosts, 1)
            if workers == 1:
                reports = [execute_summary(target) for target in targets]
            else:
                with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='recipe-host') as pool:
                    # map preserves selection order in JSON, while each worker
                    # reports completion immediately through its own context.
                    reports = list(pool.map(execute_summary, targets))
            summary = {'hosts': reports}
            if excluded:
                summary['excluded_hosts'] = excluded
            print(json.dumps(summary, indent=2))
            return 0 if all(r['status'] == 'success' for r in reports) else 1
        report, path = execute(hosts[0], 1)
        summary = {key: report[key] for key in (
            'status', 'reason_code', 'message', 'detected_kernel', 'supported_platforms')}
        summary.update(recipe_id=report['recipe']['id'], result_path=str(path) if path is not None else None)
        if excluded:
            summary['excluded_hosts'] = excluded
        print(json.dumps(summary, indent=2))
        return 0 if report['status'] == 'success' else 1
    except (ConfigError, OSError, ImportError) as exc:
        # Do not print third-party exception text or potentially sensitive config values.
        if excluded:
            print(json.dumps({'hosts': [], 'excluded_hosts': excluded}, indent=2))
        print(f'ERROR: {str(exc) if isinstance(exc, ConfigError) else type(exc).__name__}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
