"""Durable sequential Recipe execution stages over the shared Console river."""
from functools import cached_property
import json
from pathlib import Path
import re
from uuid import UUID, uuid4

from . import ConfigError
from .console_records import Records
from .core import Instance
from .identity import _locked
from .storage import resolve_data_root
from .web_settings import read_port

VERSION = '0.1.0'


def stages(metadata):
    value = metadata.get('execution')
    if value is None and 'execution' not in metadata:
        return []
    if not isinstance(value, dict) or set(value) != {'version', 'stages'} or value['version'] != VERSION:
        raise ConfigError('invalid Recipe execution contract')
    items = value['stages']
    if not isinstance(items, list) or not 1 <= len(items) <= 32:
        raise ConfigError('Recipe execution requires 1–32 stages')
    names = set()
    for item in items:
        if (not isinstance(item, dict) or set(item) != {'id', 'executor'}
                or not isinstance(item['id'], str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', item['id'])
                or item['id'] in names or item['executor'] not in ('agent', 'python')):
            raise ConfigError('invalid or duplicate Recipe execution stage')
        names.add(item['id'])
    mode = (metadata.get('launch') or {}).get('mode', 'direct')
    if (mode == 'agent') != (items[0]['executor'] == 'agent'):
        raise ConfigError('Recipe launch mode must match its first execution stage')
    runner = metadata.get('runner') or {}
    if metadata.get('kind') == 'report' or runner.get('contract') == 'python-report':
        raise ConfigError('staged report entrypoints are not supported')
    return items


def identifier(value):
    try:
        if str(UUID(value)) == value:
            return value
    except (TypeError, ValueError, AttributeError):
        pass
    raise ConfigError('invalid Recipe execution ID')


class Executions:
    def __init__(self, root, installation=None):
        self.profile = Instance.open(installation).profile(root=root)
        self.directory = self.profile.root / '.recipe-executions'
        self.data_root = resolve_data_root(self.profile.instance.root)
        self.records_root = (self.data_root if self.profile.name else self.directory) / 'console-records'
        self.profile_name = self.profile.name or 'local'

    @cached_property
    def records(self):
        return Records(self.records_root)

    def path(self, execution_id):
        if self.directory.is_symlink():
            raise ConfigError('invalid Recipe execution storage')
        return self.directory / (identifier(execution_id) + '.json')

    def read(self, execution_id):
        path = self.path(execution_id)
        if not path.is_file() or path.is_symlink():
            raise ConfigError('Recipe execution not found')
        return json.loads(path.read_text(encoding='utf-8'))

    def _save(self, state):
        from retention_store import atomic
        atomic(self.path(state['id']), json.dumps(state, ensure_ascii=False, allow_nan=False) + '\n')

    def begin(self, *, reference, title, version, fingerprint, stages, hosts, trigger):
        if not stages or not hosts or len(set(hosts)) != len(hosts):
            raise ConfigError('Recipe execution requires stages and unique hosts')
        self.directory.mkdir(mode=0o700, exist_ok=True)
        execution_id = str(uuid4())
        path = self.path(execution_id)
        from host_runtime import now
        self.records.create({
            'session_id': execution_id, 'title': title or reference,
            'host_id': f'{self.profile_name} / {hosts[0]}', 'work_id': None,
            'targets': [{'profile': self.profile_name, 'host_id': host, 'icon': '🖥'} for host in hosts],
        }, recipe_execution=True)
        state = {'schema_version': VERSION, 'id': execution_id, 'profile': self.profile.name,
                 'reference': reference, 'title': title or reference, 'version': version,
                 'fingerprint': fingerprint, 'hosts': list(hosts), 'trigger': trigger,
                 'started_at': now(), 'completed_at': None, 'status': 'waiting',
                 'observation_run_id': None, 'cursor': 0,
                 'stages': [{**stage, 'status': 'waiting'} for stage in stages],
                 'river': self.river_links(execution_id)}
        with _locked(path):
            self._save(state)
        return state

    def river_links(self, execution_id):
        port = None if self.data_root == self.profile.instance.root else read_port(self.profile.instance.root, data_root=self.data_root)
        origin = f'http://127.0.0.1:{port}' if port and self.profile.name else ''
        url = f'{origin}/console/{execution_id}'
        return {'session_id': execution_id, 'reader_url': url, 'history_url': url + '/history'}

    def find(self, execution_id):
        try:
            identifier(execution_id)
        except ConfigError:
            return []
        return [self.read(execution_id)] if self.path(execution_id).is_file() else []

    def list(self):
        if self.directory.is_symlink():
            raise ConfigError('invalid Recipe execution storage')
        return [self.read(p.stem) for p in self.directory.glob('*.json') if p.is_file()]

    @staticmethod
    def _stage(state, stage_id, executor, status):
        index = state['cursor']
        if index >= len(state['stages']):
            raise ConfigError('Recipe execution is already terminal')
        stage = state['stages'][index]
        if (stage['id'], stage['executor'], stage['status']) != (stage_id, executor, status):
            raise ConfigError('Recipe execution stage is unavailable or already claimed')
        return stage

    def claim(self, execution_id, stage_id, executor, *, binding=None, observation_run_id=None):
        from host_runtime import now
        with _locked(self.path(execution_id)):
            state = self.read(execution_id)
            stage = self._stage(state, stage_id, executor, 'waiting')
            if binding is not None and any(state.get(k) != v for k, v in binding.items()):
                raise ConfigError('Recipe execution binding changed')
            stage.update(status='running', started_at=now())
            state['status'] = 'running'
            if observation_run_id is not None:
                state['observation_run_id'] = observation_run_id
            self._save(state)
            self._write(execution_id, stage_id, 'Stage started')
            return state

    def _write(self, execution_id, stage_id, text, host=None, *, status='completed'):
        block_id = str(uuid4())
        self.records.add_block(execution_id, {
            'event_id': str(uuid4()), 'block_id': block_id, 'kind': 'status',
            'title': stage_id, 'text': text, 'form': None,
            'target_id': f'{self.profile_name} / {host}' if host is not None else None,
        })
        self.records.finish(execution_id, block_id, {
            'event_id': str(uuid4()), 'status': status,
        })

    def progress(self, execution_id, stage_id, executor, text, *, host=None, awaiting_human=False):
        if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 8192:
            raise ConfigError('invalid Recipe execution progress text')
        with _locked(self.path(execution_id)):
            state = self.read(execution_id)
            stage = self._stage(state, stage_id, executor, 'running')
            if host is not None and host not in state['hosts']:
                raise ConfigError('host outside Recipe execution scope')
            self._write(execution_id, stage_id, text, host)
            if awaiting_human and executor == 'agent':
                stage['awaiting_human'] = True
                self._save(state)

    def finish(self, execution_id, stage_id, executor, status, output):
        from host_runtime import now
        if status not in ('success', 'partial', 'failed', 'cancelled', 'unknown') or not isinstance(output, dict):
            raise ConfigError('invalid Recipe stage outcome')
        text = json.dumps({'status': status, 'output': output}, ensure_ascii=False, allow_nan=False)
        if len(text.encode('utf-8')) > 8192:
            raise ConfigError('Recipe stage output exceeds 8 KiB')
        with _locked(self.path(execution_id)):
            state = self.read(execution_id)
            stage = self._stage(state, stage_id, executor, 'running')
            stamp = now()
            stage.pop('awaiting_human', None)
            stage.update(status=status, output=output, completed_at=stamp)
            state['cursor'] += 1
            if status == 'success' and state['cursor'] < len(state['stages']):
                state['status'] = 'waiting'
            else:
                for pending in state['stages'][state['cursor']:]:
                    pending['status'] = 'skipped'
                state.update(status=status, completed_at=stamp, cursor=len(state['stages']))
            block_status = {'success': 'completed', 'cancelled': 'cancelled', 'unknown': 'interrupted'}
            self._write(execution_id, stage_id, text, status=block_status.get(status, 'failed'))
            self._save(state)
            return state


def binding(reference, metadata, fingerprint, hosts):
    return {'reference': reference, 'version': metadata['version'],
            'fingerprint': fingerprint, 'hosts': list(hosts)}


class PythonStage:
    """One coordinator and explicit host attribution for threaded workers."""

    def __init__(self, store, execution_id, identity):
        self.store, self.id = store, execution_id
        state = store.read(execution_id)
        if state['cursor'] >= len(state['stages']):
            raise ConfigError('Recipe execution is already terminal')
        self.stage_id = state['stages'][state['cursor']]['id']
        self.state = store.claim(execution_id, self.stage_id, 'python', binding=identity)

    @classmethod
    def start(cls, root, item, hosts, *, trigger, execution_id=None):
        from .recipe_install import fingerprint
        metadata = item['descriptor']
        identity = binding(item['reference'], metadata, fingerprint(Path(item['directory'])), hosts)
        store = Executions(root)
        if execution_id is None:
            execution_id = store.begin(
                **identity, stages=stages(metadata), title=item.get('title'), trigger=trigger,
            )['id']
        return cls(store, execution_id, identity)

    def link_observation(self, run_id):
        if run_id is not None:
            with _locked(self.store.path(self.id)):
                state = self.store.read(self.id)
                stage = self.store._stage(state, self.stage_id, 'python', 'running')
                stage['observation_run_id'] = run_id
                state['observation_run_id'] = run_id
                self.store._save(state)

    def progress(self, host, message):
        self.store.progress(self.id, self.stage_id, 'python', message, host=host)

    def result(self, host, report, path=None):
        self.progress(host, json.dumps({
            'status': report['status'], 'reason_code': report.get('reason_code'),
            'result_id': Path(path).relative_to(self.store.profile.root).as_posix() if path else None,
        }))

    def finish(self, reports, exit_code):
        statuses = [report['status'] for report in reports]
        if any(report.get('reason_code') == 'outcome_unknown' for report in reports):
            outcome = 'unknown'
        elif not exit_code:
            outcome = 'success'
        elif 'partial' in statuses or ('success' in statuses and 'failed' in statuses):
            outcome = 'partial'
        else:
            outcome = 'failed'
        return self.store.finish(self.id, self.stage_id, 'python', outcome, {'exit_code': exit_code})

    def __enter__(self):
        return self

    def __exit__(self, kind, value, trace):
        if kind is not None:
            try:
                state = self.store.read(self.id)
                if state['status'] == 'running' and state['cursor'] == self.state['cursor']:
                    self.store.finish(self.id, self.stage_id, 'python', 'unknown',
                                      {'error_type': kind.__name__})
            except Exception as error:
                value.add_note(f'Recipe execution recording failed ({type(error).__name__})')
