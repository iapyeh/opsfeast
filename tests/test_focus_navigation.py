"""Escape navigates focus tiers without executing operations or losing selections."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import landing_ui as home
import management_view as management
import recipe_browser
try:
    import textual
except ImportError:
    textual=None


@unittest.skipUnless(textual,'install requirements-tui.txt')
class EscapeTests(unittest.IsolatedAsyncioTestCase):
    async def test_content_sidebar_tabs_and_left_to_profiles(self):
        from textual.widgets import Input, RichLog, TabbedContent, Tabs, Tree
        from browser_fixture import snapshot
        app=home.make_home_class()()
        async def collect():app.finish('{}',0)
        with patch.object(recipe_browser,'snapshot',side_effect=snapshot), \
                patch.object(management,'profiles_snapshot',return_value={'profiles':[],'message':'fixture'}), \
                patch.object(management,'hosts_snapshot',return_value={'hosts':[{'host':'h','source':'fixture','settings':{}}],'message':'fixture'}), \
                patch.object(app,'collect',side_effect=collect):
            async with app.run_test(size=(90,30)) as pilot:
                await pilot.pause(0.1)
                tabs=app.query_one('#workbench-tabs',TabbedContent)
                app.activate_section('output-pane')
                await pilot.pause(0.05)
                tree=app.query_one('#recipe-tree',Tree)
                node=tree.root.children[0].children[1]
                tree.move_cursor(node)
                info=app.query_one('#recipe-info',RichLog)
                info.focus()
                await pilot.pause(0.05)
                self.assertIs(app.focused,info)
                app.focus_recipe_browser()  # Simulate delayed tab activation.
                self.assertIs(app.focused,info)
                await pilot.press('escape')
                self.assertIs(app.focused,tree)
                app.focus_recipe_browser()
                self.assertIs(app.focused,tree)
                self.assertIs(tree.cursor_node,node)
                await pilot.press('escape')
                self.assertIs(app.focused,tabs.query_one(Tabs))
                self.assertEqual(tabs.active,'output-pane')
                await pilot.press('left')
                self.assertEqual(tabs.active,'profiles-pane')
                app.activate_section('hosts-pane')
                await pilot.pause(0.05)
                app.query_one('#host-details',RichLog).focus()
                await pilot.pause(0.05)
                await pilot.press('escape')
                self.assertIs(app.focused,app.query_one('#host-list',Tree))
                await pilot.press('escape')
                self.assertIs(app.focused,tabs.query_one(Tabs))
                app.activate_section('actions-pane')
                await pilot.pause(0.05)
                field=app.query_one('#field-query',Input)
                field.value='preserve this'
                field.focus()
                await pilot.pause(0.05)
                await pilot.press('escape')
                self.assertIs(app.focused,tabs.query_one(Tabs))
                self.assertEqual(field.value,'preserve this')

    async def test_modal_escape_and_select_dropdown_keep_local_behavior(self):
        from textual.widgets import Select, TabbedContent
        from browser_fixture import snapshot
        from host_actions import dialog_classes
        app=home.make_home_class()()
        async def collect():app.finish('{}',0)
        with patch.object(recipe_browser,'snapshot',side_effect=snapshot), \
                patch.object(management,'profiles_snapshot',return_value={'profiles':[],'message':'fixture'}), \
                patch.object(management,'hosts_snapshot',return_value={'hosts':[],'message':'fixture'}), \
                patch.object(app,'collect',side_effect=collect):
            async with app.run_test(size=(90,30)) as pilot:
                await pilot.pause(0.1)
                app.activate_section('actions-pane')
                await pilot.pause(0.05)
                select=app.query_one('#action',Select)
                select.focus()
                await pilot.pause(0.05)
                await pilot.press('enter')
                self.assertTrue(select.expanded)
                await pilot.press('escape')
                self.assertFalse(select.expanded)
                self.assertEqual(app.query_one('#workbench-tabs',TabbedContent).active,'actions-pane')
                Menu,_,_=dialog_classes()
                original=app.screen
                app.push_screen(Menu('fixture-host','/fixture/root'))
                await pilot.pause()
                await pilot.press('escape')
                self.assertIs(app.screen,original)
