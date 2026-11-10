"""Inventory Linux local users and groups using the supplied Core Recipe scope."""
from opsfeast.linux_profile import collect

VERSION = '0.1.0'


def execute(recipe):
    return collect(recipe, 'accounts')
