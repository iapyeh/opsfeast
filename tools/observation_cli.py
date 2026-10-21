"""Compact, read-only views of explicit observation batches."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
import sys

from opsfeast import ConfigError, resolve_root
from console_output import cell, table, prepare, ConsoleDependencyError
from display_time import format_time
import observation_runs

STATES=('pending','success','partial','failed','skipped')


def short_ids(runs):
    identities={run['run_id']:run['run_id'].replace('-','') for run in runs}
    result={}
    for identity,key in identities.items():
        length=8
        while any(other!=identity and value.startswith(key[:length]) for other,value in identities.items()):
            length+=1
        result[identity]=key[:length]
    return result


def summary(run, short_id):
    execution=run.get('execution')
    completed=execution['completed_at'] if execution else run['completed_at']
    counts=Counter(t['status'] for t in run['targets'])
    return {'observation_id':run['run_id'],'short_id':short_id,'recipe_reference':run['recipe_reference'],
            'trigger':run['trigger'],'selection':run.get('selection'),'started_at':run['started_at'],
            'completed_at':completed,'execution_status':execution['status'] if execution else 'running' if run['status']=='running' else None,
            'collection_status':run['status'],'duration_seconds':max(0,int((datetime.fromisoformat(completed)-datetime.fromisoformat(run['started_at'])).total_seconds())) if completed else None,
            'counts':{state:counts[state] for state in STATES},'host_count':len(run['targets'])}


def query(root, identifier=None, *, statuses=None):
    """Return view 0.1.0 without altering full observation-run objects."""
    if statuses is not None and (not isinstance(statuses,list) or not statuses or any(s not in STATES for s in statuses)):
        raise ConfigError('status must name one or more host states')
    root=Path(root).resolve()
    runs=observation_runs.list_runs(root)
    ids=short_ids(runs)
    if identifier is None and not statuses:
        return {'view_version':'0.1.0','observations':[summary(r,ids[r['run_id']]) for r in reversed(runs)]}
    if identifier is None:
        identifier='latest'
    if identifier=='latest':
        if not runs:
            raise ConfigError('no saved observation batches')
        run=runs[-1]
    else:
        if not isinstance(identifier,str) or not (re.fullmatch('[0-9a-f]{8,32}',identifier) or re.fullmatch('[0-9a-f-]{36}',identifier)):
            raise ConfigError('observation ID must be a full UUID, unique hexadecimal prefix (8+), or latest')
        matches=[r for r in runs if (r['run_id']==identifier if '-' in identifier else r['run_id'].replace('-','').startswith(identifier))]
        if len(matches)!=1:
            raise ConfigError('ambiguous observation ID' if matches else 'observation not found')
        run=matches[0]
    # Exact raw batch membership supplies result links; never match nearby times.
    from recipe_reports import results
    indexed=results(root,kind='operation')
    links={}
    for item in indexed['results']:
        if item.get('observation_run_id')==run['run_id']:
            links.setdefault(item['host_id'],[]).append(item)
    hosts=[]
    warnings=[]
    for target in run['targets']:
        if target['retention_status']=='failed':
            warnings.append('Data storage failed for '+target['host_id']+'.')
        if statuses and target['status'] not in statuses:
            continue
        candidates=links.get(target['host_id'],[])
        linked=candidates[0] if len(candidates)==1 else None
        if len(candidates)>1:
            warnings.append('Multiple raw results match '+target['host_id']+'; result link is unavailable.')
        hosts.append({'host_id':target['host_id'],'icon':target.get('icon',''),'status':target['status'],
            'reason_code':target.get('reason_code'),'retention_status':target['retention_status'],
            'record_id':target['record_id'],'result_id':linked['result_id'] if linked else None,
            'short_id':linked['short_id'] if linked else None})
    if indexed['errors']:
        warnings.append(str(len(indexed['errors']))+' invalid raw result files were excluded from result links.')
    if (run.get('execution') or {}).get('content_status')=='failed':
        warnings.append('Content publication failed during this execution.')
    return {'view_version':'0.1.0','observation':summary(run,ids[run['run_id']]),
            'statuses':list(dict.fromkeys(statuses or [])),'hosts':hosts,'warnings':warnings}


def render(view):
    if 'observations' in view:
        rows=[[r['short_id'],format_time(r['started_at']),r['recipe_reference'],observation_runs.selection_text(r['selection']),
               r['execution_status'] or 'Not recorded',str(r['host_count'])] for r in view['observations']]
        return table(['id','started','recipe','targets','outcome','hosts'],rows) if rows else 'No saved observation batches.'
    run=view['observation']
    counts=', '.join(state+': '+str(run['counts'][state]) for state in STATES if run['counts'][state])
    lines=['Observation: '+run['observation_id'],'Started: '+format_time(run['started_at']),
           'Recipe: '+cell(run['recipe_reference']),'Targets: '+cell(observation_runs.selection_text(run['selection'])),
           'Outcome: '+(run['execution_status'] or 'Not recorded')+'; collection: '+run['collection_status'],
           'Hosts: '+str(run['host_count'])+' — '+counts,
           'Showing: '+str(len(view['hosts']))+'/'+str(run['host_count'])+
           (' ('+', '.join(view['statuses'])+')' if view['statuses'] else '')]
    if run['duration_seconds'] is not None:
        lines += ['Duration: '+str(run['duration_seconds'])+' seconds']
    lines += ['Warning: '+cell(warning) for warning in view['warnings']]
    if view['hosts']:
        lines += ['',table(['host','status','reason','result id'],[
            [((h['icon'] or '')+' '+h['host_id']).strip(),h['status'],h['reason_code'] or '-',h['short_id'] or '-'] for h in view['hosts']])]
    else:
        lines += ['','No hosts match the selected statuses.']
    return '\n'.join(lines)


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv[:1]==['result']:
        from observation_results import main as result_main
        return result_main(argv[1:])
    parser=argparse.ArgumentParser(prog='opsfeast.py observation',allow_abbrev=False,
        description='Read saved batches. No ID lists batches; --status without an ID selects latest. Use observation result [RESULT_ID] for host results. No connections or writes.',
        epilog='Example: opsfeast.py observation latest --status failed partial --profile main')
    parser.add_argument('observation_id',nargs='?',help='full UUID, unique hexadecimal prefix (8+), or latest')
    parser.add_argument('--status',choices=STATES,nargs='+',action='extend',default=None,help='filter host collection states; omitted ID means latest')
    environment=parser.add_mutually_exclusive_group()
    environment.add_argument('--root',type=Path)
    environment.add_argument('--profile')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv)
    try:
        prepare(args.json)
        root=resolve_root(args.root,args.profile).resolve(strict=True)
        view=query(root,args.observation_id,statuses=args.status)
        if args.json or not sys.stdout.isatty():
            print(json.dumps(view,indent=2,ensure_ascii=False,allow_nan=False))
        else:
            print(render(view))
        return 0
    except (ConfigError,OSError,ValueError,ImportError,ConsoleDependencyError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        return 1
