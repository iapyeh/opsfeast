"""Released SSHScript package identity and reviewed source contract."""
import hashlib
import json
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / 'schemas/sshscript-runtime.json'
CONTRACT = json.loads(MANIFEST.read_text(encoding='utf-8'))
VERSION = CONTRACT['version']
SOURCE_COMMIT = CONTRACT['source_commit']
REQUIREMENT = CONTRACT['requirement']


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
