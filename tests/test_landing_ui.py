"""Synthetic Home/Hosts/Profiles data, redaction and keyboard workflows."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import checkout_info
import landing_ui as home
import management_view as view
import opsfeast
try:
    import textual
except ImportError:
    textual = None


class DataTests(unittest.TestCase):
    def test_empty_arguments_and_cli_help(self):
        with patch.object(home, 'launch', return_value=0) as launch:
            self.assertEqual(opsfeast.main([]), 0)
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
                opsfeast.main(['--help'])
            self.assertEqual(result.exception.code, 0)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                opsfeast.main(['unknown'])
            self.assertEqual(result.exception.code, 2)
            launch.assert_called_once()

    def test_launch_prerequisites(self):
        with patch.object(sys.stdin, 'isatty', return_value=False), patch.object(home, 'make_home_class') as make, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(home.launch(), 2)
            make.assert_not_called()
        with patch.object(sys.stdin, 'isatty', return_value=True), patch.object(sys.stdout, 'isatty', return_value=True), patch.object(home, 'make_home_class', side_effect=ImportError), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(home.launch(), 1)

    def test_version_download_record_and_timezone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'VERSION').write_text('0.1.0.dev0\n')
            self.assertEqual(checkout_info.information(root)['downloaded_at'], 'Not recorded')
            checkout_info.record_download(root, '2026-10-14T12:00:00+08:00', 'synthetic source')
            self.assertEqual(checkout_info.information(root)['downloaded_at'], '2026-10-14T12:00:00+08:00')
            with self.assertRaises(ValueError):
                checkout_info.record_download(root, '2026-10-14T12:00:00+08:00', 'other')
            with self.assertRaises(ValueError):
                checkout_info.timestamp('2026-10-14T12:00:00')
            (root/checkout_info.RECEIPT).write_text('bad')
            self.assertEqual(checkout_info.information(root)['downloaded_at'], 'Invalid download record')
            (root/checkout_info.RECEIPT).unlink()
            (root/checkout_info.RECEIPT).symlink_to(root/'VERSION')
            with self.assertRaises(ValueError):
                checkout_info.record_download(root, '2026-10-14T12:00:00+08:00', 'other')
            self.assertEqual(checkout_info.information(root)['downloaded_at'], 'Invalid download record')

    def test_recursive_mask_preserves_input(self):
        data = {'connection': {'password': 'fixture-secret', 'hostname': 'host.example'},
                'users': {'alice': {'password': 'other-fixture', 'vars': {'su': {'password': 'su-fixture'}}}},
                'vars': {'sudo': {'password': 'sudo-fixture'}, 'api_token': 'token-fixture'},
                'list': [{'passphrase':'key-fixture'}], 'enabled': False}
        sanitized = view.masked(data)
        text = json.dumps(sanitized)
        for secret in ('fixture-secret','other-fixture','su-fixture','sudo-fixture','token-fixture','key-fixture'):
            self.assertNotIn(secret, text)
        self.assertEqual(sanitized['connection']['hostname'], 'host.example')
        self.assertEqual(data['connection']['password'], 'fixture-secret')
        self.assertFalse(sanitized['enabled'])

    def test_host_includes_sources_and_safe_parse_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'hosts.yaml').write_text('include: [extra.yaml]\nhosts:\n  local:\n    connection: {local: true}\n')
            extra = root/'extra.yaml'
            extra.write_text('hosts:\n  remote:\n    connection: {hostname: fixture.example, password: fixture-secret}\n')
            with patch.object(opsfeast, 'load_profiles', return_value={'default_profile':'main'}), patch.object(opsfeast,'resolve_root',return_value=root):
                snapshot = view.hosts_snapshot()
                self.assertEqual([r['host'] for r in snapshot['hosts']], ['remote','local'])
                self.assertEqual(snapshot['hosts'][0]['source'], str(extra.resolve()))
                self.assertNotIn('fixture-secret', json.dumps(snapshot))
                extra.write_text('hosts: [fixture-secret: malformed')
                error = view.hosts_snapshot()
                self.assertFalse(error['hosts'])
                self.assertNotIn('fixture-secret', json.dumps(error))

    def test_profile_switch_validation_and_write_failure(self):
        data = {'schema_version':2,'default_profile':'main','profiles':{'main':{'root':'x'},'other':{'root':'y'}}}
        with patch.object(opsfeast,'load_profiles',side_effect=lambda: json.loads(json.dumps(data))), \
                patch.object(opsfeast,'registered_root') as validate, patch.object(opsfeast,'save_profiles') as save:
            opsfeast.set_default_profile('other')
            validate.assert_called_once()
            self.assertEqual(save.call_args.args[0]['default_profile'], 'other')
            self.assertEqual(data['default_profile'],'main')
        with patch.object(opsfeast,'load_profiles',return_value=data), \
                patch.object(opsfeast,'registered_root',side_effect=opsfeast.ConfigError('invalid')), patch.object(opsfeast,'save_profiles') as save:
            with self.assertRaises(opsfeast.ConfigError): opsfeast.set_default_profile('other')
            save.assert_not_called()
            self.assertEqual(data['default_profile'],'main')

    def test_document_allowlist(self):
        self.assertIn('OpsFeast', home.document('README.md'))
        with self.assertRaises(ValueError): home.document('../hosts.yaml')

    def test_grouped_hosts_scalar_multiple_and_ungrouped(self):
        entries = [
            {'host': 'one', 'settings': {'group': ['web', 'production', 'web']}},
            {'host': 'two', 'settings': {'group': 'web'}},
            {'host': 'solo', 'settings': {}},
            {'host': 'named', 'settings': {'group': 'Ungrouped'}},
        ]
        self.assertEqual(view.grouped_hosts(entries), {
            'web': ['one', 'two'], 'production': ['one'], None: ['solo'], 'Ungrouped': ['named']})

    def test_user_accounts_explicit_alias_and_local(self):
        self.assertEqual(view.user_accounts({'connection': {'user':'operator'}, 'users': {'alice':{}}}),
                         ('operator', ['operator','alice']))
        self.assertEqual(view.user_accounts({'connection': {'ssh_config_alias':'fixture'}, 'users': {'alice':{}}}),
                         (None, ['alice']))
        with patch('getpass.getuser', return_value='operator'):
            self.assertEqual(view.user_accounts({'connection':{'hostname':'fixture'}}), ('operator',['operator']))
        import os,pwd
        login, accounts = view.user_accounts({'connection':{'local':True}})
        self.assertEqual(login,pwd.getpwuid(os.geteuid()).pw_name)
        self.assertEqual(accounts,[login])


@unittest.skipUnless(textual, 'install requirements-tui.txt for homepage tests')
class NavigationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import recipe_browser
        from browser_fixture import snapshot
        browser = patch.object(recipe_browser, 'snapshot', side_effect=snapshot)
        browser.start()
        self.addCleanup(browser.stop)

    async def test_grouped_sidebar_layout_and_shared_host_settings(self):
        from textual.widgets import RichLog, Tree
        profiles = {'profiles': [], 'message': 'fixture'}
        hosts = {'profile': 'main', 'message': 'fixture', 'default_user_icon': '👤', 'user_icons': {'operator': '👩', 'alice': '★'}, 'hosts': [
            {'host': 'shared', 'source': 'fixture.yaml', 'default_user_icon': '★', 'settings': {'group': ['web', 'production'], 'password': '********', 'icon': '🐧',
             'connection': {'hostname': 'fixture', 'user': 'operator'}, 'users': {'alice': {'icon': '♠'}}}},
            {'host': 'solo', 'source': 'fixture.yaml', 'settings': {}},
        ]}
        hosts['groups'] = {
            'web': {'label': 'WEB [SERVERS]', 'description': 'Synthetic web servers', 'hosts': ['shared']},
            'production': {'label': 'production', 'description': '', 'hosts': ['shared']},
            'empty': {'label': 'empty', 'description': '', 'hosts': []}}
        app = home.make_home_class()()
        async def collect(): app.finish('{"recipes": []}', 0)
        with patch.object(view, 'profiles_snapshot', return_value=profiles), \
                patch.object(view, 'hosts_snapshot', return_value=hosts), patch.object(app, 'collect', side_effect=collect):
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause(0.1)
                app.activate_section('hosts-pane')
                await pilot.pause(0.05)
                tree = app.query_one('#host-list', Tree)
                details = app.query_one('#host-details', RichLog)
                self.assertLessEqual(tree.region.right, details.region.x)
                self.assertGreater(details.region.width, 30)
                self.assertEqual([node.label.plain for node in tree.root.children],
                                 ['WEB [SERVERS] (web)', 'production', 'empty', 'Ungrouped (no group)'])
                for _ in range(20):
                    if app.host_cursor_ready:
                        break
                    await pilot.pause()
                self.assertTrue(app.host_cursor_ready)
                tree.move_cursor(tree.root.children[0])
                await pilot.pause()
                self.assertIn('Synthetic web servers', '\n'.join(line.text for line in details.lines))
                self.assertEqual(tree.root.children[0].data, ('group', 'web'))
                with patch.object(app, 'push_screen') as push:
                    app.action_host_menu()
                    push.assert_not_called()
                self.assertEqual(tree.root.children[0].children[0].label.plain, '🐧 shared')
                self.assertEqual([node.label.plain for node in tree.root.children[0].children[0].children],
                                 ['👩 operator (login)', '♠ alice'])
                for branch in tree.root.children[:2]:
                    tree.select_node(branch.children[0])
                    await pilot.pause()
                    text = '\n'.join(line.text for line in details.lines)
                    self.assertIn('shared', text)
                    self.assertIn('********', text)
                tree.select_node(tree.root.children[3].children[0])
                await pilot.pause()
                self.assertIn('solo', '\n'.join(line.text for line in details.lines))

    async def test_hosts_arrows_without_mouse_or_tab_focus(self):
        from textual.widgets import Tree, RichLog, TabbedContent
        profiles = {'profiles': [], 'message': 'fixture'}
        hosts = {'profile': 'main', 'message': 'fixture', 'hosts': [
            {'host': name, 'source': 'fixture.yaml', 'settings': {'label': name, 'password': '********'}}
            for name in ('first', 'second', 'third')]}
        for size in ((80, 24), (100, 36)):
            with self.subTest(size=size):
                app = home.make_home_class()()
                async def collect(): app.finish('{"recipes": []}', 0)
                with patch.object(view, 'profiles_snapshot', return_value=profiles), \
                        patch.object(view, 'hosts_snapshot', return_value=hosts), \
                        patch.object(app, 'collect', side_effect=collect), \
                        patch.object(opsfeast, 'set_default_profile') as switch:
                    async with app.run_test(size=size) as pilot:
                        await pilot.pause(0.1)
                        await pilot.press('right', 'right', 'right')
                        tabs = app.query_one('#workbench-tabs', TabbedContent)
                        self.assertEqual(tabs.active, 'hosts-pane')
                        await pilot.press('down')
                        table = app.query_one('#host-list', Tree)
                        self.assertIs(app.focused, table)
                        self.assertEqual(table.cursor_node.data, 'second')
                        await pilot.pause()
                        log = app.query_one('#host-details', RichLog)
                        self.assertIn('second', '\n'.join(line.text for line in log.lines))
                        await pilot.press('down', 'up')
                        self.assertEqual(table.cursor_node.data, 'second')
                        await pilot.press('ctrl+tab', 'ctrl+shift+tab')
                        self.assertEqual(tabs.active, 'hosts-pane')
                        await pilot.press('up')
                        self.assertEqual(table.cursor_node.data, 'first')
                        switch.assert_not_called()

    async def test_first_keyboard_cycle_and_hosts_are_sanitized(self):
        from textual.widgets import Tree, RichLog, TabbedContent, Tabs
        profiles = {'profiles':[{'name':'main','root':'/synthetic','status':'available','default':True}], 'message':'ready'}
        hosts = {'profile':'main','hosts':[{'host':'one','source':'synthetic.yaml','settings':{'connection':{'password':'********'}}}], 'message':'configuration only'}
        app = home.make_home_class()()
        calls=[]
        async def collect():
            calls.append(app.command)
            app.finish('{"recipes": []}',0)
        with patch.object(home, 'overview', return_value='OpsFeast fixture\nDownloaded: Not recorded'), \
                patch.object(view,'profiles_snapshot',return_value=profiles), patch.object(view,'hosts_snapshot',return_value=hosts), \
                patch.object(app,'collect',side_effect=collect):
            async with app.run_test(size=(90,30)) as pilot:
                await pilot.pause(0.1)
                tabs=app.query_one('#workbench-tabs',TabbedContent)
                self.assertEqual(tabs.active,'home-pane')
                self.assertIs(app.focused,tabs.query_one(Tabs))
                for pane in ('profiles-pane','output-pane'):
                    await pilot.press('right')
                    self.assertEqual(tabs.active,pane)
                await pilot.press('ctrl+tab')
                self.assertEqual(tabs.active,'hosts-pane')
                await pilot.press('f1')
                self.assertEqual(tabs.active,'help-pane')
                self.assertEqual(sum(len(node.children) for node in app.query_one('#host-list',Tree).root.children),1)
                log=app.query_one('#host-details',RichLog)
                self.assertIn('********','\n'.join(line.text for line in log.lines))
                await pilot.click(tabs.get_tab('profiles-pane'))
                self.assertEqual(tabs.active,'profiles-pane')
                self.assertEqual(len(calls),1)

    async def test_switch_by_enter_refreshes_hosts_and_preserves_recipe_scope(self):
        from textual.widgets import DataTable, Input, Select, TabbedContent
        state={'name':'main'}
        def profiles():
            return {'profiles':[{'name':name,'root':'/synthetic/'+name,'status':'available','default':state['name']==name} for name in ('main','other')], 'message':'ready'}
        def hosts():
            return {'profile':state['name'],'hosts':[{'host':state['name']+'-host','source':'synthetic.yaml','settings':{}}], 'message':'ready'}
        app=home.make_home_class()()
        async def collect():app.finish('{}',0)
        def switch(name):state['name']=name
        with patch.object(view,'profiles_snapshot',side_effect=profiles), patch.object(view,'hosts_snapshot',side_effect=hosts), \
                patch.object(opsfeast,'set_default_profile',side_effect=switch) as select, patch.object(app,'collect',side_effect=collect):
            async with app.run_test(size=(100,36)) as pilot:
                await pilot.pause(0.1)
                app.query_one('#scope',Select).value='root'
                app.query_one('#location',Input).value='/explicit/recipe-root'
                app.activate_section('profiles-pane')
                await pilot.pause(0.05)
                table=app.query_one('#profile-list',DataTable)
                table.focus()
                await pilot.press('down')
                select.assert_not_called()
                await pilot.press('enter')
                await pilot.pause(0.1)
                select.assert_called_once_with('other')
                self.assertIn('other-host',app.host_entries)
                self.assertEqual(table.cursor_row, 1)
                self.assertEqual(app.query_one('#scope',Select).value,'root')
                self.assertEqual(app.query_one('#location',Input).value,'/explicit/recipe-root')
                with patch.object(opsfeast, 'set_default_profile', side_effect=OSError('fixture-private-error')):
                    app.request_profile_switch('main')
                    await pilot.pause(0.1)
                self.assertEqual(state['name'], 'other')
                self.assertIn('other-host', app.host_entries)
                from textual.widgets import Static
                status = str(app.query_one('#profiles-status', Static).content)
                self.assertIn('OSError', status)
                self.assertNotIn('fixture-private-error', status)
                app.profile_entries['missing'] = {'status': 'missing'}
                app.request_profile_switch('missing')
                select.assert_called_once()
