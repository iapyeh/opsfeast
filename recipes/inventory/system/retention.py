"""Inventory-observations 0.1.0 normalization owned by inventory/system.

Pure local transformation: no sessions, filesystem reads, renderer or storage writes.
The platform invokes this registered bundled contract, never a candidate entrypoint.
"""
import hashlib
from opsfeast import ConfigError

VERSION = '0.1.0'
CONTRACT = 'inventory-observations'
FIELDS = ('hostname', 'platform', 'system_name', 'system_version', 'kernel_name', 'kernel_release', 'architecture')


def normalize(raw, source):
    """Produce the declared retained inventory dataset from saved collection evidence."""
    from observation_store import canonical, timestamp, nonempty, fallback_key
    from recipe_dispatch import validate_observations
    if not isinstance(raw, dict):
        raise ConfigError('raw result must be an object')
    if raw.get('status') in ('failed', 'skipped', 'unsupported'):
        return None, 'result_not_retained'
    if raw.get('evidence_kind') not in ('local', 'ssh'):
        return None, 'non_operational_evidence'
    receipt_id = (raw.get('retention') or {}).get('observation_id')
    if receipt_id is not None and not receipt_id.startswith(source + ':'):
        raise ConfigError('raw result belongs to another source; exchange structured data instead')
    if raw.get('schema_version') != '0.2.0' or raw.get('recipe', {}).get('id') != 'inventory-system':
        raise ConfigError('no retained adapter for this recipe/result contract')
    if raw.get('status') not in ('success', 'partial') or raw.get('execution_errors'):
        raise ConfigError('inconsistent raw result status')
    validate_observations(raw)
    states = [item['status'] for item in raw['observations'].values()]
    if raw['status'] == 'success' and any(state != 'success' for state in states) or raw['status'] == 'partial' and ('success' not in states or all(state == 'success' for state in states)):
        raise ConfigError('raw status contradicts observation states')
    host = nonempty(raw.get('host_id'), 'host_id')
    started, finished = timestamp(raw.get('started_at')), timestamp(raw.get('finished_at'))
    if finished < started:
        raise ConfigError('raw completion precedes start')
    observations = {field: {'value': item['value'], 'status': item['status'],
                            'observed_at': timestamp(item['observed_at']) if item['observed_at'] else None}
                    for field, item in raw['observations'].items()}
    identity = raw.get('identity', {})
    method = identity.get('method')
    key = identity.get('os_instance_key')
    derived = (identity.get('schema_version') == VERSION and method == 'linux-machine-id-hmac-sha256-v1'
               and identity.get('quality') == 'machine-derived' and isinstance(key, str)
               and len(key) == 70 and key.startswith('linux:')
               and all(c in '0123456789abcdef' for c in key[6:]))
    assigned = identity.get('identity_key')
    user_assigned = (identity.get('schema_version') == VERSION and method == 'configured-identity-key-v1'
                     and identity.get('quality') == 'user-assigned' and isinstance(assigned, str))
    if method == 'configured-identity-key-v1' and not user_assigned:
        raise ConfigError('invalid configured identity contract')
    if user_assigned:
        key = 'user:' + hashlib.sha256(assigned.encode()).hexdigest()
        if identity.get('os_instance_key') != key:
            raise ConfigError('configured identity evidence/key mismatch')
    evidence = []
    for item in identity.get('evidence', []):
        if item.get('scope') == 'device' and item.get('status') == 'success' and item.get('kind') in ('system-serial', 'enclosure-serial', 'hardware-uuid'):
            evidence.append({'kind': item['kind'], 'scope': 'device', 'value': nonempty(item.get('value'), 'identifier'),
                             'observed_at': timestamp(item.get('observed_at'))})
    identity_raw = {key: value for key, value in raw.items() if key not in ('retention', 'content_update')}
    if 'source_observation_id' in raw:
        from retention_replay import source_identity
        identity_content = source_identity(raw)
    else:
        identity_content = canonical(identity_raw)
    record = {'contract_version': VERSION, 'observation_id': source + ':' + hashlib.sha256(identity_content.encode()).hexdigest(),
              'source_id': source, 'host_id': host, 'host_key': key if derived or user_assigned else fallback_key(source, host),
              'identity_method': method if derived or user_assigned else 'source-host-id',
              'identity_quality': 'user-assigned' if user_assigned else 'machine-derived' if derived else 'fallback',
              'identity_evidence': evidence,
              'identity_warning': ('User-assigned key is an assertion, not machine verification; coordinate names and change after reinstall/replacement.' if user_assigned else 'Machine-derived Linux ID may be duplicated by clones or preserved across reinstallations.' if derived else 'Source-scoped fallback cannot establish cross-installation identity or replacement.'),
              'recipe_id': 'inventory-system', 'recipe_version': nonempty(raw['recipe'].get('recipe_version', raw['recipe'].get('version')), 'recipe_version'),
              'raw_schema_version': '0.2.0', 'started_at': started, 'observed_at': finished,
              'evidence_kind': raw['evidence_kind'], 'status': raw['status'], 'observations': observations}
    if 'inventory' in raw:
        from inventory_values import validate_inventory
        if raw.get('inventory_contract_version') != '0.1.0':
            raise ConfigError('unsupported inventory values contract')
        record.update(inventory_contract_version='0.1.0', inventory=validate_inventory(raw['inventory']))
        access = raw.get('access', {})
        record['collection_scope'] = {'mode': access.get('mode', 'unverified'),
                                      'effective_uid': access.get('actual_identity', {}).get('effective_uid')}
    if user_assigned:
        record['identity_key'] = assigned
    metadata = raw.get('host_metadata', {})
    if not isinstance(metadata, dict) or set(metadata) - {'label', 'description'}:
        raise ConfigError('invalid host display metadata')
    record.update(metadata)
    validate(record)
    return record, None

def validate(record):
    from observation_store import timestamp, nonempty, uuid_text, fallback_key
    from recipe_dispatch import validate_observations
    required = {'contract_version', 'observation_id', 'source_id', 'host_id', 'host_key', 'identity_method', 'identity_quality', 'identity_evidence', 'identity_warning', 'recipe_id', 'recipe_version', 'raw_schema_version', 'started_at', 'observed_at', 'evidence_kind', 'status', 'observations'}
    if not isinstance(record, dict) or not required.issubset(record) or set(record) - required - {'identity_key', 'label', 'description', 'inventory_contract_version', 'inventory', 'collection_scope'}:
        raise ConfigError('invalid retained record fields')
    extension = {'inventory_contract_version', 'inventory', 'collection_scope'}
    if extension & set(record):
        from inventory_values import validate_inventory
        if not extension.issubset(record) or record['inventory_contract_version'] != '0.1.0':
            raise ConfigError('invalid inventory extension')
        validate_inventory(record['inventory'])
        scope = record['collection_scope']
        if not isinstance(scope, dict) or set(scope) != {'mode', 'effective_uid'} or scope['mode'] not in ('root', 'user', 'fallback_user', 'unverified') or scope['effective_uid'] is not None and (type(scope['effective_uid']) is not int or scope['effective_uid'] < 0):
            raise ConfigError('invalid collection scope')
    for name in ('label', 'description'):
        if name in record and (not isinstance(record[name], str) or '\x00' in record[name]):
            raise ConfigError('invalid host display metadata')
    source = uuid_text(record['source_id'])
    for name in ('host_id', 'host_key', 'recipe_version', 'identity_warning'):
        nonempty(record[name], name)
    digest = record['observation_id']
    if not isinstance(digest, str) or not digest.startswith(source + ':') or len(digest) != 101 or any(c not in '0123456789abcdef' for c in digest[37:]):
        raise ConfigError('invalid observation ID')
    if record['contract_version'] != VERSION or record['recipe_id'] != 'inventory-system' or record['raw_schema_version'] != '0.2.0' or record['evidence_kind'] not in ('local', 'ssh') or record['status'] not in ('success', 'partial'):
        raise ConfigError('unsupported retained contract or state')
    for name in ('started_at', 'observed_at'):
        if timestamp(record[name]) != record[name]:
            raise ConfigError('retained timestamps must use canonical UTC')
    if record['observed_at'] < record['started_at']:
        raise ConfigError('completion precedes start')
    if record['identity_quality'] == 'user-assigned':
        assigned = nonempty(record.get('identity_key'), 'identity_key')
        if assigned != assigned.strip() or any(ord(char) < 32 for char in assigned):
            raise ConfigError('invalid user-assigned identity key')
        if record['identity_method'] != 'configured-identity-key-v1' or record['host_key'] != 'user:' + hashlib.sha256(assigned.encode()).hexdigest():
            raise ConfigError('invalid user-assigned identity')
    elif record['identity_quality'] == 'fallback':
        if record['identity_method'] != 'source-host-id' or record['host_key'] != fallback_key(source, record['host_id']):
            raise ConfigError('invalid fallback identity')
    elif record['identity_quality'] == 'machine-derived':
        key = record['host_key']
        if record['identity_method'] != 'linux-machine-id-hmac-sha256-v1' or not key.startswith('linux:') or len(key) != 70 or any(c not in '0123456789abcdef' for c in key[6:]):
            raise ConfigError('invalid machine-derived identity')
    else:
        raise ConfigError('unsupported identity quality')
    if record['identity_quality'] != 'user-assigned' and 'identity_key' in record:
        raise ConfigError('identity_key requires user-assigned identity')
    if not isinstance(record['identity_evidence'], list):
        raise ConfigError('identity evidence must be a list')
    for item in record['identity_evidence']:
        if not isinstance(item, dict) or set(item) != {'kind', 'scope', 'value', 'observed_at'} or item['scope'] != 'device' or item['kind'] not in ('system-serial', 'enclosure-serial', 'hardware-uuid'):
            raise ConfigError('invalid device evidence')
        nonempty(item['value'], 'device identifier')
        if timestamp(item['observed_at']) != item['observed_at']:
            raise ConfigError('invalid evidence timestamp')
    observations = record['observations']
    if not isinstance(observations, dict) or set(observations) != set(FIELDS):
        raise ConfigError('invalid retained observations')
    for item in observations.values():
        if not isinstance(item, dict) or set(item) != {'value', 'status', 'observed_at'}:
            raise ConfigError('invalid retained observation fields')
        if item['observed_at'] is not None and timestamp(item['observed_at']) != item['observed_at']:
            raise ConfigError('invalid field timestamp')
    validate_observations({'observations': {name: dict(item, source_ids=[], error=None) for name, item in observations.items()}})
    states = [item['status'] for item in observations.values()]
    if any(item['status'] == 'success' and item['observed_at'] is None for item in observations.values()):
        raise ConfigError('successful observation requires time')
    if record['status'] == 'success' and any(state != 'success' for state in states) or record['status'] == 'partial' and ('success' not in states or all(state == 'success' for state in states)):
        raise ConfigError('retained status contradicts observations')
