"""Shared, read-only host discovery and authenticated diagnostics (SSHScript 5.0)."""
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import tempfile
import sys

from opsfeast import ConfigError, Validator, connection_plan, connection_error, diagnostic_traceback

FACTS_VERSION = '0.1.0'
_diagnostics = ContextVar('host_diagnostics', default=(False, False, False))


@contextmanager
def diagnostic_options(verbose=False, debug=False, show_traceback=False):
    token = _diagnostics.set((verbose or debug, debug, show_traceback))
    try:
        yield
    finally:
        _diagnostics.reset(token)


def progress(stage, **details):
    verbose, debug, _ = _diagnostics.get()
    if verbose:
        print(stage, file=sys.stderr)
    if debug and details:
        print('DEBUG ' + json.dumps(details, ensure_ascii=False), file=sys.stderr)


def diagnostic_error(exc, stage=None):
    error = connection_error(exc)
    if isinstance(exc, PermissionError):
        error['reason'] = 'permission_denied'
        if stage in ('sudo_entry', 'su_entry'):
            error['reason'] = 'authentication_rejected_or_password_required'
            error['hint'] = ('Check the selected credential source and account policy; '
                             'this error does not establish that the password is incorrect.')
    progress(f'{stage or "operation"}: failed ({error["type"]}, {error.get("reason", "unknown")})')
    if _diagnostics.get()[2]:
        diagnostic_traceback(exc)
    return error


def now():
    return datetime.now(timezone.utc).isoformat()


def load_config(root, host):
    config = Validator(root)
    config.load(config.root / 'hosts.yaml')
    config.check_connections()
    if host not in config.hosts:
        raise ConfigError(f'unknown host ID: {host}')
    return config


def runtime_class():
    from importlib.metadata import version
    try:
        import sshscript
    except ImportError:
        raise ConfigError('host diagnostics require SSHScript 5.0.0 in this interpreter') from None
    if sshscript.__version__ != '5.0.0' or version('sshscript') != '5.0.0':
        raise ConfigError('host diagnostics require matching SSHScript import/distribution 5.0.0')
    return sshscript.Session


@contextmanager
def connected(config, host, session_class, timeout, report):
    local = None
    try:
        plan = connection_plan(config, host, session_class)
        progress('connection settings', hop_count=len(plan), timeout=timeout)
        local = session_class()
        session = local
        report['hops'] = []
        for index, settings in enumerate(plan, 1):
            hop = {'index': index, 'connected': False}
            report['hops'].append(hop)
            options = dict(settings)
            hostname = options.pop('hostname')
            progress(f'connection hop {index}', hop=index, hostname=hostname,
                     user=options.get('username'), password_supplied='password' in options,
                     identity_file=bool(options.get('pkey_path')),
                     proxy_command=bool(options.get('proxyCommand')))
            session = session.connect(hostname, ssh_config=False, timeout=timeout,
                                      banner_timeout=timeout, auth_timeout=timeout, **options)
            hop['connected'] = True
        report['connected'] = True
        yield session
    finally:
        if local is not None:
            try:
                progress('session cleanup')
                local.close(strict=True)
            except Exception as exc:
                diagnostic_error(exc, 'session_cleanup')
                report['cleanup_error'] = type(exc).__name__
                report['status'] = 'failed'


def output(result):
    if (result.exitcode != 0 or getattr(result, 'stdout_truncated', False)
            or getattr(result, 'stderr_truncated', False)):
        raise RuntimeError('command failed or truncated')
    return result.stdout


def line(text):
    rows = text.strip().splitlines()
    if len(rows) != 1 or not rows[0] or '\x00' in text:
        raise ValueError('invalid one-line result')
    return rows[0]


def query(session, argv, timeout):
    progress('command: ' + shlex.join(argv))
    return output(session.exec_command(argv, check=False, command_timeout=timeout))


def target_fingerprint(config, host):
    # Include jump-host connections, never credentials. Only the digest is saved.
    def expand(c):
        if 'host' in c:
            return expand(config.hosts[c['host']]['connection'])
        return {k: expand(v) if k == 'via' else v for k, v in c.items()}
    value = expand(config.hosts[host]['connection'])
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def cache_path(config, host):
    directory = config.root / 'observations' / 'host-init'
    # Reject every symlink component before reading/writing operational data.
    for path in (directory.parent, directory):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ConfigError('host-init storage must be a real directory')
    path = directory / (hashlib.sha256(host.encode()).hexdigest() + '.json')
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ConfigError('host-init data must be a regular file')
    return path


def save_facts(config, host, report):
    path = cache_path(config, host)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.host-init-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return path


def cached_facts(config, host):
    path = cache_path(config, host)
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        if (value.get('schema_version') == FACTS_VERSION and value.get('host_id') == host
                and value.get('status') == 'success'
                and value.get('target_fingerprint') == target_fingerprint(config, host)
                and isinstance(value.get('facts'), dict)
                and isinstance(value['facts'].get('os_name'), str)
                and isinstance(value.get('observed_at'), str)):
            return value
    except (ValueError, TypeError, AttributeError):
        pass
    return None


def parse_release(text):
    values = {}
    for row in text.splitlines():
        row = row.strip()
        if not row or row.startswith('#'):
            continue
        key, sep, raw = row.partition('=')
        if not sep or not re.fullmatch(r'[A-Z_][A-Z_0-9]*', key) or key in values:
            raise ValueError('invalid os-release')
        tokens = shlex.split(raw)
        if len(tokens) > 1 or '\x00' in raw:
            raise ValueError('invalid os-release value')
        values[key] = tokens[0] if tokens else ''
    return values


def discover(session, host, timeout):
    report = {'schema_version': FACTS_VERSION, 'probe_version': FACTS_VERSION,
              'host_id': host, 'observed_at': now(), 'status': 'failed',
              'facts': {}, 'fields': {}, 'sources': []}
    def probe(key, argv, parser=line):
        item = {'field': key, 'command': argv, 'observed_at': now()}
        try:
            value = parser(query(session, argv, timeout))
            if value is None or value == '':
                raise ValueError('missing value')
            report['facts'][key] = value
            item['status'] = 'success'
        except Exception as exc:
            state = ('timeout' if isinstance(exc, TimeoutError) or type(exc).__name__ == 'CommandTimeoutError' else
                     'parsing_failed' if isinstance(exc, ValueError) else
                     'permission_denied' if isinstance(exc, PermissionError) else 'command_failed')
            item.update(status=state, error=diagnostic_error(exc))
        report['fields'][key] = item['status']
        report['sources'].append(item)
        return report['facts'].get(key)
    kernel = probe('kernel_name', ['uname', '-s'])
    if kernel is None:
        report['reason_code'] = 'platform_detection_failed'
        return report
    report['facts']['os_name'] = {'Linux': 'linux', 'FreeBSD': 'freebsd', 'Darwin': 'macos'}.get(kernel, kernel.lower())
    report['fields']['os_name'] = 'success'
    probe('kernel_release', ['uname', '-r'])
    probe('architecture', ['uname', '-m'])
    if kernel == 'Linux':
        release = None
        for path in ('/etc/os-release', '/usr/lib/os-release'):
            argv = ['/bin/sh', '-c', 'if [ ! -e "$1" ]; then exit 44; fi; if [ ! -r "$1" ]; then exit 45; fi; cat "$1"', 'host-init', path]
            item = {'field': 'os_release', 'command': argv, 'observed_at': now()}
            try:
                result = session.exec_command(argv, check=False, command_timeout=timeout)
                if result.exitcode == 44:
                    item['status'] = 'unavailable'
                    report['sources'].append(item)
                    continue
                release = parse_release(output(result))
                item['status'] = 'success'
            except Exception as exc:
                item.update(status='unavailable', error=diagnostic_error(exc))
            report['sources'].append(item)
            break
        for key, source in (('distribution_id', 'ID'), ('distribution_name', 'NAME'), ('distribution_version', 'VERSION_ID')):
            value = (release or {}).get(source)
            report['fields'][key] = 'success' if value else 'unavailable'
            if value:
                report['facts'][key] = value.lower() if key == 'distribution_id' else value
        report['fields']['os_version'] = 'unavailable'
    elif kernel == 'FreeBSD':
        probe('os_version', ['freebsd-version', '-u'])
    elif kernel == 'Darwin':
        probe('os_version', ['sw_vers', '-productVersion'])
    report.update(status='success', reason_code='platform_detected')
    return report


def initialize_host(config, host, timeout=30, session_class=None, refresh=False):
    if not refresh:
        existing = cached_facts(config, host)
        if existing is not None:
            return dict(existing, selection_source='cache')
    previous = cached_facts(config, host)
    if previous is None:
        path = cache_path(config, host)
        try:
            latest = json.loads(path.read_text(encoding='utf-8'))
            historical = latest.get('previous_success')
            if (latest.get('target_fingerprint') == target_fingerprint(config, host)
                    and isinstance(historical, dict) and isinstance(historical.get('facts'), dict)
                    and isinstance(historical.get('observed_at'), str)):
                previous = historical
        except (OSError, ValueError, TypeError, AttributeError):
            pass
    report = {'host_id': host, 'schema_version': FACTS_VERSION, 'probe_version': FACTS_VERSION,
              'observed_at': now(), 'status': 'failed', 'facts': {}, 'connected': False}
    try:
        with connected(config, host, session_class or runtime_class(), timeout, report) as session:
            report.update(discover(session, host, timeout))
    except Exception as exc:
        report.update(status='failed', reason_code='host_init_failed', error=diagnostic_error(exc))
    report.update(target_fingerprint=target_fingerprint(config, host), selection_source='probe')
    if report['status'] == 'failed' and previous:
        report['previous_success'] = {k: previous[k] for k in ('observed_at', 'facts')}
    report['result_path'] = str(cache_path(config, host))
    save_facts(config, host, report)
    return report


def username(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*\$?', value):
        raise ConfigError('account must be a simple username, without options or shell syntax')
    return value


def identity(session, timeout, console=False, target=None, verification=None):
    def run(argv):
        return output(session(shlex.join(argv), check=False, command_timeout=timeout)) if console else query(session, argv, timeout)
    name = line(run(['id', '-un']))
    if verification is not None:
        verification['actual']['username'] = name
    uid = line(run(['id', '-u']))
    if not uid.isdecimal():
        raise RuntimeError('invalid effective UID')
    if verification is not None:
        verification['actual']['effective_uid'] = int(uid)
    if target is not None:
        expected_uid = line(run(['id', '-u', username(target)]))
        if verification is not None and expected_uid.isdecimal():
            verification['expected']['effective_uid'] = int(expected_uid)
            verification['matched'] = uid == expected_uid
        if not expected_uid.isdecimal() or uid != expected_uid:
            raise RuntimeError('effective UID mismatch')
    return {'username': name, 'effective_uid': int(uid)}


def identity_check(expected):
    return {'status': 'not_run', 'expected': dict(expected),
            'actual': {'username': None, 'effective_uid': None}, 'matched': None,
            'message': 'Identity verification has not run.'}


def verify_target_identity(session, timeout, target, record):
    try:
        actual = identity(session, timeout, console=True, target=target, verification=record)
    except Exception:
        record['status'] = 'failed'
        record['message'] = ('Effective UID does not match the requested account.' if record['matched'] is False
                             else 'Could not complete effective identity verification.')
        progress(record['message'])
        raise
    record.update(status='success', matched=True,
                  message='Effective UID matches the requested account; shell identity verified.')
    progress(f"Identity verified: expected {target} (UID {record['expected']['effective_uid']}), "
             f"actual {actual['username']} (UID {actual['effective_uid']}).")
    return actual


def privilege_password(config, host, user, mode, connection_user):
    """Select one credential before entry; never retry lower-priority sources."""
    account = config.hosts[host].get('users', {}).get(user, {})
    sources = [(account.get('vars', {}).get(mode, {}), f'users.<account>.vars.{mode}.password')]
    if user == connection_user:
        sources.append((config.hosts[host].get('vars', {}).get(mode, {}), f'vars.{mode}.password'))
    sources.append((account, 'users.<account>.password'))
    for settings, source in sources:
        if not isinstance(settings, dict):
            raise ConfigError(f'{mode} settings must be a mapping')
        password = settings.get('password')
        if password is not None:
            if not isinstance(password, str):
                raise ConfigError(f'{mode} password must be a string')
            return password, source
    return None, 'none'


def privilege_test(config, host, mode, targets=None, chains=None, run_as='root', timeout=30, session_class=None,
                   password_required=False):
    session_class = session_class or runtime_class()
    if mode not in ('su', 'sudo'):
        raise ConfigError('unknown privilege test')
    targets = [username(t) for t in (targets or [])]
    chains = [[username(t) for t in chain] for chain in (chains or [])]
    username(run_as)
    if mode == 'su' and (not targets and not chains or targets and chains):
        raise ConfigError('test-su requires usernames or --chain groups, without mixing')
    if mode == 'su' and (len(set(targets)) != len(targets) or
                         any(a == b for c in chains for a, b in zip(c, c[1:]))):
        raise ConfigError('duplicate independent or adjacent chain usernames')
    if mode == 'sudo' and len(set(targets)) != len(targets):
        raise ConfigError('duplicate sudo usernames')
    report = {'host': host, 'test': 'test-' + mode, 'status': 'failed', 'groups': [], 'connected': False}
    try:
        # A fresh connection per group guarantees independent starting identity.
        with connected(config, host, session_class, timeout, report) as session:
            login = identity(session, timeout)
        if report.get('cleanup_error'):
            return report
        report['connection_user'] = login['username']
        report['connection_identity'] = login
        if mode == 'su' and any(login['username'] in c for c in ([targets] if targets else chains)):
            raise ConfigError('test-su cannot target the connection account')
        groups = chains if chains else [[t] for t in (targets or [login['username']])]
        for group in groups:
            item = {'mode': 'chain' if chains else 'independent', 'accounts': group, 'steps': [], 'status': 'failed'}
            item['parent_identity_verification'] = identity_check(login)
            report['groups'].append(item)
            current = login['username']
            try:
                with connected(config, host, session_class, timeout, item) as session:
                    if identity(session, timeout) != login:
                        raise RuntimeError('connection identity changed')
                    with ExitStack() as stack:
                        actor = session
                        failed = False
                        for target in group:
                            step = {'from_user': current, 'to_user': target, 'operation': 'su' if mode == 'su' else 'sudo', 'status': 'skipped'}
                            step['identity_verification'] = identity_check(
                                {'username': target if mode == 'su' else run_as, 'effective_uid': None})
                            item['steps'].append(step)
                            if failed:
                                step['reason_code'] = 'previous_step_failed'
                                continue
                            stage = 'su_entry'
                            try:
                                if mode == 'su' or target != login['username']:
                                    password, source = privilege_password(config, host, target, 'su', login['username'])
                                    step.update(password_source=source, password_supplied=password is not None)
                                    if password is None:
                                        step['reason_code'] = 'missing_su_password'
                                        failed = True
                                        continue
                                    progress('su_entry', actor=current, target=target, password_source=source, password_supplied=True)
                                    actor = stack.enter_context(actor.su(target, password=password, enter_timeout=timeout))
                                    stage = 'su_identity'
                                    progress(stage)
                                    if mode == 'sudo':
                                        step['su_identity_verification'] = identity_check(
                                            {'username': target, 'effective_uid': None})
                                    step['identity'] = verify_target_identity(
                                        actor, timeout, target, step['su_identity_verification'] if mode == 'sudo'
                                        else step['identity_verification'])
                                if mode == 'sudo':
                                    stage = 'sudo_entry'
                                    password, password_source = privilege_password(config, host, target, 'sudo', login['username'])
                                    step.update(from_user=target, to_user=run_as, password_source=password_source,
                                                password_supplied=password is not None)
                                    if password_required and password is None:
                                        step['reason_code'] = 'missing_sudo_password'
                                        continue
                                    progress(stage, actor=target, target=run_as, password_source=password_source,
                                             password_supplied=password is not None)
                                    elevated = stack.enter_context(actor.sudo(username=run_as, password=password, enter_timeout=timeout))
                                    stage = 'sudo_identity'
                                    progress(stage)
                                    step['identity'] = verify_target_identity(elevated, timeout, run_as,
                                                                               step['identity_verification'])
                                step['status'] = 'success'
                                current = target
                            except Exception as exc:
                                step.update(status='failed', stage=stage, error=diagnostic_error(exc, stage))
                                failed = True
                    # Confirm exit to the original identity; otherwise this group failed.
                    progress('parent identity verification')
                    parent_check = item['parent_identity_verification']
                    try:
                        restored = identity(session, timeout)
                    except Exception:
                        parent_check.update(status='failed', message='Could not verify return to the connection identity.')
                        raise
                    parent_check.update(actual=restored, matched=restored == login,
                                        status='success' if restored == login else 'failed',
                                        message=('Original connection identity restored.' if restored == login
                                                 else 'Original connection identity was not restored.'))
                    progress(parent_check['message'])
                    if restored != login:
                        raise RuntimeError('parent identity not restored')
                    item['status'] = ('failed' if any(s['status'] == 'failed' for s in item['steps']) else
                                      'skipped' if any(s['status'] == 'skipped' for s in item['steps']) else 'success')
            except Exception as exc:
                item.update(status='failed', error=diagnostic_error(exc))
        report['status'] = 'failed' if any(g['status'] == 'failed' for g in report['groups']) else ('skipped' if any(g['status'] == 'skipped' for g in report['groups']) else 'success')
    except ConfigError:
        raise
    except Exception as exc:
        report.update(status='failed', error=diagnostic_error(exc))
    report['finished_at'] = now()
    return report


def test_host(config, host, timeout=30, session_class=None):
    cls = session_class or runtime_class()
    report = {'host': host, 'status': 'failed', 'tests': {}}
    connection = {'status': 'failed', 'connected': False, 'commands': []}
    report['tests']['test-connection'] = connection
    try:
        with connected(config, host, cls, timeout, connection) as session:
            for command in ('hostname', 'date'):
                try:
                    query(session, [command], timeout)
                    connection['commands'].append({'command': command, 'status': 'success'})
                except Exception as exc:
                    connection['commands'].append({'command': command, 'status': 'failed', 'error': diagnostic_error(exc, command)})
            connection['status'] = 'success' if all(c['status'] == 'success' for c in connection['commands']) else 'failed'
    except Exception as exc:
        connection['error'] = diagnostic_error(exc)
    if not connection['connected']:
        for name in ('host-init', 'test-sudo', 'test-su'):
            report['tests'][name] = {'status': 'skipped', 'reason_code': 'connection_failed'}
        return report
    report['tests']['host-init'] = initialize_host(config, host, timeout, cls)
    report['tests']['test-sudo'] = privilege_test(config, host, 'sudo', timeout=timeout, session_class=cls, password_required=True)
    users = list(config.hosts[host].get('users', {}))
    login = report['tests']['test-sudo'].get('connection_user')
    targets = [u for u in users if u != login]
    report['tests']['test-su'] = (privilege_test(config, host, 'su', targets, timeout=timeout, session_class=cls)
                                if targets and login else {'status': 'skipped', 'reason_code': 'no_other_accounts' if login else 'connection_identity_unavailable'})
    report['status'] = 'failed' if any(t['status'] == 'failed' for t in report['tests'].values()) else ('partial' if any(t['status'] == 'skipped' for t in report['tests'].values()) else 'success')
    report['finished_at'] = now()
    return report
