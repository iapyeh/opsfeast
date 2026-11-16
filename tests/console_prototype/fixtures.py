"""Explicit simulated accounts/transports on real local Bash; never invokes su/sudo."""
from contextlib import contextmanager
from types import SimpleNamespace
from sshscript import Session


class FixtureShell:
    def __init__(self, wrapper, owner, user, fail_identity=False, fail_exit=False):
        self.wrapper, self.owner, self.user = wrapper, owner, user
        self.channel = wrapper.channel
        self.fail_identity, self.fail_exit = fail_identity, fail_exit
        self.active = None

    def __enter__(self):
        self.active = self.wrapper.__enter__()
        self.owner.open_layers += 1
        return self

    def __exit__(self, *args):
        try:
            return self.wrapper.__exit__(*args)
        finally:
            self.owner.open_layers -= 1
            if self.fail_exit:
                raise RuntimeError('synthetic cleanup failure')

    def __call__(self, command, **kwargs):
        if command == 'id -un':
            if self.fail_identity:
                raise ConnectionError('synthetic identity probe failure')
            return SimpleNamespace(stdout=self.user+'\n', stderr='', exitcode=0)
        return self.active(command, **kwargs)

    def __getattr__(self, name):
        return getattr(self.active or self.wrapper, name)

    def start(self, *args, **kwargs):
        job = self.active.start(*args, **kwargs)
        if self.owner.fault == 'channel_disconnect':
            self.channel.fail(ConnectionError('synthetic active channel loss'))
        return job

    def shell(self, *args, **kwargs):
        return FixtureShell(self.active.shell(*args, **kwargs), self.owner, self.user)

    def su(self, username, *, password=None, **kwargs):
        self.owner.switch_attempts += 1
        if self.owner.fault == 'auth_failure':
            raise PermissionError(self.owner.synthetic_password)
        if password != self.owner.synthetic_password:
            raise PermissionError('synthetic authentication refusal')
        return FixtureShell(self.active.shell('bash'), self.owner, username,
                            fail_exit=self.owner.fault == 'restoration')

    def sudo(self, *, username='root', password=None, **kwargs):
        return self.su(username, password=password, **kwargs)


class SimulatedSession(Session):
    """Explicit injectable session_class fixture for OpsFeast's connection owner."""
    def __init__(self, fault=None):
        super().__init__()
        self.fault = fault
        self.username = 'fixture-login'
        self.host = 'simulated-target'
        self.open_layers = 0
        self.switch_attempts = 0
        self.connect_calls = 0
        self.owner_close_calls = 0
        self.ancestor = SimpleNamespace(closed=False)
        self.synthetic_password = 'SYNTHETIC_ONLY_' + 'credential_canary_72d'

    def connect(self, *args, **kwargs):
        self.connect_calls += 1
        raise AssertionError('fixture must not reconnect')

    def shell(self, *args, **kwargs):
        wrapper = super().shell(*args, **kwargs)
        return FixtureShell(wrapper, self, 'fixture-login',
                            fail_identity=self.fault == 'initialization',
                            fail_exit=self.fault == 'cleanup')

    def exec_command(self, *args, **kwargs):
        if self.fault == 'disconnect':
            raise ConnectionError('synthetic transport unavailable')
        return super().exec_command(*args, **kwargs)

    def close(self, *args, **kwargs):
        self.owner_close_calls += 1
        return super().close(*args, **kwargs)
