"""Bundled policy consumer; platform service lifecycle remains authoritative."""
from opsfeast.backup_policy import consume


def execute_batch(context):
    return consume(context)
