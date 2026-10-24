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
import sshscript_runtime
from opsfeast import ConfigError


class SSHScriptUpdateTests(unittest.TestCase):
    def test_runtime_gates_accept_matching_supported_version(self):
        module = SimpleNamespace(__version__='7.0.0', Session=object())
        with patch.dict(sys.modules, sshscript=module), \
                patch.object(recipe_runner, 'version', return_value='7.0.0'), \
                patch.object(metadata, 'version', return_value='7.0.0'), \
                patch.object(sshscript_runtime, 'source_identity', return_value={
                    'source_matches': True, 'source_commit': sshscript_runtime.SOURCE_COMMIT}):
            session, report = recipe_runner.load_runtime()
            self.assertIs(session, module.Session)
            self.assertIs(host_runtime.runtime_class(), module.Session)
            self.assertEqual(report['sshscript_import'], '7.0.0')
            self.assertEqual(report['sshscript_distribution'], '7.0.0')

    def test_old_newer_and_mismatched_versions_are_rejected_before_session(self):
        for imported, installed in [('6.0.0', '6.0.0'), ('6.1.0', '6.1.0'), ('8.0.0', '8.0.0'),
                                    ('7.0.0', '5.0.0'), ('5.0.0', '7.0.0')]:
            with self.subTest(imported=imported, installed=installed):
                module = SimpleNamespace(__version__=imported)
                with patch.dict(sys.modules, sshscript=module), \
                        patch.object(recipe_runner, 'version', return_value=installed), \
                        patch.object(metadata, 'version', return_value=installed):
                    with self.assertRaisesRegex(ConfigError, '7.0.0'):
                        recipe_runner.load_runtime()
                    with self.assertRaisesRegex(ConfigError, '7.0.0'):
                        host_runtime.runtime_class()

    def test_full_readiness_checks_package_and_complete_skill_contract(self):
        with patch.object(environment, 'inspect_package', return_value={'ready': True}) as inspect:
            self.assertTrue(environment.inspect_environment()['ready'])
        self.assertIn(unittest.mock.call('sshscript', '7.0.0'), inspect.call_args_list)

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

    def test_same_version_wrong_source_rejected_by_all_entrypoints(self):
        module = SimpleNamespace(__version__='7.0.0', Session=unittest.mock.Mock())
        with patch.dict(sys.modules, sshscript=module), \
                patch.object(recipe_runner, 'version', return_value='7.0.0'), \
                patch.object(metadata, 'version', return_value='7.0.0'), \
                patch.object(sshscript_runtime, 'source_identity', return_value={'source_matches': False}):
            from opsfeast import load_session_class
            for acquire in (recipe_runner.load_runtime, host_runtime.runtime_class, load_session_class):
                with self.assertRaisesRegex(ConfigError, sshscript_runtime.SOURCE_COMMIT):
                    acquire()
            module.Session.assert_not_called()

    def test_native_source_and_module_type_file_drift(self):
        import shutil
        import tempfile
        import sshscript
        identity = sshscript_runtime.source_identity()
        self.assertTrue(identity['source_matches'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = Path(sshscript.__file__).parent
            for name in sshscript_runtime.CONTRACT['files']:
                shutil.copyfile(installed / name, root / name)
            module = SimpleNamespace(__file__=str(root / '__init__.py'))
            self.assertTrue(sshscript_runtime.source_identity(module)['source_matches'])
            for name in ('session.py', 'session.pyi', 'py.typed'):
                original = (root / name).read_bytes()
                (root / name).write_bytes(original + b'\n')
                self.assertFalse(sshscript_runtime.source_identity(module)['source_matches'])
                (root / name).write_bytes(original)
            (root / 'unexpected.py').write_text('')
            self.assertFalse(sshscript_runtime.source_identity(module)['source_matches'])
            (root / 'unexpected.py').unlink()
            (root / 'session.pyi').unlink()
            self.assertFalse(sshscript_runtime.source_identity(module)['source_matches'])

    def test_native_resolver_uses_new_names_and_preserves_key_source(self):
        from sshscript import Session
        result = Session.resolve_connection('example.invalid', username='operator', ssh_config=False,
                                            parent_key_filename='/synthetic/parent-key',
                                            proxy_command='synthetic-proxy')
        self.assertEqual(result['parent_key_filename'], '/synthetic/parent-key')
        self.assertEqual(result['proxy_command'], 'synthetic-proxy')
        self.assertNotIn('pkey_path', result)
        self.assertNotIn('proxyCommand', result)
        for name in ('pkey_path', 'proxyCommand', 'proxyJump'):
            with self.subTest(name=name), self.assertRaises(TypeError):
                Session.resolve_connection('example.invalid', ssh_config=False, **{name: 'synthetic'})

    def test_dependency_surfaces_bind_the_same_public_source(self):
        import tomllib
        from packaging.requirements import Requirement
        import build_backend
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text())
        requirement = sshscript_runtime.REQUIREMENT
        self.assertEqual(project['project']['optional-dependencies']['execution'], [requirement])
        self.assertIn(requirement, (ROOT / 'requirements.txt').read_text().splitlines())
        metadata = build_backend._metadata()
        requirements = [line.removeprefix('Requires-Dist: ') for line in metadata.splitlines()
                        if line.startswith('Requires-Dist: ')]
        parsed = [Requirement(value) for value in requirements]
        selected = next(value for value in parsed if value.name == 'sshscript')
        self.assertEqual(selected.url, Requirement(requirement).url)
        self.assertIn(sshscript_runtime.SOURCE_COMMIT, selected.url)

    def test_native_borrowed_console_state_job_and_session_reuse(self):
        import time
        from sshscript import Session, Console
        local = Session()
        try:
            with Console(local, ownership='borrowed') as console:
                self.assertEqual(console.submit('value = 42').state, 'completed')
                printed = console.submit('print(value)')
                self.assertEqual(printed.state, 'completed')
                self.assertIn('42', printed.stdout)
                self.assertEqual(console.submit('$export OPSFEAST_TEST=value; cd /tmp').state, 'completed')
                update = console.start_command('printf "%s" "$OPSFEAST_TEST"', timeout=3)
                deadline = time.monotonic() + 8
                while update.state == 'running' and time.monotonic() < deadline:
                    time.sleep(.02)
                    update = console.poll()
                self.assertEqual(update.state, 'completed')
                self.assertEqual(update.result.exitcode, 0)
                self.assertEqual(update.result.stdout, 'value')
            self.assertEqual(console.session_reuse, 'confirmed')
            self.assertEqual(local.exec_command(['printf', 'reusable'], check=True,
                                                 command_timeout=3).stdout, 'reusable')
        finally:
            local.close(strict=True)


if __name__ == '__main__':
    unittest.main()
