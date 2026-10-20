"""Synthetic policy inheritance, execution gates and explicit durable observation runs."""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from opsfeast import ConfigError, Validator, TEMPLATE
import recipe_settings as policy
import recipe_runner as runner
import inventory_attention as attention
import inventory_jobs as jobs
import inventory_cli as cli
import observation_runs as runs
import retention_store as store
import retention_consumers as consumers
import host_vault as vault
import test_host_vault as fixtures
import test_inventory_jobs as job_fixtures
Actor = job_fixtures.Actor

REF = 'system/inventory/overview'


class RecipePolicyTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp

    def config(self, data):
        (self.root/'hosts.yaml').write_text(json.dumps(data))
        config = Validator(self.root)
        config.load(self.root/'hosts.yaml')
        return config

    def test_exact_references_normalize_only_bundle_and_reject_duplicates(self):
        self.assertEqual(policy.reference('bundle:system/network/check/port'), 'system/network/check/port')
        for ref in (':system/a-b/check/c-d', 'community:system/network/check/port'):
            self.assertEqual(policy.reference(ref), ref)
        for ref in ('../x','a/../x','a//b','/x','https://example.org/x','a/*','a/./b','a:b:c'):
            with self.subTest(ref=ref), self.assertRaises(ConfigError):
                policy.reference(ref)
        with self.assertRaises(ConfigError):
            policy.normalize({REF:{}, 'bundle:'+REF:{}})

    def test_first_group_wins_per_leaf_host_wins_lists_replace(self):
        data = {'default':{'recipes':{REF:{'enabled':True,'vars':{'attention':{
            'enabled':True,'thresholds':{'filesystem_used_percent':{'warning':80,'critical':85}}}}}}},
            'groups':{'first':{'recipes':{'bundle:'+REF:{'vars':{'attention':{'thresholds':{
                'filesystem_used_percent':{'warning':70}}}}}}},
                      'second':{'recipes':{REF:{'enabled':False,'vars':{'attention':{'thresholds':{
                'filesystem_used_percent':{'warning':75,'critical':90}}}}}}}},
            'hosts':{'node':{'connection':{'local':True},'group':['first','second'],
                            'recipes':{REF:{'vars':{'attention':{'thresholds':{'filesystem_used_percent':{'critical':88}}}}}}}}}
        config=self.config(data).check()
        options=config.recipe_options('node','bundle:'+REF)
        self.assertFalse(options['enabled'])
        self.assertEqual(options['vars']['attention']['thresholds']['filesystem_used_percent'],{'warning':70,'critical':88})
        self.assertEqual(policy.merge({'x':[22,80]},{'x':[443]}),{'x':[443]})
        options['vars']['attention']['enabled']=False
        self.assertTrue(config.recipe_options('node',REF)['vars']['attention']['enabled'])

    def test_defaults_select_inherited_enabled_recipe_but_recipe_default_is_false(self):
        config=self.config({'default':{'recipes':{REF:{'enabled':True}}},'hosts':{'node':{'connection':{'local':True}}}}).check()
        self.assertEqual(len(config.selected['node']),1)
        self.assertEqual(config.recipe_options('node','system/network/check/port'),{})
        self.assertIn('system/inventory/overview:\n      enabled: true',TEMPLATE)

    def test_check_rejects_missing_reference_in_unused_group_and_wrong_vars(self):
        for extra in ({'default':{'recipes':{'missing/exact/path':{'enabled':False}}}},
                      {'groups':{'empty':{'recipes':{'missing/path':{}}}}},
                      {'default':{'recipes':{REF:{'vars':{'unknown':123}}}}},
                      {'default':{'recipes':{REF:{'vars':{'attention':False}}}}}):
            with self.subTest(extra=extra),self.assertRaises((ConfigError,OSError)):
                self.config(dict(extra,hosts={'node':{'connection':{'local':True}}})).check()

    def test_explicit_target_overrides_all_three_flags_bulk_preserves_gate(self):
        data={'recipe_sources':{'bundle':{'enabled':False}}, 'hosts':{'node':{
            'connection':{'local':True},'enabled':False,'recipes':{REF:{'enabled':False}}}}}
        self.config(data)
        config,directory,_,_=runner.preflight(self.root,'node','bundle:'+REF,explicit_host=True)
        self.assertEqual(directory,ROOT/'recipes'/REF)
        self.assertEqual(config.execution_recipe['reference'],REF)
        for expected in ('host_disabled','source_disabled','recipe_disabled'):
            self.config(data)
            config,directory,_,_=runner.preflight(self.root,'node',REF,explicit_host=False)
            self.assertIsNone(directory)
            self.assertEqual(config.execution_recipe['reason_code'],expected)
            if expected=='host_disabled':data['hosts']['node']['enabled']=True
            if expected=='source_disabled':data['recipe_sources']['bundle']['enabled']=True

    def test_explicit_target_cannot_override_disabled_jump(self):
        self.config({'hosts':{'jump':{'connection':{'hostname':'jump.invalid'},'enabled':False},
                              'node':{'connection':{'hostname':'node.invalid','via':{'host':'jump'}}}}})
        with self.assertRaises(ConfigError):
            runner.preflight(self.root,'node',REF,explicit_host=True)

    def test_attention_recipe_validates_direction_unknown_metric_and_finite_bounds(self):
        for value in ({'enabled':1},{'thresholds':{'unknown':{}}},
                      {'thresholds':{'filesystem_used_percent':{'warning':95,'critical':90}}},
                      {'thresholds':{'memory_available_percent':{'warning':5,'critical':10}}},
                      {'thresholds':{'load_5m_per_cpu':{'warning':0}}},
                      {'thresholds':{'cpu_utilization_percent':{'warning':float('nan')}}}):
            with self.subTest(value=value),self.assertRaises(ConfigError):attention.resolve(value)
        value={'thresholds':{'filesystem_used_percent':{'warning':70}}}
        result=attention.resolve(value)
        self.assertEqual(result['thresholds']['filesystem_used_percent'],{'warning':70,'critical':95})
        self.assertEqual(value,{'thresholds':{'filesystem_used_percent':{'warning':70}}})


class ObservationRunTests(unittest.TestCase):
    setUp = fixtures.VaultTests.setUp
    enable = fixtures.VaultTests.enable
    acquire = job_fixtures.InventoryJobTests.acquire

    def test_no_store_leaves_no_runs_and_no_files(self):
        self.enable()
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.acquire(Actor(),properties=['storage.filesystems.used_percent'])
        self.assertEqual(runs.list_runs(self.root),[])
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_saved_run_snapshots_findings_current_policy_can_change_and_history_cannot(self):
        self.enable()
        result=self.acquire(Actor(),save=True,properties=['storage.filesystems.used_percent'],
            cli_values={'attention':{'thresholds':{'filesystem_used_percent':{'warning':70,'critical':80}}}})
        run=runs.show(self.root,result['observation_run_id'])
        self.assertEqual(run['status'],'success')
        self.assertEqual(run['targets'][0]['attention']['findings'][0]['severity'],'critical')
        self.assertEqual(run['targets'][0]['record_id'],result['retention']['record_id'])
        folder=self.root/'vault/Observations'
        pages=[p for p in folder.glob('*.md') if p.name!='SUMMARY.md']
        self.assertEqual(len(pages),1)
        self.assertRegex(pages[0].name,r'^\d{14}\.md$')
        self.assertIn('82% used',pages[0].read_text())
        before=copy.deepcopy(run)
        actor=Actor();actor.percent=20
        self.acquire(actor,save=True,properties=['storage.filesystems.used_percent'])
        (self.root/'hosts.yaml').write_text(json.dumps({'default':{'recipes':{REF:{'vars':{'attention':{'enabled':False}}}}},
                                                     'hosts':{'node':{'connection':{'local':True}}}}))
        vault.rebuild(self.root)
        self.assertEqual(runs.show(self.root,run['run_id']),before)
        self.assertIn('82% used',pages[0].read_text())
        current=next((self.root/'vault').rglob('current-system-inventory.md')).read_text()
        self.assertNotIn('## Attention',current)
        altered=copy.deepcopy(run);altered['targets'][0]['status']='failed'
        with self.assertRaises(ConfigError),store.locked(self.root):runs._save(self.root,altered)
        self.assertEqual(store.Reader(self.root).run(run['run_id']),before)

    def test_explicit_five_targets_save_failure_skip_and_incomplete_without_guessing(self):
        self.enable()
        run_id=runs.start(self.root,[{'host_id':'node'+str(i),'icon':'🍎','jobs':[{'id':'system-runtime'}]} for i in range(5)],REF)
        for i,state in enumerate(('success','partial','failed','skipped')):
            runs.record_result(self.root,run_id,'node'+str(i),{'status':state,'reason_code':'synthetic'})
        run=runs.finish(self.root,run_id)
        self.assertEqual(run['status'],'partial')
        self.assertEqual([t['status'] for t in run['targets']],['success','partial','failed','skipped','failed'])
        self.assertEqual(run['targets'][-1]['reason_code'],'execution_did_not_complete')
        with self.assertRaises(ConfigError):runs.record_result(self.root,run_id,'node0',{'status':'success'})
        vault.rebuild(self.root)
        page=next(p for p in (self.root/'vault/Observations').glob('*.md') if p.name!='SUMMARY.md').read_text()
        self.assertNotIn('## Attention',page)
        for i in range(5):self.assertIn('node'+str(i),page)
        events=[e for _,e in consumers.events(self.root) if e['event']=='retention.run.updated']
        self.assertEqual(len(events),6)

    def test_same_second_runs_have_distinct_readable_names_and_cli_reads_without_writes(self):
        self.enable()
        stamp='2026-10-20T01:02:03.000000+00:00'
        with patch.object(runs,'now',return_value=stamp):
            for _ in range(2):
                run_id=runs.start(self.root,[{'host_id':'node'}],REF)
                runs.finish(self.root,run_id)
        vault.rebuild(self.root)
        self.assertEqual(sorted(p.name for p in (self.root/'vault/Observations').glob('*.md')),
                         ['20261020010203-2.md','20261020010203.md','SUMMARY.md'])
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        output=io.StringIO()
        with redirect_stdout(output):code=cli.main(['runs','show',run_id,'--root',str(self.root),'--json'])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(output.getvalue())['run_id'],run_id)
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_runner_batch_records_one_run_with_failed_and_skipped_targets(self):
        self.enable()
        data={'default':{'recipes':{REF:{'enabled':True}}},
              'hosts':{name:{'connection':{'local':True},'enabled':name!='disabled'}
                       for name in ('node','failed','disabled')}}
        (self.root/'hosts.yaml').write_text(json.dumps(data))
        inv={'targets':[],'all':True,'exclude':[],'threads':1,'timeout':30,'quiet':True,
             'verbose':False,'vars_file':None,'assignments':[]}
        def execute(root,host,*args,**options):
            self.assertFalse(options['explicit_host'])
            self.assertIsNotNone(options['observation_run_id'])
            if host=='failed':raise ConfigError('synthetic failure')
            result=self.acquire(Actor(),save=True,properties=['storage.filesystems.used_percent'],
                                observation_run_id=options['observation_run_id'])
            return result,Path(result['result_path'])
        with patch.object(runner,'run',side_effect=execute),redirect_stdout(io.StringIO()):
            self.assertEqual(runner.execute_hosts(self.root,REF,inv,json_output=True),1)
        saved=runs.list_runs(self.root)
        self.assertEqual(len(saved),1)
        self.assertEqual([t['status'] for t in saved[0]['targets']],['success','failed','skipped'])
        self.assertEqual(saved[0]['targets'][-1]['reason_code'],'host_disabled')

    def test_all_disabled_targets_still_have_a_batch_without_any_execution(self):
        self.enable()
        (self.root/'hosts.yaml').write_text('hosts: {node: {enabled: false, connection: {local: true}}}')
        inv={'targets':[],'all':True,'exclude':[],'threads':1,'timeout':30,'quiet':True,
             'verbose':False,'vars_file':None,'assignments':[]}
        for content_status,expected_code in (('success',0),('failed',1)):
            output=io.StringIO()
            with patch.object(runner,'run',side_effect=AssertionError('must not execute')), \
                    patch.object(store,'refresh_content',return_value={'status':content_status}),redirect_stdout(output):
                self.assertEqual(runner.execute_hosts(self.root,REF,inv,json_output=True),expected_code)
            self.assertEqual(json.loads(output.getvalue())['content_update']['status'],content_status)
        saved=runs.list_runs(self.root)
        self.assertEqual(len(saved),2)
        self.assertTrue(all(run['targets'][0]['status']=='skipped' for run in saved))

    def test_scheduler_unavailable_recipe_is_a_durable_failed_attempt(self):
        self.enable()
        reference='missing/exact/path'
        disabled_reference=':copy/unavailable'
        (self.root/'hosts.yaml').write_text(json.dumps({'recipe_sources':{'profile':{'enabled':False}},
            'default':{'recipes':{reference:{'enabled':True},disabled_reference:{'enabled':True}}},
            'hosts':{'node':{'connection':{'local':True}},'omitted':{'connection':{'local':True}}}}))
        (self.root/'inventory.yaml').write_text(json.dumps({'schema_version':'0.1.0',
            'hosts':{'node':{'enabled':True,'recipe':reference},'omitted':{'enabled':True,'recipe':disabled_reference}}}))
        with patch.object(jobs,'collect_host',side_effect=AssertionError('must not execute')):
            result=jobs.dispatch(self.root,at='2026-10-20T01:00:00+00:00')
        saved=runs.show(self.root,result['observation_run_id'])
        targets={target['host_id']:target for target in saved['targets']}
        self.assertEqual(targets['node']['recipe_reference'],reference)
        self.assertEqual(targets['node']['status'],'failed')
        self.assertEqual(targets['omitted']['recipe_reference'],disabled_reference)
        self.assertEqual(targets['omitted']['status'],'skipped')
        again=jobs.dispatch(self.root,at='2026-10-20T01:00:01+00:00')
        self.assertEqual([r['host_id'] for r in again['hosts']],['omitted'])
        self.assertIsNone(again['observation_run_id'])

    def test_run_event_transaction_rolls_back_if_enqueuing_fails(self):
        self.enable()
        with patch.object(consumers,'enqueue',side_effect=RuntimeError('synthetic event failure')):
            with self.assertRaises(RuntimeError):runs.start(self.root,[{'host_id':'node'}],REF)
        self.assertEqual(runs.list_runs(self.root),[])
        self.assertEqual(consumers.events(self.root),[])

    def test_source_report_link_and_deleted_record_are_explicit(self):
        import re
        from urllib.parse import unquote
        self.enable()
        result=self.acquire(Actor(),save=True,properties=['storage.filesystems.used_percent'])
        folder=self.root/'vault/Observations'
        page=next(p for p in folder.glob('*.md') if p.name!='SUMMARY.md')
        link=re.search(r'\[Report\]\(([^)]+)\)',page.read_text()).group(1)
        self.assertTrue((folder/unquote(link)).is_file())
        for page_path in (self.root/'vault').rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)',page_path.read_text()):
                if not target.startswith('#'):
                    self.assertTrue((page_path.parent/unquote(target)).is_file(),(page_path,target))
        record=store.show(self.root,result['retention']['record_id'])
        store.delete_observation(self.root,result['source_observation_id'])
        vault.rebuild(self.root)
        self.assertIn('Retained record no longer available',page.read_text())
        self.assertNotIn('[Report](',page.read_text())

    def test_malformed_run_is_config_error_and_empty_start_writes_nothing(self):
        self.enable()
        for value in ({},{'contract_version':'0.1.0'},[],None):
            with self.subTest(value=value),self.assertRaises(ConfigError):runs.validate(value)
        with self.assertRaises(ConfigError):runs.start(self.root,[],REF)
        self.assertEqual(runs.list_runs(self.root),[])
