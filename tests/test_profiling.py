"""Profiling discovery and synthetic collection -> retention -> shared read model."""
from contextlib import redirect_stdout, redirect_stderr
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from opsfeast import ConfigError
from opsfeast.core import Instance
from opsfeast import profiling
import profiling_cli
import test_inventory_jobs as fixtures
import inventory_jobs


class ProfilingTests(unittest.TestCase):
    setUp = fixtures.InventoryJobTests.setUp
    enable = fixtures.InventoryJobTests.enable
    acquire = fixtures.InventoryJobTests.acquire

    def view(self, **options):
        return profiling.inspect_host(Instance.open().profile(root=self.root), 'node', **options)

    def test_discovery_is_data_only_and_all_properties_are_routed_once(self):
        with patch('runpy.run_path', side_effect=AssertionError('discovery must not execute code')), \
                patch.object(inventory_jobs, 'connected', side_effect=AssertionError('no connection')):
            data = profiling.catalog()
            self.assertEqual(len(data['domains']), 8)
            names = [s['id'] for c in data['capabilities'] for s in c['properties'] if s['provider_id']=='system-inventory']
            native = json.loads((inventory_jobs.BUNDLE / 'collection.json').read_text())
            self.assertEqual(set(names), set(native['properties']))
            self.assertEqual(len(names), len(set(names)))
            self.assertEqual(inventory_jobs.catalog(), native)
            self.assertEqual(next(c for c in profiling.catalog(domain='identity')['capabilities'] if c['id']=='identity.accounts')['integration'], 'partial')
        for call in (lambda: profiling.catalog(domain='bad'), lambda: profiling.provider_catalog('bad')):
            with self.assertRaises(ConfigError): call()

    def test_registry_rejects_invalid_bindings_duplicates_and_paths(self):
        original = json.loads(profiling.REGISTRY.read_text())
        for mutate in (
            lambda d: d['capabilities'][0]['properties']['system-inventory'].append('nonexistent'),
            lambda d: d['capabilities'].append(copy.deepcopy(d['capabilities'][0])),
            lambda d: d['providers'][0].update(catalog_path='../outside.json'),
            lambda d: d['providers'][0].update(adapter='unreviewed-code'),
            lambda d: d['capabilities'][0].update(properties={}),
        ):
            data = copy.deepcopy(original); mutate(data)
            candidate = self.root / 'catalog.json'; candidate.write_text(json.dumps(data))
            with patch.object(profiling, 'REGISTRY', candidate), self.assertRaises(ConfigError): profiling.catalog()
        candidate.unlink(); candidate.symlink_to(profiling.REGISTRY)
        with patch.object(profiling, 'REGISTRY', candidate), self.assertRaises(ConfigError): profiling.catalog()

    def test_empty_host_unknown_host_and_read_without_mutations(self):
        self.enable()
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        data = self.view()
        self.assertEqual(data['retained_record_count'], 0)
        self.assertTrue(all(p['state'] == 'not_collected' for p in data['items']))
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        with self.assertRaises(ConfigError): profiling.inspect_host(Instance.open().profile(root=self.root), 'absent')
        for options in ({'limit':0}, {'limit':251}, {'offset':-1}, {'limit':True}):
            with self.assertRaises(ConfigError): self.view(**options)

    def test_newer_failure_is_not_replaced_with_old_success(self):
        self.enable()
        actor = fixtures.Actor()
        old = self.acquire(actor, properties=['storage.filesystems.used_percent'], save=True)
        self.assertEqual(old['retention']['status'], 'stored')
        complete = next(p for p in self.view()['items'] if p['property_id'] == 'storage.filesystems.used_percent')
        self.assertEqual(complete['evidence'][0]['samples'][0]['value_preview'], '82.0')
        actor.fail.add('df -Pk')
        failed = self.acquire(actor, properties=['storage.filesystems.used_percent'], save=True)
        self.assertEqual(failed['retention']['status'], 'stored', failed)
        row = next(p for p in self.view()['items'] if p['property_id'] == 'storage.filesystems.used_percent')
        self.assertEqual(row['state'], 'unavailable')
        self.assertEqual(len(row['evidence']), 1)
        evidence = row['evidence'][0]
        self.assertNotEqual(evidence['samples'][0]['value_preview'], '82.0')
        self.assertTrue(evidence['reason_codes'])
        self.assertEqual(evidence['observed_at'], failed['groups'][0]['coverage'][0]['observed_at'])

    def test_saved_values_pagination_domain_scope_and_read_safety(self):
        self.enable()
        actor = fixtures.Actor(); actor.percent = 0
        result = self.acquire(actor, properties=['storage.filesystems.used_percent'], save=True)
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(inventory_jobs, 'connected', side_effect=AssertionError('read cannot connect')):
            data = self.view(domain='storage', limit=1)
            self.assertEqual(data['next_offset'], 1)
            self.assertEqual(len(data['items']), 1)
            all_data = self.view(domain='storage', limit=250)
        self.assertTrue(all(p['domain'] == 'storage' for p in all_data['items']))
        row = next(p for p in all_data['items'] if p['property_id'] == 'storage.filesystems.used_percent')
        self.assertEqual(row['state'], 'complete')
        self.assertEqual(row['evidence'][0]['samples'][0]['value_preview'], '0.0')
        self.assertEqual(row['evidence'][0]['observed_at'], result['groups'][0]['coverage'][0]['observed_at'])
        self.assertNotIn('command', row['evidence'][0])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_empty_enumeration_partial_tables_preview_and_boundary_identity(self):
        self.enable()
        self.acquire(fixtures.Actor(), properties=['storage.filesystems.used_percent'], save=True)
        import retention_store
        record = retention_store.query(self.root)['records'][0]
        other = copy.deepcopy(record)
        other.update(record_id='another-source', namespace='other', recipe_reference='external:inventory')
        group = other['data']['groups'][0]
        group['samples'] = []
        # Coverage remains complete: this is a successful empty table enumeration.
        records = [record, other]
        profile = SimpleNamespace(name='synthetic', hosts=SimpleNamespace(get=lambda _: {}),
                                  retention=SimpleNamespace(query=lambda **_: {'records': records}))
        data = profiling.inspect_host(profile, 'node')
        row = next(p for p in data['items'] if p['property_id'] == 'storage.filesystems.used_percent')
        self.assertEqual(len(row['evidence']), 2)
        self.assertEqual(row['state'], 'complete')
        self.assertTrue(any(e['sample_count'] == 0 and e['state'] == 'complete' for e in row['evidence']))
        # Large values and instance tables are explicitly bounded, not silently dropped.
        group['samples'] = [dict(record['data']['groups'][0]['samples'][0], keys={'mountpoint':str(i)}, value='x' * 3000) for i in range(25)]
        group['coverage'][0]['complete'] = False
        group['samples'][-1].update(status='unavailable', value=None, reason_code='permission_denied')
        row = next(p for p in profiling.inspect_host(profile, 'node')['items'] if p['property_id'] == 'storage.filesystems.used_percent')
        evidence = next(e for e in row['evidence'] if e['namespace'] == 'other')
        self.assertEqual(evidence['state'], 'partial')
        self.assertTrue(evidence['samples_truncated'])
        self.assertEqual(len(evidence['samples']), 20)
        self.assertTrue(evidence['samples'][0]['value_truncated'])
        self.assertEqual(len(evidence['samples'][0]['value_preview']), 2000)
        self.assertIn('permission_denied', evidence['reason_codes'])

    def test_cli_routes_help_and_errors_without_profile_discovery_side_effects(self):
        import opsfeast
        output = io.StringIO()
        with redirect_stdout(output), patch('opsfeast.resolve_root', side_effect=AssertionError('no profile')):
            self.assertEqual(opsfeast.main(['profiling', 'describe', '--domain', 'identity', '--json']), 0)
        self.assertEqual(json.loads(output.getvalue())['domains'][0]['id'], 'identity')
        for args in (['--help'], ['describe','--help'], ['show','--help']):
            with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as exited:
                profiling_cli.main(args)
            self.assertEqual(exited.exception.code, 0)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(profiling_cli.main(['describe','--domain','absent','--json']), 1)
        self.enable()
        with redirect_stdout(io.StringIO()) as out:
            code = profiling_cli.main(['show','--root',str(self.root),'--host','node','--json'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())['host_id'], 'node')
