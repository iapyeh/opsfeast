"""Independent inventory routines; transport/storage belong to the runner."""
from opsfeast.inventory.service import collect as collect_fields, finalize as finish
VERSION = '0.1.1'

def collect(recipe):
    return collect_fields(recipe, ['system.uptime_seconds', 'system.boot_time'])

def finalize(results):
    return finish(results)
