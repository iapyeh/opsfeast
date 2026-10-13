"""Catalog, offline reporting, sharing and reruns with synthetic data only."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import opsfeast as ops
import recipe_cli as cli
import recipe_catalog as catalog
import recipe_reports as reports
import recipe_packages as packages
import recipe_jobs as jobs
import recipe_contract as contract
import run_recipe as runner
from recipe_inputs import parse_json_object


class RecipeExperienceTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name).resolve()
        self.root=self.base/'feast'
        self.root.mkdir()
        self.settings={'hosts':{'h':{'connection':{'local':True},'recipes':[]}}}
        self.write_config()
        self.source=ops.REPOSITORY_RECIPES/'report/summary'
        self.input=self.base/'input.json'
        self.input.write_bytes((self.source/'examples/input.synthetic.json').read_bytes())

    def write_config(self):
        (self.root/'hosts.yaml').write_text(json.dumps(self.settings))

    def invoke(self,*args):
        output,error=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(output),contextlib.redirect_stderr(error):
            code=ops.main(['recipes',*args,'--root',str(self.root)])
        return code,output.getvalue(),error.getvalue()

    def selected(self):
        return catalog.choose(self.root,'report/summary')

    def copy_report(self,relative='report/summary'):
        dest=self.root/'recipes'/relative
        shutil.copytree(self.source,dest)
        return dest

    def run_report(self):
        with patch.object(runner,'load_runtime',side_effect=AssertionError('must not load SSHScript')),patch.object(runner,'connection_plan',side_effect=AssertionError('no connections')):
            return reports.run_report(self.root,self.selected(),[self.input])

    def test_catalog_three_sources_and_disabled_missing(self):
        self.copy_report()
        external=self.base/'community'
        shutil.copytree(self.source,external/'shared-report')
        self.settings['recipe_sources']={'community':{'path':str(external)},'disabled':{'path':str(self.base/'missing'),'enabled':False}}
        self.write_config()
        data=catalog.catalog(self.root)
        self.assertEqual(data['status'],'success')
        refs=[r['reference'] for r in data['recipes']]
        self.assertIn('report/summary',refs)
        self.assertIn(':report/summary',refs)
        self.assertIn('community:shared-report',refs)
        self.assertEqual(data['sources'][-1]['status'],'disabled')
        with self.assertRaisesRegex(ops.ConfigError,'ambiguous'):
            catalog.choose(self.root,'report-summary')
        self.assertEqual(catalog.choose(self.root,':report/summary')['source'],'profile')

    def test_catalog_no_entrypoint_execution_and_input_descriptions(self):
        directory=self.copy_report()
        entry=directory/'main.py'
        entry.write_text("raise RuntimeError('never load')\n"+entry.read_text())
        item=catalog.choose(self.root,':report/summary')
        self.assertTrue(item['runnable'])
        self.assertEqual(item['kind'],'report')
        self.assertIn('title',item['inputs']['variables'])
        self.assertEqual(item['contract'],'valid-python-report')

    def test_duplicate_ids_within_source_fail_without_hiding_valid_items(self):
        self.copy_report('one')
        self.copy_report('two')
        data=catalog.catalog(self.root)
        self.assertEqual(data['status'],'failed')
        private=[item for item in data['recipes'] if item['source']=='profile']
        self.assertTrue(all(not item['runnable'] for item in private))
        self.assertTrue(catalog.choose(self.root,'check/port')['runnable'])

    def test_unavailable_source_and_escaping_descriptor(self):
        self.settings['recipe_sources']={'bad':{'path':str(self.base/'absent')}}
        self.write_config()
        data=catalog.catalog(self.root)
        self.assertEqual(data['status'],'failed')
        self.assertEqual(data['sources'][-1]['status'],'unavailable')
        directory=self.copy_report()
        descriptor=directory/'recipe.yaml'
        descriptor.unlink()
        descriptor.symlink_to(self.source/'recipe.yaml')
        self.assertFalse(catalog.choose(self.root,':report/summary')['runnable'])

    def test_catalog_filter_and_fresh_checkout(self):
        self.assertEqual([r['reference'] for r in catalog.catalog(self.root,query='plain',kind='report')['recipes']],['report/summary'])
        output=io.StringIO()
        with patch.object(cli,'resolve_root',side_effect=AssertionError('no Feast needed')),contextlib.redirect_stdout(output):
            self.assertEqual(ops.main(['recipes','list','--checkout-only','--json']),0)
        self.assertEqual(json.loads(output.getvalue())['catalog_version'],'0.1.0')
        code,out,error=self.invoke('show','report/summary','--json')
        self.assertEqual(code,0,error)
        self.assertEqual(json.loads(out)['kind'],'report')

    def test_catalog_html_escapes_metadata_and_never_overwrites(self):
        directory=self.copy_report()
        metadata=json.loads(json.dumps(self.selected()['descriptor']))
        metadata['title']='<script>alert(1)</script>'
        (directory/'recipe.yaml').write_text(json.dumps(metadata))
        target=self.base/'catalog.html'
        code,out,error=self.invoke('list','--html',str(target))
        self.assertEqual(code,0,error)
        content=target.read_text()
        self.assertIn('&lt;script&gt;',content)
        self.assertNotIn('<script>',content)
        self.assertEqual(self.invoke('list','--html',str(target))[0],1)

    def test_report_run_without_hosts_or_session_saves_sources_artifacts(self):
        self.settings={'hosts':{}}
        self.write_config()
        report,path=self.run_report()
        self.assertEqual(report['status'],'success')
        self.assertIsNone(report['host_id'])
        self.assertEqual(report['data']['rows'],1)
        self.assertEqual(report['report_contract'],'0.1.0')
        self.assertEqual(report['sources'][0]['sha256'],hashlib.sha256(self.input.read_bytes()).hexdigest())
        self.assertNotIn(str(self.input),json.dumps(report))
        self.assertEqual(len(report['artifacts']),2)
        self.assertEqual(json.loads(path.read_text()),report)
        self.assertFalse((self.root/'observations').exists())
        self.assertFalse((self.root/'records').exists())
        info=reports.show_artifact(self.root,path.relative_to(self.root).as_posix(),'summary.html')
        self.assertEqual(info['media_type'],'text/html')
        self.assertTrue(Path(info['path']).is_absolute())
        self.assertTrue(Path(info['path']).is_file())
        self.assertEqual(info['relative_path'],'summary.html')

    def test_report_cli_params_and_no_host_selectors(self):
        code,out,error=self.invoke('run','report/summary','--input',str(self.input),'--var','title=Weekly results')
        self.assertEqual(code,0,error)
        report=json.loads(out)
        self.assertEqual(report['artifacts'][0]['title'],'Weekly results')
        self.assertTrue(report['result_id'].startswith('reports/'))
        self.assertEqual(self.invoke('run','report/summary','--host','h')[0],1)
        self.assertEqual(self.invoke('run','check/port','--input',str(self.input))[0],1)
        self.assertEqual(self.invoke('run','check/port')[0],1)
        with patch.object(runner,'load_runtime') as runtime:
            self.assertEqual(self.invoke('run','report/summary','--var','unknown=private')[0],1)
        runtime.assert_not_called()

    def test_operational_run_reuses_existing_runner(self):
        with patch.object(runner,'main',return_value=0) as run:
            self.assertEqual(self.invoke('run','check/port','--host','h','--var','port=8888')[0],0)
        argv=run.call_args.args[0]
        self.assertEqual(argv[0],'check/port')
        self.assertIn('--host',argv)
        self.assertIn('port=8888',argv)

    def test_report_preserves_failed_and_missing_states_and_escapes_html(self):
        data=json.loads(self.input.read_text())
        data.update(status='failed',host_id='<script>bad</script>',identity={'quality':'fallback','warnings':['Uncertain identity']})
        data['data']['reachable']=None
        self.input.write_text(json.dumps(data))
        report,path=self.run_report()
        raw=json.loads((path.parent/'artifacts/summary.json').read_text())
        row=raw['rows'][0]
        self.assertEqual(row['status'],'failed')
        self.assertIsNone(row['data']['reachable'])
        self.assertEqual(row['observed_from'],data['started_at'])
        self.assertEqual(row['identity_warnings'],['Uncertain identity'])
        self.assertEqual(row['recipe_version'],'0.1.0')
        self.assertEqual(row['source_evidence_kind'],'mock')
        self.assertEqual(reports.results(self.root)['results'][0]['identity_warnings'],[])  # Report has no invented host identity.
        (self.root/'observations').mkdir()
        (self.root/'observations/identity.json').write_text(json.dumps(data))
        self.assertEqual(reports.results(self.root,host=data['host_id'])['results'][0]['identity_warnings'],['Uncertain identity'])
        content=(path.parent/'artifacts/summary.html').read_text()
        self.assertNotIn('<script>',content)
        self.assertIn('&lt;script&gt;',content)

    def test_report_empty_selection_and_unsupported_data(self):
        report,_=reports.run_report(self.root,self.selected(),[])
        self.assertEqual(report['reason_code'],'empty_selection')
        self.input.write_text('{"not":"a run"}')
        report,_=self.run_report()
        self.assertEqual(report['status'],'failed')
        self.assertEqual(report['reason_code'],'unsupported_input')
        self.assertEqual(report['artifacts'],[])

    def test_artifact_tamper_traversal_and_missing_file(self):
        report,path=self.run_report()
        identifier=path.relative_to(self.root).as_posix()
        with self.assertRaises(ops.ConfigError): reports.show_artifact(self.root,identifier,'../result.json')
        artifact=path.parent/'artifacts/summary.html'
        artifact.write_text('changed')
        with self.assertRaisesRegex(ops.ConfigError,'changed'): reports.show_artifact(self.root,identifier,'summary.html')
        artifact.unlink()
        with self.assertRaises(ops.ConfigError): reports.show_artifact(self.root,identifier,'summary.html')

    def test_invalid_artifact_paths_and_symlinks(self):
        directory=self.base/'artifacts'
        directory.mkdir()
        (directory/'good.txt').write_text('good')
        outside=self.base/'outside.txt'
        outside.write_text('outside')
        (directory/'link.txt').symlink_to(outside)
        for path in ('../outside.txt',str(outside),'link.txt','missing.txt'):
            with self.subTest(path=path),self.assertRaises(ops.ConfigError):
                reports.validate_artifacts(directory,[{'path':path,'title':'T','media_type':'text/plain'}])
        item={'path':'good.txt','title':'T','media_type':'text/plain'}
        with self.assertRaises(ops.ConfigError): reports.validate_artifacts(directory,[item,item])

    def test_report_runtime_failure_does_not_expose_exception_text(self):
        directory=self.copy_report()
        (directory/'main.py').write_text("VERSION='0.1.0'\ndef execute(*,context,timeout): raise RuntimeError('private-value')")
        report,path=reports.run_report(self.root,catalog.choose(self.root,':report/summary'),[])
        self.assertEqual(report['status'],'failed')
        self.assertNotIn('private-value',path.read_text())
        (directory/'main.py').write_text("VERSION='0.1.0'\ndef execute(*,context,timeout): return {'status':'success'}")
        report,_=reports.run_report(self.root,catalog.choose(self.root,':report/summary'),[])
        self.assertEqual(report['reason_code'],'invalid_result')

    def test_report_store_symlink_refused_before_execution(self):
        (self.root/'reports').symlink_to(self.base)
        with self.assertRaises(ops.ConfigError): self.run_report()

    def test_result_query_filter_partial_and_html(self):
        report,path=self.run_report()
        observations=self.root/'observations'
        observations.mkdir()
        (observations/'synthetic.json').write_bytes(self.input.read_bytes())
        (observations/'broken.json').write_text('{')
        data=reports.results(self.root)
        self.assertEqual(data['status'],'partial')
        self.assertEqual(len(data['results']),2)
        self.assertEqual(len(data['errors']),1)
        self.assertEqual(len(reports.results(self.root,host='synthetic-host')['results']),1)
        self.assertEqual(reports.results(self.root,status='failed')['results'],[])
        code,out,error=self.invoke('results','show',path.relative_to(self.root).as_posix())
        self.assertEqual(code,0,error)
        self.assertEqual(json.loads(out)['report_contract'],'0.1.0')
        target=self.base/'results.html'
        self.assertEqual(self.invoke('results','list','--html',str(target))[0],1)
        self.assertTrue(target.exists())
        for name in ('../hosts.yaml','hosts.yaml',str(path),'reports/../../hosts.yaml'):
            with self.assertRaises(ops.ConfigError): reports.show_result(self.root,name)

    def test_result_symlink_parent_and_file_rejected(self):
        report,path=self.run_report()
        observations=self.root/'observations'
        observations.mkdir()
        (observations/'link.json').symlink_to(path)
        self.assertEqual(reports.results(self.root)['status'],'partial')
        with self.assertRaises(ops.ConfigError): reports.show_result(self.root,'observations/link.json')
        (self.root/'reports/link').symlink_to(path.parent)
        with self.assertRaises(ops.ConfigError): reports.show_result(self.root,'reports/link/result.json')

    def test_offline_recipe_rejected_by_host_runner(self):
        with patch.object(runner,'load_runtime') as runtime,self.assertRaisesRegex(ops.ConfigError,'offline'):
            runner.run(self.root,'h',recipe='report/summary')
        runtime.assert_not_called()

    def test_report_signature_and_inspection_contract(self):
        item=self.selected()
        self.assertEqual(item['contract'],'valid-python-report')
        directory=self.copy_report()
        (directory/'main.py').write_text("VERSION='0.1.0'\ndef execute(session,*,context,timeout): pass")
        self.assertFalse(catalog.choose(self.root,':report/summary')['runnable'])

    def test_jobs_save_show_rerun_and_content_change(self):
        directory=self.copy_report()
        code,out,error=self.invoke('jobs','save','weekly',':report/summary','--input',str(self.input),'--var','title=Weekly')
        self.assertEqual(code,0,error)
        self.assertEqual(json.loads(out)['job_version'],'0.1.0')
        self.assertEqual(self.invoke('jobs','run','weekly')[0],0)
        self.assertEqual(self.invoke('jobs','run','weekly')[0],0)
        self.assertEqual(len(reports.results(self.root)['results']),2)
        self.assertEqual(self.invoke('jobs','save','weekly',':report/summary')[0],1)
        self.assertEqual(json.loads(self.invoke('jobs','list')[1])['jobs'],['weekly'])
        (directory/'template.txt').write_text('new content')
        self.assertEqual(self.invoke('jobs','run','weekly')[0],1)
        self.assertEqual(self.invoke('jobs','show','weekly')[0],0)
        self.assertFalse((self.root/'schedules').exists())

    def test_invalid_jobs_preflight_names_and_symlinks(self):
        self.assertEqual(self.invoke('jobs','save','broken','report/summary','--host','h')[0],1)
        self.assertFalse((self.root/'jobs/broken.json').exists())
        for name in ('../escape','bad name',''):
            with self.assertRaises(ops.ConfigError): jobs.job_path(self.root,name)
        (self.root/'jobs').mkdir(exist_ok=True)
        (self.root/'jobs/linked.json').symlink_to(self.input)
        with self.assertRaises(ops.ConfigError): jobs.load(self.root,'linked')

    def test_pack_unpack_report_into_another_instance_no_private_bindings(self):
        item=self.selected()
        archive=self.base/'report.zip'
        packaged=packages.pack(item,['recipe.yaml','main.py','README.md','examples/input.synthetic.json'],archive)
        self.assertEqual(packaged['publisher_authentication'],'not-established')
        candidate=packages.unpack(archive,self.base/'candidate')
        self.assertIn('not-installed',candidate['activation'])
        other=self.base/'other-feast'
        other.mkdir()
        (other/'hosts.yaml').write_text('{"hosts":{}}')
        shutil.copytree(Path(candidate['recipe_directory']),other/'recipes/report/summary')
        copied=catalog.choose(other,':report/summary')
        result,path=reports.run_report(other,copied,[self.input])
        self.assertEqual(result['status'],'success')
        with zipfile.ZipFile(archive) as zipped:
            self.assertNotIn(str(self.root),zipped.read('MANIFEST.json').decode())
        with self.assertRaises(ops.ConfigError): packages.unpack(archive,self.base/'candidate')

    def test_pack_required_allowlist_private_files_and_symlink(self):
        directory=self.copy_report()
        item=catalog.choose(self.root,':report/summary')
        for files in ([],['recipe.yaml'],['recipe.yaml','main.py','README.md','hosts.yaml'],['../input.json']):
            with self.subTest(files=files),self.assertRaises(ops.ConfigError): packages.pack(item,files,self.base/'bad.zip')
        (directory/'link.txt').symlink_to(self.input)
        with self.assertRaises(ops.ConfigError): packages.pack(item,['recipe.yaml','main.py','README.md','link.txt'],self.base/'bad.zip')

    def test_bundle_digest_mismatch_and_extra_file_refused(self):
        source=self.base/'source.zip'
        packages.pack(self.selected(),['recipe.yaml','main.py','README.md'],source)
        for change in ('digest','extra'):
            archive=self.base/(change+'.zip')
            with zipfile.ZipFile(source) as src,zipfile.ZipFile(archive,'w') as dest:
                for name in src.namelist():
                    dest.writestr(name,b'changed' if change=='digest' and name=='recipe/main.py' else src.read(name))
                if change=='extra': dest.writestr('recipe/unlisted.txt','extra')
            candidate=self.base/(change+'-candidate')
            with self.assertRaises(ops.ConfigError): packages.unpack(archive,candidate)
            self.assertFalse(candidate.exists())

    def test_bundle_unsafe_paths_duplicate_link_and_limits(self):
        for index,name in enumerate(('recipe/../escape','/absolute','recipe/.git/config','unexpected.txt')):
            archive=self.base/(str(index)+'.zip')
            with zipfile.ZipFile(archive,'w') as dest:
                dest.writestr('MANIFEST.json','{}')
                dest.writestr(name,'x')
            with self.assertRaises(ops.ConfigError): packages.unpack(archive,self.base/('candidate'+str(index)))
        archive=self.base/'link.zip'
        with zipfile.ZipFile(archive,'w') as dest:
            dest.writestr('MANIFEST.json','{}')
            entry=zipfile.ZipInfo('recipe/link')
            entry.external_attr=(stat.S_IFLNK|0o777)<<16
            dest.writestr(entry,'outside')
        with self.assertRaises(ops.ConfigError): packages.unpack(archive,self.base/'link-candidate')
        source=self.base/'bounded.zip'
        packages.pack(self.selected(),['recipe.yaml','main.py','README.md'],source)
        with patch.object(packages,'MAX_BYTES',1),self.assertRaises(ops.ConfigError): packages.unpack(source,self.base/'bounded-candidate')

    def test_shared_input_parser_rejects_duplicate_keys_and_nonfinite(self):
        for text in ('{"x":1,"x":2}','{"x":NaN}','[]'):
            with self.assertRaises(ops.ConfigError): parse_json_object(text)
        with self.assertRaises(ops.ConfigError): parse_json_object('{"x":1}'.encode('utf-16'))

    def test_job_schema_tampering_is_rejected_before_execution(self):
        self.assertEqual(self.invoke('jobs','save','safe','report/summary')[0],0)
        path=self.root/'jobs/safe.json'
        original=json.loads(path.read_text())
        for key,value in (('all','false'),('timeout',True),('threads',False),('inputs','a file'),('targets',[['unknown','h']]),('quiet',1)):
            document=copy.deepcopy(original)
            document['invocation'][key]=value
            path.write_text(json.dumps(document))
            with patch.object(cli,'run_report') as execute:
                self.assertEqual(self.invoke('jobs','run','safe')[0],1)
            execute.assert_not_called()

    def test_package_exclusive_creation_race_preserves_existing_file(self):
        destination=self.base/'existing.zip'
        real_open=Path.open
        def opened(path,*args,**kwargs):
            if path==destination and args and args[0]=='xb':
                destination.write_bytes(b'another writer')
            return real_open(path,*args,**kwargs)
        with patch.object(Path,'open',opened),self.assertRaises(FileExistsError):
            packages.pack(self.selected(),['recipe.yaml','main.py','README.md'],destination)
        self.assertEqual(destination.read_bytes(),b'another writer')

    def test_duplicate_archive_and_manifest_identity_refused(self):
        archive=self.base/'duplicate.zip'
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(archive,'w') as dest:
                dest.writestr('MANIFEST.json','{}')
                dest.writestr('MANIFEST.json','{}')
        with self.assertRaises(ops.ConfigError): packages.unpack(archive,self.base/'candidate-duplicate')
        source=self.base/'original.zip'
        packages.pack(self.selected(),['recipe.yaml','main.py','README.md'],source)
        tampered=self.base/'identity.zip'
        with zipfile.ZipFile(source) as src,zipfile.ZipFile(tampered,'w') as dest:
            for name in src.namelist():
                content=src.read(name)
                if name=='MANIFEST.json':
                    document=json.loads(content)
                    document['recipe_id']='different'
                    content=json.dumps(document).encode()
                dest.writestr(name,content)
        with self.assertRaises(ops.ConfigError): packages.unpack(tampered,self.base/'identity-candidate')
        self.assertFalse((self.base/'identity-candidate').exists())

    def test_cli_package_commands_roundtrip_candidate_only(self):
        archive=self.base/'cli.zip'
        code,out,error=self.invoke('pack','report/summary','--file','recipe.yaml','--file','main.py','--file','README.md','--output',str(archive))
        self.assertEqual(code,0,error)
        self.assertEqual(json.loads(out)['bundle_version'],'0.1.0')
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(ops.main(['recipes','unpack',str(archive),'--destination',str(self.base/'cli-candidate')]),0)
        self.assertIn('not-installed',json.loads(output.getvalue())['activation'])

    def test_report_invalid_input_fails_before_creating_run(self):
        self.input.write_text('{"secret":NaN}')
        code,_,error=self.invoke('run','report/summary','--input',str(self.input))
        self.assertEqual(code,1)
        self.assertFalse((self.root/'reports').exists())

    def test_result_show_rejects_nonrun_object_and_save_failure(self):
        directory=self.root/'observations'
        directory.mkdir()
        (directory/'bad.json').write_text('{}')
        with self.assertRaises(ops.ConfigError): reports.show_result(self.root,'observations/bad.json')
        with patch.object(reports,'write_json',side_effect=OSError('private-value')):
            code,_,error=self.invoke('run','report/summary','--input',str(self.input))
        self.assertEqual(code,1)
        self.assertNotIn('private-value',error)

    def test_cli_root_alias_is_normalized_before_result_ids(self):
        alias=self.base/'feast-alias'
        alias.symlink_to(self.root,target_is_directory=True)
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(ops.main(['recipes','run','report/summary','--root',str(alias),'--input',str(self.input)]),0)
        self.assertTrue(json.loads(output.getvalue())['result_id'].startswith('reports/'))


if __name__=='__main__': unittest.main()
