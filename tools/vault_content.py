"""Bundled vault content author: plain views over public retention records."""
import hashlib
import json
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


def dataset_lines(dataset, level=2):
    """Render all supplied nested fields without recipe execution or JSON dumping."""
    lines = []
    scalar = [(key, item) for key, item in dataset.items() if not isinstance(item, (dict, list))]
    if scalar:
        lines += markdown_table(['Field', 'Value'],
                                [(label(key), value_text(item, key)) for key, item in scalar]) + ['']
    for key, item in dataset.items():
        if not isinstance(item, (dict, list)):
            continue
        lines += ['#' * level + ' ' + text(label(key)), '']
        if isinstance(item, dict):
            lines += dataset_lines(item, level + 1) if item else ['No fields reported.', '']
        elif not item:
            lines += ['No entries reported. This does not establish absence outside the collection scope.', '']
        elif all(isinstance(entry, dict) for entry in item):
            flattened = [dict(flat_values(entry)) for entry in item]
            columns = list(dict.fromkeys(key for row in flattened for key in row))
            if columns:
                lines += markdown_table([label(key) for key in columns],
                                        [[value_text(row.get(key), key) for key in columns] for row in flattened]) + ['']
            else:
                lines += [f'{len(item)} entries with no reported fields.', '']
        else:
            for index, entry in enumerate(item, 1):
                if isinstance(entry, (dict, list)):
                    lines += [f'### Entry {index}', '']
                    lines += dataset_lines(entry if isinstance(entry, dict) else {'items': entry}, level + 1)
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
    if (record.get('retention_definition') or {}).get('contract') == 'inventory-job-observations':
        digest = hashlib.sha256(record['record_id'].encode()).hexdigest()[:12]
        return observed.strftime('%Y%m%d%H%M%S') + '-' + page_slug(record) + '--' + digest + '.md'
    return observed.strftime('%Y%m%d%H%M%S') + '-' + page_slug(record) + '.md'


def host_location(runtime, host):
    """One host page under its first configured group; membership links may be many."""
    groups = group_names(runtime.hosts.get(host, {}).get('group', []), 'host group')
    group = component(groups[0]) if groups else '_ungrouped'
    # Keep the synthetic bucket distinct from a real group with the same name.
    if groups and group == '_ungrouped':
        group = '%5Fungrouped'
    return '/'.join(('hosts', group, component(host)))



def with_contents(lines, report_link=None):
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
    prefix = [*lines[:2], '## Contents', '', *entries, '']
    if report_link is not None:
        prefix += ['[Latest report — collection details and identity/coverage warnings](' +
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


def render_observation(record, *, current=False):
    data = record['data']
    origin = record.get('origin') or {}
    lines = ['# ' + text(record['host_id']), '']
    observations = data.get('observations', {})
    inventory = data.get('inventory')
    if 'groups' in data:
        lines += ['## Inventory jobs', '', 'Each group retains its own source times. Missing samples are gaps, not carried-forward measurements.', '']
        if current and data.get('identity_warning'):
            lines += ['> Identity warning: '+text(data['identity_warning']), '']
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
    if current:
        report_link = '../' + record['observed_at'][:4] + '/reports/' + history_filename(record)
        return with_contents(lines, report_link)
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



def build(root, runtime):
    from retention_store import settings
    config = settings(root)
    if config is None:
        raise ConfigError('vault namespace missing')
    all_records = query(root)['records']
    entries = {}
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
        path = '/'.join((host_location(runtime, record['host_id']), record['observed_at'][:4], section, history_filename(record)))
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
        summary = ['# ' + text(host), '', 'Namespace: ' + config['namespace'], '', 'Generated: ' + format_time(now()),
                   '', 'Latest observation: ' + format_time(max((r['observed_at'] for r in latest.values()), default='No observations')), '', '## Current reports', '']
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
            rendered = render_observation(current_record, current=True)
            path = folder + '/records/' + name
            if path in entries:
                raise ConfigError('vault latest-state filename collision')
            entries[path] = rendered
            summary.append('- [' + text(page_title(record)) + '](' + quote(name) + ') — ' + format_time(record['observed_at']) + ' / ' + text(record['data'].get('status')) + ' / ' + text(recipe))
        operations = [r for r in items if r['kind'] == 'operation']
        summary += ['', '## Operations', '']
        outcomes = {r['data']['intent_id']: r for r in operations if r['data']['phase'] == 'result'}
        for operation in operations:
            if operation['data']['phase'] != 'intent':
                continue
            outcome = outcomes.get(operation['record_id'])
            summary.append('- ' + format_time(operation['observed_at']) + ' ' + text(operation['recipe_id']) + ': ' +
                           text(outcome['data']['status'] if outcome else 'unknown: outcome not recorded') +
                           ' / verification: ' + text(outcome['data']['verification'] if outcome else 'not_observed'))
        entries[folder + '/records/README.md'] = with_contents(summary)
        configured = runtime.hosts.get(host, {})
        inventory = next((r for r in reversed(items) if r['kind'] == 'observation' and r['recipe_id'] == 'inventory-system'), None)
        system = inventory['data'].get('observations',{}).get('system_name', {}).get('value') if inventory else None
        last = max(latest.values(), key=lambda r: (r['observed_at'], r['record_id'])) if latest else None
        index.append('| [' + text(configured.get('label') or host) + '](' + quote(folder + '/README.md', safe='/') + ') | ' +
                     ' | '.join(text(v) for v in (configured.get('enabled', True) if host in runtime.hosts else 'not configured',
                     ','.join(group_names(configured.get('group', []), 'host group')), system or 'unknown', format_time(last['observed_at']) if last else 'never',
                     last['data'].get('status', 'unknown') if last else 'no observations')) + ' |')
    return entries, index, sorted(host_map)
