---
name: opsfeast-console-records
description: Publish durable Console blocks, stream bounded previews and read authenticated human form responses through the local OpsFeast service.
---

# Publish Console blocks and await human responses

For human-directed shell work, follow the [interactive chat-shell procedure](../opsfeast-interactive/references/chat-shell.md), including immediate reader display, no routine login screenshots and the agreed prompt/input presentation.

Read the complete [0.2.0 contract](../../docs/console-records.md) before use.
For chat-owned SSH Console execution, first use the shipped [worker 0.1.0](../../docs/console-agent.md), not an ad hoc bridge. Announce that this skill is being used. Start `python -B -u -m opsfeast.console_agent --token-file FILE --profile NAME --host HOST`, immediately show its returned reader_url, then send JSON-lines controls to that process. The worker owns execution; this service stores its records. A received human response should be acknowledged in chat immediately, before optional UI checks.

This is a checkout-level record/response service, not a command executor, recipe
retention/logger, SSH adapter, stop controller or model wakeup mechanism.

1. Establish target, scope and source execution authorization separately. Writer
   credentials and a work/session ID do not authorize operations. The separate
   [interactive executor](../opsfeast-interactive/SKILL.md) keeps its own rules.
2. Use `python -B -m opsfeast.console_client --token-file FILE create` with JSON stdin
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
   the page; do not use their cookie/account to self-approve. Writer/reader tokens
   cannot submit authenticated human replies. Ordinary authorized work should not
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

*Last modified: 2026-11-02 17:47:54*
