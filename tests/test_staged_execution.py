"""Staged Recipe lifecycle without real browser, Web server, or managed hosts."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opsfeast import ConfigError, Instance
from opsfeast.staged_execution import Executions, PythonStage, stages
from opsfeast.storage import initialize_data_root
from opsfeast.web_settings import configure_port
from recipe_cli import main as recipe_cli


class StagedExecutionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        with redirect_stdout(io.StringIO()):
            profile = Instance.open(root).init_profile()
        self.store = Executions(profile.root, installation=root)
        self.binding = {'reference': ':synthetic/sequence', 'version': '1.0.0',
                        'fingerprint': 'a' * 64, 'hosts': ['fake']}
        self.plan = stages({
            'launch': {'mode': 'agent'},
            'execution': {'version': '0.1.0', 'stages': [
                {'id': 'gather', 'executor': 'agent'},
                {'id': 'review', 'executor': 'agent'},
                {'id': 'process', 'executor': 'python'},
                {'id': 'report', 'executor': 'agent'},
            ]},
        })
        self.id = self.store.begin(**self.binding, title='Synthetic sequence',
                                   stages=self.plan, trigger='agent')['id']

    def test_sequential_agent_agent_python_agent_and_exclusive_claim(self):
        self.assertEqual(self.store.records.snapshot(self.id)['blocks'], [])
        with self.assertRaises(ConfigError):
            PythonStage(self.store, self.id, self.binding)
        self.store.claim(self.id, 'gather', 'agent')
        self.store.progress(self.id, 'gather', 'agent', 'Waiting for quote review', awaiting_human=True)
        self.assertTrue(self.store.read(self.id)['stages'][0]['awaiting_human'])
        self.store.finish(self.id, 'gather', 'agent', 'success', {'rate': '31.25'})
        self.store.claim(self.id, 'review', 'agent')
        self.store.finish(self.id, 'review', 'agent', 'success', {'reviewed': True})
        with self.assertRaisesRegex(ConfigError, 'binding changed'):
            PythonStage(self.store, self.id, {**self.binding, 'hosts': ['different']})

        def claim(_):
            try:
                return PythonStage(self.store, self.id, self.binding)
            except ConfigError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            (stage,) = [value for value in pool.map(claim, range(2)) if value]
        stage.progress('fake', 'Processing approved inputs')
        state = stage.finish([{'status': 'success'}], 0)
        self.assertEqual(state['status'], 'waiting')
        self.assertEqual(state['stages'][2]['output'], {'exit_code': 0})
        self.store.claim(self.id, 'report', 'agent')
        state = self.store.finish(self.id, 'report', 'agent', 'success', {})
        self.assertEqual([step['status'] for step in state['stages']], ['success'] * 4)
        self.assertTrue(state['completed_at'])
        self.assertTrue(self.store.records.snapshot(self.id)['blocks'])

    def test_cancellation_does_not_allow_later_dispatch(self):
        self.store.claim(self.id, 'gather', 'agent')
        state = self.store.finish(self.id, 'gather', 'agent', 'cancelled', {})
        self.assertEqual(state['status'], 'cancelled')
        self.assertEqual([stage['status'] for stage in state['stages'][1:]], ['skipped'] * 3)
        self.assertEqual(self.store.records.snapshot(self.id)['blocks'][-1]['status'], 'cancelled')
        with self.assertRaisesRegex(ConfigError, 'terminal'):
            self.store.claim(self.id, 'review', 'agent')

    def test_rejects_duplicate_plan_and_unsupported_schema(self):
        for value in ({'version': '0.1.0', 'stages': [self.plan[0]] * 2},
                      {'version': '0.2.0', 'stages': self.plan}):
            with self.assertRaises(ConfigError):
                stages({'execution': value})


class StagedExecutionCliTests(unittest.TestCase):
    def test_begin_creates_a_river_for_single_and_multiple_host_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            product = Path(temp) / 'product'
            product.mkdir()
            instance = Instance.open(product)
            with redirect_stdout(io.StringIO()):
                profile = instance.init_profile()
            data_root = Path(temp) / 'data'
            initialize_data_root(product, data_root)
            configure_port(product, 18841)
            (profile.root / 'hosts.yaml').write_text(
                'hosts: {first: {connection: {local: true}}, second: {connection: {local: true}}}\n',
            )
            recipe = profile.root / 'recipes' / 'fixture'
            recipe.mkdir(parents=True)
            (recipe / 'recipe.yaml').write_text(json.dumps({
                'descriptor_version': '0.3.0', 'id': 'fixture', 'version': '1.0.0',
                'title': 'Synthetic staged Recipe',
                'runner': {'contract': 'python-workflow', 'version': '0.1.0', 'entrypoint': 'main.py'},
                'launch': {'mode': 'agent', 'prompt': 'Synthetic review'},
                'execution': {'version': '0.1.0', 'stages': [{'id': 'review', 'executor': 'agent'}]},
                'output': {'schema_version': '0.1.0'},
            }))
            (recipe / 'main.py').write_text(
                "VERSION = '1.0.0'\ndef execute(*, context, timeout):\n    raise AssertionError('unexpected execution')\n",
            )
            store = Executions(profile.root, installation=product)

            def invoke(*args):
                output, errors = io.StringIO(), io.StringIO()
                with (redirect_stdout(output), redirect_stderr(errors),
                      patch('opsfeast.staged_execution.Instance.open', return_value=instance)):
                    code = recipe_cli(['execution', *args, '--root', str(profile.root)])
                self.assertEqual(code, 0, errors.getvalue())
                return json.loads(output.getvalue())

            for arguments, hosts in [
                (['--host', 'first'], ['first']),
                (['--host', 'second', 'first', '--host', 'second'], ['second', 'first']),
            ]:
                with self.subTest(arguments=arguments):
                    state = invoke('begin', ':fixture', *arguments)
                    execution_id = state['id']
                    self.assertEqual(state['hosts'], hosts)
                    self.assertEqual(state['river']['reader_url'], f'http://127.0.0.1:18841/console/{execution_id}')
                    self.assertEqual(store.read(execution_id)['status'], 'waiting')
                    river = store.records.snapshot(execution_id)
                    self.assertEqual([target['host_id'] for target in river['session']['targets']], hosts)
                    self.assertEqual(river['blocks'], [])
                    invoke('claim', execution_id, 'review')
                    self.assertEqual(store.read(execution_id)['status'], 'running')
                    self.assertEqual(len(store.records.snapshot(execution_id)['blocks']), 1)
