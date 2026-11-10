"""Self-contained ordinary-code report; no network, model or renderer dependency."""
from datetime import datetime, timezone
import html
import json

VERSION = '0.1.3'


def _human_times(value):
    # Keep the exported recipe self-contained; follow OpsFeast's display policy.
    if isinstance(value, dict):
        return {key: _human_times(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_human_times(item) for item in value]
    if isinstance(value, str):
        try:
            instant = datetime.fromisoformat(value)
            if instant.tzinfo is not None:
                return instant.astimezone().strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OverflowError, OSError):
            pass
    return value


def execute(*, context, timeout):
    rows = []
    for document in context.inputs:
        if (not isinstance(document.get('recipe'), dict) or 'host_id' not in document or
                document.get('status') not in ('success', 'partial', 'failed', 'skipped', 'unsupported')):
            return {'status': 'failed', 'reason_code': 'unsupported_input', 'message': 'Expected raw execution-result objects.', 'data': {}, 'artifacts': []}
        children=document.get('children',[])
        if not isinstance(children,list) or any(not isinstance(child,dict) or not isinstance(child.get('recipe',{}),dict) for child in children):
            return {'status':'failed','reason_code':'unsupported_input','message':'Expected child result receipts.','data':{},'artifacts':[]}
        identity = document.get('identity') or {}
        rows.append({'host': document['host_id'], 'recipe': document['recipe'].get('id'),
                     'recipe_reference':document['recipe'].get('reference'),
                     'meal_run_id':document.get('meal_run_id'),
                     'retention':document.get('retention'),
                     'content_update':document.get('content_update'),
                     'meal_scope':{key:document[key] for key in ('restoration_verified','cleanup_verified','execution_errors') if key in document},
                     'routine_evidence':document.get('routine_evidence'),
                     'connection_evidence':document.get('connection_evidence'),
                     'children':children,
                     'recipe_version': document['recipe'].get('version'), 'source_schema_version': document.get('schema_version'),
                     'source_evidence_kind': document.get('evidence_kind'),
                     'status': document['status'], 'reason_code': document.get('reason_code'),
                     'observed_from': document.get('started_at'), 'observed_to': document.get('finished_at', document.get('completed_at',document.get('observed_at'))),
                     'identity_quality': identity.get('quality') if isinstance(identity, dict) else None,
                     'identity_warnings': identity.get('warnings', [identity['warning']] if identity.get('warning') else []) if isinstance(identity, dict) else [],
                     'inventory': document.get('inventory'),
                     'collection_scope': {key: (document.get('access') or {}).get(key) for key in ('mode', 'actual_identity')},
                     'data': document.get('data'), 'observations': document.get('observations')})
    generated = datetime.now(timezone.utc).isoformat()
    title = context.vars['title']
    keys = ['host', 'recipe', 'recipe_reference', 'status', 'reason_code', 'observed_from', 'observed_to', 'identity_quality', 'identity_warnings']
    esc = lambda value: html.escape(str(value), quote=True)
    table = '<table><thead><tr>' + ''.join('<th>'+esc(key)+'</th>' for key in keys) + '<th>Details</th></tr></thead><tbody>'
    for row in rows:
        details = {key:row[key] for key in ('recipe_version', 'source_schema_version', 'source_evidence_kind', 'data', 'observations', 'inventory', 'collection_scope','meal_run_id','routine_evidence','connection_evidence','children','meal_scope','retention','content_update')}
        child_table=''
        if row['children']:
            child_table='<details><summary>Child recipe outcomes ('+str(len(row['children']))+')</summary><table><tr><th>Recipe reference</th><th>Status</th><th>Retention</th><th>Source result</th></tr>'
            for child in row['children']:
                child_table+='<tr>'+''.join('<td>'+esc(json.dumps(value,ensure_ascii=False))+'</td>' for value in (child.get('recipe',{}).get('reference'),child.get('status'),child.get('retention'),child.get('result_path')))+'</tr>'
            child_table+='</table></details>'
        table += ('<tr>' + ''.join('<td>'+esc(json.dumps(_human_times(row[key]), ensure_ascii=False))+'</td>' for key in keys) +
                  '<td><details><summary>Data and provenance</summary><pre>'+esc(json.dumps(_human_times(details), ensure_ascii=False, indent=2))+'</pre></details>'+child_table+'</td></tr>')
    content = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
               '<title>'+esc(title)+'</title><style>body{font:16px system-ui;margin:2em}table{border-collapse:collapse;width:100%}th,td{border:1px solid #bbb;padding:.5em;vertical-align:top;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
               '<h1>'+esc(title)+'</h1><p>Generated '+esc(_human_times(generated))+'. Times use controller local time to seconds; JSON preserves source times. Execution success does not imply service health. Missing values are unknown.</p>'+table+'</tbody></table></html>')
    (context.artifact_dir/'summary.html').write_text(content, encoding='utf-8')
    (context.artifact_dir/'summary.json').write_text(json.dumps({'generated_at':generated, 'rows':rows}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return {'status':'success', 'reason_code':'report_complete' if rows else 'empty_selection',
            'message':'Report generated from selected results.' if rows else 'Report generated with no source results.',
            'data':{'rows':len(rows), 'generated_at':generated},
            'artifacts':[{'path':'summary.html','title':title,'media_type':'text/html'},
                         {'path':'summary.json','title':'Report data','media_type':'application/json'}]}
