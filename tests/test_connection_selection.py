"""Synthetic connection selection/progress tests; no host connections."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import opsfeast as ops


class ConnectionSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'hosts.yaml').write_text('''hosts:
  a:
    group: [web, mixed]
    connection: {hostname: 192.0.2.1, user: operator, allow_agent: true}
  b:
    group: [web]
    connection: {hostname: 192.0.2.2, user: operator, allow_agent: true}
  disabled:
    enabled: false
    group: [web]
    connection: {hostname: 192.0.2.3}
''')

    def invoke(self, *flags, tty=False, fail_first=False):
        output, errors = io.StringIO(), io.StringIO()
        output.isatty = lambda: tty
        sessions = []
        def create():
            local, remote = Mock(), Mock()
            remote.exec_command.return_value = ('synthetic', '', 0)
            if fail_first and not sessions:
                local.connect.side_effect = ConnectionRefusedError('private exception text')
            else:
                local.connect.return_value = remote
            sessions.append(local)
            return local
        cls = Mock(side_effect=create)
        cls.resolve_connection.side_effect = lambda host, username=None, port=None, ssh_config=None, **kw: dict(hostname=host, username=username, port=port or 22, **kw)
        with patch.object(ops, 'load_session_class', return_value=cls), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = ops.main(['test-connection', '--root', str(self.root), *flags])
        return code, output.getvalue(), errors.getvalue(), sessions

    def test_all_non_tty_json_and_disabled_exclusion(self):
        code, out, err, sessions = self.invoke('--all')
        report = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([item['host'] for item in report['hosts']], ['a', 'b'])
        self.assertEqual(report['excluded_hosts'], [{'host': 'disabled', 'reason_code': 'host_disabled'}])
        self.assertEqual(report['counts'], {'total': 2, 'passed': 2, 'failed': 0, 'skipped': 0})
        self.assertEqual(err, '')
        self.assertEqual(len(sessions), 2)
        for session in sessions:
            session.close.assert_called_once_with(strict=True)

    def test_group_union_deduplicates(self):
        code, out, _, sessions = self.invoke('--group', 'web', '--group', 'mixed')
        self.assertEqual(code, 0)
        self.assertEqual([item['host'] for item in json.loads(out)['hosts']], ['a', 'b'])
        self.assertEqual(len(sessions), 2)

    def test_failure_continues_other_hosts_and_preserves_reason(self):
        code, out, _, sessions = self.invoke('--all', fail_first=True)
        report = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(report['counts']['failed'], 1)
        self.assertEqual(report['hosts'][0]['error']['reason'], 'connection_refused')
        self.assertTrue(report['hosts'][1]['success'])
        self.assertNotIn('private exception text', out)
        self.assertEqual(len(sessions), 2)

    def test_invalid_selection_fails_before_sessions(self):
        for flags in [(), ('--all', '--group', 'web'), ('a', '--all'),
                      ('--group', 'web', 'unknown'), ('missing',),
                      ('a', '--quiet', '--debug')]:
            with self.subTest(flags=flags):
                code, _, _, sessions = self.invoke(*flags)
                self.assertEqual(code, 1)
                self.assertEqual(sessions, [])

    def test_explicit_disabled_host_skips(self):
        code, out, _, sessions = self.invoke('disabled')
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)['reason_code'], 'host_disabled')
        self.assertEqual(sessions, [])

    def test_single_host_keeps_json_shape(self):
        code, out, _, _ = self.invoke('a')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['host'], 'a')
        self.assertNotIn('hosts', json.loads(out))

    def test_terminal_progress_and_table(self):
        code, out, err, _ = self.invoke('--all', tty=True)
        self.assertEqual(code, 0)
        self.assertIn('PASS', out)
        self.assertIn('host_disabled', out)
        self.assertIn('[1/2]', err)
        self.assertIn('executing hostname', err)
        self.assertIn('[2/2]', err)

    def test_terminal_quiet_and_explicit_json(self):
        code, out, err, _ = self.invoke('a', '--quiet', '--json', tty=True)
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)['success'])
        self.assertEqual(err, '')

    def test_redirected_verbose(self):
        code, out, err, _ = self.invoke('--all', '--verbose', '--json')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['status'], 'success')
        self.assertIn('connecting', err)

    def test_host_group_union_and_profile(self):
        with patch.object(ops, 'resolve_root', return_value=self.root) as resolve:
            code, out, _, sessions = self.invoke('a', '--group', 'web', '--profile', 'synthetic')
        self.assertEqual(code, 0)
        self.assertEqual(len(sessions), 2)
        self.assertEqual(len(json.loads(out)['hosts']), 2)
        self.assertEqual(resolve.call_args.args[1], 'synthetic')

    def test_batch_timeout_and_host_init_forwarded(self):
        def report(root, host, timeout, verbose, debug, traceback, init, json_output, **kw):
            self.assertEqual(timeout, 7)
            self.assertTrue(init)
            return {'host': host, 'connected': True, 'success': True, 'commands': [], 'hops': [],
                    'host_init': {'status': 'success'}}
        with patch.object(ops, 'test_connection', side_effect=report) as probe:
            code, out, _, _ = self.invoke('--all', '--timeout', '7', '--host-init')
        self.assertEqual(code, 0)
        self.assertEqual(probe.call_count, 2)
        self.assertTrue(all(item['host_init']['status'] == 'success' for item in json.loads(out)['hosts']))

    def test_conflicting_roots_before_sessions(self):
        code, _, _, sessions = self.invoke('a', str(self.root))
        self.assertEqual(code, 1)
        self.assertEqual(sessions, [])
