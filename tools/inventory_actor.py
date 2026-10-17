"""Inventory adaptation of the shared strict root policy, with explicit user fallback."""
from contextlib import ExitStack, contextmanager

from opsfeast import RootUnavailableError
from root_access import candidates, root_actor, _restore


@contextmanager
def collection_actor(session, config, host, timeout, report, *, authenticated_user=None,
                     preflight=None):
    from access_check import ConsoleSession
    with ExitStack() as stack:
        try:
            actor = stack.enter_context(root_actor(session, config, host, timeout, report,
                authenticated_user=authenticated_user, preflight=preflight))
        except RootUnavailableError:
            # Catch only acquisition failure, never an exception from collection.
            degraded = any(item.get('reason_code') != 'sudo_disabled' for item in report['attempts'])
            report.update(mode='fallback_user' if degraded else 'user', degraded=degraded,
                          selected_user=report['login_identity']['username'],
                          actual_identity=dict(report['shell_identity']),
                          reason_code='root_unavailable' if degraded else 'sudo_disabled')
            try:
                yield session
            finally:
                _restore(session, report['shell_identity'], timeout, False, report)
            return
        yield session if actor is session else ConsoleSession(actor)
