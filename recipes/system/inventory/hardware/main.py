"""Independent inventory routines; transport/storage belong to the runner."""
from opsfeast.inventory.service import collect as collect_fields, finalize as finish
VERSION = "0.1.0"

def baseline(recipe):
    return collect_fields(recipe, ['system.architecture', 'system.virtualization', 'hardware.cpu_model', 'hardware.logical_cpus', 'hardware.memory_total_bytes', 'hardware.vendor', 'hardware.model'])

def identity_unix(recipe):
    return collect_fields(recipe, ['hardware.serial', 'hardware.uuid'])

def identity_linux(recipe):
    return collect_fields(recipe, ['hardware.serial', 'hardware.uuid'])

def finalize(results):
    return finish(results)
