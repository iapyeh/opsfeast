# Chat-driven interactive SSHScript shell

Use this procedure when the human directs operations incrementally in chat while
watching a Web river. The user's own agent owns the conversation; OpsFeast is the
supporting execution/record tool. Do not require the human to predict all details
in advance. Read the [worker contract](../../../docs/console-agent.md) for exact
fields, states, credentials, supported operations and limitations.

## Start quickly, then keep the same shell

- Use the shipped `python -B -u -m opsfeast.console_agent --token-file FILE
  --host HOST`. Add `--sudo-root` only when root entry is within
  the user's authorized scope. No temporary bridge program is needed.
- When the human has not selected a profile, omit `--profile` to use `.opsfeast.yaml` `default_profile`. Never substitute `main` from an example. Use `--profile NAME` only for an explicitly selected scope. Inspect the returned `profile` and `hosts_file` before connect; stop on a mismatch. Invalid/missing configuration is an error, not permission to choose another profile.
- Preserve worker stdin across turns. For an execution tool that closes piped stdin
  immediately, choose its persistent interactive mode (for example `tty=true` in
  exec_command). Retain both its process handle and OpsFeast session ID.
- As soon as `created` returns, open its reader_url in the visible browser and
  preserve the tab. Verify that its visible heading/profile/host match the new session; posting a link alone does not show the river. Reuse the existing visible river tab when appropriate. Do this before connecting, not after login finishes. Do not
  spend time on screenshots, browser QA or extra discovery before showing it.
- Send `{"op":"connect","request_id":"connect-1"}` to that same worker.
  When authorized, follow with `{"op":"sudo","request_id":"root-1","timeout":15}`.
  Report the actual ready/identity result promptly. Do not routinely take or attach
  a login screenshot: the human is already watching the reader. Additional checks
  must resolve a concrete uncertainty, not delay an already established result.
- Execute each later instruction using run on the same worker, for example
  `{"op":"run","request_id":"inspect-1","command":"df -h","timeout":15}`.
  Preserve cwd, environment and privilege across turns. Do not reconnect or create
  a second shell for each command. Report failure honestly; do not automatically
  retry, change target/profile/account or repair configuration.

For observation-only requests, the human can watch the river without entering commands or joining an interactive shell. The agent owns execution and publishes actual commands, incremental output and status. Reuse an already visible reader or provide its URL; do not open an additional interaction page just to show progress. The record service can also carry reviewed program output independently of this shell worker; it does not execute that program itself.

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

The worker renders shell commands as `$(...)` with Python string-literal escaping; bare shell text after the Python Console prompt is invalid. Its execution adapter uses public `Console.start_command` on the raw command for streaming, while the river shows the copyable Console-input expression. The worker records the actual current prompt and input on one line in one command block, e.g. `host [root]> $('df -h')`, without a standalone prompt card. Active command/analysis/status blocks display a processing indicator until finished. For substantive analysis between commands, publish a streaming analysis/status block on the same session, then finish it when done; do not leave a false busy indication after work ends. This display reflects source reports, not continuous worker/model liveness.

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

After each concluded interaction (including noninteractive Console inspection), ask whether the human wants reusable experience extracted into [host notes](../../../docs/host-notes.md). Agreement authorizes extraction only: present the draft for final confirmation before calling the notes writer. Use source `console` for distilled Console evidence. When organizing existing notes on request, use source `agent`, display conflicts and exact retained/removed UUIDs, and obtain confirmation for the final mutation. Read relevant existing notes before starting host diagnosis.

*Last modified: 2026-11-03 20:01:37*
