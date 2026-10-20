"""Sanitized read models for private hosts and profiles; no remote operations."""
import re

MASK = '********'


def masked(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = re.sub(r'[^a-z0-9]', '', str(key).lower())
            secret = any(word in normalized for word in ('password', 'passwd', 'passphrase', 'secret', 'token')) or normalized in {'apikey', 'privatekey'}
            result[key] = MASK if secret else masked(item)
        return result
    if isinstance(value, list):
        return [masked(item) for item in value]
    return value


def hosts_snapshot():
    from opsfeast import resolve_root, load_profiles, Validator, group_names
    try:
        profile = load_profiles()['default_profile']
        if profile is None:
            return {'profile': None, 'hosts': [], 'message': 'No default profile. Initialize or attach a Feast first.'}
        root = resolve_root(profile=profile)
        validator = Validator(root)
        validator.load(root / 'hosts.yaml')
        for settings in validator.hosts.values():
            group_names(settings.get('group', []), 'host group')
        sources = {host: str(path) for host, path in validator.sources.items()}
        # Raw settings never cross the boundary into UI state or exception text.
        return {'profile': profile, 'root': str(root), 'default_user_icon': validator.default_user_icon,
                'user_icons': dict(validator.user_icon_defaults), 'groups': masked(validator.groups), 'hosts': [
            {'host': name, 'source': sources[name], 'default_user_icon': validator.host_user_icons[name],
             'settings': masked(settings)}
            for name, settings in validator.hosts.items()], 'message': 'Configuration only; no connectivity or privilege validation.'}
    except Exception as exc:
        return {'profile': None, 'hosts': [], 'message': 'Host settings unavailable: ' + type(exc).__name__}


def profiles_snapshot():
    from opsfeast import load_profiles, profile_root, registered_root, ConfigError
    try:
        data = load_profiles()
        rows = []
        for name, definition in data['profiles'].items():
            root = profile_root(definition['root'])
            status = 'available'
            try:
                registered_root(data, name)
            except ConfigError:
                try:
                    root.stat()
                    status = 'invalid'
                except FileNotFoundError:
                    status = 'missing'
                except OSError:
                    status = 'unavailable'
            except OSError:
                status = 'unavailable'
            rows.append({'name': name, 'root': str(root), 'status': status, 'default': name == data['default_profile']})
        return {'profiles': rows, 'message': 'Switch updates the persisted default; explicit recipe environment selections are preserved.'}
    except Exception as exc:
        return {'profiles': [], 'message': 'Profile registry unavailable: ' + type(exc).__name__}


def grouped_hosts(entries, catalog=None):
    """Stable group/host order; None is a distinct ungrouped bucket."""
    from opsfeast import group_names
    groups = {group: [] for group in catalog or {}}
    for row in entries:
        names = list(dict.fromkeys(group_names(row['settings'].get('group', []), 'host group')))
        for name in names or [None]:
            groups.setdefault(name, []).append(row['host'])
    return groups


def user_accounts(settings):
    """Return configured/local connection identity and declared account names."""
    connection = settings.get('connection', {})
    login = None
    if isinstance(connection, dict):
        if connection.get('local') is True:
            import os
            import pwd
            login = pwd.getpwuid(os.geteuid()).pw_name
        elif not connection.get('ssh_config_alias'):
            login = connection.get('user')
            if not login and connection.get('hostname'):
                import getpass
                login = getpass.getuser()  # Same explicit fallback as connection_plan.
    if not isinstance(login, str) or not login:
        login = None
    users = settings.get('users', {})
    names = list(users) if isinstance(users, dict) else []
    if login and login not in names:
        names.insert(0, login)
    return login, names
