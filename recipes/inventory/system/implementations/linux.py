"""Linux inventory implementation; shared report and parser contract."""
from pathlib import Path
import runpy
VERSION = '0.1.2'
common = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'main.py'))


def collect(session, report, timeout, facts, *, context=None):
    if context is not None:
        timeout = context.vars.get('command_timeout_seconds', timeout)
    return common['collect'](session, report, timeout)
