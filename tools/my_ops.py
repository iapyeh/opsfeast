#!/usr/bin/env python3
"""Compatibility entry point for ops.py; commands follow the current profile rules."""
import sys
import ops as _ops

if __name__ == '__main__':
    sys.exit(_ops.main())
else:
    # Preserve imports used by existing integrations as the same module object.
    sys.modules[__name__] = _ops
