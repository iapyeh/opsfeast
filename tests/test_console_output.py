"""TTY/non-TTY presentation with synthetic data; native Sessions are forbidden."""
from recipe_test_support import recipe_main
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
import observation_results
import recipe_runner as runner
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
            code, output = self.capture(ops.main, ['inspect-recipe', 'system/account/check/identity', *flags])
            self.assertEqual(code, 0)
            self.assertIn('recipes', json.loads(output)) if flags else self.assertIn('│ recipe', output)
        with patch('opsfeast.core.Instance.open') as opened:
            opened.return_value.inspect.return_value = {'status': 'partial', 'identity': {'identity_status': 'placeholder'}}
            code, output = self.capture(ops.main, ['instance', 'inspect'])
            self.assertEqual(code, 1)
            self.assertIn('placeholder', output)
            code, output = self.capture(ops.main, ['instance', 'inspect', '--json'])
            self.assertEqual(json.loads(output)['status'], 'partial')

    def test_check_tty_groups_users_primary_disabled_and_empty_groups(self):
        (self.root / 'hosts.yaml').write_text('''groups:
  backup:
    label: BACKUP-SERVERS
    description: Backup files
    icon: {host: 🗂, user: 👩}
    hosts:
      first:
        connection: {hostname: first.invalid, user: operator}
        group: [production, backup]
        users: {root: {}, operator: {password: SYNTHETIC-SECRET}}
      second:
        enabled: false
        connection: {hostname: second.invalid, user: operator}
  production: {}
  empty: {}
hosts:
  solo:
    connection: {hostname: solo.invalid, user: deploy}
''')
        original = (self.root / 'hosts.yaml').read_bytes()
        with patch.object(ops, 'connection_plan', side_effect=AssertionError('no connection planning')):
            code, output = self.capture(ops.main, ['check', str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn('1 YAML files, 3 groups, 3 hosts', output)
        self.assertIn('│ group', output)
        self.assertIn('users', output)
        self.assertLess(output.index('BACKUP-SERVERS (backup)'), output.index('│ empty'))
        self.assertLess(output.index('│ empty'), output.index('│ production'))
        self.assertLess(output.index('│ production'), output.index('Ungrouped (no group)'))
        self.assertIn('Backup files', output)
        first_rows = [line for line in output.splitlines() if '🗂 first' in line]
        self.assertEqual(len(first_rows), 2)
        self.assertIn('(primary)', first_rows[0])
        self.assertNotIn('(primary)', first_rows[1])
        self.assertIn('👩 operator, 👩 root', first_rows[0])
        self.assertIn('🗂 second [disabled]', output)
        self.assertIn('[disabled] = host disabled', output)
        self.assertIn('(no hosts)', output)
        self.assertIn('👤 deploy', output)
        for unwanted in ('selected recipes', 'skipped', 'SYNTHETIC-SECRET', '(login)'):
            self.assertNotIn(unwanted, output)
        self.assertEqual((self.root / 'hosts.yaml').read_bytes(), original)

    def test_check_tty_alias_login_is_unresolved_and_declared_users_are_listed(self):
        (self.root / 'hosts.yaml').write_text('''hosts:
  alias:
    connection: {ssh_config_alias: synthetic-alias}
    users: {declared: {password: SYNTHETIC-SECRET}}
''')
        with patch.object(ops, 'connection_plan', side_effect=AssertionError('no alias resolution')):
            code, output = self.capture(ops.main, ['check', str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn('login unresolved, 👤 declared', output)
        self.assertNotIn('SYNTHETIC-SECRET', output)
        self.assertNotIn('declared (login)', output)

    def test_check_tty_sorts_by_group_id_rather_than_label(self):
        (self.root / 'hosts.yaml').write_text('''groups:
  z: {label: AAA}
  a: {label: ZZZ}
''')
        code, output = self.capture(ops.main, ['check', str(self.root)])
        self.assertEqual(code, 0)
        self.assertLess(output.index('ZZZ (a)'), output.index('AAA (z)'))

    def test_check_json_and_pipe_keep_detailed_recipe_contracts(self):
        (self.root / 'hosts.yaml').write_text('''recipe_sources:
  community: {path: ./uninstalled, enabled: false}
groups:
  backup: {}
hosts:
  h:
    connection: {local: true}
    group: backup
    recipes: [community:example]
''')
        expected = {'report_version': '0.1.0', 'status': 'success', 'yaml_files': 1,
                    'hosts': [{'host': 'h', 'selected_recipes': 0,
                               'skipped': [{'reference': 'community:example', 'source': 'community',
                                            'status': 'skipped', 'reason_code': 'source_disabled'}]}],
                    'notes': []}
        for tty in (True, False):
            code, output = self.capture(ops.main, ['check', str(self.root), '--json'], tty)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output), expected)
        code, output = self.capture(ops.main, ['check', str(self.root)], False)
        self.assertEqual(code, 0)
        self.assertEqual(output, 'OK: 1 YAML files, 1 hosts; configuration checks passed.\n'
                         '  h: 0 selected recipes\n'
                         '    skipped community:example: source_disabled\n'
                         'No SSH connection or recipe execution performed; platform, authentication and full recipe contracts are not validated.\n')
        code, output = self.capture(ops.main, ['check', str(self.root)])
        self.assertEqual(code, 0)
        self.assertNotIn('selected recipes', output)
        self.assertNotIn('source_disabled', output)

    def test_check_tty_still_rejects_invalid_recipes_and_handles_empty_catalog(self):
        (self.root / 'hosts.yaml').write_text('hosts: {h: {connection: {local: true}, recipes: [{recipe: ./missing}]}}')
        code, output = self.capture(ops.main, ['check', str(self.root)])
        self.assertEqual(code, 1)
        self.assertNotIn('configuration checks passed', output)
        (self.root / 'hosts.yaml').write_text('hosts: {}')
        code, output = self.capture(ops.main, ['check', str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn('0 groups, 0 hosts', output)
        self.assertIn('│ group', output)

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
                  'host_id': None, 'status': 'partial', 'completed_at': 'synthetic-time',
                  'collection_user': None, 'identity_quality': None, 'identity_warnings': ['synthetic warning']}]}
        item = dict(catalog['recipes'][0], description='Synthetic description', contract='0.1', inputs={},
                    dependencies={}, verification={}, consumers=[], availability_evidence='static only', private_extra='must not expand text output')
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
                        if args == ['results', 'list']:
                            self.assertIn('partial', output)
                            self.assertIn('unknown', output)
                            self.assertNotIn('identity quality', output)
                            self.assertNotIn('fallback', output)
                            self.assertNotIn('warnings', output)
                            self.assertNotIn('synthetic warning', output)
                    elif force or args == ['jobs', 'list']:
                        self.assertIn(key, json.loads(output))
                        if args == ['results', 'list']:
                            self.assertEqual(json.loads(output), result)
                    elif args == ['list']:
                        self.assertIn('demo | 1 | operation', output)
                    elif args == ['results', 'list']:
                        self.assertIn('synthetic warning', output)
            exported = self.root / 'results.html'
            code, output = self.capture(recipe_cli.main, ['results', 'list', '--html', str(exported)])
            self.assertEqual(code, 0)
            self.assertIn('synthetic warning', exported.read_text())
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
                code, output = self.capture(recipe_main, ['system/inventory/overview', '--host', 'h', '--root', str(self.root), *flags])
                self.assertEqual(code, 1)  # Retention failure cannot become overall success.
                if flags: self.assertEqual(json.loads(output)['retention']['status'], 'failed')
                else:
                    self.assertIn('🐧 h', output)
                    self.assertIn('❌ FAIL', output)
            run.reset_mock()
            code, output = self.capture(ops.main, ['check-access', '--host', 'h', '--quiet', '--root', str(self.root)])
            self.assertEqual(code, 0)
            self.assertIn('connection', output)
            run.assert_not_called()
        self.assertEqual(report, before)

    def test_execution_summary_includes_result_id_and_verified_collection_actor(self):
        report = {'hosts': [
            {'host': 'h', 'status': 'success', 'result_path': '/private/long-result.json',
             'access': {'actual_identity': {'username': 'root', 'effective_uid': 0},
                        'shell_identity': {'username': 'login', 'effective_uid': 501}},
             'data': {'private_extra': 'must-not-print'}},
            {'host': 'ordinary', 'status': 'partial', 'reason_code': 'incomplete',
             'access': {'actual_identity': {'username': 'operator', 'effective_uid': 1000}}},
            {'host': 'broken', 'status': 'failed', 'error': 'RuntimeError'},
            {'host': 'fallback', 'status': 'success',
             'access': {'actual_identity': {'username': 'operator', 'effective_uid': 1000}, 'degraded': True}}
        ], 'excluded_hosts': [{'host': 'disabled', 'reason_code': 'host_disabled'}],
            'counts': {'root': 1}}
        before = json.loads(json.dumps(report))
        with patch.object(console, 'table', wraps=console.table) as render:
            output = console.execution(report, {'h': '🐧'})
        self.assertEqual(render.call_args.args[0], ['host', 'collection identity', 'result', 'result id'])
        self.assertEqual(len(render.call_args.args[1]), 5)
        for value in ('🐧 h', 'root (uid=0)', 'operator (uid=1000)', 'PARTIAL (incomplete)',
                      'RuntimeError', 'unknown', 'SKIP (host_disabled)', 'fallback_user'):
            self.assertIn(value, output)
        for value in ('/private/', 'must-not-print', 'access.', 'shell_identity', 'counts', '│ field'):
            self.assertNotIn(value, output)
        for tty, force in ((True, True), (False, False)):
            stream = Terminal() if tty else io.StringIO()
            with contextlib.redirect_stdout(stream):
                console.print_report(report, kind='execution', json_output=force)
            self.assertEqual(json.loads(stream.getvalue()), before)
        self.assertEqual(report, before)

    def test_completion_ids_match_saved_browser_and_resolve_without_changing_json(self):
        from recipe_reports import results, result_path
        directory=self.root/'observations'
        directory.mkdir()
        path=directory/'synthetic.json'
        path.write_text(json.dumps({'host_id':'h','status':'failed','recipe':{'id':'inventory-system'}}))
        report={'hosts':[{'host':'h','status':'failed','reason_code':'collection_failed','result_path':str(path)},
                         {'host':'unsaved','status':'failed'}],
                'excluded_hosts':[{'host':'disabled','reason_code':'host_disabled'}]}
        expected=results(self.root)['results'][0]['short_id']
        before=json.loads(json.dumps(report))
        with patch.object(console,'table',wraps=console.table) as render:
            console.execution(report,result_root=self.root)
        rows=render.call_args.args[1]
        self.assertEqual([row[-1] for row in rows],[expected,'-','-'])
        self.assertEqual(result_path(self.root,expected),path)
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):
            console.print_report(report,kind='execution',json_output=True,result_root=self.root)
        self.assertEqual(json.loads(stream.getvalue()),before)
        self.assertEqual(report,before)
        raw=json.loads(path.read_text())
        with patch.object(runner,'run',return_value=(raw,path)):
            code,output=self.capture(ops.main,['recipes','run','system/inventory/overview',
                                             '--host','h','--root',str(self.root)])
        self.assertEqual(code,1)
        self.assertIn('result id',output)
        self.assertIn(expected,output)
        code,output=self.capture(observation_results.main,[expected,'--detail','--root',str(self.root)])
        self.assertEqual(code,0)
        self.assertIn('host_id: h',output)

    def test_saved_results_can_be_selected_by_host_then_viewed_offline(self):
        directory = self.root / 'observations'
        directory.mkdir()
        for host in ('h', 'other'):
            document = {'host_id': host, 'status': 'success', 'recipe': {'id': 'inventory-system'},
                        'access': {'actual_identity': {'username': 'root', 'effective_uid': 0}}}
            (directory / (host + '.json')).write_text(json.dumps(document))
        code, output = self.capture(observation_results.main, ['--host', 'h',
                                   '--root', str(self.root), '--json'])
        self.assertEqual(code, 0)
        result, = json.loads(output)['results']
        self.assertEqual(result['host_id'], 'h')
        code, output = self.capture(observation_results.main, [result['result_id'], '--raw',
                                   '--root', str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)['host_id'], 'h')
        self.assertEqual(json.loads(output)['access']['actual_identity']['effective_uid'], 0)

    def test_results_detail_is_vertical_on_tty_and_pipe_without_table_dependency(self):
        directory = self.root / 'observations'
        directory.mkdir()
        identifier = 'observations/' + 'long-result-name-' * 8 + '.json'
        document = {'host_id': 'h', 'status': 'success', 'recipe': {'id': 'inventory-system'},
                    'access': {'actual_identity': {'username': 'root', 'effective_uid': 0}},
                    'text': 'line1\nline2\x1b[31m', 'empty': None, 'leading': '001'}
        (self.root / identifier).write_text(json.dumps(document))
        with patch.object(console, 'table_formatter', side_effect=AssertionError('no tables needed')):
            for tty in (True, False):
                for extra in ([], [identifier]):
                    code, output = self.capture(observation_results.main, ['--detail', *extra,
                                               '--root', str(self.root)], tty)
                    self.assertEqual(code, 0)
                    self.assertIn('result_id: ' + identifier, output)
                    self.assertIn('host_id: h', output)
                    self.assertNotIn('╭', output)
                    if extra:
                        self.assertIn('access.actual_identity.effective_uid: 0', output)
                        self.assertIn('empty: null', output)
                        self.assertIn('leading: 001', output)
                        self.assertIn(r'text: line1\nline2\u001b[31m', output)
                        self.assertNotIn('\x1b', output)
                code, output = self.capture(observation_results.main, [identifier, '--detail',
                                           '--root', str(self.root), '--json'], tty)
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(output), document)

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
