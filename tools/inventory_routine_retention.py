"""Inventory-owned routine retention 0.1.0; preserve frozen historical validator."""
import copy
import re
from opsfeast import ConfigError
CONTRACT='inventory-routine-observations'
VERSION='0.1.0'
HISTORICAL_SHA256='6bdd921bb69f0dca0b3086ab78380f614bbb3cdaddea14e577111056b4739f8f'


def _historical():
    from retention_contracts import implementation,normalizer_digest
    declaration={'contract':'inventory-job-observations','version':'0.1.0'}
    digest=normalizer_digest(declaration)
    if digest!=HISTORICAL_SHA256:raise ConfigError('historical validation dependency changed')
    return implementation(('inventory-job-observations','0.1.0'),digest)


def validate(data):
    try:return _validate(data)
    except ConfigError:raise
    except (KeyError,TypeError,ValueError,AttributeError,RecursionError):raise ConfigError('invalid inventory routine data') from None


def _validate(data):
    if not isinstance(data,dict) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',data.get('recipe_id','')):raise ConfigError('invalid routine inventory identity')
    historical=copy.deepcopy(data)
    evidence=historical.pop('routine_evidence',None);meal=historical.pop('meal_run_id',None)
    connection=historical.pop('connection_evidence',None)
    policy=historical.pop('attention_policy',None)
    from inventory_attention import resolve
    if policy!=resolve(policy):raise ConfigError('inventory policy must be resolved')
    if not isinstance(connection,dict) or type(connection.get('restoration_verified')) is not bool or type(connection.get('cleanup_verified')) is not bool:raise ConfigError('connection cleanup evidence required')
    from observation_store import uuid_text,timestamp
    uuid_text(meal)
    if set(connection)!={'meal_run_id','restoration_verified','cleanup_verified','root_unavailable','execution_errors'} or connection['meal_run_id']!=meal or connection['root_unavailable'] is not None and type(connection['root_unavailable']) is not bool:raise ConfigError('invalid connection evidence')
    if not isinstance(connection['execution_errors'],list) or len(connection['execution_errors'])>128:raise ConfigError('invalid connection errors')
    for error in connection['execution_errors']:
        if not isinstance(error,dict) or set(error)-{'stage','error_type','reason_code'} or any(not isinstance(v,str) or not v or len(v)>256 or any(ord(c)<32 for c in v) for v in error.values()):raise ConfigError('invalid connection error')
    if not isinstance(evidence,list) or not 1<=len(evidence)<=64:raise ConfigError('routine evidence required')
    seen=set()
    for row in evidence:
        if not isinstance(row,dict) or set(row)!={'id','required_permission','status','reason_code','actor','started_at','completed_at','properties'} or row['id'] in seen:raise ConfigError('invalid routine receipt')
        seen.add(row['id'])
        if row['required_permission'] not in ('login','root') or row['status'] not in ('success','partial','failed','skipped','unsupported'):raise ConfigError('invalid routine state')
        actor=row['actor']
        from collection_evidence import validate as identity
        identity({'contract_version':'0.1.0','actor':actor,'probes':[]})
        if row['status'] in ('success','partial') and (type(actor['effective_uid']) is not int or row['required_permission']=='root' and actor['effective_uid']!=0):raise ConfigError('routine permission not verified')
        for key in ('started_at','completed_at'):timestamp(row[key])
        if row['completed_at']<row['started_at'] or not data['started_at']<=row['started_at']<=row['completed_at']<=data['observed_at']:raise ConfigError('routine times outside observation')
        if not isinstance(row['properties'],list) or any(p not in data['property_definitions'] for p in row['properties']):raise ConfigError('routine property binding invalid')
    for probe in historical['probes']:
        if 'capture_id' in probe:uuid_text(probe.pop('capture_id'))
    historical['recipe_id']='inventory-system';_historical()['validate'](historical)
    return data


def normalize(raw,source):
    if raw.get('routine_execution_state')!='completed':return None,'routine_execution_incomplete'
    merged={**raw,**raw.get('data',{})}
    merged['status']=raw['status']
    captures={p['id']:p.get('capture_id') for p in merged.get('probes',[])}
    merged=copy.deepcopy(merged)
    for probe in merged.get('probes',[]):probe.pop('capture_id',None)
    data,reason=_historical()['normalize'](merged,source)
    if data is None:return None,reason
    for probe in data['probes']:
        if captures.get(probe['id']):probe['capture_id']=captures[probe['id']]
    data['recipe_id']=raw['recipe']['id'];data['routine_evidence']=copy.deepcopy(raw['routine_evidence']);data['meal_run_id']=raw['meal_run_id'];data['connection_evidence']=copy.deepcopy(raw['connection_evidence']);data['attention_policy']=copy.deepcopy(raw['attention_policy'])
    validate(data)
    return data,None
