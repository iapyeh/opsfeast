# Accumulate recipe execution experience

Use this workflow before and after agent-led recipe work, especially incomplete
`system/inventory/overview` collection. The human selects targets and effects;
the agent reads evidence, interprets new gaps and preserves reviewed lessons.
Routine collection runs reviewed recipe code without a model dependency.

## Two durable destinations

- **Host-specific knowledge:** the selected Profile's existing host notes, through
  [host-notes 0.1.0](../../../docs/host-notes.md). Store tool capabilities,
  environmental constraints, verified methods and unresolved questions with
  original evidence references. Do not create another private memory store.
- **General methods:** reviewed recipe code, public synthetic regression tests,
  recipe documentation and relevant skill routing. Never copy private host names,
  addresses, credentials or original host output into public fixtures.

A note is evidence/context, not an executable plan, permission, current fact,
capability cache or a permanent property of an OS family. A standalone CLI run
does not read these notes automatically. Agent guidance is procedural, not an
execution gate; installed agent copies must receive these updated skills to use it.

## Before execution

1. Select the exact installation, Profile, source-qualified recipe and configured
   host IDs. Resolve groups through existing Core/CLI discovery. Never merge
   same-named hosts from other Profiles.
2. Read each target's notes through `host_notes.inspect` or the CLI. Use the exact recipe-reference filter with `include_general=True`, then review
   general constraints and unlabelled notes; list all host notes if context is
   unclear. Do not rely only on text/tags, a short recipe ID or chat memory.
   Inspect saved recipe results and latest property attempts. Preserve collection,
   retention and content outcomes separately; use the [diagnosis workflow](../../../docs/result-diagnostics.md).
3. Check lesson applicability: original observation date, actor, target identity,
   OS/tool capabilities and recipe version. An upgrade, host replacement,
   configuration or actor change can invalidate a lesson. Distinguish verified,
   proposed, contradicted and no-longer-applicable claims explicitly.
4. Read the recipe's function, purpose and success criteria. The reviewed program
   is a method, not the limit of the authorized objective. Investigate unmet goals
   and choose suitable scoped alternatives rather than treating program failure
   as the end of the task. Prefer current bundled support. If the recipe now implements a lesson, use that
   recipe rather than replaying a command from a note. Existing authorization
   governs connections, privileges, writes, packages and scheduling; notes never
   expand it. Do not modify product code on an ordinary DevOps run without scope.
5. For first exploration, use a finite, explicit budget when authorized. Inventory
   supports `--var collection_budget_seconds=180` and
   `--var command_timeout_seconds=30`; budget bounds collection commands, not the
   entire connection lifecycle. These are invocation overrides, not permanent
   settings. More time cannot supply an absent kernel feature or unsupported flag.
   Use normal budgets for established routines; never increase them automatically
   after every failure or promise complete coverage on every platform.

Read-only example, with synthetic names (no connection):

```sh
python -B tools/opsfeast.py host-notes --profile lab --host node list
python -B tools/opsfeast.py observation result --profile lab --host node --json
python -B tools/opsfeast.py observation result RESULT_ID --profile lab --limit 50 --json
python -B tools/opsfeast.py inventory latest --profile lab --host node --json
```

## After execution

1. Assess exact property/entity gaps rather than only exit status. Separate
   unsupported options/features, insufficient access, absent optional values,
   malformed/truncated data, time limits and connection/cleanup failures.
   An absent filesystem or mountpoint can be inapplicable; do not invent values
   merely to make the result successful. A previous successful value stays history.
2. Inspect saved source commands, bounded stdout/stderr, exit codes and source
   times before proposing changes. If evidence already explains a gap, do not
   reconnect just to rediscover it. Preserve original failed attempts alongside
   successful alternate probes; each property must cite its actual source/time.
3. Investigate only the unresolved question with authorization: prefer selected
   inventory properties/jobs and existing APIs over repeated full collections.
   A safe alternate read can be implemented after an explicit unsupported-option
   result; permission, malformed-output and transport errors are not permission
   to keep trying commands, actors or credentials.
4. Review a generic method, add success/failure/boundary regression tests, and
   verify it before incorporating it into the recipe. Use real host execution only
   within authorized scope and record it separately from synthetic validation.
   Keep platform-specific gaps explicit if no trustworthy source exists.
5. Draft only useful new lessons; skip duplicates and routine unchanged runs.
   Apply the [human-reviewed save workflow](../../../docs/host-notes.md#human-agent-workflow):
   show the exact selected Profile/host and complete draft, obtain confirmation,
   then reread current revision and create/update through the shared service.
   Reuse already-confirmed content; a revision conflict requires reinspection,
   not blind retry. Preserve other human notes and conflicting evidence. Report
   the saved UUID, source and timestamp. Declined drafts remain unsaved.

## Lesson template

Use one note per coherent lesson or related constraint, not one note per command.
Use structured metadata for association and plain-text content for evidence and reasoning.

```text
Title: Recipe experience: system/inventory/overview — tool capability
Structured recipe_references: ["system/inventory/overview"]
Structured tags: ["linux", "tool-capability"]
Scope: selected Profile/host; actual actor; target identity limits
Observed: original source time; OS/tool capability; recipe version and available digest
Evidence: saved result/retention IDs and relevant probe IDs
Verified: concrete symptom, failed method, successful alternative and verification scope
Next run: use the current reviewed recipe; applicability/invalidation checks
Unresolved: unsupported or optional fields, missing evidence and proposed investigation
Authorization: boundaries for future work; this note grants no execution permission
```

Do not store passwords, raw credential-bearing configuration, arbitrary full logs
or copied secrets. Keep historical dates in the content: the note's modification
time is not the source observation time. Public reusable guidance uses synthetic
examples, and notes remain independent of replaceable product code/Vault rebuilds.

## Make recipe-related notes discoverable

Use structured `recipe_references` for exact source-qualified association and
`tags` for tool/platform/symptom labels. The [notes contract](../../../docs/host-notes.md#relate-notes-to-recipes)
documents validation, normalization, filters, update/clear and merge behavior.
When drafting lessons, set these arrays alongside title/content/source through the
existing revision-checked service; do not rely on a title tag or text annotation.
References do not need to resolve to currently installed code.

Before agent-led execution, retrieve the selected recipe's notes plus general
host experience:

```sh
python -B tools/opsfeast.py host-notes --profile lab --host node list --recipe system/inventory/overview --include-general
```

Python: `host_notes.inspect(installation, profile='lab', host_id='node',
recipe_reference='system/inventory/overview', include_general=True)`.
No tag filter is necessary for this initial lookup; adding tags narrows matches
and can hide relevant constraints. General unassociated notes include existing
unlabelled records. Review them for relevance and stale/contradictory facts;
if scope remains unclear, inspect the full host list. Never infer “no experience”
from a text/tag miss, and never treat metadata as permission.

Preserve human-confirmed prose when adding metadata. Omitted update arrays
preserve current values; `[]` intentionally clears. Merge unions omitted arrays
across selected notes. Use the current revision and normal reviewed mutation
workflow. The CLI runner itself does not read notes or call an agent; this lookup
is required agent guidance, not runtime enforcement or automatic strategy learning.

## Worked capability examples and limits

- Inventory 0.4.2 supports iproute2 rejecting `-j`: bounded address/route text
  queries, with original JSON failures preserved. This was verified on one
  authorized old-Linux host; it is not evidence that all old systems work.
- Inventory 0.4.3 supports lsblk rejecting `-J`: explicit `-P` key/value rows,
  quoted/hex-escaped strings, byte sizes and missing optional fields. Synthetic
  tests cover parsing, rejected data, source evidence and permission failures.
  This delivery has not executed that new alternate command on a managed host.
- A missing `/proc/pressure/memory` is evidence that the PSI file is unavailable
  in that environment; do not derive genuine memory pressure from unrelated
  counters or repeat the same missing-file query in a diagnostic loop. The
  recipe still reports this gap; automatic per-host method caching is unimplemented.

See [inventory capability details](../../../recipes/system/inventory/overview/README.md),
[host evidence lookup](../../../docs/host-notes.md#answer-host-questions-from-accumulated-evidence)
and [exploration to reusable operations](exploration-to-recipe.md).



## Nested Web meal selections

Use [the menu contract](../../../docs/web-recipe-menu.md) for preferences 0.2.0. Domain disclosures start closed; Scopes describes the domain alongside Bundle/User recipe lists. Add meal IDs to the plate rather than flattening them. User meals save direct recipes, nested meal IDs and field scopes, never hosts; creation/deletion are supported, editing is deferred. Deletion atomically removes incoming user-meal references and retains empty parents. Use `opsfeast.menu_preferences.expand(profile, recipes, meals)` for current-definition expansion and field union before execution, or pass `meals` to the authenticated recipe preview API. Repeated exact recipes execute once per host; report recipes once locally. Cycles, missing references and conflicting options fail; changed definitions require renewed review. Reads/saving grant no execution authority. Old 0.1.0 preferences are preserved but unsupported; deliberate recreation is required, without automatic migration. Synthetic tests do not establish native SSH/privilege behavior.



For Web batch work, use [execution throttle/defaults](../../../docs/web-recipe-menu.md#execution-throttle-and-defaults-010), rather than splitting targets merely to bypass a host-count cap. The installation default is 8 host lanes; pass threads with the confirmed start request for a one-time execution override. Same-host work stays sequential. Changing the default does not change saved meals, previews or running work. Saving grants no execution authority; preserve independent results and stop/cleanup evidence.

*Last modified: 2026-11-11 16:11:57*
