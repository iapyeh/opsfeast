# Recipes, routines and shared-connection meals 0.1.0

All eleven bundled Inventory children and Overview now declare one Python [execution stage](staged-recipe-execution.md). CLI and saved/scheduled inventory create their lifecycle/river automatically. Web plates use one generated parent execution across hosts, including grouped routine workers. This does not change routine permissions, shared connections or independent retention.

This is the current execution contract for the split inventory recipes. See
[inventory](inventory-jobs.md), [retention](retention.md), [Web](web-recipe-menu.md)
and the [agreed design](inventory-routine-design.md). A recipe defines purpose,
inputs, routines and retained data; a meal selects exact recipe references.
`Recipe` objects represent active, thread-bound execution scopes, separate from
immutable routine definitions. Discovery never imports candidate programs or connects.

## Python routines

```yaml
descriptor_version: 0.3.0
id: example-routines
version: 0.1.0
access_mode: read
runner:
  contract: python-routines
  version: 0.1.0
  entrypoint: main.py
  finalizer: finalize
  routines:
    - id: baseline
      function: baseline
      required_permission: login
      depends_on: []
      properties: [example.value]
      platforms: []
output: {schema_version: 0.1.0}
```

Also declare attribution, dependencies, side effects, purpose and actual verification
as required by [authoring](recipe-authoring.md). `main.py` has one literal matching
`VERSION`. Each named synchronous function accepts one supplied `Recipe`; imported
functions need local wrappers. Functions return the common status/reason/message/data
envelope. The finalizer accepts a copied list of routine receipts/results, without an
actor, and returns that same envelope. It must be deterministic and have no side
effects. A success cannot hide skipped/failed routines: the runner downgrades it.

`required_permission` is exactly login or root. Empty platforms means all detected
platforms; otherwise match linux/freebsd/macos/esxi. IDs, output properties and
dependencies are explicit. Cycles, missing prerequisites, login depending on root,
and overlapping outputs on overlapping platforms fail static validation. Dependencies
are local routine IDs, not hidden cross-recipe execution. A prerequisite that did
not run prevents its dependent body. Completed dependency results are copied into
`recipe.prerequisites`. Shipped inventory routines have no hidden cross-property
dependencies or extra baseline collection.

Review Python before authorizing execution. Core scope guards are not an untrusted
code sandbox or a promise to prevent a program from issuing its own shell sudo.

## Meals and input precedence

Use `runner: {contract: recipe-meal, version: 0.1.0, entrypoint: meal.json}` and a
data-only manifest:

```json
{"schema_version":"0.1.0","members":[
  {"reference":"system/inventory/system","enabled":true},
  {"reference":"system/inventory/hardware-sensors","enabled":false}
]}
```

Members use exact Bundle paths, `:path` or `source:path`, not recipe IDs or nested
meals. All members must opt into python-routines. Arbitrary Python-session/Core
recipes and reports retain independent execution. Duplicate resolved members fail
preflight, including selecting Overview plus one of its children. Missing/disabled
members under bulk/scheduled policy, invalid inputs and incompatible execution
policies fail before connection rather than silently running a different subset.
Explicit-host override behavior remains visible in confirmation.

Overview has ten default general members plus hardware-sensors as explicit opt-in.
Job/property selectors resolve a subset without changing that default or schedules.
Inputs remain independent: descriptor defaults -> source values -> meal common
defaults -> child Profile/group/host values -> invocation values. Overview's common
attention, command timeout and collection budget inputs are declared by all its
children. General meals should configure required member inputs under each exact
recipe reference; there is no arbitrary parameter mapping or credential storage.

## CLI and checkout services

```sh
python -B tools/opsfeast.py inspect-recipe system/inventory/hardware --json
python -B tools/opsfeast.py recipes run system/inventory/overview --profile main --host node --json
python -B tools/opsfeast.py recipes run system/inventory/storage-capacity --profile main --host node --json
python -B tools/opsfeast.py inventory query --recipe system/inventory/hardware-sensors --profile main --host node --property sensors.fans --json
```

Inspection is read-only. Runs connect/save and may dispatch configured consumers;
query saves only with explicit `--save`. These examples do not grant execution scope.
Standalone, composed, scheduled and Web operations use the same host executor.

- `opsfeast.routine_contract.validate(directory, metadata)` returns frozen
  RoutineSpec values or a validated meal manifest; `order(specs)` sorts dependencies.
- `opsfeast.routine_execution.describe(root, host, choices, explicit_host=True)` is
  static. Choices contain reference, optional vars and inventory_selection. The
  result lists selected properties, conditional permissions and fingerprints.
- `run_host(root, host, choices, timeout=30, default_budget=90, session_class=None,
  runtime=None, save=True, trigger='manual', note='', stop=None,
  observation_run_id=None, explicit_host=True)` executes one host. It requires the
  human's host/privilege/consumer authorization. A stop event withholds later routines;
  it does not prove a running remote command terminated.
- `Recipe.child(vars=None, report=None, timeout=None)` borrows an actor with copied
  variables and an independent report. Parent access is suspended while the child
  is active. Child/session handles expire on return and cannot own connections or
  acquire privilege through Core. Routines receive frozen `recipe.routine`, selected
  property IDs, prerequisite copies and a deadline.
- `opsfeast.inventory.service.collect(recipe, properties)` and `finalize(results)`
  are the shared reviewed body/finalizer. They require the executor's guarded scope
  and pinned inventory collector. Reuse them instead of copying probes. These are
  checkout services 0.1.0, not an SSHScript change or an interface in older releases.

## Identity, ordering and lifetime

Pin recipe/shared collector bytes and validate fingerprints before execution.
Different hosts have separate scopes; one connection is used sequentially on its
owning thread. Login routines run first, then compatible root routines use one
bounded acquisition. A root body requires observed UID 0. Root failure preserves
earlier observations and leaves protected fields unavailable. Configured execution
policy currently must be login; su/sudo policy conflicts are rejected, not overridden
for batching. Root login is recorded as UID 0 even during the login phase.

One logical target connection does not mean one TCP socket for every jump topology.
There is no reconnect, credential retry, package installation or automatic AI wakeup.
Unknown identity or failed restoration stops subsequent work. Strict connection
close and remote process termination are separate evidence. Per-recipe budgets default
to 90 seconds, commands to 30, capped by invocation/remaining budgets. Child windows start during host setup and overlap: waiting for earlier routines consumes later children's wall-clock budget; this is not a fresh 90-second allowance per routine. Cleanup may
need additional bounded checks after a stop or collection budget expires.

Successful identical meminfo/df captures may be reused only within one host/permission
phase and identical variables/parser version. Failed captures and CPU time-window
samples are not reused. `capture_id` and original timestamps survive projection;
each recipe keeps its own probe aliases. Root/login caches remain separate.

## Durable evidence and consumers

Children save observations/recipe-run-UUID.json. Meals save observations/meal-run-UUID.json
with child/retention receipts, not another anonymous Overview observation. Completed
routines write raw `routine_checkpoints` before advancing. A killed worker may leave
`routine_execution_state: incomplete`; ingestion refuses to treat it as completed.
Opening history never reconnects or retries.

Completed inventory children declare inventory-routine-observations 0.1.0. Its
registered schema/normalizer preserves existing properties, units, YANG paths and
sample times and adds routine permission/actor/status, meal ID, shared capture IDs
and restoration/cleanup. Failed source attempts remain retained gaps. Collection,
retention and consumer results stay independent. Receipt-only updates preserve
business digests; consumers can refresh once after child storage/run completion.

Profiling, inventory latest and Vault read new and frozen historical records without
relabeling them. Preserve namespace, Host ID, reference, definition and source times.
Cross-recipe Attention preserves baseline IDs/times; no unselected hardware is
collected to fill a missing baseline. Observation runs can link multiple children.
Web supports scopes, connection/permission review, explicit confirmation, stop,
progress, independent child results and retained data. User meals can save nonsecret
job/property selections; saving/applying does not execute.

## Compatibility and verification

Overview is now a meal; new observations belong to child references and a new data
contract. Review exact-reference filters, consumers, per-recipe settings and external
integrations. There is no automatic rewrite or data migration. Existing job IDs,
intervals and explicit scheduled-host opt-in continue for the current meal; the split
does not enable/reset schedules. Historical schemas/normalizers remain frozen for
reading/replay, not an additional legacy execution path.

Public tests use synthetic transports and local fixtures. Native SSH/sudo, target
tools, full-platform applicability and assistive technology require separate
authorized verification. Delivery checks record actual local build/browser results.

## Delivery verification (2026-11-10)

The final Python 3.14.4 suite passed 1,395 tests; the frontend suite passed 109.
Public routine tests exercise one owned connection, independent retained children,
login/root ordering, denied or incorrect root identity, stop withholding, incomplete
checkpoints, copied/expired child scopes, no-store behavior, shared capture reuse,
worker fingerprint revalidation and one worker distributing independent receipts.
Saved meal tests cover exact field roundtrips, edits and invalid selections.

Wheel and sdist builds, extracted-wheel catalog (24 recipes plus one meal), schemas,
shared collector, Web assets, selector review, confirmed offline report worker and
artifact readers passed. Python 3.11 grammar and changed-document local links and
single timestamp footers passed; this delivery did not run the complete suite on
older interpreters or establish their native execution dependencies.

An isolated browser installation with synthetic target transports exercised field
selection, saved meal application, confirmation, the shared worker and separate
retained result pages, including the selected 1,200 RPM fan value, original source
times and actor/cleanup evidence. No managed host or real Profile was used for QA.
The existing Web service was restored on its original port and data binding; its
Bundle catalog returned HTTP 200. No package installation, schedule, commit, push
or release was performed. Native SSH/sudo/platform verification remains outstanding.

## Inventory child consumers and reports

Use [the inventory dependency map](inventory-consumers.md) for current
child references, exact report filters, subscription/read-filter updates and
unchanged historical ownership. Vault already subscribes to all observations;
backup-check has no inventory dependency. Retention-summary keeps exact filters;
execution-summary 0.1.3 preserves child/meal outcomes and routine/connection evidence.
Saved-result collection_user is unknown for mixed/unverified routine actors. Existing
Overview-only filters are not aliases for children; private configuration and
historical records are never rewritten automatically. These read/presentation
interfaces require no host access; explicit report, dispatch or rebuild writes
need the human's corresponding scope.

*Last modified: 2026-11-18 15:56:07*
