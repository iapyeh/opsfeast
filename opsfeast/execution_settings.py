"""Installation recipe execution defaults 0.1.0; saving never executes work."""
import argparse
import hashlib
import json
from pathlib import Path

from . import ConfigError
from .identity import _locked
from .site import SiteConflict, _atomic

FILENAME = 'recipe-execution-settings.json'
DEFAULT_THREADS = 8


def validate_threads(value):
    if type(value) is not int or value < 1:
        raise ConfigError('threads must be a positive integer')
    return value


def inspect(data_root):
    root = Path(data_root)
    path = root / FILENAME
    if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_size > 8192)):
        raise ConfigError('invalid execution settings file')
    raw = path.read_bytes() if path.exists() else b''
    try:
        data = json.loads(raw) if raw else {'schema_version': '0.1.0', 'threads': DEFAULT_THREADS}
    except (ValueError, UnicodeError):
        raise ConfigError('invalid execution settings JSON') from None
    if not isinstance(data, dict) or set(data) != {'schema_version', 'threads'} or data['schema_version'] != '0.1.0':
        raise ConfigError('invalid execution settings schema')
    validate_threads(data['threads'])
    return {**data, 'revision': hashlib.sha256(raw).hexdigest()}


def save(data_root, *, threads, expected_revision):
    validate_threads(threads)
    root = Path(data_root)
    with _locked(root / FILENAME):
        current = inspect(root)
        if current['revision'] != expected_revision:
            raise SiteConflict('execution settings changed; reload before saving')
        data = {'schema_version': '0.1.0', 'threads': threads}
        _atomic(root / FILENAME, (json.dumps(data, indent=2) + '\n').encode())
        return inspect(root)


def main():
    parser = argparse.ArgumentParser(description='Read/save recipe execution defaults as JSON; no host access.')
    parser.add_argument('action', choices=['show', 'set'])
    parser.add_argument('--installation', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--threads', type=int)
    parser.add_argument('--expected-revision')
    args = parser.parse_args()
    from .storage import resolve_data_root
    try:
        root = resolve_data_root(args.installation, required=True)
        if args.action == 'set':
            if args.threads is None or args.expected_revision is None:
                parser.error('set requires --threads and --expected-revision')
            result = save(root, threads=args.threads, expected_revision=args.expected_revision)
        else:
            result = inspect(root)
        print(json.dumps(result))
    except (ConfigError, OSError) as exc:
        parser.exit(1, f'Execution settings failed: {exc}\n')


if __name__ == '__main__':
    main()
