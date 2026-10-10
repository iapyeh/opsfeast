"""Run one selected, installed inventory-system recipe and save its result."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import runpy
import sys
from uuid import uuid4

from my_ops import ConfigError, Validator, connection_plan, connection_error, positive_timeout, read_yaml

BUNDLE = Path(__file__).resolve().parents[1] / 'recipes/inventory/system'
collector = runpy.run_path(str(BUNDLE / 'main.py'))


def load_runtime():
    import sshscript
    installed = version('sshscript')
    if installed != sshscript.__version__ or installed != '5.0.0':
        raise ConfigError('runner requires matching SSHScript import/distribution 5.0.0; no automatic upgrade')
    return sshscript.Session, {'python': sys.version.split()[0], 'interpreter': sys.executable,
                               'sshscript_import': sshscript.__version__, 'sshscript_distribution': installed}


def preflight(root, host):
    config = Validator(root)
    config.load(config.root / 'hosts.yaml')
    config.check_connections()
    if host not in config.hosts:
        raise ConfigError(f'unknown host ID: {host}')
    config.recipes(host, config.hosts[host])
    selected = config.selected[host]
    matches = [path for path in selected if read_yaml(path / 'recipe.yaml').get('id') == 'inventory-system']
    if len(matches) != 1:
        raise ConfigError('select exactly one installed inventory-system recipe for this host')
    directory = matches[0]
    metadata = read_yaml(directory / 'recipe.yaml')
    if metadata != read_yaml(BUNDLE / 'recipe.yaml'):
        raise ConfigError('installed inventory-system descriptor differs from this runner bundle')
    entry = config.inside(directory / 'main.py')
    digest = hashlib.sha256(entry.read_bytes()).hexdigest()
    if digest != hashlib.sha256((BUNDLE / 'main.py').read_bytes()).hexdigest():
        raise ConfigError('installed inventory-system implementation differs from this runner bundle')
    output_dir = config.root / 'observations'
    if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
        raise ConfigError('observations must be a real directory within management root')
    return config, directory, digest, output_dir


def run(root, host, timeout=30, session_class=None, runtime=None):
    timeout = positive_timeout(timeout)
    config, directory, digest, output_dir = preflight(root, host)
    if session_class is None:
        session_class, runtime = load_runtime()
    report = collector['new_report'](host, 'local' if config.hosts[host]['connection'].get('local') else 'ssh')
    report['runtime'] = runtime or {'verification': 'mock'}
    if runtime is None:
        report['evidence_kind'] = 'mock'
    report['recipe']['implementation_sha256'] = digest
    report['recipe']['installed_path'] = directory.relative_to(config.root).as_posix()
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
    parser.add_argument('root', type=Path)
    parser.add_argument('--timeout', type=positive_timeout, default=30,
                        help='per-hop connection stages and per-command seconds; not a whole-run deadline')
    args = parser.parse_args(argv)
    try:
        report, path = run(args.root, args.host, args.timeout)
        print(json.dumps({'status': report['status'], 'result_path': str(path)}, indent=2))
        return 0 if report['status'] == 'success' else 1
    except (ConfigError, OSError, ImportError) as exc:
        # Do not print third-party exception text or potentially sensitive config values.
        print(f'ERROR: {str(exc) if isinstance(exc, ConfigError) else type(exc).__name__}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
