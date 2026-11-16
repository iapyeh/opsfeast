"""Borrow the reviewed Recipe session; no connection or privilege acquisition."""
from opsfeast.package_security.inventory import collect

VERSION = '0.2.0'


def execute(recipe):
    return collect(recipe)
