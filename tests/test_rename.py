"""Public, synthetic rename compatibility checks; no real user data or SSH."""
import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import opsfeast


class RenameTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.checkout = Path(temporary.name).resolve()
        patcher = patch.object(opsfeast, 'REPOSITORY_ROOT', self.checkout)
        patcher.start()
        self.addCleanup(patcher.stop)

    def cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return opsfeast.main(list(args))

    def legacy(self, version=2, name='main'):
        root = self.checkout / 'my-ops' / name
        root.mkdir(parents=True)
        (root / 'hosts.yaml').write_text('hosts: {localhost: {connection: {local: true}}}\n# human note\n')
        (root / 'my-ops.yaml').write_text('# preserved definition\nschema_version: 1\nkind: sshscript-ops\n')
        (root / 'history.txt').write_text('historical observation')
        registry = self.checkout / '.my-ops.yaml'
        data = ({'schema_version': 1, 'root': 'my-ops/' + name} if version == 1 else
                {'schema_version': 2, 'default_profile': name,
                 'profiles': {name: {'root': 'my-ops/' + name}}})
        registry.write_text(opsfeast.yaml.safe_dump(data, sort_keys=False))
        return root, registry

    def snapshot(self, root):
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def test_legacy_read_only_and_named_init_reuse_root(self):
        root, registry = self.legacy()
        before = self.snapshot(root)
        registration = registry.read_bytes()
        for command in ('profiles', 'check'):
            self.assertEqual(self.cli(command), 0)
        self.assertEqual(registry.read_bytes(), registration)
        self.assertEqual(self.cli('init'), 0)
        self.assertEqual(opsfeast.resolve_root(), root)
        for name, content in before.items():
            if name == 'my-ops.yaml':
                self.assertTrue((root / name).read_bytes().startswith(content))
                self.assertEqual(opsfeast.read_yaml(root / name)['namespace'], 'main')
            else:
                self.assertEqual((root / name).read_bytes(), content)
        self.assertFalse((root / 'feast.yaml').exists())
        self.assertFalse((self.checkout / 'feasts/main').exists())
        self.assertFalse((self.checkout / '.opsfeast.yaml').exists())

    def test_named_legacy_profile_and_new_profile_share_existing_registry(self):
        root, registry = self.legacy(name='inventory')
        self.assertEqual(self.cli('init', 'inventory'), 0)
        self.assertEqual(opsfeast.resolve_root(profile='inventory'), root)
        self.assertEqual(self.cli('init', 'new'), 0)
        self.assertEqual(opsfeast.resolve_root(profile='new'), self.checkout / 'feasts/new')
        self.assertEqual(opsfeast.load_profiles()['default_profile'], 'inventory')
        self.assertTrue(registry.is_file())
        self.assertFalse((self.checkout / '.opsfeast.yaml').exists())

    def test_schema_one_legacy_registry_upgrade_keeps_filename_and_root(self):
        root, registry = self.legacy(version=1)
        original = registry.read_bytes()
        self.assertEqual(self.cli('check'), 0)
        self.assertEqual(registry.read_bytes(), original)
        self.assertEqual(self.cli('use', 'default'), 0)
        self.assertEqual(opsfeast.read_yaml(registry)['schema_version'], 2)
        self.assertEqual(opsfeast.resolve_root(), root)
        self.assertFalse((self.checkout / '.opsfeast.yaml').exists())

    def test_registry_conflicts_never_write_or_create_a_new_feast(self):
        root, registry = self.legacy()
        (self.checkout / '.opsfeast.yaml').write_bytes(registry.read_bytes())
        before = self.snapshot(self.checkout)
        for args in (('profiles',), ('check',), ('init', 'new'), ('use', 'main'), ('attach', str(root))):
            self.assertEqual(self.cli(*args), 1)
        self.assertEqual(self.snapshot(self.checkout), before)
        self.assertFalse((self.checkout / 'feasts/new').exists())

    def test_definition_conflicts_fail_check_add_and_init_without_changes(self):
        root, _ = self.legacy()
        (root / 'feast.yaml').write_text('schema_version: 1\nkind: opsfeast\n')
        before = self.snapshot(self.checkout)
        for args in (('check',), ('check', str(root)), ('attach', str(root)), ('init', str(root))):
            self.assertEqual(self.cli(*args), 1)
        self.assertEqual(self.snapshot(self.checkout), before)

    def test_invalid_legacy_definition_is_not_ignored_by_add(self):
        root, registry = self.legacy()
        (root / 'my-ops.yaml').write_text('schema_version: true\nkind: sshscript-ops\n')
        before = registry.read_bytes()
        self.assertEqual(self.cli('attach', str(root)), 1)
        self.assertEqual(self.cli('init', str(root)), 1)
        self.assertEqual(registry.read_bytes(), before)
        self.assertFalse((root / 'feast.yaml').exists())

    def test_definition_kind_must_match_filename(self):
        self.assertEqual(self.cli('init'), 0)
        root = opsfeast.resolve_root()
        (root / 'feast.yaml').write_text('schema_version: 1\nkind: sshscript-ops\n')
        self.assertEqual(self.cli('check'), 1)
        self.assertEqual(self.cli('check', str(root)), 1)

    def test_dangling_legacy_registry_symlink_is_rejected(self):
        (self.checkout / '.my-ops.yaml').symlink_to(self.checkout / 'missing')
        self.assertEqual(self.cli('init'), 1)
        self.assertFalse((self.checkout / '.opsfeast.yaml').exists())
        self.assertFalse((self.checkout / 'feasts').exists())

    def test_dangling_legacy_definition_symlink_is_rejected(self):
        root, _ = self.legacy()
        (root / 'my-ops.yaml').unlink()
        (root / 'my-ops.yaml').symlink_to(root / 'missing')
        self.assertEqual(self.cli('check'), 1)
        self.assertEqual(self.cli('init', str(root)), 1)
        self.assertFalse((root / 'feast.yaml').exists())

    def test_explicit_filename_migration_preserves_registrations(self):
        root, registry = self.legacy()
        before = (root / 'hosts.yaml').read_bytes()
        registry.rename(self.checkout / '.opsfeast.yaml')
        definition = root / 'my-ops.yaml'
        definition.write_text(definition.read_text().replace('kind: sshscript-ops', 'kind: opsfeast'))
        definition.rename(root / 'feast.yaml')
        self.assertEqual(self.cli('check'), 0)
        self.assertEqual(opsfeast.resolve_root(), root)
        self.assertEqual((root / 'hosts.yaml').read_bytes(), before)
        self.assertFalse((self.checkout / 'feasts/main').exists())

    def test_new_cli_uses_an_isolated_registry(self):
        tools = self.checkout / 'tools'
        tools.mkdir()
        source = Path(__file__).resolve().parents[1] / 'tools'
        shutil.copytree(source, tools, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(source.parent / 'opsfeast', self.checkout / 'opsfeast', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(source.parent / 'consumers', self.checkout / 'consumers', ignore=shutil.ignore_patterns('__pycache__'))
        for args in (['init'], ['profiles'], ['init']):
            result = subprocess.run([sys.executable, '-B', str(tools / 'opsfeast.py'), *args],
                                    cwd='/', capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.checkout / '.opsfeast.yaml').is_file())
        self.assertFalse((self.checkout / '.my-ops.yaml').exists())
        self.assertEqual(opsfeast.resolve_root(), self.checkout / 'feasts/main')


if __name__ == '__main__':
    unittest.main()
