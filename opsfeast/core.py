"""Public Core API 0.1.0. No network or writes occur on open/inspection."""
from contextlib import contextmanager
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
import math
from pathlib import Path
import shlex
import threading
from uuid import uuid4

from . import (API_VERSION, ConfigError, Validator, REPOSITORY_ROOT, load_profiles,
               registered_root, profile_root, profile_name, save_profiles, initialize)
from .identity import read_identity, initialize_identity, update_identity


class CoreError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _timeout(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ConfigError('timeout must be positive finite seconds')
    return value


def _masked(value):
    from management_view import masked
    return masked(copy.deepcopy(value))


class Hosts:
    """A validated configuration snapshot; execution uses its private raw values."""
    def __init__(self, root):
        self.root = root
        self.reload()

    def reload(self):
        config = Validator(self.root)
        config.load(config.root / 'hosts.yaml')
        config.check_connections()
        self._config = config
        self.loaded_at = datetime.now(timezone.utc).isoformat()
        return self

    def list(self):
        return {host: self.get(host) for host in self._config.hosts}

    def get(self, host_id, *, reveal_secrets=False):
        if host_id not in self._config.hosts:
            raise ConfigError('unknown host ID')
        value = copy.deepcopy(self._config.hosts[host_id])
        return value if reveal_secrets else _masked(value)


class Profiles:
    def __init__(self, instance):
        self.instance = instance

    def list(self):
        data = load_profiles(self.instance.root)
        items = {}
        for name, item in data['profiles'].items():
            try:
                root = registered_root(data, name, self.instance.root)
                status = 'available'
            except (ConfigError, OSError):
                root = profile_root(item['root'], self.instance.root)
                status = 'unavailable'
            items[name] = {'root': str(root), 'status': status, 'active': name == data['default_profile']}
        return items

    def use(self, name):
        from .identity import _locked
        with _locked(self.instance.root / '.opsfeast-profiles.json'):
            data = load_profiles(self.instance.root)
            registered_root(data, name, self.instance.root)
            data['default_profile'] = name
            save_profiles(data, self.instance.root)
        return self.instance.profile(name)

    def attach(self, root, *, name=None):
        from . import instance_definition, definition_path
        from .identity import _locked
        root = Path(root).expanduser().resolve(strict=True)
        name = profile_name(root.name if name is None else name)
        definition = definition_path(root)
        if definition.exists() or definition.is_symlink():
            instance_definition(root)
        Validator(root).check()
        with _locked(self.instance.root / '.opsfeast-profiles.json'):
            data = load_profiles(self.instance.root)
            if name in data['profiles']:
                if profile_root(data['profiles'][name]['root'], self.instance.root) != root:
                    raise ConfigError('profile name already refers to another root')
            elif any(profile_root(item['root'], self.instance.root) == root for item in data['profiles'].values()):
                raise ConfigError('management root is already registered under another name')
            data['profiles'][name] = {'root': str(root.relative_to(self.instance.root)) if root.is_relative_to(self.instance.root) else str(root)}
            if data['default_profile'] is None:
                data['default_profile'] = name
            save_profiles(data, self.instance.root)
        return self.instance.profile(name)

    def detach(self, name):
        from .identity import _locked
        if name == 'main':
            raise ConfigError('main cannot be detached')
        with _locked(self.instance.root / '.opsfeast-profiles.json'):
            data = load_profiles(self.instance.root)
            if name not in data['profiles']:
                raise ConfigError('unknown profile')
            if data['default_profile'] == name:
                registered_root(data, 'main', self.instance.root)
                data['default_profile'] = 'main'
            del data['profiles'][name]
            save_profiles(data, self.instance.root)


class Instance:
    def __init__(self, installation):
        self.root = Path(installation).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ConfigError('installation must be a directory')
        self.profiles = Profiles(self)

    @classmethod
    def open(cls, installation=None):
        return cls(REPOSITORY_ROOT if installation is None else installation)

    @property
    def identity(self):
        return read_identity(self.root)

    def initialize(self, *, name=None, description=None):
        return initialize_identity(self.root, name=name, description=description)

    def renew_identity(self):
        return initialize_identity(self.root, renew=True)

    def relocate_identity(self):
        return initialize_identity(self.root, relocate=True)

    def update_metadata(self, *, name=None, description=None):
        return update_identity(self.root, name=name, description=description)

    def init_profile(self, name='main', *, root=None):
        name = profile_name(name)
        registry = load_profiles(self.root)
        if root is None and name in registry['profiles']:
            target = profile_root(registry['profiles'][name]['root'], self.root)
        else:
            target = self.root / 'feasts' / name if root is None else Path(root).expanduser().resolve()
        # Resolve conflicts before scaffolding; attach preserves existing names.
        if name in registry['profiles'] and profile_root(registry['profiles'][name]['root'], self.root) != target:
            raise ConfigError('profile name already refers to another root')
        if any(n != name and profile_root(item['root'], self.root) == target for n, item in registry['profiles'].items()):
            raise ConfigError('management root is already registered')
        initialize(target, quiet=True)
        profile = self.profiles.attach(target, name=name)
        self.initialize()
        return profile

    def profile(self, name=None, *, root=None):
        if name is not None and root is not None:
            raise ConfigError('select either profile or management root')
        if root is not None:
            target = Path(root).expanduser().resolve(strict=True)
            data = load_profiles(self.root)
            name = next((n for n, item in data['profiles'].items()
                         if profile_root(item['root'], self.root) == target), None)
            return Profile(self, name, target)
        data = load_profiles(self.root)
        name = data['default_profile'] if name is None else name
        if name is None:
            raise ConfigError('no active profile')
        return Profile(self, name, registered_root(data, name, self.root))

    def inspect(self):
        errors = []
        try:
            identity = self.identity
        except (ConfigError, OSError) as exc:
            identity = None
            errors.append({'component': 'identity', 'type': type(exc).__name__})
        try:
            profiles = self.profiles.list()
        except (ConfigError, OSError) as exc:
            profiles = {}
            errors.append({'component': 'profiles', 'type': type(exc).__name__})
        for name, item in profiles.items():
            if item['status'] != 'available':
                continue
            try:
                current = Hosts(Path(item['root']))
                item['configuration_status'] = 'valid'
                item['host_count'] = len(current._config.hosts)
            except (ConfigError, OSError, RuntimeError, RecursionError) as exc:
                item['configuration_status'] = 'invalid'
                errors.append({'component': 'configuration', 'profile': name, 'type': type(exc).__name__})
        dependencies = {}
        for distribution in ('PyYAML', 'sshscript'):
            try:
                dependencies[distribution] = metadata.version(distribution)
            except metadata.PackageNotFoundError:
                dependencies[distribution] = None
        try:
            product_version = (self.root / 'VERSION').read_text(encoding='utf-8').strip()
        except OSError:
            product_version = None
        return {'product_version': product_version, 'api_version': API_VERSION, 'inspected_at': datetime.now(timezone.utc).isoformat(),
                'status': 'partial' if errors or any(p['status'] != 'available' for p in profiles.values()) else 'success',
                'identity': identity, 'installation': str(self.root), 'profiles': profiles,
                'dependencies': dependencies, 'errors': errors}


class Profile:
    def __init__(self, instance, name, root):
        self.instance, self.name, self.root = instance, name, root
        self.hosts = Hosts(root)
        self.sessions = Sessions(self)

    @classmethod
    def _from_config(cls, instance, config):
        value = object.__new__(cls)
        data = load_profiles(instance.root)
        value.instance, value.root = instance, config.root
        value.name = next((name for name, item in data['profiles'].items()
                           if profile_root(item['root'], instance.root) == config.root), None)
        value.hosts = object.__new__(Hosts)
        value.hosts.root, value.hosts._config = config.root, config
        value.hosts.loaded_at = datetime.now(timezone.utc).isoformat()
        value.sessions = Sessions(value)
        return value

    def reload(self):
        self.hosts.reload()
        return self

    def inspect(self):
        current = Hosts(self.root)
        paths = {name: str(self.root / relative) for name, relative in
                 {'hosts': 'hosts.yaml', 'results': 'observations', 'records': 'records',
                  'runs': 'runs', 'reports': 'reports', 'jobs': 'jobs'}.items()}
        return {'api_version': API_VERSION, 'instance': self.instance.identity, 'profile': self.name,
                'root': str(self.root), 'status': 'success', 'hosts': current.list(), 'paths': paths,
                'configuration_loaded_at': current.loaded_at,
                'loaded_files': sorted(str(p) for p in current._config.loaded),
                'services': {'logging': 'unimplemented', 'notifications': 'unimplemented'},
                'verification': 'configuration snapshot only; no host/provider probes'}

    def results(self, **filters):
        from recipe_reports import results
        return results(self.root, **filters)

    def jobs(self):
        from recipe_jobs import listing
        return listing(self.root)

    @contextmanager
    def recipe(self, host_id, *, vars=None, timeout=30):
        from . import plain_values
        if vars is not None and not isinstance(vars, dict):
            raise ConfigError('recipe vars must be a mapping')
        plain_values(vars or {}, 'recipe vars')
        with self.sessions.connect(host_id, timeout=timeout) as connection:
            yield Recipe._borrow(connection, vars=vars)


@dataclass
class _State:
    active: bool = True
    failed: bool = False
    thread: int = 0
    top: object = None
    identity: object = None


class SessionView:
    """Scoped command facade; close/connect/privilege ownership stays with Core."""
    def __init__(self, owner):
        self._owner = owner

    def exec_command(self, argv, **kwargs):
        owner = self._owner
        owner._check()
        kwargs.setdefault('command_timeout', owner.timeout)
        if owner._console:
            if not isinstance(argv, (list, tuple)) or any(not isinstance(v, str) for v in argv):
                raise ConfigError('privileged exec_command requires a string argv sequence')
            return owner._actor(shlex.join(argv), **kwargs)
        return owner._actor.exec_command(argv, **kwargs)

    def start(self, argv, **kwargs):
        owner = self._owner
        owner._check()
        kwargs.setdefault('timeout', owner.timeout)
        if owner._console:
            if not isinstance(argv, (list, tuple)) or any(not isinstance(v, str) for v in argv):
                raise ConfigError('privileged start requires a string argv sequence')
            return owner._actor.start(shlex.join(argv), **kwargs)
        return owner._actor.start(argv, **kwargs)

    def close(self, *args, **kwargs):
        raise CoreError('session_not_owned')


class Recipe:
    """One execution scope, never a shared mutable recipe definition."""
    def __init__(self):
        raise TypeError('use profile.recipe() or the runner-provided Recipe')

    @classmethod
    def _create(cls, profile, config, host_id, actor, timeout, report, *, state=None, console=False, vars=None, run_id=None, owner='core'):
        value = object.__new__(cls)
        value.profile, value.host_id, value.timeout = profile, host_id, timeout
        value._config, value._actor, value._report = config, actor, report
        value._state = state or _State(thread=threading.get_ident())
        if value._state.identity is None:
            value._state.identity = profile.instance.identity
        value.connection_owner = owner
        value._console, value._active = console, True
        value.vars = copy.deepcopy(vars or {})
        value.run_id = run_id or str(uuid4())
        value.session = SessionView(value)
        value._state.top = value
        return value

    @classmethod
    def _borrow(cls, connection, *, vars=None):
        connection._check()
        connection.vars = copy.deepcopy(vars or {})
        return connection

    @property
    def instance_id(self):
        return self._state.identity['id']

    @property
    def report(self):
        return copy.deepcopy(self._report)

    def _check(self):
        if (not self._active or not self._state.active or self._state.failed or
                self._state.top is not self or self._state.thread != threading.get_ident()):
            raise CoreError('session_scope_unavailable')

    def sudo(self, user='root'):
        return self._privilege('sudo', user)

    def su(self, user):
        return self._privilege('su', user)

    @contextmanager
    def _privilege(self, mode, user):
        from host_runtime import identity, privilege_password, username
        self._check()
        user = username(user)
        try:
            before = identity(self._actor, self.timeout, console=self._console)
            login = self._report.get('connection_identity')
            if login is None:
                login = before
                configured = self._config.hosts[self.host_id]['connection'].get('user')
                if configured:
                    identity(self._actor, self.timeout, console=self._console, target=configured)
                self._report['connection_identity'] = login
        except Exception:
            self._state.failed = True
            self._report['scope_error'] = 'identity_verification_failed'
            raise CoreError('identity_verification_failed') from None
        if mode == 'su' and user not in self._config.hosts[self.host_id].get('users', {}):
            raise ConfigError('su target must be declared in hosts users')
        credential_user = user if mode == 'su' else before['username']
        password, source = privilege_password(self._config, self.host_id, credential_user, mode, login['username'])
        if source == 'sudo_disabled':
            raise CoreError('sudo_disabled')
        if mode == 'su' and password is None:
            raise CoreError('missing_su_password')
        evidence = {'operation': mode, 'target': user, 'status': 'failed', 'password_source': source,
                    'restoration_verified': False}
        self._report.setdefault('privileges', []).append(evidence)
        context = None
        entered = False
        child = None
        error = None
        try:
            context = (self._actor.su(user, password=password, enter_timeout=self.timeout) if mode == 'su'
                       else self._actor.sudo(username=user, password=password, enter_timeout=self.timeout))
            actor = context.__enter__()
            entered = True
            actual = identity(actor, self.timeout, console=True, target=user)
            evidence.update(status='success', actual_identity=actual)
            child = self._create(self.profile, self._config, self.host_id, actor, self.timeout, self._report,
                                 state=self._state, console=True, vars=self.vars, run_id=self.run_id, owner=self.connection_owner)
            yield child
        except BaseException as exc:
            error = exc
            evidence['status'] = 'failed'
            evidence['error_type'] = type(exc).__name__
            raise
        finally:
            if child is not None:
                child._active = False
            self._state.top = self
            try:
                if entered:
                    context.__exit__(type(error) if error else None, error, error.__traceback__ if error else None)
                restored = identity(self._actor, self.timeout, console=self._console)
                evidence['restoration_verified'] = restored == before
                if not evidence['restoration_verified']:
                    raise CoreError('identity_restoration_failed')
            except BaseException as cleanup:
                self._state.failed = True
                evidence.update(status='failed', cleanup_error=type(cleanup).__name__)
                self._report['cleanup_error'] = type(cleanup).__name__
                if error is not None:
                    error.add_note('Privilege cleanup/restoration failed; session disabled.')
                else:
                    raise CoreError('identity_restoration_failed') from None


class Sessions:
    def __init__(self, profile):
        self.profile = profile

    @contextmanager
    def connect(self, host_id, *, timeout=30):
        from host_runtime import runtime_class
        timeout = _timeout(timeout)
        with self._connect(host_id, timeout=timeout, session_class=runtime_class()) as connection:
            yield connection

    @contextmanager
    def _connect(self, host_id, *, timeout=30, session_class):
        from host_runtime import connected
        timeout = _timeout(timeout)
        config = copy.deepcopy(self.profile.hosts._config)
        if host_id not in config.hosts:
            raise ConfigError('unknown host ID')
        if not config.hosts[host_id].get('enabled', True):
            raise CoreError('host_disabled')
        report = {'status': 'failed', 'host_id': host_id, 'instance_id': self.profile.instance.identity['id'],
                  'profile': self.profile.name}
        value, error = None, None
        try:
            with connected(config, host_id, session_class, timeout, report) as session:
                value = Recipe._create(self.profile, config, host_id, session, timeout, report)
                report['status'] = 'success'
                yield value
        except BaseException as exc:
            error = exc
            report['status'] = 'failed'
            raise
        finally:
            if value:
                value._state.active = False
                value._active = False
            if report.get('scope_error') and not error:
                raise CoreError(report['scope_error'])
            if report.get('cleanup_error'):
                report['status'] = 'failed'
                if error:
                    error.add_note('Session cleanup failed; see connection.report.')
                else:
                    raise CoreError('session_cleanup_failed') from None
