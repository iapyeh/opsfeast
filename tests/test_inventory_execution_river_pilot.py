"""Run the migrated inventory Recipe through CLI and schedule with fake Sessions."""
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from threading import Barrier, Event
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from opsfeast import Instance
from opsfeast.staged_execution import Executions
from inventory_output_fixture import framed
from test_routine_meals import Transport

import inventory_jobs
from observation_runs import show
from recipe_cli import main


REFERENCE = 'system/inventory/system'
HOSTS = ['test-a', 'test-b']


class SystemTransport(Transport):
    def exec_command(self, argv, **kwargs):
        if 'date +%Z' in argv[-1]:
            return SimpleNamespace(stdout=framed(argv[-1], 'UTC\n\n__OPSFEAST_EXIT_0\n'), stderr='', exitcode=0)
        return super().exec_command(argv, **kwargs)


class InventoryExecutionRiverTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        product = Path(temp.name)
        instance = Instance.open(product)
        with redirect_stdout(io.StringIO()):
            self.profile = instance.init_profile()
        self.root = self.profile.root
        (self.root / 'hosts.yaml').write_text(
            'hosts:\n'
            '  test-a: {connection: {local: true}}\n'
            '  test-b: {connection: {local: true}}\n'
            'default:\n'
            '  recipes:\n'
            f'    {REFERENCE}: {{enabled: true}}\n',
            encoding='utf-8',
        )
        mocked_instance = Mock()
        mocked_instance.open.return_value = instance
        self.enterContext(patch('opsfeast.staged_execution.Instance', mocked_instance))
        self.store = Executions(self.root)

    def fake_connection(self, *, fail_second=False):
        overlapped = Event()
        rendezvous = Barrier(len(HOSTS), action=overlapped.set, timeout=10)

        @contextmanager
        def connect(config, host, session_class, timeout, report):
            (state,) = self.store.list()
            self.assertEqual(state['status'], 'running')
            self.assertEqual(state['hosts'], HOSTS)
            self.assertEqual(state['stages'][0]['id'], 'collect')
            history = self.store.records.list_sessions('main / ' + host)['sessions']
            self.assertEqual([row['session_id'] for row in history], [state['id']])
            rendezvous.wait()
            if fail_second and host == HOSTS[1]:
                raise OSError('synthetic connection failure')
            report['connected'] = True
            yield SystemTransport()
        return connect, overlapped

    def assert_history(self, execution_id, expected, trigger):
        state = self.store.read(execution_id)
        self.assertEqual(state['status'], expected)
        self.assertEqual(state['trigger'], trigger)
        self.assertEqual(state['river']['session_id'], execution_id)
        self.assertEqual(show(self.root, state['observation_run_id'])['status'], expected)
        view = self.store.records.snapshot(execution_id)
        self.assertEqual({target['host_id'] for target in view['session']['targets']}, set(HOSTS))
        events = self.store.records.events(execution_id, 0)
        self.assertEqual([event['seq'] for event in events], list(range(1, view['seq'] + 1)))
        for index, host in enumerate(HOSTS):
            blocks = [block for block in view['blocks'] if block.get('target_id') == 'main / ' + host]
            self.assertGreaterEqual(len(blocks), 2)
            receipt = json.loads(self.store.records.content(execution_id, blocks[-1]['id'])['text'])
            self.assertEqual(receipt['status'], 'failed' if index == 1 and expected == 'partial' else 'success')
            result = json.loads((self.root / receipt['result_id']).read_text())
            self.assertEqual(result['observation_run_id'], state['observation_run_id'])
        retained = {item['host_id']: item['data'] for item in self.profile.retention.query()['records']}
        self.assertEqual(set(retained), set(HOSTS))
        self.assertEqual(retained[HOSTS[0]]['status'], 'success')
        if expected == 'partial':
            self.assertEqual(retained[HOSTS[1]]['status'], 'failed')

    def test_cli_two_workers_and_partial_result_share_one_river(self):
        connect, overlapped = self.fake_connection(fail_second=True)
        with patch('opsfeast.routine_execution.connected', connect), redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()):
            code = main(['run', REFERENCE, '--root', str(self.root), '--host', *HOSTS, '--threads', '2', '--json'])
        self.assertEqual(code, 1, output.getvalue())
        result = json.loads(output.getvalue())
        self.assertTrue(overlapped.is_set())
        self.assert_history(result['execution_id'], 'partial', 'cli')

    def test_saved_inventory_query_uses_staged_execution(self):
        @contextmanager
        def connect(config, host, session_class, timeout, report):
            (state,) = self.store.list()
            self.assertEqual(state['hosts'], [host])
            self.assertEqual(state['status'], 'running')
            report['connected'] = True
            yield SystemTransport()

        with patch('opsfeast.routine_execution.connected', connect):
            result = inventory_jobs.collect_host(
                self.root, HOSTS[0], reference=REFERENCE, properties=['system.hostname'], save=True,
            )
        state = self.store.read(result['execution_id'])
        self.assertEqual(state['status'], 'success', result)
        self.assertEqual(state['stages'][0]['observation_run_id'], result['observation_run_id'])

    def test_scheduled_workers_share_one_river_without_web(self):
        (self.root / 'inventory.yaml').write_text(json.dumps({
            'schema_version': '0.1.0', 'defaults': {},
            'hosts': {host: {'enabled': True, 'jobs': {}, 'recipe': REFERENCE} for host in HOSTS},
        }), encoding='utf-8')
        dry = inventory_jobs.dispatch(self.root, dry_run=True)
        self.assertEqual([row['status'] for row in dry['hosts']], ['due', 'due'])
        self.assertFalse(self.store.directory.exists())
        connect, overlapped = self.fake_connection()
        with patch('opsfeast.routine_execution.connected', connect):
            result = inventory_jobs.dispatch(self.root, threads=2)
        self.assertTrue(overlapped.is_set(), result)
        self.assertEqual(result['status'], 'success', result)
        (execution,) = result['executions']
        self.assert_history(execution['id'], 'success', 'scheduled')
