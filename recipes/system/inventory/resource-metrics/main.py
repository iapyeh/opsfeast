"""Independent inventory routines; transport/storage belong to the runner."""
from opsfeast.inventory.service import collect as collect_fields, finalize as finish
VERSION = "0.1.0"

def collect(recipe):
    return collect_fields(recipe, ['metrics.load_1m', 'metrics.load_5m', 'metrics.load_15m', 'metrics.cpu_utilization_percent', 'metrics.memory_available_bytes', 'metrics.disk_counters', 'metrics.interface_counters', 'metrics.memory_pressure', 'metrics.interfaces.in_octets', 'metrics.interfaces.out_octets', 'metrics.interfaces.in_errors', 'metrics.interfaces.out_errors', 'metrics.interfaces.in_discards', 'metrics.interfaces.out_discards'])

def finalize(results):
    return finish(results)
