"""Configured-account access checks using synthetic SSHScript consoles only."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import access_check as access
import host_runtime as hr
import opsfeast as ops
from test_host_runtime import FakeConsole


class AccountAccessTests(unittest.TestCase):
    def setUp(self):
        for module in (access, hr):
            guard = patch.object(module, 'runtime_class', side_effect=AssertionError('native Session forbidden in synthetic tests'))
            guard.start()
            self.addCleanup(guard.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.events = []
        self.factory = lambda: FakeConsole('login', self.events)
        self.write({'login': {'sudo': False}, 'user2': {'password': 'two-secret', 'sudo': True},
                    'user3': {'password': 'three-secret', 'sudo': False}})

    def write(self, users):
        data = {'hosts': {'h': {'connection': {'local': True}, 'users': users,
                               'vars': {'sudo': {'password': 'host-secret'}}}}}
        (self.root / 'hosts.yaml').write_text(ops.yaml.safe_dump(data, sort_keys=False))

    def run_checks(self, **kwargs):
        return access.check_many(self.root, ['h'], session_class=self.factory, include_users=True, **kwargs)

    def test_su_then_sudo_and_disabled_policy_with_account_progress(self):
        events = []
        report = self.run_checks(progress=lambda stage, item: events.append((stage, item.get('user'))))
        self.assertEqual(report['status'], 'success')
        self.assertEqual([row['user'] for row in report['hosts'][0]['accounts']], ['login', 'user2', 'user3'])
        operations = [e[:3] for e in self.events if e[0] in ('su', 'sudo')]
        self.assertEqual(operations, [('su', 'login', 'user2'), ('sudo', 'user2', 'root'),
                                      ('su', 'login', 'user3')])
        password = next(e[3]['password'] for e in self.events if e[0] == 'sudo')
        self.assertEqual(password, 'two-secret')  # Never borrow the login/host credential.
        self.assertIn(('account_start', 'user2'), events)
        self.assertIn(('account_finish', 'user2'), events)
        self.assertNotIn('secret', json.dumps(report))
        self.assertEqual(list(self.root.iterdir()), [self.root / 'hosts.yaml'])

    def test_su_failure_does_not_sudo_and_other_accounts_continue(self):
        self.factory = lambda: FakeConsole('login', self.events, {'user2'})
        report = self.run_checks()
        accounts = report['hosts'][0]['accounts']
        self.assertEqual([a['status'] for a in accounts], ['success', 'failed', 'success'])
        self.assertEqual(report['status'], 'failed')
        self.assertRegex(access.format_summary(report), r'❌ FAIL\s+│ h\s+│ su\s+│ user2\s+│ su_entry_failed')
        self.assertRegex(access.format_summary(report), r'PASS\s+│ h\s+│ connection\s+│ login\s+│')
        self.assertFalse(any(e[0] == 'sudo' for e in self.events))

    def test_sudo_failure_is_distinct_and_preserves_su_evidence(self):
        self.factory = lambda: FakeConsole('login', self.events, {'root'})
        report = self.run_checks()
        account = report['hosts'][0]['accounts'][1]
        self.assertEqual(account['status'], 'failed')
        self.assertEqual(account['reason_code'], 'sudo_entry_failed')
        step = account['checks']['groups'][0]['steps'][0]
        self.assertTrue(step['su_identity_verification']['matched'])
        self.assertTrue(account['checks']['groups'][0]['parent_identity_verification']['matched'])

    def test_missing_su_password_is_skipped_and_nonzero(self):
        self.write({'login': {'sudo': False}, 'user2': {}})
        with patch.object(access, 'runtime_class', return_value=self.factory), \
                contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            code = ops.main(['check-access', '--all', '--root', str(self.root)])
        self.assertEqual(code, 1)
        self.assertRegex(out.getvalue(), r'SKIP\s+│ h\s+│ su\s+│ user2\s+│ missing_su_password')
        self.assertIn('CHECK  h / user2', err.getvalue())
        self.assertFalse(any(e[0] in ('su', 'sudo') for e in self.events))

    def test_login_sudo_rejection_still_checks_other_accounts(self):
        self.write({'login': {'password': 'login-secret'}, 'user3': {'password': 'three-secret', 'sudo': False}})
        self.factory = lambda: FakeConsole('login', self.events, {'root'})
        report = self.run_checks()
        self.assertEqual([a['status'] for a in report['hosts'][0]['accounts']], ['failed', 'success'])

    def test_failed_login_leaves_declared_accounts_unverified(self):
        def failed():
            raise OSError('secret-error')
        self.factory = failed
        report = self.run_checks()
        self.assertEqual(report['status'], 'failed')
        rows = report['hosts'][0]['accounts']
        self.assertEqual(rows[0]['status'], 'failed')
        self.assertTrue(all(row['reason_code'] == 'login_unavailable' for row in rows[1:]))
        self.assertNotIn('secret', json.dumps(report))

    def test_cleanup_failure_remains_failure_and_does_not_blame_login(self):
        class BadClose(FakeConsole):
            def close(self, strict=False):
                raise RuntimeError('secret-error')
        count = 0
        def factory():
            nonlocal count
            count += 1
            return FakeConsole('login', self.events) if count == 1 else BadClose('login', self.events)
        self.factory = factory
        report = self.run_checks()
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['hosts'][0]['accounts'][0]['status'], 'success')
        self.assertEqual(report['hosts'][0]['accounts'][1]['reason_code'], 'cleanup_failed')
        rows = access.summary_tests(report['hosts'][0])
        self.assertEqual([(r['test'], r['status']) for r in rows if r['user'] == 'user2'],
                         [('su', 'skipped'), ('sudo', 'skipped'), ('cleanup', 'failed')])
        self.assertFalse(any(r['test'] == 'connection' and r['status'] == 'failed' for r in rows))

    def test_inventory_preflight_remains_login_only(self):
        report = access.check_many(self.root, ['h'], session_class=self.factory)
        self.assertEqual(report['status'], 'success')
        self.assertNotIn('accounts', report['hosts'][0])
        self.assertFalse(any(e[0] in ('su', 'sudo') for e in self.events))

    def test_json_quiet_contains_accounts_and_no_progress(self):
        with patch.object(access, 'runtime_class', return_value=self.factory), \
                contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            code = ops.main(['check-access', '--all', '--root', str(self.root), '--json', '--quiet'])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out.getvalue())['hosts'][0]['accounts']), 3)
        self.assertEqual(err.getvalue(), '')

    def test_old_string_sudo_policy_rejected_before_any_connection(self):
        self.write({'login': {'sudo': 'false'}})
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            code = ops.main(['check-access', '--all', '--root', str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn('expected a boolean', err.getvalue())
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(self.events, [])

    def test_each_test_gets_its_own_row_without_duplicate_connections(self):
        report = self.run_checks()
        rows = access.summary_tests(report['hosts'][0])
        self.assertEqual([(r['test'], r['user'], r['status'], r['reason_code']) for r in rows], [
            ('connection', 'login', 'success', ''), ('sudo', 'login', 'skipped', 'sudo_disabled'),
            ('su', 'user2', 'success', ''), ('sudo', 'user2', 'success', ''),
            ('su', 'user3', 'success', ''), ('sudo', 'user3', 'skipped', 'sudo_disabled')])
        before = list(self.events)
        access.format_summary(report)
        self.assertEqual(self.events, before)

    def test_failed_su_skips_sudo_but_failed_sudo_preserves_su_pass(self):
        for failure, expected in [
                ('user2', [('su', 'failed', 'su_entry_failed'), ('sudo', 'skipped', 'su_failed')]),
                ('root', [('su', 'success', ''), ('sudo', 'failed', 'sudo_entry_failed')])]:
            with self.subTest(failure=failure):
                self.factory = lambda: FakeConsole('login', self.events, {failure})
                rows = access.summary_tests(self.run_checks()['hosts'][0])
                self.assertEqual([(r['test'], r['status'], r['reason_code']) for r in rows if r['user'] == 'user2'], expected)

    def test_login_sudo_failure_does_not_relabel_connection(self):
        self.write({'login': {'password': 'login-secret'}})
        self.factory = lambda: FakeConsole('login', self.events, {'root'})
        rows = access.summary_tests(self.run_checks()['hosts'][0])
        self.assertEqual([(r['test'], r['status']) for r in rows], [('connection', 'success'), ('sudo', 'failed')])

    def test_restoration_and_cleanup_failures_have_separate_rows(self):
        report = self.run_checks()['hosts'][0]
        group = report['accounts'][1]['checks']['groups'][0]
        group['parent_identity_verification']['status'] = 'failed'
        group['cleanup_error'] = 'RuntimeError'
        rows = [r for r in access.summary_tests(report) if r['user'] == 'user2']
        self.assertEqual([(r['test'], r['status']) for r in rows],
                         [('su', 'success'), ('sudo', 'success'), ('restoration', 'failed'), ('cleanup', 'failed')])
        report['access']['restoration_verified'] = False
        report['cleanup_error'] = 'RuntimeError'
        rows = [r for r in access.summary_tests(report) if r['user'] == 'login']
        self.assertEqual([(r['test'], r['status']) for r in rows],
                         [('connection', 'success'), ('sudo', 'skipped'), ('restoration', 'failed'), ('cleanup', 'failed')])

    def test_missing_su_credentials_never_become_pass(self):
        self.write({'login': {'sudo': False}, 'user2': {}})
        rows = [r for r in access.summary_tests(self.run_checks()['hosts'][0]) if r['user'] == 'user2']
        self.assertEqual([(r['test'], r['status'], r['reason_code']) for r in rows],
                         [('su', 'skipped', 'missing_su_password'), ('sudo', 'skipped', 'su_failed')])


if __name__ == '__main__':
    unittest.main()
