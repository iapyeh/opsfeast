"""Portable Linux profile data definitions 0.1.0; no acquisition or registration."""
import copy


def schema(kind, *, acquisition=True):
    from .linux_policy_schema import DATASETS, schema as policy_schema
    if kind in DATASETS:
        return policy_schema(kind, acquisition=acquisition)
    if kind not in ('accounts', 'processes'):
        raise ValueError('unknown Linux profile kind')
    text = {'type': 'string', 'maxLength': 4096}
    number = {'type': 'integer', 'minimum': 0}
    nullable_number = {'type': ['integer', 'null'], 'minimum': 0}
    instant = {'type': 'string', 'format': 'date-time'}
    def obj(properties):
        return {'type': 'object', 'additionalProperties': False,
                'required': list(properties), 'properties': properties}
    users = obj({'name': text, 'uid': number, 'gid': number, 'home': text, 'shell': text,
                 'shell_hint': {'enum': ['shell_configured', 'noninteractive_shell', 'default_shell']}})
    groups = obj({'name': text, 'gid': number,
                  'members': {'type': 'array', 'maxItems': 5000, 'items': text}})
    processes = obj({
        'pid': number, 'start_ticks': number, 'ppid': number, 'name': text, 'state': text,
        'uid_real': number, 'uid_effective': number, 'gid_real': number, 'gid_effective': number,
        'threads': number, 'rss_bytes': nullable_number, 'virtual_bytes': nullable_number,
        'cpu_user_ticks': number, 'cpu_system_ticks': number,
        'executable': {'type': ['string', 'null'], 'maxLength': 4096},
        'executable_state': {'enum': ['observed', 'unavailable']},
        'executable_deleted': {'type': ['boolean', 'null']},
    })
    datasets = {}
    for name, items in ({'users': users, 'groups': groups} if kind == 'accounts' else {'processes': processes}).items():
        properties = {'source': text, 'scope': text, 'observed_at': instant,
                      'complete': {'type': 'boolean'},
                      'items': {'type': 'array', 'maxItems': 5000, 'items': items},
                      'reason_codes': {'type': 'array', 'maxItems': 32, 'uniqueItems': True,
                          'items': {'enum': ['item_or_time_limit', 'invalid_or_duplicate_rows',
                              'source_changed_during_read', 'permission_denied', 'source_missing',
                              'invalid_or_oversized_source', 'source_read_failed', 'boot_id_unavailable',
                              'process_disappeared', 'invalid_or_changed_process', 'process_read_failed',
                              'procfs_unavailable', 'output_size_limit']}},
                      'attempted_count': number, 'unavailable_count': number}
        if name == 'processes':
            properties['boot_id'] = {'type': ['string', 'null'], 'format': 'uuid'}
        datasets[name] = obj(properties)
    properties = {'contract_version': {'const': '0.1.0'}, 'kind': {'const': kind},
                  'platform': {'const': 'linux'}, 'started_at': instant, 'observed_at': instant,
                  'effective_uid': number, 'datasets': obj(datasets)}
    if acquisition:
        properties['acquisition'] = obj({'started_at': instant, 'completed_at': instant, 'method': text})
    return copy.deepcopy(obj(properties))
