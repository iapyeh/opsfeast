"""Public synthetic UI/transport tests; no real hosts or privileged operations."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import terminal_events as events
import terminal_ui as ui
import opsfeast
import run_recipe

try:
    import textual
except ImportError:
    textual = None


class TransportTests(unittest.TestCase):
    def test_events_are_opt_in_and_round_trip_literal_values(self):
        out = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(out):
            events.emit('stage', host='host-01', stage='connecting')
        self.assertEqual(out.getvalue(), '')
        with patch.dict(os.environ, {'OPSFEAST_TUI_EVENTS': '1'}), contextlib.redirect_stderr(out):
            events.emit('stage', host='[red]測試', stage='waiting\nnext')
        event = events.decode(out.getvalue().rstrip('\n'))
        self.assertEqual(event['host'], '[red]測試')
        self.assertEqual(event['stage'], 'waiting\nnext')
        for line in ('plain stderr', events.PREFIX + 'bad', events.PREFIX + '[]', events.PREFIX + '{}'):
            self.assertIsNone(events.decode(line))

    def test_argument_forwarding_and_readonly_catalog_json(self):
        args = ['inventory/system', '--host', 'host-01', '--var', 'label=--tui-value', '--tui']
        child = ui.child_arguments(Path('run_recipe.py'), args)
        self.assertEqual(child, args[:-1] + ['--verbose'])
        self.assertEqual(ui.child_arguments(Path('run_recipe.py'), ['x', '--quiet', '--tui']), ['x', '--quiet'])
        self.assertEqual(ui.child_arguments(Path('opsfeast.py'), ['recipes', 'list', '--checkout-only', '--tui']),
                         ['recipes', 'list', '--checkout-only', '--json'])
        for quiet in ('--quiet', '-q'):
            invocation = ['test-connection', '--all', quiet, '--tui']
            self.assertEqual(ui.child_arguments(Path('opsfeast.py'), invocation), invocation[:-1])
        for args in (['init', '--tui'], ['use', '--tui'], ['check', '--tui', '--tui']):
            with self.assertRaises(ValueError):
                ui.child_arguments(Path('opsfeast.py'), args)

    def test_nonterminal_rejection_before_execution(self):
        with patch.object(sys.stdin, 'isatty', return_value=False), patch.object(ui, 'make_app_class') as factory, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(opsfeast.main(['check', '--tui']), 2)
            self.assertEqual(run_recipe.main(['inventory/system', '--host', 'h', '--tui']), 2)
            factory.assert_not_called()

    def test_missing_dependency_before_execution(self):
        with patch.object(sys.stdin, 'isatty', return_value=True), patch.object(sys.stdout, 'isatty', return_value=True), \
                patch.object(ui, 'make_app_class', side_effect=ImportError), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(ui.launch(Path('opsfeast.py'), ['check', '--tui']), 1)
        self.assertIn('requirements-tui.txt', err.getvalue())

    def test_status_and_diagnostic_rows(self):
        report = {'tests': {'test-sudo': {'status': 'skipped'}, 'test-su': {'status': 'failed'}}}
        self.assertEqual([ui.reported_status(item) for _, item in ui.report_rows(report)], ['skipped', 'failed'])
        self.assertEqual(ui.reported_status({'connected': True}), 'unknown')
        self.assertEqual(ui.reported_status({'success': False}), 'failed')
        self.assertEqual(ui.report_rows({'groups': [{'accounts': ['alice', 'root'], 'status': 'partial'}]})[0][0], 'alice / root')

    def test_duplicate_chains_and_inspection_labels(self):
        group = {'accounts': ['alice', 'root'], 'status': 'success'}
        self.assertEqual([key for key, _ in ui.report_rows({'groups': [group, group]})],
                         ['alice / root', 'alice / root [2]'])
        self.assertEqual(ui.report_rows({'recipes': [{'descriptor': {'id': 'check-port'}, 'status': 'success'}]})[0][0], 'check-port')
        self.assertEqual(ui.reported_status({'runnable': True}), 'compatible')

    def test_runner_emits_host_stage_and_preserves_stderr(self):
        output = io.StringIO()
        with patch.dict(os.environ, {'OPSFEAST_TUI_EVENTS': '1'}), contextlib.redirect_stderr(output):
            with run_recipe.reporting(True, '[1/1]', host='host-01'):
                run_recipe.progress('collecting')
        decoded = [events.decode(line) for line in output.getvalue().split('\n')]
        self.assertIn({'kind': 'stage', 'host': 'host-01', 'stage': 'collecting'}, decoded)
        self.assertIn('[1/1] collecting', output.getvalue())

    def test_batch_events_preserve_json_and_partial_retention(self):
        report = {'status': 'success', 'reason_code': 'complete', 'retention': {'status': 'failed'}}
        out, err = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'hosts.yaml').write_text('hosts:\n  one:\n    connection: {local: true}\n  two:\n    connection: {local: true}\n')
            with patch.dict(os.environ, {'OPSFEAST_TUI_EVENTS': '1'}), \
                    patch.object(run_recipe, 'run', return_value=(report, root / 'result.json')), \
                    patch('access_check.check_many', return_value={'status': 'success', 'hosts': []}), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                status = run_recipe.main(['inventory/system', '--all', '--root', str(root), '--threads', '2', '--verbose'])
        self.assertEqual(status, 1)
        self.assertEqual([r['status'] for r in json.loads(out.getvalue())['hosts']], ['success', 'success'])
        decoded = [events.decode(line) for line in err.getvalue().split('\n')]
        completions = [item for item in decoded if item and item['kind'] == 'result']
        self.assertEqual({item['host'] for item in completions}, {'one', 'two'})
        self.assertTrue(all(item['retention']['status'] == 'failed' for item in completions))


@unittest.skipUnless(textual, 'install requirements-tui.txt for headless Textual tests')
class AppTests(unittest.IsolatedAsyncioTestCase):
    async def test_child_streams_and_exit_code(self):
        from textual.widgets import DataTable, Static
        code = "import sys,json; print(json.dumps({'hosts':[{'host':'h','status':'partial','reason_code':'missing','retention':{'status':'failed'}}]})); print('safe failure',file=sys.stderr); sys.exit(1)"
        app = ui.make_app_class()([sys.executable, '-B', '-c', code])
        async with app.run_test(size=(100, 30)) as pilot:
            for _ in range(100):
                await pilot.pause(0.02)
                if app.done:
                    break
            self.assertTrue(app.done)
            self.assertEqual(app.exit_status, 1)
            self.assertEqual(app.items['h']['status'], 'partial')
            self.assertEqual(app.query_one(DataTable).row_count, 1)
            self.assertIn('exit 1', str(app.query_one('#summary', Static).content))
            await pilot.press('q')
        self.assertEqual(app.return_value, 1)

    async def test_live_rows_literals_and_final_states(self):
        from textual.widgets import DataTable, RichLog
        app = ui.make_app_class()([sys.executable, '-B', '-c', 'import time; time.sleep(0.5)'])
        async with app.run_test(size=(80, 24)) as pilot:
            app.event({'kind': 'selected', 'hosts': ['[red]測試', 'second']})
            app.event({'kind': 'stage', 'host': 'second', 'stage': 'collecting'})
            self.assertEqual(app.items['second']['status'], 'running')
            await pilot.press('q', 'ctrl+q', 'ctrl+c')
            self.assertFalse(app.done)
            app.event({'kind': 'result', 'host': 'second', 'status': 'failed', 'reason_code': 'cleanup_failed'})
            report = {'hosts': [{'host': '[red]測試', 'status': 'skipped', 'reason_code': 'host_disabled'},
                                {'host': 'second', 'status': 'failed', 'reason_code': 'cleanup_failed'}], 'excluded_hosts': ['third']}
            app.finish(json.dumps(report), 1)
            table = app.query_one(DataTable)
            self.assertEqual(table.row_count, 2)
            self.assertEqual(table.get_row_at(0)[0].plain, '[red]測試')
            table.move_cursor(row=1)
            await pilot.pause()
            self.assertTrue(app.query_one('#details', RichLog).lines)
            await pilot.pause(0.6)

    async def test_non_json_error_and_no_false_success(self):
        app = ui.make_app_class()([sys.executable, '-B', '-c', "import sys; print('ERROR: bad config',file=sys.stderr); sys.exit(2)"])
        async with app.run_test(size=(60, 20)) as pilot:
            for _ in range(100):
                await pilot.pause(0.02)
                if app.done:
                    break
            self.assertTrue(app.done)
            self.assertEqual(app.exit_status, 2)
            self.assertEqual(app.items, {})


if __name__ == '__main__':
    unittest.main()
