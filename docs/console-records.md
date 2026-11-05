For login-to-river handoff, use [browser readiness 0.1.0](browser-events.md): open the exact river so login retains its scoped next URL, then continue already-authorized work without waiting for a "logged in" reply. The reader reports `reader.opened` and the owner controller pushes `browser_event` on its existing stdout; this is readiness evidence, never approval or automatic model wakeup. Separate installations use namespaced authentication/editing cookies.

# Console blocks 0.2.0

For a multi-host investigation in one river, read [shared task river 0.1.0](shared-console.md): declared participants, per-block source IDs, exact host-history membership and independent host batch toggles and individual block toggles. Closed blocks keep one time/source/content row with a far-right ↓/↑ open/close toggle in both states; only open blocks show ↗ immediately to its left; waiting live forms remain open. Folding never changes execution or authorization.

For automatic SSHScript execution/output forwarding from an agent, use the shipped [Console worker](console-agent.md). It uses this service's existing handlers; the record API itself does not execute commands.


A durable notebook-like river of agent-reported command, output and analysis blocks,
plus administrator-authenticated form responses. This service never connects,
executes commands, switches identity, stops jobs or wakes a model. Its independent
exact-plan executor is documented in [interactive Console](interactive-console.md).
Recipe retention and notification/todo/general logging services remain separate.

All Console sessions are interactive. In agent-led work the human can remain
silent while the agent makes decisions within the agreed scope; this is an
interaction style, not a separate unrecorded Console mode.

## Availability, access and storage

Run `python -B -m opsfeast.web` in the approved environment with requirements-web.txt.
It binds to the [saved installation port](web-server.md); use the launcher URL. Browser pages require administrator login, load
immediately and need no reader token or extra unlock. Redirects preserve the reader
URL through login. Configuration retains its existing authorization requirements.

The [agent-controlled launcher](agent-owner.md) keeps its owner capability in
memory and exposes authenticated request/worker controls; no reader/writer token
files are generated. It can publish/read records and feedback, and perform all
website operations. Source authority never grants permission beyond the human's
instructions. Browser users log in separately. Agent-submitted form responses
record actor=agent and authority=agent_capability; human responses retain their
administrator identity and administrator_cookie authority. Neither is independently
verified proof of human consent. Scoped reader/writer tokens are still accepted by
explicit embedded integrations; a scoped writer cannot submit a human response.
Same-origin checks apply. Never collect passwords in durable form fields; use the
[ephemeral secret channel](console-secrets.md).

SQLite is `<installation-data>/console-records/console-blocks.sqlite3`, in a private
directory with a 0600 database. 0.2.0 is intentionally incompatible with the earlier
0.1.0 chunk API/database. Existing `console.sqlite3` is preserved untouched; old
session URLs are not served by 0.2.0. Create a new session using this contract.
No compatibility layer, migration or deletion is performed. Server restart retains
blocks/responses but does not resume or repeat any source execution. Reported source
status/identity remain historical claims, not continuous connection-health evidence.

## Discover saved Console history by host

The host detail's **Console 紀錄** tab at
`/hosts?profile=lab&host=web-01&view=console` lists real saved sessions and opens
their existing session through `/console/{session_id}/history` in a new tab. Human-directed and agent-led
worker runs are included equally. Opening, refreshing and paging records never
connects, resumes a worker, retries commands or refreshes remote observations.
The list is manually refreshed. History pages load saved evidence once; live readers retain their own SSE updates.
Times display to seconds in Asia/Taipei with `+08:00`.

An administrator can request:

```text
GET /api/v1/console-sessions?profile=lab&host_id=web-01&limit=25
GET /api/v1/console-sessions?profile=lab&host_id=web-01&limit=25&before=SESSION_UUID
```

Both scope parameters are required. The profile must be registered and the host
must currently exist in its validated configuration; no default/fuzzy matching or
fallback occurs. The existing worker records its target in session metadata as
the exact string `PROFILE / HOST`. The list matches that entire string, without
splitting, prefix matching or inferring a profile from a host name. Existing 0.2.0
worker records appear without rewriting or backfilling. Independent producers
can use that same target convention with the existing `create` interface. Records
with arbitrary/unscoped targets (including standalone `--local`'s `localhost`)
remain accessible by their reader URL but are not automatically attached to hosts.
Renaming profiles or removing host definitions does not rewrite/delete history;
existing direct readers remain available. Reusing an exact profile/host name can
display its prior history; this is a recorded label, not verified machine identity.

The response contains `protocol_version: "0.2.0"`, `profile`, `host_id`, `sessions`
and nullable `next_cursor`. Each session includes its original metadata,
`bytes`, `seq`, `reader_url`, `block_count`, `block_states` (counts by stored block
status), and `updated_at` (last event's server receive time, or creation time when
empty). It excludes block content, previews and form replies. Creation time
descending, then UUID descending, defines a stable order; `before` is the prior
page's `next_cursor`, scoped to the same recorded target. `limit` defaults to 25
and accepts 1–100; null cursor means no older page. Inserts or appends do not move
records across the creation-order cursor. Refresh starts again from the newest.

Streaming/waiting/failed/interrupted block counts describe stored evidence, not
current worker liveness, successful outcomes or confirmed remote termination.
Empty sessions and failure/partial records remain visible. Read failures are
shown separately from an empty list; a paging failure preserves already loaded
rows and its retry cursor. The UI never offers execution or reconnection here.

Discovery requires an administrator cookie and same-origin access; Console
reader/writer tokens and site-edit tokens cannot enumerate this host list.
Existing token access to a known session is unchanged. This is an installation-wide
administrator view with scope filtering, not a new per-host authorization system.
Missing parameters/invalid scope or page size return 422; unauthenticated access
401, wrong origin 403, unknown cursor 404, malformed/cross-target cursor 409, and
storage read failure 422 (`console_history_unavailable`).

The shared checkout-level Python reader is
`Records(installation_data / 'console-records').list_sessions('lab / web-01',
limit=25, before=None)` from `opsfeast.console_records`. Resolve the existing
installation data root through [storage](installation-storage.md), and use its
existing record service rather than querying SQLite or building another index.
This reader accepts the exact recorded target; unlike the HTTP adapter it does
not validate a profile/host registry or enforce Web authentication. There is no
new CLI listing command. Public storage, HTTP and browser-handler tests are in
`tests/test_console_records.py`, `tests/test_web_preview.py` and
`tests/test_host_console_history.mjs`; these synthetic tests do not establish a
remote host's state.

## Blocks, deltas and limits

Agent thinking is separate session activity metadata, not an unfinished output
block; see [agent thinking and chat handoff](#agent-thinking-and-chat-handoff).

A block is a human-readable unit. Deltas update that same block; they are not new
cards. Creation sets revision=1; append/finish/response increment revision. Content
is append-only UTF-8 bytes. `offset` is byte count (not Python character or JavaScript
UTF-16 length); JavaScript uses `new TextEncoder().encode(text).length`.

A snapshot contains session metadata, per-session seq and ordered block summaries,
never all block content or all deltas. Each summary includes id, position, kind,
title, status, revision, size in UTF-8 bytes, newline count, created_at, head/tail
preview (each at most 1024 bytes), form definition, response and optional expired flag.
A trailing partial line counts toward bytes, not newline count. Previews may omit
partial characters at boundaries; content range requests recover exact text.

Kinds: command, stdout, stderr, identity, analysis, authorization, error, status,
form. Commands/output/identity/analysis/authorization are writer reports, not proof
of execution or authenticated human decisions. Source-time support is not supplied
in 0.2.0; created_at and event received_at are server receive times.

The reader shows a processing indicator for streaming command/analysis/status blocks, both below the latest visible block and beside the active block. This reports unfinished source work, not a worker/model heartbeat. Finishing those blocks clears it; other streaming content (such as stdout alone) does not assert that an operation is active.

Text block states: streaming → completed / failed / interrupted / cancelled.
Form states: waiting → answered or cancelled; expiry is checked at submission.
Do not mark a truncated or interrupted source completed. Finish ends a block, not
an SSH connection. A new block may follow a finished block; there is no session-close
operation in this version. Add a final analysis/status block to describe completion.

Limits: 32 MiB per block, 64 MiB total text per session, 2,000 blocks and 100,000
mutation events. Each create/append text is at most 32 KiB UTF-8, and each HTTP body
at most 64 KiB (so heavily escaped JSON may need smaller appends). Title max 500 bytes.
Limits reject writes explicitly, never silently truncate existing data. Metadata is
bounded separately by typed form/title limits. HTTP mutations notify waiting SSE readers after commit, so ordinary delivery does not wait for the 250 ms cross-process recheck. SSE responses disable intermediary caching/buffering. Each mutation is a SQLite transaction;
event journal, metadata, content and response update commit atomically. Polling SSE
reads committed events, so delivery cannot precede durable acceptance.

## Routes and JSON bodies

| Method / path | Purpose |
| --- | --- |
| POST `/api/v1/console-sessions` | Idempotent metadata creation, no execution |
| GET `/api/v1/console-sessions/{sid}` | Snapshot of bounded summaries and seq |
| POST `.../{sid}/blocks` | Create one block |
| POST `.../{sid}/activity` | Report thinking/idle with a bounded lease; no execution |
| POST `.../{sid}/blocks/{bid}/append` | Append exact text at byte offset |
| POST `.../{sid}/blocks/{bid}/finish` | Finish/cancel block |
| GET `.../{sid}/blocks/{bid}/content?offset=0&limit=16384` | Read a bounded byte range |
| POST `.../{sid}/blocks/{bid}/responses` | Logged-in administrator replies once |
| GET `.../{sid}/responses?after=0&wait=25` | Durable responses, optional long poll |
| GET `.../{sid}/stream?after=N` | Ordered SSE summary updates and responses |
| GET `/console/{sid}` | River, automatically loads after login |
| GET `/console/{sid}/blocks/{bid}` | Dedicated paged content reader |

Create requires exactly session_id (canonical lowercase UUID), title, host_id
(nonempty max 200 bytes), work_id (UUID or null). Exact retries of the same ID and
metadata reuse the session; differing metadata fails session_conflict. Response
includes reader_url. Work ID links a record but grants no execution permission.

Create block requires exactly:

```json
{"event_id":"9c5c89c5-bc99-443e-b0b9-fc6099a31f90","block_id":"a3bc5d2d-2ea2-4b65-9d55-1ce452af4104","kind":"stdout","title":"Output","text":"first part\n","form":null}
```

Append body: `{event_id, offset, text}`. Creation may start with empty text; appends
may contain only whitespace (including individual CR/LF chunks), but must contain
at least one UTF-8 byte. Empty content and exact EOF range reads return empty text. Offset must equal current total byte size;
offset_conflict means reconcile with snapshot, not blind retry at a new offset.
Finish body: `{event_id, status}` with completed/failed/interrupted/cancelled.
A form can only be cancelled through finish; answering requires the human endpoint.
No automatic text rewriting, source execution or secret handling occurs.

All mutations use writer-chosen canonical UUID event_id for idempotency across the
session. Preserve ID and exact body after an ambiguous response. Exact retries
return the saved result; changed action/body/actor for that ID fail event_conflict.
A block_id collision with a new event_id fails block_exists. Do not generate new
IDs to retry uncertain writes. Reconcile first, never replay remote commands.

Content limit is 256–32768 bytes; response includes text, offset, next_offset,
total_bytes, revision and status. Offset must be a valid UTF-8 boundary. The server
trims an incomplete character from the end of a page and returns the actual
next_offset. Offset zero and EOF are valid; past EOF or mid-character fails.
Content is append-only, so the byte prefix stays stable during subsequent writes.

## Separate live interaction from historical reading

Each session has its own immutable UUID in every reader and API URL. There is no
browser-global current session. New workers allocate fresh UUIDs even when their
host and title match. The database's session primary key and canonical UUID
validation make two distinct stored sessions sharing one reader path impossible.
A repeated create with identical UUID/metadata addresses the same existing session
(idempotent recovery); changing that UUID's task/target fails `session_conflict`.
Two browser tabs may observe one session, but this does not create a second session.
This isolates river records; it does not lock host operations or coordinate writes
to the same remote resource. The breadcrumb and browser title identify the
recorded target, task title and short session ID; the complete ID remains visible
under the heading. These are recorded identities, not live connection evidence.

- `/console/{sid}` is the live reader. Its SSE subscription and form replies use
  only that session. Opening it does not connect, create a worker, reconnect,
  select another operation or automatically acquire root.
- `/console/{sid}/history` is a read-only historical view. It makes no SSE
  subscription, hides live processing/thinking indicators and offers no form
  submission. Refreshing loads the latest saved snapshot; content expansion reads
  only the byte prefix recorded in that snapshot. This is not an archived copy or
  an assertion that the source worker has ended.
- Block pages retain the mode: `/console/{sid}/blocks/{bid}` or
  `/console/{sid}/history/blocks/{bid}`. Links preserve the session and mode.
- History-list links open a new tab with `noopener`, preserving any existing live
  or historical tab. The live reader also has a separate **檢視紀錄** link.
  **另開視窗** duplicates the same session and mode, not a new SSH shell.

Optional `profile` and `host_id` query parameters provide return navigation to
that host's Console records only when their exact `PROFILE / HOST` string matches
the recorded target. They never select the API session or grant access. Missing
or mismatched context leaves the recorded target as text with a general host
navigation link; it does not guess a Profile/host by splitting stored labels.
Deleted host configuration does not invalidate direct session readers. Login
redirects preserve the mode and navigation query.

Agents must bind a worker handle to its session UUID, independently of whichever
browser tab the human selects. Reuse only a live tab for that exact session;
create a new tab for a new worker. A human can open another reader midway without
redirecting the worker. Multiple live readers of one session observe the same
operation and existing revision checks still govern competing form replies.
A browser command-entry terminal or human-created shell is not supplied by this
record reader; the shipped worker remains the incremental execution owner.

## Agent thinking and chat handoff

Below the latest visible block, the river distinguishes streaming work (the existing spinner) from
**Agent 思考中…** (pulsing dots). The worker automatically reports thinking after
a successful connect/run/sudo result. The next command's initial block clears
thinking in the same transaction, before execution. A new analysis/status/error,
authorization or form block also clears it as the agent starts communicating.
This does not publish reasoning content or infer model state from silence.

`POST /api/v1/console-sessions/{sid}/activity` accepts exactly:

```json
{"event_id":"42177c15-7036-457a-93cb-8ea78627815d","state":"thinking","lease_seconds":120}
```

`state` is `thinking` or `idle`. Thinking requires an integer lease of 1–300
seconds; idle requires 0. The worker's automatic lease is 120 seconds. Writer
credentials/administrator login and same-origin checks are required; reader
tokens cannot report activity. Validation fails with 409 `invalid_activity` or
the existing field/id errors; unknown sessions return 404. Request idempotency
and conflicts follow the existing event-ID contract. This operation runs no
commands and grants no new execution authority.

The shared Python writer is `Records.activity(sid, body)`. The response is
`{accepted, seq, activity}`, with `activity: {state, updated_at, expires_at}`;
idle has null expiry. The metadata is stored in `session.activity`, independent
of blocks. Previously recorded sessions need no rewrite and have no thinking
signal until one is reported. Additive `activity.updated` SSE events contain
`activity` and no `block`; block events also carry current activity. Consumers
must handle both shapes and preserve the sequence/gap recovery rules. Reload
the current reader assets when updating producers; earlier readers that assume
every event has a block cannot consume the new event type.

The browser checks expiry locally without polling the service or host. Expired
thinking stops animating and displays **Agent 狀態未更新**; a valid active command
still takes the existing processing display. Reload/recovery retains only the
unexpired report. No heartbeat, idle-agent wakeup or actual model/chat connection
is provided. A producer must renew explicitly while genuinely continuing work.

Before sending commentary or a final reply in the chat, the agent must report
idle; the Web service cannot observe another application's chat output. The live
worker accepts `{"op":"activity","request_id":"chat-1","state":"idle"}`
and can explicitly renew thinking with a fresh request ID. Independently, use
`console_client activity --session SID` with the JSON body above (new event ID)
and `state: "idle", lease_seconds: 0` before replying. This remains available
after the SSH scope closes, when real analysis continues on saved evidence.
Do not leave thinking active while waiting for human input or after the agent's
turn ends. A stopped/failed worker clears it during cleanup; unexpected process
loss is bounded by expiry. Remote command success, cleanup and agent activity
remain independent evidence.

## Forms and human responses

Use kind=form, text describing the exact question/action/target, and immutable form:

```json
{
  "fields":[{"name":"note","label":"Your note","type":"textarea","required":false,"options":[]}],
  "choices":[{"id":"approve","label":"Approve"},{"id":"reject","label":"Reject"}],
  "expires_at":null
}
```

At most 10 fields, 4 choices. Field types: text, textarea, select, checkbox. Each
field has exactly name, label, type, required, options; options are nonempty for
select only (max 20). Names are unique ASCII alphanumeric/underscore, max 50 bytes,
excluding prototype keys. Labels max 200 bytes; options max 200 bytes; choice id
max 50 and label max 100 bytes. expires_at is null or timezone-aware ISO datetime.
No writer HTML, script, form action, executable URL or browser secret field exists.

Browser submits exactly event_id, revision (the displayed request revision), choice
(an offered id), values (all and only declared field names). Text responses are up
to 2000 UTF-8 bytes per field; checkbox values are Boolean. Required fields and
select membership are validated server-side. One authenticated response wins an
atomic transaction; stale, answered, cancelled or expired forms cannot be answered.
Exact retries remain valid after answering. Response records include response_id,
choice, values, actor from current administrator username and authority
`administrator_cookie`, or actor=agent and authority=agent_capability for an owner
request. They also include received_at and request_revision. Actor/authority are
server-derived, not client input.
The response binds that form and revision only; it is not a grant to execute other
commands. If a submitted request is ambiguous, UI retries only the identical body,
or reloads to reconcile. Form text/values are private operational data, not secrets.

A writer token cannot fabricate a response.created event; it can still write an
`authorization` report, which is explicitly not an authenticated human response.
Producer adapters must validate the returned form ID, revision, selected choice,
target and scope before any separately authorized effect.

## Recovery and agent delivery

Load snapshot seq, subscribe SSE after that seq, ignore duplicate seq and reload a
snapshot on a gap. Block events are `{seq,session_id,type,received_at,block,activity,...}`
with block.created/updated/finished or response.created. Activity-only events are
defined above and have no block. Updated block events have offset and
added_bytes, but contain a bounded summary, not the whole accumulated text.
Responses also include response. SSE delivery is not guaranteed exactly once;
persisted sequence replay supplies recovery. Browser reload reconstructs summaries;
expanded content is fetched only on demand. No source command is replayed.

Long poll responses scans ordered journal pages and returns `{seq,responses}`.
Use its returned seq as the next cursor even after an empty result. wait is 0–25
seconds. An offline agent can recover durable responses later. This wakes a waiting
HTTP client only, not an arbitrary chat/model. No platform-specific wakeup is provided.

The river renders Console blocks as terminal-like text with small gaps between blocks. Identity blocks remain stored and accessible on their dedicated page but are excluded from river content; the toolbar shows a readable identity summary instead of raw JSON. Per-block time,
title, byte/newline counts and revision are hidden there; the dedicated content
page shows this metadata. Small Unicode arrows expand/collapse, page or open
content separately; short output has no redundant expand control. Analysis
blocks show their content without a title or separate-window link in both live
and historical rivers; long analysis still supports inline expansion and paging.
Form blocks retain their meaningful titles. This changes presentation only, not
stored text, stream ordering or authorization.

Reader preserves form drafts across summary updates, follows new content unless
scrolled up, and offers expand/collapse, read next 16 KiB and a dedicated content
page. Only requested pages are retained as expanded text; collapse releases them.
No automatic full-content download/search/export is supplied. Display normalizes
CRLF/within-chunk CR and strips ANSI CSI; raw range text remains the authoritative
stored content. This is not a terminal emulator. Text is rendered with textContent;
forms use controlled DOM inputs. Charts, Three.js, images/video and sandboxed custom
renderers remain future block types, not arbitrary HTML accepted by this API.

## CLI

`python -B -m opsfeast.console_client --token-file FILE OPERATION`:

- create: JSON body above on stdin; no session argument.
- activity: `--session SID`, `{event_id, state, lease_seconds}` JSON stdin.
- block: `--session SID`, block JSON stdin.
- append / finish: `--session SID --block BID`, matching JSON stdin.
- show: `--session SID`, snapshot summaries only.
- content: `--session SID --block BID --offset N --limit N`.
- stream: `--session SID --after N`, JSON event lines until interrupted.
- responses: `--session SID --after N`, immediate durable replies.
- wait: `--session SID --after N --timeout 30`, bounded wait (1–60 seconds).

wait outputs responses or `{seq,responses:[],timed_out:true}`. Timeout is not rejection
or permission. Stream/control interruption exits 130 without stopping any source job.
Other success is exit 0, HTTP/local errors exit 1, usage errors exit 2. The CLI
accepts loopback HTTP origins only and never automatically retries writes. There
is no agent CLI that impersonates the human response endpoint. Browser form input
or authenticated human client submission is required for an actual decision.

## Validation

Tests cover bounded Unicode range reads, partial output, offsets, concurrent writes,
replay/idempotency, storage limits, cancellation/expiry/stale replies, cookie versus
capability roles, same-origin checks, SSE race recovery and client wait behavior.
Browser fixtures use explicitly synthetic administrator/session data. These tests
prove no real SSH execution, backup health, privilege switching or stopping.

*Last modified: 2026-11-05 14:16:33*
