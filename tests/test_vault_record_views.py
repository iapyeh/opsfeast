"""Current view semantics and diagram safety over public synthetic retained data."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import vault_content as content


STAMP = '2026-10-20T02:00:00+00:00'


def record():
    return {'host_id': 'example-node', 'record_id': 'synthetic-record', 'observed_at': STAMP,
            'recipe_id': 'inventory-system', 'recipe_reference': 'system/inventory/overview',
            'origin': {'namespace': 'synthetic', 'host_id': 'example-node'},
            'data': {'status': 'partial', 'observations': {}, 'inventory': {
                'system': {'hostname': 'example-node', 'system_name': 'Example Linux', 'timezone': None},
                'hardware': {'logical_cpus': 4, 'memory_total_bytes': 8589934592, 'serial': None},
                'storage': {'filesystems': [
                    {'mountpoint': '/', 'source': '/dev/example', 'used_percent': 82, 'total_bytes': 1000000000},
                    {'mountpoint': '/empty', 'source': 'tmpfs', 'used_percent': 0, 'total_bytes': None},
                    {'mountpoint': '/unknown', 'source': None, 'used_percent': None, 'total_bytes': None}]},
                'network': {'interfaces': [{'name': 'eth0', 'address': '192.0.2.10', 'prefix_length': 24, 'mtu': None},
                                           {'name': 'eth0', 'address': '2001:db8::1', 'prefix_length': 64, 'mtu': None}],
                            'routes': None},
                'software': {'packages': None}, 'services': {'services': []}}}}


def sample(prop, value, keys=None, status='success', stamp=STAMP):
    return {'property': prop, 'value': value, 'keys': keys or {}, 'status': status,
            'observed_at': stamp, 'source_id': 'probe'}


class RecordViewTests(unittest.TestCase):
    def test_current_omits_unknowns_and_keeps_empty_zero_and_report_complete(self):
        data = record()
        before = copy.deepcopy(data)
        current = content.render_observation(data, current=True)
        history = content.render_observation(data)
        self.assertIn('## Host summary', current)
        self.assertNotIn('Not available', current)
        self.assertNotIn('## Software', current)
        self.assertNotIn('MTU', current)
        self.assertIn('No entries reported', current)
        self.assertIn('Some data was not obtained', current)
        self.assertIn('Observed: 2026-', current)
        self.assertIn('```dgmo', current)
        self.assertIn('"/empty (tmpfs)" 0', current)
        self.assertIn('Not available', history)
        self.assertIn('## Software', history)
        self.assertIn('## Collection metadata', history)
        self.assertNotIn('```dgmo', history)
        self.assertEqual(data, before)

    def test_usage_only_plots_valid_bounded_values_and_never_computes_availability(self):
        rows = [{'mountpoint': str(i), 'used_percent': v} for i, v in enumerate(
                [0, 100, '82%', None, '', 'bad', -1, 101, float('nan'), float('inf'), True])]
        plot = '\n'.join(content.capacity_diagram(rows))
        self.assertIn('"0" 0', plot)
        self.assertIn('"1" 100', plot)
        self.assertIn('"2" 82', plot)
        self.assertEqual(sum(line.startswith('"') for line in plot.splitlines()), 3)
        self.assertEqual(content.capacity_diagram([{'used_bytes': 80, 'total_bytes': 100}]), [])

    def test_interface_rows_are_grouped_without_inventing_peer_or_link_status(self):
        rows = record()['data']['inventory']['network']['interfaces']
        rows += [dict(rows[0]), {'name': 'eth1'}, {'address': '192.0.2.99'}]
        plot = '\n'.join(content.interface_diagram('example-node', rows))
        self.assertEqual(plot.count('    Interface eth0'), 1)
        self.assertEqual(plot.count('      IP 192.0.2.10/24'), 1)
        self.assertIn('2001:db8::1/64', plot)
        self.assertIn('    Interface eth1', plot)
        self.assertNotIn('192.0.2.99', plot)
        self.assertIn('not a network topology', plot)

    def test_labels_cannot_escape_fences_lines_or_quoted_nodes(self):
        attack = 'a"\\\\\n```\n  injected description: hacked\x00'
        name = content.dgmo_name(attack)
        self.assertEqual(name.count('"'), 2)
        self.assertNotIn('`', name)
        self.assertNotIn('\n', name)
        self.assertNotIn('\\', name)
        self.assertNotIn('\x00', name)
        body = '\n'.join(content.interface_diagram(attack, [{'name': attack, 'address': attack}]))
        self.assertEqual(body.count('```'), 2)

    def test_nested_missing_is_not_misrepresented_as_observed_empty(self):
        self.assertIsNone(content.readable_value([None, {'value': None}]))
        self.assertEqual(content.readable_value([]), [])
        self.assertEqual(content.readable_value({'zero': 0, 'off': False, 'unknown': None}), {'zero': 0, 'off': False})

    def test_jobs_keep_source_times_and_no_failed_value_backfill(self):
        data = record()
        data['retention_definition'] = {'contract': 'inventory-job-observations'}
        older = '2026-10-19T02:00:00+00:00'
        groups = [{'id': 'hardware-baseline', 'title': 'Hardware baseline', 'status': 'partial',
                   'observed_at': older, 'source_record_id': 'older-record', 'source_record_observed_at': older, 'identity_warning': 'Older identity warning',
                   'coverage': [{'complete': False}], 'samples': [sample('hardware.logical_cpus', 0, stamp=older),
                       sample('hardware.memory_total_bytes', None, status='unavailable', stamp=older)]},
                  {'id': 'storage-capacity', 'title': 'Storage capacity', 'status': 'success',
                   'observed_at': STAMP, 'source_record_id': 'synthetic-record', 'coverage': [{'complete': True}],
                   'samples': [sample('storage.filesystems.used_percent', 82, {'source': '/dev/example', 'mountpoint': '/'})]}]
        data['data'] = {'status': 'success', 'groups': groups}
        before = copy.deepcopy(data)
        current = content.render_observation(data, current=True)
        self.assertIn('## Host summary', current)
        self.assertIn('| Logical CPUs | 0 |', current)
        self.assertNotIn('Memory Total Bytes', current)
        self.assertIn('Older identity warning', current)
        self.assertIn('Some data was not obtained', current)
        self.assertIn(content.history_filename(dict(data, record_id='older-record', observed_at=older)), current)
        self.assertIn(content.format_time(older), current)
        self.assertIn('"/ (/dev/example)" 82', current)
        self.assertEqual(data, before)

    def test_entity_tables_preserve_retained_units_and_separate_sample_times(self):
        samples = [sample('storage.filesystems.total_megabytes', 100, {'name': '/'}),
                   sample('storage.filesystems.used_megabytes', 80, {'name': '/'}),
                   sample('storage.filesystems.used_megabytes', 90, {'name': '/'}, stamp='2026-10-20T03:00:00+00:00')]
        definitions = {s['property']: {'column': s['property'].split('.')[-1].replace('megabytes', 'bytes')} for s in samples}
        body = '\n'.join(content.job_value_tables(samples, definitions))
        self.assertIn('Total Megabytes', body)
        self.assertNotIn('100 bytes', body)
        self.assertEqual(body.count('| / |'), 2)
        self.assertNotIn('Sample Time', body)
        self.assertNotIn('Sample time', body)

    def test_long_collections_preview_visible_rows_and_preserve_full_reports(self):
        dataset = {'routes': [{'name': 'example-' + str(n), 'version': None} for n in range(13)]}
        compact = '\n'.join(content.dataset_lines(dataset, compact=True))
        complete = '\n'.join(content.dataset_lines(dataset))
        self.assertIn('13 entries; showing the first 12', compact)
        self.assertNotIn('<details>', compact)
        self.assertEqual(sum(line.startswith('| example-') for line in compact.splitlines()), 12)
        self.assertEqual(sum(line.startswith('| example-') for line in complete.splitlines()), 13)
        self.assertNotIn('Version', compact)
        self.assertIn('Not available', complete)
        self.assertNotIn('<details>', complete)

    def test_topics_group_related_samples_and_hide_cumulative_io(self):
        data = record()
        props = [('resource-metrics', 'Resource utilization', [sample('metrics.interfaces.in_octets', 100, {'name': 'eth0'})]),
                 ('software-inventory', 'Installed software', [sample('software.packages', [{'name': 'example', 'version': '1'}])]),
                 ('network-configuration', 'Network configuration', [sample('network.dns_servers', [{'address': '192.0.2.53'}])]),
                 ('hardware-baseline', 'Hardware baseline', [sample('hardware.logical_cpus', 4)])]
        data['data'] = {'status': 'success', 'groups': [dict(id=i, title=t, samples=ss, status='success',
            observed_at=STAMP, coverage=[{'complete': True}], source_record_id='source', source_record_observed_at=STAMP)
            for i,t,ss in props]}
        page = content.render_observation(data, current=True)
        self.assertNotIn('## Static inventory', page)
        self.assertNotIn('## Dynamic state', page)
        self.assertIn('## CPU and memory', page)
        self.assertIn('## Network', page)
        self.assertIn('## Software', page)
        self.assertNotIn('In Octets', page)
        self.assertNotIn('### Resource utilization', page)
        self.assertNotIn('## Inventory jobs', page)
        self.assertNotIn('Sample time', page)
        self.assertNotIn('Sample Time', page)
        self.assertNotIn('Group report', page)
        self.assertIn('[Source report —', page)
        self.assertIn('Sections can have different observation times', page)
        self.assertNotIn('Network%20activity', page)
        self.assertEqual(len([line for line in content.dataset_lines({'packages': [{'name': str(n)} for n in range(546)]}, compact=True) if line.startswith('| ')]) - 2, 546)

    def test_package_and_service_lists_are_complete_and_sorted(self):
        for name in ('software.packages', 'services.services'):
            rows = [{'version': '1', 'name': 'z-' + str(n).zfill(2)} for n in reversed(range(15))]
            data = [sample(name, rows)]
            body = '\n'.join(content.job_value_tables(data, {}))
            self.assertNotIn('showing the first', body)
            self.assertIn('| Name | Version |', body)
            self.assertEqual(sum(line.startswith('| z-') for line in body.splitlines()), 15)
            self.assertLess(body.index('| z-00'), body.index('| z-14'))
            self.assertEqual(data[0]['value'], rows)

    def test_common_source_is_linked_once_but_different_source_stays_identifiable(self):
        data = record()
        groups = [dict(id=i, title=t, samples=[sample(p, 4)], status='success', observed_at=STAMP,
                       coverage=[{'complete': True}], source_record_id=data['record_id'], source_record_observed_at=STAMP)
                  for i,t,p in [('hardware-baseline','Hardware baseline','hardware.logical_cpus'),
                                ('system-runtime','System runtime','system.uptime_seconds')]]
        data['data'] = {'status':'success','groups':groups}
        page = content.render_observation(data,current=True)
        self.assertEqual(page.count('](../2026/reports/'),1)
        self.assertNotIn('[Source report](',page)
        groups[0]['source_record_id']='old-record'
        names = {data['record_id']:'latest.md','old-record':'older.md'}
        page = content.render_observation(data,current=True,history_names=names)
        self.assertEqual(page.count('](../2026/reports/'),2)
        hardware = page.split('### Capacity\n',1)[1].split('## Software',1)[0]
        self.assertIn('[Source report](../2026/reports/older.md)',hardware)

    def test_redundant_megabytes_only_hidden_when_exact_same_probe_value_exists(self):
        exact = sample('storage.filesystems.total_bytes', 100900000, {'source':'/dev/a','mountpoint':'/'})
        derived = sample('storage.filesystems.total_megabytes', 100, {'name':'/'})
        self.assertEqual(content.readable_job_samples([exact,derived]),[exact])
        for key,value in [('source_id','other-probe'),('observed_at','2026-10-20T03:00:00+00:00'),('value',99),('keys',{'name':'/other'})]:
            other = dict(derived,**{key:value})
            self.assertEqual(content.readable_job_samples([exact,other]),[exact,other])
        missing = dict(exact,value=None,status='unavailable')
        self.assertIn(derived,content.readable_job_samples([missing,derived]))
        defs = {s['property']:{'column':s['property'].split('.')[-1]} for s in [exact,derived]}
        body = '\n'.join(content.job_value_tables([exact,derived],defs,group_id='storage-capacity'))
        self.assertIn('#### Filesystem capacity',body)
        self.assertEqual(body.count('| / |'),1)
        self.assertNotIn('Megabytes',body)

    def test_unit_column_removed_but_measurement_meaning_is_preserved(self):
        data = [sample('metrics.load_1m',0.2),sample('metrics.cpu_utilization_percent',25)]
        defs = {'metrics.load_1m':{'unit':'tasks'},'metrics.cpu_utilization_percent':{'unit':'percent'}}
        body = '\n'.join(content.job_value_tables(data,defs))
        self.assertNotIn('| Unit |',body)
        self.assertIn('0.2 tasks',body)
        self.assertIn('25%',body)
        self.assertEqual(content.current_value(1024,'memory_total_bytes','bytes'),'1 KiB (1,024 bytes)')

    def attention_record(self, values):
        data = record()
        data['data'] = {'status':'success','groups':[{
            'id':'resource-metrics','title':'Resource utilization','status':'success','observed_at':STAMP,
            'coverage':[{'complete':True}], 'samples':[sample(name,value,keys) for name,value,keys in values]}]}
        return data

    def test_attention_thresholds_show_evidence_times_and_critical_boundaries(self):
        data = self.attention_record([
            ('hardware.logical_cpus',4,{}),('metrics.load_5m',4,{}),
            ('metrics.cpu_utilization_percent',95,{}),
            ('hardware.memory_total_bytes',1000,{}),('metrics.memory_available_bytes',50,{}),
            ('storage.filesystems.used_percent',95,{'mountpoint':'/srv'})])
        before = copy.deepcopy(data)
        page = content.render_observation(data,current=True,host_icon='🖥')
        self.assertTrue(page.startswith('# 🖥 example-node'))
        self.assertLess(page.index('## Attention'),page.index('## Contents'))
        self.assertEqual(page.count('- **Critical:**'),3)
        self.assertEqual(page.count('- **Warning:**'),1)
        self.assertIn('5-minute load 4',page)
        self.assertIn(content.format_time(STAMP),page)
        self.assertIn('not live monitoring',page)
        self.assertEqual(data,before)

    def test_no_attention_section_or_contents_link_without_threshold_hints(self):
        data = self.attention_record([
            ('hardware.logical_cpus',4,{}),('metrics.load_5m',0.2,{}),
            ('metrics.cpu_utilization_percent',20,{}),
            ('hardware.memory_total_bytes',1000,{}),('metrics.memory_available_bytes',500,{}),
            ('storage.filesystems.used_percent',40,{'mountpoint':'/'})])
        page = content.render_observation(data,current=True)
        self.assertEqual(content.attention_lines(data), [])
        self.assertNotIn('## Attention',page)
        self.assertNotIn('](#Attention)',page)
        self.assertNotIn('No threshold hints',page)
        self.assertIn('## Contents',page)

    def test_attention_missing_invalid_and_failed_values_are_not_healthy_evidence(self):
        data = self.attention_record([
            ('hardware.logical_cpus',0,{}),('metrics.load_5m',50,{}),
            ('hardware.memory_total_bytes',1000,{}),('metrics.memory_available_bytes',2000,{}),
            ('metrics.cpu_utilization_percent',float('nan'),{}),
            ('storage.filesystems.used_percent',None,{'mountpoint':'/srv'})])
        page = '\n'.join(content.attention_lines(data))
        self.assertNotIn('- **Critical:**',page)
        self.assertEqual(content.attention_lines(data), [])
        self.assertNotIn('## Attention',content.render_observation(data,current=True))
        data['data']['groups'][0]['samples'] = [sample('metrics.cpu_utilization_percent',99,status='unavailable')]
        self.assertNotIn('- **Critical:**','\n'.join(content.attention_lines(data)))

    def test_attention_memory_zero_is_critical_and_mixed_age_baseline_is_explicit(self):
        data = self.attention_record([('hardware.memory_total_bytes',1000,{}),('metrics.memory_available_bytes',0,{})])
        data['data']['groups'][0]['samples'][0]['observed_at']='2026-10-19T02:00:00+00:00'
        page='\n'.join(content.attention_lines(data))
        self.assertIn('**Critical:**',page)
        self.assertIn('baseline: '+content.format_time('2026-10-19T02:00:00+00:00'),page)
        self.assertIn('0%',page)

    def test_cumulative_disk_and_network_counters_only_remain_in_reports(self):
        data = self.attention_record([
            ('metrics.disk_counters',[{'name':'disk0','reads_completed':999}],{}),
            ('metrics.interface_counters',[{'name':'eth0','in_octets':999}],{}),
            ('metrics.interfaces.in_octets',999,{'name':'eth0'}),
            ('metrics.cpu_utilization_percent',20,{})])
        current=content.render_observation(data,current=True)
        full=content.render_observation(data)
        self.assertNotIn('999',current)
        self.assertNotIn('Disk Counters',current)
        self.assertIn('20',current)
        self.assertIn('999',full)

    def test_failed_and_verified_empty_jobs_have_distinct_current_views(self):
        data = record()
        group = {'id': 'network-state', 'title': 'Network operational state', 'status': 'failed',
                 'observed_at': STAMP, 'coverage': [{'complete': False}],
                 'samples': [sample('network.routes', None, status='unavailable')]}
        data['data'] = {'status': 'failed', 'groups': [group]}
        current = content.render_observation(data, current=True)
        self.assertNotIn('### Network operational state', current)
        self.assertIn('Some data was not obtained', current)
        group.update(status='success', coverage=[{'complete': True}], samples=[])
        data['data']['status'] = 'success'
        current = content.render_observation(data, current=True)
        self.assertIn('Complete enumeration returned no matching instances', current)
        self.assertNotIn('Some data was not obtained', current)


if __name__ == '__main__':
    unittest.main()
