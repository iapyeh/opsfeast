"""Host-selected three-stage package workflow, entirely synthetic/offline."""
from contextlib import contextmanager,redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from uuid import uuid4
import unittest
from unittest.mock import patch

from opsfeast.package_security import pipeline,advisories,probe
from test_package_security import Session,row,vendor
from recipe_contract import validate_result
from opsfeast import read_yaml
from opsfeast.data_contract import validate

ROOT=Path(__file__).resolve().parents[1]
REF='system/software/check/package-security'


def fresh_vendor(name='debian',**kwargs):
    feed=vendor(name,**kwargs);feed['sources'][0]['retrieved_at']=advisories.now()
    feed['snapshot_sha256']=advisories.digest({k:v for k,v in feed.items() if k!='snapshot_sha256'})
    return feed


class Recipe:
    def __init__(self,root,*,system=None,manager='dpkg',rows=None,variables=None):
        self.profile=SimpleNamespace(root=root);self.run_id=str(uuid4());self.host_id='synthetic'
        self.timeout=30;self.vars=variables or {};self.session=Session(rows or [row()],system=system,manager=manager);self.children=0
    @contextmanager
    def child(self,*,vars):
        self.children+=1
        yield SimpleNamespace(vars=vars,host_id=self.host_id,session=self.session,timeout=self.timeout)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name).resolve()
        (self.root/'hosts.yaml').write_text('hosts: {}\n')
        self.feed=fresh_vendor()

    def run_pipeline(self,recipe=None):
        with patch.object(advisories,'fetch',return_value=self.feed) as fetch:
            result=pipeline.execute(recipe or Recipe(self.root))
        validate_result(result)
        return result,fetch

    def test_three_stages_one_borrowed_session_and_saved_artifacts(self):
        recipe=Recipe(self.root);result,fetch=self.run_pipeline(recipe)
        self.assertEqual(result['status'],'success');self.assertEqual(recipe.children,1);self.assertEqual(recipe.session.calls,3)
        self.assertEqual([s['stage'] for s in result['data']['stages']],['collection','advisories','report'])
        self.assertEqual(result['summary']['report']['counts']['affected'],1)
        saved=self.root/result['reports'][0]['result_id'];self.assertTrue(saved.is_file())
        raw=json.loads(saved.read_text());self.assertEqual(raw['status'],'success');self.assertEqual(len(raw['artifacts']),3)
        self.assertTrue((saved.parent/'artifacts/package-security.html').is_file())
        self.assertEqual(len(raw['sources']),2)
        fetch.assert_called_once();self.assertEqual(fetch.call_args.args[:2],('debian',{'os_id':'debian','version_id':'12','codename':'bookworm'}))
        schema=read_yaml(ROOT/'recipes'/REF/'recipe.yaml')['retention']['data_schema'];validate(result['data'],schema)

    def test_fresh_matching_cache_shared_across_hosts(self):
        with patch.object(advisories,'fetch',return_value=self.feed) as fetch:
            first=pipeline.execute(Recipe(self.root));second=pipeline.execute(Recipe(self.root))
        self.assertEqual(fetch.call_count,1);self.assertEqual(second['data']['stages'][1]['reason_code'],'reused_fresh_snapshot')
        self.assertNotEqual(first['reports'][0]['result_id'],second['reports'][0]['result_id'])

    def test_force_refresh_and_release_cache_separation(self):
        with patch.object(advisories,'fetch',return_value=self.feed) as fetch:
            pipeline.execute(Recipe(self.root));pipeline.execute(Recipe(self.root,variables={'advisory_cache_hours':0}))
        self.assertEqual(fetch.call_count,2)
        with patch.object(advisories,'fetch',return_value=fresh_vendor('ubuntu')) as fetch:
            result=pipeline.execute(Recipe(self.root,system={'id':'ubuntu','version_id':'22.04','version_codename':'jammy'}))
        self.assertEqual(fetch.call_args.args[0],'ubuntu');self.assertEqual(result['status'],'success')

    def test_network_failure_still_saves_unknown_report_without_retry(self):
        with patch.object(advisories,'fetch',side_effect=OSError('synthetic')) as fetch:
            result=pipeline.execute(Recipe(self.root))
        self.assertEqual(fetch.call_count,1);self.assertEqual(result['status'],'partial')
        self.assertIn('vendor_acquisition_failed',result['data']['gaps'])
        raw=json.loads((self.root/result['reports'][0]['result_id']).read_text())
        self.assertEqual(raw['data']['counts']['unknown'],1)
        artifact=json.loads((self.root/result['reports'][0]['result_id']).parent.joinpath('artifacts/package-security.json').read_text())
        self.assertFalse(artifact['reports'][0]['assessment_complete']);self.assertIn('vendor_acquisition_failed',artifact['reports'][0]['gaps'])

    def test_unsupported_distribution_no_network_and_no_safe_verdict(self):
        result,fetch=self.run_pipeline(Recipe(self.root,system={'id':'rocky','version_id':'9.4'},manager='rpm'))
        fetch.assert_not_called();self.assertEqual(result['status'],'partial');self.assertEqual(result['summary']['report']['counts']['unknown'],1)

    def test_incomplete_collection_preserves_data_and_unknowns(self):
        recipe=Recipe(self.root)
        recipe.session.change=lambda payload,count:dict(payload,snapshot_sha256='c'*64) if count==3 else payload
        result,_=self.run_pipeline(recipe)
        self.assertEqual(result['status'],'partial');self.assertFalse(result['data']['package_snapshot']['complete'])
        self.assertEqual(result['summary']['report']['counts']['unknown'],1)

    def test_report_failure_keeps_inventory_and_receipt(self):
        with patch.object(advisories,'fetch',return_value=self.feed),patch('recipe_reports.run_report',side_effect=OSError('synthetic')):
            result=pipeline.execute(Recipe(self.root))
        self.assertEqual(result['status'],'failed');self.assertEqual(result['reports'],[])
        self.assertTrue(result['data']['package_snapshot']['complete']);self.assertEqual(result['data']['stages'][-1]['status'],'failed')
        validate_result(result)

    def test_tampered_cache_does_not_become_a_clean_result(self):
        self.run_pipeline()
        path=next((self.root/'security/advisories').glob('*.snapshot.json'));data=json.loads(path.read_text());data['record_count']=999;path.write_text(json.dumps(data))
        result,fetch=self.run_pipeline();fetch.assert_not_called();self.assertEqual(result['status'],'partial')
        self.assertIn('advisory_snapshot_digest_mismatch',result['data']['gaps'])

    def test_redhat_discovery_scope_and_explicit_stream(self):
        self.feed=fresh_vendor('redhat',fixed='0:2.0-2.el9')
        recipe=Recipe(self.root,system={'id':'rhel','version_id':'9.4'},manager='rpm',rows=[row(name='example',version='0:2.0-1.el9')],variables={'declared_ecosystems':['Red Hat:enterprise_linux:9::baseos']})
        discovery={'advisory_ids':['RHSA-2026:10001'],'metadata_freshness':'not_verified'}
        with patch.object(pipeline,'_redhat_ids',return_value=discovery):result,fetch=self.run_pipeline(recipe)
        self.assertEqual(fetch.call_args.args[2],['RHSA-2026:10001']);self.assertEqual(result['status'],'partial')
        self.assertEqual(result['summary']['report']['counts']['affected'],1)
        self.assertIn('redhat_cache_metadata_freshness_unverified',result['data']['gaps'])

    def test_redhat_explicit_ids_avoid_discovery(self):
        self.feed=fresh_vendor('redhat',fixed='0:2.0-2.el9')
        recipe=Recipe(self.root,system={'id':'rhel','version_id':'9.4'},manager='rpm',rows=[row(name='example',version='0:2.0-1.el9')],variables={'redhat_advisory_ids':['RHSA-2026:10001']})
        with patch.object(pipeline,'_redhat_ids',side_effect=AssertionError('no discovery')):result,_=self.run_pipeline(recipe)
        self.assertEqual(result['summary']['report']['counts']['unknown'],1)  # Never infer product stream.

    def test_redhat_query_is_cache_only_and_deduplicated(self):
        output=io.StringIO()
        with patch.object(probe.sys,'argv',['probe','redhat-advisories','2']),patch.object(probe,'os_release',return_value={'id':'rhel'}),patch.object(probe.shutil,'which',return_value='/usr/bin/dnf'),patch.object(probe,'run',return_value='i RHSA-2026:10001 Important/Sec. example\nRHSA-2026:10001 Important/Sec. other\n') as run,redirect_stdout(output):
            probe.main()
        self.assertEqual(json.loads(output.getvalue())['advisory_ids'],['RHSA-2026:10001'])
        self.assertEqual(run.call_args.args[0],['dnf','--cacheonly','--noplugins','updateinfo','list','--all','--security'])

    def test_bad_report_reference_and_unbounded_summary_rejected(self):
        common={'status':'success','reason_code':'ok','message':'ok','data':{}}
        for field,value in [('reports',[{'result_id':'../secret','status':'success'}]),('summary',{'x':'a'*70000})]:
            with self.subTest(field=field),self.assertRaises(ValueError):validate_result({**common,field:value})

    def test_menu_meal_uses_one_orchestration_recipe(self):
        from opsfeast.recipe_menu import bundle_sets
        meal=next(s for s in bundle_sets() if s['id']=='bundle:package-security')
        self.assertEqual(meal['recipes'],[REF]);self.assertEqual(meal['meals'],[])

    def test_shared_runner_retains_full_snapshot_but_emits_bounded_cli_summary(self):
        import opsfeast
        from recipe_runner import connected
        from contextlib import contextmanager
        import recipe_runner
        with redirect_stdout(io.StringIO()):opsfeast.initialize(self.root,quiet=True,profile='main')
        (self.root/'hosts.yaml').write_text('hosts: {synthetic: {connection: {local: true}}}\n')
        fake=Recipe(self.root);fake._state=SimpleNamespace(identity={'id':'00000000-0000-0000-0000-000000000001'});fake._active=True
        @contextmanager
        def execution(policy):yield fake
        fake.execution=execution
        @contextmanager
        def connect(*args,**kwargs):yield fake.session
        def create(*args,**kwargs):
            fake.vars=kwargs['vars'];return fake
        output=io.StringIO()
        with patch.object(advisories,'fetch',return_value=self.feed),patch.object(recipe_runner,'connected',connect),patch.object(opsfeast.Recipe,'_create',side_effect=create),patch('opsfeast.identity.read_identity',return_value=fake._state.identity),redirect_stdout(output):
            code=opsfeast.main(['recipes','run',REF,'--root',str(self.root),'--host','synthetic','--json'])
        self.assertEqual(code,0,output.getvalue())
        receipt=json.loads(output.getvalue());self.assertTrue(receipt['data_is_summary']);self.assertIn('reports',receipt)
        self.assertNotIn('packages',receipt['data']['inventory'])
        raw=json.loads(Path(receipt['result_path']).read_text());self.assertEqual(len(raw['data']['package_snapshot']['packages']),1)
        self.assertEqual(raw['reports'],receipt['reports']);self.assertEqual(raw['retention']['status'],'stored')

    def test_expired_cache_is_not_reused_after_failed_refresh(self):
        old=fresh_vendor();old['sources'][0]['retrieved_at']='2000-01-01T00:00:00Z';old['snapshot_sha256']=advisories.digest({k:v for k,v in old.items() if k!='snapshot_sha256'})
        with patch.object(advisories,'fetch',return_value=old):pipeline.execute(Recipe(self.root))
        with patch.object(advisories,'fetch',side_effect=OSError('offline')) as fetch:
            result=pipeline.execute(Recipe(self.root))
        fetch.assert_called_once();self.assertEqual(result['summary']['report']['counts']['unknown'],1)
        self.assertEqual(result['data']['stages'][1]['status'],'failed')

    def test_cache_lock_wait_has_a_deadline(self):
        import time
        path=self.root/'cache.lock'
        with pipeline._lock(path,time.monotonic()+1):
            with self.assertRaisesRegex(ValueError,'wait_deadline'):
                with pipeline._lock(path,time.monotonic()-1):pass

    def test_download_reads_bounded_chunks_and_records_original_bytes(self):
        from contextlib import contextmanager
        class Response:
            headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read1(self,size):return self.chunks.pop(0)
        response=Response();response.chunks=[b'{}',b'']
        opener=SimpleNamespace(open=lambda *a,**k:response)
        with patch.object(advisories,'build_opener',return_value=opener):
            raw,source=advisories.download('debian','https://security-tracker.debian.org/tracker/data/json')
        self.assertEqual(raw,b'{}');self.assertEqual(source['acquisition'],'https_official_endpoint')
        response.chunks=[b'too big']
        with patch.object(advisories,'build_opener',return_value=opener),patch.object(advisories,'MAX_RAW',2),self.assertRaisesRegex(ValueError,'download_limit'):
            advisories.download('debian','https://security-tracker.debian.org/tracker/data/json')

    def test_redhat_download_identity_must_match_requested_advisory(self):
        raw=json.dumps({'id':'RHSA-2026:99999','affected':[]}).encode()
        with patch.object(advisories,'download',return_value=(raw,{})),self.assertRaisesRegex(ValueError,'identity_mismatch'):
            advisories.fetch('redhat',{'os_id':'rhel','version_id':'9.4','codename':''},['RHSA-2026:10001'])

    def test_esxi_native_snapshot_is_retained_and_reported_without_vendor_download(self):
        from test_package_inventory_platforms import ESXiSession
        recipe=Recipe(self.root);recipe.session=ESXiSession()
        result,fetch=self.run_pipeline(recipe)
        self.assertEqual(fetch.call_args.args[0],'esxi');self.assertEqual(result['status'],'partial')
        self.assertTrue(result['data']['package_snapshot']['complete'])
        self.assertEqual(result['summary']['report']['counts']['unknown'],3)
        validate(result['data'],read_yaml(ROOT/'recipes'/REF/'recipe.yaml')['retention']['data_schema'])

    def test_proxmox_does_not_download_unmatched_debian_feed(self):
        from test_package_security import snapshot
        data=snapshot();data['platform_details']['kind']='proxmox-ve'
        native=[{k:v for k,v in row.items() if k not in ('purl','repository_origin','provenance_status')} for row in data['packages']]
        data['snapshot_sha256']=advisories.digest({'os':data['os'],'manager':data['manager'],'packages':native,'excluded_states':data['excluded_states'],'platform_details':data['platform_details']})
        with patch.object(pipeline,'collect',return_value={'status':'success','reason_code':'os_package_snapshot','data':data}):
            result,fetch=self.run_pipeline()
        self.assertEqual(fetch.call_args.args[0],'proxmox')
        self.assertEqual(result['summary']['report']['counts']['unknown'],2)
