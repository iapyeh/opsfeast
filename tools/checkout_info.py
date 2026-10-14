"""Product version and explicit checkout-download provenance (no inferred dates)."""
import argparse
from datetime import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = '.opsfeast-download.json'


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('download time must be an ISO timestamp with timezone')
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.tzinfo is None:
        raise ValueError('download time must include a timezone')
    return date.isoformat()


def information(root=ROOT):
    try:
        version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    except OSError:
        version = 'unavailable'
    path = root / RECEIPT
    downloaded = 'Not recorded'
    if path.exists() or path.is_symlink():
        try:
            if path.is_symlink(): raise ValueError('symlink')
            receipt = json.loads(path.read_text(encoding='utf-8'))
            if receipt.get('receipt_version') != '1.0.0': raise ValueError('version')
            downloaded = timestamp(receipt['downloaded_at'])
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            downloaded = 'Invalid download record'
    return {'version': version, 'downloaded_at': downloaded}


def record_download(root, downloaded_at, source):
    """Called by an acquisition workflow with evidence of its actual download."""
    value = timestamp(downloaded_at)
    if not isinstance(source, str) or not source.strip():
        raise ValueError('download source is required')
    path = root / RECEIPT
    if path.exists() or path.is_symlink():
        raise ValueError('download record already exists; preserve it')
    # Exclusive creation refuses accidental replacement or a racing writer.
    with path.open('x', encoding='utf-8') as stream:
        json.dump({'receipt_version': '1.0.0', 'downloaded_at': value, 'source': source}, stream, indent=2)
        stream.write('\n')
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloaded-at', required=True, help='actual known download time, ISO 8601 with timezone')
    parser.add_argument('--source', required=True, help='actual download source; avoid credentials in URLs')
    args = parser.parse_args(argv)
    try:
        record_download(ROOT, args.downloaded_at, args.source)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'ERROR: download record could not be saved ({type(exc).__name__})\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
