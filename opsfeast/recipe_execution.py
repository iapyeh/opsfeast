"""Recipe-wide execution identity and exact-stdin console command adaptation."""
import shlex
from opsfeast import ConfigError

VERSION = '0.1.0'


def normalize(value=None, *, partial=False):
    value = {} if value is None else value
    if not isinstance(value, dict) or set(value) - {'via', 'user'}:
        raise ConfigError('execution permits via and user only; credentials belong to hosts users')
    via = value.get('via', 'login')
    if via not in ('login', 'su', 'sudo'):
        raise ConfigError('execution.via must be login, su or sudo')
    user = value.get('user')
    if user is not None:
        from host_runtime import username
        username(user)
    if not partial and via != 'login' and user is None:
        raise ConfigError('su/sudo execution requires an explicit target user')
    return {'via': via, 'user': user}


def console_command(argv, kwargs):
    """Translate argv and one-shot stdin without persistent target files or shell interpolation."""
    if not isinstance(argv, (list, tuple)) or not argv or any(not isinstance(v, str) or '\x00' in v for v in argv):
        raise ConfigError('privileged command requires a nonempty string argv sequence')
    options = dict(kwargs)
    data = options.pop('input', None)
    def quote(value):
        if any(ord(char) < 32 or char in '\u0085\u2028\u2029' for char in value):
            return "$'" + ''.join('\\' + format(byte, '03o') for byte in value.encode('utf-8')) + "'"
        return shlex.quote(value)
    command = ' '.join(quote(value) for value in argv)
    if data is not None:
        if isinstance(data, str):
            data = data.encode('utf-8')
        if not isinstance(data, bytes):
            raise ConfigError('command input must be text, bytes or None')
        # POSIX printf %b accepts \0ddd escapes, including NUL. Only octal digits
        # reach the shell; EOF follows even for empty input. No temp files/target Python.
        encoded = ''.join('\\0' + format(byte, '03o') for byte in data)
        command = "printf '%b' " + shlex.quote(encoded) + ' | ' + command
    else:
        # A finite Session command must not consume the console's control channel.
        command += ' < /dev/null'
    return command, options


def validate_evidence(value):
    required = {'contract_version', 'requested', 'login', 'actual', 'verified', 'restoration_verified'}
    if (not isinstance(value, dict) or not required <= set(value) or set(value) - required - {'error_type'}
            or value['contract_version'] != VERSION or type(value['verified']) is not bool
            or type(value['restoration_verified']) is not bool):
        raise ConfigError('invalid execution identity evidence')
    normalize(value['requested'])
    from host_runtime import username
    for field in ('login', 'actual'):
        actual = value[field]
        if actual is None:
            continue
        if not isinstance(actual, dict) or set(actual) != {'username', 'effective_uid'}:
            raise ConfigError('invalid execution account evidence')
        username(actual['username'])
        if type(actual['effective_uid']) is not int or actual['effective_uid'] < 0:
            raise ConfigError('invalid execution effective UID')
    if value['verified'] and (value['login'] is None or value['actual'] is None):
        raise ConfigError('verified execution requires observed identities')
    return value


def result_command(result, argv):
    """Retain JobResult fields/capture evidence while reporting the caller's argv, not stdin."""
    from dataclasses import replace
    return replace(result, command=tuple(argv))


class ConsoleJob:
    """Scoped managed-job facade, preserving the public job operations and argv metadata."""
    def __init__(self, job, argv):
        self._job, self.command = job, tuple(argv)

    def __enter__(self):
        self._job.__enter__()
        return self

    def __exit__(self, *args):
        return self._job.__exit__(*args)

    def wait(self):
        return result_command(self._job.wait(), self.command)

    def stop(self):
        return result_command(self._job.stop(), self.command)

    @property
    def result(self):
        value = self._job.result
        return result_command(value, self.command) if value is not None else None

    def __getattr__(self, name):
        return getattr(self._job, name)


def console_exec(actor, argv, kwargs):
    command, options = console_command(argv, kwargs)
    budget = options.pop('command_timeout')
    if 'timeout' in options:
        raise ConfigError('use command_timeout for scoped exec_command')
    with actor.start(command, timeout=budget, **options) as job:
        return result_command(job.wait(), argv)
