# Run an authorized operation through Core

Use this guide for agent-authored temporary programs over an existing profile.
First discover a suitable [recipe or module](agent-capabilities.md); use the
[Core contract](core-api.md) and matching [SSHScript skill](../skills/sshscript/SKILL.md)
for exact interfaces. Host selection, root access and command execution require
the user's applicable authorization. Examples use synthetic host IDs and do not
install software, change services or grant permission to connect.

## Select a profile and inspect host IDs

From the trusted checkout root, or an authorized installed package:

```python
from opsfeast import Instance

instance = Instance.open(installation="/srv/opsfeast")
profile = instance.profile("main")
hosts = profile.hosts.list()  # dict: {host_id: masked_config}
host_ids = list(hosts)
for host_id, config in hosts.items():
    print(host_id)  # Do not dump settings or credentials.
if "web-01" not in hosts:
    raise ValueError("Select an existing host ID")
```

`profile.hosts` is a snapshot manager, not callable or directly iterable.
Use the returned dictionary for membership and iteration. These are configured
IDs, not necessarily DNS names, enabled execution targets or verified reachable
hosts. Returned configurations are masked copies; editing them does not save
configuration. Use `profile.hosts.get(host_id)` for one host and explicit
`profile.reload()` after authorized configuration edits. Do not build execution
connections from masked values. Public Core imports do not require inserting
`tools/` into sys.path. Check package installation guidance when running outside
the checkout.

## Read saved system context

Inside a standalone or runner-provided Recipe, use `recipe.host_info` for saved
host-init OS/distribution/version, architecture and optional login-PATH python3
version/path. Each access returns a copied fixed-key dictionary; missing values
are None and no probe runs. See [keys and example](core-api.md#saved-host-information).
An authorized host-init collects or refreshes these facts without requiring inventory.
Users rerun it after OS/Python/PATH changes and specify other Python environments.

## Preserve Python and remote shell text

Prefer a reviewed `.py` file for substantial logic. For a short program, use a
quoted heredoc in the local shell. The following read-only example assumes the
trusted checkout as the working directory, its already selected `.venv`, an
existing main profile and authorization to connect to web-01 and enter root:

```sh
./.venv/bin/python -B <<'PY'
import shlex
from opsfeast import Instance

profile = Instance.open().profile("main")
with profile.recipe("web-01", timeout=60) as recipe:
    with recipe.root() as root:
        def run(command, *, step, seconds=60):
            print(f"Starting: {step}", flush=True)
            try:
                result = root(command, check=False, command_timeout=seconds)
                if result.exitcode != 0:
                    raise RuntimeError(f"{step}: command exited {result.exitcode}")
                return result
            except Exception as error:
                error.add_note(f"Operation step: {step}")
                raise

        # Literal data must survive both the local shell and the remote shell.
        text = "limit_req_zone $binary_remote_addr zone=example:10m rate=10r/s;\n"
        command = shlex.join(["printf", "%s", text])
        result = run(command, step="preview literal configuration", seconds=10)
        print(result.stdout, end="")  # Only this known non-secret example output.
print("Operation and scope cleanup completed.")
PY
```

Do not wrap substantial Python source in `python -c "..."`. The local shell
expands `$binary_remote_addr` and `$(date ...)` before Python sees them, including
text inside Python triple quotes or a future remote `<< 'EOF'` block. Unescaped
double quotes can also break the outer shell argument. Quoting the local heredoc
delimiter protects the Python source; `shlex.join()` separately quotes dynamic
arguments for the remote POSIX shell. Neither makes arbitrary shell code safe.
Build reviewed remote commands deliberately; do not interpolate credentials or
untrusted values into shell syntax. Local execution time and remote host time
are distinct: run a remote date command when the remote clock is intended.

`root()` yields a callable console, not a child Recipe. Retain each returned
CommandResult and read `stdout`, `stderr` and `exitcode` (not exit_code or
returncode). Live console buffers are not completed-result snapshots. Inspect
the matching SSHScript result contract for truncation and managed-job evidence.
The step label should be a fixed safe description; do not print arbitrary
commands, settings, exception text or output that may contain secrets.

## Bound commands and preserve failure evidence

`profile.recipe(..., timeout=60)` supplies per-stage/per-command defaults, not
a total 60-second recipe deadline. `root(command, command_timeout=...)` overrides
one command's completion deadline. `check=False` permits nonzero exit codes to
be interpreted explicitly; it does not suppress timeout, connection or cleanup
exceptions. A timeout can occur before a result is returned, so code after the
call cannot be relied on to print diagnostics. Use safe step labels, a bare
`raise` to retain the traceback and any exception-provided evidence; do not
fabricate an exit code. Where the documented exception provides `.result`,
preserve its partial output/truncation/termination evidence privately. Do not
assume every TimeoutError provides a result.

Choose longer finite budgets deliberately for reviewed slow operations such as
package installation. Increasing a deadline does not answer an interactive
prompt, resolve a package lock or establish successful completion. For streaming
or explicit cancellation, use `root.start()` and the documented managed-job
lifecycle, including finite timeout, stop_timeout and result evidence; see
[SSHScript console jobs](../skills/sshscript/references/api-guide.md#40-foreground-jobs-inside-shell-sudo-and-su).
Do not invent a generic send-Ctrl+C recovery loop. PTY and pipe recovery differ;
interrupting an installation can leave work incomplete. Stopping a job, closing
a channel, remote termination and privilege restoration are separate outcomes.
Core's timeout is not a wall-clock cap on all nested cleanup stages.

Let exceptions leave both root and outer Recipe scopes before handling the
failure at the program boundary. If root cleanup also fails, Core retains the
body exception, adds a cleanup note and disables the shared session. Inspect
safe fields from `recipe.report`, especially privileges restoration_verified,
cleanup_error and scope_error; reports are copies and do not repair a session.
Do not clear failure state or retry mutating operations automatically. If code
catches the body exception inside the outer Recipe scope, it must not claim
success: an unsafe scope still raises CoreError root_scope_failed on outer exit.
A cleanup-only failure may raise its own exception. Connection cleanup is a
separate stage and may add evidence. Keep the original exception and cleanup
evidence together rather than replacing one with a generic success/failure.

## Verify changes and turn reviewed work into a recipe

Before authorized writes, preserve the original files and prepare a recovery
plan. Check the exact target, expected match count and postconditions; a string
replacement that matched nothing must not report success. Prefer validated,
atomic replacement where supported and preserve unrelated settings. Syntax
validation alone does not prove that an intended rule was inserted. Verify
service state and the requested behavior after an authorized reload/restart.
After a timeout, record partial/unknown outcomes and reconcile actual state
within the existing authorization before deciding whether a retry is safe.

Follow [exploration to recipe](../skills/opsfeast-recipes/references/exploration-to-recipe.md)
for repeatable work: reviewed code, private bindings, backups/recovery,
verification, execution evidence and applicable retention. Direct Core calls do
not automatically journal operations or retain results; use the existing
[operation journaling contract](retention-replay.md) or the recipe runner as
appropriate. This guide introduces no host collection protocol or new API.

## Verification limits

`test_recipe_root.py` covers timeout propagation, simultaneous cleanup failure,
disabled-scope reuse, swallowed exceptions and connection closure with synthetic
identities. A credential-free local Bash case uses the installed SSHScript
console through the Core root facade with simulated root selection; it does not
perform sudo or establish real SSH, PAM, package-manager or service behavior.
`test_core_agent_operations.py` executes this guide's shell example against a
synthetic Core boundary and local printf to check literal dollar/newline
preservation and failure reporting without contacting a host.

*Last modified: 2026-10-29 22:51:57*
