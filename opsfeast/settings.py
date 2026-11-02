"""Settings capability catalog and presentation CLI; no operational config writes."""
import argparse
import copy
import json
from pathlib import Path

from . import ConfigError

_CATEGORIES = [
    {'id': 'site', 'scope': 'installation', 'status': 'available', 'route': '/settings/site',
     'apis': ['GET /api/v1/site', 'POST /api/v1/site/unlock', 'POST /api/v1/site/lock', 'GET /api/v1/site/settings', 'PUT /api/v1/site/settings', 'POST /api/v1/site/images', 'GET /api/v1/admin', 'POST /api/v1/admin/bootstrap', 'PUT /api/v1/admin'],
     'cli': ['python -B -m opsfeast.settings site show', 'python -B -m opsfeast.settings site update'],
     'guide': 'docs/site-presentation.md'},
    {'id': 'profiles', 'scope': 'installation', 'status': 'available', 'route': '/settings/profiles',
     'apis': ['GET /api/v1/profiles', 'POST /api/v1/profiles', 'PUT /api/v1/profiles/default', 'POST /api/v1/profiles/attach'],
     'cli': ['python -B tools/opsfeast.py profiles --json', 'python -B tools/opsfeast.py init', 'python -B tools/opsfeast.py attach', 'python -B tools/opsfeast.py use'],
     'guide': 'docs/profiles.md'},
    {'id': 'hosts', 'scope': 'profile', 'status': 'available', 'route': '/hosts',
     'apis': ['GET /api/v1/hosts','POST /api/v1/hosts','PATCH /api/v1/hosts','DELETE /api/v1/hosts'],
     'cli': ['python -B -m opsfeast.host_settings --profile NAME list', 'python -B -m opsfeast.host_settings --profile NAME create HOST --expected-revision REV', 'python -B -m opsfeast.host_settings --profile NAME update HOST --expected-revision REV', 'python -B -m opsfeast.host_settings --profile NAME delete HOST --expected-revision REV --confirm-host HOST'], 'guide': 'docs/web-hosts.md'},
    {'id': 'recipes', 'scope': 'profile', 'status': 'planned', 'route': '/settings/recipes',
     'apis': [], 'cli': [], 'guide': 'docs/recipe-sources.md'},
    {'id': 'parameters', 'scope': 'profile', 'status': 'planned', 'route': '/settings/parameters',
     'apis': [], 'cli': [], 'guide': 'docs/recipe-sources.md'},
    {'id': 'retention', 'scope': 'profile', 'status': 'planned', 'route': '/settings/retention',
     'apis': [], 'cli': [], 'guide': 'docs/retention.md'},
]


def catalog():
    """Static availability only; never imports candidate programs or reads profiles."""
    return {'schema_version': '0.1.0', 'categories': copy.deepcopy(_CATEGORIES)}


def update_site(data_root, *, expected_revision, changes=None, images=None):
    """Shared CLI/agent composition of the same site services used by Web."""
    from . import site
    settings = site.read_site(data_root)
    if type(expected_revision) is not int or settings['revision'] != expected_revision:
        raise site.SiteConflict('site settings changed; reload before saving')
    changes = {} if changes is None else changes
    images = {} if images is None else images
    if not isinstance(changes, dict) or set(changes) - {'site_name', 'slogan', 'logo', 'avatar'}:
        raise ConfigError('unknown site changes')
    if not isinstance(images, dict) or set(images) - {'logo', 'avatar'} or set(images) & set(changes):
        raise ConfigError('image changes conflict or contain unknown roles')
    candidate = dict(settings, **changes)
    site.validate_site(candidate)
    for role, payload in images.items():
        candidate[role] = site.upload_image(data_root, payload)['asset_id']
    return site.save_site(data_root, candidate, expected_revision=expected_revision)


def main():
    parser = argparse.ArgumentParser(description='Inspect settings capabilities or configure installation presentation. '
                                     'JSON output; no host connections, recipe execution or profile-config writes.')
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('catalog', help='List implemented/planned settings without reading private configuration.',
                       description='Print the versioned static settings capability catalog as JSON. No reads or writes.')
    site_parser = actions.add_parser('site', help='Read or update installation presentation through shared APIs.',
                                    description='Read or update site name/slogan/images. Select persistent data explicitly.')
    commands = site_parser.add_subparsers(dest='site_action', required=True)
    for action in ('show', 'update'):
        command = commands.add_parser(action, help='Read raw settings.' if action == 'show' else 'Save selected fields with revision checking.',
                                      description='Read raw site settings without writes.' if action == 'show' else
                                      'Update selected site fields/images through the same validation as Web; preserves other fields.')
        location = command.add_mutually_exclusive_group()
        location.add_argument('--installation', type=Path, default=None, help='Bound product checkout (default: this trusted checkout).')
        location.add_argument('--data-root', type=Path, help='Existing marked persistent installation data root.')
        if action == 'update':
            command.add_argument('--expected-revision', type=int, required=True, help='Revision returned by site show; stale updates fail.')
            name = command.add_mutually_exclusive_group()
            name.add_argument('--name', help='Site display-name override; does not change instance name/UUID.')
            name.add_argument('--inherit-name', action='store_true', help='Restore inheritance from the existing instance name.')
            command.add_argument('--slogan', help='New slogan; empty string restores the neutral default.')
            for role in ('logo', 'avatar'):
                image = command.add_mutually_exclusive_group()
                image.add_argument('--'+role, type=Path, help='Local PNG/JPEG file, at most 2 MiB.')
                image.add_argument('--default-'+role, action='store_true', help='Use the bundled image; retain uploaded files.')
    admin_parser=actions.add_parser('admin',help='Inspect or configure the single administrator locally.',description='Local administrator metadata; no default credentials. Passwords are read privately, never from argv.')
    admin_commands=admin_parser.add_subparsers(dest='admin_action',required=True)
    for action in ('show','set'):
        command=admin_commands.add_parser(action,help='Show nonsecret account status.' if action=='show' else 'Set username/password with revision and current-password checks.',description='Read nonsecret administrator status.' if action=='show' else 'Configure the administrator locally; prompts only on a terminal, or use explicit JSON password input on stdin.')
        location=command.add_mutually_exclusive_group()
        location.add_argument('--installation',type=Path)
        location.add_argument('--data-root',type=Path)
        if action=='set':
            command.add_argument('--username',required=True)
            command.add_argument('--expected-revision',type=int,required=True)
            command.add_argument('--password-stdin',action='store_true',help='Read JSON with password and optional current_password from stdin; never pass passwords as arguments.')
    args = parser.parse_args()
    try:
        if args.action == 'catalog':
            result = catalog()
        elif args.action=='admin':
            from .storage import resolve_data_root
            from . import admin
            import sys,getpass
            root=resolve_data_root(args.installation or Path(__file__).resolve().parents[1],data_root=args.data_root,required=True)
            if args.admin_action=='show':result=admin.status(root)
            else:
                if args.password_stdin:
                    try:
                        private_input=sys.stdin.read(8193)
                        if len(private_input)>8192:raise ValueError()
                        secrets=json.loads(private_input)
                    except ValueError:raise ConfigError('invalid private password JSON') from None
                    if not isinstance(secrets,dict) or set(secrets)-{'password','current_password'}:raise ConfigError('invalid private password fields')
                    password=secrets.get('password');current_password=secrets.get('current_password')
                else:
                    if not sys.stdin.isatty():parser.error('noninteractive admin set requires --password-stdin')
                    current_password=getpass.getpass('Current password: ') if admin.status(root)['configured'] else None
                    password=getpass.getpass('New password: ')
                    if password!=getpass.getpass('Confirm new password: '):raise ConfigError('password confirmation does not match')
                result=admin.configure(root,username=args.username,password=password,current_password=current_password,expected_revision=args.expected_revision)
        else:
            from .storage import resolve_data_root
            from . import site
            product = args.installation or Path(__file__).resolve().parents[1]
            root = resolve_data_root(product, data_root=args.data_root, required=True)
            if args.site_action == 'show':
                result = site.read_site(root)
            else:
                changes, images = {}, {}
                if args.name is not None: changes['site_name'] = args.name
                elif args.inherit_name: changes['site_name'] = None
                if args.slogan is not None: changes['slogan'] = args.slogan
                for role in ('logo', 'avatar'):
                    if getattr(args, 'default_'+role): changes[role] = None
                    path = getattr(args, role)
                    if path is not None:
                        if not path.is_file() or path.stat().st_size > site.MAX_UPLOAD:
                            raise ConfigError('image must be a local file of at most 2 MiB')
                        with path.open('rb') as stream:
                            payload = stream.read(site.MAX_UPLOAD+1)
                        if len(payload) > site.MAX_UPLOAD: raise ConfigError('image exceeds 2 MiB')
                        images[role] = payload
                if not changes and not images: parser.error('select at least one site change')
                result = update_site(root, expected_revision=args.expected_revision, changes=changes, images=images)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ConfigError, OSError) as exc:
        parser.exit(1, f'Settings operation failed: {exc}\n')


if __name__ == '__main__':
    main()
