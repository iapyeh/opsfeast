"""Independent inventory routines; transport/storage belong to the runner."""
from opsfeast.inventory.service import collect as collect_fields, finalize as finish
VERSION = "0.1.0"

def collect(recipe):
    return collect_fields(recipe, ['network.listening_endpoints', 'services.services'])

def finalize(results):
    return finish(results)
