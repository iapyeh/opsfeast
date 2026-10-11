"""Run one selected inventory-system recipe from the checkout and save its result."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import runpy
import sys
from uuid import uuid4

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
        # Bare CLI paths are checkout-relative; explicit ./ paths stay instance-relative.
        if (text and not Path(text).is_absolute() and not text.startswith(('./', '../'))
                and text != 'recipes' and not text.startswith('recipes/')):
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
    if metadata != read_yaml(BUNDLE / 'recipe.yaml'):
        raise ConfigError('selected inventory-system descriptor differs from this runner bundle')
    entry = config.recipe_inside(directory / 'main.py')
    digest = hashlib.sha256(entry.read_bytes()).hexdigest()
    if digest != hashlib.sha256((BUNDLE / 'main.py').read_bytes()).hexdigest():
        raise ConfigError('selected inventory-system implementation differs from this runner bundle')
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
    report['recipe']['implementation_sha256'] = digest
    repository_recipe = directory.is_relative_to(REPOSITORY_RECIPES)
    report['recipe']['installed_path'] = directory.relative_to(REPOSITORY_ROOT if repository_recipe else config.root).as_posix()
    report['recipe']['location_source'] = 'repository' if repository_recipe else 'instance'
    report['recipe']['resolved_path'] = str(directory)
    report['recipe']['selection_source'] = 'cli' if recipe is not None else 'hosts'
    report['hops'] = []
    local = None
    stage = 'connection_settings'
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
        stage = 'collection'
        collector['collect'](session, report, timeout)
    except Exception as exc:
        report['execution_errors'].append({'stage': stage, **connection_error(exc)})
    finally:
        if local is not None:
            try:
                local.close(strict=True)
            except Exception as exc:
                report['execution_errors'].append({'stage': 'cleanup', 'type': type(exc).__name__})
    collector['finish'](report)
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
    parser.add_argument('--profile', help='profile for this invocation; does not change the default')
    parser.add_argument('--recipe', metavar='DIRECTORY',
                        help='inventory/system (or recipes/...) selects this checkout; ./paths select within management root; overrides host recipe selection')
    parser.add_argument('--timeout', type=positive_timeout, default=30,
                        help='per-hop connection stages and per-command seconds; not a whole-run deadline')
    args = parser.parse_args(argv)
    try:
        report, path = run(resolve_root(args.root, args.profile), args.host, args.timeout, recipe=args.recipe)
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
