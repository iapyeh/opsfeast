"""Linux inventory implementation; shared report and parser contract."""
from pathlib import Path
import runpy
VERSION = '0.1.1'
common = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'main.py'))


def collect(session, report, timeout, facts):
    return common['collect'](session, report, timeout)
