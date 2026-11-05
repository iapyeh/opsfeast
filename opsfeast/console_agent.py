"""Persistent chat-owned Console worker, JSON-lines control protocol 0.3.0.

Creates the durable reader before connecting. No remote connection until an
explicit connect request; no arbitrary Python input or automatic retries.
"""
import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path
import select
import os
from collections import deque
import sys
import time
from urllib.parse import urlparse, urlencode
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
import uuid

VERSION = '0.3.0'


class ControlError(ValueError):
    pass


class Controls:
    """Bounded fd reader: no TextIO read-ahead, no blocking partial JSON line."""
    def __init__(self, fd):
        self.fd, self.buffer, self.pending, self.eof = fd, b'', deque(), False
        self.terminal_settings = None
        if os.isatty(fd):
            import termios
            self.terminal_settings = termios.tcgetattr(fd)
            settings = termios.tcgetattr(fd)
            settings[3] &= ~(termios.ICANON | termios.ECHO)
            settings[6][termios.VMIN], settings[6][termios.VTIME] = 1, 0
            termios.tcsetattr(fd, termios.TCSANOW, settings)

    def close(self):
        if self.terminal_settings is not None:
            import termios
            termios.tcsetattr(self.fd, termios.TCSANOW, self.terminal_settings)
            self.terminal_settings = None

    def read(self, timeout=0):
        if self.pending:
            return self.pending.popleft()
        until = time.monotonic() + timeout
        while True:
            if self.eof:
                return {'op': 'close', 'request_id': str(uuid.uuid4())}
            readable, _, _ = select.select([self.fd], [], [], max(0, until - time.monotonic()))
            if not readable:
                return None
            raw = os.read(self.fd, 4096)
            if not raw:
                self.eof = True
                if self.buffer:
                    self.pending.append({'op': 'invalid'})
                self.buffer = b''
            else:
                self.buffer += raw
                while b'\n' in self.buffer:
                    line, self.buffer = self.buffer.split(b'\n', 1)
                    try:
                        if len(line) > 65536:
                            raise ValueError()
                        self.pending.append(json.loads(line))
                    except (ValueError, UnicodeError):
                        self.pending.append({'op': 'invalid'})
                if len(self.buffer) > 65536:
                    raise ControlError('request_too_large')
            if self.pending:
                return self.pending.popleft()
            if timeout == 0 and not self.eof:
                return None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Transport:
    def __init__(self, origin, token):
        parsed = urlparse(origin)
        if (parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1', '::1')
                or parsed.path not in ('', '/') or parsed.username or parsed.query or parsed.fragment):
            raise ControlError('loopback_origin_required')
        self.origin = origin.rstrip('/')
        self.token = token
        self.http = build_opener(ProxyHandler({}), NoRedirect)

    def post(self, path, body):
        request = Request(self.origin + '/api/v1/console-sessions' + path,
                          data=json.dumps(body, ensure_ascii=False).encode(),
                          headers={'Authorization': 'Bearer ' + self.token,
                                   'Content-Type': 'application/json'})
        # No transport retry: the caller must not replay a command on uncertainty.
        with self.http.open(request, timeout=10) as response:
            return json.load(response)

    def get(self, path):
        request = Request(self.origin + '/api/v1/console-sessions' + path,
                          headers={'Authorization': 'Bearer ' + self.token})
        with self.http.open(request, timeout=10) as response:
            return json.load(response)


class Publisher:
    def __init__(self, transport, *, title, host_id, session_id=None):
        self.transport = transport
        self.sid = session_id or str(uuid.uuid4())
        self.target_id = None
        self.offsets = {}
        if session_id is not None:
            from .console_records import identifier
            identifier(session_id)
            snapshot=transport.get('/'+session_id)
            matches=[t for t in snapshot['session'].get('targets',[]) if t['id']==host_id]
            if len(matches)!=1:raise ControlError('shared_target_not_declared')
            self.target_id=host_id
            return
        transport.post('', {'session_id': self.sid, 'title': title,
                            'host_id': host_id, 'work_id': None})

    def block(self, kind, text='', *, title='', complete=False):
        bid = str(uuid.uuid4())
        self.transport.post('/' + self.sid + '/blocks', {
            'event_id': str(uuid.uuid4()), 'block_id': bid, 'kind': kind,
            'title': title or kind, 'text': text[:4000], 'form': None,
            **({'target_id':self.target_id} if self.target_id is not None else {})})
        self.offsets[bid] = len(text[:4000].encode())
        self.append(bid, text[4000:])
        if complete:
            self.finish(bid)
        return bid

    def append(self, bid, text):
        for start in range(0, len(text), 4000):
            part = text[start:start + 4000]
            self.transport.post('/' + self.sid + '/blocks/' + bid + '/append', {
                'event_id': str(uuid.uuid4()), 'offset': self.offsets[bid], 'text': part})
            self.offsets[bid] += len(part.encode())

    def finish(self, bid, status='completed'):
        self.transport.post('/' + self.sid + '/blocks/' + bid + '/finish', {
            'event_id': str(uuid.uuid4()), 'status': status})

    def status(self, text):
        self.block('status', text, complete=True)

    def activity(self, state, lease_seconds=120):
        result = self.transport.post('/' + self.sid + '/activity', {
            'event_id': str(uuid.uuid4()), 'state': state,
            'lease_seconds': lease_seconds if state == 'thinking' else 0,
            **({'target_id':self.target_id} if self.target_id is not None else {})})
        return result['target_activities'][self.target_id] if self.target_id is not None else result['activity']


class Output:
    """Forward Console writes, including synchronous sudo output, without line buffering."""
    def __init__(self, publisher, kind):
        self.publisher, self.kind, self.bid = publisher, kind, None
        self.secrets, self.pending, self.tail = [], '', ''

    def protect(self, value):
        if value and value not in self.secrets:
            self.secrets.append(value)

    def _redact(self, text, final=False):
        text = self.pending + text
        self.pending = ''
        for secret in self.secrets:
            text = text.replace(secret, '[hidden]')
        if not final:
            hold = max((n for secret in self.secrets for n in range(1, min(len(secret), len(text)+1))
                        if text.endswith(secret[:n])), default=0)
            if hold:
                text, self.pending = text[:-hold], text[-hold:]
        elif any(text and secret.startswith(text) for secret in self.secrets):
            text = '[hidden]'
        return text

    def write(self, text):
        if not text:
            return 0
        size = len(text)
        text = self._redact(text)
        self.tail = (self.tail + text)[-2048:]
        if not text:
            return size
        self._publish(text)
        return size

    def _publish(self, text):
        if self.bid is None:
            self.bid = self.publisher.block(self.kind, text)
        else:
            self.publisher.append(self.bid, text)

    def flush(self):
        pass

    def finish(self, status):
        if self.pending:
            self._publish(self._redact('', final=True))
        if self.bid:
            self.publisher.finish(self.bid, status)
        bid, self.bid = self.bid, None
        return bid


def deadline(value):
    if type(value) is not int or not 1 <= value <= 300:
        raise ControlError('timeout_must_be_integer_1_to_300')
    return value


class Worker:
    def __init__(self, publisher, opener, emit, *, connect_source="Console(session, terminal=False, get_pty=True)"):
        self.publisher, self.opener, self.emit = publisher, opener, emit
        self.console = self.scope = None
        self.stdout = Output(publisher, 'stdout')
        self.stderr = Output(publisher, 'stderr')
        self.seen = set()
        self.closed = False
        self.opening = False
        self.connect_source = connect_source
        self.active_command = None
        self.program = None
        self.program_state = None
        self.control = None
        self.pending_switch = None

    def authorize_switch(self, request):
        """Consume one exact runtime intent, not proof of human authorization."""
        expected, self.pending_switch = self.pending_switch, None
        env = request.environment
        return expected == (request.kind, request.username, env.host, env.effective_user)

    def password(self, _prompt):
        """Private callback: never return its result through the agent protocol."""
        rid = str(uuid.uuid4())
        seconds, label = self.secret_options
        if self.publisher.target_id is not None:
            label=(self.publisher.target_id+' · '+label).encode()[:200].decode(errors='ignore')
        base = '/' + self.publisher.sid + '/secret-requests'
        transport = self.publisher.transport
        reply = transport.post(base, {'request_id': rid, 'label': label, 'timeout': seconds})
        claim = {'claim': reply['claim']}
        self.publisher.activity('idle')
        self.publisher.status('請在河道的安全輸入欄位提供密碼；不會保存於紀錄。')
        self.emit({'type': 'secret_requested', 'request_id': rid, 'expires_at': reply['expires_at']})
        end = time.monotonic() + seconds
        try:
            while time.monotonic() < end:
                incoming = self.control() if self.control else None
                if incoming is not None:
                    if isinstance(incoming, dict) and incoming.get('op') in ('close', 'interrupt'):
                        raise ControlError('secret_input_cancelled')
                    self.emit({'type': 'rejected', 'error_type': 'waiting_for_secret'})
                result = transport.post(base+'/'+rid+'/take', claim)
                if result['state'] == 'consumed':
                    value = result.pop('value')
                    self.stdout.protect(value)
                    self.stderr.protect(value)
                    return value
                time.sleep(.2)
            raise ControlError('secret_input_expired')
        finally:
            try:
                transport.post(base+'/'+rid+'/cancel', claim)
            except Exception:
                pass  # Consumed/expired requests are already gone. Never retry input.

    @staticmethod
    def _line(value, name, limit=16384, empty=False):
        if (not isinstance(value, str) or (not empty and not value.strip())
                or len(value.encode()) > limit or any(c in value for c in '\x00\r\n')):
            raise ControlError('invalid_'+name)
        return value

    def _program_request(self, op, body, control):
        seconds = deadline(body.get('timeout', 30))
        if op == 'enter':
            if self.program:
                raise ControlError('leave_program_first')
            command = self._line(body.get('command'), 'command')
            prompt = self._line(body.get('prompt'), 'prompt', 200)
            exit_text = self._line(body.get('exit'), 'exit', 200)
            secret_prompt = self._line(body.get('secret_prompt', ''), 'secret_prompt', 200, empty=True)
            source = '$.enter('+repr(command)+', prompt='+repr(prompt)+', exit='+repr(exit_text)+')'
        else:
            if not self.program:
                raise ControlError('entered_program_required')
            if op in ('input', 'secret') and self.program_state not in ('waiting_input', 'waiting_secret'):
                raise ControlError('program_not_ready')
            if op == 'input':
                if self.program_state == 'waiting_secret':
                    raise ControlError('use_secret_operation')
                text = self._line(body.get('text'), 'input', empty=True)
                source = '$.input('+repr(text)+')'
            elif op == 'secret':
                if self.program_state != 'waiting_secret':
                    raise ControlError('secret_prompt_required')
                label = self._line(body.get('label', '程式密碼'), 'label', 200)
                self.secret_options = seconds, label
                source = '$.input(secret=True)'
            elif op == 'leave':
                source = '$.exit()'
            else:
                source = '$.poll()'
        self.publisher.activity('idle')
        bid = self.publisher.block('command', self.console.prompt.rstrip()+' '+source)
        self.active_command = bid
        self.emit({'type':'started', 'request_id':body['request_id'], 'command_block':bid})
        self.control = control
        self.stdout.tail = self.stderr.tail = ''
        if op == 'enter':
            self.program = {'secret_prompt': secret_prompt}
            update = self.console.submit(source)
        elif op == 'input':
            update = self.console.send_input(text, timeout=min(seconds, 2))
        elif op == 'secret':
            self.console.input(secret=True, timeout=min(seconds, 2))
            update = self.console.poll()
        elif op == 'leave':
            update = self.console.submit(source)
        else:
            update = self.console.poll()
        end = time.monotonic() + (min(seconds, 15) if op == 'secret' else seconds)
        while update.state == 'running' and time.monotonic() < end:
            marker = self.program['secret_prompt'] if self.program else ''
            if marker and marker in self.stdout.tail + self.stderr.tail:
                break
            incoming = control() if control else None
            if incoming is not None:
                if isinstance(incoming, dict) and incoming.get('op') in ('close','interrupt'):
                    update = self.console.interrupt()
                    if incoming['op'] == 'close':
                        return {'state':'closed','cleanup':self.close()}
                else:
                    self.emit({'type':'rejected','error_type':'busy_or_invalid_control'})
            time.sleep(.04)
            update = self.console.poll()
        in_program = self.console.environments[-1].kind == 'program'
        marker = self.program['secret_prompt'] if self.program else ''
        state = ('waiting_secret' if in_program and marker and marker in self.stdout.tail+self.stderr.tail
                 else update.state)
        self.program_state = state
        if not in_program:
            self.program = None
        status = 'failed' if update.state == 'failed' else 'completed'
        self.publisher.finish(bid, status)
        self.active_command = None
        out, err = self.stdout.finish(status), self.stderr.finish(status)
        if update.state == 'failed' and update.error_type:
            return {'state':'failed', 'error_type':update.error_type,
                    'stdout_block':out, 'stderr_block':err, 'cleanup':self.close()}
        if state == 'waiting_secret':
            self.publisher.status('程式正在等待密碼；請使用 secret 操作啟用安全輸入。')
        self.publisher.activity('idle' if in_program else 'thinking')
        return {'state':state, 'session_state':'program' if in_program else 'ready',
                'exitcode':update.result.exitcode if update.result else None,
                'error_type':update.error_type, 'stdout_block':out, 'stderr_block':err}

    def _identity(self):
        env = asdict(self.console.environments[-1])
        self.publisher.block('identity', json.dumps(env, ensure_ascii=False), complete=True)
        return env

    def request(self, body, control=None):
        if not isinstance(body, dict):
            raise ControlError('object_required')
        rid = body.get('request_id')
        if not isinstance(rid, str) or not 1 <= len(rid) <= 100:
            raise ControlError('request_id_required')
        if rid in self.seen:
            raise ControlError('duplicate_request_not_executed')
        self.seen.add(rid)
        op = body.get('op')
        allowed = {'connect': set(), 'run': {'command', 'timeout'},
                   'sudo': {'timeout','username','authorization'}, 'su': {'timeout','username','authorization'},
                   'close': set(), 'activity': {'state'},
                   'enter': {'command','prompt','exit','secret_prompt','timeout'},
                   'input': {'text','timeout'}, 'secret': {'label','timeout'},
                   'poll': {'timeout'}, 'leave': {'timeout'}}
        if not isinstance(op, str) or op not in allowed or set(body) - {'op', 'request_id', 'purpose'} - allowed[op]:
            raise ControlError('unsupported_operation_or_fields')
        if self.closed:
            raise ControlError('worker_closed')
        if body.get('purpose') is not None:
            self._line(body['purpose'], 'purpose', 1000)
            self.publisher.block('analysis', body['purpose'], title='執行目的', complete=True)
        if op == 'close':
            return {'state': 'closed', 'cleanup': self.close()}
        if op == 'activity':
            state=body.get('state')
            if state not in ('thinking','idle'):raise ControlError('invalid_activity')
            return {'state':'activity_reported','activity':self.publisher.activity(state)}
        if op == 'connect':
            if self.console:
                raise ControlError('already_connected')
            call = self.publisher.block('command', self.connect_source, title='建立 Console 的 API 呼叫')
            self.active_command = call
            self.publisher.status('正在建立 SSHScript Console；尚未確認登入成功。')
            self.scope = self.opener(self.stdout, self.stderr)
            self.opening = True
            self.console = self.scope.__enter__()
            self.opening = False
            self.stdout.finish('completed')
            self.stderr.finish('completed')
            self.publisher.finish(call)
            self.active_command = None
            identity = self._identity()
            self.publisher.status('登入成功：' + identity['host'] + '（' + identity['effective_user']
                                  + '）；SSHScript Console 已就緒。以下提示符來自 SSHScript Console。')
            self.publisher.activity('thinking')
            return {'state': 'ready', 'identity': identity}
        if self.console is None:
            raise ControlError('connect_required')
        if op in ('enter','input','secret','poll') or (op == 'leave' and self.program):
            try:
                return self._program_request(op, body, control)
            except ControlError:
                if self.active_command:
                    self.stdout.finish('interrupted')
                    self.stderr.finish('interrupted')
                    self.close()
                raise
        if self.program:
            raise ControlError('leave_program_first')
        seconds = deadline(body.get('timeout', 30))
        if op == 'run':
            command = body.get('command')
            if (not isinstance(command, str) or not command.strip() or len(command.encode()) > 16384
                    or any(c in command for c in '\x00\r\n')):
                raise ControlError('single_command_line_required')
            source = '$(' + repr(command) + ')'
        elif op in ('sudo', 'su'):
            target = self._line(body.get('username', 'root') if op == 'sudo' else body.get('username'), 'username', 200)
            authorization = self._line(body.get('authorization'), 'authorization', 1000)
            self.publisher.block('authorization', authorization, title='本次帳號切換授權依據', complete=True)
            env = self.console.environments[-1]
            self.pending_switch = (op, target, env.host, env.effective_user)
            self.secret_options = 300, op + '：切換至 ' + target + ' 的密碼'
            self.control = control
            source = '$.' + op + '(username=' + repr(target) + ', enter_timeout=' + str(seconds) + ')'
        else:
            if self.console.environments[-1].kind not in ('sudo', 'su'):
                raise ControlError('identity_layer_required')
            source = '$.exit()'
        bid = self.publisher.block('command', self.console.prompt.rstrip() + ' ' + source)
        self.active_command = bid
        self.emit({'type': 'started', 'request_id': rid, 'command_block': bid})
        try:
            update = (self.console.start_command(command, timeout=seconds) if op == 'run'
                      else self.console.submit(source))
        finally:
            self.pending_switch = None
        closing = False
        while update.state == 'running':
            # Only an interrupt/close control may overtake an active command.
            incoming = control() if control else None
            if incoming is not None:
                if (isinstance(incoming, dict) and incoming.get('op') in ('interrupt', 'close')
                        and set(incoming) == {'op', 'request_id'}
                        and isinstance(incoming['request_id'], str)
                        and 1 <= len(incoming['request_id']) <= 100 and incoming['request_id'] not in self.seen):
                    self.seen.add(incoming['request_id'])
                    closing = incoming['op'] == 'close'
                    update = self.console.interrupt()
                    self.emit({'type': 'control_received', 'request_id': incoming['request_id'],
                               'state': update.state, 'stop_confirmed': False})
                else:
                    self.emit({'type': 'rejected', 'error_type': 'busy_or_invalid_control'})
            if update.state == 'running':
                time.sleep(.04)
                update = self.console.poll()
        status = 'completed' if update.state == 'completed' else 'failed'
        self.publisher.finish(bid, status)
        self.active_command = None
        out, err = self.stdout.finish(status), self.stderr.finish(status)
        result = {'state': update.state, 'exitcode': update.result.exitcode if update.result else None,
                  'error_type': update.error_type, 'stdout_block': out, 'stderr_block': err}
        if op in ('sudo','su','leave'):
            result['identity'] = self._identity()
        # A normally terminated nonzero command is not a broken connection.
        recoverable = (op == 'run' and update.state == 'failed' and update.error_type is None
                       and update.result is not None and update.result.exitcode != 0
                       and getattr(update.result, 'termination_status', None) == 'confirmed')
        if closing or (update.state != 'completed' and not recoverable):
            result['cleanup'] = self.close()
        else:
            result['session_state'] = 'ready'
            if recoverable:
                self.publisher.status('指令失敗（exitcode=' + str(update.result.exitcode)
                                      + '）；連線保留，等待下一個指示，不自動重試。')
            else:
                self.publisher.activity('thinking')
        return result

    def close(self):
        if self.closed:
            return 'already_closed'
        self.closed = True
        reuse = 'unknown' if self.opening else 'not_connected'
        try:
            if self.console:
                self.scope.__exit__(None, None, None)
                reuse = self.console.session_reuse
            self.stdout.finish('completed')
            self.stderr.finish('completed')
        except BaseException:
            reuse = 'unknown'
            raise
        finally:
            if self.active_command:
                self.publisher.finish(self.active_command, 'interrupted')
                self.active_command = None
            label = 'Console 清理結果不明；cleanup=' if reuse == 'unknown' else 'Console 已關閉；cleanup='
            self.publisher.status(label + reuse
                                  + '。通道關閉不保證所有遠端子程序均已終止。')
            self.publisher.activity('idle')
            self.stdout.secrets.clear()
            self.stderr.secrets.clear()
        return reuse


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8740')
    credentials = parser.add_mutually_exclusive_group(required=True)
    credentials.add_argument('--token-file', type=Path, help='Scoped-token integrations only; agent-owned launch uses a pipe')
    credentials.add_argument('--token-fd', type=int, help='Inherited anonymous pipe containing one capability line')
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--host')
    target.add_argument('--local', action='store_true', help='credential-free local Console; explicit opt-in')
    parser.add_argument('--profile', help='registered profile; default: .opsfeast.yaml default_profile')
    parser.add_argument('--title', default='互動 Console')
    parser.add_argument('--session', help='Attach this host worker to an existing shared task UUID; no connection until connect')
    parser.add_argument('--idle-timeout', type=int, default=900)
    args = parser.parse_args(argv)
    if not 1 <= args.idle_timeout <= 3600:
        parser.error('--idle-timeout must be 1–3600')
    if args.session and args.local:parser.error('--session requires a managed host')
    output = sys.stdout
    def emit(value):
        output.write(json.dumps(value, ensure_ascii=False) + '\n')
        output.flush()
    worker = controls = None
    try:
        import importlib.metadata
        import sshscript
        if (importlib.metadata.version('sshscript') != '7.0.1'
                or sshscript.__version__ != '7.0.1'):
            raise ControlError('sshscript_7_0_1_required')
        if args.token_fd is not None:
            with os.fdopen(args.token_fd, 'r') as secret:
                token = secret.read(257).strip()
            if not 32 <= len(token) <= 256:raise ControlError('invalid_token_pipe')
        else:
            token = args.token_file.read_text().strip()
        transport = Transport(args.url, token)
        del token
        profile = None
        if not args.local:
            from opsfeast import Instance
            profile = Instance.open().profile(args.profile)
        publisher = Publisher(transport, title=args.title,
                              host_id='localhost' if args.local else profile.name + ' / ' + args.host,
                              **({'session_id':args.session} if args.session else {}))
        @contextmanager
        def opener(stdout, stderr):
            if args.local:
                from sshscript import Session, Console
                def reject(request):
                    raise ControlError('local_privilege_switch_unsupported')
                with Session() as session:
                    with Console(session, terminal=False, get_pty=True, stdout=stdout,
                                 stderr=stderr, credential_resolver=reject,
                                 password_func=lambda prompt: worker.password(prompt)) as console:
                        yield console
            else:
                target = profile.sessions.console_target(args.host)
                with profile.sessions.console(args.host, expected_fingerprint=target['fingerprint'],
                                              switch_authorizer=worker.authorize_switch, stdout=stdout, stderr=stderr,
                                              password_func=lambda prompt: worker.password(prompt)) as console:
                    yield console
        source = ('Console(session, terminal=False, get_pty=True)' if args.local else
                  f'profile.sessions.console({args.host!r}, switch_authorizer=worker.authorize_switch)')
        worker = Worker(publisher, opener, emit, connect_source=source)
        # Prepare PTY input before announcing readiness: canonical mode can
        # discard long JSON lines before Python ever receives them.
        controls = Controls(sys.stdin.fileno())
        # Configuration is read-only; no SSH connection occurs before connect.
        emit({'type': 'created', 'protocol_version': VERSION, 'session_id': publisher.sid,
              'reader_url': transport.origin + '/console/' + publisher.sid + ('' if profile is None else
                  '?' + urlencode({'profile': profile.name, 'host_id': args.host})),
              'profile': None if profile is None else profile.name,
              'hosts_file': None if profile is None else str(profile.root / 'hosts.yaml'),
              'state': 'awaiting_connect'})
        while not worker.closed:
            body = controls.read(args.idle_timeout)
            if body is None:
                emit({'type': 'closed', 'reason': 'idle_timeout', 'cleanup': worker.close()})
                break
            try:
                result = worker.request(body, controls.read)
                emit({'type': 'result', 'request_id': body.get('request_id'), **result})
            except ControlError as exc:
                emit({'type': 'rejected', 'error_type': str(exc)})
        return 0
    except BaseException as exc:
        # Never print arbitrary exception messages, config, credentials or tracebacks.
        emit({'type': 'failed', 'error_type': type(exc).__name__, 'cleanup': 'unknown'})
        if worker:
            try:
                worker.stdout.finish('interrupted')
                worker.stderr.finish('interrupted')
                worker.publisher.status('執行失敗：' + type(exc).__name__ + '；停止操作，不自動重試。')
            except BaseException:
                pass
        return 130 if isinstance(exc, KeyboardInterrupt) else 1
    finally:
        if worker and not worker.closed:
            try:
                emit({'type': 'closed', 'cleanup': worker.close()})
            except BaseException as exc:
                emit({'type': 'cleanup_failed', 'error_type': type(exc).__name__, 'cleanup': 'unknown'})
        if controls:
            controls.close()


if __name__ == '__main__':
    sys.exit(main())
