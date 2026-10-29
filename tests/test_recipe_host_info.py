"""Recipe system context from saved host-init data; synthetic hosts only."""
import json
import unittest
from unittest.mock import patch

import test_core_api as fixture
import host_runtime as hr


FIELDS = {'host_id', 'observed_at', 'os_name', 'os_version', 'distribution_id',
          'distribution_name', 'distribution_version', 'kernel_name',
          'kernel_release', 'architecture', 'python_version', 'python_executable'}


class RecipeHostInfoTests(unittest.TestCase):
    setUp = fixture.CoreTests.setUp
    write = fixture.CoreTests.write
    connection = fixture.CoreTests.connection

    def save(self, *, status='success', facts=None):
        report = {'schema_version': hr.FACTS_VERSION, 'host_id': 'h',
                  'status': status, 'observed_at': '2026-10-29T00:00:00+00:00',
                  'target_fingerprint': hr.target_fingerprint(self.profile.hosts._config, 'h'),
                  'facts': facts if facts is not None else {
                      'os_name': 'linux', 'distribution_id': 'ubuntu',
                      'distribution_name': 'Ubuntu', 'distribution_version': '24.04',
                      'kernel_name': 'Linux', 'kernel_release': '6.8',
                      'architecture': 'x86_64', 'python_version': '3.12.8',
                      'python_executable': '/usr/bin/python3'}}
        hr.save_facts(self.profile.hosts._config, 'h', report)
        return report

    def test_missing_info_never_initializes_or_runs_commands(self):
        scope, actor = self.connection()
        with scope as recipe:
            with patch.object(hr, 'discover', side_effect=AssertionError('must not probe')), \
                    patch.object(hr, 'initialize_host', side_effect=AssertionError('must not initialize')), \
                    patch.object(actor, 'exec_command', side_effect=AssertionError('must not execute')):
                info = recipe.host_info
        self.assertEqual(set(info), FIELDS)
        self.assertEqual(info['host_id'], 'h')
        self.assertTrue(all(value is None for key, value in info.items() if key != 'host_id'))
        self.assertFalse((self.management / 'observations').exists())

    def test_saved_facts_are_copied_and_not_written(self):
        report = self.save()
        path = hr.cache_path(self.profile.hosts._config, 'h')
        before = path.read_bytes()
        scope, actor = self.connection()
        with scope as recipe:
            with patch.object(actor, 'exec_command', side_effect=AssertionError('must not execute')):
                info = recipe.host_info
                self.assertEqual(set(info), FIELDS)
                self.assertEqual(info['distribution_version'], '24.04')
                self.assertEqual(info['python_executable'], '/usr/bin/python3')
                self.assertEqual(info['observed_at'], report['observed_at'])
                self.assertIsNone(info['os_version'])
                info['distribution_id'] = 'changed-copy'
                self.assertEqual(recipe.host_info['distribution_id'], 'ubuntu')
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn('private-', json.dumps(recipe.host_info))
        self.assertEqual(recipe.host_info['python_version'], '3.12.8')

    def test_partial_os_facts_do_not_require_python_or_distribution(self):
        self.save(facts={'os_name': 'macos', 'os_version': '15.0',
                         'architecture': 'arm64'})
        scope, _ = self.connection()
        with scope as recipe:
            info = recipe.host_info
        self.assertEqual(info['os_name'], 'macos')
        self.assertEqual(info['os_version'], '15.0')
        self.assertIsNone(info['python_version'])
        self.assertIsNone(info['python_executable'])
        self.assertIsNone(info['distribution_version'])

    def test_failed_latest_does_not_read_previous_success(self):
        report = self.save(status='failed', facts={})
        report['previous_success'] = {'observed_at': report['observed_at'],
                                      'facts': {'os_name': 'linux', 'python_version': '3.12.8'}}
        hr.save_facts(self.profile.hosts._config, 'h', report)
        scope, _ = self.connection()
        with scope as recipe:
            self.assertIsNone(recipe.host_info['observed_at'])
            self.assertIsNone(recipe.host_info['os_name'])
            self.assertIsNone(recipe.host_info['python_version'])

    def test_each_access_reads_latest_saved_initialization(self):
        self.save()
        scope, _ = self.connection()
        with scope as recipe:
            self.assertEqual(recipe.host_info['distribution_id'], 'ubuntu')
            self.save(facts={'os_name': 'linux', 'distribution_id': 'debian',
                             'distribution_version': '13'})
            self.assertEqual(recipe.host_info['distribution_id'], 'debian')
            self.assertIsNone(recipe.host_info['python_version'])

    def test_child_recipe_keeps_login_python_information(self):
        self.save()
        scope, _ = self.connection()
        with scope as recipe:
            original = recipe.host_info
            with recipe.sudo(user='root') as child:
                self.assertEqual(child.host_info, original)
                self.assertEqual(recipe.host_info, original)
        self.assertEqual(recipe.host_info, original)


if __name__ == '__main__':
    unittest.main()
