"""Synthetic recipe inspection; no host connections or candidate execution."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import opsfeast as ops
import recipe_inspection as inspection


class RecipeInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.recipes = self.root / 'recipes'
        self.recipe = self.recipes / 'custom'
        self.recipe.mkdir(parents=True)
        self.metadata = {
            'id': 'synthetic-recipe', 'title': 'Synthetic inspection', 'version': '1.0.0',
            'platforms': {'planned': ['linux', 'freebsd'], 'implemented': ['linux'], 'tested': []},
            'implementations': [{'id': 'linux', 'version': '1.0.0', 'entrypoint': 'linux.py',
                                 'match': {'os_name': 'linux', 'distribution_id': 'debian', 'os_version': '>=12'}}],
        }
        self.write_metadata()
        (self.recipe / 'linux.py').write_text("VERSION = '1.0.0'\nraise RuntimeError('must never execute')\n")

    def write_metadata(self):
        (self.recipe / 'recipe.yaml').write_text(json.dumps(self.metadata))

    def test_discovery_coverage_and_no_execution_or_config(self):
        with patch.object(inspection, 'REPOSITORY_RECIPES', self.recipes), patch.object(ops, 'resolve_root', side_effect=AssertionError('no profile access')):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = ops.main(['inspect-recipe', '--platform', 'freebsd', '--json'])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        item = report['recipes'][0]
        self.assertEqual(item['coverage']['not_declared_implemented'], ['freebsd'])
        self.assertEqual(item['coverage']['planned_not_implemented'], ['freebsd'])
        self.assertEqual(item['coverage']['implemented_not_declared_tested'], ['linux'])
        self.assertEqual(item['implementations'][0]['file_status'], 'valid')
        self.assertEqual(item['implementations'][0]['declaration']['match']['os_version'], '>=12')
        self.assertEqual(item['runner_contract'], 'unsupported-recipe-id')

    def test_missing_entrypoint_and_wrong_version_reported(self):
        (self.recipe / 'linux.py').unlink()
        report = inspection.inspect_recipes(str(self.recipe))
        self.assertEqual(report['status'], 'failed')
        self.assertIn('missing', report['recipes'][0]['errors'][0])
        (self.recipe / 'linux.py').write_text("VERSION = '2.0.0'\n")
        self.assertIn('differs', inspection.inspect_recipes(str(self.recipe))['recipes'][0]['errors'][0])

    def test_descriptor_and_entrypoint_symlink_escapes_rejected(self):
        outside = self.root / 'outside.py'
        outside.write_text("VERSION = '1.0.0'\n")
        (self.recipe / 'linux.py').unlink()
        (self.recipe / 'linux.py').symlink_to(outside)
        self.assertIn('escapes', inspection.inspect_recipes(str(self.recipe))['recipes'][0]['errors'][0])
        outside_metadata = self.root / 'outside.yaml'
        outside_metadata.write_text(json.dumps(self.metadata))
        (self.recipe / 'recipe.yaml').unlink()
        (self.recipe / 'recipe.yaml').symlink_to(outside_metadata)
        self.assertIsNone(inspection.inspect_recipes(str(self.recipe))['recipes'][0]['descriptor'])

    def test_malformed_recipe_does_not_hide_other_recipes(self):
        other = self.recipes / 'broken'
        other.mkdir()
        (other / 'recipe.yaml').write_text('id: [')
        with patch.object(inspection, 'REPOSITORY_RECIPES', self.recipes):
            report = inspection.inspect_recipes()
        self.assertEqual(len(report['recipes']), 2)
        self.assertEqual([r['status'] for r in report['recipes']], ['failed', 'success'])
        self.assertEqual(report['status'], 'failed')

    def test_short_paths_and_explicit_paths(self):
        with patch.object(inspection, 'REPOSITORY_RECIPES', self.recipes):
            for value in ('custom', 'recipes/custom'):
                self.assertEqual(inspection.recipe_path(value), self.recipe)
            with self.assertRaises(ops.ConfigError):
                inspection.recipe_path('recipes/../../outside')
        self.assertEqual(inspection.recipe_path(str(self.recipe)), self.recipe)

    def test_cli_failed_inspection_nonzero_and_text_output(self):
        (self.recipe / 'linux.py').write_text('this is invalid python (')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = ops.main(['inspect-recipe', str(self.recipe)])
        self.assertEqual(code, 1)
        self.assertIn('invalid Python syntax', output.getvalue())
        self.assertIn('Metadata/static inspection only', output.getvalue())

    def test_default_summary_keeps_platform_gaps_without_full_metadata(self):
        report = inspection.inspect_recipes(str(self.recipe))
        text = inspection.format_report(report)
        self.assertIn('Implemented: linux', text)
        self.assertIn('Declared tested: none declared', text)
        self.assertIn('Planned only: freebsd', text)
        self.assertNotIn('dependencies:', text)
        self.assertNotIn('os_version', text)
        self.assertLessEqual(len(text.splitlines()), 9)

    def test_platform_summary_focuses_on_requested_os_and_constraints(self):
        report = inspection.inspect_recipes(str(self.recipe), ['linux', 'freebsd', 'openbsd'])
        text = inspection.format_report(report)
        self.assertIn('linux: implemented; not declared tested', text)
        self.assertIn('distribution_id=debian, os_version=>=12', text)
        self.assertIn('freebsd: planned; not implemented', text)
        self.assertIn('openbsd: not declared supported', text)
        self.assertNotIn('dependencies:', text)
        report = inspection.inspect_recipes('inventory/system', ['freebsd'])
        text = inspection.format_report(report)
        self.assertIn('freebsd: implemented', text)
        self.assertIn('ssh: not-tested', text)
        self.assertNotIn('linux', text)
        self.assertNotIn('macos', text)

    def test_details_preserves_full_human_output_and_cli_flag(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = ops.main(['inspect-recipe', str(self.recipe), '--details'])
        self.assertEqual(code, 0)
        self.assertIn('dependencies:', output.getvalue())
        self.assertIn(str(self.recipe), output.getvalue())
        self.assertIn('os_version', output.getvalue())

    def test_inventory_contract_uses_existing_validator(self):
        report = inspection.inspect_recipes('inventory/system', ['linux', 'freebsd', 'macos', 'openbsd'])
        self.assertEqual(report['status'], 'success')
        item = report['recipes'][0]
        self.assertEqual(item['runner_contract'], 'valid-inventory-system')
        self.assertEqual(item['coverage']['not_declared_implemented'], ['openbsd'])
        self.assertEqual(len(item['implementations']), 4)


if __name__ == '__main__':
    unittest.main()
