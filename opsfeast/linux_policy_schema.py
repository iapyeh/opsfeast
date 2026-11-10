"""Data-only Linux policy projection contracts 0.1.0."""
import copy

DATASETS = {
    'ssh-policy': ('ssh_policy',),
    'sudo-policy': ('sudo_policy',),
    'firewall-policy': ('nft_rules', 'iptables_rules', 'ip6tables_rules', 'firewalld_runtime', 'firewalld_permanent', 'ufw_runtime'),
    'time-sync': ('clock_state', 'chrony_state', 'chrony_sources', 'ntp_state', 'ntp_peers', 'timesyncd_state', 'time_configuration'),
    'logging-config': ('journald_configuration', 'journal_state', 'syslog_configuration', 'application_logs', 'log_rotation'),
}


def schema(kind, *, acquisition=True):
    if kind not in DATASETS: raise ValueError('unknown Linux policy kind')
    def obj(properties):
        return {'type': 'object', 'additionalProperties': False,
                'required': list(properties), 'properties': properties}
    text = {'type': 'string', 'maxLength': 4096}
    instant = {'type': 'string', 'format': 'date-time'}
    number = {'type': 'integer', 'minimum': 0}
    command = obj({'argv': {'type': 'array', 'maxItems': 32, 'items': text},
        'started_at': instant, 'completed_at': instant,
        'exitcode': {'type': ['integer', 'null']},
        'termination_status': {'enum': ['not_started', 'confirmed', 'unknown']},
        'reason_code': {'type': ['string', 'null'], 'maxLength': 128}})
    row = obj({'name': text, 'source': text, 'basis': {'enum': ['configured', 'effective', 'runtime', 'context']},
               'value': {'type': ['object', 'array', 'string', 'number', 'integer', 'boolean', 'null']}})
    datasets = {name: obj({'source': text, 'scope': text, 'observed_at': instant,
        'complete': {'type': 'boolean'}, 'items': {'type': 'array', 'maxItems': 5000, 'items': row},
        'attempted_count': number, 'unavailable_count': number,
        'reason_codes': {'type': 'array', 'maxItems': 64, 'uniqueItems': True,
            'items': {'type': 'string', 'maxLength': 128}},
        'commands': {'type': 'array', 'maxItems': 16, 'items': command}}) for name in DATASETS[kind]}
    properties = {'contract_version': {'const': '0.1.0'}, 'kind': {'const': kind}, 'platform': {'const': 'linux'},
        'started_at': instant, 'observed_at': instant, 'effective_uid': number, 'datasets': obj(datasets)}
    if acquisition:
        properties['acquisition'] = obj({'started_at': instant, 'completed_at': instant, 'method': text})
    return copy.deepcopy(obj(properties))
