"""Bounded, allowlisted inventory details 0.1.0; no environment/argv/file crawl."""
from datetime import datetime, timezone
import csv
import io
import json
import math
import re
import shlex
import time

VERSION = '0.1.0'
FIELDS = {
    'system': ('hostname', 'platform', 'system_name', 'system_version', 'kernel_name', 'kernel_release', 'architecture', 'uptime_seconds', 'timezone', 'virtualization'),
    'hardware': ('cpu_model', 'logical_cpus', 'memory_total_bytes', 'vendor', 'model', 'serial', 'uuid'),
    'storage': ('filesystems', 'block_devices'),
    'network': ('interfaces', 'routes', 'dns_servers', 'listening_endpoints'),
    'software': ('packages',),
    'services': ('services',),
}
MAX_OUTPUT = 262144
MAX_ITEMS = 2000


def empty():
    return {section: {field: None for field in fields} for section, fields in FIELDS.items()}


def validate(data):
    if not isinstance(data, dict) or set(data) != set(FIELDS):
        raise ValueError('inventory sections differ from contract')
    for section, fields in FIELDS.items():
        if not isinstance(data[section], dict) or set(data[section]) != set(fields):
            raise ValueError('inventory fields differ from contract')
        for field, value in data[section].items():
            if value is not None:
                expected = list if section in ('storage', 'network', 'software', 'services') else (int, float) if field == 'uptime_seconds' else int if field in ('logical_cpus', 'memory_total_bytes') else str
                if not isinstance(value, expected) or isinstance(value, bool):
                    raise ValueError('inventory field type mismatch')
                if isinstance(value, (int, float)) and value < 0:
                    raise ValueError('negative inventory capacity')
            if value is not None and not isinstance(value, (str, int, float, list)) or isinstance(value, bool):
                raise ValueError('invalid inventory value')
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError('nonfinite inventory value')
            if isinstance(value, str) and (len(value) > MAX_OUTPUT or '\x00' in value):
                raise ValueError('invalid inventory text')
            if isinstance(value, list):
                if len(value) > MAX_ITEMS or any(not isinstance(row, dict) or any(not isinstance(k, str) or v is not None and not isinstance(v, (str, int, float, bool)) for k, v in row.items()) for row in value):
                    raise ValueError('invalid inventory table')
    json.dumps(data, allow_nan=False)
    return data


def csv_text(data):
    """Long-form portable CSV; missing values are empty cells, never NULL."""
    validate(data)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(('section', 'field', 'item', 'attribute', 'value'))
    def cell(value):
        # Protect text opened by spreadsheet programs; numeric values stay numeric.
        if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
            return "'" + value
        return '' if value is None else value
    for section, values in data.items():
        for field, value in values.items():
            if isinstance(value, list):
                if not value:
                    writer.writerow((section, field, '', '', '[]'))
                for index, row in enumerate(value):
                    for key, item in row.items():
                        writer.writerow((section, field, index, cell(key), cell(item)))
            else:
                writer.writerow((section, field, '', '', cell(value)))
    return stream.getvalue()


def integer(text):
    value = int(text.strip())
    if value < 0:
        raise ValueError('negative capacity')
    return value


def lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def pairs(text):
    return {key.strip(): value.strip() for line in text.splitlines() if ':' in line for key, value in [line.split(':', 1)]}


def text_value(text):
    value = text.strip()
    if not value or '\x00' in value:
        raise ValueError('missing text')
    return value


def table(text, columns, *, header=False):
    rows = lines(text)[1:] if header else lines(text)
    result = []
    for line in rows:
        values = line.split(None, len(columns) - 1)
        if len(values) != len(columns):
            raise ValueError('malformed table')
        result.append(dict(zip(columns, values)))
    return result


def filesystems(text):
    result = table(text, ('source', 'total_kib', 'used_kib', 'available_kib', 'used_percent', 'mountpoint'), header=True)
    for row in result:
        for key in ('total_kib', 'used_kib', 'available_kib'):
            row[key.replace('_kib', '_bytes')] = integer(row.pop(key)) * 1024
    return result


def packages(text):
    return table(text, ('name', 'version'))


def linux_interfaces(text):
    rows = []
    for item in json.loads(text):
        for address in item.get('addr_info', []) or [None]:
            rows.append({'name': item['ifname'], 'mac': item.get('address'), 'mtu': item.get('mtu'),
                         'state': item.get('operstate'), 'address': address.get('local') if address else None,
                         'prefix_length': address.get('prefixlen') if address else None})
    return rows


def linux_devices(text):
    rows = []
    def walk(items):
        for item in items:
            rows.append({key: item.get(key) for key in ('name', 'type', 'size', 'fstype', 'mountpoint', 'model')})
            walk(item.get('children', []))
    walk(json.loads(text)['blockdevices'])
    return rows


def bsd_interfaces(text):
    rows = []
    name = None
    for line in text.splitlines():
        if line and not line[0].isspace():
            name = line.split(':', 1)[0]
        values = line.split()
        if name and values and values[0] in ('inet', 'inet6', 'ether'):
            rows.append({'name': name, 'kind': values[0], 'address': values[1]})
    return rows


def dns(text):
    return [{'address': row.split()[1]} for row in text.splitlines() if row.strip().startswith('nameserver ') and len(row.split()) >= 2]


def collect(session, report, platform, timeout, *, budget=90):
    data = empty()
    process = {'contract_version': VERSION, 'scope': 'environment-visible-to-effective-account',
               'started_at': datetime.now(timezone.utc).isoformat(), 'probes': [],
               'limits': {'total_seconds': budget, 'command_seconds': timeout, 'output_bytes': MAX_OUTPUT, 'items': MAX_ITEMS}}
    report.update(inventory_contract_version=VERSION, inventory=data, collection_process=process)
    for field in FIELDS['system'][:7]:
        data['system'][field] = report['observations'][field]['value']
    deadline = time.monotonic() + budget
    def probe(section, field, command, parser=text_value):
        item = {'section': section, 'field': field, 'status': 'not_attempted', 'command': command,
                'observed_at': datetime.now(timezone.utc).isoformat()}
        process['probes'].append(item)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            item['reason_code'] = 'total_budget_exhausted'
            return
        try:
            # Target-side byte bound. Producer exit code is saved through a
            # bounded pipe; timeout still bounds producers blocked after head.
            script = '( ' + command + '; printf "\\n__OPSFEAST_EXIT_%s\\n" "$?" ) 2>/dev/null | head -c ' + str(MAX_OUTPUT + 1)
            result = session.exec_command(['/bin/sh', '-c', script], check=False, command_timeout=min(timeout, remaining))
            output = result.stdout
            if result.exitcode != 0:
                item.update(status='failed', reason_code='probe_shell_failed', exitcode=result.exitcode)
                return
            if len(output.encode()) > MAX_OUTPUT or getattr(result, 'stdout_truncated', False):
                item.update(status='truncated', reason_code='output_limit')
                return
            # Persistent PTY consoles use CRLF; preserve byte limits before normalization.
            output = output.replace('\r\n', '\n')
            match = re.search(r'\n__OPSFEAST_EXIT_(\d+)\n?$', output)
            if match is None:
                item.update(status='failed', reason_code='producer_marker_missing')
                return
            item['exitcode'] = int(match[1])
            if item['exitcode'] != 0:
                item.update(status='unavailable', reason_code='command_not_found' if item['exitcode'] == 127
                            else 'command_not_executable' if item['exitcode'] == 126 else 'command_failed')
                return
            value = parser(output[:match.start()])
            if isinstance(value, list) and len(value) > MAX_ITEMS:
                item.update(status='truncated', reason_code='item_limit')
                return
            data[section][field] = value
            item['status'] = 'success'
        except Exception as exc:
            item.update(status='failed', error_type=type(exc).__name__,
                        reason_code='parse_failed' if isinstance(exc, (ValueError, KeyError, TypeError)) else 'probe_execution_failed')
    probe('storage', 'filesystems', 'LC_ALL=C df -Pk', filesystems)
    probe('system', 'timezone', 'date +%Z')
    if platform == 'linux':
        probe('system', 'uptime_seconds', 'cat /proc/uptime', lambda t: float(t.split()[0]))
        probe('system', 'virtualization', 'systemd-detect-virt', text_value)
        probe('hardware', 'cpu_model', 'cat /proc/cpuinfo', lambda t: text_value(pairs(t).get('model name', pairs(t).get('Processor', ''))))
        probe('hardware', 'logical_cpus', 'getconf _NPROCESSORS_ONLN', integer)
        probe('hardware', 'memory_total_bytes', 'cat /proc/meminfo', lambda t: integer(pairs(t)['MemTotal'].split()[0]) * 1024)
        for field, path in (('vendor', 'sys_vendor'), ('model', 'product_name'), ('serial', 'product_serial'), ('uuid', 'product_uuid')):
            probe('hardware', field, 'cat /sys/class/dmi/id/' + path)
        probe('storage', 'block_devices', 'lsblk -b -J -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT,MODEL', linux_devices)
        probe('network', 'interfaces', 'ip -j address show', linux_interfaces)
        probe('network', 'routes', 'ip -j route show table all', lambda t: [{k: v for k, v in row.items() if k in ('dst', 'gateway', 'dev', 'protocol', 'scope', 'prefsrc', 'metric', 'table')} for row in json.loads(t)])
        probe('network', 'listening_endpoints', 'LC_ALL=C ss -H -lntu', lambda t: table(t, ('protocol', 'state', 'recv_queue', 'send_queue', 'local', 'peer')))
        probe('software', 'packages', "if command -v dpkg-query >/dev/null; then dpkg-query -W -f='${Package} ${Version}\\n'; elif command -v rpm >/dev/null; then rpm -qa --qf '%{NAME} %{VERSION}-%{RELEASE}\\n'; else exit 127; fi", packages)
        probe('services', 'services', 'LC_ALL=C systemctl list-units --type=service --all --no-legend --no-pager --plain', lambda t: table(t, ('name', 'load', 'active', 'sub', 'description')))
    elif platform in ('macos', 'freebsd'):
        probe('hardware', 'logical_cpus', 'sysctl -n hw.ncpu', integer)
        probe('hardware', 'memory_total_bytes', 'sysctl -n ' + ('hw.memsize' if platform == 'macos' else 'hw.physmem'), integer)
        probe('hardware', 'cpu_model', 'sysctl -n ' + ('machdep.cpu.brand_string' if platform == 'macos' else 'hw.model'))
        probe('system', 'uptime_seconds', 'sysctl -n kern.boottime; date +%s', lambda t: max(0, int(t.splitlines()[-1]) - int(re.search(r'sec\s*=\s*(\d+)', t)[1])))
        probe('network', 'interfaces', 'ifconfig -a', bsd_interfaces)
        probe('network', 'routes', 'LC_ALL=C netstat -rn', lambda t: [{'entry': row} for row in lines(t)])
        if platform == 'freebsd':
            probe('software', 'packages', "pkg query -a '%n %v'", packages)
            probe('services', 'services', 'service -e', lambda t: [{'name': row} for row in lines(t)])
            for field, name in (('vendor', 'maker'), ('model', 'product'), ('serial', 'serial'), ('uuid', 'uuid')):
                probe('hardware', field, 'kenv -q smbios.system.' + name)
            probe('storage', 'block_devices', 'sysctl -n kern.disks', lambda t: [{'name': row} for row in t.split()])
        else:
            probe('hardware', 'model', 'sysctl -n hw.model')
            probe('software', 'packages', 'pkgutil --pkgs', lambda t: [{'name': row, 'version': None, 'kind': 'installer-receipt'} for row in lines(t)])
            probe('services', 'services', 'launchctl list', lambda t: table(t, ('pid', 'exit_status', 'name'), header=True))
    elif platform == 'esxi':
        probe('hardware', 'logical_cpus', 'esxcli hardware cpu global get', lambda t: integer(pairs(t)['CPU Threads']))
        probe('software', 'packages', 'esxcli software vib list', lambda t: [{'entry': row} for row in lines(t)])
        probe('network', 'interfaces', 'esxcli network ip interface ipv4 get', lambda t: [{'entry': row} for row in lines(t)])
        probe('services', 'services', 'chkconfig --list', lambda t: [{'entry': row} for row in lines(t)])
    if platform != 'esxi':
        probe('network', 'dns_servers', 'cat /etc/resolv.conf', dns)
    # Unimplemented or inapplicable probes are visible in process only.
    attempted = {(p['section'], p['field']) for p in process['probes']}
    for section, fields in FIELDS.items():
        for field in fields:
            if (section, field) not in attempted and not (section == 'system' and field in FIELDS['system'][:7]):
                process['probes'].append({'section': section, 'field': field, 'status': 'not_supported'})
    validate(data)
    process['finished_at'] = datetime.now(timezone.utc).isoformat()
    return data
