"""Bundled content consumer; publication stays in the shared Vault application."""
def execute_batch(context):
    from host_vault import rebuild
    return rebuild(context.root)
