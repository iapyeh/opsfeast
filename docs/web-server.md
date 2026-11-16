# Installation-data Web endpoint 0.2.0

The Web endpoint belongs to an installation, alongside its administrator and site
settings in external installation-data. The checkout keeps only the data-root
binding and Profile registry. A replacement checkout attached to the same data uses
the same saved port; independent installations have separate data roots and ports.

## Configuration and launch

`<installation-data>/web-server.json` follows [the endpoint schema](../schemas/web-server.schema.json):

```json
{"schema_version":"0.2.0","port":18741}
```

The port must be an integer from 1024 through 65535; Boolean values are invalid.
Reads do not initialize storage or allocate ports. Unknown/malformed/symlinked files
fail without repair. Web uses the same resolved installation-data for its endpoint,
identity, credentials and site, including an explicitly selected `--data-root`.

```sh
.venv/bin/python -B -u -m opsfeast.web --agent-control
# An explicit human-selected change persists in installation-data:
.venv/bin/python -B -u -m opsfeast.web --agent-control --port 18741
```

An explicit `--port` takes precedence; otherwise use the saved external port.
Only a new installation with no saved endpoint/old registry port gets an automatic
available loopback port. Existing administrator data without a saved endpoint
requires explicit recovery of the original port; startup refuses to allocate a
replacement. The launcher binds/listens before atomically saving it
under a data-root lock, then passes that reserved socket to Uvicorn. Failed binds
preserve existing settings. Profile operations do not read or rewrite the port file.
Use `ready.url` or the browser-only startup message rather than assuming 8740/8741.

## First-use setup obligation

Normal first-use plans include [Web dependencies, persistent data, startup, HTTP
verification and the running URL](getting-started.md#include-and-launch-the-web-workspace).
An approved concrete setup plan covers those local actions without a second routine
startup approval. Cloning alone does not start a listener. A CLI-only/no-Web choice
remains an explicit narrower scope.

## Existing server and agent ownership

An occupied saved port is a conflict, not permission to stop an unidentified listener
or silently choose another endpoint. Establish the process, checkout, installation
data and active work first. Reuse a verified matching healthy service. For authorized
reclaim/restart, reconcile active Console/recipe work, stop only the identified
service and restore its original data/port. A different PID or invalid owner token
alone does not establish identity or prove remote cleanup. Report genuine uncertainty.

No automatic PID-killer, cross-agent ownership discovery, token sharing or active-work
arbitration is implemented. Retain the [owner controller](agent-owner.md) handle and
keep the Web service running after handoff. Independent copied installations require
independent data/identity; attaching two checkouts to one data root represents the
same installation and same saved endpoint, not independent Web workspaces.

## Updates and explicit port transfer

Follow [update preservation](update-preservation.md). Do not initialize another data
root or administrator when updating. For old checkout-local `.opsfeast.yaml web.port`,
run the one-time explicit transfer while the old checkout/registry still exists:

```sh
.venv/bin/python -B -m opsfeast.web_settings migrate-port
.venv/bin/python -B -m opsfeast.web_settings show
```

The operation preserves a private registry backup and removes only the old Web
entry. Conflicts, malformed data or missing dependencies fail. Normal startup
refuses an outstanding old entry; it has no legacy read fallback or automatic data
migration. Saved administrator, site, Profile, recipe/category/meal and result data
are unchanged. See the complete guide for replacement checkouts and browser drafts.

## Shared interfaces

Checkout facades:

- `read_port(installation, data_root=None)` returns the saved integer or None.
- `configure_port(installation, port, data_root=None)` saves an explicit selection.
- `bind_server(installation, port=None, data_root=None)` reserves and returns the
  listening socket; it never takes over another listener.
- `migrate_port(installation, data_root=None)` performs the one-time transfer and
  returns port, data_root, status and private backup path.

The `data_root` argument is keyword-only. Paths resolve through the existing marked
storage contract. The JSON CLI `python -B -m opsfeast.web_settings` provides `show`,
`set --port N` and `migrate-port`, with optional `--installation` and `--data-root`.
Reads/configuration/transfer do not connect to managed hosts or execute recipes.

## Persistent launch choices

First-use agent control requires a persistent interactive process with open stdin.
Closing stdin stops workers and Web, so `--agent-control < /dev/null` is not a
background launch method. See [controller lifetime](agent-owner.md#launch-and-lifetime).
Do not claim survival across agent/tool-host exit without an actual persistence
facility. Installing systemd/launchd or start-at-login is a separately chosen scope.

An already configured administrator can use an approved browser-only POSIX launch
from the trusted checkout, preserving the data binding and saved external port:

```sh
nohup "/absolute/path/to/selected/python" -B -u -m opsfeast.web > "/absolute/path/to/installation-data/web.log" 2>&1 < /dev/null &
```

Capture the PID/startup URL and verify HTTP before handoff. This mode has no owner
controller for initial administrator setup/reset. `nohup` is not an OpsFeast daemon
flag or a reboot guarantee. Use the approved available facility on other systems.

## Manual shell launcher and PID marker

From the checkout root, run:

```sh
./tools/start_web.sh
# Forward an explicitly chosen endpoint change to the ordinary CLI:
./tools/start_web.sh --port 18741
# Reuse a different existing interpreter (absolute executable path):
OPSFEAST_PYTHON=/absolute/path/to/python ./tools/start_web.sh
```

The POSIX shell launcher locates its own checkout, changes into it and `exec`s
`python -B -u -m opsfeast.web` using `<checkout>/.venv/bin/python` unless
`OPSFEAST_PYTHON` is supplied. It works from another current directory when invoked
by its full path, including paths containing spaces. Arguments are forwarded
without evaluation. It never creates/updates a venv, installs packages, initializes
installation data or resets an administrator/Profile. Saved external port/data
selection remains authoritative; `--port` and `--data-root` retain ordinary CLI
semantics. `--help` prints CLI usage without reserving a PID or starting Web.

The default is foreground browser-only Web for an existing administrator. Keep the
terminal open; Ctrl+C performs an orderly shutdown. An approved persistent launch
can use `nohup /absolute/path/to/ops/tools/start_web.sh > /absolute/path/to/installation-data/web.log 2>&1 < /dev/null &`.
This does not provide reboot/start-at-login integration. For first-use setup or
agent owner operations, retain a private interactive controller with
`./tools/start_web.sh --agent-control`; keep stdin open and do not redirect it to
`/dev/null`. A PID is process discovery, not an owner capability or administrator
credential. A new agent cannot recover another controller's in-memory authority
from a PID file.

Every new `python -m opsfeast.web` launch (including this script and agent-control)
reserves `<installation-data>/web-server.pid`. It contains only the positive decimal
PID followed by a newline, mode 0600, and names the actual Python Web process,
not a shell wrapper. Exclusive creation prevents concurrent launches for one data
root, even when different ports/checkouts are requested. The marker is written
before port reservation; it is not evidence that HTTP startup has completed.
Use the existing storage resolver or `python -B -m opsfeast.web_settings show` to
find the resolved external data root and saved port, then verify the returned URL
with HTTP. No secrets are stored in the PID file.

| Existing marker | Startup result |
| --- | --- |
| Valid PID still exists | Warning, exit 2; no second server or port change |
| PID exists but process inspection is denied | Refuse with exit 2; no takeover |
| PID has exited | Stale-file error, exit 1; preserve the marker for agent recovery |
| Empty, malformed, symlinked or otherwise unreadable marker | Refuse with exit 1; preserve it for inspection |
| No marker | Reserve actual PID; attempt normal Web startup |

Normal exit, Ctrl+C, SIGTERM, controller shutdown/EOF and handled startup failure
remove only the marker created by that launch. SIGTERM and ordinary SIGHUP are
handled during startup too; an inherited SIGHUP-ignore disposition (nohup) stays
ignored. Cleanup does not remove a replacement inode or modified marker. SIGKILL,
power failure, filesystem failure or another abrupt termination can leave a stale
file. There is no automatic stale-file repair, PID killer, port reassignment or
host-command replay. Servers already running from older code do not acquire a
marker retroactively; they remain running until an authorized normal restart.

For agent recovery: read the exact resolved data root/marker, validate the numeric
PID, inspect liveness and check the saved endpoint, actual process identity,
checkout and active Console/recipe work. `kill -0 PID` alone proves neither Web
identity nor HTTP health; PID reuse can point at an unrelated live process. Never
kill a PID merely because it appears in this file. A confirmed stale marker may be
preserved/removed within the human's requested recovery scope, followed by one
normal launch and HTTP verification. Ambiguous ownership, malformed data or an
unrelated listener requires investigation; do not silently overwrite the file or
repeat startup. Do not request approval again for already-authorized recovery.

Checkout support is `opsfeast.web.process.claim(data_root)` and
`ProcessMarkerError.exit_code`. The Web CLI owns this lifecycle; recipes should not
reimplement PID management or use this context to grant themselves execution
scope. Public focused tests in `tests/test_web_process.py` cover actual child PIDs,
concurrent refusal, live/dead/inaccessible/invalid markers, normal/signal/forced
termination, replacement preservation, shell quoting and isolated HTTP startup.
They do not qualify systemd/launchd, reboot persistence or managed-host execution.

*Last modified: 2026-11-16 14:50:01*
