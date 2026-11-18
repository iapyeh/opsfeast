"""Profile-local business-key guard 0.1.0; uncertain dispatch never auto-retries."""
from pathlib import Path
from uuid import uuid4
from .browser_steps import directory, digest, read, write, utc
from .identity import _locked
from . import ConfigError


def completion(item):
    if item['state'] == 'command_completed':
        return {'run_id': item['run_id'], 'completed_at': item['updated_at']}
    if item['state'] == 'failed_before_dispatch':
        return item.get('repeat_of')
    return None


def inspect(root, key):
    """Read the exact business key without creating a guard or reserving work."""
    folder = Path(root) / '.operation-guards'
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise ConfigError('unsafe workflow storage directory')
    path = folder / (digest(key) + '.json')
    if not path.exists() and not path.is_symlink():
        return {'key': key, 'state': 'available'}
    item = read(path)
    previous = completion(item)
    if previous is not None:
        return {'key': key, 'state': 'repeat_confirmation_required',
                'receipt': digest(item), 'previous_completed': previous}
    return {'key': key, 'state': 'available' if item['state'] == 'failed_before_dispatch' else 'blocked',
            'guard_state': item['state']}


class OperationGuard:
    def __init__(self, root, *, key, run_id, repeat_receipt=None):
        self.path = directory(root, '.operation-guards') / (digest(key) + '.json')
        self.lock = self.path.with_suffix('.lock')
        self.nonce = str(uuid4())
        with _locked(self.lock):
            previous = read(self.path) if self.path.exists() or self.path.is_symlink() else None
            repeat_of = completion(previous) if previous is not None else None
            if repeat_of is not None:
                if repeat_receipt is None:
                    raise ConfigError('operation_repeat_confirmation_required')
                if repeat_receipt != digest(previous):
                    raise ConfigError('operation_repeat_receipt_changed')
            elif previous is not None and previous['state'] != 'failed_before_dispatch':
                raise ConfigError('operation_already_reserved: reconcile original attempt; no automatic repeat')
            elif repeat_receipt is not None:
                raise ConfigError('operation_repeat_receipt_changed')
            if previous:
                write(self.path.with_name(self.path.stem + '-' + previous['nonce'] + '.json'), previous)
            item = dict(schema_version='0.1.0', key=key, run_id=run_id, nonce=self.nonce,
                        state='prepared', updated_at=utc().isoformat(), steps=[])
            if repeat_of is not None:
                item.update(repeat_of=repeat_of, repeat_receipt=repeat_receipt)
            write(self.path, item)
            self.repeat_of = repeat_of

    def update(self, state, **evidence):
        with _locked(self.lock):
            item = read(self.path)
            if item['nonce'] != self.nonce:
                raise ConfigError('operation guard ownership changed')
            item.update(state=state, updated_at=utc().isoformat())
            item['steps'].append(dict(at=item['updated_at'], state=state, **evidence))
            write(self.path, item)


def main():
    import argparse
    import json
    from datetime import date
    from . import resolve_root

    parser = argparse.ArgumentParser(description='Inspect a Profile-local operation serialisation guard.')
    parser.add_argument('--profile', required=True)
    parser.add_argument('--purpose', required=True)
    parser.add_argument('--host', required=True)
    parser.add_argument('--month', required=True)
    args = parser.parse_args()
    try:
        month = date.fromisoformat(args.month + '-01').isoformat()[:7]
        if month != args.month:
            raise ValueError('month must be YYYY-MM')
        info = inspect(resolve_root(None, args.profile), {'purpose': args.purpose, 'host': args.host, 'month': month})
    except (ConfigError, ValueError, OSError) as error:
        parser.exit(1, f'Guard lookup failed ({type(error).__name__})\n')
    print(json.dumps(info, ensure_ascii=False))


if __name__ == '__main__':
    main()
