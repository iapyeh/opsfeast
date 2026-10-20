"""Inventory property catalog 0.1.0: standard YANG paths first, explicit extensions.

Samples reference schema nodes; they are not complete RFC 7951 datastore documents.
No claim of full module conformance or NETCONF service is made.
"""
VERSION = '0.1.0'
MODULES = {
    'ietf-system': {'namespace': 'urn:ietf:params:xml:ns:yang:ietf-system', 'revision': '2014-08-06', 'source': 'https://www.rfc-editor.org/rfc/rfc7317.html'},
    'ietf-interfaces': {'namespace': 'urn:ietf:params:xml:ns:yang:ietf-interfaces', 'revision': '2018-02-20', 'source': 'https://www.rfc-editor.org/rfc/rfc8343.html'},
    'ietf-ip': {'namespace': 'urn:ietf:params:xml:ns:yang:ietf-ip', 'revision': '2018-02-22', 'source': 'https://www.rfc-editor.org/rfc/rfc8344.html'},
    'ietf-hardware': {'namespace': 'urn:ietf:params:xml:ns:yang:ietf-hardware', 'revision': '2018-03-13', 'source': 'https://www.rfc-editor.org/rfc/rfc8348.html'},
    'openconfig-system': {'namespace': 'http://openconfig.net/yang/system', 'revision': '2026-07-20',
        'source': 'https://github.com/openconfig/public/blob/60011899be5486cafc68b8d53f0cf4060d34a79d/release/models/system/openconfig-system.yang'},
    'opsfeast-inventory': {'namespace': 'urn:opsfeast:yang:inventory', 'revision': '2026-10-20', 'source': 'opsfeast-inventory.yang'},
}
JOBS = {
    'hardware-baseline': {'title': 'Hardware baseline', 'interval': 604800, 'enabled': True},
    'system-configuration': {'title': 'System configuration', 'interval': 86400, 'enabled': True},
    'network-configuration': {'title': 'Network configuration', 'interval': 86400, 'enabled': True},
    'software-inventory': {'title': 'Installed software', 'interval': 86400, 'enabled': True},
    'storage-layout': {'title': 'Storage layout', 'interval': 86400, 'enabled': True},
    'storage-capacity': {'title': 'Storage capacity', 'interval': 900, 'enabled': True},
    'service-state': {'title': 'Services and listening endpoints', 'interval': 300, 'enabled': True},
    'network-state': {'title': 'Network operational state', 'interval': 300, 'enabled': True},
    'system-runtime': {'title': 'System runtime', 'interval': 300, 'enabled': True},
    'resource-metrics': {'title': 'Resource utilization', 'interval': 60, 'enabled': True},
    'hardware-sensors': {'title': 'Hardware sensors', 'interval': 60, 'enabled': False},
}
PROPERTIES = {}


def add(name, job, kind='string', unit='', path=None, module=None, column=None, keys=(), note=''):
    module = module or ('ietf-system' if path and path.startswith('/ietf-system:') else 'opsfeast-inventory')
    extension = module == 'opsfeast-inventory'
    PROPERTIES[name] = {'id': name, 'job': job, 'type': kind, 'unit': unit,
        'fraction_digits': 6 if kind == 'number' else None,
        'yang_path': path or '/opsfeast-inventory:inventory/' + name.replace('_', '-').replace('.', '/'),
        'module': module, **MODULES[module], 'keys': list(keys), 'column': column,
        'description': note or name.replace('_', ' ').replace('.', ': '),
        'mapping': 'extension' if extension else 'standard'}


for name, leaf in [('hostname', '/system/hostname'), ('kernel_name', '/system-state/platform/os-name'),
                   ('system_version', '/system-state/platform/os-version'), ('kernel_release', '/system-state/platform/os-release'),
                   ('architecture', '/system-state/platform/machine')]:
    # system_version is userland/distribution version, not necessarily the kernel OS version.
    if name == 'system_version':
        add('system.' + name, 'system-configuration', note='Distribution/userland version; not equated with ietf-system os-version.')
    else:
        add('system.' + name, 'hardware-baseline' if name == 'architecture' else 'system-configuration',
            path='/ietf-system:' + leaf[1:])
for field in ('platform', 'system_name', 'timezone'):
    add('system.' + field, 'system-configuration', note='Timezone is the source abbreviation, not an IANA zone.' if field == 'timezone' else '')
add('system.virtualization', 'hardware-baseline')
add('system.kernel_version', 'system-configuration', path='/ietf-system:system-state/platform/os-version')
add('system.uptime_seconds', 'system-runtime', 'number', 'seconds')
add('system.boot_time', 'system-runtime', note='Estimated controller time minus uptime; not an authoritative target boot timestamp.')
for name in ('cpu_model', 'logical_cpus', 'memory_total_bytes', 'vendor', 'model', 'serial', 'uuid'):
    add('hardware.' + name, 'hardware-baseline', 'integer' if name in ('logical_cpus', 'memory_total_bytes') else 'string',
        'bytes' if name == 'memory_total_bytes' else '',
        note='Visible environment scope. Chassis/component identity is not assumed from whole-host DMI values.' if name in ('vendor','model','serial','uuid') else '')
for name, kind, unit in [('source','string',''),('mountpoint','string',''),('total_bytes','integer','bytes'),
                         ('used_bytes','integer','bytes'),('available_bytes','integer','bytes'),('used_percent','number','percent')]:
    add('storage.filesystems.' + name, 'storage-capacity' if name in ('total_bytes','used_bytes','available_bytes','used_percent') else 'storage-layout',
        kind, unit, column=name, keys=('source','mountpoint'))
for name,column,leaf in [('total_megabytes','total_bytes','size'),('used_megabytes','used_bytes','utilized'),('available_megabytes','available_bytes','available')]:
    add('storage.filesystems.'+name,'storage-capacity','integer','megabytes',
        path='/openconfig-system:system/mount-points/mount-point/state/'+leaf,module='openconfig-system',column=column,keys=('name',),
        note='Floor of exact source bytes / 1000000, matching integer decimal megabytes. Exact byte-valued properties remain separate to preserve precision.')
for name in ('name','type','size','fstype','mountpoint','model'):
    add('storage.block_devices.' + name, 'storage-layout', 'integer' if name == 'size' else 'string',
        'bytes' if name == 'size' else '', column=name, keys=('name',))
for name, leaf, kind in [('name','name','string'),('mac','phys-address','string'),('state','oper-status','string')]:
    add('network.interfaces.' + name, 'network-state' if name == 'state' else 'network-configuration', kind,
        path='/ietf-interfaces:interfaces/interface/' + leaf, module='ietf-interfaces', column=name, keys=('name',))
# Generic link MTU and mixed-family address rows are kept explicit until family-specific projection.
for name, kind in [('mtu','integer'),('address','string'),('prefix_length','integer'),('kind','string')]:
    add('network.interfaces.' + name, 'network-configuration', kind, 'bytes' if name == 'mtu' else '',
        column=name, keys=('name','kind','address'), note='Source interface/address observation; link MTU is not assumed to be IP-layer MTU.')
for family in ('ipv4','ipv6'):
    for column,leaf,kind in [('address','ip','string'),('prefix_length','prefix-length','integer')]:
        add('network.'+family+'.'+column, 'network-configuration', kind,
            path='/ietf-interfaces:interfaces/interface/ietf-ip:'+family+'/address/'+leaf,
            module='ietf-ip', column=column, keys=('name','address'), note='Address family selected explicitly; keys identify interface and address.')
add('network.dns_servers', 'network-configuration', 'array', note='Resolver-file nameserver snapshot; not claimed to be complete ietf-system configured/effective DNS policy.')
add('network.routes', 'network-state', 'array', note='Platform route rows; not falsely identified as complete ietf-routing RIB entries.')
add('network.listening_endpoints', 'service-state', 'array')
add('software.packages', 'software-inventory', 'array')
add('services.services', 'service-state', 'array')
for field in ('total', 'used', 'available'):
    add('storage.inodes.' + field, 'storage-capacity', 'integer', 'inodes', column=field, keys=('name',),
        path='/openconfig-system:system/mount-points/mount-point/state/inodes-'+{'total':'total','used':'utilized','available':'available'}[field],module='openconfig-system')
for field in ('total_bytes', 'used_bytes', 'available_bytes'):
    add('storage.swap.' + field, 'storage-capacity', 'integer', 'bytes')
for field in ('load_1m', 'load_5m', 'load_15m'):
    add('metrics.' + field, 'resource-metrics', 'number', 'tasks')
add('metrics.cpu_utilization_percent', 'resource-metrics', 'number', 'percent', note='Aggregate visible CPU busy-time delta; iowait treated as idle, guest columns are not added twice. Rounded to six decimal places; window recorded per probe.')
add('metrics.memory_available_bytes','resource-metrics','integer','bytes',
    path='/openconfig-system:system/memory/state/available',module='openconfig-system')
PROPERTIES['hardware.memory_total_bytes'].update(module='openconfig-system',**MODULES['openconfig-system'],
    yang_path='/openconfig-system:system/memory/state/physical',mapping='standard')
add('metrics.disk_counters', 'resource-metrics', 'array', note='Linux diskstats cumulative counters; raw counters, not rates. Linux sector counters are 512-byte sectors.')
add('metrics.interface_counters', 'resource-metrics', 'array', note='Linux net/dev cumulative counters; raw counters, not rates.')
add('metrics.memory_pressure', 'resource-metrics', 'array', note='Linux PSI some/full average stall percentages over 10/60/300 seconds and cumulative stall microseconds; missing PSI remains unavailable.')
for field,leaf in [('in_octets','in-octets'),('out_octets','out-octets'),('in_errors','in-errors'),
                   ('out_errors','out-errors'),('in_discards','in-discards'),('out_discards','out-discards')]:
    add('metrics.interfaces.'+field,'resource-metrics','integer','bytes' if field.endswith('octets') else 'packets',
        path='/ietf-interfaces:interfaces/interface/statistics/'+leaf,module='ietf-interfaces',column=field,keys=('name',),
        note='Cumulative counter, not a rate; use source times and reset/discontinuity evidence.')
add('sensors.temperatures', 'hardware-sensors', 'array', note='Linux thermal-zone readings, Celsius; sensor inventory does not establish ietf-hardware component identity.')
add('sensors.fans', 'hardware-sensors', 'array', note='Linux hwmon fan readings, RPM; unsupported sources remain explicit.')
PROPERTIES['system.hostname'].update(max_length=253,
    pattern=r'((([a-zA-Z0-9_]([a-zA-Z0-9\-_]){0,61})?[a-zA-Z0-9]\.)*([a-zA-Z0-9_]([a-zA-Z0-9\-_]){0,61})?[a-zA-Z0-9]\.?)|\.')
PROPERTIES['network.interfaces.mac']['pattern'] = r'([0-9a-fA-F]{2}(:[0-9a-fA-F]{2})*)?'
PROPERTIES['network.interfaces.state']['enum'] = ['up','down','testing','unknown','dormant','not-present','lower-layer-down']
for family,version,maximum in [('ipv4',4,32),('ipv6',6,128)]:
    PROPERTIES['network.'+family+'.address']['ip_version'] = version
    PROPERTIES['network.'+family+'.prefix_length']['maximum'] = maximum
for name,spec in PROPERTIES.items():
    if spec['module']=='ietf-interfaces':
        spec['key_paths'] = {'name':'/ietf-interfaces:interfaces/interface/name'}
    elif spec['module']=='ietf-ip':
        family = 'ipv4' if name.startswith('network.ipv4.') else 'ipv6'
        spec['key_paths'] = {'name':'/ietf-interfaces:interfaces/interface/name',
                             'address':'/ietf-interfaces:interfaces/interface/ietf-ip:'+family+'/address/ip'}
    elif spec['module']=='openconfig-system' and spec['keys']:
        spec['key_paths'] = {'name':'/openconfig-system:system/mount-points/mount-point/name'}
    else:
        spec['key_paths'] = {}


def catalog():
    import copy
    return copy.deepcopy({'contract_version': VERSION, 'modules': MODULES, 'jobs': JOBS, 'properties': PROPERTIES})
