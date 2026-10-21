"""Host/report result routing, using synthetic saved evidence without host access."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import opsfeast
import recipe_reports as reports
import terminal_ui


class ObservationResultTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve()
        (self.root/'hosts.yaml').write_text('hosts: {}\n')
        self.host={'host_id':'node','status':'failed','recipe':{'id':'example'},
                   'execution_errors':[{'stage':'execution','type':'ValueError'}],
                   'data':{'unrelated':'FULL-ONLY'}}
        self.report={'report_contract':'0.1.0','status':'success','recipe':{'id':'report'},'artifacts':[]}
        for name,data in [('observations/host.json',self.host),('reports/run/result.json',self.report)]:
            path=self.root/name;path.parent.mkdir(parents=True);path.write_text(json.dumps(data))
        self.ids={r['kind']:r['short_id'] for r in reports.results(self.root)['results']}

    def invoke(self,*args):
        out,error=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(error):
            code=opsfeast.main([*args,'--root',str(self.root)])
        return code,out.getvalue(),error.getvalue()

    def host_result(self,*args):
        return self.invoke('observation','result',*args)

    def snapshot(self):
        return {p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_selected_modes_and_read_only_default_diagnosis(self):
        before=self.snapshot()
        identifier=self.ids['operation']
        code,text,error=self.host_result(identifier)
        self.assertEqual(code,0,error)
        self.assertIn('ValueError',text)
        self.assertNotIn('FULL-ONLY',text)
        code,text,_=self.host_result(identifier,'--json')
        self.assertEqual(json.loads(text)['diagnosis_version'],'0.1.0')
        code,text,_=self.host_result(identifier,'--detail')
        self.assertIn('data.unrelated: FULL-ONLY',text)
        self.assertIn('result_id: observations/host.json',text)
        for mode in (['--raw'],['--detail','--json']):
            code,text,_=self.host_result(identifier,*mode)
            self.assertEqual(code,0)
            self.assertEqual(json.loads(text),self.host)
        self.assertEqual(self.snapshot(),before)

    def test_namespaces_reject_other_kind_and_keep_global_ids(self):
        for kind,arguments in [('operation',['observation','result','--json']),
                               ('report',['recipes','results','list','--json'])]:
            code,text,_=self.invoke(*arguments)
            self.assertEqual(code,0)
            row,=json.loads(text)['results']
            self.assertEqual(row['kind'],kind)
            self.assertEqual(row['short_id'],self.ids[kind])
        code,_,error=self.host_result(self.ids['report'])
        self.assertEqual(code,1)
        self.assertIn('recipes results',error)
        code,_,error=self.invoke('recipes','results','show',self.ids['operation'])
        self.assertEqual(code,1)
        self.assertIn('observation result',error)
        self.assertEqual(self.invoke('recipes','results','show',self.ids['report'])[0],0)
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as caught:
            self.invoke('recipes','results','list','--host','node')
        self.assertEqual(caught.exception.code,2)

    def test_filters_invalid_files_and_empty_history(self):
        (self.root/'reports/run/result.json').write_text('{')
        code,text,_=self.host_result('--host','node','--recipe-id','example','--status','failed','--json')
        self.assertEqual(code,0) # Invalid report is outside the host namespace.
        self.assertEqual(len(json.loads(text)['results']),1)
        self.assertEqual(self.invoke('recipes','results','list','--json')[0],1)
        code,text,_=self.host_result('--status','success','--detail')
        self.assertEqual(code,0)
        self.assertIn('No saved results.',text)
        (self.root/'observations/bad.json').write_text('{')
        code,text,_=self.host_result('--detail')
        self.assertEqual(code,1)
        self.assertIn('invalid result',text)
        self.assertIn('host_id: node',text)

    def test_html_exports_and_invalid_combinations(self):
        identifier=self.ids['operation']
        for name,args in [('index',[]),('detail',[identifier,'--detail'])]:
            output=self.root/(name+'.html')
            with patch('observation_results.prepare',side_effect=AssertionError('HTML needs no table dependency')):
                self.assertEqual(self.host_result(*args,'--html',str(output))[0],0)
            original=output.read_bytes()
            self.assertEqual(self.host_result(*args,'--html',str(output))[0],1)
            self.assertEqual(output.read_bytes(),original)
        for args in [('--raw',),(identifier,'--host','node'),('--limit','2'),
                     (identifier,'--raw','--limit','2'),(identifier,'--detail','--limit','2'),
                     (identifier,'--html',str(self.root/'bad.html')),
                     (identifier,'--raw','--html',str(self.root/'bad.html')),
                     ('../hosts.yaml',),('deadbeef',)]:
            with self.subTest(args=args):self.assertEqual(self.host_result(*args)[0],1)
        self.assertFalse((self.root/'bad.html').exists())

    def test_tui_child_forwards_new_host_result_entry(self):
        for args in [[],[self.ids['operation']],[self.ids['operation'],'--detail']]:
            command=['observation','result',*args,'--tui']
            self.assertEqual(terminal_ui.child_arguments(Path('opsfeast.py'),command),command[:-1]+['--json'])

    def test_kind_filter_preserves_short_id_collisions_across_namespaces(self):
        names=['observations/host.json','reports/run/result.json']
        keys={names[0]:'12345678a'+'0'*55,names[1]:'12345678b'+'0'*55}
        with patch.object(reports,'_result_key',side_effect=keys.__getitem__):
            for kind,suffix in [('operation','a'),('report','b')]:
                row,=reports.results(self.root,kind=kind)['results']
                self.assertEqual(row['short_id'],'12345678'+suffix)
                self.assertEqual(reports.show_result(self.root,row['short_id'],kind=kind),self.host if kind=='operation' else self.report)
            with self.assertRaises(opsfeast.ConfigError):reports.show_result(self.root,'12345678',kind='operation')
        with self.assertRaises(opsfeast.ConfigError):reports.results(self.root,kind='unknown')
