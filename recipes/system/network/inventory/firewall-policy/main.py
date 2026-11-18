"""Linux firewall policy views with a scoped Core Recipe."""
from opsfeast.linux_profile import collect

VERSION = '0.1.1'


def execute(recipe):
    return collect(recipe, 'firewall-policy')
