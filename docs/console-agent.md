# Chat-owned Console worker 0.1.0

Use the shipped `python -B -u -m opsfeast.console_agent` worker for incremental
human/agent Console work. Do not generate a temporary bridge. The worker owns one
SSHScript Console and its configured connection; the Web server owns durable blocks,
read/response handlers and SSE. Creation returns a reader URL before any SSH
connection. This is separate from the older exact-plan `/interactive` executor.

For the human/agent operating principles agreed during interactive trials, read [the chat-shell skill procedure](../skills/opsfeast-interactive/references/chat-shell.md). Prompt/input grouping is an accepted presentation requirement that the current separate prompt blocks do not yet implement. Routine login does not require a screenshot or browser QA before reporting success.

## Availability and authorization

Run from the trusted OpsFeast checkout with its selected Python and SSHScript
**7.0.1** (both import and distribution are checked). Start the existing local Web
server normally; its Console writer token is required. No extra package, temporary
program or Web restart is required for the worker. Use the launcher's reported
writer-token path, never credentials from documentation. The administrator must
sign in to read the river; reading does not require the settings unlock.

A writer token permits records, not host execution. Obtain the user's target,
profile and operation scope first. `--sudo-root` allows configured login-account
sudo to root only and does not itself grant human authorization. It is disabled
by default. No credential arguments, automatic retries, alternate accounts or
fallback connections exist. Shell commands are trusted and can have arbitrary
effects; this is not a shell sandbox or an enforced read-only permission system.
Do not run commands producing secrets: output is not automatically redacted.

## Start, show, then connect

```sh
python -B -u -m opsfeast.console_agent \
  --token-file /srv/opsfeast-data/.opsfeast-console-writer-8740.token \
  --profile main --host web-01 --title 'web-01 interactive inspection'
```

Optional flags: `--url http://127.0.0.1:8740`, `--idle-timeout 900` (1–3600
seconds), `--sudo-root`. `--local` replaces `--host` for credential-free local
verification; it cannot use `--sudo-root` and also requires execution permission.

Keep this process's stdin open in the agent's execution tool. Its first stdout
JSON line is:

```json
{"type":"created","protocol_version":"0.1.0","session_id":"UUID","reader_url":"http://127.0.0.1:8740/console/UUID","state":"awaiting_connect"}
```

**Immediately open this returned URL in the user's visible browser and preserve
that tab.** Do not wait for connection success or run a browser QA sequence first.
Then send one JSON object per line on this same process's stdin:

```json
{"op":"connect","request_id":"connect-1"}
{"op":"run","request_id":"inspect-1","command":"hostname; id -un","timeout":30}
{"op":"sudo","request_id":"sudo-1","timeout":15}
{"op":"run","request_id":"inspect-2","command":"id -u","timeout":30}
{"op":"close","request_id":"close-1"}
```

These are examples, not an automatically approved plan. Send each operation only
when authorized and after its predecessor returns. Sudo requires startup opt-in,
uses the configured account's credential selection once, and records actual
Console environment metadata after the attempt. `connect` uses Core's host/jump
enabled policy, connection plan, target fingerprint check and cleanup ownership.
It does not run host-init, inspect cron, retry or switch profiles automatically.

Supported normal operations are exactly connect, run, sudo and close. Every
request requires a unique nonempty `request_id` (max 100 characters). Duplicate
IDs are rejected, never executed again; IDs are tracked only for this worker's
lifetime. Unknown fields/operations and invalid single-line command/deadline input
are rejected. Run command max 16 KiB UTF-8; timeout is integer 1–300 seconds.
Raw Python/dollar evaluation, arbitrary privilege targets, password input, entered
applications and full terminal emulation are not exposed by this worker.

## Output, state and stopping

Connection records include the Core/Console API call before connection, a readable login-success status after entry, and the actual SSHScript `Console.prompt` at readiness and after successful commands. This is the SSHScript prompt, not the remote shell PS1. Raw SSH banners, authentication dialogues and shell startup prompts are not exposed by the current Console API and are not fabricated. The prompt property is verified against the public [SSHScript 7.0.1 source](https://github.com/iapyeh/sshscript/blob/b8d7c8fe88b4096e8a58e6609ba805ee2bf41049/src/sshscript/interactive.py). Identity JSON remains stored but appears only as a readable toolbar summary in the river; the dedicated identity-block page retains full details. Small gaps separate visible blocks.

The worker writes command text before submitting it. Console stdout/stderr streams
forward received text immediately, including text without a newline and output
from synchronous sudo. There is no wait for whole-command completion. Output is
stored as append-only deltas in one block per stream/operation and reaches the
existing reader via SSE. A PTY normally merges remote stdout/stderr, so an empty
stderr block is not evidence that the program emitted no errors. It is not a raw
SSH handshake trace; host keys, authentication secrets and SSH internal markers
are not exposed. Application-side buffering still determines when text arrives.

Worker stdout remains JSON-lines control/result data; it does not mix terminal
text into the protocol. `started` includes request_id and command_block. `result`
includes request_id, state, exitcode, safe error_type, stdout_block/stderr_block
(or null when empty), plus identity for connect/sudo and cleanup when applicable.
The actual output is in the river and can be read by the existing
`console_client content --session SID --block BID`. Do not infer success from
silence, a preview or a prompt; inspect the returned state/exitcode.

During a running shell command, the same control pipe accepts only:

```json
{"op":"interrupt","request_id":"interrupt-1"}
{"op":"close","request_id":"close-2"}
```

Other requests receive `busy_or_invalid_control`; they are not queued for later
execution. Interrupt uses SSHScript's bounded foreground recovery. The immediate
`control_received` message explicitly does not certify a confirmed stop. Inspect
the final result and cleanup. A failed command closes the scope rather than
silently continuing. Close during a command interrupts first, then closes.
Synchronous connection/sudo calls cannot read control until they return; their
finite budgets still apply. There is no browser stop button in this version.

EOF or idle timeout closes the scope. Normal close records Console reuse evidence
and exits the worker. Console reuse `confirmed` is a cleanup probe result, not a
promise that all remote descendants terminated. Core connection scope closure is
also required; an exception reports unknown cleanup. A transport/storage failure
stops processing and attempts cleanup; it never silently drops output or replays
a command. Uncertain delivery must be reconciled with stored blocks. Record
limits, text-only restrictions and errors remain those of [Console blocks](console-records.md).
Unexpected errors expose a safe type rather than arbitrary exception messages.

Successful worker/control completion exits 0 (a command may still have a nonzero
exitcode in its result); worker/runtime/transport failure exits 1, usage exits 2,
and keyboard interruption exits 130. Invalid controls are rejected without
executing, then the worker remains available unless it has closed.

## Questions and response delivery

Use the same session with [console_client block and wait](console-records.md#cli)
to publish structured forms or analysis; a second execution session is unnecessary.
The worker does not consume or fabricate human replies. Run the existing bounded
`wait --session SID --after SEQ --timeout 30` from another agent tool call.
On receiving an authenticated response, **tell the user the choice immediately**;
validate its form/revision/scope before acting. Do not delay acknowledgement for
browser screenshots or a second check of a response already durably received.
A waiting client is notified; an idle/ended model chat is not automatically awakened.

## Persistence, boundaries and validation

Browser closure/reopen recovers records and does not disconnect the worker.
Worker exit cannot be recovered as a live connection: start a new session under
fresh applicable authorization. Web restart retains committed data but invalidates
launch tokens and can break forwarding; no automatic reconnect/resume is supplied.
Use one worker process per Console, on one constructing thread. The Web server
never executes a browser-supplied shell command. General logging, retention,
archival, arbitrary charts/media and remote-process termination guarantees are
not added by this worker.

Reproducible tests: `tests/test_console_agent.py` exercises local HTTP + real local
SSHScript, partial Unicode before completion, stdout/stderr visibility, persistent
shell state, active close, control validation, duplicate refusal and no retry.
Core tests cover configured sudo policy and output hooks. These are local/mocked
evidence, not proof of current connectivity or sudo policy on a real host.

*Last modified: 2026-11-02 17:47:54*
