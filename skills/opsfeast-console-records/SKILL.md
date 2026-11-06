---
name: opsfeast-console-records
description: Publish durable Console blocks, stream bounded previews and read authenticated human form responses through the local OpsFeast service.
---

For login-to-river handoff, use [browser readiness 0.1.0](../../docs/browser-events.md): open the exact river so login retains its scoped next URL, then continue already-authorized work without waiting for a "logged in" reply. The reader reports `reader.opened` and the owner controller pushes `browser_event` on its existing stdout; this is readiness evidence, never approval or automatic model wakeup. Separate installations use namespaced authentication/editing cookies.

For several hosts in one task river, read [shared task river 0.1.0](../../docs/shared-console.md). Session targets declare exact profile/host/icon sources; every host block must supply its declared target_id, while joint analysis can remain unscoped. The reader independently toggles each host’s blocks or individual blocks open/closed in place: time leads each row, a far-right ↓/↑ toggle opens/closes blocks, and open blocks show ↗ immediately to its left for a separate window; 全部 opens all, while waiting live forms remain open. Per-host history discovers the same shared UUID; focus never authorizes or routes execution. Use per-target activity leases and serialize secret requests.


# Publish Console blocks and await human responses

For already-authorized root inspection, use [the login-account sudo decision rule](../../docs/console-agent.md#choose-the-actor-for-an-authorized-root-switch).
A missing sudo flag is enabled policy, not missing human preference. Do not
substitute su root or repeat an account-choice approval; use the exact current
actor's managed switch and verify its result. Preserve explicit user choices,
policy denials and concrete failure/cleanup evidence.


For multi-host tasks, [one canonical river appears in every declared host's history](../../docs/shared-console.md#one-canonical-river-discoverable-from-every-participant).
Declare all Profile/host participants in `targets` before attachment; never copy
transcripts or create filesystem links. The agent can choose a task display label
or main subject unless the human specifies one; that choice does not affect
history membership or grant execution rights. Existing single-host records do not
automatically acquire participants, and retroactive association is unsupported.


For human-directed shell work, follow the [interactive chat-shell procedure](../opsfeast-interactive/references/chat-shell.md), including immediate reader display, no routine login screenshots and the agreed prompt/input presentation.

Read the complete [0.2.0 contract](../../docs/console-records.md) before use.
For chat-owned SSH Console execution, first use the shipped [worker 0.3.0](../../docs/console-agent.md), not an ad hoc bridge. Announce that this skill is being used. Use the [memory-only owner controller](../../docs/agent-owner.md): launch `python -B -u -m opsfeast.web --agent-control`, keep its handle, send worker.start, immediately show the created worker event reader_url, then send worker.send controls. No capability files or browser cookies are used. The agent owner token authorizes all Web operations, including password reset, but actions still require the human's actual task and applicable consent. Omit the worker profile field to use `.opsfeast.yaml` default_profile; override only for an explicitly selected scope and inspect returned profile/hosts_file before connecting. Prompt/input share one command block using valid escaped `$(...)` Console syntax for shell commands, with initial text in its creation write before execution. HTTP commits wake SSE readers immediately; do not wait for completion to publish output. The reader shows processing for streaming command/analysis/status blocks; finish them when the reported work ends. This is not a heartbeat. The worker owns execution; this service stores its records. A received human response should be acknowledged in chat immediately, before optional UI checks.

This is a checkout-level record/response service, not a command executor, recipe
retention/logger, SSH adapter, stop controller or model wakeup mechanism.

For silent analysis after command completion, use the separate [agent activity
contract](../../docs/console-records.md#agent-thinking-and-chat-handoff). The worker
automatically reports thinking after successful results; new input clears it.
Before sending any chat commentary/final reply or waiting for the human, send
worker `activity` with `state: "idle"` and a fresh request ID. Resume thinking
explicitly only when continuing analysis. If no worker remains, use
`console_client activity --session SID` or `Records.activity(sid, body)` with
`{event_id,state,lease_seconds}`; idle requires 0, thinking accepts 1–300 seconds.
HTTP uses writer-authorized `POST /api/v1/console-sessions/{sid}/activity`.
This creates no output block, SSH connection or model wakeup. The current reader
handles activity-only SSE events without a `block`; do not assume every event is
a block update. Explicit reports and expiry are required because the service
cannot detect chat output or infer whether an agent is actually thinking.

For concurrent readers, preserve [the live/history distinction](../../docs/console-records.md#separate-live-interaction-from-historical-reading).
Use `/console/{sid}` for the worker's live interaction and
`/console/{sid}/history` for read-only evidence. Historical pages neither stream
nor submit forms; block links preserve that mode. Host-history links open separately.
Bind a worker to its exact session UUID; never replace another session's tab or
interpret a manually opened page as a new connection or operation authorization.

For saved history, start with [host history discovery](../../docs/console-records.md#discover-saved-console-history-by-host).
The host's Console 紀錄 tab lists human-directed and agent-led worker sessions
using their exact `PROFILE / HOST` target and opens the existing reader. It needs
administrator login, with no execution or reconnect. The discovery HTTP route is
`GET /api/v1/console-sessions?profile=lab&host_id=web-01&limit=25`; Console tokens
cannot enumerate it. Local agents can use the documented checkout-level
`Records.list_sessions('lab / web-01', limit=25, before=None)` against the resolved
installation record store, without borrowing administrator cookies or writing a
parallel SQL/index reader. Follow `next_cursor` for older records; counts and
unfinished blocks do not certify liveness or outcomes. Unscoped producers remain
accessible by reader URL; do not silently relabel or migrate their evidence.

Analysis titles remain stored metadata but are hidden in live/historical rivers,
which show the explanation directly without a separate-window arrow. Use clear
body text; long explanations retain inline expansion.

1. Establish target, scope and source execution authorization separately. Writer
   credentials and a work/session ID do not authorize operations. The separate
   [interactive executor](../opsfeast-interactive/SKILL.md) keeps its own rules.
2. For agent-owned launch, send the following record HTTP operations through the
   controller request control; see [owner control](../../docs/agent-owner.md).
   For explicit scoped integrations only, use `python -B -m opsfeast.console_client --token-file FILE create` with JSON stdin
   {session_id,title,host_id,work_id}. Open returned reader_url. Browser readers
   sign in normally and load automatically; do not ask them for another unlock.
3. Create a block through `block --session SID` with exact event_id, block_id, kind,
   title, text, form. Use fresh UUIDs for new units. For repeated output, call
   `append --session SID --block BID` with {event_id,offset,text}; UTF-8 byte offset
   must equal committed size. Do not create a card for each transport chunk.
4. Connection source calls, login status and actual SSHScript Console prompts are published by the worker. Identity JSON is metadata: it stays out of river content and has a readable toolbar summary. Remote banners and shell PS1 are not captured; never fabricate them. Commands/identity/authorization are source reports. Never fabricate execution,
   actual identity or human decisions. Omit passwords/private keys and secret input;
   automatic redaction is unavailable. Label synthetic demonstrations explicitly.
5. `show` gives previews and seq; `content --block BID --offset N --limit N` gives
   exact paged text and next_offset. Do not interpret a preview as full output.
   Preserve unknown/failure/incomplete states; never silently drop overflow data.
6. Finish each text block with {event_id,status} via finish. Status must reflect
   completed/failed/interrupted/cancelled. No remote process stops because a block
   is finished. Keep output/analysis/status separate and cite relevant block IDs.
7. When a human decision is needed, create kind=form with exact question, target,
   effect and schema from the contract (fields,choices,expires_at). No HTML/JS or
   arbitrary form actions are supported. Ask the human to review and respond in
   the page; do not use their cookie/account to self-approve. Scoped writer/reader tokens
   cannot submit authenticated human replies. The owner capability can submit an
   agent-attributed response, never proof of human consent. Ordinary authorized work should not
   acquire redundant approval requests solely because this service supports forms.
8. Run `wait --session SID --after N --timeout 30` or `responses`/`stream` to read
   durable replies. Validate form ID, request_revision, choice, actor and exact
   scope before proceeding under the human's authorization. An authorization text
   report is not the authenticated response. Timeout/feedback is not approval.
9. Persist the returned seq, reuse exact event IDs and bodies for uncertain write
   retries, and reconcile offset/stale conflicts from snapshots. Never retry a
   remote command as a transport-recovery mechanism. General SSE summaries are
   replayable; long-poll responses have their own returned continuation cursor.
10. Closing/reopening pages and server restarts preserve records but do not execute
    or resume work. A waiting HTTP client can receive a reply; a finished agent chat
    is not automatically awakened. State this limitation when handing off work.

0.2.0 replaces the old chunk API. Existing 0.1 SQLite is preserved but not served;
create a new session. Chart/media/custom renderer blocks, delete/archive/export and
full terminal emulation are not supplied. All access is installation-wide, not a
per-host permission system. See contract for limits, errors and test evidence.


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
Historical readers provide no secret field. Old workers must be replaced and the
Web service restarted after this update; preserve existing records and reconcile
active work before doing so. No automatic reconnect or program replay exists.

*Last modified: 2026-11-06 15:10:22*
