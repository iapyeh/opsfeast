"""Inventory access contract 0.1.0: no inventory or host-fact collection."""
from contextlib import contextmanager
import shlex

from opsfeast import ConfigError
from host_runtime import connected, identity, now, runtime_class, target_fingerprint

VERSION = '0.1.0'


def sudo_settings(config, host, user):
    account = config.hosts[host].get('users', {}).get(user, {})
    if 'sudo' in account and account['sudo'] != 'false':
        raise ConfigError('users.<account>.sudo accepts only the quoted string "false"; omit to enable')
    enabled = account.get('sudo') != 'false'
    # Canonical field wins by presence, including null and empty string.
    if 'sudo-password' in account:
        value = account['sudo-password']
        if value != 'false':
            if value is not None and not isinstance(value, str):
                raise ConfigError('sudo-password must be a string or null')
            return enabled, '' if value is None else value, 'users.<account>.sudo-password'
        return enabled, account.get('password'), 'users.<account>.password'
    # Preserve existing explicit vars credentials with the new presence rule.
    for settings, source in ((account.get('vars', {}).get('sudo', {}), 'users.<account>.vars.sudo.password'),
                             (config.hosts[host].get('vars', {}).get('sudo', {}), 'vars.sudo.password')):
        if not isinstance(settings, dict):
            raise ConfigError('sudo settings must be a mapping')
        if 'password' in settings:
            value = settings['password']
            if value != 'false':
                if value is not None and not isinstance(value, str):
                    raise ConfigError('sudo password must be a string or null')
                return enabled, '' if value is None else value, source
            break
    return enabled, account.get('password'), 'users.<account>.password' if 'password' in account else 'none'


class ConsoleSession:
    """Adapt the documented console string interface to collector argv calls."""
    def __init__(self, console):
        self.console = console

    def exec_command(self, argv, **kwargs):
        return self.console(shlex.join(argv), **kwargs)


@contextmanager
def collection_actor(session, config, host, timeout, report, *, force=False, fallback=False):
    login = identity(session, timeout)
    configured = config.hosts[host]['connection'].get('user')
    if configured is not None:
        identity(session, timeout, target=configured)
    report['connection_identity'] = login
    report['actual_identity'] = login
    report['restoration_verified'] = True
    enabled, password, source = sudo_settings(config, host, login['username'])
    report['sudo'] = {'status': 'not_needed' if login['effective_uid'] == 0 else 'disabled' if not enabled else 'not_attempted',
                      'password_source': source, 'password_supplied': password is not None}
    if fallback and login['effective_uid'] != 0 and enabled:
        report['sudo'].update(status='failed', reason_code='preflight_sudo_failed')
        report.update(mode='fallback_user', degraded=True)
        yield session
        return
    if login['effective_uid'] == 0 or not enabled:
        report['mode'] = 'root' if login['effective_uid'] == 0 else 'user'
        yield session
        return
    report['restoration_verified'] = False
    context = None
    entered = False
    try:
        context = session.sudo(username='root', password=password, enter_timeout=timeout)
        console = context.__enter__()
        entered = True
        actual = identity(console, timeout, console=True)
        if actual['effective_uid'] != 0:
            raise RuntimeError('sudo did not establish root')
    except Exception as exc:
        # Entry rejection can recover; a body/exit failure is never a fallback.
        report['sudo'].update(status='failed', error_type=type(exc).__name__)
        if entered:
            try:
                context.__exit__(type(exc), exc, exc.__traceback__)
            finally:
                report['restoration_verified'] = identity(session, timeout) == login
            raise
        report['restoration_verified'] = identity(session, timeout) == login
        if not report['restoration_verified']:
            raise RuntimeError('identity restoration failed') from None
        if not force:
            raise
        report.update(mode='fallback_user', degraded=True)
        yield session
        return
    report['sudo']['status'] = 'success'
    report.update(mode='root', actual_identity=actual)
    try:
        yield ConsoleSession(console)
    finally:
        context.__exit__(None, None, None)
        report['restoration_verified'] = identity(session, timeout) == login
        if not report['restoration_verified']:
            raise RuntimeError('identity restoration failed')


def check_access(config, host, timeout=30, session_class=None):
    report = {'contract_version': VERSION, 'host': host, 'started_at': now(), 'status': 'failed',
              'connected': False, 'purpose': 'access-only', 'reason_code': 'connection_failed'}
    if not config.hosts[host].get('enabled', True):
        report.update(status='skipped', reason_code='host_disabled', finished_at=now())
        return report
    report['target_fingerprint'] = target_fingerprint(config, host)
    try:
        with connected(config, host, session_class or runtime_class(), timeout, report) as session:
            report['reason_code'] = 'identity_failed'
            access = {}
            report['access'] = access
            with collection_actor(session, config, host, timeout, access):
                report.update(status='success', reason_code='access_verified')
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__)
        if report.get('access', {}).get('sudo', {}).get('status') == 'failed':
            report['reason_code'] = 'sudo_failed'
    if report.get('cleanup_error'):
        report.update(status='failed', reason_code='cleanup_failed')
    report['finished_at'] = now()
    return report


def check_many(root, hosts, timeout=30, threads=1, session_class=None):
    from concurrent.futures import ThreadPoolExecutor
    from opsfeast import Validator
    config = Validator(root)
    config.load(config.root / 'hosts.yaml')
    config.check_connections()
    if any(host not in config.hosts for host in hosts):
        raise ConfigError('unknown access-check target')
    def run(host):
        return check_access(config, host, timeout, session_class)
    with ThreadPoolExecutor(max_workers=max(1, min(threads, len(hosts)))) as pool:
        reports = list(pool.map(run, hosts))
    return {'contract_version': VERSION, 'status': 'success' if all(r['status'] == 'success' for r in reports) else 'failed',
            'hosts': reports}
