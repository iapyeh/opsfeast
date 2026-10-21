"""Observation execution runs 0.1.0, durably journaled with consumer events.

A run is anchored in its first target's annual retention archive. The anchor is
storage routing only; membership is the explicit targets list, never a time window.
"""
import copy
import json
import shlex
from uuid import uuid4
from opsfeast import ConfigError
from retention_store import archives, archive_path, canonical, database, locked, now, settings

VERSION = '0.1.0'


def validate_selection(selection):
    if selection is None:
        return
    if not isinstance(selection,dict) or set(selection) != {'kind','all','selectors','exclude'}:
        raise ConfigError('invalid run target selection')
    if selection['kind'] not in ('cli','scheduled') or type(selection['all']) is not bool:
        raise ConfigError('invalid run selection kind')
    if not isinstance(selection['selectors'],list) or not isinstance(selection['exclude'],list):
        raise ConfigError('invalid run selectors/exclusions')
    for item in selection['selectors']:
        if not isinstance(item,list) or len(item)!=2 or item[0] not in ('host','group') or not isinstance(item[1],str) or not item[1]:
            raise ConfigError('invalid run selector')
    if any(not isinstance(name,str) or not name for name in selection['exclude']):
        raise ConfigError('invalid run exclusion')
    if selection['all'] and selection['selectors'] or selection['exclude'] and not selection['all']:
        raise ConfigError('conflicting run selectors')
    if selection['kind']=='scheduled' and (selection['all'] or selection['exclude'] or any(kind!='host' for kind,_ in selection['selectors'])):
        raise ConfigError('scheduled selection records actual host IDs')
    if selection['kind']=='cli' and not selection['all'] and not selection['selectors']:
        raise ConfigError('run selection must name targets')


def selection_text(selection):
    if selection is None:
        return 'Not recorded'
    validate_selection(selection)
    if selection['kind']=='scheduled':
        return 'Scheduled hosts: ' + ', '.join(name for _,name in selection['selectors'])
    tokens=['--all'] if selection['all'] else []
    previous=None
    for kind,name in selection['selectors']:
        if kind!=previous:
            tokens.append('--'+kind)
        tokens.append(name)
        previous=kind
    if selection['exclude']:
        tokens += ['--exclude',*selection['exclude']]
    return shlex.join(tokens)


def validate_execution(execution, run):
    from observation_store import timestamp
    if not isinstance(execution,dict) or set(execution)!={'status','exit_code','completed_at','content_status'}:
        raise ConfigError('invalid execution receipt')
    if type(execution['exit_code']) is not int or execution['exit_code'] not in (0,1):
        raise ConfigError('invalid execution exit code')
    if execution['status'] != ('success' if execution['exit_code']==0 else 'failure') or execution['content_status'] not in ('success','failed','skipped'):
        raise ConfigError('invalid execution outcome')
    if run['completed_at'] is None or timestamp(execution['completed_at'])!=execution['completed_at'] or execution['completed_at']<run['completed_at']:
        raise ConfigError('invalid execution completion time')


def validate(run):
    from observation_store import uuid_text, timestamp
    try:
        fields = {'contract_version','run_id','namespace','anchor_host','recipe_reference','started_at',
                  'completed_at','status','trigger','targets'}
        if not isinstance(run, dict) or not fields.issubset(run) or set(run)-fields-{'selection','execution'} or run['contract_version'] != VERSION:
            raise ConfigError('invalid observation run contract')
        validate_selection(run.get('selection'))
        if 'execution' in run:
            validate_execution(run['execution'],run)
        uuid_text(run['run_id'])
        if timestamp(run['started_at']) != run['started_at'] or run['status'] not in ('running','success','partial','failed'):
            raise ConfigError('invalid observation run time/status')
        if (run['status']=='running') != (run['completed_at'] is None):
            raise ConfigError('observation run completion disagrees with status')
        if run['completed_at'] is not None and (timestamp(run['completed_at']) != run['completed_at'] or run['completed_at'] < run['started_at']):
            raise ConfigError('invalid observation run completion')
        for name in ('namespace','anchor_host','recipe_reference','trigger'):
            if not isinstance(run[name],str) or not run[name] or any(ord(c)<32 for c in run[name]):
                raise ConfigError('invalid observation run identity')
        targets = run['targets']
        if not isinstance(targets,list) or not targets or len({t['host_id'] for t in targets}) != len(targets):
            raise ConfigError('observation run needs distinct targets')
        if run['anchor_host'] != targets[0]['host_id']:
            raise ConfigError('observation run anchor disagrees with targets')
        target_fields = {'host_id','icon','jobs','requested_jobs','status','record_id','retention_status',
                         'reason_code','attention','baseline_record_ids','recipe_reference'}
        for target in targets:
            if set(target) != target_fields or not isinstance(target['host_id'],str) or not target['host_id']:
                raise ConfigError('invalid observation run target')
            if target['status'] not in ('pending','success','partial','failed','skipped') or not isinstance(target['jobs'],list) or not isinstance(target['requested_jobs'],list):
                raise ConfigError('invalid run target state')
            if run['status']!='running' and target['status']=='pending':
                raise ConfigError('completed run has a pending target')
            if target['record_id'] is not None:
                if not isinstance(target['record_id'],str) or not target['record_id']:
                    raise ConfigError('invalid retained record reference')
            if not isinstance(target['baseline_record_ids'],list):
                raise ConfigError('invalid baseline records')
            for identity in target['baseline_record_ids']:
                if not isinstance(identity,str) or not identity:
                    raise ConfigError('invalid baseline record reference')
        canonical(run)
        return run
    except (KeyError,TypeError,ValueError,AttributeError,RecursionError) as exc:
        raise ConfigError('invalid observation run contract') from exc


def path_for(root, run):
    return archive_path(root, {'host_id':run['anchor_host'],'observed_at':run['started_at']})


def _save(root, run):
    validate(run)
    run={key:value for key,value in run.items() if key!='execution'}
    with database(path_for(root,run), True) as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS observation_runs (run_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        existing = connection.execute('SELECT payload FROM observation_runs WHERE run_id=?',(run['run_id'],)).fetchone()
        if existing and json.loads(existing[0])['status'] != 'running':
            if json.loads(existing[0]) == run:
                return
            raise ConfigError('completed observation runs are immutable')
        connection.execute('INSERT OR REPLACE INTO observation_runs VALUES (?,?)',(run['run_id'],canonical(run)))
        from retention_consumers import enqueue
        enqueue(connection, {'kind':'run','record_id':run['run_id'],'namespace':run['namespace'],
            'host_id':run['anchor_host'],'recipe_reference':run['recipe_reference'],'observed_at':run['started_at'],
            'retention_definition':{'contract':'observation-run','version':VERSION}}, 'updated')


def list_runs(root):
    result=[]
    namespace = settings(root)
    if namespace is None:
        return []
    for path in archives(root):
        with database(path) as connection:
            if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='observation_runs'").fetchone():
                continue
            for (payload,) in connection.execute('SELECT payload FROM observation_runs'):
                run=validate(json.loads(payload))
                if run['namespace'] != namespace['namespace'] or path_for(root,run) != path:
                    raise ConfigError('observation run storage disagrees with identity')
                if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='observation_run_executions'").fetchone():
                    execution=connection.execute('SELECT payload FROM observation_run_executions WHERE run_id=? ORDER BY sequence DESC LIMIT 1',(run['run_id'],)).fetchone()
                    if execution:
                        run['execution']=json.loads(execution[0])
                        validate_execution(run['execution'],run)
                result.append(run)
    if len({r['run_id'] for r in result}) != len(result):
        raise ConfigError('duplicate observation run ID')
    return sorted(result,key=lambda r:(r['started_at'],r['run_id']))


def show(root, run_id):
    from observation_store import uuid_text
    uuid_text(run_id)
    run=next((r for r in list_runs(root) if r['run_id']==run_id),None)
    if run is None:
        raise ConfigError('observation run not found')
    return run


def start(root, targets, reference, *, trigger='manual', selection=None):
    validate_selection(selection)
    if not isinstance(targets,list) or not targets:
        raise ConfigError('observation run needs targets')
    config=settings(root)
    if config is None:
        raise ConfigError('observation runs require initialized retention')
    run={'contract_version':VERSION,'run_id':str(uuid4()),'namespace':config['namespace'],
         'anchor_host':targets[0]['host_id'],'recipe_reference':reference,'started_at':now(),
         'completed_at':None,'status':'running','trigger':trigger,'targets':[], 'selection':copy.deepcopy(selection)}
    for target in targets:
        run['targets'].append({'host_id':target['host_id'],'icon':target.get('icon',''),
            'jobs':copy.deepcopy(target.get('jobs',[])), 'requested_jobs':copy.deepcopy(target.get('jobs',[])),
            'recipe_reference':target.get('recipe_reference',reference), 'status':'pending','record_id':None,
            'retention_status':'pending','reason_code':None,'attention':None,'baseline_record_ids':[]})
    with locked(root):
        _save(root,run)
    return run['run_id']


def attention_context(root, record):
    from inventory_jobs import latest_groups
    from retention_store import query
    records=[r for r in query(root,hosts=[record['host_id']],kind='observation')['records']
             if r['observed_at'] <= record['observed_at'] and r['recipe_id']==record['recipe_id']
             and r['recipe_reference']==record['recipe_reference'] and r['origin']['namespace']==record['origin']['namespace']]
    context=copy.deepcopy(record)
    if 'groups' in record['data']:
        context['data']['groups']=latest_groups(records)
    return context, sorted({g['source_record_id'] for g in context['data'].get('groups',[]) if 'source_record_id' in g})


def record_result(root, run_id, host, result):
    from retention_store import show as retained
    from inventory_attention import evaluate
    with locked(root):
        run=show(root,run_id)
        target=next((t for t in run['targets'] if t['host_id']==host),None)
        if target is None or target['status'] != 'pending':
            raise ConfigError('observation run target is missing or already completed')
        status=result.get('status','failed')
        target['status']=status if status in ('success','partial','failed','skipped') else 'failed'
        target['reason_code']=result.get('reason_code') or result.get('error_type')
        receipt=result.get('retention',{})
        target['retention_status']=receipt.get('status','not_stored')
        target['record_id']=receipt.get('record_id')
        if 'attention_policy' in result:
            target['attention'] = evaluate({'data':{}},result['attention_policy'])
        if target['record_id']:
            observation=retained(root,target['record_id'])
            context, baselines=attention_context(root,observation)
            target['baseline_record_ids']=baselines
            target['recipe_reference']=observation['recipe_reference']
            if (observation.get('retention_definition') or {}).get('contract') in ('inventory-job-observations','inventory-observations'):
                target['attention']=evaluate(context,result.get('attention_policy',{}))
            target['jobs']=[{'id':g['id'],'title':g['title'],'status':g['status']} for g in observation['data'].get('groups',[])]
        _save(root,run)


def finish(root, run_id):
    with locked(root):
        run=show(root,run_id)
        if run['status'] != 'running':
            return run
        for target in run['targets']:
            if target['status']=='pending':
                target.update(status='failed',reason_code='execution_did_not_complete',retention_status='not_stored')
        states=[t['status'] for t in run['targets']]
        run['status']='success' if all(s in ('success','skipped') for s in states) else 'partial' if any(s in ('success','partial') for s in states) else 'failed'
        run['completed_at']=now()
        _save(root,run)
    return run


def record_execution(root, run_id, exit_code, content_status):
    """Append command outcome separately from immutable collection/Attention data.

    A failed final publication may append one success-to-failure correction.
    Later consumer retries never change the recorded command outcome.
    """
    with locked(root):
        run=show(root,run_id)
        execution={'status':'success' if exit_code==0 else 'failure','exit_code':exit_code,
                   'completed_at':now(),'content_status':content_status}
        validate_execution(execution,run)
        previous=run.get('execution')
        if previous:
            if previous['exit_code']==exit_code and previous['content_status']==content_status:
                return previous
            if not (previous['exit_code']==0 and exit_code==1 and content_status=='failed'):
                raise ConfigError('recorded execution outcome cannot be rewritten')
        with database(path_for(root,run),True) as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS observation_run_executions (sequence INTEGER PRIMARY KEY, run_id TEXT NOT NULL, payload TEXT NOT NULL)')
            connection.execute('INSERT INTO observation_run_executions (run_id,payload) VALUES (?,?)',(run_id,canonical(execution)))
            from retention_consumers import enqueue
            enqueue(connection,{'kind':'run','record_id':run_id,'namespace':run['namespace'],
                'host_id':run['anchor_host'],'recipe_reference':run['recipe_reference'],'observed_at':run['started_at'],
                'retention_definition':{'contract':'observation-run','version':VERSION}},'updated')
        return execution


def publish_execution(root, run_id, exit_code, content):
    """Record the command result, publish it, and preserve publication failures."""
    from retention_store import refresh_content
    if content['status']=='failed':
        exit_code=1
    record_execution(root,run_id,exit_code,content['status'])
    published=refresh_content(root)
    if published['status']=='failed':
        record_execution(root,run_id,1,'failed')
        return 1,published
    return exit_code, content if content['status']=='failed' else published
