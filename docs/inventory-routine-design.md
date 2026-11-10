# Proposal: inventory recipes, routines and one-connection meals

**Status: implemented for the initial inventory routine/meal contract.**
Read [the current contract](recipe-routines.md) for actual interfaces, restrictions,
storage and compatibility. The sections below preserve the agreed design rationale,
not an independent invocation manual. Initial limits include login execution policy,
explicit login/root requirements, no nested meals and no arbitrary session batching.
Native SSH/sudo verification remains separate from the synthetic delivery checks.

## Goal and implementation at design time

Turn the inventory collection groups into independently selectable/runnable recipes,
and make Overview a meal composed from those recipes. Each target host gets one
owned connection scope for the complete meal. Individual routine requirements
control verified actor selection: login actor first, root actor later. Independent
recipe identity, options, results and retention must survive that optimization.

Evidence recorded before implementation (superseded by the current contract above):

- `recipes/system/inventory/overview/collection.json` declares 11 jobs and 72
  properties. Ten jobs default enabled; hardware sensors require explicit selection.
- `tools/inventory_jobs.py:_collect_host` owns `connected(...)`, acquires
  `collection_actor(...)` before collection and calls `jobs.py:collect` once. It
  does not currently group different routines by their required permission.
- `recipes/system/inventory/overview/jobs.py:collect` already selects individual
  properties and reuses shared probe results within one call. Its large dispatch
  and helpers can be extracted; new recipes must not duplicate that program.
- `opsfeast.core.Recipe` is one active execution scope with vars, report, thread,
  actor and lifetime guards. `root()` is a verified scoped acquisition. Existing
  `_borrow()` mutates the supplied scope's vars; it is not yet a safe independent
  multi-recipe child-scope abstraction.
- `opsfeast.recipe_runs` invokes one owned worker per recipe/host pair. Merely
  adding recipes to today's menu meal does not reuse a connection.

## Proposed boundaries

```text
Recipe definition (versioned purpose, fields, inputs, retention contract)
├── Routine specification (reviewed callable, dependencies, required_permission)
│   ├── login: collect using the verified connection actor
│   └── root: collect only under a verified UID 0 scope
└── Recipe execution (independent variables, routine receipts, result and retention)

Meal definition (exact recipe references; optional fixed Host IDs)
└── Confirmed execution plan
    └── Host connection scope (one owner; no recipe-owned connect/close)
        ├── Verify login identity and platform once
        ├── Login phase
        │   ├── Recipe A / login routine
        │   └── Recipe B / login routine
        ├── Root phase (acquire once for compatible requirements)
        │   ├── Recipe A / root enrichment routine
        │   └── Recipe C / root routine
        ├── Verify restoration to login identity
        ├── Finalize independent recipe results and retention receipts
        └── Close the owned connection; publish meal/consumer receipts
```

Keep immutable recipe/routine definitions separate from mutable `Recipe` execution
objects. Add a public supported child execution scope to `Recipe`; each invocation
gets its own copied vars, report, deadlines and guard. It borrows only the parent's
transport and verified actor. The runner owns connect/close and the privilege
scope; recipe routines cannot close the shared connection or request hidden
additional privilege. Do not route recipes through a Console worker or change
SSHScript library code to accomplish this.

The first routine contract should define stable ID/version, reviewed entrypoint,
selected output property IDs, validated inputs, platform applicability,
`required_permission: login | root`, prerequisite routine IDs, deadlines and side
effects. Routine code receives a guarded execution context and returns data plus
source evidence; the runner owns durable results/retention/consumer dispatch.
Enforce the requirement in the runner: today's descriptive `permissions` metadata
alone is not enforcement. Additional service accounts, Linux capabilities and
remote management transports are later explicit requirements, not aliases for root.

## Initial split aligned with existing collection jobs

These are proposed sibling leaves under `recipes/system/inventory/`, not recipes
nested inside the current Overview leaf. UI categories can contain several recipes;
field-tree prefixes, job boundaries and recipe paths need not be identical.

| Proposed leaf | Existing job | Properties | Default Overview meal |
| --- | --- | ---: | --- |
| hardware | hardware-baseline | 9 | included |
| system | system-configuration | 8 | included |
| network-configuration | network-configuration | 11 | included |
| software | software-inventory | 1 | included |
| storage-layout | storage-layout | 8 | included |
| storage-capacity | storage-capacity | 13 | included |
| services | service-state | 2 | included |
| network-state | network-state | 2 | included |
| system-runtime | system-runtime | 2 | included |
| resource-metrics | resource-metrics | 14 | included |
| hardware-sensors | hardware-sensors | 2 | explicit opt-in |

Each recipe may contain more than one routine. Split a generally readable baseline
from root-only enrichment so an optional privileged field cannot force the entire
recipe to run as root. Audit actual probes per platform before assigning requirements;
for example hardware data availability differs between Linux, macOS, FreeBSD and
ESXi. Do not infer required privilege solely from a UI category or command name.
Keep existing property IDs, units, YANG mappings and observation times. New recipes
must declare accurate platform coverage and their own purpose/verification limits.

## Planning, ordering and permission behavior

1. Resolve the meal to exact recipe references and fixed selected Host IDs. Validate
   every definition, source enabled gate, input and output contract before connection.
   Pin reviewed code and fingerprints across all members; changing code/settings
   invalidates confirmation. Shared execution requires opted-in routines. Existing
   arbitrary Python/session recipes must not silently become shareable.
2. Build a routine dependency graph per host. Reject cycles, unknown dependencies,
   missing permission declarations and conflicting requirements. Dependencies cannot
   silently broaden the selected outputs/privileges. Expose necessary prerequisites
   in preview. Keep stable definition order within the same permission/dependency
   group. A login routine depending on a root routine conflicts with the initial
   login-first model and must fail preflight, rather than silently changing phases.
3. Group compatible login routines first and compatible root routines last. Same
   permission label alone is insufficient for reuse: Profile, host, authentication
   actor, execution policy and transport must match. Validate explicit configured
   su/sudo policies rather than overriding them for batching. An initial root login
   is recorded as such; it cannot be claimed as an unprivileged connection.
4. Acquire privilege using the existing bounded account policy and user-authorized
   scope. Verify actual identity before executing the root group. Missing or disabled
   sudo, unavailable credentials or failed acquisition leave that group unavailable;
   completed login results remain valid. Never run a root routine under login and
   report success, silently broaden credentials, install dependencies or reconnect.
5. Record restoration and cleanup independently. Unknown identity, restoration
   failure, transport failure, deadline or a stop request ends subsequent work on
   that connection. Do not try another recipe in an uncertain scope. Report queued
   routines as skipped/cancelled and preserve the original failure evidence.

Connection reuse means one logical target connection lifecycle, not one TCP socket
for every possible jump topology, and not a promise of recovery without reconnecting.
No automatic reconnection/retry is part of this proposal. Hosts can run independently;
there is no concurrent use of one thread-bound `Recipe` scope.

## Shared probes, results and storage

Extract reviewed collection/parsing functions into a product module reused by the
11 recipes. The meal executor may deduplicate identical prerequisites within the
same host run, platform, verified identity/permission phase, command, relevant input
and parser version. Do not reuse login failures as root results, share private root
outputs into unrelated recipes, reuse samples from a previous run, or equate a
higher privilege with identical observation scope. Preserve the original source
sample time and IDs for all projections; never invent fresh timestamps when reusing.

Every recipe keeps its own raw result, version/digests, routine states and declared
retention output. Write completed routine evidence before advancing, so later
root/connection failure does not erase it. An aggregate meal receipt links child
recipe/routine IDs, connection identity evidence, acquisition/restoration and cleanup;
it does not merge unrelated data into an anonymous Overview record. Collection,
retention and consumer success remain separate. Consumer refresh may be batched
once after child retention writes, with an independent receipt and partial states.

Retain the `recipe -> retention -> consumer` flow. Preserve original field and
per-sample times, namespace, user Host IDs and explicit partial/unavailable states.
Cross-recipe derived assessments (for example load per CPU requiring a CPU baseline)
use declared retained inputs and both source times. Do not quietly add unselected
hardware collection as a prerequisite or claim one snapshot is a behavior baseline.

## Compatibility and implementation order

There is no need for a legacy execution adapter or automatic data migration. Until
the new contracts, consumers and tests land, keep the current recipe working.
When the split actually ships, explain that old Overview recipe settings, selectors,
cron configuration, saved jobs and meal references must be reviewed and replaced
with the selected child references; do not rewrite them automatically. The default
meal still excludes sensors. Old retention remains under its original reference,
queryable through retention interfaces without relabeling or deleting history.
Historical views must distinguish a removed definition from missing saved data.

Implement in reviewable stages:

1. Version/validate routine and executable-meal contracts, immutable plan and child
   `Recipe` execution scopes; preserve exact-reference settings and authorization.
2. Add host-level executor, guarded borrowing, phase ordering, stop/deadline behavior,
   per-routine evidence and independent recipe/retention results.
3. Extract shared probes and deliver independently runnable inventory recipes with
   audited per-platform permissions. Standalone execution uses the same executor
   with one recipe, not another collection implementation.
4. Expose Overview as a meal in discovery/CLI/Web, update scheduled collection,
   profiling provider mappings, consumer queries, artifacts, docs and agent skills.
5. Verify the complete path before replacing the current Overview entrypoint.

Acceptance must include: exactly one connection open/close per host meal; standalone
and composed data equivalence; correct login-before-root order; no probe run under
insufficient identity; one compatible root acquisition; restored login identity;
credential-disabled/acquisition/restore/transport failures; stop between phases;
independent vars/reports and no stale scope reuse; no cross-identity cache leakage;
source/code-change confirmation invalidation; per-recipe partial/retention/consumer
receipts; scheduled opt-in preservation; old history unchanged; and extracted-package
execution. Synthetic tests establish control/data contracts, not real SSH/sudo or
platform applicability. Explicitly authorized native verification remains separate.

See [current inventory](inventory-jobs.md), [Core execution](core-api.md),
[execution policy](recipe-results-and-accounts.md), [retention](retention.md) and
[Web recipe menu](web-recipe-menu.md).

*Last modified: 2026-11-10 16:14:10*
