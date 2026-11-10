# Inventory consumers and reports after the recipe split

This is the dependency review for [inventory routines/meals 0.1.0](recipe-routines.md).
`system/inventory/overview` is an execution meal. It produces a meal receipt linking
children, not another retained Overview observation. Current inventory datasets use
`inventory-routine-observations` 0.1.0 and each child's exact recipe reference.
Historical data, events, definition hashes, timestamps and recipe ownership stay unchanged.

## Dependency map

| Reader | Current dependency and behavior | Historical behavior |
| --- | --- | --- |
| Bundled Vault consumer | Its existing unrestricted observation subscriptions already receive all children. Current pages remain independent per recipe/source; the host index reads the latest attempted `system.system_name` sample and links its original source report. A newer failed attempt displays unknown. | Frozen snapshot/job records and their original references remain readable; no relabeling or automatic rebuild is performed by an inspection. |
| Vault Attention | Resource children can use as-of retained hardware baselines from the same host/origin namespace. Saved effective policy is the starting point; current exact-child configuration can override it. Source record IDs/references/times are disclosed. Baseline data does not become part of the resource recipe's retained dataset. | Snapshot/job rendering and saved observation-run findings keep their historical semantics. Nothing recollects missing baselines. |
| Backup-check consumer | Subscribes only to backup-files-check 0.1.0; no inventory dependency or selector change is needed. | Unchanged. No historical replay gains live service effects. |
| `feast/report/retention-summary` 0.1.0 | Reads observations generically; `recipes` is an exact-reference filter. Select children explicitly, or leave the array empty for all saved observations. | Selecting Overview still selects only records originally owned by Overview. It is not an alias for children. |
| `feast/report/execution-summary` 0.1.3 | Accepts explicit raw child/meal result inputs. JSON preserves exact references, meal IDs, routine/connection evidence, retention/consumer receipts and child receipts; HTML includes a child-outcomes table. It does not follow result paths to read extra inputs. | Legacy raw snapshots/general results are still accepted with their original metadata. Missing new fields remain unknown. |
| Saved-result actor summary | A routine result reports one actor only if completed routines agree on one verified username/UID. Mixed or uncertain actors remain unknown; consult routine evidence for details. | Existing snapshot/general identity interpretation remains available. |
| Profiling / `inventory latest` | Existing split-aware readers consume child data. Overview remains a legitimate meal/catalog entrypoint; it does not own those samples. | Original reference/definition boundaries and source times are preserved. |
| Frozen normalizers, schemas and legacy exchange/CSV readers | Historical-only paths deliberately retain the old identifiers. They are not collection or child-selection alternatives. | Keep original bytes/digests and ownership. |

## Select current child datasets

All references below are Bundle references. User and external copies keep their
actual `:path` or `source:path`; do not strip source qualifiers or infer ownership
from a matching recipe ID.

```text
system/inventory/
├── hardware
├── system
├── network-configuration
├── software
├── storage-layout
├── storage-capacity
├── services
├── network-state
├── system-runtime
├── resource-metrics
└── hardware-sensors
```

Sensor collection is opt-in. Reading already saved sensor data grants no collection
or schedule permission. Read-only discovery/query examples:

```sh
python -B tools/opsfeast.py consumers list --recipe system/inventory/storage-capacity --profile main --json
python -B tools/opsfeast.py recipes show system/inventory/resource-metrics --profile main --json
python -B tools/opsfeast.py retention list --recipe system/inventory/system --profile main --json
```

An authorized offline report can select multiple children without connections:

```sh
python -B tools/opsfeast.py recipes run feast/report/retention-summary --profile main \
  --var 'recipes=["system/inventory/system","system/inventory/storage-capacity","system/inventory/resource-metrics"]' --json
```

Report execution writes a new report/artifacts. Empty or missing datasets remain
empty/unknown; it does not widen a filter, recollect, infer health or rewrite source
records. Add Overview explicitly only when historical Overview records are wanted.
The report reader records the selected original IDs/digests and times.

## Update a reviewed user consumer

Read the [consumer contract](retention-consumers.md) and its actual descriptor/code
before changing either. Update subscriptions and read filters together. For all
compatible inventory children, subscribe by contract/version. For a specific child,
add its exact reference to each subscription. Multiple subscriptions are OR; fields
within one selector are AND. There is no `recipe_references` array selector or
implicit meal expansion.

```yaml
subscriptions:
  - event: retention.observation.created
    selector: {contract: inventory-routine-observations, version: "0.1.0"}
  - event: retention.observation.deleted
    selector: {contract: inventory-routine-observations, version: "0.1.0"}
```

The corresponding read filter must use the same contract/version:

```python
records = [record for record in context.retention.query(kind="observation")["records"]
           if (record.get("retention_definition") or {}).get("contract") == "inventory-routine-observations"
           and record["retention_definition"].get("version") == "0.1.0"]
```

A contract-only subscription can include reviewed user/external producers. Restrict
references in both the descriptor and program when their source scope is required.
Keep each envelope's namespace, host, recipe reference, definition, status and source
times; do not synthesize one Overview record from the selected children. For current
property projections reuse `inventory_jobs.latest_groups(records)`; it keeps exact
reference/definition boundaries and newer failed attempts rather than filling old
successes. `observation_runs.attention_context(root, record, records=records)` can
reuse an already queried list for as-of baseline evaluation without another query;
this is a checkout helper, not an arbitrary cross-source join or an execution API.

Retain explicit old-contract/reference subscriptions and readers only if historical
updates are part of the consumer's purpose. An old Overview-only subscription still
matches old Overview events; it will not begin receiving children automatically.
There is no automatic edit of private descriptors, `feast.yaml`, saved jobs or report
variables. Review/authorize those exact changes and any output replacement or backlog
delivery. Dispatch/rebuild affects content and receipts; historical replay is not
fresh collection and does not grant live notification/mail effects.

## Verification and limits

[Public split-consumer regressions](../tests/test_inventory_consumers_split.py) cover
exact child versus historical filters, separate event subscriptions, source-linked
Vault OS identity, newer failure gaps, cross-child Attention/policy/provenance,
meal/child report artifacts and mixed-actor summaries. Tests use temporary Profiles
and synthetic transports. No production Profile, host connection, mail delivery,
schedule or private consumer configuration is changed. Consumer code remains reviewed
in-process Python rather than a sandbox; a subscriber's external effects require
the human's corresponding authorization.

Delivery verification (2026-11-10): Python 3.14.4 passed all 1,402 tests, including
seven split-consumer/report regressions; 109 frontend tests passed. Wheel/sdist
builds and extracted-wheel child/meal report generation passed, including original
time/receipt preservation and no child-path traversal. Changed-document links,
single timestamps, Python 3.11 grammar and diff whitespace passed. The authenticated
isolated Web viewer loaded the new report/static preview; artifact tests checked
child table content and escaping. This is synthetic/local evidence, not native
SSH/sudo or external delivery validation. The existing Web was restored on its
original port/data binding and returned HTTP 200 for report-summary 0.1.3. Existing
private consumers, generated Vaults/reports and historical data were not rewritten.
No install, schedule, commit, push or release occurred.

*Last modified: 2026-11-10 16:57:30*
