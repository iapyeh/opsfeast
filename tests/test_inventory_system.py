"""Synthetic inventory and runner regressions; never contact SSH hosts."""
from inventory_fixture import BUNDLE, COLLECTOR
from recipe_test_support import recipe_main
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
import recipe_runner as runner
import opsfeast as ops
import host_runtime as hr
C = COLLECTOR


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
