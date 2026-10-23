"""Synthetic setup checks: no installations, scheduler changes or SSH calls."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import check_environment as environment
import skill_bundle as bundle


def archive_bytes(extra=(), contract='6.0.0', omitted=()):
    stream = io.BytesIO()
    files = {
        'SKILL.md': f'SSHScript {contract} contract',
        'references/agent-guide.md': f'Documentation contract: SSHScript {contract}',
        'references/api-guide.md': 'synthetic API',
        'references/versioning.md': 'synthetic policy',
        'references/console.md': 'synthetic console',
    }
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, data in files.items():
            if name not in omitted:
                archive.writestr('sshscript/' + name, data)
        for name, data in extra:
            archive.writestr(name, data)
    return stream.getvalue()


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.content = archive_bytes(extra=[('sshscript/assets/extra.txt', 'complete bundle')])
        self.candidate = self.root / 'candidate'
        bundle.stage(self.content, self.candidate)
        self.installed = self.candidate / 'sshscript'

    def test_stage_preserves_complete_bundle_and_provenance(self):
        self.assertEqual((self.candidate / 'sshscript-skill.zip').read_bytes(), self.content)
        source = json.loads((self.installed / 'SOURCE.json').read_text())
        self.assertEqual(source['bundle_sha256'], hashlib.sha256(self.content).hexdigest())
        self.assertEqual(source['documentation_contract'], '6.0.0')
        self.assertEqual((self.installed / 'assets/extra.txt').read_text(), 'complete bundle')

    def test_check_is_read_only_and_detects_local_modifications(self):
        source = (self.installed / 'SOURCE.json').read_bytes()
        self.assertEqual(bundle.check(self.content, self.installed)['status'], 'unchanged')
        self.assertTrue(bundle.check(self.content, self.installed)['contract_matches_runner'])
        (self.installed / 'SKILL.md').write_text('local edit')
        report = bundle.check(self.content, self.installed)
        self.assertEqual(report['status'], 'review_required')
        self.assertFalse(report['bundle_changed'])
        self.assertFalse(report['local_matches_candidate'])
        self.assertEqual((self.installed / 'SKILL.md').read_text(), 'local edit')
        self.assertEqual((self.installed / 'SOURCE.json').read_bytes(), source)

    def test_default_check_uses_central_skill_source(self):
        bundle.stage(self.content, self.root / 'skills')
        with patch.object(bundle, 'ROOT', self.root):
            self.assertEqual(bundle.check(self.content)['status'], 'unchanged')

    def test_default_check_does_not_fall_back_to_agent_copy(self):
        bundle.stage(self.content, self.root / '.agents/skills')
        with patch.object(bundle, 'ROOT', self.root):
            with self.assertRaises(FileNotFoundError):
                bundle.check(self.content)

    def test_changed_contract_reported_without_replacement(self):
        report = bundle.check(archive_bytes(contract='7.0.0'), self.installed)
        self.assertTrue(report['bundle_changed'])
        self.assertFalse(report['contract_matches_runner'])
        self.assertEqual(report['installed_contract'], '6.0.0')
        self.assertEqual(report['candidate_contract'], '7.0.0')

    def test_existing_destination_not_overwritten(self):
        with self.assertRaises(FileExistsError):
            bundle.stage(self.content, self.candidate)
        self.assertEqual((self.candidate / 'sshscript-skill.zip').read_bytes(), self.content)

    def test_invalid_archive_rejected_before_creating_destination(self):
        cases = [b'not a zip', archive_bytes(omitted=['references/api-guide.md']),
                 archive_bytes(omitted=['references/console.md'])]
        for path in ('../escape', 'sshscript/../escape', '/sshscript/absolute',
                     'other/SKILL.md', 'sshscript/SOURCE.json', 'sshscript/./file', 'sshscript\\file'):
            cases.append(archive_bytes(extra=[(path, 'invalid')]))
        link = zipfile.ZipInfo('sshscript/link')
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        cases.append(archive_bytes(extra=[(link, '../outside')]))
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            cases.append(archive_bytes(extra=[('sshscript/SKILL.md', 'duplicate')]))
        for content in cases:
            with self.subTest(size=len(content)):
                destination = self.root / 'rejected'
                with self.assertRaises((bundle.BundleError, zipfile.BadZipFile)):
                    bundle.stage(content, destination)
                self.assertFalse(destination.exists())

    def test_inconsistent_contract_and_expansion_limit(self):
        with self.assertRaises(bundle.BundleError):
            bundle.inspect_bundle(archive_bytes(contract='unknown'))
        with patch.object(bundle, 'LIMIT', 10), self.assertRaises(bundle.BundleError):
            bundle.inspect_bundle(self.content)

    def test_failed_write_cleans_only_new_candidate(self):
        destination = self.root / 'partial'
        with patch.object(Path, 'write_bytes', side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):
                bundle.stage(self.content, destination)
        self.assertFalse(destination.exists())
        self.assertTrue(self.installed.exists())

    def test_fetch_limit_and_redirect_host(self):
        for url, content in (('https://example.invalid/file', b'zip'),
                             (bundle.SOURCE_URL, b'x' * 11)):
            response = SimpleNamespace(url=url, read=lambda size: content)
            with patch.object(bundle.urllib.request, 'urlopen') as opened, patch.object(bundle, 'LIMIT', 10):
                opened.return_value.__enter__.return_value = response
                with self.assertRaises(bundle.BundleError):
                    bundle.fetch_bundle()

    def test_network_failure_not_reported_as_unchanged(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(bundle, 'fetch_bundle', side_effect=OSError('sensitive detail')), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(bundle.main(['check']), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(errors.getvalue(), 'ERROR: OSError\n')


class EnvironmentTests(unittest.TestCase):
    def test_central_skill_source_and_missing_reference(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            bundle.stage(archive_bytes(), root / 'skills')
            with patch.object(environment, 'ROOT', root), \
                    patch.object(environment, 'inspect_package', return_value={'ready': True}):
                self.assertTrue(environment.inspect_environment()['ready'])
                (root / 'skills/sshscript/references/api-guide.md').unlink()
                self.assertFalse(environment.inspect_environment()['skill']['ready'])
                (root / 'skills/sshscript/references/api-guide.md').write_text('synthetic API')
                (root / 'skills/sshscript/references/console.md').unlink()
                self.assertFalse(environment.inspect_environment()['skill']['ready'])

    def test_agent_copy_does_not_replace_missing_source(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            bundle.stage(archive_bytes(), root / '.agents/skills')
            with patch.object(environment, 'ROOT', root), \
                    patch.object(environment, 'inspect_package', return_value={'ready': True}):
                self.assertFalse(environment.inspect_environment()['ready'])

    def test_import_distribution_mismatch_and_missing_package(self):
        module = SimpleNamespace(__version__='5.0.0', __file__='/synthetic/module.py')
        with patch.object(environment, 'import_module', return_value=module), \
                patch.object(environment.metadata, 'version', return_value='4.0.2'):
            self.assertFalse(environment.inspect_package('sshscript', '5.0.0')['ready'])
        with patch.object(environment, 'import_module', side_effect=ImportError):
            self.assertEqual(environment.inspect_package('sshscript')['error'], 'ImportError')

    def test_pyyaml_uses_distribution_name(self):
        module = SimpleNamespace(__version__='6.0.3', __file__='/synthetic/yaml.py')
        with patch.object(environment, 'import_module', return_value=module), \
                patch.object(environment.metadata, 'version', return_value='6.0.3') as version:
            self.assertTrue(environment.inspect_package('yaml', '6.0.3', 'PyYAML')['ready'])
        version.assert_called_once_with('PyYAML')

    def test_init_scope_does_not_import_sshscript(self):
        with patch.object(environment, 'inspect_package', return_value={'ready': True}) as inspect:
            report = environment.inspect_environment('init')
        self.assertEqual(inspect.call_args_list, [unittest.mock.call('yaml', '6.0.3', 'PyYAML'),
                                               unittest.mock.call('tabulate', '0.10.0'), unittest.mock.call('wcwidth')])
        self.assertTrue(report['ready'])

    def test_missing_skill_not_ready(self):
        with tempfile.TemporaryDirectory() as root, patch.object(environment, 'ROOT', Path(root)), \
                patch.object(environment, 'inspect_package', return_value={'ready': True}):
            self.assertFalse(environment.inspect_environment()['ready'])


if __name__ == '__main__':
    unittest.main()
