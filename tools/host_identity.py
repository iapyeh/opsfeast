"""Best-effort, read-only identity evidence; hardware is not an OS installation."""
from datetime import datetime, timezone
import hashlib
import hmac
import plistlib
import re
import shlex

from host_runtime import identity, privilege_password

VERSION = '0.1.0'
WARNING = ('Using a source-scoped host_id fallback: cross-installation identity and host '
           'replacement cannot be established. Inspect identity.evidence; enable identity_sudo '
           'only for authorized read-only probes if permissions are the cause. Hardware serial '
           'alone cannot distinguish OS reinstallations. Keep targets separate until identity '
           'is confirmed; no automatic historical reassignment is performed.')


def now():
    return datetime.now(timezone.utc).isoformat()


def usable(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 256:
        raise ValueError('missing or invalid identifier')
    value = value.strip()
    if '\n' in value or '\r' in value or '\x00' in value:
        raise ValueError('invalid identifier')
    compact = value.lower().replace('-', '').replace(' ', '')
    if compact in {'defaultstring', 'tobefilledbyo.e.m.', 'unknown', 'none', 'notspecified'} or set(compact) <= {'0'} or set(compact) <= {'f'}:
        raise ValueError('placeholder identifier')
    return value


def machine_id(value):
    value = usable(value).lower()
    if not re.fullmatch('[0-9a-f]{32}', value):
        raise ValueError('invalid Linux machine-id')
    # Domain separation: do not publish the original machine-id.
    return hmac.new(b'opsfeast:os-instance:linux:v1', bytes.fromhex(value), hashlib.sha256).hexdigest()


def esxi_platform(text):
    fields = {}
    for line in text.splitlines():
        key, separator, value = line.strip().partition(':')
        if separator:
            fields[key] = value.strip()
    return fields


def probe_identity(session, config, host, facts, timeout, *, allow_sudo=None):
    """Run fixed probes unprivileged first; optional login-account sudo only."""
    platform = facts.get('os_name')
    report = {'schema_version': VERSION, 'evidence': [], 'sudo': {'status': 'not_needed'},
              'method': 'source-host-id', 'quality': 'fallback', 'os_instance_key': None,
              'reason': 'os_installation_identifier_unavailable', 'warnings': []}
    probes = []
    if platform == 'linux':
        probes = [('linux-machine-id', 'os-installation', ['cat', '/etc/machine-id'], machine_id),
                  ('system-serial', 'device', ['cat', '/sys/class/dmi/id/product_serial'], usable),
                  ('hardware-uuid', 'device', ['cat', '/sys/class/dmi/id/product_uuid'], usable)]
    elif platform == 'freebsd':
        probes = [('system-serial', 'device', ['kenv', '-q', 'smbios.system.serial'], usable),
                  ('hardware-uuid', 'device', ['kenv', '-q', 'smbios.system.uuid'], usable)]
    elif platform == 'macos':
        def mac_value(key):
            def parse(text):
                nodes = plistlib.loads(text.encode())
                return usable(nodes[0].get(key))
            return parse
        probes = [('system-serial', 'device', ['/usr/sbin/ioreg', '-a', '-r', '-d', '1', '-c', 'IOPlatformExpertDevice'], mac_value('IOPlatformSerialNumber')),
                  ('hardware-uuid', 'device', ['/usr/sbin/ioreg', '-a', '-r', '-d', '1', '-c', 'IOPlatformExpertDevice'], mac_value('IOPlatformUUID'))]
    elif platform == 'esxi':
        def esxi_value(key):
            return lambda text: usable(esxi_platform(text).get(key))
        probes = [('system-serial', 'device', ['esxcli', 'hardware', 'platform', 'get'], esxi_value('Serial Number')),
                  ('enclosure-serial', 'device', ['esxcli', 'hardware', 'platform', 'get'], esxi_value('Enclosure Serial Number')),
                  ('hardware-uuid', 'device', ['esxcli', 'hardware', 'platform', 'get'], esxi_value('UUID'))]

    command_cache = {}

    def attempt(spec, actor, elevated=False):
        name, scope, argv, parser = spec
        item = {'kind': name, 'scope': scope, 'status': 'command_failed', 'value': None,
                'observed_at': now(), 'via': 'sudo' if elevated else 'login', 'command': argv}
        try:
            cache_key = (elevated, tuple(argv))
            if cache_key not in command_cache:
                command_cache[cache_key] = (actor(shlex.join(argv), check=False, command_timeout=timeout) if elevated
                                           else actor.exec_command(argv, check=False, command_timeout=timeout))
            result = command_cache[cache_key]
            if result.exitcode == 0:
                try:
                    item.update(value=parser(result.stdout), status='success')
                except (ValueError, TypeError, KeyError, IndexError, plistlib.InvalidFileException):
                    item['status'] = 'invalid_or_unavailable'
            else:
                item['status'] = 'command_failed'
        except Exception as exc:
            item.update(status='probe_failed', error_type=type(exc).__name__)
        # Never retain stdout/stderr or third-party exception text in identity.
        report['evidence'].append(item)
        return item['status']

    # Root cannot repair a parsed placeholder or invent a missing identifier.
    pending = [spec for spec in probes if attempt(spec, session) in ('command_failed', 'probe_failed')]
    if pending and allow_sudo is None:
        # Explicit sudo credentials indicate supplied capability. A login password
        # alone does not opt in. No account enumeration or alternate-user su.
        try:
            login_name = identity(session, timeout)['username']
            account = config.hosts[host].get('users', {}).get(login_name, {})
            settings = (account.get('vars', {}).get('sudo', {}), config.hosts[host].get('vars', {}).get('sudo', {}))
            allow_sudo = any(isinstance(value, dict) and isinstance(value.get('password'), str) for value in settings)
        except Exception:
            allow_sudo = False
    if pending and allow_sudo:
        login = None
        attempted = False
        entered = False
        context_failed = False
        try:
            login = identity(session, timeout)
            password, _ = privilege_password(config, host, login['username'], 'sudo', login['username'])
            # Explicit allow_sudo also permits a configured passwordless policy.
            attempted = True
            with session.sudo(username='root', password=password, enter_timeout=timeout) as root:
                entered = True
                identity(root, timeout, console=True, target='root')
                for spec in pending:
                    attempt(spec, root, True)
            if identity(session, timeout) != login:
                raise RuntimeError('identity restoration failed')
            report['sudo']['status'] = 'completed'
        except Exception as exc:
            context_failed = entered
            report['sudo'].update(status='failed', error_type=type(exc).__name__)
        finally:
            try:
                report['sudo']['cleanup_verified'] = (not attempted or login is not None and identity(session, timeout) == login) and not context_failed
            except Exception:
                report['sudo']['cleanup_verified'] = False
    elif pending:
        report['sudo']['status'] = 'not_enabled'
    keys = [item['value'] for item in report['evidence']
            if item['kind'] == 'linux-machine-id' and item['status'] == 'success']
    if keys:
        report.update(method='linux-machine-id-hmac-sha256-v1', quality='machine-derived',
                      os_instance_key='linux:' + keys[-1], reason='machine_id_observed')
        report['warnings'].append('Linux machine-id can be duplicated by images/clones or preserved across reinstallations. This is identity evidence, not proof of uniqueness.')
    else:
        report['warnings'].append(WARNING)
    assigned = config.hosts[host].get('identity_key')
    if assigned is not None:
        report.update(method='configured-identity-key-v1', quality='user-assigned',
                      identity_key=assigned, os_instance_key='user:' + hashlib.sha256(assigned.encode()).hexdigest(),
                      reason='configured_identity_key')
        report['warnings'] = ['User-assigned identity asserts the same OS installation across collectors. Use a shared namespace; change this key after reinstall/replacement. It is not machine-verified.']
    return report
