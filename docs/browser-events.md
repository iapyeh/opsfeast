# Browser reader readiness 0.1.0

Show the exact river URL in the user's visible browser as soon as its session is
created. An unauthenticated request redirects to `/login?next=...`, preserving the
session, supported live/history/block route and profile/host_id query scope.
After successful human login, the browser follows that local destination. External,
unsupported and duplicate-scope destinations fall back to `/workspace`.

Do not require the human to reply "logged in". Browser authentication is separate
from host authorization and the controller's owner capability. Once the login page
has been presented, continue already-authorized host work and publish output to
that same river. The reader loads stored output when the human arrives, then
receives new output in the usual way. Missing human authorization or an application
password still blocks the operations that need it; viewing is never approval.

## Readiness notification

After its first successful snapshot/render (and initial full-content fetch on a
block page), the reader sends one short notification per page load:

```http
POST /api/v1/console-sessions/SESSION_UUID/reader-events
Content-Type: application/json

{"view":"live","block_id":null,"seen_seq":12}
```

The request requires an authenticated human administrator, same-origin validation
and an existing session. Owner capabilities and scoped record tokens do not publish
human readiness. The body has exactly view (`live`, `history`, `block` or
`history_block`), block_id (existing block UUID for block views, otherwise null) and
seen_seq (nonnegative integer no later than the saved record cursor). Invalid
requests return 422, unknown sessions/blocks 404, missing human authentication 401,
owner-authored readiness or foreign Origin 403. Successful requests return
`{accepted:true,event}`. This does not append a Console block, submit a form, start
an SSE stream for history, or perform a host command. History remains read-only
with respect to records, forms, private input and execution; this metadata POST is
its only additional notification.

The server generates a bounded, process-local event:

```json
{"seq":1,"type":"reader.opened","session_id":"11111111-1111-4111-8111-111111111111","view":"live","block_id":null,"seen_seq":12,"received_at":"2026-11-05T06:00:00.000+00:00"}
```

No password, cookie, token, form content, page text, IP address or username is in
this event. It means an authenticated browser reported loading that snapshot, not
that a human read it, remained present or approved anything. Refresh creates a new
notification; stream updates/reconnects in the same reader do not repeatedly send
one. Notification delivery failure does not block viewing or authorized work.
There is no automatic POST retry, presence heartbeat or reader-close event.

## Delivery to the listening agent

The [owner controller](agent-owner.md) automatically pushes events on its existing
private JSON-lines stdout, even while waiting for its next stdin instruction:

```json
{"type":"browser_event","event":{"seq":1,"type":"reader.opened","session_id":"11111111-1111-4111-8111-111111111111","view":"live","block_id":null,"seen_seq":12,"received_at":"2026-11-05T06:00:00.000+00:00"}}
```

Keep the persistent controller handle and consume this channel alongside command
results and worker events. Match command results by request_id, and readiness by
the exact session_id/view/block_id; the currently selected browser tab does not
select a command target. Reading the execution tool's controller output receives
pending events; this transport does not itself wake an idle model or schedule a
new agent turn. No automatic model-wakeup integration is claimed.

For bounded recovery/other clients, the owner-only API is
`GET /api/v1/agent/browser-events?after=0&wait=0`. wait is 0–15 seconds and after is
a nonnegative cursor. It returns `{events,next_seq,gap}`; gap reports overflow
beyond the latest 256 notifications. Negative/future cursors or invalid wait return
422, missing owner authority 401, foreign Origin 403. Use next_seq for subsequent
reads. A new server starts a fresh cursor; events are not durable or transferable
between processes. No general logging, tracking database, automatic host execution
or notification adapter is added.

## Localhost cookie names

Browser cookies are not isolated by TCP port. Authentication and editing-cookie
names therefore include a stable namespace derived from the canonical external
installation-data path. Separate data roots have separate names even on localhost;
replacement checkouts attached to the same data root use the same names. Moving
data changes the namespace and requires login again. The old unqualified cookie
names are ignored; users must log in after this update. Session values remain
process-local, HttpOnly and SameSite=Strict, and restart still invalidates them.
This avoids accidental cross-installation overwrites; it does not make mutually
untrusted applications on the same hostname an isolated security boundary.

## Implementation and verification

`opsfeast.web.browser_events.BrowserEvents` is a checkout-level condition-variable
buffer with publish/read interfaces, not durable retention or a public Core API.
Its producer is the authenticated reader endpoint; its consumers are the controller
pump and owner HTTP cursor endpoint. Requirements are the existing Web environment;
no plugin, software installation, host connection or browser storage is required
apart from authentication cookies and ephemeral page state.

Public tests exercise authenticated/unauthenticated/owner/origin boundaries, saved
output before login, live/history/block metadata, unchanged record cursors, bounded
buffer recovery and actual loopback controller push while its input is idle.
JavaScript tests cover scoped next URLs, unsafe destinations, one notice per page
and history without form submissions or live SSE. Cookie tests cover independent
installation names, concurrent authentication and one installation logging out
without revoking the other's session. Synthetic tests do not prove human attention
or automatic wakeup in an agent product.

*Last modified: 2026-11-05 14:16:33*
