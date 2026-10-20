"""Readable retained views, synthetic content safety and rebuild invariants."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import vault_content as content
import retention_store as store
import host_vault as vault
import test_host_vault as fixtures
from test_result_data import raw


class VaultReadabilityTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp
    enable = fixtures.VaultTests.enable

    def record(self):
        self.enable()
        receipt = store.retain(self.root, raw())
        self.assertEqual(receipt['status'], 'stored')
        return store.query(self.root)['records'][0]

    def test_origin_is_labeled_and_identifiers_follow_readable_content(self):
        record = self.record()
        text = content.render_observation(record)
        self.assertIn('| Source | example-production / node |', text)
        self.assertNotIn("Origin: {", text)
        self.assertIn('<summary>Identifiers and source evidence</summary>', text)
        main, details = text.split('<details>', 1)
        self.assertNotIn(record['record_id'], main)
        self.assertIn(record['record_id'], details)
        for key, value in record['origin'].items():
            self.assertIn(content.label(key), details)
            self.assertIn(content.text(value), details)

    def test_inventory_all_sections_are_tables_not_json(self):
        record = self.record()
        sample = json.loads((Path(content.__file__).resolve().parents[1] /
                             'recipes/system/inventory/overview/examples/result.partitioned.synthetic.json').read_text())
        record['data']['inventory'] = sample['inventory']
        record['data']['observations']['system_version']['value'] = 'retained-system-version'
        original = copy.deepcopy(record)
        text = content.render_observation(record)
        for section in sample['inventory']:
            self.assertIn('## ' + content.label(section), text)
        self.assertIn('| Name | Address | Prefix Length | MTU |', text)
        self.assertIn('192.0.2.10', text)
        self.assertIn('8 GiB (8,589,934,592 bytes)', text)
        self.assertIn('retained-system-version', text)
        self.assertIn('Not available', text)
        self.assertIn('No entries reported', text)
        self.assertNotIn(chr(96) * 3 + 'json', text)
        self.assertEqual(record, original)

    def test_partial_and_identity_warning_remain_visible(self):
        record = self.record()
        record['data']['status'] = 'partial'
        record['data']['identity_warning'] = 'Fallback cannot establish host replacement.'
        record['data']['observations']['system_version']['value'] = None
        record['data']['observations']['system_version']['status'] = 'unavailable'
        text = content.render_observation(record)
        main = text.split('<details>')[0]
        self.assertIn('| Observation status | partial |', main)
        self.assertIn('Fallback cannot establish host replacement.', main)
        self.assertIn('older observations are not used', main)
        self.assertIn('unavailable', main)

    def test_units_keep_zero_false_empty_and_exact_base_values(self):
        self.assertEqual(content.value_text(None), 'Not available')
        self.assertEqual(content.value_text(False), 'No')
        self.assertEqual(content.value_text(0), '0')
        self.assertEqual(content.value_text(''), '(empty string)')
        self.assertIn('(0 bytes)', content.value_text(0, 'size_bytes'))
        self.assertEqual(content.value_text(90061.5, 'uptime_seconds'),
                         '1d 1h 1m 1s (90,061.5 seconds)')
        self.assertIn('(1,024 KiB)', content.value_text(1024, 'total_kib'))

    def test_generic_host_values_have_meanings_units_and_no_empty_inventory(self):
        record = self.record()
        record['data'] = {'status': 'partial', 'description': 'Synthetic reachability only.',
                          'observations': {'reachable': {'value': False, 'status': 'success',
                              'unit': '', 'description': 'Bounded connection result.',
                              'observed_at': record['observed_at']},
                              'count': {'value': 0, 'status': 'success', 'unit': 'items',
                                       'description': 'Observed count', 'observed_at': record['observed_at']}}}
        text = content.render_observation(record)
        self.assertIn('| Reachable | No | success |', text)
        self.assertIn('| Count | 0 | success | items | Observed count |', text)
        self.assertNotIn('## Inventory', text)
        self.assertNotIn(chr(96) * 3 + 'json', text)

    def test_nested_lists_and_extra_fields_are_not_dropped(self):
        lines = '\n'.join(content.dataset_lines({'custom': {'items': [
            {'name': 'a', 'nested': {'enabled': False}, 'addresses': ['192.0.2.1', '2001:db8::1']},
            {'name': 'b', 'count': 0}]}}))
        self.assertIn('Nested / Enabled', lines)
        self.assertIn('Addresses', lines)
        self.assertIn('192.0.2.1, 2001:db8::1', lines)
        self.assertIn('Not available', lines)
        self.assertIn('No', lines)
        self.assertIn('0', lines)

    def test_markup_and_fence_injection_are_escaped_everywhere(self):
        record = self.record()
        attack = '<script>alert(1)</script> | [click](https://example.invalid)\n' + chr(96) * 3
        record['origin']['host_id'] = attack
        record['data']['inventory'] = {'network': {'interfaces': [{'name': attack}]}}
        record['data']['identity_warning'] = attack
        text = content.render_observation(record)
        self.assertNotIn('<script>', text)
        self.assertNotIn('[click]', text)
        self.assertNotIn(chr(96) * 3, text)
        self.assertIn('&lt;script&gt;', text)
        self.assertIn('&#124;', text)

    def test_coverage_states_and_full_provenance_are_preserved(self):
        record = self.record()
        record['data']['collection_scope'] = {'mode': 'login_fallback', 'truncated': True,
                                               'omitted_sections': ['packages']}
        record['retention_provenance'] = {'snapshot_sha256': 'a' * 64}
        text = content.render_observation(record)
        self.assertIn('### Collection scope', text)
        self.assertIn('login_fallback', text)
        self.assertIn('Truncated', text)
        self.assertIn('packages', text)
        self.assertIn('a' * 64, text)
        self.assertNotIn('Field observations', text)

    def test_rebuild_updates_history_and_latest_preserving_data_and_human_notes(self):
        self.record()
        note = self.root / 'vault/hosts/production/node/README.md'
        note.write_text('Human notes remain intact.')
        before = {p.relative_to(self.root): p.read_bytes() for p in (self.root/'retention').rglob('*.sqlite3')}
        with patch('opsfeast.load_session_class', side_effect=AssertionError('no host operation')):
            vault.rebuild(self.root)
        pages = [p for p in (self.root/'vault/hosts/production/node').rglob('*.md') if p.name not in ('README.md', 'SUMMARY.md')]
        self.assertTrue(any('reports' in p.parts for p in pages))
        self.assertTrue(any('records' in p.parts for p in pages))
        for page in pages:
            if 'reports' in page.parts:
                self.assertIn('Identifiers and source evidence', page.read_text())
            else:
                self.assertNotIn('Collection metadata', page.read_text())
                self.assertIn('Source report', page.read_text())
            self.assertNotIn('Origin: {', page.read_text())
        after = {p.relative_to(self.root): p.read_bytes() for p in (self.root/'retention').rglob('*.sqlite3')}
        self.assertEqual(before, after)
        self.assertEqual(note.read_text(), 'Human notes remain intact.')


if __name__ == '__main__':
    unittest.main()
