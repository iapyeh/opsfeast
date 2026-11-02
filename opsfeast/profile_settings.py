"""Configuration-only profile management through existing Core interfaces."""
import hashlib
from pathlib import Path

from . import ConfigError, load_profiles, registry_path, instance_definition, definition_path, read_yaml
from .site import SiteConflict


def revision(installation):
    path=registry_path(installation)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ConfigError('profile registry must be a regular file')
    return hashlib.sha256(path.read_bytes() if path.exists() else b'no-profile-registry').hexdigest()


def check_revision(installation, expected):
    if not isinstance(expected,str) or revision(installation)!=expected:
        raise SiteConflict('profile registry changed; reload before saving')


def inspect(installation):
    from .core import Instance
    root=Path(installation).resolve(strict=True)
    for _ in range(3):
        before=revision(root)
        registry=load_profiles(root)
        rows=[]
        for name,value in Instance.open(root).profiles.list().items():
            namespace=None
            definition_status='unknown'
            try:
                profile_root=Path(value['root'])
                if definition_path(profile_root).exists():
                    instance_definition(profile_root)
                    namespace=read_yaml(definition_path(profile_root)).get('namespace')
                    definition_status='present'
                else: definition_status='missing'
            except (ConfigError,OSError): definition_status='invalid'
            rows.append(dict(value,name=name,namespace=namespace,definition_status=definition_status))
        if before==revision(root):
            return {'revision':before,'default_profile':registry['default_profile'],'profiles':rows,
                    'connectivity_verified':False}
    raise SiteConflict('profile registry changed while reading')


def create(installation, data_root, *, name, expected_revision, namespace=None):
    from .core import Instance
    from . import profile_name
    from .site import _root
    name=profile_name(name)
    check_revision(installation,expected_revision)
    parent=_root(data_root)/'profiles'
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise ConfigError('profile container must be a real directory')
    target=parent/name
    Instance.open(installation).init_profile(name,root=target,namespace=namespace,
                                            expected_revision=expected_revision,create_only=True)
    return inspect(installation)


def use(installation, *, name, expected_revision):
    from .core import Instance
    Instance.open(installation).profiles.use(name,expected_revision=expected_revision)
    return inspect(installation)


def attach(installation, *, root, name, expected_revision):
    from .core import Instance
    if not isinstance(root,str) or not Path(root).is_absolute(): raise ConfigError('existing profile root must be absolute')
    Instance.open(installation).profiles.attach(root,name=name,expected_revision=expected_revision)
    return inspect(installation)
