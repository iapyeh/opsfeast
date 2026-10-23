"""Synthetic dependency gates; no package installation or host connections."""
from importlib import metadata
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_environment as environment
import host_runtime
import recipe_runner
from opsfeast import ConfigError


class SSHScriptUpdateTests(unittest.TestCase):
    def test_runtime_gates_accept_matching_supported_version(self):
        module = SimpleNamespace(__version__='6.0.0', Session=object())
        with patch.dict(sys.modules, sshscript=module), \
                patch.object(recipe_runner, 'version', return_value='6.0.0'), \
                patch.object(metadata, 'version', return_value='6.0.0'):
            session, report = recipe_runner.load_runtime()
            self.assertIs(session, module.Session)
            self.assertIs(host_runtime.runtime_class(), module.Session)
            self.assertEqual(report['sshscript_import'], '6.0.0')
            self.assertEqual(report['sshscript_distribution'], '6.0.0')

    def test_old_newer_and_mismatched_versions_are_rejected_before_session(self):
        for imported, installed in [('5.0.0', '5.0.0'), ('7.0.0', '7.0.0'),
                                    ('6.0.0', '5.0.0'), ('5.0.0', '6.0.0')]:
            with self.subTest(imported=imported, installed=installed):
                module = SimpleNamespace(__version__=imported)
                with patch.dict(sys.modules, sshscript=module), \
                        patch.object(recipe_runner, 'version', return_value=installed), \
                        patch.object(metadata, 'version', return_value=installed):
                    with self.assertRaisesRegex(ConfigError, '6.0.0'):
                        recipe_runner.load_runtime()
                    with self.assertRaisesRegex(ConfigError, '6.0.0'):
                        host_runtime.runtime_class()

    def test_full_readiness_checks_package_and_complete_skill_contract(self):
        with patch.object(environment, 'inspect_package', return_value={'ready': True}) as inspect:
            self.assertTrue(environment.inspect_environment()['ready'])
        self.assertIn(unittest.mock.call('sshscript', '6.0.0'), inspect.call_args_list)

    def test_matching_package_does_not_hide_old_skill_contract(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / 'skills/sshscript'
            skill.mkdir(parents=True)
            (skill / 'SOURCE.json').write_text(json.dumps({'documentation_contract': '5.0.0'}))
            for relative in ('SKILL.md', 'references/agent-guide.md',
                             'references/api-guide.md', 'references/versioning.md',
                             'references/console.md'):
                path = skill / relative
                path.parent.mkdir(exist_ok=True)
                path.write_text('synthetic old contract')
            with patch.object(environment, 'ROOT', root), \
                    patch.object(environment, 'inspect_package', return_value={'ready': True}):
                self.assertFalse(environment.inspect_environment()['ready'])


if __name__ == '__main__':
    unittest.main()
