"""Real local proxy children and synthetic connection routes; no SSH/credentials."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import opsfeast as ops
import host_runtime
import process_environment as environment
from management_view import masked

PROBE = """import json, os, sys
print(json.dumps({'color': os.environ.get('NO_COLOR'), 'probe': os.environ.get('PROBE'),
 'path': os.environ.get('PATH'), 'input': sys.stdin.read(), 'pid': os.getpid()}))
"""


class ProcessEnvironmentTests(unittest.TestCase):
    def command(self, code=PROBE):
        return shlex.join([sys.executable, '-I', '-B', '-c', code])

    def run_child(self, overrides, ambient=None):
        receipt = {}
        settings = {'proxy_command': self.command(), 'proxy_environment': overrides}
        with patch.dict(os.environ, ambient or {}, clear=True):
            before = dict(os.environ)
            with environment.proxy_options(settings, receipt) as prepared:
                argv = shlex.split(prepared['proxy_command'])
                if argv != shlex.split(settings['proxy_command']):
                    material = Path(argv[-1])
                    self.assertEqual(stat.S_IMODE(material.stat().st_mode), 0o600)
                    self.assertNotIn('synthetic-sensitive', prepared['proxy_command'])
                process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True)
                try:
                    out, err = process.communicate('input preserved', timeout=10)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                self.assertEqual(process.returncode, 0, err)
                self.assertEqual(err, '')
                data = json.loads(out)
                self.assertEqual(data['pid'], process.pid)  # exec, no orphan worker.
            self.assertEqual(dict(os.environ), before)
        return data, receipt

    def test_no_color_absent_empty_presence_and_explicit_values(self):
        for ambient, expected in (({}, None), ({'NO_COLOR': ''}, None),
                                  ({'NO_COLOR': '1'}, 'true'), ({'NO_COLOR': 'true'}, 'true'),
                                  ({'NO_COLOR': '0'}, 'true'), ({'NO_COLOR': 'unexpected'}, 'true')):
            with self.subTest(ambient=ambient):
                child, receipt = self.run_child({}, ambient)
                self.assertEqual(child['color'], expected)
                self.assertEqual(child['input'], 'input preserved')
                self.assertEqual(receipt['proxy_environment']['ambient_presence']['NO_COLOR'], bool(ambient))
        for override in ('false', '', None, 'custom'):
            child, _ = self.run_child({'NO_COLOR': override}, {'NO_COLOR': '1'})
            self.assertEqual(child['color'], override)

    def test_overrides_removal_path_and_value_free_evidence(self):
        child, receipt = self.run_child({'PROBE': 'synthetic-sensitive'},
                                       {'PATH': '/synthetic/path', 'NO_COLOR': '1'})
        self.assertEqual(child['probe'], 'synthetic-sensitive')
        self.assertEqual(child['path'], '/synthetic/path')
        self.assertNotIn('synthetic-sensitive', json.dumps(receipt))
        self.assertNotIn('/synthetic/path', json.dumps(receipt))
        child, _ = self.run_child({'PROBE': None}, {'PROBE': 'synthetic-sensitive'})
        self.assertIsNone(child['probe'])

    def test_parallel_connections_do_not_mutate_environment(self):
        before = dict(os.environ)
        def run(value):
            receipt = {}
            with environment.proxy_options({'proxy_command': self.command(),
                                            'proxy_environment': {'PROBE': value}}, receipt) as options:
                result = subprocess.run(shlex.split(options['proxy_command']), input='',
                                        capture_output=True, text=True, timeout=10, check=True)
                return json.loads(result.stdout)['probe']
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(run, ('one', 'two', 'three', 'four'))),
                             ['one', 'two', 'three', 'four'])
        self.assertEqual(dict(os.environ), before)

    def test_launch_failure_exit_code_and_secret_redaction(self):
        receipt = {}
        with environment.proxy_options({'proxy_command': '/synthetic/missing-proxy synthetic-sensitive',
                                        'proxy_environment': {'PROBE': 'synthetic-sensitive'}}, receipt) as options:
            argv = shlex.split(options['proxy_command'])
            material = Path(argv[-1])
            result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 126)
            self.assertEqual(result.stdout, '')
            self.assertEqual(result.stderr, 'OpsFeast proxy launch failed\n')
            self.assertFalse(material.exists())
            self.assertNotIn('synthetic-sensitive', json.dumps(receipt))

    def test_parent_removes_launch_file_on_start_failure(self):
        with self.assertRaisesRegex(RuntimeError, 'synthetic failure'):
            with environment.proxy_options({'proxy_command': self.command(),
                                            'proxy_environment': {'PROBE': 'synthetic-sensitive'}}, {}) as options:
                material = Path(shlex.split(options['proxy_command'])[-1])
                self.assertTrue(material.exists())
                raise RuntimeError('synthetic failure')
        self.assertFalse(material.exists())

    def test_actual_sshscript_proxy_failure_closes_child_and_preserves_policy(self):
        from sshscript import Session
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory) / 'child.json'
            code = ("import json, os, sys; "
                    f"open({str(proof)!r}, 'w').write(json.dumps(dict(color=os.environ.get('NO_COLOR'), pid=os.getpid()))); "
                    "sys.stdout.write('fixture is not an SSH server\\r\\n'); sys.stdout.flush()")
            local = Session()
            receipt = {}
            try:
                with patch.dict(os.environ, {'NO_COLOR': '1'}), \
                        environment.proxy_options({'proxy_command': self.command(code)}, receipt) as options:
                    with self.assertRaises(Exception):
                        local.connect('synthetic.invalid', username='synthetic', ssh_config=False,
                                      allow_agent=False, look_for_keys=False, timeout=3,
                                      banner_timeout=3, auth_timeout=3, **options)
                self.assertEqual(json.loads(proof.read_text())['color'], 'true')
            finally:
                local.close(strict=True)
            with self.assertRaises(ProcessLookupError):
                os.kill(json.loads(proof.read_text())['pid'], 0)

    def test_termination_keeps_original_child_ownership(self):
        code = "import time; print('ready', flush=True); time.sleep(30)"
        with environment.proxy_options({'proxy_command': self.command(code),
                                        'proxy_environment': {'PROBE': 'synthetic'}}, {}) as options:
            material = Path(shlex.split(options['proxy_command'])[-1])
            with subprocess.Popen(shlex.split(options['proxy_command']), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True) as process:
                try:
                    self.assertEqual(process.stdout.readline(), 'ready\n')
                    self.assertFalse(material.exists())
                finally:
                    process.terminate()
                    process.communicate(timeout=5)
                self.assertLess(process.returncode, 0)

    def config(self, connection):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / 'hosts.yaml').write_text(yaml.safe_dump({'hosts': {'target': {'connection': connection}}}))
        config = ops.Validator(root)
        config.load(root / 'hosts.yaml')
        config.check_connections()
        return config

    def connection(self, **options):
        return {'hostname': 'example.invalid', 'user': 'operator', 'allow_agent': True,
                'proxy_command': self.command(), **options}

    def session_class(self):
        local, remote = Mock(), Mock()
        remote.exec_command.return_value = ('synthetic', '', 0)
        cls = Mock(return_value=local)
        cls.resolve_connection.side_effect = lambda hostname, username=None, port=None, **kw: {
            'hostname': hostname, 'username': username or 'operator', 'port': port or 22,
            **{k: v for k, v in kw.items() if k != 'ssh_config'}}
        local.connect.return_value = remote
        return cls, local

    def test_invalid_configuration_rejected_without_values(self):
        for invalid in (None, [], {'BAD=NAME': 'synthetic-sensitive'},
                        {'BAD\n': 'synthetic-sensitive'}, {'OK': True}, {'OK': 1},
                        {'OK': []}, {'OK': 'synthetic-sensitive\0'}):
            with self.subTest(invalid=invalid), self.assertRaises(ops.ConfigError) as caught:
                self.config(self.connection(proxy_environment=invalid))
            self.assertNotIn('synthetic-sensitive', str(caught.exception))
        for connection in ({'local': True, 'proxy_environment': {}},
                           {'hostname': 'example.invalid', 'proxy_environment': {}}):
            with self.assertRaises(ops.ConfigError):
                self.config(connection)

    def test_alias_requires_resolved_proxy_and_jump_owns_policy(self):
        cls, _ = self.session_class()
        config = self.config({'ssh_config_alias': 'synthetic', 'allow_agent': True,
                              'proxy_environment': {'PROBE': 'synthetic-sensitive'}})
        with self.assertRaisesRegex(ops.ConfigError, 'resolved proxy'):
            ops.connection_plan(config, 'target', cls)
        cls.resolve_connection.side_effect = lambda *a, **kw: {
            'hostname': 'synthetic', 'username': 'operator', 'port': 22,
            'proxy_command': self.command()}
        hop, = ops.connection_plan(config, 'target', cls)
        self.assertEqual(hop['proxy_environment']['PROBE'], 'synthetic-sensitive')
        cls, _ = self.session_class()
        config = self.config({'hostname': 'target.invalid', 'allow_agent': True,
                              'via': self.connection(proxy_environment={'PROBE': 'synthetic-sensitive'})})
        first, second = ops.connection_plan(config, 'target', cls)
        self.assertIn('proxy_environment', first)
        self.assertNotIn('proxy_environment', second)

    def test_shared_runtime_and_diagnostic_use_same_boundary(self):
        config = self.config(self.connection(proxy_environment={'PROBE': 'synthetic-sensitive'}))
        for diagnostic in (False, True):
            cls, local = self.session_class()
            def connect(*args, **kwargs):
                self.assertNotIn('proxy_environment', kwargs)
                argv = shlex.split(kwargs['proxy_command'])
                self.assertNotIn('synthetic-sensitive', kwargs['proxy_command'])
                result = subprocess.run(argv, input='', capture_output=True, text=True, timeout=10, check=True)
                self.assertEqual(json.loads(result.stdout)['probe'], 'synthetic-sensitive')
                return Mock(exec_command=Mock(return_value=('synthetic', '', 0)))
            local.connect.side_effect = connect
            if diagnostic:
                out, err = io.StringIO(), io.StringIO()
                with patch.object(ops, 'load_session_class', return_value=cls), \
                        contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    report = ops.test_connection(config.root, 'target', 5, debug=True, _report_only=True)
                self.assertNotIn('synthetic-sensitive', out.getvalue() + err.getvalue())
                self.assertTrue(report['success'])
            else:
                report = {}
                with host_runtime.connected(config, 'target', cls, 5, report):
                    pass
            local.close.assert_called_once_with(strict=True)
            self.assertIn('proxy_environment', report['hops'][0])
            self.assertNotIn('synthetic-sensitive', json.dumps(report))

    def test_connect_failure_has_environment_receipt_and_cleanup(self):
        config = self.config(self.connection(proxy_environment={'PROBE': 'synthetic-sensitive'}))
        for diagnostic in (False, True):
            cls, local = self.session_class()
            paths = []
            def fail(*a, **kw):
                paths.append(Path(shlex.split(kw['proxy_command'])[-1]))
                raise TimeoutError('synthetic-sensitive')
            local.connect.side_effect = fail
            if diagnostic:
                with patch.object(ops, 'load_session_class', return_value=cls):
                    report = ops.test_connection(config.root, 'target', 5, _report_only=True)
                self.assertFalse(report['success'])
                self.assertEqual(report['error']['reason'], 'timeout')
                self.assertNotIn('synthetic-sensitive', json.dumps(report))
            else:
                report = {}
                with self.assertRaises(TimeoutError):
                    with host_runtime.connected(config, 'target', cls, 5, report):
                        self.fail('must not yield')
            self.assertIn('proxy_environment', report['hops'][0])
            self.assertTrue(all(not path.exists() for path in paths))
            local.close.assert_called_once_with(strict=True)

    def test_snapshot_masks_every_value_and_readiness_is_value_free(self):
        value = {'connection': {'proxy_environment': {'UNUSUAL_NAME': 'synthetic-sensitive', 'REMOVE': None}}}
        snapshot = masked(value)
        self.assertNotIn('synthetic-sensitive', json.dumps(snapshot))
        self.assertIsNone(snapshot['connection']['proxy_environment']['REMOVE'])
        self.assertEqual(value['connection']['proxy_environment']['UNUSUAL_NAME'], 'synthetic-sensitive')
        with patch.dict(os.environ, {'PATH': 'synthetic-sensitive', 'NO_COLOR': 'synthetic-sensitive'}, clear=True):
            report = environment.inspect_environment()
        self.assertNotIn('synthetic-sensitive', json.dumps(report))

    def test_plain_connections_untouched_and_malformed_command_redacted(self):
        settings = {'hostname': 'example.invalid', 'allow_agent': True}
        receipt = {}
        with environment.proxy_options(settings, receipt) as prepared:
            self.assertEqual(prepared, settings)
        self.assertEqual(receipt, {})
        for command in ("'synthetic-sensitive", '   '):
            with self.assertRaises(ops.ConfigError) as caught:
                with environment.proxy_options({'proxy_command': command}, {}):
                    self.fail('invalid command accepted')
            self.assertNotIn('synthetic-sensitive', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
