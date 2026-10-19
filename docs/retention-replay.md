# Replay and explicitly delete observation retention

Use this workflow to convert saved raw observations to a [host vault](host-vault.md),
recover failed retention, or develop a scalar adapter/template without reconnecting
to a host. Replay never executes a recipe or imports its Python files. Deletion is
a separate operation and never happens implicitly during replay.

## Convert existing observations

Run from the actual OpsFeast checkout with the selected Python environment. Replace
the example profile and namespace with the intended management scope:

```sh
python -B tools/opsfeast.py profiles --json
python -B tools/opsfeast.py vault migrate --profile main --namespace example-production --json
python -B tools/opsfeast.py vault ingest --profile main --all --dry-run --json
python -B tools/opsfeast.py vault ingest --profile main --all --json
python -B tools/opsfeast.py vault groups --profile main --json
```

`migrate` enables the namespace and copies any legacy retained SQLite records;
it does not scan raw JSON. `ingest --all` scans only the selected root's direct
`observations/*.json` files. An absent/empty directory is a successful empty batch.
No recursive search, host connection, package installation or recipe execution
occurs. Existing raw bytes and legacy SQLite are preserved. Normal replay updates
records, overview and Markdown automatically. Open `<profile-root>/HOSTS.md` or
open the profile root as an Obsidian vault. Refresh groups explicitly after
hosts.yaml changes. Use `vault rebuild` to repair views; rerunning `migrate` can
copy deliberately deleted records back from the preserved legacy database.

Files may also be selected explicitly, **before options**:

```sh
python -B tools/opsfeast.py vault ingest /path/a.json /path/b.json --profile main --json
```

`--root /absolute/feast` replaces `--profile`. Success returns JSON and exit 0;
per-file failures return failed entries and exit 1 while other files continue.
Use actual ingest receipts for durable record IDs: an empty-vault dry run does not
allocate inventory source metadata.
Failed/skipped/unsupported/mock raw results produce skipped entries and no retained
observations. Offline report outputs are not host observations. Duplicate JSON
keys, non-finite values, unsafe symlinks and unknown contracts fail explicitly.
Do not treat skipped entries as successfully collected observations.

## Original definitions and development overrides

New general runner results save `retention_snapshot` before connection or recipe
execution. It contains only recipe ID/version, access mode, the scalar retention
declaration, literal Markdown template text and a canonical SHA-256 digest. It does
not contain input values, account configuration, arbitrary descriptor metadata or
Python source. Default replay verifies and uses this snapshot, even if the original
recipe directory is gone. Inventory uses the bundled versioned extraction adapter;
its retention definition is product code, not an executable snapshot.

Legacy general raw files have no snapshot. Supply a descriptor explicitly, or use
an override when intentionally trying revised retention definitions:

```sh
python -B tools/opsfeast.py vault ingest /path/raw.json --profile main \
  --recipe-dir /path/reviewed-recipe --dry-run --json
python -B tools/opsfeast.py vault ingest /path/raw.json --profile main \
  --recipe-dir /path/reviewed-recipe --json
```

The override reads recipe.yaml and its optional contained template; no entrypoint
is loaded. Its recipe ID must match the raw result. Its version can differ for
development; provenance records the retention definition version separately from
the executed recipe version. Overrides never change the saved execution access
classification and do not rewrite the original raw/snapshot. Markdown templates
are reviewed content and may contain links; review before opening untrusted output.
Use a separate test Feast and declare `access_mode: read` for read-only development.

## Source identity, conflicts and compatibility

New runner executions assign a canonical UUID `source_observation_id` once, before
work. The ID stays fixed when raw content is corrected. New raw also records
producer_instance_id; replay preserves it (or legacy Core instance evidence).
Absent producer evidence remains the all-zero unknown UUID, never the identity of
the installation replaying the file. `raw_sha256` independently
identifies raw content (excluding the mutable retention receipt). New inventory
retained IDs use source UUID plus SHA-256 of the fixed observation UUID; general
record IDs use the observation UUID directly. Existing files/records keep their
old IDs. Legacy files without UUIDs use their original content hash as the source
alias; editing legacy raw changes that alias. Retention/template changes via an
explicit override do not edit raw, so ordinary legacy development replay remains
stable. No mass raw rewrite is required for migration.

Vault envelopes optionally add `retention_provenance`: source ID, raw digest,
recorded execution mode, snapshot digest and retention recipe version. Older
envelopes remain readable. Replaying an identical old business record can add
missing conservative provenance; it never silently changes its business values.
Identical source/content deduplicates. Different content for an existing ID, or
moving an existing ID across host/year, fails rather than overwriting history.
An author may explicitly delete eligible old retention and replay revised output.
This is not a raw-authentication or anti-tampering mechanism.

## Explicit deletion and write protection

Use a `source_observation_id` returned by ingest, or an exact archived record ID:

```sh
python -B tools/opsfeast.py vault delete-observation SOURCE_ID --profile main --dry-run --json
python -B tools/opsfeast.py vault delete-observation SOURCE_ID --profile main --json
```

There is no force override. Only observations classified **read** can be deleted.
Write/unknown observations, operation intents/results, and observations linked to
such operations (including read observations referenced as verification evidence)
are rejected before archive deletion. Classification comes from
the original execution and stored records, never the currently edited descriptor.
Legacy inventory is the known built-in read path; legacy general observations
without execution evidence are unknown even if today's descriptor says read.

Deletion removes matching read records from annual SQLite, rebuilds cumulative and
overview SQLite, removes managed historical/state Markdown for those observations,
and falls back to the previous observation for the same recipe reference. If none
remains, its generated latest-state page disappears. Raw files, the legacy database,
human notes and all operation history are preserved. A repeated deletion returns
not_found. Execution by direct SQLite editing can bypass these tool protections;
the journal is not cryptographically immutable. Read observations referenced by existing operation journals are protected as audit
evidence; the operation itself is never deleted or rewritten.

Archive writes/deletes commit before projections. Multi-archive changes are not one
global transaction. A projection failure can leave stale derived files: rerun
`vault rebuild`, which uses the managed-view manifest to remove stale generated
pages as well as rebuild SQLite. Unknown/manual files are not removed. No automatic
raw expiry or silent retention replacement is introduced.

## Modules and schemas

Checkout-level `retention_replay.ingest(root, files=(), *, all_files=False,
recipe_directory=None, dry_run=False)` and `host_vault.delete_observation(root,
source, dry_run=False)` implement these CLI workflows. The flags after files are
keyword-only for ingest. `snapshot(metadata, directory)`, `validate_snapshot`,
`source_identity` and `execution_mode` are reusable pure validation helpers.
The optional `saved_snapshot`/`dry_run` arguments of `retain_general` support the
same extraction path; prefer the complete CLI for batch recovery.

Read [raw context](../schemas/raw-retention-context.schema.json),
[snapshot](../schemas/retention-snapshot.schema.json) and
[retention provenance](../schemas/retention-provenance.schema.json) together with
the existing vault record and operation schemas. These additive draft contracts
require updated strict readers; old product versions may reject the new fields.
General-purpose package import/export and transport remain deferred.

Verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed 639 tests, including 14 new replay/deletion regressions. The older interpreters reused the maintenance environment's Python dependencies, which does not prove native SSHScript readiness. Wheel/sdist builds, temporary no-dependency installation, installed-wheel snapshot replay/dedup/write protection and legacy migration/provenance-upgrade/deletion smoke checks passed. Python 3.11 grammar, schema syntax/references, skill frontmatter and Markdown link/date checks passed. No real host connection/write, automatic private-data migration, commit, push or release was performed.

_Last modified: 2026-10-19_
