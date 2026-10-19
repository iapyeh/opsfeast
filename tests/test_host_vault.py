"""Synthetic vault histories, projection repair, namespace and audit contracts."""
import copy
import contextlib
import io
from concurrent.futures import ThreadPoolExecutor
import json
import shlex
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import host_vault as vault
import retention_store as store
import observation_store as legacy
from opsfeast import ConfigError, instance_definition
from test_result_data import raw


class VaultTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        (self.root / 'feast.yaml').write_text('schema_version: 1\nkind: opsfeast\n')
        (self.root / 'hosts.yaml').write_text('hosts:\n  node:\n    connection: {local: true}\n    group: [production]\n')

    def enable(self):
        return store.initialize(self.root, 'example-production')

    def host(self):
        return self.root / 'vault' / 'hosts' / vault.component('node')

    def test_settings_definition_and_namespace_change_guard(self):
        self.enable()
        instance_definition(self.root)
        self.assertEqual(store.settings(self.root)['namespace'], 'example-production')
        with self.assertRaises(ConfigError):
            store.initialize(self.root, 'different')
        for name in ('', '../escape', 'UPPER', 'a' * 64):
            with self.assertRaises(ConfigError):
                store.validate_settings({'namespace': name})
        with self.assertRaises(ConfigError):
            store.validate_settings({'namespace': 'valid', 'overview_months': True})

    def test_migrate_defaults_to_saved_namespace_then_supplied_profile_name(self):
        self.assertEqual(store.initialize(self.root, profile='initial')['status'], 'success')
        self.assertEqual(store.settings(self.root)['namespace'], 'initial')
        store.initialize(self.root, profile='renamed')
        self.assertEqual(store.settings(self.root)['namespace'], 'initial')

    def test_init_then_first_inventory_automatically_retains_without_migrate(self):
        import test_inventory_system as inventory
        from opsfeast import initialize
        fixture = inventory.RunnerTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        initialize(fixture.root, quiet=True, profile='first-inventory')
        # Keep execution synthetic while exercising the runner's operational retention path.
        import run_recipe
        from contextlib import nullcontext
        with patch('inventory_actor.collection_actor', return_value=nullcontext(fixture.session)):
            report, path = run_recipe.run(fixture.root, 'example', session_class=fixture.session_class,
                                          runtime={'verification': 'synthetic-test'}, access_checked=True)
        self.assertEqual(report['status'], 'success', report)
        self.assertEqual(report['retention']['status'], 'stored')
        self.assertEqual(path.parent, fixture.root.resolve() / 'observations')
        found = store.records(fixture.root)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['namespace'], 'first-inventory')
        self.assertTrue((fixture.root / 'vault/HOSTS.md').exists())
        initialize(fixture.root, quiet=True, profile='renamed')
        self.assertEqual(store.records(fixture.root), found)

    def test_core_profile_init_namespace_override_and_saved_default(self):
        from opsfeast import Instance
        installation = self.root / 'installation'
        installation.mkdir()
        instance = Instance.open(installation)
        profile = instance.init_profile('Team.Production', namespace='production')
        self.assertEqual(store.settings(profile.root)['namespace'], 'production')
        self.assertTrue((profile.root / 'vault/HOSTS.md').exists())
        instance.init_profile('Team.Production')
        self.assertEqual(store.settings(profile.root)['namespace'], 'production')

    def test_migrate_preserves_legacy_and_record_ids_and_replays(self):
        receipt = legacy.retain(self.root, raw())
        original = (self.root / 'records/observations.sqlite3').read_bytes()
        result = self.enable()
        self.assertEqual(result['records'], 0)
        legacy.retain(self.root, raw())
        self.assertEqual((self.root / 'records/observations.sqlite3').read_bytes(), original)
        record = store.records(self.root)[0]
        self.assertNotEqual(record['record_id'], receipt['observation_id'])
        self.assertEqual(record['namespace'], 'example-production')
        self.assertEqual(legacy.export(self.root)['records'][0]['observation_id'], record['record_id'])
        self.enable()
        self.assertEqual(len(store.records(self.root)), 1)

    def test_archive_year_copies_and_replay(self):
        self.enable()
        first = legacy.retain(self.root, raw())
        self.assertTrue((self.root / 'retention/hosts/node/2026/observations.sqlite3').exists())
        self.assertTrue((self.root / 'retention/hosts/node/records/observations.sqlite3').exists())
        self.assertEqual(legacy.retain(self.root, raw())['status'], 'already_stored')
        self.assertEqual(first['host_key'], 'example-production/node')
        with store.database(self.root / 'retention/hosts/node/records/observations.sqlite3') as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM records').fetchone()[0], 1)

    def test_human_index_groups_states_and_executable_rebuild_guidance(self):
        (self.root / 'hosts.yaml').write_text('hosts:\n  node:\n    connection: {local: true}\n    group: [production, database]\n  empty:\n    connection: {local: true}\n')
        self.enable()
        report = raw()
        report.update(status='partial', finished_at='2026-10-13T00:00:10.123456+00:00')
        report['observations']['hostname'].update(value=None, status='unavailable', error={'code': 'missing'})
        legacy.retain(self.root, report)
        page = (self.root / 'vault' / 'HOSTS.md').read_text()
        self.assertTrue(page.startswith(vault.NOTICE + 'To regenerate this view'))
        command = page.split('```sh\n', 1)[1].split('\n```', 1)[0]
        self.assertEqual(shlex.split(command), ['cd', str(Path(vault.PACKAGE_FILE).resolve().parents[1]), '&&',
                                               'python3', '-B', '-m', 'opsfeast', 'vault', 'rebuild',
                                               '--root', str(self.root), '--json'])
        self.assertIn('| Last observation | Status |', page)
        self.assertIn('| production,database |', page)
        self.assertIn('| partial |', page)
        self.assertIn('| never | no observations |', page)
        self.assertIn(vault.format_time(report['finished_at']), page)
        self.assertNotIn('.123456', page)
        self.assertIn('To regenerate this view', (self.root / 'vault/overview/README.md').read_text())
        # The view must not change archive precision or classification.
        self.assertEqual(store.records(self.root)[0]['observed_at'], report['finished_at'])

    def test_group_cells_handle_scalar_list_and_empty_memberships(self):
        for membership, expected in (
            ('group: backup', 'backup'),
            ('group: [backup]', 'backup'),
            ('group: [backup, production]', 'backup,production'),
            ('group: 備份', '備份'),
            ('group: []', ''),
            ('', ''),
        ):
            with self.subTest(membership=membership):
                config = 'hosts:\n  node:\n    connection: {local: true}\n'
                if membership:
                    config += '    ' + membership + '\n'
                (self.root / 'hosts.yaml').write_text(config)
                self.enable()
                for name in ('HOSTS.md', 'overview/README.md'):
                    page = (self.root / 'vault' / name).read_text()
                    table = [line for line in page.splitlines() if line.startswith('|')]
                    self.assertTrue(all(len(line.split('|')) == 8 for line in table), name)
                    row = next(line for line in table if line.startswith('| [node]'))
                    self.assertEqual(row.split('|')[3].strip(), expected)
                self.assertEqual((self.root / 'hosts.yaml').read_text(), config)

    def test_all_generated_vault_times_use_local_seconds_without_mutating_records(self):
        self.enable()
        report = raw()
        report['finished_at'] = '2026-10-13T00:00:10.123456+00:00'
        report['observations']['hostname']['observed_at'] = '2026-10-13T00:00:01.654321+00:00'
        legacy.retain(self.root, report)
        intent = store.operation_intent(self.root, 'node', {'id': 'update', 'version': '1', 'access_mode': 'write'}, 'a' * 64, [])
        before = copy.deepcopy(store.records(self.root))
        vault.rebuild(self.root)
        vault.refresh_groups(self.root)
        for path in self.root.rglob('*.md'):
            with self.subTest(path=path.relative_to(self.root)):
                page = path.read_text()
                self.assertRegex(page, r'_Last modified: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}_\n$')
                self.assertNotRegex(page, r'\d{2}:\d{2}:\d{2}\.\d+')
        self.assertEqual(store.records(self.root), before)
        self.assertIn(intent['observed_at'], json.dumps(before))

    def test_native_identity_changes_do_not_split_logical_host(self):
        self.enable()
        first = raw()
        first['identity'] = {'schema_version': '0.1.0', 'method': 'linux-machine-id-hmac-sha256-v1',
                             'quality': 'machine-derived', 'os_instance_key': 'linux:' + 'a' * 64, 'evidence': []}
        a = legacy.retain(self.root, first)
        first['identity']['os_instance_key'] = 'linux:' + 'b' * 64
        b = legacy.retain(self.root, first)
        self.assertEqual(a['host_key'], b['host_key'])
        self.assertEqual(len(store.records(self.root)), 2)

    def test_vault_is_separate_from_profile_inputs_and_human_root_files(self):
        (self.root / 'README.md').write_text('Private profile notes')
        (self.root / 'hosts').mkdir()
        (self.root / 'hosts/config.yaml').write_text('Private host configuration')
        (self.root / 'observations').mkdir()
        (self.root / 'observations/raw.json').write_text('Private raw data')
        self.enable()
        legacy.retain(self.root, raw())
        vault.refresh_groups(self.root)
        self.assertTrue((self.root / 'vault/HOSTS.md').exists())
        for name in ('observations', 'hosts.yaml', 'feast.yaml', 'hosts/config.yaml'):
            self.assertFalse((self.root / 'vault' / name).exists())
        self.assertEqual((self.root / 'README.md').read_text(), 'Private profile notes')
        self.assertFalse((self.root / 'HOSTS.md').exists())

    def test_view_failure_preserves_archive_and_rebuild_repairs(self):
        self.enable()
        with patch('vault_content.build', side_effect=OSError('synthetic')):
            receipt = legacy.retain(self.root, raw())
        self.assertEqual(receipt['status'], 'stored')
        self.assertEqual(receipt['content_update']['status'], 'failed')
        self.assertEqual(len(store.records(self.root)), 1)
        shutil.rmtree(self.host() / 'records')
        self.assertEqual(vault.rebuild(self.root)['records'], 1)
        self.assertTrue((self.host() / 'records/README.md').exists())
        self.assertEqual(legacy.retain(self.root, raw())['status'], 'already_stored')

    def test_latest_partial_not_silently_filled_from_previous(self):
        self.enable()
        legacy.retain(self.root, raw())
        report = raw()
        report['finished_at'] = '2026-10-14T00:00:00Z'
        report['status'] = 'partial'
        report['observations']['hostname'].update(value=None, status='unavailable', error={'code': 'missing'})
        legacy.retain(self.root, report)
        markdown = (self.host() / 'records' / (vault.component('inventory-system') + '.md')).read_text()
        self.assertIn('partial', markdown)
        self.assertIn('hostname | None | unavailable', markdown)
        self.assertIn(vault.NOTICE, markdown)

    def test_overview_expiry_does_not_remove_old_host_or_history(self):
        self.enable()
        with patch.object(store, 'cutoff', return_value='2099-01-01T00:00:00.000000+00:00'):
            legacy.retain(self.root, raw())
        with store.database(self.root / 'retention/overview/observations.sqlite3') as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM records').fetchone()[0], 0)
        self.assertIn('node', (self.root / 'vault' / 'HOSTS.md').read_text())
        self.assertEqual(len(store.records(self.root)), 1)

    def test_group_refresh_preserves_notes_and_removes_only_managed_links(self):
        self.enable()
        vault.refresh_groups(self.root)
        folder = self.root / 'vault' / 'groups' / vault.component('production')
        link = folder / (vault.component('node') + '.md')
        self.assertIn('../../hosts/', link.read_text())
        (folder / 'notes.md').write_text('human notes')
        (self.root / 'hosts.yaml').write_text('hosts: {}\n')
        vault.refresh_groups(self.root)
        self.assertFalse(link.exists())
        self.assertEqual((folder / 'notes.md').read_text(), 'human notes')

    def test_safe_paths_case_unicode_and_symlink_rejection(self):
        self.assertNotEqual(vault.component('A').lower(), vault.component('a').lower())
        for name in ('../x', 'CON', 'a/b', '中文'):
            self.assertNotIn('/', vault.component(name))
        self.enable()
        (self.root / 'vault' / 'hosts' / vault.component('node')).mkdir(exist_ok=True)
        (self.root / 'retention/hosts/node').mkdir(parents=True, exist_ok=True)
        (self.root / 'retention/hosts/node/2026').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ConfigError):
            legacy.retain(self.root, raw())

    def test_write_unknown_audit_append_only_and_read_exclusion(self):
        self.enable()
        metadata = {'id': 'update-example', 'version': '1.0', 'access_mode': 'write'}
        intent = store.operation_intent(self.root, 'node', metadata, 'a' * 64, {'password': 'never-save'})
        before = copy.deepcopy(store.records(self.root)[0])
        store.operation_result(self.root, intent, {'status': 'failed', 'reason_code': 'connection_failed'})
        found = store.records(self.root)
        self.assertEqual(len(found), 2)
        self.assertIn(before, found)
        self.assertNotIn('never-save', json.dumps(found))
        self.assertTrue(any(r['data'].get('intent_id') == intent['record_id'] for r in found))
        metadata['access_mode'] = 'read'
        self.assertIsNone(store.operation_intent(self.root, 'node', metadata, 'a' * 64, []))
        metadata.pop('access_mode')
        self.assertIsNotNone(store.operation_intent(self.root, 'node', metadata, 'a' * 64, []))

    def test_general_retention_typed_fields_template_and_no_raw_leak(self):
        self.enable()
        recipe = self.root / 'test-recipe'
        recipe.mkdir()
        (recipe / 'state.md').write_text('Reachable: {{reachable}}')
        metadata = {'id': 'check-port', 'version': '1', 'retention': {'contract': 'host-values', 'version': '0.2.0', 'description': 'Synthetic reachability; no health inference.',
                    'fields': {'reachable': {'type': 'boolean', 'unit': '', 'description': 'TCP reachability'}}}}
        report = {'host_id': 'node', 'status': 'partial', 'completed_at': '2026-10-17T00:00:00Z',
                  'evidence_kind': 'ssh', 'data': {'reachable': False, 'password': 'never-save'},
                  'recipe': {'reference': 'company:check/port'}}
        store.retain_general(self.root, report, metadata, recipe)
        record = store.records(self.root)[0]
        self.assertFalse(record['data']['observations']['reachable']['value'])
        self.assertNotIn('never-save', json.dumps(record))
        self.assertIn('reachable | False', (self.host() / 'records' / (vault.component('company:check/port') + '.md')).read_text())
        report['data']['reachable'] = 'false'
        with self.assertRaises(ConfigError):
            store.retain_general(self.root, report, metadata, recipe)

    def test_concurrent_writers_and_id_conflict(self):
        self.enable()
        report = raw()
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda _: legacy.retain(self.root, report), range(3)))
        self.assertEqual(sum(r['status'] == 'stored' for r in results), 1)
        record = store.records(self.root)[0]
        record['data']['recipe_version'] = 'different'
        with self.assertRaises(ConfigError):
            store.save(self.root, record)

    def test_origin_and_mapping_validation(self):
        self.enable()
        legacy.retain(self.root, raw())
        record = store.records(self.root)[0]
        record['mappings'] = [{'from': {'namespace': 'example-production', 'host_id': 'node'},
                               'to': {'namespace': 'other', 'host_id': 'node'},
                               'mapped_at': '2026-10-17T00:00:00Z', 'basis': 'explicit user decision'}]
        record['namespace'] = 'other'
        store.validate_record(record)
        record['origin']['instance_id'] = 'invalid'
        with self.assertRaises(ConfigError):
            store.validate_record(record)

    def recipe(self):
        directory = self.root / 'recipes' / 'update'
        directory.mkdir(parents=True)
        metadata = {'descriptor_version': '0.3.0', 'id': 'synthetic-update', 'version': '1.0.0',
                    'access_mode': 'write', 'runner': {'contract': 'python-session', 'version': '0.1.0', 'entrypoint': 'main.py'},
                    'inputs': {'variables': {}}, 'output': {'schema_version': '0.1.0'}}
        (directory / 'recipe.yaml').write_text(json.dumps(metadata))
        (directory / 'main.py').write_text("VERSION = '1.0.0'\ndef execute(session, *, context, timeout):\n    return {'status':'success', 'reason_code':'done', 'message':'Synthetic.', 'data':{}}\n")
        return directory

    def test_runner_intent_failure_prevents_connection(self):
        import run_recipe
        self.enable()
        self.recipe()
        factory = Mock()
        with patch.object(store, 'save', side_effect=OSError('cannot persist')):
            with self.assertRaises(OSError):
                run_recipe.run(self.root, 'node', recipe=':update', session_class=factory)
        factory.assert_not_called()

    def test_runner_success_and_outcome_failure_preserves_raw(self):
        import run_recipe
        self.enable()
        self.recipe()
        factory = Mock(return_value=Mock())
        report, path = run_recipe.run(self.root, 'node', recipe=':update', session_class=factory)
        self.assertEqual(report['status'], 'success')
        self.assertEqual(len(store.records(self.root)), 2)
        with patch.object(store, 'operation_result', side_effect=OSError('cannot persist')):
            report, path = run_recipe.run(self.root, 'node', recipe=':update', session_class=factory)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['execution_status'], 'success')
        self.assertEqual(json.loads(path.read_text())['reason_code'], 'operation_recording_failed')

    def test_package_manifest_structure_only_and_path_rejection(self):
        manifest = {'contract_version': '0.1.0', 'kind': 'opsfeast-host-package', 'record_contract': '0.1.0',
                    'created_at': '2026-10-17T00:00:00Z', 'source': {'namespace': 'example', 'host_id': 'node'},
                    'source_instance_id': '00000000-0000-0000-0000-000000000000', 'mappings': [],
                    'files': [{'path': 'hosts/node/2026/observations.sqlite3', 'size_bytes': 0, 'sha256': 'a' * 64}]}
        store.validate_package_manifest(manifest)
        for name in ('../escape', '/absolute', 'a//b', 'C:/x', 'a\\b'):
            bad = copy.deepcopy(manifest)
            bad['files'][0]['path'] = name
            with self.assertRaises(ConfigError):
                store.validate_package_manifest(bad)

    def test_vault_ingest_validates_entire_batch_before_archive_writes(self):
        self.enable()
        valid = self.root / 'valid.json'
        invalid = self.root / 'invalid.json'
        valid.write_text(json.dumps(raw()))
        bad = raw()
        bad['schema_version'] = 'unsupported'
        invalid.write_text(json.dumps(bad))
        with contextlib.redirect_stderr(io.StringIO()):
            status = legacy.main(['ingest', str(valid), str(invalid), '--root', str(self.root)])
        self.assertEqual(status, 1)
        self.assertEqual(store.records(self.root), [])


if __name__ == '__main__':
    unittest.main()
