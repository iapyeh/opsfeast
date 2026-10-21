"""Public synthetic inventory jobs, utility, schedules and retention regressions."""
from inventory_output_fixture import framed
from contextlib import contextmanager, redirect_stdout
import copy
import io
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import inventory_jobs as service
import inventory_schedule as schedule
import inventory_cron as cron
import inventory_cli as cli
import retention_store as store
import retention_replay as replay
from opsfeast import ConfigError
import test_host_vault as vault_fixtures


class Actor:
    def __init__(self):
        self.commands = []
        self.fail = set()
        self.percent = 82
    def exec_command(self,argv,**kwargs):
        script = argv[-1]
        self.commands.append(script)
        code = 127 if any(command in script for command in self.fail) else 0
        if 'uname -s' in script: text='Linux\n'
        elif 'uname -n' in script:text='synthetic-node\n'
        elif 'uname -r' in script:text='6.1\n'
        elif 'uname -v' in script:text='synthetic build\n'
        elif 'uname -m' in script:text='x86_64\n'
        elif 'df -Pk' in script:text=f'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/example 100 82 18 {self.percent}% /\n'
        elif 'df -Pi' in script:text='Filesystem Inodes IUsed IFree IUse% Mounted on\n/dev/example 100 2 98 2% /\n'
        elif '/proc/meminfo' in script:text='MemTotal: 1000 kB\nMemAvailable: 500 kB\nSwapTotal: 100 kB\nSwapFree: 25 kB\n'
        elif '/proc/uptime' in script:text='123.4 20\n'
        elif 'ip -j address' in script:text=json.dumps([{'ifname':'eth0','address':'02:00:00:00:00:01','mtu':1500,'operstate':'UP','addr_info':[{'local':'192.0.2.1','prefixlen':24},{'local':'2001:db8::1','prefixlen':64}]}])
        elif '/proc/net/dev' in script:text='Inter-| Receive | Transmit\n eth0: 100 1 2 3 0 0 0 0 200 4 5 6 0 0 0 0\n'
        elif '/proc/loadavg' in script:text='0.1 0.2 0.3 1/100 5\n'
        elif '/etc/os-release' in script:text='NAME="Synthetic Distribution"\nVERSION_ID="1.0"\n'
        else:text=''
        return SimpleNamespace(stdout=framed(script,text+f'\n__OPSFEAST_EXIT_{code}\n'),stderr='',exitcode=0)


class InventoryJobTests(unittest.TestCase):
    setUp = vault_fixtures.VaultTests.setUp
    enable = vault_fixtures.VaultTests.enable

    def acquire(self,actor,**kwargs):
        @contextmanager
        def connected(config,host,session_class,timeout,report):
            yield actor
        @contextmanager
        def chosen(session,config,host,timeout,report,**options):
            report.update(actual_identity={'username':'synthetic','effective_uid':1000},mode='user')
            yield actor
        with patch.object(service,'connected',connected), patch.object(service,'collection_actor',chosen):
            return service.collect_host(self.root,'node',session_class=Actor,**kwargs)

    def test_no_store_only_selected_probe_no_files_or_schedule_state(self):
        before = {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        actor=Actor()
        result=self.acquire(actor,properties=['storage.filesystems.used_percent'])
        self.assertEqual(result['status'],'success',result)
        self.assertEqual(len(actor.commands),2)
        self.assertTrue(any('df -Pk' in c for c in actor.commands))
        self.assertFalse(any('/proc/' in c for c in actor.commands))
        self.assertIsNone(result['result_path'])
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        self.assertEqual(result['groups'][0]['samples'][0]['value'],82)

    def test_save_manual_comparison_retains_equal_samples_separate_histories(self):
        self.enable()
        actor=Actor()
        first=self.acquire(actor,properties=['storage.filesystems.used_percent'],save=True)
        actor.percent=40
        second=self.acquire(actor,properties=['storage.filesystems.used_percent'],save=True,note='After synthetic log cleanup')
        third=self.acquire(actor,properties=['storage.filesystems.used_percent'],save=True)
        for result in (first,second,third):
            self.assertEqual(result['retention']['status'],'stored',result)
            self.assertEqual(result['content_update']['status'],'success',result)
        records=store.query(self.root)['records']
        self.assertEqual(len(records),3)
        values=[r['data']['groups'][0]['samples'][0]['value'] for r in records]
        self.assertEqual(values,[82,40,40])
        self.assertEqual(len({r['record_id'] for r in records}),3)
        self.assertEqual(records[1]['data']['note'],'After synthetic log cleanup')
        self.assertFalse((self.root/'.inventory-state.json').exists())
        self.assertEqual(replay.ingest(self.root,[Path(second['result_path'])])['files'][0]['status'],'already_stored')

    def test_failed_probe_leaves_null_and_reason_no_old_fill(self):
        self.enable()
        actor=Actor()
        self.acquire(actor,properties=['storage.filesystems.used_percent'],save=True)
        actor.fail.add('df -Pk')
        result=self.acquire(actor,properties=['storage.filesystems.used_percent'],save=True)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['retention']['status'],'stored',result)
        sample=result['groups'][0]['samples'][0]
        self.assertIsNone(sample['value'])
        self.assertEqual(sample['reason_code'],'command_not_found')
        self.assertEqual(len(store.query(self.root)['records']),2)
        self.assertEqual(replay.ingest(self.root,[Path(result['result_path'])])['files'][0]['status'],'already_stored')

    def test_empty_enumeration_is_distinct_from_failure(self):
        actor=Actor()
        result=self.acquire(actor,properties=['network.listening_endpoints'])
        self.assertEqual(result['groups'][0]['samples'][0]['value'],[])
        self.assertTrue(result['groups'][0]['coverage'][0]['complete'])

    def test_shared_probe_runs_once_and_preserves_source_times(self):
        result=self.acquire(Actor(),properties=['storage.filesystems.used_percent','storage.filesystems.available_bytes'])
        samples=result['groups'][0]['samples']
        self.assertEqual(len(samples),2)
        self.assertEqual(samples[0]['source_id'],samples[1]['source_id'])
        self.assertEqual(samples[0]['observed_at'],samples[1]['observed_at'])

    def test_standard_ip_family_and_interface_state_projection(self):
        actor=Actor()
        result=self.acquire(actor,properties=['network.ipv4.address','network.ipv6.address'])
        samples=result['groups'][0]['samples']
        self.assertEqual([s['value'] for s in samples],['192.0.2.1','2001:db8::1'])
        self.assertEqual(len(actor.commands),2)
        state=self.acquire(Actor(),properties=['network.interfaces.state'])
        self.assertEqual(state['groups'][0]['samples'][0]['value'],'up')
        self.assertEqual(len(state['groups'][0]['samples']),1)

    def test_kernel_os_name_not_distribution_name(self):
        result=self.acquire(Actor(),properties=['system.kernel_name','system.system_name'])
        specs=service.catalog()['properties']
        self.assertEqual(specs['system.kernel_name']['module'],'ietf-system')
        self.assertEqual(specs['system.system_name']['module'],'opsfeast-inventory')
        self.assertEqual({s['property']:s['value'] for s in result['groups'][0]['samples']},
                         {'system.kernel_name':'Linux','system.system_name':'Synthetic Distribution'})

    def test_unknown_property_or_job_rejected_before_connect(self):
        with patch.object(service,'connected',side_effect=AssertionError('must not connect')):
            for options in ({'properties':['bogus']},{'jobs':['bogus']},{'jobs':['system-runtime'],'properties':['system.hostname']}):
                with self.subTest(options=options),self.assertRaises(ConfigError):
                    service.collect_host(self.root,'node',**options)

    def test_due_failure_advances_normal_interval_without_retry(self):
        self.enable()
        with (self.root/'hosts.yaml').open('a') as stream:
            stream.write('default:\n  recipes:\n    system/inventory/overview: {enabled: true}\n')
        (self.root/'inventory.yaml').write_text(json.dumps({'schema_version':'0.1.0','defaults':{},'hosts':{'node':{'enabled':True,'jobs':{}}}}))
        calls=[]
        def fail(root,host,**options):
            calls.append(options['jobs'])
            return {'host_id':host,'status':'failed','groups':[]}
        first=service.dispatch(self.root,at='2026-10-20T00:00:00+00:00',collect=fail)
        self.assertEqual(len(calls),1)
        self.assertNotIn('hardware-sensors',calls[0])
        second=service.dispatch(self.root,at='2026-10-20T00:00:30+00:00',collect=fail)
        self.assertEqual(second['hosts'],[])
        service.dispatch(self.root,at='2026-10-20T00:01:00+00:00',collect=fail)
        self.assertEqual(calls[1],['resource-metrics'])

    def test_no_enabled_hosts_no_collection_and_dry_run_no_writes(self):
        before=set(self.root.rglob('*'))
        with patch.object(service,'collect_host',side_effect=AssertionError('no collection')):
            result=service.dispatch(self.root,dry_run=True)
        self.assertEqual(result['hosts'],[])
        self.assertEqual(before,set(self.root.rglob('*')))

    def test_interval_override_and_validation(self):
        data=service.catalog()
        value={'defaults':{'storage-capacity':{'interval':'1h'}},'hosts':{'node':{'jobs':{'storage-capacity':{'interval':'5m'}}}}}
        self.assertEqual(schedule.effective(data,value,'node')['storage-capacity']['interval'],300)
        for invalid in (True,0,-1,59,float('nan'),'2x','0m'):
            with self.subTest(value=invalid),self.assertRaises(ConfigError):schedule.interval(invalid)
        self.assertEqual(schedule.interval('7d'),604800)

    def test_dispatch_lock_prevents_overlaps(self):
        with schedule.lock(self.root) as first:
            self.assertTrue(first)
            self.assertEqual(service.dispatch(self.root)['reason_code'],'dispatcher_already_running')

    def test_state_and_config_symlinks_rejected(self):
        for name,operation in [('.inventory-state.json',lambda:schedule.read_state(self.root)),
                               ('inventory.yaml',lambda:schedule.settings(self.root,service.catalog(),{'node':{}})),
                               ('.inventory-dispatch.lock',lambda:service.dispatch(self.root))]:
            path=self.root/name
            path.symlink_to(self.root/'hosts.yaml')
            with self.subTest(name=name),self.assertRaises(ConfigError):operation()
            path.unlink()

    def test_schema_bound_definitions_and_sample_source_checks(self):
        self.enable()
        raw=self.acquire(Actor(),properties=['storage.filesystems.used_percent'],save=True)
        normalizer=runpy.run_path(str(service.BUNDLE/'job_retention.py'))
        data=store.query(self.root)['records'][0]['data']
        bad=copy.deepcopy(data)
        bad['groups'][0]['samples'][0]['observed_at']='2000-01-01T00:00:00.000000+00:00'
        with self.assertRaises(ConfigError):normalizer['validate'](bad)
        bad=copy.deepcopy(data)
        bad['groups'][0]['samples'][0]['value']=101
        with self.assertRaises(ConfigError):normalizer['validate'](bad)
        bad=copy.deepcopy(data)
        bad['definition_sha256']='0'*64
        with self.assertRaises(ConfigError):normalizer['validate'](bad)

    def test_counter_samples_use_standard_nodes_and_entity_keys(self):
        result=self.acquire(Actor(),properties=['metrics.interfaces.in_octets','metrics.interfaces.out_octets'])
        samples=result['groups'][0]['samples']
        self.assertEqual([s['value'] for s in samples],[100,200])
        self.assertEqual(samples[0]['keys'],{'name':'eth0'})
        self.assertEqual(service.catalog()['properties'][samples[0]['property']]['module'],'ietf-interfaces')

    def test_all_help_is_without_profile_connections_or_writes(self):
        with patch.object(cli,'resolve_root',side_effect=AssertionError('help must not resolve')):
            for command in ('describe','query','run','configure','status','dispatch','cron'):
                with redirect_stdout(io.StringIO()),self.assertRaises(SystemExit) as result:
                    cli.main([command,'--help'])
                self.assertEqual(result.exception.code,0)

    def test_public_catalog_matches_executable_definition(self):
        generated=runpy.run_path(str(service.BUNDLE/'properties.py'))['catalog']()
        self.assertEqual(generated,service.catalog())
        self.assertEqual(len(generated['jobs']),11)
        self.assertEqual(json.loads((service.BUNDLE/'job-retention.schema.json').read_text())['property_catalog'],generated)

    def test_latest_view_preserves_other_properties_and_failed_gaps(self):
        self.enable()
        actor=Actor()
        first=self.acquire(actor,properties=['storage.filesystems.used_percent','storage.filesystems.available_bytes'],save=True)
        actor.percent=40
        second=self.acquire(actor,properties=['storage.filesystems.used_percent'],save=True)
        view=service.latest_groups(store.query(self.root)['records'])
        samples=[s for group in view for s in group['samples']]
        self.assertEqual({s['property']:s['value'] for s in samples},
                         {'storage.filesystems.used_percent':40,'storage.filesystems.available_bytes':18*1024})
        self.assertEqual(len({g['source_record_id'] for g in view}),2)
        actor.fail.add('df -Pk')
        third=self.acquire(actor,properties=['storage.filesystems.used_percent'],save=True)
        view=service.latest_groups(store.query(self.root)['records'])
        values={s['property']:s['value'] for g in view for s in g['samples']}
        self.assertIsNone(values['storage.filesystems.used_percent'])
        self.assertEqual(values['storage.filesystems.available_bytes'],18*1024)

    def test_connection_failure_is_saved_as_an_attempt_without_fake_values(self):
        self.enable()
        @contextmanager
        def broken(*args,**kwargs):
            raise OSError('synthetic secret must not be retained')
            yield
        with patch.object(service,'connected',broken):
            result=service.collect_host(self.root,'node',properties=['system.hostname'],save=True,session_class=Actor)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['retention']['status'],'stored',result)
        self.assertNotIn('synthetic secret',Path(result['result_path']).read_text())
        self.assertIsNone(result['groups'][0]['samples'][0]['value'])

    def test_configure_changes_settings_without_collection_or_auto_enabling_host(self):
        with patch.object(service,'collect_host',side_effect=AssertionError('no collection')),redirect_stdout(io.StringIO()):
            code=cli.main(['configure','--root',str(self.root),'--host','node','--job','storage-capacity','--interval','5m','--json'])
        self.assertEqual(code,0)
        data=schedule.settings(self.root,service.catalog(),{'node':{}})
        self.assertFalse(data['hosts']['node']['enabled'])
        self.assertEqual(data['hosts']['node']['jobs']['storage-capacity']['interval'],300)

    def test_shared_memory_and_swap_probe_has_one_source(self):
        actor=Actor()
        result=self.acquire(actor,properties=['metrics.memory_available_bytes','storage.swap.used_bytes'])
        # Shared new probes are cached across job boundaries.
        self.assertEqual(sum('/proc/meminfo' in command for command in actor.commands),1)
        values={s['property']:s['value'] for g in result['groups'] for s in g['samples']}
        self.assertEqual(values['metrics.memory_available_bytes'],500*1024)
        self.assertEqual(values['storage.swap.used_bytes'],75*1024)

    def test_standard_prefix_limits_and_public_memory_mapping(self):
        from inventory_property_types import matches
        data=service.catalog()['properties']
        self.assertTrue(matches(data['network.ipv4.prefix_length'],32))
        self.assertFalse(matches(data['network.ipv4.prefix_length'],33))
        self.assertFalse(matches(data['network.ipv6.address'],'fe80::1%eth0'))
        self.assertTrue(matches(data['system.hostname'],'synthetic-node.example'))
        self.assertFalse(matches(data['system.hostname'],'name with spaces'))
        self.assertEqual(data['hardware.memory_total_bytes']['module'],'openconfig-system')
        self.assertIn('address',data['network.ipv6.address']['key_paths'])

    def test_parallel_dispatch_is_bounded_and_attempts_precede_connections(self):
        self.enable()
        import threading
        (self.root/'hosts.yaml').write_text(json.dumps({'default':{'recipes':{'system/inventory/overview':{'enabled':True}}},'hosts':{name:{'connection':{'local':True}} for name in ('node','other')}}))
        data=service.catalog()
        defaults={job:{'enabled':job=='system-runtime'} for job in data['jobs']}
        (self.root/'inventory.yaml').write_text(json.dumps({'schema_version':'0.1.0','defaults':defaults,
            'hosts':{'node':{'enabled':True},'other':{'enabled':True}}}))
        barrier=threading.Barrier(2)
        def acquire(root,host,**options):
            state=schedule.read_state(root)
            self.assertEqual(len(state['targets']),2)
            barrier.wait(timeout=3)
            if host=='node':raise RuntimeError('synthetic hidden failure')
            return {'host_id':host,'status':'success','groups':[{'id':'system-runtime','status':'success'}]}
        result=service.dispatch(self.root,threads=2,at='2026-10-20T00:00:00+00:00',collect=acquire)
        self.assertEqual([r['status'] for r in result['hosts']],['failed','success'])
        self.assertEqual(len(list((self.root/'inventory-errors').glob('*.json'))),1)
        again=service.dispatch(self.root,threads=2,at='2026-10-20T00:00:01+00:00',collect=acquire)
        self.assertEqual(again['hosts'],[])

    def test_cpu_window_links_both_samples_and_does_not_report_a_counter_as_a_rate(self):
        class CPUActor(Actor):
            def __init__(self):super().__init__();self.reads=0
            def exec_command(self,argv,**kwargs):
                if 'cat /proc/stat' not in argv[-1]:return super().exec_command(argv,**kwargs)
                self.reads+=1
                text='cpu 1000 0 500 8000 500 0 0 0' if self.reads==1 else 'cpu 1010 0 510 8080 500 0 0 0'
                return SimpleNamespace(stdout=framed(argv[-1],text+'\n\n__OPSFEAST_EXIT_0\n'),stderr='',exitcode=0)
        actor=CPUActor()
        with patch('time.sleep'):
            result=self.acquire(actor,properties=['metrics.cpu_utilization_percent'])
        self.assertEqual(actor.reads,2)
        self.assertEqual(result['groups'][0]['samples'][0]['value'],20)
        source=result['probes'][-1]
        self.assertIn('window_started_at',source)
        self.assertEqual(source['input_source_ids'],[result['probes'][-2]['id']])

    def test_inode_and_megabyte_projections_preserve_zero_and_exact_byte_property(self):
        result=self.acquire(Actor(),properties=['storage.inodes.used','storage.filesystems.total_megabytes','storage.filesystems.total_bytes'])
        samples={s['property']:s for g in result['groups'] for s in g['samples']}
        self.assertEqual(samples['storage.inodes.used']['value'],2)
        self.assertEqual(samples['storage.inodes.used']['keys'],{'name':'/'})
        self.assertEqual(samples['storage.filesystems.total_megabytes']['value'],0)
        self.assertEqual(samples['storage.filesystems.total_megabytes']['status'],'success')
        self.assertEqual(samples['storage.filesystems.total_bytes']['value'],102400)

    def test_linux_pressure_and_disk_counter_units_and_missing_source(self):
        class MetricsActor(Actor):
            def exec_command(self,argv,**kwargs):
                if '/proc/pressure/memory' in argv[-1]:text='some avg10=0.01 avg60=0.02 avg300=0.03 total=40\n'
                elif '/proc/diskstats' in argv[-1]:text='8 0 synthetic-disk '+' '.join(str(v) for v in range(1,18))+'\n'
                else:return super().exec_command(argv,**kwargs)
                return SimpleNamespace(stdout=framed(argv[-1],text+'\n__OPSFEAST_EXIT_0\n'),stderr='',exitcode=0)
        result=self.acquire(MetricsActor(),properties=['metrics.memory_pressure','metrics.disk_counters'])
        values={s['property']:s['value'] for g in result['groups'] for s in g['samples']}
        self.assertEqual(values['metrics.memory_pressure'][0]['total_stall_microseconds'],40)
        self.assertEqual(values['metrics.disk_counters'][0]['read_sectors_512_bytes'],3)
        self.assertEqual(values['metrics.disk_counters'][0]['sector_size_bytes'],512)
        actor=Actor();actor.fail.add('/proc/pressure/memory')
        missing=self.acquire(actor,properties=['metrics.memory_pressure'])
        self.assertEqual(missing['status'],'failed')
        self.assertIsNone(missing['groups'][0]['samples'][0]['value'])


class CronTests(unittest.TestCase):
    def test_install_preserves_entries_idempotent_and_removable(self):
        current='MAILTO=""\n0 2 * * * /usr/bin/true\n'
        original=current
        def run(argv,**kwargs):
            nonlocal current
            if argv==['crontab','-l']:return SimpleNamespace(returncode=0,stdout=current,stderr='')
            current=kwargs['input']
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        root=Path('/tmp/synthetic feast')
        self.assertTrue(cron.update(root,'install',run=run)['changed'])
        self.assertTrue(current.startswith(original))
        self.assertFalse(cron.update(root,'install',run=run)['changed'])
        self.assertEqual(current.count(cron.marker(root)),1)
        cron.update(root,'remove',run=run)
        self.assertEqual(current,original)

    def test_percent_paths_are_escaped_for_cron_and_newlines_rejected(self):
        self.assertIn(r'\%',cron.command(Path('/tmp/100%example')))
        with self.assertRaises(ConfigError):cron.command(Path('/tmp/new\nline'))

    def test_read_failure_does_not_overwrite_existing_crontab_or_echo_stderr(self):
        calls=[]
        def run(argv,**kwargs):
            calls.append(argv)
            return SimpleNamespace(returncode=2,stdout='',stderr='synthetic hidden context')
        with self.assertRaises(ConfigError) as error:cron.update(Path('/tmp/synthetic'),'install',run=run)
        self.assertEqual(calls,[['crontab','-l']])
        self.assertNotIn('synthetic hidden context',str(error.exception))


if __name__=='__main__':unittest.main()
