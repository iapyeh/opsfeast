# Schemas

This directory will define versioned data contracts for host records, service relationships, observations, and recipe execution results.

For the current host configuration object, read [hosts.yaml](../docs/hosts-yaml.md); a standalone host JSON Schema is not implemented. [Core API](../docs/core-api.md) and [profiles](../docs/profiles.md) define installation/profile and runtime objects; [recipe execution](../docs/recipe-execution.md) and [recipe experience](../docs/recipe-experience.md) define the implemented execution/report/artifact/bundle/job contracts. Written contracts are authoritative where no JSON Schema exists.

After every release update, user agents must reread the current object/schema documentation and implemented schemas, regardless of diffs or previous reading, following the [mandatory release reading list](../docs/skill-updates.md#required-schema-reread-after-a-release-update). No reading-completion verification or receipt is required.

The first milestone will establish the minimal inventory and result formats. They should retain host identity, collection time, source, tool version, status, and units where relevant.

Observations, unknown values, and AI interpretations should remain distinguishable. The inventory-system result schema 0.2.0 is defined in [schema.json](../recipes/inventory/system/schema.json). [Retained inventory observation 0.1.0](retained-observation.schema.json) and [JSON exchange 0.1.0](observation-exchange.schema.json) are now implemented. Other record contracts remain planned.

See the [result-data workflow](../docs/result-data.md) for stage separation, SQLite storage, extraction, identity, replay, export and combination. JSON Schemas describe structure; the tool also checks semantic identity relations, ordering/state constraints and duplicate/conflicting IDs. A schema is not publisher authentication. Receiver analysis storage remains user-selected.

[Inventory-values 0.1.0](inventory-values.schema.json) defines nullable system/hardware/storage/network/software/services sections. Raw and retained schemas accept this optional extension with inventory_contract_version; retained records also require collection_scope. Older records remain valid, while strict consumers must update before accepting extended records. See [access, data semantics, CSV and migration](../docs/inventory-access.md). CSV is an inspection format with empty missing cells, not the JSON exchange contract.

_Last modified: 2026-10-15_
