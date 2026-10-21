"""Inventory job observations 0.1.0: schema-bound definitions, no candidate execution."""
import copy
import hashlib
import json
import math
from pathlib import Path
from uuid import UUID
from opsfeast import ConfigError

CONTRACT = 'inventory-job-observations'
VERSION = '0.1.0'


def definitions():
    # The registry binds this JSON through the retention schema digest.
    return json.loads(Path(__file__).with_name('job-retention.schema.json').read_text())['property_catalog']


def validate(data):
    from observation_store import timestamp
    catalog = definitions()
    required = {'contract_version','observation_id','source_id','recipe_id','recipe_version','observed_at',
                'started_at','status','host_id','trigger','note','definition_sha256','actor','groups','probes','identity_warning',
                'property_definitions','implementation','execution_errors'}
    if not isinstance(data,dict) or set(data) != required or data['contract_version'] != VERSION or data['recipe_id'] != 'inventory-system':
        raise ConfigError('invalid inventory job observation')
    if data['trigger'] not in ('manual','scheduled') or data['status'] not in ('success','partial','failed'):
        raise ConfigError('invalid inventory job trigger/status')
    from observation_store import uuid_text
    import re
    uuid_text(data['source_id'])
    if not isinstance(data['observation_id'],str) or not re.fullmatch(re.escape(data['source_id'])+r':[0-9a-f]{64}',data['observation_id']):
        raise ConfigError('invalid inventory observation ID')
    for key in ('host_id','recipe_version','identity_warning'):
        if not isinstance(data[key],str) or not data[key] or '\x00' in data[key]:
            raise ConfigError('invalid inventory metadata')
    if not isinstance(data['note'],str) or len(data['note']) > 4096 or '\x00' in data['note']:
        raise ConfigError('invalid inventory note')
    canonical = lambda v: json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    if data['definition_sha256'] != hashlib.sha256(canonical(catalog).encode()).hexdigest():
        raise ConfigError('inventory definitions differ from registered schema')
    for key in ('started_at','observed_at'):
        if timestamp(data[key]) != data[key]:
            raise ConfigError('inventory time must be canonical UTC')
    if data['observed_at'] < data['started_at']:
        raise ConfigError('inventory completion precedes start')
    if not isinstance(data['actor'],dict) or set(data['actor']) != {'username','effective_uid','mode'}:
        raise ConfigError('invalid inventory actor')
    from collection_evidence import validate as actor_validate
    actor_validate({'contract_version':'0.1.0','actor':data['actor'],'probes':[]})
    if not isinstance(data['probes'],list) or len(data['probes']) > 256:
        raise ConfigError('invalid inventory probe list')
    if not isinstance(data['execution_errors'],list) or any(not isinstance(e,dict) or set(e)-{'stage','error_type','reason_code'} for e in data['execution_errors']):
        raise ConfigError('invalid acquisition error evidence')
    sources = {}
    for probe in data['probes']:
        if not isinstance(probe,dict) or not {'id','started_at','observed_at','status'}.issubset(probe) or probe['id'] in sources:
            raise ConfigError('invalid inventory probe')
        for field in ('started_at','observed_at'):
            if timestamp(probe[field]) != probe[field] or not data['started_at'] <= probe[field] <= data['observed_at']:
                raise ConfigError('invalid probe time')
        if probe['observed_at'] < probe['started_at']:
            raise ConfigError('probe completion precedes start')
        # Preserve bounded original command streams alongside producer metadata.
        allowed = {'id','command','started_at','observed_at','status','reason_code','exitcode','error_type','window_started_at','input_source_ids','section','field','stdout','stderr','stdout_truncated','stderr_truncated'}
        if set(probe)-allowed:
            raise ConfigError('unexpected inventory probe fields')
        for stream in ('stdout','stderr'):
            if stream in probe and probe[stream] is not None and (not isinstance(probe[stream],str) or len(probe[stream].encode())>262144):
                raise ConfigError('invalid bounded command output')
            if stream+'_truncated' in probe and type(probe[stream+'_truncated']) is not bool:
                raise ConfigError('invalid command truncation flag')
        sources[probe['id']] = probe
    for probe in sources.values():
        if 'input_source_ids' in probe and (not isinstance(probe['input_source_ids'],list) or any(s not in sources or s==probe['id'] for s in probe['input_source_ids'])):
            raise ConfigError('invalid derived-probe input sources')
    if not isinstance(data['groups'],list) or not data['groups'] or len(data['groups']) > len(catalog['jobs']):
        raise ConfigError('invalid inventory groups')
    seen = set()
    definitions_seen = set()
    for group in data['groups']:
        if not isinstance(group,dict) or set(group) != {'id','title','started_at','observed_at','status','samples','coverage'} or group['id'] not in catalog['jobs'] or group['id'] in seen:
            raise ConfigError('invalid inventory job group')
        seen.add(group['id'])
        if group['status'] not in ('success','partial','failed'):
            raise ConfigError('invalid inventory group status')
        if group['title'] != catalog['jobs'][group['id']]['title']:
            raise ConfigError('group title differs from job definition')
        for key in ('started_at','observed_at'):
            if timestamp(group[key]) != group[key] or not data['started_at'] <= group[key] <= data['observed_at']:
                raise ConfigError('invalid group time')
        if not isinstance(group['coverage'],list) or not isinstance(group['samples'],list) or len(group['samples']) > 100000:
            raise ConfigError('invalid group samples/coverage')
        covered = set()
        for item in group['coverage']:
            if not isinstance(item,dict) or set(item) != {'property','complete','source_id','observed_at'} or type(item['complete']) is not bool:
                raise ConfigError('invalid inventory coverage')
            name = item['property']
            if name not in catalog['properties'] or catalog['properties'][name]['job'] != group['id'] or name in covered or item['source_id'] not in sources:
                raise ConfigError('invalid coverage property/source')
            covered.add(name)
            definitions_seen.add(name)
            if item['observed_at'] != sources[item['source_id']]['observed_at']:
                raise ConfigError('coverage time differs from source')
        samples_seen = set()
        for sample in group['samples']:
            if not isinstance(sample,dict) or set(sample) != {'property','keys','value','status','reason_code','observed_at','source_id'} or sample['property'] not in covered:
                raise ConfigError('invalid inventory sample')
            spec = catalog['properties'][sample['property']]
            if not isinstance(sample['keys'],dict) or set(sample['keys'])-set(spec['keys']):
                raise ConfigError('invalid sample entity keys')
            if any(not isinstance(v,(str,int)) or isinstance(v,bool) for v in sample['keys'].values()):
                raise ConfigError('invalid entity key value')
            token = canonical([sample['property'],sample['keys']])
            if token in samples_seen:
                raise ConfigError('duplicate property instance')
            samples_seen.add(token)
            if sample['source_id'] not in sources or sample['observed_at'] != sources[sample['source_id']]['observed_at']:
                raise ConfigError('sample time/source mismatch')
            value = sample['value']
            if sample['status'] == 'success':
                from inventory_property_types import matches
                valid = matches(spec,value)
                if not valid or sample['reason_code'] is not None:
                    raise ConfigError('inventory value differs from property definition')
                if spec['unit']=='percent' and not 0 <= value <= 100:
                    raise ConfigError('invalid percentage')
                if spec['keys'] and not sample['keys']:
                    raise ConfigError('successful table sample requires entity keys')
                if sample['property']=='network.interfaces.state' and value not in ('up','down','testing','unknown','dormant','not-present','lower-layer-down'):
                    raise ConfigError('invalid standard interface state')
            elif sample['status'] != 'unavailable' or value is not None or not sample['reason_code']:
                raise ConfigError('failed samples require null and a reason')
        expected = ('success' if group['coverage'] and all(c['complete'] for c in group['coverage']) else
                    'partial' if any(s['status']=='success' for s in group['samples']) else 'failed')
        if group['status'] != expected:
            raise ConfigError('group status contradicts coverage/samples')
        for item in group['coverage']:
            measured = [s for s in group['samples'] if s['property']==item['property']]
            if item['complete'] and (any(s['status']!='success' for s in measured) or
                                     not measured and not catalog['properties'][item['property']]['column']):
                raise ConfigError('complete coverage contradicts property samples')
    if data['property_definitions'] != {name:catalog['properties'][name] for name in definitions_seen}:
        raise ConfigError('saved property definitions differ from registered schema')
    implementation = data['implementation']
    if not isinstance(implementation,dict) or set(implementation) != {'entrypoint','version','platform','sha256'} or implementation['entrypoint']!='jobs.py' or implementation['version']!='0.1.0' or not re.fullmatch('[a-f0-9]{64}',implementation['sha256']):
        raise ConfigError('invalid collector implementation evidence')
    json.dumps(data,allow_nan=False)
    return data


def normalize(raw, source):
    if raw.get('evidence_kind') not in ('local','ssh'):
        return None, 'nonoperational_evidence'
    if not raw.get('groups'):
        return None, 'no_job_observations'
    from observation_store import uuid_text, timestamp
    from retention_replay import source_identity
    uuid_text(source)
    identifier = source_identity(raw)
    UUID(identifier)
    data = {key:copy.deepcopy(raw[key]) for key in ('host_id','status','trigger','note','definition_sha256','actor','groups','probes','identity_warning','property_definitions','implementation','execution_errors')}
    data.update(contract_version=VERSION, observation_id=source+':'+hashlib.sha256(identifier.encode()).hexdigest(),
                source_id=source, recipe_id='inventory-system', recipe_version=raw['recipe']['version'],
                started_at=timestamp(raw['started_at']), observed_at=timestamp(raw['observed_at']))
    validate(data)
    return data, None
