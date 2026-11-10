"""Inventory routine bodies and pure recipe finalization over shared collectors."""
import copy
import hashlib
import json
import time
from pathlib import Path
from opsfeast import ConfigError
from host_runtime import now

ROOT=Path(__file__).parent


def catalog():
    return json.loads((ROOT/'collection.json').read_text())


def collect(recipe,properties):
    acquire=recipe.inventory_collector
    selected=[name for name in properties if name in recipe.selected_properties]
    if not selected:raise ConfigError('empty inventory routine selection')
    data=catalog();jobs=list(dict.fromkeys(data['properties'][n]['job'] for n in selected))
    remaining=recipe.deadline-time.monotonic()
    if remaining<=0:raise TimeoutError('routine deadline')
    result=acquire(recipe.session,recipe.host_id,jobs,selected,
                   timeout=min(recipe.vars.get('command_timeout_seconds',recipe.timeout),recipe.timeout,remaining),
                   budget=min(recipe.vars.get('collection_budget_seconds',90),remaining),platform_observation=recipe.platform_observation)
    return {'status':result['status'],'reason_code':'inventory_collected','message':'Selected inventory properties collected.','data':result}


def finalize(results):
    """Merge only declared routine outputs, retaining source times and explicit gaps."""
    data=catalog();groups={};probes=[];platform=None
    reference=None
    started=min(r['started_at'] for r in results);observed=max(r['completed_at'] for r in results)
    for index,receipt in enumerate(results):
        part=copy.deepcopy((receipt.get('result') or {}).get('data') or {})
        allowed=set(receipt['properties'])
        prefix=str(index)+'-'
        for probe in part.get('probes',[]):
            probe['id']=prefix+probe['id']
            if 'input_source_ids' in probe:probe['input_source_ids']=[prefix+i for i in probe['input_source_ids']]
            probes.append(probe)
        if part.get('reference_ips'):
            part['reference_ips']['source_id']=prefix+part['reference_ips']['source_id'];reference=part['reference_ips']
        platform=part.get('platform') or platform
        covered=set()
        for group in part.get('groups',[]):
            if any(c['property'] not in allowed for c in group['coverage']):raise ConfigError('routine returned undeclared inventory fields')
            target=groups.setdefault(group['id'],dict(group,samples=[],coverage=[]))
            target['started_at']=min(target['started_at'],group['started_at']);target['observed_at']=max(target['observed_at'],group['observed_at'])
            for key in ('coverage','samples'):
                for item in group[key]:
                    item['source_id']=prefix+item['source_id'];target[key].append(item)
            covered.update(c['property'] for c in group['coverage'])
        missing=allowed-covered
        if missing:
            stamp=receipt['completed_at'];source=prefix+'unavailable'
            probes.append({'id':source,'command':None,'started_at':receipt['started_at'],'observed_at':stamp,'status':'failed','reason_code':receipt['reason_code'],'exitcode':None,'error_type':None})
            for name in sorted(missing):
                spec=data['properties'][name];job=spec['job']
                group=groups.setdefault(job,{'id':job,'title':data['jobs'][job]['title'],'started_at':receipt['started_at'],'observed_at':stamp,'samples':[],'coverage':[]})
                group['started_at']=min(group['started_at'],receipt['started_at']);group['observed_at']=max(group['observed_at'],stamp)
                group['coverage'].append({'property':name,'complete':False,'source_id':source,'observed_at':stamp})
                group['samples'].append({'property':name,'keys':{},'value':None,'status':'unavailable','reason_code':receipt['reason_code'],'source_id':source,'observed_at':stamp})
    for group in groups.values():group['status']='success' if all(c['complete'] for c in group['coverage']) else 'partial' if any(s['status']=='success' for s in group['samples']) else 'failed'
    status='success' if groups and all(g['status']=='success' for g in groups.values()) else 'partial' if any(g['status'] in ('partial','success') for g in groups.values()) else 'failed'
    definitions={c['property']:data['properties'][c['property']] for g in groups.values() for c in g['coverage']}
    payload={'host_id':results[0]['host_id'],'started_at':started,'observed_at':observed,'status':status,'groups':list(groups.values()),'probes':probes,'platform':platform,
             'definition_sha256':hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),
             'property_definitions':definitions,'actor':{'username':None,'effective_uid':None,'mode':'unverified'},
             'identity_warning':'Identity is scoped to configured namespace and Host ID. Actual collection identity is recorded per routine.',
             'implementation':{'entrypoint':'jobs.py','version':'0.1.0','platform':platform,'sha256':hashlib.sha256((ROOT/'jobs.py').read_bytes()).hexdigest()},'execution_errors':[], 'trigger':'manual','note':''}
    actors={json.dumps(r['actor'],sort_keys=True) for r in results if r['actor']['effective_uid'] is not None}
    if len(actors)==1:payload['actor']=json.loads(next(iter(actors)))
    if reference:payload['reference_ips']=reference
    return {'status':status,'reason_code':'inventory_routines_collected','message':'Independent inventory routine results; inspect gaps and actor evidence.','data':payload}
