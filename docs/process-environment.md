# Proxy subprocess environments

OpsFeast's proxy environment policy 0.1.0 is shared by `test-connection`, host
diagnostics, Core `profile.sessions.connect()` and recipe/inventory connections.
It applies to the **local proxy process**, including a resolved SSH config
ProxyCommand and a proxy on the first jump. It does not change remote shells,
recipe subprocesses, SSH authentication selection or the parent process environment.
Direct library connections outside OpsFeast do not acquire this policy automatically.

## Defaults and explicit configuration

Proxies inherit the calling environment, preserving PATH, locale, SSH_AUTH_SOCK
and other existing settings. If inherited NO_COLOR is nonempty, the proxy receives
`NO_COLOR=true`; an inherited empty NO_COLOR is removed. An absent NO_COLOR remains
absent. This reconciles the presence-based convention with tools whose Boolean
parser rejects values such as `1`. Even the nonempty string `0` is presence under
this policy. There is no universal normalization of arbitrary environment variables.

An explicit override wins, including null (remove) and an empty string (retain an
empty value). Quote strings: YAML Boolean/integer values are rejected before any
connection. Unknown/invalid policies fail rather than silently falling back.

```yaml
hosts:
  proxy-target:
    connection:
      hostname: target.example.invalid
      user: operator
      identity_file: /synthetic/keys/login_rsa
      proxy_command: "ssh -W target.example.invalid:22 jump.example.invalid"
      proxy_environment:
        NO_COLOR: "true"
        LANG: "C"
        UNNEEDED_VARIABLE: null
```

`connection.proxy_environment` is an optional mapping of POSIX variable names
(`[A-Za-z_][A-Za-z0-9_]*`) to strings without NUL or null. It is available on explicit
proxy connections and SSH config aliases. An alias must resolve to a proxy at
execution; otherwise connection planning fails before Session creation. It is not
valid on local connections, standalone host references or connections without a
proxy. Put first-hop overrides on that hop, not the destination's via connection.
The mapping is not inherited between hops or from default settings. `${...}`, `%h`
and shell expressions are not expanded in values.

This is trusted local execution configuration, with the same authorization boundary
as the proxy command. Changing PATH, loader variables or tool-specific proxy settings
can change what code runs and where it connects. Agents must explain the concrete
change and obtain required authorization before applying operational configuration;
loading/checking it does not authorize execution. Do not generate credentials from
the environment or retry authentication with different settings after failure.

## Inspect and diagnose

From the trusted checkout and selected interpreter:

```sh
python -B tools/check_environment.py --json
python -B tools/opsfeast.py check --profile main --json
```

The first command adds `proxy_environment`: watched ambient variable presence,
policy version and planned NO_COLOR action. It does not dump environment values,
resolve a profile, execute a proxy or change dependency readiness. The second checks
configured names/types and structural connection constraints without connecting.
Use an authorized `test-connection HOST --profile main --json --debug` for actual
connection evidence. Debug goes to stderr; JSON remains on stdout. Host operations
and recipe runs require their own authorization.

Each attempted proxy hop records `proxy_environment` with `policy_version`,
`inherit`, `ambient_presence` and `variables`. Each changed variable has `source`
(`normalized_inherited` or `connection.proxy_environment`) and `action` (`set` or
`remove`). No values or proxy command are included. Records describe the inherited
process snapshot and selected policy; they do not establish which ancestor process,
terminal, agent or CI originally set a variable, nor prove successful SSH login.
Failure receipts retain the attempted policy and the original failure/cleanup state.
Core exposes this through the connection's copied `report`; operational raw results
retain hop evidence. This is connection metadata, not a retained inventory dataset.

Core/UI configuration snapshots mask every non-null proxy_environment value,
including names with no recognizable secret keyword. Explicit CLI dump and
`reveal_secrets=True` remain raw private interfaces; do not publish them. Ordinary
diagnostics omit all values. Variable names themselves should not contain secrets.

## Implementation and lifecycle

Checkout helper `process_environment.proxy_policy(overrides=None, *, environ=None)`
returns `(changes, evidence)` without writes, subprocesses or environment mutation.
`environ` permits explicit snapshots for tests. `validate()` checks configuration;
`inspect_environment()` supplies the readiness diagnostic. These are checkout
interfaces, not additions to the versioned Core API. Recipe authors normally reuse
their supplied Session instead of launching another proxy or loading host settings.

`proxy_options(settings, evidence)` is the connection adapter. It copies settings,
records sanitized evidence and yields public Session.connect keyword arguments.
When changes are needed it writes only original argv and explicit overrides to a
unique mode-0600 temporary file. A Python launcher starts with the selected
interpreter and `-I -B`, reads and deletes the file, applies overrides to a child
environment copy and execs the original argv without a shell. Values stay out of
launcher argv; parent cleanup also removes the file after start/connection failure.
Execution or cleanup errors propagate; there is no silent unmodified retry.

Exec preserves the process PID and protocol stdin/stdout, so SSHScript still owns
and terminates the actual proxy. Launcher failures use exit 126 and a fixed stderr
message without payload/exception text. Proxies can emit their own sensitive output
or expose values through operating-system process inspection; this mechanism is not
a sandbox or a guarantee about arbitrary third-party tool logging. A hard crash
before cleanup can leave owner-only temporary material; normal/failure paths are
tested. Do not put credentials in proxy command argv.

## Verification and limits

Run the public local tests:

```sh
python -B -m unittest discover -s tests -p 'test_process_environment.py'
```

They cover absent/empty/1/true/0/unexpected NO_COLOR, explicit overrides/removals,
PATH preservation, stdin/stdout and PID continuity, concurrent child isolation,
permissions, launch/connection failure, termination, file cleanup, sanitized
receipts, configuration validation, aliases, jump ownership and shared diagnostic/
runtime routes. An actual SSHScript 7.0.1 Session opens a local proxy fixture whose
handshake deliberately fails; policy application and strict child cleanup are
verified. This proves neither native wstunnel connectivity nor successful real SSH,
authentication, jump hosts, remote shells, su/sudo, Windows support or every tool's
environment semantics. Tests use synthetic data and no real credentials/hosts.

*Last modified: 2026-10-30 12:17:33*
