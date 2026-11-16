# 8. Consumers, notifications and todos

[Book home](README.md) · Previous: [Data and Vault](07-data-and-vault.md) · Next: [Reports](09-reports-and-reuse.md)

Retention consumers turn stored evidence into useful downstream work. Services preserve the lifecycle of findings and planned work. Delivery adapters handle presentation and external transport. Collection, consumer completion and message delivery can each succeed or fail independently.

## Discover without activating

```sh
python -B tools/opsfeast.py consumers list --recipe system/inventory/overview --profile main --json
python -B tools/opsfeast.py consumers inspect --profile main --json
python -B tools/opsfeast.py services inspect --profile main --json
```

These inspect available/configured programs, receipts and service availability without sending mail. Static inspection does not execute candidate programs or prove provider credentials. Review implementation, supported data contracts, dependencies, output ownership and side effects before activation in `feast.yaml`.

The bundled Vault consumer is enabled by default. Additional consumers require explicit reviewed registration. Merely packaging a consumer with a recipe does not activate it. The backup policy is a separate consumer, not an implicit part of collecting backup metadata.

## Understand consumer recovery

Consumers process durable events with per-event receipts and retry history. Programs must tolerate repeated delivery and stale hints; an event is a reason to examine authoritative data, not proof that the hinted record is still current. The Vault consumer can batch publication while keeping individual receipts.

After identifying a failed consumer and reviewing its effects, an authorized retry might be:

```sh
python -B tools/opsfeast.py consumers dispatch vault --profile main --json
```

Dispatch runs configured code. Retention-consumer dispatch also attempts configured service dispatch, which can send mail when routes exist. Therefore even retrying a content consumer requires knowing current service configuration and authorized delivery scope. A targeted `vault rebuild` is useful when only bundled content needs repair, but does not acknowledge pending events.

## Separate findings from messages and work

A policy identifies a condition using host, exact recipe reference, subject and rule. Persistent adverse evidence updates the same episode. Verified clearance resolves it; a later recurrence creates a new episode. Unknown or incomplete evidence must not falsely clear an existing problem.

Notifications have active/resolved condition state, with independent read and acknowledgement state. Todos have `open`, `in_progress`, `blocked`, `done` and `cancelled` states. A todo is a record of intended work: assigning it or setting a date does not execute commands, delete files, install a scheduler or wake an agent.

Only eligible live collection evidence can create incidents through consumer services. Historical replay/import does not become a fresh current incident. Do not change timestamps or bypass the consumer facade to manufacture live effects.

## Review and update a todo

```sh
python -B tools/opsfeast.py services list --kind todo --profile main --json
python -B tools/opsfeast.py services show OBJECT_ID --kind todo --profile main --json
python -B tools/opsfeast.py services history OBJECT_ID --profile main --json
```

These are reads. To assign work or add a note, first read its current revision. An example authorized mutation, using the returned revision in place of `3`, is:

```sh
python -B tools/opsfeast.py services update OBJECT_ID --kind todo --revision 3 --actor operator --changes '{"status":"in_progress","assignee":"operator","note":"Review the saved file list before proposing cleanup."}' --profile main --json
```

A stale revision fails rather than overwriting another update. Reload and review the intervening change before retrying. Due/start/mute times need offsets and appropriate timezone interpretation. Human assignment and notes survive policy reconciliation. Marking a todo done while the adverse condition persists is unverified; later adverse evidence can reopen it. Editing generated Markdown does not update the service object.

## Publish and deliver within scope

```sh
python -B tools/opsfeast.py services deliveries --profile main --json
```

This reads outbox status. Authorized `services dispatch` invokes configured presentations and delivery adapters. Direct object updates do not automatically republish. Default configuration supplies Vault presentation without delivery routes; review the actual configuration before assuming dispatch is local-only.

Delivery states include pending, sending, delivered, failed, unknown and cancelled. Unknown delivery may mean a message was sent but confirmation was lost. `--retry-unknown` is an explicit decision that can duplicate delivery. Read/acknowledged state does not prove a provider delivered anything, and stable IDs do not guarantee exactly-once SMTP delivery.

Agent prompt:

> Inspect unresolved backup todos and notification delivery state in profile main without dispatching. Explain each condition's evidence, current revision, latest observation time and uncertainty. Prepare any requested lifecycle update using the current revision. Do not treat the todo as authorization to remove files.

**Checkpoint:** Explain whether the problem is a finding, an unfinished consumer, a stale presentation or an uncertain delivery. Locate the original evidence before deciding how to recover.

Canonical guidance: [consumer contract](../../retention-consumers.md), [consumer catalog](../../../consumers/README.md), [services](../../services.md), [adapters](../../service-adapters.md), and [backup policy](../../../consumers/backup-check/README.md).

*Last modified: 2026-10-26 12:55:26*
