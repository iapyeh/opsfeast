"""Shared strict two-candidate root selection for Recipe and inventory."""
from contextlib import ExitStack, contextmanager
from copy import deepcopy

from host_runtime import (IdentityProbeError, identity, identity_check, privilege_password,
                          verify_connection_identity, verify_target_identity, username)


def candidates(config, host, login):
    """At most the login and first other sudo-enabled account, in YAML order."""
    users = config.hosts[host].get('users', {})
    other = next((name for name, account in users.items()
                  if name != login and account.get('sudo', True)), None)
    ordered = [login] + ([other] if other else [])
    if other == 'root':
        ordered.reverse()
    return ordered


def _restore(parent, expected, timeout, console, record):
    record['restoration_verified'] = False
    actual = identity(parent, timeout, console=console)
    if actual != expected:
        raise RuntimeError('root identity restoration failed')
    record['restoration_verified'] = True


def _enter(stack, parent, parent_identity, parent_console, mode, target, password,
           source, timeout, attempt):
    step = {'operation': mode, 'target': target, 'status': 'failed',
            'password_source': source, 'password_supplied': password is not None}
    attempt['steps'].append(step)
    context = (parent.su(target, password=password, enter_timeout=timeout) if mode == 'su'
               else parent.sudo(username=target, password=password, enter_timeout=timeout))
    try:
        actor = context.__enter__()
    except Exception as exc:
        step.update(error_type=type(exc).__name__, reason_code=mode + '_entry_failed')
        # A successful command on this exact parent also checks SSHScript's
        # recovery state; an original Session cannot verify a nested console.
        _restore(parent, parent_identity, timeout, parent_console, step)
        return None, None

    def leave():
        step['restoration_verified'] = False
        context.__exit__(None, None, None)
        _restore(parent, parent_identity, timeout, parent_console, step)

    stack.callback(leave)
    verification = step['identity_verification'] = identity_check(
        {'username': target, 'effective_uid': None})
    # An entered context with unknown/wrong identity is fatal, never fallback.
    actual = verify_target_identity(actor, timeout, target, verification)
    if mode == 'sudo' and actual['effective_uid'] != 0:
        raise IdentityProbeError('identity_mismatch')
    step.update(status='success', actual_identity=actual)
    return actor, actual


@contextmanager
def root_actor(session, config, host, timeout, report, *, authenticated_user=None,
                     preflight=None):
    from opsfeast import RootUnavailableError
    login = verify_connection_identity(session, timeout, report,
        authenticated_user=authenticated_user,
        configured_user=config.hosts[host]['connection'].get('user'))
    login_user = report['login_identity']['username']
    report['selection_policy'] = 'two-candidate-v1'
    report['restoration_verified'] = False
    report['attempts'] = attempts = []
    report['candidate_users'] = candidates(config, host, login_user)
    report['sudo'] = {'status': 'not_needed' if login['effective_uid'] == 0 else 'not_attempted'}
    try:
        if login['effective_uid'] == 0:
            report.update(mode='root', selected_user=login_user)
            yield session
            return
        previous = {item['user']: item for item in (preflight or {}).get('access', {}).get('attempts', [])}
        users = config.hosts[host].get('users', {})
        for user in report['candidate_users']:
            username(user)
            attempt = {'user': user, 'status': 'skipped', 'steps': []}
            attempts.append(attempt)
            if user in previous and previous[user]['status'] != 'success':
                attempt.update(deepcopy(previous[user]), reused_from_preflight=True)
                continue
            if user == login_user and users.get(user, {}).get('sudo') is False:
                attempt['reason_code'] = 'sudo_disabled'
                report['sudo']['status'] = 'disabled'
                continue
            with ExitStack() as stack:
                actor, actual = session, login
                if user != login_user:
                    password, source = privilege_password(config, host, user, 'su', login_user)
                    if password is None:
                        attempt['reason_code'] = 'missing_su_password'
                        continue
                    actor, actual = _enter(stack, session, login, False, 'su', user,
                        password, source, timeout, attempt)
                    if actor is None:
                        attempt.update(status='failed', reason_code='su_entry_failed')
                        continue
                if actual['effective_uid'] != 0:
                    password, source = privilege_password(config, host, user, 'sudo', login_user)
                    elevated, actual = _enter(stack, actor, actual, user != login_user,
                        'sudo', 'root', password, source, timeout, attempt)
                    report['sudo'] = deepcopy(attempt['steps'][-1])
                    if elevated is None:
                        attempt.update(status='failed', reason_code='sudo_entry_failed')
                        continue
                    actor = elevated
                attempt['status'] = 'success'
                report.update(mode='root', selected_user=user, actual_identity=actual)
                yield actor
                return
        report['reason_code'] = 'root_unavailable'
    finally:
        # Even a body/exit error must retain explicit restoration evidence.
        # A nested cleanup failure must not be erased by a working SSH Session.
        nested_safe = all(step.get('restoration_verified') is True
                          for attempt in attempts for step in attempt['steps'])
        _restore(session, login, timeout, False, report)
        if not nested_safe:
            report['restoration_verified'] = False
            raise RuntimeError('root context cleanup is unverified')
    # Construct the safe failure only after every restoration check completed.
    raise RootUnavailableError(report)
