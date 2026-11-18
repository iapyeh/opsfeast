"""Profile-local business-key guard 0.1.0; uncertain dispatch never auto-retries."""
from uuid import uuid4
from .browser_steps import directory, digest, read, write, utc
from .identity import _locked
from . import ConfigError


class OperationGuard:
    def __init__(self, root, *, key, run_id):
        self.path = directory(root, '.operation-guards') / (digest(key) + '.json')
        self.lock = self.path.with_suffix('.lock')
        self.nonce = str(uuid4())
        with _locked(self.lock):
            if self.path.exists() and read(self.path)['state'] != 'failed_before_dispatch':
                raise ConfigError('operation_already_reserved: reconcile original attempt; no automatic repeat')
            previous = read(self.path) if self.path.exists() else None
            if previous:
                write(self.path.with_name(self.path.stem + '-' + previous['nonce'] + '.json'), previous)
            write(self.path, dict(schema_version='0.1.0', key=key, run_id=run_id, nonce=self.nonce,
                                  state='prepared', updated_at=utc().isoformat(), steps=[]))

    def update(self, state, **evidence):
        with _locked(self.lock):
            item = read(self.path)
            if item['nonce'] != self.nonce:
                raise ConfigError('operation guard ownership changed')
            item.update(state=state, updated_at=utc().isoformat())
            item['steps'].append(dict(at=item['updated_at'], state=state, **evidence))
            write(self.path, item)
