"""Bounded, noninteractive MySQL/MariaDB replication checks over the supplied Session."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re

VERSION = '0.1.0'


def configuration(values):
    """Validate every instance before executing any remote program; never echo inputs."""
    instances = values.get('instances')
    budget = values.get('command_timeout_seconds', 20)
    delay = values.get('max_delay_seconds', 60)
    if (not isinstance(instances, dict) or not instances or len(instances) > 32
            or type(budget) not in (int, float) or not math.isfinite(budget) or not 1 <= budget <= 120
            or type(delay) not in (int, float) or not math.isfinite(delay) or delay < 0):
        raise ValueError('invalid replication configuration')
    allowed = {'client', 'transport', 'socket', 'host', 'port', 'user', 'password',
               'option_file', 'expected_source', 'expected_sources', 'tls'}
    for name, options in instances.items():
        if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,63}', name):
            raise ValueError('invalid instance name')
        if not isinstance(options, dict) or set(options) - allowed:
            raise ValueError('invalid instance options')
        for key, value in options.items():
            if key in ('expected_sources', 'tls', 'port'):
                continue
            if not isinstance(value, str) or any(ord(c) < 32 for c in value):
                raise ValueError('invalid instance string')
        client = options.get('client', 'auto')
        if client not in ('auto', 'mysql', 'mariadb') and not client.startswith('/'):
            raise ValueError('client must be auto, mysql, mariadb or an absolute path')
        if options.get('transport', 'socket') not in ('socket', 'tcp'):
            raise ValueError('invalid transport')
        if 'port' in options and (type(options['port']) is not int or not 1 <= options['port'] <= 65535):
            raise ValueError('invalid database port')
        if options.get('transport', 'socket') == 'socket' and any(k in options for k in ('host', 'port', 'tls')):
            raise ValueError('TCP options cannot be used with socket transport')
        if options.get('transport') == 'tcp' and not options.get('host'):
            raise ValueError('TCP requires an explicit database host')
        if 'option_file' in options:
            if not options['option_file'].startswith('/') or any(k in options for k in ('user', 'password')):
                raise ValueError('option_file must be absolute and exclusive with user/password')
        elif not options.get('user') or 'password' not in options:
            raise ValueError('explicit user and password or option_file required')
        if 'socket' in options and not options['socket'].startswith('/'):
            raise ValueError('socket must be an absolute path')
        expected = options.get('expected_sources', {})
        if not isinstance(expected, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                or not v or any(ord(c) < 32 for c in k + v) for k, v in expected.items()):
            raise ValueError('invalid expected sources')
        tls = options.get('tls', {})
        if not isinstance(tls, dict) or set(tls) - {'ca'}:
            raise ValueError('TLS accepts only a CA path; certificate verification is required')
        if tls and (not isinstance(tls.get('ca'), str) or not tls['ca'].startswith('/')
                    or any(ord(c) < 32 for c in tls['ca'])):
            raise ValueError('invalid TLS CA path')
    return instances, budget, delay


def redact(value, secrets):
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, '[REDACTED]')
        return value
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, dict):
        return {redact(k, secrets): redact(v, secrets) for k, v in value.items()}
    return value


def execute(recipe):
    try:
        instances, budget, delay = configuration(recipe.vars)
    except ValueError:
        return {'status': 'failed', 'reason_code': 'invalid_configuration',
                'message': 'Invalid database instance configuration; see the recipe guide.', 'data': {}}
    probe = Path(__file__).with_name('probe.py').read_text()
    observed = []
    secrets = [item.get('password', '') for item in instances.values()]
    for name, options in sorted(instances.items()):
        # Only the reviewed helper is in argv. Credentials travel as exact stdin, not code or env.
        payload = json.dumps({'options': options, 'budget': min(budget, recipe.timeout), 'delay': delay})
        try:
            result = recipe.session.exec_command(['python3', '-c', probe], input=payload,
                                                 check=False, command_timeout=min(budget, recipe.timeout) + 5)
            if result.exitcode != 0 or result.stdout_truncated or result.stderr_truncated:
                item = {'health': 'unknown', 'reason': 'probe_failed', 'server': None, 'channels': [],
                        'probes': [{'operation': 'python3 -c <bundled probe.py>',
                                    'input': 'JSON instance settings; credentials redacted', 'sql': None,
                                    'exitcode': result.exitcode, 'stdout': None,
                                    'error': 'output_truncated' if result.stdout_truncated or result.stderr_truncated else 'helper_nonzero_exit'}],
                        'cleanup': 'unknown'}
            else:
                item = json.loads(result.stdout)
                if not isinstance(item, dict) or set(item) != {'health', 'reason', 'server', 'channels', 'probes', 'cleanup'}:
                    raise ValueError('invalid probe response')
        except Exception as exc:
            item = {'health': 'unknown', 'reason': 'probe_failed', 'server': None, 'channels': [],
                    'probes': [{'operation': 'python3 -c <bundled probe.py>', 'input': 'JSON instance settings; credentials redacted',
                                'sql': None, 'exitcode': None, 'stdout': None, 'error': type(exc).__name__}],
                    'cleanup': 'unknown'}
        item.update(instance=name, observed_at=datetime.now(timezone.utc).isoformat(timespec='microseconds'))
        observed.append(item)
    data = redact({'instances': observed, 'policy': {'max_delay_seconds': delay},
                   'source_verification': 'not_performed'}, secrets)
    healthy = all(i['health'] == 'healthy' and i['cleanup'] == 'confirmed' for i in observed)
    collected = any(i['server'] is not None for i in observed)
    return {'status': 'success' if healthy else 'partial' if collected else 'failed',
            'reason_code': 'replication_healthy' if healthy else 'replication_requires_attention',
            'message': 'Replica-side check only; source positions and data consistency were not verified.', 'data': data}
