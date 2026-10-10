"""Linux system inventory; only fixed read-only argv, no credentials or connections."""
from datetime import datetime, timezone
import shlex

VERSION = '0.1.0'
FIELDS = ('hostname', 'platform', 'system_name', 'system_version',
          'kernel_name', 'kernel_release', 'architecture')


def now():
    return datetime.now(timezone.utc).isoformat()


def new_report(host_id, evidence_kind):
    return {
        'schema_version': '0.1.0', 'recipe': {'id': 'inventory-system', 'version': VERSION},
        'host_id': host_id, 'evidence_kind': evidence_kind, 'started_at': now(),
        'finished_at': None, 'status': 'failed',
        'observations': {key: {'value': None, 'status': 'not_attempted', 'observed_at': None,
                              'source_ids': [], 'error': {'code': 'not_attempted'}} for key in FIELDS},
        'sources': [], 'execution_errors': [],
    }


def finish(report):
    states = [item['status'] for item in report['observations'].values()]
    if report['execution_errors']:
        status = 'failed'
    elif report['observations']['platform']['status'] == 'unsupported':
        status = 'unsupported'
    elif all(state == 'success' for state in states):
        status = 'success'
    elif 'success' in states:
        status = 'partial'
    else:
        status = 'failed'
    report.update(status=status, finished_at=now())
    return report


def observe(report, key, value, status, sources, code=None):
    report['observations'][key] = {
        'value': value, 'status': status, 'observed_at': now(),
        'source_ids': sources, 'error': {'code': code or status} if status != 'success' else None,
    }


def probe(session, report, source_id, argv, timeout):
    source = {'id': source_id, 'kind': 'command', 'command': argv,
              'started_at': now(), 'observed_at': None,
              'stdout': '', 'stderr': '', 'exitcode': None, 'error': None}
    report['sources'].append(source)
    try:
        result = session.exec_command(argv, check=False, command_timeout=timeout)
        source.update(stdout=result.stdout, stderr=result.stderr, exitcode=result.exitcode)
        state = 'success' if result.exitcode == 0 else 'command_failed'
        for key in ('termination_status', 'stop_reason', 'stdout_truncated', 'stderr_truncated'):
            if hasattr(result, key):
                source[key] = getattr(result, key)
        if source.get('stdout_truncated') or source.get('stderr_truncated'):
            state = 'parsing_failed'
            source['error'] = {'code': 'output_truncated'}
    except Exception as exc:
        state = 'timeout' if isinstance(exc, TimeoutError) or type(exc).__name__ == 'CommandTimeoutError' else 'command_failed'
        source['error'] = {'type': type(exc).__name__, 'code': state}
        partial = getattr(exc, 'result', None)
        if partial is not None:
            for key in ('stdout', 'stderr', 'termination_status', 'stdout_truncated', 'stderr_truncated'):
                if hasattr(partial, key):
                    source[key] = getattr(partial, key)
        if state != 'timeout' and not isinstance(exc, FileNotFoundError):
            report['execution_errors'].append({'stage': 'command', **source['error']})
        if isinstance(exc, FileNotFoundError):
            state = 'unavailable'
            source['error']['code'] = 'tool_not_found'
    source['observed_at'] = now()
    return source, state


def one_line(text):
    lines = text.strip().splitlines()
    if len(lines) != 1 or not lines[0].strip() or '\x00' in text:
        raise ValueError('expected one nonempty line')
    return lines[0].strip()


def parse_os_release(text):
    """Parse quoted assignment data without executing or expanding shell content."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, raw = line.partition('=')
        if not sep or not key or not key.replace('_', '').isalnum():
            raise ValueError('invalid assignment')
        if key in values:
            raise ValueError('duplicate assignment')
        tokens = shlex.split(raw, comments=False, posix=True)
        if len(tokens) > 1 or '\x00' in raw:
            raise ValueError('invalid value')
        values[key] = tokens[0] if tokens else ''
    return values


def collect(session, report, timeout):
    source, state = probe(session, report, 'kernel_name', ['uname', '-s'], timeout)
    if state != 'success':
        observe(report, 'kernel_name', None, state, [source['id']])
        return report
    try:
        kernel = one_line(source['stdout'])
    except ValueError:
        observe(report, 'kernel_name', None, 'parsing_failed', [source['id']])
        return report
    observe(report, 'kernel_name', kernel, 'success', [source['id']])
    if kernel != 'Linux':
        observe(report, 'platform', None, 'unsupported', [source['id']], 'non_linux_kernel')
        for field in FIELDS:
            if field not in ('kernel_name', 'platform'):
                observe(report, field, None, 'unsupported', [source['id']], 'non_linux_platform')
        return report
    observe(report, 'platform', 'linux', 'success', [source['id']])
    for field, option in (('hostname', '-n'), ('kernel_release', '-r'), ('architecture', '-m')):
        item, state = probe(session, report, field, ['uname', option], timeout)
        value = None
        if state == 'success':
            try:
                value = one_line(item['stdout'])
            except ValueError:
                state = 'parsing_failed'
        observe(report, field, value, state, [item['id']])
    source_ids = []
    # /etc takes precedence; fallback is a separate retained probe, never merged.
    for index, path in enumerate(('/etc/os-release', '/usr/lib/os-release')):
        item, state = probe(session, report, f'os_release_{index}', ['/bin/sh', '-c', 'if [ ! -e "$1" ]; then exit 44; fi; if [ ! -r "$1" ]; then exit 45; fi; cat "$1"', 'inventory-system', path], timeout)
        source_ids.append(item['id'])
        if item['exitcode'] == 44:
            state = 'unavailable'
        elif item['exitcode'] == 45:
            state = 'permission_denied'
        if item['exitcode'] != 44:
            break
    values = {}
    if state == 'success':
        try:
            values = parse_os_release(item['stdout'])
        except ValueError:
            state = 'parsing_failed'
    for field, key in (('system_name', 'NAME'), ('system_version', 'VERSION_ID')):
        value = values.get(key) or None
        field_state = state if state != 'success' else ('success' if value else 'unavailable')
        observe(report, field, value, field_state, source_ids,
                (('source_unavailable' if state == 'unavailable' else f'{key.lower()}_not_reported')
                 if field_state == 'unavailable' else None))
    return report
