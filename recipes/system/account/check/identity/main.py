"""Observe the login account using the runner-provided Core Recipe."""
VERSION = '0.1.0'


def execute(recipe):
    result = recipe.session.exec_command(['id', '-un'], check=True)
    if result.stdout_truncated or result.stderr_truncated:
        return {'status': 'failed', 'reason_code': 'output_truncated',
                'message': 'Identity command output was truncated.', 'data': {}}
    name = result.stdout.strip()
    if not name or '\n' in name or '\x00' in name:
        return {'status': 'failed', 'reason_code': 'invalid_identity_output',
                'message': 'Identity command returned an invalid account name.', 'data': {}}
    return {'status': 'success', 'reason_code': 'identity_observed',
            'message': 'Observed the connection account.', 'data': {'account': name}}
