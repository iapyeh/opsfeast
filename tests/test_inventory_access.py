"""Synthetic access gates and partitioned values; no native sudo or SSH."""
import contextlib
import csv
import io
import json
from pathlib import Path
import runpy
import shlex
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import access_check as access
import host_runtime as hr
import opsfeast as ops
import run_recipe as runner
import observation_store as store
from inventory_values import empty, validate_inventory, csv_text
D = runpy.run_path(str(ROOT / 'recipes/system/inventory/overview/details.py'))


def result(text='', code=0):
    return SimpleNamespace(stdout=text, stderr='', exitcode=code)


class SyntheticSession:
    sudo_passwords = []
    fail_sudo = False
    restoration_failure = False
    close_failure = False
    uid = 1001
    instances = []

    def __init__(self):
        self.elevated = False
        self.calls = []
        self.instances.append(self)

    def close(self, **kwargs):
        if self.close_failure:
            raise RuntimeError('synthetic cleanup failure')

    def exec_command(self, argv, **kwargs):
        self.calls.append((list(argv), self.elevated))
        if argv == ['id', '-un']:
            return result('root\n' if self.elevated or self.uid == 0 else 'operator\n')
        if argv == ['id', '-u']:
            return result(str(0 if self.elevated else self.uid) + '\n')
        if argv == ['id', '-u', 'root']:
            return result('0\n')
        if argv[0] == 'uname':
            return result({'-s': 'Linux', '-n': 'synthetic', '-r': '6.1', '-m': 'x86_64'}[argv[1]] + '\n')
        if argv == ['cat', '/etc/machine-id']:
            return result('1234567890abcdef1234567890abcdef\n')
        if argv[:1] == ['cat']:
            return result(code=1)
        if argv[:2] == ['/bin/sh', '-c'] and '__OPSFEAST_EXIT_' in argv[2]:
            return result('\n__OPSFEAST_EXIT_127\n')
        return result('ID=synthetic\nNAME="Synthetic Linux"\nVERSION_ID=1\n')

    def __call__(self, command, **kwargs):
        return self.exec_command(shlex.split(command), **kwargs)

    @contextlib.contextmanager
    def sudo(self, username, password, **kwargs):
        self.sudo_passwords.append(password)
        if self.fail_sudo:
            raise PermissionError('synthetic rejection')
        self.elevated = True
        try:
            yield self
        finally:
            self.elevated = False
            if self.restoration_failure:
                self.uid = 2000


class AccessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.cls = type('Session', (SyntheticSession,), {'sudo_passwords': [], 'instances': []})
        self.write({'password': 'synthetic-login'})

    def write(self, account):
        (self.root / 'hosts.yaml').write_text(ops.yaml.safe_dump({'hosts': {'h': {'connection': {'local': True}, 'users': {'operator': account}}}}))
        self.config = hr.load_config(self.root, 'h')

    def test_presence_password_selection_and_no_value_disclosure(self):
        for account, expected in [({'password': 'login'}, 'login'),
                                  ({'password': 'login', 'sudo-password': 'override'}, 'override'),
                                  ({'password': 'login', 'sudo-password': ''}, ''),
                                  ({'password': 'login', 'sudo-password': None}, ''),
                                  ({'password': 'login', 'sudo-password': 'false'}, 'login'),
                                  ({}, None)]:
            with self.subTest(account=account):
                self.write(account)
                report = access.check_access(self.config, 'h', session_class=self.cls)
                self.assertEqual(report['status'], 'success')
                self.assertEqual(self.cls.sudo_passwords[-1], expected)
                self.assertNotIn('override', json.dumps(report))
                self.assertFalse((self.root / 'observations').exists())

    def test_boolean_sudo_policy_and_rejected_non_booleans(self):
        self.write({'sudo': False, 'password': 'login'})
        self.assertEqual(access.check_access(self.config, 'h', session_class=self.cls)['access']['mode'], 'user')
        self.assertEqual(self.cls.sudo_passwords, [])
        self.write({'sudo': True, 'password': 'login'})
        self.assertEqual(access.check_access(self.config, 'h', session_class=self.cls)['access']['mode'], 'root')
        self.assertEqual(self.cls.sudo_passwords, ['login'])
        for value in ('false', 'true', 'False', 'No', 0, 1, '0', None, [], {}):
            with self.subTest(value=value), self.assertRaises(ops.ConfigError):
                self.write({'sudo': value})
            with self.subTest(runtime_value=value), self.assertRaises(ops.ConfigError):
                access.sudo_settings(SimpleNamespace(hosts={'h': {'users': {'operator': {'sudo': value}}}}), 'h', 'operator')
        for value in (False, 0, []):
            with self.assertRaises(ops.ConfigError):
                self.write({'sudo-password': value})

    def test_root_does_not_sudo(self):
        self.cls.uid = 0
        report = access.check_access(self.config, 'h', session_class=self.cls)
        self.assertEqual(report['access']['mode'], 'root')
        self.assertEqual(self.cls.sudo_passwords, [])

    def test_rejected_override_never_retries_login(self):
        self.write({'password': 'login', 'sudo-password': 'override'})
        self.cls.fail_sudo = True
        report = access.check_access(self.config, 'h', session_class=self.cls)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['reason_code'], 'sudo_failed')
        self.assertTrue(report['access']['restoration_verified'])
        self.assertEqual(self.cls.sudo_passwords, ['override'])
        self.assertNotIn('override', json.dumps(report))

    def test_force_fallback_and_root_collection(self):
        for rejected, mode in ((False, 'root'), (True, 'fallback_user')):
            self.cls.fail_sudo = rejected
            with contextlib.redirect_stderr(io.StringIO()):
                report, path = runner.run(self.root, 'h', recipe='system/inventory/overview', session_class=self.cls,
                                          runtime={'verification': 'synthetic'}, force=True)
            self.assertEqual(report['status'], 'success')
            self.assertEqual(report['access']['mode'], mode)
            self.assertTrue(report['access']['restoration_verified'])
            commands = self.cls.instances[-1].calls
            detail_calls = [(argv, elevated) for argv, elevated in commands if argv[:2] == ['/bin/sh', '-c'] and '__OPSFEAST_EXIT_' in argv[2]]
            self.assertTrue(detail_calls)
            self.assertTrue(all(elevated == (mode == 'root') for argv, elevated in detail_calls))
            self.assertEqual(json.loads(path.read_text())['inventory']['system']['hostname'], 'synthetic')
            record = store.export(self.root)['records'][-1]
            self.assertEqual(record['collection_scope']['mode'], mode)
            self.assertNotIn('collection_process', record)
            self.assertEqual(store.validate_exchange(store.export(self.root)), 1 if not rejected else 2)

    def test_force_sudo_rejection_is_not_retried(self):
        self.cls.fail_sudo = True
        with contextlib.redirect_stderr(io.StringIO()):
            report, _ = runner.run(self.root, 'h', recipe='system/inventory/overview', session_class=self.cls,
                                   runtime={'verification': 'synthetic'}, force=True)
        self.assertEqual(report['access']['mode'], 'fallback_user')
        self.assertEqual(self.cls.sudo_passwords, ['synthetic-login'])

    def test_csv_export_and_exchange_preserve_values_without_process(self):
        raw = json.loads((ROOT / 'recipes/system/inventory/overview/examples/result.partitioned.synthetic.json').read_text())
        store.retain(self.root, raw)
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            code = store.main(['export', '--root', str(self.root), '--format', 'csv'])
        self.assertEqual(code, 0)
        rows = list(csv.DictReader(io.StringIO(out.getvalue())))
        self.assertTrue(all(row['collection_mode'] == 'user' for row in rows))
        serial = next(row for row in rows if row['section'] == 'hardware' and row['field'] == 'serial')
        self.assertEqual(serial['value'], '')
        bundle = store.export(self.root)
        self.assertEqual(bundle['records'][0]['inventory']['hardware']['logical_cpus'], 4)
        self.assertNotIn('collection_process', bundle['records'][0])
        self.assertEqual(store.validate_exchange(bundle), 1)
        changed = json.loads(json.dumps(bundle))
        changed['records'][0]['inventory']['hardware']['logical_cpus'] = '4'
        with self.assertRaises(ops.ConfigError):
            store.validate_exchange(changed)

    def test_failed_exit_blocks_force_and_retention(self):
        self.cls.restoration_failure = True
        with contextlib.redirect_stderr(io.StringIO()):
            report, path = runner.run(self.root, 'h', recipe='system/inventory/overview', session_class=self.cls,
                                      runtime={'verification': 'synthetic'}, force=True, access_checked=True)
        self.assertEqual(report['status'], 'failed')
        self.assertFalse(report['access']['restoration_verified'])
        self.assertEqual(report['retention']['status'], 'skipped')

    def test_collection_sudo_race_without_force_uses_verified_fallback(self):
        self.cls.fail_sudo = True
        with contextlib.redirect_stderr(io.StringIO()):
            report, path = runner.run(self.root, 'h', recipe='system/inventory/overview', session_class=self.cls,
                                      runtime={'verification': 'synthetic'}, access_checked=True)
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['access']['mode'], 'fallback_user')
        self.assertTrue(report['access']['degraded'])
        self.assertEqual(report['retention']['status'], 'stored')

    def test_identity_failure_summary_is_actionable_without_third_party_details(self):
        import inventory_actor
        unrelated = RuntimeError('private exception text')
        unrelated.reason_code = 'private third-party code'
        for error in (hr.IdentityProbeError('identity_mismatch'), unrelated):
            with self.subTest(error=type(error).__name__), \
                    patch.object(inventory_actor, 'collection_actor', side_effect=error):
                report, path = runner.run(self.root, 'h', recipe='system/inventory/overview', session_class=self.cls,
                    runtime={'verification': 'synthetic'}, access_checked=True)
                self.assertEqual(report['status'], 'failed')
                saved = path.read_text()
                self.assertNotIn('private exception text', saved)
                self.assertNotIn('private third-party code', saved)
                if isinstance(error, hr.IdentityProbeError):
                    self.assertEqual(report['execution_errors'][0]['reason_code'], 'identity_mismatch')
                    self.assertIn('identity_mismatch', report['message'])

    def test_dryrun_and_independent_command_never_collect_or_write(self):
        for invoke, args in ((runner.main, ['system/inventory/overview', '--host', 'h', '--dryrun']),
                             (ops.main, ['check-access', '--host', 'h', '--json', '--quiet'])):
            with patch.object(access, 'runtime_class', return_value=self.cls), patch.object(runner, 'run') as collect, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                code = invoke([*args, '--root', str(self.root)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())['status'], 'success')
            collect.assert_not_called()
            self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['hosts.yaml'])

    def test_access_cli_concise_default_and_json_quiet(self):
        for flags in ([], ['--json'], ['--json', '--quiet']):
            with patch.object(access, 'runtime_class', return_value=self.cls), \
                    contextlib.redirect_stdout(io.StringIO()) as out, \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                code = ops.main(['check-access', '--all', '--root', str(self.root), *flags])
            self.assertEqual(code, 0)
            if '--json' in flags:
                report = json.loads(out.getvalue())
                self.assertEqual(report['hosts'][0]['access']['connection_identity']['username'], 'operator')
                self.assertNotIn('cleanup_error', report['hosts'][0])
            else:
                self.assertEqual([[cell.strip() for cell in line.split('│')[1:-1]] for line in out.getvalue().splitlines() if line.startswith('│')],
                                 [['status', 'host', 'test', 'user', 'reason'], ['PASS', '🍎 h', 'connection', '👤 operator', ''],
                                  ['PASS', '🍎 h', 'sudo', '👤 operator', '']])
                self.assertIn('Hosts: 1 passed, 0 failed, 0 skipped, 0 excluded', out.getvalue())
            if '--quiet' in flags:
                self.assertEqual(err.getvalue(), '')
            else:
                self.assertIn('CHECK  🍎 h / 👤 unresolved', err.getvalue())
                self.assertIn('[1/1] PASS  🍎 h / 👤 operator', err.getvalue())
            self.assertNotIn('synthetic-login', out.getvalue() + err.getvalue())

    def test_access_cli_failure_and_disabled_summary(self):
        self.cls.fail_sudo = True
        with patch.object(access, 'runtime_class', return_value=self.cls), \
                contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            code = ops.main(['check-access', '--all', '--root', str(self.root)])
        self.assertEqual(code, 1)
        self.assertRegex(out.getvalue(), r'❌ FAIL\s+│ 🍎 h\s+│ sudo\s+│ 👤 operator\s+│ sudo_failed')
        data = ops.yaml.safe_load((self.root / 'hosts.yaml').read_text())
        data['hosts']['h']['enabled'] = False
        data['hosts']['h']['connection'] = {'hostname': 'host.example.invalid', 'user': 'operator'}
        (self.root / 'hosts.yaml').write_text(ops.yaml.safe_dump(data))
        with patch.object(access, 'runtime_class') as connect, \
                contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            code = ops.main(['check-access', '--host', 'h', '--root', str(self.root)])
        self.assertEqual(code, 1)
        self.assertRegex(out.getvalue(), r'SKIP\s+│ 🍎 h\s+│ connection\s+│ 👤 operator\s+│ host_disabled')
        connect.assert_not_called()

    def test_progress_precedes_connection_and_parallel_results_stay_ordered(self):
        from threading import Event
        data = {'hosts': {host: {'connection': {'hostname': 'host.example.invalid', 'user': 'operator'}} for host in ('a', 'b')}}
        (self.root / 'hosts.yaml').write_text(ops.yaml.safe_dump(data))
        started = set()
        second_done = Event()
        finished = []

        def progress(stage, report):
            if stage == 'start':
                started.add(report['host'])
                self.assertEqual(access.account_label(report), 'operator')
            else:
                finished.append(report['host'])
                if report['host'] == 'b':
                    second_done.set()

        def check(config, host, *args):
            self.assertIn(host, started)
            if host == 'a':
                self.assertTrue(second_done.wait(5))
            return {'host': host, 'status': 'success'}

        with patch.object(access, 'check_access', side_effect=check):
            report = access.check_many(self.root, ['a', 'b'], threads=2, progress=progress)
        self.assertEqual(finished, ['b', 'a'])
        self.assertEqual([row['host'] for row in report['hosts']], ['a', 'b'])
        self.assertEqual(report['status'], 'success')

    def test_summary_unknown_account_exclusions_and_terminal_controls(self):
        report = {'hosts': [{'host': 'h\n\x1b', 'status': 'failed', 'reason_code': 'connection_failed'}],
                  'excluded_hosts': [{'host': 'other', 'reason_code': 'cli_excluded'}]}
        text = access.format_summary(report)
        self.assertIn(r'h\n\u001b', text)
        self.assertRegex(text, r'❌ FAIL\s+│ .*│ 👤 unresolved\s+│ connection_failed')
        self.assertRegex(text, r'EXCLUDED\s+│ 🍎 other\s+│ -\s+│ -\s+│ cli_excluded')
        self.assertIn('0 passed, 1 failed, 0 skipped, 1 excluded', text)
        self.assertEqual(len([line for line in text.splitlines() if line.startswith('│')]), 3)
        self.assertIn('0 passed, 0 failed', access.format_summary({'hosts': []}))

    def test_table_preserves_numeric_ids_and_unicode_alignment(self):
        from wcwidth import wcswidth
        report = {'hosts': [{'host': '001', 'user': '0002', 'status': 'success'},
                            {'host': '中文主機', 'user': '管理員', 'status': 'failed', 'reason_code': 'sudo_failed'}]}
        table = access.format_summary(report, {'001': '🐧', '中文主機': '★'})
        self.assertIn('001', table)
        self.assertIn('0002', table)
        self.assertIn('❌ FAIL', table)
        self.assertEqual(len({wcswidth(line) for line in table.splitlines()[:-1]}), 1)

    def test_cli_host_icons_include_exclusions_without_changing_ids_or_yaml(self):
        path = self.root / 'hosts.yaml'
        data = ops.yaml.safe_load(path.read_text())
        data['hosts']['h']['icon'] = '🐧'
        data['hosts']['off'] = {'connection': {'local': True}, 'icon': '★', 'enabled': False}
        data['hosts']['legacy'] = {'connection': {'local': True}, 'icon': '☀'}
        path.write_text(ops.yaml.safe_dump(data, allow_unicode=True))
        original = path.read_bytes()
        for flags in ([], ['--json', '--quiet']):
            with patch.object(access, 'runtime_class', return_value=self.cls), \
                    contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                code = ops.main(['check-access', '--all', '--exclude', 'legacy', '--root', str(self.root), *flags])
            self.assertEqual(code, 0)
            if '--json' in flags:
                report = json.loads(out.getvalue())
                self.assertEqual(report['hosts'][0]['host'], 'h')
                self.assertNotIn('icon', report['hosts'][0])
                self.assertEqual({item['host'] for item in report['excluded_hosts']}, {'off', 'legacy'})
                self.assertEqual(err.getvalue(), '')
            else:
                self.assertIn('🐧 h', out.getvalue())
                self.assertIn('★ off', out.getvalue())
                self.assertIn('☀ legacy', out.getvalue())
                self.assertIn('CHECK  🐧 h /', err.getvalue())
                self.assertIn('[1/1] PASS  🐧 h /', err.getvalue())
            self.assertEqual(path.read_bytes(), original)

    def test_missing_table_dependency_stops_before_connections_but_json_works(self):
        with patch.object(access, 'table_formatter', side_effect=ops.ConfigError('missing tabulate')), \
                patch.object(access, 'check_many') as checks, contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ops.main(['check-access', '--all', '--root', str(self.root)]), 1)
            checks.assert_not_called()
            checks.return_value = {'hosts': [], 'status': 'success'}
            self.assertEqual(ops.main(['check-access', '--all', '--root', str(self.root), '--json']), 0)
            checks.assert_called_once()

    def test_table_formatter_requires_wide_character_support(self):
        with patch.dict(sys.modules, {'tabulate': SimpleNamespace(WIDE_CHARS_MODE=False)}):
            with self.assertRaisesRegex(ops.ConfigError, r'tabulate\[widechars\]'):
                access.table_formatter()

    def test_entire_batch_gate_and_force_skip(self):
        check = {'status': 'failed', 'hosts': [{'host': 'h', 'status': 'failed', 'connected': False}]}
        for force in (False, True):
            with patch.object(access, 'check_many', return_value=check), patch.object(runner, 'run') as collect, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                code = runner.main(['system/inventory/overview', '--host', 'h', '--root', str(self.root), *(['--force'] if force else [])])
            self.assertEqual(code, 1)
            collect.assert_not_called()
            report = json.loads(output.getvalue())
            self.assertEqual(report['status'], 'skipped' if force else 'failed')

    def test_dryrun_force_rejected_before_connections(self):
        with patch.object(access, 'check_many') as connect, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            runner.main(['system/inventory/overview', '--all', '--dryrun', '--force'])
        connect.assert_not_called()

    def test_cleanup_failure_blocks_access(self):
        self.cls.close_failure = True
        report = access.check_access(self.config, 'h', session_class=self.cls)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['reason_code'], 'cleanup_failed')


class ValuesTests(unittest.TestCase):
    def collect(self, platform, answers):
        report = {'observations': {field: {'value': 'synthetic'} for field in D['FIELDS']['system'][:7]}}
        session = Mock()
        def query(argv, **kwargs):
            for command, answer in answers.items():
                if command in argv[2]:
                    return result(answer + '\n__OPSFEAST_EXIT_0\n')
            return result('\n__OPSFEAST_EXIT_127\n')
        session.exec_command.side_effect = query
        D['collect'](session, report, platform, 5)
        return report

    def test_linux_parsers_units_zero_empty_and_missing(self):
        report = self.collect('linux', {'cat /proc/uptime': '0.0 0.0', 'getconf': '4',
            'cat /proc/meminfo': 'MemTotal: 100 kB\n', 'cat /proc/cpuinfo': 'model name : Example CPU\n',
            'df -Pk': 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/sda 10 2 8 20% /',
            'ip -j address': '[{"ifname":"eth0","mtu":1500,"addr_info":[{"local":"192.0.2.1","prefixlen":24}]}]',
            'ip -j route': '[]', 'ss -H': ''})
        values = report['inventory']
        self.assertEqual(values['system']['uptime_seconds'], 0)
        self.assertEqual(values['hardware']['cpu_model'], 'Example CPU')
        self.assertEqual(values['hardware']['memory_total_bytes'], 102400)
        self.assertEqual(values['storage']['filesystems'][0]['total_bytes'], 10240)
        self.assertEqual(values['network']['interfaces'][0]['prefix_length'], 24)
        self.assertEqual(values['network']['routes'], [])
        self.assertIsNone(values['software']['packages'])
        self.assertNotIn('error', json.dumps(values))

    def test_bsd_macos_and_esxi_synthetic_parsers(self):
        for platform, replies in [('macos', {'hw.ncpu': '8', 'hw.memsize': '4096', 'pkgutil --pkgs': 'org.example.pkg\n'}),
                                  ('freebsd', {'hw.ncpu': '2', 'hw.physmem': '8192', 'pkg query': 'example 1.0\n'}),
                                  ('esxi', {'hardware cpu global get': 'CPU Threads: 16\n'})]:
            report = self.collect(platform, replies)
            self.assertIsInstance(report['inventory']['hardware']['logical_cpus'], int)
            validate_inventory(report['inventory'])

    def test_malformed_truncated_timeout_and_budget_leave_null(self):
        for response in (result('invalid\n__OPSFEAST_EXIT_0\n'), result('x' * (D['MAX_OUTPUT'] + 1)), TimeoutError('synthetic')):
            session = Mock()
            session.exec_command.side_effect = response if isinstance(response, Exception) else lambda *a, **k: response
            report = {'observations': {field: {'value': None} for field in D['FIELDS']['system'][:7]}}
            D['collect'](session, report, 'linux', 1)
            self.assertIsNone(report['inventory']['hardware']['logical_cpus'])
        with patch.object(D['time'], 'monotonic', side_effect=[0] + [100] * 100):
            session = Mock()
            report = {'observations': {field: {'value': None} for field in D['FIELDS']['system'][:7]}}
            D['collect'](session, report, 'linux', 1, budget=1)
            session.exec_command.assert_not_called()

    def test_csv_null_zero_empty_list_and_formula_escaping(self):
        data = empty()
        data['system']['uptime_seconds'] = 0
        data['system']['hostname'] = '=synthetic()'
        data['services']['services'] = []
        rows = list(csv.DictReader(io.StringIO(csv_text(data))))
        lookup = {(r['section'], r['field']): r['value'] for r in rows}
        self.assertEqual(lookup['hardware', 'serial'], '')
        self.assertEqual(lookup['system', 'uptime_seconds'], '0')
        self.assertEqual(lookup['services', 'services'], '[]')
        self.assertEqual(lookup['system', 'hostname'], "'=synthetic()")
        self.assertNotIn('NULL', csv_text(data))

    def test_invalid_values_rejected(self):
        for section, field, value in [('hardware', 'logical_cpus', '4'), ('system', 'uptime_seconds', float('nan')),
                                      ('software', 'packages', [{'bad': {}}]), ('hardware', 'memory_total_bytes', -1)]:
            data = empty()
            data[section][field] = value
            with self.assertRaises(ops.ConfigError):
                validate_inventory(data)
