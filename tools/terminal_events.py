"""Private presentation transport; never used as an execution/result contract."""
import json
import os
import sys
import threading

PREFIX = '\x1eOPSFEAST '
_lock = threading.Lock()


def emit(kind, **fields):
    if os.environ.get('OPSFEAST_TUI_EVENTS') == '1':
        with _lock:
            print(PREFIX + json.dumps(dict(kind=kind, **fields), ensure_ascii=True),
                  file=sys.stderr, flush=True)


def decode(line):
    if line.startswith(PREFIX):
        try:
            value = json.loads(line[len(PREFIX):])
            if isinstance(value, dict) and isinstance(value.get('kind'), str):
                return value
        except ValueError:
            pass
    return None
