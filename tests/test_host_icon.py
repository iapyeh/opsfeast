"""Host icon loading contract; all YAML/instances are temporary and synthetic."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opsfeast import ConfigError, Instance, Validator, main
from management_view import hosts_snapshot


class HostIconTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.entry = self.root / 'hosts.yaml'

    def write(self, **fields):
        self.entry.write_text(json.dumps({'hosts': {'h': dict(connection={'local': True}, **fields)}}, ensure_ascii=False), errors='backslashreplace')

    def load(self):
        validator = Validator(self.root)
        validator.load(self.entry)
        return validator

    def test_default_is_visible_without_modifying_yaml_or_raw_document(self):
        self.entry.write_text('# Human note\nhosts:\n  h:\n    connection: {local: true}\n')
        original = self.entry.read_bytes()
        validator = self.load()
        self.assertEqual(validator.hosts['h']['icon'], '🍎')
        self.assertNotIn('icon', validator.documents[self.entry]['hosts']['h'])
        validator.check_connections()
        self.assertEqual(self.entry.read_bytes(), original)

    def test_explicit_single_symbols_preserved(self):
        for icon in ('🍎', '🐧', '★', '☀', '$', '+', '©'):
            with self.subTest(icon=icon):
                self.write(icon=icon)
                self.assertEqual(self.load().check_connections().hosts['h']['icon'], icon)

    def test_invalid_type_character_count_or_category_rejected_on_load(self):
        for icon in (None, '', '🍎🍎', 'A', 'é', '1', ' ', '\n', '\x00', '\ud800', '\ufe0f',
                     '☀️', '👍🏽', '🇹🇼', '👩\u200d💻', 1, True, [], {}):
            with self.subTest(icon=repr(icon)):
                self.write(icon=icon)
                with self.assertRaisesRegex(ConfigError, 'h.icon: expected exactly one Unicode Symbol code point'):
                    self.load()

    def test_include_default_and_override_are_independent(self):
        self.entry.write_text('include: [extra.yaml]\nhosts:\n  first:\n    connection: {local: true}\n')
        (self.root / 'extra.yaml').write_text('hosts:\n  second:\n    icon: 🐧\n    connection: {local: true}\n')
        hosts = self.load().hosts
        self.assertEqual({key: host['icon'] for key, host in hosts.items()}, {'first': '🍎', 'second': '🐧'})

    def test_core_reload_inspection_and_failed_reload_preserve_snapshot(self):
        self.write()
        profile = Instance.open(self.root).profile(root=self.root)
        self.assertEqual(profile.hosts.get('h')['icon'], '🍎')
        self.write(icon='🐧')
        self.assertEqual(profile.inspect()['hosts']['h']['icon'], '🐧')
        self.assertEqual(profile.hosts.get('h')['icon'], '🍎')
        profile.reload()
        self.assertEqual(profile.hosts.get('h', reveal_secrets=True)['icon'], '🐧')
        self.write(icon='☀️')
        with self.assertRaises(ConfigError):
            profile.reload()
        self.assertEqual(profile.hosts.get('h')['icon'], '🐧')

    def test_cli_dump_and_ui_read_model_receive_effective_default(self):
        self.write()
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(['dump', 'hosts.h.icon', str(self.root)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), '🍎')
        import opsfeast
        with patch.object(opsfeast, 'resolve_root', return_value=self.root), \
                patch.object(opsfeast, 'load_profiles', return_value={'default_profile': 'main'}):
            self.assertEqual(hosts_snapshot()['hosts'][0]['settings']['icon'], '🍎')
        self.write(icon='invalid')
        error = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(error):
            self.assertEqual(main(['check', str(self.root)]), 1)
        self.assertIn('one Unicode Symbol code point', error.getvalue())


if __name__ == '__main__':
    unittest.main()
