#!/bin/sh
# Start the trusted checkout's Web server in the foreground. Do not source this file.
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
python=${OPSFEAST_PYTHON:-"$project_root/.venv/bin/python"}
case "$python" in
    /*) ;;
    *) printf '%s\n' 'OPSFEAST_PYTHON must be an absolute executable path.' >&2; exit 1 ;;
esac
if [ ! -x "$python" ]; then
    printf '%s\n' "Python is not executable: $python" 'Set OPSFEAST_PYTHON to the absolute path of your existing OpsFeast interpreter; no environment was created.' >&2
    exit 1
fi
cd "$project_root"
# exec preserves the actual server PID and forwards terminal signals directly.
exec "$python" -B -u -m opsfeast.web "$@"
