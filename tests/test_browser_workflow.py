"""Offline hybrid workflow contracts. All DOM, Sessions and Profiles are synthetic."""
import contextlib
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from opsfeast import ConfigError
from opsfeast import browser_steps as browser
from opsfeast.bot_usd import parse_bot_usd_table, select_monthly_usd_quote, QuoteError
from opsfeast.browser_command_workflow import run
from opsfeast.workflow import WorkflowContext
from opsfeast.operation_guard import OperationGuard, inspect as inspect_guard

HTML = '''<table><thead><tr><th rowspan="2">掛牌日期</th><th rowspan="2">幣別</th><th colspan="2">現金匯率</th><th colspan="2">即期匯率</th></tr><tr><th>本行買入</th><th>本行賣出</th><th>本行買入</th><th>本行賣出</th></tr></thead><tbody><tr><td>2032/04/16</td><td>美金 (USD)</td><td>20.01</td><td>40.01</td><td>30.01</td><td>31.250</td></tr></tbody></table>'''


def snapshot():
    return dict(table_html=HTML, range_text='2032/04/01 ~ 2032/04/20', complete=True,
                pagination_complete=True, captured_at='2032-04-20T03:00:00+00:00', request_id='synthetic', snapshot_sha256='a' * 64)


def select(value, month):
    return select_monthly_usd_quote(parse_bot_usd_table(value), month)


class BrowserWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.events = []
        self.receipt = SimpleNamespace(exitcode=0, stdout='synthetic receipt', stderr='')
        @contextlib.contextmanager
        def connect():
            self.events.append('connect')
            try:
                yield SimpleNamespace(exec_command=self.command)
            finally:
                self.events.append('cleanup')
        self.context = WorkflowContext(root=self.root, host_id='synthetic-host', reference=':synthetic/monthly',
            variables={'target_month': '2032-04'}, run_id='synthetic-run', code_directory=self.root,
            connector=connect, progress=lambda message: self.events.append(message))

    def command(self, argv, **kwargs):
        # Durable uncertain intent MUST exist when the fake command starts.
        journal = next((self.root / '.operation-guards').glob('*.json'))
        self.assertEqual(browser.read(journal)['state'], 'outcome_unknown')
        self.events.append(('command', argv, kwargs))
        return self.receipt

    def invoke(self, repeat_receipt=None, *, command_completion_is_success=False):
        return run(self.context, target_host='synthetic-host', purpose='synthetic-invoice',
                   url='https://example.test/table', select_quote=select,
                   build_argv=lambda quote: ['/opt/reviewed', '--usd-rate', quote['sell_rate']],
                   repeat_receipt=repeat_receipt, command_completion_is_success=command_completion_is_success)

    def test_parser_uses_spot_selling_and_skips_absent_fifteenth(self):
        self.assertEqual(select(snapshot(), '2032-04')['sell_rate'], '31.25')
        self.assertEqual(select(snapshot(), '2032-04')['selected_date'], '2032-04-16')
        for change, reason in [({'table_html': HTML.replace('即期匯率', '未知')}, 'schema_changed'),
                               ({'complete': False}, 'coverage_incomplete'),
                               ({'range_text': '2032/04/16 ~ 2032/04/20'}, 'coverage_incomplete'),
                               ({'table_html': HTML.replace('31.250', '-')}, 'invalid_rate'),
                               ({'table_html': HTML + HTML}, 'schema_changed')]:
            with self.subTest(change=change), self.assertRaisesRegex(QuoteError, reason):
                select(dict(snapshot(), **change), '2032-04')

    def test_observed_hidden_header_structure_keeps_all_six_semantic_columns(self):
        html = (Path(__file__).parent / 'fixtures/bot-usd-hidden-headers.html').read_text()
        value = dict(snapshot(), table_html=html)
        table = parse_bot_usd_table(value)
        self.assertEqual(len(table['rows']), 2)
        self.assertEqual(table['rows'][1]['cash_sell'], '40.01')
        self.assertEqual(table['rows'][1]['spot_buy'], '30.01')
        self.assertEqual(select(value, '2032-04')['sell_rate'], '31.25')
        self.assertEqual(select(value, '2032-04')['selected_date'], '2032-04-16')

    def test_unknown_or_contradictory_hidden_headers_fail_closed(self):
        html = (Path(__file__).parent / 'fixtures/bot-usd-hidden-headers.html').read_text()
        variants = [
            html.replace('class="noscript"', 'class="unknown"'),
            html.replace('class="rowSP_Ctrl_2_2_2 hasscript"', 'class="hasscript"'),
            html.replace('class="noscript" rowspan="2">掛牌日期', 'class="noscript" rowspan="2">日期'),
            html.replace('<th class="hidden"></th>', '<th class="hidden">Unexpected</th>', 1),
            html.replace('<th class="hidden"></th>', '<th class="hidden" colspan="2"></th>', 1),
            html.replace('<th class="hidden"></th>', '<th class="hidden"></th><th class="hidden"></th>', 1),
            html.replace('class="rate-content-cash print_table-cell" colspan="2"', 'class="hidden" colspan="2"'),
            html.replace('<td>2032/04/16</td>', '<td>2032/04/16</td><td class="hidden"></td>'),
            HTML.replace('colspan="2">即期匯率', 'class="hidden" colspan="2">即期匯率'),
        ]
        for value in variants:
            with self.subTest(value=value[:80]), self.assertRaisesRegex(QuoteError, 'schema_changed'):
                parse_bot_usd_table(dict(snapshot(), table_html=value))

    def test_reference_vectors(self):
        fixture = json.loads((Path(__file__).resolve().parents[1] / 'docs/examples/recipe-flow/quote-cases.json').read_text())
        for case in fixture['cases']:
            with self.subTest(case=case['id']):
                table = deepcopy(fixture['base_table']); table.update(case.get('table_overrides', {}))
                month = case.get('target_month', fixture['target_month'])
                expected = case['expected']
                if 'error' in expected:
                    with self.assertRaisesRegex(QuoteError, expected['error']):
                        select_monthly_usd_quote(table, month)
                else:
                    self.assertEqual(select_monthly_usd_quote(table, month), expected['quote'])

    def test_order_argv_completion_and_duplicate_block(self):
        def acquire(*args, **kwargs):
            self.events.append('browser'); return snapshot()
        with patch('opsfeast.browser_steps.acquire', side_effect=acquire):
            result = self.invoke()
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(result['data']['mail_delivery'], 'unknown')
            self.assertLess(self.events.index('browser'), self.events.index('connect'))
            command = next(item for item in self.events if isinstance(item, tuple))
            self.assertEqual(command[1], ['/opt/reviewed', '--usd-rate', '31.25'])
            self.assertEqual(command[2], {'check': False, 'command_timeout': 300})
            self.assertEqual(self.invoke()['status'], 'failed')
            self.assertEqual(self.events.count('connect'), 1)

    def test_river_dispatch_uses_same_selected_session_and_guard(self):
        from unittest.mock import Mock
        self.context.river=Mock()
        self.context.river.execute.side_effect=lambda session,argv,timeout:self.command(argv,command_timeout=timeout)
        with patch('opsfeast.browser_steps.acquire',return_value=snapshot()):
            result=self.invoke()
        self.assertEqual(result['status'],'partial')
        self.context.river.execute.assert_called_once()
        self.assertEqual(self.context.river.execute.call_args.args[1],['/opt/reviewed','--usd-rate','31.25'])
        self.assertEqual(self.events.count('connect'),1)

    def test_command_only_scope_uses_remote_exit_code_as_recipe_outcome(self):
        from recipe_runner import execution_exit_code

        with patch('opsfeast.browser_steps.acquire', return_value=snapshot()):
            result = self.invoke(command_completion_is_success=True)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['reason_code'], 'command_completed')
            self.assertEqual(result['data']['command']['exitcode'], 0)
            self.assertEqual(execution_exit_code([result]), 0)
            self.assertNotIn('business_outcome', result['data'])
            self.assertNotIn('mail_delivery', result['data'])
            self.assertEqual(self.invoke(command_completion_is_success=True)['status'], 'failed')

    def test_command_only_scope_still_fails_on_a_nonzero_remote_exit_code(self):
        from recipe_runner import execution_exit_code

        self.receipt.exitcode = 7
        with patch('opsfeast.browser_steps.acquire', return_value=snapshot()):
            result = self.invoke(command_completion_is_success=True)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason_code'], 'command_failed')
        self.assertEqual(result['data']['command']['exitcode'], 7)
        self.assertEqual(execution_exit_code([result]), 1)

    def test_failure_before_selection_has_no_connection(self):
        with patch('opsfeast.browser_steps.acquire', side_effect=browser.BrowserStepError('browser_provider_timeout')):
            self.assertEqual(self.invoke()['data']['execution'], 'failed_before_dispatch')
        self.assertNotIn('connect', self.events)
        # A separately invoked retry after a pre-dispatch failure can obtain a new guard.
        with patch('opsfeast.browser_steps.acquire', return_value=snapshot()):
            self.assertEqual(self.invoke()['status'], 'partial')

    def test_wrong_host_and_invalid_month_never_request_browser(self):
        for host, month in [('wrong-host', '2032-04'), ('synthetic-host', '2032-13')]:
            self.context.host_id=host; self.context.vars['target_month']=month
            with patch('opsfeast.browser_steps.acquire') as acquire:
                self.assertEqual(self.invoke()['status'], 'failed'); acquire.assert_not_called()
        self.assertNotIn('connect', self.events)

    def test_timeout_after_dispatch_blocks_repeat(self):
        with patch('opsfeast.browser_steps.acquire', return_value=snapshot()), patch.object(self, 'command', side_effect=TimeoutError()):
            self.assertEqual(self.invoke()['data']['execution'], 'outcome_unknown')
            self.assertEqual(self.invoke()['status'], 'failed')
        self.assertEqual(self.events.count('connect'), 1)
        self.assertIn('cleanup', self.events)

    def test_context_cannot_connect_after_close_or_reenter(self):
        with self.context.connect():
            with self.assertRaises(ConfigError):
                with self.context.connect(): pass
        self.context.close_scope()
        with self.assertRaises(ConfigError):
            with self.context.connect(): pass

    def test_bound_immutable_response_and_real_wait(self):
        request = browser.create(self.root, run_id='synthetic', reference=':synthetic', host_id='synthetic-host',
            url='https://example.test/table', target_month='2032-04', wait_seconds=2)
        response = dict(schema_version='0.1.0', request_id=request['request_id'], request_sha256=browser.digest(request),
            provider_id='synthetic-browser/1', captured_at=browser.utc().isoformat(), url=request['url'],
            table_html=HTML, range_text='2032/04/01 ~ 2032/04/20', complete=True, pagination_complete=True)
        for change in [{'request_sha256':'bad'}, {'url':'https://other.test/'}, {'complete':False},
                       {'captured_at':(browser.utc()-timedelta(days=1)).isoformat()}]:
            with self.subTest(change=change), self.assertRaises(browser.BrowserStepError):
                browser.respond(self.root, request['request_id'], dict(response, **change))
        browser.respond(self.root, request['request_id'], response)
        with self.assertRaises(browser.BrowserStepError): browser.respond(self.root, request['request_id'], response)
        with patch('opsfeast.browser_steps.create', return_value=request):
            actual = browser.acquire(self.context, url=request['url'], target_month='2032-04', wait_seconds=2)
        self.assertEqual(actual['snapshot_sha256'], browser.digest(response))
        with self.assertRaises(browser.BrowserStepError): browser.respond(self.root, request['request_id'], response)

    def test_progress_recording_failure_closes_browser_request_without_waiting(self):
        with patch.object(self.context,'progress',side_effect=OSError('synthetic river failure')):
            with self.assertRaises(OSError):
                browser.acquire(self.context,url='https://example.test/table',target_month='2032-04',wait_seconds=1)
        terminal=next((self.root/'.browser-steps').glob('*/terminal.json'))
        self.assertEqual(browser.read(terminal)['status'],'closed')
        self.assertNotIn('connect',self.events)

    def test_guard_fences_previous_owner(self):
        key = {'purpose':'synthetic', 'host':'synthetic', 'month':'2032-04'}
        first = OperationGuard(self.root, key=key, run_id='first')
        first.update('failed_before_dispatch')
        second = OperationGuard(self.root, key=key, run_id='second')
        with self.assertRaises(ConfigError): first.update('outcome_unknown')
        second.update('outcome_unknown')
        with self.assertRaises(ConfigError): OperationGuard(self.root, key=key, run_id='third')

    def test_completed_workflow_requires_explicit_receipt_and_archives_original(self):
        key = {'purpose': 'synthetic-invoice', 'host': 'synthetic-host', 'month': '2032-04'}
        first = OperationGuard(self.root, key=key, run_id='earlier')
        first.update('command_completed', command={'exitcode': 0})
        original = first.path.read_bytes()
        warning = inspect_guard(self.root, key)
        self.assertEqual(warning['state'], 'repeat_confirmation_required')
        self.assertEqual(warning['previous_completed']['run_id'], 'earlier')
        with patch.object(browser, 'acquire', return_value=snapshot()) as acquire:
            self.assertIn('operation_repeat_confirmation_required', self.invoke()['message'])
            self.assertIn('operation_repeat_receipt_changed', self.invoke('a' * 64)['message'])
            acquire.assert_not_called()
            result = self.invoke(warning['receipt'])
            self.assertEqual(result['data']['repeat_of']['run_id'], 'earlier')
            self.assertEqual(result['reason_code'], 'command_completed_business_outcome_unverified')
            self.assertIn('operation_repeat_receipt_changed', self.invoke(warning['receipt'])['message'])
            acquire.assert_called_once()
        archived = first.path.with_name(first.path.stem + '-' + first.nonce + '.json')
        self.assertEqual(archived.read_bytes(), original)

    def test_repeat_confirmation_is_exclusive_and_required_again_after_early_failure(self):
        from concurrent.futures import ThreadPoolExecutor
        key = {'purpose': 'synthetic', 'host': 'fixture', 'month': '2032-04'}
        self.assertEqual(inspect_guard(self.root, key)['state'], 'available')
        self.assertFalse((self.root / '.operation-guards').exists())
        first = OperationGuard(self.root, key=key, run_id='earlier')
        first.update('command_completed')
        receipt = inspect_guard(self.root, key)['receipt']

        def reserve(index):
            try:
                return OperationGuard(self.root, key=key, run_id=str(index), repeat_receipt=receipt)
            except ConfigError:
                return None

        with ThreadPoolExecutor(max_workers=2) as workers:
            (winner,) = [guard for guard in workers.map(reserve, range(2)) if guard is not None]
        self.assertEqual(inspect_guard(self.root, key)['state'], 'blocked')
        winner.update('failed_before_dispatch')
        self.assertEqual(inspect_guard(self.root, key)['previous_completed']['run_id'], 'earlier')
        self.assertIsNone(reserve('replay'))
        with self.assertRaisesRegex(ConfigError, 'repeat_confirmation_required'):
            OperationGuard(self.root, key=key, run_id='no-confirmation')

    def test_uncertain_dispatch_stays_blocked_even_with_a_receipt(self):
        key = {'purpose': 'synthetic', 'host': 'fixture', 'month': '2032-04'}
        first = OperationGuard(self.root, key=key, run_id='earlier')
        first.update('outcome_unknown')
        self.assertEqual(inspect_guard(self.root, key)['state'], 'blocked')
        with self.assertRaisesRegex(ConfigError, 'operation_already_reserved'):
            OperationGuard(self.root, key=key, run_id='repeat', repeat_receipt=browser.digest(browser.read(first.path)))


if __name__ == '__main__': unittest.main()
