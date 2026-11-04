# Chat-owned Console worker 0.3.0

Use the shipped `python -B -u -m opsfeast.console_agent` worker for incremental
human/agent Console work. Do not generate a temporary bridge. The worker owns one
SSHScript Console and its configured connection; the Web server owns durable blocks,
read/response handlers and SSE. Creation returns a reader URL before any SSH
connection. This is separate from the older exact-plan `/interactive` executor.

For the human/agent operating principles agreed during interactive trials, read [the chat-shell skill procedure](../skills/opsfeast-interactive/references/chat-shell.md). Each run/sudo command block contains the actual current Console prompt and input on one line. The reader shows an accessible processing indicator while a command, analysis or status block is streaming. Routine login does not require a screenshot or browser QA before reporting success.

The returned `reader_url` identifies the worker session and includes Profile/host
navigation context for remote targets. Keep the worker handle and session UUID
paired; never infer the execution target from the human's selected browser tab.
New workers get separate tabs. See [live and historical readers](console-records.md#separate-live-interaction-from-historical-reading).

## Availability and authorization

Run from the trusted OpsFeast checkout with its selected Python and SSHScript
**7.0.1** (both import and distribution are checked). Start the existing local Web
server normally; its Console writer token is required. No extra package, temporary
program or Web restart is required for the worker. Use the launcher's reported
writer-token path, never credentials from documentation. The administrator must
sign in to read the river; reading does not require the settings unlock.

A writer token permits records, not host execution. Obtain the human's host and
operation scope first. Ordinary login needs no advance privilege choice. After
explicit authorization, submit sudo/su with the exact target and a nonsecret
`authorization` description of the human's grant. The worker arms only that switch,
bound to its current host and effective actor, and clears it after the attempt.
This text is an agent report, not machine-verifiable proof of human consent.
Reuse an existing applicable grant; never create a redundant approval click.
Configured credentials do not grant permission, and account switching does not
expand an inspection into changes. Shell commands remain trusted code, not a sandbox.
No alternate account or credential is tried automatically.
Do not run commands producing unknown secrets. Values delivered through the private input channel are redacted from subsequent output, including split chunks; this is not general output-secret detection.

## Start, show, then connect

```sh
python -B -u -m opsfeast.console_agent \
  --token-file /srv/opsfeast-data/.opsfeast-console-writer-8740.token \
  --host web-01 --title 'web-01 interactive inspection'
```

For configured hosts, omitting `--profile` selects `default_profile` from the checkout's `.opsfeast.yaml`, using the same Core selection as other commands. An explicit `--profile NAME` overrides it for this worker only; it never changes the saved default. Do not assume `main` or copy an example profile. Read-only configuration loading happens before reader creation; invalid/missing selection fails without a reader or connection, with no fallback. The selected profile/configuration snapshot is held for this worker; start a new authorized worker to select another profile.

Optional flags: `--url http://127.0.0.1:8740`, `--idle-timeout 900` (1–3600
seconds). `--local` replaces `--host` for credential-free local verification;
managed account switches remain denied in local mode.

Keep this process's stdin open in the agent's execution tool. For PTY stdin, the worker disables canonical input and echo before reporting created, preserving signal handling and restoring the original terminal settings on exit. This avoids OS canonical-line truncation of JSON controls; the documented worker byte limits still apply. Its first stdout
JSON line is:

```json
{"type":"created","protocol_version":"0.3.0","session_id":"UUID","reader_url":"http://127.0.0.1:8740/console/UUID","profile":"selected-profile","hosts_file":"/srv/feast/hosts.yaml","state":"awaiting_connect"}
```

`profile` and `hosts_file` identify the actual selection before connection; both are null for `--local`. Check these against the authorized scope. A mismatch requires stopping before `connect`, not switching targets automatically. These fields were added in protocol 0.2.0 and remain present in 0.3.0.

**Immediately open this returned URL in the user's visible browser and preserve
that tab.** Do not wait for connection success or run a browser QA sequence first.
Then send one JSON object per line on this same process's stdin:

```json
{"op":"connect","request_id":"connect-1"}
{"op":"run","request_id":"inspect-1","command":"hostname; id -un","timeout":30}
{"op":"sudo","request_id":"sudo-1","username":"root","authorization":"Human authorized root inspection on this host","purpose":"Inspect protected files","timeout":15}
{"op":"run","request_id":"inspect-2","command":"id -u","timeout":30}
{"op":"close","request_id":"close-1"}
```

These are examples, not an automatically approved plan. Send each operation only
when authorized and after its predecessor returns. Sudo/su require runtime authorization and use one selected credential source;
identity metadata reports the actual result. No reconnect is needed for a switch. `connect` uses Core's host/jump
enabled policy, connection plan, target fingerprint check and cleanup ownership.
It does not run host-init, inspect cron, retry or switch profiles automatically.

Supported operations are connect, run, sudo, su, leave, enter, input, secret, poll, activity and close. Every
request requires a unique nonempty `request_id` (max 100 characters). Duplicate
IDs are rejected, never executed again; IDs are tracked only for this worker's
lifetime. Unknown fields/operations and invalid single-line command/deadline input
are rejected. Run command max 16 KiB UTF-8; timeout is integer 1–300 seconds.
Raw Python/dollar evaluation and full terminal emulation are not exposed.
Privilege targets use the explicit runtime switch controls below. Entered programs and private input use the bounded operations below.

## Runtime account switching (worker 0.3.0)

Start with the normal host command and connect as its configured login account.
Only when the human authorizes the needed identity, send one of:

```json
{"op":"sudo","request_id":"root-1","username":"root","authorization":"Human authorized root inspection on this host","purpose":"Read protected diagnostic files","timeout":15}
{"op":"leave","request_id":"back-1","purpose":"Return to the previous account","timeout":15}
{"op":"su","request_id":"app-1","username":"appuser","authorization":"Human selected appuser for this task","purpose":"Inspect the application account environment","timeout":15}
```

`sudo` defaults username to root; `su` requires a username. Both require nonblank,
single-line `authorization` (maximum 1000 UTF-8 bytes); it must accurately describe
an existing human grant. The agent must not invent one or infer it from a hostname,
a configured account or a credential. Each worker request has a fresh ID. Grants
for one host/task do not authorize another host or broader effects.

The normal configured-login and later authorized switch stay in one SSH connection
and river. Nested sudo/su layers are supported from verified SSH/sudo/su identities;
each switch needs applicable authorization. `leave` removes one identity layer and
reports the parent effective account. It cannot leave the base SSH layer: use close
to disconnect. Leave an entered application before switching accounts. Never send
raw su/sudo commands through run or disguise a rejected command.

Sudo selects credentials/policy for the **current actor**, including an account
reached through su; another actor cannot inherit login-scoped legacy credentials.
An actor with sudo disabled remains blocked. Su selects the **target account**
password; missing credentials use the existing private-input channel if available.
An explicit target need not be pre-registered in hosts.yaml: a missing su password
is supplied by the human, not guessed. Root-to-user su needs no target password.
Secrets never appear in control JSON or authorization/purpose text. There is no
credential retry, different-account fallback or automatic permission repair.
Inspect returned identity; command failure or cleanup uncertainty is not a switch.

All normal operations accept optional single-line `purpose` (1–1000 UTF-8 bytes).
It creates a completed analysis block **before** the command block and remote
submission. The stored title is metadata; the river shows the explanation
directly, without a title or separate-window arrow. State the concrete question/action, not a duplicate command.
This explains work; it does not require another approval. Do not put private input
in purpose text. The worker reports authorization separately from actual identity.

This replaces --sudo-root and Core sudo_root=True; neither old interface is
supported. New callers use runtime sudo/su controls and Core switch_authorizer.
Existing worker processes retain their startup implementation; start an updated
worker once when adopting this version. Subsequent grants need no new worker,
river, Web restart, profile switch or SSH connection.

## Entered programs and private input (worker 0.3.0)

The worker now keeps an explicitly entered text program in the same Console.
This is separate from finite shell `run`: never launch a password-prompting
application through `run`. No arbitrary Console Python cells are accepted.
The supplied command is trusted code; authorization and database privileges remain
the operator's responsibility. Database root is distinct from operating-system root.

```json
{"op":"enter","request_id":"db-enter","command":"mysql -uroot -p example_db","prompt":"> ","secret_prompt":"Enter password:","exit":"\\q","timeout":15}
{"op":"secret","request_id":"db-password","label":"MySQL root password for this host / example_db","timeout":120}
{"op":"input","request_id":"db-identity","text":"SELECT DATABASE(), CURRENT_USER();","timeout":15}
{"op":"leave","request_id":"db-leave","timeout":15}
```

Send each operation only after inspecting its predecessor. `prompt` and
`secret_prompt` are literal output markers, not regular expressions. `enter`
requires command, prompt and exit; secret_prompt is optional. Use a marker that
matches the actual application's prompt, not example SQL output. `waiting_secret`
means the configured secret marker was observed; `secret` is accepted only then.
It contains no password argument. The worker emits `secret_requested` with a public
request UUID and expiry, then waits for the signed-in human's password submission.
A successful submission is not proof of authentication: inspect the following
`waiting_input`, actual client greeting and an authorized identity query.
No credentials are retried automatically. Do not repeat `secret` after an
uncertain submission; reconcile the recorded result and program state.

`input` sends one ordinary line without evaluating Python, and is rejected while
waiting for a secret. It is recorded, so never put credentials there. `poll`
observes later output; a read budget ending in `running` retains the program and
does not claim readiness or completion. `leave` sends the configured exit sequence
once; confirm `session_state: ready` before shell work. Input/secret need a reported
ready/secret state. Ordinary `run`, sudo and nested enter are refused while a
program is active. `session_state: program` is distinct from shell readiness.
Prompt/input output is source evidence, not a full terminal emulator. Neither
`waiting_input` nor a processing indicator proves SQL success.

The private input channel is [ephemeral secret delivery 0.1.0](console-secrets.md).
Only its redacted lifecycle messages are recorded. Never ask for a password in
chat or ordinary river forms. The worker must stay running while the human replies;
a completed agent turn has no automatic wakeup. A new worker and Web restart are
required to activate this newly installed code; old workers retain old behavior.
Restart preserves saved records but disconnects active record forwarding and
invalidates launch tokens. Reconcile existing work before restarting. Do not
silently reconnect, rerun SQL or switch profiles after restart.

## Output, state and stopping

Connection records include the Core/Console API call before connection, a readable login-success status after entry, and the actual current SSHScript `Console.prompt` joined with each run/sudo input in one command block. A run is displayed as `$(PYTHON_STRING_LITERAL)`, for example `web-01 [root]> $('df -h')`, using Python literal escaping so quotes, backslashes, dollar signs and Unicode remain copyable into SSHScript Console. The worker executes the raw shell command through public `Console.start_command` for streaming and interruption; the displayed dollar expression is its Console-input form, not a bare shell line in a Python REPL. No standalone prompt blocks are emitted. This is the SSHScript prompt, not the remote shell PS1. Raw SSH banners, authentication dialogues and shell startup prompts are not exposed by the current Console API and are not fabricated. The prompt property is verified against the public [SSHScript 7.0.1 source](https://github.com/iapyeh/sshscript/blob/b8d7c8fe88b4096e8a58e6609ba805ee2bf41049/src/sshscript/interactive.py). Identity JSON remains stored but appears only as a readable toolbar summary in the river; the dedicated identity-block page retains full details. Small gaps separate visible blocks.

The worker durably creates each command block with its initial prompt/input text in the first HTTP write, before submitting anything to Console. First output is likewise included when its output block is created, then appended as chunks arrive. The SSE service wakes subscribed readers immediately after each HTTP commit instead of waiting for the periodic recheck; the 250 ms recheck remains for writes from another process. Browser rendering, network/SSH latency and application-side buffering still apply; no absolute latency guarantee is made. Console stdout/stderr streams
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
`session_state: "ready"` reports that the worker retained its shell after a successful command or a confirmed, normally terminated nonzero command. It does not turn a failed command into success or authorize another command. The actual output is in the river and can be read by the existing
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
the final result and cleanup. A run with a nonzero exit code, no Console error and confirmed termination is reported as failed while retaining the same shell (`session_state: "ready"`); wait for the human's next instruction, without retrying. Sudo failure, deadline/recovery errors, unknown termination and transport/storage exceptions still close the scope. Explicit close also closes after interrupting. Close during a command interrupts first, then closes.
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

## Processing display

The river footer below the latest block and active command/analysis/status blocks show “處理中…” while those blocks are streaming. Finish (including failed/interrupted/cancelled) clears that work indicator. Successful connect/run/sudo then automatically publishes a separate 120-second **Agent 思考中…** report, rendered with pulsing dots. The next command clears thinking before execution. A normal nonzero result waiting for human direction does not automatically claim thinking; cleanup clears it. If connection opening or command submission raises, cleanup finishes the outstanding command block as interrupted. None of these states establishes remote process termination or successful cleanup.

Before writing commentary or a final chat reply, send on the same worker:

```json
{"op":"activity","request_id":"before-chat-1","state":"idle"}
```

When substantive analysis continues after that reply, explicitly report thinking
again with a fresh request ID and `state: "thinking"`. This operation returns
`state: "activity_reported"` and `activity` metadata, never starts a command or
connects, and can also be used before connect. During a running command it is
rejected under the existing busy-control rule; command submission has already
cleared thinking. Preserve fresh request IDs and do not treat a report as a
heartbeat. If the worker has closed, use the record client's activity operation
against that same session rather than reconnecting solely to update the display.

See [the complete activity contract](console-records.md#agent-thinking-and-chat-handoff)
for HTTP/CLI fields, explicit renewal, expiry and event shapes. The browser cannot
sense external chat output; agents must clear before replying or waiting for a
human. Expiry stops stale animation without network polling. Animation respects
reduced-motion preferences. SSE status separately reports record-stream outages.

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
Native local tests also verify that a nonzero command preserves cwd/environment for the next explicitly submitted command and that prompt/input share a block. A real local Console test executes the saved displayed dollar expression itself, including quoted Unicode, dollar signs and backslashes. Profile-selection regressions cover a non-main locator default, an explicit override without registry changes, unknown/missing selection with no fallback, and local mode without profile loading. Core tests cover configured sudo policy and output hooks. These are local/mocked
evidence, not proof of current connectivity or sudo policy on a real host.

*Last modified: 2026-11-04 17:35:31*
