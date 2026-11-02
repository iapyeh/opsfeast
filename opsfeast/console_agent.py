"""Persistent chat-owned Console worker, JSON-lines control protocol 0.1.0.

Creates the durable reader before connecting. No remote connection until an
explicit connect request; no arbitrary Python input, retries or credential input.
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
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import uuid

VERSION = '0.1.0'


class ControlError(ValueError):
    pass


class Controls:
    """Bounded fd reader: no TextIO read-ahead, no blocking partial JSON line."""
    def __init__(self, fd):
        self.fd, self.buffer, self.pending, self.eof = fd, b'', deque(), False

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


class Transport:
    def __init__(self, origin, token):
        parsed = urlparse(origin)
        if (parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1', '::1')
                or parsed.path not in ('', '/') or parsed.username or parsed.query or parsed.fragment):
            raise ControlError('loopback_origin_required')
        self.origin = origin.rstrip('/')
        self.token = token

    def post(self, path, body):
        request = Request(self.origin + '/api/v1/console-sessions' + path,
                          data=json.dumps(body, ensure_ascii=False).encode(),
                          headers={'Authorization': 'Bearer ' + self.token,
                                   'Content-Type': 'application/json'})
        # No transport retry: the caller must not replay a command on uncertainty.
        with urlopen(request, timeout=10) as response:
            return json.load(response)


class Publisher:
    def __init__(self, transport, *, title, host_id):
        self.transport = transport
        self.sid = str(uuid.uuid4())
        self.offsets = {}
        transport.post('', {'session_id': self.sid, 'title': title,
                            'host_id': host_id, 'work_id': None})

    def block(self, kind, text='', *, title='', complete=False):
        bid = str(uuid.uuid4())
        self.transport.post('/' + self.sid + '/blocks', {
            'event_id': str(uuid.uuid4()), 'block_id': bid, 'kind': kind,
            'title': title or kind, 'text': '', 'form': None})
        self.offsets[bid] = 0
        self.append(bid, text)
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


class Output:
    """Forward Console writes, including synchronous sudo output, without line buffering."""
    def __init__(self, publisher, kind):
        self.publisher, self.kind, self.bid = publisher, kind, None

    def write(self, text):
        if not text:
            return 0
        if self.bid is None:
            self.bid = self.publisher.block(self.kind)
        self.publisher.append(self.bid, text)
        return len(text)

    def flush(self):
        pass

    def finish(self, status):
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

    def _prompt(self):
        self.publisher.block('stdout', self.console.prompt, title='SSHScript Console prompt', complete=True)

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
                   'sudo': {'timeout'}, 'close': set()}
        if not isinstance(op, str) or op not in allowed or set(body) - {'op', 'request_id'} - allowed[op]:
            raise ControlError('unsupported_operation_or_fields')
        if self.closed:
            raise ControlError('worker_closed')
        if op == 'close':
            return {'state': 'closed', 'cleanup': self.close()}
        if op == 'connect':
            if self.console:
                raise ControlError('already_connected')
            call = self.publisher.block('command', self.connect_source, title='建立 Console 的 API 呼叫')
            self.publisher.status('正在建立 SSHScript Console；尚未確認登入成功。')
            self.scope = self.opener(self.stdout, self.stderr)
            self.opening = True
            self.console = self.scope.__enter__()
            self.opening = False
            self.stdout.finish('completed')
            self.stderr.finish('completed')
            self.publisher.finish(call)
            identity = self._identity()
            self.publisher.status('登入成功：' + identity['host'] + '（' + identity['effective_user']
                                  + '）；SSHScript Console 已就緒。以下提示符來自 SSHScript Console。')
            self._prompt()
            return {'state': 'ready', 'identity': identity}
        if self.console is None:
            raise ControlError('connect_required')
        seconds = deadline(body.get('timeout', 30))
        if op == 'run':
            command = body.get('command')
            if (not isinstance(command, str) or not command.strip() or len(command.encode()) > 16384
                    or any(c in command for c in '\x00\r\n')):
                raise ControlError('single_command_line_required')
            source = command
        else:
            source = '$.sudo(username="root", enter_timeout=' + str(seconds) + ')'
        bid = self.publisher.block('command', source)
        self.emit({'type': 'started', 'request_id': rid, 'command_block': bid})
        update = (self.console.start_command(command, timeout=seconds) if op == 'run'
                  else self.console.submit(source))
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
        out, err = self.stdout.finish(status), self.stderr.finish(status)
        result = {'state': update.state, 'exitcode': update.result.exitcode if update.result else None,
                  'error_type': update.error_type, 'stdout_block': out, 'stderr_block': err}
        if op == 'sudo':
            result['identity'] = self._identity()
        # Failure pauses the session: never silently continue or retry.
        if closing or update.state != 'completed':
            result['cleanup'] = self.close()
        else:
            self._prompt()
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
            label = 'Console 清理結果不明；cleanup=' if reuse == 'unknown' else 'Console 已關閉；cleanup='
            self.publisher.status(label + reuse
                                  + '。通道關閉不保證所有遠端子程序均已終止。')
        return reuse


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8740')
    parser.add_argument('--token-file', type=Path, required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--host')
    target.add_argument('--local', action='store_true', help='credential-free local Console; explicit opt-in')
    parser.add_argument('--profile', default='main')
    parser.add_argument('--title', default='互動 Console')
    parser.add_argument('--sudo-root', action='store_true', help='allow configured login-account sudo to root; not an authorization grant')
    parser.add_argument('--idle-timeout', type=int, default=900)
    args = parser.parse_args(argv)
    if not 1 <= args.idle_timeout <= 3600:
        parser.error('--idle-timeout must be 1–3600')
    if args.local and args.sudo_root:
        parser.error('--sudo-root requires a configured SSH host')
    output = sys.stdout
    def emit(value):
        output.write(json.dumps(value, ensure_ascii=False) + '\n')
        output.flush()
    worker = None
    try:
        import importlib.metadata
        import sshscript
        if (importlib.metadata.version('sshscript') != '7.0.1'
                or sshscript.__version__ != '7.0.1'):
            raise ControlError('sshscript_7_0_1_required')
        transport = Transport(args.url, args.token_file.read_text().strip())
        publisher = Publisher(transport, title=args.title,
                              host_id='localhost' if args.local else args.profile + ' / ' + args.host)
        @contextmanager
        def opener(stdout, stderr):
            if args.local:
                from sshscript import Session, Console
                def reject(request):
                    raise ControlError('local_privilege_switch_unsupported')
                with Session() as session:
                    with Console(session, terminal=False, get_pty=True, stdout=stdout,
                                 stderr=stderr, credential_resolver=reject) as console:
                        yield console
            else:
                from opsfeast import Instance
                profile = Instance.open().profile(args.profile)
                target = profile.sessions.console_target(args.host)
                with profile.sessions.console(args.host, expected_fingerprint=target['fingerprint'],
                                              sudo_root=args.sudo_root, stdout=stdout, stderr=stderr) as console:
                    yield console
        source = ('Console(session, terminal=False, get_pty=True)' if args.local else
                  f'profile.sessions.console({args.host!r}, sudo_root={args.sudo_root!r})')
        worker = Worker(publisher, opener, emit, connect_source=source)
        # First output precedes profile loading, SSH connection and browser QA.
        emit({'type': 'created', 'protocol_version': VERSION, 'session_id': publisher.sid,
              'reader_url': transport.origin + '/console/' + publisher.sid,
              'state': 'awaiting_connect'})
        controls = Controls(sys.stdin.fileno())
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


if __name__ == '__main__':
    sys.exit(main())
