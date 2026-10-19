"""Readable content names and bounded collector provenance; synthetic records only."""
import copy
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import collection_evidence as evidence
import retention_store as store
import vault_content as content
import host_vault as vault
import observation_store as exchange
from opsfeast import ConfigError
import test_host_vault as fixtures
from test_result_data import raw

DETAILS = runpy.run_path(str(ROOT/'recipes/system/inventory/overview/details.py'))


def producer():
    report = raw()
    report['access'] = {'mode': 'root', 'login_identity': {'username': 'operator', 'effective_uid': 1000},
                        'actual_identity': {'username': 'root', 'effective_uid': 0},
                        'password': 'NEVER-RETAIN'}
    report['collection_process'] = {'probes': [{
        'section': 'network', 'field': 'interfaces', 'command': 'ip -j address show',
        'status': 'failed', 'reason_code': 'producer_marker_missing',
        'observed_at': '2026-10-19T01:02:03Z', 'stdout': 'NEVER-RETAIN', 'stderr': 'NEVER-RETAIN'}]}
    return report


class EvidenceTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp
    enable = fixtures.VaultTests.enable

    def record(self):
        self.enable()
        report = producer()
        report['collection_evidence'] = evidence.capture(report)
        receipt = store.retain(self.root, report)
        self.assertEqual(receipt['status'], 'stored')
        return store.show(self.root, receipt['record_id']), report

    def test_latest_name_uses_current_prefix_and_plain_consumer_title(self):
        record, _ = self.record()
        record['recipe_reference'] = 'system/inventory/overview'
        name = content.latest_filename(record)
        self.assertEqual(name, 'current-system-inventory.md')
        self.assertNotIn('%', name)
        record['recipe_reference'] = 'company:system/inventory/overview'
        self.assertEqual(content.latest_filename(record), name)
        self.assertEqual(content.page_title(record), 'System inventory')

    def test_history_name_uses_compact_utc_seconds_without_identifiers(self):
        record, _ = self.record()
        record['observed_at'] = '2026-10-19T23:59:59.123456+00:00'
        name = content.history_filename(record)
        self.assertEqual(name, '20261019235959-system-inventory.md')
        same = copy.deepcopy(record)
        same['record_id'] += '-other'
        self.assertEqual(content.history_filename(same), name)
        same['observed_at'] = '2026-10-20T00:00:00.000000+00:00'
        self.assertLess(name, content.history_filename(same))

    def test_names_are_safe_and_bounded_for_unusual_titles(self):
        record, _ = self.record()
        for title in ('../../README', 'NUL', '標題'*100, 'x'*500):
            with patch.object(content, 'page_title', return_value=title):
                name = content.history_filename(record)
                self.assertNotIn('/', name)
                self.assertNotIn('..', name)
                self.assertLess(len(name.encode()), 255)

    def test_capture_keeps_verified_actor_and_sources_without_secrets_or_output(self):
        report = producer()
        before = copy.deepcopy(report)
        captured = evidence.capture(report)
        self.assertEqual(captured['actor'], {'username': 'root', 'effective_uid': 0, 'mode': 'root'})
        self.assertIn('ip -j address show', json.dumps(captured))
        self.assertNotIn('NEVER-RETAIN', json.dumps(captured))
        self.assertNotIn('operator', json.dumps(captured))
        self.assertEqual(report, before)

    def test_retained_envelope_has_evidence_but_legacy_exchange_keeps_data_contract(self):
        record, report = self.record()
        self.assertEqual(record['collection_evidence'], report['collection_evidence'])
        self.assertNotIn('collection_evidence', record['data'])
        self.assertNotIn('collection_process', record['data'])
        exported = exchange.export(self.root)
        self.assertNotIn('collection_evidence', exported['records'][0])
        self.assertEqual(store.retain(self.root, report)['status'], 'already_stored')

    def test_render_explains_account_commands_and_missing_data_reason(self):
        record, _ = self.record()
        text = content.render_observation(record)
        self.assertIn('| Account | root |', text)
        self.assertIn('| Effective UID | 0 |', text)
        self.assertIn('ip -j address show', text)
        self.assertIn('producer_marker_missing', text)
        self.assertIn('extended query coverage is separate', text)
        self.assertIn('Not available does not mean', text)
        self.assertNotIn('NEVER-RETAIN', text)

    def test_old_records_do_not_guess_username_or_invent_commands(self):
        record, _ = self.record()
        record.pop('collection_evidence')
        record['data']['collection_scope'] = {'mode': 'root', 'effective_uid': 0}
        text = content.render_observation(record)
        self.assertIn('| Account | Not recorded |', text)
        self.assertIn('| Effective UID | 0 |', text)
        self.assertIn('not retained for this observation', text)
        self.assertNotIn('ip -j address show', text)

    def test_bad_evidence_fails_validation(self):
        original = evidence.capture(producer())
        variants = []
        for mutation in (
            lambda v: v['actor'].update(username='bad\naccount'),
            lambda v: v['actor'].update(effective_uid=True),
            lambda v: v['actor'].update(effective_uid=1000),
            lambda v: v['actor'].update(password='NEVER-RETAIN'),
            lambda v: v['probes'][0].update(status='invented'),
            lambda v: v['probes'][0].update(exitcode=True),
            lambda v: v['probes'][0].update(observed_at='not-a-time'),
            lambda v: v.update(probes=original['probes']*257),
        ):
            value = copy.deepcopy(original)
            mutation(value)
            variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ConfigError):
                evidence.validate(value)

    def test_rebuild_renames_only_generated_pages_and_keeps_human_notes(self):
        record, _ = self.record()
        latest = self.root/'vault/hosts/production/node/records'
        expected = latest/content.latest_filename(record)
        self.assertTrue(expected.exists())
        old = 'hosts/node/records/system%2Finventory%2Foverview.md'
        with vault.locked(self.root):
            vault.publish(self.root, 'bundled-retention', {old: 'old generated layout'})
        note = latest/'human-note.md'
        note.write_text('Human notes')
        vault.rebuild(self.root)
        self.assertFalse((self.root/'vault'/old).exists())
        self.assertTrue(expected.exists())
        self.assertEqual(note.read_text(), 'Human notes')

    def test_name_collision_is_explicit_instead_of_overwriting_a_source(self):
        first, _ = self.record()
        second = copy.deepcopy(first)
        second['record_id'] += '-other'
        second['recipe_reference'] = 'other:system/inventory/overview'
        second['observed_at'] = '2026-10-14T00:00:00.000000+00:00'
        with patch.object(content, 'query', return_value={'records': [first, second]}),                 patch.object(content, 'latest_filename', return_value='collision.md'):
            with self.assertRaisesRegex(ConfigError, 'filename collision'):
                content.build(self.root, SimpleNamespace(hosts={}))


class ProbeFramingTests(unittest.TestCase):
    def collect(self, response):
        report = {'observations': {field: {'value': 'synthetic'} for field in DETAILS['FIELDS']['system'][:7]}}
        session = Mock()
        session.exec_command.side_effect = response if isinstance(response, Exception) else lambda *a, **k: SimpleNamespace(stdout=response, exitcode=0)
        DETAILS['collect'](session, report, 'linux', 2)
        return report

    def test_crlf_console_results_parse_like_lf_results(self):
        payload = '[{"ifname":"eth0","addr_info":[{"local":"192.0.2.7","prefixlen":24}]}]'
        for newline in ('\n', '\r\n'):
            report = self.collect(payload + newline + '__OPSFEAST_EXIT_0' + newline)
            self.assertEqual(report['inventory']['network']['interfaces'][0]['address'], '192.0.2.7')
            probe = next(p for p in report['collection_process']['probes'] if p['field'] == 'interfaces')
            self.assertEqual(probe['status'], 'success')

    def test_missing_marker_is_reported_without_fabricating_data(self):
        report = self.collect('output without marker')
        self.assertIsNone(report['inventory']['network']['interfaces'])
        self.assertEqual(report['collection_process']['probes'][0]['reason_code'], 'producer_marker_missing')

    def test_nonzero_exit_and_parser_errors_have_distinct_reasons(self):
        for output, reason in (('\n__OPSFEAST_EXIT_127\n', 'command_not_found'),
                               ('\n__OPSFEAST_EXIT_126\n', 'command_not_executable'),
                               ('\n__OPSFEAST_EXIT_1\n', 'command_failed'),
                               ('not-json\n__OPSFEAST_EXIT_0\n', 'parse_failed')):
            report = self.collect(output)
            probe = next(p for p in report['collection_process']['probes'] if p['field'] == 'interfaces')
            self.assertEqual(probe['reason_code'], reason)

    def test_raw_byte_limit_is_checked_before_crlf_normalization(self):
        report = self.collect('\r\n' * (DETAILS['MAX_OUTPUT']//2) + '\r\n__OPSFEAST_EXIT_0\r\n')
        self.assertEqual(report['collection_process']['probes'][0]['reason_code'], 'output_limit')
        self.assertIsNone(report['inventory']['network']['interfaces'])


if __name__ == '__main__':
    unittest.main()
