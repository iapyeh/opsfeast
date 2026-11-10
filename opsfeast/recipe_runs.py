"""Reviewable recipe execution service 0.1.0 over the existing CLI runner.

Private variables stay in memory/stdin, never in argv or execution records.
Owned local worker termination is distinct from remote command cleanup.
"""
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import selectors
import signal
import subprocess
import sys
import threading
import time
from uuid import UUID, uuid4

from . import ConfigError
from .core import Instance

VERSION = '0.1.0'
MAX_STDOUT = 4 * 1024 * 1024
MAX_PROGRESS = 65536
WORKER_DEADLINE = 600


class RecipeRunError(ConfigError):
    """Public fixed reason code; never carries configuration/credential text."""


def now():
    return datetime.now(timezone.utc).isoformat()


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, allow_nan=False).encode()).hexdigest()


def inventory_selection(metadata, directory, selection=None):
    """Resolve explicit job/property scope without importing the collector."""
    if metadata.get('runner',{}).get('contract') in ('python-routines','recipe-meal'):
        from .routine_execution import collection
        data=collection(metadata)
    else:data=None
    if not metadata.get('collection') and data is None:
        if selection is not None:
            raise RecipeRunError('inventory_selection_requires_inventory_recipe')
        return None
    from inventory_jobs import inspect_collection, select
    data = data or inspect_collection(directory, metadata)
    if selection is not None:
        if (not isinstance(selection, dict) or len(selection) != 1
                or set(selection) - {'jobs', 'properties'}):
            raise RecipeRunError('select_inventory_jobs_or_properties')
        names = next(iter(selection.values()))
        allowed = data[next(iter(selection))]
        if (not isinstance(names, list) or not names or len(names) > len(allowed)
                or any(not isinstance(n, str) or n not in allowed for n in names)
                or len(set(names)) != len(names)):
            raise RecipeRunError('invalid_inventory_selection')
    jobs, properties = select(data, **(selection or {}))
    return {'mode': next(iter(selection)) if selection else 'default', 'jobs': jobs,
            'properties': properties or [name for name, spec in data['properties'].items() if spec['job'] in jobs],
            'catalog_sha256': _digest(data)}


def prepare_pair(root, reference, host, variables, inputs, selection=None):
    """Static validation shared by preview and the worker immediately before run."""
    from recipe_catalog import choose, configuration
    from recipe_dispatch import bundle_digest
    from recipe_inputs import prepare_vars
    item = choose(root, reference)
    if item['reference'] != reference or not item['runnable']:
        raise RecipeRunError('exact_runnable_reference_required')
    if item['kind'] == 'operation':
        if inputs or host is None:
            raise RecipeRunError('operation_requires_host_without_report_inputs')
        from recipe_runner import preflight
        config, directory, digest, _ = preflight(root, host, reference, cli_vars=variables)
        policy = config.execution_recipe['execution']
        values = config.execution_recipe['effective_vars']
        connection = config.hosts[host]['connection']
        from management_view import user_accounts
        login, _ = user_accounts(config.hosts[host])
        identity = {'login_user': login, 'requested': policy,
                    'inventory_root_selection': item['id'] == 'inventory-system',
                    'verified': False, 'local': connection.get('local', False)}
    else:
        if host is not None:
            raise RecipeRunError('report_has_no_host')
        config = configuration(root)
        info = config.recipe_location(reference, root / 'hosts.yaml', cli=True)
        values = prepare_vars(item['descriptor'], info['vars'], {}, variables)
        directory = Path(item['directory'])
        digest = bundle_digest(directory)
        identity = {'login_user': None, 'requested': None, 'inventory_root_selection': False,
                    'verified': False, 'local': True}
    selected_inventory = inventory_selection(item['descriptor'], directory, selection)
    files = {str(p): p.read_bytes().hex() for p in config.documents}
    for name in ('feast.yaml', 'inventory.yaml'):
        path = root / name
        if path.exists(): files[str(path)] = path.read_bytes().hex()
    # Reports accept only exact saved result IDs, not arbitrary server paths.
    safe_inputs = []
    from recipe_reports import result_path
    for value in inputs:
        if not isinstance(value, str) or Path(value).is_absolute():
            raise RecipeRunError('saved_report_result_id_required')
        path = result_path(root, value)
        safe_inputs.append(str(path))
        files[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    composition=None
    if item['descriptor'].get('runner',{}).get('contract') in ('python-routines','recipe-meal'):
        from .routine_execution import describe
        composition=describe(root,host,[{'reference':reference,'vars':variables,'inventory_selection':selection}])
    fingerprint = _digest({'composition':composition,'root': str(root), 'files': files, 'recipe': digest, 'descriptor': item['descriptor'],
                           'vars': values, 'identity': identity, 'inventory_selection': selected_inventory})
    public = {'reference': reference, 'version': item['version'], 'host_id': host,
              'kind': item['kind'], 'identity': identity,
              'access_mode': item['descriptor'].get('access_mode', 'not_declared'),
              'side_effects': item['descriptor'].get('side_effects', []),
              'variable_names': sorted(values), 'input_ids': inputs, 'inventory_selection': selected_inventory,
              'fingerprint': fingerprint,'composition':composition,
              'invocation': ['opsfeast.py', 'recipes', 'run', reference,
                             *(['--host', host] if host is not None else []), '--json', '--verbose']}
    if selection is not None:
        public['invocation'] = ['opsfeast.py', 'inventory', 'run', '--recipe', reference, '--host', host]
        for key, names in selection.items():
            for name in names:
                public['invocation'].extend(['--job' if key == 'jobs' else '--property', name])
        public['invocation'].append('--json')
    return public, safe_inputs


class RecipeRuns:
    """One serial selection at a time per Web process; previews expire in 10 min.

    Records survive process restarts. Recovery never signals a saved PID or retries
    an interrupted recipe. There is no scheduler or remote termination guarantee.
    """
    def __init__(self, product, data_root):
        self.product = Path(product).resolve()
        self.directory = Path(data_root) / 'recipe-runs'
        self.lock = threading.RLock()
        self.plans = {}
        self.active = None
        self.process = None
        self.stopping = threading.Event()
        self.thread = None

    def _profile_binding(self, name):
        profile = Instance.open(self.product).profile(name)
        from retention_store import settings
        data = settings(profile.root)
        return _digest({'root': str(profile.root), 'namespace': data['namespace'] if data else None})

    def preview(self, body):
        if not isinstance(body, dict) or set(body) != {'profile', 'hosts', 'recipes', 'timeout'}:
            raise RecipeRunError('invalid_recipe_selection')
        if not isinstance(body['profile'], str) or not body['profile']:
            raise RecipeRunError('explicit_profile_required')
        hosts, recipes, timeout = body['hosts'], body['recipes'], body['timeout']
        if (not isinstance(hosts, list) or len(hosts) > 16 or any(not isinstance(h, str) or not h for h in hosts)
                or len(set(hosts)) != len(hosts) or not isinstance(recipes, list) or not 1 <= len(recipes) <= 32
                or type(timeout) not in (int, float) or not 1 <= timeout <= 120):
            raise RecipeRunError('invalid_recipe_selection')
        profile = Instance.open(self.product).profile(body['profile'])
        known = profile.hosts.list()
        if set(hosts) - set(known):
            raise RecipeRunError('unknown_host_id')
        pairs, private, seen = [], [], set()
        for choice in recipes:
            if (not isinstance(choice, dict) or not {'reference', 'vars', 'inputs'} <= set(choice)
                    or set(choice) - {'reference', 'vars', 'inputs', 'inventory_selection'}
                    or not isinstance(choice['reference'], str) or not isinstance(choice['vars'], dict)
                    or not isinstance(choice['inputs'], list) or len(choice['inputs']) > 20
                    or choice['reference'] in seen):
                raise RecipeRunError('invalid_recipe_choice')
            seen.add(choice['reference'])
            from recipe_catalog import choose
            item = choose(profile.root, choice['reference'])
            targets = [None] if item['kind'] == 'report' else hosts
            if not targets:
                raise RecipeRunError('select_hosts_for_operations')
            if len(pairs) + len(targets) > 64:
                raise RecipeRunError('selection_exceeds_64_invocations')
            for host in targets:
                pair, _ = prepare_pair(profile.root, choice['reference'], host, choice['vars'], choice['inputs'], choice.get('inventory_selection'))
                pair['invocation'].extend(['--profile', profile.name, '--timeout', str(timeout)])
                pairs.append(pair)
                private.append(copy.deepcopy(choice))
        if len(pairs) > 64:
            raise RecipeRunError('selection_exceeds_64_invocations')
        connection_groups=[]
        for host in hosts:
            group=[choice for pair,choice in zip(pairs,private) if pair['host_id']==host and pair.get('composition')]
            if group:
                from .routine_execution import describe
                composition=describe(profile.root,host,group)
                connection_groups.append({'host_id':host,'references':[c['reference'] for c in group],'composition':composition})
        public = {'schema_version': VERSION, 'profile': profile.name, 'pairs': pairs,
                  'profile_binding': self._profile_binding(profile.name),
                  'overrides': [{'reference': c['reference'], 'vars': c['vars']} for c in recipes],
                  'timeout': timeout, 'worker_deadline_seconds': WORKER_DEADLINE,'connection_groups':connection_groups,
                  'explicit_host_override': True, 'expires_in': 600,
                  'stop_scope': 'withhold_remaining_and_terminate_owned_local_worker; remote_cleanup_unknown',
                  'visibility': 'runner progress; final structured receipts; not a per-command terminal transcript'}
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.plans = {k: v for k, v in self.plans.items() if v['expires'] > time.monotonic()}
            if len(self.plans) >= 32:
                raise RecipeRunError('too_many_recipe_previews')
            self.plans[token] = {'expires': time.monotonic() + 600, 'public': public,
                                 'root': profile.root, 'private': private, 'started': None}
        return {**copy.deepcopy(public), 'preview_id': token}

    def _path(self, identifier):
        try:
            if str(UUID(identifier)) != identifier:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise RecipeRunError('invalid_recipe_run_id') from None
        if self.directory.is_symlink():
            raise RecipeRunError('recipe_run_directory_must_be_real')
        path = self.directory / (identifier + '.json')
        if path.is_symlink():
            raise RecipeRunError('recipe_run_record_must_be_real')
        return path

    def _save(self, record):
        if self.stopping.is_set() and record['state'] == 'running':
            record['state'] = 'stopping'
        path = self._path(record['id'])
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self.directory / ('.' + str(uuid4()) + '.tmp')
        try:
            with temporary.open('x', encoding='utf-8') as stream:
                os.chmod(temporary, 0o600)
                json.dump(record, stream, ensure_ascii=True, allow_nan=False)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def show(self, identifier, profile):
        with self.lock:
            path = self._path(identifier)
            if not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
                raise RecipeRunError('recipe_run_not_found')
            record = json.loads(path.read_text())
            if record['profile'] != profile or record['profile_binding'] != self._profile_binding(profile):
                raise RecipeRunError('recipe_run_not_found')
            if record['state'] in ('running', 'stopping') and self.active != identifier:
                record.update(state='interrupted', remote_cleanup='unknown', recovery='not_retried')
            return record

    def list(self, profile):
        if self.directory.is_symlink():
            raise RecipeRunError('recipe_run_directory_must_be_real')
        records = []
        # Bounded listing; records are not automatically deleted or rerun.
        paths = sorted(self.directory.glob('*.json'), key=lambda p: p.name)
        for path in paths:
            try:
                row = self.show(path.stem, profile)
                records.append({key: row.get(key) for key in ('id', 'profile', 'created_at', 'completed_at', 'state')})
            except (ConfigError, ValueError, OSError):
                continue
        records.sort(key=lambda r: r['created_at'], reverse=True)
        return {'items': records[:100], 'total': len(records)}

    def start(self, preview_id, confirmed):
        if os.name != 'posix':
            raise RecipeRunError('recipe_workers_require_posix_controller')
        if confirmed is not True:
            raise RecipeRunError('explicit_recipe_confirmation_required')
        with self.lock:
            plan = self.plans.get(preview_id) if isinstance(preview_id, str) else None
            if not plan or plan['expires'] <= time.monotonic():
                raise RecipeRunError('recipe_preview_expired')
            if plan['started']:
                return self.show(plan['started'], plan['public']['profile'])
            if self.active:
                raise RecipeRunError('recipe_selection_already_running')
            if self._profile_binding(plan['public']['profile']) != plan['public']['profile_binding']:
                raise RecipeRunError('recipe_preview_changed_review_again')
            # Check every pair again before creating any worker.
            for pair, choice in zip(plan['public']['pairs'], plan['private']):
                current, _ = prepare_pair(plan['root'], pair['reference'], pair['host_id'], choice['vars'], choice['inputs'], choice.get('inventory_selection'))
                if current['fingerprint'] != pair['fingerprint']:
                    raise RecipeRunError('recipe_preview_changed_review_again')
            record = {'schema_version': VERSION, 'id': str(uuid4()), 'profile': plan['public']['profile'],
                      'profile_binding': plan['public']['profile_binding'],
                      'created_at': now(), 'completed_at': None, 'state': 'running', 'remote_cleanup': 'not_applicable',
                      'confirmation': 'explicit_selection_confirmed',
                      'timeout': plan['public']['timeout'],
                      'tasks': [{**p, 'state': 'queued', 'progress': '', 'progress_truncated': False,
                                 'result': None, 'local_termination': None} for p in plan['public']['pairs']]}
            self._save(record)
            self.active = record['id']
            self.stopping.clear()
            plan['started'] = record['id']
            self.thread = threading.Thread(target=self._work, args=(record, plan), daemon=True)
            self.thread.start()
            return copy.deepcopy(record)

    def stop(self, identifier, profile):
        with self.lock:
            record = self.show(identifier, profile)
            if self.active == identifier:
                self.stopping.set()
                record['state'] = 'stopping'
                self._save(record)
            return record

    def close(self):
        """Shutdown only our workers; never signal recovered PIDs or replay work."""
        self.stopping.set()
        if self.thread:
            self.thread.join(timeout=5)

    def _work(self, record, plan):
        try:
            consumed=set()
            for index,(task,choice) in enumerate(zip(record['tasks'],plan['private'])):
                if index in consumed:continue
                if self.stopping.is_set():
                    task['state'] = 'skipped'; continue
                if self._profile_binding(record['profile']) != record['profile_binding']:
                    raise RecipeRunError('recipe_profile_binding_changed')
                task['state'] = 'running'; task['started_at'] = now()
                with self.lock:
                    self._save(record)
                spec = {'root': str(plan['root']), 'reference': task['reference'], 'host': task['host_id'],
                        'vars': choice['vars'], 'inputs': choice['inputs'], 'fingerprint': task['fingerprint'],
                        'timeout': record['timeout'], 'inventory_selection': choice.get('inventory_selection')}
                group=[i for i,(other,pair) in enumerate(zip(record['tasks'],plan['public']['pairs'])) if i not in consumed and other['host_id']==task['host_id'] and pair.get('composition')] if task.get('composition') else []
                if len(group)>1:
                    spec['batch']=[{'reference':record['tasks'][i]['reference'],'vars':plan['private'][i]['vars'],'inputs':plan['private'][i]['inputs'],'inventory_selection':plan['private'][i].get('inventory_selection'),'fingerprint':record['tasks'][i]['fingerprint']} for i in group]
                    for i in group:record['tasks'][i].update(state='running',started_at=task['started_at'])
                self._invoke(task, spec, record)
                if len(group)>1:
                    children=(task.get('result') or {}).get('children',[])
                    for i in group:
                        consumed.add(i)
                        other=record['tasks'][i]
                        other['progress']=task['progress'];other['progress_truncated']=task['progress_truncated']
                        child=next((c for c in children if c.get('recipe',{}).get('reference')==other['reference']),None)
                        if child:
                            other['result']={**child,'content_update':task['result'].get('content_update'),'meal_run_id':task['result'].get('meal_run_id')}
                            other['state']='success' if child['status']=='success' and task['result'].get('content_update',{}).get('status')!='failed' and child.get('retention',{}).get('status') in ('stored','already_stored') else child['status'] if child['status'] in ('partial','unsupported','skipped') else 'failed'
                        else:other.update(state=task['state'],local_termination=task.get('local_termination','unknown'),reason_code=task.get('reason_code','shared_worker_did_not_complete'))
                        other['completed_at']=now()
                task['completed_at'] = now()
                with self.lock:
                    self._save(record)
            record['state'] = 'stopped' if self.stopping.is_set() else ('completed' if all(t['state'] == 'success' for t in record['tasks']) else 'completed_with_gaps')
        except Exception as exc:
            record.update(state='failed', error_type=type(exc).__name__)
            for task in record['tasks']:
                if task['state'] == 'running':
                    task.update(state='failed', local_termination='unknown')
                elif task['state'] == 'queued':
                    task['state'] = 'skipped'
        finally:
            record['completed_at'] = now()
            if any(t['local_termination'] for t in record['tasks']):
                record['remote_cleanup'] = 'unknown'
            with self.lock:
                try:
                    self._save(record)
                finally:
                    self.active = None
                    self.process = None
                    plan['private'] = []

    def _invoke(self, task, spec, record):
        argv = [sys.executable, '-B', '-u', '-m', 'opsfeast.recipe_run_worker']
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
        env.pop('OPSFEAST_TUI_EVENTS', None)
        process = subprocess.Popen(argv, cwd=Path(__file__).resolve().parents[1], env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        self.process = process
        output = bytearray(); overflow = False; forced = False; deadline = time.monotonic() + WORKER_DEADLINE
        try:
            process.stdin.write(json.dumps(spec).encode()); process.stdin.close()
            with selectors.DefaultSelector() as poll:
                poll.register(process.stdout, selectors.EVENT_READ, 'out')
                poll.register(process.stderr, selectors.EVENT_READ, 'err')
                while poll.get_map():
                    if self.stopping.is_set() or time.monotonic() >= deadline:
                        forced = True
                        break
                    changed = False
                    for key, _ in poll.select(.15):
                        block = os.read(key.fileobj.fileno(), 8192)
                        if not block:
                            poll.unregister(key.fileobj); continue
                        if key.data == 'out':
                            space = MAX_STDOUT - len(output)
                            output.extend(block[:space]); overflow |= len(block) > space
                        else:
                            text = block.decode('utf-8', errors='replace')
                            combined = task['progress'] + text
                            task['progress_truncated'] |= len(combined) > MAX_PROGRESS
                            task['progress'] = combined[-MAX_PROGRESS:]; changed = True
                    if changed:
                        with self.lock:
                            if self.stopping.is_set(): record['state'] = 'stopping'
                            self._save(record)
                if not forced:
                    while process.poll() is None:
                        if self.stopping.wait(.1) or time.monotonic() >= deadline:
                            forced = True; break
        finally:
            if process.poll() is None or forced:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    process.wait(timeout=2)
            for stream in (process.stdout, process.stderr): stream.close()
            self.process = None
        task['exitcode'] = process.returncode
        if forced:
            task.update(state='stopped' if self.stopping.is_set() else 'failed', local_termination='confirmed',
                        reason_code='stop_requested' if self.stopping.is_set() else 'worker_deadline')
            return
        task['state'] = 'success' if process.returncode == 0 else 'failed'
        try:
            if overflow: raise ValueError()
            result = json.loads(output)
            # Results already live in raw/retention. Keep receipts and identity here,
            # not a second copy of potentially large recipe-owned data.
            keys = ('status', 'reason_code', 'result_path', 'result_id', 'observation_run_id', 'retention',
                    'content_update', 'execution_identity', 'identity_evidence', 'collection_gaps', 'artifacts', 'children', 'meal_run_id', 'connection_evidence')
            task['result'] = {key: result[key] for key in keys if key in result}
            if len(json.dumps(task['result'])) > 65536:
                task['result'] = {key: result[key] for key in ('status', 'reason_code', 'result_path', 'result_id', 'observation_run_id') if key in result}
                task['result']['receipt_preview_truncated'] = True
            if result.get('status') in ('partial', 'unsupported', 'skipped'):
                task['state'] = result['status']
        except (ValueError, TypeError):
            task.update(state='failed', reason_code='worker_output_limit' if overflow else 'invalid_worker_output')
