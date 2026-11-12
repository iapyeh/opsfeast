# Host notes 0.1.0

For agent-led recipe work, [execution experience](../skills/opsfeast-recipes/references/execution-experience.md)
provides a pre-run evidence checklist, post-run diagnosis and a lesson template
using this existing store. It covers recipe version, tool capabilities, actor,
source time/result/probe references, validated alternatives and unresolved gaps.
Apply the reviewed save workflow below; routine CLI execution neither reads these
notes nor writes lessons automatically. The existing private store is extended with structured recipe associations and tags.


Host notes accumulate installation-specific knowledge for humans and their agents.
The host's **主機筆記** tab under `/hosts?profile=NAME&host=HOST&view=notes`
reads real private data, supports title/content search, and lets an administrator
add, review, edit and delete notes. Notes are plain text, never executable HTML. The Web view preserves line breaks,
spaces and indentation through the shared stylesheet, and wraps long lines to fit
the note panel.
The page displays source and last modification time, for example
`2026-11-03 19:43:01+08:00` (Asia/Taipei). UUID is available under record details.
A delete confirmation names the note and explains that deletion cannot be undone.
Merging is available through the CLI/Python/HTTP service; no Web merge editor is
provided. No TUI notes editor or automatic semantic conflict resolver is provided.

## Relate notes to recipes

Notes support structured `recipe_references` and `tags`. Recipe references match
exactly after the shared reference normalization: `bundle:system/check` and
`system/check` are identical; `:system/check` and `vendor:system/check` are distinct.
References are syntax-checked, not resolved/executed, so removed or unavailable
recipes can remain linked to historical experience. No substring recipe matching,
package installation, execution permission or cross-Profile association is implied.

Each list accepts up to 32 entries. Recipe references have at most 500 Unicode
characters; tags at most 64, without commas or control characters. Entries must
be nonblank with no surrounding whitespace. Tags normalize to lowercase; both
lists deduplicate and sort. Null, scalar values and malformed references fail.
An empty recipe list identifies general host experience, not “no useful knowledge.”

Read filters are optional: `recipe_reference` selects one exact reference,
`tags` requires all supplied tags, and `query` searches title/content/references/tags.
Filters combine with AND. With a recipe filter, `include_general=True` additionally
includes notes with no recipe references; it is invalid without a recipe filter.
Tag/query filters still apply to those general notes. Reads return the existing
profile-wide revision, not a filtered revision, and never write storage.

Python example:

```python
state = host_notes.inspect(installation, profile='lab', host_id='node',
    recipe_reference='system/inventory/overview', include_general=True)
# Require both tags when narrowing an investigation:
state = host_notes.inspect(installation, profile='lab', host_id='node',
    recipe_reference='system/inventory/overview', tags=['linux', 'iproute2'])
```

CLI and HTTP examples:

```sh
python -B tools/opsfeast.py host-notes --profile lab --host node list --recipe system/inventory/overview --include-general
python -B tools/opsfeast.py host-notes --profile lab --host node list --recipe system/inventory/overview --tag linux --tag iproute2
```

`GET /api/v1/host-notes?profile=lab&host_id=node&recipe_reference=system/inventory/overview&include_general=true`
accepts repeated `tag=linux&tag=iproute2`. Administrator/owner authentication and
same-origin protections apply to filtered reads and metadata writes alike.

Create/update/merge `changes` can include `recipe_references` and `tags` arrays:

```json
{"title":"Inventory tool capability","content":"Reviewed evidence and limits...","source":"agent","recipe_references":["system/inventory/overview"],"tags":["linux","iproute2","unsupported-option"]}
```

Creation defaults omitted lists to empty. Updates preserve omitted metadata;
explicit `[]` clears it. Merges union omitted metadata across the survivor and all
removed notes, while explicit arrays replace the union. Limits still apply to the
merged result. UUID/revision/source rules remain unchanged. A Web editor displays
both fields, uses one reference per line and comma-separated tags, supports
clearing, and offers exact recipe/all-tag/general-note filters.

This is an additive extension of note contract 0.1.0. Existing stored notes without
these fields remain valid and return empty lists; reading does not migrate/rewrite
them. Future writes emit explicit lists. A running older Web process must be
restarted before editing newly labelled notes; old readers rejecting new fields
are not supported. Back up/preserve the Profile as usual. No separate memory store,
automatic runner lookup or automatic execution strategy cache is added. Agents
follow [the experience discovery workflow](../skills/opsfeast-recipes/references/execution-experience.md#make-recipe-related-notes-discoverable).

## Storage and record contract

The explicitly selected registered profile owns `.host-notes.json`, independent
of hosts.yaml, host groups, observations, retention and Vault-generated pages.
Preserve the entire profile when replacing product code. Group moves and Vault
rebuilds do not move or overwrite these notes. Deleting a host definition preserves
notes; CLI/API reads and edits/deletes remain available by its old host ID. New
notes require a currently configured host. Reusing that ID reattaches the old
notes: inspect them before reuse. Automatic rename, identity migration, export,
retention ingestion and synchronization into existing Vault README notes are not
implemented. Existing human notes remain untouched.

The file contains `schema_version: "0.1.0"`, an internal revision nonce and `notes`.
The [note JSON Schema](../schemas/host-note.schema.json) documents its shape; the shared service additionally validates canonical references and text rules.
Each note has the following fields (metadata lists are optional in existing storage and always present in service output):

| Field | Meaning |
| --- | --- |
| `uuid` | Canonical UUID generated on creation; unchanged by edits |
| `host_id` | Exact host ID within this profile |
| `title` | Nonblank plain text, up to 200 Unicode code points |
| `content` | Nonblank plain text, up to 32,000 code points; multiline allowed |
| `source` | `console`, `user`, or `agent` for the latest content change |
| `recipe_references` | Exact normalized recipe references; empty means general host experience |
| `tags` | Lowercase descriptive labels; no execution semantics |
| `timestamp` | System-generated last modification time, ISO 8601 to seconds with offset |

There is no separate confirmation time, author field or edit history. Storage uses
UTC (`2026-11-03T11:43:01+00:00`); the current Web reader presents Taipei time.
`console` means distilled from interactive **or noninteractive** Console work;
`user` means manually authored/edited by a user; `agent` means agent-directed
organization or editing, including merging. Confirmation without changing content
does not change source. Human Web mutations assign `user`; owner-capability HTTP mutations assign `agent`; the local CLI/Python
caller selects the appropriate source. Source describes provenance, not a verified
identity or permission. Evidence and uncertainty belong in content, without secrets.

Reads do not initialize storage or connect to hosts. Writers lock the profile and
notes store, check a content revision, and atomically replace a private 0600 file.
There is no backup, soft delete or retained old content. Opaque `revision` is a
concurrency token distinct from UUID and timestamp; even writes within one second
produce different revisions. Every mutation requires the current revision; a merge
requires the survivor and every removed note to belong to the same selected host.
One merge atomically replaces the survivor's content and deletes the selected notes.
The survivor UUID is preserved; the other UUIDs cease to exist. Unselected notes
are preserved. A profile-wide revision can conflict with an edit to another host.
Cooperating writers serialize; external editors under the same OS account are not
isolated. Do not edit the file directly or automatically retry ambiguous writes.
The store is bounded to 16 MiB and requests to 128 KiB.

## Shared Python and CLI

The checkout-level service uses existing Core profile resolution and standard
library storage, with no new dependency, connection or model invocation:

```python
from opsfeast import host_notes
state = host_notes.inspect('/srv/opsfeast', profile='lab', host_id='web-01', query='APNIC')
receipt = host_notes.mutate('/srv/opsfeast', profile='lab', host_id='web-01',
    action='create', expected_revision=state['revision'],
    changes={'title': 'Registry dependency', 'content': 'Reviewed evidence...', 'source': 'console'})
```

Use `tools/opsfeast.py host-notes` (or `python -B -m opsfeast.host_notes`). All CLI
results, including errors, are JSON; no `--json` flag is necessary. Scope options
precede the action. Read before every reviewed mutation. Replace `REV`, `KEEP` and
`DROP` below with inspected values; examples are synthetic:

```sh
python -B tools/opsfeast.py host-notes --profile lab --host web-01 list --query APNIC
python -B tools/opsfeast.py host-notes --profile lab --host web-01 show KEEP
python -B tools/opsfeast.py host-notes --profile lab --host web-01 create --expected-revision REV <<'JSON'
{"title":"Registry dependency","content":"Reviewed evidence...","source":"console"}
JSON
python -B tools/opsfeast.py host-notes --profile lab --host web-01 update KEEP --expected-revision REV <<'JSON'
{"title":"Registry dependency","content":"Revised reviewed evidence...","source":"agent"}
JSON
python -B tools/opsfeast.py host-notes --profile lab --host web-01 merge KEEP --remove DROP --confirm DROP --expected-revision REV <<'JSON'
{"title":"Merged dependency note","content":"User-reviewed merged content...","source":"agent"}
JSON
python -B tools/opsfeast.py host-notes --profile lab --host web-01 delete KEEP --confirm KEEP --expected-revision REV
```

Repeat `--remove UUID --confirm UUID` in the same order for multiple merge inputs.
Python uses `note_uuid=KEEP`, `remove=[DROP]`, `confirmation=[DROP]`; delete uses
`confirmation=KEEP`. Full title/content/source are required for updates and merges.
`--installation PATH` selects another installation explicitly. CLI exit 0 means
success; 1 returns a sanitized error object; argument errors use argparse exit 2.
Lists return schema/profile/host, host_present, revision and notes, newest first.
Text search is case-insensitive over title/content/references/tags; structured filters follow the rules above. `show` returns the same envelope
with one note. Mutations return action, profile/host, revision, note (null on delete)
and deleted UUIDs. No write proves human approval; local OS authority and the
agent's authorization discipline remain necessary.

## HTTP and failure behavior

All endpoints require a signed-in administrator and same-origin checks. Console worker and site-edit tokens cannot manage notes. The installation owner
capability can use these APIs independently of a human session. The Web adapter
sets source to `user` for human sessions and `agent` for owner capability; local
agents can also use CLI/Python without borrowing human cookies.

| Request | Input |
| --- | --- |
| `GET /api/v1/host-notes?profile=NAME&host_id=HOST&query=TEXT` | query, recipe_reference, repeated tag, include_general optional |
| `POST /api/v1/host-notes` | profile, host_id, expected_revision, changes |
| `PATCH /api/v1/host-notes` | same plus note_uuid |
| `DELETE /api/v1/host-notes` | profile, host_id, expected_revision, note_uuid, confirmation |
| `POST /api/v1/host-notes/merge` | update fields plus remove and confirmation UUID arrays |

Unknown fields fail validation. Errors: authentication/origin 401/403; absent note
or create target 404; `note_revision_conflict` 409; invalid data, storage, source,
confirmation or cross-host references 422 (cross-host note references return 404).
Storage failures never expose raw note data/paths. After conflict, retain the draft,
reload current state, compare and ask the human to resolve substantive differences.
There is no automatic semantic merge. Do not assume a failed/ambiguous response
means no write; read back before deciding what to do next.

## Answer host questions from accumulated evidence

Apply this workflow when a user asks about a named host's condition, performance,
past incident, repair options or previous work, even if they ask only for advice
and do not request a connection. Use the existing local records before forming
host-specific conclusions. General conceptual questions without a host do not
require a host-history search.

1. Resolve the intended installation, profile and exact host ID from available
   context and read-only host discovery. Do not silently use another profile or
   merge similarly named hosts. Ask only if ambiguity affects the answer.
2. Read that host's notes, starting with a host-scoped list and then relevant
   title/content searches. A keyword miss is not proof that no relevant notes
   exist. Notes capture previous decisions, constraints, failed approaches and
   lessons that numeric observations may omit.
3. Inspect relevant saved host results with observation result, the inventory
   latest-attempt view, and retained history as needed for the question. Read the
   selected records, not just a success label or newest timestamp. Narrow by host,
   recipe, property and incident time; compare before/after evidence when useful.
   Consult [result-data](../skills/opsfeast-result-data/SKILL.md),
   [inventory jobs](inventory-jobs.md) and the
   [CLI reference](cli.md#host-result-history-and-modes) for current contracts.
4. Reconcile notes and measurements using source sample/probe times, actual
   identity/scope, units, collection coverage and partial/failed/unknown states.
   A latest inventory view combines properties sampled at different times; it is
   not necessarily one simultaneous snapshot. A newer failed attempt must not
   disappear behind an older successful value. A note's modification time is not
   necessarily the event time. A reused host ID may refer to replaced hardware.
   Show contradictions and missing evidence rather than silently resolving them.
5. Use both direct and indirect information. Direct information is relevant
   evidence in saved observations, inventory, notes or diagnostic records.
   Indirect information is external knowledge found by using those facts as
   search context: for example, an observation identifies FreeBSD, so search
   official FreeBSD documentation for relevant disk-I/O behavior, tools and
   remedies. Match the observed OS/product version when available; do not assume
   an unknown version or substitute Linux commands. Cite the external sources and
   explain how they relate to the observed facts. External documentation supports
   interpretation and possible remedies; it does not measure this host's actual
   condition.
6. Explain what was found, what it establishes at the recorded time, what remains
   a hypothesis, and what information is still needed. Reference useful
   result/record IDs, note UUIDs and observation times without exposing secrets.
   If neither direct nor indirect information is sufficient to answer, ask the
   user a focused question for the missing facts, or propose opening an
   interactive Console so the agent can inspect the host directly. State the
   target, question to resolve and intended inspection scope. Do not stop at
   generic advice or a list of commands for the user when a concrete question or
   an offer to perform the inspection can advance the task. An exhaustive web
   search is not required before asking about a material fact only the user or
   live host can supply.
7. Reuse already authorized inspection scope if fresh evidence is needed.
   Local history reads do not authorize connections, new inventory collection,
   privilege changes, repairs or scheduling. In particular, inventory latest reads
   saved data, while inventory query connects even without --save. Follow the
   relevant operational skill for authorized collection. For a Console proposal
   accepted by the user, follow the [interactive skill](../skills/opsfeast-interactive/SKILL.md)
   and its visible-reader procedure; show the Console before connecting and then
   perform the agreed inspection. Reuse an existing grant within scope without
   asking again. Root entry requires explicit authorization for that host/task;
   inspection does not authorize repairs.

Synthetic read-only examples, from the checkout with the selected interpreter:

```sh
python -B tools/opsfeast.py host-notes --profile lab --host web-01 list
python -B tools/opsfeast.py host-notes --profile lab --host web-01 list --query disk
python -B tools/opsfeast.py observation result --profile lab --host web-01 --json
python -B tools/opsfeast.py observation result RESULT_ID --profile lab --detail --json
python -B tools/opsfeast.py inventory latest --profile lab --host web-01 --json
python -B tools/opsfeast.py retention list --profile lab --host web-01 --recipe system/inventory/overview --json
python -B tools/opsfeast.py retention show RECORD_ID --profile lab --json
```

Host-notes commands already return JSON; do not add --json. Choose relevant reads
rather than dumping all records. When saved results are insufficient, relevant
[Console history](console-records.md#discover-saved-console-history-by-host) can
supply original diagnostic context without reconnecting or replaying commands.

Chat memory can locate an incident, but does not replace accessible OpsFeast
records. Never claim to have queried notes, observations or inventory when only
chat memory was read. Distinguish no matching records from inaccessible, malformed
or unavailable stores; report the affected source and continue with available
evidence. If no relevant history exists, state that limit and give conditional
advice rather than inventing a host diagnosis. Continue with a focused question
or a concrete Console inspection proposal if the answer still needs host facts.

For example, historical cleanup of disk space and inodes does not establish that
current disk latency or IOPS are healthy. Before recommending storage hardware,
look for device/mount mapping, workload and latency evidence; identify any missing
measurements explicitly. Keep this reusable guidance free of private host data.

This is an agent procedure using existing read interfaces, not an automatic
cross-store search service or a guarantee that every agent follows it. Save new
lessons through the reviewed note workflow below; an advisory answer alone does
not authorize writing notes.

## Human-agent workflow

Before operating on a host, read its relevant notes and assess age, evidence and
uncertainty. Notes provide context, never authority to run commands. Reverify
changeable facts when needed within the user's authorized inspection scope.

After **each Console interaction/task concludes**, proactively ask whether the
human wants to turn accumulated experience into host notes. This applies to both
interactive and noninteractive work. Do not interrupt every individual command.
Only after agreement, extract a concise draft, preserving confirmed facts,
uncertainties and evidence. Present the selected profile/host and complete draft.
Write only after the human confirms the final content; agreement to extraction
alone is not approval to save. Reuse already supplied approval, including accepted
small corrections, instead of requesting it again. Read back UUID/source/timestamp
after saving. This is an agent procedure, not a machine-enforced approval service.

When asked to organize existing notes, read them through this service, show
conflicting claims rather than silently choosing one, propose merged content and
explicit UUIDs to retain/remove, and obtain confirmation before applying the exact
change. Source becomes `agent`. Declined or unfinished drafts stay unsaved.

Example human prompt: “Read this host's notes before diagnosis. When finished,
ask whether to extract new experience. Show me the draft before saving. When I ask
to merge notes, show the merged text and which notes will be removed.”

## Verification

`tests/test_host_notes.py` covers private local storage, no-write reads, UUID/source,
search, concurrency, validation, host separation, orphan preservation, atomic merge,
delete confirmation, malformed/symlink storage and CLI JSON input/output.
`tests/test_web_preview.py` covers administrator/origin boundaries and HTTP CRUD,
merge, source assignment and conflict responses. `tests/test_host_notes.mjs` covers
escaped rendering, timestamp formatting and actual create/edit/delete event handlers,
including draft preservation on conflicts. These synthetic tests do not connect to
any host or prove arbitrary filesystem-writer isolation.

*Last modified: 2026-11-12 11:52:01*
