"""Bundled content consumer; publication stays in the shared Vault application."""
def execute(context):
    from host_vault import rebuild
    return rebuild(context.root)
