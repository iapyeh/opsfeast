# Chat-driven interactive SSHScript shell

Use this procedure when the human directs operations incrementally in chat while
watching a Web river. The user's own agent owns the conversation; OpsFeast is the
supporting execution/record tool. Do not require the human to predict all details
in advance. Read the [worker contract](../../../docs/console-agent.md) for exact
fields, states, credentials, supported operations and limitations.


## Enter a text program and request its password safely

Read [worker 0.3.0](../../../docs/console-agent.md#entered-programs-and-private-input-worker-030)
and [ephemeral secret delivery](../../../docs/console-secrets.md) before this workflow.
Use enter → observe waiting_secret → secret → observe waiting_input → input → leave
on the same worker. Exact field names, literal prompts, timeout/exit behavior and
an example MySQL command are in the canonical worker guide. MySQL root does not
authorize OS root. Ordinary SQL/input is recorded; passwords never belong in chat,
input operations, command arguments or ordinary durable forms. The secret operation
opens an authenticated, short-lived password field; the worker consumes its value
without returning it to the agent. Keep the worker alive and report expiry,
cancellation, uncertain delivery and authentication failures without retrying.
Historical readers provide no secret field. Old workers must be replaced and the
Web service restarted after this update; preserve existing records and reconcile
active work before doing so. No automatic reconnect or program replay exists.


## Choose root access without a redundant account question

When the human grants root for a host/task, use the verified login account's
managed sudo unless they explicitly selected another method/account, the account
sets Boolean `sudo: false`, or an actual failed attempt explains the blocker.
An omitted sudo key means enabled policy; it does not require asking the human
which account to use. Already-root sessions need no further elevation. Do not
start with su root, request a root password or try other accounts by default.
Reuse current-actor credential selection and confirm the returned identity.
Nested actor scopes retain their actual current identity. Follow the full
[decision table and limits](../../../docs/console-agent.md#choose-the-actor-for-an-authorized-root-switch).

## Start quickly, then keep the same shell

- Use the [memory-only owner controller](../../../docs/agent-owner.md): start
  `python -B -u -m opsfeast.web --agent-control` in a persistent tool session,
  send worker.start, then worker.send with the normal worker controls. No token
  files, credential arguments or temporary bridge are needed. The owner capability
  covers the website; every host operation still requires its actual human scope.
  Start as the configured login account and use authorized runtime sudo/su only
  when needed. Keep the controller handle across turns; do not restart a healthy
  service merely to create another worker.
- When the human has not selected a profile, omit `--profile` to use `.opsfeast.yaml` `default_profile`. Never substitute `main` from an example. Use `--profile NAME` only for an explicitly selected scope. Inspect the returned `profile` and `hosts_file` before connect; stop on a mismatch. Invalid/missing configuration is an error, not permission to choose another profile.
- Preserve worker stdin across turns. For an execution tool that closes piped stdin
  immediately, choose its persistent interactive mode (for example `tty=true` in
  exec_command). Retain both its process handle and OpsFeast session ID.
- As soon as `created` returns, open its reader_url in the visible browser and
  preserve the tab. Verify that its visible heading/profile/host match the new session; posting a link alone does not show the river. Reuse a tab only when its exact session UUID matches this worker. For a new session, open a separate tab; never navigate the selected tab away from another session or from a historical view. Do this before connecting, not after login finishes. A login page with the exact river in `next` is a valid
  handoff: continue already-authorized work without waiting for a chat acknowledgement.
  Use [reader readiness events](../../../docs/browser-events.md) on controller stdout
  to observe arrival; they are not host authorization or automatic model wakeup. Do not
  spend time on screenshots, browser QA or extra discovery before showing it.
- Send `{"op":"connect","request_id":"connect-1"}` to that same worker.
  When authorized, follow with `{"op":"sudo","request_id":"root-1","username":"root","authorization":"Human authorized root inspection","timeout":15}`.
  Report the actual ready/identity result promptly. Do not routinely take or attach
  a login screenshot: the human is already watching the reader. Additional checks
  must resolve a concrete uncertainty, not delay an already established result.
- Execute each later instruction using run on the same worker, for example
  `{"op":"run","request_id":"inspect-1","command":"df -h","timeout":15}`.
  Preserve cwd, environment and privilege across turns. Do not reconnect or create
  a second shell for each command. Report failure honestly; do not automatically
  retry, change target/profile/account or repair configuration.

For observation-only requests, the human can watch the river without entering commands or joining an interactive shell. The agent owns execution and publishes actual commands, incremental output and status. Reuse an already visible reader for the same session or provide its URL; do not open an additional interaction page just to show progress. The record service can also carry reviewed program output independently of this shell worker; it does not execute that program itself.

## Make the actual operation visible

Commands are saved with prompt/input in the very first block write before Console submission. The reader receives commit-triggered SSE updates. Commands and stdout/stderr must go to the river automatically as they occur,
including partial output without a newline. Keep output in the same logical block
as it streams, not a new card per transport chunk. Long content has a bounded
preview, small arrow controls and on-demand full/paged reading. A PTY can merge
stdout/stderr. Current public Console integration does not expose raw SSH banners
or remote shell PS1; do not fabricate either or call the river a full terminal
emulator. Identify source reports and missing evidence accurately.

Keep technical metadata (identity JSON, byte counts, revisions, timestamps) out of
ordinary river content; keep it available in metadata/detail views. Use distinct
backgrounds for input/commands, output and agent commentary/analysis/status,
with compact spacing. Meaningful analysis can be published through console_client
block on the same session; use kind=analysis and finish the block when complete.

The worker renders shell commands as `$(...)` with Python string-literal escaping; bare shell text after the Python Console prompt is invalid. Its execution adapter uses public `Console.start_command` on the raw command for streaming, while the river shows the copyable Console-input expression. The worker records the actual current prompt and input on one line in one command block, e.g. `host [root]> $('df -h')`, without a standalone prompt card. Active command/analysis/status blocks display a processing indicator until finished. Publish meaningful analysis as analysis blocks and finish them; use the separate activity signal below for silent thought rather than creating an empty unfinished block. Both displays reflect source reports, not continuous worker/model liveness.

### Show the handoff from commands to thought and speech

Successful connect/run/sudo automatically starts the worker's 120-second thinking
lease. Keep this **Agent 思考中…** signal during real analysis between commands;
the next command clears it automatically. Before **every** commentary or final
reply in chat, or when waiting for human input, send
`{"op":"activity","request_id":"before-chat-1","state":"idle"}` with a fresh
request ID to the same worker. Do this before writing the reply, not after it.
If analysis continues afterward, send a new activity request with
`state: "thinking"`. Renew only while genuinely continuing work; an ended turn
does not keep thinking. Do not use thinking as a substitute for execution progress.

If the SSH worker has closed but analysis of recorded evidence continues, use
`console_client activity --session SID` with `{event_id,state,lease_seconds}`;
thinking uses 1–300 seconds, idle uses 0. This only reports activity and never
reconnects. See [the canonical contract](../../../docs/console-records.md#agent-thinking-and-chat-handoff).
The browser cannot observe another application's chat, so agent-side idle reports
are required. Expiry bounds a missing cleanup report and stops stale animation
without adding remote checks. Keep authorization and thinking separate.

## Decisions, stopping and replies

Follow the human's agreed approval boundaries: every command, milestones, or
confirmation before changes. Explicit instructions already provide authorization
within their scope; do not add redundant approval clicks. Pause before unapproved
mutations, destructive actions or unexpected scope changes and explain the exact
target/effect. A finding or analysis is not permission to repair or delete.

For a reader-page question, publish a structured form and use the existing
console_client wait/responses interface. Immediately acknowledge an authenticated
reply in chat once received, then check the form/revision/scope before acting.
Do not delay acknowledgement for another screenshot or redundant response check.
A waiting client can receive replies; an ended model turn is not automatically
awakened. Do not promise an unsupported wakeup or browser stop control.

A normally terminated nonzero run with no Console error keeps the shell and returns `state: "failed"` plus `session_state: "ready"`. Report the failure and wait for the human's next instruction; do not retry or disconnect merely because the exit code is nonzero. Deadlines, unknown recovery/termination, sudo or transport failures still close the scope. Preserve the returned cleanup evidence.

On “disconnect,” send close to the existing worker, wait for its closed result,
and promptly report cleanup. Do not run unrelated inspection first. Keep the
history and analyses. Cleanup confirmed is not proof that every remote descendant
terminated; distinguish a stop request, command result and cleanup evidence.

## Prevent avoidable Console closures

The current worker closes its scope after command deadlines and unexpected
exceptions, including some errors before remote submission. A closed worker alone
does not establish an SSH/network failure. Read its `error_type`, command/output
blocks and cleanup result before explaining the cause; preserve uncertainty when
the safe error type is insufficient. Check the matching public SSHScript source
or bundled contract when necessary; do not guess from an exception class alone.

- **Enter privileges when authorized and needed.** Use managed sudo/su on the
  existing worker, with the grant description and exact target. Use leave to
  return one identity layer; do not reconnect merely to change accounts. Confirm
  the effective identity before protected commands. Raw su/sudo command heads
  are rejected by foreground job validation; never wrap or disguise them.
- **Budget each costly inspection separately.** The chat worker accepts integer
  timeouts of 1–300 seconds; the separate exact-plan executor has a 1–60 second
  contract. These are distinct from the execution tool's yield/poll wait. A
  shorter tool wait does not change the remote command deadline. Large recursive
  scans can exceed 60 seconds even when their output is small. Discover mounts,
  container mappings and log sizes first, then inspect the relevant paths with
  explicit budgets. Avoid combining several expensive scans into one deadline.
  Label an unfinished scan partial; output received before timeout is not a total.
- **Reconcile before another action.** A deadline or local validation exception
  may close a healthy SSH scope. Report command failure, scope closure and cleanup
  separately. Do not replay an uncertain command or reconnect automatically;
  reuse applicable explicit authorization and ask only when a new connection or
  action lacks it. If authorized to continue, correct the identified cause before
  opening the next visible reader and connecting. Increasing a polling wait alone
  does not fix an unsuitable command or remote deadline.

## Long operations and observation cadence

Separate the command client, SSH shell and service doing the work. For a service
such as Docker, a client timeout may leave a daemon-owned operation running.
Inspect service state and actual effects before considering another mutation;
neither a timeout nor a container's transitional `Dead` state alone proves that
deletion failed or completed. Do not resubmit deletion just because the client
stopped waiting. Do not generalize daemon independence to ordinary shell jobs.

Honor the human's monitoring interval; once progress is established, one-minute
checks can be sufficient. Simple bounded shell loops are appropriate for `df`
and container-state checks. Keep remote checks separate from reading already
recorded river output. When the human asks to stop monitoring, stop it and close
the Console if requested. Explain whether the operation has been verified to
continue independently, and report the last observation and final-state gaps.
Do not promise completion, later checks or notifications that were not arranged.

## Default to action and a brief acknowledgement

After an ordinary requested action, briefly acknowledge completion or failure.
The human can see the operation/output in the river: do not proactively analyze,
summarize, tabulate, repeat or interpret that output in chat, and do not fetch
saved output solely to prepare an unsolicited summary. Analyze/organize output
only when the human explicitly asks (for example, “check today's requests for
anomalies”). This reduces latency and duplicate information. Preserve the actual
completion/error evidence needed to avoid a false success claim; an exception or
missing authorization still requires a concise report and the appropriate pause.

For an analysis goal requiring multiple commands (for example, “look for signs of
intrusion”), show each command and its actual output in the river, but do not
provide a separate interpretation after every command. Collect the relevant
evidence, then give one consolidated analysis with findings, uncertainty and
coverage limits. Interpret intent naturally: “show df” is output-only; “check
whether today's requests are abnormal” requests analysis without requiring the
literal word “analyze.” Pause mid-task only when an error, authorization boundary
or consequential choice needs the human's decision; do not silently expand into
remediation. These inspection examples do not themselves grant host access.

## Use Python for substantive analysis

Simple navigation/listing such as cd, pwd, ls or df naturally uses shell commands.
Run ordinary shell tools directly through `run`, including `du`, `docker`,
`curl`, and straightforward shell loops. A preference for Python analysis does
not call for `python3 -c` plus `subprocess` merely to execute those tools, chain
commands, add deadlines or poll their status. Use the worker's command budget
and suitable shell control flow. Use Python when it contributes actual parsing,
aggregation or other substantive logic, not as an extra execution wrapper.
Prefer Python for structured log parsing, date/time selection, aggregation,
correlation and anomaly interpretation instead of increasingly complex awk/sed
pipelines. Reuse reviewed analysis programs/modules when suitable, verify the
remote interpreter before relying on it, and preserve scope/timezone/coverage,
parse failures, proxy/source-IP ambiguity and unknown states. Python preference
is not permission to install packages, upload code or broaden data access.

SSHScript Console Python executes in the managing Python process; SSH/sudo changes the command channel, not where Python imports or sockets run. Use controller-side Python for analysis of retrieved data. Code that must inspect the remote filesystem/network/runtime needs a remote command/interpreter (or an appropriate remote API); never assume a Python socket opened in the Console is on the SSH host.

The worker's run currently accepts single-line shell commands, not arbitrary
Python cells. Use a reviewed Python entrypoint or bounded `python3 -c` invocation
within that interface; larger analysis requires a supported, authorized delivery
method. The shipped worker disables PTY canonical input/echo before created and restores terminal settings on exit, so the OS line limit does not truncate its JSON controls. Keep the worker's 16 KiB command and control-message limits; do not automatically replay a command after uncertain delivery. Earlier already-running workers retain their startup terminal mode; keep their controls short until a newly authorized worker replaces them. A reusable product gap should be fixed
in OpsFeast rather than requiring a new connection/record bridge each time.

## Offer host notes at completion

After each concluded interaction (including agent-led Console inspection), ask whether the human wants reusable experience extracted into [host notes](../../../docs/host-notes.md). Agreement authorizes extraction only: present the draft for final confirmation before calling the notes writer. Use source `console` for distilled Console evidence. When organizing existing notes on request, use source `agent`, display conflicts and exact retained/removed UUIDs, and obtain confirmation for the final mutation. Read relevant existing notes before starting host diagnosis.

*Last modified: 2026-11-06 15:10:22*
