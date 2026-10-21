"""Focused saved-result diagnosis without connections, mutation or AI inference."""
from contextlib import redirect_stdout,redirect_stderr
import copy
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import recipe_cli
import recipe_reports
import result_diagnostics as diagnostics
import test_inventory_jobs as fixtures
from inventory_output_fixture import framed


class DiagnosisTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        (self.root/'hosts.yaml').write_text('hosts: {node: {connection: {local: true}}}\n')
        (self.root/'observations').mkdir()
        self.path=self.root/'observations/result.json'

    def save(self,**values):
        raw={'host_id':'node','status':'failed','reason_code':'collection_failed',
             'recipe':{'id':'inventory-system'},'probes':[],'execution_errors':[],'groups':[]}
        raw.update(values);self.path.write_text(json.dumps(raw))
        return recipe_reports.results(self.root)['results'][0]['short_id']

    def invoke(self,*arguments):
        out=io.StringIO();err=io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            code=recipe_cli.main(['results',*arguments,'--root',str(self.root)])
        return code,out.getvalue(),err.getvalue()

    def test_outer_error_is_prioritized_and_acquisition_duplicates_and_payload_are_omitted(self):
        identifier=self.save(execution_errors=[{'stage':'collection','error_type':'KeyError','reason_code':'collection_failed'}],
            probes=[{'id':'acquisition','command':None,'status':'failed','reason_code':'collection_failed'}],
            data={'large_irrelevant_payload':'not-for-diagnosis'*10000})
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        code,out,_=self.invoke('diagnose',identifier)
        self.assertEqual(code,0)
        self.assertIn('Problems: 1;',out)
        self.assertIn('collection / KeyError / collection_failed',out)
        self.assertIn('cannot be recovered',out)
        self.assertNotIn('not-for-diagnosis',out)
        self.assertLess(len(out),1000)
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_failed_probes_show_relevant_bounded_streams_and_skip_successful_output(self):
        identifier=self.save(status='partial',probes=[
            {'id':'ok','command':'successful','status':'success','stdout':'DO-NOT-DISPLAY'},
            {'id':'bad','command':'df -Pk','status':'failed','reason_code':'command_failed','exitcode':1,
             'stdout':'\n'.join('output '+str(i) for i in range(1000)),
             'stderr':'permission denied\n\x1b[31mtext\n','stdout_truncated':True},
            {'id':'unsupported','status':'not_supported'},
            {'id':'budget','command':'not started','status':'not_attempted','reason_code':'total_budget_exhausted'}])
        code,out,_=self.invoke('diagnose',identifier)
        self.assertEqual(code,0)
        for expected in ('df -Pk','exitcode: 1','permission denied','output 0','unsupported/not attempted probes: 1','truncated'):
            self.assertIn(expected,out)
        self.assertIn('total_budget_exhausted',out)
        self.assertNotIn('DO-NOT-DISPLAY',out)
        self.assertNotIn('output 4',out)
        self.assertNotIn('\x1b',out)

    def test_limit_and_json_report_omissions_and_keep_stored_status(self):
        identifier=self.save(probes=[{'id':str(i),'command':'probe '+str(i),'status':'failed'} for i in range(8)])
        code,out,_=self.invoke('diagnose',identifier,'--limit','2','--json')
        self.assertEqual(code,0)
        data=json.loads(out)
        self.assertEqual((data['issue_count'],data['shown_count'],data['omitted_count']),(8,2,6))
        self.assertEqual(data['status'],'failed')
        self.assertEqual(data['diagnosis_version'],'0.1.0')
        self.assertEqual(data['result_id'],'observations/result.json')

    def test_receipts_and_fallback_remain_separate_from_collection(self):
        identifier=self.save(status='success',retention={'status':'failed','error_type':'OSError'},
            content_update={'status':'failed','consumers':[{'consumer':'vault','status':'failed','error_type':'RuntimeError'}]},
            access={'degraded':True})
        data=diagnostics.diagnose(self.root,identifier)
        self.assertEqual(data['status'],'success')
        self.assertEqual([i['stage'] for i in data['issues']],['retention','content_update','content_update','access'])
        self.assertEqual(data['issues'][2]['consumer'],'vault')

    def test_sample_gaps_are_grouped_and_failed_probe_gaps_are_not_duplicated(self):
        identifier=self.save(status='partial',probes=[{'id':'failed','status':'failed','command':'bad'}],groups=[{'samples':[
            {'property':'a','source_id':'failed','status':'unavailable'},
            {'property':'b','source_id':'ok','status':'unavailable','reason_code':'invalid_property_value'},
            {'property':'b','source_id':'ok','status':'unavailable','reason_code':'invalid_property_value'},
            {'property':'c','source_id':'unsupported','status':'unavailable','reason_code':'unsupported_platform_or_probe'}]}])
        data=diagnostics.diagnose(self.root,identifier)
        self.assertEqual(data['issue_count'],2)
        self.assertEqual(data['issues'][1]['properties'],['b'])

    def test_success_and_missing_evidence_are_distinct(self):
        identifier=self.save(status='success')
        self.assertIn('No recorded failures.',diagnostics.format_diagnosis(diagnostics.diagnose(self.root,identifier)))
        identifier=self.save()
        data=diagnostics.diagnose(self.root,identifier)
        self.assertEqual(data['issue_count'],0)
        self.assertIn('No specific failure evidence',diagnostics.format_diagnosis(data))
        self.assertNotIn('No recorded failures.',diagnostics.format_diagnosis(data))

    def test_old_source_exit_codes_do_not_turn_success_into_failure(self):
        identifier=self.save(probes=None,sources=[{'id':'ok','command':['uname','-s'],'exitcode':0,'stdout':'Linux'},
            {'id':'bad','command':['df'],'exitcode':1,'stderr':'error'}])
        data=diagnostics.diagnose(self.root,identifier)
        self.assertEqual(data['issue_count'],1)
        self.assertEqual(data['issues'][0]['probe_id'],'bad')

    def test_invalid_flags_ids_and_limits_are_read_errors(self):
        identifier=self.save()
        for args in [('diagnose',),('diagnose',identifier,'--limit','0'),('diagnose',identifier,'--limit','51'),
                     ('diagnose',identifier,'--host','node'),('diagnose',identifier,'--html','new.html'),
                     ('diagnose','deadbeef'),('detail',identifier,'--limit','3')]:
            with self.subTest(args=args):self.assertEqual(self.invoke(*args)[0],1)
        self.assertFalse((self.root/'new.html').exists())


class UnsupportedProbeRegressionTests(unittest.TestCase):
    setUp=fixtures.InventoryJobTests.setUp
    enable=fixtures.InventoryJobTests.enable
    acquire=fixtures.InventoryJobTests.acquire

    def test_non_linux_full_inventory_keeps_unsupported_gaps_instead_of_keyerror(self):
        code=runpy.run_path(str(ROOT/'recipes/system/inventory/overview/jobs.py'))
        class DarwinActor(fixtures.Actor):
            def exec_command(self,argv,**options):
                if 'uname -s' in argv[-1]:
                    return SimpleNamespace(stdout=framed(argv[-1],'Darwin\n\n__OPSFEAST_EXIT_0\n'),exitcode=0)
                return super().exec_command(argv,**options)
        raw=code['collect'](DarwinActor(),'synthetic',list(code['CATALOG']['JOBS']))
        unsupported=[p for p in raw['probes'] if p['status']=='not_supported']
        self.assertTrue(unsupported)
        self.assertEqual(len(raw['groups']),11)
        for probe in unsupported:
            self.assertIn('observed_at',probe)
            self.assertEqual(probe['reason_code'],'unsupported_platform_or_probe')
        self.assertIn(raw['status'],('success','partial'))
        self.enable()
        saved=self.acquire(DarwinActor(),save=True,jobs=list(code['CATALOG']['JOBS']))
        self.assertEqual(saved['retention']['status'],'stored')
        self.assertEqual(len(saved['groups']),11)
