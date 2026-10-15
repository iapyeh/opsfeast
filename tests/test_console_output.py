"""TTY/non-TTY presentation with synthetic data; native Sessions are forbidden."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import console_output as console
import opsfeast as ops
import host_runtime as hr
import access_check as access
import recipe_cli
import run_recipe as runner
import check_environment
import recipe_identity
import skill_bundle
import observation_store
from test_host_runtime import FakeConsole


class Terminal(io.StringIO):
    def isatty(self):
        return True


class ConsoleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'hosts.yaml').write_text('''hosts:
  h:
    icon: 🐧
    connection: {local: true}
    users:
      login: {sudo: false}
      user2: {password: synthetic-password}
''')
        for module, name in ((ops, 'load_session_class'), (hr, 'runtime_class'), (access, 'runtime_class')):
            guard = patch.object(module, name, side_effect=AssertionError('native Session forbidden'))
            guard.start()
            self.addCleanup(guard.stop)

    def capture(self, invoke, args, tty=True):
        out = Terminal() if tty else io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = invoke(args)
        return code, out.getvalue()

    def test_shared_policy_and_explicit_json_preserve_original_data(self):
        data = {'id': '001', 'status': 'partial', 'value': None, 'text': '中文\n\x1b[31m'}
        original = json.loads(json.dumps(data))
        for tty, force in ((True, False), (True, True), (False, False), (False, True)):
            out = Terminal() if tty else io.StringIO()
            with contextlib.redirect_stdout(out):
                console.print_report(data, json_output=force)
            if tty and not force:
                self.assertIn('│ field', out.getvalue())
                self.assertIn('001', out.getvalue())
                self.assertNotIn('\x1b', out.getvalue())
                self.assertIn(r'\n', out.getvalue())
            else:
                self.assertEqual(json.loads(out.getvalue()), data)
            self.assertEqual(data, original)

    def test_profiles_and_check_tty_json_and_pipe_contracts(self):
        data = {'profiles': {'synthetic': {'root': str(self.root)}}, 'default_profile': 'synthetic'}
        original = (self.root / 'hosts.yaml').read_bytes()
        for tty in (True, False):
            with patch.object(ops, 'load_profiles', return_value=data):
                code, output = self.capture(ops.main, ['profiles'], tty)
                self.assertEqual(code, 0)
                self.assertIn('│ profile' if tty else 'PROFILE  ROOT', output)
                code, output = self.capture(ops.main, ['profiles', '--json'], tty)
                self.assertEqual(json.loads(output)['profiles'][0]['name'], 'synthetic')
            code, output = self.capture(ops.main, ['check', str(self.root)], tty)
            self.assertEqual(code, 0)
            self.assertIn('🐧 h' if tty else '  h:', output)
            code, output = self.capture(ops.main, ['check', str(self.root), '--json'], tty)
            self.assertEqual(json.loads(output)['hosts'][0]['host'], 'h')
        self.assertEqual((self.root / 'hosts.yaml').read_bytes(), original)
        with patch.object(ops, 'load_profiles', return_value={'profiles': {}, 'default_profile': None}):
            self.assertEqual(json.loads(self.capture(ops.main, ['profiles', '--json'])[1]), {'report_version': '0.1.0', 'profiles': []})

    def test_inspection_and_instance_terminal_summaries(self):
        for flags in ([], ['--json']):
            code, output = self.capture(ops.main, ['inspect-recipe', 'check/identity', *flags])
            self.assertEqual(code, 0)
            self.assertIn('recipes', json.loads(output)) if flags else self.assertIn('│ recipe', output)
        with patch('opsfeast.core.Instance.open') as opened:
            opened.return_value.inspect.return_value = {'status': 'partial', 'identity': {'identity_status': 'placeholder'}}
            code, output = self.capture(ops.main, ['instance', 'inspect'])
            self.assertEqual(code, 1)
            self.assertIn('placeholder', output)
            code, output = self.capture(ops.main, ['instance', 'inspect', '--json'])
            self.assertEqual(json.loads(output)['status'], 'partial')

    def test_diagnostics_keep_su_and_sudo_failures_and_exit_codes_separate(self):
        events = []
        factory = lambda: FakeConsole('login', events, {'root'})
        with patch.object(hr, 'runtime_class', return_value=factory):
            for flags in ([], ['--json']):
                code, output = self.capture(ops.main, ['test-sudo', 'h', 'user2', '--root', str(self.root), *flags])
                self.assertEqual(code, 1)
                if flags:
                    self.assertEqual(json.loads(output)['status'], 'failed')
                else:
                    self.assertRegex(output, r'PASS\s+│ 🐧 h\s+│ su\s+│ 👤 user2')
                    self.assertRegex(output, r'❌ FAIL\s+│ 🐧 h\s+│ sudo\s+│ 👤 user2')
        factory = lambda: FakeConsole('login', events, {'user2'})
        with patch.object(hr, 'runtime_class', return_value=factory):
            code, output = self.capture(ops.main, ['test-sudo', 'h', 'user2', '--root', str(self.root)])
        self.assertEqual(code, 1)
        self.assertRegex(output, r'❌ FAIL\s+│ 🐧 h\s+│ su\s+│ 👤 user2')
        self.assertRegex(output, r'SKIP\s+│ 🐧 h\s+│ sudo\s+│ 👤 user2\s+│ su_failed')

    def test_connection_host_init_and_test_host_table_routing(self):
        class ConnectionConsole(FakeConsole):
            def exec_command(self, *args, **kwargs):
                return 'synthetic-output\n', '', 0
        factory = lambda: ConnectionConsole('login', [])
        with patch.object(ops, 'load_session_class', return_value=factory):
            for tty in (True, False):
                code, output = self.capture(ops.main, ['test-connection', 'h', str(self.root)], tty)
                self.assertEqual(code, 0)
                self.assertIn('│ status', output) if tty else self.assertTrue(json.loads(output)['success'])
                if tty:
                    self.assertIn('synthetic-output', output)
        facts = {'host_id': 'h', 'status': 'success', 'facts': {'os_name': 'synthetic'}, 'selection_source': 'probe'}
        with patch.object(hr, 'initialize_host', return_value=facts):
            code, output = self.capture(ops.main, ['host-init', 'h', '--root', str(self.root)])
            self.assertEqual(code, 0)
            self.assertIn('facts.os_name', output)
            self.assertIn('🐧 h', output)
        with patch.object(hr, 'test_host', return_value={'host': 'h', 'status': 'partial', 'tests': {
                'test-su': {'status': 'skipped', 'reason_code': 'missing_su_password'}}}):
            code, output = self.capture(ops.main, ['test-host', 'h', '--root', str(self.root)])
            self.assertEqual(code, 0)
            self.assertIn('missing_su_password', output)

    def test_missing_table_dependency_fails_before_operational_calls(self):
        with patch.object(console, 'table_formatter', side_effect=ops.ConfigError('missing tabulate')), \
                patch.object(hr, 'initialize_host') as operate:
            code, output = self.capture(ops.main, ['host-init', 'h', '--root', str(self.root)])
            self.assertEqual(code, 1)
            operate.assert_not_called()
            with patch.object(ops, 'use_profile', return_value=0), patch.object(ops, 'detach_profile', return_value=0):
                self.assertEqual(self.capture(ops.main, ['use', 'synthetic'])[0], 0)
                self.assertEqual(self.capture(ops.main, ['detach', 'synthetic'])[0], 0)
        with patch.object(console, 'table_formatter', side_effect=ops.ConfigError('missing tabulate')):
            code, output = self.capture(check_environment.main, [])
            self.assertIn('packages', json.loads(output))  # Readiness remains reportable.

    def test_recipes_lists_show_and_jobs_follow_tty_and_json_policy(self):
        catalog = {'status': 'success', 'sources': [{'name': 'synthetic', 'status': 'available'}],
                   'recipes': [{'reference': 'demo', 'version': '1', 'kind': 'operation', 'title': 'Synthetic',
                                'runnable': True, 'errors': []}]}
        result = {'status': 'success', 'errors': [], 'results': [{'result_id': 'r', 'recipe_id': 'demo',
                  'host_id': 'h', 'status': 'partial', 'completed_at': 'synthetic-time',
                  'identity_quality': 'fallback', 'identity_warnings': ['synthetic warning']}]}
        item = dict(catalog['recipes'][0], description='Synthetic description', contract='0.1', inputs={},
                    dependencies={}, verification={}, availability_evidence='static only', private_extra='must not expand text output')
        with patch.object(recipe_cli, 'resolve_root', return_value=self.root), \
                patch.object(recipe_cli, 'catalog', return_value=catalog), patch.object(recipe_cli, 'results', return_value=result), \
                patch.object(recipe_cli, 'choose', return_value=item), patch.object(recipe_cli.recipe_jobs, 'listing', return_value=['001']):
            for args, key in ((['list'], 'recipes'), (['results', 'list'], 'results'), (['show', 'demo'], 'reference'),
                              (['jobs', 'list'], 'jobs')):
                for tty, force in ((True, False), (True, True), (False, False)):
                    code, output = self.capture(recipe_cli.main, [*args, *(['--json'] if force else [])], tty)
                    self.assertEqual(code, 0)
                    if tty and not force:
                        self.assertIn('╭', output)
                        self.assertNotIn('must not expand', output)
                        if args == ['results', 'list']: self.assertIn('🐧 h', output)
                    elif force or args == ['jobs', 'list']:
                        self.assertIn(key, json.loads(output))
                    elif args == ['list']:
                        self.assertIn('demo | 1 | operation', output)
            self.assertEqual(item['private_extra'], 'must not expand text output')

    def test_execution_and_dryrun_share_tables_without_changing_saved_reports(self):
        report = dict(status='success', reason_code='inventory_complete', message='Synthetic success',
                      detected_kernel='Linux', supported_platforms=['linux'], recipe={'id': 'inventory-system'},
                      retention={'status': 'failed'}, identity={'quality': 'fallback'})
        checked = {'status': 'success', 'hosts': [{'host': 'h', 'connected': True, 'status': 'success',
                   'access': {'connection_identity': {'username': 'login'}, 'sudo': {'status': 'disabled'}}}]}
        before = json.loads(json.dumps(report))
        with patch.object(access, 'check_many', return_value=checked), \
                patch.object(runner, 'run', return_value=(report, self.root / 'synthetic-result.json')) as run:
            for flags in ([], ['--json']):
                code, output = self.capture(runner.main, ['inventory/system', '--host', 'h', '--root', str(self.root), *flags])
                self.assertEqual(code, 1)  # Retention failure cannot become overall success.
                if flags: self.assertEqual(json.loads(output)['retention']['status'], 'failed')
                else:
                    self.assertIn('🐧 h', output)
                    self.assertIn('❌ FAIL', output)
            run.reset_mock()
            code, output = self.capture(runner.main, ['inventory/system', '--host', 'h', '--dryrun', '--root', str(self.root)])
            self.assertEqual(code, 0)
            self.assertIn('connection', output)
            run.assert_not_called()
        self.assertEqual(report, before)

    def test_data_commands_remain_json_on_a_terminal(self):
        code, output = self.capture(ops.main, ['dump', 'hosts.h.connection', str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output), {'local': True})
        with patch.object(recipe_cli, 'resolve_root', return_value=self.root), \
                patch.object(recipe_cli, 'show_result', return_value={'raw': [None, 0, '001']}), \
                patch.object(recipe_cli, 'show_artifact', return_value={'artifact': 'synthetic'}):
            self.assertEqual(json.loads(self.capture(recipe_cli.main, ['results', 'show', 'r'])[1]), {'raw': [None, 0, '001']})
            self.assertEqual(json.loads(self.capture(recipe_cli.main, ['artifact', 'r', 'a'])[1]), {'artifact': 'synthetic'})
        with patch.object(observation_store, 'export', return_value={'records': []}):
            code, output = self.capture(observation_store.main, ['export', '--root', str(self.root)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output), {'records': []})
            code, output = self.capture(observation_store.main, ['export', '--root', str(self.root), '--format', 'csv'])
            self.assertEqual(code, 0)
            self.assertTrue(output.startswith('observation_id,host_id,'))
            self.assertNotIn('╭', output)

    def test_saved_jobs_do_not_persist_the_json_display_flag(self):
        document = {'recipe': 'demo', 'invocation': {'synthetic': True}}
        with patch.object(recipe_cli, 'resolve_root', return_value=self.root), \
                patch.object(recipe_cli.recipe_jobs, 'load', return_value=document), patch.object(recipe_cli, 'execute', return_value=0) as execute:
            self.assertEqual(self.capture(recipe_cli.main, ['jobs', 'run', 'demo', '--json'])[0], 0)
            self.assertEqual(execute.call_args.kwargs, {'json_output': True})
            self.assertEqual(execute.call_args.args[1], document)

    def test_utility_readiness_author_and_skill_reports(self):
        with patch.object(recipe_identity, 'defaults', return_value={'author': {'name': 'Synthetic'}, 'license': 'MIT'}), \
                patch.object(check_environment, 'inspect_environment', return_value={'ready': True, 'packages': {'tabulate': {'ready': True}}}), \
                patch.object(skill_bundle, 'fetch_bundle', return_value=b'synthetic'), \
                patch.object(skill_bundle, 'check', return_value={'status': 'unchanged', 'synthetic': True}):
            for invoke, args in ((check_environment.main, []), (recipe_identity.main, ['defaults']), (skill_bundle.main, ['check'])):
                for flags in ([], ['--json']):
                    code, output = self.capture(invoke, [*args, *flags])
                    self.assertEqual(code, 0)
                    self.assertIsInstance(json.loads(output), dict) if flags else self.assertIn('│ field', output)


if __name__ == '__main__':
    unittest.main()
