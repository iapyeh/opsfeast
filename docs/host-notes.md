# Host notes 0.1.0

Host notes accumulate installation-specific knowledge for humans and their agents.
The host's **主機筆記** tab under `/hosts?profile=NAME&host=HOST&view=notes`
reads real private data, supports title/content search, and lets an administrator
add, review, edit and delete notes. Notes are plain text, never executable HTML.
The page displays source and last modification time, for example
`2026-11-03 19:43:01+08:00` (Asia/Taipei). UUID is available under record details.
A delete confirmation names the note and explains that deletion cannot be undone.
Merging is available through the CLI/Python/HTTP service; no Web merge editor is
provided. No TUI notes editor or automatic semantic conflict resolver is provided.

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
Each note has exactly:

| Field | Meaning |
| --- | --- |
| `uuid` | Canonical UUID generated on creation; unchanged by edits |
| `host_id` | Exact host ID within this profile |
| `title` | Nonblank plain text, up to 200 Unicode code points |
| `content` | Nonblank plain text, up to 32,000 code points; multiline allowed |
| `source` | `console`, `user`, or `agent` for the latest content change |
| `timestamp` | System-generated last modification time, ISO 8601 to seconds with offset |

There is no separate confirmation time, author field or edit history. Storage uses
UTC (`2026-11-03T11:43:01+00:00`); the current Web reader presents Taipei time.
`console` means distilled from interactive **or noninteractive** Console work;
`user` means manually authored/edited by a user; `agent` means agent-directed
organization or editing, including merging. Confirmation without changing content
does not change source. Web mutations always assign `user`; the local CLI/Python
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
Search is case-insensitive over title/content. `show` returns the same envelope
with one note. Mutations return action, profile/host, revision, note (null on delete)
and deleted UUIDs. No write proves human approval; local OS authority and the
agent's authorization discipline remain necessary.

## HTTP and failure behavior

All endpoints require a signed-in administrator and same-origin checks. Console
writer/agent tokens and site-edit tokens cannot manage notes. The Web adapter
sets source to `user`; local agents use CLI/Python, without borrowing administrator
cookies or self-approving a Console proposal.

| Request | Input |
| --- | --- |
| `GET /api/v1/host-notes?profile=NAME&host_id=HOST&query=TEXT` | query optional |
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

*Last modified: 2026-11-03 20:01:37*
