"""Public Python-session runner/input contracts, with synthetic Sessions only."""
import contextlib
import copy
import io
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import opsfeast as ops
import recipe_contract
import recipe_inspection
from recipe_inputs import cli_variables, json_object, prepare_vars
import run_recipe as runner

CODE = '''VERSION = '1.0.0'
def execute(session, *, context, timeout):
    result = session.exec_command(['synthetic', str(context.vars['port'])], command_timeout=timeout)
    return {'status': 'success', 'reason_code': 'checked', 'message': 'Synthetic check.',
            'data': {'host': context.host_id, 'port': context.vars['port']}}
'''


class GeneralRecipeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.directory = self.root / 'recipes/system/network/check/port'
        self.directory.mkdir(parents=True)
        self.metadata = {'descriptor_version': '0.3.0', 'id': 'synthetic-port', 'version': '1.0.0',
                         'runner': {'contract': 'python-session', 'version': '0.1.0', 'entrypoint': 'main.py'},
                         'inputs': {'variables': {'port': {'type': 'integer', 'required': True, 'minimum': 1, 'maximum': 65535}}},
                         'output': {'schema_version': '1.0.0'}}
        self.settings = {'hosts': {'h': {'connection': {'local': True}, 'recipes': [':system/network/check/port']},
                                  'other': {'connection': {'local': True}, 'recipes': [':system/network/check/port']}}}
        self.code = CODE
        self.write()

    def write(self):
        (self.directory / 'recipe.yaml').write_text(json.dumps(self.metadata))
        (self.directory / 'main.py').write_text(self.code)
        (self.root / 'hosts.yaml').write_text(json.dumps(self.settings))

    def execute(self, **kwargs):
        self.session = Mock()
        self.session.exec_command.return_value = SimpleNamespace(stdout='', stderr='', exitcode=0)
        self.factory = Mock(return_value=self.session)
        return runner.run(self.root, 'h', recipe=':system/network/check/port', session_class=self.factory, **kwargs)

    def cli(self, *args):
        output, error = io.StringIO(), io.StringIO()
        factory = Mock(return_value=Mock())
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error), \
                patch.object(runner, 'load_runtime', return_value=(factory, {'verification': 'synthetic'})):
            status = runner.main([':system/network/check/port', '--root', str(self.root), *args])
        return status, json.loads(output.getvalue()) if output.getvalue() else None, error.getvalue(), factory

    def test_success_saved_envelope_without_inventory_probes_or_retention(self):
        with patch.object(runner, 'discover') as discover, patch.object(runner, 'retain') as retain:
            report, path = self.execute(assignments=['port=8888'])
        discover.assert_not_called()
        retain.assert_not_called()
        self.assertEqual(report['data'], {'host': 'h', 'port': 8888})
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['recipe']['runner_version'], '0.1.0')
        self.assertEqual(report['recipe']['variable_names'], ['port'])
        self.assertEqual(report['retention']['reason_code'], 'no_retention_adapter')
        self.assertEqual(report['evidence_kind'], 'mock')
        self.assertTrue(path.name.startswith('recipe-run-'))
        self.assertEqual(json.loads(path.read_text()), report)
        self.assertFalse((self.root / 'facts').exists())
        self.session.close.assert_called_once_with(strict=True)
        self.assertNotIn('effective_vars', path.read_text())

    def test_cli_single_and_parallel_batch_data_and_order(self):
        for targets in (['h'], ['h', 'other']):
            status, report, error, factory = self.cli('--host', *targets, '--var', 'port=8888', '--threads', '2')
            self.assertEqual(status, 0, error)
            if len(targets) == 1:
                self.assertEqual(report['data']['port'], 8888)
            else:
                self.assertEqual([item['host'] for item in report['hosts']], targets)
                self.assertEqual([item['data']['host'] for item in report['hosts']], targets)
            self.assertEqual(factory.call_count, len(targets))

    def test_cli_file_and_assignments_precedence(self):
        self.metadata['inputs']['variables']['port']['default'] = 1000
        self.settings['recipe_sources'] = {'profile': {'vars': {'port': 2000}}}
        self.settings['hosts']['h']['recipes'] = [{'recipe': ':system/network/check/port', 'vars': {'port': 3000}}]
        self.write()
        file = self.root / 'input.json'
        file.write_text('{"port":4000}')
        status, report, error, _ = self.cli('--host', 'h', '--var', 'port=5000', '--vars-file', str(file))
        self.assertEqual(status, 0, error)
        self.assertEqual(report['data']['port'], 5000)
        self.assertEqual(json.loads((self.root / 'hosts.yaml').read_text()), self.settings)

    def test_invalid_vars_fail_before_session_and_module_execution(self):
        self.code = "raise RuntimeError('MUST_NOT_LOAD')\n" + CODE
        self.write()
        for assignments in ([], ['port=0'], ['port=65536'], ['port=true'], ['port="8888"'],
                            ['port=NaN'], ['port=Infinity'], ['port=null'], ['missing=private-value'],
                            ['port=2', 'port=3'], ['port'], ['port=private-value']):
            with self.subTest(assignments=assignments), patch.object(runner, 'load_runtime') as runtime:
                with self.assertRaises(ops.ConfigError):
                    runner.run(self.root, 'h', recipe=':system/network/check/port', assignments=assignments)
                runtime.assert_not_called()

    def test_input_error_output_does_not_disclose_value(self):
        status, _, error, factory = self.cli('--host', 'h', '--var', 'port=private-value')
        self.assertEqual(status, 1)
        self.assertNotIn('private-value', error)
        factory.assert_not_called()

    def test_parameter_isolation_between_hosts(self):
        self.metadata['inputs']['variables']['items'] = {'type': 'array'}
        self.code = '''VERSION = '1.0.0'
def execute(session, *, context, timeout):
    context.vars['items'].append(context.host_id)
    return {'status':'success', 'reason_code':'ok', 'message':'Synthetic.', 'data':{'items':context.vars['items']}}
'''
        self.write()
        status, report, _, _ = self.cli('--host', 'h', 'other', '--var', 'port=1', '--var', 'items=[]', '--threads', '2')
        self.assertEqual(status, 0)
        self.assertEqual([item['data']['items'] for item in report['hosts']], [['h'], ['other']])

    def test_refused_status_partial_skipped_and_unsupported_preserved(self):
        for state in ('success', 'partial', 'failed', 'skipped', 'unsupported'):
            self.code = "VERSION='1.0.0'\ndef execute(session, *, context, timeout):\n    return " + repr(
                {'status': state, 'reason_code': 'synthetic', 'message': 'Synthetic.', 'data': {'reachable': False}})
            self.write()
            status, report, _, _ = self.cli('--host', 'h', '--var', 'port=1')
            self.assertEqual(status, 0 if state == 'success' else 1)
            self.assertEqual(report['status'], state)
            self.assertFalse(report['data']['reachable'])

    def test_bad_results_fail_and_do_not_save_invalid_payloads(self):
        for value in (None, {'status': 'success'}, {'status': 'bogus', 'reason_code': 'ok', 'message': 'M', 'data': {}},
                      {'status': 'success', 'reason_code': '', 'message': 'M', 'data': {}},
                      {'status': 'success', 'reason_code': 'ok', 'message': 'M', 'data': []}):
            self.code = "VERSION='1.0.0'\ndef execute(session, *, context, timeout):\n    return " + repr(value)
            self.write()
            report, path = self.execute(assignments=['port=1'])
            self.assertEqual(report['reason_code'], 'invalid_result')
            self.assertEqual(report['data'], {})
            self.assertTrue(path.is_file())
            self.session.close.assert_called_once_with(strict=True)
        for expression in ("{'bad': float('nan')}", "{'bad': object()}", "{'nested': {1: 'ambiguous-key'}}"):
            self.code = "VERSION='1.0.0'\ndef execute(session, *, context, timeout):\n    return {'status':'success','reason_code':'ok','message':'M','data':" + expression + "}"
            self.write()
            report, _ = self.execute(assignments=['port=1'])
            self.assertEqual(report['reason_code'], 'invalid_result')

    def test_execution_loading_and_cleanup_errors_preserved_without_secrets(self):
        for code, stage in (("VERSION='1.0.0'\nraise RuntimeError('private-value')\ndef execute(session, *, context, timeout): pass", 'implementation_loading'),
                            ("VERSION='1.0.0'\ndef execute(session, *, context, timeout): raise TimeoutError('private-value')", 'execution')):
            self.code = code
            self.write()
            report, path = self.execute(assignments=['port=1'])
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['execution_errors'][0]['stage'], stage)
            self.assertNotIn('private-value', path.read_text())
            self.session.close.assert_called_once_with(strict=True)
        self.code = CODE
        self.write()
        session = Mock()
        session.close.side_effect = RuntimeError('private-value')
        report, _ = runner.run(self.root, 'h', recipe=':system/network/check/port', assignments=['port=1'], session_class=Mock(return_value=session))
        self.assertEqual(report['reason_code'], 'cleanup_failed')
        self.assertEqual(report['data']['port'], 1)

    def test_static_inspection_does_not_execute_entrypoint(self):
        self.code = "raise RuntimeError('never execute candidate')\n" + CODE
        self.write()
        report = recipe_inspection.inspect_recipes(str(self.directory))['recipes'][0]
        self.assertEqual(report['runner_contract'], 'valid-python-session')
        self.assertEqual(report['status'], 'success')

    def test_signature_contract_version_and_paths_preflight(self):
        changes = [('descriptor_version', '0.2.0'), ('id', '../escape'), ('version', '2.0.0'),
                   ('runner', {'contract': 'unknown', 'version': '0.1.0', 'entrypoint': 'main.py'}),
                   ('runner', {'contract': 'python-session', 'version': '2.0.0', 'entrypoint': 'main.py'}),
                   ('runner', {'contract': 'python-session', 'version': '0.1.0', 'entrypoint': '../main.py'}),
                   ('platforms', {'implemented': 'linux'}), ('implementations', [])]
        original = copy.deepcopy(self.metadata)
        for key, value in changes:
            self.metadata = {**original, key: value}
            self.write()
            with self.subTest(key=key, value=value), self.assertRaises(ops.ConfigError):
                recipe_contract.validate(self.directory, self.metadata)
        self.metadata = original
        for signature in ('def execute(session): pass', 'async def execute(session, *, context, timeout): pass',
                          'def execute(session, extra, *, context, timeout): pass'):
            self.code = "VERSION='1.0.0'\n" + signature
            self.write()
            with self.assertRaises(ops.ConfigError):
                recipe_contract.validate(self.directory, self.metadata)

    def test_entrypoint_and_helper_symlink_escape(self):
        outside = self.root / 'outside.py'
        outside.write_text(CODE)
        (self.directory / 'main.py').unlink()
        (self.directory / 'main.py').symlink_to(outside)
        with self.assertRaises(ops.ConfigError): self.execute(assignments=['port=1'])
        (self.directory / 'main.py').unlink()
        self.write()
        (self.directory / 'helper.py').symlink_to(outside)
        with self.assertRaises(ops.ConfigError): self.execute(assignments=['port=1'])

    def test_disabled_host_and_source_do_not_load_runtime(self):
        self.settings['hosts']['h']['enabled'] = False
        self.write()
        with patch.object(runner, 'load_runtime') as runtime:
            report, path = runner.run(self.root, 'h', recipe=':system/network/check/port')
        self.assertEqual(report['reason_code'], 'host_disabled')
        self.assertIsNone(path)
        runtime.assert_not_called()
        self.settings['hosts']['h']['enabled'] = True
        self.settings['recipe_sources'] = {'profile': {'enabled': False}}
        self.write()
        with patch.object(runner, 'load_runtime') as runtime:
            report, path = runner.run(self.root, 'h', recipe=':missing')
        self.assertEqual(report['reason_code'], 'source_disabled')
        runtime.assert_not_called()

    def test_named_external_source_and_failed_connection_cleanup(self):
        self.settings['recipe_sources'] = {'external': {'path': str(self.root / 'recipes')}}
        self.write()
        session = Mock()
        report, _ = runner.run(self.root, 'h', recipe='external:system/network/check/port', assignments=['port=1'], session_class=Mock(return_value=session))
        self.assertEqual(report['recipe']['source_name'], 'external')
        self.settings['hosts']['h']['connection'] = {'hostname': 'synthetic.example'}
        self.write()
        session.connect.side_effect = RuntimeError('private-value')
        with patch.object(runner, 'connection_plan', return_value=[{'hostname': 'synthetic.example'}]), \
                patch('host_runtime.connection_plan', return_value=[{'hostname': 'synthetic.example'}]):
            report, path = runner.run(self.root, 'h', recipe=':system/network/check/port', assignments=['port=1'], session_class=Mock(return_value=session))
        self.assertEqual(report['status'], 'failed')
        self.assertNotIn('private-value', path.read_text())
        self.assertFalse(report['hops'][0]['connected'])

    def test_inventory_cli_override_retains_inventory_contract(self):
        config, _, _, _ = runner.preflight(self.root, 'h', 'system/inventory/overview', assignments=['command_timeout_seconds=7'])
        self.assertEqual(config.execution_recipe['effective_vars']['command_timeout_seconds'], 7)
        with self.assertRaises(ops.ConfigError):
            runner.preflight(self.root, 'h', 'system/inventory/overview', assignments=['port=8888'])

    def test_runtime_version_callable_and_system_exit_fail_with_cleanup(self):
        for suffix in ("globals()['VERSION'] = '2.0.0'", 'execute = None'):
            self.code = CODE + '\n' + suffix
            self.write()
            report, _ = self.execute(assignments=['port=1'])
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['execution_errors'][0]['stage'], 'implementation_loading')
            self.session.close.assert_called_once_with(strict=True)
        self.code = "VERSION='1.0.0'\ndef execute(session, *, context, timeout): raise SystemExit('private-value')"
        self.write()
        report, path = self.execute(assignments=['port=1'])
        self.assertEqual(report['status'], 'failed')
        self.assertNotIn('private-value', path.read_text())
        self.session.close.assert_called_once_with(strict=True)

    def test_save_error_and_bad_vars_file_return_nonzero(self):
        with patch.object(runner, 'save_report', side_effect=OSError('private-value')):
            status, _, error, _ = self.cli('--host', 'h', '--var', 'port=1')
        self.assertEqual(status, 1)
        self.assertNotIn('private-value', error)
        file = self.root / 'invalid.json'
        file.write_text('{"port":NaN}')
        status, _, error, factory = self.cli('--host', 'h', '--vars-file', str(file))
        self.assertEqual(status, 1)
        factory.assert_not_called()

    def test_batch_input_failure_keeps_other_hosts_independent(self):
        self.settings['hosts']['h']['recipes'] = [{'recipe': ':system/network/check/port', 'vars': {'port': 8888}}]
        self.write()
        status, report, _, factory = self.cli('--host', 'h', 'other', '--threads', '1')
        self.assertEqual(status, 1)
        self.assertEqual([item['status'] for item in report['hosts']], ['success', 'failed'])
        self.assertEqual(factory.call_count, 1)

    def test_generic_inputs_do_not_allow_extra_output_fields(self):
        self.metadata['output']['retention_adapter'] = 'arbitrary.py'
        self.write()
        with self.assertRaises(ops.ConfigError):
            self.execute(assignments=['port=1'])


class InputParsingTests(unittest.TestCase):
    def test_all_types_literal_strings_empty_and_equals(self):
        values = {'s': 'true=still text', 'empty': '', 'i': 8888, 'n': 1.5, 'b': False, 'a': [1], 'o': {'x': 2}}
        types = {'s':'string', 'empty':'string', 'i':'integer', 'n':'number', 'b':'boolean', 'a':'array', 'o':'object'}
        metadata = {'inputs': {'variables': {key:{'type':kind} for key,kind in types.items()}}}
        assignments = [key+'='+(value if types[key]=='string' else json.dumps(value)) for key,value in values.items()]
        self.assertEqual(prepare_vars(metadata, {}, {}, cli_variables(metadata, assignments=assignments)), values)

    def test_json_file_invalid_duplicate_nonfinite_and_nonobject(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder)/'vars.json'
            for text in ('{', '[]', 'null', '{"port":1,"port":2}', '{"secret":{"x":1,"x":2}}', '{"port":NaN}', '{"port":Infinity}'):
                file.write_text(text)
                with self.subTest(text=text), self.assertRaises(ops.ConfigError): json_object(file)
            file.write_text('{"port":8888}')
            self.assertEqual(json_object(file), {'port':8888})
            file.unlink()
            with self.assertRaises(ops.ConfigError): json_object(file)


class PortRecipeTests(unittest.TestCase):
    def setUp(self):
        self.directory = ops.REPOSITORY_RECIPES/'system/network/check/port'
        self.recipe = runpy.run_path(str(self.directory/'main.py'))

    def test_bundled_port_inspection_and_probe_states(self):
        self.assertEqual(recipe_inspection.inspect_recipes(str(self.directory))['recipes'][0]['runner_contract'], 'valid-python-session')
        for state, reachable, status in (('open',True,'success'), ('refused',False,'success'), ('timeout',None,'failed'), ('network_error',None,'failed')):
            session = Mock()
            session.exec_command.return_value = SimpleNamespace(stdout=json.dumps({'state':state}), exitcode=0)
            result = self.recipe['execute'](session, context=SimpleNamespace(host_id='h', vars={'port':8888,'address':'127.0.0.1','connect_timeout_seconds':3}), timeout=10)
            self.assertEqual(result['data']['reachable'], reachable)
            self.assertEqual(result['status'], status)
            self.assertEqual(session.exec_command.call_args.kwargs['command_timeout'], 10)
            self.assertEqual(session.exec_command.call_args.args[0][-3:], ['127.0.0.1','8888','3'])

    def test_bad_probe_output_truncation_and_command_failure(self):
        for result in (SimpleNamespace(stdout='bad',exitcode=0), SimpleNamespace(stdout='[]',exitcode=0),
                       SimpleNamespace(stdout='{"state":"unknown"}',exitcode=0), SimpleNamespace(stdout='',exitcode=127),
                       SimpleNamespace(stdout='{"state":"open"}',exitcode=0,stdout_truncated=True)):
            session = Mock()
            session.exec_command.return_value = result
            report = self.recipe['execute'](session, context=SimpleNamespace(host_id='h',vars={'port':1,'address':'::1','connect_timeout_seconds':3}), timeout=5)
            self.assertEqual(report['status'], 'failed')
            self.assertIsNone(report['data']['reachable'])

    def test_target_script_outcomes_with_mock_sockets_no_network(self):
        for error, expected in ((None,'open'), (ConnectionRefusedError(),'refused'), (TimeoutError(),'timeout'), (OSError(),'network_error')):
            output = io.StringIO()
            with patch('socket.create_connection', side_effect=error) as connect, \
                    patch.object(sys, 'argv', ['probe','127.0.0.1','8888','2']), contextlib.redirect_stdout(output):
                exec(self.recipe['PROBE'], {})
            self.assertEqual(json.loads(output.getvalue())['state'], expected)
            connect.assert_called_once_with(('127.0.0.1',8888),timeout=2.0)


if __name__ == '__main__':
    unittest.main()
