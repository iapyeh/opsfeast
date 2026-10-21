"""Bundled vault content author: plain views over public retention records."""
import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import quote
from retention_store import component, now, query
from display_time import format_time, human_times
import html
from opsfeast import ConfigError, group_names


def text(value):
    return html.escape(str(value)).replace('\n', ' ').replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;').replace('\r', ' ').replace('`', '&#96;')


def label(name):
    words = str(name).replace('_', ' ').replace('-', ' ').replace('.', ' / ').split()
    acronyms = {'cpu': 'CPU', 'cpus': 'CPUs', 'dns': 'DNS', 'ip': 'IP', 'mtu': 'MTU',
                'uuid': 'UUID', 'id': 'ID', 'os': 'OS'}
    return ' '.join(acronyms.get(word.lower(), word.capitalize()) for word in words)


def value_text(value, field=''):
    """Human units retain their exact base value; missing values never become zero."""
    if value is None:
        return 'Not available'
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, dict):
        return '; '.join(f'{label(key)}: {value_text(item, key)}' for key, item in value.items()) or 'No fields reported'
    if isinstance(value, list):
        return ', '.join(value_text(item, field) for item in value) or 'No entries reported'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if field.endswith(('_bytes', '_kib')):
            base = value * 1024 if field.endswith('_kib') else value
            scaled = base
            unit = 'B'
            for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'):
                if abs(scaled) < 1024 or unit == 'PiB':
                    break
                scaled /= 1024
            exact = f'{value:,}' + (' KiB' if field.endswith('_kib') else ' bytes')
            return f'{scaled:,.3g} {unit} ({exact})'
        if field.endswith('_seconds'):
            seconds = int(value)
            days, remainder = divmod(seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, remainder = divmod(remainder, 60)
            return f'{days}d {hours}h {minutes}m {remainder}s ({value:,} seconds)'
        return str(value)
    return str(value) if value != '' else '(empty string)'


def markdown_table(headers, rows):
    return ['| ' + ' | '.join(text(h) for h in headers) + ' |',
            '| ' + ' | '.join('---' for _ in headers) + ' |',
            *['| ' + ' | '.join(text(v) for v in row) + ' |' for row in rows]]


def flat_values(value, prefix=''):
    """Flatten nested mappings while retaining keys for generic content authors."""
    if isinstance(value, dict) and value:
        return [row for key, item in value.items()
                for row in flat_values(item, f'{prefix}.{key}' if prefix else str(key))]
    return [(prefix, value)]


def dataset_lines(dataset, level=2, *, compact=False, limit=12):
    """Render all supplied nested fields without recipe execution or JSON dumping."""
    if compact:
        dataset = readable_value(dataset) or {}
    lines = []
    scalar = [(key, item) for key, item in dataset.items() if not isinstance(item, (dict, list))]
    if scalar:
        lines += markdown_table(['Field', 'Value'],
                                [(label(key), value_text(item, key)) for key, item in scalar]) + ['']
    for key, item in dataset.items():
        if not isinstance(item, (dict, list)):
            continue
        lines += ['#' * level + ' ' + text(label(key)), '']
        if compact and isinstance(item, list):
            if all(isinstance(row, dict) and isinstance(row.get('name'), str) for row in item):
                item = sorted(item, key=lambda row: (row['name'].casefold(), row['name']))
            item_limit = None if key in ('packages', 'services') else limit
            if item_limit is not None and len(item) > item_limit:
                lines += [str(len(item)) + ' entries; showing the first ' + str(item_limit) + '. See the source report for the full list.', '']
                item = item[:item_limit]
        if isinstance(item, dict):
            lines += dataset_lines(item, level + 1, compact=compact, limit=limit) if item else ['No fields reported.', '']
        elif not item:
            lines += ['No entries reported. This does not establish absence outside the collection scope.', '']
        elif all(isinstance(entry, dict) for entry in item):
            flattened = [dict(flat_values(entry)) for entry in item]
            columns = list(dict.fromkeys(key for row in flattened for key in row))
            if compact and 'name' in columns:
                columns = ['name'] + [key for key in columns if key != 'name']
            if columns:
                lines += markdown_table([label(key) for key in columns],
                                        [[('' if compact and row.get(key) is None else value_text(row.get(key), key)) for key in columns] for row in flattened]) + ['']
            else:
                lines += [f'{len(item)} entries with no reported fields.', '']
        else:
            for index, entry in enumerate(item, 1):
                if isinstance(entry, (dict, list)):
                    lines += [f'### Entry {index}', '']
                    lines += dataset_lines(entry if isinstance(entry, dict) else {'items': entry}, level + 1, compact=compact, limit=limit)
                else:
                    lines.append('- ' + text(value_text(entry, key)))
            lines.append('')
    return lines


def page_title(record):
    """The content author owns titles, independently of executable recipe paths."""
    definition = record.get('retention_definition', {})
    if definition.get('contract') == 'inventory-observations' or record['recipe_id'] == 'inventory-system':
        return 'System inventory'
    return label(record['recipe_id'])


def page_slug(record):
    title = unicodedata.normalize('NFKC', page_title(record))
    slug = re.sub(r'[^\w-]+', '-', title, flags=re.UNICODE).strip('-_').lower()
    slug = slug.encode('utf-8')[:120].decode('utf-8', errors='ignore')
    return slug if slug and slug not in ('readme', 'con', 'prn', 'aux', 'nul') else 'report'


def latest_filename(record):
    return 'current-' + page_slug(record) + '.md'


def current_identity(record):
    """Recipe moves keep one current page; independent sources remain distinct."""
    source, separator, _ = record['recipe_reference'].partition(':')
    return (record['origin']['namespace'], source if separator else '', record['recipe_id'])


def history_filename(record):
    observed = datetime.fromisoformat(record['observed_at']).astimezone(timezone.utc)
    if record.get('kind') == 'operation':
        # Intent and result share observation time; the operation journal keeps its own naming.
        digest = hashlib.sha256(record['record_id'].encode()).hexdigest()[:12]
        return observed.strftime('%Y-%m-%d_%H-%M-%S.%fZ') + '-' + page_slug(record) + '--' + digest + '.md'
    return observed.strftime('%Y%m%d%H%M%S') + '-' + page_slug(record) + '.md'


def host_location(runtime, host):
    """One host page under its first configured group; membership links may be many."""
    groups = group_names(runtime.hosts.get(host, {}).get('group', []), 'host group')
    group = component(groups[0]) if groups else '_ungrouped'
    # Keep the synthetic bucket distinct from a real group with the same name.
    if groups and group == '_ungrouped':
        group = '%5Fungrouped'
    return '/'.join(('hosts', group, component(host)))



def with_contents(lines, report_link=None, *, report_label='Latest report — collection details and identity/coverage warnings', lead_section=None, metadata_first=False):
    """Obsidian navigates heading text, rather than arbitrary HTML anchor IDs."""
    entries, rendered, used = [], [], {'contents'}
    disclosure = False
    for line in lines[2:]:
        if line == '<details>':
            disclosure = True
        elif line == '</details>':
            disclosure = False
        match = re.match(r'^(#{2,3}) (.+)$', line) if not disclosure else None
        if match:
            heading = match[2]
            base, number = heading, 1
            while html.unescape(heading).casefold() in used:
                number += 1
                heading = base + ' details' + (f' {number}' if number > 2 else '')
            used.add(html.unescape(heading).casefold())
            fragment = quote(html.unescape(heading), safe='')
            entries.append(('  ' if len(match[1]) == 3 else '') + '- [' + heading + '](#' + fragment + ')')
            line = match[1] + ' ' + heading
        rendered.append(line)
    leading = []
    if lead_section and '## ' + lead_section in rendered:
        start = rendered.index('## ' + lead_section)
        end = next((i for i in range(start + 1, len(rendered)) if rendered[i].startswith('## ')), len(rendered))
        leading = rendered[start:end]
        rendered = rendered[:start] + rendered[end:]
    metadata=[]
    if metadata_first:
        end=next((i for i,line in enumerate(rendered) if line.startswith('## ')),len(rendered))
        metadata,rendered=rendered[:end],rendered[end:]
    prefix = [*lines[:2], *metadata, *leading, '## Contents', '', *entries, '']
    if report_link is not None:
        prefix += ['[' + report_label + '](' +
                   quote(report_link, safe='/') + ')', '']
    return '\n'.join(prefix + rendered)


def inventory_section(section, values):
    if all(value is None for value in values.values()):
        return ['No data was collected for this section.', '']
    if section not in ('storage', 'network', 'software', 'services'):
        return dataset_lines(values, level=3)
    lines = []
    for field, value in values.items():
        if value is None:
            lines += ['### ' + label(field), '', 'No data was collected.', '']
        else:
            lines += dataset_lines({field: value}, level=3)
    return lines


def readable_value(value):
    """Omit unknown fields, preserving observed zero, false and empty collections."""
    if value is None or value == '':
        return None
    if isinstance(value, dict):
        cleaned = {key: result for key, item in value.items()
                   if (result := readable_value(item)) is not None}
        return cleaned if cleaned or not value else None
    if isinstance(value, list):
        cleaned = [result for item in value if (result := readable_value(item)) is not None]
        return cleaned if cleaned or not value else None
    return value


def dgmo_name(value, *, node=False):
    """Quote one literal label; neutralize fence, escape and line injection.

    Full source spelling remains in the accompanying Markdown table/report.
    """
    value = ' '.join(str(value).split())
    value = ''.join(char for char in value if not unicodedata.category(char).startswith('C'))
    value = value.replace('\\', '＼').replace('"', '″').replace('`', '′')
    # Mindmap 0.85 preserves quote characters in displayed labels. Common safe
    # identifiers need no quoting; unusual labels retain the protective quotes.
    if node and re.fullmatch(r'[\w./:@%-]+', value) and not value.startswith('//') and value not in {
            'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'teal', 'cyan', 'gray', 'black', 'white'}:
        return value
    return '"' + value + '"'


def capacity_diagram(rows):
    measured = []
    for row in rows:
        value = row.get('used_percent')
        if isinstance(value, str):
            try:
                value = float(value.rstrip('%'))
            except ValueError:
                continue
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
            continue
        if not row.get('mountpoint'):
            continue
        name = str(row['mountpoint'])
        if row.get('source'):
            name += ' (' + str(row['source']) + ')'
        measured.append((name, value))
    if not measured:
        return []
    lines = ['### Filesystem usage', '', '```dgmo', 'bar Filesystem usage (%)',
             'orientation-horizontal', 'y-label Used (%)']
    lines += [dgmo_name(name) + ' ' + format(value, '.6g') for name, value in measured]
    return lines + ['```', '', 'Only reported usage percentages are plotted; omitted filesystems are not zero.', '']


def interface_diagram(host, rows):
    interfaces = {}
    for row in rows:
        name = row.get('name')
        if not name:
            continue
        addresses = interfaces.setdefault(str(name), [])
        if row.get('address'):
            address = str(row['address'])
            if row.get('prefix_length') is not None:
                address += '/' + str(row['prefix_length'])
            if address not in addresses:
                addresses.append(address)
    if not interfaces:
        return []
    lines = ['### Interface overview', '',
             'Local interface/address configuration; this is not a network topology or connectivity test.', '',
             '```dgmo', 'mindmap Local interfaces', '  Host ' + dgmo_name(host, node=True)]
    for name, addresses in interfaces.items():
        lines.append('    Interface ' + dgmo_name(name, node=True))
        lines += ['      IP ' + dgmo_name(address, node=True) for address in addresses]
    return lines + ['```', '']


def current_warnings(record):
    data = record['data']
    lines = []
    warnings = list(dict.fromkeys([warning for warning in
                    [data.get('identity_warning'), *[g.get('identity_warning') for g in data.get('groups', [])]] if warning]))
    for warning in warnings:
        lines += ['> Identity warning: ' + text(warning), '']
    evidence = record.get('collection_evidence') or {}
    incomplete = data.get('status') != 'success' or any(p['status'] != 'success' for p in evidence.get('probes', []))
    incomplete |= any(g.get('status') != 'success' or any(not c['complete'] for c in g.get('coverage', []))
                      for g in data.get('groups', []))
    if incomplete:
        lines += ['> Some data was not obtained. Missing values are omitted; see the linked reports for coverage and reasons.', '']
    if 'groups' in data:
        lines += ['Sections can have different observation times. Missing values are omitted, without filling from earlier collections; see each section and its source report.', '']
    return lines


def current_inventory(record):
    data = record['data']
    inventory = {key: dict(value) for key, value in data['inventory'].items()}
    if 'system' in inventory:
        inventory['system'].update({field: item.get('value') for field, item in data.get('observations', {}).items()
                                    if field in inventory['system']})
    summary = []
    for section, fields in (('system', ('hostname', 'system_name', 'system_version', 'architecture', 'uptime_seconds')),
                            ('hardware', ('cpu_model', 'logical_cpus', 'memory_total_bytes'))):
        for field in fields:
            value = inventory.get(section, {}).get(field)
            if value is not None and value != '':
                summary.append((label(field), value_text(value, field)))
                inventory[section].pop(field)
    lines = ['## Host summary', ''] + markdown_table(['Field', 'Value'], summary) + [''] if summary else []
    for section, values in inventory.items():
        values = readable_value(values)
        if not values:
            continue
        lines += ['## ' + text(label(section)), '']
        if section == 'storage':
            lines += capacity_diagram(values.get('filesystems') or [])
        elif section == 'network':
            lines += interface_diagram(record['host_id'], values.get('interfaces') or [])
        lines += dataset_lines(values, level=3, compact=True)
    return lines


def job_diagrams(record, samples):
    """Build only within one source group: never join mixed-age property groups."""
    filesystems, interfaces = {}, {}
    for sample in samples:
        name, keys, value = sample['property'], sample['keys'], sample['value']
        if name == 'storage.filesystems.used_percent':
            token = json.dumps(keys, sort_keys=True)
            filesystems[token] = {**keys, 'used_percent': value}
        elif name in ('network.interfaces.name', 'network.interfaces.address', 'network.interfaces.prefix_length',
                      'network.ipv4.address', 'network.ipv4.prefix_length',
                      'network.ipv6.address', 'network.ipv6.prefix_length'):
            token = json.dumps([keys, sample['observed_at']], sort_keys=True)
            interfaces.setdefault(token, dict(keys))[name.rsplit('.', 1)[1]] = value
    return capacity_diagram(filesystems.values()) + interface_diagram(record['host_id'], interfaces.values())


def current_value(value, field='', unit=''):
    rendered = value_text(value, field)
    if type(value) in (int, float) and unit:
        if field.endswith(('_bytes', '_kib', '_seconds')):
            return rendered
        return rendered + ('%' if unit == 'percent' else ' ' + unit)
    return rendered


def readable_job_samples(samples):
    """Prefer exact filesystem bytes over their same-probe floored MB projection.

    Do not suppress projections based on another sample time, probe or mount.
    """
    exact = set()
    for sample in samples:
        name = sample['property']
        if name.startswith('storage.filesystems.') and name.endswith('_bytes'):
            mount = sample['keys'].get('mountpoint')
            if mount is not None and sample['status'] == 'success' and type(sample['value']) in (int, float):
                exact.add((name, mount, sample['source_id'], sample['observed_at'], sample['value'] // 1000000))
    result = []
    for sample in samples:
        name = sample['property']
        if name.startswith('storage.filesystems.') and name.endswith('_megabytes'):
            mount = sample['keys'].get('name')
            equivalent = (name.replace('_megabytes', '_bytes'), mount, sample['source_id'], sample['observed_at'], sample['value'])
            if equivalent in exact:
                continue
        result.append(sample)
    return result


def source_report_link(record, history_names=None):
    filename = (history_names or {}).get(record['record_id'], history_filename(record))
    return '../' + record['observed_at'][:4] + '/reports/' + filename


def job_value_tables(samples, definitions, *, group_id=None):
    """Pivot entity columns only within one group and identical sample times."""
    scalars, collections, arrays = [], {}, []
    for sample in readable_job_samples(samples):
        name, value = sample['property'], readable_value(sample['value'])
        spec = definitions.get(name, {})
        column = spec.get('column')
        if column:
            collection = name.rsplit('.', 1)[0]
            if collection == 'storage.filesystems' and name.endswith('_megabytes'):
                collection += ' (megabyte projection)'
            token = json.dumps([sample['keys'], sample['observed_at']], sort_keys=True)
            row = collections.setdefault(collection, {}).setdefault(token, dict(sample['keys']))
            # column describes the producer input, not necessarily the retained unit.
            row[name.rsplit('.', 1)[1]] = value
        elif isinstance(value, (list, dict)):
            arrays += ['#### ' + text(label(name)), '']
            arrays += dataset_lines({'entries': value}, level=5, compact=True,
                                    limit=None if name in ('software.packages', 'services.services') else 12)
        else:
            scalars.append((label(name), current_value(value, name, spec.get('unit', ''))))
    lines = markdown_table(['Property', 'Value'], scalars) + [''] if scalars else []
    for name, rows in collections.items():
        title = label(name)
        if name.startswith('storage.filesystems') and group_id in ('storage-layout', 'storage-capacity'):
            title = 'Filesystem mounts' if group_id == 'storage-layout' else 'Filesystem capacity'
            if name.endswith('(megabyte projection)'):
                title += ' (megabyte projection)'
        lines += ['#### ' + text(title), '']
        lines += dataset_lines({'entries': list(rows.values())}, level=5, compact=True)
    return lines + arrays


def is_io_counter(name):
    return name.startswith('metrics.interfaces.') or name in ('metrics.disk_counters', 'metrics.interface_counters')


def sample_topic(name):
    if name.startswith('metrics.') or name in ('hardware.cpu_model', 'hardware.logical_cpus', 'hardware.memory_total_bytes'):
        return 'CPU and memory'
    return {'system': 'System', 'hardware': 'Hardware', 'sensors': 'Hardware', 'network': 'Network',
            'storage': 'Storage', 'software': 'Software', 'services': 'Services'}.get(name.split('.')[0], 'Other observations')


def host_heading(host, icon=None):
    return '# ' + (text(icon) + ' ' if icon else '') + text(host)


def attention_lines(record, policy=None):
    from inventory_attention import evaluate
    return render_attention(evaluate(record, policy))


def render_attention(evaluation):
    if not evaluation['findings']:
        return []
    lines = ['## Attention', '', 'Threshold hints from retained observations, not live monitoring or a complete health assessment.', '']
    for finding in evaluation['findings']:
        times = 'Observed: ' + format_time(finding['observed_at'])
        if finding.get('baseline_at') and finding['baseline_at'] != finding['observed_at']:
            times += '; baseline: ' + format_time(finding['baseline_at'])
        lines += ['- **' + finding['severity'].capitalize() + ':** ' + text(finding['message']) + ' (' + text(times) + ')']
    return lines + ['']


def current_jobs(record, history_names=None):
    data = record['data']
    summary = []
    primary = {'system.hostname', 'system.system_name', 'system.system_version', 'system.architecture',
               'hardware.cpu_model', 'hardware.logical_cpus', 'hardware.memory_total_bytes'}
    for group in data['groups']:
        for sample in group['samples']:
            if sample['property'] in primary and sample['status'] == 'success' and readable_value(sample['value']) is not None:
                summary.append((label(sample['property'].split('.')[-1]), value_text(sample['value'], sample['property'])))
    lines = (['## Host summary', ''] + markdown_table(['Field', 'Value'], summary) + ['']) if summary else []
    topics = {name: [] for name in ('System', 'Hardware', 'CPU and memory', 'Network', 'Storage', 'Software', 'Services', 'Other observations')}
    for original in data['groups']:
        by_topic = {}
        for sample in original['samples']:
            if is_io_counter(sample['property']):
                continue
            by_topic.setdefault(sample_topic(sample['property']), []).append(sample)
        if not original['samples'] and original.get('coverage') and all(c['complete'] for c in original['coverage']):
            for coverage in original['coverage']:
                name = coverage.get('property', '')
                if not is_io_counter(name):
                    fallback = {'network-state': 'Network', 'storage-layout': 'Storage', 'software-inventory': 'Software'}.get(original['id'], 'Other observations')
                    by_topic.setdefault(sample_topic(name) if name else fallback, [])
        for topic, selected in by_topic.items():
            topics[topic].append(dict(original, samples=selected))
    for topic, groups in topics.items():
        section = []
        for group in sorted(groups, key=lambda g: (g['id'], g['observed_at'], g.get('source_record_id', ''))):
            samples = [s for s in group['samples'] if s['status'] == 'success' and readable_value(s['value']) is not None]
            complete_empty = not group['samples'] and group.get('coverage') and all(c['complete'] for c in group['coverage'])
            if not samples and not complete_empty:
                continue
            title = {
                ('System', 'hardware-baseline'): 'Platform',
                ('System', 'system-configuration'): 'Operating system',
                ('System', 'system-runtime'): 'Uptime and boot',
                ('Hardware', 'hardware-baseline'): 'Device identity',
                ('Hardware', 'hardware-sensors'): 'Sensors',
                ('CPU and memory', 'hardware-baseline'): 'Capacity',
                ('CPU and memory', 'resource-metrics'): 'Utilization',
                ('Network', 'network-configuration'): 'Interfaces and addressing',
                ('Network', 'network-state'): 'Routes and link state',
                ('Network', 'service-state'): 'Listening endpoints',
                ('Storage', 'storage-layout'): 'Mounts and devices',
                ('Storage', 'storage-capacity'): 'Capacity and usage',
                ('Software', 'software-inventory'): 'Packages',
                ('Services', 'service-state'): 'Service state',
            }.get((topic, group['id']), group['title'])
            section += ['### ' + text(title), '', 'Observed: ' + text(format_time(group['observed_at'])), '']
            if group.get('source_record_id') and group.get('source_record_observed_at'):
                source = dict(record, record_id=group['source_record_id'], observed_at=group['source_record_observed_at'])
                link = source_report_link(source, history_names)
                if link != source_report_link(record, history_names):
                    section += ['[Source report](' + quote(link, safe='/') + ')', '']
            if any(s['status'] != 'success' for s in group['samples']):
                section += ['> Some properties were not obtained in this collection; see the source report.', '']
            if complete_empty:
                section += ['Complete enumeration returned no matching instances.', '']
                continue
            definitions = group.get('property_definitions', data.get('property_definitions', {}))
            section += [line.replace('### ', '#### ', 1) if line.startswith('### ') else line
                        for line in job_diagrams(record, samples)]
            section += job_value_tables(samples, definitions, group_id=group['id'])
        if section:
            lines += ['## ' + topic, ''] + section
    if data.get('note'):
        lines += ['Manual note: ' + text(data['note']), '']
    return lines


def command_outputs(record):
    """Read recorded streams only; include the source of each mixed-age probe."""
    data=record['data']
    groups=data.get('groups',[])
    sources=[]
    seen=set()
    if groups and any('source_probes' in g for g in groups):
        for group in groups:
            for probe in group.get('source_probes',[]):
                key=(group['source_record_id'],probe['id'])
                if key not in seen:
                    seen.add(key)
                    sources.append((group['source_record_id'],probe))
    else:
        sources=[(record['record_id'],p) for p in data.get('probes',[]) if p.get('command')]
    if not sources:
        return []
    lines=['## Command output','','Original captured streams; each command is collapsed by default.','']
    for source,probe in sources:
        command=probe.get('command')
        if not command:
            continue
        lines += ['<details>', '<summary>'+html.escape(str(command))+'</summary>', '',
                  'Observed: '+text(format_time(probe['observed_at']))+'; State: '+text(probe['status'])+
                  '; Exit code: '+text(probe.get('exitcode') if probe.get('exitcode') is not None else 'Not recorded'),
                  '', 'Source observation: '+text(source),'',
                  '<pre><code>'+html.escape(str(command))+'</code></pre>','']
        for stream in ('stdout','stderr'):
            output=probe.get(stream)
            lines += [stream+(': truncated at the capture limit' if probe.get(stream+'_truncated') else ''),'']
            if output is None:
                lines += ['Not recorded.','']
            elif output=='':
                lines += ['<pre><code>(empty)</code></pre>','']
            else:
                lines += ['<pre><code>'+html.escape(output)+'</code></pre>','']
        lines += ['</details>','']
    return lines


def render_current(record, history_names=None, host_icon=None, attention_policy=None):
    """Readable current views; historical rendering remains complete and independent."""
    data = record['data']
    lines = [host_heading(record['host_id'], host_icon), '', *attention_lines(record, attention_policy),
             'Observed: ' + text(format_time(record['observed_at'])), '']
    lines += current_warnings(record)
    if 'groups' in data:
        lines += current_jobs(record, history_names)
    elif data.get('inventory'):
        lines += current_inventory(record)
    else:
        rows = [(label(field), current_value(readable_value(item['value']), field, item.get('unit', '')), item.get('status', 'unknown')) for field, item in data.get('observations', {}).items()
                if readable_value(item.get('value')) is not None]
        if rows:
            lines += ['## Observations', ''] + markdown_table(['Field', 'Value', 'State'], rows) + ['']
    if not any(line.startswith('## ') and line != '## Attention' for line in lines):
        lines += ['No collected values are available in this view. See the full report.', '']
    lines += command_outputs(record)
    report_link = source_report_link(record, history_names)
    return with_contents(lines, report_link, report_label='Source report — collection details and identity/coverage warnings', lead_section='Attention')


def render_observation(record, *, current=False, history_names=None, host_icon=None, attention_policy=None):
    if current:
        return render_current(record, history_names, host_icon, attention_policy)
    data = record['data']
    origin = record.get('origin') or {}
    lines = ['# ' + text(record['host_id']), '']
    observations = data.get('observations', {})
    inventory = data.get('inventory')
    if 'groups' in data:
        lines += ['## Inventory jobs', '', 'Each group retains its own source times. Missing samples are gaps, not carried-forward measurements.', '']
        for group in data['groups']:
            lines += ['### '+text(group['title']), '', 'State: '+text(group['status'])+'; collected: '+text(group['observed_at']), '']
            if group.get('source_record_id'):
                lines += ['Source observation: '+text(group['source_record_id'])+'; actor: '+text(group['source_actor'].get('username') or 'unknown'), '']
            definitions = group.get('property_definitions',data.get('property_definitions',{}))
            lines += markdown_table(['Property','Entity','Value','Unit','State','Sample time','Source'],
                [(s['property'], value_text(s['keys']), value_text(s['value'],s['property'].split('.')[-1]),
                  definitions.get(s['property'],{}).get('unit',''),s['status'],s['observed_at'],s['source_id']) for s in group['samples']]) + ['']
            if not group['samples']:
                lines += [('Complete enumeration returned no matching instances.' if group['coverage'] and all(c['complete'] for c in group['coverage']) else
                           'No samples; inspect coverage and collection evidence.'), '']
        if data.get('note'):
            lines += ['Manual note: '+text(data['note']), '']
    elif inventory:
        for section in ('system', 'hardware', 'storage', 'network', 'software', 'services'):
            if section in inventory:
                lines += ['## ' + label(section), '']
                values = dict(inventory[section])
                if section == 'system':
                    # The seven declared observation values are authoritative within this record.
                    values.update({field: item.get('value') for field, item in observations.items() if field in values})
                lines += inventory_section(section, values)
        extra = {key: value for key, value in inventory.items()
                 if key not in ('system', 'hardware', 'storage', 'network', 'software', 'services')}
        if extra:
            lines += ['## Additional inventory', ''] + dataset_lines(extra, level=3)
    else:
        lines += ['## Observations', '']
        if not any(item.get('value') is not None for item in observations.values()):
            lines += ['No data was collected for this section.', '']
        else:
            lines += markdown_table(['Field', 'Value', 'State', 'Unit', 'Meaning'],
                                    [(label(field), value_text(item.get('value')), item.get('status', 'unknown'),
                                      item.get('unit', ''), item.get('description', 'See dataset contract'))
                                     for field, item in observations.items()]) + ['']
    evidence = record.get('collection_evidence')
    actor = evidence['actor'] if evidence else data.get('actor') or {
        'username': None, **data.get('collection_scope', {'mode': 'unverified', 'effective_uid': None})}
    lines += ['## Collection metadata', '']
    overview = [('Host', record['host_id']), ('Report', page_title(record)),
                ('Recipe', record.get('recipe_reference', record['recipe_id'])),
                ('Observed', format_time(record['observed_at'])),
                ('Source', origin.get('namespace', 'unknown') + ' / ' + origin.get('host_id', 'unknown')),
                ('Account', actor.get('username') or 'Not recorded'),
                ('Effective UID', value_text(actor.get('effective_uid'))), ('Mode', actor.get('mode', 'unverified'))]
    if data.get('status') != 'success':
        overview.append(('Observation status', data.get('status', 'unknown')))
    lines += markdown_table(['Field', 'Value'], overview) + ['']
    warning = data.get('identity_warning')
    if warning:
        lines += ['> Identity warning: ' + text(warning), '']
    if data.get('status') == 'partial':
        lines += ['> Partial observation: missing values remain unavailable; older observations are not used to fill them.', '']
    lines += [text(data.get('description', 'Inventory observations within the reported collection scope.')), '',
              'Account means the verified collection actor, not the configured login or the controller user.', '']
    if evidence:
        probes = evidence['probes']
        incomplete = [probe for probe in probes if probe['status'] != 'success']
        lines += ['### Collection queries', '',
                  f'{len(probes) - len(incomplete)}/{len(probes)} recorded field/query results succeeded. '
                  'The observation state describes the base fields; extended query coverage is separate.', '']
        if incomplete:
            lines += ['> Some queries did not produce complete data. Not available does not mean the resource is absent.', '']
        lines += markdown_table(['Section / field', 'Command', 'State', 'Reason', 'Exit code', 'Observed'], [
            [label(probe['section']) + ' / ' + label(probe['field']), probe['command'] or 'Not attempted',
             probe['status'], probe['reason_code'] or probe['error_type'] or '',
             value_text(probe['exitcode']), value_text(format_time(probe['observed_at']))] for probe in probes]) + ['']
        lines += ['Commands are recorded sources, not instructions to execute. Identity-adapter queries may supplement hardware fields; their raw execution evidence remains separate.', '']
    else:
        if 'groups' in data:
            lines += ['### Collection queries', '']
            lines += markdown_table(['Source','Command','State','Reason','Sample time'],
                [(p['id'],p.get('command') or 'Acquisition',p['status'],p.get('reason_code') or '',p['observed_at']) for p in data.get('probes',[])])+['']
        else:
            lines += ['Collection commands and per-query reasons were not retained for this observation. '
                  'Inspect its original raw result for historical execution evidence; rebuilding a page does not collect missing data.', '']
    if data.get('collection_scope'):
        lines += ['### Collection scope', '']
        lines += dataset_lines(data['collection_scope'], level=3)
    # Keep complete provenance discoverable without putting opaque identifiers first.
    lines += ['### Source identifiers', '', '<details>', '<summary>Identifiers and source evidence</summary>', '']
    metadata = {key: value for key, value in record.items() if key not in ('data', 'collection_evidence')}
    metadata['dataset_evidence'] = {
        key: value for key, value in data.items()
        if key not in ('inventory', 'observations', 'description', 'status', 'collection_scope', 'identity_warning','groups','probes','actor','property_definitions')
    }
    lines += dataset_lines(human_times(metadata), level=3)

    lines += ['', '</details>']
    return with_contents(lines)



def run_pages(root, runtime, history_names, records):
    """Show the recorded command outcome without reinterpreting collection evidence."""
    from observation_runs import list_runs, selection_text
    runs=list_runs(root)
    if not runs:
        return {}
    by_id={record['record_id']:record for record in records}
    entries,occupied={},set()
    summary=['# Observations','','| Started | Status | Targets |','| --- | --- | --- |']
    for run in runs:
        base=run['started_at'][:19].replace('-','').replace(':','').replace('T','')
        name,ordinal=base+'.md',1
        while name in occupied:
            ordinal+=1
            name=base+'-'+str(ordinal)+'.md'
        occupied.add(name)
        execution=run.get('execution')
        status=execution['status'] if execution else 'running' if run['status']=='running' else 'Not recorded'
        selection=selection_text(run.get('selection'))
        completed=execution['completed_at'] if execution else run['completed_at']
        duration='In progress'
        if completed:
            seconds=max(0,int((datetime.fromisoformat(completed)-datetime.fromisoformat(run['started_at'])).total_seconds()))
            duration=str(seconds)+(' second' if seconds==1 else ' seconds')
        lines=['# Observation — '+format_time(run['started_at']),'',
               'Status: '+text(status),'','Trigger: '+text(run['trigger']),'',
               'Targets: '+text(selection),'','Recipe: '+text(run['recipe_reference']),'',
               'Started: '+format_time(run['started_at']),'',
               'Completed: '+format_time(completed) if completed else 'Execution has not completed.','',
               'Duration: '+duration,'']
        warnings=[]
        for target in run['targets']:
            if target['retention_status']=='failed':
                warnings.append('Data storage failed for '+target['host_id']+'.')
            if target['record_id'] and target['record_id'] not in by_id:
                warnings.append(target['host_id']+': Retained record no longer available.')
        if execution and execution['content_status']=='failed':
            warnings.append('Content publication failed during this execution; this page may have been rebuilt later.')
        lines += ['> '+text(warning) for warning in warnings]+[''] if warnings else []
        lines += ['## Hosts','','| Host | Status | Collection jobs |','| --- | --- | --- |']
        flags=[]
        for target in run['targets']:
            host=target['host_id']
            host_cell=text(((target.get('icon') or '')+' '+host).strip())
            record=by_id.get(target['record_id'])
            if record:
                section='reports' if record['kind']=='observation' else 'operations'
                path='../'+host_location(runtime,host)+'/'+record['observed_at'][:4]+'/'+section+'/'+history_names[record['record_id']]
                host_cell='['+host_cell+']('+quote(path,safe='/')+')'
            jobs=', '.join(str(j.get('title') or j['id'])+(' ('+j['status']+')' if j.get('status') else '') for j in target['jobs'])
            state=target['status']+(' / '+target['reason_code'] if target.get('reason_code') else '')
            lines.append('| '+host_cell+' | '+text(state)+' | '+text(jobs)+' |')
            evaluation=target.get('attention')
            if evaluation and evaluation['findings']:
                flags += ['### '+text(((target.get('icon') or '')+' '+host).strip()),'']+render_attention(evaluation)[2:]+['']
        if flags:
            lines += ['','## Attention','','Findings and thresholds were saved for this execution.','']+flags
        entries['Observations/'+name]=with_contents(lines,metadata_first=True)
        summary.append('| ['+format_time(run['started_at'])+']('+name+') | '+text(status)+' | '+text(selection)+' |')
    entries['Observations/SUMMARY.md']='\n'.join(summary)
    return entries


def build(root, runtime):
    from retention_store import settings
    config = settings(root)
    if config is None:
        raise ConfigError('vault namespace missing')
    all_records = query(root)['records']
    entries = {}
    # Timestamp/title names stay readable; repeated seconds get an ordinal rather
    # than an identifier. Use one mapping for publication and every source link.
    history_names, occupied = {}, set()
    for record in sorted(all_records, key=lambda r: (r['observed_at'], r['record_id'])):
        base = history_filename(record)
        folder = host_location(runtime, record['host_id']) + '/' + record['observed_at'][:4]
        name, ordinal = base, 1
        while folder + '/' + name in occupied:
            ordinal += 1
            name = base[:-3] + '-' + str(ordinal) + '.md'
        occupied.add(folder + '/' + name)
        history_names[record['record_id']] = name
    host_map = {}
    for record in all_records:
        host_map.setdefault(record['host_id'], []).append(record)
        # Yearly human views are reproducible; the SQLite journal is authoritative.
        if record['kind'] == 'operation':
            body = '# Operation\n\n```json\n' + json.dumps(human_times(record), ensure_ascii=False, indent=2).replace('`', '\\u0060') + '\n```'
            section = 'operations'
        else:
            body = render_observation(record)
            section = 'reports'
        path = '/'.join((host_location(runtime, record['host_id']), record['observed_at'][:4], section, history_names[record['record_id']]))
        if path in entries:
            raise ConfigError('vault history filename collision')
        entries[path] = body
    for host in runtime.hosts:
        host_map.setdefault(host, [])
    index = ['# Hosts', '', 'Namespace: ' + config['namespace'], '', 'Generated: ' + format_time(now()), '',
             '| Host | Enabled | Groups | System | Last observation | Status |',
             '| --- | --- | --- | --- | --- | --- |']
    for host, items in sorted(host_map.items()):
        folder = host_location(runtime, host)
        latest = {}
        for record in items:
            if record['kind'] == 'observation':
                key = current_identity(record)
                previous = latest.get(key)
                if previous is None or (record['observed_at'], record['record_id']) > (previous['observed_at'], previous['record_id']):
                    latest[key] = record
        summary = [host_heading(host, runtime.hosts.get(host, {}).get('icon')), '', 'Namespace: ' + config['namespace'], '', 'Generated: ' + format_time(now()),
                   '', 'Latest observation: ' + format_time(max((r['observed_at'] for r in latest.values()), default='No observations')), '', '## Current records', '']
        for _, record in sorted(latest.items()):
            recipe = record['recipe_reference']
            name = latest_filename(record)
            current_record = record
            if (record.get('retention_definition') or {}).get('contract') == 'inventory-job-observations':
                import copy
                from inventory_jobs import latest_groups
                current_record = copy.deepcopy(record)
                same_source = [r for r in items if r['kind']=='observation' and current_identity(r)==current_identity(record)]
                current_record['data']['groups'] = latest_groups(same_source)
                source_records = {r['record_id']: r for r in same_source}
                for group in current_record['data']['groups']:
                    source_record = source_records[group['source_record_id']]
                    group['identity_warning'] = source_record['data'].get('identity_warning')
                    group['source_record_observed_at'] = source_record['observed_at']
            options = runtime.recipe_options(host, record['recipe_reference']) if hasattr(runtime, 'recipe_options') else {}
            policy = options.get('vars', {}).get('attention', {})
            rendered = render_observation(current_record, current=True, history_names=history_names, host_icon=runtime.hosts.get(host, {}).get('icon'), attention_policy=policy)
            path = folder + '/records/' + name
            if path in entries:
                raise ConfigError('vault latest-state filename collision')
            entries[path] = rendered
            summary.append('- [' + text(page_title(record)) + '](' + quote(name) + ') — ' + format_time(record['observed_at']) + ' / ' + text(record['data'].get('status')) + ' / ' + text(recipe))
        operations = [r for r in items if r['kind'] == 'operation']
        if operations:
            summary += ['', '## Operations', '']
        outcomes = {r['data']['intent_id']: r for r in operations if r['data']['phase'] == 'result'}
        for operation in operations:
            if operation['data']['phase'] != 'intent':
                continue
            outcome = outcomes.get(operation['record_id'])
            summary.append('- ' + format_time(operation['observed_at']) + ' ' + text(operation['recipe_id']) + ': ' +
                           text(outcome['data']['status'] if outcome else 'unknown: outcome not recorded') +
                           ' / verification: ' + text(outcome['data']['verification'] if outcome else 'not_observed'))
        entries[folder + '/records/SUMMARY.md'] = with_contents(summary)
        entries[folder + '/SUMMARY.md'] = '\n'.join([
            host_heading(host,runtime.hosts.get(host,{}).get('icon')), '',
            'Namespace: '+config['namespace'], '',
            'Latest observation: '+format_time(max((r['observed_at'] for r in latest.values()),default='No observations')), '',
            '[Current records](records/SUMMARY.md)', '', '[Notes](README.md)'])
        configured = runtime.hosts.get(host, {})
        inventory = next((r for r in reversed(items) if r['kind'] == 'observation' and r['recipe_id'] == 'inventory-system'), None)
        system = inventory['data'].get('observations',{}).get('system_name', {}).get('value') if inventory else None
        last = max(latest.values(), key=lambda r: (r['observed_at'], r['record_id'])) if latest else None
        index.append('| [' + text(configured.get('label') or host) + '](' + quote(folder + '/SUMMARY.md', safe='/') + ') | ' +
                     ' | '.join(text(v) for v in (configured.get('enabled', True) if host in runtime.hosts else 'not configured',
                     ','.join(group_names(configured.get('group', []), 'host group')), system or 'unknown', format_time(last['observed_at']) if last else 'never',
                     last['data'].get('status', 'unknown') if last else 'no observations')) + ' |')
    pages = run_pages(root, runtime, history_names, all_records)
    entries.update(pages)
    if pages:
        index[2:2] = ['[Observations](Observations/SUMMARY.md)', '']
    return entries, index, sorted(host_map)
