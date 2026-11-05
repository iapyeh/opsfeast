"""Reproducible worker tests: no managed-host connection or real credentials."""
import contextlib
import concurrent.futures
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch

from opsfeast.console_agent import Controls, ControlError, Publisher, Transport, Worker, main
from opsfeast.console_records import Records


class StoreTransport:
    def __init__(self, records):
        self.records = records
    def post(self, path, body):
        parts = path.strip('/').split('/')
        if not path:
            return self.records.create(body)
        if len(parts)==2 and parts[1]=='activity':
            return self.records.activity(parts[0],body)
        if len(parts) == 2:
            return self.records.add_block(parts[0], body)
        method = self.records.append if parts[-1] == 'append' else self.records.finish
        return method(parts[0], parts[2], body)


class ProfileSelectionTests(unittest.TestCase):
    def setUp(self):
        from opsfeast import Instance
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        for name in ('main', 'selected'):
            (self.root / name).mkdir()
            (self.root / name / 'hosts.yaml').write_text('hosts: {}\n')
        self.registry = self.root / '.opsfeast.yaml'
        self.registry.write_text(json.dumps({'schema_version': 2, 'default_profile': 'selected',
            'profiles': {name: {'root': name} for name in ('main', 'selected')}}))
        self.instance = Instance.open(self.root)
        self.token = self.root / 'token'
        self.token.write_text('fixture-only')

    def launch(self, *args):
        output = io.StringIO()
        with patch('opsfeast.Instance.open', return_value=self.instance) as opened, \
                patch('opsfeast.console_agent.Transport') as transport, \
                patch('opsfeast.console_agent.Publisher') as publisher, \
                patch('opsfeast.console_agent.Worker') as worker, \
                patch('opsfeast.console_agent.Controls'), contextlib.redirect_stdout(output):
            publisher.return_value.sid = 'fixture'
            transport.return_value.origin = 'http://127.0.0.1:8740'
            worker.return_value.closed = True
            code = main(['--token-file', str(self.token), *args])
            return code, json.loads(output.getvalue()), opened, publisher, worker

    def test_omitted_profile_uses_locator_default_without_connecting(self):
        before = self.registry.read_bytes()
        code, created, _, publisher, worker = self.launch('--host', 'synthetic')
        self.assertEqual(code, 0)
        self.assertEqual(created['profile'], 'selected')
        self.assertEqual(created['hosts_file'], str(self.root / 'selected' / 'hosts.yaml'))
        self.assertEqual(publisher.call_args.kwargs['host_id'], 'selected / synthetic')
        worker.return_value.request.assert_not_called()
        self.assertEqual(self.registry.read_bytes(), before)

    def test_explicit_profile_overrides_without_changing_default(self):
        before = self.registry.read_bytes()
        code, created, _, _, _ = self.launch('--host', 'synthetic', '--profile', 'main')
        self.assertEqual(code, 0)
        self.assertEqual(created['profile'], 'main')
        self.assertEqual(self.registry.read_bytes(), before)

    def test_unknown_profile_does_not_fall_back_or_create_reader(self):
        code, event, _, publisher, worker = self.launch('--host', 'synthetic', '--profile', 'missing')
        self.assertEqual(code, 1)
        self.assertEqual(event['error_type'], 'ConfigError')
        publisher.assert_not_called()
        worker.assert_not_called()

    def test_missing_default_does_not_fall_back_to_main(self):
        self.registry.unlink()
        code, event, _, publisher, _ = self.launch('--host', 'synthetic')
        self.assertEqual(code, 1)
        self.assertEqual(event['error_type'], 'ConfigError')
        publisher.assert_not_called()

    def test_local_does_not_resolve_profile(self):
        self.registry.unlink()
        code, created, opened, _, _ = self.launch('--local')
        self.assertEqual(code, 0)
        self.assertIsNone(created['profile'])
        self.assertIsNone(created['hosts_file'])
        opened.assert_not_called()


class WorkerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.records = Records(Path(tmp.name))
        self.publisher = Publisher(StoreTransport(self.records), title='Synthetic', host_id='local')

    def test_concurrent_tasks_on_same_host_have_distinct_sessions_and_isolated_events(self):
        barrier = threading.Barrier(2)
        def task(text):
            barrier.wait(timeout=5)
            publisher = Publisher(StoreTransport(self.records), title='Same task title', host_id='lab / web-01')
            publisher.block('stdout', text, complete=True)
            publisher.activity('thinking' if text=='first' else 'idle')
            return publisher.sid
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(task, ('first','second')))
        self.assertNotEqual(first, second)
        history = self.records.list_sessions('lab / web-01')['sessions']
        self.assertEqual({item['reader_url'] for item in history}, {'/console/'+first,'/console/'+second})
        for sid,text,state in ((first,'first','thinking'),(second,'second','idle')):
            snapshot = self.records.snapshot(sid)
            self.assertEqual([b['head'] for b in snapshot['blocks']], [text])
            self.assertEqual(snapshot['session']['activity']['state'], state)
            self.assertTrue(all(event['session_id']==sid for event in self.records.events(sid,0)))
        from opsfeast.console_records import RecordError
        with self.assertRaisesRegex(RecordError,'session_conflict'):
            self.records.create({'session_id':first,'title':'A different task','host_id':'lab / web-01','work_id':None})
        self.assertEqual(self.records.snapshot(first)['session']['title'],'Same task title')

    def test_first_event_contains_text_and_large_unicode_writes_keep_offsets(self):
        text = '即時' * 2100
        bid = self.publisher.block('stdout', text)
        events = self.records.events(self.publisher.sid, 0)
        self.assertTrue(events[0]['block']['head'].startswith('即時'))
        self.assertEqual(self.records.content(self.publisher.sid, bid, 0, 16384)['text'], text)
        self.assertEqual(self.publisher.offsets[bid], len(text.encode()))

    def test_command_is_durable_before_console_starts(self):
        console = Mock(prompt='synthetic> ')
        def start(command, **options):
            blocks = self.records.snapshot(self.publisher.sid)['blocks']
            self.assertEqual(blocks[-1]['head'], 'synthetic> $(' + repr(command) + ')')
            self.assertEqual(blocks[-1]['status'], 'streaming')
            return SimpleNamespace(state='completed', result=SimpleNamespace(exitcode=0), error_type=None)
        console.start_command.side_effect = start
        worker = Worker(self.publisher, None, lambda value: None)
        worker.console = console
        self.assertEqual(worker.request({'op':'run','request_id':'live','command':'sleep 1'})['state'], 'completed')

    def test_thinking_handoff_chat_idle_next_command_and_close(self):
        console=Mock(prompt='synthetic> ',session_reuse='confirmed')
        def start(command,**options):
            self.assertEqual(self.records.snapshot(self.publisher.sid)['session']['activity']['state'],'idle')
            return SimpleNamespace(state='completed',result=SimpleNamespace(exitcode=0),error_type=None)
        console.start_command.side_effect=start
        worker=Worker(self.publisher,None,lambda value:None)
        worker.console,worker.scope=console,MagicMock()
        worker.request({'op':'activity','request_id':'thinking','state':'thinking'})
        worker.request({'op':'run','request_id':'command-1','command':'pwd'})
        self.assertEqual(self.records.snapshot(self.publisher.sid)['session']['activity']['state'],'thinking')
        worker.request({'op':'activity','request_id':'chat','state':'idle'})
        self.assertEqual(self.records.snapshot(self.publisher.sid)['session']['activity']['state'],'idle')
        worker.request({'op':'run','request_id':'command-2','command':'pwd'})
        self.assertEqual(self.records.snapshot(self.publisher.sid)['session']['activity']['state'],'thinking')
        worker.close()
        self.assertEqual(self.records.snapshot(self.publisher.sid)['session']['activity']['state'],'idle')
        self.assertEqual(console.start_command.call_count,2)
        worker.scope.__exit__.assert_called_once()

    def test_activity_control_has_no_execution_effect_and_validates_state(self):
        opener=Mock();worker=Worker(self.publisher,opener,lambda value:None)
        result=worker.request({'op':'activity','request_id':'prepare','state':'thinking'})
        self.assertEqual(result['state'],'activity_reported');opener.assert_not_called()
        with self.assertRaisesRegex(ControlError,'invalid_activity'):
            worker.request({'op':'activity','request_id':'bad','state':'live'})
        worker.request({'op':'close','request_id':'stop'})
        self.assertEqual(self.records.snapshot(self.publisher.sid)['session']['activity']['state'],'idle')

    def test_create_does_not_connect_and_validation_never_executes(self):
        opener = Mock()
        worker = Worker(self.publisher, opener, lambda value: None)
        self.assertEqual(len(self.records.snapshot(self.publisher.sid)['blocks']), 0)
        for body in (None, {'op': [], 'request_id': 'invalid-op'}, {'op':'connect'}, {'op':'run','request_id':'a','command':'pwd'},
                     {'op':'connect','request_id':'b','password':'do-not-log'}):
            with self.assertRaises(ControlError):
                worker.request(body)
        opener.assert_not_called()
        worker.close()

    def test_cleanup_finishes_command_when_connect_or_submission_raises(self):
        for operation in ('connect', 'run'):
            with self.subTest(operation=operation):
                scope = MagicMock()
                scope.__enter__.side_effect = RuntimeError('synthetic failure')
                worker = Worker(self.publisher, Mock(return_value=scope), lambda value: None)
                body = {'op':operation,'request_id':'exception'}
                if operation == 'run':
                    worker.console = Mock(prompt='synthetic> ', session_reuse='confirmed')
                    worker.console.start_command.side_effect = RuntimeError('synthetic failure')
                    worker.scope = scope
                    body['command'] = 'pwd'
                with self.assertRaises(RuntimeError):
                    worker.request(body)
                bid = worker.active_command
                worker.close()
                block = next(b for b in self.records.snapshot(self.publisher.sid)['blocks'] if b['id']==bid)
                self.assertEqual(block['status'], 'interrupted')
                self.assertIsNone(worker.active_command)

    def test_duplicate_request_never_repeats_command(self):
        console = Mock(prompt='synthetic [test]> ')
        console.start_command.return_value = SimpleNamespace(state='completed', result=SimpleNamespace(exitcode=0), error_type=None)
        worker = Worker(self.publisher, None, lambda value: None)
        worker.console = console
        worker.request({'op':'run','request_id':'once','command':'printf once'})
        with self.assertRaisesRegex(ControlError, 'duplicate'):
            worker.request({'op':'run','request_id':'once','command':'printf once'})
        console.start_command.assert_called_once()

    def test_unknown_failure_closes_scope_and_keeps_exit_status(self):
        console = Mock(prompt='synthetic> ', session_reuse='confirmed')
        console.start_command.return_value = SimpleNamespace(state='failed', result=SimpleNamespace(exitcode=9), error_type=None)
        worker = Worker(self.publisher, None, lambda value: None)
        worker.console, worker.scope = console, MagicMock()
        result = worker.request({'op':'run','request_id':'fail','command':'false'})
        self.assertEqual(result['exitcode'], 9)
        self.assertTrue(worker.closed)
        worker.scope.__exit__.assert_called_once()

    def test_normal_nonzero_exit_keeps_scope_without_retry(self):
        console = Mock(prompt='synthetic [root]> ', session_reuse='confirmed')
        console.start_command.return_value = SimpleNamespace(state='failed',
            result=SimpleNamespace(exitcode=9, termination_status='confirmed'), error_type=None)
        worker = Worker(self.publisher, None, lambda value: None)
        worker.console, worker.scope = console, MagicMock()
        result = worker.request({'op':'run','request_id':'fail','command':'false'})
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['exitcode'], 9)
        self.assertEqual(result['session_state'], 'ready')
        self.assertFalse(worker.closed)
        worker.scope.__exit__.assert_not_called()
        console.start_command.assert_called_once()
        commands = [b for b in self.records.snapshot(self.publisher.sid)['blocks'] if b['kind']=='command']
        self.assertEqual(commands[0]['head'], "synthetic [root]> $('false')")

    def test_error_or_unknown_termination_still_closes_scope(self):
        for error, termination in ((None, 'unknown'), ('TimeoutError', 'confirmed')):
            with self.subTest(error=error, termination=termination):
                console = Mock(prompt='synthetic> ', session_reuse='confirmed')
                console.start_command.return_value = SimpleNamespace(state='failed',
                    result=SimpleNamespace(exitcode=1, termination_status=termination), error_type=error)
                worker = Worker(self.publisher, None, lambda value: None)
                worker.console, worker.scope = console, MagicMock()
                result = worker.request({'op':'run','request_id':'fail','command':'false'})
                self.assertTrue(worker.closed)
                self.assertIn('cleanup', result)

    def test_invalid_commands_and_deadlines_do_not_reach_console(self):
        worker = Worker(self.publisher, None, lambda value: None)
        worker.console = Mock()
        for index, changes in enumerate(({'command':''}, {'command':'pwd\nid'},
                {'command':'x\x00'}, {'command':'a'*16385}, {'timeout':True},
                {'timeout':0}, {'timeout':301}, {'timeout':1.5})):
            with self.assertRaises(ControlError):
                worker.request({'op':'run','request_id':str(index),'command':'pwd', **changes})
        worker.console.start_command.assert_not_called()

    def test_cleanup_failure_is_not_reported_closed(self):
        worker = Worker(self.publisher, None, lambda value: None)
        worker.console, worker.scope = Mock(), MagicMock()
        worker.scope.__exit__.side_effect = RuntimeError('private-error')
        with self.assertRaises(RuntimeError):
            worker.close()
        text = self.records.snapshot(self.publisher.sid)['blocks'][-1]['head']
        self.assertIn('unknown', text)
        self.assertNotIn('private-error', text)

    def test_unknown_transport_is_not_retried(self):
        from unittest.mock import patch
        transport = Transport('http://localhost:8740', 'fixture')
        with patch.object(transport.http, 'open', side_effect=OSError('private-data')) as send:
            with self.assertRaises(OSError):
                transport.post('', {})
            send.assert_called_once()
        for url in ('https://localhost', 'http://example.invalid', 'http://localhost/path', 'http://user@localhost'):
            with self.assertRaises(ControlError):
                Transport(url, 'fixture')

    def test_controls_accept_batched_and_fragmented_lines_and_eof(self):
        read, write = os.pipe()
        self.addCleanup(os.close, read)
        self.addCleanup(os.close, write)
        controls = Controls(read)
        os.write(write, b'{"op":')
        self.assertIsNone(controls.read())
        os.write(write, b'"connect"}\n{"op":"close"}\n')
        self.assertEqual(controls.read()['op'], 'connect')
        self.assertEqual(controls.read()['op'], 'close')
        os.write(write, b'bad\n')
        self.assertEqual(controls.read()['op'], 'invalid')

    def test_pty_controls_accept_long_unicode_without_canonical_truncation_and_restore(self):
        import termios
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        before = termios.tcgetattr(slave)
        controls = Controls(slave)
        self.addCleanup(controls.close)
        body = {'op':'run','request_id':'long','command':'字'*600}
        raw = (json.dumps(body,ensure_ascii=False)+'\n').encode()
        self.assertGreater(len(raw), 1024)
        # PTY input queues can be smaller than this line: write concurrently,
        # as the real caller/worker do, rather than blocking this reader thread.
        def send():
            offset = 0
            while offset < len(raw):
                offset += os.write(master,raw[offset:])
        writer = threading.Thread(target=send,daemon=True)
        writer.start()
        self.assertEqual(controls.read(2),body)
        writer.join(2)
        self.assertFalse(writer.is_alive())
        controls.close()
        restored = termios.tcgetattr(slave)
        # macOS sets the transient kernel PENDIN bit when canonical input is
        # restored; compare configured flags, not pending-input bookkeeping.
        pending = getattr(termios, 'PENDIN', 0)
        restored[3] &= ~pending
        before[3] &= ~pending
        self.assertEqual(restored,before)


class NativeWorkerTests(unittest.TestCase):
    def setUp(self):
        try:
            import sshscript
        except ImportError:
            self.skipTest('requires matching SSHScript environment')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.records = Records(Path(self.tmp.name)/'records')
        transport = StoreTransport(self.records)
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.headers.get('Authorization') != 'Bearer fixture-only':
                    self.send_error(401)
                    return
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                result = transport.post(self.path.removeprefix('/api/v1/console-sessions'), body)
                raw = json.dumps(result).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        token = Path(self.tmp.name)/'token'
        token.write_text('fixture-only')
        self.process = subprocess.Popen([sys.executable, '-B', '-u', '-m', 'opsfeast.console_agent',
            '--local', '--token-file', str(token), '--url', 'http://127.0.0.1:' + str(self.server.server_port)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def cleanup():
            if self.process.poll() is None:
                self.process.kill()
            self.process.communicate()
        self.addCleanup(cleanup)
        self.events = queue.Queue()
        def read():
            for line in self.process.stdout:
                self.events.put(json.loads(line))
        threading.Thread(target=read, daemon=True).start()
        self.created = self.event('created')
        self.sid = self.created['session_id']

    def event(self, kind, timeout=10):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            value = self.events.get(timeout=max(.01, end-time.monotonic()))
            if value['type'] == 'failed':
                self.fail(str(value))
            if value['type'] == kind:
                return value
        self.fail('missing ' + kind)

    def send(self, body):
        self.process.stdin.write(json.dumps(body) + '\n')
        self.process.stdin.flush()

    def content(self):
        return ''.join(self.records.content(self.sid, b['id'], 0, 16384)['text']
                       for b in self.records.snapshot(self.sid)['blocks'] if b['kind'] in ('stdout','stderr'))

    def test_record_client_activity_after_worker_closes_never_reconnects(self):
        self.send({'op':'close','request_id':'close'})
        self.assertEqual(self.event('result')['cleanup'],'not_connected')
        self.process.wait(timeout=5)
        args=[sys.executable,'-B','-m','opsfeast.console_client','--url',
              'http://127.0.0.1:'+str(self.server.server_port),'--token-file',
              str(Path(self.tmp.name)/'token'),'activity','--session',self.sid]
        for state,seconds in (('thinking',120),('idle',0)):
            result=subprocess.run(args,input=json.dumps({'event_id':str(uuid.uuid4()),'state':state,'lease_seconds':seconds}),
                                  text=True,capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['activity']['state'],state)
        self.assertFalse(any(b['kind']=='command' for b in self.records.snapshot(self.sid)['blocks']))

    def test_created_first_then_streams_before_completion_and_retains_shell(self):
        self.assertEqual(self.created['state'], 'awaiting_connect')
        self.assertEqual(self.records.snapshot(self.sid)['blocks'], [])
        self.send({'op':'connect','request_id':'connect'})
        self.assertEqual(self.event('result')['state'], 'ready')
        self.assertEqual(self.records.snapshot(self.sid)['session']['activity']['state'],'thinking')
        blocks = self.records.snapshot(self.sid)['blocks']
        self.assertEqual(blocks[0]['kind'], 'command')
        self.assertIn('Console(session', blocks[0]['head'])
        self.assertTrue(any('登入成功' in b['head'] for b in blocks))
        self.assertFalse(any(b['title']=='SSHScript Console prompt' for b in blocks))
        self.send({'op':'run','request_id':'stream','command':"printf '前段'; sleep 1.2; printf '後段\\n'; printf 'ERR\\n' >&2"})
        self.event('started')
        end = time.monotonic()+1
        while '前段' not in self.content() and time.monotonic()<end:
            time.sleep(.02)
        self.assertIn('前段', self.content())
        self.assertNotIn('後段', self.content())
        self.assertEqual(self.process.poll(), None)
        result = self.event('result')
        self.assertEqual(result['exitcode'], 0)
        self.assertIn('後段', self.content())
        self.assertIn('ERR', self.content())
        self.assertEqual(self.records.snapshot(self.sid)['session']['activity']['state'],'thinking')
        self.send({'op':'activity','request_id':'chat-output','state':'idle'})
        self.assertEqual(self.event('result')['state'],'activity_reported')
        self.assertEqual(self.records.snapshot(self.sid)['session']['activity']['state'],'idle')
        self.send({'op':'run','request_id':'env','command':'export OPSFEAST_WORKER_FIXTURE=retained'})
        self.event('result')
        self.send({'op':'run','request_id':'read-env','command':'printf "$OPSFEAST_WORKER_FIXTURE"'})
        self.event('result')
        self.assertIn('retained', self.content())
        self.send({'op':'close','request_id':'close'})
        result = self.event('result')
        self.assertEqual(result['state'], 'closed')
        self.assertEqual(result['cleanup'], 'confirmed')
        self.assertEqual(self.process.wait(timeout=10), 0)

    def test_failed_command_preserves_shell_and_groups_prompt_with_next_input(self):
        self.send({'op':'connect','request_id':'connect'})
        self.event('result')
        self.send({'op':'run','request_id':'setup','command':'export OPSFEAST_KEEP=same-shell; cd /tmp'})
        self.event('result')
        self.send({'op':'run','request_id':'fail','command':'false'})
        self.event('started')
        result = self.event('result')
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['exitcode'], 1)
        self.assertEqual(result['session_state'], 'ready')
        self.assertIsNone(self.process.poll())
        self.send({'op':'run','request_id':'after','command':'printf "$OPSFEAST_KEEP"; pwd'})
        self.event('started')
        self.assertEqual(self.event('result')['state'], 'completed')
        self.assertIn('same-shell/tmp', self.content())
        blocks = self.records.snapshot(self.sid)['blocks']
        commands = [b for b in blocks if b['kind']=='command']
        self.assertIn("> $('false')", commands[-2]['head'])
        self.assertEqual(commands[-2]['status'], 'failed')
        self.assertFalse(any(b['title']=='SSHScript Console prompt' for b in blocks))
        self.send({'op':'close','request_id':'close'})
        self.assertEqual(self.event('result')['cleanup'], 'confirmed')

    def test_running_close_interrupts_and_exits_without_rerun(self):
        self.send({'op':'connect','request_id':'connect'})
        self.event('result')
        self.send({'op':'run','request_id':'long','command':'sleep 20','timeout':30})
        self.event('started')
        self.send({'op':'close','request_id':'stop'})
        self.event('control_received')
        result = self.event('result')
        self.assertIn(result['state'], ('failed','completed'))
        self.assertIn('cleanup', result)
        self.assertEqual(self.process.wait(timeout=10), 0)

    def test_eof_closes_connected_scope(self):
        self.send({'op':'connect','request_id':'connect'})
        self.event('result')
        self.process.stdin.close()
        self.process.stdin = None
        result = self.event('result')
        self.assertEqual(result['state'], 'closed')
        self.assertEqual(result['cleanup'], 'confirmed')
        self.assertEqual(self.process.wait(timeout=10), 0)

    def test_displayed_input_executes_in_python_console_with_literal_quotes(self):
        import shlex
        from sshscript import Session, Console
        value = '繁體 \'single\' "double" $literal \\path'
        command = "printf '%s' " + shlex.quote(value)
        self.send({'op':'connect','request_id':'connect'})
        self.event('result')
        self.send({'op':'run','request_id':'quoted','command':command})
        self.event('started')
        self.assertEqual(self.event('result')['exitcode'], 0)
        block = [b for b in self.records.snapshot(self.sid)['blocks'] if b['kind']=='command'][-1]
        displayed = self.records.content(self.sid, block['id'])['text']
        expression = displayed.split('> ', 1)[1]
        self.assertTrue(expression.startswith('$('))
        # Execute the saved input itself, not a separately reconstructed command.
        with contextlib.closing(Session()) as session:
            with Console(session, terminal=False) as console:
                update = console.submit(expression)
                self.assertEqual(update.state, 'completed')
                self.assertIn(value, update.stdout)
