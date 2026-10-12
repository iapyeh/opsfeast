"""Synthetic platform initialization and su/sudo tests; no host connections."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import host_runtime as hr
import opsfeast as ops
import recipe_dispatch as dispatch
import run_recipe as runner


def result(text='', code=0, **kwargs):
    return SimpleNamespace(stdout=text, stderr='', exitcode=code, **kwargs)


def facts_outputs(kernel='Linux'):
    return [result(kernel+'\n'), result('6.1\n'), result('x86_64\n')] + ([result('ID=ubuntu\nNAME=Ubuntu\nVERSION_ID=24.04\n')] if kernel == 'Linux' else [result('14.2-RELEASE\n')] if kernel == 'FreeBSD' else [result('15.0\n')] if kernel == 'Darwin' else [])


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write({'local': True})

    def write(self, connection, users=None, variables=None):
        self.root.joinpath('hosts.yaml').write_text(yaml.safe_dump({'hosts': {'h': {'connection': connection, 'users': users or {}, 'vars': variables or {}}}}))
        self.config = hr.load_config(self.root, 'h')

    def cls(self, values):
        session = Mock()
        session.exec_command.side_effect = values
        return Mock(return_value=session), session

    def test_cache_refresh_and_failure_history(self):
        cls, session = self.cls(facts_outputs())
        first = hr.initialize_host(self.config, 'h', session_class=cls)
        self.assertEqual(first['facts']['distribution_version'], '24.04')
        self.assertNotIn('os_version', first['facts'])
        second = hr.initialize_host(self.config, 'h', session_class=cls)
        self.assertEqual(second['selection_source'], 'cache')
        self.assertEqual(cls.call_count, 1)
        session.exec_command.side_effect = [TimeoutError('secret')]
        failed = hr.initialize_host(self.config, 'h', session_class=cls, refresh=True)
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['previous_success']['facts'], first['facts'])
        self.assertIsNone(hr.cached_facts(self.config, 'h'))
        self.assertNotIn('secret', json.dumps(failed))
        session.exec_command.side_effect = [TimeoutError('secret')]
        retry = hr.initialize_host(self.config, 'h', session_class=cls, refresh=True)
        self.assertEqual(retry['previous_success'], failed['previous_success'])
        session.exec_command.side_effect = facts_outputs()
        self.assertEqual(hr.initialize_host(self.config, 'h', session_class=cls)['status'], 'success')
        self.assertEqual(cls.call_count, 4)

    def test_target_change_invalidates_cache_and_symlinks_rejected(self):
        cls, _ = self.cls(facts_outputs())
        hr.initialize_host(self.config, 'h', session_class=cls)
        self.write({'hostname': 'synthetic.example', 'user': 'login'})
        self.assertIsNone(hr.cached_facts(self.config, 'h'))
        path = hr.cache_path(self.config, 'h')
        path.unlink()
        path.symlink_to(self.root / 'hosts.yaml')
        with self.assertRaises(ops.ConfigError):
            hr.cached_facts(self.config, 'h')

    def test_partial_facts_supported_and_truncation_rejected(self):
        cls, _ = self.cls([result('Linux\n'), result(code=1), result(code=1), result(code=45)])
        report = hr.initialize_host(self.config, 'h', session_class=cls)
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['fields']['distribution_version'], 'unavailable')
        cls, _ = self.cls([result('Linux\n', stdout_truncated=True)])
        self.assertEqual(hr.initialize_host(self.config, 'h', session_class=cls, refresh=True)['status'], 'failed')

    def test_freebsd_and_macos_versions_not_kernel_versions(self):
        for kernel, platform, version in [('FreeBSD', 'freebsd', '14.2-RELEASE'), ('Darwin', 'macos', '15.0')]:
            cls, _ = self.cls(facts_outputs(kernel))
            report = hr.initialize_host(self.config, 'h', session_class=cls, refresh=True)
            self.assertEqual(report['facts']['os_name'], platform)
            self.assertEqual(report['facts']['os_version'], version)
            self.assertEqual(report['facts']['kernel_release'], '6.1')

    def test_init_cleanup_failure_invalidates_cache(self):
        cls, session = self.cls(facts_outputs())
        session.close.side_effect = RuntimeError('private')
        report = hr.initialize_host(self.config, 'h', session_class=cls)
        self.assertEqual(report['status'], 'failed')
        self.assertIsNone(hr.cached_facts(self.config, 'h'))

    def test_host_connection_failure_skips_all_other_tests(self):
        self.write({'hostname': 'example.invalid', 'user': 'login'})
        cls, session = self.cls([])
        cls.resolve_connection.return_value = {'hostname': 'example.invalid', 'username': 'login', 'port': 22}
        session.connect.side_effect = OSError('secret')
        report = hr.test_host(self.config, 'h', session_class=cls)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['tests']['host-init']['reason_code'], 'connection_failed')
        self.assertFalse((self.root / 'observations').exists())

    def test_host_runs_other_tests_after_init_failure_and_reuses_success(self):
        cls, _ = self.cls([result('node'), result('today')])
        failed = {'status': 'failed', 'reason_code': 'platform_detection_failed'}
        with patch.object(hr, 'initialize_host', return_value=failed), patch.object(hr, 'privilege_test', return_value={'status':'skipped', 'connection_user':'login'}) as privilege:
            report = hr.test_host(self.config, 'h', session_class=cls)
        self.assertEqual(report['status'], 'failed')
        self.assertTrue(privilege.call_args_list[0].kwargs['password_required'])


class FakeConsole:
    uid = {'login':1000, 'user2':1002, 'user3':1003, 'root':0, 'service':1004}
    def __init__(self, name, events, failures=None):
        self.name, self.events, self.failures = name, events, failures or set()
    def __enter__(self):
        if self.name in self.failures:
            raise PermissionError('secret-password')
        self.events.append(('enter', self.name))
        return self
    def __exit__(self, *args):
        self.events.append(('exit', self.name))
    def __call__(self, command, **kwargs):
        import shlex
        return self.exec_command(shlex.split(command), **kwargs)
    def exec_command(self, argv, **kwargs):
        self.events.append(('command', self.name, argv))
        if argv == ['id', '-un']:
            return result(self.name)
        if argv[:2] == ['id', '-u']:
            return result(str(self.uid[argv[2] if len(argv)>2 else self.name]))
        return result('ok')
    def su(self, name, **kwargs):
        self.events.append(('su', self.name, name, kwargs))
        return FakeConsole(name, self.events, self.failures)
    def sudo(self, username='root', **kwargs):
        self.events.append(('sudo', self.name, username, kwargs))
        return FakeConsole(username, self.events, self.failures)
    def close(self, strict=False):
        self.events.append(('close', self.name))


class PrivilegeTests(HostTests):
    def setUp(self):
        super().setUp()
        self.write({'local':True}, {'login': {'password':'login-secret'}, 'user2': {'password':'two-secret'}, 'user3': {'password':'three-secret'}})
        self.events=[]
        self.factory=lambda: FakeConsole('login',self.events)

    def test_sudo_cli_diagnostics_preserve_json_and_omit_secrets(self):
        self.write({'local': True}, {'login': {'password': 'login-secret'}},
                   {'sudo': {'password': 'sudo-secret'}})
        factory = lambda: FakeConsole('login', self.events, {'root'})
        for flags in ([], ['--verbose'], ['--debug', '--traceback']):
            with patch.object(hr, 'runtime_class', return_value=factory), \
                    contextlib.redirect_stdout(io.StringIO()) as out, \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                code = ops.main(['test-sudo', 'h', '--root', str(self.root), *flags])
            self.assertEqual(code, 1)
            step = json.loads(out.getvalue())['groups'][0]['steps'][0]
            self.assertEqual(step['stage'], 'sudo_entry')
            self.assertEqual(step['password_source'], 'vars.sudo.password')
            self.assertEqual(step['error']['reason'], 'authentication_rejected_or_password_required')
            for secret in ('login-secret', 'sudo-secret', 'secret-password'):
                self.assertNotIn(secret, out.getvalue() + err.getvalue())
            if flags:
                self.assertIn('sudo_entry', err.getvalue())
            else:
                self.assertEqual(err.getvalue(), '')
            if '--debug' in flags:
                self.assertIn('DEBUG', err.getvalue())
                self.assertIn('Traceback (frames only)', err.getvalue())
                self.assertIn('in __enter__', err.getvalue())
        # Diagnostic settings must not leak into later invocations.
        self.assertEqual(hr._diagnostics.get(), (False, False, False))

    def test_sudo_password_sources_and_missing_password(self):
        for users, variables, expected in (
                ({'login': {'vars': {'sudo': {'password': 'actor-secret'}}}},
                 {'sudo': {'password': 'host-secret'}}, 'users.<account>.vars.sudo.password'),
                ({'login': {'password': 'login-secret'}}, {}, 'users.<account>.password'),
                ({}, {}, 'none')):
            self.write({'local': True}, users, variables)
            report = hr.privilege_test(self.config, 'h', 'sudo', session_class=self.factory)
            step = report['groups'][0]['steps'][0]
            self.assertEqual(step['password_source'], expected)
            self.assertEqual(step['password_supplied'], expected != 'none')

    def test_all_host_diagnostic_commands_accept_flags_and_trace_failures(self):
        for command, extra in (('host-init', []), ('test-su', ['user2']), ('test-host', [])):
            with patch.object(hr, 'runtime_class', return_value=Mock(side_effect=TimeoutError('private-token'))), \
                    contextlib.redirect_stdout(io.StringIO()) as out, \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                code = ops.main([command, 'h', *extra, '--root', str(self.root),
                                 '-v', '--debug', '--traceback'])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out.getvalue())['status'], 'failed')
            self.assertIn('Traceback (frames only)', err.getvalue())
            self.assertNotIn('private-token', out.getvalue() + err.getvalue())

    def test_cleanup_and_command_failures_emit_safe_tracebacks(self):
        session = Mock()
        session.exec_command.side_effect = PermissionError('command-secret')
        session.close.side_effect = RuntimeError('cleanup-secret')
        with hr.diagnostic_options(debug=True, show_traceback=True), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            report = hr.test_host(self.config, 'h', session_class=Mock(return_value=session))
        self.assertEqual(report['status'], 'failed')
        self.assertIn('session_cleanup: failed', err.getvalue())
        self.assertIn('hostname: failed', err.getvalue())
        self.assertIn('Traceback (frames only)', err.getvalue())
        for secret in ('command-secret', 'cleanup-secret'):
            self.assertNotIn(secret, err.getvalue() + json.dumps(report))

    def test_independent_and_repeated_chains(self):
        report=hr.privilege_test(self.config,'h','su',['user2','user3'],session_class=self.factory)
        self.assertEqual(report['status'],'success')
        self.assertEqual([(e[1],e[2]) for e in self.events if e[0]=='su'], [('login','user2'),('login','user3')])
        self.events.clear()
        report=hr.privilege_test(self.config,'h','su',chains=[['user2','user3'],['user3','user2']],session_class=self.factory)
        self.assertEqual(report['status'],'success')
        self.assertEqual([(e[1],e[2]) for e in self.events if e[0]=='su'], [('login','user2'),('user2','user3'),('login','user3'),('user3','user2')])
        self.assertNotIn('two-secret',json.dumps(report))

    def test_chain_failure_skips_rest_and_continues_other_chain(self):
        factory=lambda: FakeConsole('login',self.events,{'user2'})
        report=hr.privilege_test(self.config,'h','su',chains=[['user2','user3'],['user3']],session_class=factory)
        self.assertEqual(report['status'],'failed')
        self.assertEqual(report['groups'][0]['steps'][1]['reason_code'],'previous_step_failed')
        self.assertEqual(report['groups'][1]['status'],'success')
        self.assertNotIn('secret-password',json.dumps(report))

    def test_invalid_lists_and_injection(self):
        for targets,chains in [([],None),(['login'],None),(['user2','user2'],None),(['user2'],[['user3']]),([], [['user2','user2']]),(['-root'],None)]:
            with self.assertRaises(ops.ConfigError):
                hr.privilege_test(self.config,'h','su',targets,chains,session_class=self.factory)

    def test_default_sudo_uses_login_password_fallback(self):
        report=hr.privilege_test(self.config,'h','sudo',session_class=self.factory,password_required=True)
        self.assertEqual(report['status'],'success')
        event=next(e for e in self.events if e[0]=='sudo')
        self.assertEqual(event[3]['password'],'login-secret')
        self.assertNotIn('login-secret',json.dumps(report))
        self.events.clear()
        self.write({'local':True}, variables={'sudo':{'password':'sudo-secret'}})
        report=hr.privilege_test(self.config,'h','sudo',session_class=self.factory,password_required=True)
        self.assertEqual(report['status'],'success')
        event=next(e for e in self.events if e[0]=='sudo')
        self.assertEqual(event[3]['password'],'sudo-secret')
        self.assertNotIn('sudo-secret',json.dumps(report))

    def test_sudo_multiple_users_and_run_as(self):
        report=hr.privilege_test(self.config,'h','sudo',['user2','user3'],run_as='service',session_class=self.factory)
        self.assertEqual(report['status'],'success')
        self.assertEqual([(e[1],e[2]) for e in self.events if e[0]=='sudo'],[('user2','service'),('user3','service')])

    def test_privilege_credentials_priority_scope_empty_and_invalid(self):
        for mode in ('sudo', 'su'):
            for user in ('login', 'user2'):
                cases = (
                    ({'password': 'account-secret', 'vars': {mode: {'password': 'override-secret'}}},
                     {mode: {'password': 'host-secret'}}, 'override-secret', f'users.<account>.vars.{mode}.password'),
                    ({'password': 'account-secret'}, {mode: {'password': 'host-secret'}},
                     'host-secret' if user == 'login' else 'account-secret',
                     f'vars.{mode}.password' if user == 'login' else 'users.<account>.password'),
                    ({'password': 'account-secret'}, {}, 'account-secret', 'users.<account>.password'),
                    ({'password': 'account-secret', 'vars': {mode: {'password': ''}}}, {}, '',
                     f'users.<account>.vars.{mode}.password'),
                    ({'password': 'account-secret', 'vars': {mode: {'password': None}}}, {},
                     'account-secret', 'users.<account>.password'),
                    ({}, {}, None, 'none'),
                )
                for account, variables, expected, source in cases:
                    with self.subTest(mode=mode, user=user, source=source):
                        self.write({'local': True}, {user: account}, variables)
                        self.assertEqual(hr.privilege_password(self.config, 'h', user, mode, 'login'),
                                         (expected, source))
                for invalid in (False, 123, []):
                    self.write({'local': True}, {user: {'password': 'valid-secret',
                                                      'vars': {mode: {'password': invalid}}}})
                    with self.assertRaises(ops.ConfigError):
                        hr.privilege_password(self.config, 'h', user, mode, 'login')

    def test_su_chains_and_sudo_prerequisite_use_target_su_override(self):
        self.write({'local': True}, {
            'login': {'password': 'login-secret'},
            'user2': {'password': 'two-secret', 'vars': {'su': {'password': 'su-override'}}},
            'user3': {'password': 'three-secret'}},
            {'su': {'password': 'host-su-secret'}, 'sudo': {'password': 'host-sudo-secret'}})
        report = hr.privilege_test(self.config, 'h', 'su', chains=[['user2', 'user3']], session_class=self.factory)
        self.assertEqual(report['status'], 'success')
        self.assertEqual([e[3]['password'] for e in self.events if e[0] == 'su'],
                         ['su-override', 'three-secret'])
        self.events.clear()
        report = hr.privilege_test(self.config, 'h', 'sudo', ['user2'], session_class=self.factory)
        self.assertEqual(report['status'], 'success')
        self.assertEqual(next(e[3]['password'] for e in self.events if e[0] == 'su'), 'su-override')
        self.assertEqual(next(e[3]['password'] for e in self.events if e[0] == 'sudo'), 'two-secret')
        for secret in ('su-override', 'two-secret', 'host-su-secret', 'host-sudo-secret'):
            self.assertNotIn(secret, json.dumps(report))

    def test_su_uses_only_su_override_and_reports_source_without_value(self):
        self.write({'local': True}, {'user2': {'password': 'account-secret', 'vars': {
            'su': {'password': 'su-secret'}, 'sudo': {'password': 'sudo-secret'}}}})
        with patch.object(hr, 'runtime_class', return_value=self.factory), \
                contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            code = ops.main(['test-su', 'h', 'user2', '--root', str(self.root), '--debug'])
        self.assertEqual(code, 0)
        step = json.loads(out.getvalue())['groups'][0]['steps'][0]
        self.assertEqual(step['password_source'], 'users.<account>.vars.su.password')
        self.assertTrue(step['password_supplied'])
        self.assertEqual(next(e[3]['password'] for e in self.events if e[0] == 'su'), 'su-secret')
        for secret in ('account-secret', 'su-secret', 'sudo-secret'):
            self.assertNotIn(secret, out.getvalue() + err.getvalue())

    def test_rejected_override_is_not_retried_with_fallback_password(self):
        self.write({'local': True}, {'login': {'password': 'login-secret',
                                             'vars': {'sudo': {'password': 'override-secret'}}}})
        factory = lambda: FakeConsole('login', self.events, {'root'})
        report = hr.privilege_test(self.config, 'h', 'sudo', session_class=factory)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual([e[3]['password'] for e in self.events if e[0] == 'sudo'], ['override-secret'])

    def test_test_host_skips_sudo_when_all_password_sources_missing(self):
        self.write({'local': True}, {'login': {}, 'user2': {'password': 'two-secret'}})
        with patch.object(hr, 'initialize_host', return_value={'status': 'success'}):
            report = hr.test_host(self.config, 'h', session_class=self.factory)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['tests']['test-sudo']['status'], 'skipped')
        self.assertFalse(any(e[0] == 'sudo' for e in self.events))

    def test_group_cleanup_failure_is_failed_and_other_groups_continue(self):
        count = 0
        def factory():
            nonlocal count
            count += 1
            console = FakeConsole('login', self.events)
            if count == 2:
                console.close = Mock(side_effect=RuntimeError('private-cleanup'))
            return console
        report = hr.privilege_test(self.config, 'h', 'su', ['user2', 'user3'], session_class=factory)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['groups'][0]['cleanup_error'], 'RuntimeError')
        self.assertEqual(report['groups'][1]['status'], 'success')
        self.assertNotIn('private-cleanup', json.dumps(report))

    def test_actual_identity_mismatch_is_failed(self):
        with patch.object(hr,'identity',side_effect=[{'username':'login','effective_uid':1000},{'username':'login','effective_uid':1000},RuntimeError('mismatch'),{'username':'login','effective_uid':1000}]):
            report=hr.privilege_test(self.config,'h','su',['user2'],session_class=self.factory)
        self.assertEqual(report['groups'][0]['steps'][0]['stage'],'su_identity')
        self.assertEqual(report['status'],'failed')

    def test_test_host_uses_login_password_and_tests_only_other_accounts(self):
        with patch.object(hr,'initialize_host',return_value={'status':'success','selection_source':'cache'}):
            report=hr.test_host(self.config,'h',session_class=self.factory)
        self.assertEqual(report['status'],'success')
        self.assertEqual(report['tests']['test-sudo']['status'],'success')
        self.assertEqual([g['accounts'] for g in report['tests']['test-su']['groups']],[['user2'],['user3']])

    def test_cli_repeated_chain_and_explicit_refresh(self):
        with patch.object(hr,'runtime_class',return_value=self.factory),contextlib.redirect_stdout(io.StringIO()) as out:
            code=ops.main(['test-su','h','--root',str(self.root),'--chain','user2','user3','--chain','user3','user2'])
        self.assertEqual(code,0)
        self.assertEqual(len(json.loads(out.getvalue())['groups']),2)
        with patch.object(hr,'initialize_host',return_value={'status':'success'}) as init,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ops.main(['host-init','h','--root',str(self.root)]),0)
        self.assertTrue(init.call_args.kwargs['refresh'])


class DispatchTests(unittest.TestCase):
    def test_specialized_priority_and_ambiguity(self):
        linux={'id':'linux','match':{'os_name':'linux'}}
        ubuntu={'id':'ubuntu','match':{'os_name':'linux','distribution_id':'ubuntu','distribution_version':'>=24.04,<25'}}
        facts={'os_name':'linux','distribution_id':'ubuntu','distribution_version':'24.04'}
        self.assertEqual(dispatch.select([linux,ubuntu],facts)['id'],'ubuntu')
        self.assertEqual(dispatch.select([linux,ubuntu],{'os_name':'linux'})['id'],'linux')
        with self.assertRaises(ops.ConfigError):
            dispatch.select([linux,dict(linux,id='other')],facts)
        self.assertIsNone(dispatch.select([linux],{'os_name':'freebsd'}))

    def test_version_numeric_and_vendor_exact(self):
        self.assertTrue(dispatch.version_match('14.10','>=14.2,<15'))
        self.assertTrue(dispatch.version_match('14.2-RELEASE','=14.2-RELEASE'))
        self.assertFalse(dispatch.version_match('14.2-RELEASE','>=14.2'))
        with self.assertRaises(ops.ConfigError):
            dispatch.version_match('1','>=bad')

    def test_manifest_version_symlink_and_unselected_code(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); bundle=root/'recipe'; shutil.copytree(runner.BUNDLE,bundle)
            metadata=ops.read_yaml(bundle/'recipe.yaml')
            dispatch.validate(bundle,metadata)
            entry=bundle/'implementations/linux.py'
            entry.write_text(entry.read_text().replace("VERSION = '0.1.1'","VERSION = '9'"))
            with self.assertRaises(ops.ConfigError): dispatch.validate(bundle,metadata)
            entry.unlink(); entry.symlink_to(runner.BUNDLE/'implementations/linux.py')
            with self.assertRaises(ops.ConfigError): dispatch.validate(bundle,metadata)


class InventoryDispatchTests(unittest.TestCase):
    def test_platform_collectors_and_result_versions(self):
        for kernel, platform, values in [
            ('FreeBSD','freebsd',[result('node'),result('FreeBSD'),result('14.1'),result('amd64'),result('14.2-RELEASE')]),
            ('Darwin','macos',[result('node'),result('Darwin'),result('24.0'),result('arm64'),result('macOS'),result('15.0')])]:
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                (root/'hosts.yaml').write_text('hosts: {h: {connection: {local: true}}}')
                session=Mock(); session.exec_command.side_effect=facts_outputs(kernel)+values
                report,path=runner.run(root,'h',recipe='inventory/system',session_class=Mock(return_value=session))
                self.assertEqual(report['status'],'success')
                self.assertEqual(report['recipe']['implementation_id'],platform)
                self.assertEqual(report['recipe']['implementation_version'],'0.1.0')
                self.assertEqual(report['recipe']['recipe_version'],'0.2.0')
                self.assertEqual(report['schema_version'],'0.2.0')
                self.assertEqual(json.loads(path.read_text()),report)

    def test_failed_host_init_skips_recipe_and_batch_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'hosts.yaml').write_text('hosts: {h: {connection: {local: true}}}')
            session=Mock(); session.exec_command.side_effect=[TimeoutError('secret')]
            report,_=runner.run(root,'h',recipe='inventory/system',session_class=Mock(return_value=session))
            self.assertEqual(report['status'],'skipped')
            self.assertEqual(report['reason_code'],'host_init_failed')
            self.assertNotIn('implementation_id',report['recipe'])
            with patch.object(runner,'run',side_effect=[(report,root/'first.json'),(dict(report,status='success'),root/'second.json')]) as run,contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(runner.main(['h',str(root),'--hosts','other','--recipe','inventory/system']),1)
            self.assertEqual(run.call_count,2)
            self.assertEqual(len(json.loads(out.getvalue())['hosts']),2)

    def test_no_fallback_after_selected_implementation_fails(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); bundle=root/'recipes/system'; shutil.copytree(runner.BUNDLE,bundle)
            (root/'hosts.yaml').write_text('hosts: {h: {connection: {local: true}}}')
            metadata=ops.read_yaml(bundle/'recipe.yaml')
            metadata['implementations'].append({'id':'special','version':'1','entrypoint':'special.py','priority':1,'match':{'os_name':'linux'}})
            (bundle/'special.py').write_text("VERSION='1'\ndef collect(*args):\n    raise RuntimeError('secret')\n")
            (bundle/'recipe.yaml').write_text(yaml.safe_dump(metadata))
            session=Mock(); session.exec_command.side_effect=facts_outputs()
            report,_=runner.run(root,'h',recipe='./recipes/system',session_class=Mock(return_value=session))
            self.assertEqual(report['recipe']['implementation_id'],'special')
            self.assertEqual(report['status'],'failed')
            self.assertEqual(session.exec_command.call_count,4)
            self.assertNotIn('secret',json.dumps(report))

    def test_connection_test_optional_host_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'hosts.yaml').write_text('hosts: {h: {connection: {local: true}}}')
            session=Mock(); session.exec_command.side_effect=[('node','',0),('today','',0)]
            with patch.object(hr,'runtime_class',return_value=Mock(return_value=session)),patch.object(hr,'initialize_host',return_value={'status':'success'}) as init,contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(ops.main(['test-connection','h',str(root),'--host-init']),0)
            self.assertEqual(json.loads(out.getvalue())['host_init']['status'],'success')
            self.assertTrue(init.call_args.kwargs['refresh'])


if __name__ == '__main__':
    unittest.main()
