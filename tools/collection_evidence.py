"""Local collection evidence 0.1.0; never retain credentials or command output."""
import shlex
from opsfeast import ConfigError

VERSION = '0.1.0'
MODES = ('root', 'user', 'fallback_user', 'unverified')
STATUSES = ('success', 'failed', 'unavailable', 'truncated', 'not_attempted', 'not_supported',
            'unsupported', 'permission_denied', 'timeout', 'command_failed', 'parsing_failed')


def validate(value):
    if not isinstance(value, dict) or set(value) != {'contract_version', 'actor', 'probes'} or value['contract_version'] != VERSION:
        raise ConfigError('invalid collection evidence')
    actor = value['actor']
    if not isinstance(actor, dict) or set(actor) != {'username', 'effective_uid', 'mode'} or actor['mode'] not in MODES:
        raise ConfigError('invalid collection actor')
    name, uid = actor['username'], actor['effective_uid']
    if name is not None and (not isinstance(name, str) or not name or len(name) > 256 or any(ord(c) < 32 for c in name)):
        raise ConfigError('invalid collection account')
    if uid is not None and (type(uid) is not int or uid < 0):
        raise ConfigError('invalid collection UID')
    if actor['mode'] == 'root' and uid != 0:
        raise ConfigError('root collection requires verified UID 0')
    if not isinstance(value['probes'], list) or len(value['probes']) > 256:
        raise ConfigError('invalid collection probe list')
    keys = {'section', 'field', 'status', 'command', 'reason_code', 'exitcode', 'error_type', 'observed_at'}
    for item in value['probes']:
        if not isinstance(item, dict) or set(item) != keys or item['status'] not in STATUSES:
            raise ConfigError('invalid collection probe')
        for key in ('section', 'field'):
            if not isinstance(item[key], str) or not item[key] or len(item[key]) > 128:
                raise ConfigError('invalid collection field')
        for key in ('command', 'reason_code', 'error_type', 'observed_at'):
            if item[key] is not None and (not isinstance(item[key], str) or len(item[key]) > 8192 or '\x00' in item[key]):
                raise ConfigError('invalid collection source')
        if item['exitcode'] is not None and (type(item['exitcode']) is not int):
            raise ConfigError('invalid collection exit code')
        if item['observed_at'] is not None:
            from observation_store import timestamp
            timestamp(item['observed_at'])
    return value


def capture(report):
    """Explicit producer opt-in: project verified actor and bounded query metadata only."""
    access = report.get('access', {})
    actual = access.get('actual_identity') or {}
    actor = {'username': actual.get('username'), 'effective_uid': actual.get('effective_uid'),
             'mode': access.get('mode', 'unverified')}
    probes = []
    allowed = ('section', 'field', 'status', 'command', 'reason_code', 'exitcode', 'error_type', 'observed_at')
    for source in report.get('collection_process', {}).get('probes', []):
        probes.append({key: source.get(key) for key in allowed})
    sources = {source['id']: source for source in report.get('sources', [])}
    for field, item in report.get('observations', {}).items():
        for source_id in item.get('source_ids', []):
            source = sources.get(source_id)
            if not source or source.get('kind') != 'command':
                continue
            command = source.get('command')
            if isinstance(command, list):
                command = shlex.join(command)
            probes.append({'section': 'system', 'field': field, 'status': item['status'],
                           'command': command, 'reason_code': (item.get('error') or {}).get('code'),
                           'exitcode': source.get('exitcode'),
                           'error_type': (source.get('error') or {}).get('type'),
                           'observed_at': item.get('observed_at')})
    return validate({'contract_version': VERSION, 'actor': actor, 'probes': probes})
