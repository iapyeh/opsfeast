"""Public consumer registration, durable delivery and failure-boundary tests."""
import contextlib
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import retention_consumers as consumers
import retention_store as store
from opsfeast import ConfigError, main, instance_definition
from recipe_catalog import choose
import test_retention_content as fixtures


class ConsumerTests(unittest.TestCase):
    setUp = fixtures.RetentionContentTests.setUp
    enable = fixtures.RetentionContentTests.enable
    sample = fixtures.RetentionContentTests.sample
    retain = fixtures.RetentionContentTests.retain

    def configure(self, enabled=True):
        import yaml
        path = self.root / 'feast.yaml'
        data = yaml.safe_load(path.read_text())
        data['consumers'] = {'counter': {'source': 'local:consumers/counter', 'enabled': enabled}}
        path.write_text(yaml.safe_dump(data))

    def candidate(self, selector=None, events=None, code=None):
        import yaml
        directory = self.root / 'consumers/counter'
        directory.mkdir(parents=True, exist_ok=True)
        descriptor = {'schema_version': '0.1.0', 'id': 'counter', 'description': 'Synthetic local counting example.',
                      'entrypoint': 'main.py', 'subscriptions': [
                          {'event': event, 'selector': selector or {}}
                          for event in events or ['retention.observation.created', 'retention.observation.deleted']]}
        (directory / 'consumer.yaml').write_text(yaml.safe_dump(descriptor))
        (directory / 'main.py').write_text(code or '''import json
def execute(context):
    path = context.root / 'received.json'
    rows = json.loads(path.read_text()) if path.exists() else []
    rows.append(context.event)
    path.write_text(json.dumps(rows))
    assert context.retention.query()['kind'] == 'opsfeast-retention'
    return {'status': 'success'}
''')
        return directory

    def received(self):
        return json.loads((self.root / 'received.json').read_text())

    def test_discovery_is_static_unregistered_never_executes_and_show_relations(self):
        self.enable()
        self.candidate({'recipe_reference': 'system/inventory/overview', 'contract': 'inventory-observations', 'version': '0.1.0'},
                       code="raise RuntimeError('must not import during discovery')")
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        data = consumers.catalog(self.root)
        counter = next(i for i in data['consumers'] if i['id'] == 'counter')
        self.assertFalse(counter['registered'])
        self.assertFalse(counter['enabled'])
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}, before)
        item = choose(self.root, 'system/inventory/overview')
        self.assertEqual({i['id'] for i in item['consumers']}, {'vault', 'counter'})
        self.assertEqual({i['id'] for i in choose(self.root, 'system/account/check/identity')['consumers']}, {'vault'})
        self.retain()
        self.assertFalse((self.root / 'received.json').exists())

    def test_exact_source_contract_version_and_dedup(self):
        self.enable()
        self.candidate({'recipe_reference': 'alpha:check/value', 'contract': 'host-values', 'version': '0.2.0'})
        self.configure()
        instance_definition(self.root)
        metadata, report = self.sample()
        receipt = store.retain_general(self.root, report, metadata, self.root)
        self.assertEqual(receipt['content_update']['status'], 'success')
        self.assertEqual(len(self.received()), 1)
        store.retain_general(self.root, report, metadata, self.root)
        self.retain(reference='beta:check/value')
        self.assertEqual(len(self.received()), 1)
        self.assertEqual(len(consumers.events(self.root)), 2)
        deliveries = consumers.inspect_deliveries(self.root, 'counter')['events'][0]['deliveries']
        self.assertEqual(deliveries[0]['status'], 'success')
        self.assertEqual(deliveries[0]['attempts'], 1)

    def test_disabled_backlog_and_late_registration(self):
        self.enable()
        self.candidate()
        self.configure(False)
        self.retain()
        self.assertFalse((self.root / 'received.json').exists())
        self.configure(True)
        result = consumers.dispatch(self.root, 'counter')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(self.received()), 1)
        self.assertEqual(consumers.dispatch(self.root, 'counter')['consumers'], [])

    def test_failure_isolated_retry_keeps_retention_and_successful_consumer_ack(self):
        self.enable()
        self.candidate(code="def execute(context):\n    raise ValueError('private error detail')\n")
        self.configure()
        _, receipt = self.retain()
        self.assertEqual(receipt['status'], 'stored')
        self.assertEqual(receipt['content_update']['status'], 'failed')
        self.assertEqual(len(store.records(self.root)), 1)
        self.assertNotIn('private error detail', json.dumps(receipt))
        self.assertTrue(any(i['consumer'] == 'vault' and i['status'] == 'success' for i in receipt['content_update']['consumers']))
        self.candidate()
        result = consumers.dispatch(self.root)
        self.assertEqual([i['consumer'] for i in result['consumers']], ['counter'])
        self.assertEqual(result['consumers'][0]['attempts'], 2)
        self.assertEqual(len(self.received()), 1)

    def test_crash_after_side_effect_before_ack_retries_running_delivery(self):
        self.enable()
        self.candidate()
        self.configure()
        metadata, report = self.sample()
        with patch('retention_consumers.dispatch', side_effect=RuntimeError):
            receipt = store.retain_general(self.root, report, metadata, self.root)
        self.assertEqual(receipt['status'], 'stored')
        real = consumers.execute
        def crash(root, item, event):
            result = real(root, item, event)
            if item['id'] == 'counter':
                raise KeyboardInterrupt()
            return result
        with patch('retention_consumers.execute', side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                consumers.dispatch(self.root, 'counter')
        self.assertEqual(consumers.inspect_deliveries(self.root, 'counter')['events'][0]['deliveries'][0]['status'], 'running')
        result = consumers.dispatch(self.root, 'counter')
        self.assertEqual(result['consumers'][0]['attempts'], 2)
        self.assertEqual(len(self.received()), 2)  # at least once, never claim exactly once

    def test_transaction_rollback_does_not_leave_record_or_event(self):
        self.enable()
        metadata, report = self.sample()
        real = consumers.enqueue
        def broken(connection, record, action):
            real(connection, record, action)
            raise sqlite3.OperationalError('synthetic')
        with patch('retention_consumers.enqueue', side_effect=broken):
            with self.assertRaises(sqlite3.OperationalError):
                store.retain_general(self.root, report, metadata, self.root)
        self.assertEqual(store.records(self.root), [])
        self.assertEqual(consumers.events(self.root), [])

    def test_projection_failure_preserves_event_for_manual_dispatch(self):
        self.enable()
        self.candidate()
        self.configure()
        with patch('retention_store.rebuild_unlocked', side_effect=OSError):
            with self.assertRaises(OSError):
                self.retain()
        self.assertEqual(len(store.records(self.root)), 1)
        self.assertEqual(len(consumers.events(self.root)), 1)
        self.assertEqual(consumers.dispatch(self.root)['status'], 'success')
        self.assertEqual(len(self.received()), 1)

    def test_delete_tombstone_and_reinsert_are_distinct_events(self):
        self.enable()
        self.candidate()
        self.configure()
        metadata, report = self.sample()
        receipt = store.retain_general(self.root, report, metadata, self.root)
        store.delete_observation(self.root, receipt['record_id'], dry_run=True)
        self.assertEqual(len(consumers.events(self.root)), 1)
        store.delete_observation(self.root, receipt['record_id'])
        self.assertEqual(store.records(self.root), [])
        self.assertEqual(self.received()[-1]['event'], 'retention.observation.deleted')
        self.assertEqual(self.received()[-1]['contract'], 'host-values')
        store.retain_general(self.root, report, metadata, self.root)
        self.assertEqual(len({e['event_id'] for e in self.received()}), 3)

    def test_deleted_pending_creation_is_a_change_hint_not_record_snapshot(self):
        self.enable()
        self.candidate()
        self.configure(False)
        _, receipt = self.retain()
        store.delete_observation(self.root, receipt['record_id'])
        self.configure()
        consumers.dispatch(self.root, 'counter')
        self.assertEqual(len(self.received()), 2)
        self.assertEqual(store.query(self.root)['records'], [])

    def test_bad_registration_and_unsafe_entrypoint(self):
        self.enable()
        for registration in ({'x': {'source': 'local:../evil', 'enabled': True}}, {'x': {'source': 'builtin:vault', 'enabled': 'true'}}):
            with self.subTest(registration=registration), self.assertRaises(ConfigError):
                consumers.registrations({'consumers': registration})
        directory = self.candidate()
        (directory / 'main.py').unlink()
        (directory / 'main.py').symlink_to(self.root / 'feast.yaml')
        self.configure()
        item = next(i for i in consumers.catalog(self.root)['consumers'] if i['id'] == 'counter')
        self.assertEqual(item['status'], 'failed')
        _, receipt = self.retain()
        self.assertEqual(receipt['status'], 'stored')
        self.assertEqual(receipt['content_update']['status'], 'failed')

    def test_recipe_and_contract_must_match_same_subscription(self):
        self.enable()
        directory = self.candidate({'recipe_reference': 'system/inventory/overview', 'contract': 'host-values', 'version': '0.2.0'})
        import yaml
        path = directory / 'consumer.yaml'
        data = yaml.safe_load(path.read_text())
        data['subscriptions'].append({'event': 'retention.observation.created', 'selector': {
            'recipe_reference': 'other:system/inventory/overview', 'contract': 'inventory-observations', 'version': '0.1.0'}})
        path.write_text(yaml.safe_dump(data))
        self.assertEqual({i['id'] for i in choose(self.root, 'system/inventory/overview')['consumers']}, {'vault'})

    def test_concurrent_dispatch_does_not_duplicate_success(self):
        self.enable()
        self.candidate()
        self.configure(False)
        self.retain()
        self.configure()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: consumers.dispatch(self.root, 'counter'), range(2)))
        self.assertTrue(all(r['status'] == 'success' for r in results))
        self.assertEqual(len(self.received()), 1)

    def test_operation_event_and_recursive_dispatch_guard(self):
        self.enable()
        self.candidate(events=['retention.operation.created'], code='''def execute(context):
    from retention_consumers import dispatch
    dispatch(context.root)
    return {'status': 'success'}
''')
        self.configure()
        record = store.envelope(self.root, 'operation', 'node', 'synthetic', '2026-10-19T00:00:00Z',
                                {'phase': 'intent', 'status': 'unknown', 'recipe_version': '1', 'access_mode': 'write', 'descriptor_sha256': 'a'*64,
                                 'variable_names': []})
        receipt = store.save(self.root, record)
        self.assertEqual(receipt['status'], 'stored')
        self.assertEqual(receipt['content_update']['status'], 'failed')
        self.assertEqual(consumers.events(self.root)[0][1]['event'], 'retention.operation.created')

    def test_cli_list_show_inspect_dispatch_and_missing_consumer(self):
        self.enable()
        self.candidate()
        for args in (['list', '--recipe', 'system/inventory/overview'], ['show', 'vault'], ['inspect'], ['dispatch']):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['consumers', *args, '--root', str(self.root), '--json'])
            self.assertEqual(code, 0, output.getvalue())
            self.assertEqual(json.loads(output.getvalue())['status'], 'success')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['consumers', 'show', 'missing', '--root', str(self.root), '--json']), 1)

    def test_raw_ingest_uses_the_shared_consumer_path(self):
        import retention_replay as replay
        self.enable()
        self.candidate()
        self.configure()
        metadata, report = self.sample()
        report['retention_snapshot'] = replay.snapshot(metadata, self.root)
        path = self.root / 'saved-raw.json'
        path.write_text(json.dumps(report))
        preview = replay.ingest(self.root, [path], dry_run=True)
        self.assertEqual(preview['status'], 'success')
        self.assertEqual(consumers.events(self.root), [])
        result = replay.ingest(self.root, [path])
        self.assertEqual(result['status'], 'success', result)
        self.assertEqual(len(self.received()), 1)
        replay.ingest(self.root, [path])
        self.assertEqual(len(self.received()), 1)

    def test_runner_dispatches_new_consumer_without_a_runner_branch(self):
        import run_recipe
        import test_host_vault as vault_fixtures
        self.enable()
        self.candidate()
        self.configure()
        directory = vault_fixtures.VaultTests.recipe(self)
        path = directory / 'recipe.yaml'
        metadata = json.loads(path.read_text())
        metadata.update(access_mode='read', retention=self.sample()[0]['retention'])
        path.write_text(json.dumps(metadata))
        report, path = run_recipe.run(self.root, 'node', recipe=':update', session_class=Mock(return_value=Mock()),
                                      runtime={'verification': 'synthetic-test'})
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['retention']['status'], 'stored')
        self.assertEqual(report['content_update']['status'], 'success')
        self.assertEqual(self.received()[0]['recipe_reference'], ':update')
        self.assertEqual(json.loads(path.read_text())['content_update'], report['content_update'])

    def test_skipped_is_acknowledged_and_invalid_return_is_retryable(self):
        self.enable()
        self.candidate(code="def execute(context):\n    return {'status': 'skipped', 'reason_code': 'no_output_needed'}\n")
        self.configure()
        self.retain()
        self.assertEqual(consumers.dispatch(self.root, 'counter')['consumers'], [])
        self.candidate(code='def execute(context):\n    return None\n')
        _, receipt = self.retain()
        self.assertEqual(receipt['content_update']['status'], 'failed')
        self.candidate()
        retried = consumers.dispatch(self.root, 'counter')
        self.assertEqual(retried['consumers'][0]['attempts'], 2)
        self.assertEqual(len(self.received()), 1)

    def test_version_mismatch_and_overlapping_subscriptions(self):
        self.enable()
        directory = self.candidate({'contract': 'host-values', 'version': '9.0.0'})
        self.configure()
        self.retain()
        self.assertFalse((self.root / 'received.json').exists())
        self.candidate()
        import yaml
        path = directory / 'consumer.yaml'
        descriptor = yaml.safe_load(path.read_text())
        descriptor['subscriptions'].append(descriptor['subscriptions'][0])
        path.write_text(yaml.safe_dump(descriptor))
        consumers.dispatch(self.root, 'counter')
        self.assertEqual(len(self.received()), 1)

    def test_delete_rollback_keeps_record_and_does_not_emit_tombstone(self):
        self.enable()
        _, receipt = self.retain()
        with patch('retention_consumers.enqueue', side_effect=sqlite3.OperationalError):
            with self.assertRaises(sqlite3.OperationalError):
                store.delete_observation(self.root, receipt['record_id'])
        self.assertEqual(len(store.records(self.root)), 1)
        self.assertEqual(len(consumers.events(self.root)), 1)

    def test_preexisting_eventless_record_and_rebuild_emit_no_backfill(self):
        self.enable()
        metadata, report = self.sample()
        with patch('retention_consumers.enqueue'):
            store.retain_general(self.root, report, metadata, self.root)
        self.assertEqual(consumers.events(self.root), [])
        store.retain_general(self.root, report, metadata, self.root)
        store.rebuild(self.root)
        self.assertEqual(consumers.events(self.root), [])
        self.assertEqual(len(store.records(self.root)), 1)

    def test_invalid_persisted_event_rejected_without_execution(self):
        self.enable()
        self.retain()
        path, event = consumers.events(self.root)[0]
        event['contract_version'] = '99.0.0'
        with store.database(path, True) as connection:
            connection.execute('UPDATE retention_events SET payload=?', (json.dumps(event),))
        with self.assertRaises(ConfigError):
            consumers.inspect_deliveries(self.root)

    def test_malformed_descriptor_and_configuration_are_explicit_errors(self):
        self.enable()
        directory = self.candidate()
        path = directory / 'consumer.yaml'
        import yaml
        data = yaml.safe_load(path.read_text())
        data['subscriptions'][0]['event'] = []
        path.write_text(yaml.safe_dump(data))
        self.assertEqual(consumers.catalog(self.root)['status'], 'failed')
        for bad in ([], {'vault': []}, {'consumers': []}):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                if isinstance(bad, dict):
                    definition = self.root / 'feast.yaml'
                    definition.write_text(yaml.safe_dump(bad))
                    consumers.catalog(self.root)
                else:
                    consumers.registrations(bad)

    def test_relative_helper_import_and_source_drift_check(self):
        self.enable()
        directory = self.candidate(code="from .helper import result\ndef execute(context):\n    return result\n")
        (directory / 'helper.py').write_text("result = {'status': 'success'}\n")
        self.configure()
        self.retain()
        item = next(i for i in consumers.catalog(self.root)['consumers'] if i['id'] == 'counter')
        event = consumers.events(self.root)[0][1]
        self.assertEqual(consumers.execute(self.root, item, event)['status'], 'success')
        (directory / 'main.py').write_text("raise RuntimeError('changed program must not execute')\n")
        with self.assertRaisesRegex(ConfigError, 'source changed'):
            consumers.execute(self.root, item, event)

    def test_bootstrap_never_imports_registered_local_program(self):
        self.candidate(code="raise RuntimeError('do not execute during setup')")
        self.configure()
        self.enable()
        self.assertEqual(consumers.events(self.root), [])
        self.assertTrue((self.root / 'vault/HOSTS.md').exists())


if __name__ == '__main__':
    unittest.main()
