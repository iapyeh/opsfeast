"""Run one selected inventory-system recipe from the checkout and save its result."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import runpy
import sys
from uuid import uuid4

from host_runtime import discover, cached_facts, cache_path, save_facts, target_fingerprint
from recipe_dispatch import validate, select, bundle_digest, validate_observations

from ops import ConfigError, Validator, REPOSITORY_ROOT, REPOSITORY_RECIPES, connection_plan, connection_error, positive_timeout, read_yaml, mapping, resolve_root

BUNDLE = Path(__file__).resolve().parents[1] / 'recipes/inventory/system'
collector = runpy.run_path(str(BUNDLE / 'main.py'))


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
    if recipe is not None:
        text = str(recipe)
        if text == 'recipes' or text.startswith('recipes/'):
            raise ConfigError('omit the recipes/ prefix from --recipe; use inventory/system')
        # Bare CLI paths are checkout-relative; explicit ./ paths stay instance-relative.
        if text and not Path(text).is_absolute() and not text.startswith(('./', '../')):
            text = 'recipes/' + text
        scope, pattern, source = config.recipe_scope(text, config.root / 'hosts.yaml')
        directory = scope.path(pattern, source)
        if not directory.is_dir():
            raise ConfigError('CLI recipe directory does not exist')
    else:
        config.recipes(host, config.hosts[host])
        selected = config.selected[host]
        matches = [path for path in selected if read_yaml(path / 'recipe.yaml').get('id') == 'inventory-system']
        if len(matches) != 1:
            raise ConfigError('select exactly one inventory-system recipe for this host or pass --recipe DIRECTORY')
        directory = matches[0]
    descriptor = config.recipe_inside(directory / 'recipe.yaml')
    if not descriptor.is_file():
        raise ConfigError('selected recipe directory must contain recipe.yaml')
    metadata = mapping(read_yaml(descriptor), str(descriptor))
    if metadata.get('id') != 'inventory-system':
        raise ConfigError('this minimal runner only supports inventory-system')
    validate(directory, metadata)
    # The shared report helper is still internal to the trusted runner.
    digest = bundle_digest(directory)
    cache_path(config, host)
    output_dir = config.root / 'observations'
    if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
        raise ConfigError('observations must be a real directory within management root')
    return config, directory, digest, output_dir


def run(root, host, timeout=30, session_class=None, runtime=None, recipe=None):
    timeout = positive_timeout(timeout)
    config, directory, digest, output_dir = preflight(root, host, recipe)
    if session_class is None:
        session_class, runtime = load_runtime()
    report = collector['new_report'](host, 'local' if config.hosts[host]['connection'].get('local') else 'ssh')
    report['runtime'] = runtime or {'verification': 'mock'}
    if runtime is None:
        report['evidence_kind'] = 'mock'
    metadata = read_yaml(directory / 'recipe.yaml')
    report['schema_version'] = metadata['output']['schema_version']
    report['recipe'].update(version=metadata['version'], recipe_version=metadata['version'], bundle_sha256=digest)
    report['supported_platforms'] = sorted({e['match'].get('os_name') for e in metadata['implementations'] if e['match'].get('os_name')})
    repository_recipe = directory.is_relative_to(REPOSITORY_RECIPES)
    report['recipe']['installed_path'] = directory.relative_to(REPOSITORY_ROOT if repository_recipe else config.root).as_posix()
    report['recipe']['location_source'] = 'repository' if repository_recipe else 'instance'
    report['recipe']['resolved_path'] = str(directory)
    report['recipe']['selection_source'] = 'cli' if recipe is not None else 'hosts'
    report['hops'] = []
    local = None
    stage = 'connection_settings'
    dispatch_status = None
    try:
        plan = connection_plan(config, host, session_class)
        local = session_class()
        session = local
        stage = 'connection'
        for index, settings in enumerate(plan, 1):
            options = dict(settings)
            hostname = options.pop('hostname')
            hop = {'index': index, 'connected': False}
            report['hops'].append(hop)
            session = session.connect(hostname, ssh_config=False, timeout=timeout,
                                      banner_timeout=timeout, auth_timeout=timeout, **options)
            hop['connected'] = True
        stage = 'host_init'
        facts = cached_facts(config, host)
        if facts is not None:
            try:
                if select(metadata['implementations'], facts['facts']) is None:
                    # Missing required facts may become available on a fresh probe.
                    facts = None
            except ConfigError:
                pass  # Preserve ambiguity for the explicit selection result below.
        if facts is None:
            facts = discover(session, host, timeout)
            facts.update(target_fingerprint=target_fingerprint(config, host), selection_source='probe')
            save_facts(config, host, facts)
        else:
            facts = dict(facts, selection_source='cache')
        report['host_init'] = facts
        report['sources'].append({'id': 'host-init', 'kind': 'host-facts',
                                  'observed_at': facts['observed_at'], 'facts': facts['facts']})
        if facts['status'] != 'success':
            dispatch_status = ('skipped', 'host_init_failed', 'Host initialization failed; recipe was not executed.')
        else:
            stage = 'implementation_selection'
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
                selected = runpy.run_path(str(entry))
                if selected.get('VERSION') != implementation['version'] or not callable(selected.get('collect')):
                    raise ConfigError('implementation runtime VERSION or collect function does not match contract')
                stage = 'collection'
                selected['collect'](session, report, timeout, facts['facts'])
                stage = 'result_validation'
                validate_observations(report)
        if dispatch_status:
            kernel = facts.get('facts', {}).get('kernel_name')
            if kernel:
                collector['observe'](report, 'kernel_name', kernel, 'success', ['host-init'])

    except Exception as exc:
        report['execution_errors'].append({'stage': stage, **connection_error(exc)})
    finally:
        if local is not None:
            try:
                local.close(strict=True)
            except Exception as exc:
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
    output_dir.mkdir(exist_ok=True)
    path = output_dir / f'inventory-system-{uuid4()}.json'
    with path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    return report, path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('host')
    parser.add_argument('root', type=Path, nargs='?', help='management directory (default: selected profile)')
    parser.add_argument('--hosts', nargs='+', help='additional host IDs; each is initialized and dispatched independently')
    parser.add_argument('--profile', help='profile for this invocation; does not change the default')
    parser.add_argument('--recipe', metavar='DIRECTORY',
                        help='inventory/system selects this checkout (omit recipes/); ./paths select within management root; overrides host recipe selection')
    parser.add_argument('--timeout', type=positive_timeout, default=30,
                        help='per-hop connection stages and per-command seconds; not a whole-run deadline')
    args = parser.parse_args(argv)
    try:
        root = resolve_root(args.root, args.profile)
        if args.hosts:
            reports = []
            for host in dict.fromkeys([args.host, *args.hosts]):
                try:
                    item, path = run(root, host, args.timeout, recipe=args.recipe)
                    reports.append(dict(host=host, status=item['status'], reason_code=item['reason_code'], result_path=str(path)))
                except (ConfigError, OSError, ImportError) as exc:
                    reports.append(dict(host=host, status='failed', error=type(exc).__name__))
            print(json.dumps({'hosts': reports}, indent=2))
            return 0 if all(r['status'] == 'success' for r in reports) else 1
        report, path = run(root, args.host, args.timeout, recipe=args.recipe)
        summary = {key: report[key] for key in (
            'status', 'reason_code', 'message', 'detected_kernel', 'supported_platforms')}
        summary.update(recipe_id=report['recipe']['id'], result_path=str(path))
        print(json.dumps(summary, indent=2))
        return 0 if report['status'] == 'success' else 1
    except (ConfigError, OSError, ImportError) as exc:
        # Do not print third-party exception text or potentially sensitive config values.
        print(f'ERROR: {str(exc) if isinstance(exc, ConfigError) else type(exc).__name__}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
