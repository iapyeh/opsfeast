# Diagnose and repair the SSHScript environment

Use this guide when an operation reports `RuntimeEnvironmentError`, an
`sshscript_*` environment reason, or different import/distribution versions.
These failures concern the local Python installation, not necessarily hosts.yaml.
The shared runtime guard stops before creating an SSHScript Session.

## Check the interpreter before retrying a host operation

From the trusted checkout, use the **same Python executable as the failing
command**:

```sh
python3 -B tools/check_environment.py --json
```

The command reads local packages and the bundled skill; it does not install,
connect, run proxy commands or initialize a Feast. It returns 1 when not ready.
After switching environments or updating packages, run this check before retrying
host operations. `opsfeast.py check` validates host configuration and does not
replace this environment check.

Read `interpreter` and `packages.sshscript`. The SSHScript report contains
`required_version`, `import_version`, `distribution_version`, `module_path`,
`distributions` (version and metadata_path per distinct installation record), and
`ready`. Source verification appears under `source` once the package and metadata
checks pass; `reviewed_source_commit` identifies the required source. Missing
values are null, not successful checks. Failure adds `reason`, `summary`, `hint`
and `repair_commands`. Import/metadata inspection failures expose only exception
types, never arbitrary third-party exception messages. Local paths may identify
the user and should be reviewed before sharing diagnostics publicly.

| Reason | Meaning and next action |
| --- | --- |
| `sshscript_import_failed` | The selected Python could not import SSHScript. Check interpreter/package availability; inspect `import_error_type`. This alone does not prove a missing OS library. |
| `sshscript_metadata_missing` | Import may work, but pip/distribution metadata is missing. Review the module path and reinstall the reviewed release in the selected environment. |
| `sshscript_metadata_unreadable` | Metadata inspection failed. Review the reported exception type, permissions and installation before repairing. |
| `sshscript_duplicate_metadata` | More than one distinct SSHScript metadata directory is discoverable, even if versions match. Review every listed location; do not assume upgrading removed old metadata. |
| `sshscript_version_mismatch` | Import or distribution version differs from the required release. Update the selected environment within its authorized scope. |
| `sshscript_source_mismatch` | Versions match, but package/type files differ from reviewed release hashes. Review the installation's provenance; do not bypass the source guard. |

For example, import 7.0.1 with distribution 7.0.0 and both
`sshscript-7.0.0.dist-info` and `sshscript-7.0.1.dist-info` is reported as duplicate
metadata. The same condition fails even when metadata lookup happens to select
7.0.1. Repeated discovery of the same resolved directory is counted once.
This detects the installation state; it does not establish why an earlier pip
upgrade left that state.

## Repair only the selected environment

First confirm that the reported interpreter is the intended environment and that
its modification is authorized. If the wrong interpreter was selected, use the
correct existing environment and rerun the check instead of changing another one.
The diagnostics supply shell-quoted commands using that exact interpreter and the
trusted installation's environment-check path; agents should reuse those commands.
Do not run bare `pip` and assume it belongs to the failing Python.

For an approved reinstall of the currently required release, the sequence is:

```sh
# Replace this synthetic path with the interpreter printed by the check.
SELECTED_PYTHON='/path/to/selected/venv/bin/python3'
"$SELECTED_PYTHON" -m pip uninstall sshscript
"$SELECTED_PYTHON" -m pip install --force-reinstall --no-deps --no-cache-dir --index-url https://pypi.org/simple 'sshscript==7.0.1'
"$SELECTED_PYTHON" -B tools/check_environment.py --json
"$SELECTED_PYTHON" -m pip check
```

Review pip's uninstall target before accepting. Stop on command failure. Reinstall
uses the official PyPI index and skips the cache; `--no-deps` preserves other
dependencies, so `pip check` and full readiness remain necessary. For a managed
mirror, offline environment or intentionally customized installation, review a
trusted matching artifact under the [package update procedure](skill-updates.md#update-sshscript-with-one-prompt)
instead of bypassing local policy or assuming network access. If PyPI cannot
supply the release, preserve the error and investigate index/access availability.

If duplicate records remain, review their paths again and the output of each pip
step before planning additional cleanup. Do not delete site-packages, copy a
metadata directory, edit version labels, rebuild the venv or upgrade unrelated
packages to hide the mismatch. Neither OpsFeast nor this procedure automatically
modifies the environment. Checks do not install or retry operations.

Restart long-running OpsFeast/TUI/Python processes after repair so they reload
imports. A successful check proves local package/skill readiness, not SSH,
su/sudo, host reachability or recipe success. Retry the original operation only
within its existing authorization; environment repair does not authorize new
host operations.

## Read failures in CLI, TUI and saved results

The shared guard is used by host diagnostics, Core session acquisition and the
Python recipe runner. `RuntimeEnvironmentError` is a `ConfigError` subclass.
Catch `ConfigError` as before; code comparing exact error type strings must now
accept `RuntimeEnvironmentError`. Duplicate metadata is rejected even when the
previous first-record version lookup would have passed. No hosts.yaml or stored
data migration is needed, and historical failures are not rewritten.

Host-init failures preserve `error.reason`, `error.message`, `error.hint` and
`error.environment`, with the same reason in `reason_code`. Recipe batch runtime
failures preserve the structured `error` object and reason as well. Standalone
test-connection records the error using its existing connection-failure shape.
Terminal diagnostics show environment details and host-init/access/recipe-batch
failures also write them to stderr without requiring debug flags. In the TUI,
use **Progress / errors** for stderr and the raw output tab for the JSON record.
The table may retain a broader test/connection stage; read the structured error
for the environment cause.

`--traceback` still prints frames without arbitrary exception messages, source
lines or locals. Only this controlled runtime diagnostic is expanded; other
third-party exceptions retain their existing filtering. For earlier records that
contain only `ConfigError`, the original message cannot be reconstructed. Run
the read-only environment check before deciding whether a host retry is needed.

The checkout helper `sshscript_runtime.inspect_runtime()` returns this report;
`require_runtime()` is an internal guard, not a Core SDK installation API.
Synthetic regressions in `tests/test_runtime_diagnostics.py` cover duplicate
metadata, partial/missing packages, source drift, pre-Session rejection, persisted
host-init diagnostics, terminal/TUI data and command quoting. They do not prove
pip repair behavior on every environment or native SSH access.

*Last modified: 2026-10-31 13:08:20*
