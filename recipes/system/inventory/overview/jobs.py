"""Selective command collection for inventory job observations. No storage/network setup."""
from datetime import datetime, timezone
import ipaddress
import json
import math
from pathlib import Path
import re
import runpy
import time

VERSION = '0.1.0'
ROOT = Path(__file__).resolve().parent
CATALOG = runpy.run_path(str(ROOT / 'properties.py'))
DETAILS = runpy.run_path(str(ROOT / 'details.py'))
BASE = runpy.run_path(str(ROOT / 'main.py'))


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def collect(actor, host, jobs, properties=None, *, timeout=30, budget=90):
    """Only selected properties are measured; shared probes retain original times."""
    specs = CATALOG['PROPERTIES']
    names = list(properties) if properties is not None else [n for n, s in specs.items() if s['job'] in jobs]
    if any(n not in specs or specs[n]['job'] not in jobs for n in names):
        raise ValueError('unknown property or property outside selected jobs')
    report = {'host_id': host, 'started_at': now(), 'groups': [], 'probes': []}
    deadline = time.monotonic() + budget
    cache = {}

    def probe(command, parser=DETAILS['text_value']):
        if command in cache:
            return cache[command]
        item = {'id': 'probe-' + str(len(report['probes']) + 1), 'command': command,
                'started_at': now(), 'observed_at': now(), 'status': 'failed',
                'reason_code': None, 'exitcode': None, 'error_type': None}
        report['probes'].append(item)
        value = None
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                item['reason_code'] = 'budget_exhausted'
            else:
                script = '( ' + command + '; printf "\\n__OPSFEAST_EXIT_%s\\n" "$?" ) 2>/dev/null | head -c 262145'
                result = actor.exec_command(['/bin/sh', '-c', script], check=False, command_timeout=min(timeout, remaining))
                output = result.stdout
                if len(output.encode()) > 262144 or getattr(result, 'stdout_truncated', False):
                    item['reason_code'] = 'output_limit'
                elif result.exitcode != 0:
                    item.update(reason_code='shell_failed', exitcode=result.exitcode)
                else:
                    output = output.replace('\r\n', '\n')
                    trailer = re.search(r'\n__OPSFEAST_EXIT_(\d+)\n?$', output)
                    if not trailer:
                        item['reason_code'] = 'producer_marker_missing'
                    else:
                        item['exitcode'] = int(trailer[1])
                        if item['exitcode']:
                            item['reason_code'] = 'command_not_found' if item['exitcode'] == 127 else 'command_failed'
                        else:
                            value = parser(output[:trailer.start()])
                            json.dumps(value, allow_nan=False)
                            if isinstance(value, list) and len(value) > 2000:
                                raise ValueError('item_limit')
                            item['status'] = 'success'
        except Exception as exc:
            item.update(reason_code='timeout' if isinstance(exc, TimeoutError) or type(exc).__name__ == 'CommandTimeoutError' else 'probe_or_parse_failed', error_type=type(exc).__name__)
        finally:
            item['observed_at'] = now()
        cache[command] = (value if item['status'] == 'success' else None, item)
        return cache[command]

    kernel, kernel_source = probe('uname -s')
    platform = {'Linux': 'linux', 'Darwin': 'macos', 'FreeBSD': 'freebsd', 'VMkernel': 'esxi'}.get(kernel)
    report['platform'] = platform
    fields = set()
    for name in names:
        parts = name.split('.')
        if parts[0] in DETAILS['FIELDS'] and parts[1] in DETAILS['FIELDS'][parts[0]]:
            fields.add((parts[0], parts[1]))
        if name.startswith(('network.ipv4.','network.ipv6.')):
            fields.add(('network','interfaces'))
    old = BASE['new_report'](host, 'local')
    if platform:
        DETAILS['collect'](actor, old, platform, timeout, budget=max(0, deadline-time.monotonic()), fields=fields)
    extra_sources = {}
    if 'collection_process' in old:
        for source in old['collection_process']['probes']:
            pair = (source['section'], source['field'])
            if pair not in fields:
                continue
            item = {'id': 'probe-' + str(len(report['probes']) + 1),
                    'command': source.get('command'), 'started_at': source.get('started_at', report['started_at']),
                    'observed_at': source['observed_at'], 'status': source['status'],
                    'reason_code': source.get('reason_code'), 'exitcode': source.get('exitcode'),
                    'error_type': source.get('error_type')}
            report['probes'].append(item)
            extra_sources[pair] = item
    def unavailable(reason='unsupported_platform_or_probe'):
        return None, dict(kernel_source, status='unsupported', reason_code=reason)
    def meminfo(text):
        return {k: int(v.split()[0]) * 1024 for k, v in DETAILS['pairs'](text).items() if v.endswith('kB')}
    def inode_rows(text):
        rows = DETAILS['table'](text, ('source','total','used','available','percent','mountpoint'), header=True)
        for row in rows:
            for key in ('total','used','available'):
                row[key] = DETAILS['integer'](row[key])
        return rows
    def cpu(text):
        values = [int(v) for v in text.splitlines()[0].split()[1:9]]
        if len(values) < 4:
            raise ValueError('CPU columns')
        return values
    def counters(text):
        rows = []
        columns = ['reads_completed','reads_merged','read_sectors_512_bytes','read_milliseconds',
                   'writes_completed','writes_merged','written_sectors_512_bytes','write_milliseconds',
                   'io_in_progress','io_milliseconds','weighted_io_milliseconds',
                   'discards_completed','discards_merged','discarded_sectors_512_bytes','discard_milliseconds',
                   'flushes_completed','flush_milliseconds']
        for line in text.splitlines():
            parts = line.split()
            if len(parts)<14:
                raise ValueError('diskstats columns')
            values = [int(value) for value in parts[3:]]
            if min(values)<0:
                raise ValueError('negative disk counter')
            rows.append({'major':int(parts[0]),'minor':int(parts[1]),'name':parts[2],
                         **dict(zip(columns,values)), 'sector_size_bytes':512})
        return rows
    def netdev(text):
        rows = []
        for line in text.splitlines():
            if ':' not in line:
                continue
            name,values = line.rsplit(':',1)
            counts = [int(v) for v in values.split()]
            if len(counts) != 16:
                raise ValueError('netdev columns')
            rows.append({'name':name.strip(), **{key:counts[index] for key,index in
                [('in_octets',0),('out_octets',8),('in_errors',2),('out_errors',10),('in_discards',3),('out_discards',11)]}})
        return rows
    base_values = {}
    for name in names:
        if name == 'system.platform':
            base_values[name] = (platform, kernel_source) if platform else unavailable()
        elif name == 'system.kernel_name':
            base_values[name] = (kernel, kernel_source)
        elif name in ('system.hostname','system.kernel_release','system.architecture','system.kernel_version'):
            base_values[name] = probe('uname ' + {'system.hostname':'-n','system.kernel_release':'-r','system.architecture':'-m','system.kernel_version':'-v'}[name])
        elif name in ('system.system_name','system.system_version'):
            if platform == 'linux':
                values, source = probe('cat /etc/os-release', BASE['parse_os_release'])
                base_values[name] = ((values or {}).get('NAME' if name.endswith('system_name') else 'VERSION_ID'), source)
            elif platform == 'macos':
                base_values[name] = probe('sw_vers ' + ('-productName' if name.endswith('system_name') else '-productVersion'))
            elif platform == 'freebsd':
                base_values[name] = ('FreeBSD', kernel_source) if name.endswith('system_name') else probe('freebsd-version -u')
            elif platform == 'esxi':
                base_values[name] = ('VMware ESXi', kernel_source) if name.endswith('system_name') else probe('vmware -v')
        elif name.startswith('storage.inodes.'):
            base_values[name] = probe('LC_ALL=C df -Pi', inode_rows) if platform == 'linux' else unavailable()
        elif name.startswith('storage.swap.'):
            values, source = probe('cat /proc/meminfo', meminfo) if platform == 'linux' else unavailable()
            total, free = (values or {}).get('SwapTotal'), (values or {}).get('SwapFree')
            value = {'total_bytes':total, 'available_bytes':free, 'used_bytes': total-free if total is not None and free is not None else None}[name.split('.')[-1]]
            base_values[name] = value, source
        elif name.startswith('metrics.'):
            if platform != 'linux':
                base_values[name] = unavailable()
            elif name.startswith('metrics.interfaces.'):
                base_values[name] = probe('cat /proc/net/dev', netdev)
            elif name.startswith('metrics.load_'):
                values, source = probe('cat /proc/loadavg', lambda t: [float(v) for v in t.split()[:3]])
                base_values[name] = ((values or [None]*3)[{'metrics.load_1m':0,'metrics.load_5m':1,'metrics.load_15m':2}[name]], source)
            elif name.startswith('metrics.memory_'):
                if name == 'metrics.memory_pressure':
                    def pressure(text):
                        rows = []
                        for line in text.splitlines():
                            parts = line.split()
                            values = dict(p.split('=',1) for p in parts[1:])
                            rows.append({'kind':parts[0],**{'avg_'+str(window)+'s_percent':float(values['avg'+str(window)]) for window in (10,60,300)},
                                         'total_stall_microseconds':int(values['total'])})
                        return rows
                    base_values[name] = probe('cat /proc/pressure/memory',pressure)
                else:
                    values, source = probe('cat /proc/meminfo', meminfo)
                    base_values[name] = (values or {}).get('MemTotal' if name.endswith('total_bytes') else 'MemAvailable'), source
            elif name == 'metrics.cpu_utilization_percent':
                first, src1 = probe('cat /proc/stat', cpu)
                remaining = deadline-time.monotonic()
                if first is None or remaining <= .25:
                    base_values[name] = unavailable('CPU_sample_window_unavailable')
                else:
                    time.sleep(.2)
                    cache.pop('cat /proc/stat', None)
                    second, src2 = probe('cat /proc/stat', cpu)
                    src2['window_started_at'] = src1['observed_at']
                    src2['input_source_ids'] = [src1['id']]
                    value = None
                    if second is not None and len(first) == len(second):
                        delta = [b-a for a,b in zip(first, second)]
                        if min(delta) >= 0 and sum(delta) > 0:
                            value = 100 * (sum(delta)-delta[3]-(delta[4] if len(delta)>4 else 0))/sum(delta)
                    base_values[name] = value, src2
            else:
                base_values[name] = probe('cat /proc/diskstats', counters) if name == 'metrics.disk_counters' else probe('cat /proc/net/dev', netdev)
        elif name.startswith('sensors.'):
            if platform != 'linux':
                base_values[name] = unavailable()
            else:
                fans = name == 'sensors.fans'
                command = ('found=0; for f in ' + ('/sys/class/hwmon/hwmon*/fan*_input' if fans else '/sys/class/thermal/thermal_zone*/temp') +
                           '; do [ -r "$f" ] || continue; found=1; printf "%s " "$f"; cat "$f" || exit; done; [ "$found" = 1 ]')
                def sensors(text):
                    return [{'sensor':line.split()[0], 'value':float(line.split()[1])/(1 if fans else 1000), 'unit':'rpm' if fans else 'celsius'} for line in text.splitlines()]
                base_values[name] = probe(command, sensors)
    # Boot estimate uses the same uptime probe and preserves its original time.
    if 'system.boot_time' in names:
        source = extra_sources.get(('system','uptime_seconds'))
        if source is None and platform:
            # Boot time depends on uptime even when only the estimate was requested.
            dependency = BASE['new_report'](host, 'local')
            DETAILS['collect'](actor, dependency, platform, timeout, budget=max(0,deadline-time.monotonic()), fields={('system','uptime_seconds')})
            p = next(p for p in dependency['collection_process']['probes'] if p['field']=='uptime_seconds')
            source = dict(p, id='probe-'+str(len(report['probes'])+1))
            report['probes'].append(source)
            uptime = dependency['inventory']['system']['uptime_seconds']
        else:
            uptime = old.get('inventory',{}).get('system',{}).get('uptime_seconds')
        from datetime import timedelta
        base_values['system.boot_time'] = ((datetime.fromisoformat(source['observed_at'])-timedelta(seconds=uptime)).isoformat() if source and uptime is not None else None, source or unavailable()[1])
    def project(name):
        spec = specs[name]
        if name in base_values:
            value, source = base_values[name]
        else:
            section, field, *_ = name.split('.')
            if section == 'network' and field in ('ipv4','ipv6'):
                field = 'interfaces'
            value = old.get('inventory',{}).get(section,{}).get(field)
            source = extra_sources.get((section,field), unavailable()[1])
        rows = []
        if spec['column'] and isinstance(value,list):
            seen = set()
            for row in value:
                if not isinstance(row, dict):
                    continue
                if name.startswith(('network.ipv4.','network.ipv6.')):
                    try:
                        address = ipaddress.ip_address(str(row.get('address','')).split('%')[0])
                    except ValueError:
                        continue
                    if address.version != (4 if name.startswith('network.ipv4.') else 6):
                        continue
                    row = dict(row,address=str(address))
                # BSD ether rows describe the MAC, not an IP address.
                column = spec['column']
                cell = row.get('address') if name == 'network.interfaces.mac' and row.get('kind') == 'ether' else row.get(column)
                if name == 'network.interfaces.address' and row.get('kind') == 'ether':
                    continue
                keys = {key:row[key] for key in spec['keys'] if row.get(key) is not None}
                if spec['module']=='openconfig-system' and row.get('mountpoint') is not None:
                    keys = {'name':row['mountpoint']}
                if name.startswith('storage.filesystems.') and name.endswith('_megabytes') and cell is not None:
                    cell = cell//1000000
                if name == 'network.interfaces.state' and cell is not None:
                    cell = {'UP':'up','DOWN':'down','UNKNOWN':'unknown','DORMANT':'dormant','LOWERLAYERDOWN':'lower-layer-down','NOTPRESENT':'not-present','TESTING':'testing'}.get(cell)
                token = json.dumps([keys,cell], sort_keys=True)
                if token in seen:
                    continue
                seen.add(token)
                rows.append((keys,cell))
        elif spec['column'] and value is None:
            rows = [({}, None)]
        elif spec['column']:
            rows = [({}, None)]
        else:
            rows = [({}, value)]
        # Empty successful enumerations are explicit scope evidence, not synthetic null rows.
        samples = []
        for keys,value in rows:
            if name == 'storage.filesystems.used_percent' and isinstance(value,str):
                try:
                    value = float(value.rstrip('%'))
                except ValueError:
                    value = None
            if spec['type']=='number' and type(value) in (int,float):
                value = round(value,6) if math.isfinite(value) else None
            from inventory_property_types import matches
            good = source.get('status') == 'success' and value is not None and matches(spec,value)
            samples.append({'property':name, 'keys':keys, 'value':value if good else None,
                'status':'success' if good else 'unavailable', 'reason_code':None if good else source.get('reason_code') or ('invalid_property_value' if value is not None else 'value_not_reported'),
                'observed_at':source['observed_at'], 'source_id':source['id']})
        return samples, {'property':name, 'complete':source.get('status') == 'success' and value is not None and all(s['status']=='success' for s in samples),
                         'source_id':source['id'], 'observed_at':source['observed_at']}
    for job in jobs:
        group = {'id':job, 'title':CATALOG['JOBS'][job]['title'], 'started_at':report['started_at'],
                 'observed_at':now(), 'samples':[], 'coverage':[]}
        for name in names:
            if specs[name]['job'] == job:
                samples, coverage = project(name)
                group['samples'].extend(samples)
                group['coverage'].append(coverage)
        states = [s['status'] for s in group['samples']]
        complete = all(c['complete'] for c in group['coverage'])
        group['status'] = 'success' if complete else 'partial' if 'success' in states else 'failed'
        report['groups'].append(group)
    report['observed_at'] = now()
    report['status'] = 'success' if all(g['status']=='success' for g in report['groups']) else 'partial' if any(g['status'] in ('success','partial') for g in report['groups']) else 'failed'
    return report
