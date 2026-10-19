"""Terminal-cell width limits with synthetic records and offline recipe metadata."""
from contextlib import redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from wcwidth import wcswidth

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import console_output as console
import access_check
import opsfeast


class Terminal(io.StringIO):
    def isatty(self):
        return True


class ConsoleWidthTests(unittest.TestCase):
    def render(self, width, headers, rows):
        with patch.object(sys.stdout, 'isatty', return_value=True), \
                patch.object(console.shutil, 'get_terminal_size', return_value=os.terminal_size((width, 24))):
            result = console.table(headers, rows)
        for line in result.splitlines():
            self.assertLessEqual(wcswidth(line), width, repr(line))
        return result

    def test_actual_recipe_show_fits_multiple_terminal_widths_without_execution(self):
        for width in (40, 80, 120):
            with self.subTest(width=width):
                output = Terminal()
                with redirect_stdout(output), \
                        patch.object(console.shutil, 'get_terminal_size', return_value=os.terminal_size((width, 24))), \
                        patch('opsfeast.load_session_class', side_effect=AssertionError('no host execution')), \
                        patch('recipe_cli.execute', side_effect=AssertionError('no recipe execution')):
                    code = opsfeast.main(['recipes', 'show', 'system/inventory/overview', '--checkout-only'])
                self.assertEqual(code, 0)
                text = output.getvalue()
                self.assertIn('inventory', text)
                self.assertIn('consumers', text)
                for line in text.splitlines():
                    self.assertLessEqual(wcswidth(line), width, repr(line))

    def test_long_unicode_identifier_is_complete_and_original_data_unchanged(self):
        token = '中文🚀e\u0301' * 25 + '001' * 35
        rows = [[token]]
        original = copy.deepcopy(rows)
        text = self.render(40, ['identifier'], rows)
        data_lines = text.split('├', 1)[1].splitlines()[1:-1]
        reconstructed = ''.join(line.split('│')[1].strip() for line in data_lines)
        self.assertEqual(reconstructed, token)
        self.assertEqual(rows, original)
        self.assertNotIn('…', text)

    def test_long_headers_and_escaped_controls_wrap(self):
        text = self.render(40, ['long_header_' * 8, 'value'],
                           [['001', 'line\n\x1b[31m' + 'x' * 90]])
        self.assertIn('001', text)
        self.assertNotIn('\x1b', text)
        self.assertIn('long_header_', text)
        # Displayed control escapes can cross a wrap boundary, but remain complete.
        compact = ''.join(line.split('│')[-2].strip() for line in text.splitlines() if line.startswith('│'))
        self.assertIn(r'line\n\u001b[31m', compact)

    def test_many_columns_switch_to_labeled_records_without_losing_values(self):
        headers = ['column_' + str(i) for i in range(10)]
        rows = [['value_' + str(i) for i in range(10)], ['other_' + str(i) for i in range(10)]]
        text = self.render(40, headers, rows)
        self.assertIn('Record 1', text)
        self.assertIn('Record 2', text)
        for row in rows:
            for header, value in zip(headers, row):
                self.assertIn(header + ': ' + value, text)

    def test_very_narrow_terminal_still_preserves_wide_characters(self):
        text = self.render(2, ['欄'], [['中文🚀001']])
        self.assertNotIn('╭', text)
        self.assertEqual(text.count('中'), 1)
        self.assertEqual(text.count('文'), 1)
        self.assertEqual(text.count('🚀'), 1)

    def test_empty_tables_and_short_rows_remain_renderable(self):
        self.render(40, ['long_header' * 10, 'second'], [])
        self.render(20, ['field', 'value'], [['only one cell']])
        self.assertEqual(self.render(40, [], []), '')

    def test_width_is_recomputed_and_wide_terminal_keeps_existing_layout(self):
        rows = [['001', 'x' * 100]]
        narrow = self.render(40, ['id', 'value'], rows)
        wide = self.render(180, ['id', 'value'], rows)
        expected = console.table_formatter()(rows, headers=['id', 'value'], tablefmt='rounded_outline',
                                             disable_numparse=True, preserve_whitespace=True)
        self.assertEqual(wide, expected)
        self.assertGreater(len(narrow.splitlines()), len(wide.splitlines()))

    def test_redirected_tables_keep_existing_format_without_width_lookup(self):
        rows = [['001', '中文' * 60]]
        with patch.object(sys.stdout, 'isatty', return_value=False), \
                patch.object(console.shutil, 'get_terminal_size', side_effect=AssertionError('no width lookup')):
            text = console.table(['id', 'value'], rows)
        expected = console.table_formatter()(rows, headers=['id', 'value'], tablefmt='rounded_outline',
                                             disable_numparse=True, preserve_whitespace=True)
        self.assertEqual(text, expected)

    def test_check_access_uses_same_width_policy_without_changing_evidence(self):
        report = {'hosts': [{'host': 'long-synthetic-host-name', 'user': '0002', 'status': 'failed',
                             'reason_code': 'connection_failed'}]}
        original = copy.deepcopy(report)
        with patch.object(sys.stdout, 'isatty', return_value=True), \
                patch.object(console.shutil, 'get_terminal_size', return_value=os.terminal_size((40, 24))):
            text = access_check.format_summary(report)
        for line in text.splitlines()[:-1]:  # The separate host-count footer is prose.
            self.assertLessEqual(wcswidth(line), 40)
        self.assertIn('FAIL', text)
        self.assertIn('connection_failed', text)
        self.assertIn('0002', text)
        self.assertIn('1 failed', text)
        self.assertEqual(report, original)

    def test_json_bypasses_width_and_table_dependencies(self):
        data = {'id': '001', 'text': '中文\n' * 100}
        output = Terminal()
        with redirect_stdout(output), \
                patch.object(console.shutil, 'get_terminal_size', side_effect=AssertionError('no width lookup')), \
                patch.object(console, 'table_formatter', side_effect=AssertionError('no table dependency')):
            console.print_report(data, json_output=True)
        self.assertEqual(json.loads(output.getvalue()), data)


if __name__ == '__main__':
    unittest.main()
