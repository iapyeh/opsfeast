# Portable recipes, observations and retention data

OpsFeast provides three independent portable units. A recipe is executable operational knowledge; an observation is original host-execution evidence and its declared attachments; a retention unit is already structured data with its data definition and provenance. Each can be transferred independently. Observation and retention packages can also contain both kinds. Generated Vault pages, human notes, service lifecycle objects, host credentials and provider configuration are separate resources.

Use [recipe sharing](recipe-sharing.md) for source/licensing review and [the schema dialect](portable-contracts.md) for recipe-carried data semantics. Read the [data-unit schema](../schemas/portable-data-unit.schema.json), [data manifest](../schemas/data-package.schema.json) and [portable retention declaration](../schemas/portable-retention.schema.json). A hash verifies consistency, not publisher authenticity or permission to transmit. These commands perform local file/database operations, never host connections or recipe/consumer/provider execution.

## Discover and copy data

```sh
python -B tools/opsfeast.py transfer list --kind observation --profile main --json
python -B tools/opsfeast.py transfer list --kind retention --recipe :backup/files/check/daily-backups --profile main --json
python -B tools/opsfeast.py transfer show UNIT_ID --profile main --json
python -B tools/opsfeast.py transfer export --kind retention --recipe :backup/files/check/daily-backups --output /destination/retained-data.zip --profile main --json
```

List returns selected IDs, source identities, times, estimated package bytes and local source/protection information. Show returns the complete unit. Export copies only the selected kinds; omitting --kind selects both. Repeat --id to select specific unit IDs, --host for origin host IDs, or use an exact --recipe reference. Optional --older-than DAYS or --before OFFSET_TIMESTAMP selects strictly older evidence; the two cutoff forms are mutually exclusive. Days must be 0–365000. Selection uses canonical UTC original observation/completion time, never mtime or import time. Running/incomplete executions without completion evidence are not selected. Failed, partial, skipped and unsupported completed host results can be copied independently of retention eligibility.

Data ZIP packages contain MANIFEST.json and per-unit JSON. Each unit preserves original instance, profile, namespace, host and source ID, recipe reference/version evidence, original payload, schema, declared attachment contents and available batch/consumer context. Raw IDs use source_observation_id when available; result location remains contextual metadata. Retention carries already structured values and bundled offline schema references. Raw output can contain operationally sensitive evidence: review selected content before sharing; configuration-name exclusion alone cannot sanitize evidence. Export never transmits or removes the source. Destinations must be new files. Package limits are 20000 units and 512 MiB uncompressed payload; attachments are hex-encoded and count toward that limit. Larger collections require multiple selections/packages.

## Import with merge or replacement

```sh
python -B tools/opsfeast.py transfer import-plan --package /incoming/retained-data.zip --mode merge --profile main --json
python -B tools/opsfeast.py transfer import --package /incoming/retained-data.zip --mode merge --plan PLAN_SHA256 --profile main --json
```

The second command requires the current reviewed plan's sha256. Recompute the plan after any package/target change. The inventory, ordinary-file paths, sizes, digests, unique identities, payload/schema and embedded attachment integrity are checked before mutation. No archive member is extracted into arbitrary paths. Remote schema references and unsupported schema rules fail explicitly.

Merge adds new identities, skips identical content and rejects differing content for an existing identity. Replace replaces only colliding identities included in the package; it does **not** clear unrelated observations or datasets. Use --mode replace for both plan and apply. Origin identities are preserved, so the same host name from another instance/profile is independent. Importing into an empty destination requires no installed producer recipe or registered domain normalizer. It validates saved data instead of rerunning normalization. Import cannot generate current incidents or advance schedules. Native retention replacement also revokes the previous live events' service-effect eligibility, including later retries and rollback, so corrected historical data cannot inherit permission to create current incidents.

Imported units live in `<profile>/transfer/space.sqlite3`. `profile.transfer.query()` and transfer show/export read both native and imported units. Core profile.retention.query/show also expose imported retention through origin-qualified host IDs and portable record IDs, preserving the original record in transfer storage. These are read-only management projections, not host merges or new native observations. Native batch indexes remain their original execution journals; a transferred batch snapshot is context, not a recreated run. Use transfer show for imported raw observations rather than treating their origin file path as a local result path.

Imports use a single SQLite transaction for imported units and journal native replacements with verified before-image packages. Protected write/unknown/linked-operation evidence cannot be replaced. Native attachment changes require a separate archive/import, rather than overwriting shared files. Data replacement preserves origin/storage identity. Import receipts and before images live under transfer/imports/ and intentionally consume additional recovery space. A crash or write failure is explicit and recoverable:

```sh
python -B tools/opsfeast.py transfer import-recovery-plan RECEIPT_ID --profile main --json
python -B tools/opsfeast.py transfer import-recover RECEIPT_ID --plan PLAN_SHA256 --profile main --json
```

Recovery rolls back the affected data to its saved before state and refuses to overwrite later edits. Receipt IDs identify the import operation, not observation IDs. Completed imports can also be rolled back while affected data remains unchanged. No automatic deletion of recovery packages is provided. Keep the profile's transfer metadata with its data.

## Archive to release active storage

```sh
python -B tools/opsfeast.py transfer archive-plan --kind observation --older-than 90 --recipe :backup/files/check/daily-backups --output /external/archive/observations.zip --profile main --json
python -B tools/opsfeast.py transfer archive --output /external/archive/observations.zip --plan PLAN_SHA256 --profile main --json
```

Omit --recipe for all recipes. Choose --kind retention to archive structured history while keeping raw evidence, or omit --kind to archive both. Archive-plan writes a small frozen plan under transfer/plans/. It records the exact exclusive cutoff, membership, source fingerprints, protections and destination. Apply uses this saved membership without advancing the clock or selecting newly eligible records. Selection flags belong to archive-plan; archive takes the plan and destination. A stale source or changed protection requires a new plan.

Archive destinations must be outside the active profile, including after path resolution; use another filesystem when the goal is to free that filesystem's capacity. The package is written and fsynced, reopened and validated before source cleanup begins. A durable receipt under transfer/archives/ records the verified package hash and cleanup progress. Unresolved write/unknown operations and linked verification evidence stay protected. A shared attachment cannot be removed while an unselected observation references it. The entire selected plan is refused if it includes protected entries; narrow the selection instead of guessing which evidence is disposable.

After verification, archive removes only selected raw files/declared unshared attachments and/or selected retained rows and associated consumer-event receipts. The package preserves the available consumer context. It rebuilds retention projections, vacuums the authoritative/projection/transfer SQLite files and refreshes bundled data-only Vault views. It does not invoke custom consumers/adapters, send mail, modify todo/notification lifecycle or delete human notes. Service views can identify archived evidence through the receipt/package location. Custom applications and external copies may retain their own data and need their own authorized refresh.

The receipt reports logical file-size reclamation, compaction and content completion separately; filesystem free-space changes can differ due to allocation/compression and other writers. Small batch/audit/service journals and archive receipts remain so references do not silently disappear. Archive removes active data rather than marking hidden rows, and SQLite VACUUM returns reusable database pages to the filesystem. Recovery before-image packages are intentionally preserved separately.

```sh
python -B tools/opsfeast.py transfer receipts --profile main --json
python -B tools/opsfeast.py transfer resume ARCHIVE_RECEIPT_ID --profile main --json
```

An interruption leaves a verified package and recoverable receipt. Resume checks that package and remaining source fingerprints again, completes deletions, compaction and view repair, and is harmless after completion. Missing/changed packages or later source edits stop further cleanup. Never remove the only archive copy while cleanup/recovery is pending. Restore by importing the archive with the normal merge/replace plan; restoration does not consume or delete the archive.

## Recipe packages and path conflicts

Recipe bundle 0.2.0 uses existing recipes pack/unpack with an explicit allowlist; descriptor, README, entrypoints and applicable license are required. Include every helper, schema, template, optional consumer and necessary asset. File digests and safe executable modes are preserved. Dependencies are declared by the author; pack does not infer a dynamic Python dependency closure. Bundle 0.1.0 is not accepted by this revision. The receiver does not need the sender's private profile settings.

```sh
python -B tools/opsfeast.py recipes pack :example --file recipe.yaml --file main.py --file README.md --file LICENSE --output /destination/example.zip --profile main --json
python -B tools/opsfeast.py transfer recipe-plan --package /incoming/example.zip --path example --profile main --json
python -B tools/opsfeast.py transfer recipe-install --package /incoming/example.zip --path example --plan PLAN_SHA256 --profile main --json
```

Installation targets only profile recipes/. It never overwrites bundled or external checkouts. Same path and identical complete tree fingerprint skips; same path with different content is a conflict. Version numbers never authorize overwrite. The plan shows old/new descriptors, dependency status, different-recipe identity and configuration effects. Specify --resolution replace on both plan/apply to update; --resolution skip keeps the installed tree. Choose another --path to keep both. Same recipe IDs at different paths are supported; short ID selection becomes ambiguous, so use exact source/path references. Host exact-reference settings, saved jobs and consumer subscriptions are preserved and must be reviewed rather than silently rebound. History keeps its original recipe reference and digests.

Optional descriptor portability is `{api: '0.1.0', python: '>=3.11', distributions: {sshscript: '==7.0.1'}, services: {notifications: '0.1.0', todos: '0.1.0'}}`. Dependency inspection checks metadata/API versions only, never imports candidate providers, installs software or proves native runtime/host applicability. Review declared requirements and implementation behavior before applying. Optional consumers are packaged assets and require a separate reviewed installation/activation; no source or delivery route is enabled automatically.

Updates preserve the previous tree under transfer/recipes/ and journal under transfer/recipe-installs/. Replacement uses atomic directory exchange on macOS/Linux controllers; unsupported controller primitives fail explicitly. General Python-operation and offline-report execution pin a complete temporary source tree under the installation lock, so an update cannot mix generations within that execution. Exact native inventory collection still uses its existing bundled job implementation; no general third-party inventory backend is implied.

```sh
python -B tools/opsfeast.py transfer recipe-rollback-plan RECIPE_RECEIPT_ID --profile main --json
python -B tools/opsfeast.py transfer recipe-rollback RECIPE_RECEIPT_ID --plan PLAN_SHA256 --profile main --json
```

Rollback restores the saved tree and preserves the displaced version. It also recovers an interrupted directory exchange. Later local edits cause conflict instead of being overwritten. Neither update nor rollback rewrites historical observation/retention values.

## Python API, views and verification

Use `profile.transfer` or `opsfeast.transfer.Space(profile.root)`: query, select, export, import_plan/import_package, archive_plan/archive and receipts. API mutations require expected_plan; archive accepts resume=RECEIPT_ID. `opsfeast.recipe_install.plan/install/rollback_plan/rollback` provide recipe operations. `opsfeast.transfer.import_recovery_plan/recover_import` handle interrupted imports. Read the owning implementations for exact keyword signatures; source observation and retention payloads are independent even when their IDs link them.

Import creates basic protected `vault/Transfers/` pages with source identities and 12000-character previews; transfer show/API returns complete data/schema/attachments. `transfer rebuild` repairs only these data-only views. View failure is a separate content_update receipt and does not undo committed import. No user adapter executes during import or archival. Review any separately requested consumer/service dispatch because it may run configured external effects.

Public tests cover cross-instance recipe/data transfer, a user-defined contract without registry registration, isolated data import without producer code, dedup/conflict/replacement, recovery before images, archive cutoff/frozen membership, raw-versus-retention independence, attachment and operation protection, ZIP corruption/path rejection, physical SQLite compaction, source-qualified reads, atomic recipe replacement/rollback and pinned execution. A portable backup recipe is exercised with native local scanning and disabled domain registry support. Tests do not establish external transmission, remote archive durability, Windows/FreeBSD controller replacement support or restoreability of the database dump contents.


## Required product features

`portability.features` maps trusted product feature names to required versions: recipe-assessment 0.1.0, recipe-execution 0.1.0 and portable-retention 0.1.0. Plan checks availability without candidate code. Upgrade the receiving product for unavailable features; account bindings stay private. See [results and accounts](recipe-results-and-accounts.md#saved-evidence-and-portability).

*Last modified: 2026-10-30 12:17:33*
