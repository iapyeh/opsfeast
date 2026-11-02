# Interactive Console protocol 0.1.0

For chat-driven incremental interaction, use the shipped [Console worker](console-agent.md). This page describes the separate exact-plan executor.

This is an isolated, opt-in Web service for one administrator and their chosen
agent. It uses SSHScript 7.0.1 `Console.start_command/poll/interrupt` over Core's
configured connection planner. It is not a workflow engine or a Python sandbox.
The first version supports persistent Bash shell jobs, not arbitrary Python,
entered applications, raw stdin, su/sudo UI or secret input. Compound shell code
is trusted input: approval is not proof that a command is read-only. Shell startup
and Console identity probes occur when connecting, before the first planned job.

## Enable and open

Install `requirements-web.txt` only in the approved environment, then run:

```sh
.venv/bin/python -B -m opsfeast.web --interactive-profile main --interactive-host example-host
```

No host is enabled by default. The flags only enable explicitly selected profile /
host pairs; they do not connect. Open `/interactive`. Browser users sign in as administrator and the page loads automatically, without
a separate unlock. The private `.opsfeast-interactive-operator-8740.token` under
the marked installation data root remains an operator HTTP/CLI capability. The launcher also creates a separate
`.opsfeast-interactive-agent-8740.token`. Neither token is printed; files are 0600,
per-launch and removed on normal shutdown. Site-edit tokens grant no Console
access. Never put these values in a prompt, URL, command argument or public log.
Same-OS-account agents can read owner files; this is not OS-user isolation.
Loopback binding, same-origin checks, no CORS and authenticated APIs are retained.

Create a work with goal, profile and host. This creates a UUID and persisted event,
not a connection. Propose a finite plan, then an operator approves its exact plan
ID. The server connects and executes the exact listed commands. Agent credentials
can read, propose plans, append feedback/analysis and request stop, but cannot
create work, approve/continue/reject or close the operator's Console. `operator`
means the administrator/capability holder, not proof that a human clicked a button.
Automation may use that capability only under the human's actual authorization.

Only one live Console is supported per server process, including idle connections.
A nonblocking owner lock prevents two enabled servers from executing against the
same interactive store. This prototype uses the project's POSIX file-lock model.
SSHScript Console requires serialized same-thread ownership; the dedicated worker
constructs, polls, interrupts and closes it. No Python input evaluation is exposed.
Idle connections close after 15 minutes. Each job has a 1–60 second deadline;
there are at most 20 commands per plan. A work retains at most 2 MiB output; excess
is explicitly recorded and triggers an interrupt attempt. This is not a scheduler.

## Plan and confirmation

```json
{
  "request_id": "unique-retry-key-001",
  "title": "Inspect the authorized target",
  "approval_mode": "plan",
  "steps": [
    {"command": "hostname; id -un", "purpose": "Verify host and identity", "checkpoint": true, "timeout": 15}
  ]
}
```

`each` waits before each subsequent step. `plan` permits only the exact approved
list to continue; `checkpoint: true` pauses after that step. Failure or stop holds
further execution. At the final checkpoint the Web page hides approve/continue
and states that this phase is finished; a new plan is needed for additional commands. Each command must be a single line (no CR or LF), including
inside shell quotes. For `printf` use literal backslash-n; in JSON encode that as
`\\n`. Invalid multi-step plans are rejected atomically before approval or connection
with `command_must_be_single_line`; no command is rewritten automatically. Revised plans receive a new plan ID; stale approvals fail.
The work captures namespace and configured target/login metadata plus a digest.
Changed connection settings fail approval and initial connection; create a new
work to review the changed target. A failed step needs a new reviewed plan. There is no automatic retry, reconnection,
credential fallback or command replay. Feedback is durable commentary, never shell
input and never an implicit approval. Skill instructions cannot enlarge scope.

The worker records connection identity from Console environments, not a model's
claim. Commands may change the shell's effective identity; the entry identity is
not a continuous authorization/identity guarantee. Managed su/sudo switches through
this exact-plan adapter are rejected (it does not enable Core's explicit `sudo_root` option); shell code itself remains trusted and
can have arbitrary effects, so do not approve hidden privilege changes.

## Snapshot, events and deltas

The snapshot is `{protocol_version, seq, state}`. `state` contains work_id,
profile, host_id, goal, target metadata/fingerprint, creation time, status, plan, current, history, feedback,
analyses, identity, output_bytes, cleanup and last_error. Current includes step_id,
index, purpose, exact command, timeout, checkpoint, stdout/stderr and execution
state. Finished records additionally carry exitcode (nullable), completion time,
error type, stop request and Console Session reuse evidence.

Every event contains protocol_version, work_id, event_id, per-work integer seq,
server UTC received_at, authenticated actor, type, delta and payload. This version
has server receive time only, not an independently verified source timestamp.
Actors are operator, agent, executor or server. Deltas are ordered operations:

- `set`: replace a value at a nonempty string-array path.
- `append_text`: append incremental stdout/stderr to the current step.
- `append`: append a completed step, feedback or analysis to a list.

There is no delete or arbitrary agent-provided patch endpoint. The service builds
its own deltas from typed actions. Explicit output_truncated evidence is retained
when the work output cap is exceeded. Prototype-related keys are rejected. Replaying
all deltas from `{}` produces the snapshot. Each event and projected state update
commit together in SQLite. Step finalization atomically appends the composed
current state to history, clears current and sets the waiting/ready/failure state.
The final delta is never mistaken for the entire streamed output. Waiting state
and plan remain visible after streaming ends. No plan/command is executed by replay.

SQLite is `<installation-data>/interactive/interactive.sqlite3` (0600) in a private
directory. It is separate from recipe retention and notification/todo services.
Raw commands, outputs, feedback and analyses are private operational data. This
version does not redact arbitrary program output: never enter passwords, private
keys or secret-bearing commands. No arbitrary HTML/JavaScript is rendered. Analysis
supports text and bounded tables; chart components and entered-program protocols
are not yet provided. No deletion/export/archive UI is added for this store yet. The Web page shows
failure recovery instructions and per-step error types. Its agent handoff text does
not notify or wake an agent: tell an existing agent the work ID, or copy the handoff
into a chosen chat. A terminal failed/interrupted work needs a new work and approval;
a failed step in a still-live Console needs a revised plan.

## HTTP and agent CLI

All JSON APIs use `/api/v1/interactive` and require an administrator cookie or the
appropriate Bearer capability. Cross-origin requests are rejected. Body limit is
64 KiB for actions; invalid or conflicting actions fail without dispatch. Reads
and actions are restricted to the launcher's enabled targets.

| Method / suffix | Contract |
| --- | --- |
| GET root | Protocol version, caller role, enabled targets and recent works |
| POST root | `{profile, host_id, goal}` creates work; operator only |
| GET `/{work_id}` | Atomic snapshot |
| GET `/{work_id}/events?after=N` | Authenticated SSE deltas after cursor; ordered, paged batches and heartbeats |
| POST `/{work_id}/plan` | Finite plan above; no execution |
| POST `/{work_id}/approve` or `/continue` | `{request_id, plan_id}`; operator only |
| POST `/{work_id}/reject`, `/close` | `{request_id}`; operator only |
| POST `/{work_id}/stop` | `{request_id}`; requests interrupt of this work's foreground job |
| POST `/{work_id}/feedback` | `{request_id, text}`; commentary only |
| POST `/{work_id}/analysis` | `{request_id, content}` where content is text or a table |

Every action needs a per-work request_id. Exact retries return the prior accepted
response; reusing an ID for different action/body/role yields request_id_conflict.
Acceptance is persisted before executable dispatch; it is not execution success.
Creation is not idempotent: avoid automatically retrying a creation after an
ambiguous response; inspect recent works first. No write action is retried by CLI.

Use the shared JSON client, not new SSH calls or database edits:

```sh
.venv/bin/python -B -m opsfeast.interactive_client --token-file /private/data/.opsfeast-interactive-agent-8740.token list
.venv/bin/python -B -m opsfeast.interactive_client --token-file /private/data/.opsfeast-interactive-agent-8740.token show --work WORK_UUID
.venv/bin/python -B -m opsfeast.interactive_client --token-file /private/data/.opsfeast-interactive-agent-8740.token events --work WORK_UUID --after 0
```

For plan/feedback/analysis, pass the JSON object on stdin. `--request-id` allows an
exact explicit retry. `--url` accepts only a loopback HTTP origin. Events print
one JSON event per line until interrupted; interrupting the reader does not stop
a remote job. The client does not print tokens, install dependencies or connect
to SSH. See the [agent skill](../skills/opsfeast-interactive/SKILL.md).

## Recovery, stopping and evidence

Browser snapshot loading followed by events after its sequence prevents gaps.
Duplicate events are ignored; a gap triggers a fresh snapshot. Reload/close does
not authorize more commands or stop the session. Reopening the work URL and
signing in if needed rebuilds output, waiting state, feedback and tables. Tokens are
not saved in browser storage. Server restart marks unfinished work interrupted,
with unknown cleanup, and never recreates a worker or resubmits old commands.
Create a fresh work for an explicitly authorized continuation.

Stop acceptance, interrupt attempt, job completion and connection cleanup are
separate events. Interrupt targets only this Console's current foreground job.
A compound shell command may continue subsequent clauses after a signal; use
separate planned steps for consequential boundaries. Do not use detach/exec-style
commands unsupported by Console jobs. Channel close does not certify termination
of every remote descendant, nor undo effects. `cleanup: confirmed` means the
Console/Core scope closed successfully, not that all remote processes vanished.
On failure the error is categorized without raw exception text. Shutdown requests
close but does not promise the worker finishes within process shutdown deadlines.

## Validation

Public tests: `tests/test_interactive.py`, Web API tests and
`tests/test_interactive_state.mjs`. Local Console tests use the installed 7.0.1,
not SSH. Native-host validation must separately report profile/host, actual identity,
commands, milestones, streaming, stop and cleanup evidence. A local or synthetic
success does not prove native SSH or privilege behavior.

*Last modified: 2026-11-02 17:03:25*
