"""Checkout-local Web endpoint settings; no host execution or process takeover."""
from pathlib import Path
import socket

from . import ConfigError, load_profiles, save_profiles, mapping
from .identity import _locked


def validate(value):
    settings=mapping(value, 'web', ('port',))
    port=settings.get('port')
    if type(port) is not int or not 1024<=port<=65535:
        raise ConfigError('web.port must be an integer between 1024 and 65535')
    return port


def read_port(installation):
    data=load_profiles(installation)
    return validate(data['web']) if 'web' in data else None


def configure_port(installation, port):
    """Persist an explicit endpoint, preserving profile registrations. Does not bind."""
    validate({'port':port})
    root=Path(installation).resolve(strict=True)
    with _locked(root/'.opsfeast-profiles.json'):
        data=load_profiles(root)
        data['web']={'port':port}
        save_profiles(data,root)
    return port


def bind_server(installation, port=None):
    """Reserve loopback before saving; automatic selection occurs only once."""
    root=Path(installation).resolve(strict=True)
    with _locked(root/'.opsfeast-profiles.json'):
        data=load_profiles(root)
        chosen=validate({'port':port}) if port is not None else (validate(data['web']) if 'web' in data else 0)
        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(('127.0.0.1',chosen))
            sock.listen(2048)
            actual=sock.getsockname()[1]
            if data.get('web')!={'port':actual}:
                data['web']={'port':actual}
                save_profiles(data,root)
            return sock
        except BaseException:
            sock.close()
            raise
