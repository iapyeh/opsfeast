"""Reviewed browser -> deterministic selection -> guarded login command, 0.1.0."""
from hashlib import sha256
import re
from . import ConfigError
from . import browser_steps
from .operation_guard import OperationGuard


def run(context, *, target_host, purpose, url, select_quote, build_argv, repeat_receipt=None,
        command_completion_is_success=False):
    """Authorization is supplied by the human's run request, never by page content."""
    data = {} if command_completion_is_success else {'business_outcome': 'unverified', 'mail_delivery': 'unknown'}
    guard = None
    dispatched = False
    terminal = False
    try:
        if context.host_id != target_host:
            raise ConfigError('wrong_target_host')
        month = context.vars.get('target_month')
        if not isinstance(month, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}', month):
            raise ConfigError('invalid_month')
        from datetime import date
        date.fromisoformat(month + '-15')
        wait = context.vars.get('browser_wait_seconds', 180)
        deadline = context.vars.get('command_timeout_seconds', 300)
        if type(wait) is not int or not 1 <= wait <= 180 or type(deadline) is not int or not 1 <= deadline <= 300:
            raise ConfigError('invalid_workflow_deadline')
        guard = OperationGuard(context.root, key={'purpose': purpose, 'host': target_host, 'month': month},
                               run_id=context.run_id, repeat_receipt=repeat_receipt)
        data['guard_id'] = guard.path.stem
        if guard.repeat_of is not None:
            data['repeat_of'] = guard.repeat_of
            context.progress('Confirmed repeat of completed operation ' + guard.repeat_of['run_id'])
        snapshot = browser_steps.acquire(context, url=url, target_month=month, wait_seconds=wait)
        data.update(browser_request_id=snapshot['request_id'], snapshot_sha256=snapshot['snapshot_sha256'])
        context.progress('02 parse table; 03 select same-month spot bank-selling quote')
        quote = select_quote(snapshot, month)
        argv = build_argv(quote)
        if not isinstance(argv, list) or not argv or any(not isinstance(value, str) or not value or '\x00' in value for value in argv):
            raise ConfigError('invalid_command_argv')
        data.update(quote=quote, argv=argv)
        guard.update('prepared', step='03', quote=quote, snapshot_sha256=snapshot['snapshot_sha256'], argv=argv)
        context.progress('03 selected ' + quote['selected_date'] + ' USD spot bank sell ' + quote['sell_rate'])
        with context.connect() as session:
            # Persist uncertain intent BEFORE the command can have any remote effects.
            guard.update('outcome_unknown', step='04', argv=argv)
            dispatched = True
            context.progress('04 dispatch reviewed monthly command to ' + target_host + ' (may generate and mail bills)')
            if context.river is not None:
                receipt = context.river.execute(session, argv, timeout=deadline)
            else:
                receipt = session.exec_command(argv, check=False, command_timeout=deadline)
            data['command'] = {'exitcode': receipt.exitcode}
            for field in ('stdout', 'stderr'):
                output = getattr(receipt, field, '') or ''
                raw = output if isinstance(output, bytes) else output.encode('utf-8')
                data['command'][field + '_sha256'] = sha256(raw).hexdigest()
                data['command'][field + '_bytes'] = len(raw)
                data['command'][field + '_truncated'] = bool(getattr(receipt, field + '_truncated', False))
            state = 'command_completed' if receipt.exitcode == 0 else 'command_failed'
            guard.update(state, step='05', command=data['command'])
            terminal = True
        if receipt.exitcode != 0:
            status, reason, message = 'failed', state, 'Command failed; do not automatically repeat billing.'
        elif command_completion_is_success:
            status, reason, message = 'success', state, 'Command completed with exit code 0.'
        else:
            status, reason = 'partial', state + '_business_outcome_unverified'
            message = 'Command completed; invoice creation and mail delivery are unverified.'
        context.progress('05 ' + message)
        return {'status': status, 'reason_code': reason, 'message': message, 'data': data}
    except Exception as exc:
        state = 'outcome_unknown' if dispatched else 'failed_before_dispatch'
        if guard is not None and not terminal:
            guard.update(state, error_type=type(exc).__name__)
        data['execution'] = state
        # Only our typed validation errors have safe user-visible reason text.
        candidate = str(exc).split(':', 1)[0]
        reason = candidate if isinstance(exc, (ConfigError, ValueError)) and re.fullmatch(r'[a-z_]{1,100}', candidate) else type(exc).__name__
        return {'status': 'failed', 'reason_code': state,
                'message': state + ': ' + reason + ('; reconcile before any repeat.' if dispatched else '; no command dispatched.'), 'data': data}
