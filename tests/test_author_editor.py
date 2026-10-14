"""Local-only author default persistence and keyboard/mouse editing."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import recipe_identity as identity
import landing_ui
import management_view
from opsfeast import ConfigError
try:
    import textual
except ImportError:
    textual = None


class PersistenceTests(unittest.TestCase):
    def test_independent_fields_and_invalid_save_preserve_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity.save_field('name', 'Example', root)
            identity.save_field('contacts', ['a@example.invalid', 'https://example.invalid'], root)
            identity.save_field('license', 'MIT', root)
            self.assertEqual(identity.defaults(root), {'author': {'name': 'Example', 'contacts': ['a@example.invalid', 'https://example.invalid']}, 'license': 'MIT'})
            path = root / identity.DEFAULT_FILE
            before = path.read_bytes()
            for field, value in [('name', ' Bundle '), ('contacts', ['bUnDlE']), ('contacts', []), ('license', ''), ('other', 'x')]:
                with self.assertRaises(ConfigError): identity.save_field(field, value, root)
                self.assertEqual(path.read_bytes(), before)
            with patch.object(identity.os, 'replace', side_effect=OSError('fixture')):
                with self.assertRaises(OSError): identity.save_field('name', 'Changed', root)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(root.iterdir()), [path])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_invalid_file_and_symlink_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / identity.DEFAULT_FILE
            path.write_text('invalid: schema\n')
            with self.assertRaises(ConfigError): identity.save_field('name', 'Example', root)
            self.assertEqual(path.read_text(), 'invalid: schema\n')
            target = root / 'target'
            target.write_text('private fixture')
            path.unlink()
            path.symlink_to(target)
            with self.assertRaises(ConfigError): identity.save_field('name', 'Example', root)
            self.assertTrue(path.is_symlink())
            self.assertEqual(target.read_text(), 'private fixture')


@unittest.skipIf(textual is None, 'optional Textual missing')
class EditorTests(unittest.IsolatedAsyncioTestCase):
    async def test_tab_enter_click_validation_save_and_escape(self):
        from textual.widgets import Button, Input, Static
        read, write = identity.defaults, identity.save_field
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = landing_ui.make_home_class()()
            async def collect(): app.finish('{}', 0)
            with patch.object(identity, 'defaults', side_effect=lambda *args: read(root)), \
                    patch.object(identity, 'save_field', side_effect=lambda field, value: write(field, value, root)), \
                    patch.object(management_view, 'profiles_snapshot', return_value={'profiles': [], 'message': 'fixture'}), \
                    patch.object(management_view, 'hosts_snapshot', return_value={'hosts': [], 'message': 'fixture'}), \
                    patch.object(app, 'collect', side_effect=collect):
                async with app.run_test(size=(100, 36)) as pilot:
                    await pilot.pause(0.1)
                    await pilot.press('tab')
                    name = app.query_one('#author-name', Button)
                    self.assertIs(app.focused, name)
                    await pilot.press('enter')
                    value = app.screen.query_one(Input)
                    self.assertEqual(value.value, 'Unknown')
                    value.value = 'Bundle'
                    await pilot.press('enter')
                    self.assertIn('reserved', str(app.screen.query_one('#author-error', Static).content))
                    self.assertFalse((root / identity.DEFAULT_FILE).exists())
                    value.value = 'Example Author'
                    await pilot.press('enter')
                    await pilot.pause()
                    self.assertIn('Example Author', str(name.label))
                    self.assertIs(app.focused, name)
                    await pilot.press('tab', 'enter')
                    app.screen.query_one(Input).value = 'not JSON'
                    await pilot.press('enter')
                    self.assertIn('JSON list', str(app.screen.query_one('#author-error', Static).content))
                    app.screen.query_one(Input).value = json.dumps(['a@example.invalid', 'https://example.invalid'])
                    await pilot.click('#save-author')
                    await pilot.pause()
                    await pilot.click('#author-license')
                    app.screen.query_one(Input).value = 'MIT'
                    await pilot.click('#save-author')
                    await pilot.pause()
                    self.assertEqual(read(root)['license'], 'MIT')
                    await pilot.click('#author-name')
                    app.screen.query_one(Input).value = 'Cancelled'
                    await pilot.press('escape')
                    await pilot.pause()
                    self.assertEqual(read(root)['author']['name'], 'Example Author')
                    self.assertEqual(read(root)['author']['contacts'], ['a@example.invalid', 'https://example.invalid'])
