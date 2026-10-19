# Retention consumers 0.1.0

A consumer is a reviewed local program that reacts to retained-data changes. It can render Vault Markdown, rebuild an index, combine recipe datasets or update another local application. Recipe creators keep ownership of retention definitions. Consumers declare their input dependencies independently; adding a consumer requires no edits to the recipe or runner.

## Discover the relation to a recipe

```sh
python -B tools/opsfeast.py recipes show inventory/system --profile main --json
python -B tools/opsfeast.py consumers list --recipe inventory/system --profile main --json
python -B tools/opsfeast.py consumers show vault --profile main --json
python -B tools/opsfeast.py consumers inspect --profile main --json
```

`recipes show` includes `consumers` with ID, source, registration, effective enabled state and static validation errors. `consumers list --recipe` resolves the recipe through the existing catalog, then matches its exact source-qualified reference and declared retention contract/version. The bundled reference is `inventory/system`; profile recipes use `:inventory/system`, and registered sources use `company:inventory/system`. A contract-only subscription can consume compatible definitions from multiple sources. Unknown recipe references fail explicitly. A missing consumer descriptor is reported as unavailable; it does not imply that no dependency exists.

List/show inspect descriptors and entrypoint bytes without importing candidate programs, creating directories or connecting. They distinguish unregistered candidates from enabled registrations. Inspection is static evidence; Python dependencies, historical output quality and execution safety require review. `consumers inspect [ID]` reads the durable event/delivery journal without writing. Its top-level success means the inspection succeeded; inspect individual delivery statuses for failures. An empty delivery list means no attempt has been recorded, including events without matching enabled subscribers.

All commands accept mutually exclusive `--root PROFILE_ROOT` and `--profile NAME`, plus `--json`; stdout is always JSON, including in terminals. Exit 0 means successful inspection/dispatch, 1 configuration, storage or delivery failure, 2 argument parsing error. `list`/`show` may use `--recipe`; `show` requires an ID. `dispatch [ID]` and `inspect [ID]` optionally select a consumer. Unknown IDs fail for show/dispatch; inspect can return an empty selection.

## Source layout and explicit activation

```text
<checkout>/consumers/vault/              # shipped implementation
<profile-root>/consumers/inventory-dashboard/
  consumer.yaml
  main.py
  README.md
```

Only immediate child directories containing `consumer.yaml` are discovered. Use unique consumer IDs. A shipped consumer uses `builtin:NAME`; a Feast-local consumer uses `local:consumers/NAME`. Arbitrary external paths, symlinked sources/entrypoints and entrypoints escaping their source directory are refused. Installation/download and execution remain separate scopes. Discovery alone never authorizes execution.

Enable a reviewed local program in `<profile-root>/feast.yaml`:

```yaml
schema_version: 1
kind: opsfeast
namespace: production
consumers:
  vault:
    source: builtin:vault
    enabled: true
  inventory-dashboard:
    source: local:consumers/inventory-dashboard
    enabled: true
```

Each registration requires exactly `source` and Boolean `enabled`. The registration key must match the descriptor ID, and one source can have only one registration. IDs/directory names start with a lowercase letter followed by lowercase letters, digits, underscores or hyphens, maximum 63 characters. Registration authorizes the reviewed program to run during subsequent writes/replays or explicit dispatch; review its dependencies, inputs, output paths and side effects before enabling it. Consumer programs execute with the controller's Python privileges. This is not a sandbox or an independent approval-verification system.

The shipped `vault` registration defaults to enabled. Other shipped/local consumers require explicit registration. `consumers.vault.enabled: false` disables automatic Vault delivery. The existing `vault.auto_refresh: false` also disables that consumer and does not disable other consumers. Explicit `vault rebuild` remains available. Profile initialization bootstraps only the shipped Vault landing content when enabled; it never invokes local consumer code.

## Consumer descriptor and Python interface

The [descriptor schema](../schemas/retention-consumer.schema.json) defines the complete 0.1.0 descriptor:

```yaml
schema_version: "0.1.0"
id: inventory-dashboard
description: Rebuild the local inventory dashboard from retained system observations.
entrypoint: main.py
subscriptions:
  - event: retention.observation.created
    selector:
      recipe_reference: inventory/system
      contract: inventory-observations
      version: "0.1.0"
  - event: retention.observation.deleted
    selector:
      recipe_reference: inventory/system
      contract: inventory-observations
      version: "0.1.0"
```

All five top-level fields are required; unknown fields fail validation. `entrypoint` names a relative `.py` file. `subscriptions` is a nonempty list. Each subscription requires `event` and `selector`; permitted events are `retention.observation.created`, `retention.observation.deleted` and `retention.operation.created`. The selector permits only `recipe_reference`, `contract` and `version`, each an exact nonempty string. Contract/version must appear together. `{}` selects all events of that type. Conditions within a subscription are AND; multiple subscriptions are OR and do not duplicate a delivery. Operation events have null contract/version and can be selected by recipe reference or an empty selector.

The selected Python must be 3.11+ with the normal OpsFeast initialization dependencies. Declare any consumer-specific dependencies and supported data versions in its README and verify availability in the selected environment; the dispatcher does not install packages. It imports the registered entrypoint and invokes:

```python
def execute(context):
    # Rebuild from current retained state; handles duplicate and deletion hints.
    selection = context.retention.query(
        recipe="inventory/system", kind="observation"
    )
    # Render selection into this consumer's reviewed output location.
    # Preserve partial/unknown states, source times and identity warnings.
    return {"status": "success", "records": len(selection["records"])}
```

`context.root` is the selected profile's absolute Path. `context.event` is a copy of the event envelope. `context.retention.query/show` is the existing read-only retention facade. It supports the same filters and schemas as [retention queries](retention.md#discover-and-read-data). Use this facade instead of parsing raw files or generating SQL storage code. Relative helper imports such as `from .render import build` are supported; only the reviewed entrypoint is automatically called. Do not print to stdout, mutate process-wide state, start background work, connect or transmit without the user's corresponding authorization. No consumer-specific configuration/input-variable mechanism is implemented in 0.1.0; private application settings belong in reviewed local configuration.

Return a JSON-serializable object with `status: success|failed|skipped`, plus useful safe result details. Success and skipped acknowledge the event. Failed returns and ordinary exceptions remain retryable; exception text is omitted and only its type is recorded. Do not put secrets in returned diagnostics. There is no enforced timeout, resource quota, process isolation or remote-delivery service; consumers must finish synchronously and impose their own bounded work. Interrupted execution can leave a running receipt that will retry. Recursive dispatch in the same thread/profile is refused; consumers should read retention and write derived outputs, not create feedback loops through retention writes.

## Durable event and delivery semantics

Record insertion and its event are committed together in the same authoritative annual SQLite database. Data projections and consumer outputs are subsequent phases. Identical record replay does not create a new event. Deletion writes a metadata tombstone in the same transaction that removes each observation; protected write/unknown and operation evidence remains protected. Reinsert after deletion creates a new event ID even for the same record ID.

The [event schema](../schemas/retention-event.schema.json) includes contract version, UUID event ID, event name, emission time, record ID, namespace, host ID, exact recipe reference, data contract/version and original observation time. Contract/version are null for records without a declaration. Events carry metadata only; they are change hints, not data snapshots. A queued creation event can refer to an already-deleted record. Consumers must query current state or handle a missing record explicitly; do not reconstruct deleted business data from the journal.

The authoritative annual databases additionally contain:

| Table | Columns and meaning |
| --- | --- |
| `retention_events` | `event_id` primary key, `emitted_at`, canonical JSON `payload` |
| `consumer_deliveries` | Primary key `(event_id, consumer)`; consumer identity is `ID@SOURCE`; `status`, integer `attempts`, canonical JSON `payload` |

The record schema remains SQLite `user_version=1`; event payloads use their separate 0.1.0 contract. Event/delivery tables belong to the annual archives and are not copied into rebuildable cumulative/recent projections. Never independently edit these tables. Event/delivery history is retained after observation deletion; tombstones and receipts must not contain deleted business values. No journal pruning command is implemented.

Dispatch orders events by controller UTC emission time, then event ID; this is deterministic ordering, not an independently verified causal order across writers. Delivery is serialized per profile with `.consumers.lock`. The retention lock is released before invoking a consumer, so program failure does not roll back committed data. Each consumer/event pair has a durable running attempt followed by success, skipped or failed. Successful/skipped pairs are not invoked again. Other consumers and later events continue after an ordinary program failure. A failed event can therefore be retried after a later event succeeded; do not assume successful processing is strictly ordered. A crash after an output write and before acknowledgement can repeat the output action: this is **at-least-once delivery**, not exactly once. Make output replacement idempotent, or use `event_id` in the destination's own transactional deduplication.

Subscriptions and enabled registrations are evaluated at dispatch time. Disabled/unregistered consumers leave their events unacknowledged. Later activation processes all matching events still in this journal, including events emitted before registration. A changed source is a new delivery identity; changing code/subscriptions under the same ID/source does not reset prior success acknowledgements. The receipt records a SHA-256 over descriptor and entrypoint bytes for diagnosis, not publisher authentication or a digest of imported helpers/dependencies. No automatic reinstall, source-version pin or full-output rebuild is inferred from an edit.

## Runner, replay and recovery

All shared retention saves create events, including runner collection, local ingest and explicit standalone saves. Intent/outcome journaling defers dispatch until the runner has completed its data writes. Deletion also dispatches after committing. A dry-run and `retention rebuild` emit no events and execute no consumers. Standalone programs using `save(..., refresh=False)` must call `retention_store.refresh_content(root)` after their write batch, or use explicit dispatch later.

The existing `content_update` receipt is now an aggregate consumer-dispatch receipt with `contract_version`, overall status, `consumers` attempt receipts and a recovery command. It no longer has the old single-Vault result shape. Runner saves it separately from `retention`; both remain excluded from raw-data identity/digest. Inspect each attempt's consumer/source/event/record IDs, status, attempts, implementation SHA-256 and completion time. A dispatch with no pending enabled matches succeeds with an empty attempt list. It does not mean that disabled consumers are current or all historical content was rebuilt. A consumer failure preserves recipe/retention results but causes a nonzero runner/replay CLI exit. Receipt-writing/storage failures can interrupt dispatch and leave running/pending attempts; retry after repairing storage.

```sh
python -B tools/opsfeast.py consumers inspect --profile main --json
python -B tools/opsfeast.py consumers dispatch --profile main --json
python -B tools/opsfeast.py consumers dispatch inventory-dashboard --profile main --json
python -B tools/opsfeast.py vault rebuild --profile main --json
```

Dispatch retries outstanding running/failed attempts and processes pending matching events. It does not rerun recipes, reconnect or recreate already-acknowledged outputs. `vault rebuild` explicitly regenerates all current Vault content even when no event is pending; it does not acknowledge consumer deliveries. If data projection rebuilding failed after the annual commit, repair with `retention rebuild`, then dispatch. Raw replay deduplicates a stored record and can also retry its pending deliveries.

Existing annual records from before this feature have no events. No event backfill or migration is performed, and existing data/human notes are preserved. Replaying an identical already-stored record still does not create a new event. Use each application's explicit rebuild/current-state reader to initialize historical outputs; use `vault rebuild` for Vault. Consumers appear automatically in static discovery but require explicit activation to run. These are development-stage interface changes; callers reading the old `content_update` fields must update to per-consumer receipts.

## Checkout module interfaces and verification

The checkout-level `retention_consumers.catalog(root, recipe=None)`, `related(root, reference, declaration=None)`, `inspect_deliveries(root, consumer=None)` and `dispatch(root, consumer=None)` back the CLI. Import them from the trusted checkout's `tools/` path; installed OpsFeast exposes that bundled path through its normal package import. These are documented checkout interfaces, not new Core SDK methods. `enqueue`, `bootstrap`, locks and tables are internal integration helpers. Consumers use `ConsumerContext` and its retention reader, not these internal helpers.

The bundled [Vault consumer](../consumers/vault/README.md) delegates full local rebuilds to `host_vault`, whose renderer remains `vault_content`. Local synthetic tests cover discovery without imports, exact source/contract/version matching, deduplication, disabled backlog, durable rollback/crash recovery, independent failures/retries, deletion/reinsertion, concurrent dispatch, CLI and operation events. They do not establish native SSH/su/sudo, external delivery, application-specific idempotency or live network/cloud filesystem safety. No scheduler or daemon automatically wakes pending work; dispatch occurs on the next shared write/replay or explicit command.

_Last modified: 2026-10-19 14:57:27_
