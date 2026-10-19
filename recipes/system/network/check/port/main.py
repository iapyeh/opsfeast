"""One host-origin TCP check, using SSHScript argv and a bounded remote command."""
import ipaddress
import json

VERSION = '0.1.0'
PROBE = '''import json, socket, sys
address, port, budget = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
try:
    with socket.create_connection((address, port), timeout=budget):
        state = "open"
except ConnectionRefusedError:
    state = "refused"
except (TimeoutError, socket.timeout):
    state = "timeout"
except OSError:
    state = "network_error"
print(json.dumps({"state": state}))
'''


def execute(session, *, context, timeout):
    # IP literals avoid DNS resolution whose duration may exceed a socket timeout.
    address = str(ipaddress.ip_address(context.vars['address']))
    port = context.vars['port']
    budget = min(context.vars['connect_timeout_seconds'], timeout)
    data = {'probe_from': context.host_id, 'address': address, 'port': port,
            'protocol': 'tcp', 'reachable': None, 'state': 'unknown'}
    result = session.exec_command(['python3', '-c', PROBE, address, str(port), str(budget)],
                                  check=False, command_timeout=timeout)
    if (result.exitcode != 0 or getattr(result, 'stdout_truncated', False)
            or getattr(result, 'stderr_truncated', False)):
        return {'status': 'failed', 'reason_code': 'command_failed',
                'message': 'TCP probe command failed or its output was truncated.', 'data': data}
    try:
        payload = json.loads(result.stdout)
        state = payload['state']
        if state not in ('open', 'refused', 'timeout', 'network_error'):
            raise ValueError('unknown state')
    except (ValueError, KeyError, TypeError):
        return {'status': 'failed', 'reason_code': 'parsing_failed',
                'message': 'TCP probe output could not be interpreted.', 'data': data}
    data['state'] = state
    data['reachable'] = True if state == 'open' else False if state == 'refused' else None
    if state in ('open', 'refused'):
        return {'status': 'success', 'reason_code': 'port_' + state,
                'message': 'TCP connection succeeded.' if state == 'open' else 'TCP connection was refused.', 'data': data}
    return {'status': 'failed', 'reason_code': 'port_' + state,
            'message': 'TCP reachability could not be established.', 'data': data}
