"""Independent inventory routines; transport/storage belong to the runner."""
from opsfeast.inventory.service import collect as collect_fields, finalize as finish
VERSION = '0.1.1'

def collect(recipe):
    return collect_fields(recipe, ['network.interfaces.name', 'network.interfaces.mac', 'network.interfaces.mtu', 'network.interfaces.address', 'network.interfaces.prefix_length', 'network.interfaces.kind', 'network.ipv4.address', 'network.ipv4.prefix_length', 'network.ipv6.address', 'network.ipv6.prefix_length', 'network.dns_servers'])

def finalize(results):
    return finish(results)
