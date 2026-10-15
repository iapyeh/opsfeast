"""Synthetic profile lifecycle and interaction tests; no SSH or real user data."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import opsfeast as ops
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
        self.pointer = self.checkout / '.opsfeast.yaml'

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
            (root / 'feast.yaml').write_text('schema_version: 1\nkind: opsfeast\n')
        return root

    def snapshot(self, root):
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def test_default_named_and_relative_path_init(self):
        self.assertEqual(self.cli('init')[0], 0)
        default = self.checkout / 'feasts/main'
        self.assertEqual(ops.resolve_root(), default)
        with contextlib.chdir(self.root):
            self.assertEqual(self.cli('init', 'inventory')[0], 0)
            self.assertEqual(self.cli('init', './external')[0], 0)
        self.assertEqual(ops.resolve_root(profile='inventory'), self.checkout / 'feasts/inventory')
        self.assertEqual(ops.resolve_root(profile='external'), self.root / 'external')
        self.assertEqual(ops.resolve_root(), default)
        self.assertEqual(ops.load_profiles()['profiles']['inventory']['root'], 'feasts/inventory')
        self.assertEqual(ops.load_profiles()['profiles']['external']['root'], str(self.root / 'external'))

    def test_tilde_expanded_even_when_passed_as_literal(self):
        with patch.object(ops.Path, 'expanduser', lambda p: Path(str(p).replace('~', str(self.root), 1))):
            self.assertEqual(self.cli('init', '~/private/inventory')[0], 0)
        self.assertEqual(ops.resolve_root(), self.root / 'private/inventory')

    def test_names_with_unicode_spaces_and_invalid_path_components(self):
        for name in ('盤點資料', 'team inventory', '.hidden'):
            self.assertEqual(self.cli('init', name)[0], 0)
            self.assertEqual(ops.resolve_root(profile=name), self.checkout / 'feasts' / name)
        before = self.pointer.read_bytes()
        for name in ('.', '..', ' trailing ', 'bad\nname'):
            self.assertEqual(self.cli('init', name)[0], 1)
            self.assertEqual(self.pointer.read_bytes(), before)

    def test_same_directory_keeps_name_through_symlink(self):
        root = self.existing('existing/inventory')
        self.assertEqual(self.cli('attach', str(root), '--profile', 'special')[0], 0)
        link = self.root / 'alias'
        link.symlink_to(root, target_is_directory=True)
        self.assertEqual(self.cli('attach', str(link))[0], 0)
        self.assertEqual(self.cli('init', str(root))[0], 0)
        self.assertEqual(list(ops.load_profiles()['profiles']), ['special'])
        self.assertEqual(self.cli('attach', str(root), '--profile', 'different')[0], 1)

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
        self.assertEqual(ops.resolve_root(), self.checkout / 'feasts/inventory')
        before = self.pointer.read_bytes()
        code, output, errors = self.cli('profiles')
        self.assertEqual(code, 0)
        self.assertIn('inventory', output)
        self.assertIn(str(self.checkout / 'feasts/inventory'), output)
        self.assertIn('*', output)
        self.assertEqual(self.pointer.read_bytes(), before)
        self.assertEqual(self.cli('check', str(self.checkout / 'feasts/main'), '--profile', 'inventory')[0], 1)

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
        self.assertIn('opsfeast.py use <profile>', output)
        self.assertEqual(self.pointer.read_bytes(), before)

    def test_empty_list_unknown_or_missing_profile(self):
        self.assertEqual(self.cli('profiles')[0], 0)
        self.assertEqual(self.cli('use')[0], 1)
        self.assertFalse(self.pointer.exists())
        self.cli('init')
        before = self.pointer.read_bytes()
        self.assertEqual(self.cli('use', 'missing')[0], 1)
        (self.checkout / 'feasts/main/feast.yaml').write_text('schema_version: 9')
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
        root = self.existing('checkout/feasts/default')
        self.assertEqual(self.cli('attach', str(root))[0], 0)
        before = self.snapshot(root)
        self.assertEqual(self.cli('init')[0], 0)
        self.assertEqual(list(ops.load_profiles()['profiles']), ['default', 'main'])
        self.assertEqual(ops.load_profiles()['default_profile'], 'default')
        self.assertEqual(ops.resolve_root(), root)
        self.assertEqual(ops.resolve_root(profile='main'), self.checkout / 'feasts/main')
        self.assertEqual(self.snapshot(root), before)
        code, output, errors = self.cli('use', interactive=True, answers=['main'])
        self.assertEqual(code, 0, errors)
        self.assertRegex(output, r'default\s+│ ' + __import__('re').escape(str(root)) + r'\s+│ available\s+│ true')
        self.assertEqual(ops.load_profiles()['default_profile'], 'main')

    def test_attach_legacy_and_modern_directory_preserves_all_contents(self):
        for name, definition in (('legacy', False), ('modern', True)):
            root = self.existing(name, definition)
            (root / 'notes.txt').write_text('human note')
            before = self.snapshot(root)
            with contextlib.chdir(self.root):
                self.assertEqual(self.cli('attach', name)[0], 0)
            self.assertEqual(ops.resolve_root(profile=name), root)
            self.assertEqual(self.snapshot(root), before)
            self.assertFalse((root / 'observations').exists())
        self.assertEqual(ops.load_profiles()['default_profile'], 'legacy')

    def test_attach_missing_invalid_and_collision_preserve_registry(self):
        self.cli('init')
        before = self.pointer.read_bytes()
        invalid = self.existing('invalid')
        (invalid / 'hosts.yaml').write_text('hosts: []')
        for root in (self.root / 'missing', invalid):
            self.assertEqual(self.cli('attach', str(root))[0], 1)
            self.assertEqual(self.pointer.read_bytes(), before)
        duplicate = self.existing('shared/main')
        self.assertEqual(self.cli('attach', str(duplicate))[0], 1)
        self.assertEqual(self.pointer.read_bytes(), before)
        self.assertEqual(self.cli('attach', str(duplicate), '--profile', 'shared.main')[0], 0)
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
        self.assertEqual(list(self.checkout.glob('.opsfeast-*.tmp')), [])

    def test_runner_uses_profile_without_changing_default(self):
        self.cli('init')
        self.cli('init', 'inventory')
        path = self.checkout / 'feasts/inventory/result.json'
        report = {'status': 'success', 'reason_code': 'inventory_complete',
                  'message': 'Synthetic successful run.', 'detected_kernel': 'Linux',
                  'supported_platforms': ['linux'], 'recipe': {'id': 'inventory-system'}}
        with patch.object(run_recipe, 'run', return_value=(report, path)) as run, \
                patch('access_check.check_many', return_value={'status': 'success', 'hosts': []}), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_recipe.main(['inventory/system', '--host', 'localhost', '--profile', 'inventory']), 0)
        run.assert_called_once_with(path.parent, 'localhost', 30, recipe='inventory/system', force=False, access_checked=True, access_result=None)
        self.assertEqual(ops.load_profiles()['default_profile'], 'main')

    def test_profile_boundaries_and_result_directories(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        self.cli('init')
        self.cli('init', 'inventory')
        default = self.checkout / 'feasts/main'
        inventory = self.checkout / 'feasts/inventory'
        original = (default / 'hosts.yaml').read_bytes()
        (default / 'hosts.yaml').write_text('include: [../inventory/hosts.yaml]\n')
        self.assertEqual(self.cli('check', '--profile', 'main')[0], 1)
        (default / 'hosts.yaml').write_bytes(original)
        paths = []
        for profile in ('main', 'inventory'):
            session = Mock()
            session.exec_command.return_value = SimpleNamespace(stdout='OpenBSD\n', stderr='', exitcode=0)
            report, path = run_recipe.run(ops.resolve_root(profile=profile), 'localhost',
                                          recipe='inventory/system',
                                          session_class=Mock(return_value=session))
            self.assertEqual(report['status'], 'unsupported')
            self.assertEqual(path.parent, self.checkout / 'feasts' / profile / 'observations')
            paths.append(path)
        self.assertTrue(all(p.is_file() for p in paths))


    def test_detach_preserves_directory_and_can_reattach(self):
        self.cli('init')
        self.cli('init', 'inventory')
        root = self.checkout / 'feasts/inventory'
        (root / 'records/human-note.md').write_text('Synthetic note to preserve.')
        before = self.snapshot(root)
        code, output, errors = self.cli('detach', 'inventory')
        self.assertEqual(code, 0)
        self.assertEqual(errors, '')
        self.assertIn('Management directory and its contents preserved', output)
        self.assertEqual(self.snapshot(root), before)
        self.assertNotIn('inventory', ops.load_profiles()['profiles'])
        self.assertEqual(ops.load_profiles()['default_profile'], 'main')
        self.assertEqual(self.cli('attach', str(root))[0], 0)
        self.assertEqual(self.snapshot(root), before)
        self.assertEqual(ops.resolve_root(profile='inventory'), root)

    def test_detach_default_switches_to_valid_main_in_one_registry_write(self):
        self.cli('init')
        self.cli('init', 'inventory')
        self.cli('use', 'inventory')
        save = ops.save_profiles
        with patch.object(ops, 'save_profiles', wraps=save) as writer:
            code, output, _ = self.cli('detach', 'inventory')
        self.assertEqual(code, 0)
        self.assertIn('Default profile: main', output)
        writer.assert_called_once()
        self.assertEqual(ops.load_profiles()['default_profile'], 'main')
        self.assertEqual(ops.resolve_root(), self.checkout / 'feasts/main')
        self.assertTrue((self.checkout / 'feasts/inventory').is_dir())

    def test_main_is_protected_and_unknown_names_do_not_write(self):
        self.assertEqual(self.cli('detach', 'main')[0], 1)
        self.assertFalse(self.pointer.exists())
        self.cli('init')
        before = self.pointer.read_bytes()
        for name in ('main', 'unknown', 'ma'):
            code, _, error = self.cli('detach', name)
            self.assertEqual(code, 1)
            self.assertIn('reserved' if name == 'main' else 'unknown profile', error)
            self.assertEqual(self.pointer.read_bytes(), before)

    def test_detach_default_refuses_when_main_not_registered(self):
        self.cli('init', 'inventory')
        before = self.pointer.read_bytes()
        code, _, error = self.cli('detach', 'inventory')
        self.assertEqual(code, 1)
        self.assertIn('main is not registered', error)
        self.assertEqual(self.pointer.read_bytes(), before)
        self.assertFalse((self.checkout / 'feasts/main').exists())

    def test_default_detach_accepts_a_registered_legacy_hosts_only_main(self):
        self.cli('init', 'inventory')
        root = self.existing('legacy-main', definition=False)
        before = self.snapshot(root)
        self.assertEqual(self.cli('attach', str(root), '--profile', 'main')[0], 0)
        self.assertEqual(self.cli('detach', 'inventory')[0], 0)
        self.assertEqual(ops.resolve_root(), root)
        self.assertEqual(self.snapshot(root), before)
        self.assertFalse((root / 'feast.yaml').exists())

    def test_detach_default_rejects_missing_or_invalid_main_before_writing(self):
        self.cli('init')
        self.cli('init', 'inventory')
        self.cli('use', 'inventory')
        before = self.pointer.read_bytes()
        main = self.checkout / 'feasts/main'
        saved = self.checkout / 'main-offline'
        main.rename(saved)
        self.assertEqual(self.cli('detach', 'inventory')[0], 1)
        self.assertEqual(self.pointer.read_bytes(), before)
        self.assertFalse(main.exists())
        saved.rename(main)
        definition = (main / 'feast.yaml').read_bytes()
        (main / 'feast.yaml').write_text('schema_version: 1\nkind: wrong')
        self.assertEqual(self.cli('detach', 'inventory')[0], 1)
        self.assertEqual(self.pointer.read_bytes(), before)
        (main / 'feast.yaml').write_bytes(definition)
        (main / 'hosts.yaml').unlink()
        self.assertEqual(self.cli('detach', 'inventory')[0], 1)
        self.assertEqual(self.pointer.read_bytes(), before)
        (main / 'hosts.yaml').symlink_to(self.existing('outside') / 'hosts.yaml')
        self.assertEqual(self.cli('detach', 'inventory')[0], 1)
        self.assertEqual(self.pointer.read_bytes(), before)

    def test_missing_nondefault_profile_is_listed_and_detachable(self):
        self.cli('init')
        self.cli('init', 'inventory')
        root = self.checkout / 'feasts/inventory'
        relocated = self.checkout / 'inventory-offline'
        root.rename(relocated)
        before = self.pointer.read_bytes()
        code, output, _ = self.cli('profiles')
        self.assertEqual(code, 0)
        self.assertIn(str(root) + '  missing', output)
        self.assertEqual(self.pointer.read_bytes(), before)
        self.assertIn('inventory', ops.load_profiles()['profiles'])
        self.assertEqual(self.cli('detach', 'inventory')[0], 0)
        self.assertTrue(relocated.is_dir())
        self.assertFalse(root.exists())

    def test_profiles_basic_status_is_read_only_and_not_a_connection_check(self):
        self.cli('init')
        root = self.checkout / 'feasts/main'
        (root / 'feast.yaml').write_text('schema_version: 9')
        before = self.pointer.read_bytes()
        code, output, _ = self.cli('profiles')
        self.assertEqual(code, 0)
        self.assertIn(str(root) + '  invalid', output)
        self.assertEqual(self.pointer.read_bytes(), before)

    def test_detach_write_failure_keeps_registry_and_directories(self):
        self.cli('init')
        self.cli('init', 'inventory')
        self.cli('use', 'inventory')
        before = self.pointer.read_bytes()
        with patch.object(ops.os, 'replace', side_effect=OSError('synthetic atomic write failure')):
            self.assertEqual(self.cli('detach', 'inventory')[0], 1)
        self.assertEqual(self.pointer.read_bytes(), before)
        self.assertEqual(list(self.checkout.glob('.opsfeast-*.tmp')), [])
        self.assertTrue((self.checkout / 'feasts/inventory').is_dir())

    def test_detach_updates_active_legacy_registry_and_keeps_definitions(self):
        self.cli('init')
        self.cli('init', 'inventory')
        legacy = self.checkout / '.my-ops.yaml'
        self.pointer.rename(legacy)
        root = self.checkout / 'feasts/inventory'
        before = self.snapshot(root)
        self.assertEqual(self.cli('detach', 'inventory')[0], 0)
        self.assertTrue(legacy.is_file())
        self.assertFalse(self.pointer.exists())
        self.assertEqual(self.snapshot(root), before)

    def test_attach_has_no_add_alias(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            ops.main(['add', str(self.root)])
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse(self.pointer.exists())


if __name__ == '__main__':
    unittest.main()
