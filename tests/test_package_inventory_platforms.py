"""Native platform package inventories with synthetic I/O only."""
from datetime import datetime,timezone
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape

from opsfeast.package_security import probe,inventory,esxi
from opsfeast.package_security.analysis import validate_inventory,assess
from opsfeast import read_yaml
from opsfeast.data_contract import validate
from test_package_security import vendor

ROOT=Path(__file__).resolve().parents[1]


def xml(rows):
    return '<output xmlns="http://www.vmware.com/Products/ESX/5.0/esxcli/"><list type="Synthetic">'+''.join('<structure typeName="Synthetic">'+''.join('<field name="'+escape(k)+'"><string>'+escape(v)+'</string></field>' for k,v in row.items())+'</structure>' for row in rows)+'</list></output>'


class ESXiSession:
    def __init__(self,fail=None,change=False):self.calls=[];self.fail=fail;self.change=change;self.vib_reads=0
    def exec_command(self,argv,**kwargs):
        self.calls.append(argv)
        assert not kwargs.get('input')  # No target interpreter dependency.
        assert kwargs['check'] is False and kwargs['command_timeout']>0
        key=tuple(argv)
        if key==self.fail:return SimpleNamespace(exitcode=1,stdout='',stderr='synthetic permission denial',stdout_truncated=False,stderr_truncated=False)
        if argv==['uname','-s']:text='VMkernel\n'
        elif argv==['uname','-m']:text='x86_64\n'
        elif argv[-3:]==['system','version','get']:text=xml([{'Product':'VMware ESXi','Version':'8.0.3','Build':'Releasebuild-12345678','Update':'3'}])
        elif argv[-3:]==['software','profile','get']:text=xml([{'Name':'synthetic-profile','Vendor':'Synthetic OEM'}])
        elif argv[-3:]==['software','vib','list']:
            self.vib_reads+=1
            text=xml([{'Name':'driver','Version':'2' if self.change and self.vib_reads==2 else '1','Vendor':'Synthetic','AcceptanceLevel':'PartnerSupported','InstallDate':'2026-01-01'}])
        elif argv[-3:]==['software','component','list']:text=xml([{'Name':'driver','Version':'1','Vendor':'Synthetic','DisplayName':'Synthetic Component'}])
        else:raise AssertionError(argv)
        return SimpleNamespace(exitcode=0,stdout=text,stderr='',stdout_truncated=False,stderr_truncated=False)


class PlatformTests(unittest.TestCase):
    def recipe(self,session):return SimpleNamespace(host_id='synthetic-esxi',vars={},timeout=30,session=session)

    def test_esxi_vib_component_version_profile_and_no_python(self):
        session=ESXiSession();result=inventory.collect(self.recipe(session));data=result['data']
        self.assertEqual(result['status'],'success');self.assertEqual(data['schema_version'],'0.2.0')
        self.assertTrue(data['packages_complete']);self.assertEqual(data['collected_count'],2)
        self.assertEqual({p['package_kind'] for p in data['packages']},{'vib','component'})
        self.assertTrue(all(p['architecture']=='unknown' and p['purl'] is None for p in data['packages']))
        self.assertEqual(data['platform_details']['facts']['system_version']['Build'],'Releasebuild-12345678')
        self.assertEqual(data['platform_details']['facts']['image_profile'][0]['Name'],'synthetic-profile')
        self.assertEqual(data['packages'][1]['native_fields']['AcceptanceLevel'],'PartnerSupported')
        self.assertFalse(any('python' in arg for argv in session.calls for arg in argv))
        validate_inventory(data);validate(data,json.loads((ROOT/'schemas/os-package-inventory.schema.json').read_text()))

    def test_esxi_component_unavailable_keeps_vibs_and_metadata(self):
        session=ESXiSession(fail=('esxcli','--formatter=xml','software','component','list'))
        data=inventory.collect(self.recipe(session))['data']
        self.assertFalse(data['complete']);self.assertFalse(data['packages_complete']);self.assertEqual(len(data['packages']),1)
        self.assertEqual(data['packages'][0]['package_kind'],'vib');self.assertIn('system_version',data['platform_details']['facts'])

    def test_esxi_profile_unavailable_is_identity_gap_not_lost_packages(self):
        session=ESXiSession(fail=('esxcli','--formatter=xml','software','profile','get'))
        data=inventory.collect(self.recipe(session))['data']
        self.assertFalse(data['complete']);self.assertTrue(data['packages_complete']);self.assertEqual(len(data['packages']),2)

    def test_esxi_change_on_final_read_is_incomplete(self):
        data=inventory.collect(self.recipe(ESXiSession(change=True)))['data']
        self.assertFalse(data['complete']);self.assertIn('package_database_changed_during_collection',data['gaps'])

    def test_esxi_xml_rejects_entities_duplicates_and_resource_limits(self):
        for text in ['<!DOCTYPE output [<!ENTITY x "boom">]><output><string>&x;</string></output>','<output><structure><field name="Name"><string>x</string></field><field name="Name"><string>y</string></field></structure></output>','<output>not xml']:
            with self.subTest(text=text),self.assertRaises((ValueError,esxi.ET.ParseError)):esxi.parse(text)
        with patch.object(esxi,'MAX_XML_NODES',2),self.assertRaises(ValueError):esxi.parse(xml([{'Name':'x'}]))

    def test_freebsd_versions_are_independent_and_preserve_patch_levels(self):
        def query(argv,timeout):
            return {('freebsd-version','-k'):'14.3-RELEASE-p5\n',('freebsd-version','-r'):'14.3-RELEASE-p3\n',('freebsd-version','-u'):'14.3-RELEASE-p6\n',('pkg','query','-a','%n\t%v\t%q\t%o'):'example\t2.0_1\tFreeBSD:14:amd64\tdevel/example\n'}[tuple(argv)]
        with patch.object(probe,'os_release',return_value={'platform':'freebsd','id':'freebsd','version_id':'14.3-RELEASE-p3'}),patch.object(probe,'run',side_effect=query):
            system,manager,rows,excluded,fingerprint,query_sha,details=probe.inventory(5)
        self.assertEqual(details['facts']['userland']['patch_level'],6)
        self.assertEqual(details['facts']['installed_kernel']['patch_level'],5)
        self.assertEqual(details['facts']['running_kernel']['patch_level'],3)
        self.assertEqual(rows[0]['ports_origin'],'devel/example');self.assertEqual(details['status'],'complete')

    def test_freebsd_missing_pkg_retains_base_identity(self):
        def query(argv,timeout):
            if argv[0]=='pkg':raise FileNotFoundError('synthetic')
            return '14.3-RELEASE-p4\n'
        with patch.object(probe,'os_release',return_value={'platform':'freebsd','id':'freebsd'}),patch.object(probe,'run',side_effect=query):
            result=probe.inventory(5)
        self.assertEqual(result[2],[]);self.assertEqual(result[6]['facts']['userland']['patch_level'],4)
        self.assertEqual(result[6]['package_database_status'],'failed');self.assertEqual(result[6]['status'],'partial')

    def test_freebsd_unavailable_running_version_is_not_zero(self):
        def query(argv,timeout):
            if argv==['freebsd-version','-r']:raise probe.QueryError('package_query_failed',exitcode=1)
            return '' if argv[0]=='pkg' else '15.0-CURRENT\n'
        with patch.object(probe,'os_release',return_value={'platform':'freebsd','id':'freebsd'}),patch.object(probe,'run',side_effect=query):
            details=probe.inventory(5)[6]
        self.assertIsNone(details['facts']['running_kernel']['version']);self.assertIsNone(details['facts']['userland']['patch_level'])
        self.assertEqual(details['package_database_status'],'complete');self.assertEqual(details['status'],'partial')

    def test_proxmox_identifies_product_without_changing_debian_identity(self):
        versions='proxmox-ve: 8.4.0 (running kernel: 6.8.12-9-pve)\npve-manager: 8.4.1 (running version: 8.4.1/synthetic) [available: 8.4.2]\nzfsutils-linux: 2.2.7-pve2\n'
        def query(argv,timeout):
            if argv[0]=='pveversion':return versions
            return 'pve-manager\t8.4.1\tamd64\tpve-manager\t8.4.1\tinstalled\tProxmox\nproxmox-ve\t8.4.0\tall\tproxmox-ve\t8.4.0\tinstalled\tProxmox\n'
        with patch.object(probe,'os_release',return_value={'platform':'linux','id':'debian','version_id':'12'}),patch.object(probe,'run',side_effect=query):
            system,_,rows,_,_,_,details=probe.inventory(5)
        self.assertEqual(system['id'],'debian');self.assertEqual(details['kind'],'proxmox-ve')
        self.assertEqual(details['facts']['manager_package_version'],'8.4.1');self.assertEqual(details['facts']['running_kernel'],'6.8.12-9-pve')
        manager=details['facts']['components'][1];self.assertEqual(manager['version'],'8.4.1');self.assertEqual(manager['available_version'],'8.4.2')
        self.assertEqual(len(rows),2)

    def test_proxmox_missing_tool_keeps_dpkg_identity_and_reports_gap(self):
        def query(argv,timeout):
            if argv[0]=='pveversion':raise FileNotFoundError('synthetic')
            return 'pve-manager\t8.4.1\tamd64\tpve-manager\t8.4.1\tinstalled\tProxmox\n'
        with patch.object(probe,'os_release',return_value={'platform':'linux','id':'debian'}),patch.object(probe,'run',side_effect=query):
            details=probe.inventory(5)[6]
        self.assertEqual(details['kind'],'proxmox-ve');self.assertEqual(details['status'],'partial');self.assertEqual(details['package_database_status'],'complete')

    def test_old_snapshot_contract_is_rejected_without_rewriting(self):
        from test_package_security import snapshot
        data=snapshot();data['schema_version']='0.1.0'
        with self.assertRaises(ValueError):validate_inventory(data)

    def test_proxmox_does_not_inherit_unqualified_debian_safe_findings(self):
        from test_package_security import snapshot
        from opsfeast.package_security.advisories import digest
        data=snapshot();data['platform_details']['kind']='proxmox-ve'
        native=[{k:v for k,v in row.items() if k not in ('purl','repository_origin','provenance_status')} for row in data['packages']]
        data['snapshot_sha256']=digest({'os':data['os'],'manager':data['manager'],'packages':native,'excluded_states':data['excluded_states'],'platform_details':data['platform_details']})
        result=assess(data,[vendor()],as_of='2026-11-13T01:00:00Z')
        self.assertEqual(result['findings'][0]['status'],'unknown');self.assertIn('missing_or_ambiguous_vendor_snapshot',result['gaps'])

    def test_partial_identity_still_validates_database_fingerprint(self):
        data=inventory.collect(self.recipe(ESXiSession(fail=('esxcli','--formatter=xml','software','profile','get'))))['data']
        validate_inventory(data)
        data['packages'][0]['version']='tampered'
        with self.assertRaisesRegex(ValueError,'digest_mismatch'):validate_inventory(data)

    def test_esxi_report_retains_native_facts_with_unknown_vendor(self):
        from opsfeast.package_security.report import generate
        data=inventory.collect(self.recipe(ESXiSession()))['data']
        report=generate([data],{'allow_missing_advisories':True})['reports'][0]
        self.assertFalse(report['assessment_complete'])
        self.assertEqual(report['platform_details']['facts']['system_version']['Version'],'8.0.3')
        self.assertEqual(report['counts']['unknown'],3)
        self.assertEqual({f['package_kind'] for f in report['findings']},{'vib','component','platform'})

    def test_freebsd_paged_controller_preserves_base_when_identity_query_fails(self):
        class NativeSession:
            def exec_command(inner,argv,**kwargs):
                if argv==['uname','-s']:text='FreeBSD\n'
                else:
                    def query(command,timeout):
                        if command==['freebsd-version','-r']:raise FileNotFoundError('synthetic')
                        return 'example\t1.0\tFreeBSD:14:amd64\tdevel/example\n' if command[0]=='pkg' else '14.3-RELEASE-p5\n'
                    with patch.object(probe,'os_release',return_value={'platform':'freebsd','id':'freebsd'}),patch.object(probe,'run',side_effect=query):
                        text=json.dumps(probe.page(int(argv[3]),int(argv[4]),5))
                return SimpleNamespace(exitcode=0,stdout=text,stderr='',stdout_truncated=False,stderr_truncated=False)
        result=inventory.collect(self.recipe(NativeSession()));data=result['data']
        self.assertEqual(result['status'],'partial');self.assertTrue(data['packages_complete']);self.assertFalse(data['complete'])
        self.assertIsNone(data['platform_details']['facts']['running_kernel']['version'])
        self.assertEqual(data['platform_details']['facts']['userland']['patch_level'],5)
        validate_inventory(data);validate(data,json.loads((ROOT/'schemas/os-package-inventory.schema.json').read_text()))

    def test_freebsd_malformed_version_is_missing_identity(self):
        def query(argv,timeout):return '' if argv[0]=='pkg' else 'not-a-native-version'
        with patch.object(probe,'os_release',return_value={'platform':'freebsd','id':'freebsd'}),patch.object(probe,'run',side_effect=query):
            details=probe.inventory(5)[6]
        self.assertEqual(details['status'],'partial');self.assertIsNone(details['facts']['installed_kernel']['version'])
