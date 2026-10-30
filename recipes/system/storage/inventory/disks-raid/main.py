"""Read-only Linux/ESXi block and StorCLI-family inventory; no target files written."""
from datetime import datetime, timezone
import csv
import io
import json
import math
from pathlib import Path
import re
import shlex

VERSION = '0.4.0'
LIMIT = 262144
LSBLK = ['lsblk', '--json', '--bytes', '--list', '--output',
         'NAME,KNAME,PATH,TYPE,SIZE,MODEL,SERIAL,WWN,TRAN,ROTA,HCTL']
DISCOVER = ('IFS=:; for n in racadm idracadm7 storcli64 storcli perccli64 perccli; do '
            'for d in $PATH /opt/MegaRAID/storcli /opt/MegaRAID/perccli '
            '/opt/lsi/perccli /opt/lsi/storcli /opt/dell/racadm/bin /opt/dell/srvadmin/bin; do p="$d/$n"; '
            'if [ -f "$p" ] && [ -x "$p" ]; then printf "%s\\n" "$p"; exit 0; fi; '
            'done; done; exit 127')


def now():
    return datetime.now(timezone.utc).isoformat()


def configuration(values, timeout):
    budget = values.get('command_timeout_seconds', 20)
    cli = values.get('raid_cli', 'auto')
    root = values.get('require_root', True)
    expected = values.get('expected_disks', {})
    expected_raids = values.get('expected_raids')
    boot_policy = values.get('boot_policy', 'auto')
    if (not isinstance(expected, dict) or set(expected)-{'data'} or
            any(type(v) is not int or v < 0 for v in expected.values()) or
            expected_raids is not None and (type(expected_raids) is not int or expected_raids < 0) or
            boot_policy not in ('auto','mirrored-ssd-pair')):
        raise ValueError('invalid physical inventory or RAID expectation')
    if (type(root) is not bool or type(budget) not in (int, float)
            or not math.isfinite(budget) or not 1 <= budget <= 120
            or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0
            or not isinstance(cli, str) or (cli != 'auto' and
                not re.fullmatch(r'/[A-Za-z0-9_./-]+', cli))):
        raise ValueError('invalid disk inventory configuration')
    return min(budget, timeout), cli, root


def probe(run, command, budget, evidence, name):
    item = {'id': name, 'command': command, 'started_at': now(), 'completed_at': None,
            'status': 'failed', 'error': None, 'exitcode': None,
            'observed_at': None, 'stdout_truncated': False, 'stderr_truncated': False,
            'stdout': None, 'stderr': None, 'truncated': False}
    evidence.append(item)
    try:
        result = run(command, check=False, command_timeout=budget)
    except Exception as exc:
        result = getattr(exc, 'result', None)
        item['error'] = type(exc).__name__
    if result is not None:
        for stream in ('stdout', 'stderr'):
            value = getattr(result, stream, None)
            if value is not None:
                encoded = value.encode('utf-8')
                item[stream] = encoded[:LIMIT].decode('utf-8', errors='ignore')
                item[stream + '_truncated'] |= len(encoded) > LIMIT
                item['truncated'] |= len(encoded) > LIMIT
            item[stream + '_truncated'] |= bool(getattr(result, stream + '_truncated', False))
            item['truncated'] |= item[stream + '_truncated']
        item['exitcode'] = result.exitcode
        if item['error'] is None and not item['truncated'] and result.exitcode == 0:
            item['status'] = 'success'
        elif item['error'] is None:
            item['error'] = 'output_truncated' if item['truncated'] else 'command_failed'
    item['completed_at'] = now()
    item['observed_at'] = item['completed_at']
    return item


def strict_json(value):
    def reject_constant(token):
        raise ValueError('non-finite JSON value')
    return json.loads(value, parse_constant=reject_constant)


def parse_disks(value):
    rows = value['blockdevices']
    if not isinstance(rows, list):
        raise ValueError('invalid lsblk rows')
    disks = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('type'), str):
            raise ValueError('invalid block device')
        if row['type'] != 'disk':
            continue
        size = row.get('size')
        if size is not None:
            if type(size) not in (str, int) or not re.fullmatch(r'\d+', str(size)):
                raise ValueError('invalid byte size')
            size = int(size)
        if not isinstance(row.get('path'), str) or not row['path'].startswith('/dev/'):
            raise ValueError('invalid disk path')
        disks.append({'path': row['path'], 'kernel_name': row.get('kname'),
                      'model': row.get('model'), 'serial': row.get('serial'), 'wwn': row.get('wwn'),
                      'size_bytes': size, 'transport': row.get('tran'), 'rotational': row.get('rota'),
                      'hctl': row.get('hctl'), 'scope': 'os_visible_not_verified_physical'})
    return disks


def parse_raid(value, kind):
    """Preserve vendor details; controller-local IDs never imply OS-device mapping."""
    controllers = value['Controllers']
    if not isinstance(controllers, list) or not controllers:
        raise ValueError('missing controller status')
    records, errors = [], []
    for entry in controllers:
        try:
            status = entry['Command Status']
            if status.get('Status') != 'Success':
                raise ValueError('controller command failed')
            controller = status.get('Controller')
            if type(controller) not in (int, str) or not str(controller).isdigit():
                raise ValueError('invalid controller id')
            response = entry['Response Data']
            if not isinstance(response, dict):
                raise ValueError('invalid controller response')
            if kind == 'controllers':
                if not response:
                    raise ValueError('empty controller response')
                records.append({'controller': str(controller), 'details': response})
            elif kind == 'physical_drives':
                found = False
                for key, rows in response.items():
                    if re.fullmatch(r'Drive /c\d+(?:/e\d+)?/s\d+', key):
                        if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
                            raise ValueError('invalid physical drive rows')
                        found = True
                        for row in rows:
                            records.append({'controller': str(controller), 'address': key[6:],
                                            'summary': row, 'details': response.get(key + ' - Detailed Information', {})})
                if not found:
                    raise ValueError('unrecognized physical drive response')
            else:
                rows = response.get('VD LIST')
                if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
                    raise ValueError('unrecognized virtual drive response')
                records.extend({'controller': str(controller), 'summary': row}
                               for row in rows)
        except (ValueError, TypeError, KeyError, AttributeError):
            errors.append('invalid_or_failed_controller_response')
    if errors and not records:
        raise ValueError('no usable controller response')
    return {'records': records, 'errors': errors}


def racadm_empty_virtual_disks(output):
    lines = [line.strip() for line in output.splitlines() if line.strip() and
             not line.strip().startswith('Please wait while the raid config data is being fetched.')]
    return len(lines) == 1 and bool(re.fullmatch(r'(?:ERROR:\s*)?STOR0104\s*:\s*No virtual disks are displayed\.?', lines[0], re.I))


def parse_racadm(output, kind):
    """Parse fixed storage-get -o key/value records, preserving Dell FQDDs."""
    if kind == 'virtual_drives' and racadm_empty_virtual_disks(output):
        return []
    records, current, fields = [], None, {}

    def finish():
        if current is not None:
            if not fields:
                raise ValueError('RACADM record has no fields')
            records.append((current, dict(fields)))

    seen = set()
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lower().startswith(('error', 'warning:', 'racadm error')):
            raise ValueError('RACADM reported an error or warning')
        if line.startswith('Please wait while the raid config data is being fetched.'):
            continue
        if '=' in line:
            key, _, value = line.partition('=')
            key, value = key.strip(), value.strip()
            if current is None or not key or key in fields:
                raise ValueError('invalid or duplicate RACADM property')
            fields[key] = value
        elif re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]+', line):
            finish()
            if line in seen:
                raise ValueError('duplicate RACADM FQDD')
            seen.add(line)
            current, fields = line, {}
        else:
            raise ValueError('unsupported RACADM output line')
    finish()
    if not records:
        raise ValueError('no verified RACADM records')
    result = []
    for fqdd, values in records:
        if kind == 'controllers':
            if fqdd.startswith('Disk.'):
                raise ValueError('invalid controller FQDD')
            result.append({'controller': fqdd, 'provider': 'racadm', 'details': values})
            continue
        if ':' not in fqdd or not fqdd.startswith('Disk.'):
            raise ValueError('invalid disk FQDD')
        controller = fqdd.rsplit(':', 1)[1]
        summary = {'Name': values.get('Name'), 'State': values.get('State'), 'Status': values.get('Status'),
                   'Size': values.get('Size'), 'Med': values.get('MediaType')}
        common = {'controller': controller, 'provider': 'racadm', 'summary': summary,
                  'details': values, 'capacity': values.get('Size')}
        if kind == 'physical_drives':
            slot = re.match(r'Disk\.(?:Bay|Direct)\.(\d+)(?:-|:)', fqdd)
            if slot is None:
                raise ValueError('unsupported physical tray FQDD')
            result.append({**common, 'address': fqdd, 'tray': slot.group(1)})
        else:
            if not fqdd.startswith('Disk.Virtual.'):
                raise ValueError('invalid virtual disk FQDD')
            level = values.get('Layout')
            result.append({**common, 'id': fqdd, 'raid_level': level.lower() if level else None})
    return result


def racadm_health(row):
    """Reported controller status plus disk online state; unknown is never healthy."""
    values = row.get('details', {})
    if str(values.get('FailurePredicted', '')).strip().lower() in ('yes', 'true', '1'):
        return 'UNHEALTHY', 'racadm_failure_predicted'
    status = str(values.get('Status', '')).strip().lower()
    rollup = str(values.get('RollupStatus', '')).strip().lower()
    state = str(values.get('State', '')).strip().lower()
    if status in ('critical', 'non-critical', 'error', 'failed') or rollup in ('critical', 'non-critical', 'error', 'failed'):
        return 'UNHEALTHY', 'racadm_reported_status'
    if state in ('offline', 'failed', 'missing', 'degraded', 'rebuilding', 'blocked'):
        return 'UNHEALTHY', 'racadm_reported_state'
    good_states = ('online','ready','non-raid','jbod','hotspare','hot spare','global hotspare','dedicated hotspare') if 'address' in row else ('online',)
    if status == 'ok' and rollup == 'ok' and state in good_states:
        return 'HEALTHY', 'racadm_status_ok_and_online'
    return 'UNKNOWN', 'incomplete_racadm_health_evidence'


def collect(run, budget, cli, platform='linux'):
    data = {'observed_at': now(), 'os_disks': [], 'md_arrays': [], 'controllers': [],
            'physical_drives': [], 'virtual_drives': [], 'coverage': {}, 'probes': [],
            'limitations': ['OS disks may be virtual disks, SAN LUNs or guest devices.',
                            'No SMART self-test, patrol read, rescan, repair or configuration change is performed.',
                            'Linux MD, Dell RACADM and StorCLI/PERC are covered; ZFS, LVM RAID and other controllers are outside scope.',
                            'Device names and controller IDs are observation-local; no physical-to-OS mapping is inferred.'],
            'scope': {'excluded_devices': [], 'selection_complete': True}}

    def section(name, command, parser, json_output=True):
        result = probe(run, command, budget, data['probes'], name)
        reason = result['error']
        if name == 'virtual_drives' and not json_output and racadm_empty_virtual_disks(result['stdout'] or ''):
            if result['truncated'] or result['error'] not in (None, 'command_failed') or (result['stderr'] or '').strip():
                data['coverage'][name] = {'status': 'unknown', 'reason': 'incomplete_or_conflicting_empty_response'}
            else:
                data[name] = []
                data['coverage'][name] = {'status': 'complete', 'reason': 'source_reports_no_virtual_disks'}
            return
        if result['status'] == 'success':
            try:
                parsed = parser(strict_json(result['stdout']) if json_output else result['stdout'])
                if isinstance(parsed, dict) and 'records' in parsed:
                    data[name] = parsed['records']
                    if parsed['errors']:
                        data['coverage'][name] = {'status': 'partial', 'reason': 'incomplete_source_data'}
                        return
                else:
                    data[name] = parsed
                data['coverage'][name] = {'status': 'complete', 'reason': None}
                return
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                reason = 'invalid_or_unsupported_output'
        data['coverage'][name] = {'status': 'unknown', 'reason': reason}

    if platform == 'linux':
        section('os_disks', shlex.join(LSBLK), parse_disks)
        script = Path(__file__).with_name('md_probe.py').read_text()

        def md(value):
            if not isinstance(value, dict) or not isinstance(value.get('arrays'), list) or not isinstance(value.get('errors'), list):
                raise ValueError('invalid sysfs response')
            return {'records': value['arrays'], 'errors': value['errors']}

        section('md_arrays', shlex.join(['python3', '-c', script]), md)
    else:
        def esxi_disks(output):
            reader = csv.DictReader(io.StringIO(output))
            if not reader.fieldnames or 'Device' not in reader.fieldnames:
                raise ValueError('unrecognized esxcli CSV columns')
            rows = list(reader)
            if any(not row.get('Device') or None in row for row in rows):
                raise ValueError('invalid esxcli CSV row')
            return [{'path': row['Device'], 'scope': 'os_visible_not_verified_physical',
                     'details': row} for row in rows]
        section('os_disks', 'esxcli --formatter=csv storage core device list', esxi_disks, False)
        data['coverage']['md_arrays'] = {'status': 'not_applicable', 'reason': 'linux_md_only'}
    if cli == 'auto':
        result = probe(run, DISCOVER, budget, data['probes'], 'raid_cli_discovery')
        candidate = (result['stdout'] or '').strip()
        cli = candidate if (result['status'] == 'success' and
                            re.fullmatch(r'(?:/[A-Za-z0-9_./-]+|racadm|idracadm7|storcli64|storcli|perccli64|perccli)', candidate)) else None
    if not cli and platform == 'esxi':
        # ESXi's installed LSU plugin can expose RAID member locations without
        # vendor CLI. Locations alone do not establish serial/state/health.
        queried, failed = 0, 0
        for disk in data['os_disks']:
            info = disk['details']
            if info.get('DeviceType', '').strip() != 'Direct-Access' or info.get('IsLocal', '').strip() != 'true':
                continue
            boot = info.get('IsBootDevice', '').strip().lower()
            data['virtual_drives'].append({'controller': None, 'logical_device': disk['path'],
                                           'provider': 'esxcli_lsu', 'summary': info})
            command = shlex.join(['esxcli', '--formatter=csv', 'storage', 'core', 'device',
                                  'raid', 'list', '--device', disk['path']])
            source = probe(run, command, budget, data['probes'], 'lsu_members_' + str(queried))
            queried += 1
            if source['status'] != 'success':
                failed += 1
                continue
            try:
                reader = csv.DictReader(io.StringIO(source['stdout']))
                if not reader.fieldnames or 'PhysicalLocation' not in reader.fieldnames:
                    raise ValueError('unrecognized LSU CSV columns')
                rows = list(reader)
                if any(not row.get('PhysicalLocation') or None in row for row in rows):
                    raise ValueError('invalid LSU location row')
                addresses = {row['PhysicalLocation'] for row in rows}
                reported = info.get('NumberofPhysicalDrives', '').strip()
                if not rows or reported.isdigit() and int(reported) != len(addresses):
                    failed += 1
                for row in rows:
                    data['physical_drives'].append({'controller': None, 'address': row['PhysicalLocation'],
                        'logical_device': disk['path'], 'provider': 'esxcli_lsu', 'summary': row, 'details': {}})
            except (ValueError, TypeError, csv.Error):
                failed += 1
        data['enumeration'] = {'complete': queried > 0 and failed == 0, 'queried_devices': queried, 'failed_devices': failed}
        data['coverage']['controllers'] = {'status': 'unknown', 'reason': 'raid_cli_unavailable'}
        data['coverage']['virtual_drives'] = {'status': 'partial' if queried else 'unknown',
                                              'reason': 'os_reported_raid_metadata_only'}
        data['coverage']['physical_drives'] = {
            'status': 'partial' if data['physical_drives'] else 'unknown',
            'reason': 'lsu_locations_only_with_device_gaps' if failed else 'lsu_locations_only'}
        data['limitations'].append('ESXi LSU provides member locations only; physical serial/model/state and unsupported controllers remain unknown.')
    elif cli and cli.rsplit('/', 1)[-1] in ('racadm', 'idracadm7'):
        for name, kind in [('controllers', 'controllers'), ('physical_drives', 'pdisks'), ('virtual_drives', 'vdisks')]:
            section(name, shlex.join([cli, 'storage', 'get', kind, '-o']),
                    lambda output, section=name: parse_racadm(output, section), False)
    elif cli:
        for name, args in [('controllers', ['/call', 'show', 'all', 'J']),
                           ('physical_drives', ['/call/eall/sall', 'show', 'all', 'J']),
                           ('virtual_drives', ['/call', 'show', 'all', 'J'])]:
            section(name, shlex.join([cli, *args]), lambda value, kind=name: parse_raid(value, kind))
    else:
        for name in ('controllers', 'physical_drives', 'virtual_drives'):
            data['coverage'][name] = {'status': 'unknown', 'reason': 'raid_cli_unavailable'}
    complete = sum(c['status'] in ('complete', 'not_applicable') for c in data['coverage'].values())
    usable = any(data[name] or data['coverage'][name]['status'] == 'complete' for name in data['coverage'])
    data['status'] = 'success' if complete == 5 else 'partial' if usable else 'failed'
    return {'status': data['status'],
            'reason_code': 'inventory_collected' if complete == 5 else 'inventory_incomplete',
            'message': 'Collection coverage is separate from disk/RAID health; inspect source states and gaps.',
            'data': data}


def nested_value(value, names):
    if isinstance(value, dict):
        for name in names:
            if name in value and not isinstance(value[name], (dict, list)):
                return value[name]
        for item in value.values():
            found = nested_value(item, names)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = nested_value(item, names)
            if found is not None:
                return found
    return None


def drive_health(row):
    if row.get('provider') == 'racadm':
        return racadm_health(row)
    if row.get('provider') == 'esxcli_lsu':
        return 'UNKNOWN', 'member_location_is_not_health_evidence'
    details = row.get('details', {})
    invalid_counter = False
    for name in ('Predictive Failure Count', 'Media Error Count'):
        count = nested_value(details, [name])
        if count is None:
            continue
        if type(count) is int and count >= 0 or isinstance(count, str) and count.isdigit():
            if int(count) > 0:
                return 'UNHEALTHY', 'reported_drive_errors'
        else:
            invalid_counter = True
    smart = nested_value(details, ['S.M.A.R.T alert flagged by drive', 'SMART alert flagged by drive'])
    if str(smart).strip().lower() in ('yes', 'true', '1'):
        return 'UNHEALTHY', 'smart_alert'
    state = str(row.get('summary', {}).get('State', '')).strip().lower()
    if invalid_counter:
        return 'UNKNOWN', 'invalid_reported_drive_counter'
    if state in ('onln', 'online', 'ugood', 'ghs', 'dhs', 'jbod'):
        return 'HEALTHY', 'vendor_drive_state'
    if state in ('offln', 'offline', 'ubad', 'failed', 'fail', 'missing', 'rbld', 'rebuild'):
        return 'UNHEALTHY', 'vendor_drive_state'
    return 'UNKNOWN', 'unrecognized_or_missing_drive_state'


def volume_health(row):
    if row.get('provider') == 'racadm':
        return racadm_health(row)
    if row.get('provider') == 'esxcli_lsu':
        return 'UNKNOWN', 'os_device_on_is_not_raid_health'
    state = str(row.get('summary', {}).get('State', '')).strip().lower()
    if state in ('optl', 'optimal'):
        return 'HEALTHY', 'vendor_virtual_drive_state'
    if state in ('dgrd', 'degraded', 'ofln', 'offln', 'offline', 'pdgd', 'partially degraded', 'failed'):
        return 'UNHEALTHY', 'vendor_virtual_drive_state'
    return 'UNKNOWN', 'unrecognized_or_missing_raid_state'


def md_health(row):
    degraded = row.get('degraded')
    state = row.get('array_state')
    if str(degraded).isdigit() and int(degraded) > 0:
        return 'UNHEALTHY', 'md_degraded_members'
    if state in ('clear', 'inactive', 'suspended', 'broken'):
        return 'UNHEALTHY', 'md_array_not_active'
    if row.get('sync_action') in ('recover', 'resync', 'reshape', 'repair'):
        return 'UNKNOWN', 'md_synchronization_in_progress'
    if str(degraded) == '0' and state in ('clean', 'active', 'active-idle', 'write-pending') and row.get('sync_action') == 'idle':
        return 'HEALTHY', 'md_active_not_degraded'
    return 'UNKNOWN', 'incomplete_md_health_evidence'


def disk_usage(row):
    """Describe the physical drive's use without inferring RAID membership."""
    values = row.get('details', {})
    spare = nested_value(values, ['Hotspare', 'HotSpareStatus'])
    state = str(row.get('summary', {}).get('State', '')).strip().lower()
    if str(spare).lower() in ('yes', 'true', 'global', 'dedicated', '1', '2') or state in ('ghs', 'dhs', 'hotspare', 'hot spare'):
        return 'spare'
    if state in ('ready', 'ugood'):
        return 'unconfigured'
    if state in ('non-raid', 'jbod'):
        return 'standalone'
    return 'online' if state in ('online', 'onln') else 'unknown'


def physical_inventory_summary(data, values):
    """Count every reported physical disk independently of virtual disks/RAID."""
    expected_data = values.get('expected_disks', {}).get('data')
    boot_policy = values.get('boot_policy', 'auto')
    expected_raids = values.get('expected_raids')
    controllers = {r['controller']: r for r in data['controllers']}
    boss_ids = {identity for identity,row in controllers.items()
                if re.match(r'^BOSS(?:-|\b)', str(nested_value(row['details'], ['Name', 'Model']) or ''), re.I)}
    boss_s1_ids = {identity for identity,row in controllers.items()
                   if re.match(r'^BOSS-S1(?:\b|\s)', str(nested_value(row['details'], ['Name', 'Model']) or ''), re.I)}
    expected_boot = 2 if boot_policy == 'mirrored-ssd-pair' else 2 * len(boss_s1_ids) if boss_s1_ids else None
    source_complete = data['coverage']['physical_drives']['status'] == 'complete'
    controllers_complete = data['coverage']['controllers']['status'] == 'complete'
    native = any(row.get('provider') == 'esxcli_lsu' for row in data['virtual_drives'])
    os_devices = {r['path']:r.get('details', {}) for r in data['os_disks']}
    selected = {'data': [], 'boot': [], 'unknown': []}
    role_complete = controllers_complete and source_complete
    for row in data['physical_drives']:
        row['usage'] = disk_usage(row)
        row['health'], row['health_reason'] = drive_health(row)
        if row.get('provider') == 'esxcli_lsu':
            flag = os_devices.get(row.get('logical_device'), {}).get('IsBootDevice', '').strip().lower()
            role = 'boot' if flag == 'true' else 'data' if flag == 'false' else 'unknown'
        elif row.get('controller') in boss_ids:
            role = 'boot'
        elif row.get('controller') in controllers:
            model = nested_value(controllers[row['controller']]['details'], ['Name', 'Model'])
            role = 'data' if model and str(model).strip().lower() not in ('unknown','not applicable') else 'unknown'
        else:
            role = 'unknown'
        row['role'] = role
        selected[role].append(row)
        if role == 'unknown':
            role_complete = False
    for key, interpret in (('virtual_drives', volume_health), ('md_arrays', md_health)):
        for row in data[key]:
            row['health'], row['health_reason'] = interpret(row)
    # A limited LSU source cannot verify an all-installed-disk total: it sees
    # RAID members but not unconfigured, standalone or spare drives.
    if native:
        role_complete = False
    data['scope']['selection_complete'] = role_complete
    findings, groups = [], []
    def aggregate(rows, complete, empty='UNKNOWN'):
        states = [row['health'] for row in rows]
        if 'UNHEALTHY' in states:
            return 'UNHEALTHY'
        if not complete or 'UNKNOWN' in states:
            return 'UNKNOWN'
        return 'HEALTHY' if states else empty
    for role, expected in (('data', expected_data), ('boot', expected_boot), ('unknown', None)):
        rows = selected[role]
        if role != 'data' and not rows and expected is None:
            continue
        observed = len({(r.get('controller'),r['address']) for r in rows})
        if native:
            by_device = {}
            for r in rows:
                by_device.setdefault(r.get('logical_device'), set()).add(r['address'])
            observed = max((len(v) for v in by_device.values()), default=0)
        complete = role_complete and role != 'unknown'
        count_status = ('NOT CONFIGURED' if expected is None else
                        'MATCH' if complete and observed == expected else 'MISMATCH' if complete else 'UNVERIFIED')
        health = 'HEALTHY' if complete and observed == 0 and expected == 0 else aggregate(rows, complete)
        overall = 'UNHEALTHY' if count_status == 'MISMATCH' or health == 'UNHEALTHY' else 'HEALTHY' if count_status == 'MATCH' and health == 'HEALTHY' else 'UNKNOWN'
        group = {'id':role,'role':role,'observed':observed,'total':observed if complete else None,
                 'expected':expected,'expected_source':'operator' if role=='data' and expected is not None else 'fixed mirrored-SSD policy' if expected is not None else 'not_configured',
                 'enumeration_complete':complete,'count_status':count_status,'disk_health':health,'health':overall,
                 'physical_ids':[r['address'] for r in rows],
                 'controller_ids':sorted({r['controller'] for r in rows if r.get('controller') is not None})}
        groups.append(group)
        if count_status != 'MATCH' or health != 'HEALTHY':
            severity = 'critical' if count_status in ('MISMATCH','UNVERIFIED') or health == 'UNHEALTHY' else 'warning'
            findings.append({'code':'physical_inventory_requires_attention','severity':severity,
                             'message':f'{role.capitalize()} disks: observed {observed}, expected {expected}; count {count_status}; health {health}.'})
    volumes_complete = data['coverage']['virtual_drives']['status'] == 'complete' and data['coverage']['md_arrays']['status'] in ('complete','not_applicable')
    raid_count = len(data['virtual_drives']) + len(data['md_arrays'])
    raid_health = aggregate(data['virtual_drives'] + data['md_arrays'], volumes_complete, empty='NOT CONFIGURED')
    raid_count_status = ('NOT CONFIGURED' if expected_raids is None else
                         'MATCH' if volumes_complete and raid_count == expected_raids else 'MISMATCH' if volumes_complete else 'UNVERIFIED')
    if raid_count_status in ('MISMATCH','UNVERIFIED'):
        findings.append({'code':'raid_count_requires_attention','severity':'critical',
                         'message':f'RAID arrays/volumes: observed {raid_count}, expected {expected_raids}; count {raid_count_status}.'})
    # Boot mirroring is a RAID check, never a filter on the physical inventory.
    require_boot_mirror = expected_boot is not None
    boot_arrays = [r for r in data['virtual_drives'] if r.get('controller') in boss_ids]
    if require_boot_mirror and volumes_complete and not boot_arrays:
        raid_health = 'UNHEALTHY'
        findings.append({'code':'boot_mirror_missing','severity':'critical','message':'The mirrored boot policy requires a reported boot RAID volume.'})
    if require_boot_mirror and boot_arrays:
        # Presence and Online state do not prove mirroring. Verify every
        # identified boot controller and retain unknown layouts as gaps.
        missing = volumes_complete and any(not any(r.get('controller') == identity for r in boot_arrays)
                                           for identity in boss_ids)
        levels = [re.sub(r'[^a-z0-9]', '', str(r.get('raid_level') or
                  r.get('summary', {}).get('TYPE') or '')) for r in boot_arrays]
        wrong = any(re.fullmatch(r'raid\d+', level) and level != 'raid1' for level in levels)
        unknown = any(not re.fullmatch(r'raid\d+', level) for level in levels)
        if missing or wrong:
            raid_health = 'UNHEALTHY'
            findings.append({'code':'boot_mirror_invalid','severity':'critical',
                             'message':'Each identified boot controller requires a reported RAID-1 boot volume.'})
        elif unknown:
            if raid_health != 'UNHEALTHY':
                raid_health = 'UNKNOWN'
            findings.append({'code':'boot_mirror_unverified','severity':'warning',
                             'message':'A boot RAID level is unavailable; mirroring is unverified.'})
    if raid_health in ('UNKNOWN','UNHEALTHY'):
        findings.append({'code':'raid_health_requires_attention','severity':'critical' if raid_health=='UNHEALTHY' else 'warning',
                         'message':'RAID health is '+raid_health+'.'})
    controller_bad = any(str(r['details'].get(k,'')).lower() in ('critical','non-critical','error','failed')
                         for r in data['controllers'] for k in ('Status','RollupStatus'))
    active_ids = {r.get('controller') for r in data['physical_drives']+data['virtual_drives']}
    controller_unknown = any(r.get('provider')=='racadm' and r['controller'] in active_ids and
                             any(str(r['details'].get(k,'')).lower()!='ok' for k in ('Status','RollupStatus'))
                             for r in data['controllers'])
    if controller_bad or controller_unknown:
        findings.append({'code':'controller_health_requires_attention','severity':'critical' if controller_bad else 'warning',
                         'message':'Storage controller health is '+('UNHEALTHY' if controller_bad else 'UNKNOWN')+'.'})
    def rollup(key):
        states=[g[key] for g in groups]
        return 'UNHEALTHY' if 'UNHEALTHY' in states else 'HEALTHY' if states and all(s=='HEALTHY' for s in states) else 'UNKNOWN'
    counts = [g['count_status'] for g in groups]
    count_status = 'MISMATCH' if 'MISMATCH' in counts else 'UNVERIFIED' if 'UNVERIFIED' in counts else 'MATCH' if all(c=='MATCH' for c in counts) else 'NOT CONFIGURED'
    all_observed = (max((g['observed'] for g in groups), default=0) if native else
                    len({(r.get('controller'), r['address']) for r in data['physical_drives']}))
    total = all_observed if source_complete and not native else None
    expected = sum(g['expected'] for g in groups) if all(g['expected'] is not None for g in groups) else None
    overall = ('UNHEALTHY' if rollup('health')=='UNHEALTHY' or raid_health=='UNHEALTHY' or raid_count_status=='MISMATCH' or controller_bad
               else 'HEALTHY' if rollup('health')=='HEALTHY' and raid_health in ('HEALTHY','NOT CONFIGURED') and raid_count_status not in ('MISMATCH','UNVERIFIED') and not controller_unknown else 'UNKNOWN')
    data['disk_groups'] = groups
    data['policy'] = {'expected_disks':dict(values.get('expected_disks',{})), 'boot_policy':boot_policy,'expected_raids':expected_raids}
    data['findings'] = findings
    data['summary'] = {'health':overall,
        'physical_disks':{'observed':all_observed,'total':total,'enumeration_complete':source_complete and not native,
                          'expected':expected,'count_status':count_status,'health':aggregate(data['physical_drives'], source_complete and not native)},
        'raid_volumes':{'observed':raid_count,'total':raid_count if volumes_complete else None,'enumeration_complete':volumes_complete,
                        'expected':expected_raids,'count_status':raid_count_status,'health':raid_health}}
    critical = any(f['severity']=='critical' for f in findings)
    return {'label':'STORAGE '+overall,'severity':'critical' if critical else 'info' if overall=='HEALTHY' else 'warning',
            'summary':f'{all_observed} reported physical disks (including spare/unconfigured/standalone); {raid_count} RAID arrays/volumes; health {overall}.'}


def session_command(session, command, **kwargs):
    # Session uses argv; only the fixed discovery loop needs a POSIX shell.
    argv = ['/bin/sh', '-c', command] if command == DISCOVER else shlex.split(command)
    return session.exec_command(argv, **kwargs)


def execute(recipe):
    budget, cli, require_root = configuration(recipe.vars, recipe.timeout)
    evidence = []
    run_session = lambda command, **kwargs: session_command(recipe.session, command, **kwargs)
    platform = probe(run_session,
                     'uname -s', budget, evidence, 'platform')
    target = {'Linux': 'linux', 'VMkernel': 'esxi'}.get((platform['stdout'] or '').strip())
    if platform['status'] != 'success' or target is None:
        return {'status': 'unsupported' if platform['status'] == 'success' else 'failed',
                'reason_code': 'unsupported_platform', 'message': 'This recipe requires Linux or ESXi.', 'data': {'probes': evidence}}
    # The runner's Core execution scope already verified the current actor,
    # including ESXi's supported identity probes when the id utility is absent.
    identity = recipe.report.get('execution_identity', {})
    actual = identity.get('actual') or {}
    uid = actual.get('effective_uid')
    if (identity.get('verified') is not True or type(uid) is not int or uid < 0
            or not isinstance(actual.get('username'), str) or not actual['username']):
        return {'status': 'failed', 'reason_code': 'identity_unverified',
                'message': 'Core execution identity is unavailable or unverified.', 'data': {'probes': evidence}}
    already_root = uid == 0
    if require_root and not already_root:
        if target == 'esxi':
            return {'status': 'failed', 'reason_code': 'root_required',
                    'message': 'Select an authorized root execution account for ESXi; no escalation was attempted.', 'data': {'probes': evidence}}
        with recipe.root() as root:
            result = collect(root, budget, cli, target)
    else:
        result = collect(run_session, budget, cli, target)
    result['data']['probes'] = evidence + result['data']['probes']
    result['data']['platform'] = target
    result['data']['privilege_scope'] = 'verified_root' if require_root or already_root else 'selected_execution_account'
    result['assessment'] = physical_inventory_summary(result['data'], recipe.vars)
    if result['status'] == 'success' and (result['assessment']['severity'] == 'critical' or result['data']['summary']['health'] != 'HEALTHY'):
        result['status'] = result['data']['status'] = 'partial'
        result['reason_code'] = 'storage_requires_attention'
    return result
