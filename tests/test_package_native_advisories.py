"""Synthetic official-format native vendor adapters; no host/network access."""
from pathlib import Path
import bz2
import hashlib
import json
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from opsfeast.package_security import advisories as feeds,native_advisories as native,report,pipeline
from opsfeast.package_security.analysis import assess
from opsfeast.package_security.freebsd_versions import compare
from test_package_security import snapshot,row,TIME,AS_OF
from test_package_security_pipeline import Recipe

FB='https://www.freebsd.org/security/advisories/FreeBSD-SA-26:01.synthetic.asc'
PVE=native.PVE_THREAD
ESX='https://support.broadcom.com/web/ecx/support-content-notification/-/external/content/SecurityAdvisories/0/12345'
VUXML=b'''<?xml version="1.0"?><vuxml xmlns="http://www.vuxml.org/apps/vuxml-1"><vuln vid="synthetic-id"><topic>synthetic package issue</topic><affects><package><name>example*</name><range><ge>1.0</ge><lt>2.0_1,1</lt></range><range><eq>3.0,1</eq></range></package></affects><references><cvename>CVE-2026-12345</cvename></references><dates><entry>2026-11-12</entry></dates></vuln></vuxml>'''
BASE=b'''FreeBSD-SA-26:01.synthetic Security Advisory
Topic: synthetic kernel issue
Category: core
Module: kern
Announced: 2026-11-12
Corrected: 2026-11-12 00:00:00 UTC (releng/14.3, 14.3-RELEASE-p5)
           2026-11-12 00:00:00 UTC (releng/13.5, 13.5-RELEASE-p9)
CVE Name: CVE-2026-12345
I. Background
'''
PROXMOX=b'''<article data-author="ProxmoxSecurityAdvisory" id="post-1"><div class="bbWrapper"><h3>Subject: PSA-2026-00001-1: synthetic package bug</h3><br>Advisory date: 2026-11-12<br>Packages: example<br>Details:<br>CVE-2026-12345<br>Fixed in:<br>- example &gt;= 2.0-1 (Proxmox VE 9.x)<br></div></article>'''
ESXI=b'''<h1>VMSA-2026-0001: synthetic bugs CVE-2026-12345 CVE-2026-99999</h1><table><tr><th>VMware Product</th><th>Version</th><th>Running On</th><th>CVE</th><th>Fixed Version</th></tr><tr><td rowspan="2">VMware ESXi</td><td>8.0</td><td>Any</td><td>CVE-2026-12345</td><td>ESXi80U3d-24585383</td></tr><tr><td>8.0</td><td>Any</td><td>CVE-2026-12345</td><td>ESXi80U2d-24585300</td></tr><tr><td>VMware vCenter</td><td>8.0</td><td>Any</td><td>CVE-2026-99999</td><td>8.0.3</td></tr></table>'''


def scope(vendor):return {'os_id':feeds.OS_IDS[vendor],'version_id':{'freebsd':'14.3','proxmox':'9','esxi':'8.0.3'}[vendor],'codename':''}

def feed(vendor,raw,url):
    return feeds.snapshot(vendor,scope(vendor),[{'url':url,'retrieved_at':TIME,'sha256':hashlib.sha256(raw).hexdigest(),'acquisition':'user_attested_local_import'}],[(raw,url)])

def platform(vendor,packages=None):
    data=snapshot(packages if packages is not None else [row(name='example',version='1.5',source_name='example',source_version='1.5')])
    facts={}
    if vendor=='freebsd':
        data['os']={'id':'freebsd','version_id':'14.3-RELEASE-p3'};data['manager']='pkg'
        facts={k:{'version':v,'patch_level':int(v.split('-p')[1])} for k,v in [('installed_kernel','14.3-RELEASE-p5'),('running_kernel','14.3-RELEASE-p3'),('userland','14.3-RELEASE-p5')]}
    elif vendor=='proxmox':facts={'manager_package_version':'9.1.1','running_kernel':'6.14.8-pve'}
    else:data['os']={'id':'esxi','version_id':'8.0.3'};data['manager']='esxcli';facts={'system_version':{'Version':'8.0.3','Build':'Releasebuild-24585382'}}
    data['platform_details'].update(kind={'proxmox':'proxmox-ve'}.get(vendor,vendor),facts=facts)
    resign(data);return data

def resign(data):
    native_rows=[{k:v for k,v in r.items() if k not in ('purl','repository_origin','provenance_status')} for r in data['packages']]
    data['snapshot_sha256']=feeds.digest({'os':data['os'],'manager':data['manager'],'packages':native_rows,'excluded_states':data['excluded_states'],'platform_details':data['platform_details']})


class NativeAdvisoryTests(unittest.TestCase):
    def test_pkg_epoch_revision_prerelease_components(self):
        pairs=[('1.0','1.0.0',0),('1.0_1','1.0',1),('1.0,1','9.0',1),('1.0alpha1','1.0',-1),('1.0rc2','1.0rc10',-1),('1.0','1.0a',-1),('1.0pl1','1.0alpha1',-1),('2.*','2pl1',-1),('1.dev2','1.d2',0),('1.0+2','1.0+3',-1)]
        for a,b,expected in pairs:
            with self.subTest(a=a,b=b):self.assertEqual(compare(a,b),expected);self.assertEqual(compare(b,a),-expected)
        for value in ('','1_foo','1,epoch','../bad'):
            with self.assertRaises(ValueError):compare(value,'1')

    def test_vuxml_multi_range_glob_epoch_and_revision(self):
        f=feed('freebsd',VUXML,native.VUXML.removesuffix('.bz2'));data=platform('freebsd',[row(name='example-devel',version='2.0,1')])
        r=assess(data,[f],as_of=AS_OF);p=r['findings'][0]
        self.assertEqual(p['status'],'affected');self.assertIn('CVE-2026-12345',p['cves'])
        data['packages'][0]['version']='2.0_1,1';resign(data)
        self.assertEqual(assess(data,[f],as_of=AS_OF)['findings'][0]['status'],'not_affected')

    def test_freebsd_installed_kernel_does_not_mask_running_kernel(self):
        data=platform('freebsd');r=assess(data,[feed('freebsd',BASE,FB)],as_of=AS_OF)
        by_name={p['package']:p for p in r['findings']}
        self.assertEqual(by_name['freebsd-base:installed_kernel']['status'],'fixed')
        self.assertEqual(by_name['freebsd-base:running_kernel']['status'],'affected')
        self.assertTrue(by_name['freebsd-base:running_kernel']['evidence']['comparisons'])

    def test_freebsd_stable_unknown_and_unrelated_branch_not_fixed(self):
        data=platform('freebsd');data['platform_details']['facts']['running_kernel']['version']='14.3-STABLE';resign(data)
        r=assess(data,[feed('freebsd',BASE,FB)],as_of=AS_OF)
        p=next(p for p in r['findings'] if p['package']=='freebsd-base:running_kernel');self.assertEqual(p['status'],'unknown')
        f=feed('freebsd',BASE.replace(b'14.3-RELEASE-p5',b'14.2-RELEASE-p5'),FB)
        self.assertTrue(all(p['status']=='unknown' for p in assess(platform('freebsd'),[f],as_of=AS_OF)['findings']))

    def test_native_xml_entities_and_expansion_rejected(self):
        for raw in [b'<!DOCTYPE vuxml [<!ENTITY secret SYSTEM "file:///etc/passwd">]><vuxml>&secret;</vuxml>',b'<vuxml>']:
            with self.assertRaises((ValueError,native.ET.ParseError)):list(native.vuxml(raw,native.VUXML))
        inert=b'<!DOCTYPE vuxml [<!ENTITY vuln-2020 SYSTEM "vuln/2020.xml">]>'+VUXML.split(b'?>',1)[1]
        self.assertEqual(len(list(native.vuxml(inert,native.VUXML))),1)
        self.assertEqual(len(list(native.normalize('freebsd',bz2.compress(VUXML),native.VUXML))),1)
        with self.assertRaises(ValueError):list(native.normalize('freebsd',bz2.compress(VUXML)+b'trailing',native.VUXML))

    def test_proxmox_vendor_scope_and_debian_order(self):
        f=feed('proxmox',PROXMOX,PVE);data=platform('proxmox',[row(name='example',version='2.0~rc1')])
        p=assess(data,[f],as_of=AS_OF)['findings'][0];self.assertEqual(p['status'],'affected')
        self.assertEqual(p['evidence']['comparisons'][0]['fixed'],'2.0-1')
        data['packages'][0]['version']='2.0-1';resign(data);self.assertEqual(assess(data,[f],as_of=AS_OF)['findings'][0]['status'],'fixed')
        wrong=feed('proxmox',PROXMOX.replace(b'9.x',b'8.x'),PVE)
        self.assertEqual(assess(data,[wrong],as_of=AS_OF)['findings'][0]['status'],'unknown')

    def test_proxmox_ignores_other_authors_and_retains_unparsed_bulletin(self):
        with self.assertRaises(ValueError):list(native.proxmox(PROXMOX.replace(b'ProxmoxSecurityAdvisory',b'arbitrary-user'),PVE))
        f=feed('proxmox',PROXMOX.replace(b'Fixed in:',b'Changed prose:'),PVE)
        r=assess(platform('proxmox'),[f],as_of=AS_OF)
        self.assertTrue(any(p['reason']=='proxmox_fix_rules_unparsed' for p in r['findings']))

    def test_esxi_matrix_excludes_vcenter_and_uses_same_update_build(self):
        f=feed('esxi',ESXI,ESX);data=platform('esxi',[])
        p=next(p for p in assess(data,[f],as_of=AS_OF)['findings'] if p['status']=='affected')
        self.assertEqual(p['cves'],['CVE-2026-12345']);self.assertEqual(p['evidence']['comparisons'][0]['fixed'],'ESXi80U3d-24585383')
        data['platform_details']['facts']['system_version']['Build']='Releasebuild-24585383';resign(data)
        self.assertTrue(any(p['status']=='fixed' for p in assess(data,[f],as_of=AS_OF)['findings']))
        data['platform_details']['facts']['system_version']['Version']='8.0.1';resign(data)
        self.assertTrue(all(p['status']=='unknown' for p in assess(data,[f],as_of=AS_OF)['findings']))

    def test_esxi_unparseable_or_runtime_restricted_is_unknown(self):
        for raw in (ESXI.replace(b'ESXi80U3d-24585383',b'Please contact support').replace(b'ESXi80U2d-24585300',b'Pending'),ESXI.replace(b'>Any<',b'>Windows<')):
            r=assess(platform('esxi',[]),[feed('esxi',raw,ESX)],as_of=AS_OF);self.assertTrue(all(p['status']=='unknown' for p in r['findings']))

    def test_native_feed_scope_stale_and_coverage_gaps_do_not_pass(self):
        for change in ('stale','scope','gap'):
            f=feed('proxmox',PROXMOX,PVE)
            if change=='stale':f['sources'][0]['retrieved_at']='2020-01-01T00:00:00Z'
            elif change=='scope':f['scope']['version_id']='8'
            else:f['coverage_gaps']=['vendor_advisory_document_acquisition_failed']
            f['snapshot_sha256']=feeds.digest({k:v for k,v in f.items() if k!='snapshot_sha256'})
            self.assertTrue(all(p['status']=='unknown' for p in assess(platform('proxmox'),[f],as_of=AS_OF)['findings']))

    def test_official_url_allowlist_rejects_external_paths_and_redirects(self):
        for vendor,url in [('freebsd','https://evil.invalid/vuln.xml'),('proxmox','https://forum.proxmox.com/threads/arbitrary.123/'),('esxi','https://support.broadcom.com/private/secrets'),('esxi',ESX+'?redirect=evil')]:
            with self.assertRaises(ValueError):feeds.validate_url(vendor,url)

    def test_native_import_and_offline_html_json_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'bulletin.html';source.write_bytes(PROXMOX)
            f=feeds.import_local('proxmox',scope('proxmox'),source,PVE,TIME)
            out=root/'report';out.mkdir();data=report.generate([platform('proxmox'),f],{'as_of':AS_OF});report.render(data,out)
            self.assertTrue((out/'package-security.html').is_file());self.assertEqual(json.loads((out/'package-security.json').read_text())['schema_version'],'0.3.0')

    def test_proxmox_discovery_reads_every_page_no_retry(self):
        first=PROXMOX+b'<a href="/threads/proxmox-virtual-environment-security-advisories.149331/page-2">2</a>'
        second=PROXMOX.replace(b'00001-1',b'00002-1')
        def download(vendor,url,timeout):
            raw=first if url==PVE else second
            return raw,{'url':url,'retrieved_at':TIME,'sha256':hashlib.sha256(raw).hexdigest(),'acquisition':'https_official_endpoint'}
        with patch.object(feeds,'download',side_effect=download) as get:
            f=feeds.fetch('proxmox',scope('proxmox'))
        self.assertEqual(get.call_count,2);self.assertEqual(f['record_count'],2);self.assertEqual(f['coverage_gaps'],[])

    def test_partial_fetch_keeps_valid_advisories_and_explicit_gap(self):
        def download(vendor,url,timeout):
            if url.endswith('page-2'):raise OSError('synthetic')
            raw=PROXMOX+b'<a href="/threads/proxmox-virtual-environment-security-advisories.149331/page-2">2</a>'
            return raw,{'url':url,'retrieved_at':TIME,'sha256':hashlib.sha256(raw).hexdigest(),'acquisition':'https_official_endpoint'}
        with patch.object(feeds,'download',side_effect=download):f=feeds.fetch('proxmox',scope('proxmox'))
        self.assertEqual(f['record_count'],1);self.assertIn('vendor_advisory_document_acquisition_failed',f['coverage_gaps'])

    def test_selected_source_urls_skip_discovery(self):
        def download(vendor,url,timeout):return ESXI,{'url':url,'retrieved_at':TIME,'sha256':hashlib.sha256(ESXI).hexdigest(),'acquisition':'https_official_endpoint'}
        with patch.object(feeds,'download',side_effect=download) as get:f=feeds.fetch('esxi',scope('esxi'),[ESX])
        self.assertEqual(get.call_count,1);self.assertTrue(f['records'])

    def test_esxi_blocked_index_fails_explicitly(self):
        raw=b'<h1>Access denied</h1>'
        def download(vendor,url,timeout,**kwargs):return raw,{'url':url,'retrieved_at':TIME,'sha256':hashlib.sha256(raw).hexdigest(),'acquisition':'https_official_endpoint'}
        with patch.object(feeds,'download',side_effect=download),self.assertRaisesRegex(ValueError,'index_unavailable'):feeds.fetch('esxi',scope('esxi'))

    def test_esxi_official_api_pagination_filters_product_and_keeps_requests(self):
        def download(vendor,url,timeout,**kwargs):
            if url==native.ESXI_INDEX:
                page=kwargs['payload']['pageNumber'];data={'success':True,'data':{'pageInfo':{'currentPage':page,'lastPage':1},'list':[{'title':'VMSA: VMware ESXi bug' if page==0 else 'vCenter only','notificationUrl':ESX}]}}
                raw=json.dumps(data).encode()
            else:raw=ESXI
            return raw,{'url':url,'retrieved_at':TIME,'sha256':hashlib.sha256(raw).hexdigest(),'acquisition':'https_official_endpoint'}
        with patch.object(feeds,'download',side_effect=download) as get:f=feeds.fetch('esxi',scope('esxi'))
        self.assertEqual(get.call_count,3);self.assertEqual(f['record_count'],1);self.assertEqual(f['coverage_gaps'],[])

    def test_freebsd_discovers_only_exact_release_base_advisories(self):
        vx=VUXML.replace(b'<name>example*</name>',b'<name>FreeBSD</name>').replace(b'<ge>1.0</ge><lt>2.0_1,1</lt>',b'<ge>14.3</ge><lt>14.3_5</lt>').replace(b'<references>',b'<references><freebsdsa>SA-26:01.synthetic</freebsdsa>')
        def download(vendor,url,timeout):
            raw=bz2.compress(vx) if url==native.VUXML else BASE
            return raw,{'url':url,'retrieved_at':TIME,'sha256':hashlib.sha256(raw).hexdigest(),'acquisition':'https_official_endpoint'}
        with patch.object(feeds,'download',side_effect=download) as get:f=feeds.fetch('freebsd',scope('freebsd'))
        self.assertEqual(get.call_count,2);self.assertEqual(f['record_count'],2);self.assertEqual(f['coverage_gaps'],[])
        self.assertEqual(get.call_args.args[1],FB)

    def test_all_native_platforms_integrate_collection_feed_and_saved_report(self):
        for vendor,raw,url in [('freebsd',BASE,FB),('proxmox',PROXMOX,PVE),('esxi',ESXI,ESX)]:
            with self.subTest(vendor=vendor),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);(root/'hosts.yaml').write_text('hosts: {}\n');data=platform(vendor,[row(name='example',version='2.0~rc1')])
                data['acquisition'].update(started_at=feeds.now(),completed_at=feeds.now())
                current_feed=feed(vendor,raw,url);current_feed['sources'][0]['retrieved_at']=feeds.now()
                current_feed['snapshot_sha256']=feeds.digest({k:v for k,v in current_feed.items() if k!='snapshot_sha256'})
                with patch.object(pipeline,'collect',return_value={'status':'success','reason_code':'os_package_snapshot','data':data}),patch.object(feeds,'fetch',return_value=current_feed) as fetch:
                    result=pipeline.execute(Recipe(root))
                self.assertEqual(fetch.call_args.args[0],vendor)
                self.assertEqual(result['data']['stages'][2]['reason_code'],'package_security_report_incomplete')
                self.assertTrue((root/result['reports'][0]['result_id']).is_file())
                self.assertGreaterEqual(result['summary']['report']['counts']['affected'],1)

    def test_esxi_index_failure_in_meal_keeps_inventory_unknown_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'hosts.yaml').write_text('hosts: {}\n')
            with patch.object(pipeline,'collect',return_value={'status':'success','reason_code':'os_package_snapshot','data':platform('esxi')}),patch.object(feeds,'fetch',side_effect=ValueError('esxi_advisory_index_unavailable')):
                result=pipeline.execute(Recipe(root))
            self.assertEqual(result['status'],'partial');self.assertIn('esxi_advisory_index_unavailable',result['data']['gaps']);self.assertTrue(result['reports'])

    def test_esxi_matrix_merges_alternative_update_branches(self):
        f=feed('esxi',ESXI,ESX);self.assertEqual(len(f['records'][0]['affected']),1)
        p=assess(platform('esxi',[]),[f],as_of=AS_OF)['findings']
        self.assertEqual(len(p),1);self.assertEqual(p[0]['status'],'affected')

    def test_unfixed_proxmox_package_retains_advisory_reference(self):
        raw=PROXMOX.replace(b'<br></div>',b'<br>Not Fixed:<br>- example-legacy<br></div>')
        f=feed('proxmox',raw,PVE);r=assess(platform('proxmox',[row(name='example-legacy',version='2.0')]),[f],as_of=AS_OF)
        p=r['findings'][0];self.assertEqual(p['reason'],'proxmox_vendor_no_fix');self.assertEqual(p['advisory_id'],'PSA-2026-00001-1')

    def test_invalid_native_scope_fails_before_network(self):
        with patch.object(feeds,'download') as download:
            for vendor in ('freebsd','proxmox','esxi'):
                with self.assertRaises(ValueError):feeds.fetch(vendor,{'os_id':feeds.OS_IDS[vendor],'version_id':'unidentified','codename':''})
            download.assert_not_called()

    def test_xml_utf16_entities_are_rejected_before_parsing(self):
        raw='<!DOCTYPE vuxml [<!ENTITY x "boom">]><vuxml>&x;</vuxml>'.encode('utf-16')
        with self.assertRaises(ValueError):native.xml(raw)

    def test_recipe_meal_uses_reviewed_native_source_urls(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'hosts.yaml').write_text('hosts: {}\n')
            data=platform('esxi')
            with patch.object(pipeline,'collect',return_value={'status':'success','reason_code':'os_package_snapshot','data':data}),patch.object(feeds,'fetch',return_value=feed('esxi',ESXI,ESX)) as fetch:
                pipeline.execute(Recipe(root,variables={'vendor_advisory_urls':[ESX]}))
            self.assertEqual(fetch.call_args.args[2],[ESX])

    def test_contradictory_vuxml_range_is_unknown_not_not_affected(self):
        raw=VUXML.replace(b'<ge>1.0</ge>',b'<ge>9.0,1</ge>')
        r=assess(platform('freebsd'),[feed('freebsd',raw,native.VUXML.removesuffix('.bz2'))],as_of=AS_OF)
        self.assertEqual(r['findings'][0]['status'],'unknown');self.assertEqual(r['findings'][0]['reason'],'vuxml_contradictory_range')
