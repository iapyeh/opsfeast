"""Reader assets are configured locally without overwriting user preferences."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import host_vault as vault
from opsfeast import ConfigError


class ReaderTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.appearance = self.root / 'vault/.obsidian/appearance.json'
        self.css = self.root / 'vault/.obsidian/snippets/opsfeast-mermaid-fit.css'
        self.manifest = self.root / 'vault/.reader-assets.json'

    def prepare(self, root=None):
        root = root or self.root
        with vault.locked(root):
            vault.prepare_reader(root)

    def test_first_adoption_preserves_preferences_and_updates_only_owned_css(self):
        self.appearance.parent.mkdir(parents=True)
        original = {'theme': 'moonstone', 'baseFontSize': 18, 'enabledCssSnippets': ['personal']}
        self.appearance.write_text(json.dumps(original))
        human = self.appearance.parent / 'snippets/personal.css'
        human.parent.mkdir()
        human.write_text('/* Human stylesheet. */')
        self.prepare()
        expected = dict(original, enabledCssSnippets=['personal', vault.READER_SNIPPET])
        self.assertEqual(json.loads(self.appearance.read_text()), expected)
        self.assertEqual(human.read_text(), '/* Human stylesheet. */')
        self.assertTrue(self.css.is_file())
        first = {p: p.read_bytes() for p in (self.css, self.appearance, self.manifest)}
        self.prepare()
        self.assertEqual({p: p.read_bytes() for p in first}, first)
        self.css.write_text('/* Edited managed CSS. */')
        self.prepare()
        self.assertEqual(self.css.read_bytes(), first[self.css])
        self.assertEqual(json.loads(self.appearance.read_text()), expected)

    def test_rebuild_respects_later_opt_out_and_repairs_missing_asset(self):
        self.prepare()
        self.appearance.write_text(json.dumps({'enabledCssSnippets': ['personal'], 'theme': 'obsidian'}))
        self.css.unlink()
        self.prepare()
        self.assertTrue(self.css.is_file())
        self.assertEqual(json.loads(self.appearance.read_text()),
                         {'enabledCssSnippets': ['personal'], 'theme': 'obsidian'})

    def test_unmanaged_css_collision_preserves_files_and_does_not_enable(self):
        self.css.parent.mkdir(parents=True)
        self.css.write_text('/* Unmanaged file at the reserved name. */')
        self.appearance.write_text('{"enabledCssSnippets":["personal"]}')
        with self.assertRaisesRegex(ConfigError, 'unmanaged'):
            self.prepare()
        self.assertEqual(self.css.read_text(), '/* Unmanaged file at the reserved name. */')
        self.assertEqual(json.loads(self.appearance.read_text()), {'enabledCssSnippets': ['personal']})
        self.assertFalse(self.manifest.exists())

    def test_invalid_preferences_or_manifest_fail_before_css_publication(self):
        self.appearance.parent.mkdir(parents=True)
        for body in ('{', '[]', '{"enabledCssSnippets":null}', '{"enabledCssSnippets":[false]}'):
            with self.subTest(body=body):
                self.appearance.write_text(body)
                with self.assertRaises((ConfigError, ValueError)):
                    self.prepare()
                self.assertEqual(self.appearance.read_text(), body)
                self.assertFalse(self.css.exists())
        self.appearance.write_text('{}')
        for body in ('[]', '{"unexpected":"value"}'):
            with self.subTest(manifest=body):
                self.manifest.write_text(body)
                with self.assertRaisesRegex(ConfigError, 'manifest'):
                    self.prepare()
                self.assertFalse(self.css.exists())
                self.assertEqual(self.appearance.read_text(), '{}')

    def test_symlink_reader_paths_are_rejected(self):
        external = self.root / 'outside'
        external.mkdir()
        sentinel = external / 'settings.json'
        sentinel.write_text('{}')
        for index, parts in enumerate((('.obsidian',), ('.obsidian', 'appearance.json'),
                ('.obsidian', 'snippets', 'opsfeast-mermaid-fit.css'), ('.reader-assets.json',))):
            root = self.root / ('case-' + str(index))
            root.mkdir()
            link = root.joinpath('vault', *parts)
            link.parent.mkdir(parents=True)
            link.symlink_to(external if len(parts) == 1 and parts[0] == '.obsidian' else sentinel,
                            target_is_directory=len(parts) == 1 and parts[0] == '.obsidian')
            with self.subTest(path=parts), self.assertRaisesRegex(ConfigError, 'symlink'):
                self.prepare(root)
            self.assertEqual(sentinel.read_text(), '{}')

    def test_interrupted_first_adoption_retries_without_duplicate_enabling(self):
        original = vault.atomic
        def interrupted(path, content):
            if path == self.manifest:
                raise OSError('Synthetic interruption')
            return original(path, content)
        with patch.object(vault, 'atomic', side_effect=interrupted), self.assertRaises(OSError):
            self.prepare()
        self.assertFalse(self.manifest.exists())
        self.prepare()
        self.assertTrue(self.manifest.is_file())
        self.assertEqual(json.loads(self.appearance.read_text())['enabledCssSnippets'], [vault.READER_SNIPPET])
