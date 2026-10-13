"""Public synthetic stage 1/2/3, identity and ESXi tests; no real hosts or sudo."""
import contextlib
import copy
import io
import json
from pathlib import Path
import plistlib
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import host_identity as hi
import observation_store as store
import run_recipe as runner
from opsfeast import ConfigError


def result(text='', code=0):
    return SimpleNamespace(stdout=text, stderr='', exitcode=code)


def raw(host='node'):
    report = runner.collector['new_report'](host, 'ssh')
    report.update(started_at='2026-10-13T00:00:00+00:00', finished_at='2026-10-13T00:00:10+00:00', status='success')
    for field in store.FIELDS:
        report['observations'][field].update(value='example', status='success', observed_at='2026-10-13T00:00:01+00:00', error=None)
    return report


class StoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'hosts.yaml').write_text('hosts: {}\n')

    def test_retention_replay_and_receipt_do_not_duplicate(self):
        report = raw()
        receipt = store.retain(self.root, report)
        report['retention'] = receipt
        second = store.retain(self.root, report)
        self.assertEqual(second['status'], 'already_stored')
        self.assertEqual(receipt['observation_id'], second['observation_id'])
        bundle = store.export(self.root)
        self.assertEqual(store.validate_exchange(bundle), 1)
        record = bundle['records'][0]
        self.assertEqual(record['identity_quality'], 'fallback')
        self.assertNotIn('sources', record)
        self.assertNotIn('runtime', record)
        self.assertNotIn('execution_errors', record)
        self.assertNotIn('source_ids', record['observations']['hostname'])
        with store.database(self.root) as connection:
            self.assertEqual(connection.execute('SELECT hostname FROM inventory_system').fetchone()[0], 'example')

    def test_same_host_names_in_two_sources_are_separate(self):
        other = self.root / 'other'
        other.mkdir()
        a = store.retain(self.root, raw())
        b = store.retain(other, raw())
        self.assertNotEqual(a['host_key'], b['host_key'])
        self.assertNotEqual(a['observation_id'], b['observation_id'])

    def test_derived_keys_match_across_sources_but_history_is_preserved(self):
        report = raw()
        report['identity'] = {'schema_version': hi.VERSION, 'method': 'linux-machine-id-hmac-sha256-v1',
                              'quality': 'machine-derived', 'os_instance_key': 'linux:' + 'a' * 64, 'evidence': []}
        other = self.root / 'other'
        other.mkdir()
        a = store.retain(self.root, report)
        b = store.retain(other, report)
        self.assertEqual(a['host_key'], b['host_key'])
        # A new OS installation must not inherit the previous installation key.
        report['identity']['os_instance_key'] = 'linux:' + 'b' * 64
        store.retain(self.root, report)
        self.assertEqual(len(store.export(self.root)['records']), 2)

    def test_partial_preserves_missing_values_and_failed_is_ignored(self):
        report = raw()
        report['status'] = 'partial'
        report['observations']['system_version'].update(value=None, status='unavailable', error={'code': 'missing'})
        store.retain(self.root, report)
        retained = store.export(self.root)['records'][0]
        self.assertIsNone(retained['observations']['system_version']['value'])
        report['status'] = 'failed'
        self.assertEqual(store.retain(self.root, report)['status'], 'skipped')
        self.assertEqual(len(store.export(self.root)['records']), 1)

    def test_mock_and_failed_do_not_create_database(self):
        for state, evidence in (('failed', 'ssh'), ('success', 'mock')):
            report = raw()
            report.update(status=state, evidence_kind=evidence)
            self.assertEqual(store.retain(self.root, report)['status'], 'skipped')
        self.assertFalse((self.root / 'records').exists())

    def test_filtered_export_timezone_and_order(self):
        store.retain(self.root, raw('b'))
        store.retain(self.root, raw('a'))
        bundle = store.export(self.root, hosts=['a'], since='2026-10-13T08:00:10+08:00', until='2026-10-13T00:00:10Z')
        self.assertEqual([r['host_id'] for r in bundle['records']], ['a'])
        self.assertEqual(store.export(self.root, hosts=['missing'])['records'], [])
        with self.assertRaises(ConfigError):
            store.export(self.root, since='2026-10-14T00:00:00Z', until='2026-10-13T00:00:00Z')

    def test_exchange_rejects_secrets_extra_fields_versions_and_duplicates(self):
        store.retain(self.root, raw())
        bundle = store.export(self.root)
        mutations = [lambda b: b.update(exchange_version='99'),
                     lambda b: b['records'][0].update(password='private'),
                     lambda b: b['records'].append(copy.deepcopy(b['records'][0])),
                     lambda b: b['records'][0].update(host_key='fallback:wrong'),
                     lambda b: b['records'][0]['observations']['hostname'].update(value=None)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                candidate = copy.deepcopy(bundle)
                mutate(candidate)
                with self.assertRaises(ConfigError):
                    store.validate_exchange(candidate)

    def test_conflicting_id_and_transaction_rollback(self):
        store.retain(self.root, raw())
        record = store.export(self.root)['records'][0]
        with self.assertRaises(ConfigError), store.database(self.root, write=True) as connection:
            record['recipe_version'] = 'different'
            store.insert(connection, record)
        self.assertNotEqual(store.export(self.root)['records'][0]['recipe_version'], 'different')

    def test_malformed_and_unknown_raw_contract(self):
        for mutate in (lambda r: r.update(schema_version='99'),
                       lambda r: r.update(finished_at='2026-10-13'),
                       lambda r: r['observations']['hostname'].update(value=None),
                       lambda r: r.update(execution_errors=[{'stage': 'cleanup'}])):
            report = raw()
            mutate(report)
            with self.assertRaises(ConfigError):
                store.retain(self.root, report)

    def test_symlink_and_database_version_rejected(self):
        (self.root / 'records').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ConfigError):
            store.retain(self.root, raw())
        (self.root / 'records').unlink()
        store.retain(self.root, raw())
        with contextlib.closing(sqlite3.connect(store.store_path(self.root))) as connection:
            connection.execute('PRAGMA user_version=99')
            connection.commit()
        with self.assertRaises(ConfigError):
            store.export(self.root)

    def test_read_only_export_does_not_initialize(self):
        with self.assertRaises(ConfigError):
            store.export(self.root)
        self.assertFalse((self.root / 'records').exists())

    def test_cli_ingest_validate_and_export(self):
        path = self.root / 'raw.json'
        path.write_text(json.dumps(raw()))
        warning = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(warning):
            self.assertEqual(store.main(['ingest', str(path), '--root', str(self.root)]), 0)
        self.assertIn('fallback observations', warning.getvalue())
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(store.main(['export', '--root', str(self.root), '--host', 'node']), 0)
        path.write_text(stream.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(store.main(['validate', str(path)]), 0)
        self.assertEqual(store.validate_exchange(json.loads(path.read_text())), 1)

    def test_cli_invalid_batch_has_no_partial_ingest(self):
        a, b = self.root / 'a.json', self.root / 'b.json'
        a.write_text(json.dumps(raw()))
        report = raw()
        report['schema_version'] = 'invalid'
        b.write_text(json.dumps(report))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(store.main(['ingest', str(a), str(b), '--root', str(self.root)]), 1)
        self.assertFalse((self.root / 'records').exists())

    def test_combine_two_sources_replay_and_conflict(self):
        store.retain(self.root, raw())
        other = self.root / 'other'
        other.mkdir()
        store.retain(other, raw())
        a, b = store.export(self.root), store.export(other)
        merged = store.combine([a, b, a])
        self.assertEqual(store.validate_exchange(merged), 2)
        self.assertEqual(len({r['host_key'] for r in merged['records']}), 2)
        b = copy.deepcopy(a)
        b['records'][0]['recipe_version'] = 'conflicting'
        with self.assertRaises(ConfigError):
            store.combine([a, b])

    def test_batch_ingest_all_excluded_does_not_initialize(self):
        path = self.root / 'failed.json'
        report = raw()
        report['status'] = 'failed'
        path.write_text(json.dumps(report))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(store.main(['ingest', str(path), '--root', str(self.root)]), 0)
        self.assertFalse((self.root / 'records').exists())

    def test_raw_reingest_in_different_source_is_rejected(self):
        report = raw()
        report['retention'] = store.retain(self.root, report)
        other = self.root / 'other'
        other.mkdir()
        with self.assertRaises(ConfigError):
            store.retain(other, report)

    def test_failed_then_retry_does_not_reassign_old_fallback(self):
        report = raw()
        store.retain(self.root, report)
        first = store.export(self.root)['records'][0]['host_key']
        report['identity'] = {'schema_version': hi.VERSION, 'quality': 'machine-derived',
                              'method': 'linux-machine-id-hmac-sha256-v1', 'os_instance_key': 'linux:' + 'a' * 64}
        store.retain(self.root, report)
        self.assertIn(first, {r['host_key'] for r in store.export(self.root)['records']})
        self.assertEqual(len(store.export(self.root)['records']), 2)

    def test_concurrent_retention_one_source_no_duplicate(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts = list(pool.map(lambda _: store.retain(self.root, raw()), range(8)))
        self.assertEqual(sum(r['status'] == 'stored' for r in receipts), 1)
        self.assertEqual(len(store.export(self.root)['records']), 1)


class IdentityTests(unittest.TestCase):
    def config(self, sudo=None):
        return SimpleNamespace(hosts={'node': {'users': {'actor': {'password': 'login-secret'}},
                                              'vars': {'sudo': sudo or {}}}})

    def test_nonroot_linux_machine_id_and_serial(self):
        session = Mock()
        session.exec_command.side_effect = [result('1234567890abcdef1234567890abcdef\n'), result('SERIAL-EXAMPLE\n'), result('12345678-abcd-1234-abcd-123456789abc\n')]
        report = hi.probe_identity(session, self.config(), 'node', {'os_name': 'linux'}, 5)
        self.assertEqual(report['quality'], 'machine-derived')
        self.assertNotIn('1234567890abcdef1234567890abcdef', json.dumps(report))
        session.sudo.assert_not_called()

    def test_missing_evidence_fallback_and_login_password_is_not_sudo_optin(self):
        session = Mock()
        session.exec_command.return_value = result(code=1)
        with patch.object(hi, 'identity', return_value={'username': 'actor', 'effective_uid': 10}):
            report = hi.probe_identity(session, self.config(), 'node', {'os_name': 'linux'}, 5)
        self.assertEqual(report['quality'], 'fallback')
        self.assertTrue(report['warnings'])
        session.sudo.assert_not_called()

    def test_supplied_sudo_credentials_retry_missing_probes_only(self):
        session, elevated = Mock(), Mock()
        session.exec_command.side_effect = [result('1234567890abcdef1234567890abcdef'), result(code=1), result(code=1)]
        session.sudo.return_value.__enter__ = Mock(return_value=elevated)
        session.sudo.return_value.__exit__ = Mock(return_value=False)
        elevated.side_effect = [result('SERIAL-EXAMPLE'), result('UUID-EXAMPLE')]
        login = {'username': 'actor', 'effective_uid': 10}
        with patch.object(hi, 'identity', side_effect=[login, login, {'username': 'root', 'effective_uid': 0}, login, login]):
            report = hi.probe_identity(session, self.config({'password': 'sudo-secret'}), 'node', {'os_name': 'linux'}, 5)
        session.sudo.assert_called_once_with(username='root', password='sudo-secret', enter_timeout=5)
        self.assertEqual(elevated.call_count, 2)
        self.assertTrue(report['sudo']['cleanup_verified'])
        self.assertNotIn('sudo-secret', json.dumps(report))

    def test_sudo_failure_fallback_with_verified_restoration(self):
        session = Mock()
        session.exec_command.return_value = result(code=1)
        session.sudo.side_effect = PermissionError('private-secret')
        login = {'username': 'actor', 'effective_uid': 10}
        with patch.object(hi, 'identity', return_value=login):
            report = hi.probe_identity(session, self.config(), 'node', {'os_name': 'linux'}, 5, allow_sudo=True)
        self.assertEqual(report['quality'], 'fallback')
        self.assertTrue(report['sudo']['cleanup_verified'])
        self.assertNotIn('private-secret', json.dumps(report))

    def test_hardware_serial_never_promotes_freebsd_to_os_identity(self):
        session = Mock()
        session.exec_command.side_effect = [result('SERIAL-EXAMPLE'), result('UUID-EXAMPLE')]
        report = hi.probe_identity(session, self.config(), 'node', {'os_name': 'freebsd'}, 5)
        self.assertEqual(report['quality'], 'fallback')
        self.assertEqual(len(report['evidence']), 2)

    def test_mac_plist_and_esxi_platform_fields(self):
        for platform, text, count in [('macos', plistlib.dumps([{'IOPlatformSerialNumber': 'SERIAL-EXAMPLE', 'IOPlatformUUID': 'UUID-EXAMPLE'}]).decode(), 2),
                                      ('esxi', 'Serial Number: SERIAL-EXAMPLE\nUUID: UUID-EXAMPLE\nEnclosure Serial Number: ENCLOSURE-EXAMPLE', 3)]:
            with self.subTest(platform=platform):
                session = Mock()
                session.exec_command.return_value = result(text)
                report = hi.probe_identity(session, self.config(), 'node', {'os_name': platform}, 5)
                self.assertEqual(report['quality'], 'fallback')
                self.assertEqual(sum(i['status'] == 'success' for i in report['evidence']), count)

    def test_placeholder_and_invalid_machine_ids(self):
        for value in ('Default String', 'To Be Filled By O.E.M.', '00000000', 'FFFFFFFF', ''):
            with self.assertRaises(ValueError):
                hi.usable(value)
        with self.assertRaises(ValueError):
            hi.machine_id('not-a-machine-id')

    def test_explicit_disable_overrides_supplied_sudo(self):
        session = Mock()
        session.exec_command.return_value = result(code=1)
        report = hi.probe_identity(session, self.config({'password': 'sudo-secret'}), 'node', {'os_name': 'linux'}, 5, allow_sudo=False)
        session.sudo.assert_not_called()
        self.assertEqual(report['quality'], 'fallback')

    def test_passwordless_optin_and_unknown_restoration(self):
        session, elevated = Mock(), Mock()
        session.exec_command.return_value = result(code=1)
        session.sudo.return_value.__enter__ = Mock(return_value=elevated)
        session.sudo.return_value.__exit__ = Mock(return_value=False)
        elevated.return_value = result(code=1)
        config = self.config()
        config.hosts['node']['users']['actor'].pop('password')
        login = {'username': 'actor', 'effective_uid': 10}
        with patch.object(hi, 'identity', side_effect=[login, {'username': 'root', 'effective_uid': 0}, RuntimeError(), RuntimeError()]):
            report = hi.probe_identity(session, config, 'node', {'os_name': 'linux'}, 5, allow_sudo=True)
        session.sudo.assert_called_once_with(username='root', password=None, enter_timeout=5)
        self.assertFalse(report['sudo']['cleanup_verified'])

    def test_placeholder_serial_does_not_trigger_elevation(self):
        session = Mock()
        session.exec_command.return_value = result('Default String')
        report = hi.probe_identity(session, self.config({'password': 'sudo-secret'}), 'node', {'os_name': 'freebsd'}, 5)
        session.sudo.assert_not_called()
        self.assertEqual(report['quality'], 'fallback')

    def test_user_assignment_takes_precedence_over_native_candidate(self):
        session = Mock()
        session.exec_command.side_effect = [result('1234567890abcdef1234567890abcdef'), result('SERIAL-EXAMPLE'), result('UUID-EXAMPLE')]
        config = self.config()
        config.hosts['node']['identity_key'] = 'example.org:mail:os-2026-10'
        report = hi.probe_identity(session, config, 'node', {'os_name': 'linux'}, 5)
        self.assertEqual(report['quality'], 'user-assigned')
        self.assertEqual(report['identity_key'], 'example.org:mail:os-2026-10')
        self.assertEqual(len(report['evidence']), 3)


class HostMetadataTests(unittest.TestCase):
    def root(self, hosts):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        from opsfeast import yaml
        (root / 'hosts.yaml').write_text(yaml.safe_dump({'hosts': hosts}, allow_unicode=True))
        return root

    def test_configuration_preserves_free_text_and_rejects_invalid_fields(self):
        from opsfeast import Validator
        host = {'connection': {'local': True}, 'identity_key': 'example.org:mail:os-1', 'label': '郵件服務', 'description': 'First line\nSecond line'}
        config = Validator(self.root({'node': host})).check()
        self.assertEqual(config.hosts['node'], host)
        for name, value in [('identity_key', ''), ('identity_key', ' trailing '), ('identity_key', 'line\nbreak'), ('identity_key', 123), ('label', None), ('label', 4), ('description', ['bad'])]:
            candidate = copy.deepcopy(host)
            candidate[name] = value
            with self.subTest(name=name, value=value), self.assertRaises(ConfigError):
                Validator(self.root({'node': candidate})).check()
        with self.assertRaises(ConfigError):
            Validator(self.root({'a': host, 'b': host})).check()

    def test_shared_key_different_local_names_labels_and_reinstall_key(self):
        import hashlib
        roots = []
        records = []
        for host, label in [('a-local', 'Mail A'), ('b-local', 'Mail B')]:
            root = self.root({host: {'connection': {'local': True}}})
            report = raw(host)
            assigned = 'example.org:mail:os-1'
            report['identity'] = {'schema_version': hi.VERSION, 'method': 'configured-identity-key-v1', 'quality': 'user-assigned', 'identity_key': assigned, 'os_instance_key': 'user:' + hashlib.sha256(assigned.encode()).hexdigest()}
            report['host_metadata'] = {'label': label, 'description': 'Operations\nOwner notes'}
            store.retain(root, report)
            roots.append(root)
            records.append(store.export(root)['records'][0])
        self.assertEqual(records[0]['host_key'], records[1]['host_key'])
        self.assertNotEqual(records[0]['source_id'], records[1]['source_id'])
        merged = store.combine([store.export(root) for root in roots])
        self.assertEqual(len(merged['records']), 2)
        self.assertEqual({r['label'] for r in merged['records']}, {'Mail A', 'Mail B'})
        with store.database(roots[0]) as connection:
            self.assertEqual(connection.execute('SELECT label, description FROM inventory_system').fetchone(), ('Mail A', 'Operations\nOwner notes'))
        altered = copy.deepcopy(records[0])
        altered['identity_key'] = 'example.org:mail:os-2'
        with self.assertRaises(ConfigError):
            store.validate_record(altered)
        altered['host_key'] = 'user:' + hashlib.sha256(altered['identity_key'].encode()).hexdigest()
        store.validate_record(altered)
        self.assertNotEqual(altered['host_key'], records[0]['host_key'])

    def test_database_v1_upgrade_preserves_source_and_records(self):
        root = self.root({})
        store.retain(root, raw())
        before = store.export(root)
        with store.database(root, write=True) as connection:
            source = store.source_id(connection)
            connection.execute('PRAGMA user_version=1')
            connection.execute('DROP VIEW inventory_system')
            connection.execute('CREATE VIEW inventory_system AS SELECT host_id FROM observations')
        self.assertEqual(store.retain(root, raw())['status'], 'already_stored')
        self.assertEqual(store.export(root)['records'], before['records'])
        with store.database(root) as connection:
            self.assertEqual(store.source_id(connection), source)
            self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], 2)
            self.assertEqual(connection.execute('SELECT label FROM inventory_system').fetchone()[0], 'node')


class PipelineTests(unittest.TestCase):
    def run_inventory(self, kernel='Linux', fail_retention=False, metadata=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        from opsfeast import yaml
        (root / 'hosts.yaml').write_text(yaml.safe_dump({'hosts': {'node': {'connection': {'local': True}, **(metadata or {})}}}, allow_unicode=True))
        session = Mock()
        def execute(argv, **kwargs):
            if argv[:1] == ['uname']:
                return result({'-s': kernel, '-n': 'node', '-r': '8.0', '-m': 'x86_64'}[argv[1]] + '\n')
            if argv == ['vmware', '-v']:
                return result('VMware ESXi 8.0.0 build-example\n')
            if argv == ['esxcli', 'hardware', 'platform', 'get']:
                return result('UUID: UUID-EXAMPLE\nSerial Number: SERIAL-EXAMPLE\nEnclosure Serial Number: ENCLOSURE-EXAMPLE\n')
            if argv == ['cat', '/etc/machine-id']:
                return result('1234567890abcdef1234567890abcdef\n')
            if argv[:1] == ['cat']:
                return result(code=1)
            if argv == ['id', '-un']:
                return result('actor\n')
            if argv == ['id', '-u']:
                return result('10\n')
            return result('ID=example\nNAME="Example Linux"\nVERSION_ID=1.2\n')
        session.exec_command.side_effect = execute
        manager = patch.object(runner, 'retain', side_effect=sqlite3.OperationalError()) if fail_retention else contextlib.nullcontext()
        with manager, contextlib.redirect_stderr(io.StringIO()):
            report, path = runner.run(root, 'node', recipe='inventory/system', session_class=Mock(return_value=session), runtime={'verification': 'synthetic'})
        return root, report, path

    def test_automatic_retention_raw_receipt_and_replay(self):
        root, report, path = self.run_inventory()
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['retention']['status'], 'stored')
        self.assertEqual(json.loads(path.read_text()), report)
        self.assertEqual(store.retain(root, json.loads(path.read_text()))['status'], 'already_stored')
        self.assertEqual(store.validate_exchange(store.export(root)), 1)

    def test_configured_identity_and_labels_reach_exchange(self):
        root, report, path = self.run_inventory(metadata={'identity_key': 'example.org:mail:os-1', 'label': '郵件服務', 'description': 'Line one\nLine two'})
        self.assertEqual(report['identity']['quality'], 'user-assigned')
        self.assertEqual(json.loads(path.read_text())['host_metadata']['label'], '郵件服務')
        record = store.export(root)['records'][0]
        self.assertEqual(record['identity_key'], 'example.org:mail:os-1')
        self.assertEqual(record['label'], '郵件服務')
        self.assertEqual(record['description'], 'Line one\nLine two')

    def test_retention_failure_preserves_recoverable_raw(self):
        root, report, path = self.run_inventory(fail_retention=True)
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['retention']['status'], 'failed')
        self.assertEqual(json.loads(path.read_text()), report)
        self.assertEqual(store.retain(root, report)['status'], 'stored')

    def test_esxi_dispatch_identity_and_retention(self):
        root, report, path = self.run_inventory(kernel='VMkernel')
        self.assertEqual(report['recipe']['implementation_id'], 'esxi')
        self.assertEqual(report['host_init']['facts']['os_name'], 'esxi')
        self.assertEqual(report['observations']['system_name']['value'], 'VMware ESXi')
        self.assertEqual(report['identity']['quality'], 'fallback')
        self.assertEqual(report['retention']['status'], 'stored')

    def test_cli_retention_failure_is_nonzero(self):
        report = raw()
        report.update(reason_code='inventory_complete', message='success', detected_kernel='Linux', supported_platforms=['linux'], retention={'status': 'failed'})
        with patch.object(runner, 'resolve_root', return_value=ROOT), patch.object(runner, 'select_hosts', return_value=['node']), patch.object(runner, 'run', return_value=(report, ROOT / 'synthetic.json')), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(runner.main(['inventory/system', '--host', 'node', '--quiet']), 1)
            self.assertEqual(runner.main(['inventory/system', '--all', '--quiet']), 1)

    def test_atomic_raw_write_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'raw.json'
            path.write_text('{"previous": true}\n')
            with patch.object(runner.os, 'replace', side_effect=OSError()), self.assertRaises(OSError):
                runner.save_report(path, raw())
            self.assertEqual(json.loads(path.read_text()), {'previous': True})
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_receipt_write_failure_still_reports_raw_path(self):
        save = runner.save_report
        calls = []
        def saving(path, report):
            calls.append(path)
            if len(calls) == 2:
                raise OSError()
            return save(path, report)
        with patch.object(runner, 'save_report', side_effect=saving):
            root, report, path = self.run_inventory()
        self.assertEqual(report['retention']['reason_code'], 'receipt_save_failed')
        self.assertTrue(path.is_file())
        self.assertEqual(store.retain(root, json.loads(path.read_text()))['status'], 'already_stored')

    def test_checked_in_exchange_fixture_and_declared_contract(self):
        example = json.loads((ROOT / 'recipes/inventory/system/examples/exchange.synthetic.json').read_text())
        self.assertEqual(store.validate_exchange(example), 1)
        from recipe_dispatch import validate
        from opsfeast import read_yaml
        directory = ROOT / 'recipes/inventory/system'
        descriptor = read_yaml(directory / 'recipe.yaml')
        for field in ('retention_adapter', 'retained_contract_version', 'exchange_version'):
            metadata = copy.deepcopy(descriptor)
            metadata['output'][field] = 'unknown'
            with self.assertRaises(ConfigError):
                validate(directory, metadata)


if __name__ == '__main__':
    unittest.main()
