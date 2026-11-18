"""Independent inventory routines; transport/storage belong to the runner."""
from opsfeast.inventory.service import collect as collect_fields, finalize as finish
VERSION = "0.1.1"

def collect(recipe):
    return collect_fields(recipe, ['system.hostname', 'system.kernel_name', 'system.system_version', 'system.kernel_release', 'system.platform', 'system.system_name', 'system.timezone', 'system.kernel_version'])

def finalize(results):
    return finish(results)
