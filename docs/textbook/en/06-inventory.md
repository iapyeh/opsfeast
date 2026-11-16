# 6. Inventory, freshness and scheduling

[Book home](README.md) · Previous: [Recipes](05-recipes-and-results.md) · Next: [Data and Vault](07-data-and-vault.md)

Inventory answers measured questions about a host. You can request one property immediately, save a comparison, run a job containing related properties or opt specific hosts into periodic collection. These choices differ in persistence and future effects.

## Discover the measurement

```sh
python -B tools/opsfeast.py inventory describe --json
python -B tools/opsfeast.py inventory describe --job storage-capacity --json
```

These local reads require no profile and list properties, types, units, entity keys and source-model mappings. The [collection table](../../../recipes/system/inventory/overview/collection-plan.md) lists job contents, starting intervals and coverage. A property can yield several entities, such as filesystems keyed by source and mountpoint.

## Query only what you need

With the selected target and inventory privilege policy authorized:

```sh
python -B tools/opsfeast.py inventory query --profile main --host server-01 --property storage.filesystems.used_percent --json
```

Without `--save`, this performs real probes and actor/platform checks but makes no OpsFeast raw, retention, Vault, host-fact-cache or schedule-state writes. Target SSH/sudo audit mechanisms can still record activity. The probe can use inventory's bounded privilege acquisition policy, so a “read query” does not imply login-only execution.

Select properties or jobs; do not combine both selector kinds. Unsupported fields, failed probes, unknown values and capture truncation remain explicit. A shared probe may supply several properties; budgets apply to collection commands rather than proving a whole-connection deadline.

## Keep an immediate comparison

```sh
python -B tools/opsfeast.py inventory query --profile main --host server-01 --property storage.filesystems.used_percent --save --note "Capacity review before application rollout" --json
python -B tools/opsfeast.py inventory run --profile main --host server-01 --job storage-capacity --json
```

Both commands connect and save evidence. The first keeps the selected property query and human note; the second runs the selected job. Inspect raw save, retention and downstream receipts independently. Repeated equal values remain independent samples. Notes provide human context, not proof that an associated change occurred.

Immediate refreshes do not advance inventory schedules. They update only the measured properties in the latest view. A failed latest attempt remains a gap; current views do not silently substitute an older success. Different properties can legitimately have different source times.

## Read freshness honestly

Suppose hardware facts were collected yesterday and filesystem capacity was collected five minutes ago. A current page can combine them. Its generation time is not the sample time for both. Preserve sample times, source IDs, measured scope and actual actor warnings when comparing values.

Rates require a measured interval or compatible samples. A cumulative byte counter alone is not throughput. Sparse YANG node mappings describe property observations; they do not establish full NETCONF, gNMI or complete datastore conformance. The owning recipe's field definitions determine what each value means.

Inventory Attention applies current configured thresholds to current views; historical batch Attention preserves the saved findings/policy of that execution. Changing today's thresholds and rebuilding should not reinterpret yesterday's batch.

## Opt into periodic collection deliberately

Inventory schedules live in profile-local `inventory.yaml`. Missing schedule settings enable no hosts. A reviewed scheduling plan should name hosts, jobs, intervals, privilege scope, storage effects, controller availability and how failures will be noticed.

After that scope is authorized, an example local configuration change is:

```sh
python -B tools/opsfeast.py inventory configure --profile main --host server-01 --job storage-capacity --interval 30m --json
```

This writes settings without connecting or installing cron. A host enable action is separate:

```sh
python -B tools/opsfeast.py inventory configure --profile main --host server-01 --enable --json
```

Enabling the host can make other default-enabled jobs eligible too. Review all effective jobs before enabling it; a storage interval override alone does not restrict collection to storage. Host, source and exact recipe enablement in `hosts.yaml` are additional gates.

Inspect configuration and planned work before running it:

```sh
python -B tools/opsfeast.py inventory status --profile main --json
python -B tools/opsfeast.py inventory dispatch --profile main --dry-run --json
python -B tools/opsfeast.py inventory cron show --profile main --json
```

These are reads. Ordinary `inventory dispatch` connects to due enabled work once. Authorized `inventory cron install` changes the current user's crontab to call the dispatcher each minute, using pinned absolute paths and the selected profile root. It preserves unrelated entries and does not enable hosts. The controller must be running and able to access those paths.

Failures advance the next normal interval. There is no automatic collection retry, catch-up backlog, AI wakeup or inventory notification service. Consumer retries are a different mechanism. Confirm later saved attempts/times to establish that cron actually ran; a configured entry alone is insufficient.

Agent prompt:

> Prepare a periodic capacity plan for server-01. Inspect all effective jobs and enablement first. Show which jobs will become eligible, interval, privileges, storage and failure visibility. Do not enable the host or install cron until that concrete schedule is within my authorization.

**Checkpoint:** Distinguish an unsaved query, saved manual refresh, due dispatch and cron installation. Explain why a newly rebuilt current page can still contain yesterday's data.

Canonical guidance: [inventory jobs](../../inventory-jobs.md), [recipe catalog entry](../../../recipes/system/inventory/overview/README.md), [collection table](../../../recipes/system/inventory/overview/collection-plan.md), and [inventory access](../../inventory-access.md).

*Last modified: 2026-10-26 12:55:26*
