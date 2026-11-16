# 10. Author, share, transfer and archive

[Book home](README.md) · Previous: [Reports](09-reports-and-reuse.md) · Next: [Backup case](11-backup-case.md)

Reusable operations and their evidence have independent lifecycles. A receiver may need a recipe without your private settings, or historical data without installing its producer. Archiving needs a verified recoverable package before source cleanup.

## Choose the unit you mean

| Unit | What it preserves | What it does not imply |
| --- | --- | --- |
| Recipe bundle | Reviewed executable knowledge, schema, documentation, helpers and licensing | Credentials, receiver bindings, consumer activation or execution permission |
| Observation package | Original execution evidence and declared attachments | A newly executed local batch or fresh observations |
| Retention package | Structured data, definitions and provenance | Re-running a producer or making old evidence live |
| Operational Vault copy | Human-readable files and selected notes | Complete authoritative history or service lifecycle backup |

Notification/todo lifecycle, provider configuration and human notes are separate resources. Data export is a local copy, not permission to transmit. Review selected payloads for sensitive evidence even when filenames look safe.

## Create a reusable recipe

Before writing, ask the agent to discover suitable tools through the [capability map](../../agent-capabilities.md) and [recipe skill](../../../skills/opsfeast-recipes/SKILL.md). New user-specific recipes normally belong under the actual profile root's `recipes/<domain>/<subdomains>/<action>/<name>/`; shared code can use an explicitly registered external source. Do not edit bundled product recipes merely to bind one user's hosts.

An author should deliver a descriptor, complete implementation, typed configuration, data definition, human/agent guide, attribution/license, synthetic examples and reproducible tests. Declare target/dependency/privilege/effect limits. Preserve unknown and partial states, and use existing connection, retention, service and artifact APIs rather than recreating framework plumbing. Prefer SSHScript for suitable execution/session orchestration; document concrete reasons when another tool better fits.

Registered bundled contracts remain usable. For new portable structured data, recipe-carried schemas avoid adding a product registry entry for every domain. Read the [portable schema dialect](../../portable-contracts.md); do not assume every JSON Schema feature or remote reference is supported.

## Package and review source

Recipe bundle 0.2.0 requires an explicit file allowlist. The example assumes an existing reviewed user recipe at `:example`:

```sh
python -B tools/opsfeast.py recipes pack :example --file recipe.yaml --file main.py --file README.md --file LICENSE --output /destination/example.zip --profile main
```

Add every required helper, schema, asset, template and optional consumer. Pack emits JSON directly and does not accept a `--json` flag. It does not infer dynamic dependencies or sanitize arbitrary file contents. A digest establishes consistency, not publisher authenticity. Review origin, license, implementation and requested effects on acquisition. Old bundle 0.1.0 is rejected; recreate it using the current format.

Plan installation into a receiver's profile-local recipe tree:

```sh
python -B tools/opsfeast.py transfer recipe-plan --package /incoming/example.zip --path example --profile main --json
```

This inspects the package and target without activating code. Resolve conflicts explicitly: another path keeps both trees; `--resolution replace` requests replacement; skip preserves the existing tree. Version numbers alone never authorize overwrite. Private exact-reference settings, jobs and subscriptions do not automatically rebind to a new path.

Only after reviewing the current plan and authorizing installation:

```sh
python -B tools/opsfeast.py transfer recipe-install --package /incoming/example.zip --path example --plan PLAN_SHA256 --profile main --json
```

Use matching resolution options from the plan. Dependency checks are static, not proof of host applicability or a dependency installer. Preserve the returned receipt; replacement has reviewed rollback plans, and later edits can block rollback instead of being overwritten. Optional consumer source still requires separate reviewed placement and activation.

## Copy or import saved data

```sh
python -B tools/opsfeast.py transfer list --kind retention --profile main --json
python -B tools/opsfeast.py transfer show UNIT_ID --profile main --json
python -B tools/opsfeast.py transfer export --kind retention --id UNIT_ID --output /destination/retained-data.zip --profile main --json
```

List/show are reads. Export creates a new local package without removing or transmitting the source. Use an observation selection when you need raw evidence, or both kinds when needed. Preserve source times, origin identities and attachments.

On the receiver:

```sh
python -B tools/opsfeast.py transfer import-plan --package /incoming/retained-data.zip --mode merge --profile main --json
python -B tools/opsfeast.py transfer import --package /incoming/retained-data.zip --mode merge --plan PLAN_SHA256 --profile main --json
```

The first command inspects; the second mutates local storage using the reviewed current plan. Merge adds new identities, skips identical content and rejects conflicting content. Replace affects colliding identities included in the package, preserving unrelated data; it is not “clear the profile.” Recompute plans after package/target changes.

Import preserves origins, validates saved data without executing candidate recipes/consumers/providers, and does not create fresh incidents. Imported units live in `transfer/space.sqlite3`; reads expose origin-qualified retained records. Recovery receipts and before-image packages consume space intentionally. Use the documented import recovery plan if interrupted, not manual SQLite changes.

## Archive to reclaim active storage

An archive plan writes a small local frozen selection; it is not entirely read-only. After choosing an authorized external destination and cutoff:

```sh
python -B tools/opsfeast.py transfer archive-plan --kind observation --older-than 90 --output /external/archive/observations.zip --profile main --json
```

Review exact membership, original-time cutoff, protected evidence, destination and planned removal. Apply only the reviewed plan:

```sh
python -B tools/opsfeast.py transfer archive --output /external/archive/observations.zip --plan PLAN_SHA256 --profile main --json
```

The destination must resolve outside the active profile; use another filesystem if you intend to free the source filesystem. Apply writes and verifies the archive before deleting selected source material, compacts SQLite, repairs bundled data-only views and records progress. It does not invoke custom consumers/adapters, send mail or delete human notes/service objects. Protected operation evidence and shared attachments impose explicit limits.

If interrupted, inspect `transfer receipts`, then use `transfer resume ARCHIVE_RECEIPT_ID` with the same profile. Resume verifies the archive and remaining fingerprints. Preserve the verified package and receipts. Restore by reviewed import of the archive; do not emulate archive by exporting and manually unlinking raw files. Raw and retention can be archived independently, so state exactly which evidence remains active.

Agent prompt:

> Prepare an archive plan for completed observations older than 90 days in profile main, using the external destination I specified. Explain selected counts, source-time cutoff, protected entries, remaining retention and recovery. Do not apply until the concrete source removal is authorized. Preserve all human notes and service lifecycle state.

**Checkpoint:** Explain the difference between packaging recipe code, exporting data, importing a collision and removing active source data through archive. Identify the recovery artifact before any deletion.

Canonical guidance: [portability](../../portability.md), [portable contracts](../../portable-contracts.md), [authoring](../../recipe-authoring.md), [sharing](../../recipe-sharing.md), and [acquisition review](../../recipe-acquisition.md).

*Last modified: 2026-10-26 12:55:26*
