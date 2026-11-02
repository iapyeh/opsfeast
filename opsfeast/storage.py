"""Explicit product/data separation for installation identity and presentation."""
import argparse
import hashlib
import json
from pathlib import Path

from . import ConfigError

BINDING = '.opsfeast-storage.json'
MARKER = '.opsfeast-data.json'


def _directory(path):
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise ConfigError('storage root must be a directory')
    return path


def _json(path):
    if path.is_symlink() or not path.is_file():
        raise ConfigError('storage metadata must be a regular file')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ConfigError('duplicate storage field')
            result[key] = value
        return result
    try:
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs)
    except (ValueError, UnicodeError):
        raise ConfigError('invalid storage metadata') from None


def validate_data_root(path):
    root = _directory(path)
    if _json(root / MARKER) != {'schema_version': '0.1.0', 'kind': 'opsfeast-installation-data'}:
        raise ConfigError('unsupported installation data root')
    return root


def resolve_data_root(installation, *, data_root=None, required=False):
    """Reads never initialize. An invalid binding never falls back to product data."""
    root = _directory(installation)
    if data_root is not None:
        data = validate_data_root(data_root)
    elif (root / BINDING).exists() or (root / BINDING).is_symlink():
        value = _json(root / BINDING)
        if (not isinstance(value, dict) or set(value) != {'schema_version', 'data_root'}
                or value['schema_version'] != '0.1.0' or not isinstance(value['data_root'], str)
                or not Path(value['data_root']).is_absolute()):
            raise ConfigError('invalid installation storage binding')
        data = validate_data_root(value['data_root'])
    elif (root / MARKER).exists():
        return validate_data_root(root)
    elif required:
        raise ConfigError('select an external installation data root before starting Web')
    else:
        # Existing Core callers without a configured data root retain their contract.
        return root
    if data == root or data.is_relative_to(root) or root.is_relative_to(data):
        raise ConfigError('product and installation data directories must be separate')
    return data


def bind_data_root(installation, data_root):
    """Attach an existing data root to a product checkout; refuse implicit rebinding."""
    from .identity import read_identity, _locked
    from .site import _atomic
    root = _directory(installation)
    data = resolve_data_root(root, data_root=data_root)
    if read_identity(data)['identity_status'] != 'assigned':
        raise ConfigError('data root identity is unassigned or moved; reconcile explicitly')
    from . import site
    settings = site.read_site(data)
    for key in ('logo', 'avatar'):
        if settings[key] is not None:
            asset = site.image_path(data, settings[key])
            if hashlib.sha256(asset.read_bytes()).hexdigest() + '.png' != settings[key]:
                raise ConfigError('referenced data asset digest mismatch')
    target = root / BINDING
    with _locked(target):
        if target.exists() or target.is_symlink():
            if resolve_data_root(root) != data:
                raise ConfigError('checkout already bound to another data root')
            return data
        _atomic(target, (json.dumps({'schema_version': '0.1.0', 'data_root': str(data)}, indent=2)+'\n').encode())
    return data


def initialize_data_root(installation, destination):
    """Explicit one-time preserved copy of identity/site assets, not a general importer.

    Requires an absent destination. No source files are removed. The final binding
    is written only after the copied data validates. Profiles/registries stay put.
    """
    from .identity import read_identity, initialize_identity, NIL_UUID, _locked
    from . import site
    root = _directory(installation)
    if (root / BINDING).exists() or (root / MARKER).exists():
        raise ConfigError('installation already uses a data root; attach it instead')
    destination = Path(destination).expanduser()
    if not destination.is_absolute():
        raise ConfigError('destination must be absolute')
    destination = destination.parent.resolve(strict=True) / destination.name
    if destination.exists() or destination.is_symlink():
        raise ConfigError('destination already exists; it will not be overwritten')
    if destination.is_relative_to(root) or root.is_relative_to(destination):
        raise ConfigError('data destination must be outside the product checkout')
    with _locked(root / '.opsfeast-instance.json'), _locked(root / site.FILENAME):
        identity = read_identity(root)
        source_settings = root / site.FILENAME
        snapshot = None
        if source_settings.exists() or source_settings.is_symlink():
            snapshot = site.validate_site(_json(source_settings))
        source_assets = root / site.ASSET_DIRECTORY
        if source_assets.is_symlink() or (source_assets.exists() and not source_assets.is_dir()):
            raise ConfigError('source asset directory is invalid')
        assets = []
        if source_assets.exists():
            for source in source_assets.iterdir():
                if source.is_symlink() or not source.is_file() or not site.ASSET_ID.fullmatch(source.name):
                    raise ConfigError('unexpected source asset; review before initialization')
                content = source.read_bytes()
                if hashlib.sha256(content).hexdigest()+'.png' != source.name:
                    raise ConfigError('source asset digest mismatch')
                assets.append((source.name, content))
        if snapshot and any(snapshot[key] and snapshot[key] not in {name for name,_ in assets} for key in ('logo','avatar')):
            raise ConfigError('referenced source asset is missing')
        destination.mkdir(mode=0o700)
        # Failure leaves the candidate for inspection; it never removes source data.
        site._atomic(destination / MARKER, b'{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}\n')
        initialize_identity(destination, identifier=identity['id'] if identity['id'] != NIL_UUID else None,
                            name=identity['name'] if identity['name'] != identity['id'] else None,
                            description=identity['description'])
        if snapshot:
            site._atomic(destination / site.FILENAME, (json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n').encode())
        if assets:
            target_assets = site._assets(destination,create=True)
            for name,content in assets:
                site._atomic(target_assets / name,content)
                if (target_assets/name).read_bytes() != content:
                    raise ConfigError('copied asset verification failed')
        if site.read_site(destination) != (snapshot or site.DEFAULT):
            raise ConfigError('copied settings verification failed')
        return bind_data_root(root,destination)


def main():
    parser = argparse.ArgumentParser(description='Initialize or attach persistent installation identity/site data. '
                                     'Never moves profile data, connects to hosts or removes source files.')
    parser.add_argument('action',choices=['init','attach','show'])
    parser.add_argument('--installation',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--data-root',type=Path)
    args=parser.parse_args()
    try:
        if args.action=='show':
            result=resolve_data_root(args.installation,data_root=args.data_root,required=True)
        elif args.data_root is None:
            parser.error('--data-root is required for init/attach')
        else:
            result=(initialize_data_root if args.action=='init' else bind_data_root)(args.installation,args.data_root)
        print(json.dumps({'data_root':str(result)},ensure_ascii=False))
    except (ConfigError,OSError) as exc:
        parser.exit(1,f'Storage operation failed: {exc}\n')


if __name__=='__main__':
    main()
