"""Explicit targets, command receipts and concise Vault pages over synthetic runs."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from opsfeast import ConfigError
import observation_runs as runs
import retention_store as store
import retention_consumers as consumers
import host_vault as vault
import test_host_vault as fixtures
import test_inventory_jobs as job_fixtures

REF='system/inventory/overview'


class ObservationPresentationTests(unittest.TestCase):
    setUp=fixtures.VaultTests.setUp
    enable=fixtures.VaultTests.enable
    acquire=job_fixtures.InventoryJobTests.acquire

    def completed(self, selection=None, result=None):
        with patch.object(runs,'now',return_value='2026-10-21T01:00:00.000000+00:00'):
            run_id=runs.start(self.root,[{'host_id':'node'}],REF,selection=selection)
        runs.record_result(self.root,run_id,'node',result or {'status':'success'})
        with patch.object(runs,'now',return_value='2026-10-21T01:00:30.000000+00:00'):
            runs.finish(self.root,run_id)
        return run_id

    def page(self):
        return next(p for p in (self.root/'vault/Observations').glob('*.md') if p.name!='SUMMARY.md').read_text()

    def test_original_selectors_and_exclusions_are_preserved_independently_of_members(self):
        self.enable()
        for selection,expected in (
            ({'kind':'cli','all':True,'selectors':[],'exclude':['spare']},'--all --exclude spare'),
            ({'kind':'cli','all':False,'selectors':[['group','g1'],['group','g2']],'exclude':[]},'--group g1 g2'),
            ({'kind':'cli','all':False,'selectors':[['host','ca1'],['host','ca2']],'exclude':[]},'--host ca1 ca2'),
            ({'kind':'cli','all':False,'selectors':[['host','ca1'],['group','g1'],['host','ca2']],'exclude':[]},'--host ca1 --group g1 --host ca2'),
            ({'kind':'scheduled','all':False,'selectors':[['host','ca1']],'exclude':[]},'Scheduled hosts: ca1')):
            with self.subTest(selection=selection):
                run_id=self.completed(selection)
                self.assertEqual(runs.show(self.root,run_id)['selection'],selection)
                self.assertEqual(runs.selection_text(selection),expected)
        self.assertEqual(runs.selection_text(None),'Not recorded')
        for invalid in ({'kind':'cli'}, {'kind':'cli','all':True,'selectors':[['host','node']],'exclude':[]},
                        {'kind':'scheduled','all':True,'selectors':[],'exclude':[]}):
            with self.assertRaises(ConfigError):runs.validate_selection(invalid)

    def test_metadata_precedes_contents_and_duration_is_whole_seconds(self):
        self.enable()
        selection={'kind':'cli','all':False,'selectors':[['group','g1'],['group','g2']],'exclude':[]}
        run_id=self.completed(selection)
        with patch.object(runs,'now',return_value='2026-10-21T01:00:30.999999+00:00'):
            runs.record_execution(self.root,run_id,0,'success')
        vault.rebuild(self.root)
        page=self.page()
        self.assertIn('Status: success',page)
        self.assertIn('Duration: 30 seconds',page)
        self.assertIn('Targets: --group g1 g2',page)
        for label in ('Status:','Trigger:','Targets:','Recipe:','Started:','Completed:','Duration:'):
            self.assertLess(page.index(label),page.index('## Contents'))
        self.assertIn('| Host | Status | Collection jobs |',page)
        self.assertNotIn('| Retention |',page)
        self.assertNotIn('Source report',page)
        index=(self.root/'vault/Observations/SUMMARY.md').read_text()
        self.assertIn('| Started | Status | Targets |',index)
        self.assertIn('| success | --group g1 g2 |',index)

    def test_one_second_duration_uses_singular_unit(self):
        self.enable()
        run_id=self.completed()
        saved=runs.show(self.root,run_id)
        from vault_content import run_pages
        saved['completed_at']='2026-10-21T01:00:01.999999+00:00'
        with patch.object(runs,'list_runs',return_value=[saved]):
            pages=run_pages(self.root,None,{},[])
        self.assertIn('Duration: 1 second\n',pages['Observations/20261021010000.md'])

    def test_attention_critical_does_not_fail_successful_command_and_host_links_to_report(self):
        import re
        from urllib.parse import unquote
        self.enable()
        result=self.acquire(job_fixtures.Actor(),save=True,properties=['storage.filesystems.used_percent'],
            cli_values={'attention':{'thresholds':{'filesystem_used_percent':{'warning':70,'critical':80}}}})
        saved=runs.show(self.root,result['observation_run_id'])
        self.assertEqual(saved['execution']['exit_code'],0)
        self.assertEqual(saved['targets'][0]['attention']['findings'][0]['severity'],'critical')
        page=self.page()
        self.assertIn('Status: success',page)
        link=re.search(r'\[[^\]]*node\]\(([^)]+/reports/[^)]+)\)',page).group(1)
        self.assertTrue((self.root/'vault/Observations'/unquote(link)).is_file())
        self.assertNotIn('[Report](',page)
        self.assertEqual(saved['selection']['selectors'],[['host','node']])

    def test_storage_failure_is_explicit_without_a_retention_column_or_report_link(self):
        self.enable()
        run_id=self.completed(result={'status':'success','retention':{'status':'failed'}})
        runs.record_execution(self.root,run_id,1,'success')
        vault.rebuild(self.root)
        page=self.page()
        self.assertIn('Status: failure',page)
        self.assertIn('Data storage failed for node.',page)
        self.assertNotIn('/reports/',page)
        self.assertNotIn('| Retention |',page)
        self.assertEqual(runs.show(self.root,run_id)['status'],'success')

    def test_publication_failure_corrects_outcome_without_rewriting_collection_or_findings(self):
        self.enable()
        run_id=self.completed()
        before=copy.deepcopy(runs.show(self.root,run_id))
        with patch.object(store,'refresh_content',return_value={'status':'failed'}):
            code,content=runs.publish_execution(self.root,run_id,0,{'status':'success'})
        self.assertEqual((code,content['status']),(1,'failed'))
        saved=runs.show(self.root,run_id)
        self.assertEqual(saved['execution']['status'],'failure')
        self.assertEqual({k:v for k,v in saved.items() if k!='execution'},before)
        with store.database(runs.path_for(self.root,saved)) as connection:
            rows=connection.execute('SELECT payload FROM observation_run_executions ORDER BY sequence').fetchall()
        self.assertEqual([json.loads(row[0])['exit_code'] for row in rows],[0,1])
        vault.rebuild(self.root)
        self.assertIn('Status: failure',self.page())
        self.assertIn('Content publication failed',self.page())
        self.assertEqual(runs.show(self.root,run_id)['execution'],saved['execution'])
        with self.assertRaises(ConfigError):runs.record_execution(self.root,run_id,0,'success')

    def test_execution_receipt_and_event_are_transactional(self):
        self.enable()
        run_id=self.completed()
        before=consumers.events(self.root)
        with patch.object(consumers,'enqueue',side_effect=RuntimeError('synthetic transaction failure')):
            with self.assertRaises(RuntimeError):runs.record_execution(self.root,run_id,0,'success')
        self.assertNotIn('execution',runs.show(self.root,run_id))
        self.assertEqual(consumers.events(self.root),before)

    def test_missing_metadata_is_not_inferred_from_existing_members(self):
        self.enable()
        run_id=self.completed()
        vault.rebuild(self.root)
        page=self.page()
        self.assertIn('Targets: Not recorded',page)
        self.assertIn('Status: Not recorded',page)
        self.assertNotIn('--all',page)
        self.assertNotIn('execution',runs.show(self.root,run_id))

    def test_host_summary_is_generated_and_existing_readme_notes_are_preserved(self):
        host=self.root/'vault/hosts/production/node'
        host.mkdir(parents=True)
        notes=b'# Human notes\n\nPrivate notes remain here.\n'
        (host/'README.md').write_bytes(notes)
        self.enable()
        vault.rebuild(self.root)
        self.assertEqual((host/'README.md').read_bytes(),notes)
        self.assertIn('(records/SUMMARY.md)',(host/'SUMMARY.md').read_text())
        self.assertIn('(README.md)',(host/'SUMMARY.md').read_text())
        self.assertIn('(hosts/production/node/SUMMARY.md)',(self.root/'vault/HOSTS.md').read_text())
        self.assertIn('../../hosts/production/node/SUMMARY.md',(self.root/'vault/groups/production/node.md').read_text())
