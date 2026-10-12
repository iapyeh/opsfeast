#!/usr/bin/env python3
"""Compatibility entrypoint for the former SSHScript Ops CLI and imports.

New callers should use opsfeast.py / opsfeast. Importing ops returns the same
module, so existing runtime integrations keep one shared configuration state.
"""
import sys
import opsfeast

if __name__ == '__main__':
    raise SystemExit(opsfeast.main())

sys.modules[__name__] = opsfeast
