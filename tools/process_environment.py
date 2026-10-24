"""Child-only proxy environment policy; never mutate the host process environment."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile

WATCHED = ('NO_COLOR', 'PATH', 'LANG', 'LC_ALL', 'SSH_AUTH_SOCK')


def validate(overrides, where='proxy_environment'):
    from opsfeast import ConfigError
    if not isinstance(overrides, dict):
        raise ConfigError(f'{where}: expected a mapping of environment names to strings or null')
    for name, value in overrides.items():
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
            raise ConfigError(f'{where}: invalid environment variable name')
        if value is not None and (not isinstance(value, str) or '\0' in value):
            raise ConfigError(f'{where}: environment values must be strings without NUL or null')
    return dict(overrides)


def proxy_policy(overrides=None, *, environ=None):
    """Return child overrides and value-free evidence, from an explicit snapshot."""
    ambient = dict(os.environ if environ is None else environ)
    configured = validate({} if overrides is None else overrides)
    changes, evidence = {}, {}
    # NO_COLOR is a presence convention; Rust CLI boolean parsers often require
    # true/false instead. Empty means no request, so remove it in the proxy only.
    if 'NO_COLOR' in ambient:
        changes['NO_COLOR'] = 'true' if ambient['NO_COLOR'] else None
        evidence['NO_COLOR'] = {'source': 'normalized_inherited',
                                'action': 'set' if ambient['NO_COLOR'] else 'remove'}
    for name, value in configured.items():
        changes[name] = value
        evidence[name] = {'source': 'connection.proxy_environment',
                          'action': 'remove' if value is None else 'set'}
    return changes, {'policy_version': '0.1.0', 'inherit': True,
                     'ambient_presence': {name: name in ambient for name in WATCHED},
                     'variables': evidence}


def inspect_environment():
    """Read-only, value-free local readiness diagnostic; no execution or writes."""
    _, evidence = proxy_policy()
    return evidence


@contextmanager
def proxy_options(settings, evidence):
    """Prepare one public Session.connect call and remove private launch material.

    The launcher execs the original argv, retaining PID/stdin/stdout for SSHScript
    ownership. Environment values never enter argv or ordinary diagnostics.
    """
    options = dict(settings)
    overrides = options.pop('proxy_environment', {})
    if not options.get('proxy_command'):
        yield options
        return
    from opsfeast import ConfigError
    changes, receipt = proxy_policy(overrides)
    evidence['proxy_environment'] = receipt
    try:
        argv = shlex.split(options['proxy_command'])
    except ValueError:
        raise ConfigError('proxy command has invalid argument quoting') from None
    if not argv:
        raise ConfigError('proxy command must contain an executable')
    if not changes:
        yield options
        return
    fd, name = tempfile.mkstemp(prefix='opsfeast-proxy-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'argv': argv, 'environment': changes}, stream)
        launcher = Path(__file__).with_name('proxy_launcher.py').resolve()
        options['proxy_command'] = shlex.join([sys.executable, '-I', '-B', str(launcher), name])
        yield options
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass  # Launcher removes it before exec; parent covers start failures.
