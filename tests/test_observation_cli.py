"""Read-only batch views: selection, historical membership and explicit result links."""
from contextlib import redirect_stdout,redirect_stderr
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from opsfeast import ConfigError, main as ops_main
import observation_cli as cli
import observation_runs as runs
import recipe_reports
import console_output
import inventory_jobs
import test_host_vault as fixtures


class Terminal(io.StringIO):
    def isatty(self):return True


class ObservationCLITests(unittest.TestCase):
    setUp=fixtures.VaultTests.setUp
    enable=fixtures.VaultTests.enable

    def make(self, *, start='2026-10-21T01:00:00.000000+00:00', states=('failed','partial'), finished=True, receipt=True):
        self.enable()
        with patch.object(runs,'now',return_value=start):
            identity=runs.start(self.root,[{'host_id':h,'icon':'🖥'} for h in ('node','other')],
                'system/inventory/overview',selection={'kind':'cli','all':True,'selectors':[],'exclude':[]})
        if finished:
            for host,state in zip(('node','other'),states):
                runs.record_result(self.root,identity,host,{'status':state,'reason_code':'synthetic_'+state})
            runs.finish(self.root,identity)
            if receipt:runs.record_execution(self.root,identity,1 if any(s in ('failed','partial') for s in states) else 0,'success')
        return identity

    def raw(self, identity, host='node', name='result'):
        directory=self.root/'observations';directory.mkdir(exist_ok=True)
        path=directory/(name+'.json')
        path.write_text(json.dumps({'host_id':host,'status':'failed','recipe':{'id':'inventory-system'},
                                   'observation_run_id':identity}))
        return path

    def invoke(self,*arguments,tty=True):
        out=Terminal() if tty else io.StringIO();err=io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            code=ops_main(['observation',*arguments,'--root',str(self.root)])
        return code,out.getvalue(),err.getvalue()

    def test_default_lists_newest_first_without_exposing_host_payloads(self):
        older=self.make()
        newer=self.make(start='2026-10-21T02:00:00.000000+00:00')
        view=cli.query(self.root)
        self.assertEqual([o['observation_id'] for o in view['observations']],[newer,older])
        code,out,_=self.invoke()
        self.assertEqual(code,0)
        for expected in ('id','outcome','--all',newer[:8]):self.assertIn(expected,out)
        self.assertNotIn('synthetic_failed',out)

    def test_status_without_id_selects_latest_and_keeps_full_counts(self):
        identity=self.make()
        self.raw(identity)
        view=cli.query(self.root,statuses=['failed'])
        self.assertEqual(view['observation']['observation_id'],identity)
        self.assertEqual(view['observation']['host_count'],2)
        self.assertEqual(view['observation']['counts']['partial'],1)
        self.assertEqual([h['host_id'] for h in view['hosts']],['node'])
        short=recipe_reports.results(self.root)['results'][0]['short_id']
        self.assertEqual(view['hosts'][0]['short_id'],short)
        self.assertTrue(recipe_reports.result_path(self.root,short).is_file())
        code,out,_=self.invoke('--status','failed')
        self.assertEqual(code,0)
        for expected in ('Observation: '+identity,'Showing: 1/2 (failed)','synthetic_failed',short):self.assertIn(expected,out)
        self.assertNotIn('synthetic_partial',out)

    def test_full_and_short_ids_are_fixed_batches_and_multi_status_is_union(self):
        older=self.make()
        self.make(start='2026-10-21T02:00:00.000000+00:00',states=('success','success'))
        for identity in (older,older[:8]):
            view=cli.query(self.root,identity,statuses=['failed','partial','failed'])
            self.assertEqual(view['observation']['observation_id'],older)
            self.assertEqual(len(view['hosts']),2)
            self.assertEqual(view['statuses'],['failed','partial'])
        latest=cli.query(self.root,'latest',statuses=['failed'])
        self.assertEqual(latest['hosts'],[])
        self.assertIn('No hosts match',cli.render(latest))

    def test_latest_includes_running_and_does_not_choose_an_older_matching_run(self):
        self.make()
        latest=self.make(start='2026-10-21T02:00:00.000000+00:00',finished=False)
        view=cli.query(self.root,statuses=['failed'])
        self.assertEqual(view['observation']['observation_id'],latest)
        self.assertEqual(view['observation']['execution_status'],'running')
        self.assertEqual(view['observation']['counts']['pending'],2)
        self.assertEqual(view['hosts'],[])
        self.assertIsNone(view['observation']['duration_seconds'])

    def test_raw_deletion_and_ambiguous_matches_preserve_membership_without_guessing(self):
        identity=self.make()
        first=self.raw(identity)
        self.raw(identity,name='copy')
        view=cli.query(self.root,identity)
        self.assertIsNone(view['hosts'][0]['result_id'])
        self.assertIn('Multiple raw results',view['warnings'][0])
        first.unlink()
        (self.root/'observations/copy.json').unlink()
        view=cli.query(self.root,identity)
        self.assertEqual([h['status'] for h in view['hosts']],['failed','partial'])
        self.assertTrue(all(h['result_id'] is None for h in view['hosts']))

    def test_raw_without_explicit_batch_id_is_not_linked_by_host_or_time(self):
        identity=self.make()
        self.raw('different-batch')
        view=cli.query(self.root,identity)
        self.assertIsNone(view['hosts'][0]['short_id'])

    def test_json_and_piped_output_use_view_contract_and_reads_do_not_write(self):
        identity=self.make();self.raw(identity)
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(inventory_jobs,'collect_host',side_effect=AssertionError('must not collect')):
            for arguments,tty in ((('latest','--json'),True),(('latest',),False)):
                code,out,_=self.invoke(*arguments,tty=tty)
                self.assertEqual(code,0)
                view=json.loads(out)
                self.assertEqual(view['view_version'],'0.1.0')
                self.assertEqual(view['observation']['observation_id'],identity)
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_missing_execution_metadata_is_unknown_and_invalid_raw_is_visible(self):
        identity=self.make(receipt=False)
        directory=self.root/'observations';directory.mkdir()
        (directory/'broken.json').write_text('not json')
        view=cli.query(self.root,identity)
        self.assertIsNone(view['observation']['execution_status'])
        self.assertIn('Outcome: Not recorded',cli.render(view))
        self.assertIn('invalid raw result',view['warnings'][0])

    def test_empty_list_missing_latest_and_invalid_options(self):
        code,out,_=self.invoke()
        self.assertEqual(code,0)
        self.assertIn('No saved observation',out)
        self.assertFalse((self.root/'retention').exists())
        for value in ('latest','not-an-id','aaaaaaaa',''):
            self.assertEqual(self.invoke(value)[0],1)
        with self.assertRaises(SystemExit) as exc:self.invoke('--status','failure')
        self.assertEqual(exc.exception.code,2)
        with self.assertRaises(ConfigError):cli.query(self.root,statuses=['bogus'])

    def test_uuid_prefix_collisions_extend_and_ambiguous_input_is_rejected(self):
        identity=self.make()
        base=runs.show(self.root,identity)
        first=copy.deepcopy(base);second=copy.deepcopy(base)
        first['run_id']='12345678-aaaa-4000-8000-000000000001'
        second['run_id']='12345678-bbbb-4000-8000-000000000002'
        with patch.object(runs,'list_runs',return_value=[first,second]):
            view=cli.query(self.root)
            self.assertEqual([len(r['short_id']) for r in view['observations']],[9,9])
            with self.assertRaisesRegex(ConfigError,'ambiguous'):cli.query(self.root,'12345678')
            self.assertEqual(cli.query(self.root,'12345678a')['observation']['observation_id'],first['run_id'])

    def test_storage_publication_warnings_survive_a_host_status_filter(self):
        self.enable()
        identity=runs.start(self.root,[{'host_id':'node'}],'synthetic/recipe')
        runs.record_result(self.root,identity,'node',{'status':'success','retention':{'status':'failed'}})
        runs.finish(self.root,identity)
        runs.record_execution(self.root,identity,1,'failed')
        view=cli.query(self.root,identity,statuses=['failed'])
        self.assertEqual(view['hosts'],[])
        self.assertEqual(view['observation']['counts']['success'],1)
        self.assertEqual(view['observation']['execution_status'],'failure')
        rendered=cli.render(view)
        self.assertIn('Data storage failed for node',rendered)
        self.assertIn('Content publication failed',rendered)

    def test_human_output_escapes_terminal_controls(self):
        identity=self.make()
        view=cli.query(self.root,identity)
        view['observation']['recipe_reference']='name\x1b[31m'
        view['hosts'][0]['reason_code']='reason\x1b[31m'
        rendered=cli.render(view)
        self.assertNotIn('\x1b',rendered)
        self.assertIn('\\u001b',rendered)

    def test_general_recipe_batch_persists_an_explicit_raw_association(self):
        import recipe_runner
        import retention_store
        self.enable()
        directory=self.root/'observations';directory.mkdir()
        path=directory/'general.json'
        report={'host_id':'node','status':'failed','reason_code':'synthetic',
                'recipe':{'id':'generic-example'}}
        path.write_text(json.dumps(report))
        invocation={'targets':[('host','node')],'all':False,'exclude':[],'threads':1,
                    'timeout':30,'quiet':True,'verbose':False,'vars_file':None,'assignments':[]}
        out=io.StringIO()
        with patch.object(recipe_runner,'run',return_value=(report,path)), \
                patch.object(retention_store,'refresh_content',return_value={'status':'success'}),redirect_stdout(out):
            self.assertEqual(recipe_runner.execute_hosts(self.root,'system/account/check/identity',invocation,json_output=True),1)
        identity=json.loads(out.getvalue())['observation_run_id']
        self.assertEqual(json.loads(path.read_text())['observation_run_id'],identity)
        view=cli.query(self.root,identity)
        self.assertEqual(view['hosts'][0]['result_id'],'observations/general.json')

    def test_completion_displays_shared_id_without_changing_json(self):
        identity=self.make()
        report={'observation_run_id':identity,'hosts':[{'host':'node','status':'failed'}]}
        self.assertIn('Observation ID: '+identity,console_output.execution(report))
        out=Terminal()
        with redirect_stdout(out):console_output.print_report(report,kind='execution',json_output=True)
        self.assertEqual(json.loads(out.getvalue()),report)
