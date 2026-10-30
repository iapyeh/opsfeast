"""Synthetic storage queries only; never connect to hardware or modify real disks."""
import contextlib
import copy
import io
import json
from pathlib import Path
import runpy
import shlex
import sys
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from opsfeast import ConfigError, read_yaml
from opsfeast.data_contract import validate
from recipe_catalog import choose
from retention_replay import snapshot, ingest
import retention_store as store
import vault_content
import test_host_vault as vault_fixtures

DIRECTORY = ROOT / 'recipes/system/storage/inventory/disks-raid'
CODE = runpy.run_path(str(DIRECTORY / 'main.py'))
MD = runpy.run_path(str(DIRECTORY / 'md_probe.py'))
META = read_yaml(DIRECTORY / 'recipe.yaml')


def result(value='', code=0, truncated=False):
    return SimpleNamespace(stdout=value if isinstance(value, str) else json.dumps(value),
                           stderr='', exitcode=code, stdout_truncated=truncated, stderr_truncated=False)


def controller(data, number=0, status='Success'):
    return {'Command Status': {'Controller': number, 'Status': status}, 'Response Data': data}


def response(data):
    return {'Controllers': [controller(data)]}


DISKS = {'blockdevices': [{'type': 'disk', 'path': '/dev/sda', 'kname': 'sda',
                           'size': '1000000000', 'model': 'Synthetic VD', 'serial': None},
                          {'type': 'part', 'path': '/dev/sda1'}]}
CTRL = response({'Basics': {'Model': 'Synthetic PERC'}, 'VD LIST': [
    {'DG/VD': '0/0', 'TYPE': 'RAID1', 'State': 'Dgrd', 'Size': '1 TB'}]})
PD = response({'Drive /c0/e32/s0': [{'EID:Slt': '32:0', 'State': 'Onln', 'DG': 0}],
               'Drive /c0/e32/s0 - Detailed Information': {'SN': 'SYNTHETIC-SERIAL'}})


class Session:
    def __init__(self, platform='Linux', uid='0', failures=None, md=None):
        self.platform, self.uid = platform, uid
        self.calls = []
        self.failures = failures or {}
        self.md = md or {'arrays': [], 'errors': []}

    def exec_command(self, command, **kwargs):
        if isinstance(command, list):
            command = command[2] if command[:2] == ['/bin/sh', '-c'] else shlex.join(command)
        self.calls.append((command, kwargs))
        self_command = shlex.split(command)
        if command in self.failures:
            failure = self.failures[command]
            if isinstance(failure, Exception):
                raise failure
            return failure
        if command == 'uname -s': return result(self.platform + '\n')
        if command == 'id -u': return result(self.uid + '\n')
        if self_command[0] == 'lsblk': return result(DISKS)
        if self_command[:2] == ['python3', '-c']: return result(self.md)
        if command == CODE['DISCOVER']: return result('/opt/lsi/perccli/perccli\n')
        if self_command[0] == 'esxcli':
            if 'raid' in self_command:
                return result('PhysicalLocation,\n"enclosure 1, slot 0",\n"enclosure 1, slot 1",\n')
            return result('Device,DisplayName,IsLocal,DeviceType,IsBootDevice,RAIDLevel,Size,\nnaa.synthetic,"Dell, VD",true,Direct-Access ,false,RAID1,1024,\n')
        if self_command[1] == '/call/eall/sall': return result(PD)
        if self_command[1] == '/call': return result(CTRL)
        raise AssertionError(command)


def recipe(session=None, values=None):
    session = session or Session()
    return SimpleNamespace(session=session, vars=values or {}, timeout=15,
                           report={'execution_identity': {'verified': True, 'actual': {
                               'username': 'root' if session.uid == '0' else 'operator',
                               'effective_uid': int(session.uid)}}},
                           root=lambda: (_ for _ in ()).throw(AssertionError('root console not needed')))


class StorageTests(unittest.TestCase):
    def execute(self, session=None, values=None):
        value = CODE['execute'](recipe(session, values))
        if value['status'] in ('success', 'partial'):
            validate(value['data'], META['retention']['data_schema'])
        return value

    def test_session_uses_argv_and_explicit_posix_shell_for_discovery(self):
        session = SimpleNamespace(exec_command=lambda argv, **kw: argv)
        self.assertEqual(CODE['session_command'](session, 'uname -s'), ['uname', '-s'])
        self.assertEqual(CODE['session_command'](session, CODE['DISCOVER']), ['/bin/sh', '-c', CODE['DISCOVER']])
        text = 'print("quoted input")'
        self.assertEqual(CODE['session_command'](session, shlex.join(['python3','-c',text])), ['python3','-c',text])

    def test_linux_scopes_and_source_details(self):
        session = Session()
        value = self.execute(session)
        self.assertEqual(value['status'], 'partial')
        self.assertEqual(value['data']['os_disks'][0]['size_bytes'], 1000000000)
        self.assertIn('not_verified_physical', value['data']['os_disks'][0]['scope'])
        self.assertIsNone(value['data']['os_disks'][0]['serial'])
        self.assertEqual(value['data']['physical_drives'][0]['details']['SN'], 'SYNTHETIC-SERIAL')
        self.assertEqual(value['data']['virtual_drives'][0]['summary']['State'], 'Dgrd')
        self.assertTrue(all(kw['command_timeout'] <= 15 for cmd, kw in session.calls))
        self.assertTrue(all(p['started_at'] and p['completed_at'] for p in value['data']['probes']))

    def test_esxi_root_needs_no_python_or_bash(self):
        session = Session('VMkernel')
        value = self.execute(session)
        self.assertEqual(value['status'], 'partial')
        self.assertEqual(value['data']['platform'], 'esxi')
        self.assertEqual(value['data']['coverage']['md_arrays']['status'], 'not_applicable')
        self.assertEqual(value['data']['os_disks'][0]['details']['DisplayName'], 'Dell, VD')
        self.assertFalse(any(shlex.split(cmd)[0] in ('python3', 'bash', 'lsblk') for cmd, _ in session.calls))

    def test_discovery_uses_portable_builtins_without_command_utility(self):
        with tempfile.TemporaryDirectory() as temp:
            cli = Path(temp)/'perccli64'
            cli.write_text('synthetic tool; discovery must never execute it')
            cli.chmod(0o700)
            value = subprocess.run(['/bin/sh','-c',CODE['DISCOVER']], env={'PATH':temp},
                                   text=True,capture_output=True,timeout=3)
            self.assertEqual(value.returncode,0,value.stderr)
            self.assertEqual(value.stdout.strip(),str(cli))
        self.assertNotIn('command -v', CODE['DISCOVER'])

    def test_esxi_lsu_preserves_slots_and_explicit_identity_gaps(self):
        value = self.execute(Session('VMkernel',failures={CODE['DISCOVER']:result('',127)}))
        self.assertEqual(value['status'],'partial')
        data=value['data']
        self.assertEqual(len(data['physical_drives']),2)
        self.assertIsNone(data['physical_drives'][0]['controller'])
        self.assertEqual(data['physical_drives'][0]['logical_device'],'naa.synthetic')
        self.assertEqual(data['physical_drives'][0]['address'],'enclosure 1, slot 0')
        self.assertEqual(data['physical_drives'][0]['details'],{})
        self.assertEqual(data['coverage']['physical_drives']['reason'],'lsu_locations_only')
        self.assertEqual(data['coverage']['controllers']['status'],'unknown')
        self.assertEqual(data['virtual_drives'][0]['summary']['RAIDLevel'],'RAID1')

    def test_esxi_lsu_failure_does_not_claim_no_physical_disks(self):
        command='esxcli --formatter=csv storage core device raid list --device naa.synthetic'
        for failure in (result('No LSU plugin',1),result('PhysicalLocation,\n',truncated=True),result('DifferentColumn,\nvalue,\n')):
            value=self.execute(Session('VMkernel',failures={CODE['DISCOVER']:result('',127),command:failure}))
            self.assertEqual(value['status'],'partial')
            self.assertEqual(value['data']['physical_drives'],[])
            self.assertEqual(value['data']['coverage']['physical_drives']['status'],'unknown')
            self.assertEqual(value['data']['coverage']['virtual_drives']['status'],'partial')

    def test_explicit_path_and_no_shell_injection(self):
        for cli in ('/opt/PERC/perccli64', '/opt/a-b/cli'):
            session = Session()
            self.assertEqual(self.execute(session, {'raid_cli': cli})['status'], 'partial')
            self.assertFalse(any(cmd == CODE['DISCOVER'] for cmd, _ in session.calls))
        for cli in ('/a;touch /tmp/no', 'perccli', '/a\nwhoami', '/a$(id)', ''):
            session = Session()
            with self.assertRaises(ValueError): self.execute(session, {'raid_cli': cli})
            self.assertEqual(session.calls, [])

    def test_configuration_bounds_checked_before_query(self):
        for values in ({'command_timeout_seconds': True}, {'command_timeout_seconds': 0},
                       {'command_timeout_seconds': float('nan')}, {'command_timeout_seconds': 121},
                       {'require_root': 'true'}):
            session = Session()
            with self.assertRaises(ValueError): self.execute(session, values)
            self.assertEqual(session.calls, [])

    def test_missing_cli_is_unknown_and_does_not_prove_no_raid(self):
        value = self.execute(Session(failures={CODE['DISCOVER']: result('', 127)}))
        self.assertEqual(value['status'], 'partial')
        self.assertEqual(value['data']['coverage']['physical_drives']['reason'], 'raid_cli_unavailable')
        self.assertEqual(value['data']['coverage']['md_arrays']['status'], 'complete')

    def test_truncation_and_nonzero_never_parsed_as_complete(self):
        command = shlex.join(CODE['LSBLK'])
        for failure in (result(DISKS, truncated=True), result(DISKS, 1), result('{invalid')):
            value = self.execute(Session(failures={command: failure}))
            self.assertEqual(value['status'], 'partial')
            self.assertEqual(value['data']['os_disks'], [])
            self.assertEqual(value['data']['coverage']['os_disks']['status'], 'unknown')
            self.assertIsNotNone(value['data']['probes'][1]['stdout'])

    def test_timeout_preserves_partial_stream_and_exception_type(self):
        error = TimeoutError('private untrusted exception text')
        error.result = result('partial evidence', 9)
        value = self.execute(Session(failures={shlex.join(CODE['LSBLK']): error}))
        probe = value['data']['probes'][1]
        self.assertEqual(probe['error'], 'TimeoutError')
        self.assertEqual(probe['stdout'], 'partial evidence')
        self.assertNotIn('private untrusted', json.dumps(value))

    def test_nested_controller_failure_is_not_success(self):
        invalid = {'Controllers': [controller({}, status='Failure')]}
        command = '/opt/lsi/perccli/perccli /call show all J'
        value = self.execute(Session(failures={command: result(invalid)}))
        self.assertEqual(value['status'], 'partial')
        self.assertEqual(value['data']['coverage']['controllers']['status'], 'unknown')
        self.assertEqual(value['data']['coverage']['virtual_drives']['status'], 'unknown')

    def test_multi_controller_partial_preserves_valid_data(self):
        value = copy.deepcopy(CTRL)
        value['Controllers'].append(controller({}, 1, 'Failure'))
        parsed = CODE['parse_raid'](value, 'controllers')
        self.assertEqual(len(parsed['records']), 1)
        self.assertTrue(parsed['errors'])
        command = '/opt/lsi/perccli/perccli /call show all J'
        run = self.execute(Session(failures={command: result(value)}))
        self.assertEqual(run['data']['coverage']['controllers']['status'], 'partial')
        self.assertEqual(len(run['data']['controllers']), 1)

    def test_unknown_or_empty_vendor_shapes_fail_conservatively(self):
        for value in ({'Controllers': []}, response({}), response({'unexpected': []}), {'Controllers': [None]}):
            with self.assertRaises(ValueError): CODE['parse_raid'](value, 'physical_drives')
        self.assertEqual(CODE['parse_raid'](response({'VD LIST': []}), 'virtual_drives')['records'], [])

    def test_md_race_preserves_arrays_and_partial_coverage(self):
        value = self.execute(Session(md={'arrays': [{'name': 'md0', 'degraded': '1'}], 'errors': ['/sys/block/md0/md/level']}))
        self.assertEqual(value['data']['md_arrays'][0]['degraded'], '1')
        self.assertEqual(value['data']['coverage']['md_arrays']['status'], 'partial')

    def test_esxi_uses_verified_core_actor_without_id_utility(self):
        session = Session('VMkernel', failures={'id -u': result('',127)})
        value = self.execute(session)
        self.assertEqual(value['status'], 'partial')
        self.assertFalse(any(cmd.startswith('id ') for cmd, _ in session.calls))
        r = recipe(session)
        for evidence in ({}, {'verified': False, 'actual': {'username':'root','effective_uid':0}},
                         {'verified': True, 'actual': {'username':'root','effective_uid':True}}):
            r.report = {'execution_identity': evidence}
            self.assertEqual(CODE['execute'](r)['reason_code'], 'identity_unverified')

    def test_esxi_nonroot_and_unsupported_platform(self):
        session = Session('VMkernel', '1000')
        self.assertEqual(self.execute(session)['reason_code'], 'root_required')
        self.assertEqual(len(session.calls), 1)
        session = Session('Darwin')
        self.assertEqual(self.execute(session)['status'], 'unsupported')
        self.assertEqual(len(session.calls), 1)

    def test_linux_acquires_shared_root_once_and_restores(self):
        session = Session(uid='1000')
        seen = []
        @contextlib.contextmanager
        def root():
            seen.append('enter')
            try: yield session.exec_command
            finally: seen.append('exit')
        r = recipe(session)
        r.root = root
        value = CODE['execute'](r)
        self.assertEqual(value['status'], 'partial')
        self.assertEqual(seen, ['enter', 'exit'])

    def test_optional_nonroot_preserves_selected_scope(self):
        value = self.execute(Session(uid='1000'), {'require_root': False})
        self.assertEqual(value['data']['privilege_scope'], 'selected_execution_account')

    def test_all_collection_failures_and_byte_bound(self):
        session = Session()
        with patch.dict(CODE['collect'].__globals__, probe=lambda *args, **kw: {
            'status': 'failed', 'error': 'missing', 'stdout': '', 'stderr': ''}):
            value = CODE['collect'](session.exec_command, 2, 'auto')
        self.assertEqual(value['status'], 'failed')
        evidence = []
        item = CODE['probe'](lambda *a, **kw: result('磁' * CODE['LIMIT']), 'synthetic', 2, evidence, 'limit')
        self.assertLessEqual(len(item['stdout'].encode()), CODE['LIMIT'])
        self.assertTrue(item['truncated'])
        self.assertEqual(item['status'], 'failed')

    def test_md_sysfs_and_missing_attribute(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            md = base/'md0/md'
            md.mkdir(parents=True)
            for name, text in {'level':'raid1','array_state':'clean','raid_disks':'2','degraded':'0'}.items():
                (md/name).write_text(text)
            member = md/'dev-sda1'
            member.mkdir()
            (member/'state').write_text('in_sync')
            value = MD['collect'](base)
            self.assertEqual(value['arrays'][0]['members'][0]['state'], 'in_sync')
            self.assertEqual(value['errors'], [])
            (md/'level').unlink()
            self.assertTrue(MD['collect'](base)['errors'])
            self.assertTrue(MD['collect'](base/'missing')['errors'])

    def test_discovery_never_imports_recipe_and_descriptor_schema(self):
        with patch('runpy.run_path', side_effect=AssertionError('no candidate execution')):
            self.assertTrue(choose(None, 'system/storage/inventory/disks-raid')['runnable'])
        with self.assertRaises(ConfigError): validate({}, META['retention']['data_schema'])


class StorageHealthTests(unittest.TestCase):
    execute = StorageTests.execute
    def healthy(self, expected=1):
        ctrl=copy.deepcopy(CTRL);ctrl['Controllers'][0]['Response Data']['VD LIST'][0]['State']='Optl'
        return self.execute(Session(failures={'/opt/lsi/perccli/perccli /call show all J':result(ctrl)}),
                            {'expected_disks':{'data':expected}})

    def test_expected_count_and_health_are_independent_checks(self):
        value=self.healthy()
        self.assertEqual(value['status'],'success')
        self.assertEqual(value['assessment']['label'],'STORAGE HEALTHY')
        self.assertEqual(value['data']['summary']['physical_disks']['count_status'],'MATCH')

    def test_count_mismatch_is_critical(self):
        for expected in (0,2):
            value=self.healthy(expected)
            self.assertEqual(value['status'],'partial')
            self.assertEqual(value['assessment']['severity'],'critical')
            self.assertEqual(value['data']['disk_groups'][0]['count_status'],'MISMATCH')

    def test_friendly_count_policy_rejects_ids_and_invalid_values(self):
        for value in ({'data':True},{'data':-1},{'data':1.5},{'data':'4'},{'RAID.Integrated.9-1':4},{'boot':2},[]):
            with self.assertRaises(ValueError):self.execute(values={'expected_disks':value})
        for value in (True,-1,'2'):
            with self.assertRaises(ValueError):self.execute(values={'expected_raids':value})
        with self.assertRaises(ValueError):self.execute(values={'boot_policy':'guess'})

    def test_lsu_members_cannot_verify_all_installed_disks(self):
        value=self.execute(Session('VMkernel',failures={CODE['DISCOVER']:result('',127)}),{'expected_disks':{'data':2}})
        self.assertEqual(value['data']['disk_groups'][0]['count_status'],'UNVERIFIED')
        self.assertIsNone(value['data']['summary']['physical_disks']['total'])
        self.assertEqual(value['data']['summary']['physical_disks']['health'],'UNKNOWN')
        self.assertEqual(value['assessment']['severity'],'critical')

    def test_data_and_boot_are_both_queried(self):
        csv='Device,IsLocal,DeviceType,IsBootDevice,NumberofPhysicalDrives,\nnaa.synthetic,true,Direct-Access ,false,2,\nnaa.boot,true,Direct-Access ,true,unknown,\n'
        session=Session('VMkernel',failures={CODE['DISCOVER']:result('',127),
            'esxcli --formatter=csv storage core device list':result(csv),
            'esxcli --formatter=csv storage core device raid list --device naa.boot':result('unsupported',1)})
        value=self.execute(session,{'expected_disks':{'data':2},'boot_policy':'mirrored-ssd-pair'})
        self.assertTrue(any('--device naa.boot' in command for command,_ in session.calls))
        self.assertEqual(value['data']['scope']['excluded_devices'],[])
        self.assertEqual(value['status'],'partial')

    def test_historical_scope_and_policy_are_not_reinterpreted(self):
        data=self.healthy()['data'];data['policy']={'include_boot_devices':False,'expected_physical_disks':1}
        before=copy.deepcopy(data)
        rendered='\n'.join(vault_content.disks_raid_lines(data))
        self.assertIn('historical attempt: boot devices excluded',rendered)
        self.assertEqual(data,before)

    def test_predictive_errors_override_online(self):
        for details in ({'Predictive Failure Count':1},{'Media Error Count':'2'},
                        {'S.M.A.R.T alert flagged by drive':'Yes'}):
            row=copy.deepcopy(CODE['parse_raid'](PD,'physical_drives')['records'][0]);row['details'].update(details)
            self.assertEqual(CODE['drive_health'](row)[0],'UNHEALTHY')
        self.assertEqual(CODE['drive_health']({'summary':{'State':'Onln'},'details':{'Predictive Failure Count':'bad'}})[0],'UNKNOWN')

    def test_md_degraded_and_sync_are_distinct(self):
        self.assertEqual(CODE['md_health']({'degraded':'1','array_state':'active','sync_action':'idle'})[0],'UNHEALTHY')
        self.assertEqual(CODE['md_health']({'degraded':'0','array_state':'active','sync_action':'resync'})[0],'UNKNOWN')
        self.assertEqual(CODE['md_health']({'degraded':'0','array_state':'clean','sync_action':'idle'})[0],'HEALTHY')

    def test_renderer_stays_narrow(self):
        data=self.healthy()['data'];data['os_disks'][0]['details']={f'Field{i}':'PERC synthetic model' for i in range(50)}
        rendered='\n'.join(vault_content.disks_raid_lines(data));self.assertIn('PERC synthetic model',rendered)
        self.assertNotIn('P E R C',rendered)
        self.assertTrue(all(line.count('|')<=6 for line in rendered.splitlines() if line.startswith('|')))


def racadm_text(records):
    return 'Please wait while the raid config data is being fetched.\n' + '\n\n'.join(
        identity+'\n'+'\n'.join('   '+key+' = '+str(value) for key,value in fields.items()) for identity,fields in records)


def racadm_fixture():
    data_id, boot_id = 'RAID.Integrated.9-1', 'AHCI.Slot.9-1'
    controllers=[(data_id,{'Name':'Synthetic PERC','Status':'Ok','RollupStatus':'Ok'}),
                 (boot_id,{'Name':'BOSS-S1 (Synthetic Slot)','Status':'Ok','RollupStatus':'Ok'}),
                 ('AHCI.Integrated.9-1',{'Name':'Empty synthetic controller','Status':'Unknown','RollupStatus':'Unknown'})]
    disks=[]
    for index in range(4):
        disks.append((f'Disk.Bay.{index}:Enclosure.Internal.9-1:{data_id}',
                      {'Name':f'Synthetic disk {index}','Status':'Ok','RollupStatus':'Ok','State':'Online',
                       'Size':'100.500 GB','MediaType':'HDD','FailurePredicted':'NO'}))
    for index in range(2):
        disks.append((f'Disk.Direct.{index}-{index}:{boot_id}',
                      {'Name':f'Synthetic SSD {index}','Status':'Ok','RollupStatus':'Ok','State':'Online',
                       'Size':'20.250 GB','MediaType':'SSD','FailurePredicted':'NO'}))
    volumes=[('Disk.Virtual.0:'+data_id,{'Name':'Synthetic data','Status':'Ok','RollupStatus':'Ok','State':'Online','Layout':'Raid-10','Size':'201.000 GB'}),
             ('Disk.Virtual.0:'+boot_id,{'Name':'Synthetic boot','Status':'Ok','RollupStatus':'Ok','State':'Online','Layout':'Raid-1','Size':'20.000 GB'})]
    return {'controllers':controllers,'pdisks':disks,'vdisks':volumes}


class RacadmSession(Session):
    def __init__(self, records=None, failures=None, platform='VMkernel', md=None):
        super().__init__(platform,failures=failures,md=md)
        self.records=copy.deepcopy(records or racadm_fixture())
    def exec_command(self,command,**kwargs):
        if isinstance(command,list):
            command=command[2] if command[:2]==['/bin/sh','-c'] else shlex.join(command)
        if command in self.failures:
            return super().exec_command(command,**kwargs)
        if command==CODE['DISCOVER']:
            self.calls.append((command,kwargs));return result('/bin/racadm\n')
        argv=shlex.split(command)
        if argv[:3]==['/bin/racadm','storage','get']:
            self.calls.append((command,kwargs));return result(racadm_text(self.records[argv[3]]))
        return super().exec_command(command,**kwargs)


class RacadmTests(unittest.TestCase):
    execute=StorageTests.execute
    def run_fixture(self,records=None,values=None,**kwargs):
        return self.execute(RacadmSession(records,**kwargs),values if values is not None else
                            {'expected_disks':{'data':4},'boot_policy':'mirrored-ssd-pair','expected_raids':2})

    def test_friendly_inventory_counts_do_not_require_fqdd(self):
        value=self.run_fixture();data=value['data']
        self.assertEqual(value['status'],'success')
        self.assertEqual(data['summary']['physical_disks']['total'],6)
        self.assertEqual(data['summary']['raid_volumes']['total'],2)
        self.assertEqual([g['id'] for g in data['disk_groups']],['data','boot'])
        self.assertEqual([g['expected'] for g in data['disk_groups']],[4,2])
        self.assertEqual(data['policy']['expected_disks'],{'data':4})
        self.assertNotIn('RAID.Integrated.9-1',data['policy']['expected_disks'])
        self.assertEqual([v['capacity'] for v in data['virtual_drives']],['201.000 GB','20.000 GB'])
        rendered='\n'.join(vault_content.disks_raid_lines(data))
        for token in ('Physical disks — Data','Physical disks — Boot','RAID.Integrated.9-1','AHCI.Slot.9-1','100.500 GB','20.250 GB','raid-10','raid-1'):
            self.assertIn(token,rendered)
        self.assertTrue(all(line.count('|')<=6 for line in rendered.splitlines() if line.startswith('|')))

    def test_hardware_ids_can_change_without_changing_configuration(self):
        records=racadm_fixture();rename={'RAID.Integrated.9-1':'RAID.Slot.8-7','AHCI.Slot.9-1':'AHCI.Slot.3-4'}
        for kind,rows in records.items():
            for index,(identity,fields) in enumerate(rows):
                for old,new in rename.items():identity=identity.replace(old,new)
                rows[index]=(identity,fields)
        value=self.run_fixture(records)
        self.assertEqual(value['status'],'success')
        self.assertEqual(value['data']['policy']['expected_disks'],{'data':4})

    def test_zero_expected_data_disks_with_boot_pair(self):
        records=racadm_fixture();records['pdisks']=records['pdisks'][4:];records['vdisks']=records['vdisks'][1:]
        value=self.run_fixture(records,{'expected_disks':{'data':0},'boot_policy':'mirrored-ssd-pair','expected_raids':1})
        self.assertEqual(value['data']['disk_groups'][0]['count_status'],'MATCH')
        self.assertEqual(value['status'],'success')

    def test_spare_ready_disk_counts_without_being_online(self):
        records=racadm_fixture();records['pdisks'][3][1].update(State='Ready',Hotspare='YES')
        value=self.run_fixture(records);disk=value['data']['physical_drives'][3]
        self.assertEqual(disk['usage'],'spare');self.assertEqual(disk['health'],'HEALTHY')
        self.assertEqual(value['data']['disk_groups'][0]['observed'],4)
        self.assertEqual(value['status'],'success')

    def test_unconfigured_and_standalone_disks_are_not_missing(self):
        records=racadm_fixture();records['pdisks'][0][1]['State']='Ready';records['pdisks'][1][1]['State']='Non-RAID'
        value=self.run_fixture(records)
        self.assertEqual([r['usage'] for r in value['data']['physical_drives'][:2]],['unconfigured','standalone'])
        self.assertEqual(value['data']['disk_groups'][0]['count_status'],'MATCH')
        self.assertEqual(value['data']['disk_groups'][0]['disk_health'],'HEALTHY')

    def test_physical_count_and_health_do_not_depend_on_raid_query_success(self):
        session=RacadmSession(failures={'/bin/racadm storage get vdisks -o':result('denied',1)})
        value=self.execute(session,{'expected_disks':{'data':4},'boot_policy':'mirrored-ssd-pair','expected_raids':2})
        self.assertEqual(value['data']['summary']['physical_disks']['total'],6)
        self.assertEqual(value['data']['summary']['physical_disks']['count_status'],'MATCH')
        self.assertEqual(value['data']['summary']['physical_disks']['health'],'HEALTHY')
        self.assertEqual(value['data']['summary']['raid_volumes']['count_status'],'UNVERIFIED')
        self.assertEqual(value['status'],'partial')

    def test_missing_controller_metadata_does_not_erase_physical_inventory(self):
        value=self.run_fixture(failures={'/bin/racadm storage get controllers -o':result('denied',1)})
        self.assertEqual(value['data']['summary']['physical_disks']['total'],6)
        self.assertEqual(value['data']['summary']['physical_disks']['health'],'HEALTHY')
        self.assertEqual(value['data']['summary']['physical_disks']['count_status'],'UNVERIFIED')
        self.assertEqual(value['assessment']['severity'],'critical')

    def test_all_standalone_inventory_with_no_raid(self):
        records=racadm_fixture();records['controllers']=records['controllers'][:1];records['pdisks']=records['pdisks'][:4]
        for row in records['pdisks']:row[1]['State']='Non-RAID'
        session=RacadmSession(records,failures={'/bin/racadm storage get vdisks -o':result('ERROR: STOR0104 : No virtual disks are displayed.\n',1)})
        value=self.execute(session,{'expected_disks':{'data':4},'expected_raids':0})
        self.assertEqual(value['status'],'success')
        self.assertEqual(value['data']['summary']['raid_volumes']['total'],0)
        self.assertEqual(value['data']['summary']['raid_volumes']['health'],'NOT CONFIGURED')
        self.assertEqual(value['data']['summary']['physical_disks']['total'],4)

    def test_known_empty_raid_message_does_not_hide_other_errors(self):
        failure='ERROR: STOR0104 : No virtual disks are displayed.\nERROR: permission denied\n'
        stderr_failure=result('ERROR: STOR0104 : No virtual disks are displayed.\n',1)
        stderr_failure.stderr='ERROR: permission denied'
        for failed in (result(failure,1),stderr_failure):
            value=self.run_fixture(failures={'/bin/racadm storage get vdisks -o':failed})
            self.assertEqual(value['data']['coverage']['virtual_drives']['status'],'unknown')
            self.assertEqual(value['assessment']['severity'],'critical')

    def test_multiple_controllers_share_one_data_count(self):
        records=racadm_fixture();identity='RAID.Slot.8-1';records['controllers'].append((identity,{'Name':'Synthetic adapter','Status':'Ok','RollupStatus':'Ok'}))
        records['pdisks'].append(('Disk.Bay.0:Enclosure.Internal.8-1:'+identity,{'Status':'Ok','RollupStatus':'Ok','State':'Ready','Hotspare':'Global','Size':'100.500 GB'}))
        value=self.run_fixture(records,{'expected_disks':{'data':5},'boot_policy':'mirrored-ssd-pair','expected_raids':2})
        group=value['data']['disk_groups'][0]
        self.assertEqual(group['observed'],5);self.assertEqual(group['count_status'],'MATCH')
        self.assertEqual(len(group['controller_ids']),2)
        self.assertEqual(value['status'],'success')

    def test_boot_pair_or_entire_boot_controller_missing_is_critical_without_ids(self):
        for controller_missing in (False,True):
            records=racadm_fixture();records['pdisks']=records['pdisks'][:4];records['vdisks']=records['vdisks'][:1]
            if controller_missing:records['controllers']=[r for r in records['controllers'] if 'BOSS-S1' not in r[1]['Name']]
            value=self.run_fixture(records);boot=value['data']['disk_groups'][1]
            self.assertEqual(boot['id'],'boot');self.assertEqual(boot['expected'],2)
            self.assertEqual(boot['count_status'],'MISMATCH')
            self.assertEqual(value['assessment']['severity'],'critical')

    def test_boot_health_is_always_included(self):
        for field,bad in (('State','Offline'),('Status','Critical'),('FailurePredicted','YES')):
            records=racadm_fixture();records['pdisks'][-1][1][field]=bad
            value=self.run_fixture(records)
            self.assertEqual(value['data']['disk_groups'][0]['disk_health'],'HEALTHY')
            self.assertEqual(value['data']['disk_groups'][1]['disk_health'],'UNHEALTHY')
            self.assertEqual(value['status'],'partial')

    def test_ready_boot_disks_do_not_replace_a_required_mirror(self):
        records=racadm_fixture();records['vdisks']=records['vdisks'][:1]
        for row in records['pdisks'][4:]:row[1]['State']='Ready'
        value=self.run_fixture(records)
        self.assertEqual(value['data']['disk_groups'][1]['count_status'],'MATCH')
        self.assertEqual(value['data']['summary']['raid_volumes']['health'],'UNHEALTHY')
        self.assertEqual(value['status'],'partial')

    def test_data_count_mismatch_and_raid_count_mismatch_are_separate(self):
        value=self.run_fixture(values={'expected_disks':{'data':5},'boot_policy':'mirrored-ssd-pair','expected_raids':2})
        self.assertEqual(value['data']['disk_groups'][0]['count_status'],'MISMATCH')
        self.assertEqual(value['data']['summary']['raid_volumes']['count_status'],'MATCH')
        value=self.run_fixture(values={'expected_disks':{'data':4},'boot_policy':'mirrored-ssd-pair','expected_raids':3})
        self.assertEqual(value['data']['summary']['physical_disks']['count_status'],'MATCH')
        self.assertEqual(value['data']['summary']['raid_volumes']['count_status'],'MISMATCH')
        self.assertEqual(value['assessment']['severity'],'critical')

    def test_boot_mirror_requires_raid1_not_just_an_online_volume(self):
        for level, health in (('Raid-0', 'UNHEALTHY'), ('Raid-10', 'UNHEALTHY'),
                              ('Unknown', 'UNKNOWN'), (None, 'UNKNOWN')):
            records = racadm_fixture()
            if level is None:
                records['vdisks'][-1][1].pop('Layout')
            else:
                records['vdisks'][-1][1]['Layout'] = level
            value = self.run_fixture(records)
            self.assertEqual(value['data']['summary']['physical_disks']['count_status'], 'MATCH')
            self.assertEqual(value['data']['summary']['raid_volumes']['health'], health)
            self.assertEqual(value['status'], 'partial')

    def test_auto_boot_policy_requires_a_mirror_for_each_boss_controller(self):
        records = racadm_fixture()
        identity = 'AHCI.Slot.8-1'
        records['controllers'].append((identity, {'Name': 'BOSS-S1', 'Status': 'Ok', 'RollupStatus': 'Ok'}))
        for index in range(2):
            records['pdisks'].append((f'Disk.Direct.{index}-{index}:{identity}',
                dict(records['pdisks'][-1][1])))
        value = self.run_fixture(records, {'expected_disks': {'data': 4}})
        self.assertEqual(value['data']['disk_groups'][1]['count_status'], 'MATCH')
        self.assertEqual(value['data']['summary']['raid_volumes']['health'], 'UNHEALTHY')
        self.assertEqual(value['status'], 'partial')

        records['vdisks'].append(('Disk.Virtual.0:' + identity, dict(records['vdisks'][-1][1])))
        self.assertEqual(self.run_fixture(records, {'expected_disks': {'data': 4}})['status'], 'success')

    def test_auto_policy_uses_identified_boss_not_arbitrary_ssd(self):
        value=self.run_fixture(values={'expected_disks':{'data':4}})
        self.assertEqual(value['data']['disk_groups'][1]['expected'],2)
        records=racadm_fixture();records['controllers'][1][1]['Name']='Generic synthetic SSD controller'
        value=self.run_fixture(records,{'expected_disks':{'data':6}})
        self.assertEqual(len(value['data']['disk_groups']),1)
        self.assertEqual(value['data']['disk_groups'][0]['observed'],6)

    def test_malformed_duplicate_error_truncated_and_missing_fields(self):
        fixture=racadm_text(racadm_fixture()['pdisks'])
        for output in ('ERROR: storage unavailable\n',fixture+'\nStatus = Ok\n',fixture+'\n'+fixture,'Disk.Bay.0:RAID.Integrated.9-1\n'):
            with self.assertRaises(ValueError):CODE['parse_racadm'](output,'physical_drives')
        value=self.run_fixture(failures={'/bin/racadm storage get pdisks -o':result(fixture,truncated=True)})
        self.assertEqual(value['data']['coverage']['physical_drives']['status'],'unknown')
        self.assertEqual(value['assessment']['severity'],'critical')
        records=racadm_fixture();records['pdisks'][0][1].pop('Size');records['vdisks'][0][1].pop('Layout')
        value=self.run_fixture(records)
        self.assertIsNone(value['data']['physical_drives'][0]['capacity'])
        self.assertIsNone(value['data']['virtual_drives'][0]['raid_level'])

    def test_md_and_controller_health_are_independent_of_physical_counts(self):
        value=self.run_fixture(platform='Linux',md={'arrays':[{'name':'md9','degraded':'1','array_state':'active','sync_action':'idle'}],'errors':[]})
        self.assertEqual(value['data']['summary']['physical_disks']['count_status'],'MATCH')
        self.assertEqual(value['data']['summary']['health'],'UNHEALTHY')
        self.assertEqual(value['data']['summary']['raid_volumes']['total'],3)
        records=racadm_fixture();records['controllers'][1][1]['RollupStatus']='Unknown'
        self.assertEqual(self.run_fixture(records)['status'],'partial')


class StorageRetentionTests(unittest.TestCase):
    setUp = vault_fixtures.VaultTests.setUp
    enable = vault_fixtures.VaultTests.enable

    def test_runner_preserves_storage_data_and_retention_receipts(self):
        import recipe_runner
        from test_core_api import Actor
        class StorageActor(Actor):
            def __init__(self):
                super().__init__('root', 0)
                self.storage = Session('VMkernel')
            def exec_command(self, argv, **kwargs):
                if isinstance(argv, (tuple, list)) and argv[:1] == ['id']:
                    return super().exec_command(argv, **kwargs)
                command = (argv[2] if argv[:2] == ['/bin/sh', '-c'] else shlex.join(argv)) if isinstance(argv, (tuple, list)) else argv
                return self.storage.exec_command(command, **kwargs)
        self.enable()
        report, path = recipe_runner.run(self.root, 'node', recipe='system/storage/inventory/disks-raid',
                                        session_class=StorageActor, runtime={'verification':'synthetic-transport'})
        self.assertEqual(report['status'], 'partial', report)
        self.assertEqual(report['retention']['status'], 'stored', report)
        self.assertTrue(path.is_file())
        self.assertEqual(report['data']['platform'], 'esxi')

    def test_retention_replay_and_readable_vault(self):
        self.enable()
        execution = CODE['execute'](recipe())
        raw = {**execution, 'host_id':'node', 'completed_at':execution['data']['observed_at'],
               'evidence_kind':'local', 'source_observation_id':str(uuid4()),
               'recipe':{'id':'disks-raid','version':META['version'],'reference':'system/storage/inventory/disks-raid'},
               'retention_snapshot':snapshot(META, DIRECTORY), 'execution_access_mode':'read'}
        receipt = store.retain_general(self.root, raw, META, DIRECTORY)
        self.assertEqual(receipt['status'], 'stored', receipt)
        record = store.show(self.root, receipt['record_id'])
        self.assertEqual(record['data']['physical_drives'][0]['details']['SN'], 'SYNTHETIC-SERIAL')
        for current in (False, True):
            rendered = vault_content.render_observation(record, current=current)
            self.assertIn('SYNTHETIC-SERIAL', rendered)
            self.assertIn('Storage health', rendered)
        path = self.root/'raw.json'
        path.write_text(json.dumps(raw))
        with patch('runpy.run_path', side_effect=AssertionError('no candidate normalizer')):
            replay = ingest(self.root, [path])
        self.assertEqual(replay['status'], 'success', replay)


if __name__ == '__main__':
    unittest.main()
