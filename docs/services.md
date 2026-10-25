# Notification and todo services 0.1.0

OpsFeast owns notification/todo data objects, condition identity, revision checks, audit history and lifecycle. Recipes and retention consumers use the same service. Presentation and delivery are adaptable; lifecycle is deliberately platform-owned. A todo records planned work; it never executes a command, deletes a file or wakes an agent.

Read [adapter configuration and interfaces](service-adapters.md) before enabling providers, and [backup checks](backup-file-checks.md) for a complete producer → retention → policy → service example. These are checkout/package APIs with service contract 0.1.0, controller Python 3.11+ and the normal OpsFeast dependencies. No extra dependency is needed for the bundled Vault or SMTP adapters. General logging, reminders, a todo executor and automatic service scheduling are not implemented.

## Discover availability without sending

```sh
python -B tools/opsfeast.py services inspect --profile main --json
python -B tools/opsfeast.py services list --kind todo --profile main --json
python -B tools/opsfeast.py services deliveries --profile main --json
```

`inspect` reads local configuration, object counts, initialization state, adapter source/digest availability and presentation receipts. It never imports local adapters, connects to providers or sends mail. Static availability does not establish provider credentials, native runtime readiness or delivery. Reads do not initialize the service database. Writes require a valid profile retention namespace in feast.yaml, established through the normal profile setup; otherwise they fail with services_require_namespace. Do not invent or replace an existing namespace to bypass this prerequisite. An absent services configuration provides the default Vault presentation, no delivery channels and no routes. Preserve existing `feast.yaml` keys when adding the optional `services` mapping.

## Shared Python interface

```python
from opsfeast import Instance

profile = Instance.open(installation="/path/to/opsfeast").profile("main")
services = profile.services
print(services.inspect())
print(services.todos.list(status="open"))
```

A python-recipe uses its supplied `recipe.services`; event and batch consumers use `context.services`. Recipe scope ends with the Recipe; do not retain the facade beyond execution. Use the consumer facade for event-driven effects: it enforces which evidence records may produce effects. Do not bypass it with a new unrestricted Profile/Services instance.

Create or update a condition from reviewed evidence:

```python
outcome = services.reconcile(
    source={"host_id": "backup-example", "recipe_reference": ":backup/files/check/daily-backups",
            "subject": "database-a", "rule": "daily-missing"},
    owner="backup-check", observed_at="2026-10-25T02:00:00+00:00",
    evidence={"record_id": "the-actual-retained-record-id"},
    active=True, title="Daily backup missing", body="The expected dated file is absent.",
    severity="error", notification=True, todo=False,
)
```

Supply real evidence IDs and source observation timestamps; the example does not itself authorize creation or sending. Source has exactly four nonempty strings: `host_id`, exact `recipe_reference`, `subject` and `rule`. They define a stable profile-local condition key. `owner` is the one policy implementation allowed to reconcile that key; a conflicting owner fails. Evidence requires `record_id`; additional JSON metadata can explain the finding. Severity is `info`, `warning`, `error` or `critical`.

`reconcile` returns a condition outcome, including ignored/suppressed outcomes, rather than a notification object. Optional arguments are `effects=True` and `recovery_notification=False`. `notifications.create(...)` and `todos.create(...)` accept source, owner, observed_at, evidence, title, body and optional severity, and reconcile an active condition for that kind. Use `reconcile` for recovery and uncertain observations. `notifications/todos.list(host=None, status=None)` and `.show(object_id)` return objects; `.update(object_id, expected_revision=..., actor=..., **changes)` returns the updated object. `services.history(object_id=None)`, `.deliveries()` and `.snapshot()` provide audit, outbox and coherent presentation inputs. `ServiceError` derives from `ConfigError` and exposes a safe `.code`; callers must handle configuration, ownership and revision failures explicitly.

## Conditions, deduplication and lifecycle

Observations are ordered by normalized UTC `(observed_at, record_id)`. Older or duplicate observations are ignored; the same evidence can supplement a missing object kind without creating a duplicate episode. Persistent adverse state updates the existing episode. A verified clear state resolves the condition; a later recurrence creates new episode objects. Notification status is `active` or `resolved`; read and acknowledgement are independent user state. Resolving cancels pending/failed deliveries. Optional recovery notification creation must be explicitly selected by the policy.

`active=None` advances the observation watermark while preserving the previous condition and objects. This prevents an uncertain or incomplete scan from falsely clearing a problem. `effects=False` can record condition state without creating objects. Historical replay/ingest through consumer services is suppressed with `historical_service_effects_disabled` and creates no objects. Only durable live-collection events from operational local/SSH results permit effects for their evidence IDs. Permission is recorded atomically with the retention event and survives retry; older events without that evidence remain ineligible. Replay is still useful for retained data and presentation. Do not convert old evidence into current incidents by changing its time.

Todo statuses are `open`, `in_progress`, `blocked`, `done` and `cancelled`. Open/in_progress/blocked can transition among themselves or to done/cancelled; done and cancelled can reopen to open. A manual completion while the adverse condition remains active is unverified; the next adverse observation reopens a done todo. Verified clearance marks a todo done, unless it was cancelled, and preserves human assignment, schedule and notes. Unknown state cannot verify completion.

## Revision-checked human updates

```sh
python -B tools/opsfeast.py services show OBJECT_ID --kind todo --profile main --json
python -B tools/opsfeast.py services update OBJECT_ID --kind todo --revision 3 --actor operator --changes '{"status":"in_progress","assignee":"operator","note":"Review the listed files before scheduling cleanup."}' --profile main --json
python -B tools/opsfeast.py services history OBJECT_ID --profile main --json
```

Read the current `revision`, then update with that exact value. A concurrent change fails instead of overwriting another writer; reload and review before retrying. Todo editable fields are `status`, `assignee`, `start_at`, `due_at`, `timezone`, `note` and `priority`. Notification editable fields are `read`, `acknowledged` and `muted_until`. Schedule/mute timestamps must include an offset; the object timezone defaults to UTC and can be updated to a valid IANA `timezone`, and due must not precede start. Timestamps normalize to UTC. Read/ack updates record actor and time. Muting postpones queued delivery; it does not resolve a condition. No recurring reminders or calendar integration are supplied.

## Storage, presentation and delivery outcomes

Authoritative state lives in `<profile-root>/services/objects.sqlite3`, with condition, object, history, delivery and projection records. The directory/file use restrictive permissions, path/symlink checks and transactional writes. Preserve it with its profile; editing generated Markdown never updates lifecycle state. Do not manipulate SQLite rows or copy only the Markdown as a service backup. No service deletion/import/export/migration CLI is provided.

```sh
python -B tools/opsfeast.py services dispatch --profile main --json
```

Dispatch explicitly invokes configured adapters: it publishes presentations and sends eligible notification outbox items. A retention consumer dispatch also attempts service dispatch, reported separately under `content_update.services`; collection, retention, consumer and service outcomes must be assessed separately. Direct API lifecycle mutations do not automatically republish. Todo priority uses info/warning/error/critical; assignee and note can be cleared with null, and start_at/due_at/muted_until accept null to clear them. Todo work is never executed by dispatch. External sending requires the user's corresponding authorization; enabling a delivery route affects later eligible events and explicit dispatches.

Delivery states are `pending`, `sending`, `delivered`, `failed`, `unknown` and `cancelled`. Failed items retry only when due and within adapter limits. Crashed/in-flight or uncertain items require explicit `services dispatch --retry-unknown`; that action may duplicate a message. Stable delivery IDs and SMTP Message-ID do not guarantee exactly-once delivery. Resolution prevents future retries, including after an in-flight failure. Provider delivery is separate from notification read/acknowledgement.

Default Vault presentation publishes `vault/Services/SUMMARY.md` and per-kind object pages. It includes source identity, revision, condition state, history and a historical report link only when that owned report actually exists. Missing reports stay explicit. Human notes belong in platform todo fields or separate human files. Generated-file ownership protects unrelated files; adapter failures have independent receipts. See [Vault](host-vault.md) and [adapters](service-adapters.md).

## Verification and limits

Public tests cover lifecycle, deduplication, ownership, concurrent revision updates, live versus historical effects, retries and resolution races, separate projections, source pinning, file ownership and SMTP protocol handling with mocks. Backup collection → retention → policy → Vault → todo was also exercised over an authorized SSH connection. Actual SMTP delivery and native FreeBSD backup scanning have not been verified. No background worker, approval ledger, custom-code sandbox or general logging service is implied.

*Last modified: 2026-10-25 14:06:31*
