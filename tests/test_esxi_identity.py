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
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import access_check as access
import host_runtime as hr
import opsfeast as ops


def result(stdout='', exitcode=0, **kwargs):
    return SimpleNamespace(stdout=stdout, stderr='', exitcode=exitcode, **kwargs)


class EsxiSession:
    def __init__(self, *, kernel='VMkernel', uid=0, name='root', expected=0, payload=None,
                 first_python=0, second_python=0, truncated=False):
        self.kernel, self.uid, self.name, self.expected = kernel, uid, name, expected
        self.payload, self.first_python, self.second_python = payload, first_python, second_python
        self.truncated = truncated
        self.calls = []
        self.closed = False

    def exec_command(self, argv, **kwargs):
        self.calls.append(list(argv))
        if argv == ['id', '-un']:
            return result(exitcode=127)
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
        self.assertEqual(evidence, {'source': 'esxi_python', 'status': 'success', 'interpreter': '/bin/python'})
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
