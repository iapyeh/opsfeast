# Recipe retention and content applications

For automatic downstream updates, use [retention consumers 0.1.0](retention-consumers.md): static dependencies, explicit activation, transactional events, per-consumer delivery receipts and retry. `recipes show REFERENCE` and `consumers list --recipe REFERENCE` expose which programs use a recipe's retained data. Vault is the default consumer; additional consumers require no runner changes.

The data flow is **Recipe → Retention → Content**. A recipe creator defines and produces the retained dataset. OpsFeast discovers and runs recipes, validates and stores their declared data, and provides documented read interfaces. Content authors and user AI agents select one or many retained datasets to produce Markdown, graphs, web pages or other artifacts. Vault is the currently bundled content application; it is not the retention contract or the authoritative data store.

## Discover and read data

Start with `recipes list --profile NAME --json`, `recipes show REFERENCE --profile NAME --json` or `inspect-recipe PATH --json`. Their `retention` metadata identifies the declared contract, field meanings and retrieval interfaces. A declaration does not prove that a recipe has run or produced usable data. Distinguish catalog recipe IDs from exact source-qualified references such as `company:system/network/check/port`.

```sh
python -B tools/opsfeast.py retention list --profile main --recipe company:system/network/check/port --host node --json
python -B tools/opsfeast.py retention export --profile main --since 2026-01-01T00:00:00Z --status partial --json
python -B tools/opsfeast.py retention show RECORD_ID --profile main --json
python -B tools/opsfeast.py retention inspect --profile main --json
```

`list` and `export` return the same complete structured selection, with [selection schema](../schemas/retention-selection.schema.json) `contract_version: 0.1.0`, `kind: opsfeast-retention`, namespace and validated record envelopes. Export writes JSON to stdout; it does not transmit, import or sanitize data. Both support repeated `--host`, exact `--recipe` reference, inclusive `--since`/`--until`, `--status` and `--kind observation|operation`. Times must include a timezone; results sort by precise UTC observation time then record ID, oldest first. Empty selection is successful. Unknown record IDs and invalid ranges fail explicitly. All commands accept mutually exclusive `--profile NAME` or `--root PROFILE_ROOT`. Output stays JSON in terminals; `--json` is accepted explicitly. Exit codes are 0 for success, 1 for data/content/storage failure and 2 for argument parsing errors.

Readers inspect authoritative archives without creating directories, locks, manifests or projections. Full records preserve original timestamps, field states, identity quality/warnings, recipe reference/version, source and producer identity, provenance and origin. Generation time never replaces observation time. Partial observations do not borrow old values; null stays unavailable, zero and false remain values. Review record contents before sharing.

```python
from opsfeast import Instance
profile = Instance.open('/path/to/installation').profile('main')
selection = profile.retention.query(hosts=['node'], recipe='company:system/network/check/port', kind='observation')
for record in selection['records']:
    print(record['record_id'], record['observed_at'], record['data'])
record = profile.retention.show(selection['records'][0]['record_id'])  # only for a nonempty selection
```

Checkout composition also supports `from retention_store import query, show, Reader` after adding the trusted checkout's `tools/` directory to the Python import path. `query(root, *, hosts=None, recipe=None, since=None, until=None, status=None, kind=None)` and `show(root, record_id)` have the same semantics as the CLI. Prefer `profile.retention` in Core programs. No connection, recipe execution or publication is implied by a read.

## Local collection evidence

Inventory recipe 0.3.2 adds an optional envelope-level collection_evidence object, defined in [collection-evidence.schema.json](../schemas/collection-evidence.schema.json). It is local collection provenance 0.1.0, independent of data.inventory / inventory-observations 0.1.0 and the unchanged normalizer/schema digest bindings. The runner explicitly captures the verified actor and bounded probe metadata into new raw reports, and retention preserves that opt-in object. Old raw reports do not have it and are not backfilled. Replaying an identical new report deduplicates normally; changing an existing record's evidence remains a content conflict, not an enrichment/migration path.

The actor contains username (nullable), effective_uid (nullable) and mode. Each probe has section, field, status, command, reason_code, exitcode, error_type and observed_at, with nullable evidence where unrecorded. Capture projects only those fields; it excludes stdout/stderr, access passwords and credential-source/attempt details. Built-in source commands are fixed reviewed read queries. Authors must keep secrets out of commands and this explicit retained evidence; arbitrary query text is not automatically redacted. Validation is structural evidence, not proof that a remote host executed the report.

Core profile.retention.query/show and retention list/show/export return the optional metadata with the envelope. The legacy observation exchange exports normalized data only, so this evidence is not added to its contract. Use record.get('collection_evidence') and preserve missing/unknown state. The existing data.collection_scope remains mode/effective_uid only. No change to SQLite physical layout, retained business fields or existing snapshot extraction is required.

Checkout modules may reuse collection_evidence.capture(report) and validate(value), after reviewing signatures and supported schema. capture is a producer opt-in projection; never call it to guess evidence from a retained record or read arbitrary raw files in a content consumer. The bundled runner invokes it after detail collection and before saving. Content authors read it through public retention readers; Vault displays account/query evidence without host operations.

## Recipe-owned data declarations

Inventory declares its recipe-owned `inventory-observations` 0.1.0 contract, [schema and normalizer](../recipes/system/inventory/overview/README.md#recipe-owned-retention-contract). The platform does not infer a declaration from its recipe ID. General operation recipes may declare scalar `host-values` **0.2.0**:

```yaml
access_mode: read
retention:
  contract: host-values
  version: 0.2.0
  description: TCP reachability only; failure does not establish its cause or overall service health.
  fields:
    reachable:
      type: boolean
      unit: ""
      description: Whether the bounded TCP connection attempt succeeded.
```

The creator must explain the dataset's scope/limits and each field's meaning. Types are string, integer, number and boolean; each field requires an explicit unit (empty for unitless) and nonempty description. Only declared top-level `result.data` fields are retained. Null/missing values are unavailable; wrong types fail retention. Only operational local/SSH success or partial results qualify. Failed, skipped, unsupported and mock results are excluded. Undeclared inputs, credentials, commands and raw errors are not copied. Field descriptions and declared business values must themselves be safe to retain.

Retention does not execute custom adapter code or templates. `markdown_template`, rendered `data.markdown` and snapshot template text are no longer supported. Content belongs to a separate program. All current operation snapshots, including inventory, use **0.2.0**, capturing the recipe identity/version, data extraction declaration, execution classification and digest. See [offline replay and protection](retention-replay.md).

### Registered structured retention

system/inventory/overview 0.3.2 declares `retention: {contract: inventory-observations, version: 0.1.0, description: ..., schema: retention.schema.json}` and explicit access_mode. Its raw `output` no longer selects an adapter. The recipe-owned schema includes nested field meanings/units and limitations; shared retained/exchange schemas reference that source. Discovery reports the declared metadata, schema_path/schema_sha256 and registered normalizer source/digest without loading collection code.

The platform registry (`retention_contracts`) maps supported contract/version pairs to shipped creator-owned normalizers, independent of recipe ID. It validates declarations and exact schema content (top-level comments excluded), then invokes registered semantic validation/normalization. It never loads arbitrary normalizers from candidate paths. Contributing a new structured contract requires product registration, schema, reviewed code, tests and guidance; descriptor paths are not executable plugin permissions. A clone reusing inventory-observations uses the installed registered normalizer; ship its matching retention.schema.json and declare the required OpsFeast contract support.

Saved snapshots include normalizer_sha256 and canonical schema_sha256. Replay refuses installed implementation/schema drift unless an explicit reviewed --recipe-dir selects revised extraction. Envelopes carry retention_definition, and provenance links its snapshot digest. Record IDs never authorize overwriting changed business data or definitions. Raw/retained/exchange versions remain separate from recipe versions. Content programs continue to consume the public retained envelopes, without inventory-specific raw parsing.

## Storage and execution phases

```text
<profile-root>/
  feast.yaml                     # namespace, overview_months, vault.auto_refresh
  hosts.yaml
  observations/                  # saved raw recipe results
  retention/
    .projections.json
    hosts/<encoded-host-id>/
      <UTC-year>/observations.sqlite3   # authoritative envelopes
      records/observations.sqlite3      # rebuildable cumulative projection
    overview/observations.sqlite3       # rebuildable rolling observation projection
  vault/                         # content and human notes; no SQLite
  reports/<run-id>/               # content report result and artifacts
  .retention-source.json
  .retention.lock
  .vault.lock
```

Logical identity remains `(namespace, host_id)` across OS/hardware replacement. Source/producer UUIDs and native identifiers remain evidence; namespaces are user assertions, not authenticated publisher identities. IDs use reversible UTF-8 percent encoding. One profile holds one namespace, fixed after initialization. `overview_months` defaults to 3 (1–1200); cumulative records do not expire. UTC completion time selects the archive year; operation result events remain in their intent year.

Annual databases use SQLite `user_version=1`, a `records` table containing `record_id` primary key, kind, namespace, host_id, recipe_id, observed_at and canonical JSON payload, plus an index on kind/recipe_id/observed_at. See [record envelope](../schemas/host-vault-record.schema.json), [scalar values](../schemas/host-values.schema.json) and [operation events](../schemas/operation-event.schema.json). Stable IDs deduplicate identical content; conflicting content fails. `retention rebuild` recreates data projections without updating vault content. Authoritative history is never pruned by rebuild.

New profile initialization establishes retention and the bundled vault. `vault.auto_refresh` defaults to true; set it to Boolean false in `feast.yaml` to retain data without automatically updating Vault (other enabled consumers remain active):

```yaml
schema_version: 1
kind: opsfeast
namespace: production
overview_months: 3
vault:
  auto_refresh: false
```

Runner execution saves raw results, records operation outcomes, retains data and then dispatches enabled retention consumers, including bundled Vault. Saved `retention` and `content_update` receipts are siblings. Collection/recipe status, data persistence and content publication are separate evidence. A renderer failure preserves the committed data and recipe status, records a failed per-consumer attempt in the aggregate `content_update` receipt with a `consumers dispatch` recovery command and produces a nonzero CLI exit. Retention failure remains explicit and raw stays available. Both receipts are excluded from raw identity/digest calculations. No whole-pipeline transaction or automatic remote retry exists.

## Content authors and offline reports

Use the existing `python-report` framework for reviewed local content generation. `ReportContext.retention.query(...)` and `.show(record_id)` provide the selected profile's read-only data interface; existing explicit JSON `context.inputs` and artifact output remain available. No raw files or vault-internal paths are needed. Report results include `retention_sources` recording selections, record IDs, source times and selection digests. Full input records remain authoritative; output must preserve relevant partial/unknown and quality context. This facade is a usable API, not a Python/network sandbox.

```sh
python -B tools/opsfeast.py recipes run feast/report/retention-summary --profile main --json
python -B tools/opsfeast.py recipes run feast/report/retention-summary --profile main \
  --var 'recipes=["company:system/network/check/port","company:system/account/check/identity"]' --var 'hosts=["node"]' --json
```

The bundled [retention report](../recipes/feast/report/retention-summary/README.md) demonstrates Markdown and escaped HTML from the same data that feeds the bundled vault. Multiple selected recipe references can be combined without a connection or collection. Outputs use existing validated artifacts, result lookup, portable recipe packaging and saved-job mechanisms. Custom graph/web renderers declare their dependencies and verification; web hosting, scheduling, transmission and automatic installation are not provided by this feature. Report generation does not refresh collection and is not itself a host retention producer.

## Operation journals and module boundaries

Runner-managed write/unknown recipes commit an intent before loading operation code or connecting (inventory follows its existing access-preflight boundary), then append the result after cleanup. A failed intent write prevents operation execution; a crash leaves unresolved intent. Cleanup/remote termination and verified state changes remain separate evidence. Outcome-journal failure remains a runner failure; no content failure can erase or downgrade this evidence. Direct Core/session calls require explicit journaling and are not automatically audited.

`retention_store.operation_intent(root, host, metadata, descriptor_digest, variable_names, *, reference=None, implementation_digest=None, source_observation_id=None, bundle_digest=None)` returns an intent or None for read/no namespace. `operation_result(root, intent, report, observation_ids=())` appends the outcome. `retain_general(root, report, metadata, directory, *, saved_snapshot=None, dry_run=False)` uses reviewed declarations; `retain(root, raw, dry_run=False, *, saved_snapshot=None)` dispatches registered structured normalization by the saved declaration. `retention_contracts.validate_declaration(metadata, directory=None)`, `normalize((contract, version), raw, source)` and `validate_payload((contract, version), data)` are checkout developer interfaces; users normally use runner/replay/query instead. Successful data-write receipts may include a separate nested `content_update`; runner summaries store it at the top level. Record writes also commit change events transactionally. The content_update payload now contains per-consumer attempts rather than a single Vault result. Intent/result functions defer consumer dispatch; standalone callers explicitly call `retention_store.refresh_content(root)` after completing their data writes. See [Core integration](core-api.md#host-vault-integration).

POSIX cooperating retention writers serialize through `.retention.lock`; content publication uses `.vault.lock`. Annual commit precedes projections; projection failure can leave committed records requiring `retention rebuild`. Content uses atomic per-file replacement with author manifests, not a whole-vault transaction. Copy with writers stopped or consistent SQLite backups; live cloud/network SQLite and noncooperating editors remain unsupported. No host connections, native privilege verification or cryptographic audit guarantee follows from synthetic tests.

## Development incompatibility

Existing SQLite under `vault/` is rejected before new storage use; no automatic relocation/fallback is supplied. Preserve the old profile and notes, initialize a separate profile with the same namespace and replay selected raw. Keep old raw receipts to preserve source identity. Old inventory raw without a current snapshot and general raw with old template snapshots require an explicit reviewed current descriptor through `--recipe-dir`. Changing that descriptor cannot change historical execution classification. Existing data and notes are never moved or deleted automatically. Profiles without namespace retain their existing legacy observation-store behavior until explicitly initialized; this is separate from the rejected vault SQLite layout.


Retention/content delivery verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 679 public tests, including headless TUI, inventory-owned contracts, scalar/list group rendering, replacement of edited generated outputs, protected human notes and isolated installed-wheel data/content assertions. Older interpreters reused the maintenance environment's Python dependencies; this does not establish native execution-library readiness. Wheel/sdist builds, temporary no-dependency installation and installed-wheel scalar/structured queries, replay/dedup, offline Markdown/HTML, vault and protected operation evidence checks passed. Python 3.11 grammar, schema syntax/references, skill frontmatter, document links/footers and diff whitespace checks passed. Verification used synthetic/local data and performed no host connections or collection, private-data relocation, push or release.

## Explicit observation runs

Operational CLI batches, saved inventory collections and due-work dispatch persist [observation-run 0.1.0](observation-runs.md), anchored in the first target's annual archive beside retained records. Run identity/membership, outcomes and saved Attention policy/findings are separate from recipe-owned normalized data. No normalizer/schema digest or old observation is rewritten. Use Core/report-reader runs()/run(run_id), checkout observation_runs.list_runs/show or inventory runs list/show. Ordinary query/export does not include these objects. Completed runs are immutable; read stored snapshots for historical evaluation and current settings only for current views. Updates emit retention.run.updated atomically; the [consumer contract](retention-consumers.md) distinguishes run IDs from observation record IDs. Missing/deleted source data does not erase saved batch evidence or authorize recollection.

_Last modified: 2026-10-20 23:10:05_
