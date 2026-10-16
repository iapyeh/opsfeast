"""Synthetic inventory and runner regressions; never contact SSH hosts."""
import json
import contextlib
from concurrent.futures import ThreadPoolExecutor
import io
from pathlib import Path
import runpy
import shutil
from attribution_fixture import copy_recipe
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_recipe as runner
import opsfeast as ops
import host_runtime as hr
C = runner.collector


def result(text='', code=0):
    return SimpleNamespace(stdout=text, stderr='', exitcode=code)


def linux_outputs(product='NAME="Example Linux"\nVERSION_ID="1.2"\n'):
    return [result('Linux\n'), result('node\n'), result('6.1\n'), result('x86_64\n'), result(product)]


def runner_outputs():
    def execute(argv, **kwargs):
        if argv[:1] == ['uname']:
            return result({'-s': 'Linux', '-n': 'node', '-r': '6.1', '-m': 'x86_64'}[argv[1]] + '\n')
        return result('ID=example\nNAME="Example Linux"\nVERSION_ID=1.2\n')
    return execute


def completed_report():
    report = C['new_report']('example', 'mock')
    session = Mock()
    session.exec_command.side_effect = linux_outputs()
    C['collect'](session, report, 7)
    return C['finish'](report)


class InventoryTests(unittest.TestCase):
    def collect(self, responses):
        session = Mock()
        session.exec_command.side_effect = responses
        report = C['new_report']('example', 'mock')
        C['collect'](session, report, 7)
        C['finish'](report)
        return report, session

    def test_success_and_finite_argv(self):
        report, session = self.collect(linux_outputs())
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['reason_code'], 'inventory_complete')
        self.assertIn('7/7', report['message'])
        self.assertEqual(report['detected_kernel'], 'Linux')
        self.assertEqual(report['observations']['system_name']['value'], 'Example Linux')
        for call in session.exec_command.call_args_list:
            self.assertIsInstance(call.args[0], list)
            self.assertEqual(call.kwargs, {'check': False, 'command_timeout': 7})

    def test_version_absent(self):
        report, _ = self.collect(linux_outputs('NAME=Example\n'))
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['reason_code'], 'inventory_incomplete')
        self.assertIn('6/7', report['message'])
        self.assertIn('system_version (unavailable)', report['message'])
        self.assertEqual(report['observations']['system_version']['status'], 'unavailable')
        self.assertIsNone(report['observations']['system_version']['value'])

    def test_unsupported_stops_after_detection(self):
        for kernel in ('Darwin', 'FreeBSD'):
            with self.subTest(kernel=kernel):
                report, session = self.collect([result(kernel + '\n')])
                self.assertEqual(report['status'], 'unsupported')
                self.assertEqual(session.exec_command.call_count, 1)
                self.assertEqual(report['observations']['kernel_name']['value'], kernel)
                self.assertEqual(report['reason_code'], 'unsupported_platform')
                self.assertEqual(report['detected_kernel'], kernel)
                self.assertEqual(report['supported_platforms'], ['linux'])
                self.assertIn(kernel, report['message'])
                self.assertIn('remaining inventory fields were not collected', report['message'])

    def test_cleanup_error_takes_precedence_over_unsupported(self):
        report, _ = self.collect([result('FreeBSD\n')])
        report['execution_errors'].append({'stage': 'cleanup', 'type': 'RuntimeError'})
        C['finish'](report)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['reason_code'], 'execution_error')
        self.assertIn('cleanup', report['message'])
        self.assertIn('1/7', report['message'])
        self.assertEqual(report['detected_kernel'], 'FreeBSD')

    def test_bad_kernel_does_not_guess(self):
        report, session = self.collect([result('Linux\nDarwin\n')])
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['reason_code'], 'no_observations')
        self.assertIsNone(report['detected_kernel'])
        self.assertIn('parsing_failed', report['message'])
        self.assertEqual(report['observations']['platform']['status'], 'not_attempted')
        self.assertEqual(session.exec_command.call_count, 1)

    def test_missing_file_fallback(self):
        responses = linux_outputs()[:-1] + [result(code=44), result('NAME=Fallback\nVERSION_ID=2\n')]
        report, _ = self.collect(responses)
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['observations']['system_name']['source_ids'], ['os_release_0', 'os_release_1'])

    def test_denied_does_not_fallback(self):
        report, session = self.collect(linux_outputs()[:-1] + [result(code=45)])
        self.assertEqual(report['observations']['system_name']['status'], 'permission_denied')
        self.assertEqual(session.exec_command.call_count, 5)

    def test_successful_exit_with_truncation_is_not_a_success_value(self):
        outputs = linux_outputs()
        outputs[1] = SimpleNamespace(stdout='partial', stderr='', exitcode=0,
                                     stdout_truncated=True, stderr_truncated=False)
        report, _ = self.collect(outputs)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['observations']['hostname']['status'], 'parsing_failed')
        self.assertIsNone(report['observations']['hostname']['value'])
        self.assertEqual(report['sources'][1]['error']['code'], 'output_truncated')

    def test_timeout_preserves_partial_output(self):
        exc = TimeoutError('private exception text')
        exc.result = SimpleNamespace(stdout='partial', stderr='', termination_status='unknown')
        outputs = linux_outputs()
        outputs[1] = exc
        report, _ = self.collect(outputs)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['observations']['hostname']['status'], 'timeout')
        self.assertEqual(report['sources'][1]['termination_status'], 'unknown')
        self.assertNotIn('private exception text', json.dumps(report))

    def test_transport_failure_is_failed_even_with_observations(self):
        outputs = linux_outputs()
        outputs[1] = OSError('secret')
        report, _ = self.collect(outputs)
        self.assertEqual(report['status'], 'failed')
        self.assertNotIn('secret', json.dumps(report))

    def test_command_failure_and_parse_failure(self):
        outputs = linux_outputs()
        outputs[1] = result(code=1)
        outputs[2] = result('')
        report, _ = self.collect(outputs)
        self.assertEqual(report['observations']['hostname']['status'], 'command_failed')
        self.assertEqual(report['observations']['kernel_release']['status'], 'parsing_failed')
        self.assertEqual(report['status'], 'partial')

    def test_release_parser_never_executes_and_rejects_malformed(self):
        self.assertEqual(C['parse_os_release']('NAME="$(touch /tmp/never-run)"')['NAME'], '$(touch /tmp/never-run)')
        for text in ('NAME="unterminated', 'NAME=x\nNAME=y', 'NAME=two words', 'invalid'):
            with self.assertRaises(ValueError):
                C['parse_os_release'](text)
        report, _ = self.collect(linux_outputs('NAME="unterminated'))
        self.assertEqual(report['observations']['system_name']['status'], 'parsing_failed')


class RunnerTests(unittest.TestCase):
    def setUp(self):
        from access_check import VERSION
        checker = patch('access_check.check_many', side_effect=lambda root, hosts, *args: {'contract_version': VERSION, 'status': 'success', 'hosts': [{'host': h, 'status': 'success', 'connected': True} for h in hosts]})
        checker.start()
        self.addCleanup(checker.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'recipes/inventory/system'
        copy_recipe(runner.BUNDLE, self.directory)
        (self.root / 'hosts.yaml').write_text('hosts:\n  example:\n    connection: {local: true}\n    recipes:\n      - recipe: ./recipes/inventory/system\n')
        self.session = Mock()
        self.session.exec_command.side_effect = runner_outputs()
        self.session_class = Mock(return_value=self.session)

    def run_recipe(self):
        return runner.run(self.root, 'example', session_class=self.session_class)

    def test_result_filename_uses_start_second_and_preserves_precise_metadata(self):
        original = runner.collector['new_report']
        started = '2026-10-14T00:00:00.987654+08:00'
        def new_report(host, evidence):
            return dict(original(host, evidence), started_at=started)
        with patch.dict(runner.collector, {'new_report': new_report}):
            report, path = self.run_recipe()
        self.assertEqual(report['status'], 'success')
        self.assertRegex(path.name, r'^20261013T160000Z-inventory-system-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.json$')
        self.assertEqual(json.loads(path.read_text())['started_at'], started)
        self.assertNotEqual(report['finished_at'], started)

    def test_result_filename_same_second_unique_and_seconds_sort(self):
        first = runner._inventory_result_filename('2026-10-14T00:00:00.100000+00:00')
        same = runner._inventory_result_filename('2026-10-14T00:00:00.900000Z')
        later = runner._inventory_result_filename('2026-10-14T00:00:01+00:00')
        self.assertNotEqual(first, same)
        self.assertEqual(first[:16], same[:16])
        self.assertLess(first, later)
        self.assertLess(same, later)

    def test_result_filename_requires_an_aware_start_time(self):
        with self.assertRaises(ValueError):
            runner._inventory_result_filename('2026-10-14T00:00:00')

    def test_result_index_and_lookup_accept_legacy_and_timestamp_names(self):
        from recipe_reports import results, show_result
        report, new_path = self.run_recipe()
        legacy = new_path.parent / 'inventory-system-00000000-0000-4000-8000-000000000001.json'
        old_report = dict(report, started_at='2020-01-01T00:00:00+00:00')
        legacy.write_text(json.dumps(old_report))
        root = self.root.resolve()
        index = results(root, recipe='inventory-system')
        self.assertEqual(index['status'], 'success')
        self.assertEqual([row['result_id'] for row in index['results']],
                         [new_path.relative_to(root).as_posix(), legacy.relative_to(root).as_posix()])
        for path, expected in ((legacy, old_report), (new_path, report)):
            self.assertEqual(show_result(root, path.relative_to(root).as_posix()), expected)
        self.assertEqual(json.loads(legacy.read_text()), old_report)

    def test_parallel_runner_owns_separate_sessions_facts_and_results(self):
        (self.root / 'hosts.yaml').write_text('''hosts:
  example:
    connection: {local: true}
  other:
    connection: {local: true}
''')
        barrier = threading.Barrier(2)
        sessions, owners = [], []
        lock = threading.Lock()
        def factory():
            owner = threading.get_ident()
            values = runner_outputs()
            session = Mock()
            def command(*args, **kwargs):
                self.assertEqual(threading.get_ident(), owner)
                return values(*args, **kwargs)
            def close(strict=False):
                self.assertTrue(strict)
                self.assertEqual(threading.get_ident(), owner)
            session.exec_command.side_effect = command
            session.close.side_effect = close
            with lock:
                sessions.append(session)
                owners.append(owner)
            barrier.wait(timeout=3)
            return session
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(runner.run, self.root, host, session_class=factory,
                                   recipe='inventory/system') for host in ('example', 'other')]
            results = [future.result() for future in futures]
        self.assertEqual(len(set(owners)), 2)
        self.assertEqual([report['host_id'] for report, _ in results], ['example', 'other'])
        self.assertEqual([report['status'] for report, _ in results], ['success', 'success'])
        self.assertNotEqual(results[0][1], results[1][1])
        for report, path in results:
            self.assertEqual(json.loads(path.read_text()), report)
        self.assertEqual(len(list((self.root / 'observations/host-init').glob('*.json'))), 2)
        for session in sessions:
            session.close.assert_called_once_with(strict=True)

    def test_save_and_cleanup(self):
        report, path = self.run_recipe()
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['evidence_kind'], 'mock')
        self.assertEqual(json.loads(path.read_text()), report)
        self.session.close.assert_called_once_with(strict=True)
        self.session.connect.assert_not_called()
        self.assertEqual(report['recipe']['selection_source'], 'hosts')

    def test_checkout_recipe_without_instance_copy(self):
        shutil.rmtree(self.root / 'recipes')
        for selection in ('cli', 'hosts', 'absolute'):
            with self.subTest(selection=selection):
                (self.root / 'hosts.yaml').write_text('include: [hosts/group.yaml]\n')
                (self.root / 'hosts').mkdir(exist_ok=True)
                (self.root / 'hosts/group.yaml').write_text('hosts:\n  example:\n    connection: {local: true}\n    recipes: [{recipe: recipes/inventory/system}]\n')
                self.session.exec_command.side_effect = runner_outputs()
                recipe = {'hosts': None, 'absolute': str(runner.BUNDLE),
                          'cli': 'inventory/system'}[selection]
                report, path = runner.run(self.root, 'example', recipe=recipe, session_class=self.session_class)
                self.assertEqual(report['status'], 'success')
                self.assertEqual(report['recipe']['location_source'], 'repository')
                self.assertEqual(report['recipe']['resolved_path'], str(runner.BUNDLE))
                self.assertEqual(report['recipe']['installed_path'], 'recipes/inventory/system')
                self.assertEqual(path.parent, self.root.resolve() / 'observations')
                self.assertFalse((self.root / 'recipes').exists())

    def test_checkout_selection_ignores_outdated_instance_copy(self):
        (self.directory / 'main.py').write_text('outdated copy')
        report, _ = runner.run(self.root, 'example', recipe='inventory/system', session_class=self.session_class)
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['recipe']['location_source'], 'repository')

    def test_short_path_has_no_instance_fallback_and_cannot_escape(self):
        # Even a matching instance copy must not be used for a missing checkout path.
        copy_recipe(runner.BUNDLE, self.root / 'inventory/system')
        empty_recipes = self.root / 'checkout/recipes'
        empty_recipes.mkdir(parents=True)
        with patch.object(ops, 'REPOSITORY_RECIPES', empty_recipes):
            for recipe in ('inventory/system', 'inventory/../../../recipes/inventory/system'):
                with self.subTest(recipe=recipe), self.assertRaises(ops.ConfigError):
                    runner.run(self.root, 'example', recipe=recipe, session_class=self.session_class)
        self.session_class.assert_not_called()

    def test_short_path_symlink_escape_rejected(self):
        recipes = self.root / 'checkout/recipes'
        recipes.mkdir(parents=True)
        (recipes / 'inventory').symlink_to(self.root / 'recipes/inventory', target_is_directory=True)
        with patch.object(ops, 'REPOSITORY_RECIPES', recipes), self.assertRaises(ops.ConfigError):
            runner.run(self.root, 'example', recipe='inventory/system', session_class=self.session_class)
        self.session_class.assert_not_called()

    def test_cli_recipes_prefix_rejected_with_correction_before_connecting(self):
        for recipe in ('recipes', 'recipes/inventory/system', 'recipes/inventory/system/'):
            with self.subTest(recipe=recipe), self.assertRaisesRegex(ops.ConfigError, 'omit the recipes/ prefix'):
                runner.run(self.root, 'example', recipe=recipe, session_class=self.session_class)
        self.session_class.assert_not_called()
        self.assertFalse((self.root / 'observations').exists())

    def test_main_recipes_prefix_reports_correction(self):
        with patch.object(runner, 'load_runtime') as runtime, \
                contextlib.redirect_stderr(io.StringIO()) as error, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            code = runner.main(['--host', 'example', '--root', str(self.root), '--recipe', 'recipes/inventory/system'])
        self.assertEqual(code, 1)
        self.assertIn('omit the recipes/ prefix', error.getvalue())
        self.assertIn('inventory/system', error.getvalue())
        self.assertEqual(output.getvalue(), '')
        runtime.assert_not_called()

    def test_checkout_update_changes_recorded_digest_without_copying(self):
        checkout = self.root / 'checkout'
        recipes = checkout / 'recipes'
        bundle = recipes / 'inventory/system'
        shutil.copytree(runner.BUNDLE, bundle)
        shutil.rmtree(self.root / 'recipes')
        with patch.object(ops, 'REPOSITORY_RECIPES', recipes), \
             patch.object(runner, 'REPOSITORY_ROOT', checkout), \
             patch.object(runner, 'REPOSITORY_RECIPES', recipes), \
             patch.object(runner, 'BUNDLE', bundle):
            first, _ = runner.run(self.root, 'example', recipe='inventory/system', session_class=self.session_class)
            entry = bundle / 'implementations/linux.py'
            entry.write_text(entry.read_text() + '\n# Updated checkout fixture\n')
            self.session.exec_command.side_effect = runner_outputs()
            second, _ = runner.run(self.root, 'example', recipe='inventory/system', session_class=self.session_class)
        self.assertNotEqual(first['recipe']['implementation_sha256'], second['recipe']['implementation_sha256'])
        self.assertFalse((self.root / 'recipes').exists())

    def test_checkout_files_and_glob_cannot_escape_recipe_boundary(self):
        checkout = self.root / 'checkout'
        recipes = checkout / 'recipes'
        bundle = recipes / 'inventory/system'
        copy_recipe(runner.BUNDLE, bundle)
        with tempfile.TemporaryDirectory() as external:
            external = Path(external)
            with patch.object(ops, 'REPOSITORY_RECIPES', recipes):
                for name in ('recipe.yaml', 'implementations/linux.py'):
                    with self.subTest(name=name):
                        entry = bundle / name
                        content = entry.read_bytes()
                        (external / name).parent.mkdir(parents=True, exist_ok=True)
                        (external / name).write_bytes(content)
                        entry.unlink()
                        entry.symlink_to(external / name)
                        with self.assertRaises(ops.ConfigError):
                            runner.run(self.root, 'example', recipe='inventory/system', session_class=self.session_class)
                        entry.unlink()
                        entry.write_bytes(content)
                (recipes / 'escape').symlink_to(external, target_is_directory=True)
                (self.root / 'hosts.yaml').write_text('hosts: {example: {connection: {local: true}, recipes: [{glob: "recipes/**"}]}}')
                with self.assertRaises(ops.ConfigError):
                    ops.Validator(self.root).check()
        self.session_class.assert_not_called()

    def test_cli_recipe_without_host_selection(self):
        for selection in ('', '    recipes: []\n'):
            with self.subTest(selection=selection):
                (self.root / 'hosts.yaml').write_text('hosts:\n  example:\n    connection: {local: true}\n' + selection)
                self.session.exec_command.side_effect = runner_outputs()
                report, path = runner.run(self.root, 'example', recipe='./recipes/inventory/system',
                                          session_class=self.session_class)
                self.assertEqual(report['status'], 'success')
                self.assertEqual(report['recipe']['selection_source'], 'cli')
                self.assertEqual(json.loads(path.read_text()), report)

    def test_cli_recipe_overrides_invalid_host_recipe_selection(self):
        (self.root / 'hosts.yaml').write_text('hosts:\n  example:\n    connection: {local: true}\n    recipes:\n      - recipe: missing-host-recipe\n')
        report, _ = runner.run(self.root, 'example', recipe=str(self.directory),
                               session_class=self.session_class)
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['recipe']['installed_path'], 'recipes/inventory/system')

    def test_cli_relative_path_uses_root_not_include_directory_or_cwd(self):
        (self.root / 'hosts').mkdir()
        (self.root / 'hosts.yaml').write_text('include: [hosts/group.yaml]\n')
        (self.root / 'hosts/group.yaml').write_text('hosts:\n  example:\n    connection: {local: true}\n')
        report, _ = runner.run(self.root, 'example', recipe='./recipes/inventory/system',
                               session_class=self.session_class)
        self.assertEqual(report['status'], 'success')

    def test_invalid_cli_recipe_never_falls_back_or_connects(self):
        with tempfile.TemporaryDirectory() as outside:
            escape = self.root / 'escape'
            escape.symlink_to(outside, target_is_directory=True)
            bad_descriptor = self.root / 'bad-descriptor'
            bad_descriptor.mkdir()
            (bad_descriptor / 'recipe.yaml').write_text('[]\n')
            unsupported = self.root / 'unsupported'
            unsupported.mkdir()
            (unsupported / 'recipe.yaml').write_text('id: other-recipe\n')
            for recipe in ('missing', 'hosts.yaml', '', str(outside), '../outside',
                           'escape', 'bad-descriptor', 'unsupported'):
                with self.subTest(recipe=recipe), self.assertRaises(ops.ConfigError):
                    runner.run(self.root, 'example', recipe=recipe, session_class=self.session_class)
            self.session_class.assert_not_called()

    def test_cli_descriptor_symlink_outside_root_rejected(self):
        descriptor = self.directory / 'recipe.yaml'
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / 'recipe.yaml'
            shutil.copy2(descriptor, external)
            descriptor.unlink()
            descriptor.symlink_to(external)
            with self.assertRaises(ops.ConfigError):
                runner.run(self.root, 'example', recipe='./recipes/inventory/system',
                           session_class=self.session_class)
        self.session_class.assert_not_called()

    def test_main_passes_cli_recipe_and_reports_success(self):
        path = self.root / 'result.json'
        with patch.object(runner, 'run', return_value=(completed_report(), path)) as run:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = runner.main(['--host', 'example', '--root', str(self.root), '--recipe', './recipes/inventory/system'])
        self.assertEqual(code, 0)
        run.assert_called_once_with(self.root, 'example', 30, recipe='./recipes/inventory/system', force=False, access_checked=True, access_result={'host': 'example', 'status': 'success', 'connected': True})
        self.assertEqual(json.loads(output.getvalue())['result_path'], str(path))

    def test_runner_progress_explains_stages_without_raw_output(self):
        with contextlib.redirect_stderr(io.StringIO()) as err, runner.reporting(True, '[1/1] synthetic:'):
            report, path = self.run_recipe()
        for stage in ('validating configuration and recipe', 'preparing connection',
                      'checking cached host facts', 'discovering host platform',
                      'selecting platform implementation', 'collecting inventory',
                      'validating inventory result', 'closing session', 'saving result'):
            self.assertIn(stage, err.getvalue())
        self.assertTrue(path.is_file())
        self.assertEqual(report['status'], 'success')
        self.assertIsNone(runner._progress.get())

    def test_main_unsupported_summary_matches_saved_result(self):
        (self.root / 'hosts.yaml').write_text('hosts: {example: {connection: {local: true}}}')
        self.session.exec_command.side_effect = [result('OpenBSD\n'), result('7.6\n'), result('amd64\n')]
        with patch.object(runner, 'load_runtime', return_value=(self.session_class, {'verification': 'mock'})), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            code = runner.main(['--host', 'example', '--root', str(self.root), '--recipe', 'inventory/system'])
        summary = json.loads(output.getvalue())
        saved = json.loads(Path(summary['result_path']).read_text())
        self.assertEqual(code, 1)
        self.assertEqual(summary['recipe_id'], 'inventory-system')
        self.assertEqual(summary['status'], 'unsupported')
        for key in ('status', 'reason_code', 'message', 'detected_kernel', 'supported_platforms'):
            self.assertEqual(summary[key], saved[key])
        self.assertEqual(saved['observations']['kernel_name']['value'], 'OpenBSD')
        self.assertEqual(self.session.exec_command.call_count, 3)
        self.session.close.assert_called_once_with(strict=True)

    def test_main_uses_remembered_management_directory(self):
        checkout = self.root / 'checkout'
        checkout.mkdir()
        with patch.object(ops, 'REPOSITORY_ROOT', checkout):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ops.main(['init', str(self.root)]), 0)
            with patch.object(runner, 'run', return_value=(completed_report(), self.root / 'result.json')) as run, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(['--host', 'example', '--recipe', 'inventory/system']), 0)
            run.assert_called_once_with(self.root.resolve(), 'example', 30, recipe='inventory/system', force=False, access_checked=True, access_result={'host': 'example', 'status': 'success', 'connected': True})
            (checkout / '.my-ops.yaml').write_text('schema_version: 1\nroot: missing\n')
            with patch.object(runner, 'run') as run, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(runner.main(['inventory/system', '--host', 'example']), 1)
            run.assert_not_called()

    def test_cleanup_failure_retains_observations(self):
        self.session.close.side_effect = RuntimeError('secret')
        report, _ = self.run_recipe()
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['observations']['hostname']['value'], 'node')
        self.assertEqual(report['execution_errors'][-1]['stage'], 'cleanup')
        self.assertNotIn('secret', json.dumps(report))

    def test_selection_and_modified_code_rejected_before_session(self):
        (self.directory / 'implementations/linux.py').write_text('raise RuntimeError("should not execute")')
        with self.assertRaises(ops.ConfigError):
            self.run_recipe()
        self.session_class.assert_not_called()

    def test_output_symlink_rejected_before_session(self):
        (self.root / 'observations').symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(ops.ConfigError):
            self.run_recipe()
        self.session_class.assert_not_called()

    def test_unselected_rejected(self):
        (self.root / 'hosts.yaml').write_text('hosts:\n  example:\n    connection: {local: true}\n    recipes: []\n')
        with self.assertRaises(ops.ConfigError):
            self.run_recipe()
        self.session_class.assert_not_called()

    def test_connection_failure_saved_safely(self):
        (self.root / 'hosts.yaml').write_text('hosts:\n  example:\n    connection: {hostname: example.invalid, user: ops, allow_agent: true}\n    recipes:\n      - recipe: ./recipes/inventory/system\n')
        self.session_class.resolve_connection.return_value = {'hostname': 'example.invalid', 'username': 'ops', 'port': 22}
        self.session.connect.side_effect = OSError('private credential')
        report, _ = self.run_recipe()
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['sources'], [])
        self.assertNotIn('private credential', json.dumps(report))
        self.session.close.assert_called_once_with(strict=True)

    def test_nested_hops_receive_budgets_and_cleanup_root(self):
        (self.root / 'hosts.yaml').write_text('hosts:\n  bastion:\n    connection: {hostname: bastion.example, allow_agent: true}\n  example:\n    connection:\n      hostname: target.example\n      allow_agent: true\n      via: {host: bastion}\n    recipes:\n      - recipe: ./recipes/inventory/system\n')
        self.session_class.resolve_connection.side_effect = [
            {'hostname': 'bastion.example', 'username': 'ops', 'port': 22},
            {'hostname': 'target.example', 'username': 'ops', 'port': 22}]
        middle = Mock()
        target = Mock()
        self.session.connect.return_value = middle
        middle.connect.return_value = target
        target.exec_command.side_effect = runner_outputs()
        report, _ = self.run_recipe()
        self.assertEqual(report['status'], 'success')
        self.assertEqual(len(report['hops']), 2)
        self.assertTrue(all(hop['connected'] for hop in report['hops']))
        for session in (self.session, middle):
            kwargs = session.connect.call_args.kwargs
            self.assertIs(kwargs['allow_agent'], True)
            self.assertIs(kwargs['look_for_keys'], False)
            self.assertEqual(kwargs['timeout'], 30)
            self.assertEqual(kwargs['banner_timeout'], 30)
            self.assertEqual(kwargs['auth_timeout'], 30)
            self.assertFalse(kwargs['ssh_config'])
        self.session.close.assert_called_once_with(strict=True)

    def test_runtime_mismatch_rejected(self):
        with patch.dict(sys.modules, {'sshscript': SimpleNamespace(__version__='5.0.0', Session=Mock())}), \
                patch.object(runner, 'version', return_value='4.0.2'):
            with self.assertRaises(ops.ConfigError):
                runner.load_runtime()

    def test_descriptor_mismatch_rejected(self):
        descriptor = self.directory / 'recipe.yaml'
        descriptor.write_text(descriptor.read_text().replace('schema_version: 0.2.0', 'schema_version: 9.0.0'))
        with self.assertRaises(ops.ConfigError):
            self.run_recipe()
        self.session_class.assert_not_called()

    def test_repeated_runs_preserve_results(self):
        _, first = self.run_recipe()
        original = first.read_bytes()
        self.session.exec_command.side_effect = runner_outputs()
        _, second = self.run_recipe()
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
