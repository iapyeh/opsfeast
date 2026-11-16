# Embedded Console consumer validation prototype

This directory is a **test-only browser adapter and consumer fixture**, not an OpsFeast console command, installed Core API or production integration. It uses the unpublished SSHScript unified Console revision, not the published package with the same 6.0.0 version. No existing profile, host settings or credentials are read. It creates disposable local configuration with `Validator`; no profile is initialized.

## Reproduce

Set `SOURCE` to the user-approved read-only SSHScript checkout and `WHEEL` to its local wheel. Use a new temporary virtual environment, install that local wheel offline, and supply OpsFeast's already installed dependencies read-only or install them in the temporary environment within authorization. Never replace the normal OpsFeast/shared environment. Run all commands from this OpsFeast checkout.

```sh
TEST_PYTHON=/path/to/isolated-test-venv/bin/python
SOURCE=/path/to/approved/sshscript/working_branch
WHEEL=/path/to/local/sshscript-6.0.0-py3-none-any.whl
EXPECTED_SHA256=da9708ef560aa925f4aac837189fecdbf32c6f04c4b4be5f36259a9485579ce0

"$TEST_PYTHON" -B tests/console_prototype/verify_artifact.py \
  --source "$SOURCE" --wheel "$WHEEL" --sha256 "$EXPECTED_SHA256"
CONSOLE_EVIDENCE=/path/to/new-evidence-directory \
  "$TEST_PYTHON" -B tests/console_prototype/test_validation.py
"$TEST_PYTHON" -B tests/console_prototype/repro_ctrlc.py
CONSOLE_RETEST_EVIDENCE=/path/to/new-ctrlc-evidence-directory \
  "$TEST_PYTHON" -B tests/console_prototype/test_ctrlc_retest.py
"$TEST_PYTHON" -B tests/console_prototype/app.py \
  --port 8766 --journal /path/to/new-ui-events.jsonl
```

The artifact verifier compares every shipped Python module/stub to both flat source and installed files. A different digest, source drift or import mismatch is a rebuild/review prerequisite. A version string alone is insufficient. The first candidate (SHA-256 f3ae81f4f34800b83d66bba1a61c97b4dd7619eda2245e25e16adbbf581a6923) failed the enter-program Ctrl-C readiness assertion. Preserve that historical evidence. The new candidate at source commit 67f6b174e76e9b58e1d0d44553bd49ba02fdd881 passes the unchanged minimal reproduction and original 12 consumer tests. Five additional Ctrl-C checks cover idle/running/ignored/delayed/exit cases, including all three cleanup endings. Follow state/result; KeyboardInterrupt is diagnostic metadata and does not by itself mean failed or ready. No prompt-text parsing or extra input is used to repair readiness. Use a new evidence directory for each run because journals append.

Open `http://127.0.0.1:8766` and use the visible controls. Open fixture creates an OpsFeast-held Session and borrows that exact object. Submit cell accepts Python/dollar input; Start shell job uses asynchronous `start_command`/`poll`. Enter Python starts a real local program; Send program input preserves its variables. Ctrl-C, EOF, Leave one layer, Close console and Host exception exercise distinct lifecycle paths. `quit()` is a cell submission. Probe owner reuse is allowed only after confirmed borrowed cleanup and records a real command result. Stop the server with Ctrl-C after closing the test console.

All Console operations, including construction and teardown, run on one fixed worker. HTTP/UI threads only enqueue operations or read cached events. Synchronous Python evaluation queues later operations; it is not safely preemptible. The UI heartbeat remains independent. The displayed state is the last structured backend update; it is not proof that a queued Python request has completed. This minimal UI does not implement production request correlation or queue cancellation.

## Integration boundary

`adapter.py` explicitly borrows at the existing checkout-level `host_runtime.connected` owner, which reuses `connection_plan` and cleanup. It does not access Recipe._actor or mutate Console internals/reserved variables. The public Core session facade is not a raw SSHScript Session; this experiment does not add a Core handover method. A formal toolkit API still needs ownership/scope integration, API documentation and supported UI design.

The synthetic hosts file is loaded through OpsFeast `Validator`. Explicit su/sudo targets reuse `host_runtime.privilege_password`, including target declaration, actor scoping and Boolean sudo policy. No root-candidate selector is reimplemented; automatic bounded root selection is outside this prototype. Credential hooks run before switches; observers record only safe metadata. Native account switches are refused in local mode. Synthetic tokens are used only in fixture memory/configuration and never placed in submitted source or UI history. No input history, namespace, result.command or arbitrary exception text is serialized. Arbitrary Python/output is trusted test code, not a sandbox or general secret filter.

`fixtures.py` is explicit transport/account test instrumentation, not a compatibility layer or monkey patch. Simulated su/sudo opens real nested Bash channels but reports synthetic identity probes; it never runs operating-system su/sudo. Its ancestor is simulated metadata, not an actual SSH jump. Faults inject identity-probe failure, exit failure, failed Session health probe, or active channel failure through the fixture's transport. These results do not validate native SSH, PAM, sudo policy, real identity restoration or SSH jump transport.

Unknown recovery downgrades displayed identity to unknown/unverified and prevents owner reuse; failures never trigger account retries. Shells use real PTYs by default although the host needs no TTY. Shell jobs reject stdin; use enter() for a known text-program protocol. Python evaluation/stdout redirection is process-wide, so this prototype hosts at most one active Console per process. Full-screen terminal emulation is unsupported.

_Last modified: 2026-10-23 18:24:07_
