"""Bundled staged execution adoption using temporary data and no managed hosts."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opsfeast import ConfigError, Instance, REPOSITORY_RECIPES, read_yaml
from opsfeast.staged_execution import Executions, stages
from recipe_catalog import choose
from recipe_cli import main
from recipe_contract import validate
from recipe_reports import run_report


class RecipeStageAdoptionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.instance = Instance.open(Path(temp.name))
        with redirect_stdout(io.StringIO()):
            self.profile = self.instance.init_profile()
        self.root = self.profile.root
        (self.root / 'hosts.yaml').write_text('hosts: {fixture: {connection: {local: true}}}\n')
        self.enterContext(patch('opsfeast.staged_execution.Instance.open', return_value=self.instance))
        self.store = Executions(self.root)

    def test_all_bundled_descriptors_have_valid_stages_and_matching_program_versions(self):
        paths = list(REPOSITORY_RECIPES.rglob('recipe.yaml'))
        self.assertEqual(len(paths), 28)
        for path in paths:
            with self.subTest(recipe=str(path.parent)):
                metadata = read_yaml(path)
                validate(path.parent, metadata)
                plan = stages(metadata)
                self.assertEqual(len(plan), 1)
                self.assertEqual(plan[0]['executor'], 'python')

    def test_every_bundled_host_recipe_enters_and_finishes_a_python_stage(self):
        for path in REPOSITORY_RECIPES.rglob('recipe.yaml'):
            metadata = read_yaml(path)
            if metadata['runner']['contract'] == 'python-report':
                continue
            reference = path.parent.relative_to(REPOSITORY_RECIPES).as_posix()
            output, errors = io.StringIO(), io.StringIO()

            def run(root, host, *args, **kwargs):
                stage = kwargs['stage_run']
                self.assertEqual(stage.state['status'], 'running')
                self.assertEqual(stage.state['reference'], reference)
                self.assertEqual(stage.state['hosts'], ['fixture'])
                return {'status': 'success', 'reason_code': 'synthetic'}, None

            with self.subTest(recipe=reference), patch('recipe_runner.run', side_effect=run), redirect_stdout(output), redirect_stderr(errors):
                code = main(['run', reference, '--root', str(self.root), '--host', 'fixture', '--json'])
                self.assertEqual(code, 0, errors.getvalue())
                result = json.loads(output.getvalue())
                state = self.store.read(result['execution_id'])
                self.assertEqual(state['status'], 'success')
                self.assertEqual(state['river']['session_id'], state['id'])

    def test_offline_report_executes_without_hosts_and_saves_its_river_receipt(self):
        item = choose(self.root, 'feast/report/retention-summary')
        with patch('recipe_runner.connected', side_effect=AssertionError('no host connections')):
            report, path = run_report(self.root, item, [])
        self.assertEqual(report['status'], 'success')
        state = self.store.read(report['execution_id'])
        self.assertEqual(state['scope'], 'controller')
        self.assertEqual(state['hosts'], [])
        self.assertEqual(state['status'], 'success')
        self.assertEqual(json.loads(path.read_text())['river'], state['river'])
        river = self.store.records.snapshot(state['id'])
        self.assertNotIn('targets', river['session'])
        receipt = json.loads(self.store.records.content(state['id'], river['blocks'][-2]['id'])['text'])
        self.assertEqual(receipt['result_id'], path.relative_to(self.root).as_posix())

    def test_report_failure_is_terminal_and_host_scope_still_requires_hosts(self):
        item = choose(self.root, 'feast/report/retention-summary')
        with patch('recipe_reports._run_report', side_effect=OSError('synthetic storage failure')):
            with self.assertRaises(OSError):
                run_report(self.root, item, [])
        (state,) = self.store.list()
        self.assertEqual(state['status'], 'unknown')
        self.assertTrue(state['completed_at'])
        with self.assertRaises(ConfigError):
            self.store.begin(reference='fixture', title='fixture', version='1.0.0',
                             fingerprint='a' * 64, stages=[{'id': 'run', 'executor': 'python'}],
                             hosts=[], trigger='cli')
        with self.assertRaises(ConfigError):
            stages({'runner': {'contract': 'python-report'}, 'execution': {
                'version': '0.1.0', 'stages': [{'id': 'first', 'executor': 'python'},
                                             {'id': 'second', 'executor': 'python'}]}})

    def test_execution_receipts_preserve_observation_and_existing_workflow_digests(self):
        from retention_replay import raw_digest
        report = {'status': 'success', 'data': {'value': 7},
                  'river': {'session_id': 'original-workflow'}, 'execution_id': 'original-id'}
        before = raw_digest(report)
        report['execution_receipt'] = {'schema_version': '0.1.0',
            'execution_id': 'receipt-id', 'execution_status': 'success', 'river': {}}
        self.assertEqual(raw_digest(report), before)
        report['river'] = {'session_id': 'changed-evidence'}
        self.assertNotEqual(raw_digest(report), before)
