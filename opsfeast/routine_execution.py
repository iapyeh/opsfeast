"""Host-owned, sequential routine meals with verified permission phases 0.1.0."""
from contextlib import ExitStack,contextmanager
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import runpy
import threading
import tempfile
import time
from uuid import uuid4

from . import ConfigError, Instance, Recipe, RootUnavailableError, REPOSITORY_ROOT
from .routine_contract import validate,order,ROUTINES,MEAL
from host_runtime import connected,verify_connection_identity,identity,now,runtime_class,output

@dataclass(frozen=True)
class PlannedRecipe:
    reference: str
    directory: Path
    descriptor: str
    variables: str
    routines: tuple
    properties: tuple
    fingerprint: str
    source_directory: Path
    source_fingerprint: str


@contextmanager
def read_snapshot(directory):
    """Private temporary copy without creating Profile lock/output files."""
    from .recipe_install import tree
    before=tree(directory)
    with tempfile.TemporaryDirectory(prefix='opsfeast-routine-code-') as temp:
        for name,value in before.items():
            target=Path(temp)/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(value);target.chmod(0o755 if (Path(directory)/name).stat().st_mode & 0o111 else 0o644)
        if tree(directory)!=before:raise ConfigError('recipe changed while copying')
        yield Path(temp)


def _program(path):
    from recipe_runner import _implementation_lock
    with _implementation_lock:return runpy.run_path(str(path))


def engine_digest():
    paths=[Path(__file__),Path(__file__).with_name('routine_contract.py'),Path(__file__).with_name('core.py'),*[REPOSITORY_ROOT/'tools'/name for name in ('root_access.py','host_runtime.py','inventory_property_types.py','inventory_attention.py','recipe_inputs.py','recipe_settings.py')]]
    paths+=list((Path(__file__).parent/'inventory').glob('*.py'))+[Path(__file__).parent/'inventory/collection.json']
    h=hashlib.sha256()
    for path in sorted(paths):h.update(path.name.encode()+b'\0'+path.read_bytes())
    return h.hexdigest()


def collection(metadata):
    from .inventory.service import catalog
    data=catalog()
    if metadata.get('runner',{}).get('contract')==MEAL:return data
    binding=metadata.get('inventory')
    if binding is None:return None
    if binding.get('version')!='0.1.0' or set(binding)!={'version','job','properties'} or binding['job'] not in data['jobs']:raise ConfigError('invalid inventory recipe binding')
    expected=[n for n,s in data['properties'].items() if s['job']==binding['job']]
    if binding['properties']!=expected:raise ConfigError('inventory recipe fields differ from reviewed catalog')
    declared={p for r in metadata['runner']['routines'] for p in r['properties']}
    if declared!=set(expected):raise ConfigError('inventory routine fields differ from recipe')
    return {**data,'jobs':{binding['job']:{**data['jobs'][binding['job']],'enabled':True}},'properties':{n:data['properties'][n] for n in expected}}


def plan(root,host,choices,*,explicit_host=True):
    if not isinstance(choices,(list,tuple)) or not 1<=len(choices)<=32:raise ConfigError('meal choices must be a nonempty bounded list')
    for choice in choices:
        if not isinstance(choice,dict) or set(choice)-{'reference','vars','inputs','inventory_selection'} or not isinstance(choice.get('reference'),str) or not isinstance(choice.get('vars',{}),dict) or choice.get('inputs',[]):raise ConfigError('invalid routine choice')
    try:return _plan(root,host,choices,explicit_host=explicit_host)
    except ConfigError:raise
    except (ValueError,KeyError,TypeError,AttributeError,RecursionError):raise ConfigError('invalid routine selection') from None


def _plan(root,host,choices,*,explicit_host=True):
    """Validate every member and input before any transport or candidate import."""
    from recipe_runner import preflight
    from .recipe_install import fingerprint
    from recipe_inputs import prepare_vars
    from inventory_jobs import select
    members=[];configs=[];seen=set()
    for choice in choices:
        config,directory,_,_=preflight(root,host,choice['reference'],cli_vars=choice.get('vars'),explicit_host=explicit_host)
        if directory is None:raise ConfigError('meal member disabled')
        metadata=config.execution_recipe['metadata'];contract=metadata['runner']['contract']
        data=validate(directory,metadata);selection=choice.get('inventory_selection')
        inventory=collection(metadata)
        jobs,props=select(inventory,**(selection or {})) if inventory else ([],None)
        selected=props or [n for n,s in inventory['properties'].items() if s['job'] in jobs] if inventory else []
        if selection is not None and inventory is None:raise ConfigError('inventory selection requires collection')
        references=[(choice['reference'],None)]
        if contract==MEAL:
            references=[]
            for member in data['members']:
                child_config,child,_,_=preflight(root,host,member['reference'],explicit_host=explicit_host)
                if child is None:raise ConfigError('meal member disabled')
                child_meta=child_config.execution_recipe['metadata']
                if child_meta['runner']['contract']!=ROUTINES:raise ConfigError('meal members must opt into python-routines')
                child_fields=set(child_meta.get('inventory',{}).get('properties',[]))
                include=(bool(set(selected)&child_fields) if selection is not None else member['enabled'])
                if include:references.append((member['reference'],set(selected)&child_fields))
        elif contract!=ROUTINES:raise ConfigError('shared execution requires python-routines')
        for ref,subset in references:
            child_config,child,_,_=preflight(root,host,ref,explicit_host=explicit_host)
            meta=child_config.execution_recipe['metadata'];specs=validate(child,meta)
            if child_config.execution_recipe['execution']!={'via':'login','user':None}:raise ConfigError('routine phases require login execution policy; do not override it')
            from recipe_settings import merge
            common=config.execution_recipe['effective_vars'] if contract==MEAL else {}
            child_info=child_config.execution_recipe
            source_values=merge(child_info.get('vars',{}),common)
            host_values=child_config.matching_recipe_vars(host,child,child_info)
            values=prepare_vars(meta,source_values,host_values,choice.get('vars') or {})
            if meta.get('inventory'):
                from inventory_attention import resolve
                resolve(values.get('attention',{}))
                binding=collection(meta);fields=list(binding['properties'])
                chosen=set(selected) if contract!=MEAL else subset
                fields=[n for n in fields if n in chosen] if chosen is not None else fields
            else:fields=list(dict.fromkeys(p for s in specs for p in s.properties))
            if ref in seen:raise ConfigError('duplicate resolved meal recipe')
            seen.add(ref)
            if not fields and meta.get('inventory'):continue
            members.append(PlannedRecipe(ref,child,json.dumps(meta,sort_keys=True),json.dumps(values,sort_keys=True),order(specs),tuple(fields),fingerprint(child),directory,fingerprint(directory)))
            configs.append(child_config)
    if not members:raise ConfigError('no selected meal members')
    first=configs[0]
    if any(c.hosts[host]!=first.hosts[host] or c.documents!=first.documents for c in configs):raise ConfigError('meal host configuration changed during planning')
    return tuple(members),first


def describe(root,host,choices,*,explicit_host=True):
    members,_=plan(root,host,choices,explicit_host=explicit_host)
    return {'contract_version':'0.1.0','engine_sha256':engine_digest(),'connection_scope':'one owned target connection per host; no retry',
            'members':[{'reference':m.reference,'fingerprint':m.fingerprint,'composition_fingerprint':m.source_fingerprint,'variable_names':sorted(json.loads(m.variables)),
                        'properties':list(m.properties),'routines':[{'id':s.id,'required_permission':s.required_permission,'platforms':list(s.platforms),'properties':[p for p in s.properties if p in m.properties],'depends_on':list(s.depends_on)} for s in m.routines if set(s.properties).intersection(m.properties) or not json.loads(m.descriptor).get('inventory')]} for m in members]}


def run_host(root,host,choices,*,timeout=30,default_budget=90,session_class=None,runtime=None,save=True,trigger='manual',note='',stop=None,observation_run_id=None,explicit_host=True):
    from recipe_runner import save_report,save_receipt,finalize_content
    from .recipe_install import execution_snapshot,fingerprint
    from recipe_contract import validate_result
    from retention_replay import snapshot
    from retention_store import retain_general,settings
    from .inventory.service import catalog
    from . import positive_timeout
    timeout,default_budget=positive_timeout(timeout),positive_timeout(default_budget)
    if trigger not in ('manual','scheduled') or not isinstance(note,str) or len(note)>4096 or '\x00' in note:raise ConfigError('invalid routine invocation metadata')
    members,config=plan(root,host,choices,explicit_host=explicit_host)
    expected_engine=engine_digest();identifier=str(uuid4());began=now()
    aggregate={'schema_version':'0.1.0','meal_run_id':identifier,'host_id':host,'started_at':began,'observed_at':began,'status':'failed','reason_code':'routine_execution_failed','message':'Routine meal execution.','recipe':{'id':'recipe-meal','version':'0.1.0','reference':choices[0]['reference']},'children':[],'groups':[],'actor':{'username':None,'effective_uid':None,'mode':'unverified'},'identity_warning':'Actual collection identity is recorded independently for each recipe routine.','execution_errors':[],'restoration_verified':False,'cleanup_verified':False,'observation_run_id':observation_run_id}
    reports={};receipts={m.reference:[] for m in members};executed=[];platform=None
    clock=time.monotonic();member_deadlines={m.reference:clock+json.loads(m.variables).get('collection_budget_seconds',default_budget) for m in members}
    deadline=max(member_deadlines.values());cancelled=lambda:stop is not None and stop.is_set()
    profile=__import__('opsfeast.core',fromlist=['Profile']).Profile._from_config(Instance.open(),config)
    from retention_store import checked
    output_dir=checked(root,'observations')
    if save and settings(root) is None:raise ConfigError('saved routine execution requires retention namespace')
    def persist(member):
        if save:
            output_dir.mkdir(exist_ok=True);save_report(output_dir/('recipe-run-'+reports[member.reference]['source_observation_id']+'.json'),reports[member.reference])
    with ExitStack() as pins:
        programs={}
        shared=pins.enter_context(read_snapshot(Path(__file__).parent/'inventory'))
        inventory_program=_program(shared/'jobs.py')['collect']
        for member in members:
            pinned=pins.enter_context(execution_snapshot(Path(root),member.directory) if save else read_snapshot(member.directory));meta=json.loads(member.descriptor)
            if fingerprint(pinned)!=member.fingerprint:raise ConfigError('meal code changed after planning')
            # Store evidence before the first candidate body; imports are reviewed code.
            programs[member.reference]=_program(pinned/meta['runner']['entrypoint'])
            reports[member.reference]={'run_contract':'0.1.0','schema_version':meta['output']['schema_version'],'meal_run_id':identifier,'source_observation_id':str(uuid4()),'observation_run_id':observation_run_id,'producer_instance_id':profile.instance.identity['id'],'host_id':host,'started_at':began,'completed_at':None,'status':'partial','reason_code':'execution_not_complete','routine_execution_state':'incomplete','message':'Routine recipe has not completed.','data':{},'routine_evidence':[],'execution_errors':[],'execution_access_mode':'read','evidence_kind':'local' if config.hosts[host]['connection'].get('local') else 'ssh','runtime':runtime or {'verification':'runtime-selected'},'recipe':{'id':meta['id'],'version':meta['version'],'recipe_version':meta['version'],'reference':member.reference,'runner_contract':ROUTINES,'bundle_sha256':member.fingerprint,'variable_names':sorted(json.loads(member.variables))},'retention_snapshot':snapshot(meta,pinned),'retention':{'status':'skipped','reason_code':'not_finalized'}}
            if meta.get('inventory'):
                from inventory_attention import resolve
                reports[member.reference]['attention_policy']=resolve(json.loads(member.variables).get('attention',{}))
            persist(member)
        session_class=session_class or runtime_class()
        uncertain=False
        try:
            if engine_digest()!=expected_engine or any(fingerprint(m.source_directory)!=m.source_fingerprint for m in members):raise ConfigError('routine engine or meal changed after planning')
            from . import Validator
            fresh=Validator(root);fresh.load(fresh.root/'hosts.yaml');fresh.check_connections()
            if fresh.documents!=config.documents:raise ConfigError('host configuration changed after planning')
            if cancelled():raise InterruptedError('stop requested')
            with connected(config,host,session_class,timeout,aggregate) as session:
                login=verify_connection_identity(session,timeout,aggregate,authenticated_user=aggregate.get('login_identity',{}).get('username'),configured_user=config.hosts[host]['connection'].get('user'))
                platform_started=now();uname=session.exec_command(['uname','-s'],command_timeout=timeout)
                kernel=output(uname).strip()
                if len(kernel)>4096:raise ConfigError('platform output too large')
                platform_source={'id':'platform','command':'uname -s','started_at':platform_started,'observed_at':now(),'status':'success','reason_code':None,'exitcode':0,'error_type':None,'stdout':uname.stdout,'stderr':uname.stderr,'stdout_truncated':False,'stderr_truncated':False}
                platform={'Linux':'linux','Darwin':'macos','FreeBSD':'freebsd','VMkernel':'esxi'}.get(kernel)
                def phase(actor,actual,permission):
                    nonlocal uncertain
                    phase_cache={}
                    owner=Recipe._create(profile,config,host,actor,timeout,aggregate,run_id=identifier,owner='routine-executor')
                    try:
                        for member in members:
                            for spec in member.routines:
                                if spec.required_permission!=permission or spec.platforms and platform not in spec.platforms:continue
                                fields=[p for p in spec.properties if p in member.properties]
                                if not fields and json.loads(member.descriptor).get('inventory'):continue
                                stamp=now();receipt={'id':spec.id,'host_id':host,'required_permission':permission,'properties':fields,'actor':dict(actual,mode='root' if actual['effective_uid']==0 else 'user'),'started_at':stamp,'completed_at':stamp,'status':'skipped','reason_code':'not_started','result':None}
                                receipts[member.reference].append(receipt)
                                member_deadline=member_deadlines[member.reference]
                                if cancelled() or time.monotonic()>=member_deadline or uncertain:
                                    receipt['reason_code']='stop_requested' if cancelled() else 'scope_unavailable' if uncertain else 'budget_exhausted';continue
                                previous={r['id']:r['status'] for r in receipts[member.reference]}
                                if any(previous.get(dep) not in ('success','partial') for dep in spec.depends_on):receipt['reason_code']='prerequisite_failed';continue
                                try:
                                    remaining=min(timeout,member_deadline-time.monotonic())
                                    before=identity(actor,remaining)
                                    if before!=actual or permission=='root' and before['effective_uid']!=0:raise RuntimeError('routine identity mismatch')
                                    from recipe_runner import progress
                                    progress('routine '+member.reference+'/'+spec.id+'; permission='+permission+'; actor='+actual['username']+'; uid='+str(actual['effective_uid']))
                                    with owner.child(vars=json.loads(member.variables),report={'routine_identity':deepcopy(actual)},timeout=remaining) as child:
                                        child.routine=spec;child.selected_properties=tuple(fields);child.deadline=member_deadline;child.inventory_collector=inventory_program;child.platform_observation=(kernel,deepcopy(platform_source)) if permission=='login' else None
                                        child.session.inventory_probe_cache=phase_cache;child.session.inventory_cache_scope=member.variables
                                        child.prerequisites={r['id']:deepcopy(r['result']) for r in receipts[member.reference] if r['id'] in spec.depends_on and r['result'] is not None}
                                        result=validate_result(programs[member.reference][spec.function](child))
                                    after=identity(actor,min(timeout,max(.01,deadline-time.monotonic())))
                                    if after!=actual:raise RuntimeError('routine identity changed')
                                    receipt.update(status=result['status'],reason_code=result['reason_code'],result=result)
                                except Exception as exc:
                                    receipt.update(status='failed',reason_code='routine_failed',error_type=type(exc).__name__)
                                    reports[member.reference]['execution_errors'].append({'stage':'routine','routine':spec.id,'error_type':type(exc).__name__})
                                    # Continue only after verifying this exact actor remains usable.
                                    try:
                                        if identity(actor,timeout)!=actual:raise RuntimeError('identity changed')
                                    except Exception:uncertain=True
                                receipt['completed_at']=now();executed.append((member.reference,spec.id))
                                reports[member.reference]['routine_evidence']=_public_receipts(receipts[member.reference]);reports[member.reference]['routine_checkpoints']=[{'id':r['id'],'result':deepcopy(r['result'])} for r in receipts[member.reference] if r.get('result') is not None];persist(member)
                    finally:owner._active=False;owner._state.active=False
                phase(session,login,'login')
                needed=any(all(next((r['status'] for r in receipts[m.reference] if r['id']==dep),None) in ('success','partial') or any(parent.id==dep and parent.required_permission=='root' for parent in m.routines) for dep in s.depends_on) and time.monotonic()<member_deadlines[m.reference] and s.required_permission=='root' and (not s.platforms or platform in s.platforms) and (set(s.properties).intersection(m.properties) or not json.loads(m.descriptor).get('inventory')) for m in members for s in m.routines)
                if needed and not uncertain and not cancelled() and time.monotonic()<deadline:
                    from root_access import root_actor
                    from access_check import ConsoleSession
                    evidence=aggregate.setdefault('root_access',{})
                    try:
                        with root_actor(session,config,host,min(timeout,deadline-time.monotonic()),evidence,authenticated_user=aggregate.get('login_identity',{}).get('username')) as privileged:
                            adapter=session if privileged is session else ConsoleSession(privileged)
                            root_identity=identity(adapter,timeout)
                            if root_identity['effective_uid']!=0:raise RuntimeError('root identity mismatch')
                            phase(adapter,root_identity,'root')
                    except RootUnavailableError:
                        aggregate['root_unavailable']=True
                    except Exception as exc:
                        uncertain=True;aggregate['execution_errors'].append({'stage':'root','error_type':type(exc).__name__})
                aggregate['restoration_verified']=identity(session,timeout)==login and not uncertain
                if not aggregate['restoration_verified']:aggregate['execution_errors'].append({'stage':'restoration','reason_code':'identity_restoration_failed'})
        except Exception as exc:
            aggregate['execution_errors'].append({'stage':'connection_or_identity','error_type':type(exc).__name__})
        aggregate['cleanup_verified']=aggregate.get('connected',False) and 'cleanup_error' not in aggregate
        for member in members:
            report=reports[member.reference];meta=json.loads(member.descriptor)
            present={r['id'] for r in receipts[member.reference]}
            for spec in member.routines:
                if spec.id in present or spec.platforms and platform is not None and platform not in spec.platforms:continue
                covered={p for r in receipts[member.reference] for p in r['properties']}
                fields=[p for p in spec.properties if p in member.properties and (platform is not None or p not in covered)]
                if not fields and meta.get('inventory'):continue
                stamp=now();receipts[member.reference].append({'id':spec.id,'host_id':host,'required_permission':spec.required_permission,'properties':fields,'actor':{'username':None,'effective_uid':None,'mode':'unverified'},'started_at':stamp,'completed_at':stamp,'status':'skipped','reason_code':'stop_requested' if cancelled() else 'budget_exhausted' if time.monotonic()>=member_deadlines[member.reference] else 'root_unavailable' if spec.required_permission=='root' and aggregate.get('root_unavailable') else 'scope_unavailable','result':None})
            finalized=False
            try:
                if engine_digest()!=expected_engine:raise ConfigError('routine engine changed during execution')
                value=validate_result(programs[member.reference][meta['runner']['finalizer']](deepcopy(receipts[member.reference])))
                if not receipts[member.reference]:value.update(status='unsupported',reason_code='platform_unsupported',message='No selected routine supports the detected platform.')
                if any(r['status'] not in ('success','partial') for r in receipts[member.reference]) and value['status']=='success':value['status']='partial'
                report.update(value);finalized=True
            except Exception as exc:report.update(status='failed',reason_code='finalization_failed',message='Recipe finalization failed.');report['execution_errors'].append({'stage':'finalizer','error_type':type(exc).__name__})
            for key in ('groups','probes','platform','property_definitions','definition_sha256','actor','identity_warning','implementation','reference_ips','trigger','note'):
                if key in report['data']:report[key]=deepcopy(report['data'][key])
            report['groups']=deepcopy(report['data'].get('groups',[]))
            if finalized:report.pop('routine_checkpoints',None);report['routine_execution_state']='completed'
            report['routine_evidence']=_public_receipts(receipts[member.reference]);report['completed_at']=now()
            if report['data'].get('groups'):
                report['data']['trigger']=trigger;report['data']['note']=note;report['data']['started_at']=began;report['data']['observed_at']=report['completed_at']
            if aggregate['execution_errors'] or not aggregate['cleanup_verified']:
                report['execution_status']=report['status'];report.update(status='failed',reason_code='meal_scope_failed',message='Shared identity/transport cleanup could not be verified.')
            report['connection_evidence']={k:deepcopy(aggregate.get(k)) for k in ('meal_run_id','restoration_verified','cleanup_verified','root_unavailable','execution_errors')}
            report['observed_at']=report['completed_at']
            persist(member)
            if save:
                path=output_dir/('recipe-run-'+report['source_observation_id']+'.json');report['result_path']=str(path)
                try:report['retention']=retain_general(root,report,meta,member.directory,saved_snapshot=report['retention_snapshot'])
                except Exception as exc:report['retention']={'status':'failed','reason_code':'retention_failed','error_type':type(exc).__name__}
                from .host_reference import update
                try:report['reference_ips_update']=update(root,report)
                except Exception:report['reference_ips_update']={'status':'failed','reason_code':'reference_ips_update_failed'}
                save_receipt(path,report)
            else:report['retention']={'status':'skipped','reason_code':'utility_no_store'};report['result_path']=None;report['reference_ips_update']={'status':'skipped','reason_code':'utility_no_store'}
            aggregate['children'].append({k:report[k] for k in ('recipe','status','reason_code','source_observation_id','result_path','retention','connection_evidence','reference_ips_update','routine_evidence','execution_errors','attention_policy') if k in report})
            if report['data'].get('reference_ips'):aggregate['reference_ips']=deepcopy(report['data']['reference_ips'])
            aggregate['groups'].extend(deepcopy(report['data'].get('groups',[])))
        policies={json.dumps(c['attention_policy'],sort_keys=True) for c in aggregate['children'] if 'attention_policy' in c}
        if len(policies)==1:aggregate['attention_policy']=json.loads(next(iter(policies)))
        aggregate['observed_at']=now();aggregate['status']='success' if all(r['status']=='success' for r in reports.values()) else 'partial' if any(r['status'] in ('success','partial') for r in reports.values()) else 'failed'
        aggregate['reason_code']='routine_meal_completed' if aggregate['status']=='success' else 'routine_meal_with_gaps';aggregate['execution_order']=[list(p) for p in executed]
        aggregate['retention']={'status':'stored' if all(c['retention']['status'] in ('stored','already_stored') for c in aggregate['children']) else 'partial' if any(c['retention']['status'] in ('stored','already_stored') for c in aggregate['children']) else 'skipped' if not save else 'failed','children':[c['retention'] for c in aggregate['children']]}
        if save:
            aggregate['result_path']=str(output_dir/('meal-run-'+identifier+'.json'));save_report(Path(aggregate['result_path']),aggregate)
            updates=[c.get('reference_ips_update',{}) for c in aggregate['children']]
            aggregate['reference_ips_update']={'status':'failed' if any(u.get('status')=='failed' for u in updates) else 'updated' if any(u.get('status')=='updated' for u in updates) else 'skipped'}
            if observation_run_id:aggregate['content_update']={'status':'skipped','reason_code':'deferred_to_observation_run'}
            else:finalize_content(root,aggregate)
            update_children_content(root,aggregate,aggregate['content_update'])
            save_receipt(Path(aggregate['result_path']),aggregate)
        else:aggregate['result_path']=None;aggregate['content_update']={'status':'skipped','reason_code':'utility_no_store'}
        if len(members)==1 and len(choices)==1 and json.loads(members[0].descriptor)['runner']['contract']==ROUTINES and choices[0]['reference']==members[0].reference:
            report=next(iter(reports.values()));report['content_update']=aggregate['content_update'];
            if save:save_receipt(Path(report['result_path']),report)
            return report
        return aggregate


def _public_receipts(rows):
    keys=('id','required_permission','status','reason_code','actor','started_at','completed_at','properties')
    return [{k:deepcopy(r[k]) for k in keys} for r in rows]


def update_children_content(root,aggregate,content):
    """Receipt-only update; collection data and raw business digest stay unchanged."""
    from recipe_runner import save_receipt
    base=Path(root).resolve()/'observations'
    for child in aggregate.get('children',[]):
        if not child.get('result_path'):continue
        path=Path(child['result_path'])
        if path.is_symlink() or path.parent.resolve()!=base or not path.is_file():raise ConfigError('child result escapes observations')
        raw=json.loads(path.read_text());raw['content_update']=deepcopy(content);save_receipt(path,raw)
