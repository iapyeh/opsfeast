"""Linux profiling acquisition service 0.1.0, using a supplied Core Recipe scope."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from . import ConfigError
from .data_contract import validate

VERSION = '0.1.0'


def _command_evidence(result=None, error=None):
    termination = getattr(result, 'termination_status', None)
    exitcode = getattr(result, 'exitcode', None)
    return {'error_type': type(error).__name__ if error is not None else None,
            'exitcode': exitcode if type(exitcode) is int else None,
            'termination_status': termination if termination in ('confirmed', 'unknown') else 'unknown',
            'stdout_truncated': bool(getattr(result, 'stdout_truncated', False)),
            'stderr_truncated': bool(getattr(result, 'stderr_truncated', False))}


def collect(recipe, kind):
    """Collect one reviewed Linux inventory/policy kind without implicit elevation.

    Returned data is final portable retention data; raw command streams/errors are
    not stored. Transport/no-valid-payload failures remain raw failures, not empty
    successful observations. The caller owns targets, session and cleanup.
    """
    from .linux_policy_schema import DATASETS
    policy = kind in DATASETS
    if kind not in ('accounts', 'processes') and not policy:
        raise ConfigError('unknown Linux profile kind')
    limit = recipe.vars.get('max_items', 1000)
    timeout = recipe.vars.get('command_timeout_seconds', 20)
    if (type(limit) is not int or not 1 <= limit <= 5000 or type(timeout) not in (int, float)
            or not math.isfinite(timeout) or not 1 <= timeout <= 120):
        raise ConfigError('Linux profile requires max_items 1-5000 and command_timeout_seconds 1-120')
    timeout = min(timeout, recipe.timeout)
    script = Path(__file__).with_name('linux_policy_probe.py' if policy else 'linux_profile_probe.py').read_text()
    options = recipe.vars.get('ssh_context', {}) if kind == 'ssh-policy' else {}
    if kind == 'ssh-policy':
        from .linux_policy_probe import context
        try: context(options)
        except (ValueError, TypeError): raise ConfigError('ssh_context must contain user, host, addr, laddr and integer lport, or be empty') from None
    argv = ['python3', '-B', '-', kind, str(limit), str(timeout * .8)]
    if policy: argv.append(json.dumps(options, separators=(',', ':')))
    started = datetime.now(timezone.utc).isoformat(timespec='microseconds')
    try:
        result = recipe.session.exec_command(argv,
            input=script, check=False, command_timeout=timeout)
    except Exception as error:
        return {'status': 'failed', 'reason_code': 'linux_profile_acquisition_failed',
                'message': 'Profile command failed; command termination and runner cleanup are separate evidence.',
                'data': {'command_evidence': _command_evidence(getattr(error, 'result', None), error)}}
    finished = datetime.now(timezone.utc).isoformat(timespec='microseconds')
    if result.exitcode != 0 or result.stdout_truncated or result.stderr_truncated:
        return {'status': 'failed', 'reason_code': 'linux_profile_command_failed_or_truncated',
                'message': 'Profile command did not return a complete payload.',
                'data': {'command_evidence': _command_evidence(result)}}
    try:
        data = json.loads(result.stdout)
        if not isinstance(data, dict): raise ValueError('invalid_payload')
        if data.get('platform') != 'linux':
            if set(data) != {'platform'} or not isinstance(data['platform'], str):
                raise ValueError('invalid_platform_response')
            return {'status': 'unsupported', 'reason_code': 'linux_required',
                    'message': 'This collector requires Linux.', 'data': {}}
        from .linux_profile_schema import schema
        validate(data, schema(kind, acquisition=False))
        if data['kind'] != kind: raise ValueError('wrong_probe_kind')
        data['acquisition'] = {'started_at': started, 'completed_at': finished,
                               'method': 'SSHScript exec_command argv/stdin; fixed Python stdlib probe'}
        validate(data, schema(kind))
    except (ValueError, TypeError, KeyError):
        return {'status': 'failed', 'reason_code': 'linux_profile_invalid_payload',
                'message': 'Profile response failed the declared data contract.', 'data': {}}
    status = 'success' if all(d['complete'] for d in data['datasets'].values()) else 'partial'
    return {'status': status, 'reason_code': 'linux_profile_' + status,
            'message': 'Collected scoped Linux profile evidence; inspect per-dataset gaps.', 'data': data}
