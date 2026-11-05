# Shared task river 0.1.0

Use one river for an investigation involving several hosts, such as a guest VM
and its hypervisor. Each host keeps an independent worker, connection, account,
command budget and authorization. The shared reader never chooses an execution
target. This extension uses Console blocks 0.2.0 and worker 0.3.0; it is not a host
operation lock or an automatic multi-host executor.

## Open or close blocks without changing the timeline

The reader starts with every block open. Each host button toggles that host's
blocks closed or open independently; **全部** opens all blocks and clears individual
overrides. Buttons show the host icon and host ID, without profile names or added state text. Their
pressed state is exposed visually and through `aria-pressed`. These are toggle
buttons, not a filter or execution selector; arrow keys move focus without toggling.

Click a block's source row or ordinary preview area to toggle just that block.
Enter/Space on its source row provides the same action. A closed block occupies
one line: time, source icon/name, the first nonblank content line truncated with
an ellipsis, and a fixed right-hand toggle. The toggle is always at the far right: **↓**
opens a closed block and **↑** closes an open block. Waiting live forms keep
the toggle disabled.
Open blocks also place time first on their source row and retain the upper-right
**↗** link immediately to the left of the toggle, which opens the original block
separately. The link is hidden while the block is closed. Open blocks retain the existing preview, content loading and form
controls. Links, buttons, inputs and loaded full text retain their own actions.
Background colors, labels and gaps distinguish sources without a colored edge.

New blocks inherit their host's batch state; an individual override survives
streamed updates until the host button or **全部** resets it. Common task blocks
can be toggled individually. No block moves or disappears from the timeline.
Expanded content and drafts remain in their existing DOM nodes. Live forms awaiting
a reply and the separate private-input controls stay open regardless of batch
state. These local choices reset on reload and never change stored records,
commands, authorization or worker state. Read-only history supports the same
presentation controls but still opens no stream and submits no forms or secrets.
The toolbar always retains all declared hosts' latest identities. Individual block
pages retain full content and have no river folding controls.

Block positions follow record-service insertion order. Appends update the original
block and do not reorder it. This is a receive-order timeline, not proof of remote
clock agreement or simultaneous sampling. Preserve source times in operational
output and account for clock skew when comparing measurements.

## Create the shared task before starting workers

Use the [memory-only owner controller](agent-owner.md), or the existing scoped
[record client](console-records.md#cli). The following JSON is synthetic. Replace
UUIDs, profiles, hosts and icons with the intended task's values; obtain icons
from the selected host configuration. Metadata creation does not connect.

```json
{"op":"request","request_id":"task-create","method":"POST","path":"/api/v1/console-sessions","authorization":"Human requested a shared guest and hypervisor investigation","body":{"session_id":"11111111-1111-4111-8111-111111111111","title":"Guest storage investigation","host_id":"Guest and hypervisor investigation","work_id":null,"targets":[{"profile":"lab","host_id":"guest","icon":"🦉"},{"profile":"lab","host_id":"hypervisor","icon":"🖥"}]}}
{"op":"worker.start","request_id":"guest-create","worker_id":"guest-shell","profile":"lab","host":"guest","session":"11111111-1111-4111-8111-111111111111"}
{"op":"worker.start","request_id":"host-create","worker_id":"host-shell","profile":"lab","host":"hypervisor","session":"11111111-1111-4111-8111-111111111111"}
```

Send each control after its predecessor's acknowledgement. Wait for each worker's
`created` event. Both return the same session/reader URL with their own selected
profile and hosts_file. Show one reader for that exact session before connecting;
reuse its tab for the second participant. Then send separate `worker.send` connect
controls to the exact worker IDs, within the human's scope. Worker request IDs,
stdin handles and actual identity stay independent; subsequent run/sudo/su/close
controls still name one worker. Different workers can run simultaneously. Closing
one does not close the other or end the shared record. Do not reconnect solely to
change the selected TAB. `worker.start` membership validation occurs in the worker
before `created` or connection; a controller `starting` result is not successful
attachment.

The direct worker equivalent is:

```sh
python -B -u -m opsfeast.console_agent --host guest --profile lab --session 11111111-1111-4111-8111-111111111111 --token-fd INHERITED_FD
```

The launcher supplies the anonymous pipe; `INHERITED_FD` is not a literal usable
file descriptor. Prefer the owner controller above; do not create a token file
for this workflow. Omitting --session creates the usual independent host river.
Local mode cannot attach to a shared host task. Declaring participants does not
validate connectivity, make an unsupported shell work, or authorize connections.
For ESXi or other targets without the supported Bash Console, use reviewed Core
SSH-exec within existing authorization and publish host-tagged records through
the record service; do not fabricate a persistent interactive shell.

## Source and storage contract

`POST /api/v1/console-sessions` and `Records.create(body)` accept optional `targets`:

- One to sixteen objects, each with exactly `profile`, `host_id`, `icon`.
- Profile and host strings are nonblank, at most 100 UTF-8 bytes each; profile
  cannot contain `/`. Icon is nonblank plain text, at most 32 UTF-8 bytes.
- The service derives `id = profile + ' / ' + host_id`, at most 200 UTF-8 bytes.
  Duplicate participants fail. The returned session stores these immutable IDs.
- The session's existing `host_id` is a task display label. It is not a connection
  selector and must not be parsed as a shared task's participant list.
- Retrying creation with the same UUID and identical original metadata is safe;
  changed targets/order/title return `session_conflict`. No participant editing,
  existing-record relabeling, automatic import or migration tool is supplied.

`POST .../{sid}/blocks` / `Records.add_block` accept optional `target_id`. A declared
ID tags the block; omission or null means common task content. Unknown IDs fail
atomically with `unknown_target`; the block summary and all its subsequent events
preserve the source. Block IDs remain unique across the whole shared river.
Publisher(session_id=SID, host_id=TARGET_ID, ...) attaches to an existing declaration,
never creates/relabels a task, and tags every worker block automatically. Missing
membership raises `shared_target_not_declared` without connecting. Public record
writers are trusted producers: a tag is attributed evidence, not independently
verified identity or an authorization capability.

`POST .../{sid}/activity` / `Records.activity` accept optional `target_id` too.
Per-host leases live in `session.target_activities`, keyed by target ID, and are
included in activity/block events. A command or idle report from one host clears
only that host's lease. Unscoped task activity retains `session.activity`.
Before chat replies or human waits, clear the relevant workers' activity as usual;
expiry stops thinking animation but never stops remote work.

The existing profile/host Console-history query includes shared tasks declaring
that exact participant, with the same session UUID and global timeline for each
host. The lookup still validates the requested registered profile and host, and
keeps stable creation-time/UUID pagination. It does not duplicate blocks into
separate histories, connect, infer membership from a title, or treat source labels
as current identity. Unrelated profiles/hosts do not match.

## Safety and failure boundaries

Use explicit worker IDs for commands, stops, account switches and response
handling. One host's root grant never grants root on another. Block folding is only
presentation, not an authorization gate. A streaming badge or last identity may be
historical evidence; it is not a live-host guarantee.

Private input remains bounded to one active secret request per river. Serialize
password requests across participants; shared workers prefix the field label with
their exact profile/host. A host toggle does not change the recipient of the
private field, which remains separately visible with its target label. No secret
is stored in blocks. Concurrent private requests can fail rather than switch target
or retry credentials automatically. Ordinary forms remain block-scoped.

Existing single-host and untagged records remain readable without rewriting data.
An untagged block has no inferred host source and stays common; do not guess tags
from text. Restart the local Web service and start new workers to load this
extension; preserve all saved records and reconcile active work first. Old workers
retain their loaded code. No source compatibility aliases or historical backfill
are provided.

## Verification

`tests/test_console_shared_river.py` covers validation, membership, concurrency,
independent activity, exact host-history discovery/paging and controller forwarding.
`tests/test_console_shared_workers.py` runs two separate local Bash workers against
one synthetic record service and verifies independent streaming/closure; it does
not SSH to real hosts. `tests/test_web_preview.py` verifies HTTP authorization,
source persistence, rejection and asset availability. The JavaScript host-focus
and navigation tests exercise TAB keyboard/click behavior, chronological slots,
source labels, independent host toggles, individual overrides, stream updates,
expanded-content preservation, waiting-form visibility and form drafts.
Real multi-host SSH, simultaneous privilege switching and real private input
across hosts are not established by these synthetic/local tests.

*Last modified: 2026-11-05 12:05:06*
