"""Synthetic package-security contracts. No host connections or live feed downloads."""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from opsfeast.package_security import advisories as feeds, inventory, probe, report
from opsfeast.package_security.analysis import assess, ranges_status
from opsfeast.package_security.versions import debian, rpm
from opsfeast.data_contract import validate

ROOT = Path(__file__).resolve().parents[1]
TIME = '2026-11-13T00:00:00Z'
AS_OF = '2026-11-13T01:00:00Z'


def row(name='libexample1', version='1:2.0-1', **changes):
    result = dict(package_kind='package',name=name, version=version, architecture='amd64', source_name='example',
                  source_version=version, installation_state='installed', producer='Example maintainer',
                  epoch=None, release=None, source_rpm=None)
    return dict(result, **changes)


def page(rows, system=None, manager='dpkg', offset=0, limit=200):
    system = system or {'id':'debian','version_id':'12','version_codename':'bookworm','platform':'linux'}
    details={'kind':system.get('platform','linux'),'status':'complete','facts':{},'sources':[],'gaps':[],'package_database_status':'complete'}
    fingerprint = feeds.digest({'platform_details':details,'os':system,'manager':manager,'packages':rows,'excluded_states':{}})
    selected = rows[offset:offset+limit]
    return dict(schema_version='0.2.0', platform_details=details,os=system, manager=manager, total=len(rows), offset=offset,
                next_offset=offset+len(selected), packages=selected, excluded_states={},
                snapshot_sha256=fingerprint, query_sha256='a'*64, observed_at=TIME)


class Session:
    def __init__(self, rows, change=None, system=None, manager='dpkg'):
        self.rows=rows;self.calls=0;self.change=change;self.system=system;self.manager=manager

    def exec_command(self, argv, **kwargs):
        self.calls+=1
        if argv==['uname','-s']:
            return SimpleNamespace(exitcode=0,stdout='FreeBSD' if (self.system or {}).get('id')=='freebsd' else 'Linux',stdout_truncated=False,stderr_truncated=False)
        assert argv[:3]==['python3','-B','-']
        assert 'subprocess.Popen' in kwargs['input'] and not kwargs['check']
        data=page(self.rows,self.system,self.manager,int(argv[3]),int(argv[4]))
        if self.change:data=self.change(data,self.calls)
        return SimpleNamespace(exitcode=0,stdout=json.dumps(data),stdout_truncated=False,stderr_truncated=False,termination_status='completed')


def snapshot(rows=None, **changes):
    recipe=SimpleNamespace(vars={},timeout=300,host_id='synthetic-host',session=Session(rows if rows is not None else [row()]))
    data=inventory.collect(recipe)['data']
    data['acquisition'].update(started_at=TIME,completed_at=TIME)
    data.update(changes)
    if data['complete']:
        native=[{k:v for k,v in p.items() if k not in ('purl','repository_origin','provenance_status')} for p in data['packages']]
        data['snapshot_sha256']=feeds.digest({'os':data['os'],'manager':data['manager'],'packages':native,'excluded_states':data['excluded_states'],'platform_details':data['platform_details']})
    return data


def vendor(vendor='debian', status='resolved', fixed='1:2.0-2', ecosystem=None, events=None):
    system={'debian':('debian','12','bookworm'),'ubuntu':('ubuntu','22.04','jammy'),'redhat':('rhel','9.4','')}[vendor]
    scope=dict(zip(('os_id','version_id','codename'),system))
    if vendor=='debian':
        document={'example':{'CVE-2026-10001':{'description':'Synthetic issue','releases':{'bookworm':{'status':status,'fixed_version':fixed,'urgency':'high'}}}}}
        url='https://security-tracker.debian.org/tracker/data/json'
    else:
        ecosystem=ecosystem or ('Ubuntu:22.04:LTS' if vendor=='ubuntu' else 'Red Hat:enterprise_linux:9::baseos')
        document={'id':'UBUNTU-CVE-2026-10001' if vendor=='ubuntu' else 'RHSA-2026:10001','aliases':['CVE-2026-10001'], 'modified':TIME,
                  'affected':[{'package':{'name':'example','ecosystem':ecosystem},'ranges':[{'type':'ECOSYSTEM','events':events or [{'introduced':'0'},{'fixed':fixed}]}]}]}
        url='https://security-metadata.canonical.com/osv/test.json' if vendor=='ubuntu' else 'https://security.access.redhat.com/data/osv/RHSA-2026:10001.json'
    raw=json.dumps(document).encode()
    source=dict(url=url,retrieved_at=TIME,sha256=hashlib.sha256(raw).hexdigest(),acquisition='user_attested_local_import')
    return feeds.snapshot(vendor,scope,[source],[(raw,'test.json')])


class VersionTests(unittest.TestCase):
    def test_debian_native_order(self):
        for a,b,sign in [('1:1.0','99.0',1),('1.0~rc1','1.0',-1),('1.0-2','1.0-10',-1),('1.0','1.0-0',0),('1.01','1.1',0),('1.0+deb12u2','1.0+deb12u10',-1),('1a','1+',-1)]:
            with self.subTest(a=a,b=b):self.assertEqual(debian(a,b),sign);self.assertEqual(debian(b,a),-sign)

    def test_rpm_native_order(self):
        for a,b,sign in [('1:1.0-1','0:99.0-9',1),('1.0~rc1','1.0',-1),('2.0^150825','2.0',1),('2.0^150825','2.0.1',-1),('1+.+0','1.0',0),('abc0123','abc.123',0),('1.xyz','1.0',-1),('1.0-5','1.0',1),('1.0-2.el9','1.0-10.el9',-1)]:
            with self.subTest(a=a,b=b):self.assertEqual(rpm(a,b),sign);self.assertEqual(rpm(b,a),-sign)

    def test_invalid_versions_unknown(self):
        for value in ('', '1.0;id', 'one two', 'x:1', '1:2:3', '1\n'):
            with self.subTest(value=value),self.assertRaises(ValueError):debian(value,'1')


class CollectionTests(unittest.TestCase):
    def test_more_than_2000_and_final_fingerprint(self):
        session=Session([row(name='p'+str(i)) for i in range(2301)])
        value=inventory.collect(SimpleNamespace(vars={},timeout=300,host_id='h',session=session))
        self.assertEqual(value['status'],'success');self.assertEqual(value['data']['collected_count'],2301)
        self.assertEqual(session.calls,14)
        self.assertIn('arch=amd64',value['data']['packages'][0]['purl'])
        schema=json.loads((ROOT/'schemas/os-package-inventory.schema.json').read_text());validate(value['data'],schema)

    def test_changed_database_not_complete(self):
        session=Session([row()],lambda data,count:dict(data,snapshot_sha256='b'*64) if count==3 else data)
        value=inventory.collect(SimpleNamespace(vars={},timeout=300,host_id='h',session=session))
        self.assertEqual(value['status'],'partial');self.assertFalse(value['data']['complete'])

    def test_forged_page_digest_rejected(self):
        session=Session([row()],lambda data,count:dict(data,snapshot_sha256='b'*64))
        data=inventory.collect(SimpleNamespace(vars={},timeout=300,host_id='h',session=session))['data']
        self.assertIn('package_snapshot_digest_mismatch',data['gaps'])

    def test_broken_offsets_not_complete(self):
        session=Session([row()],lambda data,count:dict(data,next_offset=999))
        self.assertFalse(inventory.collect(SimpleNamespace(vars={},timeout=300,host_id='h',session=session))['data']['complete'])

    def test_truncated_transport_not_complete(self):
        response=SimpleNamespace(exitcode=0,stdout='{}',stdout_truncated=True,stderr_truncated=False)
        recipe=SimpleNamespace(vars={},timeout=300,host_id='h',session=SimpleNamespace(exec_command=lambda *a,**k:response))
        self.assertEqual(inventory.collect(recipe)['status'],'failed')

    def test_dpkg_source_and_noninstalled_states(self):
        output='libexample1\t1:2.0-1+b1\tamd64\texample\t1:2.0-1\tinstalled\tMaintainer\nremoved\t1\tamd64\tremoved\t1\tconfig-files\tMaintainer\nbroken\t1\tamd64\tbroken\t1\tunpacked\tMaintainer\n'
        with patch.object(probe,'os_release',return_value={'platform':'linux','id':'debian'}),patch.object(probe,'run',return_value=output):
            system,manager,rows,excluded,*_=probe.inventory(5)
        self.assertEqual(manager,'dpkg');self.assertEqual(len(rows),2);self.assertEqual(excluded,{'config-files':1})
        package=next(p for p in rows if p['name']=='libexample1');self.assertNotEqual(package['version'],package['source_version'])

    def test_rpm_epoch_and_source_rpm(self):
        with patch.object(probe,'os_release',return_value={'platform':'linux','id':'rhel'}),patch.object(probe.shutil,'which',return_value='/usr/bin/rpm'),patch.object(probe,'run',return_value='example\t(none)\t2.0\t1.el9\tx86_64\texample-2.0-1.el9.src.rpm\tVendor\n'):
            _,manager,rows,*_=probe.inventory(5)
        self.assertEqual(rows[0]['version'],'0:2.0-1.el9');self.assertEqual(rows[0]['epoch'],0);self.assertIsNone(rows[0]['source_name'])

    def test_freebsd_inventory_only(self):
        with patch.object(probe,'os_release',return_value={'platform':'freebsd','id':'freebsd'}),patch.object(probe,'run',return_value='example\t2.0_1\tFreeBSD:14:amd64\tdevel/example\n'):
            _,manager,rows,*_=probe.inventory(5)
        self.assertEqual(manager,'pkg');self.assertEqual(rows[0]['ports_origin'],'devel/example')

    def test_unsupported_os(self):
        with patch.object(probe,'os_release',return_value={'platform':'darwin'}),self.assertRaisesRegex(ValueError,'unsupported'):probe.inventory(5)

    def test_native_failure_and_stderr_are_preserved(self):
        with self.assertRaises(probe.QueryError) as raised:
            probe.run([sys.executable,'-c','import sys;sys.stderr.write("synthetic failure");sys.exit(7)'],3)
        self.assertEqual(raised.exception.evidence['exitcode'],7)
        self.assertEqual(raised.exception.evidence['stderr'],'synthetic failure')

    def test_native_timeout_and_output_bound(self):
        with self.assertRaisesRegex(probe.QueryError,'timeout'):
            probe.run([sys.executable,'-c','import time;time.sleep(3)'],.03)
        with patch.object(probe,'MAX_DATABASE',10),self.assertRaisesRegex(probe.QueryError,'byte_limit'):
            probe.run([sys.executable,'-c','print("x"*100)'],3)

    def test_byte_pages(self):
        rows=[row(name='p'+str(i),producer='x'*3000) for i in range(100)]
        with patch.object(probe,'inventory',return_value=({},'dpkg',rows,{},'a'*64,'b'*64,{'status':'complete'})):
            data=probe.page(0,200,5)
        self.assertLess(len(data['packages']),100);self.assertGreater(data['next_offset'],0)


class AssessmentTests(unittest.TestCase):
    def finding(self,inv=None,feed=None,**kwargs):
        return assess(inv or snapshot(),[feed or vendor()],as_of=AS_OF,**kwargs)['findings'][0]

    def test_affected_with_source_evidence(self):
        finding=self.finding();self.assertEqual(finding['status'],'affected');self.assertEqual(finding['cves'],['CVE-2026-10001'])
        self.assertEqual(finding['evidence']['comparisons'][0]['fixed'],'1:2.0-2')

    def test_backport_fixed_not_upstream_semver(self):
        self.assertEqual(self.finding(snapshot([row(version='1:2.0-3')]))['status'],'fixed')

    def test_binary_version_is_not_source_version(self):
        self.assertEqual(self.finding(snapshot([row(version='1:2.0-2+b1',source_version='1:2.0-1')]))['status'],'affected')

    def test_debian_not_affected_and_undetermined(self):
        self.assertEqual(self.finding(feed=vendor(fixed='0'))['status'],'not_affected')
        self.assertEqual(self.finding(feed=vendor(status='undetermined',fixed=''))['status'],'unknown')

    def test_debian_open(self):
        self.assertEqual(self.finding(feed=vendor(status='open',fixed=''))['status'],'affected')

    def test_same_cve_multiple_source_packages(self):
        first=vendor();raw={'example':{'CVE-2026-10001':{'releases':{'bookworm':{'status':'open'}}}},'another':{'CVE-2026-10001':{'releases':{'bookworm':{'status':'resolved','fixed_version':'0'}}}}}
        data=feeds.snapshot('debian',first['scope'],first['sources'],[(json.dumps(raw).encode(),'data.json')])
        self.assertEqual(data['record_count'],2)

    def test_incomplete_and_stale_never_clean(self):
        for changes,reason in [({'complete':False},'inventory_incomplete'),({'acquisition':{'started_at':'2020-01-01T00:00:00Z','completed_at':'2020-01-01T01:00:00Z'}},'inventory_stale')]:
            finding=self.finding(snapshot(**changes));self.assertEqual(finding['status'],'unknown');self.assertIn(reason,finding['uncertainty']);self.assertEqual(finding['candidate_status'],'affected')

    def test_stale_feed_and_future_time(self):
        for instant,reason in [('2020-01-01T00:00:00Z','advisory_snapshot_stale'),('2030-01-01T00:00:00Z','advisory_retrieval_time_in_future')]:
            feed=vendor();feed['sources'][0]['retrieved_at']=instant;feed['snapshot_sha256']=feeds.digest({k:v for k,v in feed.items() if k!='snapshot_sha256'})
            self.assertIn(reason,self.finding(feed=feed)['uncertainty'])

    def test_no_matching_package_is_unknown(self):
        self.assertEqual(self.finding(snapshot([row(source_name='unlisted')]))['status'],'unknown')

    def test_wrong_release_and_derivative_unknown(self):
        for system in [{'id':'debian','version_id':'13','version_codename':'trixie'},{'id':'linuxmint','id_like':'ubuntu','version_id':'22'}]:
            self.assertEqual(self.finding(snapshot(os=system))['status'],'unknown')

    def test_ubuntu_native_osv_and_pro_scope(self):
        inv=snapshot(os={'id':'ubuntu','version_id':'22.04','version_codename':'jammy'})
        self.assertEqual(self.finding(inv,vendor('ubuntu'))['status'],'affected')
        feed=vendor('ubuntu',ecosystem='Ubuntu:Pro:22.04:LTS')
        self.assertEqual(self.finding(inv,feed)['status'],'unknown')
        inv['declared_ecosystems']=['Ubuntu:Pro:22.04:LTS'];self.assertEqual(self.finding(inv,feed)['status'],'affected')

    def test_redhat_exact_stream_required(self):
        inv=snapshot([row(name='example',version='0:2.0-1.el9')],os={'id':'rhel','version_id':'9.4'},manager='rpm')
        feed=vendor('redhat',fixed='0:2.0-2.el9')
        self.assertEqual(self.finding(inv,feed)['status'],'unknown')
        inv['declared_ecosystems']=['Red Hat:enterprise_linux:9::baseos'];self.assertEqual(self.finding(inv,feed)['status'],'affected')
        inv['os']['id']='rocky';inv['complete']=False;inv['packages_complete']=False;self.assertEqual(self.finding(inv,feed)['status'],'unknown')

    def test_malformed_rule_unknown(self):
        inv=snapshot(os={'id':'ubuntu','version_id':'22.04','version_codename':'jammy'})
        self.assertEqual(self.finding(inv,vendor('ubuntu',events=[{'fixed':'2'}]))['status'],'unknown')

    def test_ranges_reintroduction_and_last_affected(self):
        entry={'ranges':[{'type':'ECOSYSTEM','events':[{'introduced':'0'},{'fixed':'2'},{'introduced':'3'},{'fixed':'4'}]}]}
        for version,status in [('1','affected'),('2','fixed'),('3','affected'),('4','fixed')]:self.assertEqual(ranges_status(version,entry,'deb')[0],status)
        entry={'ranges':[{'type':'ECOSYSTEM','events':[{'introduced':'1'},{'last_affected':'2'}]}]}
        self.assertEqual(ranges_status('2',entry,'deb')[0],'affected');self.assertEqual(ranges_status('3',entry,'deb')[0],'not_affected')

    def test_limits_and_ambiguous_sources(self):
        data=assess(snapshot([row(),row(name='p2')]),[vendor()],as_of=AS_OF,max_findings=1)
        self.assertEqual(data['omitted_findings'],1);self.assertFalse(data['assessment_complete'])
        data=assess(snapshot(),[vendor(),vendor(fixed='2')],as_of=AS_OF)
        self.assertTrue(all(f['status']=='unknown' for f in data['findings']))
        with self.assertRaises(ValueError):self.finding(max_inventory_age_hours=float('nan'))


class FeedAndReportTests(unittest.TestCase):
    def test_tampered_snapshot_and_duplicate_json(self):
        data=vendor();data['records'][0]['id']='tampered'
        with self.assertRaisesRegex(ValueError,'digest'):feeds.load(data)
        with self.assertRaises(ValueError):feeds.parse(b'{"x":1,"x":2}')
        with self.assertRaises(ValueError):feeds.parse(b'{"x":NaN}')

    def test_archive_without_extraction_and_traversal_rejection(self):
        for name,valid in [('nested/test.json',True),('../test.json',False)]:
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w:xz') as archive:
                content=b'{"id":"test"}';item=tarfile.TarInfo(name);item.size=len(content);archive.addfile(item,io.BytesIO(content))
            if valid:self.assertEqual(list(feeds.documents(stream.getvalue(),'sample.tar.xz')),[{'id':'test'}])
            else:
                with self.assertRaises(ValueError):list(feeds.documents(stream.getvalue(),'sample.tar.xz'))

    def test_url_allowlist_and_explicit_rhsa(self):
        for url in ['http://security-tracker.debian.org/tracker/data/json','https://evil.example/data','https://security-tracker.debian.org@evil.example/data']:
            with self.assertRaises(ValueError):feeds.validate_url('debian',url)
        with self.assertRaises(ValueError):feeds.fetch('redhat',dict(os_id='rhel',version_id='9.4',codename=''))

    def test_report_html_escaped_and_evidence_exported(self):
        data=report.generate([snapshot(),vendor()],{'as_of':AS_OF,'title':'<script>hostile</script>'})
        with tempfile.TemporaryDirectory() as directory:
            artifacts=report.render(data,directory)
            html=(Path(directory)/'package-security.html').read_text()
            self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
            self.assertEqual(len(artifacts),3)
            parsed=json.loads((Path(directory)/'package-security.json').read_text())
            self.assertEqual(parsed['reports'][0]['findings'][0]['status'],'affected')

    def test_report_invalid_inputs_no_artifacts(self):
        context=SimpleNamespace(inputs=[{'old':'inventory'}],vars={},artifact_dir=None)
        self.assertEqual(report.execute(context=context,timeout=20)['status'],'failed')

    def test_recipe_descriptors_and_retention_schema(self):
        from opsfeast import read_yaml
        for reference in ('system/software/inventory/os-packages','feast/report/package-security'):
            result=subprocess.run([sys.executable,'-B','tools/opsfeast.py','inspect-recipe',reference,'--json'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        schema=read_yaml(ROOT/'recipes/system/software/inventory/os-packages/recipe.yaml')['retention']['data_schema']
        self.assertEqual(schema,json.loads((ROOT/'schemas/os-package-inventory.schema.json').read_text()))
        validate(snapshot(),schema)

    def test_snapshot_digest_and_time_order(self):
        value=snapshot();value['packages'][0]['source_version']='9'
        with self.assertRaisesRegex(ValueError,'digest'):assess(value,[vendor()],as_of=AS_OF)
        value=snapshot();value['acquisition']['started_at']='2027-01-01T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'time_order'):assess(value,[vendor()],as_of=AS_OF)

    def test_explicit_official_fetch_receipt(self):
        raw=json.dumps({'example':{'CVE-2026-10001':{'releases':{'bookworm':{'status':'open'}}}}}).encode()
        source=dict(url='https://security-tracker.debian.org/tracker/data/json',retrieved_at=TIME,sha256=hashlib.sha256(raw).hexdigest(),acquisition='https_official_endpoint')
        with patch.object(feeds,'download',return_value=(raw,source)) as download:
            data=feeds.fetch('debian',dict(os_id='debian',version_id='12',codename='bookworm'))
        download.assert_called_once();self.assertEqual(data['record_count'],1)
        self.assertEqual(data['sources'][0]['acquisition'],'https_official_endpoint')

    def test_local_import_preserves_original_age(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'native.json';raw=json.dumps({'example':{'CVE-2026-10001':{'releases':{'bookworm':{'status':'open'}}}}});path.write_text(raw)
            data=feeds.import_local('debian',dict(os_id='debian',version_id='12',codename='bookworm'),path,'https://security-tracker.debian.org/tracker/data/json','2020-01-01T00:00:00Z')
            self.assertEqual(data['sources'][0]['retrieved_at'],'2020-01-01T00:00:00Z');self.assertEqual(path.read_text(),raw)
            self.assertEqual(assess(snapshot(),[data],as_of=AS_OF)['findings'][0]['status'],'unknown')

    def test_report_through_shared_recipe_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'hosts.yaml').write_text('{"hosts":{}}')
            (root/'inventory.json').write_text(json.dumps({'data':snapshot()}));(root/'feed.json').write_text(json.dumps(vendor()))
            args=[sys.executable,'-B','tools/opsfeast.py','recipes','run','feast/report/package-security','--root',str(root),'--input',str(root/'inventory.json'),'--input',str(root/'feed.json'),'--var','as_of='+AS_OF,'--json']
            result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertTrue(list(root.glob('reports/*/artifacts/package-security.html')))
            self.assertFalse((root/'observations').exists())

    def test_cli_offline_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'inventory.json').write_text(json.dumps(snapshot()));(root/'feed.json').write_text(json.dumps(vendor()))
            args=[sys.executable,'-B','-m','opsfeast.package_security','assess','--inventory',str(root/'inventory.json'),'--advisory',str(root/'feed.json'),'--output-dir',str(root/'report'),'--as-of',AS_OF]
            result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertTrue((root/'report/package-security.html').is_file())
            self.assertEqual(subprocess.run(args,cwd=ROOT,capture_output=True).returncode,1)


if __name__=='__main__':unittest.main()
