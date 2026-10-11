"""Synthetic profile lifecycle and interaction tests; no SSH or real user data."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ops
import run_recipe


class Terminal(io.StringIO):
    def isatty(self):
        return True


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.checkout = self.root / 'checkout'
        self.checkout.mkdir()
        patcher = patch.object(ops, 'REPOSITORY_ROOT', self.checkout)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.pointer = self.checkout / '.my-ops.yaml'

    def cli(self, *arguments, interactive=False, answers=()):
        output = Terminal() if interactive else io.StringIO()
        errors = io.StringIO()
        stdin = Terminal() if interactive else io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors), \
                patch('sys.stdin', stdin), patch('builtins.input', side_effect=answers):
            code = ops.main(list(arguments))
        return code, output.getvalue(), errors.getvalue()

    def existing(self, relative, definition=True):
        root = self.root / relative
        root.mkdir(parents=True)
        (root / 'hosts.yaml').write_text('hosts: {localhost: {connection: {local: true}}}\n')
        if definition:
            (root / 'my-ops.yaml').write_text('schema_version: 1\nkind: sshscript-ops\n')
        return root

    def snapshot(self, root):
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def test_default_named_and_relative_path_init(self):
        self.assertEqual(self.cli('init')[0], 0)
        default = self.checkout / 'my-ops/main'
        self.assertEqual(ops.resolve_root(), default)
        with contextlib.chdir(self.root):
            self.assertEqual(self.cli('init', 'inventory')[0], 0)
            self.assertEqual(self.cli('init', './external')[0], 0)
        self.assertEqual(ops.resolve_root(profile='inventory'), self.checkout / 'my-ops/inventory')
        self.assertEqual(ops.resolve_root(profile='external'), self.root / 'external')
        self.assertEqual(ops.resolve_root(), default)
        self.assertEqual(ops.load_profiles()['profiles']['inventory']['root'], 'my-ops/inventory')
        self.assertEqual(ops.load_profiles()['profiles']['external']['root'], str(self.root / 'external'))

    def test_tilde_expanded_even_when_passed_as_literal(self):
        with patch.object(ops.Path, 'expanduser', lambda p: Path(str(p).replace('~', str(self.root), 1))):
            self.assertEqual(self.cli('init', '~/private/inventory')[0], 0)
        self.assertEqual(ops.resolve_root(), self.root / 'private/inventory')

    def test_names_with_unicode_spaces_and_invalid_path_components(self):
        for name in ('盤點資料', 'team inventory', '.hidden'):
            self.assertEqual(self.cli('init', name)[0], 0)
            self.assertEqual(ops.resolve_root(profile=name), self.checkout / 'my-ops' / name)
        before = self.pointer.read_bytes()
        for name in ('.', '..', ' trailing ', 'bad\nname'):
            self.assertEqual(self.cli('init', name)[0], 1)
            self.assertEqual(self.pointer.read_bytes(), before)

    def test_same_directory_keeps_name_through_symlink(self):
        root = self.existing('existing/inventory')
        self.assertEqual(self.cli('add', str(root), '--profile', 'special')[0], 0)
        link = self.root / 'alias'
        link.symlink_to(root, target_is_directory=True)
        self.assertEqual(self.cli('add', str(link))[0], 0)
        self.assertEqual(self.cli('init', str(root))[0], 0)
        self.assertEqual(list(ops.load_profiles()['profiles']), ['special'])
        self.assertEqual(self.cli('add', str(root), '--profile', 'different')[0], 1)

    def test_collision_suggests_name_and_never_creates_new_root(self):
        self.assertEqual(self.cli('init', 'inventory')[0], 0)
        root = self.root / 'other/inventory'
        before = self.pointer.read_bytes()
        code, output, errors = self.cli('init', str(root))
        self.assertEqual(code, 1)
        self.assertIn('other.inventory', errors)
        self.assertIn('--profile NAME', errors)
        self.assertFalse(root.exists())
        self.assertEqual(self.pointer.read_bytes(), before)
        self.assertEqual(self.cli('init', str(root), '--profile', 'other.inventory')[0], 0)
        self.assertEqual(ops.load_profiles()['default_profile'], 'inventory')

    def test_interactive_collision_requires_user_choice(self):
        self.cli('init', 'inventory')
        root = self.root / 'other/inventory'
        code, output, errors = self.cli('init', str(root), interactive=True,
                                        answers=['inventory', 'bad/name', 'other.inventory'])
        self.assertEqual(code, 0, errors)
        self.assertIn('Invalid profile name', output)
        self.assertEqual(ops.resolve_root(profile='other.inventory'), root)

    def test_cancelled_collision_leaves_registry_and_directory_unchanged(self):
        self.cli('init', 'inventory')
        before = self.pointer.read_bytes()
        root = self.root / 'other/inventory'
        for answer in ('', KeyboardInterrupt(), EOFError()):
            with self.subTest(answer=type(answer).__name__):
                self.assertEqual(self.cli('init', str(root), interactive=True, answers=[answer])[0], 1)
                self.assertFalse(root.exists())
                self.assertEqual(self.pointer.read_bytes(), before)

    def test_use_switches_and_explicit_selection_does_not(self):
        self.cli('init')
        self.cli('init', 'inventory')
        self.assertEqual(self.cli('check', '--profile', 'inventory')[0], 0)
        self.assertEqual(ops.load_profiles()['default_profile'], 'main')
        self.assertEqual(self.cli('use', 'inventory')[0], 0)
        self.assertEqual(ops.resolve_root(), self.checkout / 'my-ops/inventory')
        before = self.pointer.read_bytes()
        code, output, errors = self.cli('profiles')
        self.assertEqual(code, 0)
        self.assertIn('inventory', output)
        self.assertIn(str(self.checkout / 'my-ops/inventory'), output)
        self.assertIn('*', output)
        self.assertEqual(self.pointer.read_bytes(), before)
        self.assertEqual(self.cli('check', str(self.checkout / 'my-ops/main'), '--profile', 'inventory')[0], 1)

    def test_interactive_use_retries_invalid_and_accepts_number_or_name(self):
        self.cli('init')
        self.cli('init', 'inventory')
        code, output, errors = self.cli('use', interactive=True, answers=['wrong', '99', '2'])
        self.assertEqual(code, 0, errors)
        self.assertIn('Invalid selection', output)
        self.assertEqual(ops.load_profiles()['default_profile'], 'inventory')
        self.assertEqual(self.cli('use', interactive=True, answers=['main'])[0], 0)
        self.assertEqual(ops.load_profiles()['default_profile'], 'main')

    def test_use_cancel_and_noninteractive_do_not_change_selection(self):
        self.cli('init')
        before = self.pointer.read_bytes()
        for answer in ('', KeyboardInterrupt(), EOFError()):
            self.assertEqual(self.cli('use', interactive=True, answers=[answer])[0], 0)
            self.assertEqual(self.pointer.read_bytes(), before)
        code, output, errors = self.cli('use')
        self.assertEqual(code, 1)
        self.assertIn('ops.py use <profile>', output)
        self.assertEqual(self.pointer.read_bytes(), before)

    def test_empty_list_unknown_or_missing_profile(self):
        self.assertEqual(self.cli('profiles')[0], 0)
        self.assertEqual(self.cli('use')[0], 1)
        self.assertFalse(self.pointer.exists())
        self.cli('init')
        before = self.pointer.read_bytes()
        self.assertEqual(self.cli('use', 'missing')[0], 1)
        (self.checkout / 'my-ops/main/my-ops.yaml').write_text('schema_version: 9')
        self.assertEqual(self.cli('use', 'main')[0], 1)
        self.assertEqual(self.pointer.read_bytes(), before)

    def test_legacy_locator_read_only_until_registration_or_use(self):
        root = self.existing('legacy')
        original = 'schema_version: 1\nroot: ' + str(root) + '\n'
        self.pointer.write_text(original)
        self.assertEqual(self.cli('profiles')[0], 0)
        self.assertEqual(ops.resolve_root(), root)
        self.assertEqual(self.pointer.read_text(), original)
        self.cli('init', 'inventory')
        data = ops.read_yaml(self.pointer)
        self.assertEqual(data['schema_version'], 2)
        self.assertEqual(data['default_profile'], 'default')
        self.assertEqual(ops.resolve_root(), root)
        self.assertEqual(self.snapshot(root)['hosts.yaml'], b'hosts: {localhost: {connection: {local: true}}}\n')

    def test_existing_default_profile_preserved_when_main_is_created(self):
        root = self.existing('checkout/my-ops/default')
        self.assertEqual(self.cli('add', str(root))[0], 0)
        before = self.snapshot(root)
        self.assertEqual(self.cli('init')[0], 0)
        self.assertEqual(list(ops.load_profiles()['profiles']), ['default', 'main'])
        self.assertEqual(ops.load_profiles()['default_profile'], 'default')
        self.assertEqual(ops.resolve_root(), root)
        self.assertEqual(ops.resolve_root(profile='main'), self.checkout / 'my-ops/main')
        self.assertEqual(self.snapshot(root), before)
        code, output, errors = self.cli('use', interactive=True, answers=['main'])
        self.assertEqual(code, 0, errors)
        self.assertIn('default  ' + str(root) + ' [current default]', output)
        self.assertEqual(ops.load_profiles()['default_profile'], 'main')

    def test_add_legacy_and_modern_directory_preserves_all_contents(self):
        for name, definition in (('legacy', False), ('modern', True)):
            root = self.existing(name, definition)
            (root / 'notes.txt').write_text('human note')
            before = self.snapshot(root)
            with contextlib.chdir(self.root):
                self.assertEqual(self.cli('add', name)[0], 0)
            self.assertEqual(ops.resolve_root(profile=name), root)
            self.assertEqual(self.snapshot(root), before)
            self.assertFalse((root / 'observations').exists())
        self.assertEqual(ops.load_profiles()['default_profile'], 'legacy')

    def test_add_missing_invalid_and_collision_preserve_registry(self):
        self.cli('init')
        before = self.pointer.read_bytes()
        invalid = self.existing('invalid')
        (invalid / 'hosts.yaml').write_text('hosts: []')
        for root in (self.root / 'missing', invalid):
            self.assertEqual(self.cli('add', str(root))[0], 1)
            self.assertEqual(self.pointer.read_bytes(), before)
        duplicate = self.existing('shared/main')
        self.assertEqual(self.cli('add', str(duplicate))[0], 1)
        self.assertEqual(self.pointer.read_bytes(), before)
        self.assertEqual(self.cli('add', str(duplicate), '--profile', 'shared.main')[0], 0)
        self.assertEqual(ops.load_profiles()['default_profile'], 'main')

    def test_registry_validation_and_atomic_save_failure(self):
        self.cli('init')
        original = self.pointer.read_bytes()
        invalid_documents = [
            'schema_version: 2\nprofiles: {}\ndefault_profile: default',
            'schema_version: 2\nprofiles: {a: {root: x}}\ndefault_profile: []',
            'schema_version: 2\nprofiles: {a: {root: x}, b: {root: ./x}}\ndefault_profile: a',
            'schema_version: true\nroot: x',
        ]
        for document in invalid_documents:
            self.pointer.write_text(document)
            self.assertEqual(self.cli('profiles')[0], 1)
        self.pointer.write_bytes(original)
        with patch.object(ops.os, 'replace', side_effect=OSError('synthetic')):
            self.assertEqual(self.cli('init', 'inventory')[0], 1)
        self.assertEqual(self.pointer.read_bytes(), original)
        self.assertEqual(list(self.checkout.glob('.my-ops-*.tmp')), [])

    def test_runner_uses_profile_without_changing_default(self):
        self.cli('init')
        self.cli('init', 'inventory')
        path = self.checkout / 'my-ops/inventory/result.json'
        report = {'status': 'success', 'reason_code': 'inventory_complete',
                  'message': 'Synthetic successful run.', 'detected_kernel': 'Linux',
                  'supported_platforms': ['linux'], 'recipe': {'id': 'inventory-system'}}
        with patch.object(run_recipe, 'run', return_value=(report, path)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_recipe.main(['localhost', '--profile', 'inventory']), 0)
        run.assert_called_once_with(path.parent, 'localhost', 30, recipe=None)
        self.assertEqual(ops.load_profiles()['default_profile'], 'main')

    def test_profile_boundaries_and_result_directories(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        self.cli('init')
        self.cli('init', 'inventory')
        default = self.checkout / 'my-ops/main'
        inventory = self.checkout / 'my-ops/inventory'
        original = (default / 'hosts.yaml').read_bytes()
        (default / 'hosts.yaml').write_text('include: [../inventory/hosts.yaml]\n')
        self.assertEqual(self.cli('check', '--profile', 'main')[0], 1)
        (default / 'hosts.yaml').write_bytes(original)
        paths = []
        for profile in ('main', 'inventory'):
            session = Mock()
            session.exec_command.return_value = SimpleNamespace(stdout='Darwin\n', stderr='', exitcode=0)
            report, path = run_recipe.run(ops.resolve_root(profile=profile), 'localhost',
                                          recipe='recipes/inventory/system',
                                          session_class=Mock(return_value=session))
            self.assertEqual(report['status'], 'unsupported')
            self.assertEqual(path.parent, self.checkout / 'my-ops' / profile / 'observations')
            paths.append(path)
        self.assertTrue(all(p.is_file() for p in paths))


if __name__ == '__main__':
    unittest.main()
