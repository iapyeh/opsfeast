"""Public synthetic data/content boundaries; no network or private profile data."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import host_vault as vault
import retention_store as store
import retention_replay as replay
from opsfeast import ConfigError, main
from recipe_catalog import choose
from recipe_reports import run_report
import test_host_vault as fixtures


class RetentionContentTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp
    enable = fixtures.VaultTests.enable

    def sample(self, reference='alpha:check/value', host='node', time='2026-10-19T00:00:00Z', value=0, status='success'):
        metadata = {'id': 'check-value', 'version': '1', 'access_mode': 'read',
                    'retention': {'contract': 'host-values', 'version': '0.2.0',
                                  'description': 'Synthetic scalar; no health assessment.',
                                  'fields': {'value': {'type': 'integer', 'unit': 'items', 'description': 'Observed count'}}}}
        report = {'host_id': host, 'status': status, 'evidence_kind': 'ssh', 'completed_at': time,
                  'execution_access_mode': 'read', 'source_observation_id': str(uuid4()),
                  'recipe': {'id': 'check-value', 'version': '1', 'reference': reference}, 'data': {'value': value, 'secret': 'never-retain'}}
        return metadata, report

    def retain(self, **kwargs):
        metadata, report = self.sample(**kwargs)
        result = store.retain_general(self.root, report, metadata, self.root)
        return report, result

    def snapshot(self):
        return {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_new_layout_and_query_are_independent_of_vault(self):
        self.enable()
        self.retain()
        self.assertEqual(list((self.root/'vault').rglob('*.sqlite3')), [])
        self.assertTrue((self.root/'retention/hosts/node/2026/observations.sqlite3').is_file())
        import shutil
        shutil.rmtree(self.root/'vault')
        before = self.snapshot()
        selected = store.query(self.root, hosts=['node'], recipe='alpha:check/value')
        record = store.show(self.root, selected['records'][0]['record_id'])
        self.assertEqual(record['data']['observations']['value']['value'], 0)
        self.assertNotIn('never-retain', json.dumps(selected))
        self.assertEqual(self.snapshot(), before)
        vault.rebuild(self.root)
        self.assertTrue((self.root/'vault/HOSTS.md').exists())

    def test_auto_refresh_disabled_and_explicit_rebuild(self):
        self.enable()
        definition = self.root/'feast.yaml'
        definition.write_text(definition.read_text()+'vault: {auto_refresh: false}\n')
        before = (self.root/'vault/HOSTS.md').read_bytes()
        _, receipt = self.retain()
        self.assertEqual(receipt['status'], 'stored')
        self.assertEqual(receipt['content_update']['reason_code'], 'auto_refresh_disabled')
        self.assertEqual((self.root/'vault/HOSTS.md').read_bytes(), before)
        vault.rebuild(self.root)
        self.assertIn('success', (self.root/'vault/HOSTS.md').read_text())

    def test_renderer_failure_receipt_digest_and_recovery(self):
        self.enable()
        metadata, report = self.sample()
        before = replay.raw_digest(report)
        with patch('vault_content.build', side_effect=OSError('synthetic')):
            receipt = store.retain_general(self.root, report, metadata, self.root)
        self.assertEqual(receipt['status'], 'stored')
        report['content_update'] = receipt.pop('content_update')
        report['retention'] = receipt
        self.assertEqual(report['content_update']['status'], 'failed')
        self.assertEqual(before, replay.raw_digest(report))
        self.assertEqual(len(store.query(self.root)['records']), 1)
        vault.rebuild(self.root)
        self.assertEqual(store.retain_general(self.root, report, metadata, self.root)['status'], 'already_stored')

    def test_queries_separate_sources_order_years_and_preserve_partial(self):
        self.enable()
        self.retain(reference='beta:check/value', time='2027-01-01T00:00:00Z', value=None, status='partial')
        self.retain(time='2025-01-01T00:00:00Z')
        self.retain(host='other', time='2026-01-01T00:00:00Z')
        rows = store.query(self.root, hosts=['node'])['records']
        self.assertEqual([r['observed_at'][:4] for r in rows], ['2025', '2027'])
        selected = store.query(self.root, recipe='beta:check/value', since='2026-01-01T00:00:00Z', until='2028-01-01T00:00:00Z', status='partial')['records']
        self.assertEqual(len(selected), 1)
        self.assertIsNone(selected[0]['data']['observations']['value']['value'])
        self.assertEqual(store.query(self.root, recipe='check-value')['records'], [])
        with self.assertRaises(ConfigError):
            store.query(self.root, since='2028-01-01T00:00:00Z', until='2026-01-01T00:00:00Z')

    def test_query_cli_and_export_match_python_and_do_not_write(self):
        self.enable()
        self.retain()
        before = self.snapshot()
        for action in ('list', 'export'):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(['retention', action, '--root', str(self.root), '--host', 'node', '--recipe', 'alpha:check/value', '--json'])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue()), store.query(self.root, hosts=['node'], recipe='alpha:check/value'))
        self.assertEqual(self.snapshot(), before)
        record_id = store.query(self.root)['records'][0]['record_id']
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['retention', 'show', record_id, '--root', str(self.root)]), 0)
        with self.assertRaises(ConfigError):
            store.show(self.root, 'missing')

    def test_invalid_config_semantics_and_template_declarations(self):
        self.enable()
        metadata, _ = self.sample()
        for edit in ('template', 'description', 'field_description', 'type'):
            bad = copy.deepcopy(metadata)
            if edit == 'template':
                bad['retention']['markdown_template'] = 'view.md'
            elif edit == 'description':
                bad['retention'].pop('description')
            elif edit == 'field_description':
                bad['retention']['fields']['value'].pop('description')
            else:
                bad['retention']['fields']['value']['type'] = 'object'
            with self.subTest(edit=edit), self.assertRaises(ConfigError):
                store.validate_retention(bad)
        for value in ('false', None, 0):
            with self.subTest(value=value), self.assertRaises(ConfigError):
                store.validate_settings({'namespace': 'valid', 'vault': {'auto_refresh': value}})

    def test_old_layout_rejected_without_changes(self):
        self.enable()
        old = self.root/'vault/hosts/node/2026/observations.sqlite3'
        old.parent.mkdir(parents=True)
        old.write_bytes(b'preserve legacy data')
        before = self.snapshot()
        for operation in (lambda: store.query(self.root), lambda: self.retain(), lambda: vault.rebuild(self.root)):
            with self.assertRaisesRegex(ConfigError, 'old vault SQLite layout'):
                operation()
        self.assertEqual(self.snapshot(), before)

    def test_owned_outputs_replace_edits_and_preserve_other_authors(self):
        self.enable()
        with vault.locked(self.root):
            vault.publish(self.root, 'user-summary', {'custom/note.md': '# User report'})
            with self.assertRaises(ConfigError):
                vault.publish(self.root, 'other-author', {'custom/note.md': '# Other'})
        self.retain()
        manifests = [self.root/'vault'/('.content-'+owner+'.json')
                     for owner in ('structure', 'bundled-retention', 'groups')]
        paths = {name for manifest in manifests for name in json.loads(manifest.read_text())}
        self.assertIn('HOSTS.md', paths)
        self.assertIn('overview/README.md', paths)
        for name in paths:
            (self.root/'vault'/name).write_text('Editor changed generated content, including its notice')
        (self.root/'vault/README.md').write_text('Human landing notes')
        vault.rebuild(self.root)
        for manifest in manifests:
            for name, digest in json.loads(manifest.read_text()).items():
                output = self.root/'vault'/name
                self.assertTrue(output.read_text().startswith(vault.NOTICE), name)
                self.assertNotIn('Editor changed', output.read_text(), name)
                self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), digest, name)
        self.assertEqual((self.root/'vault/README.md').read_text(), 'Human landing notes')
        self.assertIn('User report', (self.root/'vault/custom/note.md').read_text())

    def test_unmanaged_notice_does_not_claim_ownership(self):
        self.enable()
        (self.root/'vault/unmanaged.md').write_text(vault.NOTICE+'Human content')
        with vault.locked(self.root), self.assertRaises(ConfigError):
            vault.publish(self.root, 'custom', {'unmanaged.md': 'Replacement'})

    def test_ownership_removes_only_own_stale_outputs(self):
        self.enable()
        with vault.locked(self.root):
            vault.publish(self.root, 'custom', {'custom/a.md': 'A', 'custom/b.md': 'B'})
            (self.root/'vault/custom/a.md').write_text('Edited generated output')
            (self.root/'vault/custom/notes.md').write_text('Notes')
            vault.publish(self.root, 'custom', {'custom/b.md': 'New B'})
        self.assertFalse((self.root/'vault/custom/a.md').exists())
        self.assertEqual((self.root/'vault/custom/notes.md').read_text(), 'Notes')

    def test_no_vault_db_writes_and_no_recipe_execution_on_rebuild(self):
        self.enable()
        self.retain()
        before = {p: p.read_bytes() for p in (self.root/'retention').rglob('*.sqlite3')}
        with patch('runpy.run_path', side_effect=AssertionError('must not execute')):
            vault.rebuild(self.root)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_old_snapshot_requires_explicit_current_definition(self):
        self.enable()
        metadata, report = self.sample()
        snapshot = replay.snapshot(metadata, self.root)
        snapshot['contract_version'] = '0.1.0'
        snapshot['markdown_template_text'] = 'old template'
        snapshot['sha256'] = replay.digest({k: v for k, v in snapshot.items() if k != 'sha256'})
        report['retention_snapshot'] = snapshot
        with self.assertRaisesRegex(ConfigError, 'incompatible retention snapshot'):
            replay.select_snapshot(report)
        directory = self.root/'definition'
        directory.mkdir()
        (directory/'recipe.yaml').write_text(json.dumps(metadata))
        self.assertEqual(replay.select_snapshot(report, directory)['contract_version'], '0.2.0')

    def test_offline_report_combines_retention_and_html_without_raw(self):
        self.enable()
        self.retain()
        self.retain(reference='beta:check/value', status='partial', value=None)
        item = choose(self.root, 'report/retention')
        self.assertIsNone(item['retention']['declaration'])
        before = {p: p.read_bytes() for p in (self.root/'retention').rglob('*.sqlite3')}
        with patch('opsfeast.load_session_class', side_effect=AssertionError('no connections')):
            report, path = run_report(self.root, item, [], values={'title': '<script>no</script>'})
        self.assertEqual(report['status'], 'success', report)
        self.assertEqual(report['data']['rows'], 2)
        self.assertEqual(len(report['retention_sources'][0]['records']), 2)
        html = (path.parent/'artifacts/retention.html').read_text()
        self.assertNotIn('<script>no</script>', html)
        self.assertIn('alpha:check/value', html)
        self.assertIn('beta:check/value', html)
        self.assertIn('partial', html)
        self.assertTrue((self.root/'vault/hosts/node/records').is_dir())
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_runner_content_failure_preserves_status_and_returns_nonzero(self):
        import run_recipe
        self.enable()
        fixtures.VaultTests.recipe(self)
        directory = self.root/'recipes/update'
        metadata = json.loads((directory/'recipe.yaml').read_text())
        metadata['retention'] = self.sample()[0]['retention']
        metadata['access_mode'] = 'read'
        (directory/'recipe.yaml').write_text(json.dumps(metadata))
        with patch('vault_content.build', side_effect=OSError('synthetic renderer failure')):
            report, path = run_recipe.run(self.root, 'node', recipe=':update', session_class=Mock(return_value=Mock()), runtime={'verification': 'synthetic-test'})
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['retention']['status'], 'stored')
        self.assertEqual(report['content_update']['status'], 'failed')
        self.assertNotIn('content_update', report['retention'])
        self.assertEqual(json.loads(path.read_text())['status'], 'success')
        with patch.object(run_recipe, 'run', return_value=(report, path)), contextlib.redirect_stdout(io.StringIO()) as out:
            code = run_recipe.main([':update', '--host', 'node', '--root', str(self.root), '--json'])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())['content_update']['status'], 'failed')
        vault.rebuild(self.root)

    def test_empty_retention_report_and_invalid_selection(self):
        self.enable()
        item = choose(self.root, 'report/retention')
        report, _ = run_report(self.root, item, [])
        self.assertEqual(report['reason_code'], 'empty_selection')
        report, _ = run_report(self.root, item, [], values={'hosts': [7]})
        self.assertEqual(report['reason_code'], 'invalid_selection')

    def test_core_reader_and_discovery_need_no_prior_conversation(self):
        self.enable()
        from opsfeast import Instance
        profile = Instance.open(self.root).profile(root=self.root)
        self.assertEqual(profile.retention.query()['records'], [])
        item = choose(self.root, 'check/port')
        declaration = item['retention']['declaration']
        self.assertEqual(declaration['version'], '0.2.0')
        self.assertIn('description', declaration['fields']['reachable'])
        self.assertIn('retention list', item['retention']['cli'])


if __name__ == '__main__':
    unittest.main()
