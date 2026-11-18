"""Linux time synchronization configuration and state with a scoped Core Recipe."""
from opsfeast.linux_profile import collect

VERSION = '0.1.1'


def execute(recipe):
    return collect(recipe, 'time-sync')
