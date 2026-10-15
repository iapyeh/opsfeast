#!/usr/bin/env python3
"""Compatibility CLI/import entrypoint for the bundled OpsFeast package."""
from pathlib import Path
import importlib.util
import sys

_root = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    sys.path.insert(0, str(_root))
    from opsfeast import main
    raise SystemExit(main())
else:
    _spec = importlib.util.spec_from_file_location(
        'opsfeast', _root / 'opsfeast/__init__.py',
        submodule_search_locations=[str(_root / 'opsfeast')])
    _module = importlib.util.module_from_spec(_spec)
    sys.modules['opsfeast'] = _module
    _spec.loader.exec_module(_module)
    globals().update(vars(_module))
