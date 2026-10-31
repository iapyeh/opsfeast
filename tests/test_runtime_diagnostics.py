"""Synthetic broken installations; never install packages or connect to hosts."""
import contextlib
from importlib import metadata
import io
import json
from pathlib import Path
import shlex
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import check_environment
import console_output
import host_runtime
import recipe_runner
import sshscript_runtime as runtime
import terminal_ui
from opsfeast import RuntimeEnvironmentError, connection_error, load_session_class


class RuntimeDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.module = SimpleNamespace(__version__='7.0.1', __file__='/synthetic/sshscript/__init__.py',
                                      Session=Mock())
        self.addCleanup(patch.stopall)
        patch.object(runtime, 'import_module', return_value=self.module).start()
        patch.object(metadata, 'version', return_value='7.0.1').start()
        self.distributions = patch.object(metadata, 'distributions', return_value=[]).start()
        self.source = patch.object(runtime, 'source_identity', return_value={'source_matches': True}).start()

    def dist(self, version, suffix='', name='sshscript'):
        path = self.root / f'sshscript-{version}{suffix}.dist-info'
        path.mkdir()
        (path / 'METADATA').write_text(f'Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n')
        return metadata.PathDistribution(path)

    def test_duplicate_metadata_rejected_even_when_selected_versions_match(self):
        old, current = self.dist('7.0.0'), self.dist('7.0.1')
        self.distributions.return_value = [old, current]
        for selected in ('7.0.0', '7.0.1'):
            with self.subTest(selected=selected), patch.object(metadata, 'version', return_value=selected):
                report = runtime.inspect_runtime()
                self.assertFalse(report['ready'])
                self.assertEqual(report['reason'], 'sshscript_duplicate_metadata')
                self.assertEqual({d['version'] for d in report['distributions']}, {'7.0.0', '7.0.1'})
                self.assertTrue(all(d['metadata_path'].startswith(str(self.root)) for d in report['distributions']))
        self.source.assert_not_called()

    def test_same_version_duplicate_and_repeated_search_path(self):
        first = self.dist('7.0.1')
        self.distributions.return_value = [first, first]
        self.assertTrue(runtime.inspect_runtime()['ready'])
        second = self.dist('7.0.1', '-second')
        self.distributions.return_value = [first, second]
        self.assertEqual(runtime.inspect_runtime()['reason'], 'sshscript_duplicate_metadata')

    def test_unrelated_distributions_are_ignored(self):
        self.distributions.return_value = [self.dist('1.0', name='unrelated')]
        self.assertTrue(runtime.inspect_runtime()['ready'])

    def test_import_failure_preserves_available_metadata_without_private_exception(self):
        self.distributions.return_value = [self.dist('7.0.1')]
        with patch.object(runtime, 'import_module', side_effect=ImportError('private-password')):
            report = runtime.inspect_runtime()
        self.assertEqual(report['reason'], 'sshscript_import_failed')
        self.assertEqual(report['distribution_version'], '7.0.1')
        self.assertEqual(report['import_error_type'], 'ImportError')
        self.assertNotIn('private-password', json.dumps(report))

    def test_missing_and_unreadable_metadata(self):
        for error, reason in [(metadata.PackageNotFoundError('sshscript'), 'sshscript_metadata_missing'),
                              (ValueError('private-token'), 'sshscript_metadata_unreadable')]:
            with self.subTest(reason=reason), patch.object(metadata, 'version', side_effect=error):
                report = runtime.inspect_runtime()
                self.assertEqual(report['reason'], reason)
                self.assertEqual(report['import_version'], '7.0.1')
                self.assertNotIn('private-token', json.dumps(report))

    def test_metadata_enumeration_failure_is_not_ready(self):
        self.distributions.side_effect = OSError('private-token')
        report = runtime.inspect_runtime()
        self.assertEqual(report['reason'], 'sshscript_metadata_unreadable')
        self.assertNotIn('private-token', json.dumps(report))

    def test_version_mismatch_and_same_version_source_drift(self):
        self.module.__version__ = '7.0.0'
        self.assertEqual(runtime.inspect_runtime()['reason'], 'sshscript_version_mismatch')
        self.module.__version__ = '7.0.1'
        self.source.return_value = {'source_matches': False}
        self.assertEqual(runtime.inspect_runtime()['reason'], 'sshscript_source_mismatch')

    def test_all_shared_gates_stop_before_session_creation(self):
        self.distributions.return_value = [self.dist('7.0.0'), self.dist('7.0.1')]
        for acquire in (runtime.require_runtime, host_runtime.runtime_class,
                        recipe_runner.load_runtime, load_session_class):
            with self.subTest(acquire=acquire.__name__), self.assertRaises(RuntimeEnvironmentError) as caught:
                acquire()
            self.assertEqual(connection_error(caught.exception)['reason'], 'sshscript_duplicate_metadata')
        self.module.Session.assert_not_called()

    def test_successful_shared_gates_keep_receipts(self):
        self.distributions.return_value = [self.dist('7.0.1')]
        cls, report = recipe_runner.load_runtime()
        self.assertIs(cls, self.module.Session)
        self.assertEqual(report['sshscript_distribution'], '7.0.1')
        self.assertIs(host_runtime.runtime_class(), cls)

    def test_repair_commands_quote_current_interpreter_and_do_not_execute(self):
        self.module.__version__ = '7.0.0'
        interpreter = "/synthetic/it's a venv/bin/python3"
        with patch.object(sys, 'executable', interpreter), patch('subprocess.run') as run:
            report = runtime.inspect_runtime()
        for command in report['repair_commands']:
            self.assertEqual(shlex.split(command)[0], interpreter)
        self.assertIn('sshscript==7.0.1', shlex.split(report['repair_commands'][1]))
        self.assertIn('--no-deps', shlex.split(report['repair_commands'][1]))
        self.assertIn('https://pypi.org/simple', report['repair_commands'][1])
        run.assert_not_called()

    def test_environment_cli_reports_duplicate_and_nonzero(self):
        self.distributions.return_value = [self.dist('7.0.0'), self.dist('7.0.1')]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = check_environment.main(['--json'])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(report['packages']['sshscript']['reason'], 'sshscript_duplicate_metadata')

    def test_host_init_persists_reason_and_shows_it_without_debug(self):
        (self.root / 'hosts.yaml').write_text('hosts:\n  synthetic:\n    connection: {local: true}\n')
        config = host_runtime.load_config(self.root, 'synthetic')
        self.distributions.return_value = [self.dist('7.0.0'), self.dist('7.0.1')]
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            report = host_runtime.initialize_host(config, 'synthetic', refresh=True)
        self.assertFalse(report['connected'])
        self.assertEqual(report['reason_code'], 'sshscript_duplicate_metadata')
        self.assertEqual(json.loads(Path(report['result_path']).read_text())['error'], report['error'])
        self.assertIn('repair_commands', stderr.getvalue())
        self.assertIn('before Session creation', stderr.getvalue())
        rendered = console_output.diagnostic(report)
        for text in ('sshscript_duplicate_metadata', sys.executable, '7.0.0', 'pip uninstall'):
            self.assertIn(text, rendered)
        rows = terminal_ui.report_rows(report)
        self.assertEqual(rows[0][1]['error']['environment'], report['error']['environment'])
        self.module.Session.assert_not_called()

    def test_untrusted_exception_messages_remain_omitted(self):
        for error in (ValueError('private-password'), ImportError('private-password')):
            self.assertNotIn('private-password', json.dumps(connection_error(error)))

    def test_recipe_batch_keeps_runtime_error_in_public_summary(self):
        (self.root / 'hosts.yaml').write_text('hosts:\n  synthetic:\n    connection: {local: true}\n')
        self.module.__version__ = '7.0.0'
        error = RuntimeEnvironmentError(runtime.inspect_runtime())
        invocation = {'targets': [('host', 'synthetic')], 'all': False, 'exclude': [],
                      'vars_file': None, 'threads': 1, 'quiet': True, 'verbose': False,
                      'timeout': 30, 'assignments': []}
        with patch.object(recipe_runner, 'run', side_effect=error), \
                contextlib.redirect_stdout(io.StringIO()) as stdout, \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = recipe_runner.execute_hosts(self.root, 'synthetic-recipe', invocation, json_output=True)
        report = json.loads(stdout.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(report['error']['reason'], 'sshscript_version_mismatch')
        self.assertIn('repair_commands', stderr.getvalue())
        self.assertIn('pip uninstall', console_output.execution(report))

    def test_standalone_connection_preserves_runtime_failure_without_connecting(self):
        import opsfeast
        (self.root / 'hosts.yaml').write_text('hosts:\n  synthetic:\n    connection: {local: true}\n')
        self.module.__version__ = '7.0.0'
        with contextlib.redirect_stdout(io.StringIO()) as stdout, \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = opsfeast.main(['test-connection', 'synthetic', str(self.root), '--json', '--quiet'])
        self.assertEqual(code, 1)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report['error']['reason'], 'sshscript_version_mismatch')
        self.assertFalse(report['connected'])
        self.assertEqual(report['commands'], [])
        self.assertIn('repair_commands', stderr.getvalue())
        self.module.Session.assert_not_called()

    def test_access_check_preserves_same_environment_reason(self):
        import access_check
        (self.root / 'hosts.yaml').write_text('hosts:\n  synthetic:\n    connection: {local: true}\n')
        config = host_runtime.load_config(self.root, 'synthetic')
        self.module.__version__ = '7.0.0'
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            report = access_check.check_access(config, 'synthetic')
        self.assertEqual(report['reason_code'], 'sshscript_version_mismatch')
        self.assertEqual(report['error_type'], 'RuntimeEnvironmentError')
        self.assertIn('repair_commands', stderr.getvalue())
        self.assertFalse(report['connected'])
        self.module.Session.assert_not_called()


if __name__ == '__main__':
    unittest.main()
