"""Real bundled retained contracts -> shared profiling, without target execution."""
import copy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from opsfeast import Instance
from opsfeast.profiling import inspect_host
from opsfeast.profiling_sources import project
import retention_store as store
from retention_replay import snapshot
import test_host_vault as fixtures
import test_disks_raid as disks
import test_mysql_replication as mysql


class ProfilingSourceTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp
    enable = fixtures.VaultTests.enable

    def storage(self):
        execution = disks.CODE['execute'](disks.recipe())
        raw = {**execution, 'host_id':'node', 'completed_at':execution['data']['observed_at'],
               'evidence_kind':'local', 'source_observation_id':str(uuid4()),
               'recipe':{'id':'disks-raid','version':disks.META['version'],'reference':'system/storage/inventory/disks-raid'},
               'retention_snapshot':snapshot(disks.META, disks.DIRECTORY), 'execution_access_mode':'read'}
        receipt = store.retain_general(self.root, raw, disks.META, disks.DIRECTORY)
        self.assertEqual(receipt['status'], 'stored', receipt)
        return store.show(self.root, receipt['record_id'])

    def replica(self):
        metadata, raw = mysql.RetentionTests().sample()
        raw['retention_snapshot'] = snapshot(metadata, mysql.DIRECTORY)
        receipt = store.retain_general(self.root, raw, metadata, mysql.DIRECTORY)
        self.assertEqual(receipt['status'], 'stored', receipt)
        return store.show(self.root, receipt['record_id'])

    def test_existing_contracts_project_without_recollection_or_reinterpretation(self):
        self.enable(); disk = self.storage(); replica = self.replica()
        with patch('runpy.run_path', side_effect=AssertionError('read must not execute producers')):
            data = inspect_host(Instance.open().profile(root=self.root), 'node')
        self.assertEqual(data['retained_record_count'], 2)
        physical = next(p for p in data['items'] if p['property_id']=='raid.physical_drives')
        self.assertIn('SYNTHETIC-SERIAL', json.dumps(physical))
        self.assertEqual(physical['evidence'][0]['observed_at'], disk['data']['observed_at'])
        summary = next(p for p in data['items'] if p['property_id']=='raid.summary')
        self.assertEqual(summary['state'], 'complete')  # complete report, not healthy storage
        self.assertIn(disk['data']['summary']['health'], summary['evidence'][0]['samples'][0]['value_preview'])
        server = next(p for p in data['items'] if p['property_id']=='mysql.servers')
        self.assertEqual(server['state'], 'complete')
        self.assertEqual(server['evidence'][0]['instance'], 'main')
        self.assertIn('8.0.46', server['evidence'][0]['samples'][0]['value_preview'])
        self.assertEqual(server['evidence'][0]['observed_at'], replica['data']['instances'][0]['observed_at'])

    def test_new_partial_storage_record_replaces_old_values_with_gap(self):
        self.enable(); old = self.storage(); newer = copy.deepcopy(old)
        newer['record_id'] = 'later-storage'; newer['observed_at'] = '2099-01-01T00:00:00.000000+00:00'
        newer['data']['physical_drives'] = []
        newer['data']['coverage']['physical_drives'] = {'status':'unknown', 'reason':'permission_denied'}
        profile = SimpleNamespace(name='fixture', hosts=SimpleNamespace(get=lambda _: {}),
            retention=SimpleNamespace(query=lambda **_: {'records':[old, newer]}))
        row = next(p for p in inspect_host(profile, 'node')['items'] if p['property_id']=='raid.physical_drives')
        self.assertEqual(row['state'], 'unavailable'); self.assertEqual(len(row['evidence']), 1)
        self.assertNotIn('SYNTHETIC-SERIAL', json.dumps(row)); self.assertEqual(row['evidence'][0]['reason_codes'], ['permission_denied'])

    def test_database_query_completeness_is_independent_of_health_and_keeps_instances(self):
        self.enable(); record = self.replica()
        bad = copy.deepcopy(record['data']['instances'][0]); bad.update(instance='other', server=None, channels=[], health='unknown', reason='query_failed', probes=[])
        record['data']['instances'].append(bad)
        record['data']['instances'][0]['health'] = 'unhealthy'
        from opsfeast.profiling import catalog
        data = catalog(); provider = next(p for p in data['providers'] if p['id']=='mysql-replication')
        spec = next(s for c in data['capabilities'] for s in c['properties'] if s['id']=='mysql.replication')
        entries = project(record, provider, spec)
        self.assertEqual([e['instance'] for e in entries], ['main','other'])
        self.assertEqual([e['state'] for e in entries], ['complete','unavailable'])
        self.assertEqual(entries[0]['samples'][0]['value']['health'], 'unhealthy')
        self.assertEqual(entries[1]['reason_codes'], ['query_failed'])
        # A carried contract with the same label/version but incompatible shape
        # stays an explicit gap rather than crashing or importing producer code.
        record['data']['instances'] = 42
        self.assertEqual(project(record, provider, spec)[0]['reason_codes'], ['unsupported_instance_shape'])

    def test_successful_empty_not_applicable_and_partial_rows_have_distinct_states(self):
        self.enable(); record = self.storage()
        from opsfeast.profiling import catalog
        data = catalog(); provider = next(p for p in data['providers'] if p['id']=='disks-raid')
        spec = next(s for c in data['capabilities'] for s in c['properties'] if s['id']=='raid.virtual_drives')
        record['data']['virtual_drives'] = []
        record['data']['coverage']['virtual_drives'] = {'status':'complete','reason':None}
        empty = project(record, provider, spec)[0]
        self.assertEqual(empty['state'], 'complete'); self.assertEqual(empty['sample_count'], 0)
        record['data']['coverage']['virtual_drives'] = {'status':'not_applicable','reason':'not_supported'}
        self.assertEqual(project(record, provider, spec)[0]['state'], 'unavailable')
        record['data']['virtual_drives'] = [{'name':'partial-value'}]
        self.assertEqual(project(record, provider, spec)[0]['state'], 'partial')

    def test_other_contract_versions_and_unselected_host_do_not_leak(self):
        self.enable(); record = self.storage()
        record['retention_definition']['version'] = '99.0.0'
        profile = SimpleNamespace(name='fixture', hosts=SimpleNamespace(get=lambda _: {}),
            retention=SimpleNamespace(query=lambda **_: {'records':[record]}))
        data = inspect_host(profile, 'node')
        self.assertEqual(data['retained_record_count'], 0)
        self.assertTrue(all(not p['evidence'] for p in data['items']))
