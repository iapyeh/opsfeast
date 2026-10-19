"""Portable content author consuming the report's public retention reader."""
from datetime import datetime
import html
import json

VERSION = '0.1.0'


def execute(*, context, timeout):
    references, hosts = context.vars['recipes'], context.vars['hosts']
    if any(not isinstance(v, str) or not v for v in references + hosts):
        return {'status': 'failed', 'reason_code': 'invalid_selection', 'message': 'Selectors must contain nonempty strings.', 'data': {}, 'artifacts': []}
    records = context.retention.query(hosts=hosts, kind='observation')['records']
    if references:
        records = [r for r in records if r['recipe_reference'] in references]
    generated = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
    title = context.vars['title']
    md = lambda v: html.escape(str(v)).replace('|', '&#124;').replace('\n', ' ').replace('[', '&#91;').replace(']', '&#93;')
    rows = []
    for record in records:
        data = record['data']
        # Keep the entire record: partial/missing fields and identity warnings are evidence.
        rows.append([record['host_id'], record['recipe_reference'], data['status'], record['observed_at'], record['record_id'], json.dumps(record, ensure_ascii=False)])
    headers = ['Host', 'Recipe reference', 'Status', 'Observed (source time)', 'Record ID', 'Data and provenance']
    markdown = '# ' + md(title) + '\n\nGeneration does not refresh observations. Missing data stays unknown.\n\n'
    markdown += '| ' + ' | '.join(headers) + ' |\n|' + '|'.join([' --- ']*len(headers)) + '|\n'
    markdown += '\n'.join('| ' + ' | '.join(md(v) for v in row) + ' |' for row in rows)
    markdown += '\n\n_Last modified: ' + generated + '_\n'
    table = '<table><tr>' + ''.join('<th>'+html.escape(h)+'</th>' for h in headers) + '</tr>'
    table += ''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows) + '</table>'
    web = '<!doctype html><html lang="en"><meta charset="utf-8"><title>'+html.escape(title)+'</title><h1>'+html.escape(title)+'</h1><p>Generation does not refresh observations. Missing data stays unknown.</p>'+table+'<footer>Last modified: '+generated+'</footer></html>'
    (context.artifact_dir/'retention.md').write_text(markdown, encoding='utf-8')
    (context.artifact_dir/'retention.html').write_text(web, encoding='utf-8')
    return {'status': 'success', 'reason_code': 'content_generated' if rows else 'empty_selection',
            'message': 'Offline content generated from retained observations.',
            'data': {'rows': len(rows), 'record_ids': [r['record_id'] for r in records]},
            'artifacts': [{'path': 'retention.md', 'title': title, 'media_type': 'text/markdown'},
                          {'path': 'retention.html', 'title': title, 'media_type': 'text/html'}]}
