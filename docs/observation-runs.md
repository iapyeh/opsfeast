# Observation execution runs 0.1.0

An observation run is an explicit execution batch over selected hosts. It records what was selected and what completed, including failures before any retained observation exists. It is separate from an individual retained record, a saved recipe invocation, a report result and a scheduler's per-job attempt state. Membership is never inferred from nearby timestamps.

## When a batch is created

In a namespace-enabled profile, `recipes run REFERENCE --host/--group/--all` creates one batch for the resolved target union. Saved single-host `inventory run` and `inventory query --save` create one batch; a containing recipes batch passes its ID to the collector to avoid a second batch per host. Scheduled `inventory dispatch` creates one batch when at least one due task is planned, including its skipped configured targets. A dispatch with no tasks creates no batch. Dry runs, unsaved queries, offline report generation, raw replay and Vault rebuild create no batches. Existing historical records are not backfilled or regrouped.

A recipe batch includes disabled members omitted from a group/all selection as skipped targets. An entirely disabled selection is journaled without executing anything. Hosts excluded explicitly with `--exclude` are not selected batch members. Unknown selectors and invalid invocation syntax fail before a batch starts. See [execution gates](recipe-sources.md#enabled-flags-and-explicit-targets).

## Compact human batch views

Use the top-level observation command to revisit an execution after terminal output has scrolled away: observation lists batches; observation ID/latest shows host results; observation --status failed defaults to latest, and --status failed partial selects both states. UUID prefixes are accepted when unique. Full batch metadata/counts remain visible after filtering. A saved recipes run completion prints the shared Observation ID alongside per-host Result IDs. See [canonical CLI behavior and examples](cli.md#revisit-an-observation-batch).

The 0.2.0 [view schema](../schemas/observation-view.schema.json) is separate from the complete run contract below. Human/JSON summaries preserve explicit host membership; raw result links use an exact observation_run_id plus host match, never time proximity. The host table matches recipes run completion: collection identity, effective result with receipt failures, and Result ID. --status filters this effective result, including retention/content failures and degraded access; collection status remains separate. JSON result_status and whole-batch result_counts represent this outcome; host status and observation.counts remain collection evidence. Exact raw results supply collection_identity/access_degraded/content_status; missing/ambiguous raw data leaves these unknown with a warning, while known collection/retention states remain usable. Batch-only content failure is not assigned to individual hosts. Missing raw files do not erase historical host states. Existing inventory runs readers and Core/report interfaces remain available unchanged.

## Read without connecting or writing

```sh
python -B tools/opsfeast.py inventory runs list --profile main --json
python -B tools/opsfeast.py inventory runs show RUN_UUID --profile main --json
```

Use `--root PATH` instead of `--profile NAME`. List returns `{"runs": [...]}` sorted by start time and run UUID. Show requires the full UUID and returns the run object. A successful read exits 0 even when the saved run failed; missing/invalid IDs, configuration or storage failures exit 1, parsing errors 2. Reads do not initialize a profile, invoke consumers or connect. Original precision stays in JSON; terminal/Vault time display uses controller-local seconds.

Core/report input readers expose the same data:

```python
from opsfeast import Instance

profile = Instance.open(installation="/srv/opsfeast").profile("main")
runs = profile.retention.runs()
if runs:
    saved = profile.retention.run(runs[-1]["run_id"])
    for target in saved["targets"]:
        print(target["host_id"], target["status"], target["retention_status"])
```

Offline report recipes can use `context.retention.runs()` and `.run(run_id)`. Reads add selection/digest evidence to the reader's sources, as query/show do. These methods return complete run data, not a filtered projection; keep private run data local unless sharing is separately authorized. Ordinary `retention query/export` selects retained observation/operation records and does not export these run objects.

## Data and storage

The [JSON Schema](../schemas/observation-run.schema.json) defines `contract_version: 0.1.0`. Required top-level fields are run_id, namespace, anchor_host, recipe_reference, trigger, started_at, completed_at, status and targets. Optional selection and execution supply invocation/outcome evidence; absent metadata is Not recorded, never inferred from target membership or collection state. The run UUID identifies membership; it is not used in Markdown filenames. The first target's host/year archive stores the `observation_runs(run_id, payload)` table beside records in `retention/hosts/HOST/YEAR/observations.sqlite3`. anchor_host is storage routing only; each target keeps its actual identity/reference. No additional host or recipe-retention payload is fabricated, and group changes do not move these archives.

Each target stores host_id, icon, requested_jobs, jobs, recipe_reference, status, reason_code, retention_status, record_id, attention and baseline_record_ids. Jobs are major collection categories with IDs and available title/status, not every probe command. Actual stored job groups replace the target's displayed job list after retention. Generic operational recipes can have an empty job list. record_id and attention can be null when no record/evaluation was available. Missing evaluation is not a clean-health result.

The run starts as running, with completed_at null and pending targets. Outcomes use success/partial/failed/skipped; a generic result outside that set is represented as failed while its original raw result remains available. Finalization marks still-pending targets failed with execution_did_not_complete. Overall success means every target is success or skipped; any success/partial with other failures yields partial; otherwise failed. Collection, retention and content receipts remain separate: a completed run does not prove retention/publication succeeded or that all targets collected data. Process/storage interruption can leave a running batch; no automatic retry, stale-run reconciliation or resume command is provided.

An all-skipped recipe batch still returns its independent content_update receipt; publication failure makes that invocation exit nonzero even when no host executed. Scheduled skipped targets retain their configured recipe reference.

Run updates and `retention.run.updated` events commit in the same annual SQLite transaction under the retention lock. Events use the run UUID as record_id, the anchor host as host_id and contract/version observation-run/0.1.0. This event ID refers to a run: consumer code uses `context.retention.run(event["record_id"])`, not `.show`, to read it. The bundled Vault consumer subscribes to updates and rebuilds from current persisted state. A later retry must not assume a creation/update hint describes the latest run state. Completed collection snapshots are immutable; delivery/content retries do not reevaluate or rewrite their membership, policy or findings. The read object may also join the separately journaled execution receipt described below. Direct SQL editing is unsupported.

### Selection and command outcome

New producers persist selection as `{kind, all, selectors, exclude}`. kind is cli or scheduled; selectors is an ordered list of `["host", "HOST"]` or `["group", "GROUP"]` pairs. CLI selections preserve the semantic invocation, including explicit exclusions, rather than reconstructing it from resolved membership. Consecutive selectors of the same kind display together, such as `--group g1 g2`; mixed selector kinds keep their order. Scheduled selections name actual planned/skipped hosts and display Scheduled hosts, without pretending there was a CLI selector.

The joined execution object has status (success/failure), exit_code (0/1), completed_at and content_status (success/failed/skipped). It records the actual command outcome, independently of top-level collection status (success/partial/failed) and each target's status. Partial/failed collection, degraded recipe-run access, retention failure or publication failure makes the corresponding command fail; Attention thresholds alone do not. A successful all-skipped command does not prove collection took place.

After collection finalization and initial consumer dispatch, producers use record_execution/publish_execution to append an outcome to `observation_run_executions(sequence, run_id, payload)` in the same anchor archive. Each receipt and its update event commit atomically. Readers join the latest receipt. Publishing this final outcome can itself fail: one success-to-failure correction is appended, leaving a delivery event for repair. Later consumer retries/rebuilds may display the recorded failure but never turn a failed historical command into success. No final receipt means the outcome was not recorded, even if collection completed. This does not promise whole-Vault atomicity or automatic recovery after process/storage interruption.

## Attention evidence and Vault pages

Inventory saves its actual validated Attention policy and evaluated findings in each target, with source/baseline timestamps and record IDs. Evaluation may use older inventory groups at or before the target observation time; it does not use later observations. A later policy change or collection affects current host views, while this saved execution evidence remains unchanged. Findings are threshold hints, not live monitoring or a full health assessment. See [threshold semantics](inventory-jobs.md#attention-thresholds).

```text
vault/
  Observations/
    SUMMARY.md
    YYYYMMDDHHMMSS.md
    YYYYMMDDHHMMSS-2.md
```

The directory is uppercase `Observations/`, distinct from profile-root `observations/` raw JSON. Filenames use the batch start's UTC second, adding ordinal suffixes for collisions. The index has Started, Status and Targets columns; completed Status is the recorded command success/failure, while Targets shows the original selectors, not a host count. Missing old metadata says Not recorded; an unfinished run says running. Each page places Status, Trigger, Targets, Recipe, Started, Completed and integer-second Duration before Contents. Duration includes recorded execution finalization when available, otherwise the known collection interval. The Hosts table has Host, Status and Collection jobs columns. The icon/name links directly to the stored source report; targets without a report remain plain text. Retention is not a table column: failed storage is an explicit warning, and original publication failure remains visible even after a successful rebuild. Attention lists only flagged hosts; an empty Attention section is omitted. Deleted records leave an explicit unavailable-reference message and no dangling report link; their saved batch evidence is not regenerated from other records. HOSTS.md and overview link to the batch index.

Generated batch pages follow the same [ownership policy](host-vault.md#directory-and-ownership) as other Vault pages. Rebuild performs no collection, writes no retention/run data and cannot recover unrecorded old batch membership. There is no batch deletion, pruning, import or automatic migration command. Preserve existing private data and operation evidence.

## Checkout interfaces and verification

`observation_runs.list_runs(root)` and `show(root, run_id)` are read-only checkout services. `start(root, targets, reference, trigger="manual", selection=None)`, `record_result(root, run_id, host, result)` and `finish(root, run_id)` are producer services requiring initialized retention, valid explicit targets and execution authorization; use the CLI/collector workflows rather than reconstructing their lifecycle. A standalone producer dispatches consumers after completing its writes via `retention_store.refresh_content(root)`, computes the actual command exit code, then calls `publish_execution(root, run_id, exit_code, content_receipt)` and uses its returned exit code/content receipt. This helper journals the outcome with `record_execution(root, run_id, exit_code, content_status)` and publishes it without modifying the completed collection snapshot. These helpers are shipped modules, not additional stable Core execution APIs.

Public synthetic tests in tests/test_recipe_policy_runs.py and tests/test_observation_presentation.py cover selector/exclusion preservation, unknown old metadata, binary command outcomes, integer duration, publication-failure correction/rollback, preserved human notes and isolated reads, single/multi-host batches, pre-collection failure, all-skipped selections, transaction rollback, immutable policy/findings, missing source records, same-second filenames and generated links. No new native SSH, privilege escalation or scheduling installation is performed by these tests.

## Host results under observation

Use `opsfeast.py observation result [RESULT_ID]` for host history/diagnosis, `observation result RESULT_ID --detail` for full vertical evidence, and `--raw` for the original complete JSON. No ID lists host history with --host/--recipe-id/--status filters; --json returns structured index/diagnosis (selected --detail returns complete JSON). Use the original root/profile; successful reads return 0 independently of saved failure. Explicit --html exports a new index or selected --detail file without overwriting. These commands perform no collection or retry. `recipes results` is now offline-report-only; old host forms and --host are removed. Files and Result IDs remain unchanged. See [canonical modes, failures and verification limits](cli.md#host-result-history-and-modes).

_Last modified: 2026-10-21 18:12:20_
