"""Current pages link to historical evidence; both offer navigable readable data."""
import copy
from pathlib import Path
import re
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import vault_content as content
import retention_store as store
import inventory_values
from opsfeast import ConfigError
import test_host_vault as fixtures
from test_result_data import raw


class CurrentPageTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp
    enable = fixtures.VaultTests.enable

    def retain(self, report=None):
        self.enable()
        receipt = store.retain(self.root, report or raw())
        self.assertEqual(receipt['content_update']['status'], 'success')
        return store.show(self.root, receipt['record_id'])

    def pages(self, record):
        host = self.root/'vault/hosts/production/node'
        return (host/'records'/content.latest_filename(record),
                host/record['observed_at'][:4]/'reports'/content.history_filename(record))

    def test_current_title_is_plain_and_only_history_has_metadata(self):
        record = self.retain()
        current, history = self.pages(record)
        self.assertEqual(current.name, 'current-system-inventory.md')
        self.assertIn('## Contents', current.read_text())
        self.assertNotIn('## Collection metadata', current.read_text())
        self.assertNotIn('Source identifiers', current.read_text())
        self.assertIn('## Collection metadata', history.read_text())
        self.assertIn('Source report', current.read_text())
        self.assertNotIn(record['record_id'], current.read_text())

    def test_latest_link_resolves_to_the_selected_report_across_years(self):
        self.retain()
        report = raw()
        report['finished_at'] = '2027-01-01T00:00:00Z'
        report['observations']['hostname']['value'] = 'new-observation-hostname'
        record = self.retain(report)
        current, history = self.pages(record)
        links = re.findall(r'\]\(([^)]+)\)', current.read_text())
        relative = next(link for link in links if '/reports/' in link)
        self.assertEqual((current.parent/unquote(relative)).resolve(), history.resolve())
        self.assertTrue(history.exists())
        self.assertIn('new-observation-hostname', current.read_text())

    def test_relocated_recipe_rebuild_keeps_one_current_and_all_history(self):
        old = raw()
        old['recipe']['reference'] = 'inventory/system'
        first = self.retain(old)
        new = raw()
        new['recipe']['reference'] = 'system/inventory/overview'
        new['finished_at'] = '2026-10-14T00:00:00Z'
        new['status'] = 'partial'
        new['observations']['hostname'].update(value=None, status='unavailable')
        latest = self.retain(new)
        import host_vault
        self.assertEqual(host_vault.rebuild(self.root)['status'], 'success')
        current, history = self.pages(latest)
        self.assertEqual(len(list(current.parent.glob('current-*.md'))), 1)
        self.assertIn(history.name, current.read_text())
        self.assertNotIn('| Hostname |', current.read_text())
        self.assertIn('Some data was not obtained', current.read_text())
        self.assertIn('Hostname | Not available', history.read_text())
        self.assertTrue(self.pages(first)[1].exists())
        self.assertTrue(history.exists())
        self.assertEqual(len(store.query(self.root)['records']), 2)

    def test_current_selection_is_independent_of_reference_and_input_order(self):
        first = self.retain()
        newest = copy.deepcopy(first)
        newest.update(recipe_reference='inventory/system', record_id=first['record_id']+'-new',
                      observed_at='2027-01-01T00:00:00.000000+00:00')
        for records in ([first, newest], [newest, first]):
            with patch.object(content, 'query', return_value={'records': records}):
                entries, _, _ = content.build(self.root, SimpleNamespace(hosts={}))
            pages = [body for path, body in entries.items() if path.endswith('/'+content.latest_filename(first))]
            self.assertEqual(len(pages), 1)
            self.assertIn(content.history_filename(newest), pages[0])

    def test_equal_time_selection_uses_record_id_even_after_move(self):
        first = self.retain()
        other = copy.deepcopy(first)
        other.update(recipe_reference='inventory/system', record_id=first['record_id']+'-z')
        # Isolate latest selection: historical whole-second collisions still fail normally.
        with patch.object(content, 'query', return_value={'records': [other, first]}), \
                patch.object(content, 'history_filename', side_effect=lambda r: r['record_id']+'.md'):
            entries, _, _ = content.build(self.root, SimpleNamespace(hosts={}))
        page = next(body for path, body in entries.items() if path.endswith('/'+content.latest_filename(first)))
        self.assertIn(other['record_id']+'.md', unquote(page))

    def test_independent_sources_are_not_silently_merged(self):
        first = self.retain()
        for origin, reference in (('other-origin', first['recipe_reference']),
                                  (first['origin']['namespace'], 'company:system/inventory/overview')):
            other = copy.deepcopy(first)
            other.update(record_id=first['record_id']+'-other', recipe_reference=reference,
                         observed_at='2027-01-01T00:00:00.000000+00:00')
            other['origin']['namespace'] = origin
            with patch.object(content, 'query', return_value={'records': [first, other]}):
                with self.assertRaisesRegex(ConfigError, 'latest-state filename collision'):
                    content.build(self.root, SimpleNamespace(hosts={}))

    def test_different_recipe_ids_with_same_title_still_fail(self):
        first = self.retain()
        other = copy.deepcopy(first)
        other.update(recipe_id='other-recipe', record_id=first['record_id']+'-other',
                     observed_at='2027-01-01T00:00:00.000000+00:00')
        with patch.object(content, 'query', return_value={'records': [first, other]}), \
                patch.object(content, 'page_title', return_value='Same title'):
            with self.assertRaisesRegex(ConfigError, 'latest-state filename collision'):
                content.build(self.root, SimpleNamespace(hosts={}))

    def test_every_contents_link_targets_a_unique_native_heading(self):
        record = self.retain()
        record['data']['inventory'] = inventory_values.empty()
        record['data']['inventory']['services']['services'] = []
        for current in (False, True):
            text = content.render_observation(record, current=current)
            headings = re.findall(r'^#{2,3} (.+)$', text.split('<details>', 1)[0], re.M)
            links = [unquote(link) for link in re.findall(r'\]\(#([^)]+)\)', text)]
            self.assertTrue(links)
            self.assertEqual(len(headings), len(set(headings)))
            self.assertEqual(set(links), set(headings)-{'Contents'})
            self.assertIn('Services', links)
            self.assertIn('Services details', links)
            self.assertNotIn('<a id=', text)
            self.assertNotIn('#vault-', text)

    def test_obsidian_heading_fragments_preserve_case_spaces_and_unicode(self):
        text = content.with_contents(['# node', '', '## Network interfaces', '',
                                      '## 網路資訊', '', '## Collection metadata', ''])
        self.assertIn('[Network interfaces](#Network%20interfaces)', text)
        self.assertIn('](#%E7%B6%B2%E8%B7%AF%E8%B3%87%E8%A8%8A)', text)
        self.assertIn('[Collection metadata](#Collection%20metadata)', text)

    def test_duplicate_heading_renaming_avoids_existing_and_contents_titles(self):
        text = content.with_contents(['# node', '', '## Contents', '', '## Services', '',
                                      '### Services details', '', '### Services', '',
                                      '### Services', ''])
        headings = re.findall(r'^#{2,3} (.+)$', text, re.M)
        self.assertEqual(len(headings), len(set(headings)))
        self.assertIn('Services details 3', headings)
        links = [unquote(link) for link in re.findall(r'\]\(#([^)]+)\)', text)]
        self.assertEqual(set(links), set(headings)-{'Contents'})

    def test_field_observations_removed_from_both_views(self):
        record = self.retain()
        for current in (False, True):
            text = content.render_observation(record, current=current)
            self.assertNotIn('Field observations', text)
        # Original observation states and source times remain in the retained record.
        self.assertEqual(record, store.show(self.root, record['record_id']))

    def test_empty_inventory_section_says_no_data_without_field_dump(self):
        record = self.retain()
        record['data']['inventory'] = inventory_values.empty()
        for current in (False, True):
            text = content.render_observation(record, current=current)
            if current:
                self.assertNotIn('## Network\n', text)
            else:
                network = text.split('## Network\n', 1)[1].split('## ', 1)[0]
                self.assertIn('No data was collected for this section.', network)
                self.assertNotIn('| Interfaces |', network)

    def test_missing_collection_and_successful_empty_collection_differ(self):
        record = self.retain()
        record['data']['inventory'] = inventory_values.empty()
        record['data']['inventory']['network'].update(
            interfaces=None, routes=[], dns_servers=[{'address': '192.0.2.53'}])
        text = content.render_observation(record, current=True)
        self.assertNotIn('### Interfaces', text)
        self.assertIn('### Routes\n\nNo entries reported.', text)
        self.assertIn('192.0.2.53', text)

    def test_system_display_uses_same_record_observations_without_old_value_fill(self):
        record = self.retain()
        record['data']['inventory'] = inventory_values.empty()
        record['data']['inventory']['system']['hostname'] = 'contradictory-nested-value'
        record['data']['observations']['hostname'].update(value=None, status='unavailable')
        original = copy.deepcopy(record)
        text = content.render_observation(record, current=True)
        self.assertNotIn('| Hostname |', text)
        self.assertNotIn('contradictory-nested-value', text)
        self.assertEqual(record, original)

    def test_generic_all_missing_is_no_data_while_zero_false_are_values(self):
        record = self.retain()
        record['data'] = {'status': 'partial', 'observations': {
            'reachable': {'value': None, 'status': 'unavailable', 'unit': '', 'description': 'Reachability'}}}
        self.assertIn('No collected values are available', content.render_observation(record, current=True))
        record['data']['observations']['reachable'].update(value=False, status='success')
        record['data']['observations']['count'] = {'value': 0, 'status': 'success', 'unit': 'items', 'description': 'Count'}
        text = content.render_observation(record, current=True)
        self.assertIn('| Reachable | No | success |', text)
        self.assertIn('| Count | 0 items | success |', text)


if __name__ == '__main__':
    unittest.main()
