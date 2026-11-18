# Unified Recipe definitions and conversational authoring

All recipes use the ordinary descriptor and the same Recipe detail page. There
is no separate draft lifecycle, descriptor, reader, page or executable placeholder.
A missing entrypoint means not runnable. The virtual-plan interpreter and closed flow
importer remain unimplemented; storing a flow plan does not execute it. Reviewed
actual Python can use [python-workflow](python-workflows.md) with delayed SSH and
an active-agent browser handoff.

## Human and agent workflow

When a human asks to create a recipe, resolve the Profile and immediately save an
ordinary initial definition. Keep unknown text empty, mappings empty and lists
empty according to their field types. Give its stable Web detail URL:
`/recipes?profile=PROFILE&recipe=ENCODED_EXACT_REFERENCE`.
Save each agreed milestone through the same interface; no promotion/conversion
step is required when a real implementation is later supplied. The Recipes index
shows **可執行 / 不可執行** only. Readiness is static contract/entrypoint validation,
not an enabled flag, proof of host applicability or execution authorization.

Every detail page uses the same content/declarations/defaults/category/history
response and renderer. Its content section checks every three seconds, updates
only when the displayed definition/readiness changes, and preserves open resource
sections and scroll. Other form controls are not replaced, so unsaved default
edits remain intact. Reload before saving defaults after a definition change to
obtain current options/revisions. Failed refreshes retain the last visible content
and report the failure. The index requires refresh to discover new recipes.

Creation scope permits local authoring, not browser acquisition, SSH connections,
installation, execution or publication. Resource text is inert and escaped. Do
not import/eval virtual Python plans or generate missing utilities on each run.
Private bindings stay in the selected Profile; keep credentials out of descriptors
and resource previews. No watcher automatically turns chat into saved definitions:
the agent explicitly saves milestones. Do not add a dummy runner automatically.

## One descriptor, optional content

The existing descriptor 0.3.0 retains its execution-specific contracts. Authoring
adds optional `resources` and `authoring` fields to that ordinary mapping:

```yaml
descriptor_version: "0.3.0"
id: monthly-rate
version: ""
title: ""
description: ""
runner: {}
inputs:
  variables: {}
output: {}
resources: {}
```

Executable recipes use the same fields and their actual runner declaration.
Existing Python-session/Core/report/routine/meal validators remain authoritative;
configured entrypoints must exist and satisfy the chosen contract and versions.
An absent/empty runner or missing entrypoint is `contract: not-configured`,
`status: success`, `runnable: false` in static inspection/catalog. A supplied but
invalid implementation fails static checks and cannot execute. Optional missing
purpose/version fields remain empty and are listed as missing on the detail page.
The legacy inventory-system inspector keeps its explicit existing contract.
No runner is inferred from resource text, a filename or a plan's callable names.
Use an empty mapping for an unset runner, not null.

`resources` maps at most 50 safe relative names to UTF-8 text, including flow plans,
contracts and reviewed routine sources. Empty resources are valid. This is common
optional descriptive content for any recipe, not a second execution format. Text
is embedded in the descriptor; it does not materialize executable files. Real
runner/code files remain ordinary recipe-directory files and are never generated,
modified or deleted by the descriptor save service. Binary resources are not
supported by this text-preview field. Descriptor size is limited to 1 MiB.

`authoring` is optional bookkeeping containing exactly `schema_version: "0.1.0"`,
a positive integer `change_number`, timezone-aware `updated_at`, and text `summary`.
It is independent of semantic recipe `version` and execution records. Recipes
without it use change number 0 and blank update text in the same interface.
Only the latest descriptor is current; private backups are not an execution journal.

## Shared Python and always-JSON CLI

Use the selected product interpreter from the checkout:

```python
from pathlib import Path
from opsfeast import Instance
from opsfeast.recipe_authoring import new_definition, inspect, save

selected = Instance.open(Path.cwd()).profile("main")
definition = new_definition(":finance/monthly-rate", title="Monthly USD rate")
created = save(selected, ":finance/monthly-rate", expected_revision=None,
               definition=definition, summary="Created purpose")
current = inspect(selected, ":finance/monthly-rate")
definition = current["definition"]
definition["resources"]["flow.plan.md"] = "# 01: Acquire a rendered table.\n"
saved = save(selected, ":finance/monthly-rate",
             expected_revision=current["revision"], definition=definition,
             summary="Added first step")
```

`save` replaces the complete descriptor. Preserve unrelated fields when updating;
omitted definition fields/resources are removed. Its scope is Profile recipes
only (`:path`); Bundle/external definitions are read-only through this writer.
`inspect` reads exact enabled Profile/Bundle/registered-source references. It
returns the complete definition plus content/readiness fields without importing
candidate code, connecting hosts, changing the default Profile or creating files.

Save `{expected_revision, definition, summary}` to a JSON snapshot, then run:

```sh
python -B -m opsfeast.recipe_authoring --profile main --reference :finance/monthly-rate --snapshot /tmp/monthly-rate.json
python -B -m opsfeast.recipe_authoring --profile main --reference :finance/monthly-rate
```

Commands always emit JSON on success, stderr and exit 1 on errors. `--product PATH`
selects an existing checkout. `expected_revision=null` creates only; updates require
the current SHA-256 descriptor-content `revision`, not a change-number counter.
Cooperating writers use a POSIX lock and atomic replacement; stale/non-cooperating
edits fail rather than being overwritten. Prior descriptor bytes go to private
`.recipe-authoring-backups/SHA256.yaml`. Safe names exclude traversal/absolute
paths, and symlinked recipe paths/descriptors are rejected. No delete, promote,
install, import or run operation is provided here.

## Shared Web read contract

Administrator-authenticated `GET /api/v1/recipe-content?profile=NAME&reference=REF`
returns the same content view for every recipe: schema_version, profile/reference,
revision, view_revision, change_number, updated_at, summary, definition, title,
description, version, runner, resources, runnable, missing_fields and errors.
`view_revision` covers descriptor revision and displayed static readiness/errors,
so adding a valid real entrypoint can reveal the add-to-plate action even without
rewriting the descriptor. It is not the save revision or a complete package digest.
Reads resolve one exact source and do not scan saved execution/retention histories.
Web responses apply the existing sensitive-key masking to definition/content fields;
local authoring reads retain the full definition for edits. Never embed credentials
in resource text, which is intended for human-readable local review.
`GET /api/v1/recipe-detail` always includes `recipe`, `declarations`, `defaults`,
`preferences`, `saved`, `reports`, `attempts`, `content`; there is no alternate payload
for incomplete definitions. No Web authoring mutation endpoint is introduced.

## Human-readable purpose, metadata and composition

The shared detail page presents the operator workflow first: business title and
purpose, declared collection fields with their editable options, common settings,
human-readable execution conditions, category controls and recent outcomes/report
links. Users reach **Technical details and composition** only below these sections.
Raw field contracts are absent from the top collection view; raw saved JSON is in
the lower technical area. Machine field codes and runner protocols are kept out of
the human execution-condition summary.

The shared read model separates four concerns:

1. Name and business purpose: title and description only.
2. Definition information: exact reference, ID, version, static state, update time
   and change number. The latest authoring summary is a separate closed disclosure.
3. Execution conditions: human-readable missing/invalid execution prerequisites.
4. Recipe composition: plan, step contracts, utilities, implementation/entrypoint,
   inputs, outputs, verification, dependencies, permission/effect declarations,
   guide and additional assets, including currently absent components.

Composition presence is not an execution-success or test-passed claim. Items are
marked execution-required for the selected current contract, or optional; an absent
optional plan/README/test file does not make a valid script non-runnable. Required
input declarations and routine/meal permission/routine metadata are distinguished.
Execution conditions use the actual static inspector; the structured gaps explain
missing runner/entrypoint/version/output declarations, unavailable entry files and
static validation failures. No gate, provider or flow execution is inferred from
prose. Host applicability and the human execution grant remain separate.

Optional descriptor `resource_titles` maps existing embedded resource paths to
nonempty, single-line human labels (at most 120 characters each). Unknown resource
keys are refused. When removing a resource, remove its title too. For example:

```yaml
resources:
  flow.plan.md: "# 01: Acquire a rendered table."
resource_titles:
  flow.plan.md: Monthly USD acquisition plan
```

The page groups resource previews under semantic roles, uses these labels for
resource disclosures, and retains the filename as secondary source information.
Without a custom label, the role name is used. Existing canonical files (README,
plan, dependency files, declared entrypoint and files under the known component
directories) are recognized by safe, bounded existence checks; they are not
misreported as absent just because they are outside the embedded text map.
These filesystem entries are listed as existing files, not loaded/imported or
silently copied into preview resources. Embedded text takes precedence over a
same-named file. Presence does not verify content, dependencies, tests or authority.

`inspect()` and both authenticated detail/content reads include:

- `components`: ordered records with stable `id`, `required_for_execution`,
  `state` (`provided`, `file_present`, `declared`, `missing`), `resources` entries
  (`path`, `title`), safe existing `files`, and relevant metadata `fields`;
- `execution_blockers`: records with a stable reason `code`, relevant `field`,
  and original inspector `errors` for static validation failures;
- `resource_titles`: the declared embedded-resource label map.

Role IDs are `plan`, `step_contracts`, `utilities`, `execution`, `inputs`, `outputs`,
`verification`, `dependencies`, `permissions`, `guide`, `assets`. Current typed
reason codes include runner_contract_missing, runner_version_missing,
entrypoint_missing, entrypoint_unavailable, version_missing,
descriptor_version_missing, output_schema_missing and static_validation_failed.
Consumers localize labels rather than treating filenames/error codes as the human
explanation. Reuse `opsfeast.recipe_authoring.inspect()` for this shared read model;
`recipe_structure.describe` is its internal implementation helper, not a runner.
`view_revision` covers displayed composition/readiness as well as descriptor edits.
Polling refreshes separate purpose/readiness/technical slots, preserving opened
resource and metadata disclosures without replacing other forms or their unsaved
values. Execution protocol/error details and raw declarations stay in the lower
technical area; section moves do not change API contracts, defaults, authorization
or saved data. The USD case has readable resource titles and, at this revision, explicitly
lacks an execution contract, actual entrypoint and output schema declaration.

## Development-stage replacement and verification

The former `lifecycle: draft` / nested `draft` structure, draft module/CLI and
`/api/v1/recipe-draft` endpoint are removed, with no compatibility adapter or
automatic general migration. Obsolete fields fail validation explicitly. The
owner's requested USD case was converted in place with its previous bytes backed
up, resources retained and its review URL unchanged. Its runner stays empty and
no case action ran. Other old private definitions require an explicitly scoped
conversion before use; existing ordinary executable descriptors need no change.

Public tests cover blank content, common detail/API shapes, inert resources,
entrypoint absent/added/invalid transitions, digest conflicts, path/source limits,
CLI/error handling, authenticated reads, escaped rendering and content-only polling.
Synthetic checks do not prove bank extraction, host access or monthly-job results.
See [execution](recipe-execution.md), [flow design](recipe-flow-design.md) and the
[USD plan](recipe-flow-exchange-rate.md) for their separate limits.

## Launch guidance

Set `launch: {mode: agent, prompt: ...}` for a Recipe requiring an active agent.
The same descriptor/detail page remains in use; this introduces no draft lifecycle.
Keep `runnable` as static code readiness and use `web_runnable` for direct Web
launch eligibility. [The launch contract](python-workflows.md#agent-conversation-as-the-launch-surface)
defines validation, prompt display/copy, Web rejection and agent CLI execution.
Do not embed credentials or treat the saved prompt as an execution grant.

*Last modified: 2026-11-17 17:37:43*
