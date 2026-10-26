# Schemas

[collection-evidence.schema.json](collection-evidence.schema.json) defines optional local raw/retained-envelope collection provenance 0.1.0: verified actor and bounded query metadata without outputs or credentials. It is referenced by host-vault-record and inventory raw schemas, independent of the unchanged normalized inventory/exchange payload. See [local evidence semantics](../docs/retention.md#local-collection-evidence).

Replay adds [raw-retention-context.schema.json](raw-retention-context.schema.json), [retention-snapshot.schema.json](retention-snapshot.schema.json) and optional [retention-provenance.schema.json](retention-provenance.schema.json) in retention envelopes. Operation events can link a source observation UUID. Read [runtime validation and compatibility](../docs/retention-replay.md); SHA-256 equality and cross-record deletion protection are enforced by code beyond JSON Schema.

[retention-selection.schema.json](retention-selection.schema.json) defines complete query/export results. Raw replay context also defines the independent content_update receipt.

system/inventory/overview 0.3.1 owns [retention.schema.json](../recipes/system/inventory/overview/retention.schema.json), including nested meanings/units. The shared retained-observation and exchange/envelope schemas reference that creator-owned source. Structured snapshots bind normalizer_sha256 and schema_sha256; envelopes preserve retention_definition. See [registered contract workflow](../docs/retention.md#registered-structured-retention). Raw, recipe, retained and exchange versions remain independent.

## Retention contracts

[host-vault-record.schema.json](host-vault-record.schema.json) defines namespace-based management identity, immutable origin and recipe provenance. [host-vault-package.schema.json](host-vault-package.schema.json) is an earlier, unimplemented manifest proposal; current independent data transfers use the portable unit/package contracts below. Read [runtime storage and validation](../docs/retention.md) and [portability](../docs/portability.md). Existing inventory payload contracts remain independent of the transfer envelope.

Host-values and snapshots are now data-only 0.2.0; field semantics are required and Markdown templates are removed. See [query/content contracts](../docs/retention.md).

This directory defines versioned data contracts for host records, service relationships, observations, and recipe execution results.

For the current host configuration object, read [hosts.yaml](../docs/hosts-yaml.md); a standalone host JSON Schema is not implemented. [Core API](../docs/core-api.md) and [profiles](../docs/profiles.md) define installation/profile and runtime objects; [recipe execution](../docs/recipe-execution.md) and [recipe experience](../docs/recipe-experience.md) define the implemented execution/report/artifact/bundle/job contracts. Written contracts are authoritative where no JSON Schema exists.

After every release update, user agents must reread the current object/schema documentation and implemented schemas, regardless of diffs or previous reading, following the [mandatory release reading list](../docs/skill-updates.md#required-schema-reread-after-a-release-update). No reading-completion verification or receipt is required.

Implemented inventory and result formats preserve host identity, collection time, source, tool version, status, and units where relevant.

Observations, unknown values, and AI interpretations remain distinguishable. The inventory-system result schema 0.2.0 is defined in [schema.json](../recipes/system/inventory/overview/schema.json). [Retained inventory observation 0.1.0](retained-observation.schema.json) and [JSON exchange 0.1.0](observation-exchange.schema.json) are implemented. Recipe-owned structured and portable contracts are described in the retention and portability guides.

See the [result-data workflow](../docs/result-data.md) for stage separation, SQLite storage, extraction, identity, replay, export and combination. JSON Schemas describe structure; the tool also checks semantic identity relations, ordering/state constraints and duplicate/conflicting IDs. A schema is not publisher authentication. Receiver analysis storage remains user-selected.

[Inventory-values 0.1.0](inventory-values.schema.json) defines nullable system/hardware/storage/network/software/services sections. Raw and retained schemas accept this optional extension with inventory_contract_version; retained records also require collection_scope. Older records remain valid, while strict consumers must update before accepting extended records. See [access, data semantics, CSV and migration](../docs/inventory-access.md). CSV is an inspection format with empty missing cells, not the JSON exchange contract.

## Observation execution run contract

[observation-run.schema.json](observation-run.schema.json) defines explicit batch membership, per-host outcomes, major job categories, source record/baseline links and saved Attention policy/findings. It is independent of recipe data contracts and ordinary retention selection/export. [Run lifecycle/storage/read APIs](../docs/observation-runs.md) define semantic validation and immutable completed collection snapshots beyond JSON Schema. Optional selection preserves invocation selectors/exclusions; optional execution joins the latest separately journaled command receipt. Its success/failure and exit_code are distinct from collection status. Absent historical metadata remains unknown. Retention event/consumer schemas also accept retention.run.updated, whose record_id identifies a run rather than an observation.

[result-diagnosis.schema.json](result-diagnosis.schema.json) defines read-only saved-result diagnosis projection 0.1.0: selected failure evidence with bounded excerpts and explicit issue/omission counts. It is independent of raw execution and retained-data contracts. See [selection, exit codes and interpretation limits](../docs/cli.md#diagnose-a-saved-failure).

[observation-view.schema.json](observation-view.schema.json) defines compact batch index/host views 0.2.0 for the top-level observation CLI. This projection separates whole-batch collection/result counts, effective result_status, nullable actor/access/content evidence and exact raw Result ID links independently of full observation-run objects. See [CLI and checkout helper semantics](../docs/cli.md#revisit-an-observation-batch).

## Portable units and recipe-carried data

[portable-data-unit.schema.json](portable-data-unit.schema.json) defines independent observation and retention units with original identity, payload, attachments and context. [data-package.schema.json](data-package.schema.json) defines their package manifest. [portable-retention.schema.json](portable-retention.schema.json) defines a recipe-owned data declaration using the supported offline schema dialect. [retention-snapshot.schema.json](retention-snapshot.schema.json) preserves that definition for later data-only validation. Follow [portable authoring](../docs/portable-contracts.md) and [transfer/import/archive plans](../docs/portability.md); archive selection, protected operations, recovery and source deletion require runtime checks beyond schema validation. Recipe bundles use the separately documented 0.2.0 contract.

## Recipe assessments and execution identity

[recipe-assessment.schema.json](recipe-assessment.schema.json) defines optional label, severity and summary separately from fixed execution status. [recipe-execution.schema.json](recipe-execution.schema.json) describes partial operator policy; effective inherited su/sudo policies require an explicit target. [recipe-execution-evidence.schema.json](recipe-execution-evidence.schema.json) preserves verified login/actual identities and restoration evidence. Retained envelopes, batch targets and compact observation views reference the applicable metadata contracts. Read [results and accounts](../docs/recipe-results-and-accounts.md) for configuration, failure precedence and verification limits.

*Last modified: 2026-10-26 12:19:58*
