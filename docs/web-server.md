# Per-installation Web endpoint 0.1.0

The Web workspace belongs to the launching user agent's OpsFeast installation.
Its loopback port is saved in that checkout's private `.opsfeast.yaml`, separately
from profile selection and external installation data. Two independent checkouts
can therefore run at the same time without sharing a hard-coded port.

## Configuration and launch

```yaml
schema_version: 2
default_profile: main
profiles:
  main:
    root: feasts/main
web:
  port: 18741
```

`web` is optional and accepts exactly `port`, an integer from 1024 through 65535
(Boolean values are invalid). Existing profile operations preserve it. Configuration
reads do not allocate ports or write files. Malformed values fail without repair.

```sh
.venv/bin/python -B -u -m opsfeast.web --agent-control
# Explicitly select and persist a different port for this checkout:
.venv/bin/python -B -u -m opsfeast.web --agent-control --port 18741
```

At launch, an explicit --port takes precedence; otherwise the saved port is used.
On first launch without either, the OS allocates an available loopback port. The
launcher binds/listens before atomically saving the selected port under the shared
profile-registry lock, and passes that same socket to Uvicorn without releasing
its reservation. It preserves registrations and the default profile. Failed binds
do not replace the saved setting. The controller's ready.url (or the browser-only
startup message) is authoritative: open that URL and use it for reader/worker
clients rather than assuming 8740. Direct scoped worker/client tools still accept
--url; their standalone defaults are not installation endpoint discovery.

--data-root selects existing external site data; it does not select a different
checkout or move web.port into that data directory. A copied checkout containing
.opsfeast.yaml also copies the saved port: when both copies are used on one
computer, explicitly configure an available different port in the new copy.
There is no machine-wide port registry or uniqueness guarantee for copied settings.

## Existing server and agent ownership

An occupied saved port is a conflict, not permission to stop any process listening
there. Do not silently allocate another port, borrow another agent's token, or
fall back to another installation. Inspect the process PID, launch command,
checkout and selected installation data. A different PID or invalid owner token
alone does not prove identity or establish that remote work has ended.

When the human has authorized the user agent to manage this installation, the
agent can reclaim its Web workspace from an obsolete controller without asking
again solely because another agent launched it. First verify the exact installation
and reconcile active Console work; preserve uncertain remote cleanup evidence.
Stop only the identified server through its controller or a reviewed process-stop
operation, then relaunch on its saved port and verify HTTP availability. An explicit
human instruction to preserve or stop a particular service takes precedence.
If ownership cannot be established or active work requires a decision, report the
specific uncertainty and ask for that decision. Other installations remain outside
this takeover scope.

This is an actionable user-agent workflow, not an implemented automatic PID-killer
or inter-agent lock. OpsFeast currently has no public ownership-discovery endpoint,
automatic controller handoff or cross-agent active-work arbitration. Keep the
[controller handle](agent-owner.md) and restore necessarily paused services before
handoff. A restart replaces capabilities/cookies and does not restore workers or
replay host commands.

## Checkout-level Python interfaces and verification

`opsfeast.web_settings.read_port(checkout)` reads without writing;
`configure_port(checkout, port)` validates and atomically saves without binding;
`bind_server(checkout, port=None)` returns a caller-owned listening socket and
saves only after successful reservation. Close that socket in all exit paths.
These are bundled checkout-level interfaces, not a new Core versioned API.
They require the existing Python/PyYAML environment and local registry write access;
no software installation or host connection is performed.

Tests cover independent first allocations, persistent reuse, occupied ports with
unchanged settings, invalid/unknown fields, profile preservation and actual
controller startup with an explicit saved port in a temporary installation. They
do not establish safe takeover of arbitrary external processes. Existing launchers
that assume 8740 must use the returned URL or read the saved port; no compatibility
listener is created on the old default.

*Last modified: 2026-11-05 13:49:41*
