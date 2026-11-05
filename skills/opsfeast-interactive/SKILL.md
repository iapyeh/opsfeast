---
name: opsfeast-interactive
description: Operate a persistent SSHScript shell with a human through chat and a visible Web river; use the shipped Console worker for incremental instructions or the separate exact-plan executor when that approval mode is selected.
---

For login-to-river handoff, use [browser readiness 0.1.0](../../docs/browser-events.md): open the exact river so login retains its scoped next URL, then continue already-authorized work without waiting for a "logged in" reply. The reader reports `reader.opened` and the owner controller pushes `browser_event` on its existing stdout; this is readiness evidence, never approval or automatic model wakeup. Separate installations use namespaced authentication/editing cookies.

For per-installation Web ports and agent ownership, follow [Web endpoint 0.1.0](../../docs/web-server.md): `.opsfeast.yaml` stores `web.port`; first launch allocates it, `--port N` persists an explicit choice, and the returned URL is authoritative. Reuse `opsfeast.web_settings.read_port/configure_port/bind_server` for checkout-level operations; occupied ports never authorize stopping an unidentified process.

For an investigation involving several hosts in one visible river, follow [shared task river 0.1.0](../../docs/shared-console.md). Predeclare exact profile/host/icon participants, attach each independent worker with controller `session` or worker `--session UUID`, and reuse the one reader for that session. Host buttons independently toggle their own blocks open/closed, and 全部 opens all; dark always means all applicable blocks are open, while light means some or all are closed; individual block toggles preserve chronological slots. Time leads every source row; a far-right ↓/↑ toggle opens/closes each block; only open blocks show ↗ immediately to its left. Waiting live forms and private-input controls remain open. Keep command routing, accounts, authorization, activity and cleanup scoped to each worker; serialize private input requests across the river.


For website access and administrator/password management, prefer the shipped
[memory-only agent owner controller](../../docs/agent-owner.md): highest Web API
capability, distinct from human login, no token files, no borrowed browser cookies.
Use worker.start/worker.send for Console work and request for API operations;
admin.password accepts a human-provided password or explicitly requested generation.
Follow the human's task/consent; capability possession never supplies authorization.

For service continuity during development and Git work, follow
[controller lifetime](../../docs/agent-owner.md#launch-and-lifetime): keep the
user-facing Web server running. Restore any necessarily paused task-owned server
with its original installation/port and verify HTTP availability before handoff,
unless the human explicitly requests otherwise. Reconcile workers before restart;
never automatically replay host commands.

# Use the interactive Console service

Every Console session is interactive. Agent-led operation means the human can
remain silent while the agent decides within the agreed scope; it is not a
different record mode or permission grant.


## Enter a text program and request its password safely

Read [worker 0.3.0](../../docs/console-agent.md#entered-programs-and-private-input-worker-030)
and [ephemeral secret delivery](../../docs/console-secrets.md) before this workflow.
Use enter → observe waiting_secret → secret → observe waiting_input → input → leave
on the same worker. Exact field names, literal prompts, timeout/exit behavior and
an example MySQL command are in the canonical worker guide. MySQL root does not
authorize OS root. Ordinary SQL/input is recorded; passwords never belong in chat,
input operations, command arguments or ordinary durable forms. The secret operation
opens an authenticated, short-lived password field; the worker consumes its value
without returning it to the agent. Keep the worker alive and report expiry,
cancellation, uncertain delivery and authentication failures without retrying.
Keep the reader open while the human types: polling and new output preserve
private-input focus and unsent text; refreshing the page clears unsent input.
Historical readers provide no secret field. Old workers must be replaced and the
Web service restarted after this update; preserve existing records and reconcile
active work before doing so. No automatic reconnect or program replay exists.


## Switch accounts when the task requires it

Use [runtime account switching](../../docs/console-agent.md#runtime-account-switching-worker-030).
Start normally without a privilege flag. After explicit human authorization, send
sudo/su with exact username and a truthful nonsecret authorization description on
the same worker. No new river or SSH connection is needed. Su uses target-account
credentials (or the private human input field); sudo uses the current actor's
policy/credentials. Leave an application before switching and use leave to return
one identity layer. Check the actual returned identity and cleanup; never retry
credentials automatically. Local mode rejects managed switches. Old startup
--sudo-root and Core sudo_root are removed, without a compatibility path.
Supply a short purpose for each command/group so the river explains why it runs.

## Choose the interaction mode

Switching to root requires the human's **explicit permission** for the relevant
host and task. A request to connect, inspect or diagnose alone does not grant
root entry; configured sudo/su access is not permission.
Ask once when the grant is missing, before entering root or another account. Reuse an
existing explicit grant within its scope without asking again. Root permission
does not expand an inspection-only task into changes, restarts or termination.

For “connect to a host; I want to interact,” use the shipped chat-owned worker,
not the exact-plan executor below. For this worker, omit `--profile` unless the human selects a specific profile: the checkout's `.opsfeast.yaml` `default_profile` is authoritative. Never copy `main` from an example; check returned `profile` and `hosts_file` before connecting. Read [the chat-shell procedure](references/chat-shell.md)
and [worker protocol 0.3.0](../../docs/console-agent.md). Default to execution plus a brief acknowledgement; do not proactively analyze or repeat visible output. Analyze only when the human explicitly requests it. The human can supply details
one step at a time; do not demand a complete plan or repeat approval for already
explicitly authorized connection, sudo or read-only commands.

The worker combines prompt/input in one command block and the reader shows streaming work as processing. A confirmed ordinary nonzero run retains the shell and returns `session_state: "ready"`; report failure and wait for the next instruction without retrying. Unsafe/unknown recovery still closes. See the chat-shell procedure for processing reports during analysis.

After a successful result the worker reports **Agent 思考中…** automatically.
The next input clears it; **before every chat commentary/final reply or wait for
human input**, report `{"op":"activity","request_id":"chat-1","state":"idle"}`
using a fresh request ID. Explicitly report thinking again if analysis continues.
Read [the activity handoff](../../docs/console-agent.md#processing-display): the
reader cannot detect external chat output and the signal expires without renewal.

Before privileged or potentially slow work, read [closure prevention and long
operations](references/chat-shell.md#prevent-avoidable-console-closures): enter
root through the worker's `sudo` operation, budget costly commands separately,
distinguish client/scope failure from remote service progress, and honor the
human's monitoring cadence. Run shell tools directly; Python is for substantive
analysis, not a wrapper around ordinary shell commands.

For an operator-selected exact plan with Web approval/checkpoints, follow the
separate procedure below. Never switch modes to bypass an existing approval gate.

## Exact-plan executor

Read [protocol 0.1.0](../../docs/interactive-console.md) and the installed release's
[SSHScript skill](../sshscript/SKILL.md), agent guide and embedded Console contract.
This is a checkout-level service, not a recipe retention producer or an agent-task
launcher. The CLI/HTTP interfaces are shared across agent products.

1. Establish the human's goal, exact profile/namespace/host scope and permitted
   effects. Obtain the work UUID created by the operator. Read the server's enabled
   targets and current snapshot. Work IDs do not authorize execution. No connection
   occurs merely from reading. Never switch profile or host to bypass a failure.
2. Use `python -B -m opsfeast.interactive_client --token-file FILE list|show|events`.
   The agent token is distinct from the operator token. Do not read/use the operator
   credential to self-approve, expose either token, or paste credentials in prompts.
3. Propose a bounded exact plan using `plan --work UUID` with JSON on stdin:
   title, approval_mode (`each` or `plan`), and steps containing command, purpose,
   checkpoint Boolean and timeout (1–60 seconds). State targets, privileges,
   side effects and expected evidence. No arbitrary Python or program stdin is
   supported. Each command must be one line without CR/LF, even inside shell
   quotes; encode a literal backslash-n as `\\n` in JSON for printf output.
   `command_must_be_single_line` rejects the whole plan before connection.
   Commands are not a sandbox: separate consequential actions into steps.
4. Wait for operator approval. Do not invoke another SSH tool or direct Session
   to bypass Web confirmation. Approved exact steps may continue to a checkpoint;
   new commands, privilege changes or exceptions require a revised reviewed plan.
   Never infer approval from feedback text, elapsed time or a browser closing.
5. Consume sequence-ordered events. Preserve unknown/failure/partial states and
   original output. Check snapshot seq; deduplicate repeats; recover gaps with a
   snapshot, never by rerunning commands. Only report actual returned identity.
6. Append analysis through `analysis --work UUID`, e.g. stdin JSON
   `{"content":{"kind":"table","columns":["Finding","Evidence"],"rows":[["Example","source step ID"]]}}`.
   Text uses `{"content":{"kind":"text","text":"..."}}`. Analysis is distinct from
   execution output; cite relevant step IDs and uncertainties. Tables/text are
   supported; charts, HTML and executable presentation code are not.
7. Treat stop_requested as a request, not a confirmed remote termination.
   Inspect the job result and cleanup separately. Never replay failed/unknown
   commands automatically or retry credentials. Report the typed failure and
   required decision. A restarted server preserves history but interrupts work;
   any new execution needs a fresh explicitly authorized work/plan.

Human feedback is an event, not shell input. Exact action retries must reuse the
same request_id and identical body; ambiguous work creation must be reconciled
through recent works rather than retried blindly. Host settings/credentials and
arbitrary program output may be sensitive: no passwords, private keys or secret
input in this first version. No su/sudo UI, raw stdin, general scheduling,
retention ingestion or automatic agent wakeup is delivered.

Examples and errors are defined by the canonical protocol; a fresh agent must
read it before operating. An external agent may need the user to provide the
reachable server/checkout and agent-token file path; never assume localhost refers
to the same machine across remote agent environments.

## Keep concurrent sessions and history distinct

Bind each worker process to its returned session UUID. Reuse only a live reader
for that exact session; open a new tab for a new worker and preserve the human's
other readers. Host history opens `/console/{sid}/history` in a separate read-only
tab, without SSE updates or form replies. A human opening another page does not
change the worker target or create a connection. Follow [the reader modes](../../docs/console-records.md#separate-live-interaction-from-historical-reading).

## Accumulate host experience after work

Saved sessions, including agent-led work, are discoverable from the host's
**Console 紀錄** tab. Reuse [the record-service history reader](../opsfeast-console-records/SKILL.md)
and its exact Profile/host matching; opening history never reconnects. Preserve
direct reader URLs and distinguish recorded block state from current liveness.

Follow [host notes](../../docs/host-notes.md). Read relevant host notes before diagnosis. After each concluded human-directed or agent-led Console task, proactively ask whether to extract reusable experience. Only after agreement, draft facts, uncertainties and evidence; save with source `console` only after final content confirmation. Reuse already granted confirmation. Use the shared notes CLI, read back the saved UUID and timestamp, and never interpret a note as remote execution permission. This is agent guidance, not an automated approval gate.

## Carry verified tool lessons into skills

After a demonstrated tool failure or an operator correction, distinguish reusable
execution guidance from private host facts. For the reusable lesson, identify the
trigger, verified cause, supported alternative, authorization boundary and evidence
limits. Check the current implementation and version-matched contract; do not turn
an unexplained failure or one successful workaround into a universal rule.

When skill maintenance is authorized, update the existing authoritative skill and
its relevant reference, making the lesson discoverable from this entrypoint.
Reuse authorization already given; otherwise propose the focused update without
silently changing shared skills. Check known loaded copies for conflicts before
editing, following [skill storage and conflict resolution](../../docs/agent-guidance.md#skill-storage-and-conflict-resolution).
Keep the upstream SSHScript snapshot intact and put OpsFeast worker guidance here.
Use synthetic examples; host names, private bindings, credentials, incident output
and host-specific conclusions belong outside public skills. Host notes retain
their separate confirmation workflow above.

Validate skill structure, links and consistency with the current worker contract;
report what was verified and what remains uncertain. Documenting a procedure does
not fix runtime behavior or prove real-host behavior. Do not rerun host operations
merely to validate a prose correction. Preserve unrelated work and report the
updated source; do not claim installed or cached copies were refreshed unless
that separate action was actually authorized and completed.

*Last modified: 2026-11-05 14:35:41*
