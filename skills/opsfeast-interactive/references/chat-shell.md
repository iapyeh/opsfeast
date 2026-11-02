# Chat-driven interactive SSHScript shell

Use this procedure when the human directs operations incrementally in chat while
watching a Web river. The user's own agent owns the conversation; OpsFeast is the
supporting execution/record tool. Do not require the human to predict all details
in advance. Read the [worker contract](../../../docs/console-agent.md) for exact
fields, states, credentials, supported operations and limitations.

## Start quickly, then keep the same shell

- Use the shipped `python -B -u -m opsfeast.console_agent --token-file FILE
  --profile NAME --host HOST`. Add `--sudo-root` only when root entry is within
  the user's authorized scope. No temporary bridge program is needed.
- Preserve worker stdin across turns. For an execution tool that closes piped stdin
  immediately, choose its persistent interactive mode (for example `tty=true` in
  exec_command). Retain both its process handle and OpsFeast session ID.
- As soon as `created` returns, open its reader_url in the visible browser and
  preserve the tab. Do this before connecting, not after login finishes. Do not
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

## Make the actual operation visible

Commands and stdout/stderr must go to the river automatically as they occur,
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

**Agreed presentation requirement, still pending in the current worker:** prompt
and input belong on one line in one input block, e.g. `host [root]> df -h`.
Do not treat a standalone prompt card as the desired interaction. The current
worker still emits separate prompt blocks; these instructions record the accepted
design, not a claim that prompt grouping has already been implemented.

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

The worker's run currently accepts single-line shell commands, not arbitrary
Python cells. Use a reviewed Python entrypoint or bounded `python3 -c` invocation
within that interface; larger analysis requires a supported, authorized delivery
method. A tool's PTY canonical line limit may be lower than the worker's 16 KiB
command limit. Do not paste a large JSON/program into that PTY or automatically
replay a command after uncertain delivery. A reusable product gap should be fixed
in OpsFeast rather than requiring a new connection/record bridge each time.

*Last modified: 2026-11-02 17:53:57*
