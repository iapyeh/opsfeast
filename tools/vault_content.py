"""Bundled vault content author: plain views over public retention records."""
import hashlib
import json
from urllib.parse import quote
from retention_store import component, now, query
from display_time import format_time, human_times
import html
from opsfeast import ConfigError, group_names


def text(value):
    return html.escape(str(value)).replace('\n', ' ').replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;')


def render_observation(record):
    data = record['data']
    lines = ['# ' + text(record['host_id']) + ': ' + text(record['recipe_id']),
             '', 'Observed: ' + format_time(record['observed_at']), '', 'Status: ' + text(data.get('status', 'unknown')),
             '', 'Record: ' + text(record['record_id']), '', 'Origin: ' + text(record['origin']),
             '', 'Environment identity evidence: ' + text(data.get('identity_warning', 'not applicable')),
             '', 'Dataset: ' + text(data.get('description', 'Inventory observations; preserve identity and coverage warnings.')),
             '', '| Field | Value | Status | Observed | Unit | Meaning |', '| --- | --- | --- | --- | --- | --- |']
    for field, item in data.get('observations', {}).items():
        lines.append('| ' + ' | '.join(text(v) for v in (field, item['value'], item['status'], format_time(item['observed_at']), item.get('unit', ''), item.get('description', 'See inventory contract'))) + ' |')
    # JSON code blocks preserve all six inventory sections without executing markup.
    body = json.dumps(human_times(data.get('inventory', {})), ensure_ascii=False, indent=2).replace('`', '\\u0060')
    return '\n'.join(lines) + '\n\n## Inventory\n\n```json\n' + body + '\n```'

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
        digest = hashlib.sha256(record['record_id'].encode()).hexdigest()
        if record['kind'] == 'operation':
            body = '# Operation\n\n```json\n' + json.dumps(human_times(record), ensure_ascii=False, indent=2).replace('`', '\\u0060') + '\n```'
            section = 'operations'
        else:
            body = render_observation(record)
            section = 'reports'
        entries['/'.join(('hosts', component(record['host_id']), record['observed_at'][:4], section, digest + '.md'))] = body
    for host in runtime.hosts:
        host_map.setdefault(host, [])
    index = ['# Hosts', '', 'Namespace: ' + config['namespace'], '', 'Generated: ' + format_time(now()), '',
             '| Host | Enabled | Groups | System | Last observation | Status |',
             '| --- | --- | --- | --- | --- | --- |']
    for host, items in sorted(host_map.items()):
        folder = component(host)
        latest = {}
        for record in items:
            if record['kind'] == 'observation':
                latest[record['recipe_reference']] = record
        summary = ['# ' + text(host), '', 'Namespace: ' + config['namespace'], '', 'Generated: ' + format_time(now()),
                   '', 'Latest observation: ' + format_time(max((r['observed_at'] for r in latest.values()), default='No observations')), '']
        for recipe, record in sorted(latest.items()):
            name = component(recipe) + '.md'
            rendered = render_observation(record)
            entries['hosts/' + folder + '/records/' + name] = rendered
            summary.append('- [' + text(recipe) + '](' + quote(name) + ') — ' + format_time(record['observed_at']) + ' / ' + text(record['data'].get('status')))
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
        entries['hosts/' + folder + '/records/README.md'] = '\n'.join(summary)
        configured = runtime.hosts.get(host, {})
        inventory = next((r for r in reversed(items) if r['kind'] == 'observation' and r['recipe_id'] == 'inventory-system'), None)
        system = inventory['data']['observations'].get('system_name', {}).get('value') if inventory else None
        last = max(latest.values(), key=lambda r: (r['observed_at'], r['record_id'])) if latest else None
        index.append('| [' + text(configured.get('label') or host) + '](' + quote('hosts/' + folder + '/README.md', safe='/') + ') | ' +
                     ' | '.join(text(v) for v in (configured.get('enabled', True) if host in runtime.hosts else 'not configured',
                     ','.join(group_names(configured.get('group', []), 'host group')), system or 'unknown', format_time(last['observed_at']) if last else 'never',
                     last['data'].get('status', 'unknown') if last else 'no observations')) + ' |')
    return entries, index, sorted(host_map)
