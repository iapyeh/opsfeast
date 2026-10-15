"""Synthetic host/group selection tests; no sessions or network operations."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import opsfeast as ops
import run_recipe as runner


class HostSelectionTests(unittest.TestCase):
    def setUp(self):
        from access_check import VERSION
        checker = patch('access_check.check_many', side_effect=lambda root, hosts, *args: {'contract_version': VERSION, 'status': 'success', 'hosts': [{'host': h, 'status': 'success', 'connected': True} for h in hosts]})
        checker.start()
        self.addCleanup(checker.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'included.yaml').write_text('''hosts:
  web-01:
    connection: {hostname: web-01.example}
    group: [web, production, web]
  db-01:
    connection: {hostname: db-01.example}
    group: production
''')
        (self.root / 'hosts.yaml').write_text('''include: [included.yaml]
hosts:
  localhost:
    connection: {local: true}
  web-02:
    connection: {hostname: web-02.example}
    group: [web, staging]
  bastion:
    connection: {hostname: bastion.example}
    group: []
''')
        self.report = dict(status='success', reason_code='inventory_complete',
                           message='Synthetic success', detected_kernel='Linux',
                           supported_platforms=['linux'], recipe={'id': 'inventory-system'})

    def cli(self, argv, **run_options):
        stdout, stderr = io.StringIO(), io.StringIO()
        options = {'return_value': (self.report, self.root / 'result.json'), **run_options}
        with patch.object(runner, 'run', **options) as execute, \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = runner.main([*argv, '--threads', '1'] if '--threads' not in argv else argv)
        return status, stdout.getvalue(), stderr.getvalue(), execute

    def test_multi_membership_and_include_union_order(self):
        self.assertEqual(runner.select_hosts(self.root, [('group', 'web')]), ['web-01', 'web-02'])
        self.assertEqual(runner.select_hosts(self.root, [('host', 'db-01'), ('group', 'web'),
                                                     ('group', 'production'), ('group', 'staging')]),
                         ['db-01', 'web-01', 'web-02'])
        self.assertEqual(ops.Validator(self.root).check().hosts['web-01']['group'],
                         ['web', 'production', 'web'])

    def test_all_includes_ungrouped_local_and_jump_hosts(self):
        self.assertEqual(runner.select_hosts(self.root, [], True),
                         ['web-01', 'db-01', 'localhost', 'web-02', 'bastion'])

    def test_scalar_and_list_membership_are_equivalent_and_dump_is_preserved(self):
        for value, stored in (('web', 'web'), ('[web]', ['web']), ('[web, web]', ['web', 'web'])):
            with self.subTest(value=value):
                (self.root / 'hosts.yaml').write_text(
                    'hosts: {h: {connection: {local: true}, group: ' + value + '}}')
                self.assertEqual(runner.select_hosts(self.root, [('group', 'web')]), ['h'])
                config = ops.Validator(self.root).check()
                self.assertEqual(config.hosts['h']['group'], stored)
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(ops.main(['dump', 'hosts.h.group', str(self.root)]), 0)
                self.assertEqual(json.loads(out.getvalue()), stored)

    def test_old_plural_field_and_both_fields_are_rejected_with_hint(self):
        for fields in ('groups: [web]', 'groups: [web], group: web'):
            with self.subTest(fields=fields):
                (self.root / 'hosts.yaml').write_text('hosts: {h: {connection: {local: true}, ' + fields + '}}')
                with self.assertRaisesRegex(ops.ConfigError, 'groups has been renamed to group'):
                    ops.Validator(self.root).check()
                status, _, err, execute = self.cli(['inventory/system', '--all', '--root', str(self.root)])
                self.assertEqual(status, 1)
                self.assertIn('renamed to group', err)
                execute.assert_not_called()

    def test_group_type_validation(self):
        for value in ('null', '2', 'true', '{}', '""', '" "', '[null]', '[2]', '[true]', '[""]', '[" "]', '[[web]]'):
            with self.subTest(value=value):
                (self.root / 'hosts.yaml').write_text(
                    'hosts: {h: {connection: {local: true}, group: ' + value + '}}')
                with self.assertRaisesRegex(ops.ConfigError, 'group'):
                    ops.Validator(self.root).check()

    def test_same_name_and_literal_prefixed_ids_need_no_guessing(self):
        with (self.root / 'hosts.yaml').open('a') as stream:
            stream.write('  web:\n    connection: {local: true}\n  "group:web":\n    connection: {local: true}\n')
        self.assertEqual(runner.select_hosts(self.root, [('host', 'web')]), ['web'])
        self.assertEqual(runner.select_hosts(self.root, [('group', 'web')]), ['web-01', 'web-02'])
        self.assertEqual(runner.select_hosts(self.root, [('host', 'group:web')]), ['group:web'])

    def test_bad_selector_prevents_all_execution_and_never_switches_kind(self):
        for option, target in (('--host', 'missing'), ('--group', 'missing'),
                               ('--host', 'web'), ('--group', 'web-01')):
            with self.subTest(option=option, target=target):
                status, out, err, execute = self.cli(
                    ['inventory/system', '--root', str(self.root), '--host', 'web-01', option, target])
                self.assertEqual(status, 1)
                self.assertEqual(out, '')
                self.assertIn('unknown', err)
                execute.assert_not_called()

    def test_cli_leading_recipe_and_single_host_summary(self):
        status, out, _, execute = self.cli(['inventory/system', '--host', 'web-01', '--root', str(self.root)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out)['status'], 'success')
        execute.assert_called_once_with(self.root, 'web-01', 30, recipe='inventory/system', force=False, access_checked=True, access_result={'host': 'web-01', 'status': 'success', 'connected': True})

    def test_cli_multiple_groups_and_hosts_preserve_option_order(self):
        status, out, _, execute = self.cli(
            ['inventory/system', '--root', str(self.root), '--group', 'production',
             '--host', 'bastion', 'web-01', '--group', 'web', 'staging', '--host', 'db-01'])
        expected = ['web-01', 'db-01', 'bastion', 'web-02']
        self.assertEqual(status, 0)
        self.assertEqual([r['host'] for r in json.loads(out)['hosts']], expected)
        self.assertEqual([call.args[1] for call in execute.call_args_list], expected)

    def test_one_member_group_and_duplicate_hosts_use_single_summary(self):
        for targets in (['--group', 'staging'], ['--host', 'web-02', 'web-02']):
            with self.subTest(targets=targets):
                status, out, _, execute = self.cli(['inventory/system', '--root', str(self.root), *targets])
                self.assertEqual(status, 0)
                self.assertEqual(json.loads(out)['status'], 'success')
                execute.assert_called_once_with(self.root, 'web-02', 30, recipe='inventory/system', force=False, access_checked=True, access_result={'host': 'web-02', 'status': 'success', 'connected': True})

    def test_all_one_host_still_uses_batch_summary(self):
        (self.root / 'hosts.yaml').write_text('hosts: {h: {connection: {local: true}}}')
        status, out, _, execute = self.cli(['inventory/system', '--all', '--root', str(self.root)])
        self.assertEqual(status, 0)
        self.assertEqual([r['host'] for r in json.loads(out)['hosts']], ['h'])
        execute.assert_called_once_with(self.root, 'h', 30, recipe='inventory/system', force=False, access_checked=True, access_result={'host': 'h', 'status': 'success', 'connected': True})

    def test_cli_explicit_recipe_at_different_positions(self):
        for args in (['--recipe', 'inventory/system', '--group', 'web'],
                     ['--group', 'web', '--recipe', 'inventory/system'],
                     ['--group', 'web', '--recipe', 'inventory/system', '--host', 'db-01']):
            with self.subTest(args=args):
                status, out, _, execute = self.cli([*args, '--root', str(self.root)])
                self.assertEqual(status, 0)
                self.assertEqual(execute.call_count, 3 if '--host' in args else 2)
                self.assertTrue(all(c.kwargs['recipe'] == 'inventory/system' for c in execute.call_args_list))

    def test_cli_all_with_profile_and_root(self):
        for args in (['--all', '--profile', 'synthetic'], ['--all', '--root', str(self.root)]):
            with self.subTest(args=args), patch.object(runner, 'resolve_root', return_value=self.root) as resolve:
                status, out, _, execute = self.cli([*args, '--recipe', 'inventory/system'])
                self.assertEqual(status, 0)
                self.assertEqual(len(json.loads(out)['hosts']), 5)
                self.assertEqual(execute.call_count, 5)
                resolve.assert_called_once_with(None if '--profile' in args else self.root,
                                                'synthetic' if '--profile' in args else None)

    def test_batch_continues_after_preflight_error_and_partial(self):
        results = [ops.ConfigError('synthetic failure'),
                   (dict(self.report, status='partial'), self.root / 'partial.json'),
                   (self.report, self.root / 'success.json')]
        status, out, _, execute = self.cli(
            ['inventory/system', '--root', str(self.root), '--group', 'production', 'web'], side_effect=results)
        self.assertEqual(status, 1)
        self.assertEqual([r['status'] for r in json.loads(out)['hosts']], ['failed', 'partial', 'success'])
        self.assertEqual(execute.call_count, 3)

    def test_empty_inventory_is_error(self):
        (self.root / 'hosts.yaml').write_text('hosts: {}')
        status, _, err, execute = self.cli(['inventory/system', '--all', '--root', str(self.root)])
        self.assertEqual(status, 1)
        self.assertIn('no hosts selected', err)
        execute.assert_not_called()

    def test_usage_errors_prevent_environment_resolution(self):
        for args in ([], ['--host', 'web-01'], ['inventory/system'],
                     ['inventory/system', '--all', '--host', 'web-01'],
                     ['inventory/system', '--all', '--group', 'web'],
                     ['inventory/system', '--host'], ['inventory/system', '--group'],
                     ['inventory/system', '--all', '--recipe', 'inventory/system'],
                     ['--all', '--recipe', 'inventory/system', '--recipe', 'inventory/system'],
                     ['--all', 'inventory/system'], ['--root', str(self.root), 'inventory/system', '--all'],
                     ['inventory/system', '--hosts', 'web-01'],
                     ['inventory/system', str(self.root), '--host', 'web-01']):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), \
                    patch.object(runner, 'run') as execute, patch.object(runner, 'resolve_root') as resolve:
                with self.assertRaises(SystemExit) as raised:
                    runner.main(args)
                self.assertEqual(raised.exception.code, 2)
                execute.assert_not_called()
                resolve.assert_not_called()

    def test_root_and_profile_conflict_prevents_execution(self):
        status, _, err, execute = self.cli(['inventory/system', '--host', 'web-01',
                                          '--root', str(self.root), '--profile', 'synthetic'])
        self.assertEqual(status, 1)
        self.assertIn('either a management directory or --profile', err)
        execute.assert_not_called()

    def test_progress_auto_tty_and_manual_overrides_with_json_output_override(self):
        for tty, flags, expected in ((True, [], True), (False, [], False),
                                      (False, ['--verbose'], True), (True, ['--quiet'], False), (True, ['--json'], True)):
            with self.subTest(tty=tty, flags=flags):
                out, err = io.StringIO(), io.StringIO()
                with patch.object(out, 'isatty', return_value=tty), \
                        contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                        patch.object(runner, 'run', return_value=(self.report, self.root / 'result.json')):
                    code = runner.main(['inventory/system', '--all', '--root', str(self.root), *flags])
                self.assertEqual(code, 0)
                if tty and '--json' not in flags:
                    self.assertIn('│ status', out.getvalue())
                    self.assertIn('result_path', out.getvalue())
                else:
                    self.assertEqual(len(json.loads(out.getvalue())['hosts']), 5)
                if expected:
                    self.assertIn('[1/5]', err.getvalue())
                    self.assertIn('[5/5]', err.getvalue())
                    self.assertIn('completed: success', err.getvalue())
                else:
                    self.assertEqual(err.getvalue(), '')
                self.assertIsNone(runner._progress.get())

    def test_progress_reports_failed_host_and_continues_without_exception_text(self):
        status, out, err, execute = self.cli(
            ['inventory/system', '--root', str(self.root), '--host', 'web-01', 'db-01', '--verbose'],
            side_effect=[ops.ConfigError('private-secret'), (self.report, self.root / 'result.json')])
        self.assertEqual(status, 1)
        self.assertEqual(execute.call_count, 2)
        self.assertIn('[1/2]', err)
        self.assertIn('failed before completion: ConfigError', err)
        self.assertIn('[2/2]', err)
        self.assertIn('completed: success', err)
        self.assertNotIn('private-secret', out + err)
        self.assertEqual(len(json.loads(out)['hosts']), 2)

    def test_heartbeat_reports_wait_without_sleeping_or_target_queries(self):
        reporter = runner.RunProgress('[1/1] "synthetic":')
        with patch.object(reporter.stop, 'wait', side_effect=[False, True]), \
                patch.object(runner.time, 'monotonic', return_value=reporter.changed + 6), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            reporter.heartbeat()
        self.assertIn('still starting (6s in this stage)', err.getvalue())

    def test_progress_context_stops_worker_and_resets_after_error(self):
        with patch.object(runner.threading, 'Thread') as worker, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(RuntimeError):
                with runner.reporting(True, '[test]'):
                    reporter = runner._progress.get()
                    raise RuntimeError('synthetic')
        worker.return_value.start.assert_called_once()
        worker.return_value.join.assert_called_once()
        self.assertTrue(reporter.stop.is_set())
        self.assertIsNone(runner._progress.get())

    def test_verbose_quiet_conflict_is_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), patch.object(runner, 'run') as execute:
            with self.assertRaises(SystemExit) as raised:
                runner.main(['inventory/system', '--all', '--verbose', '--quiet'])
        self.assertEqual(raised.exception.code, 2)
        execute.assert_not_called()

    def test_parallel_limit_failure_isolation_order_and_progress_contexts(self):
        barrier = threading.Barrier(2)
        second_finished = threading.Event()
        lock = threading.Lock()
        active = maximum = 0
        completed, labels = [], {}
        def collect(root, host, timeout, recipe, **options):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
                labels[host] = runner._progress.get().label
            try:
                barrier.wait(timeout=3)
                if host == 'web-01':
                    self.assertTrue(second_finished.wait(3))
                with lock:
                    completed.append(host)
                if host == 'db-01':
                    second_finished.set()
                    raise RuntimeError('private-parallel-error')
                runner.progress('synthetic collection')
                return self.report, self.root / (host + '.json')
            finally:
                with lock:
                    active -= 1
        expected = ['web-01', 'db-01', 'web-02', 'bastion']
        status, out, err, execute = self.cli(
            ['inventory/system', '--root', str(self.root), '--host', *expected,
             '--threads', '2', '--verbose'], side_effect=collect)
        self.assertEqual(status, 1)
        self.assertEqual(maximum, 2)
        self.assertEqual(active, 0)
        self.assertEqual(completed[0], 'db-01')
        reports = json.loads(out)['hosts']
        self.assertEqual([r['host'] for r in reports], expected)
        self.assertEqual([r['status'] for r in reports], ['success', 'failed', 'success', 'success'])
        self.assertEqual(execute.call_count, 4)
        for index, host in enumerate(expected, 1):
            self.assertEqual(labels[host], f'[{index}/4] {json.dumps(host)}:')
        self.assertNotIn('private-parallel-error', out + err)
        self.assertIsNone(runner._progress.get())

    def test_sequential_mode_does_not_create_pool(self):
        with patch.object(runner, 'ThreadPoolExecutor') as pool:
            status, out, _, execute = self.cli(
                ['inventory/system', '--all', '--root', str(self.root), '--threads', '1'])
        self.assertEqual(status, 0)
        pool.assert_not_called()
        self.assertEqual([c.args[1] for c in execute.call_args_list],
                         [r['host'] for r in json.loads(out)['hosts']])

    def test_cpu_default_cap_fallback_and_actual_worker_count(self):
        for cores, expected in ((None, 1), (1, 1), (3, 3), (64, 8)):
            with self.subTest(cores=cores), patch.object(runner.os, 'cpu_count', return_value=cores):
                self.assertEqual(runner.default_threads(), expected)
        executor = runner.ThreadPoolExecutor
        with patch.object(runner.os, 'cpu_count', return_value=3), \
                patch.object(runner, 'ThreadPoolExecutor', wraps=executor) as pool, \
                patch.object(runner, 'run', return_value=(self.report, self.root / 'result.json')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(['inventory/system', '--all', '--root', str(self.root)]), 0)
        pool.assert_called_once_with(max_workers=3, thread_name_prefix='recipe-host')

    def test_invalid_thread_count_and_singular_alias_are_rejected(self):
        for option, value in (('--threads', '0'), ('--threads', '-1'), ('--threads', '1.5'),
                              ('--threads', 'abc'), ('--thread', '2')):
            with self.subTest(option=option, value=value), contextlib.redirect_stderr(io.StringIO()), \
                    patch.object(runner, 'run') as execute:
                with self.assertRaises(SystemExit) as raised:
                    runner.main(['inventory/system', '--all', option, value])
                self.assertEqual(raised.exception.code, 2)
                execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
