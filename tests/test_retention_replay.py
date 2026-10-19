"""Public offline replay/deletion tests; temporary synthetic profiles, no connections."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import host_vault as vault
import retention_store as store
import observation_store as legacy
import retention_replay as replay
import test_host_vault as fixtures
from test_result_data import raw
from opsfeast import ConfigError


class ReplayTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp
    enable = fixtures.VaultTests.enable
    host = fixtures.VaultTests.host
    recipe = fixtures.VaultTests.recipe

    def sample(self, mode='read', legacy=False):
        directory = self.root / ('recipe-' + str(uuid4()))
        directory.mkdir()
        metadata = {'id': 'sample-check', 'version': '1.0', 'access_mode': mode,
                    'retention': {'contract': 'host-values', 'version': '0.2.0', 'description': 'Synthetic count; unavailable when missing.',
                                  'fields': {'count': {'type': 'integer', 'unit': 'items', 'description': 'Observed item count'}}}}
        (directory / 'recipe.yaml').write_text(json.dumps(metadata))
        (directory / 'view.md').write_text('Count: {{count}}')
        (directory / 'main.py').write_text("raise RuntimeError('offline replay must never import me')")
        report = {'host_id': 'node', 'status': 'success', 'evidence_kind': 'ssh',
                  'completed_at': '2026-10-19T00:00:00Z', 'data': {'count': 7, 'secret': 'omit-me'},
                  'recipe': {'id': 'sample-check', 'version': '1.0', 'reference': 'sample/check'}}
        if not legacy:
            report.update(source_observation_id=str(uuid4()), execution_access_mode=mode,
                          retention_snapshot=replay.snapshot(metadata, directory))
        file = self.root / ('raw-' + str(uuid4()) + '.json')
        file.write_text(json.dumps(report))
        return directory, metadata, report, file

    def test_saved_snapshot_replays_after_recipe_removed_and_deduplicates(self):
        self.enable()
        directory, _, report, file = self.sample()
        shutil.rmtree(directory)
        before = file.read_bytes()
        first = replay.ingest(self.root, [file])
        self.assertEqual(first['files'][0]['status'], 'stored')
        self.assertEqual(replay.ingest(self.root, [file])['files'][0]['status'], 'already_stored')
        self.assertEqual(len(store.records(self.root)), 1)
        self.assertEqual(file.read_bytes(), before)
        record = store.records(self.root)[0]
        self.assertEqual(record['retention_provenance']['source_observation_id'], report['source_observation_id'])
        self.assertEqual(record['origin']['instance_id'], '00000000-0000-0000-0000-000000000000')
        self.assertNotIn('markdown', record['data'])
        self.assertNotIn('omit-me', json.dumps(record))

    def test_changed_retention_conflicts_until_explicit_read_delete(self):
        self.enable()
        directory, _, report, file = self.sample()
        replay.ingest(self.root, [file])
        metadata = json.loads((directory / 'recipe.yaml').read_text())
        metadata['retention']['fields']['count']['unit'] = 'revised-items'
        (directory / 'recipe.yaml').write_text(json.dumps(metadata))
        conflict = replay.ingest(self.root, [file], recipe_directory=directory)
        self.assertEqual(conflict['status'], 'failed')
        self.assertIn('conflict', conflict['files'][0]['message'])
        store.delete_observation(self.root, report['source_observation_id'])
        result = replay.ingest(self.root, [file], recipe_directory=directory)
        self.assertEqual(result['files'][0]['status'], 'stored')
        self.assertEqual(store.records(self.root)[0]['data']['observations']['count']['unit'], 'revised-items')

    def test_fixed_inventory_source_id_survives_raw_change_and_year_change_conflicts(self):
        self.enable()
        report = raw()
        report.update(source_observation_id=str(uuid4()), execution_access_mode='read')
        first = legacy.retain(self.root, report)
        changed = copy.deepcopy(report)
        changed['observations']['hostname']['value'] = 'replacement-name'
        with self.assertRaises(ConfigError):
            legacy.retain(self.root, changed)
        shifted = copy.deepcopy(report)
        shifted['finished_at'] = '2027-01-01T00:00:00Z'
        with self.assertRaises(ConfigError):
            legacy.retain(self.root, shifted)
        self.assertFalse((self.host() / '2027').exists())
        store.delete_observation(self.root, report['source_observation_id'])
        second = legacy.retain(self.root, changed)
        self.assertEqual(first['observation_id'], second['observation_id'])
        self.assertNotEqual(replay.raw_digest(report), replay.raw_digest(changed))

    def test_migrated_legacy_raw_replay_adds_provenance_preserving_unknown_producer(self):
        report = raw()
        report['recipe']['reference'] = 'inventory/system'
        report['source_observation_id'] = str(uuid4())
        report['retention'] = legacy.retain(self.root, report)
        legacy_bytes = (self.root / 'records/observations.sqlite3').read_bytes()
        self.enable()
        file = self.root / 'legacy.json'
        file.write_text(json.dumps(report))
        dry = replay.ingest(self.root, [file], dry_run=True)
        self.assertEqual(dry['files'][0]['status'], 'validated')
        result = replay.ingest(self.root, [file])
        self.assertEqual(result['files'][0]['status'], 'stored')
        self.assertEqual((self.root / 'records/observations.sqlite3').read_bytes(), legacy_bytes)
        found = store.records(self.root)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['origin']['instance_id'], '00000000-0000-0000-0000-000000000000')
        self.assertEqual(found[0]['retention_provenance']['execution_access_mode'], 'read')
        self.assertEqual(replay.ingest(self.root, [file])['files'][0]['status'], 'already_stored')

    def test_write_unknown_and_legacy_general_cannot_be_deleted(self):
        self.enable()
        for mode, legacy in (('write', False), ('unknown', False), ('read', True)):
            with self.subTest(mode=mode, legacy=legacy):
                directory, metadata, report, file = self.sample(mode, legacy)
                result = replay.ingest(self.root, [file], recipe_directory=directory if legacy else None)
                self.assertEqual(result['status'], 'success')
                identifier = result['files'][0]['source_observation_id']
                metadata['access_mode'] = 'read'
                (directory / 'recipe.yaml').write_text(json.dumps(metadata))
                with self.assertRaises(ConfigError):
                    store.delete_observation(self.root, identifier)
        self.assertEqual(len(store.records(self.root)), 3)

    def test_operation_events_and_linked_observations_are_protected(self):
        self.enable()
        _, metadata, report, file = self.sample('read')
        intent = store.operation_intent(self.root, 'node', dict(metadata, access_mode='write'), 'a' * 64, [],
                                        source_observation_id=report['source_observation_id'])
        replay.ingest(self.root, [file])
        before = copy.deepcopy(store.records(self.root))
        for identifier in (report['source_observation_id'], intent['record_id']):
            with self.assertRaises(ConfigError):
                store.delete_observation(self.root, identifier)
        self.assertEqual(store.records(self.root), before)

    def test_read_verification_evidence_of_write_operation_is_protected(self):
        self.enable()
        _, metadata, report, file = self.sample('read')
        result = replay.ingest(self.root, [file])
        record_id = result['files'][0]['record_id']
        intent = store.operation_intent(self.root, 'node', dict(metadata, access_mode='write'), 'a' * 64, [])
        store.operation_result(self.root, intent, {'status': 'success'}, observation_ids=[record_id])
        with self.assertRaises(ConfigError):
            store.delete_observation(self.root, report['source_observation_id'])

    def test_delete_latest_falls_back_then_last_removes_stale_views(self):
        self.enable()
        _, _, first, a = self.sample()
        _, _, last, b = self.sample()
        last['completed_at'] = '2026-10-20T00:00:00Z'
        last['data']['count'] = 8
        b.write_text(json.dumps(last))
        replay.ingest(self.root, [a, b])
        page = self.host() / 'records' / (vault.component('sample/check') + '.md')
        self.assertIn('count | 8', page.read_text())
        store.delete_observation(self.root, last['source_observation_id'])
        self.assertIn('count | 7', page.read_text())
        (self.host() / 'notes.md').write_text('Human notes')
        store.delete_observation(self.root, first['source_observation_id'])
        self.assertFalse(page.exists())
        self.assertEqual(list((self.host() / '2026/reports').glob('*.md')), [])
        self.assertEqual((self.host() / 'notes.md').read_text(), 'Human notes')
        self.assertTrue(a.exists() and b.exists())
        for path in (self.root / 'retention/hosts/node/records/observations.sqlite3', self.root / 'retention/overview/observations.sqlite3'):
            with store.database(path) as connection:
                self.assertEqual(connection.execute('SELECT count(*) FROM records').fetchone()[0], 0)

    def test_delete_projection_failure_is_repairable_by_rebuild(self):
        self.enable()
        _, _, report, file = self.sample()
        replay.ingest(self.root, [file])
        page = self.host() / 'records' / (vault.component('sample/check') + '.md')
        original = store.rebuild_unlocked
        count = 0
        def fail_second(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 1:
                raise OSError('synthetic projection failure')
            return original(*args, **kwargs)
        with patch.object(store, 'rebuild_unlocked', side_effect=fail_second):
            with self.assertRaises(OSError):
                store.delete_observation(self.root, report['source_observation_id'])
        self.assertEqual(store.records(self.root), [])
        vault.rebuild(self.root)
        self.assertFalse(page.exists())

    def test_dry_run_does_not_write_raw_archives_or_views(self):
        self.enable()
        _, _, report, file = self.sample()
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = replay.ingest(self.root, [file], dry_run=True)
        self.assertEqual(result['files'][0]['status'], 'validated')
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        replay.ingest(self.root, [file])
        before = copy.deepcopy(store.records(self.root))
        store.delete_observation(self.root, report['source_observation_id'], dry_run=True)
        self.assertEqual(before, store.records(self.root))

    def test_missing_tampered_and_wrong_recipe_snapshots_fail_explicitly(self):
        self.enable()
        directory, metadata, report, file = self.sample(legacy=True)
        self.assertEqual(replay.ingest(self.root, [file])['status'], 'failed')
        self.assertEqual(replay.ingest(self.root, [file], recipe_directory=directory)['status'], 'success')
        report['retention_snapshot'] = replay.snapshot(metadata, directory)
        report['retention_snapshot']['retention']['fields']['count']['unit'] = 'tampered'
        file.write_text(json.dumps(report))
        self.assertEqual(replay.ingest(self.root, [file])['status'], 'failed')
        metadata['id'] = 'different'
        (directory / 'recipe.yaml').write_text(json.dumps(metadata))
        self.assertEqual(replay.ingest(self.root, [file], recipe_directory=directory)['status'], 'failed')

    def test_ingest_all_continues_failures_skips_and_never_runs_recipe(self):
        self.enable()
        directory, _, report, file = self.sample()
        observations = self.root / 'observations'
        observations.mkdir()
        shutil.copy(file, observations / 'good.json')
        (observations / 'bad.json').write_text('{"duplicate":1,"duplicate":2}')
        failed = dict(report, status='failed')
        (observations / 'failed.json').write_text(json.dumps(failed))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = store.main(['ingest', '--all', '--root', str(self.root), '--json'])
        self.assertEqual(code, 1)
        summary = json.loads(out.getvalue())
        self.assertEqual(sorted(r['status'] for r in summary['files']), ['failed', 'skipped', 'stored'])
        self.assertEqual(len(store.records(self.root)), 1)
        self.assertTrue((directory / 'main.py').exists())

    def test_runner_captures_snapshot_before_execution_and_links_audit(self):
        import run_recipe
        from unittest.mock import Mock
        self.enable()
        directory = self.recipe()
        report, file = run_recipe.run(self.root, 'node', recipe=':update', session_class=Mock(return_value=Mock()))
        self.assertEqual(report['execution_access_mode'], 'write')
        self.assertIn('producer_instance_id', report)
        self.assertEqual(replay.source_identity(report), report['source_observation_id'])
        self.assertEqual(replay.validate_snapshot(report['retention_snapshot'])['access_mode'], 'write')
        events = store.records(self.root)
        self.assertTrue(all(store.observation_source(r) == report['source_observation_id'] for r in events))
        self.assertEqual(json.loads(file.read_text())['retention_snapshot'], report['retention_snapshot'])

    def test_custom_inventory_write_declaration_is_not_misclassified_as_read(self):
        import test_inventory_system as inventory
        fixture = inventory.RunnerTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        (fixture.root / 'feast.yaml').write_text('schema_version: 1\nkind: opsfeast\n')
        store.initialize(fixture.root, 'synthetic-inventory')
        descriptor = fixture.directory / 'recipe.yaml'
        import yaml
        metadata = yaml.safe_load(descriptor.read_text())
        metadata['access_mode'] = 'write'
        descriptor.write_text(yaml.safe_dump(metadata))
        report, _ = fixture.run_recipe()
        self.assertEqual(report['execution_access_mode'], 'write')
        events = store.records(fixture.root)
        self.assertEqual(len(events), 2)
        self.assertTrue(all(r['data']['access_mode'] == 'write' for r in events))
        with self.assertRaises(ConfigError):
            store.delete_observation(fixture.root, report['source_observation_id'])


if __name__ == '__main__':
    unittest.main()
