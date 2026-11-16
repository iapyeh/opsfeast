"""Minimal public-API reproduction: enter() Ctrl-C loses structured prompt readiness."""
import json
import shlex
import sys
import time
from sshscript import Console, Session


def main():
    session = Session()
    console = Console(session, ownership='borrowed')
    records = []
    def record(update):
        records.append({'state': update.state, 'stdout': update.stdout,
                        'stderr': update.stderr, 'error_type': update.error_type,
                        'session_reuse': update.session_reuse})
    try:
        console.enter(shlex.quote(sys.executable)+' -q -u', prompt='>>>', exit='quit()')
        record(console.poll())
        record(console.interrupt())
        until = time.monotonic()+2
        while time.monotonic()<until:
            time.sleep(.04)
            update = console.poll()
            if update.stdout or update.stderr or update.state != 'running':
                record(update)
            if update.state != 'running':
                break
        record(update)
        matched = update.state == 'waiting_input'
        record(console.close())
    finally:
        session.close(strict=True)
    print(json.dumps({'expected': 'waiting_input', 'matched': matched,
                      'events': records}, indent=2))
    return 0 if matched else 1

if __name__ == '__main__':
    raise SystemExit(main())
