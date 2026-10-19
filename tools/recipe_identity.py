"""Recipe attribution 0.1.0 and local installation author defaults."""
import argparse
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = '.opsfeast-author.yaml'
BUNDLED = ('check/identity', 'check/port', 'inventory/system', 'report/summary', 'report/retention')
UNKNOWN = {'author': {'name': 'Unknown', 'contacts': ['Unknown']}, 'license': 'Unknown'}


def normalized(metadata):
    from opsfeast import ConfigError
    if not isinstance(metadata, dict):
        raise ConfigError('attribution metadata must be a mapping')
    author = metadata.get('author', UNKNOWN['author'])
    license = metadata.get('license', 'Unknown')
    if not isinstance(author, dict) or set(author) != {'name', 'contacts'}:
        raise ConfigError('author requires exactly name and contacts')
    if not isinstance(author['name'], str) or not author['name'].strip():
        raise ConfigError('author.name must be a nonempty string')
    if not isinstance(author['contacts'], list) or not author['contacts'] or any(not isinstance(v,str) or not v.strip() for v in author['contacts']):
        raise ConfigError('author.contacts must be a nonempty list of strings')
    if not isinstance(license, str) or not license.strip():
        raise ConfigError('license must be a nonempty identifier or Unknown')
    return {'author': {'name': author['name'], 'contacts': list(author['contacts'])}, 'license': license}


def reserved(identity):
    return any(value.strip().casefold() == 'bundle' for value in [identity['author']['name'], *identity['author']['contacts']])


def validate(metadata, directory=None, external=False):
    from opsfeast import ConfigError, REPOSITORY_RECIPES
    identity = normalized(metadata)
    builtin = directory is not None and Path(directory).resolve() in {(REPOSITORY_RECIPES/path).resolve() for path in BUNDLED}
    if external or not builtin:
        if reserved(identity):
            raise ConfigError('Bundle author/contact is reserved for built-in OpsFeast recipes; external recipes are rejected')
    elif identity != {'author': {'name':'Bundle','contacts':['Bundle']},'license':'MIT'}:
        raise ConfigError('built-in recipes require Bundle author/contacts and MIT license')
    return identity


def defaults(root=ROOT):
    from opsfeast import ConfigError, read_yaml
    path = root/DEFAULT_FILE
    if not path.exists() and not path.is_symlink():
        return normalized({})
    if path.is_symlink() or not path.is_file():
        raise ConfigError('author defaults must be a regular local file')
    data=read_yaml(path)
    if not isinstance(data,dict) or set(data)!={'schema_version','recipe_defaults'} or type(data['schema_version']) is not int or data['schema_version']!=1:
        raise ConfigError('invalid author defaults schema')
    if not isinstance(data['recipe_defaults'], dict) or set(data['recipe_defaults']) - {'author', 'license'}:
        raise ConfigError('recipe_defaults accepts only author and license')
    identity=validate(data['recipe_defaults'],external=True)
    return identity


def save_field(field, value, root=ROOT):
    """Validate and atomically save one default, preserving the other fields."""
    from opsfeast import ConfigError
    import yaml
    identity = defaults(root)
    if field in {'name', 'contacts'}:
        identity['author'][field] = value
    elif field == 'license':
        identity['license'] = value
    else:
        raise ConfigError('unsupported author default field')
    identity = validate(identity, external=True)
    path = root / DEFAULT_FILE
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root,
                                         prefix=DEFAULT_FILE + '.', delete=False) as stream:
            temporary = Path(stream.name)
            yaml.safe_dump({'schema_version': 1, 'recipe_defaults': identity}, stream,
                           allow_unicode=True, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return identity


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['defaults'])
    parser.add_argument('--json', action='store_true')
    args=parser.parse_args(argv)
    try:
        from console_output import prepare, print_report
        prepare(args.json)
        print_report(defaults(),json_output=args.json)
    except Exception as exc:
        from console_output import ConsoleDependencyError
        if isinstance(exc, ConsoleDependencyError):
            parser.exit(1, f'ERROR: {exc}\n')
        parser.exit(1,f'ERROR: author defaults unavailable ({type(exc).__name__})\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
