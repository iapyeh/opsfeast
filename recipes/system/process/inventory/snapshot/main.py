"""Snapshot visible Linux processes using the supplied Core Recipe scope."""
from opsfeast.linux_profile import collect

VERSION = '0.1.1'


def execute(recipe):
    return collect(recipe, 'processes')
