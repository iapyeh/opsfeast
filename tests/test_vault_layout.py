"""Compact observation pages and primary-group routing, without private profiles."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import host_vault as vault
import vault_content as content
import retention_store as store
from opsfeast import Validator
import test_host_vault as fixtures
from test_result_data import raw


class VaultLayoutTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp
    enable = fixtures.VaultTests.enable

    def retain(self):
        self.enable()
        receipt = store.retain(self.root, raw())
        self.assertEqual(receipt['content_update']['status'], 'success')
        return store.show(self.root, receipt['record_id'])

    def runtime(self):
        runtime = Validator(self.root)
        runtime.load(self.root/'hosts.yaml')
        return runtime

    def test_report_name_has_only_second_timestamp_and_label(self):
        record = self.retain()
        record['observed_at'] = '2026-10-19T08:43:28.987654+00:00'
        self.assertEqual(content.history_filename(record), '20261019084328-system-inventory.md')
        self.assertNotIn(record['record_id'], content.history_filename(record))

    def test_metadata_is_one_final_section_without_success_banner(self):
        record = self.retain()
        text = content.render_observation(record)
        self.assertTrue(text.startswith('# node\n'))
        self.assertNotIn('Status: success', text)
        self.assertNotIn('# node: System inventory', text)
        self.assertNotIn('## Collection account', text)
        self.assertEqual(text.count('## Collection metadata\n'), 1)
        self.assertEqual([line for line in text.splitlines() if line.startswith('## ')][-1],
                         '## Collection metadata')
        tail = text.split('## Collection metadata', 1)[1]
        self.assertIn('| Report | System inventory |', tail)
        self.assertIn('| Account | Not recorded |', tail)
        self.assertIn('| Observed |', tail)
        self.assertIn('Identifiers and source evidence', tail)

    def test_first_membership_selects_one_host_folder(self):
        for groups in ('production', ['production', 'database'], ['database', 'production']):
            runtime = SimpleNamespace(hosts={'node': {'group': groups}})
            expected = groups if isinstance(groups, str) else groups[0]
            self.assertEqual(content.host_location(runtime, 'node'), 'hosts/'+expected+'/node')

    def test_ungrouped_archived_and_real_reserved_group_are_distinct(self):
        runtime = SimpleNamespace(hosts={'node': {}, 'member': {'group': '_ungrouped'}})
        self.assertEqual(content.host_location(runtime, 'node'), 'hosts/_ungrouped/node')
        self.assertEqual(content.host_location(runtime, 'archived'), 'hosts/_ungrouped/archived')
        self.assertEqual(content.host_location(runtime, 'member'), 'hosts/%5Fungrouped/member')
        self.assertNotIn('../', content.host_location(SimpleNamespace(hosts={'node': {'group': '../unsafe'}}), 'node'))

    def test_indexes_and_secondary_group_links_resolve_to_primary(self):
        self.enable()
        (self.root/'hosts.yaml').write_text('hosts:\n  node:\n    connection: {local: true}\n    group: [production, database]\n')
        vault.rebuild(self.root)
        host = self.root/'vault/hosts/production/node'
        self.assertTrue((host/'README.md').is_file())
        for group in ('production', 'database'):
            page = self.root/f'vault/groups/{group}/node.md'
            self.assertIn('../../hosts/production/node/SUMMARY.md', page.read_text())
        self.assertIn('(hosts/production/node/SUMMARY.md)', (self.root/'vault/HOSTS.md').read_text())
        self.assertIn('(../hosts/production/node/SUMMARY.md)', (self.root/'vault/overview/README.md').read_text())
        self.assertFalse((self.root/'vault/hosts/database/node').exists())

    def test_regrouping_moves_generated_views_without_rewriting_notes_or_retention(self):
        record = self.retain()
        old = self.root/'vault/hosts/production/node'
        (old/'README.md').write_text('Human notes at their original location')
        before = {p:p.read_bytes() for p in (self.root/'retention').rglob('*.sqlite3')}
        (self.root/'hosts.yaml').write_text('hosts:\n  node:\n    connection: {local: true}\n    group: [database, production]\n')
        vault.rebuild(self.root)
        new = self.root/'vault/hosts/database/node'
        self.assertTrue((new/'records'/content.latest_filename(record)).is_file())
        self.assertEqual(list((old/'records').glob('*.md')), [])
        self.assertEqual((old/'README.md').read_text(), 'Human notes at their original location')
        self.assertEqual(before, {p:p.read_bytes() for p in before})
        self.assertIn('../../hosts/database/node/SUMMARY.md',
                      (self.root/'vault/groups/production/node.md').read_text())

    def test_same_second_reports_use_ordinals_and_links_target_the_right_record(self):
        self.retain()
        before = {p:p.read_bytes() for p in (self.root/'vault').rglob('*.md')}
        report = raw()
        report['observations']['hostname']['value'] = 'different-node-name'
        receipt = store.retain(self.root, report)
        self.assertEqual(receipt['status'], 'stored')
        self.assertEqual(receipt['content_update']['status'], 'success')
        records = store.query(self.root)['records']
        self.assertEqual(len(records), 2)
        reports = sorted((self.root/'vault/hosts/production/node/2026/reports').glob('*.md'))
        self.assertEqual(len(reports), 2)
        self.assertEqual(reports[0].name, '20261013000010-system-inventory-2.md')
        self.assertEqual(reports[1].name, '20261013000010-system-inventory.md')
        latest = max(records, key=lambda r: (r['observed_at'], r['record_id']))
        page = (self.root/'vault/hosts/production/node/records'/content.latest_filename(latest)).read_text()
        import re
        from urllib.parse import unquote
        link = next(link for link in re.findall(r'\]\(([^)]+)\)', page) if '/reports/' in link)
        linked = self.root/'vault/hosts/production/node/records'/unquote(link)
        self.assertIn(latest['record_id'], linked.read_text())
        first_names = {p.name: p.read_text().split('_Last modified:')[0] for p in reports}
        vault.rebuild(self.root)
        self.assertEqual(first_names, {p.name:p.read_text().split('_Last modified:')[0] for p in reports})

    def test_summary_index_and_resolved_host_icon_preserve_human_notes(self):
        self.enable()
        (self.root/'hosts.yaml').write_text('hosts:\n  node:\n    connection: {local: true}\n    group: [production]\n    icon: 🖥\n')
        record=self.retain()
        host=self.root/'vault/hosts/production/node'
        summary=host/'records/SUMMARY.md'
        self.assertTrue(summary.exists())
        self.assertFalse((host/'records/README.md').exists())
        self.assertIn('# 🖥 node',summary.read_text())
        self.assertIn('# 🖥 node',(host/'records'/content.latest_filename(record)).read_text())
        self.assertIn('(SUMMARY.md)',(host/'README.md').read_text())
        self.assertIn('(records/SUMMARY.md)',(host/'SUMMARY.md').read_text())
        self.assertIn('(README.md)',(host/'SUMMARY.md').read_text())
        (host/'README.md').write_text('Human notes remain intact.')
        vault.rebuild(self.root)
        self.assertEqual((host/'README.md').read_text(),'Human notes remain intact.')

    def test_operation_intent_and_result_keep_distinct_journal_paths(self):
        record = self.retain()
        record['kind'] = 'operation'
        other = copy.deepcopy(record)
        other['record_id'] += '-result'
        self.assertNotEqual(content.history_filename(record), content.history_filename(other))


if __name__ == '__main__':
    unittest.main()
