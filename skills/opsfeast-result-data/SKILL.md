---
name: opsfeast-result-data
description: Interpret and recover OpsFeast retained observations, prepare selected JSON exchanges, validate or combine shared data, and guide recipient-selected analysis without exposing raw execution details.
---

# OpsFeast result data

Start with the [central skill index](../README.md). Keep newly authored Feast-specific skills in the selected management root's `skills/`; check task-relevant source/loaded copies and agree with the user on any naming, version, instruction or loader conflict before the affected action. Follow [storage and conflict resolution](../../docs/agent-guidance.md#skill-storage-and-conflict-resolution).

Read the repository AGENTS.md, [CLI reference](../../docs/cli.md#retained-observations-and-exchange) and [canonical workflow and capability contract](../../docs/result-data.md). Use the [recipe skill](../opsfeast-recipes/SKILL.md) for authorized execution. This skill and its linked guides/schemas must be distributed together; automatic skill loading is not required.

General Python-session recipe results are raw JSON with explicit no_retention_adapter; this skill's inventory recovery/exchange contracts do not ingest them. See [general results](../../docs/recipe-execution.md#results-failure-states-and-storage).

## Available capability catalog

| Capability | Interface/version | Availability and limits |
| --- | --- | --- |
| Automatic retained inventory | run_recipe.py → inventory-system-v1, retained 0.1.0 | Raw result 0.2.0, operational local/SSH success/partial; SQLite via Python standard library |
| Recovery | observation_store.py ingest FILE... | Explicit local raw files in their originating Feast; no host connection |
| Shareable export | observation_store.py export | JSON exchange 0.1.0, recipe/host/time selection; no transmission |
| Static exchange validation | observation_store.py validate FILE | Strict record/envelope checking; no database/profile required |
| Exchange combination | observation_store.py combine FILE... | Validated union and ID deduplication; conflicts fail; no host reconciliation |
| Recipient analysis | User-provided tool/script | Published schema; no bundled stage-4 database importer or charts |

Check the selected interpreter, available tool files and chosen profile/root first. Setup does not authorize collection or sudo. Reading/exporting existing data does not authorize sending it to others. Do not read hosts.yaml credentials merely to process retained results. A missing retained database is not a successful empty inventory; propose ingestion of specifically identified local results or authorized collection as appropriate.

## Follow the four-stage workflow

1. Explain that raw execution evidence, retained observations, exchange data and analysis storage have independent contracts. Read the relevant result/retained/exchange schemas, not thousands of raw files, to choose a workflow.
2. After authorized recipe execution, inspect collection status **and** retention receipt. Runner automatically attempts stage 1 → 2. Failed/skipped/unsupported/mock results are excluded; partial retains null states. A zero exit requires complete collection and no retention failure. Source-disabled/host-disabled paths may have no report.
3. If retention failed, identify the raw result_path and retry `python -B tools/observation_store.py ingest /absolute/raw.json --profile NAME`. Explain that replay performs no remote work. Inspect stored/already_stored/skipped results and database errors; do not silently change raw files, delete the database or re-run remote operations. Backup/recovery requires its own concrete scope.
4. For sharing, determine the intended recipe, local hosts, completion-time interval and destination from the user's request. Use export with explicit filters where appropriate; absence of filters exports all retained data. Explain that device IDs and hostnames may be included. Export to a new reviewed file, validate it, confirm record count/selection and inspect for unexpected fields. Sending remains separately authorized; there is no transmission tool in this capability.
5. For A/B data, validate each received exchange before combining. Use combine to remove identical observation IDs and reject conflicting content. Preserve all different observations; equal host keys do not authorize collapsing history. Do not ingest foreign raw data as local observations.
6. For recipient analysis, inspect the exchange contract and choose the user's requested store/tool. Preserve IDs, timezones, statuses and identity quality. A missing OpsFeast importer does not block a feasible user-authorized script; report missing dependencies and test transformations with synthetic data. Do not invent a bundled import command.

## Handle identity honestly

Host means OS installation: reinstalling/changing the OS is a different host, even on the same equipment. Rotate user-assigned identity_key after reinstall/replacement; inability to detect a preserved native identifier or fallback continuity is a limitation, not an exception to this definition. IP/hostname are mutable; hardware serial/UUID links equipment and cannot detect reinstall. Linux uses an application-specific machine-id HMAC digest as a candidate, with clone/reinstall caveats. FreeBSD/macOS/ESXi currently use fallback installation identity even if hardware probes succeed. Inspect raw identity.evidence only when investigating a concrete identity problem, and keep raw execution details local.

Fallback keys namespace local host_id by source Feast UUID. They permit local history but cannot prove continuity after target replacement or cross-source equality. Read/relay identity_warning and give a concrete remedy according to probe state. Supplied explicit sudo credentials enable missing fixed probes; identity_sudo false disables, true also supports authorized passwordless sudo. A login password alone does not opt in. Do not promise elevation resolves missing OS-identity contracts. No target installation marker is written.

Matching machine-derived keys are evidence, not uniqueness proof. Compare device evidence for contradictions and preserve unresolved conflicts. Do not auto-merge fallback identities, rename keys, assign all old observations to newly discovered identities, or equate lack of a new record with a host disappearing. Reviewed historical aliases and organization-wide asset mapping are not implemented.

## Maintenance and extension

Contract versions and database physical version are distinct. Never mutate schema ad hoc. New recipes need a trusted adapter, versioned retained/transfer contracts, failure and partial rules, tests and discoverable recipe capability references. No arbitrary third-party adapter is executed by ingest/validate/combine. Real sudo/SSH/ESXi support remains unverified beyond documented interfaces and synthetic tests. Preserve human records, source databases and unrelated files; retention deletion/transport/authentication remain separate operations.

Host identity_key, label and description are now supported. An explicit identity_key takes precedence and is shared across Feasts as user-assigned identity; change it after OS reinstall/replacement and coordinate its namespace. label/description are captured human text, never identity keys, and are preserved through retention/exchange. See [the canonical host configuration](../../docs/hosts-yaml.md#explicit-host-identity-and-human-readable-metadata) and [identity/metadata rules](../../docs/result-data.md#explicit-identity-and-display-metadata). MAC is not an automatic key.

_Last modified: 2026-10-13_
