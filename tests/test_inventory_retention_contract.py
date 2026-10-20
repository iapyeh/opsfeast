"""Creator-owned inventory retention; synthetic data only, no session execution."""
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import retention_contracts as contracts
import retention_store as store
import retention_replay as replay
import recipe_dispatch
import recipe_inspection
from opsfeast import ConfigError, read_yaml
import test_host_vault as fixtures
from test_result_data import raw
from inventory_fixture import historical_metadata

BUNDLE = ROOT / 'recipes/system/inventory/overview'


class InventoryRetentionContractTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp
    enable = fixtures.VaultTests.enable

    def metadata(self):
        return read_yaml(BUNDLE/'recipe.yaml')

    def historical_directory(self):
        candidate = self.root/'historical-definition'
        candidate.mkdir(exist_ok=True)
        shutil.copy(BUNDLE/'retention.schema.json', candidate/'retention.schema.json')
        (candidate/'recipe.yaml').write_text(json.dumps(historical_metadata()))
        return candidate

    def test_recipe_declaration_is_discovery_authority(self):
        metadata = self.metadata()
        report = recipe_inspection.inspect_one(BUNDLE, [])
        self.assertEqual(report['status'], 'success', report)
        self.assertEqual(report['retention']['declaration'], metadata['retention'])
        self.assertEqual(report['retention']['schema_path'], str(BUNDLE/'job-retention.schema.json'))
        self.assertIn('retention list', report['retention']['cli'])
        # Discovery never guesses a declaration based on recipe ID.
        self.assertIsNone(store.describe({'id': 'inventory-system'})['declaration'])
        metadata['id'] = 'some-other-producer'
        self.assertEqual(store.describe(metadata)['declaration']['contract'], 'inventory-job-observations')

    def test_descriptor_requires_retention_and_rejects_output_adapter_knobs(self):
        metadata = self.metadata()
        recipe_dispatch.validate(BUNDLE, metadata)
        bad = copy.deepcopy(metadata)
        bad.pop('retention')
        with self.assertRaises(ConfigError):
            recipe_dispatch.validate(BUNDLE, bad)
        for field in ('retention_adapter', 'retained_contract_version', 'exchange_version'):
            bad = copy.deepcopy(metadata)
            bad['output'][field] = 'inventory-system-v1'
            with self.subTest(field=field), self.assertRaises(ConfigError):
                recipe_dispatch.validate(BUNDLE, bad)

    def test_static_discovery_and_snapshot_do_not_load_normalizer(self):
        with patch.object(contracts, 'implementation', side_effect=AssertionError('must not import normalizer')):
            report = recipe_inspection.inspect_one(BUNDLE, [])
            saved = replay.snapshot(self.metadata(), BUNDLE)
        self.assertEqual(report['status'], 'success', report)
        self.assertEqual(saved['normalizer_sha256'], hashlib.sha256((BUNDLE/'job_retention.py').read_bytes()).hexdigest())

    def test_schema_declares_nested_data_meanings_units_and_limits(self):
        schema = json.loads((BUNDLE/'retention.schema.json').read_text())
        fields = schema['properties']['inventory']['properties']
        self.assertEqual(fields['hardware']['properties']['memory_total_bytes']['unit'], 'bytes')
        self.assertEqual(fields['system']['properties']['uptime_seconds']['unit'], 'seconds')
        for section in fields.values():
            for field in section['properties'].values():
                self.assertTrue(field['description'])
                self.assertIn('unit', field)
        self.assertIn('not online status', schema['description'])
        shared = json.loads((ROOT/'schemas/retained-observation.schema.json').read_text())
        self.assertEqual(shared['$ref'], '../recipes/system/inventory/overview/retention.schema.json')

    def test_candidate_schema_missing_changed_or_escape_is_rejected(self):
        candidate = self.root/'candidate'
        candidate.mkdir()
        meta = self.metadata()
        with self.assertRaises(ConfigError):
            contracts.validate_declaration(meta, candidate)
        for invalid in ('{}', '{', '[]', '{"a":1,"a":1}'):
            (candidate/'retention.schema.json').write_text(invalid)
            with self.subTest(invalid=invalid), self.assertRaises(ConfigError):
                contracts.validate_declaration(meta, candidate)
        (candidate/'retention.schema.json').unlink()
        (candidate/'retention.schema.json').symlink_to(BUNDLE/'retention.schema.json')
        with self.assertRaises(ConfigError):
            contracts.validate_declaration(meta, candidate)
        meta['retention']['schema'] = '../escape.json'
        with self.assertRaises(ConfigError):
            contracts.validate_declaration(meta, candidate)

    def test_replay_uses_saved_contract_and_never_candidate_code(self):
        self.enable()
        report = raw()
        file = self.root/'raw.json'
        file.write_text(json.dumps(report))
        candidate = self.root/'candidate'
        candidate.mkdir()
        shutil.copy(BUNDLE/'retention.schema.json', candidate/'retention.schema.json')
        meta = historical_metadata()
        meta.update(version=report['recipe']['version'])
        (candidate/'recipe.yaml').write_text(json.dumps(meta))
        (candidate/'retention.py').write_text("raise AssertionError('candidate code must never load')")
        (candidate/'main.py').write_text("raise AssertionError('collection must never rerun')")
        with patch('runpy.run_path', side_effect=AssertionError('no candidate execution')):
            result = replay.ingest(self.root, [file], recipe_directory=candidate)
        self.assertEqual(result['status'], 'success', result)
        retained = store.query(self.root)['records'][0]
        self.assertEqual(retained['retention_definition'], meta['retention'])
        self.assertEqual(retained['retention_provenance']['snapshot_sha256'], report['retention_snapshot']['sha256'])
        self.assertEqual(replay.ingest(self.root, [file])['files'][0]['status'], 'already_stored')

    def test_missing_snapshot_needs_explicit_definition_no_id_fallback(self):
        self.enable()
        report = raw()
        report.pop('retention_snapshot')
        file = self.root/'old-raw.json'
        file.write_text(json.dumps(report))
        self.assertEqual(replay.ingest(self.root, [file])['status'], 'failed')
        result = replay.ingest(self.root, [file], recipe_directory=self.historical_directory())
        self.assertEqual(result['status'], 'success', result)

    def test_wrong_normalizer_digest_fails_without_data_writes(self):
        self.enable()
        report = raw()
        saved = report['retention_snapshot']
        saved['normalizer_sha256'] = 'a'*64
        saved['sha256'] = replay.digest({k:v for k,v in saved.items() if k!='sha256'})
        file = self.root/'raw.json'
        file.write_text(json.dumps(report))
        before = {p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(replay.ingest(self.root, [file])['status'], 'failed')
        self.assertEqual(before, {p:p.read_bytes() for p in before})
        self.assertEqual(store.records(self.root), [])
        self.assertEqual(replay.ingest(self.root, [file], recipe_directory=self.historical_directory())['status'], 'success')

    def test_schema_digest_is_verified_independently_of_code(self):
        saved = replay.snapshot(self.metadata(), BUNDLE)
        self.assertEqual(saved['schema_sha256'], contracts.schema_digest(saved['retention']))
        saved['schema_sha256'] = 'b'*64
        saved['sha256'] = replay.digest({k:v for k,v in saved.items() if k!='sha256'})
        with self.assertRaisesRegex(ConfigError, 'schema differs'):
            replay.validate_snapshot(saved)

    def test_recipe_normalizer_preserves_existing_values_status_and_privacy(self):
        self.enable()
        report = raw()
        report['status'] = 'partial'
        report['observations']['hostname'].update(value=None, status='unavailable', error={'code':'missing'})
        report['host_metadata'] = {'label': 'Synthetic host', 'description': 'Human context'}
        report['private_input'] = 'must-not-retain'
        receipt = store.retain(self.root, report)
        retained = store.show(self.root, receipt['record_id'])
        data = retained['data']
        self.assertEqual(data['status'], 'partial')
        self.assertIsNone(data['observations']['hostname']['value'])
        self.assertIn('fallback', data['identity_warning'])
        self.assertNotIn('must-not-retain', json.dumps(retained))
        data['observations']['hostname']['value'] = 'inconsistent'
        with self.assertRaises(ConfigError):
            store.validate_record(retained)

    def test_same_id_with_changed_definition_conflicts(self):
        self.enable()
        report = raw()
        store.retain(self.root, report)
        changed = copy.deepcopy(report['retention_snapshot'])
        changed['retention']['description'] = 'Reviewed different interpretation'
        changed['sha256'] = replay.digest({k:v for k,v in changed.items() if k!='sha256'})
        with self.assertRaises(ConfigError):
            store.retain(self.root, report, saved_snapshot=changed)

    def test_unknown_structured_contract_never_loads_any_code(self):
        bad = self.metadata()
        bad['retention']['contract'] = 'unregistered'
        with patch.object(contracts, 'implementation', side_effect=AssertionError('must not load')):
            with self.assertRaises(ConfigError):
                contracts.validate_declaration(bad)
        with self.assertRaises(ConfigError):
            contracts.normalize(('unregistered','0.1.0'), {}, 'source')

    def test_package_boundary_excludes_new_private_storage(self):
        from recipe_packages import payload_name
        for path in ('retention/hosts/node/data.json', 'vault/hosts/node/notes.md'):
            with self.assertRaises(ConfigError):
                payload_name(path)


if __name__ == '__main__':
    unittest.main()
