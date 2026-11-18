"""Rendered-table browser handoff 0.1.0; no browser launch or network fallback."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from . import ConfigError
from .identity import _locked
from .site import _atomic

VERSION = '0.1.0'
MAX_BYTES = 2 * 1024 * 1024


class BrowserStepError(ConfigError):
    pass


def utc():
    return datetime.now(timezone.utc)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def directory(root, name):
    path = Path(root) / name
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise BrowserStepError('unsafe workflow storage directory')
    path.mkdir(mode=0o700, exist_ok=True)
    return path


def read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise BrowserStepError('invalid workflow artifact')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise BrowserStepError('invalid workflow artifact envelope')
    return value


def write(path, value):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise BrowserStepError('unsafe workflow artifact')
    if len(json.dumps(value, ensure_ascii=False).encode()) > MAX_BYTES:
        raise BrowserStepError('workflow artifact too large')
    _atomic(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def request_path(root, request_id, *, create=False):
    try:
        if str(UUID(request_id)) != request_id:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise BrowserStepError('invalid browser request id') from None
    base = Path(root) / '.browser-steps'
    path = base / request_id
    if create:
        return directory(directory(root, '.browser-steps'), request_id)
    if base.is_symlink() or not base.is_dir() or path.is_symlink() or not path.is_dir():
        raise BrowserStepError('browser request does not exist or has unsafe storage')
    return path


def timestamp(value):
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (TypeError, ValueError):
        raise BrowserStepError('invalid browser timestamp') from None


def create(root, *, run_id, reference, host_id, url, target_month, wait_seconds):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.netloc or parts.username or parts.password or parts.fragment:
        raise BrowserStepError('browser URL must be exact HTTPS without credentials or fragment')
    if type(wait_seconds) is not int or not 1 <= wait_seconds <= 180:
        raise BrowserStepError('browser wait must be 1..180 seconds')
    started = utc()
    item = dict(schema_version=VERSION, request_id=str(uuid4()), run_id=run_id,
                reference=reference, host_id=host_id, url=url, target_month=target_month,
                created_at=started.isoformat(), expires_at=(started + timedelta(seconds=wait_seconds)).isoformat())
    path = request_path(root, item['request_id'], create=True)
    write(path / 'request.json', item)
    return item


def validate_response(request, response):
    required = {'schema_version', 'request_id', 'request_sha256', 'provider_id', 'captured_at',
                'url', 'table_html', 'range_text', 'complete', 'pagination_complete'}
    if set(response) != required or response['schema_version'] != VERSION:
        raise BrowserStepError('browser_response_schema_changed')
    if response['request_id'] != request['request_id'] or response['request_sha256'] != digest(request) or response['url'] != request['url']:
        raise BrowserStepError('browser_response_wrong_request')
    captured = timestamp(response['captured_at'])
    if not timestamp(request['created_at']) <= captured <= min(utc(), timestamp(request['expires_at'])):
        raise BrowserStepError('browser_response_stale')
    if response['complete'] is not True or response['pagination_complete'] is not True:
        raise BrowserStepError('coverage_incomplete')
    for field, limit in [('provider_id', 200), ('table_html', 1500000), ('range_text', 1000)]:
        if not isinstance(response[field], str) or not 0 < len(response[field]) <= limit or '\x00' in response[field]:
            raise BrowserStepError('invalid browser response text')
    return response


def respond(root, request_id, response):
    path = request_path(root, request_id)
    with _locked(path / 'write.lock'):
        request = read(path / 'request.json')
        if utc() > timestamp(request['expires_at']) or (path / 'terminal.json').exists():
            raise BrowserStepError('browser request is closed')
        if (path / 'response.json').exists():
            raise BrowserStepError('browser response already supplied')
        validate_response(request, response)
        write(path / 'response.json', response)
    return {'request_id': request_id, 'status': 'responded'}


def acquire(context, *, url, target_month, wait_seconds=180):
    request = create(context.root, run_id=context.run_id, reference=context.reference,
                     host_id=context.host_id, url=url, target_month=target_month, wait_seconds=wait_seconds)
    path = request_path(context.root, request['request_id'])
    completed = False
    deadline = time.monotonic() + wait_seconds
    try:
        context.progress('01 browser request ' + request['request_id'] + '; active agent must supply rendered table via opsfeast.browser_steps')
        while time.monotonic() <= deadline and utc() <= timestamp(request['expires_at']):
            if (path / 'response.json').exists():
                result = validate_response(request, read(path / 'response.json'))
                completed = True
                return dict(result, snapshot_sha256=digest(result))
            time.sleep(0.2)
        raise BrowserStepError('browser_provider_timeout')
    finally:
        with _locked(path / 'write.lock'):
            write(path / 'terminal.json', {'status': 'consumed' if completed else 'closed', 'at': utc().isoformat()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product', type=Path, default=Path.cwd())
    parser.add_argument('--profile', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list')
    show = commands.add_parser('show'); show.add_argument('request_id')
    reply = commands.add_parser('respond'); reply.add_argument('request_id'); reply.add_argument('--file', type=Path, required=True)
    args = parser.parse_args()
    try:
        from .core import Instance
        root = Instance.open(args.product).profile(args.profile).root
        if args.command == 'list':
            base = Path(root) / '.browser-steps'
            if base.is_symlink():
                raise BrowserStepError('unsafe browser request directory')
            result = []
            for path in sorted(base.glob('*/request.json')):
                if path.parent.is_symlink():
                    raise BrowserStepError('unsafe browser request directory')
                item = read(path)
                state = ('closed' if (path.parent / 'terminal.json').exists() else
                         'expired' if utc() > timestamp(item['expires_at']) else
                         'responded' if (path.parent / 'response.json').exists() else 'waiting')
                result.append(dict(item, request_sha256=digest(item), status=state))
        elif args.command == 'show':
            item = read(request_path(root, args.request_id) / 'request.json')
            result = dict(item, request_sha256=digest(item))
        else:
            result = respond(root, args.request_id, read(args.file))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ConfigError, ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
