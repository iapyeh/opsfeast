"""Installation-data Web endpoint 0.2.0; reads never allocate or initialize."""
import argparse
import io
import json
from pathlib import Path
import socket
from uuid import uuid4

from . import ConfigError, load_profiles, mapping
from .identity import _locked
from .site import _atomic
from .storage import resolve_data_root, _json

VERSION = '0.2.0'
FILENAME = 'web-server.json'


def validate(value):
    # Also used to validate the old registry entry for explicit transfer only.
    settings=mapping(value,'web',('port',))
    port=settings.get('port')
    if type(port) is not int or not 1024<=port<=65535:
        raise ConfigError('web port must be an integer between 1024 and 65535')
    return port


def _read(root):
    path=root/FILENAME
    if not path.exists() and not path.is_symlink():return None
    if path.is_symlink() or not path.is_file() or path.stat().st_size>8192:
        raise ConfigError('invalid Web endpoint settings file')
    data=_json(path)
    if not isinstance(data,dict) or set(data)!={'schema_version','port'} or data['schema_version']!=VERSION:
        raise ConfigError('unsupported Web endpoint settings schema')
    return validate({'port':data['port']})


def _write(root,port):
    _atomic(root/FILENAME,(json.dumps({'schema_version':VERSION,'port':validate({'port':port})},indent=2)+'\n').encode())


def _require_external_port(installation):
    if 'web' in load_profiles(installation):
        raise ConfigError('Web port is still in the profile registry; run opsfeast.web_settings migrate-port before starting')


def read_port(installation, *, data_root=None):
    root=resolve_data_root(installation,data_root=data_root,required=True)
    _require_external_port(installation)
    return _read(root)


def configure_port(installation,port, *, data_root=None):
    """Save an explicitly selected port in existing installation data; never bind."""
    validate({'port':port})
    root=resolve_data_root(installation,data_root=data_root,required=True)
    _require_external_port(installation)
    with _locked(root/FILENAME):
        _read(root)  # Refuse to overwrite malformed data.
        _write(root,port)
    return port


def bind_server(installation,port=None, *, data_root=None):
    """Reserve loopback before saving; preserve the chosen installation's port."""
    root=resolve_data_root(installation,data_root=data_root,required=True)
    _require_external_port(installation)
    with _locked(root/FILENAME):
        saved=_read(root)
        if saved is None and port is None and (root/'.opsfeast-admin.json').exists():
            raise ConfigError('existing administrator data has no saved Web port; recover the original port before starting')
        chosen=validate({'port':port}) if port is not None else (saved or 0)
        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(('127.0.0.1',chosen));sock.listen(2048)
            actual=sock.getsockname()[1]
            if saved!=actual:_write(root,actual)
            return sock
        except BaseException:
            sock.close()
            raise


def migrate_port(installation, *, data_root=None):
    """Explicit one-time port transfer; preserve registry comments and all data."""
    product=Path(installation).resolve(strict=True)
    root=resolve_data_root(product,data_root=data_root,required=True)
    registry=product/'.opsfeast.yaml'
    with _locked(product/'.opsfeast-profiles.json'),_locked(root/FILENAME):
        data=load_profiles(product);saved=_read(root)
        if 'web' not in data:
            if saved is None:raise ConfigError('no existing Web port to transfer; do not allocate a replacement during an update')
            return {'port':saved,'data_root':str(root),'status':'already_external','backup':None}
        port=validate(data['web'])
        if saved is not None and saved!=port:
            raise ConfigError('registry and installation-data ports conflict; neither was overwritten')
        original=registry.read_bytes()
        try:from ruamel.yaml import YAML
        except ImportError:raise ConfigError('port transfer requires requirements-host-settings.txt in the selected Web environment') from None
        yaml=YAML();yaml.preserve_quotes=True
        document=yaml.load(original.decode('utf-8'));del document['web']
        stream=io.StringIO();yaml.dump(document,stream);updated=stream.getvalue().encode()
        backups=root/'web-port-backups'
        if backups.is_symlink() or (backups.exists() and not backups.is_dir()):raise ConfigError('invalid port transfer backup directory')
        backups.mkdir(mode=0o700,exist_ok=True)
        backup=backups/(str(uuid4())+'.yaml')
        if registry.read_bytes()!=original:raise ConfigError('profile registry changed during port transfer')
        _atomic(backup,original)
        if saved is None:_write(root,port)
        if registry.read_bytes()!=original:raise ConfigError('profile registry changed; copied port and backup preserved, reconcile before continuing')
        _atomic(registry,updated)
        assert load_profiles(product)=={key:value for key,value in data.items() if key!='web'}
        return {'port':port,'data_root':str(root),'status':'transferred','backup':str(backup)}


def main():
    parser=argparse.ArgumentParser(description='Read/configure a persistent Web port or explicitly transfer its old registry setting. No server or host execution.')
    parser.add_argument('action',choices=['show','set','migrate-port'])
    parser.add_argument('--installation',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--data-root',type=Path)
    parser.add_argument('--port',type=int)
    args=parser.parse_args()
    try:
        if args.action=='migrate-port':result=migrate_port(args.installation,data_root=args.data_root)
        else:
            root=resolve_data_root(args.installation,data_root=args.data_root,required=True)
            if args.action=='set':
                if args.port is None:parser.error('set requires --port')
                configure_port(args.installation,args.port,data_root=root)
            result={'schema_version':VERSION,'data_root':str(root),'port':read_port(args.installation,data_root=root)}
        print(json.dumps(result))
    except (ConfigError,OSError,ValueError) as exc:parser.exit(1,f'Web endpoint operation failed: {exc}\n')


if __name__=='__main__':main()
