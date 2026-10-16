# Host initialization and diagnostics

These commands use the selected management profile unless `--profile NAME` or an explicit management directory is supplied. Diagnostics and initialization require matching SSHScript import/distribution 5.0.0, Python 3.11+ and PyYAML. They retain the existing connection, jump-host, key and host-key trust rules. They do not install packages or alter target configuration. Connecting may execute a configured proxy command; authentication attempts and login-shell startup may create target audit records.

For complete tool syntax, defaults, behavior, output and exit codes, see the [CLI reference](cli.md). It covers both tools/opsfeast.py and tools/run_recipe.py for administrators and agents.

For inventory readiness, use inventory --dryrun for login-only checks. For all declared accounts, use [check-access](inventory-access.md#check-access-without-collection): it checks login/root, independent su to other declared users and enabled sudo as each actor, without initializing platform facts. Test-host additionally handles platform facts and is not the inventory gate.

## Initialize platform facts

```sh
python -B tools/opsfeast.py host-init host-01 --profile main
python -B tools/opsfeast.py host-init host-01 --root /srv/feasts/main
python -B tools/opsfeast.py test-connection host-01 /srv/feasts/main --host-init
```

A direct `host-init` invocation always refreshes facts. The optional `test-connection --host-init` also performs a fresh probe after its connection test; it currently uses a separate connection. Standalone connection-test behavior is unchanged.

The probe uses `uname -s`, `uname -r` and `uname -m`. Linux distribution identity/version comes from `/etc/os-release`, falling back to `/usr/lib/os-release` only when the first file is absent. It parses data without executing its content. FreeBSD userland version comes from `freebsd-version -u`; macOS product version comes from `sw_vers -productVersion`. Kernel release remains separate from OS/distribution version. Unknown fields remain unavailable. A recognized kernel is sufficient for platform discovery; missing distribution/version does not prevent a generic implementation from matching. An unrecognized kernel is recorded without guessing that it is Linux.

Facts are saved atomically in `observations/host-init/<sha256-of-host-id>.json` inside the management directory. Symlink storage is rejected. Reports retain host ID, UTC observation time, probe/schema version, per-field state, commands and a digest of the connection target including jump-host settings. No credentials or raw command output are included. A changed target configuration, failed latest initialization, incompatible facts schema or malformed cache causes a new probe. SSH config changes outside hosts.yaml and reinstallation at the same endpoint cannot be inferred from this digest: run `host-init` explicitly after such changes. There is no age-based expiry.

A failed explicit refresh retains the previous successful facts as historical evidence, but the latest state is failed and those facts are not reused for dispatch. Cleanup failure also makes initialization fail.

## Independent and chained su tests

```sh
python -B tools/opsfeast.py test-su host-01 user2 user3 --root /srv/feasts/main
python -B tools/opsfeast.py test-su host-01 --chain user2 user3 --chain user3 user2 --root /srv/feasts/main
```

The first command independently tests connection-user → user2 and connection-user → user3. Each repeated `--chain` starts a fresh connection: the second command tests connection-user → user2 → user3, then connection-user → user3 → user2. A failed chain step prevents later steps in that chain, while other groups continue. Chains cannot be mixed with independent usernames. At least one target is required, and the actual connection account cannot appear in any chain/list. Independent duplicates and adjacent chain duplicates are rejected; nonadjacent chain repeats are allowed.

Su selects the target account password using the [credential precedence rules](#credential-precedence) below. Each independent target, chain step and su prerequisite for another sudo actor uses the same rule. Missing credentials produce skipped steps; these diagnostics do not probe passwordless su. No interactive password prompt is issued by Ops.

## Sudo tests

```sh
python -B tools/opsfeast.py test-sudo host-01 --root /srv/feasts/main
python -B tools/opsfeast.py test-sudo host-01 user2 user3 --run-as service-user --root /srv/feasts/main
```

Omitting usernames tests the actual connection account. Supplied usernames are independent **sudo actors**; `--run-as` is the sudo target, default root. For another actor, Ops first enters that account through su and verifies identity, then tests sudo. A failed prerequisite is reported with a su stage, rather than a claim that sudo was attempted.

Sudo selects the actor password using the [credential precedence rules](#credential-precedence) below. Standalone `test-sudo` and `test-host` can test passwordless sudo when no password source is selected; account sudo: false skips sudo. Successful entry does not prove that a supplied password was consumed; sudo policy/cache may avoid a password prompt.

Tests enter an authenticated shell and query effective UID/name, compare UID with the requested account, then verify return to the connection identity. They test shell access, not command-specific sudo rules. Bash and id are required by the SSHScript authenticated-console contract. Authentication/identity/cleanup errors remain separate from skipped steps; exception messages, passwords and raw privileged outputs are omitted.

### Read the identity evidence

Each step retains `identity` and adds `identity_verification`: `expected` and `actual` username/effective_uid, `matched`, `status` and a short `message`. The expected UID comes from `id -u TARGET`; the actual identity comes from `id -un` and `id -u` inside the entered shell. Effective UID equality is the success criterion; account aliases may have different names but the same UID. Environment variables such as USER/HOME are not identity evidence.

For example, a verified sudo-to-root step reports expected `{username: root, effective_uid: 0}`, actual `{username: root, effective_uid: 0}`, `matched: true`, and `status: success`. A UID mismatch retains both observed values with `matched: false` and `status: failed`. Incomplete checks retain available values with `matched: null`; entry failures and skipped steps have `status: not_run`, never implied success. When another sudo actor requires su first, `su_identity_verification` records that prerequisite separately from the final sudo check.

The report's `connection_identity` records the original shell name/UID; `login_identity` separately identifies the authenticated SSH account. Each independent target or chain group includes `parent_identity_verification` with expected/actual identity and an explicit restoration result. This check runs after exiting the group's authenticated contexts; a chain reports restoration after the whole chain, not each intermediate exit. Restoration requires both name and UID to match the original connection identity. An unperformed or failed check remains explicit; successful restoration does not erase an operation or Session cleanup failure.

Default stdout is a terminal table; use --json for the complete structured report. Non-TTY stdout remains JSON. See [console output policy](cli.md#terminal-tables-and-json). With --verbose/--debug, stderr also explains the expected/actual account and UID after successful verification and states whether the original identity was restored. Identity evidence verifies shell access; it does not establish command-specific permissions or whether a supplied password was consumed. These fields add explanation without additional probes or environment dumps.

All host diagnostics accept `-v`/`--verbose`, `--debug` and `--traceback`; see [diagnostic options](cli.md#connection-diagnostics-and-options). For example, add `--debug --traceback` to test-sudo to inspect the actor, target, whether a sudo password was supplied and its configuration source, plus frames for caught failures. A PermissionError at su/sudo entry does not by itself prove the password is wrong: entry may reject authentication, request a password again, or request one when none was supplied. Keep the reported stage and credential source when investigating; the tool does not report a verified native policy cause.

## Credential precedence

Sudo uses the canonical [access credential rules](inventory-access.md#configure-the-actual-connection-account), including account sudo: false, sudo-password field presence, null/empty passwords, the exact "false" fallback marker, legacy explicit vars credentials and account-password fallback. No alternate source is tried after rejection. Host credentials remain exclusive to the actual connection account. Missing all password sources permits noninteractive passwordless sudo. Root-shell access and cached authentication do not prove that the password was consumed or that command-specific sudo is available.

Su rules are unchanged: users.<target>.vars.su.password → host vars.su.password only when the target is the connection account → users.<target>.password. Missing/null values advance to the next source; empty strings are explicitly selected. Missing all sources skips su; no passwordless su is probed. No reported credential source reveals the value.

## Test one host

```sh
python -B tools/opsfeast.py test-host host-01 --root /srv/feasts/main
```

`test-host` always tests hostname/date and performs the following:

1. Reuse successful, target-matching host-init data; otherwise initialize it.
2. Test sudo for the actual connection account unless account sudo is false; use the selected password or attempt passwordless entry when none is selected.
3. Independently test su from the connection account to other accounts declared in `users`. It does not enumerate system accounts or test chains.

A connection failure skips all subsequent tests. A platform-probe failure does not prevent account diagnostics. Tests use fresh connections for independent groups. All results are returned in one JSON report, including cache/probe provenance and original facts timestamp. The summary is success, partial (some tests skipped) or failed. Individual diagnostics may also report skipped. Any actual failure returns exit code 1; success/partial/skipped return 0. Skipped never means verified.

`--timeout` is a positive finite number, default 30 seconds, per connection stage/command and authenticated entry/exit, not a whole-run deadline. SSHScript base-shell/capability setup and failure recovery have their own contract limits; channel closure does not prove remote-process termination.

## Verification and sources

Synthetic tests cover cache refresh/invalidation, platform parsing, identity mismatches, independent/repeated chains, missing credentials and failure/cleanup handling. Native su/sudo and real SSH behavior have not been verified by this change. Do not claim target compatibility from mocks.

SSHScript APIs follow the included public snapshot: [Agent Guide](https://iapyeh.github.io/sshscript/v3a/ai-agents/guide/), [canonical API](https://iapyeh.github.io/sshscript/v3a/recommended-api/) and `skills/sshscript/SOURCE.json`, documentation contract 5.0.0, bundle SHA-256 `e065bec4e7bd48791563412c5ca3bdaac5f46c5e09456ba5d24665a01ba79b4b`. The su/sudo signatures were additionally checked against public repository branch `release`, commit `fea109ebcbf2b5c7bfa5ebd2cd17c44e9090ebeb`: [session.py](https://github.com/iapyeh/sshscript/blob/fea109ebcbf2b5c7bfa5ebd2cd17c44e9090ebeb/src/sshscript/session.py) and [sessionwrapper.py](https://github.com/iapyeh/sshscript/blob/fea109ebcbf2b5c7bfa5ebd2cd17c44e9090ebeb/src/sshscript/sessionwrapper.py). FreeBSD userland semantics follow the [FreeBSD manual](https://man.freebsd.org/cgi/man.cgi?query=freebsd-version&sektion=1), consulted 2026-10-11. macOS commands are verified by local read-only execution.

For connection-only troubleshooting, use `test-connection HOST --profile NAME --debug --traceback --json`. Batch selection supports `test-connection --group web --profile NAME` and `test-connection --all --profile NAME`; terminal output includes automatic progress and per-host result tables. Use --json --quiet for machine consumption. See [selection, output contracts and failure behavior](cli.md#select-and-monitor-connection-tests). These tests execute hostname/date, without su/sudo or inventory; --host-init explicitly adds a facts refresh.

## ESXi login identity without id

Connection-only tests run hostname/date and do not verify the effective account. Access checks verify the account separately. The shared identity probe first uses `id -un` and `id -u`, including `id -u TARGET` for a configured account. When the initial id command returns 127 (missing command), or returns 2 with empty stdout and the exact shell error form `sh: exec: line N: id: not found` (optional shell path/line number), it checks the kernel. Only an untruncated `uname -s` result exactly equal to `VMkernel` enables the ESXi adapter. Exit 2 alone, unrelated stderr, nonempty stdout, truncated results and other kernels do not enable this fallback. This handles ESXi SSH exec channels whose missing-command exit code differs from interactive shells.

The adapter executes a fixed, Python-2/3-compatible standard-library expression with `/bin/python -B -c ...`; only a missing interpreter (127) permits trying `/bin/python3`. It obtains the current effective UID from `os.geteuid()`, resolves that UID's account through `pwd.getpwuid()`, and resolves an explicit target through `pwd.getpwnam()`. Target names use the existing username validator and are separate argv arguments. It never infers privilege from hosts.yaml, environment variables, a shell prompt or account-list membership. The -B flag prevents bytecode cache writes. No program is installed, remote helper file uploaded, host setting changed or inventory performed. The same finite command timeout and strict Session cleanup apply. Interpreter errors are not retried with another credential or interpreter.

A verified UID 0 login uses the existing root path: no sudo is attempted, even if sudo is enabled in users. Other UIDs remain ordinary users and follow their account policy. Standard id-based behavior on Linux/FreeBSD/macOS is unchanged. This adapter does not add ESXi su/sudo support: authenticated-console operations retain SSHScript's Bash/id prerequisites and must not be treated as supported merely because direct-login identity now works.

Use the existing CLI; no new hosts.yaml property is required:

```sh
python -B tools/opsfeast.py check-access --host HOST --root /srv/feasts/main --json --quiet
```

The access contract remains 0.1.0 with additive `access.identity_probe` and `access.configured_identity_probe` evidence: source (`id` or `esxi_python`), status, and interpreter for the successful ESXi backend. Each probe records id_exitcode from its initial id -un attempt. A failed probe may include reason_code; source/interpreter identify the attempted Python backend even if that backend fails. When an ESXi configured-account comparison reaches UID validation, configured_identity_probe also records actual {username, effective_uid}, expected {username, effective_uid}, and matched. These are normalized fields, never raw remote output. Existing connection_identity keeps exactly username/effective_uid and is published only after the configured-account check succeeds. access.actual_identity records the observed shell actor as soon as the initial probe succeeds, including when a later configured-account mismatch rejects access. The ESXi root-shell relationship described below can accept a numeric mismatch when the successful final-hop SSH login is known, the effective shell is consistently UID 0, and the kernel is verified as VMkernel. Other mismatches remain failures. Identity-stage failures keep the top-level identity_failed reason and add `identity_error.reason_code`: identity_tool_missing, identity_probe_failed, identity_invalid_output, identity_mismatch or the generic identity_failed. No raw Python output or exception text is retained. Table output shows successful SSH connection separately from a failed identity row, followed by unattempted sudo; the host still fails. This prevents a reachable host being described as an SSH failure or an unverified login being described as root. Retained observation schemas do not change.

For an already-authorized connected Session, checkout maintainers can reuse the shared probe instead of generating platform-specific account logic:

```python
from host_runtime import identity

probe = {}
actual = identity(session, timeout=15, evidence=probe)
# actual: {"username": ..., "effective_uid": ...}; inspect probe separately.
```

This is a checkout-level helper in tools/, not a new versioned Core API. `console=True`, `target=...` and the existing verification record are supported by the same helper; an appropriate authenticated console and its dependencies must already exist. Core privilege scopes and the inventory access gate reuse the shared helper; this does not authorize entering a privilege scope or executing inventory. Backend extensions belong in the shared probe with platform detection, verifiable OS identity, bounded output, failure preservation, public tests and documentation, rather than user-generated connection wrappers.

Evidence: a real VMware ESXi 7.0.0 build 16324942 direct root login through two SSH hops passed the updated check-access on 2026-10-16: UID 0, sudo not_needed, strict cleanup without errors. BusyBox on that host lacked the id applet; both system Python paths could read the effective UID. Synthetic cases cover ordinary users, target mismatch, missing tools, malformed/truncated output, fallback selection and CLI failure reporting. Other ESXi releases, additional non-root accounts, native ESXi su/sudo and inventory execution remain outside this evidence; see the later root-shell login verification below. Public API references: Python [effective UID](https://docs.python.org/3/library/os.html#os.geteuid) and [account lookup](https://docs.python.org/3/library/pwd.html); a Broadcom [ESXi troubleshooting example](https://knowledge.broadcom.com/external/article/427365/commands-from-ssh-session-on-esxi-host-f.html) also identifies /bin/python. These references support the interfaces, not universal ESXi-version compatibility.

### Diagnose ESXi identity failures

Interactive id results can differ from SSH exec results; inspect access.identity_probe.id_exitcode.
An exit 2 missing-id signature still requires the VMkernel gate and successful fixed
Python UID/account probes. After any rejection, sudo stays unattempted and the report
retains identity_failed plus the specific identity_error.reason_code.

If configured_identity_probe.matched is false, compare its actual and expected UIDs.
A configured ordinary account can produce a shell with effective root UID on the
observed ESXi exec path. The connection-level ESXi root-shell model can accept that relationship with the evidence below. A numeric mismatch remains visible in matched; acceptance is recorded separately by identity_model and accepted_by. Other platforms and su/sudo target comparisons keep strict UID matching. Do not rewrite the configured account to root to hide the distinction. Report account/UID evidence
without claiming the SSH server's internal cause from these probes alone.

Use the existing authorized `check-access --host HOST --root ROOT --json --quiet` command.
It opens real configured connections; collection, remote installation, configuration
writes and other hosts are outside that command's diagnostic scope. Reuse the shared
probe rather than adding recipe-specific identity fallbacks. No new configuration key
is needed. Additive access diagnostics do not change retained inventory schemas.

Native evidence (2026-10-16): a root login returning exit 2 and the missing-id signature
over SSH exec was confirmed as VMkernel; fixed Python probes returned UID 0 and matched
the root account. Another configured non-root login returned actual root UID 0 and
expected account UID 1000. With the verified final-hop login and ESXi root-shell model, both paths now pass while preserving those distinct identities. Both configured paths used
two SSH hops and strict cleanup completed without errors. Host bindings/credentials
are private and are not test fixtures. Other ESXi releases and authenticated su/sudo
remain outside this evidence.

Delivery checks: 554 tests passed on each of Python 3.11.15, 3.13.13 and 3.14.4.
Older interpreters reused the selected environment's pure-Python dependencies; this
is not native SSH readiness evidence for those interpreters. Wheel/sdist build,
temporary installation and outside-checkout synthetic exit-2 fallback, configured
UID comparison, accepted ESXi root-shell mapping and local Core/recipe smoke checks passed on 3.14. Changed-document
links/dates and skill frontmatter passed. Native host evidence is limited to the
specific two-hop probes described above; no host configuration was rewritten.

## SSH login and ESXi root-shell identity

An SSH authentication principal and the shell's effective OS account are distinct.
The shared connected lifecycle records login_identity {username, source: ssh_connection}
only after the complete target chain connects, using the username passed to the
successful final-hop Session.connect call. This includes resolved aliases and never
uses a jump-host principal or YAML alone as authentication evidence. Local-only
connections instead derive the account from verified effective identity.

The shared verify_connection_identity helper records shell_identity and the observed
actual_identity, then checks the configured/resolved login relationship. Its default
identity_model is uid_match (or effective_identity for local observations without an
account comparison). A connection-level numeric UID mismatch may be accepted as
esxi_root_shell only when all of these conditions hold:

1. The final-hop successful SSH username is known and agrees with an explicit
   configured user when one is present.
2. The initial and configured-account probes observe the same shell actor at UID 0.
3. VMkernel is verified from an untruncated uname -s result. The existing missing-id
   ESXi probe supplies this evidence; working-id paths make the same bounded kernel
   check when considering a root-shell mismatch.
4. The configured/resolved account lookup and UID comparison complete. Missing tools,
   failed/malformed/truncated probes, changing actors and non-root mismatches fail.

This model describes observed ESXi shell capability, not a verified vSphere role or
permission for every command/API. No configuration override, account rewrite or privilege
attempt is added. Other kernels and identity(..., target=...) calls used for su/sudo
remain strict. The special rule belongs in connection identity verification only.

Access reports contain login_identity, shell_identity and identity_model. Existing
connection_identity remains the verified initial shell actor used for restoration;
actual_identity may later describe an elevated collector actor. For an accepted ESXi
mapping, configured_identity_probe.status is success, matched remains false to describe
numeric UID inequality, and accepted_by is esxi_root_shell. The absence of a failure
reason and the explicit policy distinguish successful relationship verification from
simple UID equality. A synthetic example is:

```json
{
  "login_identity": {"username": "operator", "source": "ssh_connection"},
  "shell_identity": {"username": "root", "effective_uid": 0},
  "identity_model": "esxi_root_shell",
  "configured_identity_probe": {
    "status": "success",
    "actual": {"username": "root", "effective_uid": 0},
    "expected": {"username": "operator", "effective_uid": 1000},
    "matched": false,
    "accepted_by": "esxi_root_shell"
  }
}
```

The access table shows PASS connection for the SSH login, PASS identity with
shell=root, uid=0 (ESXi), and SKIP sudo / already_root. Status is success when all
required checks and cleanup pass. Sudo/account policy and extra-user exclusion bind
to the authentication principal, not the root shell username. This prevents treating
the login as another su target or borrowing another account's credentials. Restoration
still compares the original shell name/UID, and explicit privilege targets still need
their own strict verification. Authenticated ESXi su/sudo console support is not added.
Core scopes and inventory access reuse these distinctions; raw diagnostics are additive,
while retained inventory schemas remain unchanged.

Use the existing authorized check-access --host HOST --root ROOT --json --quiet CLI.
No new setup, dependency or remote file is required. Native two-hop verification on
2026-10-16 passed both a direct root login and an ordinary login whose shell runs at
UID 0. Public tests use synthetic accounts and cover final-hop/alias evidence, missing
principal, non-root/Linux mismatch rejection, strict privilege targets, account-policy
binding and no duplicate login-user su. Host bindings and credentials remain private.
Broadcom's [SSH access guidance](https://knowledge.broadcom.com/external/article/323375/enabling-secure-shell-ssh-access-for-loc.html)
also distinguishes SSH shell access from UI-role restrictions; it does not establish
this behavior on every ESXi installation.

_Last modified: 2026-10-16_
