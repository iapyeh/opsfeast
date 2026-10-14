"""Trusted bundled inventory values contract and CSV codec; no candidate loading."""
from pathlib import Path
import runpy
from opsfeast import ConfigError

_contract = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'recipes/inventory/system/details.py'))
FIELDS = _contract['FIELDS']
empty = _contract['empty']
csv_text = _contract['csv_text']


def validate_inventory(data):
    try:
        return _contract['validate'](data)
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        raise ConfigError('invalid inventory values contract') from None
