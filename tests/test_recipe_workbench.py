"""Synthetic workbench forms/routing; no connections or real recipe execution."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import opsfeast
import recipe_cli
import recipe_workbench as workbench
try:
    import textual
except ImportError:
    textual = None


class FormTests(unittest.TestCase):
    def test_only_bare_recipes_routes_to_workbench(self):
        with patch.object(workbench, 'launch', return_value=0) as launch, patch.object(recipe_cli, 'main', return_value=0) as cli:
            self.assertEqual(opsfeast.main(['recipes']), 0)
            launch.assert_called_once()
            for args in (['list'], ['--help'], ['unknown']):
                opsfeast.main(['recipes', *args])
                cli.assert_called_with(args)
            self.assertEqual(launch.call_count, 1)

    def test_nonterminal_and_dependency_fail_before_app(self):
        with patch.object(sys.stdin, 'isatty', return_value=False), patch.object(workbench, 'make_workbench_class') as factory, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(workbench.launch(), 2)
            factory.assert_not_called()
        with patch.object(sys.stdin, 'isatty', return_value=True), patch.object(sys.stdout, 'isatty', return_value=True), patch.object(workbench, 'make_workbench_class', side_effect=ImportError), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(workbench.launch(), 1)

    def test_invocation_form_and_all_exclusions(self):
        fields = {'recipe': 'check/port', 'all': 'true', 'exclude': '["one", "two"]',
                  'variables': '{"port":8888,"label":"hello world"}', 'threads': '4'}
        args = workbench.arguments('run', 'profile', 'main', fields)
        self.assertIn('--all', args)
        self.assertEqual(args[args.index('--exclude') + 1:args.index('--exclude') + 3], ['one', 'two'])
        self.assertIn('port=8888', args)
        self.assertIn('label=hello world', args)
        self.assertIn('--threads=4', args)
        self.assertIn('--verbose', args)
        self.assertNotIn('--tui', args)

    def test_all_forms_parse_through_shared_cli(self):
        values = {'recipe':'report/summary', 'name':'example', 'result_id':'reports/example/result.json',
                  'archive':'/tmp/example.zip', 'destination':'/tmp/candidate', 'output':'/tmp/new.zip',
                  'files':'["recipe.yaml", "main.py"]', 'inputs':'["/tmp/input.json"]'}
        # Stop immediately after argparse; prove forms target the real CLI grammar.
        for action in workbench.ACTIONS:
            with self.subTest(action=action):
                scope = 'checkout' if action in {'list','show','pack','unpack'} else 'root'
                args = workbench.arguments(action, scope, '/tmp/feast', values)
                with patch.object(recipe_cli, 'resolve_root', side_effect=RuntimeError('stop')), \
                        patch.object(recipe_cli, 'catalog', side_effect=RuntimeError('stop')), \
                        patch.object(recipe_cli, 'choose', side_effect=RuntimeError('stop')), \
                        patch.object(recipe_cli, 'unpack', side_effect=RuntimeError('stop')), \
                        contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(recipe_cli.main(args), 1)

    def test_required_fields_scope_and_invalid_lists(self):
        for action, fields in [('run', {}), ('pack', {'recipe':'x'}), ('run', {'recipe':'x', 'hosts':'[1]'}),
                               ('run', {'recipe':'x', 'variables':'[]'})]:
            with self.subTest(action=action, fields=fields), self.assertRaises(ValueError):
                workbench.arguments(action, 'root', '/tmp/feast', fields)
        with self.assertRaises(ValueError):
            workbench.arguments('results-list', 'checkout', '', {})
        with self.assertRaises(ValueError):
            workbench.arguments('list', 'profile', '', {})
        self.assertFalse(workbench.needs_confirmation('list', {}))
        self.assertTrue(workbench.needs_confirmation('list', {'html':'/tmp/new.html'}))
        for action in ('run','jobs-save','jobs-run','pack','unpack'):
            self.assertTrue(workbench.needs_confirmation(action, {}))


@unittest.skipUnless(textual, 'install requirements-tui.txt for workbench UI tests')
class WorkbenchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import recipe_browser
        from browser_fixture import snapshot
        browser = patch.object(recipe_browser, 'snapshot', side_effect=snapshot)
        browser.start()
        self.addCleanup(browser.stop)

    async def test_arrow_keys_select_recipes_on_open_and_return(self):
        from textual.widgets import DataTable, Input, TabbedContent, Tree
        for size in ((80,24),(100,36)):
            with self.subTest(size=size):
                app=workbench.make_workbench_class()()
                async def collect(): app.finish('{}',0)
                with patch.object(app,'collect',side_effect=collect):
                    async with app.run_test(size=size) as pilot:
                        await pilot.pause()  # Drain deferred mount/refresh callbacks before key input.
                        tree=app.query_one('#recipe-tree',Tree)
                        await pilot.press('down')
                        self.assertIs(app.focused,tree)
                        self.assertEqual(tree.cursor_node.data,'second')
                        await pilot.pause()
                        self.assertEqual(app.query_one('#recipe-history',DataTable).row_count,1)
                        app.activate_section('actions-pane')
                        await pilot.pause()
                        field=app.query_one('#field-query',Input)
                        field.focus()
                        await pilot.press('down')
                        self.assertIs(app.focused,field)
                        app.activate_section('output-pane')
                        await pilot.pause()
                        await pilot.press('down')
                        self.assertEqual(tree.cursor_node.data,'third')

    async def test_catalog_on_open_and_form_switch(self):
        from textual.widgets import Select, Input, TabbedContent
        App = workbench.make_workbench_class()
        app = App()
        async def synthetic_collect():
            app.finish(json.dumps({'recipes':[{'reference':'check/port','runnable':True}]}), 0)
        with patch.object(app, 'collect', side_effect=synthetic_collect):
            async with app.run_test(size=(100, 36)) as pilot:
                await pilot.pause()
                self.assertEqual(app.command[-3:], ['list','--checkout-only','--json'])
                self.assertTrue(app.done)
                app.query_one('#workbench-tabs', TabbedContent).active = 'actions-pane'
                app.query_one('#action', Select).value = 'run'
                await pilot.pause()
                self.assertTrue(app.query_one('#field-hosts', Input).display)
                self.assertFalse(app.query_one('#field-files', Input).display)

    async def test_write_review_cancel_and_confirm(self):
        from textual.widgets import Select, Input, TabbedContent
        app = workbench.make_workbench_class()()
        commands = []
        async def synthetic_collect():
            commands.append(app.command)
            app.finish('{}', 0)
        with patch.object(app, 'collect', side_effect=synthetic_collect):
            async with app.run_test(size=(100, 40)) as pilot:
                await pilot.pause()
                app.query_one('#workbench-tabs', TabbedContent).active = 'actions-pane'
                app.query_one('#action', Select).value = 'run'
                app.query_one('#scope', Select).value = 'root'
                app.query_one('#location', Input).value = '/tmp/synthetic-feast'
                app.query_one('#field-recipe', Input).value = 'check/port'
                app.query_one('#field-hosts', Input).value = '["host-01"]'
                await pilot.pause()
                from textual.widgets import Button
                app.on_button_pressed(Button.Pressed(app.query_one('#apply', Button)))
                await pilot.pause()
                self.assertEqual(len(commands), 1)
                app.screen.dismiss(False)
                await pilot.pause()
                self.assertEqual(len(commands), 1)
                app.on_button_pressed(Button.Pressed(app.query_one('#apply', Button)))
                await pilot.pause()
                app.screen.dismiss(True)
                await pilot.pause()
                self.assertEqual(len(commands), 2)
                self.assertIn('host-01', commands[-1])
                self.assertTrue(app.done)
                self.assertEqual(app.query_one('#workbench-tabs', TabbedContent).active, 'actions-pane')
                self.assertEqual(app.query_one('#action-view', TabbedContent).active, 'action-output-pane')
