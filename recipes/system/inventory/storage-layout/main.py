"""Independent inventory routines; transport/storage belong to the runner."""
from opsfeast.inventory.service import collect as collect_fields, finalize as finish
VERSION = "0.1.0"

def collect(recipe):
    return collect_fields(recipe, ['storage.filesystems.source', 'storage.filesystems.mountpoint', 'storage.block_devices.name', 'storage.block_devices.type', 'storage.block_devices.size', 'storage.block_devices.fstype', 'storage.block_devices.mountpoint', 'storage.block_devices.model'])

def finalize(results):
    return finish(results)
