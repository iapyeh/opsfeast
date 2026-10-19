# Offline retention replay and protected deletion

After an actual successful write, replay dispatches enabled [retention consumers](retention-consumers.md), including registered local programs. Its dry-run never dispatches. Identical replay creates no new event but can retry pending deliveries. `content_update.consumers` records each attempt independently; use `consumers inspect/dispatch` for delivery recovery. Previously retained records without events require application rebuilds rather than replay-based event backfill.

Replay is the data-only recovery/development path from saved recipe raw results into [retention storage](retention.md). It never connects, imports recipe execution code or refreshes collection. Default vault publication is a subsequent content application, with its own result; it can be disabled with `vault.auto_refresh: false`.

## Convert existing observations

```sh
python -B tools/opsfeast.py retention ingest --profile main --all --dry-run --json
python -B tools/opsfeast.py retention ingest --profile main --all --json
python -B tools/opsfeast.py retention ingest /path/to/raw.json --profile main --json
```

Files precede options. Choose explicit files or `--all` over the selected profile's `observations/*.json`. `--dry-run` validates without writing raw, archives, source identity, locks or content. Actual replay preserves raw files. Eligible operational success/partial results are stored; failed/skipped/unsupported/mock and non-host report results are skipped. Invalid inputs fail individually while other files continue. Results include per-file stored/already_stored/validated/skipped/failed and separate content receipts. Any data or content failure makes the batch status failed and exits 1; argument errors exit 2. Empty `--all` selection succeeds.

## Original definitions and development overrides

Inventory and general raw records include a data-only retention snapshot **0.2.0** created before execution. It contains the recipe identity/version, reviewed scalar declaration, access mode and canonical SHA-256 digest. It includes no Markdown template. Replay uses the saved declaration even if the recipe is removed or changed. Structured inventory snapshots also bind the registered creator-owned normalizer and canonical schema digests. Replay invokes that shipped pure data normalizer; it never imports candidate collection/normalizer code.

```sh
python -B tools/opsfeast.py retention ingest /path/to/general-raw.json --profile main \
  --recipe-dir /path/to/reviewed/current-recipe --dry-run --json
```

An explicit `--recipe-dir` selects a reviewed current descriptor and matching registered schema without importing candidate code. Its contract/version selects the shipped normalizer, not a candidate Python path. Use it for old inventory/general raw without a current snapshot or a mismatched registered normalizer/schema digest or to test revised extraction definitions. Old template-bearing snapshots, missing inventory snapshots and mismatched structured digests are rejected unless explicitly overridden. This does not make protected history deletable. The selected recipe ID must match the executed recipe; changing current metadata never reclassifies historical execution mode. Never change old write/unknown evidence to read to permit deletion.

## Source identity, conflicts and compatibility

`source_observation_id` is the stable execution UUID; raw digest detects evidence changes independently. Both `retention` and `content_update` receipts are excluded from raw digest/identity. Producer identity comes from saved evidence, never the replaying installation; missing producer remains all-zero. Inventory replay retains the original source UUID from an existing raw retention receipt. Replay into a separately initialized profile does not alter source provenance or imply transport authorization.

Identical IDs/content deduplicate; changed content or a host/year change for an existing ID fails. Fix a read-only extraction by explicitly deleting its prior retained observation and replaying a reviewed declaration. Preserve protected evidence. Old SQLite-in-vault storage is rejected: preserve it and its human notes, initialize a separate profile with the same namespace, then replay selected raw. No automatic relocation, fallback reader, relabeling or deletion is provided.

## Explicit deletion and write protection

```sh
python -B tools/opsfeast.py retention delete-observation SOURCE_OR_RECORD_ID --profile main --dry-run --json
python -B tools/opsfeast.py retention delete-observation SOURCE_OR_RECORD_ID --profile main --json
```

Deletion removes matching read observations only, rebuilds data projections and attempts enabled content refresh. Raw files and human notes are preserved. Unknown IDs return not_found. Operation events, write/unknown observations, their linked source observations and verification evidence are protected. Missing historical general execution classification is unknown, even if a current descriptor says read. Data deletion cannot be undone by content rebuild; preserved raw is the recovery source. If projection repair is needed use `retention rebuild`; if only content failed use `vault rebuild`.

## Modules and schemas

Checkout modules: `retention_replay.snapshot(metadata, directory)`, `validate_snapshot(value)`, `select_snapshot(report, directory=None)`, `ingest(root, files=(), *, all_files=False, recipe_directory=None, dry_run=False)`; `retention_store.delete_observation(root, source, dry_run=False)` and `retain_general(..., saved_snapshot=None, dry_run=False)`. Reuse these instead of direct SQL deletion/scanners. Reads and dry-run never initialize state.

Schemas: [raw replay context](../schemas/raw-retention-context.schema.json), [data-only snapshot](../schemas/retention-snapshot.schema.json), [provenance](../schemas/retention-provenance.schema.json), [record envelope](../schemas/host-vault-record.schema.json), [scalar fields](../schemas/host-values.schema.json), [operation events](../schemas/operation-event.schema.json). Synthetic tests verify replay and failure/protection behavior; they establish no native SSH/su/sudo or remote termination guarantees.

_Last modified: 2026-10-19 14:55:28_
