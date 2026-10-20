"""Invoke the public CLI in recipe execution tests; no alternative argument parser."""
def recipe_main(argv=None):
    import opsfeast
    return opsfeast.main(['recipes', 'run', *(argv or [])])
