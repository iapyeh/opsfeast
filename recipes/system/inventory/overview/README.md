# System inventory meal

Overview **0.1.0** is a `recipe-meal` composition, not an anonymous data producer.
Its independent child recipes share one owned logical connection per host. Login
routines execute before verified root routines. Each child keeps its own variables,
raw results and retention; failures and unavailable fields stay explicit.

## Members

- [hardware](../hardware/README.md) — default member.
- [system](../system/README.md) — default member.
- [network-configuration](../network-configuration/README.md) — default member.
- [software](../software/README.md) — default member.
- [storage-layout](../storage-layout/README.md) — default member.
- [storage-capacity](../storage-capacity/README.md) — default member.
- [services](../services/README.md) — default member.
- [network-state](../network-state/README.md) — default member.
- [system-runtime](../system-runtime/README.md) — default member.
- [resource-metrics](../resource-metrics/README.md) — default member.
- [hardware-sensors](../hardware-sensors/README.md) — explicit sensor opt-in.

## Run and select

```sh
python -B tools/opsfeast.py inspect-recipe system/inventory/overview --json
python -B tools/opsfeast.py recipes run system/inventory/overview --profile main --host node --json
python -B tools/opsfeast.py inventory query --recipe system/inventory/overview --profile main --host node --property system.hostname --json
```

Inspection never connects. Runs need the human's target, privilege and consumer
scope. Query does not save unless `--save` is explicit. Choose `--job` or `--property`,
never both. Choosing sensors.fans explicitly runs just that selected property and
its necessary reviewed prerequisites; it does not enable sensors or schedules.
The Recipes Web page exposes the member dishes, field scope, review and confirmed
execution. Saving/applying a user meal only changes selection metadata.

Common inputs are attention, command_timeout_seconds and collection_budget_seconds.
Child exact-reference settings override common meal defaults; invocation values
win. Budgets cover overlapping wall-clock time from host execution setup, rather
than granting an extra full budget to every later member. Per-command and worker
limits remain separate. Missing tools or root access remain gaps; nothing installs
or reconnects automatically.

## Routine identity and storage

Linux serial/UUID acquisition is a separate root routine. Other selected baseline
queries run under the verified login actor. Root login is recorded as UID 0. Unknown
identity/restoration stops later work. One connection lifecycle is not a claim of
one TCP socket through all jumps or proof of remote process termination.

Each completed child retains inventory-routine-observations 0.1.0 under its exact
reference with the existing property IDs/units/YANG paths and original sample times.
The meal receipt links children; it does not store duplicate Overview observations.
Checkpoints preserve completed routine data before subsequent work. Incomplete
worker checkpoints cannot be ingested as completed results. Collection, retention
and consumer receipts remain independent; reading history never reruns a command.

Scheduled inventory keeps existing job IDs, intervals and explicit host opt-in.
Due work resolves only the relevant children, sharing a host connection. The split
neither enables a schedule nor migrates/relabels historical records. Review old
exact-reference consumer filters/settings when adopting independent child outputs.

## Linux iproute2 capabilities 0.4.2

The shared collector retains the existing bounded JSON-capability handling and
text fallback for older Linux iproute2. Unsupported JSON options do not require an
upgrade. Permission/parse errors remain gaps; route text remains raw entry rows,
not a fabricated structured route. The original parser tests remain in the public
suite. This does not establish native target verification for the new composition.

## Recipe-owned retention contract

Historical inventory-observations 0.1.0 and inventory-job-observations 0.1.0 schemas
and normalizers in this directory are frozen read/replay resources. Current child
execution uses the new registered routine contract. Historical records keep their
original recipe reference/definition and do not become child records automatically.
Legacy collection resources are not an alternative execution entrypoint for the meal.

## Verification and agent entrypoints

Python 3.11+, SSHScript 7.0.1 and the product routines service 0.1.0 are required.
No native SSH/sudo/platform execution for this split/composed version is claimed;
public tests use synthetic transports and local fixture processes. See the canonical
[routine contract](../../../../docs/recipe-routines.md), [inventory jobs](../../../../docs/inventory-jobs.md),
[retention](../../../../docs/retention.md), [collection table](collection-plan.md),
[Web menu](../../../../docs/web-recipe-menu.md) and [recipes skill](../../../../skills/opsfeast-recipes/SKILL.md).

*Last modified: 2026-11-10 15:57:34*
