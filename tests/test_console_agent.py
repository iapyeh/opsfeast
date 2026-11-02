"""Reproducible worker tests: no managed-host connection or real credentials."""
import contextlib
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock

from opsfeast.console_agent import Controls, ControlError, Publisher, Transport, Worker
from opsfeast.console_records import Records


class StoreTransport:
    def __init__(self, records):
        self.records = records
    def post(self, path, body):
        parts = path.strip('/').split('/')
        if not path:
            return self.records.create(body)
        if len(parts) == 2:
            return self.records.add_block(parts[0], body)
        method = self.records.append if parts[-1] == 'append' else self.records.finish
        return method(parts[0], parts[2], body)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.records = Records(Path(tmp.name))
        self.publisher = Publisher(StoreTransport(self.records), title='Synthetic', host_id='local')

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

    def test_duplicate_request_never_repeats_command(self):
        console = Mock(prompt='synthetic [test]> ')
        console.start_command.return_value = SimpleNamespace(state='completed', result=SimpleNamespace(exitcode=0), error_type=None)
        worker = Worker(self.publisher, None, lambda value: None)
        worker.console = console
        worker.request({'op':'run','request_id':'once','command':'printf once'})
        with self.assertRaisesRegex(ControlError, 'duplicate'):
            worker.request({'op':'run','request_id':'once','command':'printf once'})
        console.start_command.assert_called_once()

    def test_failure_closes_scope_and_keeps_exit_status(self):
        console = Mock(session_reuse='confirmed')
        console.start_command.return_value = SimpleNamespace(state='failed', result=SimpleNamespace(exitcode=9), error_type=None)
        worker = Worker(self.publisher, None, lambda value: None)
        worker.console, worker.scope = console, MagicMock()
        result = worker.request({'op':'run','request_id':'fail','command':'false'})
        self.assertEqual(result['exitcode'], 9)
        self.assertTrue(worker.closed)
        worker.scope.__exit__.assert_called_once()

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
        with patch('opsfeast.console_agent.urlopen', side_effect=OSError('private-data')) as send:
            with self.assertRaises(OSError):
                Transport('http://localhost:8740', 'fixture').post('', {})
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

    def test_created_first_then_streams_before_completion_and_retains_shell(self):
        self.assertEqual(self.created['state'], 'awaiting_connect')
        self.assertEqual(self.records.snapshot(self.sid)['blocks'], [])
        self.send({'op':'connect','request_id':'connect'})
        self.assertEqual(self.event('result')['state'], 'ready')
        blocks = self.records.snapshot(self.sid)['blocks']
        self.assertEqual(blocks[0]['kind'], 'command')
        self.assertIn('Console(session', blocks[0]['head'])
        self.assertTrue(any('登入成功' in b['head'] for b in blocks))
        self.assertTrue(any(b['title']=='SSHScript Console prompt' and '> ' in b['head'] for b in blocks))
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
