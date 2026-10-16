"""Human local-time policy with synthetic saved results; no remote execution."""
import contextlib
import io
import json
import os
import runpy
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import console_output as console
import display_time as display
import landing_ui
import recipe_browser
import recipe_cli
import recipe_reports


@contextlib.contextmanager
def timezone(zone):
    try:
        with patch.dict(os.environ, {'TZ': zone}):
            time.tzset()
            yield
    finally:
        time.tzset()


@unittest.skipUnless(hasattr(time, 'tzset'), 'requires OS timezone switching')
class DisplayTimeTests(unittest.TestCase):
    def test_portable_report_html_uses_local_seconds_but_json_preserves_times(self):
        source = '2026-10-14T20:34:56.987654Z'
        recipe = Path(__file__).resolve().parents[1] / 'recipes/report/summary/main.py'
        execute = runpy.run_path(str(recipe))['execute']
        document = {'host_id': 'synthetic', 'status': 'success', 'recipe': {'id': 'synthetic'},
                    'started_at': source, 'completed_at': source, 'data': {'observed_at': source}}
        with tempfile.TemporaryDirectory() as folder, timezone('Asia/Taipei'):
            root = Path(folder)
            context = SimpleNamespace(inputs=[document], vars={'title': 'Synthetic'}, artifact_dir=root)
            result = execute(context=context, timeout=5)
            self.assertEqual(result['status'], 'success')
            html = (root / 'summary.html').read_text()
            self.assertIn('2026-10-15 04:34:56', html)
            self.assertNotIn('.987654', html)
            raw = json.loads((root / 'summary.json').read_text())
            self.assertEqual(raw['rows'][0]['observed_from'], source)
            self.assertEqual(raw['rows'][0]['data']['observed_at'], source)

    def test_local_seconds_dst_offsets_and_no_invented_timezone(self):
        for zone, source, expected in (
            ('Asia/Taipei', '2026-10-14T20:34:56.987654Z', '2026-10-15 04:34:56'),
            ('Asia/Kolkata', '2026-10-14T02:00:00+00:00', '2026-10-14 07:30:00'),
            ('UTC', '2026-10-14T12:00:00.123+08:00', '2026-10-14 04:00:00'),
            ('America/New_York', '2026-01-14T02:00:00Z', '2026-01-13 21:00:00'),
            ('America/New_York', '2026-07-14T02:00:00Z', '2026-07-13 22:00:00')):
            with self.subTest(zone=zone), timezone(zone):
                self.assertEqual(display.format_time(source), expected)
        for source in (None, 0, 1.25, True, '', '001', 'not-a-time',
                       '2026-10-14', '2026-10-14T02:00:00', '2026-99-14T02:00:00Z'):
            self.assertEqual(display.format_time(source), source)

    def test_nested_table_vertical_and_home_preserve_original_values(self):
        source = '2026-10-14T20:34:56.987654Z'
        data = {'observed_at': source, 'nested': [{'completed_at': source}], 'seconds': 1.25}
        original = json.dumps(data)
        with timezone('Asia/Taipei'):
            for output in (console.details(data), console.vertical(data),
                           console.table(['time'], [[source]])):
                self.assertIn('2026-10-15 04:34:56', output)
                self.assertNotIn('.987654', output)
            converted = display.human_times(data)
            self.assertEqual(converted['nested'][0]['completed_at'], '2026-10-15 04:34:56')
            self.assertEqual(converted['seconds'], 1.25)
            with patch('checkout_info.information', return_value={'version': 'synthetic', 'downloaded_at': source}):
                self.assertIn('Downloaded: 2026-10-15 04:34:56', landing_ui.overview())
        self.assertEqual(json.dumps(data), original)

    def test_results_list_detail_html_and_original_json(self):
        class Terminal(io.StringIO):
            def isatty(self): return True
        source = '2026-10-14T20:34:56.987654Z'
        document = {'host_id': 'synthetic', 'status': 'success', 'started_at': source,
                    'completed_at': source, 'recipe': {'id': 'inventory-system',
                    'source_name': 'repository', 'reference': 'inventory/system'}}
        with tempfile.TemporaryDirectory() as folder, timezone('Asia/Taipei'):
            root = Path(folder)
            path = root / 'observations' / 'synthetic.json'
            path.parent.mkdir()
            original = json.dumps(document)
            path.write_text(original)
            def invoke(arguments, tty):
                output = Terminal() if tty else io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = recipe_cli.main(['results', *arguments, '--root', str(root)])
                self.assertEqual(code, 0)
                return output.getvalue()
            for tty in (True, False):
                for arguments in (['list'], ['detail'], ['detail', 'observations/synthetic.json']):
                    output = invoke(arguments, tty)
                    self.assertIn('2026-10-15 04:34:56', output)
                    self.assertNotIn('.987654', output)
                self.assertEqual(json.loads(invoke(['show', 'observations/synthetic.json'], tty)), document)
                for action in ('list', 'detail'):
                    indexed = json.loads(invoke([action, '--json'], tty))
                    self.assertEqual(indexed['results'][0]['completed_at'], source)
                self.assertEqual(json.loads(invoke(['detail', 'observations/synthetic.json', '--json'], tty)), document)
            for action in ('list', 'show'):
                exported = root / (action + '.html')
                arguments = [action, 'observations/synthetic.json'] if action == 'show' else [action]
                invoke([*arguments, '--html', str(exported)], False)
                self.assertIn('2026-10-15 04:34:56', exported.read_text())
                self.assertNotIn('.987654', exported.read_text())
            view = recipe_browser.execution_output(root, 'observations/synthetic.json',
                {'source': 'repository', 'reference': 'inventory/system'})
            self.assertIn('2026-10-15 04:34:56', view['details'])
            self.assertEqual(view['original'], original)
            self.assertEqual(path.read_text(), original)
            self.assertEqual(recipe_reports.results(root)['results'][0]['completed_at'], source)


if __name__ == '__main__':
    unittest.main()
