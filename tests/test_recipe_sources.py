"""Public synthetic source/vars/disable/exclude integration; no real hosts."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import opsfeast as ops
import run_recipe as runner
from recipe_inputs import prepare_vars
from types import SimpleNamespace


class RecipeSourcesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.root = self.base / 'profile'
        self.root.mkdir()
        self.external = self.base / 'community'
        shutil.copytree(runner.BUNDLE, self.external / 'inventory/system')
        shutil.copytree(runner.BUNDLE, self.root / 'recipes/inventory/system')
        self.data = {
            'recipe_sources': {'community': {'path': str(self.external)}},
            'hosts': {'h': {'connection': {'local': True}, 'group': 'g',
                            'recipes': ['community:inventory/system']},
                      'other': {'connection': {'local': True}, 'group': 'g', 'recipes': []}}}
        self.write()

    def write(self):
        (self.root / 'hosts.yaml').write_text(yaml.safe_dump(self.data, sort_keys=False))

    def config(self):
        return ops.Validator(self.root).check()

    def session(self):
        session = Mock()
        def output(argv, **kwargs):
            text = ({'-s': 'Linux', '-n': 'synthetic-node', '-r': '6.1', '-m': 'x86_64'}[argv[1]]
                    if argv[0] == 'uname' else 'ID=example\nNAME="Example Linux"\nVERSION_ID=1.2')
            return SimpleNamespace(stdout=text + '\n', stderr='', exitcode=0)
        session.exec_command.side_effect = output
        return session

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                patch.object(runner, 'load_runtime', side_effect=lambda: (Mock(return_value=self.session()), {'verification': 'synthetic'})):
            code = runner.main([*args, '--root', str(self.root), '--threads', '1'])
        return code, json.loads(out.getvalue()) if out.getvalue() else None, err.getvalue()

    def test_three_sources_shorthand_and_legacy_paths(self):
        for reference, directory in (('inventory/system', runner.BUNDLE.resolve()),
                                     (':inventory/system', self.root / 'recipes/inventory/system'),
                                     ('community:inventory/system', self.external / 'inventory/system'),
                                     ('recipes/inventory/system', runner.BUNDLE.resolve()),
                                     ('./recipes/inventory/system', self.root / 'recipes/inventory/system')):
            with self.subTest(reference=reference):
                self.data['hosts']['h']['recipes'] = [reference]
                self.write()
                self.assertEqual(self.config().selected['h'], [directory])
                if not reference.startswith('recipes/'):
                    report, path = runner.run(self.root, 'h', recipe=reference, session_class=Mock(return_value=self.session()))
                    self.assertEqual(report['status'], 'success')
                    self.assertEqual(report['recipe']['resolved_path'], str(directory))
                    self.assertTrue(path.is_relative_to(self.root / 'observations'))

    def test_includes_use_entry_sources_and_profile_prefix(self):
        self.data['include'] = ['hosts/extra.yaml']
        (self.root / 'hosts').mkdir()
        (self.root / 'hosts/extra.yaml').write_text('hosts: {included: {connection: {local: true}, recipes: [":inventory/system", "community:inventory/system"]}}')
        self.write()
        cfg = self.config()
        self.assertEqual(len(cfg.selected['included']), 2)
        (self.root / 'hosts/extra.yaml').write_text('recipe_sources: {evil: {path: /tmp}}\nhosts: {}')
        with self.assertRaisesRegex(ops.ConfigError, 'unsupported fields'):
            self.config()

    def test_source_relative_and_home_paths(self):
        self.data['recipe_sources']['community']['path'] = '../community'
        self.write()
        self.assertEqual(self.config().selected['h'], [self.external / 'inventory/system'])
        self.data['recipe_sources']['community'] = {'path': '~/synthetic-disabled-recipe-source', 'enabled': False}
        self.write()
        self.assertEqual(self.config().recipe_sources['community']['root'], Path('~/synthetic-disabled-recipe-source').expanduser().resolve())

    def test_boundaries_traversal_descriptor_symlink_and_unknown_source(self):
        for reference in ('community:../../outside', ':../outside', 'community:/absolute', 'community:', 'missing:inventory/system'):
            with self.subTest(reference=reference):
                self.data['hosts']['h']['recipes'] = [reference]
                self.write()
                with self.assertRaises(ops.ConfigError):
                    self.config()
        self.data['hosts']['h']['recipes'] = ['community:inventory/system']
        self.write()
        descriptor = self.external / 'inventory/system/recipe.yaml'
        descriptor.unlink()
        outside = self.base / 'outside.yaml'
        outside.write_text('id: inventory-system')
        descriptor.symlink_to(outside)
        with self.assertRaisesRegex(ops.ConfigError, 'outside'):
            self.config()

    def test_directory_glob_and_namespaced_id_duplicates(self):
        self.data['hosts']['h']['recipes'] = [
            {'directory': 'community:inventory', 'recursive': True},
            {'glob': 'community:inventory/*'}, ':inventory/system', 'inventory/system']
        self.write()
        self.assertEqual(len(self.config().selected['h']), 3)
        shutil.copytree(self.external / 'inventory/system', self.external / 'inventory/duplicate')
        with self.assertRaisesRegex(ops.ConfigError, 'duplicate recipe ID'):
            self.config()

    def test_disabled_source_skips_missing_paths_without_runtime_or_fallback(self):
        self.data['recipe_sources']['community'] = {'path': str(self.base / 'absent'), 'enabled': False}
        self.write()
        cfg = self.config()
        self.assertEqual(cfg.selected['h'], [])
        self.assertEqual(cfg.recipe_skips['h'][0]['reason_code'], 'source_disabled')
        with patch.object(runner, 'load_runtime') as runtime:
            report, path = runner.run(self.root, 'h', recipe='community:missing')
        runtime.assert_not_called()
        self.assertIsNone(path)
        self.assertEqual(report['status'], 'skipped')
        self.assertEqual(report['reason_code'], 'source_disabled')
        self.assertFalse((self.root / 'observations').exists())
        code, result, _ = self.cli('community:missing', '--host', 'h')
        self.assertEqual(code, 1)
        self.assertEqual(result['reason_code'], 'source_disabled')
        self.assertIsNone(result['result_path'])

    def test_bundle_and_profile_disable_cover_all_reference_forms(self):
        self.data['recipe_sources'].update({'bundle': {'enabled': False}, 'profile': {'enabled': False}})
        shutil.rmtree(self.root / 'recipes')
        self.data['hosts']['h']['recipes'] = ['inventory/system', 'recipes/inventory/system', ':missing', './recipes/missing']
        self.write()
        cfg = self.config()
        self.assertEqual(cfg.selected['h'], [])
        self.assertEqual(len(cfg.recipe_skips['h']), 4)
        for ref in ('inventory/system', ':missing', './recipes/missing', str(runner.BUNDLE.resolve())):
            with self.subTest(ref=ref), patch.object(runner, 'load_runtime') as runtime:
                report, path = runner.run(self.root, 'h', recipe=ref)
                self.assertEqual(report['reason_code'], 'source_disabled')
                self.assertIsNone(path)
                runtime.assert_not_called()
        report, _ = runner.run(self.root, 'h', recipe='community:inventory/system', session_class=Mock(return_value=self.session()))
        self.assertEqual(report['status'], 'success')

    def test_default_source_vars_and_host_overrides(self):
        for name, ref in (('bundle', 'inventory/system'), ('profile', ':inventory/system')):
            with self.subTest(name=name):
                self.data['recipe_sources'][name] = {'vars': {'command_timeout_seconds': 12}}
                self.data['hosts']['h']['recipes'] = [{'recipe': ref, 'vars': {'command_timeout_seconds': 8}}]
                self.write()
                cfg, _, _, _ = runner.preflight(self.root, 'h', ref)
                self.assertEqual(cfg.execution_recipe['effective_vars']['command_timeout_seconds'], 8)
                self.data['hosts']['h']['recipes'] = [ref]
                self.write()
                cfg, _, _, _ = runner.preflight(self.root, 'h', ref)
                self.assertEqual(cfg.execution_recipe['effective_vars']['command_timeout_seconds'], 12)

    def test_default_source_settings_reject_paths_bad_flags_and_aliases(self):
        original = copy.deepcopy(self.data)
        for name in ('bundle', 'profile'):
            for settings in ({'path': str(self.external)}, {'enabled': 'false'}, {'vars': []}):
                with self.subTest(name=name, settings=settings):
                    self.data = copy.deepcopy(original)
                    self.data['recipe_sources'][name] = settings
                    self.write()
                    with self.assertRaises(ops.ConfigError): self.config()
        self.data = original
        self.write()
        for reference in ('bundle:inventory/system', 'profile:inventory/system'):
            with self.assertRaisesRegex(ops.ConfigError, 'unknown recipe source'):
                runner.preflight(self.root, 'h', reference)

    def test_default_source_optional_paths_accept_only_resolved_defaults(self):
        for name, expected in (('bundle', ops.REPOSITORY_RECIPES.resolve()), ('profile', self.root / 'recipes')):
            alias = self.root / (name + '-recipe-link')
            alias.symlink_to(expected, target_is_directory=True)
            for text in (str(expected), os.path.relpath(expected, self.root), './' + alias.name):
                with self.subTest(name=name, text=text):
                    self.data['recipe_sources'][name] = {'path': text, 'enabled': False}
                    self.write()
                    cfg = self.config()
                    self.assertFalse(cfg.default_recipe_sources[name]['enabled'])
            for bad in ('', None, 3, 'https://example.invalid', str(self.external)):
                with self.subTest(name=name, bad=bad):
                    self.data['recipe_sources'][name] = {'path': bad, 'enabled': False}
                    self.write()
                    with self.assertRaises(ops.ConfigError): self.config()
            del self.data['recipe_sources'][name]

    def test_vars_overlay_timeout_provenance_and_no_disclosure(self):
        self.data['recipe_sources']['community']['vars'] = {'command_timeout_seconds': 15}
        self.data['hosts']['h']['recipes'] = [{'recipe': 'community:inventory/system', 'vars': {'command_timeout_seconds': 7}}]
        self.write()
        session = self.session()
        report, _ = runner.run(self.root, 'h', recipe='community:inventory/system', session_class=Mock(return_value=session))
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['recipe']['variable_names'], ['command_timeout_seconds'])
        # The initial facts probe keeps the CLI timeout; collection gets the recipe override.
        self.assertEqual(session.exec_command.call_args_list[-1].kwargs['command_timeout'], 7)
        self.assertEqual(session.exec_command.call_args_list[0].kwargs['command_timeout'], 30)
        self.assertNotIn('effective_vars', json.dumps(report))
        self.assertEqual(self.data['recipe_sources']['community']['vars']['command_timeout_seconds'], 15)

    def test_invalid_or_required_vars_fail_before_session(self):
        for value in (False, 'seven', 0, -1):
            with self.subTest(value=value):
                self.data['recipe_sources']['community']['vars'] = {'command_timeout_seconds': value}
                self.write()
                session = Mock()
                with self.assertRaises(ops.ConfigError):
                    runner.run(self.root, 'h', recipe='community:inventory/system', session_class=session)
                session.assert_not_called()
        schema = {'inputs': {'variables': {'token': {'type': 'string', 'required': True}}}}
        with self.assertRaisesRegex(ops.ConfigError, 'missing required'):
            prepare_vars(schema, {}, {})
        with self.assertRaisesRegex(ops.ConfigError, 'undeclared'):
            prepare_vars(schema, {'other': 'private'}, {'token': 'private'})

    def test_shallow_overlay_defaults_and_deep_copy(self):
        schema = {'inputs': {'variables': {
            'options': {'type': 'object', 'default': {'a': 1, 'b': 2}},
            'names': {'type': 'array', 'default': ['x']}}}}
        source, host = {'options': {'a': 3, 'b': 4}}, {'options': {'a': 5}}
        values = prepare_vars(schema, source, host)
        self.assertEqual(values['options'], {'a': 5})
        values['options']['a'] = 9
        values['names'].append('y')
        self.assertEqual(host['options']['a'], 5)
        self.assertEqual(schema['inputs']['variables']['names']['default'], ['x'])

    def test_all_input_types_defaults_and_bounds_are_validated(self):
        for kind, good, bad in (('string', 'x', 1), ('integer', 1, True),
                                ('number', 1.5, float('nan')), ('boolean', True, 1),
                                ('object', {'x': 1}, []), ('array', [1], {})):
            with self.subTest(kind=kind):
                schema = {'inputs': {'variables': {'v': {'type': kind, 'default': good}}}}
                self.assertEqual(prepare_vars(schema, {}, {})['v'], good)
                with self.assertRaises(ops.ConfigError): prepare_vars(schema, {}, {'v': bad})
                schema['inputs']['variables']['v']['default'] = bad
                with self.assertRaises(ops.ConfigError): prepare_vars(schema, {}, {'v': good})
        with self.assertRaises(ops.ConfigError):
            prepare_vars({'inputs': {'variables': {'v': {'type': 'number', 'minimum': 3, 'maximum': 1}}}}, {}, {})

    def test_vars_require_context_support_before_loading_legacy_code(self):
        entry = self.external / 'inventory/system/implementations/linux.py'
        entry.write_text("VERSION = '0.1.2'\nraise RuntimeError('never execute candidate')\ndef collect(session, report, timeout, facts):\n    pass\n")
        self.data['recipe_sources']['community']['vars'] = {'command_timeout_seconds': 5}
        self.write()
        with self.assertRaisesRegex(ops.ConfigError, 'context'), patch.object(runner, 'load_runtime') as runtime:
            runner.run(self.root, 'h', recipe='community:inventory/system')
        runtime.assert_not_called()

    def test_first_matching_selector_wins_and_unrelated_selectors_are_bypassed(self):
        self.data['hosts']['h']['recipes'] = [
            {'recipe': 'community:absent', 'vars': {'unrelated': 'private'}},
            'community:inventory/system',
            {'recipe': 'community:inventory/system', 'vars': {'command_timeout_seconds': 5}}]
        self.write()
        cfg, _, _, _ = runner.preflight(self.root, 'h', 'community:inventory/system')
        self.assertEqual(cfg.execution_recipe['effective_vars'], {})
        self.data['hosts']['h']['recipes'] = [
            {'directory': 'community:inventory', 'vars': {'command_timeout_seconds': 6}}]
        self.write()
        cfg, _, _, _ = runner.preflight(self.root, 'h', 'community:inventory/system')
        self.assertEqual(cfg.execution_recipe['effective_vars']['command_timeout_seconds'], 6)

    def test_invalid_source_and_host_flags_and_selector_vars(self):
        original = copy.deepcopy(self.data)
        for update in ({'path': str(self.external), 'enabled': 'false'},
                       {'path': str(self.external), 'vars': []}, {'path': 'https://example.invalid'}, {'path': ''}):
            self.data = copy.deepcopy(original)
            self.data['recipe_sources']['community'] = update
            self.write()
            with self.assertRaises(ops.ConfigError): self.config()
        self.data = copy.deepcopy(original)
        self.data['hosts']['h']['enabled'] = 'false'
        self.write()
        with self.assertRaisesRegex(ops.ConfigError, 'boolean'): self.config()
        self.data = copy.deepcopy(original)
        self.data['hosts']['h']['recipes'] = [{'recipe': 'community:inventory/system', 'vars': []}]
        self.write()
        with self.assertRaises(ops.ConfigError): self.config()

    def test_disabled_host_selection_skip_and_disabled_jump(self):
        self.data['hosts']['h']['enabled'] = False
        self.write()
        omitted = []
        self.assertEqual(runner.select_hosts(self.root, [], True, excluded=omitted), ['other'])
        self.assertEqual(omitted, [{'host': 'h', 'reason_code': 'host_disabled'}])
        self.assertEqual(runner.select_hosts(self.root, [('group', 'g')]), ['other'])
        code, result, _ = self.cli('inventory/system', '--host', 'h')
        self.assertEqual(code, 1)
        self.assertEqual(result['reason_code'], 'host_disabled')
        self.data['hosts']['h']['connection'] = {'hostname': 'jump.example'}
        self.data['hosts']['other']['connection'] = {'hostname': 'target.example', 'via': {'host': 'h'}}
        self.write()
        cfg = self.config()
        with self.assertRaisesRegex(ops.ConfigError, 'disabled'):
            ops.connection_plan(cfg, 'other', Mock())

    def test_cli_exclude_is_exact_and_keeps_excluded_jump_available(self):
        code, report, _ = self.cli('inventory/system', '--all', '--exclude', 'other', 'other')
        self.assertEqual(code, 0)
        self.assertEqual([r['host'] for r in report['hosts']], ['h'])
        self.assertEqual(report['excluded_hosts'], [{'host': 'other', 'reason_code': 'cli_excluded'}])
        code, _, error = self.cli('inventory/system', '--all', '--exclude', 'typo')
        self.assertEqual(code, 1)
        self.assertIn('unknown excluded host ID', error)
        code, report, error = self.cli('inventory/system', '--all', '--exclude', 'h', 'other')
        self.assertEqual(code, 1)
        self.assertEqual(len(report['excluded_hosts']), 2)
        self.assertIn('no hosts selected', error)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            runner.main(['inventory/system', '--host', 'h', '--exclude', 'other'])
        # Exclusion is target-only; it does not mutate enabled or the jump plan.
        self.data['hosts']['other']['connection'] = {'hostname': 'jump.example'}
        self.data['hosts']['h']['connection'] = {'hostname': 'target.example', 'via': {'host': 'other'}}
        self.write()
        fake = Mock()
        fake.resolve_connection.side_effect = lambda name, **kw: {'hostname': name, 'username': 'synthetic'}
        self.assertEqual(len(ops.connection_plan(self.config(), 'h', fake)), 2)


if __name__ == '__main__':
    unittest.main()
