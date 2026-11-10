"""Inventory job service: static discovery, selective acquisition and optional retention."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
from uuid import uuid4

from opsfeast import ConfigError, Instance, REPOSITORY_ROOT, REPOSITORY_RECIPES, read_yaml
from host_runtime import connected, runtime_class, now
from inventory_actor import collection_actor
from retention_store import canonical, checked
import inventory_schedule as schedule

BUNDLE = REPOSITORY_RECIPES / 'system/inventory/overview'
CONTRACT = {'contract':'inventory-job-observations','version':'0.1.0',
            'description':'Per-job standard YANG node references and extension values with source times, identity scope and explicit gaps.',
            'schema':'job-retention.schema.json'}


def catalog():
    from opsfeast.profiling import provider_catalog
    return provider_catalog('system-inventory')


def inspect_collection(directory, metadata):
    """Data-only collection declaration validation, shared with recipe discovery."""
    if metadata.get('runner',{}).get('contract') in ('python-routines','recipe-meal'):
        from opsfeast.routine_contract import validate
        from opsfeast.routine_execution import collection
        validate(directory,metadata)
        data=collection(metadata)
        if data is None:raise ConfigError('not an inventory collection')
        return data
    from recipe_dispatch import declared_version
    from retention_contracts import validate_declaration
    if metadata.get('collection') != {'version':'0.1.0','catalog':'collection.json','entrypoint':'jobs.py','retention':CONTRACT}:
        raise ConfigError('recipe does not declare inventory job collection 0.1.0')
    for name in ('collection.json','jobs.py','job-retention.schema.json','properties.py','opsfeast-inventory.yang'):
        path = directory/name
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()) or not path.is_file():
            raise ConfigError('inventory job resource is missing or escapes recipe')
    data = json.loads((directory/'collection.json').read_text())
    if data != catalog():
        raise ConfigError('different property definitions require a reviewed registered contract')
    if declared_version(directory/'jobs.py') != '0.1.0':
        raise ConfigError('unsupported inventory job entrypoint version')
    validate_declaration({'retention':CONTRACT},directory)
    return data


def definition(config, reference='system/inventory/overview', *, explicit_host=False):
    """Static candidate inspection; never execute recipe code here."""
    info = config.recipe_location(reference, config.root/'hosts.yaml', cli=True)
    if not info['enabled'] and not explicit_host:
        raise ConfigError('inventory source is disabled')
    if info['scope'] is None:
        from opsfeast import Validator
        info['scope'] = Validator(info['root'])
    directory = info['scope'].path(info['pattern'],info['origin'])
    from recipe_dispatch import validate, bundle_digest
    metadata = read_yaml(directory/'recipe.yaml')
    if metadata.get('runner',{}).get('contract') in ('python-routines','recipe-meal'):
        from opsfeast.routine_contract import validate as validate_routine
        validate_routine(directory,metadata)
    else:validate(directory, metadata)
    data = inspect_collection(directory, metadata)
    if metadata.get('access_mode') != 'read':
        raise ConfigError('inventory job collection requires access_mode read')
    return {'directory':directory,'reference':info['reference'],'metadata':metadata,'catalog':data,
            'source_info':info,
            'definition_sha256':hashlib.sha256(canonical(data).encode()).hexdigest(),
            'bundle_sha256':bundle_digest(directory)}


def profile(root):
    return Instance.open().profile(root=root)


def select(data, jobs=None, properties=None, *, include_disabled=False):
    if properties and jobs:
        raise ConfigError('select properties or jobs, not both')
    if properties:
        names = list(dict.fromkeys(properties))
        if any(name not in data['properties'] for name in names):
            raise ConfigError('unknown property; use inventory describe for supported property IDs')
        return list(dict.fromkeys(data['properties'][n]['job'] for n in names)), names
    selected = list(dict.fromkeys(jobs)) if jobs else [key for key,value in data['jobs'].items() if include_disabled or value['enabled']]
    if not selected or any(key not in data['jobs'] for key in selected):
        raise ConfigError('select at least one known inventory job')
    return selected, None


def collect_host(root, host, **options):
    """A saved explicit host invocation owns one batch unless its caller supplies one."""
    from observation_runs import start, record_result, finish
    from retention_store import settings as retention_settings, refresh_content
    own = options.get('save', False) and not options.get('observation_run_id') and retention_settings(root) is not None
    run_id = options.get('observation_run_id')
    if own:
        config = profile(root).hosts._config
        if host not in config.hosts:
            raise ConfigError('unknown inventory host')
        jobs = options.get('jobs') or [key for key,value in catalog()['jobs'].items() if value['enabled']]
        if options.get('properties'):
            jobs = list(dict.fromkeys(catalog()['properties'][n]['job'] for n in options['properties'] if n in catalog()['properties']))
        run_id = start(root, [{'host_id':host, 'icon':config.hosts[host].get('icon',''),
                              'jobs':[{'id':j} for j in jobs]}],
                       options.get('reference','system/inventory/overview'), trigger=options.get('trigger','manual'),
                       selection={'kind':'cli','all':False,'selectors':[['host',host]],'exclude':[]})
        options['observation_run_id'] = run_id
    result = None
    try:
        result = _collect_host(root, host, **options)
        if own:
            record_result(root, run_id, host, result)
        return result
    except BaseException:
        if own:
            record_result(root, run_id, host, {'status':'failed','reason_code':'execution_did_not_complete'})
        raise
    finally:
        if own:
            finish(root, run_id)
            content = refresh_content(root)
            from observation_runs import publish_execution
            _,content = publish_execution(root,run_id,result_exit_code(result,content),content)
            if result is not None:
                result['content_update'] = content
                if result.get('result_path'):
                    from recipe_runner import save_receipt
                    save_receipt(Path(result['result_path']),result)


def _collect_host(root, host, *, jobs=None, properties=None, save=False, note='', trigger='manual',
                 reference='system/inventory/overview', timeout=30, budget=90,
                 session_class=None, prepared=None, cli_values=None, assignments=(), explicit_host=True,
                 observation_run_id=None):
    if jobs and properties:raise ConfigError('select properties or jobs, not both')
    if not isinstance(note,str) or len(note)>4096 or '\x00' in note:raise ConfigError('invalid inventory note')
    from opsfeast import positive_timeout
    from opsfeast.routine_execution import run_host
    from recipe_inputs import cli_variables
    timeout,budget=positive_timeout(timeout),positive_timeout(budget)
    selected_reference=prepared['reference'] if prepared else reference
    chosen=definition(profile(root).hosts._config,selected_reference,explicit_host=explicit_host)
    values=cli_variables(chosen['metadata'],cli_values,assignments)
    selection={'properties':properties} if properties else {'jobs':jobs} if jobs else None
    return run_host(root,host,[{'reference':selected_reference,'vars':values,'inventory_selection':selection}],
                    timeout=timeout,default_budget=budget,session_class=session_class,save=save,
                    trigger=trigger,note=note,observation_run_id=observation_run_id,explicit_host=explicit_host)


def dispatch(root, *, dry_run=False, timeout=30, budget=90, threads=4, at=None, collect=None):
    """Explicitly enabled hosts only. Attempts advance even on failure; no retry loop."""
    p = profile(root)
    config = p.hosts._config
    data = catalog()
    settings = schedule.settings(root,data,config.hosts)
    stamp = at or now()
    if type(threads) is not int or not 1<=threads<=64:
        raise ConfigError('dispatcher threads must be an integer from 1 to 64')
    def execute(state, locked=False):
        results = []
        tasks = []
        for host,entry in settings.get('hosts',{}).items():
            if not entry.get('enabled',False):
                continue
            if not config.hosts[host].get('enabled',True):
                results.append({'host_id':host,'status':'skipped','reason_code':'host_disabled'})
                continue
            reference = entry.get('recipe','system/inventory/overview')
            try:
                source = config.recipe_location(reference,config.root/'hosts.yaml',check_exists=False)
                if not source['enabled'] or not config.recipe_options(host,reference).get('enabled',False):
                    results.append({'host_id':host,'status':'skipped','reason_code':'source_disabled' if not source['enabled'] else 'recipe_disabled'})
                    continue
                chosen = definition(config,reference)
            except (ConfigError,OSError) as exc:
                chosen = {'reference':reference,'definition_sha256':hashlib.sha256(('unavailable:'+reference).encode()).hexdigest(),
                          'planning_error':type(exc).__name__}
            key = schedule.state_key(host,chosen['reference'],chosen['definition_sha256'])
            jobs = schedule.effective(chosen.get('catalog',data),settings,host)
            selected = schedule.due(jobs,state['targets'].get(key,{}),stamp)
            if not selected:
                continue
            if dry_run:
                results.append({'host_id':host,'jobs':selected,'status':'due'})
                continue
            target = state['targets'].setdefault(key,{})
            for job in selected:
                target[job] = {'attempted_at':stamp,'status':'started','source_observation_id':None}
            tasks.append((host,key,chosen,selected))
        if tasks:
            # All attempt times are durable before any worker connects.
            schedule.write_state(root,state)
        from observation_runs import start, record_result, finish
        run_id = start(root, [{'host_id':h, 'icon':config.hosts[h].get('icon',''),
                              'recipe_reference':chosen['reference'],
                              'jobs':[{'id':j} for j in selected]} for h,_,chosen,selected in tasks] +
                       [{'host_id':r['host_id'],'icon':config.hosts[r['host_id']].get('icon',''),
                         'recipe_reference':settings['hosts'][r['host_id']].get('recipe','system/inventory/overview')} for r in results],
                       'system/inventory/overview', trigger='scheduled', selection={
                           'kind':'scheduled','all':False,
                           'selectors':[['host',h] for h,_,_,_ in tasks]+[['host',r['host_id']] for r in results],
                           'exclude':[]}) if tasks else None
        if run_id:
            for result in results:
                record_result(root,run_id,result['host_id'],result)
        def acquire(task):
            host,key,chosen,selected = task
            try:
                if chosen.get('planning_error'):
                    raise ConfigError('scheduled recipe unavailable: '+chosen['planning_error'])
                result = (collect or collect_host)(root,host,jobs=selected,save=True,trigger='scheduled',
                                                  timeout=timeout,budget=budget,prepared=chosen,explicit_host=False,observation_run_id=run_id)
            except Exception as exc:
                # Pre-acquisition/storage failures are durable scheduler evidence too.
                result = {'host_id':host,'status':'failed','error_type':type(exc).__name__,
                          'reason':str(exc) if isinstance(exc,ConfigError) else 'pre_collection_or_persistence_failed'}
            return task,result
        if tasks:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(threads,len(tasks))) as pool:
                completed = list(pool.map(acquire,tasks))
        else:
            completed = []
        for (host,key,chosen,selected),result in completed:
            target = state['targets'][key]
            for job in selected:
                group = next((g for g in result.get('groups',[]) if g['id']==job),{})
                state_value = result['status'] if result.get('execution_errors') else group.get('status',result['status'])
                target[job].update(status=state_value, source_observation_id=result.get('source_observation_id'))
            if result.get('error_type'):
                # Preserve each failed attempt; no automatic deletion or retry policy.
                errors = checked(root,'inventory-errors')
                errors.mkdir(exist_ok=True)
                failure = errors/(str(uuid4())+'.json')
                from retention_store import atomic
                atomic(failure,canonical({'host_id':host,'jobs':selected,'attempted_at':stamp,'error_type':result['error_type'],'reason':result['reason']})+'\n')
            schedule.write_state(root,state)
            record_result(root,run_id,host,result)
            results.append(result)
        if run_id:
            finish(root,run_id)
            from retention_store import refresh_content
            content = refresh_content(root)
            from observation_runs import publish_execution
            code=1 if any(result_exit_code(r,content) for r in results) else 0
            _,content = publish_execution(root,run_id,code,content)
            for result in results:
                result['content_update'] = content
                if result.get('result_path'):
                    from recipe_runner import save_receipt
                    save_receipt(Path(result['result_path']),result)
        failed = any(result_exit_code(r) for r in results)
        return {'status':'failed' if failed else 'success','dry_run':dry_run,'hosts':results,'attempted_at':stamp,'observation_run_id':run_id}
    if dry_run:
        return execute(schedule.read_state(root))
    with schedule.lock(root) as acquired:
        if not acquired:
            return {'status':'skipped','reason_code':'dispatcher_already_running','hosts':[]}
        return execute(schedule.read_state(root),True)


def latest_groups(records):
    """A read-only mixed-age view. Latest attempt wins per property; never fill failed values."""
    selected = {}
    for record in sorted(records,key=lambda r:(r['observed_at'],r['record_id'])):
        if (record.get('retention_definition') or {}).get('contract') not in (CONTRACT['contract'],'inventory-routine-observations'):
            continue
        for group in record['data']['groups']:
            for coverage in group['coverage']:
                key = (record['namespace'],record['host_id'],record['recipe_reference'],record['data']['definition_sha256'],group['id'],coverage['property'])
                candidate = (coverage['observed_at'],record['observed_at'],record['record_id'])
                if key not in selected or candidate > selected[key][0]:
                    selected[key] = (candidate,record,group)
    buckets = {}
    for key,(_,record,group) in selected.items():
        bucket = buckets.setdefault((record['record_id'],group['id']),{'record':record,'group':group,'properties':set()})
        bucket['properties'].add(key[-1])
    result = []
    for bucket in buckets.values():
        record,original,names = bucket['record'],bucket['group'],bucket['properties']
        group = copy.deepcopy(original)
        group['samples'] = [s for s in group['samples'] if s['property'] in names]
        group['coverage'] = [s for s in group['coverage'] if s['property'] in names]
        group['source_record_id'] = record['record_id']
        group['source_actor'] = record['data']['actor']
        group['source_routines']=[copy.deepcopy(r) for r in record['data'].get('routine_evidence',[]) if set(r['properties']).intersection(names)]
        used={s['source_id'] for s in group['samples']} | {c['source_id'] for c in group['coverage']}
        probes={p['id']:p for p in record['data']['probes']}
        pending=list(used)
        while pending:
            for source in probes[pending.pop()].get('input_source_ids',[]):
                if source not in used:
                    used.add(source);pending.append(source)
        group['source_probes']=[copy.deepcopy(p) for p in record['data']['probes'] if p['id'] in used]
        group['property_definitions'] = {name:record['data']['property_definitions'][name] for name in names}
        group['definition_sha256'] = record['data']['definition_sha256']
        group['age_basis'] = 'original per-probe sample times; not view-generation time'
        result.append(group)
    return sorted(result,key=lambda g:(g['id'],g['observed_at'],g['source_record_id']))


def result_exit_code(result, content=None):
    """Single saved utility/dispatcher result, preserving independent storage errors."""
    if result is None:
        return 1
    return 0 if result.get('status') in ('success','skipped','due') and (
        result.get('retention') or {}).get('status')!='failed' and (
        content or result.get('content_update') or {}).get('status')!='failed' and (
        result.get('reference_ips_update') or {}).get('status')!='failed' else 1
