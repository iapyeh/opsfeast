# Schemas

This directory will define versioned data contracts for host records, service relationships, observations, and recipe execution results.

The first milestone will establish the minimal inventory and result formats. They should retain host identity, collection time, source, tool version, status, and units where relevant.

Observations, unknown values, and AI interpretations should remain distinguishable. The inventory-system result schema 0.2.0 is defined in [schema.json](../recipes/inventory/system/schema.json). [Retained inventory observation 0.1.0](retained-observation.schema.json) and [JSON exchange 0.1.0](observation-exchange.schema.json) are now implemented. Other record contracts remain planned.

See the [result-data workflow](../docs/result-data.md) for stage separation, SQLite storage, extraction, identity, replay, export and combination. JSON Schemas describe structure; the tool also checks semantic identity relations, ordering/state constraints and duplicate/conflicting IDs. A schema is not publisher authentication. Receiver analysis storage remains user-selected.

_Last modified: 2026-10-13_
