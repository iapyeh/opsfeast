"""Released SSHScript package identity and reviewed source contract."""
import hashlib
import json
from importlib import import_module, metadata
from pathlib import Path
import shlex
import sys

MANIFEST = Path(__file__).resolve().parents[1] / 'schemas/sshscript-runtime.json'
CONTRACT = json.loads(MANIFEST.read_text(encoding='utf-8'))
VERSION = CONTRACT['version']
SOURCE_COMMIT = CONTRACT['source_commit']
REQUIREMENT = CONTRACT['requirement']


def inspect_runtime(module=None):
    """Read installed identity without creating Sessions or exposing import errors."""
    report = {'interpreter': sys.executable, 'required_version': VERSION,
              'reviewed_source_commit': SOURCE_COMMIT,
              'import_version': None, 'distribution_version': None,
              'module_path': None, 'distributions': [], 'ready': False}
    import_error = None
    try:
        module = module if module is not None else import_module('sshscript')
        report.update(import_version=getattr(module, '__version__', None),
                      module_path=getattr(module, '__file__', None))
    except Exception as exc:
        import_error = type(exc).__name__
        report['import_error_type'] = import_error
    metadata_error = None
    try:
        report['distribution_version'] = metadata.version('sshscript')
        seen = set()
        for dist in metadata.distributions():
            if (dist.metadata.get('Name') or '').lower().replace('_', '-').replace('.', '-') != 'sshscript':
                continue
            metadata_path = getattr(dist, '_path', None)
            path = str(metadata_path if metadata_path is not None else dist.locate_file(''))
            identity = str(Path(path).resolve())
            if identity not in seen:
                seen.add(identity)
                report['distributions'].append({'version': dist.version, 'metadata_path': path})
    except metadata.PackageNotFoundError:
        metadata_error = 'sshscript_metadata_missing'
    except Exception as exc:
        metadata_error = 'sshscript_metadata_unreadable'
        report['metadata_error_type'] = type(exc).__name__
    report['distributions'].sort(key=lambda item: item['metadata_path'])
    if import_error:
        reason = 'sshscript_import_failed'
    elif metadata_error:
        reason = metadata_error
    elif len(report['distributions']) > 1:
        reason = 'sshscript_duplicate_metadata'
    elif report['import_version'] != VERSION or report['distribution_version'] != VERSION:
        reason = 'sshscript_version_mismatch'
    else:
        report['source'] = source_identity(module)
        reason = None if report['source']['source_matches'] else 'sshscript_source_mismatch'
    report['ready'] = reason is None
    if reason:
        report['reason'] = reason
        report['summary'] = {
            'sshscript_import_failed': 'SSHScript could not be imported in this interpreter.',
            'sshscript_metadata_missing': 'SSHScript installation metadata is missing.',
            'sshscript_metadata_unreadable': 'SSHScript installation metadata could not be inspected.',
            'sshscript_duplicate_metadata': 'Multiple SSHScript installation metadata records were found.',
            'sshscript_version_mismatch': 'SSHScript import and distribution versions must both match the required version.',
            'sshscript_source_mismatch': 'SSHScript package files do not match the reviewed release source.',
        }[reason]
        python = shlex.quote(sys.executable)
        report['hint'] = ('Review this interpreter and installation records before changing the environment. '
                          'With environment-change authorization, uninstall and reinstall the required release, '
                          'then rerun the environment check. Do not delete site-packages or rebuild the environment. '
                          'Restart long-running OpsFeast processes after repair; checks never install packages.')
        report['repair_commands'] = [
            f'{python} -m pip uninstall sshscript',
            f'{python} -m pip install --force-reinstall --no-deps --no-cache-dir '
            f'--index-url https://pypi.org/simple {shlex.quote(REQUIREMENT)}',
            f'{python} -B {shlex.quote(str(MANIFEST.parents[1] / "tools/check_environment.py"))} --json',
            f'{python} -m pip check',
        ]
    return report


def require_runtime():
    """Shared pre-Session gate for diagnostics, Core and runner."""
    from opsfeast import RuntimeEnvironmentError
    report = inspect_runtime()
    if not report['ready']:
        raise RuntimeEnvironmentError(report)
    return import_module('sshscript'), report


def source_identity(module=None):
    """Compare installed package modules/type files with the reviewed source bytes.

    No network, installation, Session creation or reliance on a version label.
    The manifest binds the public source snapshot, not local checkout paths.
    """
    report = {'source_commit': SOURCE_COMMIT, 'source_matches': False,
              'expected_files': len(CONTRACT['files'])}
    try:
        if module is None:
            import sshscript as module
        root = Path(module.__file__).resolve().parent
        actual = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in root.iterdir() if p.is_file()
                  and (p.suffix in ('.py', '.pyi') or p.name == 'py.typed')}
        report['source_matches'] = actual == CONTRACT['files']
        report['checked_files'] = len(actual)
    except (ImportError, AttributeError, OSError, TypeError) as exc:
        report['error_type'] = type(exc).__name__
    return report


def require_source(module):
    from opsfeast import ConfigError
    report = source_identity(module)
    if not report['source_matches']:
        raise ConfigError(f'SSHScript {VERSION} must match reviewed source {SOURCE_COMMIT}; '
                          'no automatic installation or fallback')
    return report
