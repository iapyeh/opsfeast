# Storage capacity

Recipe `system/inventory/storage-capacity` **0.1.0**, Python-routines **0.1.0**. This is an independently
runnable collection recipe and a member of the [Overview meal](../overview/README.md).
It calls the shared reviewed `opsfeast.inventory.service` collector; it never
owns a connection, escalates privilege itself or dispatches consumers in its body.

## Scope and execution

- Existing collection job: `storage-capacity`; 13 declared properties.
- Target queries are bounded, read-only and selected by platform. Missing tools,
  unsupported sources and denied access remain explicit gaps, never successful zeros.
- Root routines: none. Actual identity is verified by the runner.
  A root-only routine never runs under a login actor when root acquisition fails.
- Synthetic control/data tests exist; native SSH/sudo/platform execution for this
  split recipe has not been established. Platform declarations describe code coverage,
  not a complete inventory or verified target prerequisites.

```sh
python -B tools/opsfeast.py inspect-recipe system/inventory/storage-capacity --json
python -B tools/opsfeast.py recipes run system/inventory/storage-capacity --profile main --host node --json
```

The first command is read-only discovery. The second requires the human's target,
connection/privilege and configured consumer authorization. No packages are installed.
For a no-store query or selected fields, use `inventory query --recipe system/inventory/storage-capacity
--host node --property PROPERTY --json`; add `--save` only to retain it. Standalone
and composed execution use the same host-level executor. Selecting this recipe
explicitly selects its fields; hardware sensors still stay outside the default
Overview meal.

## Options and retained results

Profile/default/group/host recipe vars apply to this **exact reference**. Inputs:
`command_timeout_seconds` (positive per-command limit), `collection_budget_seconds`
(positive per-recipe budget) and `attention` (the existing typed inventory policy).
Invocation values override configured values. The runner rejects unknown variables
before connecting. No secret values belong in generated output.

Each recipe saves its own raw result and `inventory-routine-observations` **0.1.0**
retention, with original source times, property definitions, namespace/Host ID,
per-routine permission/actor/status, connection restoration and cleanup evidence.
Collection, retention and consumer delivery have independent receipts. A meal links
these records; it does not create an anonymous duplicate Overview observation.
Reading retained data or rebuilding consumers never reconnects to hosts.

## Fields

- `storage.filesystems.total_bytes`
- `storage.filesystems.used_bytes`
- `storage.filesystems.available_bytes`
- `storage.filesystems.used_percent`
- `storage.filesystems.total_megabytes`
- `storage.filesystems.used_megabytes`
- `storage.filesystems.available_megabytes`
- `storage.inodes.total`
- `storage.inodes.used`
- `storage.inodes.available`
- `storage.swap.total_bytes`
- `storage.swap.used_bytes`
- `storage.swap.available_bytes`

See [routine contract and execution](../../../../docs/recipe-routines.md),
[inventory jobs/schedules](../../../../docs/inventory-jobs.md),
[retention](../../../../docs/retention.md) and [Web selection](../../../../docs/web-recipe-menu.md).

*Last modified: 2026-11-10 12:27:11*
