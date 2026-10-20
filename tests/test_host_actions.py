"""Synthetic host modal actions; real SSH and recipes are never executed."""
import asyncio
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import host_actions
import landing_ui as home
import management_view as view
try:
    import textual
except ImportError:
    textual = None


class CommandTests(unittest.TestCase):
    def test_user_command_scope(self):
        for action in ('test-su', 'test-sudo'):
            command = host_actions.command_for(action, 'host-01', '/fixture/root', user='alice')
            self.assertEqual(command[3:6], [action, 'host-01', 'alice'])
            self.assertIn('--root=/fixture/root', command)
            self.assertNotIn('--chain', command)
            if action == 'test-sudo': self.assertIn('--run-as=root', command)
        with self.assertRaises(Exception):
            host_actions.command_for('test-su', 'h', '/root', user='--root')

    def test_exact_host_root_and_literal_recipe(self):
        command = host_actions.command_for('test-connection', 'host-01', '/fixture/root with spaces')
        self.assertEqual(command[-4:], ['test-connection', 'host-01', '/fixture/root with spaces', '--verbose'])
        command = host_actions.command_for('run recipe', 'host-01', '/fixture/root', 'custom; echo example')
        self.assertIn('custom; echo example', command)
        self.assertEqual(command[command.index('--host')+1], 'host-01')
        self.assertNotIn('--all', command)
        for action, recipe in [('run recipe',''), ('cancel',''), ('unknown','path')]:
            with self.assertRaises(ValueError): host_actions.command_for(action, 'h', '/root', recipe)


class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_streams_and_nonzero_code(self):
        stages, logs = [], []
        from terminal_events import PREFIX
        code = f"import sys,json; print({(PREFIX+json.dumps({'kind':'stage','stage':'connecting'}))!r},file=sys.stderr); print('safe error',file=sys.stderr); print('{{\"status\":\"failed\"}}'); sys.exit(1)"
        status, output = await host_actions.execute([sys.executable,'-B','-c',code], stages.append, logs.append)
        self.assertEqual(status,1)
        self.assertEqual(json.loads(output)['status'],'failed')
        self.assertEqual(stages,['connecting'])
        self.assertEqual(logs,['safe error'])


@unittest.skipUnless(textual, 'install requirements-tui.txt for modal UI tests')
class DialogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import recipe_browser
        from browser_fixture import snapshot
        browser = patch.object(recipe_browser, 'snapshot', side_effect=snapshot)
        browser.start()
        self.addCleanup(browser.stop)

    async def test_user_nodes_and_login_sensitive_menus(self):
        from textual.widgets import SelectionList, Tree
        hosts = {'profile':'main', 'root':'/fixture/root', 'message':'fixture', 'hosts': [
            {'host':'one','source':'fixture.yaml','settings':{'connection':{'hostname':'fixture.example','user':'operator'},
             'users':{'operator':{},'alice':{'password':'********'}}}}]}
        app = home.make_home_class()()
        async def collect(): app.finish('{"recipes":[]}',0)
        async def execute(command, progress, log): return 0, '{"status":"success"}'
        with patch.object(view,'profiles_snapshot',return_value={'profiles':[],'message':'fixture'}), \
                patch.object(view,'hosts_snapshot',return_value=hosts), patch.object(app,'collect',side_effect=collect), \
                patch.object(host_actions,'execute',side_effect=execute) as run:
            async with app.run_test(size=(90,30)) as pilot:
                await pilot.pause(0.1)
                app.activate_section('hosts-pane')
                await pilot.pause(0.05)
                tree = app.query_one('#host-list',Tree)
                host = tree.root.children[0].children[0]
                self.assertEqual([node.data for node in host.children], [('user','one','operator'),('user','one','alice')])
                tree.move_cursor(host.children[0])
                tree.focus()
                await pilot.pause(0.05)
                await pilot.press('enter')
                menu = app.screen.query_one(SelectionList)
                self.assertEqual([menu.get_option_at_index(i).value for i in range(menu.option_count)], ['test-sudo','cancel'])
                await pilot.press('escape')
                run.assert_not_called()
                tree.move_cursor(host.children[1])
                tree.focus()
                await pilot.pause(0.05)
                await pilot.press('enter')
                menu = app.screen.query_one(SelectionList)
                self.assertEqual([menu.get_option_at_index(i).value for i in range(menu.option_count)], ['test-su','test-sudo','cancel'])
                await pilot.press('enter')
                await pilot.pause(0.1)
                self.assertEqual(run.call_args.args[0][3:6], ['test-su','one','alice'])
                await pilot.press('escape')
                tree.move_cursor(host.children[0])
                tree.focus()
                await pilot.pause(0.05)
                await pilot.press('enter','enter')
                await pilot.pause(0.1)
                self.assertEqual(run.call_args.args[0][3:6], ['test-sudo','one','operator'])

    async def test_enter_menu_cancel_recipe_input_and_result(self):
        from textual.widgets import Button, Input, ProgressBar, SelectionList, Tree
        profiles={'profiles':[],'message':'fixture'}
        hosts={'profile':'main','root':'/fixture/root','message':'fixture','hosts':[
            {'host':'host-01','source':'fixture.yaml','settings':{}}]}
        app=home.make_home_class()()
        async def collect(): app.finish('{"recipes":[]}',0)
        completed = asyncio.Event()
        async def execute(command, progress, log):
            progress('synthetic connecting')
            log('synthetic safe warning')
            await completed.wait()
            return 1, json.dumps({'status':'partial','result_path':'/fixture/result.json','retention':{'status':'failed'}})
        with patch.object(view,'profiles_snapshot',return_value=profiles), patch.object(view,'hosts_snapshot',return_value=hosts), \
                patch.object(app,'collect',side_effect=collect), patch.object(host_actions,'execute',side_effect=execute) as run:
            async with app.run_test(size=(90,30)) as pilot:
                await pilot.pause(0.1)
                app.activate_section('hosts-pane')
                await pilot.pause(0.05)
                tree=app.query_one('#host-list',Tree)
                tree.focus()
                await pilot.pause(0.05)
                await pilot.press('enter')
                menu=app.screen.query_one(SelectionList)
                self.assertEqual([menu.get_option_at_index(i).value for i in range(3)], ['test-connection','run recipe','cancel'])
                await pilot.press('down','down','enter')
                await pilot.pause()
                run.assert_not_called()
                self.assertFalse(app.host_operation_busy)
                await pilot.press('enter')
                await pilot.press('down','enter')
                await pilot.pause()
                field=app.screen.query_one(Input)
                self.assertEqual(field.value,'')
                await pilot.press('enter')
                run.assert_not_called()
                field.value='system/inventory/overview'
                await pilot.press('enter')
                await pilot.pause(0.02)
                self.assertTrue(app.host_operation_busy)
                self.assertIsNone(app.screen.query_one(ProgressBar).total)
                self.assertTrue(app.screen.query_one('#close',Button).disabled)
                await pilot.press('escape')
                self.assertTrue(app.screen.query_one('#close',Button).disabled)
                completed.set()
                await pilot.pause(0.15)
                self.assertEqual(run.call_count,1)
                command=run.call_args.args[0]
                self.assertIn('system/inventory/overview',command)
                self.assertIn('--root=/fixture/root',command)
                self.assertIn('host-01',command)
                self.assertEqual(app.screen.exit_code,1)
                self.assertFalse(app.screen.query_one('#close',Button).disabled)
                await pilot.press('escape')
                await pilot.pause()
                self.assertFalse(app.host_operation_busy)
                await pilot.press('enter','enter')
                await pilot.pause(0.15)
                self.assertEqual(run.call_count,2)
                self.assertIn('test-connection',run.call_args.args[0])
