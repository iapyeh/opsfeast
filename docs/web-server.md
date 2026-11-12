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

*Last modified: 2026-11-11 22:41:14*
