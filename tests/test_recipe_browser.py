"""Source-separated recipe history tests with synthetic local records."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import recipe_browser as browser
from recipe_reports import results
try:
    import textual
except ImportError:
    textual=None


class HistoryTests(unittest.TestCase):
    def test_records_match_source_and_reference_not_shared_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'observations').mkdir()
            for name, source, reference in [('a','repository','system/inventory/overview'), ('b','community','community:system/inventory/overview'), ('old',None,None)]:
                raw={'status':'partial','host_id':'host-'+name,'started_at':'2026-10-14T00:00:00Z',
                     'recipe':{'id':'same-id','source_name':source,'reference':reference}}
                (root/'observations'/f'{name}.json').write_text(json.dumps(raw))
            index=results(root)
            records=browser.history_for({'source':'repository','reference':'system/inventory/overview'},index['results'])
            self.assertEqual(len(records),1)
            self.assertEqual(records[0]['host_id'],'host-a')
            self.assertEqual(records[0]['status'],'partial')
            self.assertEqual(len(index['results']),3)
            self.assertEqual(browser.directory_parts({'directory':'/fixture/recipes/system/inventory/overview'}, {'root':'/fixture/recipes'}), ('system','inventory','overview'))


@unittest.skipUnless(textual,'install requirements-tui.txt')
class BrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_source_roots_and_selected_history(self):
        from textual.widgets import DataTable, RichLog, TabbedContent, Tree
        import recipe_workbench
        data={'catalog':{'status':'success','sources':[
            {'name':'repository','root':'/fixture/repo','status':'available'},
            {'name':'community','root':'/fixture/community','status':'available'}], 'recipes':[
                {'reference':'system/inventory/overview','source':'repository','directory':'/fixture/repo/system/inventory/overview'},
                {'reference':'community:system/inventory/overview','source':'community','directory':'/fixture/community/system/inventory/overview','title':'Community inventory','description':'[red]Literal description','inputs':{'variables':{'sample':{'type':'string'}}},'verification':{'evidence':'synthetic'}}]},
            'history':{'status':'success','errors':[],'results':[
                {'recipe_source':'repository','recipe_reference':'system/inventory/overview','started_at':'2026-10-14T01:00:00Z',
                 'status':'success','host_id':'repo-host','result_id':'repo.json','kind':'operation'},
                {'recipe_source':'community','recipe_reference':'community:system/inventory/overview','started_at':'2026-10-14T02:00:00.123456Z',
                 'status':'failed','host_id':'community-host','result_id':'community.json','kind':'operation'}]},
            'message':'fixture','root':'/fixture/feast'}
        app=recipe_workbench.make_workbench_class()()
        async def collect():app.finish('{}',0)
        with patch.object(browser,'snapshot',return_value=data),patch.object(app,'collect',side_effect=collect):
            async with app.run_test(size=(80,24)) as pilot:
                await pilot.pause(0.1)
                tree=app.query_one('#recipe-tree',Tree)
                table=app.query_one('#recipe-history',DataTable)
                self.assertEqual(len(tree.root.children),2)
                tabs=app.query_one('#recipe-view',TabbedContent)
                self.assertLessEqual(tree.region.right,tabs.region.x)
                self.assertEqual(tabs.active,'info-pane')
                leaf=tree.root.children[1].children[0].children[0].children[0]
                tree.move_cursor(leaf)
                await pilot.pause()
                info=app.query_one('#recipe-info',RichLog)
                text='\n'.join(line.text for line in info.lines)
                self.assertIn('Community inventory',text)
                self.assertIn('[red]Literal description',text)
                self.assertIn('synthetic',text)
                await pilot.click(tabs.get_tab('history-pane'))
                self.assertEqual(tabs.active,'history-pane')
                self.assertEqual(table.row_count,1)
                row=table.get_row_at(0)
                self.assertEqual([cell.plain for cell in row[:3]],[browser.display_started('2026-10-14T02:00:00.123456Z'),'failed','community-host'])
                tree.move_cursor(tree.root.children[0].children[0].children[0].children[0])
                await pilot.pause()
                self.assertEqual(tabs.active,'history-pane')
                self.assertEqual(table.get_row_at(0)[2].plain,'repo-host')
                await pilot.click(tabs.get_tab('info-pane'))
                self.assertIn('repository','\n'.join(line.text for line in info.lines))
                tree.move_cursor(tree.root.children[0])
                await pilot.pause()
                self.assertIn('Select a recipe', '\n'.join(line.text for line in info.lines))


class ExecutionOutputTests(unittest.TestCase):
    def test_original_saved_text_source_checks_and_safe_paths(self):
        from opsfeast import ConfigError
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'observations').mkdir()
            path = root / 'observations' / 'one.json'
            original = '{ "status": "partial", "recipe": {"source_name": "repository", "reference": "system/inventory/overview"}, "host_id": "h", "data": {"literal": "[red]"}}\n'
            path.write_text(original)
            item = {'source': 'repository', 'reference': 'system/inventory/overview'}
            output = browser.execution_output(root, 'observations/one.json', item)
            self.assertEqual(output['original'], original)
            self.assertIn('partial', output['details'])
            for identifier in ('../one.json', '/tmp/one.json', 'observations/missing.json'):
                with self.assertRaises(ConfigError): browser.execution_output(root, identifier, item)
            with self.assertRaises(ConfigError): browser.execution_output(root, 'observations/one.json', {'source': 'community', 'reference': 'system/inventory/overview'})
            path.unlink()
            target = root / 'private.json'
            target.write_text(original)
            path.symlink_to(target)
            with self.assertRaises(ConfigError): browser.execution_output(root, 'observations/one.json', item)


@unittest.skipUnless(textual, 'install requirements-tui.txt')
class ExecutionBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_profile_label_empty_profile_and_selected_execution(self):
        from textual.widgets import DataTable, RichLog, Static, TabbedContent, TabPane, Tree
        from browser_fixture import snapshot
        import landing_ui
        import management_view
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'observations').mkdir()
            data = snapshot()
            data['root'] = str(root)
            data['profile_name'] = 'testops'
            data['catalog']['sources'].append({'name': 'profile', 'root': '/fixture/profile', 'status': 'available'})
            data['history']['results'] = []
            for ref, host in [('first', 'host-a'), ('first', 'host-b'), ('second', 'other-recipe')]:
                name = host + '.json'
                document = {'status': 'success', 'host_id': host, 'recipe': {'source_name': 'repository', 'reference': ref}, 'data': {'literal': '[red]' + host}}
                (root / 'observations' / name).write_text(json.dumps(document))
                data['history']['results'].append({'recipe_source': 'repository', 'recipe_reference': ref, 'host_id': host, 'status': 'success', 'result_id': 'observations/' + name})
            app = landing_ui.make_home_class()()
            async def collect(): app.finish('{"global_action": "catalog"}', 0)
            with patch.object(browser, 'snapshot', return_value=data), patch.object(app, 'collect', side_effect=collect), \
                    patch.object(management_view, 'profiles_snapshot', return_value={'profiles': [], 'message': 'fixture'}), \
                    patch.object(management_view, 'hosts_snapshot', return_value={'hosts': [], 'message': 'fixture'}):
                async with app.run_test(size=(100, 36)) as pilot:
                    await pilot.pause(0.1)
                    app.activate_section('output-pane')
                    await pilot.pause(0.1)
                    tree = app.query_one('#recipe-tree', Tree)
                    self.assertEqual([node.label.plain for node in tree.root.children], ['OpsFeast Bundle (available)'])
                    view = app.query_one('#recipe-view', TabbedContent)
                    self.assertEqual([pane.id for pane in view.query(TabPane) if pane.parent is view.get_pane('info-pane').parent], ['info-pane', 'history-pane'])
                    view.active = 'history-pane'
                    app.query_one('#execution-view', TabbedContent).active = 'execution-original-pane'
                    await pilot.pause(0.1)
                    table = app.query_one('#recipe-history', DataTable)
                    self.assertEqual(table.row_count, 2)
                    table.focus()
                    await pilot.press('down', 'enter')
                    await pilot.pause(0.1)
                    original = app.query_one('#execution-original', RichLog)
                    self.assertIn('host-b', '\n'.join(line.text for line in original.lines))
                    self.assertNotIn('global_action', '\n'.join(line.text for line in original.lines))
                    saved = root / 'observations' / 'other-recipe.json'
                    saved_text = saved.read_text()
                    saved.unlink()
                    tree.move_cursor(tree.root.children[0].children[1])
                    await pilot.pause(0.1)
                    table.focus()
                    await pilot.press('enter')
                    await pilot.pause(0.1)
                    self.assertIn('unavailable', str(app.query_one('#execution-status', Static).content))
                    self.assertEqual(list(original.lines), [])
                    saved.write_text(saved_text)
                    await pilot.press('enter')
                    await pilot.pause(0.1)
                    self.assertIn('other-recipe', '\n'.join(line.text for line in original.lines))
                    self.assertNotIn('host-b', '\n'.join(line.text for line in original.lines))
                    data['catalog']['recipes'].append({'source': 'profile', 'reference': ':custom', 'directory': '/fixture/profile/custom'})
                    await app.refresh_browser()
                    await pilot.pause(0.1)
                    self.assertEqual(tree.root.children[1].label.plain, 'testops (available)')
                    tree.move_cursor(tree.root.children[1].children[0])
                    await pilot.pause(0.1)
                    self.assertEqual(table.row_count, 0)
                    self.assertEqual(list(original.lines), [])


class LocalTimeTests(unittest.TestCase):
    def test_missing_invalid_and_timezone_unknown_are_not_guessed(self):
        self.assertEqual(browser.display_started(None), '(unknown)')
        for value in ('not-a-time', '2026-10-14T02:00:00', '2026-99-14T02:00:00Z'):
            self.assertEqual(browser.display_started(value), '(invalid or unzoned time)')

    def test_system_timezone_offsets_date_rollover_and_dst(self):
        import os
        import time
        if not hasattr(time, 'tzset'):
            self.skipTest('POSIX timezone switching required for synthetic system timezone tests')
        cases = [
            ('Asia/Taipei', '2026-10-14T20:34:56.987654Z', '2026-10-15 04:34:56', 'Time (started, GMT+8)'),
            ('Asia/Kolkata', '2026-10-14T02:00:00+00:00', '2026-10-14 07:30:00', 'Time (started, GMT+5:30)'),
            ('UTC', '2026-10-14T12:00:00.123+08:00', '2026-10-14 04:00:00', 'Time (started, GMT+0)'),
            ('America/New_York', '2026-01-14T02:00:00Z', '2026-01-13 21:00:00', 'Time (started, GMT-5)'),
            ('America/New_York', '2026-07-14T02:00:00Z', '2026-07-13 22:00:00', 'Time (started, GMT-4)'),
        ]
        for zone, original, expected, header in cases:
            with self.subTest(zone=zone, original=original):
                try:
                    with patch.dict(os.environ, {'TZ': zone}):
                        time.tzset()
                        self.assertEqual(browser.display_started(original), expected)
                        self.assertEqual(browser.started_column([original]), header)
                        if zone == 'America/New_York':
                            self.assertEqual(browser.started_column(['2026-01-14T02:00:00Z', '2026-07-14T02:00:00Z']), 'Time (started, GMT-5/GMT-4)')
                finally:
                    time.tzset()
