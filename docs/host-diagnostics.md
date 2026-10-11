# Host initialization and diagnostics

These commands use the selected management profile unless `--profile NAME` or an explicit management directory is supplied. Diagnostics and initialization require matching SSHScript import/distribution 5.0.0, Python 3.11+ and PyYAML. They retain the existing connection, jump-host, key and host-key trust rules. They do not install packages or alter target configuration. Connecting may execute a configured proxy command; authentication attempts and login-shell startup may create target audit records.

## Initialize platform facts

```sh
python -B tools/ops.py host-init host-01 --profile main
python -B tools/ops.py host-init host-01 --root /srv/my-ops
python -B tools/ops.py test-connection host-01 /srv/my-ops --host-init
```

A direct `host-init` invocation always refreshes facts. The optional `test-connection --host-init` also performs a fresh probe after its connection test; it currently uses a separate connection. Standalone connection-test behavior is unchanged.

The probe uses `uname -s`, `uname -r` and `uname -m`. Linux distribution identity/version comes from `/etc/os-release`, falling back to `/usr/lib/os-release` only when the first file is absent. It parses data without executing its content. FreeBSD userland version comes from `freebsd-version -u`; macOS product version comes from `sw_vers -productVersion`. Kernel release remains separate from OS/distribution version. Unknown fields remain unavailable. A recognized kernel is sufficient for platform discovery; missing distribution/version does not prevent a generic implementation from matching. An unrecognized kernel is recorded without guessing that it is Linux.

Facts are saved atomically in `observations/host-init/<sha256-of-host-id>.json` inside the management directory. Symlink storage is rejected. Reports retain host ID, UTC observation time, probe/schema version, per-field state, commands and a digest of the connection target including jump-host settings. No credentials or raw command output are included. A changed target configuration, failed latest initialization, incompatible facts schema or malformed cache causes a new probe. SSH config changes outside hosts.yaml and reinstallation at the same endpoint cannot be inferred from this digest: run `host-init` explicitly after such changes. There is no age-based expiry.

A failed explicit refresh retains the previous successful facts as historical evidence, but the latest state is failed and those facts are not reused for dispatch. Cleanup failure also makes initialization fail.

## Independent and chained su tests

```sh
python -B tools/ops.py test-su host-01 user2 user3 --root /srv/my-ops
python -B tools/ops.py test-su host-01 --chain user2 user3 --chain user3 user2 --root /srv/my-ops
```

The first command independently tests connection-user → user2 and connection-user → user3. Each repeated `--chain` starts a fresh connection: the second command tests connection-user → user2 → user3, then connection-user → user3 → user2. A failed chain step prevents later steps in that chain, while other groups continue. Chains cannot be mixed with independent usernames. At least one target is required, and the actual connection account cannot appear in any chain/list. Independent duplicates and adjacent chain duplicates are rejected; nonadjacent chain repeats are allowed.

Target passwords come only from `hosts.<host>.users.<target>.password`. Missing credentials produce skipped steps; these diagnostics do not probe passwordless su. No interactive password prompt is issued by Ops.

## Sudo tests

```sh
python -B tools/ops.py test-sudo host-01 --root /srv/my-ops
python -B tools/ops.py test-sudo host-01 user2 user3 --run-as service-user --root /srv/my-ops
```

Omitting usernames tests the actual connection account. Supplied usernames are independent **sudo actors**; `--run-as` is the sudo target, default root. For another actor, Ops first enters that account through su and verifies identity, then tests sudo. A failed prerequisite is reported with a su stage, rather than a claim that sudo was attempted.

Sudo passwords come from `users.<actor>.vars.sudo.password`. The actual connection account may use host-level `vars.sudo.password` as fallback. Login/su passwords are never automatically used as sudo passwords. An explicitly configured account-level sudo password takes precedence. Standalone `test-sudo` can test passwordless sudo when no sudo password is configured. Successful entry does not prove that a supplied password was consumed; sudo policy/cache may avoid a password prompt.

Tests enter an authenticated shell and query effective UID/name, compare UID with the requested account, then verify return to the connection identity. They test shell access, not command-specific sudo rules. Bash and id are required by the SSHScript authenticated-console contract. Authentication/identity/cleanup errors remain separate from skipped steps; exception messages, passwords and raw privileged outputs are omitted.

## Test one host

```sh
python -B tools/ops.py test-host host-01 --root /srv/my-ops
```

`test-host` always tests hostname/date and performs the following:

1. Reuse successful, target-matching host-init data; otherwise initialize it.
2. Test sudo only for the actual connection account, only when an explicit sudo password is configured. Missing password is skipped; passwordless sudo is not attempted.
3. Independently test su from the connection account to other accounts declared in `users`. It does not enumerate system accounts or test chains.

A connection failure skips all subsequent tests. A platform-probe failure does not prevent account diagnostics. Tests use fresh connections for independent groups. All results are returned in one JSON report, including cache/probe provenance and original facts timestamp. The summary is success, partial (some tests skipped) or failed. Individual diagnostics may also report skipped. Any actual failure returns exit code 1; success/partial/skipped return 0. Skipped never means verified.

`--timeout` is a positive finite number, default 30 seconds, per connection stage/command and authenticated entry/exit, not a whole-run deadline. SSHScript base-shell/capability setup and failure recovery have their own contract limits; channel closure does not prove remote-process termination.

## Verification and sources

Synthetic tests cover cache refresh/invalidation, platform parsing, identity mismatches, independent/repeated chains, missing credentials and failure/cleanup handling. Native su/sudo and real SSH behavior have not been verified by this change. Do not claim target compatibility from mocks.

SSHScript APIs follow the included public snapshot: [Agent Guide](https://iapyeh.github.io/sshscript/v3a/ai-agents/guide/), [canonical API](https://iapyeh.github.io/sshscript/v3a/recommended-api/) and `.agents/skills/sshscript/SOURCE.json`, documentation contract 5.0.0, bundle SHA-256 `e065bec4e7bd48791563412c5ca3bdaac5f46c5e09456ba5d24665a01ba79b4b`. The su/sudo signatures were additionally checked against public repository branch `release`, commit `fea109ebcbf2b5c7bfa5ebd2cd17c44e9090ebeb`: [session.py](https://github.com/iapyeh/sshscript/blob/fea109ebcbf2b5c7bfa5ebd2cd17c44e9090ebeb/src/sshscript/session.py) and [sessionwrapper.py](https://github.com/iapyeh/sshscript/blob/fea109ebcbf2b5c7bfa5ebd2cd17c44e9090ebeb/src/sshscript/sessionwrapper.py). FreeBSD userland semantics follow the [FreeBSD manual](https://man.freebsd.org/cgi/man.cgi?query=freebsd-version&sektion=1), consulted 2026-10-11. macOS commands are verified by local read-only execution.

_Last modified: 2026-10-11_
