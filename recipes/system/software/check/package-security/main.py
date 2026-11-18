"""Three dependent stages on a single supplied Recipe scope."""
from opsfeast.package_security.pipeline import execute as run_pipeline

VERSION = '0.3.1'

def execute(recipe):
    return run_pipeline(recipe)
