"""Internal host recipe execution, target selection and result persistence. No CLI."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import runpy
import sys
import threading
import tempfile
import time
from uuid import uuid4
from terminal_events import emit
from console_output import print_report

from host_runtime import connected, now
from recipe_dispatch import validate, bundle_digest
from recipe_inputs import RecipeContext, prepare_vars, cli_variables
import recipe_contract

from opsfeast import ConfigError, Validator, REPOSITORY_ROOT, positive_timeout, read_yaml, mapping

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
    def __init__(self, label, interval=5, host=None):
        self.label, self.interval = label, interval
        self.host = host
        self.stage = 'starting'
        self.changed = time.monotonic()
        self.stop = threading.Event()
        self.lock = threading.Lock()

    def update(self, message):
        with self.lock:
            self.stage, self.changed = message, time.monotonic()
            emit('stage', host=self.host, stage=message)
            progress_line(f'{self.label} {message}')

    def heartbeat(self):
        while not self.stop.wait(self.interval):
            with self.lock:
                elapsed = time.monotonic() - self.changed
                if elapsed >= self.interval:
                    progress_line(f'{self.label} still {self.stage} ({elapsed:.0f}s in this stage)')


@contextmanager
def reporting(enabled, label, host=None):
    reporter = RunProgress(label, host=host) if enabled else None
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


def inventory_result_filename(started_at):
    """Internal storage name: UTC start second plus an independent run UUID."""
    started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
    if started.tzinfo is None:
        raise ValueError('inventory start time requires a timezone')
    prefix = started.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return f'{prefix}-inventory-system-{uuid4()}.json'


def save_report(path, report):
    """Readers see complete JSON; a failed replacement preserves the old report."""
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.inventory-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_receipt(path, report):
    """Preserve the durable original raw if the final receipt cannot be replaced."""
    try:
        save_report(path, report)
    except OSError as exc:
        report['retention'] = {'status':'failed','reason_code':'receipt_save_failed',
                               'error_type':type(exc).__name__}


def preflight(root, host, recipe, cli_vars=None, assignments=()):
    config = Validator(root)
    config.load(config.root / 'hosts.yaml')
    config.check_connections()
    if host not in config.hosts:
        raise ConfigError(f'unknown host ID: {host}')
    info = config.recipe_location(str(recipe), config.root / 'hosts.yaml', cli=True,
                                  check_exists=config.hosts[host].get('enabled', True))
    if not config.hosts[host].get('enabled', True) or not info['enabled']:
        config.execution_recipe = dict(info, reason_code='host_disabled' if not config.hosts[host].get('enabled', True) else 'source_disabled')
        return config, None, None, None
    directory = info['scope'].path(info['pattern'], info['origin'])
    metadata = mapping(read_yaml(info['scope'].inside(directory / 'recipe.yaml')), 'recipe.yaml')
    if metadata.get('id') == 'inventory-system':
        from inventory_jobs import inspect_collection
        validate(directory, metadata)
        inspect_collection(directory, metadata)
        if metadata.get('access_mode') != 'read':
            raise ConfigError('inventory job collection requires access_mode read')
    else:
        recipe_contract.validate(directory, metadata)
        if metadata['runner']['contract'] == recipe_contract.REPORT_CONTRACT:
            raise ConfigError('offline report recipes use opsfeast.py recipes run without host selectors')
    variables = prepare_vars(metadata, info['vars'], config.matching_recipe_vars(host, directory, info),
                             cli_variables(metadata, cli_vars, assignments))
    config.execution_recipe = dict(info, effective_vars=variables, metadata=metadata)
    digest = bundle_digest(directory)
    output_dir = config.root / 'observations'
    if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
        raise ConfigError('observations must be a real directory within management root')
    return config, directory, digest, output_dir

def run_general(config, host, directory, digest, output_dir, timeout, session_class, runtime):
    info = config.execution_recipe
    metadata = info['metadata']
    entry = directory / metadata['runner']['entrypoint']
    source_root = REPOSITORY_ROOT.resolve() if info['name'] == 'repository' else info['root']
    report = {
        'run_contract': recipe_contract.VERSION, 'schema_version': metadata['output']['schema_version'],
        'host_id': host, 'started_at': now(), 'completed_at': None,
        'status': 'failed', 'reason_code': 'execution_failed', 'message': 'Recipe execution failed.', 'data': {},
        'detected_kernel': None, 'supported_platforms': metadata.get('platforms', {}).get('implemented', []),
        'evidence_kind': 'mock' if runtime is None else ('local' if config.hosts[host]['connection'].get('local') else 'ssh'),
        'runtime': runtime or {'verification': 'mock'}, 'hops': [], 'execution_errors': [],
        'host_metadata': {key: config.hosts[host][key] for key in ('label', 'description') if key in config.hosts[host]},
        'recipe': {'id': metadata['id'], 'version': metadata['version'], 'recipe_version': metadata['version'],
                   'runner_contract': metadata['runner']['contract'], 'runner_version': metadata['runner']['version'],
                   'entrypoint': metadata['runner']['entrypoint'],
                   'implementation_sha256': hashlib.sha256(entry.read_bytes()).hexdigest(),
                   'descriptor_sha256': hashlib.sha256((directory / 'recipe.yaml').read_bytes()).hexdigest(),
                   'bundle_sha256': digest, 'installed_path': directory.relative_to(source_root).as_posix(),
                   'source_name': info['name'], 'source_root': str(info['root']),
                   'reference': info['reference'], 'resolved_path': str(directory),
                   'variable_names': sorted(info['effective_vars']), 'selection_source': 'cli'},
        'retention': {'status': 'skipped', 'reason_code': 'no_retention_adapter'},
    }
    from retention_replay import snapshot
    report['source_observation_id'] = str(uuid4())
    from opsfeast.identity import read_identity
    report['producer_instance_id'] = read_identity(REPOSITORY_ROOT)['id']
    report['execution_access_mode'] = metadata.get('access_mode', 'unknown')
    report['retention_snapshot'] = snapshot(metadata, directory)
    from retention_store import operation_intent, operation_result
    intent = operation_intent(config.root, host, metadata, report['recipe']['descriptor_sha256'], info['effective_vars'],
                              reference=info['reference'], implementation_digest=report['recipe']['implementation_sha256'],
                              source_observation_id=report['source_observation_id'])
    if intent is not None:
        report['operation_intent_id'] = intent['record_id']
    stage = 'connection'
    try:
        progress('preparing recipe connection')
        with connected(config, host, session_class, timeout, report) as session:
            stage = 'implementation_loading'
            with _implementation_lock:
                selected = runpy.run_path(str(entry))
            if selected.get('VERSION') != metadata['version'] or not callable(selected.get('execute')):
                raise ConfigError('recipe runtime VERSION or execute does not match contract')
            stage = 'execution'
            progress('executing recipe ' + json.dumps(metadata['id'], ensure_ascii=True))
            context = RecipeContext(host, info['effective_vars'])
            if metadata['runner']['contract'] == recipe_contract.CORE_CONTRACT:
                from opsfeast import Instance, Profile, Recipe
                instance = Instance.open(REPOSITORY_ROOT)
                profile = Profile._from_config(instance, config)
                execution = Recipe._create(profile, config, host, session, timeout, report,
                                           vars=info['effective_vars'], owner='runner')
                report['instance'] = dict(execution._state.identity)
                report['profile'] = profile.name
                report['run_id'] = execution.run_id
                try:
                    result = selected['execute'](execution)
                finally:
                    execution._state.active = False
                    execution._active = False
            else:
                result = selected['execute'](session, context=context, timeout=timeout)
            stage = 'result_validation'
            report.update(recipe_contract.validate_result(result))
    except (Exception, SystemExit) as exc:
        report.update(status='failed', reason_code='invalid_result' if stage == 'result_validation' else 'execution_failed',
                      message='Recipe result is invalid.' if stage == 'result_validation' else 'Recipe execution failed.')
        # Custom exception text may contain input values; preserve type/stage only.
        report['execution_errors'].append({'stage': stage, 'type': type(exc).__name__})
    if report.get('scope_error'):
        report.update(status='failed', reason_code=report['scope_error'], message='Session identity verification failed.')
    if 'cleanup_error' in report:
        report.update(status='failed', reason_code='cleanup_failed', message='Session cleanup failed.')
        report['execution_errors'].append({'stage': 'cleanup', 'type': report['cleanup_error']})
    report['completed_at'] = now()
    output_dir.mkdir(exist_ok=True)
    path = output_dir / f'recipe-run-{uuid4()}.json'
    progress('saving recipe result')
    save_report(path, report)
    try:
        operation_result(config.root, intent, report)
    except Exception as exc:
        report['operation_recording'] = {'status': 'failed', 'error_type': type(exc).__name__}
        report['execution_status'] = report['status']
        report.update(status='failed', reason_code='operation_recording_failed',
                      message='Operation outcome could not be recorded; saved intent remains unresolved.')
    from retention_store import retain_general
    try:
        report['retention'] = retain_general(config.root, report, metadata, directory, saved_snapshot=report['retention_snapshot'])
    except Exception as exc:
        report['retention'] = {'status': 'failed', 'reason_code': 'retention_failed', 'error_type': type(exc).__name__}
    finalize_content(config.root, report)
    save_receipt(path, report)
    return report, path

def run(root, host, timeout=30, session_class=None, runtime=None, *, recipe, cli_vars=None, assignments=()):
    """Execute a reviewed explicit recipe; inventory always uses the job collector."""
    timeout = positive_timeout(timeout)
    progress('validating configuration and recipe')
    config, directory, digest, output_dir = preflight(root, host, recipe, cli_vars, assignments)
    if directory is None:
        info = config.execution_recipe
        return {'host_id': host, 'status': 'skipped', 'reason_code': info['reason_code'],
                'message': 'Host or recipe source is disabled.', 'evidence_kind': 'not-executed',
                'recipe': {'id': None, 'reference': info.get('reference')}}, None
    if config.execution_recipe['metadata'].get('collection'):
        from inventory_jobs import collect_host
        report = collect_host(root, host, save=True, reference=recipe, timeout=timeout,
                              session_class=session_class, cli_values=cli_vars, assignments=assignments)
        return report, Path(report['result_path']) if report.get('result_path') else None
    if session_class is None:
        progress('checking execution runtime')
        session_class, runtime = load_runtime()
    return run_general(config, host, directory, digest, output_dir, timeout, session_class, runtime)


def finalize_content(root, report):
    """Dispatch retention consumers after data/audit writes; preserve execution status."""
    receipt = report.get('retention', {})
    content = receipt.pop('content_update', None)
    if content is None:
        from retention_store import settings, refresh_content
        content = refresh_content(root) if settings(root) is not None else {'status': 'skipped', 'reason_code': 'retention_not_initialized'}
    report['content_update'] = content


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
    groups = {group: definition['hosts'] for group, definition in config.groups.items()}
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



def execute_hosts(root, recipe, inv, *, json_output=False):
    """Shared operation batch for recipes run and saved jobs; no command parsing."""
    from recipe_inputs import json_object
    excluded = []
    try:
        hosts = select_hosts(root, inv['targets'], inv['all'], inv['exclude'], excluded)
    except ConfigError:
        if excluded:
            print(json.dumps({'hosts':[], 'excluded_hosts':excluded}))
        raise
    values = json_object(Path(inv['vars_file'])) if inv['vars_file'] else None
    workers = min(inv['threads'] or default_threads(), len(hosts))
    show_progress = not inv['quiet'] and (inv['verbose'] or sys.stdout.isatty())
    icons = {}
    if sys.stdout.isatty() and not json_output:
        from access_check import host_icons
        icons = host_icons(root, hosts + [item['host'] for item in excluded])
    emit('selected', hosts=hosts)
    def execute(target):
        index, host = target
        label = f'[{index}/{len(hosts)}] {json.dumps(host, ensure_ascii=True)}:'
        with reporting(show_progress, label, host=host):
            try:
                report, path = run(root, host, inv['timeout'], recipe=recipe,
                                   cli_vars=values, assignments=inv['assignments'])
                progress(f"completed: {report['status']} ({report.get('reason_code', 'unknown')})")
                emit('result', host=host, status=report['status'], reason_code=report.get('reason_code'),
                     result_path=str(path) if path else None, retention=report.get('retention'),
                     content_update=report.get('content_update'))
                return report, path
            except Exception as exc:
                progress(f'failed before completion: {type(exc).__name__}')
                emit('result', host=host, status='failed', reason_code=type(exc).__name__)
                return {'host_id': host, 'status': 'failed', 'reason_code': type(exc).__name__,
                        'error': type(exc).__name__}, None
    targets = enumerate(hosts, 1)
    if workers == 1:
        results = [execute(item) for item in targets]
    else:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='recipe-host') as pool:
            results = list(pool.map(execute, targets))
    summaries = []
    for host, (report, path) in zip(hosts, results):
        summary = {key: report[key] for key in ('status', 'reason_code', 'message', 'data', 'retention', 'content_update', 'access', 'actor') if key in report}
        summary.update(host=host, result_path=str(path) if path else None)
        summaries.append(summary)
    result = {'hosts': summaries} if inv['all'] or len(hosts)>1 else dict(summaries[0])
    if excluded:
        result['excluded_hosts'] = excluded
    print_report(result, json_output=json_output, kind='execution', icons=icons,
                 recipe=recipe, host=hosts[0] if len(hosts)==1 else None, ensure_ascii=True)
    return 0 if all(r['status']=='success' and
        not (r.get('access') or {}).get('degraded') and
        (r.get('retention') or {}).get('status')!='failed' and
        (r.get('content_update') or {}).get('status')!='failed' for r in summaries) else 1
