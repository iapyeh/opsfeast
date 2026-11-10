"""Synthetic files/procfs and recipe -> portable retention -> shared profile tests."""
import copy
import io
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from opsfeast import ConfigError, Instance, read_yaml
from opsfeast.data_contract import validate
from opsfeast import linux_profile as service, linux_profile_probe as probe
from opsfeast.linux_profile_schema import schema
from opsfeast.profiling import inspect_host
import test_host_vault as fixtures
from test_core_api import Actor, Result

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = {'accounts': 'system/account/inventory/local-users', 'processes': 'system/process/inventory/snapshot'}
SECRET = 'SYNTHETIC_HASH_NEVER_EMIT'


def files(root):
    (root / 'etc').mkdir(exist_ok=True)
    (root / 'etc/passwd').write_text('root:' + SECRET + ':0:0:private full name:/root:/bin/bash\n'
        'daemon:x:1:1::/:/usr/sbin/nologin\n')
    (root / 'etc/group').write_text('root:' + SECRET + ':0:\noperators:x:10:root,daemon\n')
    (root / 'proc/sys/kernel/random').mkdir(parents=True, exist_ok=True)
    (root / 'proc/sys/kernel/random/boot_id').write_text('76904e73-7658-44ac-9000-19a1eb671f83')
    process(root, 17)


def process(root, pid, start=123):
    path = root / 'proc' / str(pid); path.mkdir(exist_ok=True)
    stats = ['0'] * 20
    stats[0], stats[1], stats[11], stats[12], stats[19] = 'S', '1', '10', '20', str(start)
    (path / 'stat').write_text(str(pid) + ' (name with ) spaces) ' + ' '.join(stats))
    (path / 'status').write_text('Name:\tworker\nState:\tS (sleeping)\nPid:\t' + str(pid)
        + '\nUid:\t1000 1001 1001 1001\nGid:\t10 11 11 11\nThreads:\t2\nVmRSS:\t4 kB\nVmSize:\t20 kB\n')
    exe = path / 'exe'
    if not exe.is_symlink(): exe.symlink_to('/usr/bin/worker (deleted)')


class LinuxProfileTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name); files(self.root)

    def snapshot(self, kind, limit=1000):
        return probe.snapshot(kind, limit, 5, root=self.root)

    def acquire(self, kind, data=None, **result_fields):
        result = SimpleNamespace(exitcode=0, stdout=json.dumps(data or self.snapshot(kind)),
                                 stdout_truncated=False, stderr_truncated=False)
        for key, value in result_fields.items(): setattr(result, key, value)
        recipe = SimpleNamespace(vars={}, timeout=10, session=SimpleNamespace(exec_command=Mock(return_value=result)))
        return service.collect(recipe, kind), recipe

    def test_local_accounts_project_without_hash_gecos_or_login_claim(self):
        data = self.snapshot('accounts'); validate(data, schema('accounts', acquisition=False))
        users, groups = data['datasets']['users'], data['datasets']['groups']
        self.assertTrue(users['complete']); self.assertTrue(groups['complete'])
        self.assertEqual(users['items'][0]['uid'], 0)
        self.assertEqual(users['items'][1]['shell_hint'], 'noninteractive_shell')
        self.assertEqual(groups['items'][1]['members'], ['root', 'daemon'])
        self.assertNotIn(SECRET, json.dumps(data)); self.assertNotIn('private full name', json.dumps(data))
        self.assertNotIn('login_allowed', json.dumps(data))

    def test_accounts_malformed_duplicates_shared_uid_and_limits_are_explicit(self):
        with (self.root / 'etc/passwd').open('a') as stream:
            stream.write('other:x:0:0::/:/bin/sh\nroot:x:0:0::/:/bin/sh\nbad-row\n')
        data = self.snapshot('accounts')['datasets']['users']
        self.assertEqual([r['name'] for r in data['items']], ['root', 'daemon', 'other'])
        self.assertFalse(data['complete']); self.assertEqual(data['unavailable_count'], 2)
        limited = self.snapshot('accounts', limit=1)['datasets']['users']
        self.assertEqual(len(limited['items']), 1); self.assertIn('item_or_time_limit', limited['reason_codes'])
        (self.root / 'etc/group').unlink()
        data = self.snapshot('accounts')['datasets']['groups']
        self.assertFalse(data['complete']); self.assertIn('source_missing', data['reason_codes'])

    def test_permission_source_change_oversize_and_time_gaps(self):
        original = probe.bounded
        def denied(path, limit):
            if path.name == 'passwd': raise PermissionError(SECRET)
            return original(path, limit)
        with patch.object(probe, 'bounded', denied):
            data = self.snapshot('accounts')['datasets']['users']
        self.assertFalse(data['complete']); self.assertEqual(data['reason_codes'], ['permission_denied'])
        self.assertNotIn(SECRET, json.dumps(data))
        def changed(path, limit):
            text = original(path, limit)
            if path.name == 'passwd': path.write_text(text + '\n')
            return text
        with patch.object(probe, 'bounded', changed):
            self.assertIn('source_changed_during_read', self.snapshot('accounts')['datasets']['users']['reason_codes'])
        with patch.object(probe, 'MAX_FILE', 5):
            self.assertIn('invalid_or_oversized_source', self.snapshot('accounts')['datasets']['users']['reason_codes'])
        data = probe.accounts(self.root, 'users', 1000, time.monotonic() - 1)
        self.assertFalse(data['complete']); self.assertEqual(data['items'], [])

    def test_process_identity_resources_optional_exe_and_no_sensitive_inputs(self):
        data = self.snapshot('processes'); validate(data, schema('processes', acquisition=False))
        section = data['datasets']['processes']; row = section['items'][0]
        self.assertTrue(section['complete'])
        self.assertEqual((row['pid'], row['start_ticks'], row['ppid']), (17, 123, 1))
        self.assertEqual((row['rss_bytes'], row['virtual_bytes']), (4096, 20480))
        self.assertEqual((row['cpu_user_ticks'], row['cpu_system_ticks']), (10, 20))
        self.assertEqual(row['uid_effective'], 1001); self.assertTrue(row['executable_deleted'])
        self.assertNotIn('cmdline', row); self.assertNotIn('environment', row)
        (self.root / 'proc/17/exe').unlink()
        row = self.snapshot('processes')['datasets']['processes']['items'][0]
        self.assertIsNone(row['executable_deleted']); self.assertEqual(row['executable_state'], 'unavailable')

    def test_process_races_permission_and_boot_identity_are_not_complete(self):
        original = probe.bounded; reads = 0
        def reused(path, maximum):
            nonlocal reads
            text = original(path, maximum)
            if path.name == 'stat':
                reads += 1
                if reads == 2: text = text.rsplit(' ', 1)[0] + ' 999'
            return text
        with patch.object(probe, 'bounded', reused):
            data = self.snapshot('processes')['datasets']['processes']
        self.assertFalse(data['complete']); self.assertEqual(data['items'], [])
        self.assertIn('invalid_or_changed_process', data['reason_codes'])
        def denied(path, maximum):
            if path.name == 'status': raise PermissionError()
            return original(path, maximum)
        with patch.object(probe, 'bounded', denied):
            data = self.snapshot('processes')['datasets']['processes']
        self.assertFalse(data['complete']); self.assertEqual(data['unavailable_count'], 1)
        (self.root / 'proc/sys/kernel/random/boot_id').unlink()
        data = self.snapshot('processes')['datasets']['processes']
        self.assertIsNone(data['boot_id']); self.assertIn('boot_id_unavailable', data['reason_codes'])

    def test_output_limit_does_not_become_empty_success(self):
        for index in range(18, 25): process(self.root, index)
        with patch.object(probe, 'MAX_OUTPUT', 2000): data = self.snapshot('processes')
        section = data['datasets']['processes']
        self.assertLess(len(section['items']), section['attempted_count'])
        self.assertFalse(section['complete']); self.assertIn('output_size_limit', section['reason_codes'])

    def test_service_deadline_contract_privacy_and_failures(self):
        result, recipe = self.acquire('accounts')
        self.assertEqual(result['status'], 'success'); validate(result['data'], schema('accounts'))
        call = recipe.session.exec_command.call_args
        self.assertEqual(call.args[0][:3], ['python3', '-B', '-'])
        self.assertEqual(call.kwargs['command_timeout'], 10)
        self.assertIn('def snapshot', call.kwargs['input'])
        self.assertNotIn(SECRET, json.dumps(result))
        for fields in ({'exitcode':127}, {'stdout_truncated':True}, {'stderr_truncated':True}, {'stdout':'not json'}, {'stdout':json.dumps({'platform':'linux'})}):
            self.assertEqual(self.acquire('accounts', **fields)[0]['status'], 'failed')
        self.assertEqual(self.acquire('accounts', data={'platform':'darwin'})[0]['status'], 'unsupported')
        recipe.session.exec_command.side_effect = RuntimeError(SECRET)
        result = service.collect(recipe, 'accounts')
        self.assertEqual(result['status'], 'failed'); self.assertNotIn(SECRET, json.dumps(result))
        from recipe_contract import validate_result
        validate_result(result)
        self.assertEqual(result['data']['command_evidence']['termination_status'], 'unknown')
        for value in (True, 0, 5001, '10'):
            recipe.vars = {'max_items':value}
            with self.assertRaises(ConfigError): service.collect(recipe, 'accounts')

    def test_descriptor_schema_and_data_only_inspection(self):
        import recipe_inspection
        for kind, reference in REFERENCES.items():
            descriptor = read_yaml(ROOT / 'recipes' / reference / 'recipe.yaml')
            self.assertEqual(descriptor['retention']['data_schema'], schema(kind))
            with patch('runpy.run_path', side_effect=AssertionError('no execution during discovery')):
                self.assertEqual(recipe_inspection.inspect_recipes(reference)['status'], 'success')


class LinuxProfileDeliveryTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp
    enable = fixtures.VaultTests.enable

    def test_runner_retention_and_profile_preserve_actual_values_and_failures(self):
        import recipe_runner
        import retention_store
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        target = Path(directory.name); files(target)
        class ProfileActor(Actor):
            def exec_command(actor, argv, **options):
                if argv[:3] == ['python3', '-B', '-']:
                    assert options['input'] == Path(probe.__file__).read_text()
                    data = probe.snapshot(argv[3], int(argv[4]), 5, root=target)
                    return Result(json.dumps(data), '', 0)
                return super().exec_command(argv, **options)
        self.enable()
        for kind, reference in REFERENCES.items():
            report, path = recipe_runner.run(self.root, 'node', recipe=reference,
                session_class=ProfileActor, runtime={'verification':'synthetic-only'})
            self.assertEqual(report['status'], 'success', report)
            self.assertEqual(report['retention']['status'], 'stored', report)
            self.assertTrue(path.is_file()); self.assertNotIn(SECRET, path.read_text())
        profile = Instance.open().profile(root=self.root)
        data = inspect_host(profile, 'node')
        users = next(p for p in data['items'] if p['property_id'] == 'identity.local_users')
        processes = next(p for p in data['items'] if p['property_id'] == 'processes.snapshot')
        self.assertEqual(users['state'], 'complete'); self.assertEqual(processes['state'], 'complete')
        self.assertIn('daemon', json.dumps(users)); self.assertIn('uid_effective', json.dumps(processes))
        self.assertEqual(len(retention_store.query(self.root)['records']), 2)
        self.assertEqual(retention_store.refresh_content(self.root)['status'], 'success')
        self.assertTrue(list((self.root / 'vault').rglob('*.md')))
        (target / 'etc/group').unlink()
        report, _ = recipe_runner.run(self.root, 'node', recipe=REFERENCES['accounts'],
            session_class=ProfileActor, runtime={'verification':'synthetic-only'})
        self.assertEqual(report['status'], 'partial', report)
        self.assertEqual(report['retention']['status'], 'stored', report)
        groups = next(p for p in inspect_host(profile, 'node')['items'] if p['property_id'] == 'identity.local_groups')
        self.assertEqual(groups['state'], 'unavailable')
        self.assertEqual(groups['evidence'][0]['reason_codes'], ['source_missing'])
