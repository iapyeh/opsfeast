"""TEST ADAPTER ONLY: fixed-thread Console borrowing at OpsFeast connection owner.

Not an installed Core API, production UI or authentication sandbox. Synthetic
configuration is loaded with Validator; all credential selection reuses OpsFeast.
"""
from concurrent.futures import Future
from contextlib import ExitStack
from dataclasses import asdict
import json
from pathlib import Path
import queue
import shlex
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from opsfeast import Validator
from host_runtime import connected, privilege_password
from sshscript import Console, CredentialsRequiredError, Session, SwitchCredentials
from fixtures import SimulatedSession


class Bridge:
    def __init__(self, journal=None):
        self.commands = queue.Queue()
        self.lock = threading.Lock()
        self.events = []
        self.current = {'state': 'closed', 'session_reuse': 'unknown', 'environments': []}
        self.journal = Path(journal) if journal else None
        self.halt = False
        self.thread = threading.Thread(target=self._run, name='fixed-console-owner', daemon=True)
        self.thread.start()

    def request(self, operation, value='', **options):
        future = Future()
        self.commands.put((operation, value, options, future))
        return future

    def call(self, operation, value='', **options):
        return self.request(operation, value, **options).result(timeout=20)

    def snapshot(self):
        with self.lock:
            return {'current': dict(self.current), 'events': list(self.events)}

    def _record(self, update=None, *, operation, error=None, extra=None):
        event = {'sequence': len(self.events)+1, 'operation': operation,
                 'worker_thread': threading.get_ident(), 'evidence': self.mode,
                 'state': update.state if update else ('failed' if error else self.current['state']),
                 'stdout': update.stdout if update else '', 'stderr': update.stderr if update else '',
                 'error_type': update.error_type if update else (type(error).__name__ if error else None),
                 'session_reuse': self.console.session_reuse if self.console else getattr(error, 'session_reuse', 'unknown'),
                 'exitcode': getattr(getattr(update, 'result', None), 'exitcode', None),
                 'stop_reason': getattr(getattr(update, 'result', None), 'stop_reason', None),
                 'termination_status': getattr(getattr(update, 'result', None), 'termination_status', None),
                 'environments': [], 'same_session': None, 'owner_closed': None}
        if self.console:
            event['environments'] = [asdict(x) for x in self.console.environments]
            if event['environments']:
                event['same_session'] = self.console.connection is self.session
        if event['session_reuse'] == 'unknown':
            for env in event['environments']:
                env['identity_verified'] = False
                env['effective_user'] = 'unknown'
        if self.session:
            event.update(owner_closed=self.session.closed,
                         ancestor_closed=getattr(getattr(self.session, 'ancestor', None), 'closed', None),
                         open_fixture_layers=getattr(self.session, 'open_layers', None),
                         connect_calls=getattr(self.session, 'connect_calls', None))
        event['switches'] = list(self.outcomes)
        if extra:
            event.update(extra)
        # Never serialize input source, namespace, result.command or exception text.
        with self.lock:
            self.current = event
            self.events.append(event)
        if update is not None:
            self.polling = update.state in ('running', 'waiting_input')
        elif event['session_reuse'] == 'unknown':
            self.polling = False
        if self.journal:
            with self.journal.open('a') as out:
                out.write(json.dumps(event)+'\n')
        return event

    def _resolve(self, request):
        if self.mode != 'simulated':
            raise PermissionError('native account switches disabled in this test adapter')
        if not request.environment.identity_verified:
            raise PermissionError('identity not verified')
        actor = request.environment.effective_user
        target = request.username or 'root'
        if request.kind == 'su' and target not in self.config.hosts['local-fixture'].get('users', {}):
            raise PermissionError('undeclared target')
        user = target if request.kind == 'su' else actor
        password, source = privilege_password(self.config, 'local-fixture', user,
                                              request.kind, self.login_user)
        if source == 'sudo_disabled':
            raise PermissionError('sudo disabled')
        if password is None and request.kind == 'su':
            raise CredentialsRequiredError('missing declared su credential')
        return SwitchCredentials(password)

    def _observe(self, outcome):
        self.outcomes.append({'kind': outcome.request.kind, 'target': outcome.request.username,
                              'success': outcome.success, 'error_type': outcome.error_type})

    def _open(self, mode, fault=None):
        if self.console and not self.console.done:
            raise RuntimeError('close current console first')
        if self.owner:
            self.owner.close()
        self.mode, self.console, self.outcomes = mode, None, []
        self.owner = ExitStack()
        directory = self.owner.enter_context(tempfile.TemporaryDirectory(prefix='ops-console-fixture-'))
        root = Path(directory)
        users = {}
        if mode == 'simulated':
            secret = 'SYNTHETIC_ONLY_' + 'credential_canary_72d'
            users = {'fixture-login': {'password': secret},
                     'operator': {'password': secret},
                     'blocked': {'password': secret, 'sudo': False}, 'missing': {}}
        (root/'hosts.yaml').write_text(json.dumps({'hosts': {'local-fixture': {
            'connection': {'local': True}, 'users': users}}}))
        self.config = Validator(root)
        self.config.load(root/'hosts.yaml')
        self.config.check_connections()
        self.connection_report = {}
        cls = (lambda: SimulatedSession(fault)) if mode == 'simulated' else Session
        # Explicit test接入點: existing OpsFeast owner yields the raw Session.
        self.session = self.owner.enter_context(connected(self.config, 'local-fixture', cls, 5, self.connection_report))
        self.login_user = self.session.username
        self.console = Console(self.session, ownership='borrowed', terminal=False,
                               credential_resolver=self._resolve, switch_observer=self._observe)
        if self.login_user is None:
            self.login_user = self.console.environments[0].effective_user
        return self._record(self.console.poll(), operation='open')

    def _run(self):
        self.owner = self.console = self.session = None
        self.mode, self.outcomes, self.polling = 'none', [], False
        while not self.halt:
            try:
                operation, value, options, future = self.commands.get(timeout=.04)
            except queue.Empty:
                if self.console and not self.console.done and self.polling:
                    try:
                        update = self.console.poll()
                        if update.state != self.current['state'] or update.stdout or update.stderr or update.error_type != self.current.get('error_type'):
                            self._record(update, operation='poll')
                    except BaseException as exc:
                        self._record(operation='poll', error=exc)
                continue
            try:
                if operation == 'open':
                    event = self._open(value or 'local', options.get('fault'))
                elif operation == 'shutdown':
                    try:
                        if self.console and not self.console.done:
                            self.console.close()
                    finally:
                        try:
                            if self.owner:
                                self.owner.close()
                        finally:
                            self.halt = True
                    event = self.current
                else:
                    if operation == 'submit': update = self.console.submit(value)
                    elif operation == 'start': update = self.console.start_command(value, timeout=options.get('timeout', 5), stop_timeout=1)
                    elif operation == 'input': update = self.console.send_input(value, timeout=options.get('timeout', .3), newline=options.get('newline', True))
                    elif operation == 'enter':
                        self.console.enter(shlex.quote(sys.executable)+' -q -u', prompt='>>>', exit='quit()')
                        update = self.console.poll()
                    elif operation == 'shell':
                        self.console.shell('bash'); update = self.console.poll()
                    elif operation == 'su':
                        self.console.su(value); update = self.console.poll()
                    elif operation == 'sudo':
                        self.console.sudo(username=value or 'root'); update = self.console.poll()
                    elif operation == 'reuse':
                        if self.console is None or self.console.session_reuse != 'confirmed': raise RuntimeError('Session reuse is unknown')
                        result = self.session.exec_command(['printf', 'OWNER_REUSED'], check=True, command_timeout=3)
                        event = self._record(operation=operation, extra={'owner_reuse_stdout': result.stdout, 'owner_reuse_exitcode': result.exitcode})
                        future.set_result(event)
                        continue
                    elif operation == 'host_exception':
                        try:
                            with self.console: raise ValueError('synthetic host body failure')
                        except ValueError:
                            update = self.console.poll()
                    else: update = getattr(self.console, operation)()
                    event = self._record(update, operation=operation)
                future.set_result(event)
            except BaseException as exc:
                event = self._record(operation=operation, error=exc)
                future.set_result(event)

    def stop(self):
        if self.thread.is_alive():
            self.call('shutdown')
            self.thread.join(5)
