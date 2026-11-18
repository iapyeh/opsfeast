"""Python-workflow 0.1.0 context: one selected host, explicit delayed connection."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

from . import ConfigError


class WorkflowContext:
    def __init__(self, *, root, host_id, reference, variables, run_id, code_directory,
                 connector, progress, river=None, identity=None, execution=None):
        self.root = Path(root)
        self.host_id = host_id
        self.reference = reference
        self.vars = deepcopy(variables)
        self.run_id = run_id
        self.code_directory = Path(code_directory)
        self._identity = identity
        self.river = river
        self.execution = deepcopy(execution)
        self._connector = connector
        self._progress = progress
        self._active = True
        self._connecting = False

    def progress(self, message):
        if not self._active:
            raise ConfigError('workflow scope is closed')
        if self.river is not None:
            self.river.progress(message)
        self._progress(message)

    @contextmanager
    def connect(self):
        """Use only the runner-selected host/login; never infer another target/actor."""
        if not self._active or self._connecting:
            raise ConfigError('workflow connection scope unavailable')
        self._connecting = True
        try:
            self.progress('connecting selected workflow host')
            with self._connector() as session:
                if self.river is not None and self._identity is not None:
                    import json
                    identity = self._identity()
                    self.river.text('identity', 'Connection identity', json.dumps({
                        'host': self.host_id, 'connection_user': identity.get('username'),
                        'effective_user': '未另行核對', 'identity_verified': False,
                        'source': identity.get('source')}, ensure_ascii=False))
                yield session
        finally:
            self._connecting = False

    def close_scope(self):
        self._active = False
