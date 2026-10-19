"""Inventory access contract 0.1.0: no inventory or host-fact collection."""
from contextlib import contextmanager
import json
import shlex
import sys
from threading import Lock

from opsfeast import ConfigError
from console_output import user_label, host_label as console_host_label
from host_runtime import connected, identity, verify_connection_identity, now, runtime_class, target_fingerprint, privilege_test, username

VERSION = '0.1.0'


def sudo_settings(config, host, user):
    account = config.hosts[host].get('users', {}).get(user, {})
    if 'sudo' in account and type(account['sudo']) is not bool:
        raise ConfigError('users.<account>.sudo must be a boolean; use false to disable or true to enable')
    enabled = account.get('sudo', True)
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
def collection_actor(session, config, host, timeout, report, *, force=False, fallback=False, authenticated_user=None):
    configured = config.hosts[host]['connection'].get('user')
    login = verify_connection_identity(session, timeout, report,
        authenticated_user=authenticated_user, configured_user=configured)
    report['restoration_verified'] = True
    enabled, password, source = sudo_settings(config, host, report['login_identity']['username'])
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


def check_access(config, host, timeout=30, session_class=None, *, inventory=False):
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
            if inventory:
                from inventory_actor import collection_actor as actor_context
            else:
                actor_context = collection_actor
            with actor_context(session, config, host, timeout, access,
                                  authenticated_user=report.get('login_identity', {}).get('username')):
                report.update(status='success', reason_code=access.get('reason_code', 'access_verified'))
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__)
        if report['reason_code'] == 'identity_failed':
            report['identity_error'] = {'reason_code': getattr(exc, 'reason_code', 'identity_failed')}
        if report.get('access', {}).get('sudo', {}).get('status') == 'failed':
            report['reason_code'] = 'sudo_failed'
    if report.get('cleanup_error'):
        report.update(status='failed', reason_code='cleanup_failed')
    report['finished_at'] = now()
    return report


def account_label(report):
    """Prefer the verified login; SSH aliases may resolve only after connecting."""
    return (report.get('user') or report.get('access', {}).get('login_identity', {}).get('username')
            or report.get('access', {}).get('connection_identity', {}).get('username')
            or report.get('configured_user') or 'unresolved')


def display_value(value):
    # Keep host/account controls on one terminal line without interpreting them.
    return json.dumps(str(value), ensure_ascii=False)[1:-1]


def host_label(host, icons=None):
    return display_value(console_host_label(host, icons))


def host_icons(root, hosts):
    """Load validated display metadata without changing IDs or JSON reports."""
    from opsfeast import Validator
    config = Validator(root)
    config.load(config.root / 'hosts.yaml')
    from console_output import DisplayIcons
    return DisplayIcons(config)


def host_summary(report, icons=None):
    status = {'success': 'PASS', 'failed': 'FAIL', 'skipped': 'SKIP'}.get(report['status'], 'UNKNOWN')
    label = f"{host_label(report['host'], icons)} / {display_value(user_label(account_label(report), report['host'], icons))}"
    reason = report.get('reason_code', 'unknown')
    return ('❌ ' if status == 'FAIL' else '') + f"{status}  {label}" + (f"  ({display_value(reason)})" if status != 'PASS' else '')


def table_formatter():
    """Check display dependencies before the CLI makes any connection."""
    from console_output import table_formatter as formatter, ConsoleDependencyError
    try:
        return formatter()
    except ConsoleDependencyError as exc:
        raise ConfigError(str(exc)) from None


def summary_tests(report):
    """Project existing evidence into test rows without issuing any probes."""
    rows = []

    def add(test, user, status, reason=''):
        rows.append({'test': test, 'user': user, 'status': status,
                     'reason_code': '' if status == 'success' else reason})

    access = report.get('access', {})
    login = account_label(report)
    # Incomplete/legacy display inputs cannot establish individual test outcomes.
    if 'connected' not in report:
        add('access', login, report['status'], report.get('reason_code', 'unknown'))
        return rows
    if report['status'] == 'skipped' and not report.get('connected'):
        add('connection', login, 'skipped', report.get('reason_code', 'not_run'))
    else:
        add('connection', login, 'success' if report.get('connected') else 'failed', 'connection_failed')
        if report.get('connected') and not access.get('connection_identity'):
            add('identity', login, 'failed', report.get('identity_error', {}).get('reason_code', 'identity_failed'))
        elif access.get('identity_model') == 'esxi_root_shell':
            add('identity', login, 'success')
            rows[-1]['reason_code'] = 'shell=' + access['shell_identity']['username'] + ', uid=0 (ESXi)'
    if 'attempts' in access and access['attempts']:
        for attempt in access['attempts']:
            if not attempt['steps']:
                add('sudo' if attempt['user'] == login else 'su', attempt['user'],
                    'skipped', attempt.get('reason_code', 'not_attempted'))
            for step in attempt['steps']:
                add(step['operation'], attempt['user'], step['status'], step.get('reason_code', 'identity_failed'))
        if access.get('degraded'):
            add('selection', login, 'success')
            rows[-1]['reason_code'] = 'fallback_user / root_unavailable'
    else:
        sudo = access.get('sudo', {})
        state = sudo.get('status')
        add('sudo', login, 'success' if state == 'success' else 'failed' if state == 'failed' else 'skipped',
            {'failed': 'sudo_failed', 'disabled': 'sudo_disabled', 'not_needed': 'already_root'}.get(
                state, 'not_attempted' if access.get('connection_identity') else 'connection_unverified'))
    if access.get('restoration_verified') is False:
        add('restoration', login, 'failed', 'restoration_failed')
    if report.get('cleanup_error'):
        add('cleanup', login, 'failed', 'cleanup_failed')

    for account in report.get('accounts', []):
        if account['role'] == 'login':
            continue
        user = account_label(account)
        detail = account.get('checks')
        if detail is None:
            add('su', user, 'skipped', account['reason_code'])
            add('sudo', user, 'skipped', account['reason_code'])
            continue
        groups = detail.get('groups', [])
        if not groups:
            reason = ('cleanup_failed' if detail.get('cleanup_error') else
                      'identity_failed' if detail.get('connected') else 'connection_failed')
            if reason != 'cleanup_failed':
                add('connection', login, 'success' if detail.get('connected') else 'failed', reason)
                if detail.get('connected'):
                    add('identity', login, 'failed', reason)
            add('su', user, 'skipped', reason)
            add('sudo', user, 'skipped', 'su_failed')
        for group in groups:
            steps = group.get('steps', [])
            if not steps:
                reason = 'identity_failed' if group.get('connected') else 'connection_failed'
                add('connection', login, 'success' if group.get('connected') else 'failed', reason)
                if group.get('connected'):
                    add('identity', login, 'failed', reason)
                add('su', user, 'skipped', reason)
                add('sudo', user, 'skipped', 'su_failed')
            for step in steps:
                sudo_enabled = account.get('sudo') == 'enabled'
                su_check = step.get('su_identity_verification' if sudo_enabled else 'identity_verification', {})
                stage = step.get('stage', '')
                su_status = ('success' if su_check.get('status') == 'success' else
                             'failed' if stage.startswith('su_') or su_check.get('status') == 'failed' else 'skipped')
                su_reason = stage + '_failed' if su_status == 'failed' and stage.startswith('su_') else step.get('reason_code', 'su_unverified')
                add('su', user, su_status, su_reason)
                if not sudo_enabled:
                    add('sudo', user, 'skipped', 'sudo_disabled')
                elif su_status != 'success':
                    add('sudo', user, 'skipped', 'su_failed')
                else:
                    sudo_check = step.get('identity_verification', {})
                    sudo_status = ('success' if sudo_check.get('status') == 'success' else
                                   'failed' if stage.startswith('sudo_') or sudo_check.get('status') == 'failed' else 'skipped')
                    add('sudo', user, sudo_status, stage + '_failed' if sudo_status == 'failed' else
                        step.get('reason_code', 'sudo_unverified'))
            parent = group.get('parent_identity_verification', {})
            if parent.get('status') == 'failed' or steps and parent.get('status') != 'success':
                add('restoration', user, 'failed', 'restoration_failed' if parent.get('status') == 'failed' else 'restoration_unverified')
            if group.get('cleanup_error'):
                add('cleanup', user, 'failed', 'cleanup_failed')
        if detail.get('cleanup_error'):
            add('cleanup', user, 'failed', 'cleanup_failed')
    return rows


def format_summary(report, icons=None):
    rows = []
    for host in report['hosts']:
        for test in summary_tests(host):
            status = {'success': 'PASS', 'failed': '❌ FAIL', 'skipped': 'SKIP'}.get(test['status'], 'UNKNOWN')
            rows.append([status, host_label(host['host'], icons), test['test'], display_value(user_label(account_label(test), host['host'], icons)),
                         display_value(test['reason_code'])])
    rows.extend(['EXCLUDED', host_label(item['host'], icons), '-', '-', display_value(item['reason_code'])]
                for item in report.get('excluded_hosts', []))
    counts = {state: sum(host['status'] == state for host in report['hosts'])
              for state in ('success', 'failed', 'skipped')}
    total = (f"Hosts: {counts['success']} passed, {counts['failed']} failed, "
             f"{counts['skipped']} skipped, {len(report.get('excluded_hosts', []))} excluded")
    from console_output import render_table
    return render_table(['status', 'host', 'test', 'user', 'reason'], rows) + '\n' + total


def progress_printer(total, icons=None):
    """Serialize parallel progress and flush before potentially slow connections."""
    lock = Lock()
    completed = 0

    def progress(stage, report):
        nonlocal completed
        with lock:
            if stage in ('start', 'account_start'):
                message = f"CHECK  {host_label(report['host'], icons)} / {display_value(user_label(account_label(report), report['host'], icons))}"
            elif stage == 'account_finish':
                message = host_summary(report, icons)
            else:
                completed += 1
                message = (f"[{completed}/{total}] {host_label(report['host'], icons)}: {report['status']}"
                           if len(report.get('accounts', [])) > 1 else
                           f"[{completed}/{total}] {host_summary(report, icons)}")
            print(message, file=sys.stderr, flush=True)
    return progress


def check_host_accounts(config, host, timeout=30, session_class=None, *, progress=None):
    """Explicit CLI account checks; inventory preflight remains login-only."""
    report = check_access(config, host, timeout, session_class)
    configured = config.hosts[host]['connection'].get('user')
    report['configured_user'] = configured
    login = (report.get('access', {}).get('login_identity', {}).get('username')
             or report.get('access', {}).get('connection_identity', {}).get('username'))
    accounts = report['accounts'] = [
        {'user': login or configured, 'status': report['status'], 'reason_code': report['reason_code'],
         'role': 'login'}]
    other_users = [user for user in config.hosts[host].get('users', {}) if user != (login or configured)]
    if progress and other_users:
        progress('account_finish', dict(accounts[0], host=host))
    safe = (login and not report.get('cleanup_error')
            and report.get('access', {}).get('restoration_verified') is True)
    for user, settings in config.hosts[host].get('users', {}).items():
        if user == (login or configured):
            continue
        account = {'user': user, 'role': 'su', 'status': 'skipped',
                   'reason_code': 'login_unavailable' if not login else 'login_cleanup_unverified'}
        accounts.append(account)
        if progress:
            progress('account_start', dict(account, host=host))
        if safe and report.get('status') != 'skipped':
            mode = 'su' if settings.get('sudo') is False else 'sudo'
            detail = privilege_test(config, host, mode, [user], timeout=timeout,
                                    session_class=session_class or runtime_class())
            account.update(status=detail['status'], checks=detail,
                           sudo='disabled' if mode == 'su' else 'enabled')
            groups = detail.get('groups', [])
            steps = [step for group in groups for step in group['steps']]
            if detail.get('cleanup_error') or any(group.get('cleanup_error') for group in groups):
                reason = 'cleanup_failed'
            elif any(group.get('parent_identity_verification', {}).get('status') == 'failed' for group in groups):
                reason = 'restoration_failed'
            else:
                problem = next((step for step in steps if step['status'] != 'success'), {})
                reason = problem.get('reason_code') or (problem['stage'] + '_failed' if 'stage' in problem else
                         'access_verified' if detail['status'] == 'success' else 'account_check_failed')
            account['reason_code'] = reason
        if progress:
            progress('account_finish', dict(account, host=host))
    report['status'] = ('failed' if any(a['status'] == 'failed' for a in accounts) else
                        'skipped' if any(a['status'] == 'skipped' for a in accounts) else 'success')
    if report['status'] != 'success' and report['reason_code'] == 'access_verified':
        report['reason_code'] = 'account_access_unverified'
    report['finished_at'] = now()
    return report


def check_many(root, hosts, timeout=30, threads=1, session_class=None, *, progress=None, include_users=False, inventory=False):
    from concurrent.futures import ThreadPoolExecutor
    from opsfeast import Validator
    config = Validator(root)
    config.load(config.root / 'hosts.yaml')
    config.check_connections()
    if any(host not in config.hosts for host in hosts):
        raise ConfigError('unknown access-check target')
    if include_users:
        for host in hosts:
            for user in config.hosts[host].get('users', {}):
                username(user)
    def run(host):
        configured_user = config.hosts[host]['connection'].get('user')
        if progress:
            progress('start', {'host': host, 'configured_user': configured_user})
        report = (check_host_accounts(config, host, timeout, session_class, progress=progress) if include_users
                  else check_access(config, host, timeout, session_class, inventory=True) if inventory
                  else check_access(config, host, timeout, session_class))
        report['configured_user'] = configured_user
        if progress:
            progress('finish', report)
        return report
    with ThreadPoolExecutor(max_workers=max(1, min(threads, len(hosts)))) as pool:
        reports = list(pool.map(run, hosts))
    return {'contract_version': VERSION, 'status': 'success' if all(r['status'] == 'success' for r in reports) else 'failed',
            'hosts': reports}
