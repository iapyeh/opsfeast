"""Creator-owned mysql-replication 0.1.0 normalization; never load collection code."""
import copy
import hashlib
import json
import math
from pathlib import Path
from opsfeast import ConfigError

CONTRACT = 'mysql-replication'
VERSION = '0.1.0'


def shape(value, schema, root):
    """Validate this contract's deliberately small schema vocabulary without new dependencies."""
    if '$ref' in schema:
        return shape(value, root['$defs'][schema['$ref'].split('/')[-1]], root)
    if 'oneOf' in schema:
        matches = 0
        for candidate in schema['oneOf']:
            try: shape(value, candidate, root)
            except ConfigError: continue
            matches += 1
        if matches != 1: raise ConfigError('invalid replication retained union')
        return
    tests = {'object': isinstance(value, dict), 'array': isinstance(value, list),
             'string': isinstance(value, str), 'null': value is None,
             'integer': type(value) is int,
             'number': type(value) in (int, float) and math.isfinite(value)}
    kinds = schema.get('type', list(tests))
    kinds = [kinds] if isinstance(kinds, str) else kinds
    if not any(tests[k] for k in kinds): raise ConfigError('invalid replication retained type')
    if 'const' in schema and value != schema['const']: raise ConfigError('invalid replication contract constant')
    if 'enum' in schema and value not in schema['enum']: raise ConfigError('invalid replication state')
    if isinstance(value, dict):
        properties = schema.get('properties', {})
        if set(schema.get('required', ())) - set(value) or (schema.get('additionalProperties') is False and set(value) - set(properties)):
            raise ConfigError('invalid replication retained fields')
        for key, item in value.items():
            if key in properties: shape(item, properties[key], root)
    elif isinstance(value, list):
        if len(value) < schema.get('minItems', 0): raise ConfigError('empty replication instances')
        for item in value: shape(item, schema['items'], root)
    elif isinstance(value, str):
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', 2097152):
            raise ConfigError('invalid replication text length')
    elif value is not None and 'minimum' in schema and value < schema['minimum']:
        raise ConfigError('negative replication measurement')


def validate(data):
    from observation_store import timestamp, uuid_text
    schema = json.loads(Path(__file__).with_name('retention.schema.json').read_text())
    shape(data, schema, schema)
    uuid_text(data['source_id'])
    for instant in [data['observed_at'], *(i['observed_at'] for i in data['instances'])]:
        if timestamp(instant) != instant: raise ConfigError('replication timestamps must be canonical UTC')
    if len({i['instance'] for i in data['instances']}) != len(data['instances']):
        raise ConfigError('duplicate database instance')
    if data['status'] == 'success' and any(i['health'] != 'healthy' or i['cleanup'] != 'confirmed' for i in data['instances']):
        raise ConfigError('successful replication observation requires healthy instances')
    for instance in data['instances']:
        if len({c['channel'] for c in instance['channels']}) != len(instance['channels']):
            raise ConfigError('duplicate replication channel')
        if instance['health'] == 'healthy' and (instance['server'] is None or not instance['channels'] or instance['cleanup'] != 'confirmed'
                or any(c['health'] != 'healthy' for c in instance['channels'])):
            raise ConfigError('inconsistent replication health')
        for channel in instance['channels']:
            if channel['health'] == 'healthy' and (channel['io_running'] != 'Yes' or channel['sql_running'] != 'Yes'
                    or not channel['source_host']
                    or channel['last_io_errno'] != 0 or channel['last_sql_errno'] != 0
                    or channel['delay_seconds'] is None or channel['delay_seconds'] > data['policy']['max_delay_seconds']
                    or channel['reasons'] or channel['error_text']
                    or channel['expected_source'] is not None and channel['source_host'] != channel['expected_source']):
                raise ConfigError('unverified replication health')
    json.dumps(data, allow_nan=False)
    return data


def normalize(raw, source):
    from observation_store import timestamp, uuid_text
    from retention_replay import source_identity
    if raw.get('evidence_kind') not in ('local', 'ssh') or raw.get('status') not in ('success', 'partial'):
        return None, 'nonoperational_or_failed_result'
    uuid_text(source)
    payload = raw.get('data', {})
    if set(payload) != {'instances', 'policy', 'source_verification'}:
        raise ConfigError('invalid replication result data')
    data = copy.deepcopy(payload)
    data.update(contract_version=VERSION, source_id=source,
                observation_id=source + ':' + hashlib.sha256(source_identity(raw).encode()).hexdigest(),
                recipe_id=raw['recipe']['id'], recipe_version=raw['recipe'].get('version', raw['recipe'].get('recipe_version')),
                observed_at=timestamp(raw['completed_at']), status=raw['status'])
    validate(data)
    return data, None
