"""Synthetic ESXi identity adapter tests; no hosts or native sessions."""
import contextlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import access_check as access
import host_runtime as hr
import opsfeast as ops


def result(stdout='', exitcode=0, **kwargs):
    return SimpleNamespace(stdout=stdout, stderr='', exitcode=exitcode, **kwargs)


class EsxiSession:
    def __init__(self, *, kernel='VMkernel', uid=0, name='root', expected=0, payload=None,
                 first_python=0, second_python=0, truncated=False, id_exitcode=127, id_stderr=''):
        self.kernel, self.uid, self.name, self.expected = kernel, uid, name, expected
        self.payload, self.first_python, self.second_python = payload, first_python, second_python
        self.truncated = truncated
        self.id_exitcode, self.id_stderr = id_exitcode, id_stderr
        self.calls = []
        self.closed = False

    def exec_command(self, argv, **kwargs):
        self.calls.append(list(argv))
        if argv == ['id', '-un']:
            value = result(exitcode=self.id_exitcode)
            value.stderr = self.id_stderr
            return value
        if argv == ['uname', '-s']:
            return result(self.kernel+'\n')
        if argv[0] in ('/bin/python', '/bin/python3'):
            code = self.first_python if argv[0] == '/bin/python' else self.second_python
            data = {'actual': {'username': self.name, 'effective_uid': self.uid},
                    'expected_uid': self.expected if len(argv) == 5 else None}
            return result(self.payload if self.payload is not None else json.dumps(data), code,
                          stdout_truncated=self.truncated)
        raise AssertionError('unexpected probe')

    def __call__(self, text, **kwargs):
        return self.exec_command(shlex.split(text), **kwargs)

    def close(self, strict=False):
        self.closed = strict

    def sudo(self, **kwargs):
        raise AssertionError('verified root must not invoke sudo')


class EsxiIdentityTests(unittest.TestCase):
    def test_effective_uid_backend_and_finite_readonly_command(self):
        session = EsxiSession()
        evidence = {}
        self.assertEqual(hr.identity(session, 7, evidence=evidence), {'username': 'root', 'effective_uid': 0})
        self.assertEqual(evidence, {'source': 'esxi_python', 'status': 'success',
                                    'interpreter': '/bin/python', 'id_exitcode': 127, 'platform': 'esxi'})
        self.assertEqual(session.calls[:2], [['id', '-un'], ['uname', '-s']])
        self.assertEqual(session.calls[2][:3], ['/bin/python', '-B', '-c'])
        # Run the actual portable probe with the test interpreter and an OS-derived expected identity.
        import os, pwd
        name = pwd.getpwuid(os.geteuid()).pw_name
        completed = subprocess.run([sys.executable, '-B', '-c', hr._ESXI_IDENTITY, name],
                                   check=True, capture_output=True, text=True, timeout=5)
        data = json.loads(completed.stdout)
        self.assertEqual(data['actual']['effective_uid'], os.geteuid())
        self.assertEqual(data['expected_uid'], os.geteuid())

    def test_nonroot_uid_is_preserved_and_environment_name_is_not_used(self):
        self.assertEqual(hr.identity(EsxiSession(uid=1001, name='operator'), 5),
                         {'username': 'operator', 'effective_uid': 1001})

    def test_missing_id_ssh_exec_exit_two_uses_verified_esxi_backend(self):
        session = EsxiSession(id_exitcode=2, id_stderr='sh: exec: line 1: id: not found\n')
        evidence = {}
        self.assertEqual(hr.identity(session, 5, evidence=evidence), {'username': 'root', 'effective_uid': 0})
        self.assertEqual(evidence['id_exitcode'], 2)
        self.assertEqual(evidence['source'], 'esxi_python')
        self.assertEqual(session.calls[1], ['uname', '-s'])

    def test_exit_two_fallback_rejects_other_errors_truncation_and_other_kernels(self):
        for error in ('permission denied', 'id: invalid option', 'prefix id: not found',
                      'sh: exec: line 1: id: not found\nextra'):
            session = EsxiSession(id_exitcode=2, id_stderr=error)
            with self.subTest(error=error), self.assertRaises(RuntimeError):
                hr.identity(session, 5)
            self.assertEqual(len(session.calls), 1)
        missing = result(exitcode=2, stderr_truncated=True)
        missing.stderr = 'sh: exec: line 1: id: not found\n'
        self.assertFalse(hr._missing_id(missing))
        missing = result(stdout='unexpected output', exitcode=2)
        missing.stderr = 'sh: exec: line 1: id: not found\n'
        self.assertFalse(hr._missing_id(missing))
        session = EsxiSession(kernel='Linux', id_exitcode=2, id_stderr='sh: exec: line 1: id: not found\n')
        with self.assertRaises(hr.IdentityProbeError):
            hr.identity(session, 5)
        self.assertFalse(any('python' in call[0] for call in session.calls))

    def test_mismatch_retains_observed_actor_expected_uid_and_blocks_sudo(self):
        from types import SimpleNamespace
        cfg = SimpleNamespace(hosts={'synthetic': {'connection': {'user': 'operator'},
                             'users': {'operator': {'sudo': False}}}})
        session = EsxiSession(expected=1000)
        report = {}
        with self.assertRaises(hr.IdentityProbeError) as error:
            with access.collection_actor(session, cfg, 'synthetic', 5, report):
                self.fail('mismatched configured account must not execute a body')
        self.assertEqual(error.exception.reason_code, 'identity_mismatch')
        self.assertEqual(report['actual_identity'], {'username': 'root', 'effective_uid': 0})
        self.assertNotIn('connection_identity', report)
        self.assertNotIn('sudo', report)
        probe = report['configured_identity_probe']
        self.assertEqual(probe['actual'], {'username': 'root', 'effective_uid': 0})
        self.assertEqual(probe['expected'], {'username': 'operator', 'effective_uid': 1000})
        self.assertIs(probe['matched'], False)

    def test_authenticated_esxi_login_accepts_root_shell_without_matching_account_uid(self):
        report = {}
        shell = hr.verify_connection_identity(EsxiSession(expected=1000), 5, report,
            authenticated_user='operator', configured_user='operator')
        self.assertEqual(shell, {'username': 'root', 'effective_uid': 0})
        self.assertEqual(report['login_identity'], {'username': 'operator', 'source': 'ssh_connection'})
        self.assertEqual(report['shell_identity'], shell)
        self.assertEqual(report['identity_model'], 'esxi_root_shell')
        probe = report['configured_identity_probe']
        self.assertIs(probe['matched'], False)  # Numeric UIDs still differ.
        self.assertEqual(probe['status'], 'success')
        self.assertEqual(probe['accepted_by'], 'esxi_root_shell')
        self.assertNotIn('reason_code', probe)
        self.assertEqual(probe['expected']['effective_uid'], 1000)

    def test_esxi_mapping_requires_authentication_root_uid_and_matching_principal(self):
        for authenticated, configured, uid in ((None, 'operator', 0),
                ('operator', 'operator', 1001), ('unexpected', 'operator', 0)):
            report = {}
            with self.subTest(authenticated=authenticated, uid=uid), self.assertRaises(hr.IdentityProbeError):
                hr.verify_connection_identity(EsxiSession(uid=uid, expected=1000), 5, report,
                    authenticated_user=authenticated, configured_user=configured)
            self.assertNotIn('connection_identity', report)

    def test_working_id_requires_independent_vm_kernel_confirmation_for_mapping(self):
        class IdSession(EsxiSession):
            def exec_command(self, argv, **options):
                if argv == ['id', '-un']:
                    return result('root\n')
                if argv == ['id', '-u']:
                    return result('0\n')
                if argv == ['id', '-u', 'operator']:
                    return result(str(self.expected) + '\n')
                return super().exec_command(argv, **options)
        for kernel in ('VMkernel', 'Linux', 'Darwin', 'VMkernel\nextra'):
            report = {}
            session = IdSession(kernel=kernel, expected=1000)
            with self.subTest(kernel=kernel):
                if kernel == 'VMkernel':
                    hr.verify_connection_identity(session, 5, report,
                        authenticated_user='operator', configured_user='operator')
                    self.assertEqual(report['identity_model'], 'esxi_root_shell')
                    self.assertEqual(report['identity_platform_probe']['kernel'], 'VMkernel')
                else:
                    with self.assertRaises(hr.IdentityProbeError):
                        hr.verify_connection_identity(session, 5, report,
                            authenticated_user='operator', configured_user='operator')
                    self.assertNotIn('connection_identity', report)
        for invalid_uid in ('unknown', '-1', ''):
            report = {}
            with self.subTest(invalid_uid=invalid_uid), self.assertRaises((hr.IdentityProbeError, ValueError)):
                hr.verify_connection_identity(IdSession(expected=invalid_uid), 5, report,
                    authenticated_user='operator', configured_user='operator')
            self.assertNotIn('connection_identity', report)

    def remote_config(self, root):
        (root / 'hosts.yaml').write_text('''hosts:
  jump:
    connection: {hostname: jump.invalid, user: bridge, allow_agent: true}
  h:
    connection: {hostname: target.invalid, user: operator, allow_agent: true, via: {host: jump}}
    users:
      operator: {sudo: false, password: synthetic-only}
''')
        return ops.Validator(root).check()

    def remote_factory(self, session):
        session.connect = Mock(return_value=session)
        factory = Mock(return_value=session)
        factory.resolve_connection.side_effect = lambda host, username=None, port=None, ssh_config=None, **kw: dict(
            hostname=host, username=username, port=port or 22, **kw)
        return factory

    def test_access_final_hop_principal_policy_and_no_duplicate_su(self):
        with tempfile.TemporaryDirectory() as folder:
            config = self.remote_config(Path(folder))
            session = EsxiSession(expected=1000)
            factory = self.remote_factory(session)
            with patch.object(access, 'privilege_test', side_effect=AssertionError('login must not be tested as an extra user')), \
                    patch.object(access, 'sudo_settings', wraps=access.sudo_settings) as policy:
                report = access.check_host_accounts(config, 'h', session_class=factory)
            self.assertEqual(report['status'], 'success')
            self.assertEqual(report['login_identity']['username'], 'operator')
            self.assertEqual([c.kwargs['username'] for c in session.connect.call_args_list], ['bridge', 'operator'])
            self.assertEqual(len(report['accounts']), 1)
            self.assertEqual(report['accounts'][0]['user'], 'operator')
            self.assertEqual(report['access']['sudo']['status'], 'not_needed')
            policy.assert_called_once_with(config, 'h', 'operator')
            rows = access.summary_tests(report)
            self.assertEqual([(r['test'], r['user'], r['status']) for r in rows],
                             [('connection', 'operator', 'success'), ('identity', 'operator', 'success'),
                              ('sudo', 'operator', 'skipped')])
            self.assertIn('uid=0 (ESXi)', rows[1]['reason_code'])
            self.assertEqual(rows[2]['reason_code'], 'already_root')
            self.assertTrue(session.closed)

    def test_core_policy_stays_bound_to_authenticated_login(self):
        from opsfeast import Instance, CoreError
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.remote_config(root)
            profile = Instance.open(root).profile(root=root)
            session = EsxiSession(expected=1000)
            with profile.sessions._connect('h', session_class=self.remote_factory(session)) as recipe:
                with self.assertRaises(CoreError) as error:
                    with recipe.sudo():
                        self.fail('sudo is disabled for the authenticated operator')
                self.assertEqual(error.exception.code, 'sudo_disabled')
                self.assertEqual(recipe.report['identity_model'], 'esxi_root_shell')
                self.assertEqual(recipe.report['connection_identity']['effective_uid'], 0)
                self.assertEqual(recipe.report['login_identity']['username'], 'operator')
            self.assertTrue(session.closed)

    def test_alias_login_uses_successful_resolved_username(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'hosts.yaml').write_text('''hosts:
  h:
    connection: {ssh_config_alias: synthetic}
    users: {operator: {sudo: false}}
''')
            config = ops.Validator(root).check()
            session = EsxiSession(expected=1000)
            factory = self.remote_factory(session)
            factory.resolve_connection.side_effect = lambda *args, **kw: {
                'hostname': 'target.invalid', 'username': 'operator', 'port': 22,
                'key_filename': '/synthetic/key'}
            with patch.object(access, 'privilege_test', side_effect=AssertionError('must not su to login')):
                report = access.check_host_accounts(config, 'h', session_class=factory)
            self.assertEqual(report['status'], 'success')
            self.assertEqual(report['access']['login_identity']['username'], 'operator')
            self.assertEqual(report['access']['shell_identity']['effective_uid'], 0)
            self.assertEqual(len(report['accounts']), 1)

    def test_fixed_secondary_interpreter_only_when_missing(self):
        session = EsxiSession(first_python=127)
        self.assertEqual(hr.identity(session, 5)['effective_uid'], 0)
        self.assertEqual(session.calls[-1][0], '/bin/python3')
        session = EsxiSession(first_python=1)
        with self.assertRaisesRegex(hr.IdentityProbeError, 'identity_probe_failed'):
            hr.identity(session, 5)
        self.assertFalse(any(call[0] == '/bin/python3' for call in session.calls))

    def test_no_python_fallback_for_other_platforms_or_nonmissing_id(self):
        session = EsxiSession(kernel='Linux')
        with self.assertRaisesRegex(hr.IdentityProbeError, 'identity_tool_missing'):
            hr.identity(session, 5)
        self.assertFalse(any('python' in call[0] for call in session.calls))
        with patch.object(session, 'exec_command', return_value=result(exitcode=1)) as execute:
            with self.assertRaises(RuntimeError):
                hr.identity(session, 5)
            self.assertEqual(execute.call_count, 1)

    def test_absent_interpreters_fail_closed(self):
        evidence = {}
        with self.assertRaisesRegex(hr.IdentityProbeError, 'identity_tool_missing'):
            hr.identity(EsxiSession(first_python=127, second_python=127), 5, evidence=evidence)
        self.assertEqual(evidence['status'], 'failed')
        self.assertEqual(evidence['reason_code'], 'identity_tool_missing')

    def test_reject_invalid_or_truncated_evidence(self):
        payloads = ['secret error text', '{}', '[]', 'null',
                    json.dumps({'actual': {'username': 'root', 'effective_uid': True}, 'expected_uid': None}),
                    json.dumps({'actual': {'username': 'root', 'effective_uid': -1}, 'expected_uid': None}),
                    json.dumps({'actual': {'username': 'root\nextra', 'effective_uid': 0}, 'expected_uid': None}),
                    'x'*4097]
        for payload in payloads:
            with self.subTest(payload=payload[:40]):
                with self.assertRaisesRegex(hr.IdentityProbeError, 'identity_invalid_output') as error:
                    hr.identity(EsxiSession(payload=payload), 5)
                self.assertNotIn('secret', str(error.exception))
        with self.assertRaisesRegex(hr.IdentityProbeError, 'identity_invalid_output'):
            hr.identity(EsxiSession(truncated=True), 5)

    def test_target_uid_match_mismatch_and_console_execution(self):
        for expected in (0, 1001):
            record = hr.identity_check({'username': 'root', 'effective_uid': None})
            session = EsxiSession(expected=expected)
            if expected == 0:
                hr.identity(session, 5, console=True, target='root', verification=record)
                self.assertTrue(record['matched'])
            else:
                with self.assertRaisesRegex(hr.IdentityProbeError, 'identity_mismatch'):
                    hr.identity(session, 5, console=True, target='root', verification=record)
                self.assertFalse(record['matched'])
                self.assertEqual(record['actual']['effective_uid'], 0)
                self.assertEqual(record['expected']['effective_uid'], 1001)
        session = EsxiSession()
        with self.assertRaises(ops.ConfigError):
            hr.identity(session, 5, target='root;unwanted')
        self.assertEqual(session.calls, [])

    def test_check_access_cli_root_and_missing_tools(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'hosts.yaml').write_text('hosts:\n  h:\n    connection: {local: true}\n    users: {root: {sudo: true}}\n')
            for missing in (False, True):
                session = EsxiSession(first_python=127 if missing else 0, second_python=127)
                with patch.object(access, 'runtime_class', return_value=lambda: session), \
                        contextlib.redirect_stdout(io.StringIO()) as out, \
                        contextlib.redirect_stderr(io.StringIO()):
                    code = ops.main(['check-access','--host','h','--root',str(root),'--json','--quiet'])
                report = json.loads(out.getvalue())['hosts'][0]
                self.assertEqual(code, int(missing))
                self.assertTrue(report['connected'])
                self.assertTrue(session.closed)
                rows = access.summary_tests(report)
                self.assertEqual(rows[0]['status'], 'success')
                if missing:
                    self.assertEqual(report['identity_error']['reason_code'], 'identity_tool_missing')
                    self.assertIn({'test': 'identity', 'user': 'unresolved', 'status': 'failed',
                                   'reason_code': 'identity_tool_missing'}, rows)
                else:
                    self.assertEqual(report['access']['sudo']['status'], 'not_needed')
                    self.assertEqual(report['access']['identity_probe']['source'], 'esxi_python')
                    self.assertEqual(report['access']['connection_identity']['effective_uid'], 0)
