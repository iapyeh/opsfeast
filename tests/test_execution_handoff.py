"""Readable completion entrypoints over real synthetic retention/Vault; no network."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import console_output as console
import host_vault as vault
import retention_store as store
import test_host_vault as fixtures
from opsfeast import ConfigError


class Terminal(io.StringIO):
    def isatty(self):
        return True


class HandoffTests(unittest.TestCase):
    def setUp(self):
        fixtures.VaultTests.setUp(self)
        fixtures.VaultTests.enable(self)
        metadata = {'id': 'service-check', 'version': '1', 'access_mode': 'read',
            'retention': {'contract': 'host-values', 'version': '0.2.0', 'description': 'Synthetic service state.',
                'fields': {'state': {'type': 'string', 'unit': '', 'description': 'Observed state.'}}}}
        raw = {'host_id': 'node', 'status': 'success', 'reason_code': 'checked', 'message': 'Synthetic check.',
            'evidence_kind': 'local', 'completed_at': '2026-10-24T00:00:00.000000+00:00',
            'execution_access_mode': 'read', 'source_observation_id': str(uuid4()),
            'recipe': {'id': metadata['id'], 'version': '1', 'reference': ':service/check/health'},
            'data': {'state': 'ready'}}
        receipt = store.retain_general(self.root, raw, metadata, self.root)
        vault.rebuild(self.root)
        folder = self.root/'observations'; folder.mkdir()
        self.path = folder/'synthetic.json'; self.path.write_text(json.dumps(raw))
        self.report = dict(raw, host='node', result_path=str(self.path), retention=receipt,
            content_update={'status': 'success', 'consumers': [{'consumer': 'vault', 'source': 'builtin:vault', 'status': 'success'}]})
        self.locations = vault.result_locations(self.root, host='node', record_id=receipt['record_id'])

    def test_single_host_completion_links_actual_saved_and_current_results(self):
        before = copy.deepcopy(self.report)
        out = Terminal()
        with contextlib.redirect_stdout(out):
            console.print_report(self.report, kind='execution', result_root=self.root)
        text = out.getvalue()
        self.assertIn('Raw JSON: '+str(self.path), text)
        self.assertIn('Vault current (latest state): '+self.locations['current'], text)
        self.assertIn('result id', text)
        self.assertEqual(self.report, before)
        self.assertIn('publication succeeded; result root unavailable', console.execution_locations(self.report))
        mixed = copy.deepcopy(self.report)
        mixed['content_update']['status'] = 'failed'
        mixed['content_update']['consumers'].append({'consumer': 'other', 'source': 'local:consumers/other', 'status': 'failed'})
        self.assertIn(self.locations['current'], console.execution_locations(mixed, self.root))
        self.assertEqual(console.execution_result(mixed)['status'], 'failed')

    def test_failed_or_disabled_publication_does_not_link_stale_pages(self):
        for receipt in ({'status': 'failed'}, {'status': 'skipped'}, {'status': 'success', 'consumers': []}):
            report = dict(self.report, content_update=receipt)
            out = Terminal()
            with contextlib.redirect_stdout(out), patch.object(vault, 'result_locations', side_effect=AssertionError('stale lookup forbidden')):
                console.print_report(report, kind='execution', result_root=self.root)
            self.assertNotIn(self.locations['current'], out.getvalue())
            self.assertIn('Raw JSON:', out.getvalue())
            self.assertIn('for this run', out.getvalue())

    def test_json_and_pipe_remain_original_structured_reports(self):
        for stream, forced in ((Terminal(), True), (io.StringIO(), False)):
            with contextlib.redirect_stdout(stream), patch.object(vault, 'result_locations', side_effect=AssertionError('no display lookup')):
                console.print_report(self.report, kind='execution', result_root=self.root, json_output=forced)
            self.assertEqual(json.loads(stream.getvalue()), self.report)

    def test_batch_uses_shared_index_and_raw_directory(self):
        report = {'hosts': [self.report, dict(self.report, host='node-two')]}
        out = Terminal()
        with contextlib.redirect_stdout(out):
            console.print_report(report, kind='execution', result_root=self.root)
        self.assertIn('Raw results directory: '+str(self.path.parent), out.getvalue())
        self.assertIn('Vault index: '+self.locations['index'], out.getvalue())
        self.assertNotIn('Vault current', out.getvalue())

    def test_locator_is_read_only_and_missing_pages_are_not_invented(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(vault.result_locations(self.root, host='node', record_id=self.report['retention']['record_id']), self.locations)
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        Path(self.locations['current']).unlink()
        located = vault.result_locations(self.root, host='node', record_id=self.report['retention']['record_id'])
        self.assertNotIn('current', located)
        self.assertTrue(Path(located['host']).is_file())
        out = console.execution_locations(self.report, self.root)
        self.assertIn('Vault host results:', out)
        self.path.unlink()
        self.assertIn('Raw JSON: saved file unavailable', console.execution_locations(self.report, self.root))
        self.assertIn('Raw JSON: not saved', console.execution_locations(dict(self.report, result_path=None), self.root))

    def test_symlink_and_unowned_files_are_not_result_entrypoints(self):
        path = Path(self.locations['current']); path.unlink()
        outside = self.root/'unmanaged.md'; outside.write_text('Human notes.')
        path.symlink_to(outside)
        with self.assertRaises(ConfigError):
            vault.result_locations(self.root, host='node', record_id=self.report['retention']['record_id'])
        self.assertIn('entrypoint unavailable', console.execution_locations(self.report, self.root))
        path.unlink(); path.write_text('Unowned content.')
        manifest = self.root/'vault/.content-bundled-retention.json'
        entries = json.loads(manifest.read_text()); entries.pop(path.relative_to(self.root/'vault').as_posix()); manifest.write_text(json.dumps(entries))
        self.assertNotIn('current', vault.result_locations(self.root, host='node', record_id=self.report['retention']['record_id']))


if __name__ == '__main__':
    unittest.main()
