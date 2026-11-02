# Console blocks 0.2.0

For automatic SSHScript execution/output forwarding from an agent, use the shipped [Console worker](console-agent.md). It uses this service's existing handlers; the record API itself does not execute commands.


A durable notebook-like river of agent-reported command, output and analysis blocks,
plus administrator-authenticated form responses. This service never connects,
executes commands, switches identity, stops jobs or wakes a model. Its independent
exact-plan executor is documented in [interactive Console](interactive-console.md).
Recipe retention and notification/todo/general logging services remain separate.

## Availability, access and storage

Run `python -B -m opsfeast.web` in the approved environment with requirements-web.txt.
It binds to loopback port 8740. Browser pages require administrator login, load
immediately and need no reader token or extra unlock. Redirects preserve the reader
URL through login. Configuration retains its existing authorization requirements.

The launcher generates private per-launch `.opsfeast-console-writer-8740.token`
and `.opsfeast-console-reader-8740.token` under installation data. Writer can create,
append, finish and read; reader can only read. Both can consume responses but cannot
submit a human response: that requires a valid administrator cookie. Site-edit and
interactive credentials do not grant this service access. Administrator login can
also perform writer operations. Same-origin checks apply to all requests. These
installation-wide capabilities grant access to all its transcripts, not per-host ACLs.
Same OS-user agents may read owner files; this is not OS-user isolation. Keep token
values out of URLs, argv, logs and prompts. Never write passwords or private keys;
no automatic output redaction is supplied. Do not collect secrets in form fields.

SQLite is `<installation-data>/console-records/console-blocks.sqlite3`, in a private
directory with a 0600 database. 0.2.0 is intentionally incompatible with the earlier
0.1.0 chunk API/database. Existing `console.sqlite3` is preserved untouched; old
session URLs are not served by 0.2.0. Create a new session using this contract.
No compatibility layer, migration or deletion is performed. Server restart retains
blocks/responses but does not resume or repeat any source execution. Reported source
status/identity remain historical claims, not continuous connection-health evidence.

## Blocks, deltas and limits

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

Text block states: streaming → completed / failed / interrupted / cancelled.
Form states: waiting → answered or cancelled; expiry is checked at submission.
Do not mark a truncated or interrupted source completed. Finish ends a block, not
an SSH connection. A new block may follow a finished block; there is no session-close
operation in this version. Add a final analysis/status block to describe completion.

Limits: 32 MiB per block, 64 MiB total text per session, 2,000 blocks and 100,000
mutation events. Each create/append text is at most 32 KiB UTF-8, and each HTTP body
at most 64 KiB (so heavily escaped JSON may need smaller appends). Title max 500 bytes.
Limits reject writes explicitly, never silently truncate existing data. Metadata is
bounded separately by typed form/title limits. Each mutation is a SQLite transaction;
event journal, metadata, content and response update commit atomically. Polling SSE
reads committed events, so delivery cannot precede durable acceptance.

## Routes and JSON bodies

| Method / path | Purpose |
| --- | --- |
| POST `/api/v1/console-sessions` | Idempotent metadata creation, no execution |
| GET `/api/v1/console-sessions/{sid}` | Snapshot of bounded summaries and seq |
| POST `.../{sid}/blocks` | Create one block |
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
choice, values, actor from current administrator username, authority
`administrator_cookie`, received_at and request_revision. Actor is not client input.
The response binds that form and revision only; it is not a grant to execute other
commands. If a submitted request is ambiguous, UI retries only the identical body,
or reloads to reconcile. Form text/values are private operational data, not secrets.

A writer token cannot fabricate a response.created event; it can still write an
`authorization` report, which is explicitly not an authenticated human response.
Producer adapters must validate the returned form ID, revision, selected choice,
target and scope before any separately authorized effect.

## Recovery and agent delivery

Load snapshot seq, subscribe SSE after that seq, ignore duplicate seq and reload a
snapshot on a gap. Events are `{seq,session_id,type,received_at,block,...}` with
block.created/updated/finished or response.created. Updated events have offset and
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
content separately; short output has no redundant expand control. Analysis and
form blocks retain their meaningful titles. This changes presentation only, not
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

*Last modified: 2026-11-02 17:13:17*
