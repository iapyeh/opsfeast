"""Independent inventory routines; transport/storage belong to the runner."""
from opsfeast.inventory.service import collect as collect_fields, finalize as finish
VERSION = "0.1.0"

def collect(recipe):
    return collect_fields(recipe, ['storage.filesystems.total_bytes', 'storage.filesystems.used_bytes', 'storage.filesystems.available_bytes', 'storage.filesystems.used_percent', 'storage.filesystems.total_megabytes', 'storage.filesystems.used_megabytes', 'storage.filesystems.available_megabytes', 'storage.inodes.total', 'storage.inodes.used', 'storage.inodes.available', 'storage.swap.total_bytes', 'storage.swap.used_bytes', 'storage.swap.available_bytes'])

def finalize(results):
    return finish(results)
